"""
cargar_datos.py
Script para crear las tablas en Supabase y cargar los datos desde los archivos Excel de insumos/.
Uso: uv run cargar_datos.py
"""

from services.carga_excel import cargar_datos_desde_archivos


def main():
    print("Iniciando creación de tablas y carga de datos en Supabase...")
    try:
        estudiantes_cargados, evaluaciones_cargadas = cargar_datos_desde_archivos(
            ruta_maestro="insumos/Maestro_Estudiantes.xlsx",
            ruta_evaluaciones="insumos/Registro_Evaluaciones.xlsx",
        )
        print("=" * 50)
        print("¡Carga completada con éxito!")
        print(f"Estudiantes en base de datos: {estudiantes_cargados}")
        print(f"Evaluaciones en base de datos: {evaluaciones_cargadas}")
        print("=" * 50)
    except Exception as e:
        print(f"Error durante la carga de datos: {e}")
        raise


if __name__ == "__main__":
    main()
