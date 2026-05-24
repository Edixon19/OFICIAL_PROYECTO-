"""
GestorPro - Gestor de Tareas con Streamlit + Supabase (PostgreSQL)
==================================================================
Versión 2.0 — Con autenticación Supabase Auth
Autores: GestorPro, equipo del segundo semestre UTEDÉ
"""

import json
from datetime import datetime, date

import streamlit as st

from auth import (
    render_auth,
    auth_current_user,
    auth_logout,
    auth_user_display,
    auth_user_id,
)
from database import (
    init_db,
    seed_sample_data,
    db_load_tasks,
    db_load_teams,
    db_load_activity,
    db_create_team,
    db_add_member,
    db_update_member_role,
    db_move_member,
    db_remove_member,
    db_delete_team,
    db_get_user_teams,
    db_is_team_owner,
)
from logic import (
    add_task,
    update_task,
    delete_task,
    toggle_task_status,
    get_filtered_tasks,
    get_stats,
    render_priority_badge,
    render_status_badge,
    render_tag_badge,
    render_role_badge,
    _hex_to_rgb,
    _time_ago,
)

# ─────────────────────────────────────────────
# CONFIGURACIÓN INICIAL
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="GestorPro",
    page_icon=":material/target:",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────
# CONSTANTES
# ─────────────────────────────────────────────
PRIORITIES     = ["High", "Medium", "Low"]
CATEGORIES     = ["Trabajo", "Personal", "Compras", "Diseño", "Desarrollo", "Otro", "Casa", "Universidad", "Fiestas"]
STATUS_OPTIONS = ["Pendiente", "Activa", "Completada"]
TEAM_ROLES     = ["Líder", "Miembro", "Editor", "Viewer"]

PRIORITY_COLORS = {"High": "#ef4444", "Medium": "#f59e0b", "Low": "#22c55e"}
CATEGORY_COLORS = {
    "Trabajo": "#3b82f6", "Personal": "#8b5cf6", "Compras": "#f59e0b",
    "Diseño": "#ec4899", "Desarrollo": "#06b6d4", "Otro": "#6b7280",
    "Casa": "#94a3b8", "Universidad": "#10b981", "Fiestas": "#f59e0b"
}

# ── Temas ─────────────────────────────────────
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
#  SESSION STATE
# ══════════════════════════════════════════════

def init_session_state() -> None:
    defaults = {
        # ── UI / navegación ──────────────────
        "dark_mode":              False,
        "active_page":            "Dashboard",
        "filter_status":          "Todas",
        "filter_category":        "Todas",
        "show_new_task_form":     False,
        "show_new_team_form":     False,
        "editing_task_id":        None,
        "confirm_delete_id":      None,
        "confirm_delete_team_id": None,
        "search_query":           "",
        "managing_team_id":       None,
        # ── Contexto de equipo ────────────────
        "active_team_id":         None,   # None = espacio personal
        "user_teams":             [],     # equipos del usuario para el selector
        # ── Base de datos ────────────────────
        "db_ok":                  False,
        # ── Autenticación ────────────────────
        "auth_user":              None,
        "auth_session":           None,
        "auth_page":              "login",
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val

    # Inicializar BD solo si el usuario está autenticado
    if st.session_state.get("auth_user") and not st.session_state.db_ok:
        ok = init_db()
        st.session_state.db_ok = ok
        if ok:
            seed_sample_data()

    if st.session_state.get("auth_user"):
        # Cargar equipos del usuario para el selector del sidebar
        st.session_state.user_teams = db_get_user_teams()
        # Cargar tareas filtradas por el equipo activo
        st.session_state.tasks = db_load_tasks(team_id=st.session_state.active_team_id)
        st.session_state.teams = db_load_teams()
    else:
        st.session_state.setdefault("tasks", [])
        st.session_state.setdefault("teams", [])


# ══════════════════════════════════════════════
#  CSS DINÁMICO
# ══════════════════════════════════════════════

def inject_css() -> None:
    theme    = THEMES["dark"] if st.session_state.dark_mode else THEMES["light"]
    css_vars = "\n".join(f"    {k}: {v};" for k, v in theme.items())

    css = f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Sora:wght@300;400;500;600;700&display=swap');
    @import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@24,400,0,0');

    :root {{
{css_vars}
    }}

    html, body, .stApp {{
        background-color: var(--bg-main) !important;
        font-family: 'Sora', sans-serif !important;
        color: var(--text-primary) !important;
    }}
    #MainMenu, header, [data-testid="stHeader"] {{ display: none !important; }}
    .stDeployButton {{ display: none !important; }}

    /* ── Sidebar fijo ── */
    [data-testid="collapsedControl"],
    button[data-testid="collapsedControl"],
    [data-testid="stSidebarCollapseButton"],
    button[data-testid="stSidebarCollapseButton"],
    [data-testid="stSidebarCollapsedControl"],
    .stSidebarCollapsedControl,
    section[data-testid="stSidebar"] > div:first-child > div > button,
    section[data-testid="stSidebar"] button[kind="header"] {{
        display: none !important;
        visibility: hidden !important;
        pointer-events: none !important;
        opacity: 0 !important;
        width: 0 !important;
        height: 0 !important;
        overflow: hidden !important;
        position: absolute !important;
    }}
    section[data-testid="stSidebar"][aria-expanded="false"] {{
        transform: none !important;
        left: 0 !important;
        min-width: 240px !important;
        visibility: visible !important;
        display: block !important;
    }}
    section[data-testid="stSidebar"] {{
        background: var(--bg-sidebar) !important;
        min-width: 240px !important;
        padding: 1.25rem 1rem !important;
    }}
    section[data-testid="stSidebar"] .stButton > button {{
        background: transparent !important;
        color: var(--text-sidebar) !important;
        border: none !important;
        border-radius: 8px !important;
        text-align: left !important;
        font-size: 0.9rem !important;
        font-weight: 500 !important;
        padding: 0.5rem 0.75rem !important;
        width: 100% !important;
        transition: background 0.15s !important;
        box-shadow: none !important;
    }}
    section[data-testid="stSidebar"] .stButton > button:hover {{
        background: rgba(255,255,255,0.08) !important;
        transform: none !important;
        box-shadow: none !important;
    }}
    section[data-testid="stSidebar"] .stToggle label,
    section[data-testid="stSidebar"] .stToggle p {{
        color: var(--text-sidebar) !important;
        font-family: 'Sora', sans-serif !important;
        font-size: 0.88rem !important;
    }}

    /* ── Botón cerrar sesión en sidebar ── */
    .st-key-nav_logout button {{
        color: #ef4444 !important;
        border: 1px solid rgba(239,68,68,0.25) !important;
        background: rgba(239,68,68,0.06) !important;
        margin-top: 0.2rem !important;
    }}
    .st-key-nav_logout button:hover {{
        background: rgba(239,68,68,0.14) !important;
        border-color: rgba(239,68,68,0.5) !important;
        transform: none !important;
        box-shadow: none !important;
    }}

    /* ── Main content ── */
    .main .block-container,
    .stMainBlockContainer,
    [data-testid="stAppViewBlockContainer"],
    [data-testid="stMainBlockContainer"],
    [data-testid="block-container"] {{
        padding-top: 1rem !important;
        padding-bottom: 1rem !important;
        padding-left: 2rem !important;
        padding-right: 2rem !important;
        max-width: 1400px !important;
    }}

    /* ── Inputs ── */
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea {{
        background: var(--input-bg) !important;
        border-color: var(--input-border) !important;
        color: var(--text-primary) !important;
        border-radius: 8px !important;
        font-family: 'Sora', sans-serif !important;
        font-size: 0.88rem !important;
    }}
    .stTextInput label, .stTextArea label,
    .stDateInput label, .stSelectbox label {{
        color: var(--text-primary) !important;
        font-family: 'Sora', sans-serif !important;
        font-size: 0.84rem !important;
        font-weight: 500 !important;
    }}
    .stDateInput > div > div > input {{
        background: var(--input-bg) !important;
        border-color: var(--input-border) !important;
        color: var(--text-primary) !important;
        border-radius: 8px !important;
        font-family: 'Sora', sans-serif !important;
    }}

    /* ── Expanders ── */
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

    /* ── Tabs ── */
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

    /* ── Radio horizontal ── */
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

    /* ══════════════════════════════════════════
       JERARQUÍA DE BOTONES
    ══════════════════════════════════════════ */

    /* Nivel 2 SECONDARY — base */
    .stButton > button {{
        background: transparent !important;
        color: #0d9488 !important;
        border: 1.5px solid #0d9488 !important;
        border-radius: 10px !important;
        font-family: 'Sora', sans-serif !important;
        font-weight: 600 !important;
        font-size: 0.88rem !important;
        padding: 0.5rem 1.2rem !important;
        cursor: pointer !important;
        transition: background 0.18s, box-shadow 0.18s, transform 0.15s, opacity 0.18s !important;
    }}
    .stButton > button:hover {{
        background: rgba(13,148,136,0.09) !important;
        transform: translateY(-1px) !important;
        box-shadow: 0 3px 10px rgba(13,148,136,0.2) !important;
    }}

    /* Nivel 1 PRIMARY — CTAs */
    .st-key-btn_create_task button, .st-key-dash_new_task button,
    .st-key-dash_new_team button,   .st-key-open_new_task button,
    .st-key-open_new_team button,   .st-key-btn_create_team button,
    .st-key-new_reminder_btn button,.st-key-save_profile button,
    .st-key-save_notifs button,     .st-key-refresh_activity button,
    .st-key-reconnect_db button {{
        background: #262525 !important;
        color: white !important;
        border: none !important;
    }}
    .st-key-btn_create_task button:hover, .st-key-dash_new_task button:hover,
    .st-key-dash_new_team button:hover,   .st-key-open_new_task button:hover,
    .st-key-open_new_team button:hover,   .st-key-btn_create_team button:hover,
    .st-key-new_reminder_btn button:hover,.st-key-save_profile button:hover,
    .st-key-save_notifs button:hover,     .st-key-refresh_activity button:hover,
    .st-key-reconnect_db button:hover {{
        background: #262525 !important;
        transform: translateY(-1px) !important;
    }}

    /* save_{{taskid}} — Primary naranja */
    [class*="st-key-save_"] button {{
        background: #e55a2b !important;
        color: white !important;
        border: none !important;
        box-shadow: 0 2px 8px rgba(229,90,43,0.22) !important;
    }}
    [class*="st-key-save_"] button:hover {{
        background: #c94d22 !important;
        box-shadow: 0 4px 16px rgba(229,90,43,0.38) !important;
        transform: translateY(-1px) !important;
    }}

    /* Nivel 3 GHOST */
    .st-key-btn_cancel_new button,     .st-key-btn_cancel_team button,
    [class*="st-key-cancel_edit_"] button,
    [class*="st-key-confirm_no_"] button,
    [class*="st-key-conf_no_team_"] button {{
        background: transparent !important;
        color: var(--text-secondary) !important;
        border: 1.5px solid var(--border-color) !important;
        box-shadow: none !important;
    }}
    .st-key-btn_cancel_new button:hover,     .st-key-btn_cancel_team button:hover,
    [class*="st-key-cancel_edit_"] button:hover,
    [class*="st-key-confirm_no_"] button:hover,
    [class*="st-key-conf_no_team_"] button:hover {{
        background: var(--hover-bg) !important;
        transform: none !important;
        box-shadow: none !important;
    }}

    /* Nivel 4 DANGER */
    [class*="st-key-del_team_"] button,
    [class*="st-key-confirm_yes_"] button,[class*="st-key-conf_del_team_"] button,
    [class*="st-key-remove_member_"] button {{
        background: rgba(239,68,68,0.08) !important;
        color: #ef4444 !important;
        border: 1.5px solid rgba(239,68,68,0.4) !important;
        box-shadow: none !important;
    }}
    [class*="st-key-del_team_"] button:hover,
    [class*="st-key-confirm_yes_"] button:hover,[class*="st-key-conf_del_team_"] button:hover,
    [class*="st-key-remove_member_"] button:hover {{
        background: rgba(239,68,68,0.16) !important;
        border-color: #ef4444 !important;
        box-shadow: 0 3px 10px rgba(239,68,68,0.25) !important;
        transform: translateY(-1px) !important;
    }}

    /* reset_data — Advertencia */
    .st-key-reset_data button {{
        background: rgba(245,158,11,0.1) !important;
        color: #d97706 !important;
        border: 1.5px solid rgba(245,158,11,0.4) !important;
        box-shadow: none !important;
    }}
    .st-key-reset_data button:hover {{
        background: rgba(245,158,11,0.18) !important;
        border-color: #d97706 !important;
        box-shadow: 0 3px 10px rgba(245,158,11,0.25) !important;
        transform: translateY(-1px) !important;
    }}

    /* Download button */
    .stDownloadButton > button {{
        background: transparent !important;
        color: #0d9488 !important;
        border: 1.5px solid #0d9488 !important;
        border-radius: 10px !important;
        font-family: 'Sora', sans-serif !important;
        font-weight: 600 !important;
        transition: background 0.18s, box-shadow 0.18s !important;
    }}
    .stDownloadButton > button:hover {{
        background: rgba(13,148,136,0.09) !important;
        box-shadow: 0 3px 10px rgba(13,148,136,0.2) !important;
    }}

    /* ── Stat cards ── */
    .stat-card {{
        background: var(--bg-card);
        border-radius: 14px; padding: 1.25rem 1.5rem;
        border: 1px solid var(--border-color);
        box-shadow: var(--shadow);
        transition: box-shadow 0.2s, transform 0.2s; margin-bottom: 1rem;
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

    /* ── Task card wrapper (unified card with inline actions) ── */
    /* ── Task card wrapper (keyed st.container) ── */
    [class*="st-key-task_wrapper_"] {{
        background: var(--bg-card); border-radius: 14px;
        border: 1px solid var(--border-color);
        box-shadow: var(--shadow); margin-bottom: 0.7rem; transition: all 0.2s;
        padding: 0; overflow: hidden;
    }}
    [class*="st-key-task_wrapper_"]:hover {{ box-shadow: var(--shadow-hover); border-color: rgba(229,90,43,0.3); }}

    /* Inner card content — transparent, inherits from wrapper */
    [class*="st-key-task_wrapper_"] .task-card {{
        background: transparent; border: none;
        box-shadow: none; margin: 0; border-radius: 0;
        padding: 1.1rem 1.4rem;
    }}
    [class*="st-key-task_wrapper_"] .task-card:hover {{ box-shadow: none; border-color: transparent; }}

    /* Actions column inside card — vertically centered, left border */
    [class*="st-key-task_wrapper_"] [data-testid="stColumn"]:last-child {{
        display: flex !important;
        flex-direction: row !important;
        align-items: center !important;
        justify-content: center !important;
        
        padding: 0.5rem 0.3rem !important;
    }}

    /* Standalone task-card (dashboard recent tasks, calendar, etc.) */
    .task-card {{
        background: var(--bg-card); border-radius: 14px;
        padding: 1.1rem 1.4rem; border: 1px solid var(--border-color);
        box-shadow: var(--shadow); margin-bottom: 0.7rem; transition: all 0.2s;
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


    /* ── Task action icon buttons ── */
    .task-actions-col {{
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        gap: 0.35rem;
        padding: 0.25rem 0;
    }}
    /* Toggle (complete / reactivate) */
    [class*="st-key-toggle_"] button {{
        width: 36px !important; height: 36px !important;
        min-height: 36px !important; max-width: 36px !important;
        padding: 0 !important;
        border-radius: 10px !important;
        display: inline-flex !important; align-items: center !important; justify-content: center !important;
        background: rgba(34,197,94,0.10) !important;
        color: #16a34a !important;
        border: 1.5px solid rgba(34,197,94,0.30) !important;
        box-shadow: none !important;
        transition: all 0.18s ease !important;
    }}
    [class*="st-key-toggle_"] button:hover {{
        background: rgba(34,197,94,0.22) !important;
        border-color: #16a34a !important;
        transform: translateY(-1px) !important;
        box-shadow: 0 3px 10px rgba(34,197,94,0.20) !important;
    }}
    /* Toggle — reactivate variant (amber) */
    [class*="st-key-toggle_"] button[data-reactivate] {{
        background: rgba(245,158,11,0.10) !important;
        color: #d97706 !important;
        border-color: rgba(245,158,11,0.30) !important;
    }}
    /* Edit icon button */
    [class*="st-key-edit_btn_"] button {{
        width: 36px !important; height: 36px !important;
        min-height: 36px !important; max-width: 36px !important;
        padding: 0 !important;
        border-radius: 10px !important;
        display: inline-flex !important; align-items: center !important; justify-content: center !important;
        background: rgba(13,148,136,0.10) !important;
        color: #0d9488 !important;
        border: 1.5px solid rgba(13,148,136,0.30) !important;
        box-shadow: none !important;
        transition: all 0.18s ease !important;
    }}
    [class*="st-key-edit_btn_"] button:hover {{
        background: rgba(13,148,136,0.22) !important;
        border-color: #0d9488 !important;
        transform: translateY(-1px) !important;
        box-shadow: 0 3px 10px rgba(13,148,136,0.20) !important;
    }}
    /* Delete icon button */
    [class*="st-key-delete_btn_"] button {{
        width: 36px !important; height: 36px !important;
        min-height: 36px !important; max-width: 36px !important;
        padding: 0 !important;
        border-radius: 10px !important;
        display: inline-flex !important; align-items: center !important; justify-content: center !important;
        background: rgba(239,68,68,0.08) !important;
        color: #ef4444 !important;
        border: 1.5px solid rgba(239,68,68,0.30) !important;
        box-shadow: none !important;
        transition: all 0.18s ease !important;
    }}
    [class*="st-key-delete_btn_"] button:hover {{
        background: rgba(239,68,68,0.20) !important;
        border-color: #ef4444 !important;
        transform: translateY(-1px) !important;
        box-shadow: 0 3px 10px rgba(239,68,68,0.20) !important;
    }}
    /* Hide text inside task action buttons, show only icon */
    [class*="st-key-toggle_"] button p,
    [class*="st-key-edit_btn_"] button p,
    [class*="st-key-delete_btn_"] button p {{
        display: none !important;
    }}
    [class*="st-key-toggle_"] button [data-testid="stIconMaterial"],
    [class*="st-key-edit_btn_"] button [data-testid="stIconMaterial"],
    [class*="st-key-delete_btn_"] button [data-testid="stIconMaterial"] {{
        margin: 0 !important;
        font-size: 1.15rem !important;
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

    /* ── Botones Sidebar (Navbar) ── */
    div[class*="st-key-nav_"] button {{
        justify-content: flex-start !important;
        text-align: left !important;
        padding-left: 1rem !important;
    }}
    div[class*="st-key-nav_"] button div {{
        display: flex !important;
        justify-content: flex-start !important;
        align-items: center !important;
        width: 100% !important;
    }}
    div[class*="st-key-nav_"] button p {{
        text-align: left !important;
        margin: 0 !important;
        width: 100% !important;
    }}

    /* ── Sidebar team selector ── */
    section[data-testid="stSidebar"] .stSelectbox [data-baseweb="select"] > div {{
        background: rgba(255,255,255,0.06) !important;
        border: 1px solid rgba(255,255,255,0.12) !important;
        border-radius: 10px !important;
        color: #f1f5f9 !important;
        font-family: 'Sora', sans-serif !important;
        font-size: 0.84rem !important;
        font-weight: 600 !important;
        min-height: 38px !important;
    }}
    section[data-testid="stSidebar"] .stSelectbox [data-baseweb="select"] > div:hover {{
        border-color: rgba(229,90,43,0.4) !important;
    }}
    section[data-testid="stSidebar"] .stSelectbox [data-baseweb="select"] svg {{
        fill: #94a3b8 !important;
    }}
    section[data-testid="stSidebar"] .stSelectbox label {{
        color: #94a3b8 !important;
    }}

    /* ── Configuración ── */
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
    /* ── Perfil fijo ── */
    [data-testid="stSidebarContent"] {{
        padding-bottom: 80px !important;
    }}

    /* ── Ocultar navegación por defecto de Streamlit ── */
    [data-testid="stSidebarNav"] {{
        display: none !important;
    }}

    /* ── Ocultar el header vacío del sidebar para eliminar el espacio superior ── */
    [data-testid="stSidebarHeader"] {{
        display: none !important;
        padding: 0 !important;
        margin: 0 !important;
        height: 0 !important;
        min-height: 0 !important;
    }}
    </style>
    """

    js = """
    <script>
    (function fixSidebar() {
        var COLLAPSE_SELECTORS = [
            '[data-testid="collapsedControl"]',
            '[data-testid="stSidebarCollapseButton"]',
            '[data-testid="stSidebarCollapsedControl"]',
            'button[data-testid="collapsedControl"]',
            'button[data-testid="stSidebarCollapseButton"]'
        ];
        function removeCollapseBtn() {
            COLLAPSE_SELECTORS.forEach(function(sel) {
                document.querySelectorAll(sel).forEach(function(el) {
                    el.style.display = 'none';
                    el.style.visibility = 'hidden';
                    el.style.pointerEvents = 'none';
                    el.style.opacity = '0';
                });
            });
            var sidebar = document.querySelector('section[data-testid="stSidebar"]');
            if (sidebar) {
                if (sidebar.getAttribute('aria-expanded') === 'false')
                    sidebar.setAttribute('aria-expanded', 'true');
                sidebar.style.transform = 'none';
                sidebar.style.left = '0';
                sidebar.style.minWidth = '240px';
                sidebar.style.visibility = 'visible';
                sidebar.style.display = 'block';
                
                var p = document.getElementById('user-profile-fixed');
                if (p) p.style.width = sidebar.offsetWidth + 'px';
            }
        }
        removeCollapseBtn();
        new MutationObserver(removeCollapseBtn).observe(document.body, { childList: true, subtree: true });
        var c = 0;
        var iv = setInterval(function() { removeCollapseBtn(); if (++c >= 10) clearInterval(iv); }, 500);
        
        // Resize observer para que el perfil siempre coincida con el sidebar
        var ro = new ResizeObserver(function() {
            var s = document.querySelector('section[data-testid="stSidebar"]');
            var p = document.getElementById('user-profile-fixed');
            if (s && p) p.style.width = s.offsetWidth + 'px';
        });
        setTimeout(function() {
            var s = document.querySelector('section[data-testid="stSidebar"]');
            if (s) ro.observe(s);
        }, 1000);
    })();
    </script>
    """

    st.markdown(css, unsafe_allow_html=True)
    st.markdown(js,  unsafe_allow_html=True)


# ══════════════════════════════════════════════
#  COMPONENTES UI
# ══════════════════════════════════════════════

def render_task_card(task: dict) -> None:
    is_completed = task["status"] == "Completada"
    completed_class = " completed" if is_completed else ""
    tags_html    = " ".join(render_tag_badge(t) for t in task.get("tags", []))
    assignee_name = task.get("assignee", "")
    assignee_id = task.get("assignee_id")
    if assignee_id:
        found = False
        for team in st.session_state.get("teams", []):
            for m in team.get("members", []):
                if str(m["user_id"]) == str(assignee_id):
                    assignee_name = m["member_name"]
                    found = True
                    break
            if found:
                break
    due_str      = f'<span class="material-symbols-rounded" style="vertical-align: middle; font-size: inherit;">calendar_month</span> {task.get("due_date","")}' if task.get("due_date") else ""
    asgn_str     = f'<span class="material-symbols-rounded" style="vertical-align: middle; font-size: inherit;">person</span> {assignee_name}'         if assignee_name else ""
    meta_html    = " &nbsp;·&nbsp; ".join(p for p in [due_str, asgn_str] if p)

    # Use a keyed container so CSS can target it, with columns inside for layout
    with st.container(key=f"task_wrapper_{task['id']}"):
        col_card, col_actions = st.columns([6, 1])

        with col_card:
            st.markdown(f"""
            <div class="task-card{completed_class}">
                <div class="task-title">{task['title']}</div>
                <div class="task-desc">{task.get('description','')}</div>
                <div style="display:flex;flex-wrap:wrap;align-items:center;gap:0.3rem;margin-bottom:0.4rem;">
                    {render_priority_badge(task['priority'])}{render_status_badge(task['status'])}
                </div>
                <div style="margin-bottom:0.3rem;">{tags_html}</div>
                <div class="task-meta">{meta_html}</div>
            </div>
            """, unsafe_allow_html=True) 


        with col_actions:
            toggle_icon = ":material/undo:" if is_completed else ":material/check:"
            toggle_tip  = "Reactivar" if is_completed else "Completar"
            if st.button(" ", icon=toggle_icon, key=f"toggle_{task['id']}", help=toggle_tip):
                toggle_task_status(task["id"], task["status"], task["title"])
                st.rerun()
            if st.button(" ", icon=":material/edit:", key=f"edit_btn_{task['id']}", help="Editar"):
                st.session_state.editing_task_id = (
                    None if st.session_state.editing_task_id == task["id"] else task["id"])
                st.rerun()
            if st.button(" ", icon=":material/delete:", key=f"delete_btn_{task['id']}", help="Eliminar"):
                st.session_state.confirm_delete_id = task["id"]
                st.rerun()

    if st.session_state.confirm_delete_id == task["id"]:
        st.markdown('<div class="confirm-delete-box"><span class="material-symbols-rounded">warning</span> ¿Confirmar eliminación? No se puede deshacer.</div>',
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
    st.markdown('<div class="form-container"><div class="form-title"><span class="material-symbols-rounded">edit</span> Editar Tarea</div>',
                unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        nt  = st.text_input("Título *", value=task["title"], key=f"edit_title_{task['id']}")
        nd  = st.text_area("Descripción", value=task.get("description",""),
                            key=f"edit_desc_{task['id']}", height=80)
        
        active_team_id = st.session_state.get("active_team_id")
        team_members = []
        if active_team_id:
            active_team = next((t for t in st.session_state.get("teams", []) if t["id"] == active_team_id), None)
            if active_team:
                team_members = active_team.get("members", [])

        if active_team_id and team_members:
            options = ["Sin asignar"] + [f"{m['member_name']} ({m['email']})" for m in team_members]
            default_index = 0
            task_assignee_id = task.get("assignee_id")
            task_assignee_name = task.get("assignee")
            if task_assignee_id:
                for idx, m in enumerate(team_members):
                    if str(m["user_id"]) == str(task_assignee_id):
                        default_index = idx + 1
                        break
            elif task_assignee_name:
                for idx, m in enumerate(team_members):
                    if m["member_name"] == task_assignee_name:
                        default_index = idx + 1
                        break

            selected_assignee = st.selectbox(
                "Asignado a",
                options,
                index=default_index,
                key=f"edit_assignee_sel_{task['id']}"
            )
            if selected_assignee == "Sin asignar":
                na = ""
                na_id = None
            else:
                m_selected = team_members[options.index(selected_assignee) - 1]
                na = m_selected["member_name"]
                na_id = m_selected["user_id"]
        else:
            na  = st.text_input("Asignado a", value=task.get("assignee",""),
                                 key=f"edit_assignee_{task['id']}")
            na_id = None
    with c2:
        np_ = st.selectbox("Prioridad", PRIORITIES,
                            index=PRIORITIES.index(task["priority"]) if task["priority"] in PRIORITIES else 0,
                            format_func=lambda x: {"High": "Alta", "Medium": "Media", "Low": "Baja"}.get(x, x),
                            key=f"edit_priority_{task['id']}")
        nc  = st.selectbox("Categoría", CATEGORIES,
                            index=CATEGORIES.index(task["category"]) if task["category"] in CATEGORIES else 0,
                            key=f"edit_category_{task['id']}")
        ns  = st.selectbox("Estado", STATUS_OPTIONS,
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
        if st.button("Guardar", icon=":material/save:", key=f"save_{task['id']}", use_container_width=True):
            if not nt.strip():
                st.error("El título es obligatorio.")
            else:
                update_task(task["id"], title=nt.strip(), description=nd.strip(),
                            priority=np_, category=nc, status=ns,
                            due_date=ndate.isoformat(), assignee=na.strip(),
                            assignee_id=na_id,
                            tags=[t.strip() for t in tags_str.split(",") if t.strip()])
                st.session_state.editing_task_id = None
                st.success(":material/check_circle: Tarea actualizada.")
                st.rerun()
    with cc:
        if st.button("Cancelar", key=f"cancel_edit_{task['id']}"):
            st.session_state.editing_task_id = None
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)


def render_new_task_page() -> None:
    if st.button(" ", icon=":material/arrow_back:", key="btn_back_new_task", help="Volver"):
        st.session_state.active_page = "Tareas"
        st.rerun()

    st.markdown('<div class="page-title"><span class="material-symbols-rounded">add</span> Nueva Tarea</div>', unsafe_allow_html=True)

    # Indicador del espacio de trabajo activo
    active_team_id = st.session_state.get("active_team_id")
    if active_team_id:
        team_name = next((t["name"] for t in st.session_state.get("user_teams", [])
                          if t["id"] == active_team_id), "Equipo")
        workspace_label = f'<span class="material-symbols-rounded" style="font-size:inherit;vertical-align:middle;">groups</span> {team_name}'
    else:
        workspace_label = '<span class="material-symbols-rounded" style="font-size:inherit;vertical-align:middle;">person</span> Mi Espacio Personal'
    st.markdown(
        f'<div class="page-subtitle">Añade una nueva tarea a: '
        f'<span style="font-weight:600;color:var(--accent-primary);">{workspace_label}</span></div>',
        unsafe_allow_html=True)

    st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)

    active_team_id = st.session_state.get("active_team_id")
    team_members = []
    if active_team_id:
        active_team = next((t for t in st.session_state.get("teams", []) if t["id"] == active_team_id), None)
        if active_team:
            team_members = active_team.get("members", [])

    c1, c2 = st.columns(2)
    with c1:
        title    = st.text_input("Título *", placeholder="¿Qué necesitas hacer?", key="new_title")
        
        if active_team_id and team_members:
            options = ["Sin asignar"] + [f"{m['member_name']} ({m['email']})" for m in team_members]
            selected_assignee = st.selectbox("Asignado a", options, key="new_assignee_sel")
            if selected_assignee == "Sin asignar":
                assignee = ""
                assignee_id = None
            else:
                m_selected = team_members[options.index(selected_assignee) - 1]
                assignee = m_selected["member_name"]
                assignee_id = m_selected["user_id"]


        priority = st.selectbox("Prioridad", PRIORITIES, key="new_priority",
                                format_func=lambda x: {"High": "Alta", "Medium": "Media", "Low": "Baja"}.get(x, x))
    with c2:
       
        category = st.selectbox("Categoría", CATEGORIES, key="new_category")
        status   = st.selectbox("Estado inicial", STATUS_OPTIONS, key="new_status")
        due_date = st.date_input("Fecha límite", value=date.today(), key="new_date")
    tags_input = st.text_input("Etiquetas (separadas por coma)",
                                placeholder="ej: diseño, urgente", key="new_tags")
    desc     = st.text_area("Descripción", placeholder="Añade más detalles...",
                                 key="new_desc", height=90)
    cb, cc, _ = st.columns([1, 1, 4])
    with cb:
        if st.button("Crear Tarea", icon=":material/check_circle:", key="btn_create_task", use_container_width=True):
            if not title.strip():
                st.error(":material/warning: El título es obligatorio.")
            else:
                tags = [t.strip() for t in tags_input.split(",") if t.strip()]
                add_task(title, desc, priority, category, status, due_date, assignee, tags, assignee_id=assignee_id)
                st.session_state.active_page = "Tareas"
                st.success(f":material/check_circle: Tarea '{title.strip()}' creada.")
                st.rerun()
    with cc:
        if st.button("Cancelar", key="btn_cancel_new"):
            st.session_state.active_page = "Tareas"
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)


# ══════════════════════════════════════════════
#  SIDEBAR
# ══════════════════════════════════════════════

def render_sidebar() -> None:
    user       = st.session_state.get("auth_user")
    name, email = auth_user_display(user)
    # Avatar: iniciales del nombre
    initials   = "".join(p[0].upper() for p in name.split()[:2]) if name else "U"

    with st.sidebar:
        # ── Logo ──────────────────────────────────
        st.markdown("""
        <div class="sidebar-logo">
            <div class="logo-icon">GP</div>
            <div>
                <div class="logo-text">GestorPro</div>
                <div class="logo-sub">Productividad elevada</div>
            </div>
        </div>
        """, unsafe_allow_html=True)


        # ── Selector de equipo ─────────────────────
        user_teams = st.session_state.get("user_teams", [])
        team_options = [{"id": None, "name": "Mi Espacio Personal"}] + user_teams
        team_names = [t["name"] for t in team_options]
        # Encontrar índice del equipo activo
        active_id = st.session_state.active_team_id
        current_idx = 0
        for i, t in enumerate(team_options):
            if t["id"] == active_id:
                current_idx = i
                break

        selected_team_name = st.selectbox(
            "Espacio de trabajo",
            team_names,
            index=current_idx,
            key="sidebar_team_selector",
            label_visibility="collapsed",
        )
        # Resolver el ID del equipo seleccionado
        selected_team = next(t for t in team_options if t["name"] == selected_team_name)
        if selected_team["id"] != st.session_state.active_team_id:
            st.session_state.active_team_id = selected_team["id"]
            st.session_state.tasks = db_load_tasks(team_id=selected_team["id"])
            st.rerun()

        st.markdown(
            "<div style='height:1px;background:rgba(255,255,255,0.08);margin:0.5rem 0 0.75rem;'></div>",
            unsafe_allow_html=True,
        )

        # ── Navegación ────────────────────────────
        for icon, page in [
            (":material/dashboard:","Dashboard"), (":material/check:","Tareas"), (":material/calendar_view_month:","Calendario"),
            (":material/groups:","Equipo"),    (":material/notifications_active:","Recordatorios"), (":material/bolt:","Actividad"),
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
        st.markdown(
            "<div style='height:1px;background:rgba(255,255,255,0.08);margin-bottom:0.75rem;'></div>",
            unsafe_allow_html=True,
        )

        # ── Modo oscuro ───────────────────────────
        dark = st.toggle(":material/dark_mode:  Modo Oscuro", value=st.session_state.dark_mode, key="sidebar_dark_toggle")
        if dark != st.session_state.dark_mode:
            st.session_state.dark_mode = dark
            st.rerun()

        if st.button("Configuración", icon=":material/settings:", key="nav_config", use_container_width=True):
            st.session_state.active_page = "Configuración"
            st.rerun()

        # ── Cerrar sesión ─────────────────────────
        if st.button("Cerrar sesión", icon=":material/logout:", key="nav_logout", use_container_width=True):
            auth_logout()
            st.rerun()

        # ── Perfil del usuario autenticado (Fijo al fondo) ────────
        st.markdown(f"""
        <div id="user-profile-fixed" style="position:fixed;bottom:0;left:0;display:flex;align-items:center;gap:0.65rem;
                    background:var(--bg-sidebar);padding:1rem;
                    border-top:1px solid rgba(255,255,255,0.08);z-index:9999;">
            <div style="width:34px;height:34px;border-radius:50%;flex-shrink:0;
                        background:linear-gradient(135deg,#e55a2b,#0d9488);
                        display:flex;align-items:center;justify-content:center;
                        color:white;font-size:0.75rem;font-weight:700;
                        font-family:'Sora',sans-serif;">{initials}</div>
            <div style="overflow:hidden;">
                <div style="font-size:0.82rem;font-weight:600;color:#f1f5f9;
                            font-family:'Sora',sans-serif;
                            white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{name}</div>
                <div style="font-size:0.68rem;color:#94a3b8;font-family:'Sora',sans-serif;
                            white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{email}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)



# ══════════════════════════════════════════════
#  PÁGINAS (sin cambios respecto a v1)
# ══════════════════════════════════════════════

def render_dashboard() -> None:
    tp = THEMES["dark"]["--text-primary"] if st.session_state.dark_mode else THEMES["light"]["--text-primary"]
    ts = THEMES["dark"]["--text-secondary"] if st.session_state.dark_mode else THEMES["light"]["--text-secondary"]

    user = st.session_state.get("auth_user")
    name, _ = auth_user_display(user)

    st.markdown(f"""
    <div style="margin-bottom:1.5rem;">
        <div style="font-size:1.5rem;font-weight:700;color:{tp};font-family:'Sora',sans-serif;">
            Hola, {name.split()[0]} <span class="material-symbols-rounded">waving_hand</span></div>
        <div style="font-size:0.8rem;color:{ts};font-family:'Sora',sans-serif;">
            Resumen de productividad · Actualizado en tiempo real</div>
    </div>
    """, unsafe_allow_html=True)
    

    stats = get_stats()
    s1, s2, s3, s4 = st.columns(4)
    for col, icon, bg, val, lbl, delta, pos in [
        (s1,'<span class="material-symbols-rounded">assignment</span>',"#fff3ee",stats["completed"],"Completadas",f"▲ +{stats['completed']} tareas",True),
        (s2,'<span class="material-symbols-rounded">hourglass_empty</span>',"#fff8ee",stats["pending"],"Pendientes","▼ Por completar",False),
        (s3,'<span class="material-symbols-rounded">local_fire_department</span>',"#eefbf7",stats["active"],"Tareas activas","▲ En progreso",True),
        (s4,'<span class="material-symbols-rounded">target</span>',"#eef4ff",f"{stats['completion_rate']}%","Tasa finalización","▲ Tiempo real",True),
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
        st.markdown('<div class="section-title"><span class="material-symbols-rounded">trending_up</span> Tareas por Categoría</div>', unsafe_allow_html=True)
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
        st.markdown('<div class="section-title"><span class="material-symbols-rounded">pie_chart</span> Distribución por Estado</div>', unsafe_allow_html=True)
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

    st.markdown('<div class="section-title"><span class="material-symbols-rounded">assignment</span> Tareas Recientes</div>', unsafe_allow_html=True)
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
        # Mostrar nombre del espacio activo
        active_tid = st.session_state.get("active_team_id")
        if active_tid:
            workspace_name = next((t["name"] for t in st.session_state.get("user_teams", [])
                                   if t["id"] == active_tid), "Equipo")
        else:
            workspace_name = "Mi Espacio Personal"
        st.markdown(f'<div class="page-title">Tareas · {workspace_name}</div>', unsafe_allow_html=True)
        st.markdown('<div class="page-subtitle">Gestiona y organiza las tareas de este espacio</div>',
                    unsafe_allow_html=True)
    with col_btn:
        st.markdown("<div style='height:0.4rem'></div>", unsafe_allow_html=True)
        if st.button("Nueva Tarea", icon=":material/add:", key="open_new_task", use_container_width=True):
            st.session_state.active_page = "Nueva Tarea"
            st.rerun()

    st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)

    search = st.text_input(":material/search: Buscar tareas...", value=st.session_state.search_query,
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
            <div style="font-size:2.5rem;margin-bottom:0.75rem;"><span class="material-symbols-rounded">inbox</span></div>
            <div style="font-size:1rem;font-weight:500;">No se encontraron tareas</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        for task in filtered:
            render_task_card(task)


def render_calendar_page() -> None:
    st.markdown('<div class="page-title"><span class="material-symbols-rounded">calendar_month</span> Calendario</div>', unsafe_allow_html=True)
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
            {display}{'  <span class="material-symbols-rounded">circle</span> HOY' if is_today else ""}
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
        st.markdown('<div class="page-title"><span class="material-symbols-rounded">group</span> Equipos</div>', unsafe_allow_html=True)
        st.markdown('<div class="page-subtitle">Crea y gestiona tus equipos de trabajo</div>',
                    unsafe_allow_html=True)
    with col_btn:
        st.markdown("<div style='height:0.4rem'></div>", unsafe_allow_html=True)
        if st.button("Nuevo Equipo", icon=":material/add:", key="open_new_team", use_container_width=True):
            st.session_state.show_new_team_form = not st.session_state.show_new_team_form
            st.rerun()

    st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)

    if st.session_state.show_new_team_form:
        st.markdown('<div class="form-container"><div class="form-title"><span class="material-symbols-rounded">construction</span> Crear Nuevo Equipo</div>',
                    unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            team_name   = st.text_input("Nombre del equipo *",
                                         placeholder="ej: Equipo Frontend", key="new_team_name")
            team_desc   = st.text_area("Descripción",
                                        placeholder="¿Cuál es el propósito?",
                                        key="new_team_desc", height=80)
        with c2:
            st.markdown("""
            <div style="background:rgba(229,90,43,0.08);border-radius:10px;padding:0.75rem 1rem;
                        border:1px solid rgba(229,90,43,0.2);margin-top:0.5rem;">
                <div style="font-size:0.8rem;color:var(--text-primary);font-family:'Sora',sans-serif;font-weight:600;">
                    <span class="material-symbols-rounded">push_pin</span> Serás añadido automáticamente como Líder</div>
                <div style="font-size:0.75rem;color:var(--text-secondary);font-family:'Sora',sans-serif;margin-top:0.3rem;">
                    <span class="material-symbols-rounded">circle</span> <b>Líder</b>: Gestiona equipo · <span class="material-symbols-rounded">circle</span> <b>Miembro</b>: Participa<br>
                    <span class="material-symbols-rounded">circle</span> <b>Editor</b>: Edita tareas · <span class="material-symbols-rounded">circle_outline</span> <b>Viewer</b>: Solo lectura</div>
            </div>
            """, unsafe_allow_html=True)
        cs, cc, _ = st.columns([1, 1, 3])
        with cs:
            if st.button("Crear Equipo", icon=":material/check_circle:", key="btn_create_team", use_container_width=True):
                if not team_name.strip():
                    st.error("El nombre del equipo es obligatorio.")
                else:
                    if db_create_team(team_name, team_desc):
                        st.session_state.show_new_team_form = False
                        st.session_state.teams = db_load_teams()
                        st.session_state.user_teams = db_get_user_teams()
                        st.success(f":material/check_circle: Equipo '{team_name}' creado.")
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
            <div style="font-size:2.5rem;margin-bottom:0.75rem;"><span class="material-symbols-rounded">group</span></div>
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
                    <span class="material-symbols-rounded">stars</span> Líder: {leader['member_name'] if leader else 'Sin líder'}<br>
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

        # Solo el creador del equipo puede gestionar/eliminar
        is_owner = db_is_team_owner(team["id"])
        if is_owner:
            col_manage, col_del_team, _ = st.columns([1, 1, 4])
            with col_manage:
                open_lbl = ":material/expand_more: Cerrar" if st.session_state.managing_team_id == team["id"] else ":material/settings: Gestionar"
                if st.button(open_lbl, key=f"manage_{team['id']}", use_container_width=True):
                    st.session_state.managing_team_id = (
                        None if st.session_state.managing_team_id == team["id"] else team["id"])
                    st.rerun()
            with col_del_team:
                if st.button("Eliminar equipo", icon=":material/delete:", key=f"del_team_{team['id']}", use_container_width=True):
                    st.session_state.confirm_delete_team_id = team["id"]
                    st.rerun()

        if st.session_state.get("confirm_delete_team_id") == team["id"]:
            st.markdown('<div class="confirm-delete-box"><span class="material-symbols-rounded">warning</span> ¿Eliminar el equipo y todos sus miembros?</div>',
                        unsafe_allow_html=True)
            cy, cn = st.columns(2)
            with cy:
                if st.button("Sí, eliminar equipo", key=f"conf_del_team_{team['id']}", use_container_width=True):
                    db_delete_team(team["id"], team["name"])
                    st.session_state.confirm_delete_team_id = None
                    st.session_state.teams = db_load_teams()
                    st.session_state.user_teams = db_get_user_teams()
                    # Si el equipo eliminado era el activo, volver al espacio personal
                    if st.session_state.active_team_id == team["id"]:
                        st.session_state.active_team_id = None
                        st.session_state.tasks = db_load_tasks(team_id=None)
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
            tab_add, tab_manage = st.tabs([":material/add: Agregar miembro", ":material/build: Gestionar miembros"])

            with tab_add:
                cnm, cnr, cnb = st.columns([2, 1, 1])
                with cnm:
                    new_member_email = st.text_input("Correo del miembro",
                                                     placeholder="ej: usuario@email.com",
                                                     key=f"new_member_{team['id']}")
                with cnr:
                    new_member_role = st.selectbox("Rol", TEAM_ROLES,
                                                    key=f"new_member_role_{team['id']}")
                with cnb:
                    st.markdown("<div style='height:1.75rem'></div>", unsafe_allow_html=True)
                    if st.button("Agregar", key=f"add_member_{team['id']}", use_container_width=True):
                        if not new_member_email.strip():
                            st.error("Ingresa el correo del miembro.")
                        else:
                            ok, err = db_add_member(team["id"], new_member_email, new_member_role, team["name"])
                            if ok:
                                st.session_state.teams = db_load_teams()
                                st.success(f":material/check_circle: Miembro agregado como {new_member_role}.")
                                st.rerun()
                            elif err:
                                st.error(err)

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
                                if st.button(" ", icon=":material/check:", key=f"save_role_{m['id']}", help="Guardar rol"):
                                    db_update_member_role(m["id"], new_role, m["member_name"])
                                    st.session_state.teams = db_load_teams()
                                    st.rerun()
                        with c_move:
                            if other_teams:
                                target_name = st.selectbox(
                                    "Mover a", [t["name"] for t in other_teams],
                                    key=f"move_target_{m['id']}", label_visibility="collapsed")
                                if st.button("Mover", icon=":material/arrow_outward:", key=f"move_member_{m['id']}", use_container_width=True):
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
                            if st.button(" ", icon=":material/close:", key=f"remove_member_{m['id']}",
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
    col_h, col_btn = st.columns([3, 1])
    with col_h:
        st.markdown('<div class="page-title"><span class="material-symbols-rounded">notifications</span> Recordatorios</div>', unsafe_allow_html=True)
    with col_btn:
        st.markdown("<div style='height:0.4rem'></div>", unsafe_allow_html=True)
        if st.button("Nueva Tarea", icon=":material/add:", key="new_reminder_btn", use_container_width=True):
            st.session_state.active_page        = "Nueva Tarea"
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
        alarm_icon = '<span class="material-symbols-rounded">error</span>' if is_overdue else ('<span class="material-symbols-rounded">alarm</span>' if is_today else '<span class="material-symbols-rounded">notifications</span>')
        cat        = task.get("category","")
        alert_txt  = '  <span class="material-symbols-rounded">circle</span> VENCIDA' if is_overdue else ('  <span class="material-symbols-rounded">circle</span> HOY' if is_today else "")

        col_icon, col_body, col_badge = st.columns([1, 8, 2])
        with col_icon:
            st.markdown(f"""
            <div style="display:flex;align-items:center;justify-content:center;
                        height:100%;padding-top:0.5rem;font-size:1.4rem;">{alarm_icon}</div>
            """, unsafe_allow_html=True)
        with col_body:
            cat_html = (f'<span class="badge badge-tag">{cat}</span>' if cat else "")
            st.markdown(f"""
            <div style="border-left:3px solid {border};padding-left:0.75rem;
                        padding-top:0.25rem;padding-bottom:0.25rem;">
                <div class="reminder-title">{task['title']}</div>
                <div class="reminder-desc">{task.get('description','')}</div>
                <div class="reminder-meta">
                    <span class="material-symbols-rounded" style="vertical-align: middle; font-size: inherit;">calendar_month</span> {dd} &nbsp; {cat_html}
                    <span style="font-weight:600;">{alert_txt}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
        with col_badge:
            st.markdown(
                f'<div style="padding-top:0.5rem;">{render_priority_badge(task["priority"])}</div>',
                unsafe_allow_html=True)

        st.markdown(
            "<div style='height:0.1rem;background:var(--border-color);margin:0.2rem 0;'></div>",
            unsafe_allow_html=True)


def render_activity_page() -> None:
    st.markdown('<div class="page-title"><span class="material-symbols-rounded">bolt</span> Actividad Reciente</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-subtitle">Registro en tiempo real de todas las acciones</div>',
                unsafe_allow_html=True)
    st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)

    col_ref, _ = st.columns([1, 5])
    with col_ref:
        if st.button("Actualizar", icon=":material/refresh:", key="refresh_activity", use_container_width=True):
            st.rerun()

    activity = db_load_activity(limit=30)
    if not activity:
        st.markdown("""
        <div style="text-align:center;padding:3rem;color:var(--text-secondary);font-family:'Sora',sans-serif;">
            <div style="font-size:2.5rem;margin-bottom:0.75rem;"><span class="material-symbols-rounded">inbox</span></div>
            <div style="font-size:1rem;font-weight:500;">No hay actividad registrada aún</div>
        </div>
        """, unsafe_allow_html=True)
        return

    action_icons = {
        "creó la tarea":      ('<span class="material-symbols-rounded">check_circle</span>',"#22c55e"),
        "actualizó la tarea": ('<span class="material-symbols-rounded">edit</span>',"#8b5cf6"),
        "eliminó la tarea":   ('<span class="material-symbols-rounded">delete</span>',"#ef4444"),
        "completó la tarea":  ('<span class="material-symbols-rounded">target</span>',"#22c55e"),
        "reactivó la tarea":  ('<span class="material-symbols-rounded">undo</span>',"#f59e0b"),
        "creó el equipo":     ('<span class="material-symbols-rounded">group</span>',"#3b82f6"),
        "agregó":             ('<span class="material-symbols-rounded">add</span>',"#0d9488"),
        "removió":            ('<span class="material-symbols-rounded">close</span>',"#ef4444"),
        "movió":              ('<span class="material-symbols-rounded">arrow_outward</span>',"#f59e0b"),
        "cambió el rol":      ('<span class="material-symbols-rounded">refresh</span>',"#8b5cf6"),
        "eliminó el equipo":  ('<span class="material-symbols-rounded">delete</span>',"#ef4444"),
    }

    for item in activity:
        action      = item.get("action","")
        icon, color = next(
            ((ic,co) for key,(ic,co) in action_icons.items() if key in action),
            ('<span class="material-symbols-rounded">push_pin</span>',"#6b7280"),
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
    st.markdown('<div class="page-title"><span class="material-symbols-rounded">settings</span> Configuración</div>', unsafe_allow_html=True)
    st.markdown("<div style='height:0.75rem'></div>", unsafe_allow_html=True)

    user = st.session_state.get("auth_user")
    name, email_val = auth_user_display(user)

    with st.expander(":material/person: Perfil", expanded=True):
        c1, c2 = st.columns(2)
        with c1:
            st.text_input("Nombre completo", value=name, key="config_name")
        with c2:
            st.text_input("Email", value=email_val, key="config_email", disabled=True)
        if st.button("Guardar Perfil", icon=":material/save:", key="save_profile"):
            st.success(":material/check_circle: Perfil actualizado correctamente.")

    with st.expander(":material/notifications: Notificaciones", expanded=True):
        st.toggle("Notificaciones de tareas",    value=True,  key="notif_tasks")
        st.toggle("Recordatorios diarios",        value=True,  key="notif_daily")
        st.toggle("Actualizaciones de proyectos", value=False, key="notif_projects")
        st.toggle("Mensajes del equipo",          value=True,  key="notif_team")
        if st.button("Guardar Notificaciones", icon=":material/save:", key="save_notifs"):
            st.success(":material/check_circle: Preferencias guardadas.")

    with st.expander(":material/palette: Apariencia", expanded=False):
        def _apply_dark():
            st.session_state.dark_mode = st.session_state._cfg_dark

        st.toggle(":material/dark_mode: Modo Oscuro", value=st.session_state.dark_mode,
                   key="_cfg_dark", on_change=_apply_dark)
        st.markdown(
            '<div class="config-hint">También puedes alternar el tema desde el panel lateral.</div>',
            unsafe_allow_html=True)

    with st.expander(":material/folder_open: Gestión de Datos", expanded=False):
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
            if st.button("Datos de ejemplo", icon=":material/refresh:", key="reset_data", use_container_width=True):
                from database import _exec
                _exec("DELETE FROM tasks")
                seed_sample_data()
                st.session_state.tasks = db_load_tasks()
                st.success(":material/check_circle: Datos de ejemplo restaurados.")
                st.rerun()

    with st.expander(":material/power: Base de Datos (Supabase)", expanded=False):
        status_html = (
            '<span style="color:#16a34a;font-weight:600;">:material/check_circle: Conectado a Supabase</span>'
            if st.session_state.db_ok
            else '<span style="color:#ef4444;font-weight:600;">:material/cancel: Sin conexión</span>'
        )
        st.markdown(f"""
        <div class="config-info">
            <div style="margin-bottom:0.5rem;"><b>Estado:</b> {status_html}</div>
            <div><b>Host:</b> db.wopthjsdceattleaeczt.supabase.co:5432</div>
            <div><b>Base de datos:</b> postgres</div>
            <div><b>Usuario:</b> postgres</div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Reconectar", icon=":material/refresh:", key="reconnect_db"):
            st.cache_resource.clear()
            st.session_state.db_ok = False
            st.rerun()

    with st.expander("🔐 Cuenta", expanded=False):
        st.markdown(
            f'<div class="config-info"><b>Email:</b> {email_val}<br>'
            f'<b>Proveedor:</b> Supabase Auth</div>',
            unsafe_allow_html=True,
        )
        st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
        if st.button("Cerrar sesión", icon=":material/logout:", key="config_logout", use_container_width=False):
            auth_logout()
            st.rerun()


# ══════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════

def main() -> None:
    init_session_state()

    # ── Guard de autenticación ─────────────────────────────────────────────
    # Si no hay usuario en session_state, intentar restaurar desde Supabase.
    if not st.session_state.get("auth_user"):
        user = auth_current_user()
        if user:
            st.session_state.auth_user = user
            # Recargar tareas y equipos del usuario recién restaurado
            if not st.session_state.db_ok:
                ok = init_db()
                st.session_state.db_ok = ok
                if ok:
                    seed_sample_data()
            st.session_state.tasks = db_load_tasks()
            st.session_state.teams = db_load_teams()
        else:
            # Usuario no autenticado → mostrar páginas de auth
            render_auth()
            return

    # ── App principal (usuario autenticado) ───────────────────────────────
    inject_css()
    render_sidebar()

    {
        "Dashboard":     render_dashboard,
        "Tareas":        render_tasks_page,
        "Nueva Tarea":   render_new_task_page,
        "Calendario":    render_calendar_page,
        "Equipo":        render_team_page,
        "Recordatorios": render_reminders_page,
        "Actividad":     render_activity_page,
        "Configuración": render_config_page,
    }.get(st.session_state.active_page, render_dashboard)()


if __name__ == "__main__":
    main()