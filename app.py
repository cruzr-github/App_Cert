"""
app.py
Punto de entrada de la aplicación web Flask.
Inicializa la aplicación en la variable 'app', registra los controladores y levanta el servidor
en el puerto 5000 respetando la arquitectura MVC definida en AGENTS.md.
"""

import os
import secrets

from flask import Flask, flash, redirect, url_for
from dotenv import load_dotenv

# Cargar variables de entorno (.env en local, variables del panel en Vercel)
load_dotenv()

# Inicialización de la app Flask configurando la carpeta de plantillas en 'views'
app = Flask(__name__, template_folder="views")

# Clave para firmar la cookie de sesión. Debe venir de FLASK_SECRET_KEY.
# Si no existe, se genera una temporal: las sesiones se pierden al reiniciar.
app.secret_key = os.getenv("FLASK_SECRET_KEY") or secrets.token_hex(32)

# La cookie de sesión no es accesible desde JavaScript y no se envía entre sitios
# MAX_CONTENT_LENGTH corta los envíos de más de 4 MB antes de llegar a Vercel (4.5 MB)
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=bool(os.getenv("VERCEL")),
    MAX_CONTENT_LENGTH=4 * 1024 * 1024,
)

# Registro de controladores (rutas)
from controllers.auth import auth_bp
from controllers.tablero import tablero_bp

app.register_blueprint(auth_bp)
app.register_blueprint(tablero_bp)


@app.errorhandler(413)
def archivo_demasiado_grande(error):
    """Avisa con un mensaje claro cuando el envío supera el límite de 4 MB."""
    flash(
        "Los archivos superan el límite de 4 MB. Reduce su tamaño e intenta de nuevo.",
        "danger",
    )
    return redirect(url_for("tablero.index")), 303


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    # El depurador solo se activa si se pide explícitamente con FLASK_DEBUG=1
    debug = os.getenv("FLASK_DEBUG", "").lower() in ("1", "true", "yes")
    print(f"Iniciando App de Certificados en http://localhost:{port}")
    app.run(host="0.0.0.0", port=port, debug=debug)
