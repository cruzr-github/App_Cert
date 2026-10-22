"""
api/index.py
Punto de entrada para Vercel.
Vercel ejecuta este archivo como función serverless y busca la variable `app`.
Reutiliza la aplicación Flask de app.py, sin duplicar rutas ni lógica.
"""

import sys
from pathlib import Path

# En Vercel el proyecto se copia a otra carpeta; agregamos la raíz al path
# para que se puedan importar app.py, controllers/, models/ y services/.
RAIZ_PROYECTO = Path(__file__).resolve().parent.parent
if str(RAIZ_PROYECTO) not in sys.path:
    sys.path.insert(0, str(RAIZ_PROYECTO))

from app import app  # noqa: E402
