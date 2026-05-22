"""
GestorPro — Lógica de negocio y helpers de UI

Contiene:
  - Helpers CRUD (envoltorios sobre database.py que actualizan session_state)
  - Filtrado y estadísticas de tareas
  - Renderizado de badges HTML
  - Utilidades de formato (_hex_to_rgb, _time_ago)
"""

from datetime import datetime

import streamlit as st

from database import (
    db_add_task,
    db_update_task,
    db_delete_task,
    db_toggle_task_status,
    db_load_tasks,
)


# ══════════════════════════════════════════════
#  HELPERS CRUD
#  (llaman a database.py y sincronizan session_state)
# ══════════════════════════════════════════════

def add_task(title, description, priority, category, status, due_date, assignee, tags,
             team_id=None) -> None:
    # Usa el equipo activo de la sesión si no se especifica
    if team_id is None:
        team_id = st.session_state.get("active_team_id")
    if db_add_task(title, description, priority, category, status, due_date, assignee, tags, team_id):
        st.session_state.tasks = db_load_tasks(team_id=team_id)


def update_task(task_id, **kwargs) -> None:
    if db_update_task(task_id, **kwargs):
        st.session_state.tasks = db_load_tasks(team_id=st.session_state.get("active_team_id"))


def delete_task(task_id, task_title="") -> None:
    if db_delete_task(task_id, task_title):
        st.session_state.tasks = db_load_tasks(team_id=st.session_state.get("active_team_id"))


def toggle_task_status(task_id, current_status, title="") -> None:
    if db_toggle_task_status(task_id, current_status, title):
        st.session_state.tasks = db_load_tasks(team_id=st.session_state.get("active_team_id"))


# ══════════════════════════════════════════════
#  FILTRADO Y ESTADÍSTICAS
# ══════════════════════════════════════════════

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
                 or s in t.get("description", "").lower()
                 or s in " ".join(t.get("tags", [])).lower()]
    return sorted(tasks, key=lambda x: prio.get(x["priority"], 99))


def get_stats() -> dict:
    tasks     = st.session_state.tasks
    total     = len(tasks)
    completed = sum(1 for t in tasks if t["status"] == "Completada")
    pending   = sum(1 for t in tasks if t["status"] == "Pendiente")
    active    = sum(1 for t in tasks if t["status"] == "Activa")
    return {
        "total":           total,
        "completed":       completed,
        "pending":         pending,
        "active":          active,
        "completion_rate": round(completed / total * 100) if total else 0,
    }


# ══════════════════════════════════════════════
#  BADGES HTML
# ══════════════════════════════════════════════

def render_priority_badge(priority: str) -> str:
    icons = {
        "Alta": '<span class="material-symbols-rounded" style="font-size: 1.1em; vertical-align: middle;">keyboard_double_arrow_up</span>',
        "Media": '<span class="material-symbols-rounded" style="font-size: 1.1em; vertical-align: middle;">drag_handle</span>',
        "Baja": '<span class="material-symbols-rounded" style="font-size: 1.1em; vertical-align: middle;">keyboard_double_arrow_down</span>',
        "High": '<span class="material-symbols-rounded" style="font-size: 1.1em; vertical-align: middle;">keyboard_double_arrow_up</span>',
        "Medium": '<span class="material-symbols-rounded" style="font-size: 1.1em; vertical-align: middle;">drag_handle</span>',
        "Low": '<span class="material-symbols-rounded" style="font-size: 1.1em; vertical-align: middle;">keyboard_double_arrow_down</span>'
    }
    display_priority = {"High": "Alta", "Medium": "Media", "Low": "Baja"}.get(priority, priority)
    return (f'<span class="badge badge-priority-{priority.lower()}">'
            f'{icons.get(priority, "")} {display_priority}</span>')


def render_status_badge(status: str) -> str:
    icons = {
        "Pendiente": '<span class="material-symbols-rounded" style="font-size: 1.1em; vertical-align: middle;">hourglass_empty</span>',
        "Activa": '<span class="material-symbols-rounded" style="font-size: 1.1em; vertical-align: middle;">play_circle</span>',
        "Completada": '<span class="material-symbols-rounded" style="font-size: 1.1em; vertical-align: middle;">check_circle</span>'
    }
    return (f'<span class="badge badge-status-{status.lower()}">'
            f'{icons.get(status, "")} {status}</span>')


def render_tag_badge(tag: str) -> str:
    return f'<span class="badge badge-tag">#{tag}</span>'


def render_role_badge(role: str) -> str:
    colors = {"Líder": "#e55a2b", "Editor": "#0d9488", "Viewer": "#6b7280", "Miembro": "#3b82f6"}
    color  = colors.get(role, "#6b7280")
    return (f'<span class="badge" style="background:rgba(0,0,0,0.06);'
            f'color:{color};border:1px solid {color}40;">{role}</span>')


# ══════════════════════════════════════════════
#  UTILIDADES DE FORMATO
# ══════════════════════════════════════════════

def _hex_to_rgb(hex_color: str):
    h = hex_color.lstrip("#")
    try:
        return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
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