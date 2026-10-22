"""
controllers/auth.py
Controlador de acceso: rutas /login y /salir, y decoradores de permisos
(requiere_login y solo_admin).
Arquitectura MVC: no calcula reglas de negocio; delega la validación de
credenciales en models.usuarios y solo maneja la sesión de Flask.
"""

from functools import wraps
from urllib.parse import urlsplit

from flask import (
    Blueprint,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from models.usuarios import autenticar, es_modo_demo

auth_bp = Blueprint("auth", __name__)


def requiere_login(vista):
    """
    Decorador que protege las rutas que muestran datos.
    Si no hay sesión iniciada, guarda el destino y manda a /login.
    """
    @wraps(vista)
    def envoltura(*args, **kwargs):
        if not session.get("correo"):
            flash("Debes iniciar sesión para ver esta página.", "warning")
            return redirect(url_for("auth.login", next=request.path))
        return vista(*args, **kwargs)

    return envoltura


def solo_admin(vista):
    """
    Decorador que permite el paso únicamente al rol "admin".
    Si la sesión tiene otro rol (o no tiene rol), responde 403 con una
    página amable. Debe usarse después de @requiere_login.
    """
    @wraps(vista)
    def envoltura(*args, **kwargs):
        if session.get("rol") != "admin":
            return render_template("sin_permiso.html"), 403
        return vista(*args, **kwargs)

    return envoltura


def _destino_seguro(destino: str):
    """
    Solo permite redirecciones internas (por ejemplo "/cargar").
    Evita que alguien use ?next=https://sitio-falso.com como trampa.
    """
    if not destino:
        return None

    # Rechazar barras invertidas (los navegadores las convierten en "/")
    if "\\" in destino or "%5c" in destino.lower():
        return None

    partes = urlsplit(destino)
    if partes.scheme or partes.netloc:
        return None
    if not destino.startswith("/") or destino.startswith("//"):
        return None
    return destino


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """Muestra el formulario de entrada y valida correo + contraseña."""
    # Si ya hay sesión, no tiene sentido volver a entrar
    if session.get("correo"):
        return redirect(url_for("tablero.index"))

    modo_demo = es_modo_demo()

    if request.method == "POST":
        correo = request.form.get("correo", "").strip()
        clave = request.form.get("clave", "")

        usuario = autenticar(correo, clave)
        if not usuario:
            # Mensaje rojo en la misma pantalla, sin revelar cuál dato falló
            return (
                render_template(
                    "login.html",
                    error="Correo o contraseña incorrectos.",
                    correo=correo,
                    modo_demo=modo_demo,
                ),
                401,
            )

        # Sesión nueva para evitar fijación de sesión
        session.clear()
        session["correo"] = usuario["correo"]
        session["rol"] = usuario["rol"]

        destino = _destino_seguro(request.args.get("next", ""))
        return redirect(destino or url_for("tablero.index"))

    return render_template("login.html", modo_demo=modo_demo)


@auth_bp.route("/salir")
def salir():
    """Borra la sesión y devuelve a la pantalla de entrada."""
    session.clear()
    flash("Has cerrado sesión correctamente.", "success")
    return redirect(url_for("auth.login"))
