"""
services/generador_excel.py
Servicio para exportar los resultados del tablero a un archivo Excel.
Todo se arma en memoria (io.BytesIO): no se escribe nada en el disco,
porque en Vercel el sistema de archivos es de solo lectura.
"""

import io
from typing import Any, Dict

import pandas as pd


def crear_excel_resultados(datos: Dict[str, Any]) -> bytes:
    """
    Recibe el resultado ya calculado por models.certificados y devuelve
    los bytes de un Excel con la hoja Resultados y, si hay alertas,
    una hoja adicional de Inconsistencias.
    No aplica reglas de negocio: solo ordena lo que el modelo ya calculó.
    """
    filas = [
        {
            "Identificación": est["identificacion"],
            "Nombre completo": est["nombre_completo"],
            "Programa": est["programa"],
            "Cohorte": est["cohorte"],
            "Promedio nota": est["promedio_nota"],
            "Asistencia %": est["promedio_asistencia"],
            "Estado": est["estado"],
            "Emite certificado": "Sí" if est["emite_certificado"] else "No",
            "Alerta": est.get("alerta") or "",
        }
        for est in datos["estudiantes"]
    ]

    filas_inconsistencias = [
        {
            "Tipo": inc["tipo"],
            "Identificación": inc["identificacion"],
            "Nombre": inc["nombre"],
            "Programa": inc["programa"],
            "Detalle": inc["detalle"],
        }
        for inc in datos["inconsistencias"]
    ]

    # BytesIO es como una caja vacía en la memoria RAM: pandas "escribe" el Excel
    # ahí adentro y al final sacamos los bytes, sin tocar el disco.
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        pd.DataFrame(filas).to_excel(writer, sheet_name="Resultados", index=False)
        if filas_inconsistencias:
            pd.DataFrame(filas_inconsistencias).to_excel(
                writer, sheet_name="Inconsistencias", index=False
            )

    return buffer.getvalue()
