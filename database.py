import os
import streamlit as st

# ─────────────────────────────────────────────
# IMPORTACIÓN DE PSYCOPG2
# ─────────────────────────────────────────────
try:
    import psycopg2
    import psycopg2.extras
    PSYCOPG2_OK = True
except ImportError:
    PSYCOPG2_OK = False

# ─────────────────────────────────────────────
# GESTIÓN DE LA URL (Pooler)
# ─────────────────────────────────────────────
def _get_dsn() -> str:
    # Prioridad 1: Streamlit Secrets
    try:
        return st.secrets["supabase"]["url"]
    except Exception:
        pass

    # Prioridad 2: Variable de entorno
    env_url = os.getenv("DATABASE_URL")
    if env_url:
        return env_url

    # Prioridad 3: Fallback (Copia aquí tu URL completa con puerto 6543)
    return "postgresql://postgres.wopthjsdceattleaeczt:utede2026sem2@aws-1-us-east-2.pooler.supabase.com:6543/postgres"

# ─────────────────────────────────────────────
# CONEXIÓN CACHEADA (Optimización Pooler)
# ─────────────────────────────────────────────

@st.cache_resource(ttl=600) # <--- EL SECRETO: Refresca la conexión cada 10 min
def get_connection():
    """
    Abre y mantiene la conexión al Pooler de Supabase.
    """
    if not PSYCOPG2_OK:
        return None
    try:
        conn = psycopg2.connect(
            _get_dsn(),
            connect_timeout=10,
            sslmode="require" # Obligatorio para Pooler en muchos casos
        )
        conn.autocommit = False
        return conn
    except Exception as e:
        print(f"[database.py] Error al conectar al Pooler: {e}")
        return None

def get_cursor(conn):
    """Retorna un DictCursor para trabajar con diccionarios."""
    if conn is None:
        return None
    # Si la conexión está cerrada o rota, esto fallará y devolverá None
    try:
        return conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    except Exception:
        return None

def close_conn(conn) -> None:
    """Cierra la conexión."""
    try:
        if conn:
            conn.close()
    except Exception:
        pass

# ─────────────────────────────────────────────
# INICIALIZACIÓN (Mantener igual)
# ─────────────────────────────────────────────
def init_db() -> bool:
    conn = get_connection()
    if conn is None:
        return False

    # ... (Tu lista de ddl permanece igual) ...
    # [Mantén tu código DDL aquí tal cual lo tenías]
    return True