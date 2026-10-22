"""
models/usuarios.py
Usuarios de acceso a la aplicación SIN base de datos (todavía no existe).
Las credenciales se leen de variables de entorno mediante python-dotenv:
    ADMIN_CORREO / ADMIN_CLAVE      -> rol "admin"
    USUARIO_CORREO / USUARIO_CLAVE  -> rol "usuario"
Si alguna variable falta, se usan credenciales de demostración y la pantalla
de entrada muestra un aviso de "modo demostración".
NUNCA se escriben contraseñas reales en este archivo.
"""

import hmac
import os
from typing import Any, Dict, List, Optional, Tuple

from dotenv import load_dotenv

# Cargar variables desde .env (en Vercel llegan como variables de entorno)
load_dotenv()

# Credenciales de demostración: solo se usan cuando faltan las variables reales.
DEMO_ADMIN_CORREO = "admin@academia.cr"
DEMO_ADMIN_CLAVE = "admin123"
DEMO_USUARIO_CORREO = "usuario@academia.cr"
DEMO_USUARIO_CLAVE = "usuario123"


def _leer_credencial(nombre_variable: str, valor_demo: str) -> Tuple[str, bool]:
    """
    Lee una variable de entorno y devuelve (valor, es_demo).
    Si la variable no existe o está vacía, devuelve el valor de demostración.
    """
    valor = os.environ.get(nombre_variable, "").strip()
    if not valor:
        return valor_demo, True
    return valor, False


def obtener_usuarios() -> Tuple[List[Dict[str, str]], bool]:
    """
    Devuelve la lista de usuarios configurados y si la app está en modo demostración.
    Cada usuario tiene correo, clave y rol. La clave solo se usa para comparar
    en el momento del ingreso; nunca se envía a las plantillas.
    """
    admin_correo, admin_demo = _leer_credencial("ADMIN_CORREO", DEMO_ADMIN_CORREO)
    admin_clave, admin_clave_demo = _leer_credencial("ADMIN_CLAVE", DEMO_ADMIN_CLAVE)
    usuario_correo, usuario_demo = _leer_credencial("USUARIO_CORREO", DEMO_USUARIO_CORREO)
    usuario_clave, usuario_clave_demo = _leer_credencial("USUARIO_CLAVE", DEMO_USUARIO_CLAVE)

    usuarios = [
        {"correo": admin_correo, "clave": admin_clave, "rol": "admin"},
        {"correo": usuario_correo, "clave": usuario_clave, "rol": "usuario"},
    ]

    modo_demo = any(
        [admin_demo, admin_clave_demo, usuario_demo, usuario_clave_demo]
    )
    return usuarios, modo_demo


def es_modo_demo() -> bool:
    """Indica si falta alguna credencial real y se están usando las de demostración."""
    _, modo_demo = obtener_usuarios()
    return modo_demo


def autenticar(correo: str, clave: str) -> Optional[Dict[str, str]]:
    """
    Busca un usuario por correo (sin distinguir mayúsculas) y compara la clave.
    Devuelve {"correo", "rol"} si las credenciales son correctas, o None si no.
    """
    correo_limpio = (correo or "").strip().lower()
    clave_ingresada = clave or ""

    usuarios, _ = obtener_usuarios()
    for usuario in usuarios:
        if usuario["correo"].strip().lower() != correo_limpio:
            continue
        # Se comparan bytes para admitir contraseñas con tildes o "ñ"
        # compare_digest evita filtrar información por el tiempo de comparación
        if hmac.compare_digest(
            clave_ingresada.encode("utf-8"), usuario["clave"].encode("utf-8")
        ):
            return {"correo": usuario["correo"], "rol": usuario["rol"]}
    return None
