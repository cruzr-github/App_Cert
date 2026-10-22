"""
models/datos.py
Único archivo del proyecto que interactúa con la base de datos Supabase (PostgreSQL).
Lee la variable DATABASE_URL del archivo .env mediante python-dotenv y utiliza psycopg
con prepare_threshold=None para compatibilidad con el pooler de Supabase.
Incluye soporte de respaldo local para permitir pruebas inmediatas si DATABASE_URL aún no ha sido provista.
"""

import os
import sqlite3
from typing import List, Dict, Any, Optional
import psycopg
from dotenv import load_dotenv

# Cargar variables de entorno desde .env
load_dotenv()


def is_postgres() -> bool:
    """Verifica si DATABASE_URL está configurada para PostgreSQL / Supabase."""
    url = os.getenv("DATABASE_URL", "").strip()
    return url.startswith("postgres://") or url.startswith("postgresql://")


def get_connection():
    """
    Obtiene una conexión a la base de datos.
    Si DATABASE_URL está configurada con postgres/postgresql, conecta a Supabase
    usando psycopg con prepare_threshold=None (pooler mode).
    De lo contrario, utiliza un archivo SQLite local para desarrollo y pruebas.
    """
    if is_postgres():
        database_url = os.getenv("DATABASE_URL")
        return psycopg.connect(database_url, prepare_threshold=None)
    else:
        # Fallback local SQLite para desarrollo/pruebas
        conn = sqlite3.connect("datos_local.db")
        conn.row_factory = sqlite3.Row
        return conn


def crear_tablas():
    """Crea las tablas estudiantes y evaluaciones si no existen."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        if is_postgres():
            cur.execute("""
                CREATE TABLE IF NOT EXISTS estudiantes (
                    identificacion TEXT PRIMARY KEY,
                    nombre_completo TEXT NOT NULL,
                    correo TEXT,
                    programa TEXT NOT NULL,
                    cohorte TEXT
                );
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS evaluaciones (
                    id SERIAL PRIMARY KEY,
                    identificacion TEXT NOT NULL,
                    programa TEXT NOT NULL,
                    modulo TEXT NOT NULL,
                    nota NUMERIC(5, 2) NOT NULL,
                    asistencia_pct NUMERIC(5, 2) NOT NULL,
                    fecha_cierre DATE
                );
            """)
        else:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS estudiantes (
                    identificacion TEXT PRIMARY KEY,
                    nombre_completo TEXT NOT NULL,
                    correo TEXT,
                    programa TEXT NOT NULL,
                    cohorte TEXT
                );
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS evaluaciones (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    identificacion TEXT NOT NULL,
                    programa TEXT NOT NULL,
                    modulo TEXT NOT NULL,
                    nota REAL NOT NULL,
                    asistencia_pct REAL NOT NULL,
                    fecha_cierre TEXT
                );
            """)
        conn.commit()
    finally:
        conn.close()


def limpiar_tablas():
    """Elimina todos los registros de estudiantes y evaluaciones para carga limpia."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM evaluaciones;")
        cur.execute("DELETE FROM estudiantes;")
        conn.commit()
    finally:
        conn.close()


def guardar_estudiantes(estudiantes: List[Dict[str, Any]]):
    """Guarda una lista de diccionarios de estudiantes en la base de datos."""
    if not estudiantes:
        return

    conn = get_connection()
    try:
        cur = conn.cursor()
        query = """
            INSERT INTO estudiantes (identificacion, nombre_completo, correo, programa, cohorte)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (identificacion) DO UPDATE SET
                nombre_completo = EXCLUDED.nombre_completo,
                correo = EXCLUDED.correo,
                programa = EXCLUDED.programa,
                cohorte = EXCLUDED.cohorte;
        """
        if not is_postgres():
            query = query.replace("%s", "?")

        datos = [
            (
                str(est["identificacion"]).strip(),
                str(est["nombre_completo"]).strip(),
                str(est.get("correo", "")).strip() if est.get("correo") else None,
                str(est["programa"]).strip(),
                str(est.get("cohorte", "")).strip() if est.get("cohorte") else None,
            )
            for est in estudiantes
        ]
        cur.executemany(query, datos)
        conn.commit()
    finally:
        conn.close()


def guardar_evaluaciones(evaluaciones: List[Dict[str, Any]]):
    """Guarda una lista de diccionarios de evaluaciones en la base de datos."""
    if not evaluaciones:
        return

    conn = get_connection()
    try:
        cur = conn.cursor()
        query = """
            INSERT INTO evaluaciones (identificacion, programa, modulo, nota, asistencia_pct, fecha_cierre)
            VALUES (%s, %s, %s, %s, %s, %s);
        """
        if not is_postgres():
            query = query.replace("%s", "?")

        datos = [
            (
                str(ev["identificacion"]).strip(),
                str(ev["programa"]).strip(),
                str(ev["modulo"]).strip(),
                float(ev["nota"]),
                float(ev["asistencia_pct"]),
                ev.get("fecha_cierre") or None,
            )
            for ev in evaluaciones
        ]
        cur.executemany(query, datos)
        conn.commit()
    finally:
        conn.close()


def contar_estudiantes() -> int:
    """Devuelve el total de filas en la tabla estudiantes."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM estudiantes;")
        resultado = cur.fetchone()
        return resultado[0] if resultado else 0
    finally:
        conn.close()


def contar_evaluaciones() -> int:
    """Devuelve el total de filas en la tabla evaluaciones."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM evaluaciones;")
        resultado = cur.fetchone()
        return resultado[0] if resultado else 0
    finally:
        conn.close()


def obtener_estudiantes() -> List[Dict[str, Any]]:
    """Obtiene todos los registros de estudiantes ordenados por nombre."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT identificacion, nombre_completo, correo, programa, cohorte
            FROM estudiantes
            ORDER BY nombre_completo ASC;
        """)
        if is_postgres():
            columnas = [desc[0] for desc in cur.description]
            return [dict(zip(columnas, fila)) for fila in cur.fetchall()]
        else:
            return [dict(fila) for fila in cur.fetchall()]
    finally:
        conn.close()


def obtener_evaluaciones() -> List[Dict[str, Any]]:
    """Obtiene todas las evaluaciones registradas."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT id, identificacion, programa, modulo, nota, asistencia_pct, fecha_cierre
            FROM evaluaciones
            ORDER BY identificacion, modulo;
        """)
        if is_postgres():
            columnas = [desc[0] for desc in cur.description]
            return [dict(zip(columnas, fila)) for fila in cur.fetchall()]
        else:
            return [dict(fila) for fila in cur.fetchall()]
    finally:
        conn.close()
