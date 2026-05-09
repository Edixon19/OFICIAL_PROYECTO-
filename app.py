"""
GestorPro - Gestor de Tareas con Streamlit + Supabase (PostgreSQL)
==================================================================
Versión 1.2
Autores: GestorPro, equipo del segundo semestre UTEDÉ
"""

import json
from datetime import datetime, date

import streamlit as st

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
    CSS + JS con tres capas de protección para el sidebar fijo:

    CAPA 1 — CSS exhaustivo: cubre todos los data-testid conocidos del botón
             de colapsar con display:none, pointer-events:none y opacity:0.
    CAPA 2 — CSS en aria-expanded=false: si Streamlit colapsa el sidebar,
             se fuerza transform:none y left:0 para mantenerlo visible.
    CAPA 3 — JavaScript MutationObserver: elimina el botón cada vez que
             Streamlit lo vuelva a insertar tras un rerun, y revierte
             cualquier estado colapsado en tiempo real.
    """
    theme    = THEMES["dark"] if st.session_state.dark_mode else THEMES["light"]
    css_vars = "\n".join(f"    {k}: {v};" for k, v in theme.items())

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
       SIDEBAR FIJO — CAPA 1: CSS exhaustivo
       Cubre todos los selectores conocidos del
       botón de colapsar en distintas versiones
       de Streamlit. Se usa pointer-events:none
       como respaldo por si display:none falla.
    ══════════════════════════════════════════ */
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

    /* CAPA 2 — CSS aria-expanded */
    section[data-testid="stSidebar"][aria-expanded="false"] {{
        transform: none !important;
        left: 0 !important;
        min-width: 240px !important;
        visibility: visible !important;
        display: block !important;
    }}

    /* ── Sidebar general ── */
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

    /* ── Main content ── */
    .main .block-container {{
        padding: 1.5rem 2rem !important;
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

    /* ── Date input ── */
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
       JERARQUÍA DE BOTONES — 4 niveles cognitivos
       Nivel 1 Primary   → gradiente naranja-teal  (acción principal / CTA)
       Nivel 2 Secondary → borde teal, fondo transp (acción reversible)
       Nivel 3 Ghost     → borde sutil, texto muted  (cancelar / bajo peso)
       Nivel 4 Danger    → rojo                      (destructivo)
    ══════════════════════════════════════════ */

    /* ── Nivel 2 SECONDARY: base predeterminada para todos los botones ── */
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

    /* ── Nivel 1 PRIMARY: CTAs principales ── */
    /* Streamlit expone el key como clase .st-key en el wrapper del widget */
    .st-key-btn_create_task button,
    .st-key-dash_new_task button,
    .st-key-dash_new_team button,
    .st-key-open_new_task button,
    .st-key-open_new_team button,
    .st-key-btn_create_team button,
    .st-key-new_reminder_btn button,
    .st-key-save_profile button,
    .st-key-save_notifs button,
    .st-key-refresh_activity button,
    .st-key-reconnect_db button {{
        background: #262525 !important;
        color: white !important;
        border: none !important;
         
    }}
    .st-key-btn_create_task button:hover,
    .st-key-dash_new_task button:hover,
    .st-key-dash_new_team button:hover,
    .st-key-open_new_task button:hover,
    .st-key-open_new_team button:hover,
    .st-key-btn_create_team button:hover,
    .st-key-new_reminder_btn button:hover,
    .st-key-save_profile button:hover,
    .st-key-save_notifs button:hover,
    .st-key-refresh_activity button:hover,
    .st-key-reconnect_db button:hover {{
        background: #262525 !important;
        transform: translateY(-1px) !important;
    }}

    /* save_{{taskid}} (guardar edicion tarea) — Primary */
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

    /* ── Nivel 3 GHOST: cancelar / bajo peso visual ── */
    .st-key-btn_cancel_new button,
    .st-key-btn_cancel_team button,
    [class*="st-key-cancel_edit_"] button,
    [class*="st-key-confirm_no_"] button,
    [class*="st-key-conf_no_team_"] button {{
        background: transparent !important;
        color: var(--text-secondary) !important;
        border: 1.5px solid var(--border-color) !important;
        box-shadow: none !important;
    }}
    .st-key-btn_cancel_new button:hover,
    .st-key-btn_cancel_team button:hover,
    [class*="st-key-cancel_edit_"] button:hover,
    [class*="st-key-confirm_no_"] button:hover,
    [class*="st-key-conf_no_team_"] button:hover {{
        background: var(--hover-bg) !important;
        transform: none !important;
        box-shadow: none !important;
    }}

    /* ── Nivel 4 DANGER: acciones destructivas ── */
    [class*="st-key-delete_btn_"] button,
    [class*="st-key-del_team_"] button,
    [class*="st-key-confirm_yes_"] button,
    [class*="st-key-conf_del_team_"] button,
    [class*="st-key-remove_member_"] button {{
        background: rgba(239,68,68,0.08) !important;
        color: #ef4444 !important;
        border: 1.5px solid rgba(239,68,68,0.4) !important;
        box-shadow: none !important;
    }}
    [class*="st-key-delete_btn_"] button:hover,
    [class*="st-key-del_team_"] button:hover,
    [class*="st-key-confirm_yes_"] button:hover,
    [class*="st-key-conf_del_team_"] button:hover,
    [class*="st-key-remove_member_"] button:hover {{
        background: rgba(239,68,68,0.16) !important;
        border-color: #ef4444 !important;
        box-shadow: 0 3px 10px rgba(239,68,68,0.25) !important;
        transform: translateY(-1px) !important;
    }}

    /* ── reset_data — Advertencia (accion reversible pero llamativa) ── */
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

    /* ── Download button (Secondary igual) ── */
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
    </style>
    """

    # ══════════════════════════════════════════
    # CAPA 3 — JavaScript MutationObserver
    # ══════════════════════════════════════════
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
                    el.style.width = '0';
                    el.style.height = '0';
                    el.style.overflow = 'hidden';
                    el.style.position = 'absolute';
                });
            });

            var sidebar = document.querySelector('section[data-testid="stSidebar"]');
            if (sidebar) {
                if (sidebar.getAttribute('aria-expanded') === 'false') {
                    sidebar.setAttribute('aria-expanded', 'true');
                }
                sidebar.style.transform = 'none';
                sidebar.style.left = '0';
                sidebar.style.minWidth = '240px';
                sidebar.style.visibility = 'visible';
                sidebar.style.display = 'block';
            }
        }

        removeCollapseBtn();

        var observer = new MutationObserver(function(mutations) {
            removeCollapseBtn();
        });
        observer.observe(document.body, { childList: true, subtree: true });

        var count = 0;
        var interval = setInterval(function() {
            removeCollapseBtn();
            count++;
            if (count >= 10) clearInterval(interval);
        }, 500);
    })();
    </script>
    """

    st.markdown(css, unsafe_allow_html=True)
    st.markdown(js, unsafe_allow_html=True)


# ══════════════════════════════════════════════
#  COMPONENTES UI
# ══════════════════════════════════════════════

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

        alert_txt = ""
        if is_overdue:
            alert_txt = "  🔴 VENCIDA"
        elif is_today:
            alert_txt = "  🟡 HOY"

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
                    📅 {dd} &nbsp; {cat_html}
                    <span style="font-weight:600;">{alert_txt}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

        with col_badge:
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

    with st.expander("👤 Perfil", expanded=True):
        c1, c2 = st.columns(2)
        with c1:
            st.text_input("Nombre completo", value="Usuario Demo", key="config_name")
        with c2:
            st.text_input("Email", value="usuario@gestorpro.com", key="config_email")
        if st.button("💾 Guardar Perfil", key="save_profile"):
            st.success("✅ Perfil actualizado correctamente.")

    with st.expander("🔔 Notificaciones", expanded=True):
        st.toggle("Notificaciones de tareas",     value=True,  key="notif_tasks")
        st.toggle("Recordatorios diarios",         value=True,  key="notif_daily")
        st.toggle("Actualizaciones de proyectos",  value=False, key="notif_projects")
        st.toggle("Mensajes del equipo",           value=True,  key="notif_team")
        if st.button("💾 Guardar Notificaciones", key="save_notifs"):
            st.success("✅ Preferencias guardadas.")

    with st.expander("🎨 Apariencia", expanded=False):
        def _apply_dark():
            st.session_state.dark_mode = st.session_state._cfg_dark

        st.toggle("🌙 Modo Oscuro", value=st.session_state.dark_mode,
                   key="_cfg_dark", on_change=_apply_dark)
        st.markdown('<div class="config-hint">También puedes alternar el tema desde el panel lateral.</div>',
                    unsafe_allow_html=True)

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
                from database import _exec
                _exec("DELETE FROM tasks")
                seed_sample_data()
                st.session_state.tasks = db_load_tasks()
                st.success("✅ Datos de ejemplo restaurados.")
                st.rerun()

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