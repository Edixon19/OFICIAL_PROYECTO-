"""
database.py — Conexión a Supabase (PostgreSQL)
===============================================
⚠️  ESTE ARCHIVO CONTIENE CREDENCIALES.
    Agrégalo a .gitignore y NUNCA lo subas a GitHub.

    En Streamlit Cloud usa st.secrets en lugar de este archivo:
    Crea en el dashboard de Streamlit Cloud > Secrets:

        [supabase]
        url = "postgresql://postgres:TU_PASSWORD@db.wopthjsdceattleaeczt.supabase.co:5432/postgres"

Uso desde app.py:
    from database import get_connection, init_db, close_conn
"""

import os
import streamlit as st

# ─────────────────────────────────────────────
# IMPORTACIÓN DE PSYCOPG2
# ─────────────────────────────────────────────
try:
    import psycopg2
    import psycopg2.extras          # para DictCursor
    PSYCOPG2_OK = True
except ImportError:
    PSYCOPG2_OK = False

# ─────────────────────────────────────────────
# CADENA DE CONEXIÓN
# Prioridad:
#   1. st.secrets["supabase"]["url"]  → Streamlit Cloud
#   2. Variable de entorno DATABASE_URL → entorno local con .env
#   3. Cadena hardcodeada (solo desarrollo, reemplaza TU_PASSWORD)
# ─────────────────────────────────────────────

def _get_dsn() -> str:
    # 1. Streamlit Cloud secrets
    try:
        return st.secrets["supabase"]["url"]
    except Exception:
        pass

    # 2. Variable de entorno (útil con python-dotenv en local)
    env_url = os.getenv("DATABASE_URL")
    if env_url:
        return env_url

    # 3. Fallback hardcodeado — SOLO DESARROLLO LOCAL
    #    Reemplaza TU_PASSWORD por tu contraseña real de Supabase.
    return (
        "postgresql://postgres:utede2026sem2"
        "@db.wopthjsdceattleaeczt.supabase.co:5432/postgres"
    )


# ─────────────────────────────────────────────
# CONEXIÓN CACHEADA
# st.cache_resource mantiene UNA sola conexión
# por sesión del servidor, evitando abrir miles
# de conexiones a Supabase.
# ─────────────────────────────────────────────

@st.cache_resource
def _get_cached_connection():
    """
    Abre y cachea la conexión a Supabase (PostgreSQL).
    Si psycopg2 no está instalado retorna None.
    """
    if not PSYCOPG2_OK:
        return None
    try:
        conn = psycopg2.connect(
            _get_dsn(),
            connect_timeout=10,
            # Supabase requiere SSL; psycopg2 lo activa automáticamente
            # con sslmode='require' cuando la URL lo indica.
            # Si ves errores SSL descomenta la línea de abajo:
            # sslmode="require",
        )
        conn.autocommit = False          # manejamos commit manualmente
        return conn
    except Exception as e:
        # No mostramos st.error aquí para no romper el arranque
        print(f"[database.py] Error al conectar a Supabase: {e}")
        return None


# En tu archivo database.py
def get_connection():
    try:
        url = st.secrets["supabase"]["url"]
        return psycopg2.connect(url)
    except Exception as e:
        # Esto hará que el error aparezca en tu app de Streamlit
        st.error(f"EL ERROR ES: {e}")
        return None


def get_cursor(conn):
    """
    Retorna un DictCursor (las filas son accesibles como dict).
    Ejemplo:
        conn = get_connection()
        cur  = get_cursor(conn)
        cur.execute("SELECT * FROM tasks")
        rows = cur.fetchall()   # cada row es un dict
    """
    if conn is None:
        return None
    return conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)


def close_conn(conn) -> None:
    """Cierra la conexión de forma segura (úsalo al final de scripts)."""
    try:
        if conn:
            conn.close()
    except Exception:
        pass


# ─────────────────────────────────────────────
# INICIALIZACIÓN DE TABLAS
# ─────────────────────────────────────────────

def init_db() -> bool:
    """
    Crea las tablas necesarias si no existen en Supabase.
    Retorna True si todo salió bien.

    Diferencias con MySQL:
      · ENUM → VARCHAR con CHECK CONSTRAINT
      · AUTO_INCREMENT → SERIAL o GENERATED ALWAYS AS IDENTITY
      · JSON → JSONB  (más eficiente en PostgreSQL)
      · DATETIME → TIMESTAMPTZ
      · ON UPDATE CURRENT_TIMESTAMP no existe; se gestiona en app
    """
    conn = get_connection()
    if conn is None:
        return False

    ddl = [
        # ── Tareas ──────────────────────────────────────────────────
        """
        CREATE TABLE IF NOT EXISTS tasks (
            id          VARCHAR(36)  PRIMARY KEY,
            title       VARCHAR(255) NOT NULL,
            description TEXT,
            priority    VARCHAR(20)  DEFAULT 'Medium'
                        CHECK (priority IN ('High','Medium','Low')),
            category    VARCHAR(100),
            status      VARCHAR(30)  DEFAULT 'Pendiente'
                        CHECK (status IN ('Pendiente','Activa','Completada')),
            due_date    DATE,
            assignee    VARCHAR(255),
            tags        JSONB        DEFAULT '[]'::jsonb,
            created_at  TIMESTAMPTZ  DEFAULT NOW()
        )
        """,
        # ── Equipos ─────────────────────────────────────────────────
        """
        CREATE TABLE IF NOT EXISTS teams (
            id          VARCHAR(36)  PRIMARY KEY,
            name        VARCHAR(255) NOT NULL UNIQUE,
            description TEXT,
            created_at  TIMESTAMPTZ  DEFAULT NOW()
        )
        """,
        # ── Miembros de equipo ───────────────────────────────────────
        """
        CREATE TABLE IF NOT EXISTS team_members (
            id          VARCHAR(36)  PRIMARY KEY,
            team_id     VARCHAR(36)  NOT NULL
                        REFERENCES teams(id) ON DELETE CASCADE,
            member_name VARCHAR(255) NOT NULL,
            role        VARCHAR(30)  DEFAULT 'Miembro'
                        CHECK (role IN ('Líder','Miembro','Editor','Viewer')),
            joined_at   TIMESTAMPTZ  DEFAULT NOW(),
            UNIQUE (team_id, member_name)
        )
        """,
        # ── Log de actividad ────────────────────────────────────────
        """
        CREATE TABLE IF NOT EXISTS activity_log (
            id          VARCHAR(36)  PRIMARY KEY,
            user_name   VARCHAR(255),
            action      VARCHAR(100) NOT NULL,
            entity_type VARCHAR(50),
            entity_name VARCHAR(255),
            detail      TEXT,
            created_at  TIMESTAMPTZ  DEFAULT NOW()
        )
        """,
    ]

    cur = get_cursor(conn)
    if cur is None:
        return False

    try:
        for stmt in ddl:
            cur.execute(stmt)
        conn.commit()
        cur.close()
        return True
    except Exception as e:
        conn.rollback()
        print(f"[database.py] Error al crear tablas: {e}")
        return False

# ─────────────────────────────────────────────
# DIAGNÓSTICO RÁPIDO (ejecutar directamente)
# ─────────────────────────────────────────────

if __name__ == "__main__":
    print("Probando conexión a Supabase…")
    if not PSYCOPG2_OK:
        print("❌  psycopg2 no instalado. Ejecuta: pip install psycopg2-binary")
    else:
        c = psycopg2.connect(_get_dsn())
        cur = c.cursor()
        cur.execute("SELECT version()")
        print("✅  Conectado:", cur.fetchone()[0])
        c.close()