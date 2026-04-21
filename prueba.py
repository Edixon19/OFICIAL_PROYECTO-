"""
GestorPro - Gestor de Tareas con Streamlit
==========================================
Versión 1.0.0 

Autores: GestorPro, equipo del segundo semestre UTEDÉ
"""
#conectar base de datos con supabase en lugar de con docker

import streamlit as st
import json
import uuid
import os
from datetime import datetime, date
from typing import Optional
import mysql.connector
from mysql.connector import Error as MySQLError

from dotenv import load_dotenv
load_dotenv()

# ─────────────────────────────────────────────
# CONFIGURACIÓN INICIAL DE STREAMLIT
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="GestorPro",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────
# CONSTANTES
# ─────────────────────────────────────────────
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", 3306)),
    "database": os.getenv("DB_NAME", "testdb"),
    "user": os.getenv("DB_USER", "testuser"),
    "password": os.getenv("DB_PASSWORD", "testpass"),
}

PRIORITIES = ["High", "Medium", "Low"]
CATEGORIES = ["Trabajo", "Personal", "Compras", "Diseño", "Desarrollo", "Otro"]
STATUS_OPTIONS = ["Pendiente", "Activa", "Completada"]
TEAM_ROLES = ["Líder", "Miembro", "Editor", "Viewer"]

PRIORITY_COLORS = {
    "High": "#ef4444",
    "Medium": "#f59e0b",
    "Low": "#22c55e",
}

CATEGORY_COLORS = {
    "Trabajo": "#3b82f6",
    "Personal": "#8b5cf6",
    "Compras": "#f59e0b",
    "Diseño": "#ec4899",
    "Desarrollo": "#06b6d4",
    "Otro": "#6b7280",
}

THEMES = {
    "light": {
        "--bg-main": "#f8fafc",
        "--bg-card": "#ffffff",
        "--bg-sidebar": "#1a1a2e",
        "--text-primary": "#0f172a",
        "--text-secondary": "#64748b",
        "--text-sidebar": "#e2e8f0",
        "--border-color": "#e2e8f0",
        "--accent-primary": "#e55a2b",
        "--accent-secondary": "#0d9488",
        "--accent-gradient": "linear-gradient(135deg, #e55a2b, #0d9488)",
        "--hover-bg": "#f1f5f9",
        "--input-bg": "#f8fafc",
        "--shadow": "0 2px 8px rgba(0,0,0,0.08)",
        "--shadow-hover": "0 4px 16px rgba(0,0,0,0.12)",
        "--badge-bg": "#f1f5f9",
        "--completed-text": "#94a3b8",
        "--stats-bg": "#f8fafc",
    },
    "dark": {
        "--bg-main": "#0f172a",
        "--bg-card": "#1e293b",
        "--bg-sidebar": "#020617",
        "--text-primary": "#f1f5f9",
        "--text-secondary": "#94a3b8",
        "--text-sidebar": "#e2e8f0",
        "--border-color": "#334155",
        "--accent-primary": "#e55a2b",
        "--accent-secondary": "#0d9488",
        "--accent-gradient": "linear-gradient(135deg, #e55a2b, #0d9488)",
        "--hover-bg": "#334155",
        "--input-bg": "#1e293b",
        "--shadow": "0 2px 8px rgba(0,0,0,0.3)",
        "--shadow-hover": "0 4px 16px rgba(0,0,0,0.5)",
        "--badge-bg": "#334155",
        "--completed-text": "#475569",
        "--stats-bg": "#1e293b",
    },
}


# ─────────────────────────────────────────────
# BASE DE DATOS: CONEXIÓN Y SETUP
# ─────────────────────────────────────────────

@st.cache_resource
def get_db_connection():
    """
    Retorna una conexión persistente a MySQL.
    Se cachea con st.cache_resource para reutilizarla entre reruns.
    """
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except MySQLError as e:
        st.error(f"❌ Error de conexión a MySQL: {e}")
        return None


def get_cursor():
    """Obtiene cursor, reconectando si la conexión fue perdida."""
    conn = get_db_connection()
    if conn is None:
        return None, None
    try:
        if not conn.is_connected():
            conn.reconnect(attempts=3, delay=1)
        cursor = conn.cursor(dictionary=True)
        return conn, cursor
    except MySQLError as e:
        st.error(f"Error de cursor: {e}")
        return None, None


def init_db() -> bool:
    """
    Crea las tablas necesarias si no existen.
    Retorna True si la inicialización fue exitosa.
    """
    conn, cursor = get_cursor()
    if cursor is None:
        return False

    ddl_statements = [
        """
        CREATE TABLE IF NOT EXISTS tasks (
            id VARCHAR(36) PRIMARY KEY,
            title VARCHAR(255) NOT NULL,
            description TEXT,
            priority ENUM('High','Medium','Low') DEFAULT 'Medium',
            category VARCHAR(100),
            status ENUM('Pendiente','Activa','Completada') DEFAULT 'Pendiente',
            due_date DATE,
            assignee VARCHAR(255),
            tags JSON,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS teams (
            id VARCHAR(36) PRIMARY KEY,
            name VARCHAR(255) NOT NULL UNIQUE,
            description TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS team_members (
            id VARCHAR(36) PRIMARY KEY,
            team_id VARCHAR(36) NOT NULL,
            member_name VARCHAR(255) NOT NULL,
            role ENUM('Líder','Miembro','Editor','Viewer') DEFAULT 'Miembro',
            joined_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (team_id) REFERENCES teams(id) ON DELETE CASCADE,
            UNIQUE KEY unique_member_team (team_id, member_name)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS activity_log (
            id VARCHAR(36) PRIMARY KEY,
            user_name VARCHAR(255),
            action VARCHAR(100) NOT NULL,
            entity_type VARCHAR(50),
            entity_name VARCHAR(255),
            detail TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """,
    ]

    try:
        for stmt in ddl_statements:
            cursor.execute(stmt)
        conn.commit()
        return True
    except MySQLError as e:
        st.error(f"Error al inicializar BD: {e}")
        return False
    finally:
        cursor.close()


# ─────────────────────────────────────────────
# CRUD: TAREAS
# ─────────────────────────────────────────────

def db_load_tasks() -> list[dict]:
    """Carga todas las tareas desde MySQL."""
    conn, cursor = get_cursor()
    if cursor is None:
        return _get_sample_tasks()
    try:
        cursor.execute("SELECT * FROM tasks ORDER BY FIELD(priority,'High','Medium','Low'), created_at DESC")
        rows = cursor.fetchall()
        tasks = []
        for row in rows:
            task = dict(row)
            # Deserializar tags JSON
            if isinstance(task.get("tags"), str):
                try:
                    task["tags"] = json.loads(task["tags"])
                except Exception:
                    task["tags"] = []
            elif task.get("tags") is None:
                task["tags"] = []
            # Convertir date a isoformat string
            if isinstance(task.get("due_date"), date):
                task["due_date"] = task["due_date"].isoformat()
            if isinstance(task.get("created_at"), datetime):
                task["created_at"] = task["created_at"].isoformat()
            tasks.append(task)
        return tasks
    except MySQLError as e:
        st.error(f"Error al cargar tareas: {e}")
        return []
    finally:
        cursor.close()


def db_add_task(title, description, priority, category, status, due_date, assignee, tags) -> bool:
    """Inserta una nueva tarea en MySQL y registra actividad."""
    conn, cursor = get_cursor()
    if cursor is None:
        return False
    try:
        task_id = str(uuid.uuid4())
        cursor.execute(
            """INSERT INTO tasks (id, title, description, priority, category, status,
               due_date, assignee, tags, created_at)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            (
                task_id, title.strip(), description.strip(), priority, category, status,
                due_date.isoformat() if due_date else date.today().isoformat(),
                assignee.strip(), json.dumps(tags, ensure_ascii=False),
                datetime.now().isoformat(),
            ),
        )
        conn.commit()
        _log_activity(
            user_name=assignee.strip() or "Sistema",
            action="creó la tarea",
            entity_type="tarea",
            entity_name=title.strip(),
        )
        return True
    except MySQLError as e:
        st.error(f"Error al crear tarea: {e}")
        return False
    finally:
        cursor.close()


def db_update_task(task_id: str, **kwargs) -> bool:
    """Actualiza campos de una tarea en MySQL."""
    conn, cursor = get_cursor()
    if cursor is None:
        return False
    try:
        # Serializar tags si vienen en kwargs
        if "tags" in kwargs:
            kwargs["tags"] = json.dumps(kwargs["tags"], ensure_ascii=False)

        set_clause = ", ".join(f"{k} = %s" for k in kwargs)
        values = list(kwargs.values()) + [task_id]
        cursor.execute(f"UPDATE tasks SET {set_clause} WHERE id = %s", values)
        conn.commit()

        title = kwargs.get("title", task_id)
        _log_activity(
            user_name="Usuario",
            action="actualizó la tarea",
            entity_type="tarea",
            entity_name=title,
        )
        return True
    except MySQLError as e:
        st.error(f"Error al actualizar tarea: {e}")
        return False
    finally:
        cursor.close()


def db_delete_task(task_id: str, task_title: str = "") -> bool:
    """Elimina una tarea de MySQL."""
    conn, cursor = get_cursor()
    if cursor is None:
        return False
    try:
        cursor.execute("DELETE FROM tasks WHERE id = %s", (task_id,))
        conn.commit()
        _log_activity(
            user_name="Usuario",
            action="eliminó la tarea",
            entity_type="tarea",
            entity_name=task_title or task_id,
        )
        return True
    except MySQLError as e:
        st.error(f"Error al eliminar tarea: {e}")
        return False
    finally:
        cursor.close()


def db_toggle_task_status(task_id: str, current_status: str, title: str = "") -> bool:
    """Alterna el estado de la tarea entre Activa y Completada."""
    new_status = "Activa" if current_status == "Completada" else "Completada"
    action = "completó la tarea" if new_status == "Completada" else "reactivó la tarea"
    conn, cursor = get_cursor()
    if cursor is None:
        return False
    try:
        cursor.execute("UPDATE tasks SET status = %s WHERE id = %s", (new_status, task_id))
        conn.commit()
        _log_activity(user_name="Usuario", action=action, entity_type="tarea", entity_name=title)
        return True
    except MySQLError as e:
        st.error(f"Error: {e}")
        return False
    finally:
        cursor.close()


# ─────────────────────────────────────────────
# CRUD: EQUIPOS
# ─────────────────────────────────────────────

def db_load_teams() -> list[dict]:
    """Carga todos los equipos con sus miembros."""
    conn, cursor = get_cursor()
    if cursor is None:
        return []
    try:
        cursor.execute("SELECT * FROM teams ORDER BY created_at DESC")
        teams = cursor.fetchall()
        result = []
        for team in teams:
            cursor.execute(
                "SELECT * FROM team_members WHERE team_id = %s ORDER BY role",
                (team["id"],)
            )
            members = cursor.fetchall()
            t = dict(team)
            t["members"] = [dict(m) for m in members]
            if isinstance(t.get("created_at"), datetime):
                t["created_at"] = t["created_at"].isoformat()
            result.append(t)
        return result
    except MySQLError as e:
        st.error(f"Error al cargar equipos: {e}")
        return []
    finally:
        cursor.close()


def db_create_team(name: str, description: str, leader_name: str) -> bool:
    """Crea un nuevo equipo y agrega al líder como primer miembro."""
    conn, cursor = get_cursor()
    if cursor is None:
        return False
    try:
        team_id = str(uuid.uuid4())
        cursor.execute(
            "INSERT INTO teams (id, name, description) VALUES (%s, %s, %s)",
            (team_id, name.strip(), description.strip()),
        )
        # Agregar líder automáticamente
        if leader_name.strip():
            cursor.execute(
                "INSERT INTO team_members (id, team_id, member_name, role) VALUES (%s, %s, %s, %s)",
                (str(uuid.uuid4()), team_id, leader_name.strip(), "Líder"),
            )
        conn.commit()
        _log_activity(
            user_name=leader_name or "Sistema",
            action="creó el equipo",
            entity_type="equipo",
            entity_name=name.strip(),
        )
        return True
    except MySQLError as e:
        st.error(f"Error al crear equipo: {e}")
        return False
    finally:
        cursor.close()


def db_add_member(team_id: str, member_name: str, role: str, team_name: str = "") -> bool:
    """Agrega un miembro a un equipo."""
    conn, cursor = get_cursor()
    if cursor is None:
        return False
    try:
        cursor.execute(
            "INSERT INTO team_members (id, team_id, member_name, role) VALUES (%s, %s, %s, %s)",
            (str(uuid.uuid4()), team_id, member_name.strip(), role),
        )
        conn.commit()
        _log_activity(
            user_name="Usuario",
            action=f"agregó a {member_name} al equipo",
            entity_type="equipo",
            entity_name=team_name,
        )
        return True
    except MySQLError as e:
        if "Duplicate" in str(e):
            st.warning(f"'{member_name}' ya es miembro de este equipo.")
        else:
            st.error(f"Error al agregar miembro: {e}")
        return False
    finally:
        cursor.close()


def db_update_member_role(member_id: str, new_role: str, member_name: str = "") -> bool:
    """Cambia el rol de un miembro del equipo."""
    conn, cursor = get_cursor()
    if cursor is None:
        return False
    try:
        cursor.execute("UPDATE team_members SET role = %s WHERE id = %s", (new_role, member_id))
        conn.commit()
        _log_activity(
            user_name="Líder",
            action=f"cambió el rol de {member_name} a {new_role}",
            entity_type="equipo",
            entity_name="",
        )
        return True
    except MySQLError as e:
        st.error(f"Error: {e}")
        return False
    finally:
        cursor.close()


def db_move_member(member_id: str, new_team_id: str, member_name: str = "", new_team_name: str = "") -> bool:
    """Mueve un miembro a otro equipo."""
    conn, cursor = get_cursor()
    if cursor is None:
        return False
    try:
        cursor.execute(
            "UPDATE team_members SET team_id = %s, role = 'Miembro' WHERE id = %s",
            (new_team_id, member_id),
        )
        conn.commit()
        _log_activity(
            user_name="Líder",
            action=f"movió a {member_name} al equipo",
            entity_type="equipo",
            entity_name=new_team_name,
        )
        return True
    except MySQLError as e:
        if "Duplicate" in str(e):
            st.warning("El miembro ya pertenece a ese equipo.")
        else:
            st.error(f"Error: {e}")
        return False
    finally:
        cursor.close()


def db_remove_member(member_id: str, member_name: str = "", team_name: str = "") -> bool:
    """Elimina un miembro de un equipo."""
    conn, cursor = get_cursor()
    if cursor is None:
        return False
    try:
        cursor.execute("DELETE FROM team_members WHERE id = %s", (member_id,))
        conn.commit()
        _log_activity(
            user_name="Líder",
            action=f"removió a {member_name} del equipo",
            entity_type="equipo",
            entity_name=team_name,
        )
        return True
    except MySQLError as e:
        st.error(f"Error: {e}")
        return False
    finally:
        cursor.close()


def db_delete_team(team_id: str, team_name: str = "") -> bool:
    """Elimina un equipo y todos sus miembros (CASCADE)."""
    conn, cursor = get_cursor()
    if cursor is None:
        return False
    try:
        cursor.execute("DELETE FROM teams WHERE id = %s", (team_id,))
        conn.commit()
        _log_activity(
            user_name="Usuario",
            action="eliminó el equipo",
            entity_type="equipo",
            entity_name=team_name,
        )
        return True
    except MySQLError as e:
        st.error(f"Error: {e}")
        return False
    finally:
        cursor.close()


# ─────────────────────────────────────────────
# ACTIVIDAD
# ─────────────────────────────────────────────

def _log_activity(user_name: str, action: str, entity_type: str = "", entity_name: str = "", detail: str = ""):
    """Registra una entrada en el log de actividad."""
    conn, cursor = get_cursor()
    if cursor is None:
        return
    try:
        cursor.execute(
            """INSERT INTO activity_log (id, user_name, action, entity_type, entity_name, detail)
               VALUES (%s, %s, %s, %s, %s, %s)""",
            (str(uuid.uuid4()), user_name, action, entity_type, entity_name, detail),
        )
        conn.commit()
    except MySQLError:
        pass  # El log nunca debe romper el flujo principal
    finally:
        cursor.close()


def db_load_activity(limit: int = 30) -> list[dict]:
    """Carga el historial de actividad real desde MySQL."""
    conn, cursor = get_cursor()
    if cursor is None:
        return []
    try:
        cursor.execute(
            "SELECT * FROM activity_log ORDER BY created_at DESC LIMIT %s",
            (limit,),
        )
        rows = cursor.fetchall()
        result = []
        for row in rows:
            r = dict(row)
            if isinstance(r.get("created_at"), datetime):
                r["created_at"] = r["created_at"].isoformat()
            result.append(r)
        return result
    except MySQLError as e:
        st.error(f"Error al cargar actividad: {e}")
        return []
    finally:
        cursor.close()


def _time_ago(created_at_str: str) -> str:
    """Convierte un datetime ISO a texto relativo (ej: 'Hace 5 min')."""
    try:
        dt = datetime.fromisoformat(created_at_str)
        diff = datetime.now() - dt
        seconds = int(diff.total_seconds())
        if seconds < 60:
            return f"Hace {seconds} seg"
        elif seconds < 3600:
            return f"Hace {seconds // 60} min"
        elif seconds < 86400:
            return f"Hace {seconds // 3600} h"
        else:
            return f"Hace {seconds // 86400} días"
    except Exception:
        return "Recientemente"


# ─────────────────────────────────────────────
# DATOS DE EJEMPLO
# ─────────────────────────────────────────────

def _get_sample_tasks() -> list[dict]:
    today = date.today().isoformat()
    return [
        {
            "id": str(uuid.uuid4()), "title": "Diseñar interfaz de usuario",
            "description": "Crear mockups para la nueva aplicación", "priority": "High",
            "category": "Diseño", "status": "Activa", "due_date": today,
            "assignee": "Ana García", "tags": ["diseño", "UI/UX"],
            "created_at": datetime.now().isoformat(),
        },
        {
            "id": str(uuid.uuid4()), "title": "Revisar documentación del proyecto",
            "description": "Actualizar la documentación técnica", "priority": "Medium",
            "category": "Trabajo", "status": "Activa", "due_date": today,
            "assignee": "", "tags": ["documentación"],
            "created_at": datetime.now().isoformat(),
        },
        {
            "id": str(uuid.uuid4()), "title": "Comprar suministros de oficina",
            "description": "Papel, bolígrafos y carpetas", "priority": "Low",
            "category": "Compras", "status": "Pendiente", "due_date": today,
            "assignee": "", "tags": ["compras"],
            "created_at": datetime.now().isoformat(),
        },
    ]


def seed_sample_data():
    """Inserta datos de ejemplo si la tabla de tareas está vacía."""
    conn, cursor = get_cursor()
    if cursor is None:
        return
    try:
        cursor.execute("SELECT COUNT(*) as cnt FROM tasks")
        row = cursor.fetchone()
        if row and row["cnt"] == 0:
            for t in _get_sample_tasks():
                cursor.execute(
                    """INSERT INTO tasks (id, title, description, priority, category, status,
                       due_date, assignee, tags, created_at) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (
                        t["id"], t["title"], t["description"], t["priority"],
                        t["category"], t["status"], t["due_date"], t["assignee"],
                        json.dumps(t["tags"]), t["created_at"],
                    ),
                )
            conn.commit()
    except MySQLError:
        pass
    finally:
        cursor.close()


# ─────────────────────────────────────────────
# INICIALIZACIÓN DE SESSION STATE
# ─────────────────────────────────────────────

def init_session_state() -> None:
    defaults = {
        "tasks": [],
        "teams": [],
        "dark_mode": False,
        "active_page": "Dashboard",
        "filter_status": "Todas",
        "filter_category": "Todas",
        "show_new_task_form": False,
        "show_new_team_form": False,
        "editing_task_id": None,
        "confirm_delete_id": None,
        "confirm_delete_team_id": None,
        "search_query": "",
        "db_ok": False,
        "managing_team_id": None,
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val

    if not st.session_state.db_ok:
        ok = init_db()
        st.session_state.db_ok = ok
        if ok:
            seed_sample_data()

    # Cargar datos frescos en cada rerun
    st.session_state.tasks = db_load_tasks()
    st.session_state.teams = db_load_teams()


# ─────────────────────────────────────────────
# CSS DINÁMICO
# ─────────────────────────────────────────────

def inject_css() -> None:
    theme = THEMES["dark"] if st.session_state.dark_mode else THEMES["light"]
    css_vars = "\n".join([f"    {k}: {v};" for k, v in theme.items()])

    css = f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Sora:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

    :root {{
{css_vars}
    }}

    .stApp {{
        background-color: var(--bg-main) !important;
        font-family: 'Sora', sans-serif !important;
    }}

    /* Ocultar elementos nativos de Streamlit */
    #MainMenu, footer, header {{ visibility: hidden; }}
    .stDeployButton {{ display: none; }}

    /* ── CORRECCIÓN: Sidebar toggle siempre visible ── */
    [data-testid="collapsedControl"] {{
        display: flex !important;
        visibility: visible !important;
        opacity: 1 !important;
        background: var(--accent-primary) !important;
        border-radius: 0 8px 8px 0 !important;
        width: 28px !important;
        height: 48px !important;
        align-items: center !important;
        justify-content: center !important;
        position: fixed !important;
        left: 0 !important;
        top: 50% !important;
        transform: translateY(-50%) !important;
        z-index: 9999 !important;
        cursor: pointer !important;
        box-shadow: 2px 0 8px rgba(0,0,0,0.2) !important;
    }}

    [data-testid="collapsedControl"]:hover {{
        background: #c94d22 !important;
        width: 34px !important;
    }}

    [data-testid="collapsedControl"] svg {{
        color: white !important;
        fill: white !important;
    }}

    section[data-testid="stSidebar"] {{
        background: var(--bg-sidebar) !important;
        border-right: 1px solid rgba(255,255,255,0.06);
    }}

    section[data-testid="stSidebar"] * {{
        color: var(--text-sidebar) !important;
    }}

    .main .block-container {{
        padding: 1.5rem 2rem !important;
        max-width: 100% !important;
        background: var(--bg-main);
    }}

    h1, h2, h3 {{
        font-family: 'Sora', sans-serif !important;
        color: var(--text-primary) !important;
        font-weight: 700 !important;
    }}

    p, span, div, label {{ color: var(--text-primary); }}

    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea,
    .stSelectbox > div > div > div {{
        background: var(--input-bg) !important;
        border: 1.5px solid var(--border-color) !important;
        border-radius: 10px !important;
        color: var(--text-primary) !important;
        font-family: 'Sora', sans-serif !important;
        padding: 0.6rem 1rem !important;
    }}

    .stButton > button {{
        background: var(--accent-gradient) !important;
        color: white !important;
        border: none !important;
        border-radius: 10px !important;
        font-family: 'Sora', sans-serif !important;
        font-weight: 600 !important;
        font-size: 0.9rem !important;
        padding: 0.55rem 1.4rem !important;
        cursor: pointer !important;
        transition: opacity 0.2s ease, transform 0.15s ease !important;
    }}

    .stButton > button:hover {{
        opacity: 0.9 !important;
        transform: translateY(-1px) !important;
        box-shadow: 0 4px 14px rgba(229, 90, 43, 0.35) !important;
    }}

    .stCheckbox > label {{
        color: var(--text-primary) !important;
        font-family: 'Sora', sans-serif !important;
        font-size: 0.9rem !important;
    }}

    .stToggle > label span {{ color: var(--text-sidebar) !important; }}

    .stDateInput > div > div > input {{
        background: var(--input-bg) !important;
        border: 1.5px solid var(--border-color) !important;
        border-radius: 10px !important;
        color: var(--text-primary) !important;
    }}

    .stat-card {{
        background: var(--bg-card);
        border-radius: 14px;
        padding: 1.25rem 1.5rem;
        border: 1px solid var(--border-color);
        box-shadow: var(--shadow);
        transition: box-shadow 0.2s ease, transform 0.2s ease;
        margin-bottom: 1rem;
    }}
    .stat-card:hover {{ box-shadow: var(--shadow-hover); transform: translateY(-2px); }}
    .stat-card .stat-value {{
        font-size: 2rem; font-weight: 700; color: var(--text-primary);
        line-height: 1.1; font-family: 'Sora', sans-serif;
    }}
    .stat-card .stat-label {{
        font-size: 0.82rem; color: var(--text-secondary);
        margin-top: 0.25rem; font-family: 'Sora', sans-serif;
    }}
    .stat-card .stat-delta {{ font-size: 0.78rem; font-weight: 600; margin-top: 0.5rem; }}
    .stat-card .stat-delta.positive {{ color: #22c55e; }}
    .stat-card .stat-delta.negative {{ color: #ef4444; }}
    .stat-icon {{
        width: 42px; height: 42px; border-radius: 10px;
        display: flex; align-items: center; justify-content: center;
        font-size: 1.3rem; margin-bottom: 0.75rem;
    }}

    .task-card {{
        background: var(--bg-card);
        border-radius: 14px;
        padding: 1.1rem 1.4rem;
        border: 1px solid var(--border-color);
        box-shadow: var(--shadow);
        margin-bottom: 0.7rem;
        transition: all 0.2s ease;
    }}
    .task-card:hover {{ box-shadow: var(--shadow-hover); border-color: rgba(229,90,43,0.3); }}
    .task-card.completed {{ opacity: 0.65; }}
    .task-card .task-title {{
        font-size: 0.98rem; font-weight: 600; color: var(--text-primary);
        font-family: 'Sora', sans-serif; margin-bottom: 0.2rem;
    }}
    .task-card.completed .task-title {{ text-decoration: line-through; color: var(--completed-text); }}
    .task-card .task-desc {{
        font-size: 0.82rem; color: var(--text-secondary);
        font-family: 'Sora', sans-serif; margin-bottom: 0.6rem;
    }}

    .badge {{
        display: inline-flex; align-items: center; gap: 0.25rem;
        padding: 0.18rem 0.65rem; border-radius: 100px;
        font-size: 0.72rem; font-weight: 600;
        font-family: 'Sora', sans-serif;
        margin-right: 0.3rem; margin-bottom: 0.2rem;
    }}
    .badge-priority-high {{ background:rgba(239,68,68,0.12);color:#ef4444;border:1px solid rgba(239,68,68,0.25); }}
    .badge-priority-medium {{ background:rgba(245,158,11,0.12);color:#f59e0b;border:1px solid rgba(245,158,11,0.25); }}
    .badge-priority-low {{ background:rgba(34,197,94,0.12);color:#22c55e;border:1px solid rgba(34,197,94,0.25); }}
    .badge-tag {{ background:var(--badge-bg);color:var(--text-secondary);border:1px solid var(--border-color); }}
    .badge-status-pendiente {{ background:rgba(245,158,11,0.12);color:#f59e0b;border:1px solid rgba(245,158,11,0.2); }}
    .badge-status-activa {{ background:rgba(13,148,136,0.12);color:#0d9488;border:1px solid rgba(13,148,136,0.25); }}
    .badge-status-completada {{ background:rgba(34,197,94,0.12);color:#22c55e;border:1px solid rgba(34,197,94,0.2); }}

    .page-title {{
        font-size: 1.6rem; font-weight: 700; color: var(--text-primary);
        font-family: 'Sora', sans-serif;
    }}
    .page-subtitle {{
        font-size: 0.82rem; color: var(--text-secondary);
        font-family: 'Sora', sans-serif; margin-top: 0.1rem;
    }}

    .form-container {{
        background: var(--bg-card); border-radius: 16px;
        padding: 1.75rem; border: 1px solid var(--border-color);
        box-shadow: var(--shadow); margin-bottom: 1.5rem;
    }}
    .form-title {{
        font-size: 1.1rem; font-weight: 700; color: var(--text-primary);
        font-family: 'Sora', sans-serif; margin-bottom: 1.25rem;
        padding-bottom: 0.75rem; border-bottom: 1px solid var(--border-color);
    }}

    .section-title {{
        font-size: 1.1rem; font-weight: 700; color: var(--text-primary);
        font-family: 'Sora', sans-serif; margin-bottom: 1rem; margin-top: 0.5rem;
    }}

    .task-count {{
        font-size: 0.78rem; color: var(--text-secondary);
        font-family: 'Sora', sans-serif; margin-bottom: 0.75rem;
    }}

    .activity-item {{
        display: flex; align-items: flex-start; gap: 0.85rem;
        padding: 0.85rem 0; border-bottom: 1px solid var(--border-color);
    }}
    .activity-item:last-child {{ border-bottom: none; }}
    .activity-icon {{
        width: 36px; height: 36px; border-radius: 50%;
        display: flex; align-items: center; justify-content: center;
        font-size: 0.9rem; flex-shrink: 0;
    }}
    .activity-text {{
        font-size: 0.85rem; color: var(--text-primary);
        font-family: 'Sora', sans-serif; line-height: 1.4;
    }}
    .activity-time {{
        font-size: 0.75rem; color: var(--text-secondary);
        font-family: 'Sora', sans-serif; margin-top: 0.15rem;
    }}

    .reminder-card {{
        background: var(--bg-card); border-radius: 14px;
        padding: 1rem 1.25rem; border: 1px solid var(--border-color);
        box-shadow: var(--shadow); margin-bottom: 0.6rem;
        display: flex; align-items: center; gap: 1rem;
        transition: all 0.2s ease;
    }}
    .reminder-card:hover {{ box-shadow: var(--shadow-hover); transform: translateX(3px); }}

    .team-card {{
        background: var(--bg-card); border-radius: 14px;
        padding: 1.25rem 1.5rem; border: 1px solid var(--border-color);
        box-shadow: var(--shadow); margin-bottom: 1rem;
        transition: all 0.2s ease;
    }}
    .team-card:hover {{ box-shadow: var(--shadow-hover); }}

    .confirm-delete-box {{
        background: rgba(239,68,68,0.08);
        border: 1px solid rgba(239,68,68,0.3);
        border-radius: 10px; padding: 0.75rem 1rem; margin: 0.5rem 0;
    }}

    .stRadio > div {{
        flex-direction: row !important;
        gap: 0.5rem !important;
        flex-wrap: wrap !important;
    }}
    .stRadio > div > label {{
        background: var(--bg-card) !important;
        border: 1px solid var(--border-color) !important;
        border-radius: 8px !important;
        padding: 0.35rem 0.85rem !important;
        cursor: pointer !important;
        font-family: 'Sora', sans-serif !important;
        font-size: 0.84rem !important;
    }}

    .stSelectbox [data-baseweb="select"] > div {{
        background: var(--input-bg) !important;
        border-color: var(--border-color) !important;
    }}

    .stTextInput label, .stTextArea label,
    .stSelectbox label, .stDateInput label {{
        font-family: 'Sora', sans-serif !important;
        font-size: 0.85rem !important;
        font-weight: 500 !important;
        color: var(--text-primary) !important;
    }}

    .stSuccess, .stError, .stWarning, .stInfo {{
        border-radius: 10px !important;
        font-family: 'Sora', sans-serif !important;
    }}

    ::-webkit-scrollbar {{ width: 6px; height: 6px; }}
    ::-webkit-scrollbar-track {{ background: var(--bg-main); }}
    ::-webkit-scrollbar-thumb {{ background: var(--border-color); border-radius: 3px; }}
    ::-webkit-scrollbar-thumb:hover {{ background: var(--accent-primary); }}

    /* Sidebar logo */
    .sidebar-logo {{
        display: flex; align-items: center; gap: 0.75rem;
        padding: 0.5rem 0 1.5rem 0;
        border-bottom: 1px solid rgba(255,255,255,0.08);
        margin-bottom: 1.25rem;
    }}
    .logo-icon {{
        width: 40px; height: 40px;
        background: var(--accent-gradient);
        border-radius: 10px; display: flex;
        align-items: center; justify-content: center;
        font-weight: 700; font-size: 1rem;
        color: white; font-family: 'Sora', sans-serif;
    }}
    .logo-text {{ font-size: 1.1rem; font-weight: 700; color: #f1f5f9; font-family: 'Sora', sans-serif; }}
    .logo-sub {{ font-size: 0.7rem; color: #94a3b8; font-family: 'Sora', sans-serif; }}

    .db-status-ok {{
        font-size: 0.72rem; color: #22c55e;
        font-family: 'Sora', sans-serif;
        display: flex; align-items: center; gap: 0.3rem;
        padding: 0.3rem 0.75rem;
        background: rgba(34,197,94,0.1);
        border-radius: 20px; width: fit-content;
        margin-bottom: 0.75rem;
    }}
    .db-status-err {{
        font-size: 0.72rem; color: #ef4444;
        font-family: 'Sora', sans-serif;
        display: flex; align-items: center; gap: 0.3rem;
        padding: 0.3rem 0.75rem;
        background: rgba(239,68,68,0.1);
        border-radius: 20px; width: fit-content;
        margin-bottom: 0.75rem;
    }}

    /* ── Corrección modo oscuro toggle en Configuración ── */
    div[data-testid="stToggle"] label {{
        color: var(--text-primary) !important;
    }}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)


# ─────────────────────────────────────────────
# HELPERS CRUD (session state + DB)
# ─────────────────────────────────────────────

def add_task(title, description, priority, category, status, due_date, assignee, tags):
    ok = db_add_task(title, description, priority, category, status, due_date, assignee, tags)
    if ok:
        st.session_state.tasks = db_load_tasks()


def update_task(task_id, **kwargs):
    ok = db_update_task(task_id, **kwargs)
    if ok:
        st.session_state.tasks = db_load_tasks()


def delete_task(task_id, task_title=""):
    ok = db_delete_task(task_id, task_title)
    if ok:
        st.session_state.tasks = db_load_tasks()


def toggle_task_status(task_id, current_status, title=""):
    ok = db_toggle_task_status(task_id, current_status, title)
    if ok:
        st.session_state.tasks = db_load_tasks()


def get_filtered_tasks(status_filter="Todas", category_filter="Todas", search="") -> list[dict]:
    priority_order = {"High": 0, "Medium": 1, "Low": 2}
    tasks = st.session_state.tasks.copy()
    if status_filter != "Todas":
        tasks = [t for t in tasks if t["status"] == status_filter]
    if category_filter != "Todas":
        tasks = [t for t in tasks if t["category"] == category_filter]
    if search:
        s = search.lower()
        tasks = [
            t for t in tasks
            if s in t["title"].lower()
            or s in t.get("description", "").lower()
            or s in " ".join(t.get("tags", [])).lower()
        ]
    return sorted(tasks, key=lambda x: priority_order.get(x["priority"], 99))


def get_stats() -> dict:
    tasks = st.session_state.tasks
    total = len(tasks)
    completed = sum(1 for t in tasks if t["status"] == "Completada")
    pending = sum(1 for t in tasks if t["status"] == "Pendiente")
    active = sum(1 for t in tasks if t["status"] == "Activa")
    return {
        "total": total,
        "completed": completed,
        "pending": pending,
        "active": active,
        "completion_rate": round((completed / total * 100) if total > 0 else 0),
    }


# ─────────────────────────────────────────────
# COMPONENTES UI
# ─────────────────────────────────────────────

def render_priority_badge(priority: str) -> str:
    cls = f"badge-priority-{priority.lower()}"
    icons = {"High": "🔴", "Medium": "🟡", "Low": "🟢"}
    return f'<span class="badge {cls}">{icons.get(priority,"⚪")} {priority}</span>'


def render_status_badge(status: str) -> str:
    cls = f"badge-status-{status.lower()}"
    icons = {"Pendiente": "⏳", "Activa": "🔵", "Completada": "✅"}
    return f'<span class="badge {cls}">{icons.get(status,"")} {status}</span>'


def render_tag_badge(tag: str) -> str:
    return f'<span class="badge badge-tag">#{tag}</span>'


def render_role_badge(role: str) -> str:
    colors = {"Líder": "#e55a2b", "Editor": "#0d9488", "Viewer": "#6b7280", "Miembro": "#3b82f6"}
    color = colors.get(role, "#6b7280")
    return f'<span class="badge" style="background:rgba(0,0,0,0.06);color:{color};border:1px solid {color}40;">{role}</span>'


def render_task_card(task: dict) -> None:
    is_completed = task["status"] == "Completada"
    card_class = "task-card completed" if is_completed else "task-card"

    tags_html = " ".join(render_tag_badge(t) for t in task.get("tags", []))
    priority_html = render_priority_badge(task["priority"])
    status_html = render_status_badge(task["status"])

    due_str = f"📅 {task.get('due_date', '')}" if task.get("due_date") else ""
    assignee_str = f"👤 {task['assignee']}" if task.get("assignee") else ""
    meta_parts = [p for p in [due_str, assignee_str] if p]
    meta_html = " &nbsp;·&nbsp; ".join(meta_parts)

    st.markdown(f"""
    <div class="{card_class}">
        <div class="task-title">{task['title']}</div>
        <div class="task-desc">{task.get('description','')}</div>
        <div style="display:flex;flex-wrap:wrap;align-items:center;gap:0.3rem;margin-bottom:0.4rem;">
            {priority_html}{status_html}
        </div>
        <div style="margin-bottom:0.3rem;">{tags_html}</div>
        <div style="font-size:0.78rem;color:var(--text-secondary);font-family:'Sora',sans-serif;">
            {meta_html}
        </div>
    </div>
    """, unsafe_allow_html=True)

    col_check, col_edit, col_delete, col_spacer = st.columns([1, 1, 1, 4])

    with col_check:
        label = "↩ Reactivar" if is_completed else "✓ Completar"
        if st.button(label, key=f"toggle_{task['id']}", use_container_width=True):
            toggle_task_status(task["id"], task["status"], task["title"])
            st.rerun()

    with col_edit:
        if st.button("✏️ Editar", key=f"edit_btn_{task['id']}", use_container_width=True):
            st.session_state.editing_task_id = (
                None if st.session_state.editing_task_id == task["id"] else task["id"]
            )
            st.rerun()

    with col_delete:
        if st.button("🗑️ Eliminar", key=f"delete_btn_{task['id']}", use_container_width=True):
            st.session_state.confirm_delete_id = task["id"]
            st.rerun()

    if st.session_state.confirm_delete_id == task["id"]:
        st.markdown(
            '<div class="confirm-delete-box">⚠️ ¿Confirmar eliminación? Esta acción no se puede deshacer.</div>',
            unsafe_allow_html=True,
        )
        col_yes, col_no = st.columns(2)
        with col_yes:
            if st.button("Sí, eliminar", key=f"confirm_yes_{task['id']}", use_container_width=True):
                delete_task(task["id"], task["title"])
                st.session_state.confirm_delete_id = None
                st.success("Tarea eliminada.")
                st.rerun()
        with col_no:
            if st.button("Cancelar", key=f"confirm_no_{task['id']}", use_container_width=True):
                st.session_state.confirm_delete_id = None
                st.rerun()

    if st.session_state.editing_task_id == task["id"]:
        render_edit_form(task)

    st.markdown("<div style='height:0.25rem'></div>", unsafe_allow_html=True)


def render_edit_form(task: dict) -> None:
    st.markdown('<div class="form-container">', unsafe_allow_html=True)
    st.markdown('<div class="form-title">✏️ Editar Tarea</div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        new_title = st.text_input("Título *", value=task["title"], key=f"edit_title_{task['id']}")
        new_desc = st.text_area("Descripción", value=task.get("description", ""), key=f"edit_desc_{task['id']}", height=80)
        new_assignee = st.text_input("Asignado a", value=task.get("assignee", ""), key=f"edit_assignee_{task['id']}")
    with col2:
        new_priority = st.selectbox("Prioridad", PRIORITIES, index=PRIORITIES.index(task["priority"]), key=f"edit_priority_{task['id']}")
        new_category = st.selectbox("Categoría", CATEGORIES, index=CATEGORIES.index(task["category"]) if task["category"] in CATEGORIES else 0, key=f"edit_category_{task['id']}")
        new_status = st.selectbox("Estado", STATUS_OPTIONS, index=STATUS_OPTIONS.index(task["status"]) if task["status"] in STATUS_OPTIONS else 0, key=f"edit_status_{task['id']}")
        try:
            current_date = date.fromisoformat(task.get("due_date", date.today().isoformat()))
        except (ValueError, TypeError):
            current_date = date.today()
        new_due_date = st.date_input("Fecha límite", value=current_date, key=f"edit_date_{task['id']}")

    tags_str = st.text_input("Etiquetas (separadas por coma)", value=", ".join(task.get("tags", [])), key=f"edit_tags_{task['id']}")

    col_save, col_cancel = st.columns([1, 3])
    with col_save:
        if st.button("💾 Guardar cambios", key=f"save_{task['id']}", use_container_width=True):
            if not new_title.strip():
                st.error("El título es obligatorio.")
            else:
                new_tags = [t.strip() for t in tags_str.split(",") if t.strip()]
                update_task(
                    task["id"],
                    title=new_title.strip(),
                    description=new_desc.strip(),
                    priority=new_priority,
                    category=new_category,
                    status=new_status,
                    due_date=new_due_date.isoformat(),
                    assignee=new_assignee.strip(),
                    tags=new_tags,
                )
                st.session_state.editing_task_id = None
                st.success("✅ Tarea actualizada.")
                st.rerun()
    with col_cancel:
        if st.button("Cancelar", key=f"cancel_edit_{task['id']}"):
            st.session_state.editing_task_id = None
            st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)


def render_new_task_form() -> None:
    st.markdown('<div class="form-container">', unsafe_allow_html=True)
    st.markdown('<div class="form-title">➕ Nueva Tarea</div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        title = st.text_input("Título *", placeholder="¿Qué necesitas hacer?", key="new_title")
        description = st.text_area("Descripción", placeholder="Añade más detalles...", key="new_desc", height=90)
        assignee = st.text_input("Asignado a", placeholder="Nombre del responsable", key="new_assignee")
    with col2:
        priority = st.selectbox("Prioridad", PRIORITIES, key="new_priority")
        category = st.selectbox("Categoría", CATEGORIES, key="new_category")
        status = st.selectbox("Estado inicial", STATUS_OPTIONS, key="new_status")
        due_date = st.date_input("Fecha límite", value=date.today(), key="new_date")

    tags_input = st.text_input("Etiquetas (separadas por coma)", placeholder="ej: diseño, urgente, cliente", key="new_tags")

    col_btn, col_cancel, _ = st.columns([1, 1, 4])
    with col_btn:
        if st.button("✅ Crear Tarea", key="btn_create_task", use_container_width=True):
            if not title.strip():
                st.error("⚠️ El título es obligatorio.")
            else:
                tags = [t.strip() for t in tags_input.split(",") if t.strip()]
                add_task(title, description, priority, category, status, due_date, assignee, tags)
                st.session_state.show_new_task_form = False
                st.success(f"✅ Tarea '{title.strip()}' creada.")
                st.rerun()
    with col_cancel:
        if st.button("Cancelar", key="btn_cancel_new"):
            st.session_state.show_new_task_form = False
            st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────

def render_sidebar() -> None:
    with st.sidebar:
        st.markdown("""
        <div class="sidebar-logo">
            <div class="logo-icon">GP</div>
            <div>
                <div class="logo-text">GestorPro</div>
                <div class="logo-sub">Productividad elevada</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Estado de conexión DB
        db_status_html = (
            '<div class="db-status-ok">🟢 MySQL conectado</div>'
            if st.session_state.db_ok
            else '<div class="db-status-err">🔴 Sin conexión DB</div>'
        )
        st.markdown(db_status_html, unsafe_allow_html=True)

        nav_items = [
            ("📊", "Dashboard"),
            ("✅", "Tareas"),
            ("📅", "Calendario"),
            ("👥", "Equipo"),
            ("🔔", "Recordatorios"),
            ("⚡", "Actividad"),
        ]

        for icon, page in nav_items:
            if st.button(f"{icon}  {page}", key=f"nav_{page}", use_container_width=True):
                st.session_state.active_page = page
                st.session_state.show_new_task_form = False
                st.session_state.show_new_team_form = False
                st.session_state.editing_task_id = None
                st.session_state.confirm_delete_id = None
                st.session_state.managing_team_id = None
                st.rerun()

        st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
        st.markdown("<div style='height:1px;background:rgba(255,255,255,0.08);margin-bottom:0.75rem;'></div>", unsafe_allow_html=True)

        dark_mode = st.toggle("🌙  Modo Oscuro", value=st.session_state.dark_mode, key="toggle_dark_mode")
        if dark_mode != st.session_state.dark_mode:
            st.session_state.dark_mode = dark_mode
            st.rerun()

        if st.button("⚙️  Configuración", key="nav_config", use_container_width=True):
            st.session_state.active_page = "Configuración"
            st.rerun()

        st.markdown("<div style='height:0.75rem'></div>", unsafe_allow_html=True)
        stats = get_stats()
        st.markdown(f"""
        <div style="background:rgba(255,255,255,0.04);border-radius:12px;padding:1rem;
                    border:1px solid rgba(255,255,255,0.07);">
            <div style="font-size:0.75rem;color:#94a3b8;font-family:'Sora',sans-serif;
                        margin-bottom:0.6rem;font-weight:600;letter-spacing:0.05em;text-transform:uppercase;">
                Resumen Rápido
            </div>
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:0.5rem;">
                <div style="text-align:center;">
                    <div style="font-size:1.4rem;font-weight:700;color:#f1f5f9;font-family:'Sora',sans-serif;">{stats['total']}</div>
                    <div style="font-size:0.68rem;color:#94a3b8;font-family:'Sora',sans-serif;">Total</div>
                </div>
                <div style="text-align:center;">
                    <div style="font-size:1.4rem;font-weight:700;color:#22c55e;font-family:'Sora',sans-serif;">{stats['completed']}</div>
                    <div style="font-size:0.68rem;color:#94a3b8;font-family:'Sora',sans-serif;">Completadas</div>
                </div>
                <div style="text-align:center;">
                    <div style="font-size:1.4rem;font-weight:700;color:#f59e0b;font-family:'Sora',sans-serif;">{stats['pending']}</div>
                    <div style="font-size:0.68rem;color:#94a3b8;font-family:'Sora',sans-serif;">Pendientes</div>
                </div>
                <div style="text-align:center;">
                    <div style="font-size:1.4rem;font-weight:700;color:#e55a2b;font-family:'Sora',sans-serif;">{stats['completion_rate']}%</div>
                    <div style="font-size:0.68rem;color:#94a3b8;font-family:'Sora',sans-serif;">Tasa</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)


# ─────────────────────────────────────────────
# PÁGINAS
# ─────────────────────────────────────────────

def render_dashboard() -> None:
    col_title, _ = st.columns([3, 1])
    with col_title:
        st.markdown("""
        <div style="margin-bottom:1.5rem;">
            <div style="font-size:1.5rem;font-weight:700;color:var(--text-primary);font-family:'Sora',sans-serif;">
                Resumen de Productividad
            </div>
            <div style="font-size:0.8rem;color:var(--text-secondary);font-family:'Sora',sans-serif;">
                Actualizado en tiempo real desde MySQL
            </div>
        </div>
        """, unsafe_allow_html=True)

    qa_col1, qa_col2, qa_col3, qa_col4 = st.columns(4)
    quick_actions = [
        (qa_col1, "🟠", "#fff3ee", "Nueva Tarea", "Crear tarea rápida"),
        (qa_col2, "🟢", "#eefbf7", "Vista Rápida", "Tareas urgentes"),
        (qa_col3, "🟡", "#fffbea", "Invitar Equipo", "Agregar miembros"),
        (qa_col4, "🔵", "#eef4ff", "Nuevo Equipo", "Iniciar equipo"),
    ]

    for col, color_bg, bg, label, sub in quick_actions:
        with col:
            st.markdown(f"""
            <div style="background:var(--bg-card);border-radius:14px;padding:1.25rem;
                        border:1px solid var(--border-color);box-shadow:var(--shadow);
                        text-align:center;margin-bottom:0.5rem;min-height:90px;
                        display:flex;flex-direction:column;align-items:center;justify-content:center;gap:0.4rem;">
                <div style="width:36px;height:36px;border-radius:9px;background:{bg};
                            display:flex;align-items:center;justify-content:center;
                            font-size:1.1rem;margin:0 auto;">{color_bg}</div>
                <div style="font-size:0.82rem;font-weight:600;color:var(--text-primary);
                            font-family:'Sora',sans-serif;">{label}</div>
                <div style="font-size:0.72rem;color:var(--text-secondary);
                            font-family:'Sora',sans-serif;">{sub}</div>
            </div>
            """, unsafe_allow_html=True)

    with qa_col1:
        if st.button("+ Crear tarea", key="dash_new_task", use_container_width=True):
            st.session_state.active_page = "Tareas"
            st.session_state.show_new_task_form = True
            st.rerun()
    with qa_col4:
        if st.button("+ Crear equipo", key="dash_new_team", use_container_width=True):
            st.session_state.active_page = "Equipo"
            st.session_state.show_new_team_form = True
            st.rerun()

    stats = get_stats()
    s1, s2, s3, s4 = st.columns(4)
    with s1:
        st.markdown(f'<div class="stat-card"><div class="stat-icon" style="background:#fff3ee;">📋</div><div class="stat-value">{stats["completed"]}</div><div class="stat-label">Completadas</div><div class="stat-delta positive">▲ +{stats["completed"]} tareas</div></div>', unsafe_allow_html=True)
    with s2:
        st.markdown(f'<div class="stat-card"><div class="stat-icon" style="background:#fff8ee;">⏳</div><div class="stat-value">{stats["pending"]}</div><div class="stat-label">Pendientes</div><div class="stat-delta negative">▼ Por completar</div></div>', unsafe_allow_html=True)
    with s3:
        st.markdown(f'<div class="stat-card"><div class="stat-icon" style="background:#eefbf7;">🔥</div><div class="stat-value">{stats["active"]}</div><div class="stat-label">Tareas activas</div><div class="stat-delta positive">▲ En progreso</div></div>', unsafe_allow_html=True)
    with s4:
        st.markdown(f'<div class="stat-card"><div class="stat-icon" style="background:#eef4ff;">🎯</div><div class="stat-value">{stats["completion_rate"]}%</div><div class="stat-label">Tasa de finalización</div><div class="stat-delta positive">▲ Tiempo real</div></div>', unsafe_allow_html=True)

    st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)

    col_chart, col_dist = st.columns(2)
    with col_chart:
        st.markdown('<div class="section-title">📈 Tareas por Categoría</div>', unsafe_allow_html=True)
        category_counts = {}
        for task in st.session_state.tasks:
            cat = task.get("category", "Otro")
            category_counts[cat] = category_counts.get(cat, 0) + 1
        if category_counts:
            import pandas as pd
            df_cat = pd.DataFrame(list(category_counts.items()), columns=["Categoría", "Tareas"])
            st.bar_chart(df_cat.set_index("Categoría"), color="#e55a2b", height=220)
        else:
            st.info("No hay datos para mostrar.")

    with col_dist:
        st.markdown('<div class="section-title">🍩 Distribución por Estado</div>', unsafe_allow_html=True)
        total = stats["total"] or 1
        for status, count in [("Completada", stats["completed"]), ("Activa", stats["active"]), ("Pendiente", stats["pending"])]:
            pct = round(count / total * 100)
            colors = {"Completada": "#22c55e", "Activa": "#0d9488", "Pendiente": "#f59e0b"}
            color = colors[status]
            st.markdown(f"""
            <div style="margin-bottom:0.6rem;">
                <div style="display:flex;justify-content:space-between;font-size:0.82rem;
                            font-family:'Sora',sans-serif;color:var(--text-primary);margin-bottom:0.25rem;">
                    <span>{status}</span>
                    <span style="font-weight:600;">{count} ({pct}%)</span>
                </div>
                <div style="height:8px;background:var(--border-color);border-radius:4px;overflow:hidden;">
                    <div style="height:100%;width:{pct}%;background:{color};border-radius:4px;"></div>
                </div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
    st.markdown('<div class="section-title">📋 Tareas Recientes</div>', unsafe_allow_html=True)
    recent = sorted(st.session_state.tasks, key=lambda x: x.get("created_at", ""), reverse=True)[:4]
    for task in recent:
        st.markdown(f"""
        <div class="task-card" style="margin-bottom:0.5rem;">
            <div style="display:flex;justify-content:space-between;align-items:flex-start;">
                <div>
                    <div class="task-title">{task['title']}</div>
                    <div class="task-desc">{task.get('description','')}</div>
                </div>
                <div style="display:flex;gap:0.3rem;flex-shrink:0;">
                    {render_priority_badge(task['priority'])}{render_status_badge(task['status'])}
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)


def render_tasks_page() -> None:
    col_h, col_btn = st.columns([3, 1])
    with col_h:
        st.markdown('<div class="page-title">Mis Tareas</div>', unsafe_allow_html=True)
        st.markdown('<div class="page-subtitle">Gestiona y organiza todas tus tareas</div>', unsafe_allow_html=True)
    with col_btn:
        st.markdown("<div style='height:0.4rem'></div>", unsafe_allow_html=True)
        if st.button("➕ Nueva Tarea", key="open_new_task", use_container_width=True):
            st.session_state.show_new_task_form = not st.session_state.show_new_task_form
            st.rerun()

    st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)

    if st.session_state.show_new_task_form:
        render_new_task_form()

    search = st.text_input("🔍 Buscar tareas...", value=st.session_state.search_query,
                           placeholder="Buscar por título, descripción o etiquetas...", key="search_input")
    if search != st.session_state.search_query:
        st.session_state.search_query = search

    col_f1, col_f2 = st.columns(2)
    with col_f1:
        status_filter = st.radio("Estado", ["Todas", "Activa", "Pendiente", "Completada"], horizontal=True, key="status_filter_radio")
    with col_f2:
        category_filter = st.selectbox("Categoría", ["Todas"] + CATEGORIES, key="category_filter_select")

    filtered = get_filtered_tasks(status_filter, category_filter, st.session_state.search_query)
    total = len(st.session_state.tasks)
    completed = sum(1 for t in st.session_state.tasks if t["status"] == "Completada")
    st.markdown(
        f'<div class="task-count">{len(filtered)} tareas encontradas &nbsp;·&nbsp; {total} total &nbsp;·&nbsp; {completed} completadas</div>',
        unsafe_allow_html=True,
    )

    if not filtered:
        st.markdown("""
        <div style="text-align:center;padding:3rem;color:var(--text-secondary);font-family:'Sora',sans-serif;">
            <div style="font-size:2.5rem;margin-bottom:0.75rem;">📭</div>
            <div style="font-size:1rem;font-weight:500;">No se encontraron tareas</div>
            <div style="font-size:0.82rem;margin-top:0.3rem;">Intenta ajustar los filtros o crea una nueva tarea</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        for task in filtered:
            render_task_card(task)


def render_calendar_page() -> None:
    st.markdown('<div class="page-title">📅 Calendario</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="page-subtitle">Vista de {date.today().strftime("%B %Y")}</div>', unsafe_allow_html=True)
    st.markdown("<div style='height:0.75rem'></div>", unsafe_allow_html=True)

    tasks_by_date: dict[str, list] = {}
    for task in st.session_state.tasks:
        due = task.get("due_date", "")
        if due:
            tasks_by_date.setdefault(due, []).append(task)

    st.markdown('<div class="section-title">Próximas tareas</div>', unsafe_allow_html=True)

    if not tasks_by_date:
        st.info("No hay tareas con fechas asignadas.")
    else:
        for date_str in sorted(tasks_by_date.keys()):
            try:
                d = date.fromisoformat(date_str)
                display_date = d.strftime("%d de %B, %Y")
            except (ValueError, TypeError):
                display_date = date_str

            is_today = date_str == date.today().isoformat()
            today_indicator = " 🔵 HOY" if is_today else ""

            st.markdown(f"""
            <div style="font-size:0.88rem;font-weight:700;color:var(--text-primary);
                        font-family:'Sora',sans-serif;margin:1rem 0 0.5rem 0;
                        padding-left:0.5rem;border-left:3px solid var(--accent-primary);">
                {display_date}{today_indicator}
            </div>
            """, unsafe_allow_html=True)

            for task in tasks_by_date[date_str]:
                cat_color = CATEGORY_COLORS.get(task["category"], "#6b7280")
                st.markdown(f"""
                <div class="task-card" style="border-left:3px solid {cat_color};">
                    <div style="display:flex;justify-content:space-between;align-items:center;">
                        <div>
                            <div class="task-title">{task['title']}</div>
                            <div class="task-desc">{task.get('description','')}</div>
                        </div>
                        <div style="display:flex;gap:0.3rem;">
                            {render_priority_badge(task['priority'])}{render_status_badge(task['status'])}
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)


def render_team_page() -> None:
    """
    Página de gestión de equipos con CRUD completo:
    - Crear equipos con líder
    - Agregar/remover miembros
    - Cambiar roles (solo líder puede gestionar)
    - Mover miembros entre equipos
    """
    col_h, col_btn = st.columns([3, 1])
    with col_h:
        st.markdown('<div class="page-title">👥 Equipos</div>', unsafe_allow_html=True)
        st.markdown('<div class="page-subtitle">Crea y gestiona tus equipos de trabajo</div>', unsafe_allow_html=True)
    with col_btn:
        st.markdown("<div style='height:0.4rem'></div>", unsafe_allow_html=True)
        if st.button("➕ Nuevo Equipo", key="open_new_team", use_container_width=True):
            st.session_state.show_new_team_form = not st.session_state.show_new_team_form
            st.rerun()

    st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)

    # ── Formulario de nuevo equipo ──
    if st.session_state.show_new_team_form:
        st.markdown('<div class="form-container">', unsafe_allow_html=True)
        st.markdown('<div class="form-title">🏗️ Crear Nuevo Equipo</div>', unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            team_name = st.text_input("Nombre del equipo *", placeholder="ej: Equipo Frontend", key="new_team_name")
            team_desc = st.text_area("Descripción", placeholder="¿Cuál es el propósito de este equipo?", key="new_team_desc", height=80)
        with col2:
            leader_name = st.text_input("Tu nombre (serás el Líder) *", placeholder="ej: Ana García", key="new_team_leader")
            st.markdown("""
            <div style="background:rgba(229,90,43,0.08);border-radius:10px;padding:0.75rem 1rem;
                        border:1px solid rgba(229,90,43,0.2);margin-top:0.5rem;">
                <div style="font-size:0.8rem;color:var(--text-primary);font-family:'Sora',sans-serif;font-weight:600;">
                    📌 Roles disponibles:
                </div>
                <div style="font-size:0.75rem;color:var(--text-secondary);font-family:'Sora',sans-serif;margin-top:0.3rem;">
                    🟠 <b>Líder</b>: Gestiona equipo y miembros<br>
                    🔵 <b>Miembro</b>: Participa en el equipo<br>
                    🟢 <b>Editor</b>: Puede editar tareas<br>
                    ⚪ <b>Viewer</b>: Solo lectura
                </div>
            </div>
            """, unsafe_allow_html=True)

        col_save, col_cancel, _ = st.columns([1, 1, 3])
        with col_save:
            if st.button("✅ Crear Equipo", key="btn_create_team", use_container_width=True):
                if not team_name.strip():
                    st.error("El nombre del equipo es obligatorio.")
                elif not leader_name.strip():
                    st.error("Debes ingresar tu nombre como líder.")
                else:
                    ok = db_create_team(team_name, team_desc, leader_name)
                    if ok:
                        st.session_state.show_new_team_form = False
                        st.session_state.teams = db_load_teams()
                        st.success(f"✅ Equipo '{team_name}' creado.")
                        st.rerun()
        with col_cancel:
            if st.button("Cancelar", key="btn_cancel_team"):
                st.session_state.show_new_team_form = False
                st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    # ── Lista de equipos ──
    teams = st.session_state.teams

    if not teams:
        st.markdown("""
        <div style="text-align:center;padding:3rem;color:var(--text-secondary);font-family:'Sora',sans-serif;">
            <div style="font-size:2.5rem;margin-bottom:0.75rem;">👥</div>
            <div style="font-size:1rem;font-weight:500;">No hay equipos creados</div>
            <div style="font-size:0.82rem;margin-top:0.3rem;">Crea tu primer equipo con el botón de arriba</div>
        </div>
        """, unsafe_allow_html=True)
        return

    avatar_colors = ["#e55a2b", "#0d9488", "#8b5cf6", "#f59e0b", "#3b82f6", "#ec4899"]

    for team in teams:
        members = team.get("members", [])
        leader = next((m for m in members if m["role"] == "Líder"), None)
        member_count = len(members)

        st.markdown(f"""
        <div class="team-card">
            <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:0.75rem;">
                <div>
                    <div style="font-size:1.1rem;font-weight:700;color:var(--text-primary);
                                font-family:'Sora',sans-serif;">{team['name']}</div>
                    <div style="font-size:0.8rem;color:var(--text-secondary);font-family:'Sora',sans-serif;">
                        {team.get('description','Sin descripción')}
                    </div>
                </div>
                <div style="font-size:0.75rem;color:var(--text-secondary);font-family:'Sora',sans-serif;
                            text-align:right;flex-shrink:0;">
                    👑 Líder: {leader['member_name'] if leader else 'Sin líder'}<br>
                    <span style="color:var(--accent-primary);font-weight:600;">{member_count} miembros</span>
                </div>
            </div>
            <div style="display:flex;flex-wrap:wrap;gap:0.4rem;margin-bottom:0.5rem;">
        """, unsafe_allow_html=True)

        for i, m in enumerate(members):
            color = avatar_colors[i % len(avatar_colors)]
            initials = "".join([p[0].upper() for p in m["member_name"].split()[:2]])
            st.markdown(f"""
            <span style="display:inline-flex;align-items:center;gap:0.4rem;
                         background:rgba(0,0,0,0.04);border-radius:20px;
                         padding:0.2rem 0.6rem;margin-bottom:0.2rem;
                         border:1px solid var(--border-color);">
                <span style="width:22px;height:22px;border-radius:50%;background:{color};
                             display:inline-flex;align-items:center;justify-content:center;
                             color:white;font-size:0.6rem;font-weight:700;">{initials}</span>
                <span style="font-size:0.78rem;color:var(--text-primary);font-family:'Sora',sans-serif;">
                    {m['member_name']}</span>
                {render_role_badge(m['role'])}
            </span>
            """, unsafe_allow_html=True)

        st.markdown("</div></div>", unsafe_allow_html=True)

        # ── Controles de equipo ──
        col_manage, col_delete_team, _ = st.columns([1, 1, 4])

        with col_manage:
            manage_label = "🔽 Cerrar" if st.session_state.managing_team_id == team["id"] else "⚙️ Gestionar"
            if st.button(manage_label, key=f"manage_{team['id']}", use_container_width=True):
                st.session_state.managing_team_id = (
                    None if st.session_state.managing_team_id == team["id"] else team["id"]
                )
                st.rerun()

        with col_delete_team:
            if st.button("🗑️ Eliminar equipo", key=f"del_team_{team['id']}", use_container_width=True):
                st.session_state.confirm_delete_team_id = team["id"]
                st.rerun()

        # Confirmación de eliminar equipo
        if st.session_state.get("confirm_delete_team_id") == team["id"]:
            st.markdown('<div class="confirm-delete-box">⚠️ ¿Eliminar el equipo y todos sus miembros? No se puede deshacer.</div>', unsafe_allow_html=True)
            cy, cn = st.columns(2)
            with cy:
                if st.button("Sí, eliminar equipo", key=f"conf_del_team_{team['id']}", use_container_width=True):
                    db_delete_team(team["id"], team["name"])
                    st.session_state.confirm_delete_team_id = None
                    st.session_state.teams = db_load_teams()
                    st.success("Equipo eliminado.")
                    st.rerun()
            with cn:
                if st.button("Cancelar", key=f"conf_no_team_{team['id']}", use_container_width=True):
                    st.session_state.confirm_delete_team_id = None
                    st.rerun()

        # ── Panel de gestión de miembros ──
        if st.session_state.managing_team_id == team["id"]:
            st.markdown("""
            <div style="background:var(--bg-card);border-radius:14px;padding:1.25rem;
                        border:1px solid var(--border-color);margin-top:0.5rem;margin-bottom:0.5rem;">
            """, unsafe_allow_html=True)

            # Sub-tabs: Agregar / Gestionar miembros existentes
            tab_add, tab_manage = st.tabs(["➕ Agregar miembro", "🔧 Gestionar miembros"])

            with tab_add:
                col_nm, col_nr, col_nb = st.columns([2, 1, 1])
                with col_nm:
                    new_member_name = st.text_input("Nombre del miembro", placeholder="ej: Carlos Ruiz", key=f"new_member_{team['id']}")
                with col_nr:
                    new_member_role = st.selectbox("Rol", TEAM_ROLES, key=f"new_member_role_{team['id']}")
                with col_nb:
                    st.markdown("<div style='height:1.75rem'></div>", unsafe_allow_html=True)
                    if st.button("Agregar", key=f"add_member_{team['id']}", use_container_width=True):
                        if not new_member_name.strip():
                            st.error("Ingresa el nombre del miembro.")
                        else:
                            ok = db_add_member(team["id"], new_member_name, new_member_role, team["name"])
                            if ok:
                                st.session_state.teams = db_load_teams()
                                st.success(f"✅ {new_member_name} agregado como {new_member_role}.")
                                st.rerun()

            with tab_manage:
                if not members:
                    st.info("No hay miembros en este equipo.")
                else:
                    # Obtener otros equipos para mover miembros
                    other_teams = [t for t in st.session_state.teams if t["id"] != team["id"]]

                    for m in members:
                        mcol_name, mcol_role, mcol_move, mcol_remove = st.columns([2, 1, 2, 1])

                        with mcol_name:
                            st.markdown(f"""
                            <div style="padding-top:0.5rem;font-size:0.88rem;font-weight:600;
                                        color:var(--text-primary);font-family:'Sora',sans-serif;">
                                {m['member_name']}
                            </div>
                            """, unsafe_allow_html=True)

                        with mcol_role:
                            current_role_idx = TEAM_ROLES.index(m["role"]) if m["role"] in TEAM_ROLES else 1
                            new_role = st.selectbox(
                                "Rol", TEAM_ROLES,
                                index=current_role_idx,
                                key=f"role_select_{m['id']}",
                                label_visibility="collapsed",
                            )
                            if new_role != m["role"]:
                                if st.button("✓", key=f"save_role_{m['id']}", help="Guardar rol"):
                                    db_update_member_role(m["id"], new_role, m["member_name"])
                                    st.session_state.teams = db_load_teams()
                                    st.rerun()

                        with mcol_move:
                            if other_teams:
                                target_team_names = [t["name"] for t in other_teams]
                                target_team_selected = st.selectbox(
                                    "Mover a",
                                    target_team_names,
                                    key=f"move_target_{m['id']}",
                                    label_visibility="collapsed",
                                )
                                if st.button("↗ Mover", key=f"move_member_{m['id']}", use_container_width=True):
                                    target = next(t for t in other_teams if t["name"] == target_team_selected)
                                    ok = db_move_member(m["id"], target["id"], m["member_name"], target["name"])
                                    if ok:
                                        st.session_state.teams = db_load_teams()
                                        st.success(f"{m['member_name']} movido a {target['name']}.")
                                        st.rerun()
                            else:
                                st.markdown("<div style='font-size:0.75rem;color:var(--text-secondary);padding-top:0.5rem;'>No hay otros equipos</div>", unsafe_allow_html=True)

                        with mcol_remove:
                            if st.button("✕", key=f"remove_member_{m['id']}", help=f"Remover a {m['member_name']}"):
                                ok = db_remove_member(m["id"], m["member_name"], team["name"])
                                if ok:
                                    st.session_state.teams = db_load_teams()
                                    st.success(f"{m['member_name']} removido del equipo.")
                                    st.rerun()

                        st.markdown("<div style='height:0.1rem;background:var(--border-color);margin:0.3rem 0;'></div>", unsafe_allow_html=True)

            st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)


def render_reminders_page() -> None:
    col_h, col_btn = st.columns([3, 1])
    with col_h:
        st.markdown('<div class="page-title">🔔 Recordatorios</div>', unsafe_allow_html=True)
    with col_btn:
        st.markdown("<div style='height:0.4rem'></div>", unsafe_allow_html=True)
        if st.button("➕ Nueva Tarea", key="new_reminder_btn", use_container_width=True):
            st.session_state.active_page = "Tareas"
            st.session_state.show_new_task_form = True
            st.rerun()

    st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)

    reminders = sorted(
        [t for t in st.session_state.tasks if t.get("due_date")],
        key=lambda x: x.get("due_date", ""),
    )

    if not reminders:
        st.info("No tienes recordatorios configurados.")
    else:
        for task in reminders:
            cat = task.get("category", "")
            cat_badge = f'<span class="badge badge-tag">{cat}</span>' if cat else ""
            st.markdown(f"""
            <div class="reminder-card">
                <div style="width:36px;height:36px;border-radius:50%;background:rgba(229,90,43,0.12);
                            display:flex;align-items:center;justify-content:center;font-size:1.1rem;flex-shrink:0;">🔔</div>
                <div style="flex:1;">
                    <div style="font-weight:600;font-size:0.9rem;color:var(--text-primary);
                                font-family:'Sora',sans-serif;">{task['title']}</div>
                    <div style="font-size:0.78rem;color:var(--text-secondary);font-family:'Sora',sans-serif;">
                        {task.get('description','')}
                    </div>
                    <div style="margin-top:0.3rem;font-size:0.76rem;color:var(--text-secondary);font-family:'Sora',sans-serif;">
                        📅 {task.get('due_date','')} &nbsp; {cat_badge}
                    </div>
                </div>
                <div style="flex-shrink:0;">{render_priority_badge(task['priority'])}</div>
            </div>
            """, unsafe_allow_html=True)


def render_activity_page() -> None:
    """
    Muestra el historial real de actividad desde MySQL.
    Se actualiza automáticamente con cada cambio en tareas o equipos.
    """
    st.markdown('<div class="page-title">⚡ Actividad Reciente</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-subtitle">Registro en tiempo real de todas las acciones</div>', unsafe_allow_html=True)
    st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)

    # Botón de refresco manual
    col_ref, _ = st.columns([1, 5])
    with col_ref:
        if st.button("🔄 Actualizar", key="refresh_activity", use_container_width=True):
            st.rerun()

    activity = db_load_activity(limit=30)

    if not activity:
        st.markdown("""
        <div style="text-align:center;padding:3rem;color:var(--text-secondary);font-family:'Sora',sans-serif;">
            <div style="font-size:2.5rem;margin-bottom:0.75rem;">📭</div>
            <div style="font-size:1rem;font-weight:500;">No hay actividad registrada aún</div>
            <div style="font-size:0.82rem;margin-top:0.3rem;">Las acciones en tareas y equipos aparecerán aquí</div>
        </div>
        """, unsafe_allow_html=True)
        return

    action_icons = {
        "creó la tarea": ("✅", "#22c55e"),
        "actualizó la tarea": ("✏️", "#8b5cf6"),
        "eliminó la tarea": ("🗑️", "#ef4444"),
        "completó la tarea": ("🎯", "#22c55e"),
        "reactivó la tarea": ("↩️", "#f59e0b"),
        "creó el equipo": ("👥", "#3b82f6"),
        "agregó": ("➕", "#0d9488"),
        "removió": ("✕", "#ef4444"),
        "movió": ("↗️", "#f59e0b"),
        "cambió el rol": ("🔄", "#8b5cf6"),
        "eliminó el equipo": ("🗑️", "#ef4444"),
    }

    for item in activity:
        action = item.get("action", "")
        icon, color = next(
            ((ic, co) for key, (ic, co) in action_icons.items() if key in action),
            ("📌", "#6b7280"),
        )
        r, g, b = _hex_to_rgb(color)
        entity_name = item.get("entity_name", "")
        time_str = _time_ago(item.get("created_at", ""))

        st.markdown(f"""
        <div class="activity-item">
            <div class="activity-icon" style="background:rgba({r},{g},{b},0.12);">
                {icon}
            </div>
            <div>
                <div class="activity-text">
                    <strong>{item.get('user_name','Usuario')}</strong>
                    {action}
                    {f'<strong>{entity_name}</strong>' if entity_name else ''}
                </div>
                <div class="activity-time">🕐 {time_str}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)


def render_config_page() -> None:
    st.markdown('<div class="page-title">⚙️ Configuración</div>', unsafe_allow_html=True)
    st.markdown("<div style='height:0.75rem'></div>", unsafe_allow_html=True)

    with st.expander("👤 Perfil", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            st.text_input("Nombre completo", value="Usuario Demo", key="config_name")
        with col2:
            st.text_input("Email", value="usuario@gestorpro.com", key="config_email")
        if st.button("💾 Guardar Perfil", key="save_profile"):
            st.success("✅ Perfil actualizado correctamente.")

    with st.expander("🔔 Notificaciones", expanded=True):
        st.toggle("Notificaciones de tareas", value=True, key="notif_tasks")
        st.toggle("Recordatorios diarios", value=True, key="notif_daily")
        st.toggle("Actualizaciones de proyectos", value=False, key="notif_projects")
        st.toggle("Mensajes del equipo", value=True, key="notif_team")
        if st.button("💾 Guardar Notificaciones", key="save_notifs"):
            st.success("✅ Preferencias guardadas.")

    with st.expander("🗄️ Gestión de Datos", expanded=False):
        col_export, col_reset = st.columns(2)
        with col_export:
            tasks_json = json.dumps(st.session_state.tasks, ensure_ascii=False, indent=2)
            st.download_button(
                label="📥 Exportar Tareas (JSON)",
                data=tasks_json,
                file_name="gestorpro_tasks.json",
                mime="application/json",
                use_container_width=True,
            )
        with col_reset:
            if st.button("🔄 Datos de ejemplo", key="reset_data", use_container_width=True):
                # Borra y reinserta datos de ejemplo
                conn, cursor = get_cursor()
                if cursor:
                    try:
                        cursor.execute("DELETE FROM tasks")
                        conn.commit()
                    except MySQLError:
                        pass
                    finally:
                        cursor.close()
                seed_sample_data()
                st.session_state.tasks = db_load_tasks()
                st.success("✅ Datos de ejemplo restaurados.")
                st.rerun()

    with st.expander("🎨 Apariencia", expanded=False):
        # CORRECCIÓN: usar on_change para sincronizar correctamente el toggle con session_state
        def _toggle_dark():
            st.session_state.dark_mode = st.session_state._config_dark_toggle

        current_dark = st.session_state.dark_mode
        st.toggle(
            "Modo Oscuro",
            value=current_dark,
            key="_config_dark_toggle",
            on_change=_toggle_dark,
        )
        st.markdown(
            '<div style="font-size:0.8rem;color:var(--text-secondary);font-family:\'Sora\',sans-serif;margin-top:0.5rem;">'
            "También puedes alternar el tema desde el panel lateral."
            "</div>",
            unsafe_allow_html=True,
        )

    with st.expander("🔌 Base de Datos", expanded=False):
        st.markdown(f"""
        <div style="font-family:'Sora',sans-serif;font-size:0.85rem;color:var(--text-primary);">
            <div style="margin-bottom:0.5rem;"><b>Estado:</b>
                {'<span style="color:#22c55e;">✅ Conectado</span>' if st.session_state.db_ok else '<span style="color:#ef4444;">❌ Sin conexión</span>'}
            </div>
            <div><b>Host:</b> {DB_CONFIG['host']}:{DB_CONFIG['port']}</div>
            <div><b>Base de datos:</b> {DB_CONFIG['database']}</div>
            <div><b>Usuario:</b> {DB_CONFIG['user']}</div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("🔄 Reconectar BD", key="reconnect_db"):
            st.cache_resource.clear()
            st.session_state.db_ok = False
            st.rerun()


# ─────────────────────────────────────────────
# UTILIDADES
# ─────────────────────────────────────────────

def _hex_to_rgb(hex_color: str):
    hex_color = hex_color.lstrip("#")
    try:
        r, g, b = (int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        return r, g, b
    except (ValueError, IndexError):
        return 0, 0, 0


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

def main() -> None:
    init_session_state()
    inject_css()
    render_sidebar()

    page_renderers = {
        "Dashboard": render_dashboard,
        "Tareas": render_tasks_page,
        "Calendario": render_calendar_page,
        "Equipo": render_team_page,
        "Recordatorios": render_reminders_page,
        "Actividad": render_activity_page,
        "Configuración": render_config_page,
    }

    page_renderers.get(st.session_state.active_page, render_dashboard)()


if __name__ == "__main__":
    main()