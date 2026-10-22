"""
models/certificados.py
Implementación de las reglas del negocio de AGENTS.md (R1 a R6) para la certificación de estudiantes.
Constantes fijas: NOTA_MINIMA = 70, ASISTENCIA_MINIMA = 80.
No habla con la base de datos directamente; recibe o solicita los datos a models.datos.
"""

from collections import defaultdict
from typing import Dict, Any, List, Tuple
from models.datos import obtener_estudiantes, obtener_evaluaciones

# Constantes fijas de negocio según AGENTS.md
NOTA_MINIMA = 70.0
ASISTENCIA_MINIMA = 80.0
ASISTENCIA_CRITICA = 50.0


def procesar_certificados_e_inconsistencias(
    estudiantes: List[Dict[str, Any]],
    evaluaciones: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Aplica las reglas R1 a R6 cruzando estudiantes y evaluaciones.
    Retorna un diccionario con totales, lista de resultados por estudiante y lista de inconsistencias.
    """
    # R1. Agrupar evaluaciones por identificacion + programa
    evals_por_grupo = defaultdict(list)
    idents_con_evaluaciones = set()

    for ev in evaluaciones:
        ident = str(ev["identificacion"]).strip()
        prog = str(ev["programa"]).strip()
        evals_por_grupo[(ident, prog)].append(ev)
        idents_con_evaluaciones.add(ident)

    # Mapeo de estudiantes del maestro
    maestro_map = {}
    idents_maestro = set()

    for est in estudiantes:
        ident = str(est["identificacion"]).strip()
        prog = str(est["programa"]).strip()
        maestro_map[(ident, prog)] = est
        idents_maestro.add(ident)

    inconsistencias = []
    resultados_estudiantes = []

    # Inconsistencia Tipo 2: Identificación con evaluaciones que no está en el maestro
    for ident in sorted(idents_con_evaluaciones):
        if ident not in idents_maestro:
            # Obtener programas asociados a esta identificación huérfana
            programas_asoc = {
                prog for (i, prog) in evals_por_grupo.keys() if i == ident
            }
            prog_str = ", ".join(programas_asoc) if programas_asoc else "Desconocido"
            inconsistencias.append({
                "tipo": "Identificación no registrada en el maestro",
                "identificacion": ident,
                "nombre": "No registrado en Maestro",
                "programa": prog_str,
                "detalle": "Tiene registros de evaluaciones pero no existe en el maestro de estudiantes.",
            })

    # Procesar estudiantes del maestro
    for (ident, prog), est in maestro_map.items():
        evals = evals_por_grupo.get((ident, prog), [])

        # Inconsistencia Tipo 1: Estudiante del maestro sin evaluaciones
        if not evals:
            inconsistencias.append({
                "tipo": "Estudiante sin evaluaciones",
                "identificacion": ident,
                "nombre": est["nombre_completo"],
                "programa": prog,
                "detalle": "El estudiante está matriculado en el maestro pero no cuenta con evaluaciones registradas.",
            })
            continue

        # R2. Promedio = promedio de nota. Asistencia = promedio de asistencia_pct. Redondear a 2 decimales.
        notas = [float(e["nota"]) for e in evals]
        asistencias = [float(e["asistencia_pct"]) for e in evals]

        prom_nota = round(sum(notas) / len(notas), 2)
        prom_asist = round(sum(asistencias) / len(asistencias), 2)

        # Inconsistencia Tipo 3: Asistencia menor al 50 %
        es_inconsistencia_asistencia = prom_asist < ASISTENCIA_CRITICA
        if es_inconsistencia_asistencia:
            inconsistencias.append({
                "tipo": "Asistencia crítica (< 50%)",
                "identificacion": ident,
                "nombre": est["nombre_completo"],
                "programa": prog,
                "detalle": f"Asistencia promedio de {prom_asist}%, por debajo del umbral mínimo del 50%.",
            })

        # Reglas de certificación (R3, R4, R5)
        # R3. Aprobación: promedio >= 70 y asistencia >= 80 (límites incluyen)
        # R4. Participación: promedio < 70 y asistencia >= 80
        # R5. Sin certificado: asistencia < 80
        if prom_asist >= ASISTENCIA_MINIMA:
            if prom_nota >= NOTA_MINIMA:
                estado = "Aprobación"
            else:
                estado = "Participación"
        else:
            estado = "Sin certificado"

        # R6. Inconsistencias no se certifican (emite_certificado indica si se puede generar PDF)
        emite_certificado = (estado in ["Aprobación", "Participación"]) and not es_inconsistencia_asistencia

        resultados_estudiantes.append({
            "identificacion": ident,
            "nombre_completo": est["nombre_completo"],
            "correo": est.get("correo") or "",
            "programa": prog,
            "cohorte": est.get("cohorte") or "",
            "promedio_nota": prom_nota,
            "promedio_asistencia": prom_asist,
            "estado": estado,
            "emite_certificado": emite_certificado,
            "alerta": "Asistencia crítica (< 50%)" if es_inconsistencia_asistencia else None,
        })

    # Ordenar por nombre de estudiante
    resultados_estudiantes.sort(key=lambda x: x["nombre_completo"])

    # Contadores de control
    conteo = {
        "Aprobación": sum(1 for r in resultados_estudiantes if r["estado"] == "Aprobación"),
        "Participación": sum(1 for r in resultados_estudiantes if r["estado"] == "Participación"),
        "Sin certificado": sum(1 for r in resultados_estudiantes if r["estado"] == "Sin certificado"),
    }

    return {
        "totales": conteo,
        "inconsistencias": inconsistencias,
        "estudiantes": resultados_estudiantes,
    }


def obtener_datos_tablero() -> Dict[str, Any]:
    """Obtiene los datos desde Supabase y calcula el estado del tablero."""
    estudiantes = obtener_estudiantes()
    evaluaciones = obtener_evaluaciones()
    return procesar_certificados_e_inconsistencias(estudiantes, evaluaciones)
