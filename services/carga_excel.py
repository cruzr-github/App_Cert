"""
services/carga_excel.py
Servicio para leer los archivos Excel y validar sus columnas.
Las funciones aceptan una ruta o un archivo en memoria (por ejemplo io.BytesIO).
Si no se les pasa nada, leen los Excel de fábrica de la carpeta insumos/.
La escritura en la base de datos se conserva para el script cargar_datos.py.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from models.datos import (
    crear_tablas,
    limpiar_tablas,
    guardar_estudiantes,
    guardar_evaluaciones,
    contar_estudiantes,
    contar_evaluaciones,
)

COLUMNAS_ESTUDIANTES = ["Identificacion", "Nombre_Completo", "Correo", "Programa", "Cohorte"]
COLUMNAS_EVALUACIONES = ["Identificacion", "Programa", "Modulo", "Nota", "Asistencia_Pct", "Fecha_Cierre"]

# Rutas absolutas a los Excel de fábrica, sin depender de la carpeta desde donde se ejecute
BASE_DIR = Path(__file__).resolve().parent.parent
RUTA_MAESTRO_FABRICA = BASE_DIR / "insumos" / "Maestro_Estudiantes.xlsx"
RUTA_EVALUACIONES_FABRICA = BASE_DIR / "insumos" / "Registro_Evaluaciones.xlsx"


def leer_y_validar_maestro(ruta_o_archivo=None) -> List[Dict[str, Any]]:
    """
    Lee el archivo Excel de estudiantes y valida las columnas requeridas.
    Si no se recibe nada, usa el Maestro_Estudiantes.xlsx de insumos/.
    """
    fuente = ruta_o_archivo if ruta_o_archivo is not None else RUTA_MAESTRO_FABRICA
    df = pd.read_excel(fuente, sheet_name="Estudiantes", dtype=str)

    # Validar columnas
    columnas_faltantes = [c for c in COLUMNAS_ESTUDIANTES if c not in df.columns]
    if columnas_faltantes:
        raise ValueError(f"El archivo de Estudiantes no contiene las columnas requeridas: {columnas_faltantes}")

    # Limpieza de datos
    estudiantes = []
    for _, fila in df.iterrows():
        ident = str(fila["Identificacion"]).strip()
        nombre = str(fila["Nombre_Completo"]).strip()
        correo = str(fila["Correo"]).strip() if pd.notna(fila.get("Correo")) else None
        programa = str(fila["Programa"]).strip()
        cohorte = str(fila["Cohorte"]).strip() if pd.notna(fila.get("Cohorte")) else None

        if ident and ident != "nan":
            # Un archivo con celdas obligatorias vacías no debe generar resultados falsos
            if nombre.lower() == "nan" or not nombre or programa.lower() == "nan" or not programa:
                raise ValueError(
                    "El archivo de Estudiantes tiene filas sin Nombre_Completo o sin Programa."
                )
            estudiantes.append({
                "identificacion": ident,
                "nombre_completo": nombre,
                "correo": correo,
                "programa": programa,
                "cohorte": cohorte,
            })

    return estudiantes


def leer_y_validar_evaluaciones(ruta_o_archivo=None) -> List[Dict[str, Any]]:
    """
    Lee el archivo Excel de evaluaciones y valida las columnas requeridas.
    Si no se recibe nada, usa el Registro_Evaluaciones.xlsx de insumos/.
    """
    fuente = ruta_o_archivo if ruta_o_archivo is not None else RUTA_EVALUACIONES_FABRICA
    # La identificación siempre se lee como texto para no perder ceros ni volverla "123.0"
    df = pd.read_excel(
        fuente, sheet_name="Evaluaciones", dtype={"Identificacion": str}
    )

    # Validar columnas
    columnas_faltantes = [c for c in COLUMNAS_EVALUACIONES if c not in df.columns]
    if columnas_faltantes:
        raise ValueError(f"El archivo de Evaluaciones no contiene las columnas requeridas: {columnas_faltantes}")

    # Limpieza de datos
    evaluaciones = []
    for _, fila in df.iterrows():
        ident = str(fila["Identificacion"]).strip()
        programa = str(fila["Programa"]).strip()
        modulo = str(fila["Modulo"]).strip()

        # Nota y asistencia vacías no pueden convertirse en un certificado
        if pd.isna(fila["Nota"]) or pd.isna(fila["Asistencia_Pct"]):
            raise ValueError(
                "El archivo de Evaluaciones tiene filas sin Nota o sin Asistencia_Pct."
            )
        if programa.lower() == "nan" or not programa or modulo.lower() == "nan" or not modulo:
            raise ValueError(
                "El archivo de Evaluaciones tiene filas sin Programa o sin Modulo."
            )

        nota = float(fila["Nota"])
        asistencia_pct = float(fila["Asistencia_Pct"])

        fecha_cierre = None
        if pd.notna(fila.get("Fecha_Cierre")):
            # Convertir a formato de fecha YYYY-MM-DD
            fecha_cierre = pd.to_datetime(fila["Fecha_Cierre"]).strftime("%Y-%m-%d")

        if ident and ident != "nan":
            evaluaciones.append({
                "identificacion": ident,
                "programa": programa,
                "modulo": modulo,
                "nota": nota,
                "asistencia_pct": asistencia_pct,
                "fecha_cierre": fecha_cierre,
            })

    return evaluaciones


def leer_datos(
    archivo_maestro=None,
    archivo_evaluaciones=None,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Lee y devuelve (estudiantes, evaluaciones).
    - Sin argumentos: lee los dos Excel de fábrica de insumos/.
    - Con archivos: lee los archivos recibidos, que pueden ser rutas o BytesIO.
    """
    estudiantes = leer_y_validar_maestro(archivo_maestro)
    evaluaciones = leer_y_validar_evaluaciones(archivo_evaluaciones)
    return estudiantes, evaluaciones


def cargar_datos_desde_archivos(
    ruta_maestro: Optional[str] = None,
    ruta_evaluaciones: Optional[str] = None,
) -> Tuple[int, int]:
    """
    Crea las tablas si no existen, lee los dos Excel, limpia los datos previos
    y guarda la nueva información en la base de datos Supabase.
    Lo usa el script cargar_datos.py; la web ya no escribe en la base.
    Retorna la cantidad de estudiantes y evaluaciones guardadas.
    """
    # 1. Asegurar que las tablas existan
    crear_tablas()

    # 2. Leer y validar ambos Excel (si no se indican rutas, usa insumos/)
    lista_estudiantes = leer_y_validar_maestro(ruta_maestro)
    lista_evaluaciones = leer_y_validar_evaluaciones(ruta_evaluaciones)

    # 3. Limpiar tablas existentes para reemplazo limpio
    limpiar_tablas()

    # 4. Guardar datos
    guardar_estudiantes(lista_estudiantes)
    guardar_evaluaciones(lista_evaluaciones)

    # 5. Retornar conteos verificados desde la base de datos
    total_est = contar_estudiantes()
    total_eval = contar_evaluaciones()

    return total_est, total_eval
