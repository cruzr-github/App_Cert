"""
tests/test_app.py
Pruebas automáticas del flujo web con el cliente de pruebas de Flask.
No se abre el navegador ni se levanta el servidor: app.test_client() simula
las peticiones HTTP y conserva las cookies de sesión entre llamadas.

Las credenciales se definen ANTES de importar app para que las pruebas no
dependan del archivo .env de la máquina donde se ejecuten.
"""

import io
import os
import re
from pathlib import Path

import pandas as pd

# --- Credenciales aisladas para las pruebas (siempre antes de importar app) ---
os.environ["ADMIN_CORREO"] = "admin@prueba.cr"
os.environ["ADMIN_CLAVE"] = "clave-admin-prueba"
os.environ["USUARIO_CORREO"] = "usuario@prueba.cr"
os.environ["USUARIO_CLAVE"] = "clave-usuario-prueba"
os.environ["SECRET_KEY"] = "clave-secreta-de-pruebas"
os.environ["FLASK_SECRET_KEY"] = "clave-secreta-de-pruebas"

from app import app  # noqa: E402  (se importa después de definir el entorno)

BASE_DIR = Path(__file__).resolve().parent.parent
RUTA_MAESTRO = BASE_DIR / "insumos" / "Maestro_Estudiantes.xlsx"
RUTA_EVALUACIONES = BASE_DIR / "insumos" / "Registro_Evaluaciones.xlsx"

ADMIN_CORREO = os.environ["ADMIN_CORREO"]
ADMIN_CLAVE = os.environ["ADMIN_CLAVE"]
USUARIO_CORREO = os.environ["USUARIO_CORREO"]
USUARIO_CLAVE = os.environ["USUARIO_CLAVE"]


def _cliente():
    """Crea un navegador de pruebas nuevo, con su propia sesión vacía."""
    app.config["TESTING"] = True
    return app.test_client()


def _entrar(cliente, correo: str, clave: str):
    """Simula escribir el correo y la contraseña en la pantalla de entrada."""
    return cliente.post("/login", data={"correo": correo, "clave": clave})


def _contadores(html: str):
    """Extrae los tres números grandes de las tarjetas del tablero, en orden."""
    return [
        int(numero)
        for numero in re.findall(
            r'class="metrica-numero[^"]*"[^>]*>\s*(\d+)', html
        )
    ]


def test_sin_sesion_redirige_a_login():
    """Simula abrir la página principal sin haber iniciado sesión."""
    cliente = _cliente()

    respuesta = cliente.get("/")

    assert respuesta.status_code == 302
    assert "/login" in respuesta.headers["Location"]


def test_clave_incorrecta_no_entra():
    """Simula escribir un correo válido con una contraseña equivocada."""
    cliente = _cliente()

    respuesta = _entrar(cliente, ADMIN_CORREO, "esta-clave-no-es")

    # 401 significa "no autorizado": sigue en la pantalla de entrada
    assert respuesta.status_code == 401
    html = respuesta.get_data(as_text=True)
    assert "Correo o contraseña incorrectos." in html
    assert "Acceso al sistema" in html

    # La sesión no quedó iniciada: la página principal vuelve a mandar al login
    assert cliente.get("/").status_code == 302


def test_usuario_no_puede_cargar():
    """Simula que una persona con rol 'usuario' intenta abrir la carga de Excel."""
    cliente = _cliente()
    _entrar(cliente, USUARIO_CORREO, USUARIO_CLAVE)

    respuesta = cliente.get("/cargar")

    assert respuesta.status_code == 403
    assert "solo para administradores" in respuesta.get_data(as_text=True).lower()


def _evaluaciones_con_camila_en_40():
    """
    Lee el Excel de evaluaciones de insumos y devuelve otro Excel en memoria
    con las cuatro notas de Camila (101230456) en 40. El archivo original
    nunca se modifica: solo se lee y el resultado se escribe en un BytesIO.
    """
    df = pd.read_excel(
        RUTA_EVALUACIONES,
        sheet_name="Evaluaciones",
        dtype={"Identificacion": str},
    )

    es_camila = df["Identificacion"].astype(str).str.strip() == "101230456"
    assert es_camila.any(), "La prueba esperaba encontrar a Camila en el Excel de insumos"
    df.loc[es_camila, "Nota"] = 40

    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Evaluaciones", index=False)
    buffer.seek(0)
    return buffer


def test_excel_modificado_cambia_contadores():
    """
    Simula que el admin sube un Registro de Evaluaciones modificado.
    Al bajar las notas de Camila a 40, ella pasa de Aprobación a Participación:
    18 aprobaciones, 4 participaciones y 1 sin certificado.
    """
    cliente = _cliente()
    _entrar(cliente, ADMIN_CORREO, ADMIN_CLAVE)

    maestro = io.BytesIO(RUTA_MAESTRO.read_bytes())
    evaluaciones = _evaluaciones_con_camila_en_40()

    respuesta = cliente.post(
        "/cargar",
        data={
            "archivo_maestro": (maestro, "Maestro_Estudiantes.xlsx"),
            "archivo_evaluaciones": (evaluaciones, "Registro_Evaluaciones.xlsx"),
            "accion": "ver",
        },
        content_type="multipart/form-data",
    )

    assert respuesta.status_code == 200
    html = respuesta.get_data(as_text=True)

    # Las tres tarjetas deben reflejar el cambio, sin tocar la base de datos
    assert _contadores(html) == [18, 4, 1]

    # Debe avisarse que son datos subidos y que no se guardan
    assert "acabas de subir" in html.lower()
    assert "Registro_Evaluaciones.xlsx" in html
