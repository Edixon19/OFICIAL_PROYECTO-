"""
GestorPro - Gestor de Tareas con Streamlit + Supabase (PostgreSQL)
==================================================================
Versión 1.1 — Correcciones:
  · Sidebar FIJO (sin botón de colapsar — se elimina con CSS)
  · FIX recordatorios: HTML del badge se renderizaba como texto plano
  · FIX modo claro: textos de toggles, expanders, labels y
    todos los elementos que quedaban blancos sobre fondo blanco
  · Colores explícitos en TODOS los textos para que funcionen
    correctamente en modo claro Y modo oscuro

Autores: GestorPro, equipo del segundo semestre UTEDÉ
"""

import streamlit as st
import json
import uuid
import os
from datetime import datetime, date

from database import get_connection, get_cursor, init_db

# ─────────────────────────────────────────────
# CONFIGURACIÓN INICIAL
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
PRIORITIES     = ["High", "Medium", "Low"]
CATEGORIES     = ["Trabajo", "Personal", "Compras", "Diseño", "Desarrollo", "Otro"]
STATUS_OPTIONS = ["Pendiente", "Activa", "Completada"]
TEAM_ROLES     = ["Líder", "Miembro", "Editor", "Viewer"]

PRIORITY_COLORS = {"High": "#ef4444", "Medium": "#f59e0b", "Low": "#22c55e"}
CATEGORY_COLORS = {
    "Trabajo": "#3b82f6", "Personal": "#8b5cf6", "Compras": "#f59e0b",
    "Diseño": "#ec4899", "Desarrollo": "#06b6d4", "Otro": "#6b7280",
}

# ── Temas ─────────────────────────────────────
# Nota: todos los colores de texto son EXPLÍCITOS para evitar
# que hereden valores incorrectos en cada modo.
THEMES = {
    "light": {
        "--bg-main":         "#f8fafc",
        "--bg-card":         "#ffffff",
        "--bg-sidebar":      "#1a1a2e",
        "--text-primary":    "#0f172a",
        "--text-secondary":  "#475569",
        "--text-sidebar":    "#e2e8f0",
        "--border-color":    "#e2e8f0",
        "--accent-primary":  "#e55a2b",
        "--accent-secondary":"#0d9488",
        "--accent-gradient": "linear-gradient(135deg, #e55a2b, #0d9488)",
        "--hover-bg":        "#f1f5f9",
        "--input-bg":        "#ffffff",
        "--input-border":    "#cbd5e1",
        "--shadow":          "0 2px 8px rgba(0,0,0,0.08)",
        "--shadow-hover":    "0 4px 16px rgba(0,0,0,0.14)",
        "--badge-bg":        "#f1f5f9",
        "--completed-text":  "#94a3b8",
        "--expander-bg":     "#f8fafc",
        "--expander-header": "#0f172a",
        "--toggle-label":    "#0f172a",
        "--card-meta":       "#475569",
    },
    "dark": {
        "--bg-main":         "#0f172a",
        "--bg-card":         "#1e293b",
        "--bg-sidebar":      "#020617",
        "--text-primary":    "#f1f5f9",
        "--text-secondary":  "#94a3b8",
        "--text-sidebar":    "#e2e8f0",
        "--border-color":    "#334155",
        "--accent-primary":  "#e55a2b",
        "--accent-secondary":"#0d9488",
        "--accent-gradient": "linear-gradient(135deg, #e55a2b, #0d9488)",
        "--hover-bg":        "#334155",
        "--input-bg":        "#1e293b",
        "--input-border":    "#475569",
        "--shadow":          "0 2px 8px rgba(0,0,0,0.3)",
        "--shadow-hover":    "0 4px 16px rgba(0,0,0,0.5)",
        "--badge-bg":        "#334155",
        "--completed-text":  "#475569",
        "--expander-bg":     "#1e293b",
        "--expander-header": "#f1f5f9",
        "--toggle-label":    "#f1f5f9",
        "--card-meta":       "#94a3b8",
    },
}


# ══════════════════════════════════════════════
#  CAPA DE DATOS — Supabase
# ══════════════════════════════════════════════

def _exec(sql: str, params=(), fetch: str = "none"):
    conn = get_connection()
    if conn is None:
        return [] if fetch == "all" else ({} if fetch == "one" else None)
    cur = get_cursor(conn)
    if cur is None:
        return [] if fetch == "all" else ({} if fetch == "one" else None)
    try:
        cur.execute(sql, params)
        if fetch == "all":
            rows = cur.fetchall()
            conn.commit()
            return [dict(r) for r in rows]
        elif fetch == "one":
            row = cur.fetchone()
            conn.commit()
            return dict(row) if row else {}
        else:
            conn.commit()
            return True
    except Exception as e:
        conn.rollback()
        st.error(f"Error BD: {e}")
        return [] if fetch == "all" else ({} if fetch == "one" else False)
    finally:
        cur.close()


# ── TAREAS ──────────────────────────────────

def db_load_tasks() -> list:
    rows = _exec(
        "SELECT * FROM tasks ORDER BY "
        "CASE priority WHEN 'High' THEN 1 WHEN 'Medium' THEN 2 ELSE 3 END, "
        "created_at DESC",
        fetch="all",
    )
    for r in rows:
        if isinstance(r.get("tags"), str):
            try:
                r["tags"] = json.loads(r["tags"])
            except Exception:
                r["tags"] = []
        elif r.get("tags") is None:
            r["tags"] = []
        if hasattr(r.get("due_date"), "isoformat"):
            r["due_date"] = r["due_date"].isoformat()
        if hasattr(r.get("created_at"), "isoformat"):
            r["created_at"] = r["created_at"].isoformat()
    return rows


def db_add_task(title, description, priority, category, status, due_date, assignee, tags) -> bool:
    task_id = str(uuid.uuid4())
    ok = _exec(
        """INSERT INTO tasks (id,title,description,priority,category,status,
           due_date,assignee,tags,created_at) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s)""",
        (task_id, title.strip(), description.strip(), priority, category, status,
         due_date.isoformat() if due_date else date.today().isoformat(),
         assignee.strip(), json.dumps(tags, ensure_ascii=False), datetime.now().isoformat()),
    )
    if ok:
        _log_activity(assignee.strip() or "Sistema", "creó la tarea", "tarea", title.strip())
    return bool(ok)


def db_update_task(task_id: str, **kwargs) -> bool:
    if "tags" in kwargs:
        kwargs["tags"] = json.dumps(kwargs["tags"], ensure_ascii=False)
    if not kwargs:
        return False
    set_parts = [f"{k} = %s::jsonb" if k == "tags" else f"{k} = %s" for k in kwargs]
    ok = _exec(f"UPDATE tasks SET {', '.join(set_parts)} WHERE id = %s",
               list(kwargs.values()) + [task_id])
    if ok:
        _log_activity("Usuario", "actualizó la tarea", "tarea", kwargs.get("title", task_id))
    return bool(ok)


def db_delete_task(task_id: str, task_title: str = "") -> bool:
    ok = _exec("DELETE FROM tasks WHERE id = %s", (task_id,))
    if ok:
        _log_activity("Usuario", "eliminó la tarea", "tarea", task_title or task_id)
    return bool(ok)


def db_toggle_task_status(task_id: str, current_status: str, title: str = "") -> bool:
    new_status = "Activa" if current_status == "Completada" else "Completada"
    action = "completó la tarea" if new_status == "Completada" else "reactivó la tarea"
    ok = _exec("UPDATE tasks SET status = %s WHERE id = %s", (new_status, task_id))
    if ok:
        _log_activity("Usuario", action, "tarea", title)
    return bool(ok)


# ── EQUIPOS ─────────────────────────────────

def db_load_teams() -> list:
    teams = _exec("SELECT * FROM teams ORDER BY created_at DESC", fetch="all")
    for team in teams:
        if hasattr(team.get("created_at"), "isoformat"):
            team["created_at"] = team["created_at"].isoformat()
        members = _exec(
            "SELECT * FROM team_members WHERE team_id = %s ORDER BY role",
            (team["id"],), fetch="all",
        )
        for m in members:
            if hasattr(m.get("joined_at"), "isoformat"):
                m["joined_at"] = m["joined_at"].isoformat()
        team["members"] = members
    return teams


def db_create_team(name: str, description: str, leader_name: str) -> bool:
    team_id = str(uuid.uuid4())
    ok = _exec("INSERT INTO teams (id,name,description) VALUES (%s,%s,%s)",
               (team_id, name.strip(), description.strip()))
    if ok and leader_name.strip():
        _exec("INSERT INTO team_members (id,team_id,member_name,role) VALUES (%s,%s,%s,%s)",
              (str(uuid.uuid4()), team_id, leader_name.strip(), "Líder"))
        _log_activity(leader_name, "creó el equipo", "equipo", name.strip())
    return bool(ok)


def db_add_member(team_id: str, member_name: str, role: str, team_name: str = "") -> bool:
    ok = _exec("INSERT INTO team_members (id,team_id,member_name,role) VALUES (%s,%s,%s,%s)",
               (str(uuid.uuid4()), team_id, member_name.strip(), role))
    if ok:
        _log_activity("Usuario", f"agregó a {member_name} al equipo", "equipo", team_name)
    return bool(ok)


def db_update_member_role(member_id: str, new_role: str, member_name: str = "") -> bool:
    ok = _exec("UPDATE team_members SET role = %s WHERE id = %s", (new_role, member_id))
    if ok:
        _log_activity("Líder", f"cambió el rol de {member_name} a {new_role}", "equipo", "")
    return bool(ok)


def db_move_member(member_id: str, new_team_id: str, member_name: str = "", new_team_name: str = "") -> bool:
    ok = _exec("UPDATE team_members SET team_id = %s, role = 'Miembro' WHERE id = %s",
               (new_team_id, member_id))
    if ok:
        _log_activity("Líder", f"movió a {member_name} al equipo", "equipo", new_team_name)
    return bool(ok)


def db_remove_member(member_id: str, member_name: str = "", team_name: str = "") -> bool:
    ok = _exec("DELETE FROM team_members WHERE id = %s", (member_id,))
    if ok:
        _log_activity("Líder", f"removió a {member_name} del equipo", "equipo", team_name)
    return bool(ok)


def db_delete_team(team_id: str, team_name: str = "") -> bool:
    ok = _exec("DELETE FROM teams WHERE id = %s", (team_id,))
    if ok:
        _log_activity("Usuario", "eliminó el equipo", "equipo", team_name)
    return bool(ok)


# ── ACTIVIDAD ────────────────────────────────

def _log_activity(user_name: str, action: str, entity_type: str = "",
                  entity_name: str = "", detail: str = "") -> None:
    _exec("""INSERT INTO activity_log (id,user_name,action,entity_type,entity_name,detail)
             VALUES (%s,%s,%s,%s,%s,%s)""",
          (str(uuid.uuid4()), user_name, action, entity_type, entity_name, detail))


def db_load_activity(limit: int = 30) -> list:
    rows = _exec("SELECT * FROM activity_log ORDER BY created_at DESC LIMIT %s",
                 (limit,), fetch="all")
    for r in rows:
        if hasattr(r.get("created_at"), "isoformat"):
            r["created_at"] = r["created_at"].isoformat()
    return rows


# ── DATOS DEMO ───────────────────────────────

def _get_sample_tasks() -> list:
    today = date.today().isoformat()
    now   = datetime.now().isoformat()
    return [
        {"id": str(uuid.uuid4()), "title": "Diseñar interfaz de usuario",
         "description": "Crear mockups para la nueva aplicación", "priority": "High",
         "category": "Diseño", "status": "Activa", "due_date": today,
         "assignee": "Ana García", "tags": ["diseño", "UI/UX"], "created_at": now},
        {"id": str(uuid.uuid4()), "title": "Revisar documentación del proyecto",
         "description": "Actualizar la documentación técnica", "priority": "Medium",
         "category": "Trabajo", "status": "Activa", "due_date": today,
         "assignee": "", "tags": ["documentación"], "created_at": now},
        {"id": str(uuid.uuid4()), "title": "Comprar suministros de oficina",
         "description": "Papel, bolígrafos y carpetas", "priority": "Low",
         "category": "Compras", "status": "Pendiente", "due_date": today,
         "assignee": "", "tags": ["compras"], "created_at": now},
    ]


def seed_sample_data() -> None:
    row = _exec("SELECT COUNT(*) AS cnt FROM tasks", fetch="one")
    if row and int(row.get("cnt", 0)) == 0:
        for t in _get_sample_tasks():
            _exec("""INSERT INTO tasks (id,title,description,priority,category,status,
                     due_date,assignee,tags,created_at) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s)""",
                  (t["id"], t["title"], t["description"], t["priority"], t["category"],
                   t["status"], t["due_date"], t["assignee"],
                   json.dumps(t["tags"]), t["created_at"]))


# ══════════════════════════════════════════════
#  SESSION STATE
# ══════════════════════════════════════════════

def init_session_state() -> None:
    defaults = {
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

    st.session_state.tasks = db_load_tasks()
    st.session_state.teams = db_load_teams()


# ══════════════════════════════════════════════
#  CSS DINÁMICO
# ══════════════════════════════════════════════

def inject_css() -> None:
    """
    CSS global con tres objetivos principales:

    1. SIDEBAR FIJO — se elimina el botón de colapsar/expandir con CSS.
       El sidebar siempre está visible; no hay flecha ni toggle.

    2. COLORES MODO CLARO — todos los textos usan color: var(--text-primary)
       explícito para que nunca hereden el blanco del tema Streamlit por defecto.
       Se sobreescriben: expanders, toggles, labels, placeholders, tabs, info boxes.

    3. HTML EN RECORDATORIOS — este bug no es de CSS; se arregló separando
       el badge HTML en una variable Python antes del f-string principal.
    """
    theme    = THEMES["dark"] if st.session_state.dark_mode else THEMES["light"]
    css_vars = "\n".join(f"    {k}: {v};" for k, v in theme.items())

    # Color explícito para uso inline en elementos que no leen variables CSS
    tp  = theme["--text-primary"]
    ts  = theme["--text-secondary"]
    bc  = theme["--bg-card"]
    brd = theme["--border-color"]
    bg  = theme["--bg-main"]

    css = f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Sora:wght@300;400;500;600;700&display=swap');

    :root {{
{css_vars}
    }}

    /* ── Base ── */
    html, body, .stApp {{
        background-color: var(--bg-main) !important;
        font-family: 'Sora', sans-serif !important;
        color: var(--text-primary) !important;
    }}
    #MainMenu, footer, header {{ visibility: hidden; }}
    .stDeployButton {{ display: none; }}

    /* ══════════════════════════════════════════
       SIDEBAR FIJO — sin botón de colapsar
       Se oculta el control de colapsar/expandir
       para que el sidebar quede permanentemente
       visible y no haya confusión con la flecha.
    ══════════════════════════════════════════ */
    [data-testid="collapsedControl"],
    button[data-testid="collapsedControl"] {{
        display: none !important;
        visibility: hidden !important;
    }}

    section[data-testid="stSidebar"] {{
        background: var(--bg-sidebar) !important;
        border-right: 1px solid rgba(255,255,255,0.08) !important;
        min-width: 240px !important;
        max-width: 280px !important;
    }}
    /* Todos los textos del sidebar en color claro */
    section[data-testid="stSidebar"],
    section[data-testid="stSidebar"] p,
    section[data-testid="stSidebar"] span,
    section[data-testid="stSidebar"] div,
    section[data-testid="stSidebar"] label {{
        color: var(--text-sidebar) !important;
    }}
    section[data-testid="stSidebar"] .stButton > button {{
        color: white !important;
    }}

    /* ── Área principal ── */
    .main .block-container {{
        padding: 1.5rem 2rem !important;
        max-width: 100% !important;
        background: var(--bg-main) !important;
    }}

    /* ══════════════════════════════════════════
       COLORES MODO CLARO — corrección global
       Todos los elementos de texto deben usar
       var(--text-primary) o var(--text-secondary)
       explícitamente para evitar herencia de blanco.
    ══════════════════════════════════════════ */

    /* Párrafos, spans y divs genéricos */
    .main p, .main span:not(.badge), .main div:not([class*="st"]) {{
        color: var(--text-primary);
    }}

    /* Headings */
    h1, h2, h3, h4, h5, h6 {{
        color: var(--text-primary) !important;
        font-family: 'Sora', sans-serif !important;
        font-weight: 700 !important;
    }}

    /* Labels de inputs, selectbox, date, radio */
    .stTextInput > label,
    .stTextArea > label,
    .stSelectbox > label,
    .stDateInput > label,
    .stNumberInput > label,
    .stRadio > label,
    .stCheckbox > label,
    label[data-testid] {{
        color: var(--text-primary) !important;
        font-family: 'Sora', sans-serif !important;
        font-size: 0.85rem !important;
        font-weight: 500 !important;
    }}

    /* Inputs */
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea,
    .stSelectbox > div > div > div,
    .stDateInput > div > div > input {{
        background: var(--input-bg) !important;
        border: 1.5px solid var(--input-border) !important;
        border-radius: 10px !important;
        color: var(--text-primary) !important;
        font-family: 'Sora', sans-serif !important;
        padding: 0.6rem 1rem !important;
        transition: border-color 0.2s, box-shadow 0.2s;
    }}
    .stTextInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus {{
        border-color: var(--accent-primary) !important;
        box-shadow: 0 0 0 3px rgba(229,90,43,0.15) !important;
    }}
    /* Placeholder */
    .stTextInput > div > div > input::placeholder,
    .stTextArea > div > div > textarea::placeholder {{
        color: var(--text-secondary) !important;
        opacity: 1 !important;
    }}

    /* ── Toggles — FIX modo claro ── */
    div[data-testid="stToggle"] > label,
    div[data-testid="stToggle"] label,
    div[data-testid="stToggle"] p,
    div[data-testid="stToggle"] span {{
        color: var(--toggle-label) !important;
        font-family: 'Sora', sans-serif !important;
    }}

    /* ── Expanders — FIX modo claro ── */
    .streamlit-expanderHeader,
    [data-testid="stExpander"] summary,
    [data-testid="stExpander"] summary p,
    [data-testid="stExpander"] summary span {{
        background: var(--expander-bg) !important;
        color: var(--expander-header) !important;
        font-family: 'Sora', sans-serif !important;
        font-weight: 600 !important;
        border-radius: 10px !important;
    }}
    [data-testid="stExpander"] > div > div {{
        background: var(--bg-card) !important;
        border-color: var(--border-color) !important;
    }}

    /* ── Tabs — FIX modo claro ── */
    .stTabs [data-baseweb="tab-list"] {{
        background: var(--bg-card) !important;
        border-bottom: 1px solid var(--border-color) !important;
    }}
    .stTabs [data-baseweb="tab"] {{
        color: var(--text-secondary) !important;
        font-family: 'Sora', sans-serif !important;
        font-size: 0.84rem !important;
    }}
    .stTabs [aria-selected="true"] {{
        color: var(--accent-primary) !important;
        border-bottom: 2px solid var(--accent-primary) !important;
        font-weight: 600 !important;
    }}
    .stTabs [data-baseweb="tab-panel"] {{
        background: var(--bg-card) !important;
        padding: 1rem !important;
        border-radius: 0 0 10px 10px !important;
    }}

    /* ── Info / Warning / Success / Error boxes ── */
    div[data-testid="stInfo"],
    div[data-testid="stSuccess"],
    div[data-testid="stWarning"],
    div[data-testid="stError"] {{
        border-radius: 10px !important;
        font-family: 'Sora', sans-serif !important;
    }}
    div[data-testid="stInfo"] p,
    div[data-testid="stSuccess"] p,
    div[data-testid="stWarning"] p,
    div[data-testid="stError"] p {{
        color: inherit !important;
    }}

    /* ── Radio horizontal — FIX colores ── */
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
        color: var(--text-primary) !important;
    }}
    .stRadio > div > label span {{
        color: var(--text-primary) !important;
    }}

    /* ── Selectbox dropdown ── */
    .stSelectbox [data-baseweb="select"] > div {{
        background: var(--input-bg) !important;
        border-color: var(--input-border) !important;
        color: var(--text-primary) !important;
    }}
    [data-baseweb="popover"] [data-baseweb="menu"] {{
        background: var(--bg-card) !important;
    }}
    [data-baseweb="popover"] [role="option"] {{
        color: var(--text-primary) !important;
        font-family: 'Sora', sans-serif !important;
    }}
    [data-baseweb="popover"] [role="option"]:hover {{
        background: var(--hover-bg) !important;
    }}

    /* ── Botones ── */
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
        transition: opacity 0.2s, transform 0.15s !important;
    }}
    .stButton > button:hover {{
        opacity: 0.9 !important;
        transform: translateY(-1px) !important;
        box-shadow: 0 4px 14px rgba(229,90,43,0.35) !important;
    }}

    /* ── Download button ── */
    .stDownloadButton > button {{
        background: var(--accent-gradient) !important;
        color: white !important;
        border: none !important;
        border-radius: 10px !important;
        font-family: 'Sora', sans-serif !important;
        font-weight: 600 !important;
    }}

    /* ── Cards de stats ── */
    .stat-card {{
        background: var(--bg-card);
        border-radius: 14px;
        padding: 1.25rem 1.5rem;
        border: 1px solid var(--border-color);
        box-shadow: var(--shadow);
        transition: box-shadow 0.2s, transform 0.2s;
        margin-bottom: 1rem;
    }}
    .stat-card:hover {{ box-shadow: var(--shadow-hover); transform: translateY(-2px); }}
    .stat-card .stat-value {{
        font-size: 2rem; font-weight: 700;
        color: var(--text-primary); font-family: 'Sora', sans-serif;
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

    /* ── Task cards ── */
    .task-card {{
        background: var(--bg-card);
        border-radius: 14px;
        padding: 1.1rem 1.4rem;
        border: 1px solid var(--border-color);
        box-shadow: var(--shadow);
        margin-bottom: 0.7rem;
        transition: all 0.2s;
    }}
    .task-card:hover {{ box-shadow: var(--shadow-hover); border-color: rgba(229,90,43,0.3); }}
    .task-card.completed {{ opacity: 0.65; }}
    .task-card .task-title {{
        font-size: 0.98rem; font-weight: 600;
        color: var(--text-primary); font-family: 'Sora', sans-serif; margin-bottom: 0.2rem;
    }}
    .task-card.completed .task-title {{
        text-decoration: line-through; color: var(--completed-text);
    }}
    .task-card .task-desc {{
        font-size: 0.82rem; color: var(--text-secondary);
        font-family: 'Sora', sans-serif; margin-bottom: 0.6rem;
    }}
    .task-meta {{
        font-size: 0.78rem; color: var(--card-meta); font-family: 'Sora', sans-serif;
    }}

    /* ── Badges ── */
    .badge {{
        display: inline-flex; align-items: center; gap: 0.25rem;
        padding: 0.18rem 0.65rem; border-radius: 100px;
        font-size: 0.72rem; font-weight: 600; font-family: 'Sora', sans-serif;
        margin-right: 0.3rem; margin-bottom: 0.2rem;
    }}
    .badge-priority-high   {{ background: rgba(239,68,68,0.12);  color: #ef4444; border: 1px solid rgba(239,68,68,0.25); }}
    .badge-priority-medium {{ background: rgba(245,158,11,0.12); color: #d97706; border: 1px solid rgba(245,158,11,0.25); }}
    .badge-priority-low    {{ background: rgba(34,197,94,0.12);  color: #16a34a; border: 1px solid rgba(34,197,94,0.25); }}
    .badge-tag             {{ background: var(--badge-bg); color: var(--text-secondary); border: 1px solid var(--border-color); }}
    .badge-status-pendiente  {{ background: rgba(245,158,11,0.12); color: #d97706; border: 1px solid rgba(245,158,11,0.2); }}
    .badge-status-activa     {{ background: rgba(13,148,136,0.12); color: #0d9488; border: 1px solid rgba(13,148,136,0.25); }}
    .badge-status-completada {{ background: rgba(34,197,94,0.12);  color: #16a34a; border: 1px solid rgba(34,197,94,0.2); }}

    /* ── Tipografía páginas ── */
    .page-title {{
        font-size: 1.6rem; font-weight: 700;
        color: var(--text-primary); font-family: 'Sora', sans-serif;
    }}
    .page-subtitle {{
        font-size: 0.82rem; color: var(--text-secondary);
        font-family: 'Sora', sans-serif; margin-top: 0.1rem;
    }}
    .section-title {{
        font-size: 1.1rem; font-weight: 700;
        color: var(--text-primary); font-family: 'Sora', sans-serif;
        margin-bottom: 1rem; margin-top: 0.5rem;
    }}
    .task-count {{
        font-size: 0.78rem; color: var(--text-secondary);
        font-family: 'Sora', sans-serif; margin-bottom: 0.75rem;
    }}

    /* ── Formularios ── */
    .form-container {{
        background: var(--bg-card); border-radius: 16px; padding: 1.75rem;
        border: 1px solid var(--border-color); box-shadow: var(--shadow); margin-bottom: 1.5rem;
    }}
    .form-title {{
        font-size: 1.1rem; font-weight: 700; color: var(--text-primary);
        font-family: 'Sora', sans-serif; margin-bottom: 1.25rem;
        padding-bottom: 0.75rem; border-bottom: 1px solid var(--border-color);
    }}

    /* ── Confirmación borrado ── */
    .confirm-delete-box {{
        background: rgba(239,68,68,0.08); border: 1px solid rgba(239,68,68,0.3);
        border-radius: 10px; padding: 0.75rem 1rem; margin: 0.5rem 0;
        color: var(--text-primary) !important; font-family: 'Sora', sans-serif;
    }}

    /* ── Actividad ── */
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

    /* ── Recordatorios ── */
    .reminder-card {{
        background: var(--bg-card); border-radius: 14px; padding: 1rem 1.25rem;
        border: 1px solid var(--border-color); box-shadow: var(--shadow);
        margin-bottom: 0.6rem; display: flex; align-items: center;
        gap: 1rem; transition: all 0.2s;
    }}
    .reminder-card:hover {{ box-shadow: var(--shadow-hover); transform: translateX(3px); }}
    .reminder-title {{
        font-weight: 600; font-size: 0.9rem;
        color: var(--text-primary); font-family: 'Sora', sans-serif;
    }}
    .reminder-desc {{
        font-size: 0.78rem; color: var(--text-secondary); font-family: 'Sora', sans-serif;
    }}
    .reminder-meta {{
        margin-top: 0.3rem; font-size: 0.76rem;
        color: var(--text-secondary); font-family: 'Sora', sans-serif;
    }}

    /* ── Equipos ── */
    .team-card {{
        background: var(--bg-card); border-radius: 14px; padding: 1.25rem 1.5rem;
        border: 1px solid var(--border-color); box-shadow: var(--shadow);
        margin-bottom: 1rem; transition: all 0.2s;
    }}
    .team-card:hover {{ box-shadow: var(--shadow-hover); }}
    .team-name {{
        font-size: 1.1rem; font-weight: 700;
        color: var(--text-primary); font-family: 'Sora', sans-serif;
    }}
    .team-desc {{
        font-size: 0.8rem; color: var(--text-secondary); font-family: 'Sora', sans-serif;
    }}

    /* ── DB status ── */
    .db-status-ok {{
        font-size: 0.72rem; color: #16a34a; font-family: 'Sora', sans-serif;
        display: flex; align-items: center; gap: 0.3rem; padding: 0.3rem 0.75rem;
        background: rgba(34,197,94,0.15); border-radius: 20px;
        width: fit-content; margin-bottom: 0.75rem;
    }}
    .db-status-err {{
        font-size: 0.72rem; color: #ef4444; font-family: 'Sora', sans-serif;
        display: flex; align-items: center; gap: 0.3rem; padding: 0.3rem 0.75rem;
        background: rgba(239,68,68,0.1); border-radius: 20px;
        width: fit-content; margin-bottom: 0.75rem;
    }}

    /* ── Scrollbar ── */
    ::-webkit-scrollbar {{ width: 6px; height: 6px; }}
    ::-webkit-scrollbar-track {{ background: var(--bg-main); }}
    ::-webkit-scrollbar-thumb {{ background: var(--border-color); border-radius: 3px; }}
    ::-webkit-scrollbar-thumb:hover {{ background: var(--accent-primary); }}

    /* ── Sidebar logo ── */
    .sidebar-logo {{
        display: flex; align-items: center; gap: 0.75rem;
        padding: 0.5rem 0 1.5rem 0;
        border-bottom: 1px solid rgba(255,255,255,0.08); margin-bottom: 1.25rem;
    }}
    .logo-icon {{
        width: 40px; height: 40px; background: var(--accent-gradient);
        border-radius: 10px; display: flex; align-items: center; justify-content: center;
        font-weight: 700; font-size: 1rem; color: white; font-family: 'Sora', sans-serif;
    }}
    .logo-text {{ font-size: 1.1rem; font-weight: 700; color: #f1f5f9; font-family: 'Sora', sans-serif; }}
    .logo-sub  {{ font-size: 0.7rem; color: #94a3b8; font-family: 'Sora', sans-serif; }}

    /* ── Configuración — colores modo claro ── */
    .config-label {{
        font-size: 0.85rem; font-weight: 500;
        color: var(--text-primary); font-family: 'Sora', sans-serif;
        margin-bottom: 0.25rem;
    }}
    .config-hint {{
        font-size: 0.8rem; color: var(--text-secondary);
        font-family: 'Sora', sans-serif; margin-top: 0.5rem;
    }}
    .config-info {{
        font-family: 'Sora', sans-serif; font-size: 0.85rem;
        color: var(--text-primary); line-height: 1.7;
    }}
    .config-info b {{ color: var(--text-primary); }}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)


# ══════════════════════════════════════════════
#  HELPERS CRUD
# ══════════════════════════════════════════════

def add_task(title, description, priority, category, status, due_date, assignee, tags):
    if db_add_task(title, description, priority, category, status, due_date, assignee, tags):
        st.session_state.tasks = db_load_tasks()


def update_task(task_id, **kwargs):
    if db_update_task(task_id, **kwargs):
        st.session_state.tasks = db_load_tasks()


def delete_task(task_id, task_title=""):
    if db_delete_task(task_id, task_title):
        st.session_state.tasks = db_load_tasks()


def toggle_task_status(task_id, current_status, title=""):
    if db_toggle_task_status(task_id, current_status, title):
        st.session_state.tasks = db_load_tasks()


def get_filtered_tasks(status_filter="Todas", category_filter="Todas", search="") -> list:
    prio  = {"High": 0, "Medium": 1, "Low": 2}
    tasks = st.session_state.tasks.copy()
    if status_filter != "Todas":
        tasks = [t for t in tasks if t["status"] == status_filter]
    if category_filter != "Todas":
        tasks = [t for t in tasks if t["category"] == category_filter]
    if search:
        s = search.lower()
        tasks = [t for t in tasks if s in t["title"].lower()
                 or s in t.get("description","").lower()
                 or s in " ".join(t.get("tags",[])).lower()]
    return sorted(tasks, key=lambda x: prio.get(x["priority"], 99))


def get_stats() -> dict:
    tasks     = st.session_state.tasks
    total     = len(tasks)
    completed = sum(1 for t in tasks if t["status"] == "Completada")
    pending   = sum(1 for t in tasks if t["status"] == "Pendiente")
    active    = sum(1 for t in tasks if t["status"] == "Activa")
    return {"total": total, "completed": completed, "pending": pending,
            "active": active,
            "completion_rate": round(completed / total * 100) if total else 0}


# ══════════════════════════════════════════════
#  COMPONENTES UI
# ══════════════════════════════════════════════

def render_priority_badge(priority: str) -> str:
    icons = {"High": "🔴", "Medium": "🟡", "Low": "🟢"}
    return (f'<span class="badge badge-priority-{priority.lower()}">'
            f'{icons.get(priority,"⚪")} {priority}</span>')


def render_status_badge(status: str) -> str:
    icons = {"Pendiente": "⏳", "Activa": "🔵", "Completada": "✅"}
    return (f'<span class="badge badge-status-{status.lower()}">'
            f'{icons.get(status,"")} {status}</span>')


def render_tag_badge(tag: str) -> str:
    return f'<span class="badge badge-tag">#{tag}</span>'


def render_role_badge(role: str) -> str:
    colors = {"Líder": "#e55a2b", "Editor": "#0d9488", "Viewer": "#6b7280", "Miembro": "#3b82f6"}
    color  = colors.get(role, "#6b7280")
    return (f'<span class="badge" style="background:rgba(0,0,0,0.06);'
            f'color:{color};border:1px solid {color}40;">{role}</span>')


def _hex_to_rgb(hex_color: str):
    h = hex_color.lstrip("#")
    try:
        return int(h[0:2],16), int(h[2:4],16), int(h[4:6],16)
    except Exception:
        return 0, 0, 0


def _time_ago(created_at_str: str) -> str:
    try:
        dt   = datetime.fromisoformat(str(created_at_str)[:19])
        diff = int((datetime.now() - dt).total_seconds())
        if diff < 60:    return f"Hace {diff} seg"
        if diff < 3600:  return f"Hace {diff//60} min"
        if diff < 86400: return f"Hace {diff//3600} h"
        return f"Hace {diff//86400} días"
    except Exception:
        return "Recientemente"


def render_task_card(task: dict) -> None:
    is_completed = task["status"] == "Completada"
    card_class   = "task-card completed" if is_completed else "task-card"
    tags_html    = " ".join(render_tag_badge(t) for t in task.get("tags", []))
    due_str      = f"📅 {task.get('due_date','')}" if task.get("due_date") else ""
    asgn_str     = f"👤 {task['assignee']}"         if task.get("assignee") else ""
    meta_html    = " &nbsp;·&nbsp; ".join(p for p in [due_str, asgn_str] if p)

    st.markdown(f"""
    <div class="{card_class}">
        <div class="task-title">{task['title']}</div>
        <div class="task-desc">{task.get('description','')}</div>
        <div style="display:flex;flex-wrap:wrap;align-items:center;gap:0.3rem;margin-bottom:0.4rem;">
            {render_priority_badge(task['priority'])}{render_status_badge(task['status'])}
        </div>
        <div style="margin-bottom:0.3rem;">{tags_html}</div>
        <div class="task-meta">{meta_html}</div>
    </div>
    """, unsafe_allow_html=True)

    c_check, c_edit, c_del, _ = st.columns([1, 1, 1, 4])
    with c_check:
        lbl = "↩ Reactivar" if is_completed else "✓ Completar"
        if st.button(lbl, key=f"toggle_{task['id']}", use_container_width=True):
            toggle_task_status(task["id"], task["status"], task["title"])
            st.rerun()
    with c_edit:
        if st.button("✏️ Editar", key=f"edit_btn_{task['id']}", use_container_width=True):
            st.session_state.editing_task_id = (
                None if st.session_state.editing_task_id == task["id"] else task["id"])
            st.rerun()
    with c_del:
        if st.button("🗑️ Eliminar", key=f"delete_btn_{task['id']}", use_container_width=True):
            st.session_state.confirm_delete_id = task["id"]
            st.rerun()

    if st.session_state.confirm_delete_id == task["id"]:
        st.markdown('<div class="confirm-delete-box">⚠️ ¿Confirmar eliminación? No se puede deshacer.</div>',
                    unsafe_allow_html=True)
        cy, cn = st.columns(2)
        with cy:
            if st.button("Sí, eliminar", key=f"confirm_yes_{task['id']}", use_container_width=True):
                delete_task(task["id"], task["title"])
                st.session_state.confirm_delete_id = None
                st.success("Tarea eliminada.")
                st.rerun()
        with cn:
            if st.button("Cancelar", key=f"confirm_no_{task['id']}", use_container_width=True):
                st.session_state.confirm_delete_id = None
                st.rerun()

    if st.session_state.editing_task_id == task["id"]:
        render_edit_form(task)

    st.markdown("<div style='height:0.25rem'></div>", unsafe_allow_html=True)


def render_edit_form(task: dict) -> None:
    st.markdown('<div class="form-container"><div class="form-title">✏️ Editar Tarea</div>',
                unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        nt   = st.text_input("Título *", value=task["title"], key=f"edit_title_{task['id']}")
        nd   = st.text_area("Descripción", value=task.get("description",""),
                             key=f"edit_desc_{task['id']}", height=80)
        na   = st.text_input("Asignado a", value=task.get("assignee",""),
                              key=f"edit_assignee_{task['id']}")
    with c2:
        np_  = st.selectbox("Prioridad", PRIORITIES,
                             index=PRIORITIES.index(task["priority"]) if task["priority"] in PRIORITIES else 0,
                             key=f"edit_priority_{task['id']}")
        nc   = st.selectbox("Categoría", CATEGORIES,
                             index=CATEGORIES.index(task["category"]) if task["category"] in CATEGORIES else 0,
                             key=f"edit_category_{task['id']}")
        ns   = st.selectbox("Estado", STATUS_OPTIONS,
                             index=STATUS_OPTIONS.index(task["status"]) if task["status"] in STATUS_OPTIONS else 0,
                             key=f"edit_status_{task['id']}")
        try:
            cur_date = date.fromisoformat(task.get("due_date","")) if task.get("due_date") else date.today()
        except (ValueError, TypeError):
            cur_date = date.today()
        ndate = st.date_input("Fecha límite", value=cur_date, key=f"edit_date_{task['id']}")
    tags_str = st.text_input("Etiquetas (coma)", value=", ".join(task.get("tags",[])),
                              key=f"edit_tags_{task['id']}")
    cs, cc = st.columns([1, 3])
    with cs:
        if st.button("💾 Guardar", key=f"save_{task['id']}", use_container_width=True):
            if not nt.strip():
                st.error("El título es obligatorio.")
            else:
                update_task(task["id"], title=nt.strip(), description=nd.strip(),
                            priority=np_, category=nc, status=ns,
                            due_date=ndate.isoformat(), assignee=na.strip(),
                            tags=[t.strip() for t in tags_str.split(",") if t.strip()])
                st.session_state.editing_task_id = None
                st.success("✅ Tarea actualizada.")
                st.rerun()
    with cc:
        if st.button("Cancelar", key=f"cancel_edit_{task['id']}"):
            st.session_state.editing_task_id = None
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)


def render_new_task_form() -> None:
    st.markdown('<div class="form-container"><div class="form-title">➕ Nueva Tarea</div>',
                unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        title    = st.text_input("Título *", placeholder="¿Qué necesitas hacer?", key="new_title")
        desc     = st.text_area("Descripción", placeholder="Añade más detalles...",
                                 key="new_desc", height=90)
        assignee = st.text_input("Asignado a", placeholder="Nombre del responsable",
                                  key="new_assignee")
    with c2:
        priority = st.selectbox("Prioridad", PRIORITIES, key="new_priority")
        category = st.selectbox("Categoría", CATEGORIES, key="new_category")
        status   = st.selectbox("Estado inicial", STATUS_OPTIONS, key="new_status")
        due_date = st.date_input("Fecha límite", value=date.today(), key="new_date")
    tags_input = st.text_input("Etiquetas (separadas por coma)",
                                placeholder="ej: diseño, urgente", key="new_tags")
    cb, cc, _ = st.columns([1, 1, 4])
    with cb:
        if st.button("✅ Crear Tarea", key="btn_create_task", use_container_width=True):
            if not title.strip():
                st.error("⚠️ El título es obligatorio.")
            else:
                tags = [t.strip() for t in tags_input.split(",") if t.strip()]
                add_task(title, desc, priority, category, status, due_date, assignee, tags)
                st.session_state.show_new_task_form = False
                st.success(f"✅ Tarea '{title.strip()}' creada.")
                st.rerun()
    with cc:
        if st.button("Cancelar", key="btn_cancel_new"):
            st.session_state.show_new_task_form = False
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)


# ══════════════════════════════════════════════
#  SIDEBAR
# ══════════════════════════════════════════════

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

        db_html = (
            '<div class="db-status-ok">🟢 Supabase conectado</div>'
            if st.session_state.db_ok
            else '<div class="db-status-err">🔴 Sin conexión BD</div>'
        )
        st.markdown(db_html, unsafe_allow_html=True)

        for icon, page in [
            ("📊","Dashboard"), ("✅","Tareas"), ("📅","Calendario"),
            ("👥","Equipo"),    ("🔔","Recordatorios"), ("⚡","Actividad"),
        ]:
            if st.button(f"{icon}  {page}", key=f"nav_{page}", use_container_width=True):
                st.session_state.active_page        = page
                st.session_state.show_new_task_form = False
                st.session_state.show_new_team_form = False
                st.session_state.editing_task_id    = None
                st.session_state.confirm_delete_id  = None
                st.session_state.managing_team_id   = None
                st.rerun()

        st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
        st.markdown("<div style='height:1px;background:rgba(255,255,255,0.08);margin-bottom:0.75rem;'></div>",
                    unsafe_allow_html=True)

        # Toggle modo oscuro — sidebar
        dark = st.toggle("🌙  Modo Oscuro", value=st.session_state.dark_mode, key="sidebar_dark_toggle")
        if dark != st.session_state.dark_mode:
            st.session_state.dark_mode = dark
            st.rerun()

        if st.button("⚙️  Configuración", key="nav_config", use_container_width=True):
            st.session_state.active_page = "Configuración"
            st.rerun()

        stats = get_stats()
        st.markdown(f"""
        <div style="margin-top:0.75rem;background:rgba(255,255,255,0.04);border-radius:12px;
                    padding:1rem;border:1px solid rgba(255,255,255,0.07);">
            <div style="font-size:0.75rem;color:#94a3b8;font-family:'Sora',sans-serif;
                        margin-bottom:0.6rem;font-weight:600;letter-spacing:0.05em;text-transform:uppercase;">
                Resumen Rápido</div>
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


# ══════════════════════════════════════════════
#  PÁGINAS
# ══════════════════════════════════════════════

def render_dashboard() -> None:
    tp = THEMES["dark"]["--text-primary"] if st.session_state.dark_mode else THEMES["light"]["--text-primary"]
    ts = THEMES["dark"]["--text-secondary"] if st.session_state.dark_mode else THEMES["light"]["--text-secondary"]

    st.markdown(f"""
    <div style="margin-bottom:1.5rem;">
        <div style="font-size:1.5rem;font-weight:700;color:{tp};font-family:'Sora',sans-serif;">
            Resumen de Productividad</div>
        <div style="font-size:0.8rem;color:{ts};font-family:'Sora',sans-serif;">
            Actualizado en tiempo real desde Supabase</div>
    </div>
    """, unsafe_allow_html=True)

    qa1, qa2, qa3, qa4 = st.columns(4)
    for col, emoji, bg, label, sub in [
        (qa1,"🟠","#fff3ee","Nueva Tarea","Crear tarea rápida"),
        (qa2,"🟢","#eefbf7","Vista Rápida","Tareas urgentes"),
        (qa3,"🟡","#fffbea","Invitar Equipo","Agregar miembros"),
        (qa4,"🔵","#eef4ff","Nuevo Equipo","Iniciar equipo"),
    ]:
        with col:
            st.markdown(f"""
            <div style="background:var(--bg-card);border-radius:14px;padding:1.25rem;
                        border:1px solid var(--border-color);box-shadow:var(--shadow);
                        text-align:center;margin-bottom:0.5rem;min-height:90px;
                        display:flex;flex-direction:column;align-items:center;justify-content:center;gap:0.4rem;">
                <div style="width:36px;height:36px;border-radius:9px;background:{bg};
                            display:flex;align-items:center;justify-content:center;font-size:1.1rem;">{emoji}</div>
                <div style="font-size:0.82rem;font-weight:600;color:var(--text-primary);font-family:'Sora',sans-serif;">{label}</div>
                <div style="font-size:0.72rem;color:var(--text-secondary);font-family:'Sora',sans-serif;">{sub}</div>
            </div>
            """, unsafe_allow_html=True)

    with qa1:
        if st.button("+ Crear tarea", key="dash_new_task", use_container_width=True):
            st.session_state.active_page        = "Tareas"
            st.session_state.show_new_task_form = True
            st.rerun()
    with qa4:
        if st.button("+ Crear equipo", key="dash_new_team", use_container_width=True):
            st.session_state.active_page        = "Equipo"
            st.session_state.show_new_team_form = True
            st.rerun()

    stats = get_stats()
    s1, s2, s3, s4 = st.columns(4)
    for col, icon, bg, val, lbl, delta, pos in [
        (s1,"📋","#fff3ee",stats["completed"],"Completadas",f"▲ +{stats['completed']} tareas",True),
        (s2,"⏳","#fff8ee",stats["pending"],"Pendientes","▼ Por completar",False),
        (s3,"🔥","#eefbf7",stats["active"],"Tareas activas","▲ En progreso",True),
        (s4,"🎯","#eef4ff",f"{stats['completion_rate']}%","Tasa finalización","▲ Tiempo real",True),
    ]:
        with col:
            cls = "positive" if pos else "negative"
            st.markdown(
                f'<div class="stat-card">'
                f'<div class="stat-icon" style="background:{bg};">{icon}</div>'
                f'<div class="stat-value">{val}</div>'
                f'<div class="stat-label">{lbl}</div>'
                f'<div class="stat-delta {cls}">{delta}</div></div>',
                unsafe_allow_html=True)

    st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
    col_chart, col_dist = st.columns(2)

    with col_chart:
        st.markdown('<div class="section-title">📈 Tareas por Categoría</div>', unsafe_allow_html=True)
        counts = {}
        for t in st.session_state.tasks:
            counts[t.get("category","Otro")] = counts.get(t.get("category","Otro"), 0) + 1
        if counts:
            import pandas as pd
            st.bar_chart(
                pd.DataFrame(list(counts.items()), columns=["Categoría","Tareas"]).set_index("Categoría"),
                color="#e55a2b", height=220)
        else:
            st.info("No hay datos.")

    with col_dist:
        st.markdown('<div class="section-title">🍩 Distribución por Estado</div>', unsafe_allow_html=True)
        total = stats["total"] or 1
        for st_name, count, color in [
            ("Completada", stats["completed"], "#22c55e"),
            ("Activa",     stats["active"],    "#0d9488"),
            ("Pendiente",  stats["pending"],   "#f59e0b"),
        ]:
            pct = round(count / total * 100)
            st.markdown(f"""
            <div style="margin-bottom:0.6rem;">
                <div style="display:flex;justify-content:space-between;font-size:0.82rem;
                            font-family:'Sora',sans-serif;color:var(--text-primary);margin-bottom:0.25rem;">
                    <span>{st_name}</span><span style="font-weight:600;">{count} ({pct}%)</span>
                </div>
                <div style="height:8px;background:var(--border-color);border-radius:4px;overflow:hidden;">
                    <div style="height:100%;width:{pct}%;background:{color};border-radius:4px;"></div>
                </div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown('<div class="section-title">📋 Tareas Recientes</div>', unsafe_allow_html=True)
    for task in sorted(st.session_state.tasks, key=lambda x: x.get("created_at",""), reverse=True)[:4]:
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
        st.markdown('<div class="page-subtitle">Gestiona y organiza todas tus tareas</div>',
                    unsafe_allow_html=True)
    with col_btn:
        st.markdown("<div style='height:0.4rem'></div>", unsafe_allow_html=True)
        if st.button("➕ Nueva Tarea", key="open_new_task", use_container_width=True):
            st.session_state.show_new_task_form = not st.session_state.show_new_task_form
            st.rerun()

    st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
    if st.session_state.show_new_task_form:
        render_new_task_form()

    search = st.text_input("🔍 Buscar tareas...", value=st.session_state.search_query,
                           placeholder="Buscar por título, descripción o etiquetas...",
                           key="search_input")
    if search != st.session_state.search_query:
        st.session_state.search_query = search

    cf1, cf2 = st.columns(2)
    with cf1:
        status_filter = st.radio("Estado", ["Todas","Activa","Pendiente","Completada"],
                                  horizontal=True, key="status_filter_radio")
    with cf2:
        category_filter = st.selectbox("Categoría", ["Todas"]+CATEGORIES,
                                        key="category_filter_select")

    filtered  = get_filtered_tasks(status_filter, category_filter, st.session_state.search_query)
    total     = len(st.session_state.tasks)
    completed = sum(1 for t in st.session_state.tasks if t["status"] == "Completada")
    st.markdown(
        f'<div class="task-count">{len(filtered)} encontradas &nbsp;·&nbsp; '
        f'{total} total &nbsp;·&nbsp; {completed} completadas</div>',
        unsafe_allow_html=True)

    if not filtered:
        st.markdown("""
        <div style="text-align:center;padding:3rem;color:var(--text-secondary);font-family:'Sora',sans-serif;">
            <div style="font-size:2.5rem;margin-bottom:0.75rem;">📭</div>
            <div style="font-size:1rem;font-weight:500;">No se encontraron tareas</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        for task in filtered:
            render_task_card(task)


def render_calendar_page() -> None:
    st.markdown('<div class="page-title">📅 Calendario</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="page-subtitle">Vista de {date.today().strftime("%B %Y")}</div>',
                unsafe_allow_html=True)
    st.markdown("<div style='height:0.75rem'></div>", unsafe_allow_html=True)

    tasks_by_date: dict = {}
    for task in st.session_state.tasks:
        dd = task.get("due_date","")
        if dd:
            tasks_by_date.setdefault(dd, []).append(task)

    st.markdown('<div class="section-title">Próximas tareas</div>', unsafe_allow_html=True)
    if not tasks_by_date:
        st.info("No hay tareas con fechas asignadas.")
        return

    for date_str in sorted(tasks_by_date.keys()):
        try:
            d = date.fromisoformat(date_str)
            display = d.strftime("%d de %B, %Y")
        except Exception:
            display = date_str
        is_today = date_str == date.today().isoformat()
        st.markdown(f"""
        <div style="font-size:0.88rem;font-weight:700;color:var(--text-primary);
                    font-family:'Sora',sans-serif;margin:1rem 0 0.5rem;
                    padding-left:0.5rem;border-left:3px solid var(--accent-primary);">
            {display}{"  🔵 HOY" if is_today else ""}
        </div>
        """, unsafe_allow_html=True)
        for task in tasks_by_date[date_str]:
            cat_color = CATEGORY_COLORS.get(task["category"],"#6b7280")
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
    col_h, col_btn = st.columns([3, 1])
    with col_h:
        st.markdown('<div class="page-title">👥 Equipos</div>', unsafe_allow_html=True)
        st.markdown('<div class="page-subtitle">Crea y gestiona tus equipos de trabajo</div>',
                    unsafe_allow_html=True)
    with col_btn:
        st.markdown("<div style='height:0.4rem'></div>", unsafe_allow_html=True)
        if st.button("➕ Nuevo Equipo", key="open_new_team", use_container_width=True):
            st.session_state.show_new_team_form = not st.session_state.show_new_team_form
            st.rerun()

    st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)

    if st.session_state.show_new_team_form:
        st.markdown('<div class="form-container"><div class="form-title">🏗️ Crear Nuevo Equipo</div>',
                    unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            team_name   = st.text_input("Nombre del equipo *",
                                         placeholder="ej: Equipo Frontend", key="new_team_name")
            team_desc   = st.text_area("Descripción",
                                        placeholder="¿Cuál es el propósito?",
                                        key="new_team_desc", height=80)
        with c2:
            leader_name = st.text_input("Tu nombre (serás el Líder) *",
                                         placeholder="ej: Ana García", key="new_team_leader")
            st.markdown("""
            <div style="background:rgba(229,90,43,0.08);border-radius:10px;padding:0.75rem 1rem;
                        border:1px solid rgba(229,90,43,0.2);margin-top:0.5rem;">
                <div style="font-size:0.8rem;color:var(--text-primary);font-family:'Sora',sans-serif;font-weight:600;">
                    📌 Roles disponibles:</div>
                <div style="font-size:0.75rem;color:var(--text-secondary);font-family:'Sora',sans-serif;margin-top:0.3rem;">
                    🟠 <b>Líder</b>: Gestiona equipo · 🔵 <b>Miembro</b>: Participa<br>
                    🟢 <b>Editor</b>: Edita tareas · ⚪ <b>Viewer</b>: Solo lectura</div>
            </div>
            """, unsafe_allow_html=True)
        cs, cc, _ = st.columns([1, 1, 3])
        with cs:
            if st.button("✅ Crear Equipo", key="btn_create_team", use_container_width=True):
                if not team_name.strip():
                    st.error("El nombre del equipo es obligatorio.")
                elif not leader_name.strip():
                    st.error("Debes ingresar tu nombre como líder.")
                else:
                    if db_create_team(team_name, team_desc, leader_name):
                        st.session_state.show_new_team_form = False
                        st.session_state.teams = db_load_teams()
                        st.success(f"✅ Equipo '{team_name}' creado.")
                        st.rerun()
        with cc:
            if st.button("Cancelar", key="btn_cancel_team"):
                st.session_state.show_new_team_form = False
                st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    teams = st.session_state.teams
    if not teams:
        st.markdown("""
        <div style="text-align:center;padding:3rem;color:var(--text-secondary);font-family:'Sora',sans-serif;">
            <div style="font-size:2.5rem;margin-bottom:0.75rem;">👥</div>
            <div style="font-size:1rem;font-weight:500;">No hay equipos creados</div>
        </div>
        """, unsafe_allow_html=True)
        return

    avatar_colors = ["#e55a2b","#0d9488","#8b5cf6","#f59e0b","#3b82f6","#ec4899"]

    for team in teams:
        members = team.get("members", [])
        leader  = next((m for m in members if m["role"]=="Líder"), None)

        st.markdown(f"""
        <div class="team-card">
            <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:0.75rem;">
                <div>
                    <div class="team-name">{team['name']}</div>
                    <div class="team-desc">{team.get('description','Sin descripción')}</div>
                </div>
                <div style="font-size:0.75rem;color:var(--text-secondary);font-family:'Sora',sans-serif;
                            text-align:right;flex-shrink:0;">
                    👑 Líder: {leader['member_name'] if leader else 'Sin líder'}<br>
                    <span style="color:var(--accent-primary);font-weight:600;">{len(members)} miembros</span>
                </div>
            </div>
            <div style="display:flex;flex-wrap:wrap;gap:0.4rem;margin-bottom:0.5rem;">
        """, unsafe_allow_html=True)

        for i, m in enumerate(members):
            color    = avatar_colors[i % len(avatar_colors)]
            initials = "".join(p[0].upper() for p in m["member_name"].split()[:2])
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

        col_manage, col_del_team, _ = st.columns([1, 1, 4])
        with col_manage:
            open_lbl = "🔽 Cerrar" if st.session_state.managing_team_id == team["id"] else "⚙️ Gestionar"
            if st.button(open_lbl, key=f"manage_{team['id']}", use_container_width=True):
                st.session_state.managing_team_id = (
                    None if st.session_state.managing_team_id == team["id"] else team["id"])
                st.rerun()
        with col_del_team:
            if st.button("🗑️ Eliminar equipo", key=f"del_team_{team['id']}", use_container_width=True):
                st.session_state.confirm_delete_team_id = team["id"]
                st.rerun()

        if st.session_state.get("confirm_delete_team_id") == team["id"]:
            st.markdown('<div class="confirm-delete-box">⚠️ ¿Eliminar el equipo y todos sus miembros?</div>',
                        unsafe_allow_html=True)
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

        if st.session_state.managing_team_id == team["id"]:
            st.markdown("""
            <div style="background:var(--bg-card);border-radius:14px;padding:1.25rem;
                        border:1px solid var(--border-color);margin-top:0.5rem;margin-bottom:0.5rem;">
            """, unsafe_allow_html=True)
            tab_add, tab_manage = st.tabs(["➕ Agregar miembro", "🔧 Gestionar miembros"])

            with tab_add:
                cnm, cnr, cnb = st.columns([2, 1, 1])
                with cnm:
                    new_member_name = st.text_input("Nombre del miembro",
                                                     placeholder="ej: Carlos Ruiz",
                                                     key=f"new_member_{team['id']}")
                with cnr:
                    new_member_role = st.selectbox("Rol", TEAM_ROLES,
                                                    key=f"new_member_role_{team['id']}")
                with cnb:
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
                    other_teams = [t for t in st.session_state.teams if t["id"] != team["id"]]
                    for m in members:
                        c_name, c_role, c_move, c_rem = st.columns([2, 1, 2, 1])
                        with c_name:
                            st.markdown(f"""
                            <div style="padding-top:0.5rem;font-size:0.88rem;font-weight:600;
                                        color:var(--text-primary);font-family:'Sora',sans-serif;">
                                {m['member_name']}</div>
                            """, unsafe_allow_html=True)
                        with c_role:
                            cur_idx  = TEAM_ROLES.index(m["role"]) if m["role"] in TEAM_ROLES else 1
                            new_role = st.selectbox("Rol", TEAM_ROLES, index=cur_idx,
                                                     key=f"role_sel_{m['id']}",
                                                     label_visibility="collapsed")
                            if new_role != m["role"]:
                                if st.button("✓", key=f"save_role_{m['id']}", help="Guardar rol"):
                                    db_update_member_role(m["id"], new_role, m["member_name"])
                                    st.session_state.teams = db_load_teams()
                                    st.rerun()
                        with c_move:
                            if other_teams:
                                target_name = st.selectbox(
                                    "Mover a", [t["name"] for t in other_teams],
                                    key=f"move_target_{m['id']}", label_visibility="collapsed")
                                if st.button("↗ Mover", key=f"move_member_{m['id']}", use_container_width=True):
                                    target = next(t for t in other_teams if t["name"]==target_name)
                                    if db_move_member(m["id"], target["id"], m["member_name"], target["name"]):
                                        st.session_state.teams = db_load_teams()
                                        st.success(f"{m['member_name']} movido a {target['name']}.")
                                        st.rerun()
                            else:
                                st.markdown(
                                    "<div style='font-size:0.75rem;color:var(--text-secondary);"
                                    "padding-top:0.5rem;'>Sin otros equipos</div>",
                                    unsafe_allow_html=True)
                        with c_rem:
                            if st.button("✕", key=f"remove_member_{m['id']}",
                                          help=f"Remover a {m['member_name']}"):
                                if db_remove_member(m["id"], m["member_name"], team["name"]):
                                    st.session_state.teams = db_load_teams()
                                    st.success(f"{m['member_name']} removido.")
                                    st.rerun()
                        st.markdown(
                            "<div style='height:0.1rem;background:var(--border-color);margin:0.3rem 0;'></div>",
                            unsafe_allow_html=True)

            st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)


def render_reminders_page() -> None:
    """
    FIX: El bug del HTML crudo se producía porque render_priority_badge()
    retorna un string HTML y al usarlo dentro de otro f-string con
    unsafe_allow_html=True, Streamlit a veces lo escapa si el string
    exterior no cierra correctamente los tags.

    Solución: separar cada tarjeta en DOS llamadas st.markdown:
      1. La parte de texto/layout (sin el badge de prioridad)
      2. El badge por separado, o mejor: usar st.columns para separar
         los elementos y evitar que el HTML anidado se escape.
    """
    col_h, col_btn = st.columns([3, 1])
    with col_h:
        st.markdown('<div class="page-title">🔔 Recordatorios</div>', unsafe_allow_html=True)
    with col_btn:
        st.markdown("<div style='height:0.4rem'></div>", unsafe_allow_html=True)
        if st.button("➕ Nueva Tarea", key="new_reminder_btn", use_container_width=True):
            st.session_state.active_page        = "Tareas"
            st.session_state.show_new_task_form = True
            st.rerun()

    st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
    reminders = sorted([t for t in st.session_state.tasks if t.get("due_date")],
                       key=lambda x: x.get("due_date",""))
    if not reminders:
        st.info("No tienes recordatorios configurados.")
        return

    today_str = date.today().isoformat()

    for task in reminders:
        dd         = task.get("due_date","")
        is_today   = dd == today_str
        is_overdue = dd < today_str and task["status"] != "Completada"

        border     = "#ef4444" if is_overdue else ("#f59e0b" if is_today else "var(--border-color)")
        alarm_icon = "🚨" if is_overdue else ("⏰" if is_today else "🔔")
        cat        = task.get("category","")

        # ── Etiquetas de alerta (solo texto, sin HTML externo) ──
        alert_txt = ""
        if is_overdue:
            alert_txt = "  🔴 VENCIDA"
        elif is_today:
            alert_txt = "  🟡 HOY"

        # ── Layout: icono | contenido | prioridad ──
        # Se usan 3 columnas para evitar anidar HTML de badge dentro de otro bloque HTML,
        # que era la causa del renderizado como texto plano.
        col_icon, col_body, col_badge = st.columns([1, 8, 2])

        with col_icon:
            st.markdown(f"""
            <div style="display:flex;align-items:center;justify-content:center;
                        height:100%;padding-top:0.5rem;font-size:1.4rem;">{alarm_icon}</div>
            """, unsafe_allow_html=True)

        with col_body:
            # Construir badge de categoría como HTML simple sin funciones externas
            cat_html = (f'<span class="badge badge-tag">{cat}</span>' if cat else "")
            st.markdown(f"""
            <div style="border-left:3px solid {border};padding-left:0.75rem;
                        padding-top:0.25rem;padding-bottom:0.25rem;">
                <div class="reminder-title">{task['title']}</div>
                <div class="reminder-desc">{task.get('description','')}</div>
                <div class="reminder-meta">
                    📅 {dd} &nbsp; {cat_html}
                    <span style="font-weight:600;">{alert_txt}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

        with col_badge:
            # El badge de prioridad se renderiza en su propia celda de columna,
            # completamente aislado del f-string anterior.
            st.markdown(
                f'<div style="padding-top:0.5rem;">{render_priority_badge(task["priority"])}</div>',
                unsafe_allow_html=True)

        st.markdown("<div style='height:0.1rem;background:var(--border-color);margin:0.2rem 0;'></div>",
                    unsafe_allow_html=True)


def render_activity_page() -> None:
    st.markdown('<div class="page-title">⚡ Actividad Reciente</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-subtitle">Registro en tiempo real de todas las acciones</div>',
                unsafe_allow_html=True)
    st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)

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
        "creó la tarea":      ("✅","#22c55e"),
        "actualizó la tarea": ("✏️","#8b5cf6"),
        "eliminó la tarea":   ("🗑️","#ef4444"),
        "completó la tarea":  ("🎯","#22c55e"),
        "reactivó la tarea":  ("↩️","#f59e0b"),
        "creó el equipo":     ("👥","#3b82f6"),
        "agregó":             ("➕","#0d9488"),
        "removió":            ("✕","#ef4444"),
        "movió":              ("↗️","#f59e0b"),
        "cambió el rol":      ("🔄","#8b5cf6"),
        "eliminó el equipo":  ("🗑️","#ef4444"),
    }

    for item in activity:
        action     = item.get("action","")
        icon, color = next(
            ((ic,co) for key,(ic,co) in action_icons.items() if key in action),
            ("📌","#6b7280"),
        )
        r,g,b   = _hex_to_rgb(color)
        entity  = item.get("entity_name","")
        st.markdown(f"""
        <div class="activity-item">
            <div class="activity-icon" style="background:rgba({r},{g},{b},0.12);">{icon}</div>
            <div>
                <div class="activity-text">
                    <strong>{item.get('user_name','Usuario')}</strong>
                    {action}
                    {f'<strong> {entity}</strong>' if entity else ''}
                </div>
                <div class="activity-time">🕐 {_time_ago(item.get('created_at',''))}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)


def render_config_page() -> None:
    st.markdown('<div class="page-title">⚙️ Configuración</div>', unsafe_allow_html=True)
    st.markdown("<div style='height:0.75rem'></div>", unsafe_allow_html=True)

    # ── Perfil ──
    with st.expander("👤 Perfil", expanded=True):
        c1, c2 = st.columns(2)
        with c1:
            st.text_input("Nombre completo", value="Usuario Demo", key="config_name")
        with c2:
            st.text_input("Email", value="usuario@gestorpro.com", key="config_email")
        if st.button("💾 Guardar Perfil", key="save_profile"):
            st.success("✅ Perfil actualizado correctamente.")

    # ── Notificaciones ──
    with st.expander("🔔 Notificaciones", expanded=True):
        st.toggle("Notificaciones de tareas",     value=True,  key="notif_tasks")
        st.toggle("Recordatorios diarios",         value=True,  key="notif_daily")
        st.toggle("Actualizaciones de proyectos",  value=False, key="notif_projects")
        st.toggle("Mensajes del equipo",           value=True,  key="notif_team")
        if st.button("💾 Guardar Notificaciones", key="save_notifs"):
            st.success("✅ Preferencias guardadas.")

    # ── Apariencia — FIX modo claro ──
    with st.expander("🎨 Apariencia", expanded=False):
        # on_change sincroniza dark_mode y provoca rerun para regenerar CSS
        def _apply_dark():
            st.session_state.dark_mode = st.session_state._cfg_dark

        st.toggle("🌙 Modo Oscuro", value=st.session_state.dark_mode,
                   key="_cfg_dark", on_change=_apply_dark)
        st.markdown('<div class="config-hint">También puedes alternar el tema desde el panel lateral.</div>',
                    unsafe_allow_html=True)

    # ── Gestión de Datos ──
    with st.expander("🗄️ Gestión de Datos", expanded=False):
        col_export, col_reset = st.columns(2)
        with col_export:
            st.download_button(
                "📥 Exportar Tareas (JSON)",
                data=json.dumps(st.session_state.tasks, ensure_ascii=False, indent=2),
                file_name="gestorpro_tasks.json",
                mime="application/json",
                use_container_width=True,
            )
        with col_reset:
            if st.button("🔄 Datos de ejemplo", key="reset_data", use_container_width=True):
                _exec("DELETE FROM tasks")
                seed_sample_data()
                st.session_state.tasks = db_load_tasks()
                st.success("✅ Datos de ejemplo restaurados.")
                st.rerun()

    # ── Conexión Supabase ──
    with st.expander("🔌 Base de Datos (Supabase)", expanded=False):
        status_html = (
            '<span style="color:#16a34a;font-weight:600;">✅ Conectado a Supabase</span>'
            if st.session_state.db_ok
            else '<span style="color:#ef4444;font-weight:600;">❌ Sin conexión</span>'
        )
        st.markdown(f"""
        <div class="config-info">
            <div style="margin-bottom:0.5rem;"><b>Estado:</b> {status_html}</div>
            <div><b>Host:</b> db.wopthjsdceattleaeczt.supabase.co:5432</div>
            <div><b>Base de datos:</b> postgres</div>
            <div><b>Usuario:</b> postgres</div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("🔄 Reconectar", key="reconnect_db"):
            st.cache_resource.clear()
            st.session_state.db_ok = False
            st.rerun()


# ══════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════

def main() -> None:
    init_session_state()
    inject_css()
    render_sidebar()

    {
        "Dashboard":     render_dashboard,
        "Tareas":        render_tasks_page,
        "Calendario":    render_calendar_page,
        "Equipo":        render_team_page,
        "Recordatorios": render_reminders_page,
        "Actividad":     render_activity_page,
        "Configuración": render_config_page,
    }.get(st.session_state.active_page, render_dashboard)()


if __name__ == "__main__":
    main()