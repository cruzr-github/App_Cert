"""
controllers/tablero.py
Controlador del tablero principal (/), la carga de Excel (/cargar), la emisión
de certificados individuales y la descarga masiva.
Arquitectura MVC: no aplica reglas de negocio ni escribe SQL. Lee los datos a
través de services, deja que models.certificados calcule y solo coordina la
respuesta para el navegador.
"""

import io
import zipfile
from urllib.parse import unquote

from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    send_file,
    session,
    url_for,
)

from controllers.auth import requiere_login, solo_admin
from models.certificados import procesar_certificados_e_inconsistencias
from services.carga_excel import leer_datos
from services.generador_excel import crear_excel_resultados
from services.generador_pdf import crear_pdf_certificado

tablero_bp = Blueprint("tablero", __name__)

# Límite por archivo (Vercel rechaza peticiones de más de 4.5 MB)
LIMITE_ARCHIVO_BYTES = 4 * 1024 * 1024
ORIGEN_FABRICA = (
    "Datos de fábrica (insumos/Maestro_Estudiantes.xlsx y "
    "insumos/Registro_Evaluaciones.xlsx)"
)
TIPO_EXCEL = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _datos_fabrica():
    """Lee los Excel de insumos y aplica las reglas de negocio existentes."""
    estudiantes, evaluaciones = leer_datos()
    return procesar_certificados_e_inconsistencias(estudiantes, evaluaciones)


def _datos_vacios():
    """Estructura mínima para que la plantilla no falle si la lectura falla."""
    return {
        "totales": {"Aprobación": 0, "Participación": 0, "Sin certificado": 0},
        "inconsistencias": [],
        "estudiantes": [],
    }


def _vista_tablero(datos, origen, datos_subidos=False, error=None):
    """
    Renderiza el tablero aplicando la privacidad por rol:
    el usuario normal no recibe inconsistencias ni alertas internas.
    """
    es_admin = session.get("rol") == "admin"

    estudiantes = datos["estudiantes"]
    if not es_admin:
        estudiantes = [dict(est, alerta=None) for est in estudiantes]

    return render_template(
        "tablero.html",
        totales=datos["totales"],
        inconsistencias=datos["inconsistencias"] if es_admin else [],
        estudiantes=estudiantes,
        origen=origen,
        datos_subidos=datos_subidos,
        error=error,
    )


def _tablero_con_error(mensaje):
    """Vuelve al tablero con datos de fábrica y un aviso rojo, sin dejar la página en blanco."""
    try:
        datos = _datos_fabrica()
    except Exception:
        current_app.logger.exception("No se pudieron leer los Excel de fábrica")
        datos = _datos_vacios()
    return _vista_tablero(datos, ORIGEN_FABRICA, error=mensaje)


@tablero_bp.route("/")
@requiere_login
def index():
    """Muestra el tablero con los datos de fábrica (o los que se hayan subido en esta pantalla)."""
    try:
        datos = _datos_fabrica()
    except Exception:
        current_app.logger.exception("No se pudieron leer los Excel de fábrica")
        return _vista_tablero(
            _datos_vacios(),
            "Sin datos",
            error="No se pudieron leer los Excel de fábrica. Revisa que estén en la carpeta insumos/.",
        )

    return _vista_tablero(datos, ORIGEN_FABRICA)


@tablero_bp.route("/cargar", methods=["GET", "POST"])
@requiere_login
@solo_admin
def cargar():
    """
    Procesa los dos Excel subidos, siempre en memoria.
    - accion="ver": muestra la tabla con los datos subidos (no se guardan).
    - accion="excel": devuelve un Excel con los resultados calculados.
    """
    # El panel ahora vive en la página principal
    if request.method == "GET":
        return redirect(url_for("tablero.index", _anchor="panel-admin"))

    archivo_maestro = request.files.get("archivo_maestro")
    archivo_evaluaciones = request.files.get("archivo_evaluaciones")

    # Validar que los dos archivos hayan llegado con un nombre
    if (
        not archivo_maestro
        or not archivo_maestro.filename
        or not archivo_evaluaciones
        or not archivo_evaluaciones.filename
    ):
        return _tablero_con_error(
            "Debes seleccionar los dos archivos: Maestro de estudiantes y Registro de evaluaciones."
        )

    nombre_maestro = archivo_maestro.filename
    nombre_evaluaciones = archivo_evaluaciones.filename

    # Validar la extensión antes de intentar leer el contenido
    for nombre in (nombre_maestro, nombre_evaluaciones):
        if not nombre.lower().endswith(".xlsx"):
            return _tablero_con_error(
                f"El archivo «{nombre}» no es un Excel .xlsx válido. "
                "Sube los dos archivos oficiales en formato .xlsx."
            )

    try:
        contenido_maestro = archivo_maestro.read()
        contenido_evaluaciones = archivo_evaluaciones.read()

        if (
            len(contenido_maestro) > LIMITE_ARCHIVO_BYTES
            or len(contenido_evaluaciones) > LIMITE_ARCHIVO_BYTES
        ):
            return _tablero_con_error(
                "El envío supera el límite de 4 MB. Reduce el tamaño de los archivos e intenta de nuevo."
            )

        # BytesIO es como una caja vacía en la memoria RAM: guardamos ahí los
        # bytes del archivo subido y pandas lo lee como si fuera un archivo normal,
        # sin escribir nada en el disco (que en Vercel es de solo lectura).
        estudiantes, evaluaciones = leer_datos(
            io.BytesIO(contenido_maestro),
            io.BytesIO(contenido_evaluaciones),
        )
        datos = procesar_certificados_e_inconsistencias(estudiantes, evaluaciones)
    except ValueError as error:
        # Errores esperables de archivos mal formados (sin traza técnica en el log)
        current_app.logger.warning("Excel rechazado: %s", error)
        return _tablero_con_error(
            "No pudimos leer los archivos. Verifica que sean los Excel oficiales "
            "(.xlsx) con las hojas «Estudiantes» y «Evaluaciones», sus columnas "
            "y sin celdas obligatorias vacías."
        )
    except Exception:
        current_app.logger.exception("Error inesperado al procesar los Excel subidos")
        return _tablero_con_error(
            "No pudimos leer los archivos. Verifica que sean los Excel oficiales "
            "(.xlsx) con las hojas «Estudiantes» y «Evaluaciones» y sus columnas."
        )

    # El botón "Procesar y descargar Excel" devuelve el archivo sin mostrar la tabla
    if request.form.get("accion") == "excel":
        contenido = crear_excel_resultados(datos)
        return send_file(
            io.BytesIO(contenido),
            mimetype=TIPO_EXCEL,
            as_attachment=True,
            download_name="resultados_excel.xlsx",
        )

    # El botón "Procesar y ver en pantalla" muestra los resultados solo en esta respuesta
    origen = f"Archivos subidos: {nombre_maestro} y {nombre_evaluaciones}"
    return _vista_tablero(datos, origen, datos_subidos=True)


@tablero_bp.route("/descargar-excel")
@requiere_login
@solo_admin
def descargar_excel_fabrica():
    """Descarga en Excel los resultados calculados con los datos de fábrica."""
    try:
        datos = _datos_fabrica()
    except Exception:
        current_app.logger.exception("No se pudieron leer los Excel de fábrica")
        flash("No se pudieron leer los Excel de fábrica. Revisa la carpeta insumos/.", "danger")
        return redirect(url_for("tablero.index"))

    contenido = crear_excel_resultados(datos)
    return send_file(
        io.BytesIO(contenido),
        mimetype=TIPO_EXCEL,
        as_attachment=True,
        download_name="resultados_fabrica.xlsx",
    )


@tablero_bp.route("/certificado/<identificacion>/<path:programa>")
@requiere_login
def descargar_certificado(identificacion: str, programa: str):
    """
    Genera y sirve el certificado PDF individual para un estudiante elegible.
    No se genera certificado si el estado es 'Sin certificado' o presenta inconsistencias.
    """
    ident_limpia = str(identificacion).strip()
    prog_limpio = unquote(programa).strip()

    datos = _datos_fabrica()
    estudiante = None
    for est in datos["estudiantes"]:
        if str(est["identificacion"]).strip() == ident_limpia and str(est["programa"]).strip() == prog_limpio:
            estudiante = est
            break

    if not estudiante:
        abort(404, description="Estudiante no encontrado en el programa especificado.")

    # Regla: No se genera certificado para 'Sin certificado' ni inconsistencias
    if not estudiante.get("emite_certificado") or estudiante.get("estado") == "Sin certificado":
        abort(403, description="El estudiante no cumple con los requisitos para emisión de certificado.")

    pdf_bytes = crear_pdf_certificado(estudiante)
    nombre_archivo = f"Certificado_{ident_limpia}_{estudiante['estado']}.pdf"

    return send_file(
        io.BytesIO(pdf_bytes),
        mimetype="application/pdf",
        as_attachment=False,
        download_name=nombre_archivo,
    )


@tablero_bp.route("/descargar-todos")
@requiere_login
@solo_admin
def descargar_todos():
    """
    Genera en memoria un archivo .zip que contiene todos los certificados emitidos
    (Aprobación y Participación). Excluye 'Sin certificado' e inconsistencias.
    """
    datos = _datos_fabrica()
    estudiantes_elegibles = [
        est for est in datos["estudiantes"]
        if est.get("emite_certificado") and est.get("estado") in ["Aprobación", "Participación"]
    ]

    if not estudiantes_elegibles:
        flash("No hay certificados disponibles para descargar.", "warning")
        return redirect(url_for("tablero.index"))

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for est in estudiantes_elegibles:
            pdf_bytes = crear_pdf_certificado(est)
            nombre_limpio = est["nombre_completo"].replace(" ", "_")
            nombre_pdf = f"Certificado_{est['identificacion']}_{nombre_limpio}_{est['estado']}.pdf"
            zf.writestr(nombre_pdf, pdf_bytes)

    zip_buffer.seek(0)
    return send_file(
        zip_buffer,
        mimetype="application/zip",
        as_attachment=True,
        download_name="certificados_academia.zip",
    )
