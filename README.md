# App_Cert

Aplicación Flask para calcular certificados académicos a partir de dos Excel:
maestro de estudiantes y registro de evaluaciones.

## Desarrollo local

```bash
uv sync
uv run python app.py
```

La app queda en `http://localhost:5000`.

Credenciales y secretos se leen del archivo `.env` (no se sube al repositorio).
Usa `.env.ejemplo` como plantilla.

## Pruebas

```bash
uv run pytest
```

## Despliegue en Vercel

Vercel detecta automáticamente la aplicación Flask en `app.py`. No se necesitan
reescrituras de rutas ni un archivo `api/index.py`. `vercel.json` solo configura
la duración máxima y los archivos que deben incluirse (plantillas y `insumos/`).

En **Project Settings → Environment Variables** configura:

- `FLASK_SECRET_KEY`
- `ADMIN_CORREO` y `ADMIN_CLAVE`
- `USUARIO_CORREO` y `USUARIO_CLAVE`
- `DATABASE_URL` (opcional; solo lo usa el script `cargar_datos.py`)

No subas `.env`: está protegido por `.gitignore`.
