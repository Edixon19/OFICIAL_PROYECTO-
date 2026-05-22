
#GestorPro, Capa de acceso a datos


import os
import json
import uuid
from datetime import datetime, date

import streamlit as st
from auth import auth_user_id

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

    # Prioridad 3: Fallback, URL completa
    return "postgresql://postgres.wopthjsdceattleaeczt:utede2026sem2@aws-1-us-east-2.pooler.supabase.com:6543/postgres"


# ─────────────────────────────────────────────
# CONEXIÓN CACHEADA (Optimización Pooler)
# ─────────────────────────────────────────────

@st.cache_resource(ttl=600)  # Refresca la conexión cada 10 min
def get_connection():
    """Abre y mantiene la conexión al Pooler de Supabase."""
    if not PSYCOPG2_OK:
        return None
    try:
        conn = psycopg2.connect(
            _get_dsn(),
            connect_timeout=10,
            sslmode="require",  # Obligatorio para Pooler en muchos casos
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
# INICIALIZACIÓN
# ─────────────────────────────────────────────

def init_db() -> bool:
    conn = get_connection()
    if conn is None:
        return False
    return True


# ══════════════════════════════════════════════
#  EJECUCIÓN SQL GENÉRICA
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


# ══════════════════════════════════════════════
#  TAREAS
# ══════════════════════════════════════════════

def _normalize_task_row(r: dict) -> dict:
    """Normaliza una fila de tarea (tags, fechas)."""
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
    return r


def db_load_tasks(team_id=None) -> list:
    """Carga tareas filtradas por equipo.
    team_id=None  → tareas personales (team_id IS NULL) del usuario actual.
    team_id=<uuid> → tareas del equipo indicado.
    """
    user_id = auth_user_id()
    if team_id is None:
        rows = _exec(
            "SELECT * FROM tasks WHERE team_id IS NULL AND user_id = %s ORDER BY "
            "CASE priority WHEN 'High' THEN 1 WHEN 'Medium' THEN 2 ELSE 3 END, "
            "created_at DESC",
            (user_id,), fetch="all",
        )
    else:
        rows = _exec(
            "SELECT * FROM tasks WHERE team_id = %s ORDER BY "
            "CASE priority WHEN 'High' THEN 1 WHEN 'Medium' THEN 2 ELSE 3 END, "
            "created_at DESC",
            (team_id,), fetch="all",
        )
    return [_normalize_task_row(r) for r in rows]


def db_add_task(title, description, priority, category, status, due_date,
                assignee, tags, team_id=None) -> bool:
    task_id = str(uuid.uuid4())
    user_id = auth_user_id()
    ok = _exec(
        """INSERT INTO tasks (id,title,description,priority,category,status,
           due_date,assignee,tags,created_at,user_id,team_id)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s,%s,%s)""",
        (task_id, title.strip(), description.strip(), priority, category, status,
         due_date.isoformat() if due_date else date.today().isoformat(),
         assignee.strip(), json.dumps(tags, ensure_ascii=False),
         datetime.now().isoformat(), user_id, team_id),
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


# ══════════════════════════════════════════════
#  EQUIPOS
# ══════════════════════════════════════════════

def db_get_user_teams() -> list:
    """Devuelve los equipos a los que pertenece el usuario actual.
    Retorna lista de dicts con id y name.
    """
    user_id = auth_user_id()
    if not user_id:
        return []
    return _exec(
        "SELECT t.id, t.name FROM teams t "
        "JOIN team_members tm ON t.id = tm.team_id "
        "WHERE tm.user_id = %s "
        "ORDER BY t.name",
        (user_id,), fetch="all",
    )


def db_load_teams() -> list:
    """Carga solo los equipos a los que pertenece el usuario actual,
    con sus miembros (incluyendo nombre obtenido de auth.users).
    """
    user_id = auth_user_id()
    if not user_id:
        return []
    teams = _exec(
        "SELECT t.* FROM teams t "
        "JOIN team_members tm ON t.id = tm.team_id "
        "WHERE tm.user_id = %s "
        "ORDER BY t.created_at DESC",
        (user_id,), fetch="all",
    )
    for team in teams:
        if hasattr(team.get("created_at"), "isoformat"):
            team["created_at"] = team["created_at"].isoformat()
        # Cargar miembros con nombre de auth.users
        members = _exec(
            "SELECT tm.id, tm.team_id, tm.user_id, tm.role, tm.joined_at, "
            "       u.email, "
            "       COALESCE(u.raw_user_meta_data->>'full_name', "
            "                u.raw_user_meta_data->>'name', "
            "                split_part(u.email, '@', 1)) AS member_name "
            "FROM team_members tm "
            "JOIN auth.users u ON tm.user_id = u.id "
            "WHERE tm.team_id = %s "
            "ORDER BY CASE tm.role WHEN 'Líder' THEN 0 WHEN 'Editor' THEN 1 "
            "         WHEN 'Miembro' THEN 2 ELSE 3 END",
            (team["id"],), fetch="all",
        )
        for m in members:
            if hasattr(m.get("joined_at"), "isoformat"):
                m["joined_at"] = m["joined_at"].isoformat()
        team["members"] = members
    return teams


def db_get_user_by_email(email: str) -> dict:
    """Busca un usuario registrado por email. Retorna dict con id, email, nombre o {}."""
    row = _exec(
        "SELECT id, email, "
        "       COALESCE(raw_user_meta_data->>'full_name', "
        "                raw_user_meta_data->>'name', "
        "                split_part(email, '@', 1)) AS display_name "
        "FROM auth.users WHERE email = %s",
        (email.strip().lower(),), fetch="one",
    )
    return row


def db_create_team(name: str, description: str) -> bool:
    """Crea un equipo y añade al usuario actual como Líder."""
    team_id = str(uuid.uuid4())
    user_id = auth_user_id()
    ok = _exec("INSERT INTO teams (id,name,description,user_id) VALUES (%s,%s,%s,%s)",
               (team_id, name.strip(), description.strip(), user_id))
    if ok:
        # Auto-añadir al creador como Líder
        _exec("INSERT INTO team_members (id,team_id,user_id,role) VALUES (%s,%s,%s,%s)",
              (str(uuid.uuid4()), team_id, user_id, "Líder"))
        _log_activity("Usuario", "creó el equipo", "equipo", name.strip())
    return bool(ok)


def db_add_member(team_id: str, email: str, role: str, team_name: str = "") -> tuple:
    """Añade un miembro al equipo por email.
    Retorna (ok: bool, error_msg: str | None).
    """
    target = db_get_user_by_email(email)
    if not target or not target.get("id"):
        return False, "No se encontró un usuario registrado con ese correo."

    target_user_id = str(target["id"])
    display_name = target.get("display_name", email)

    # Verificar si ya es miembro
    existing = _exec(
        "SELECT id FROM team_members WHERE team_id = %s AND user_id = %s",
        (team_id, target_user_id), fetch="one",
    )
    if existing:
        return False, f"{display_name} ya es miembro de este equipo."

    ok = _exec(
        "INSERT INTO team_members (id,team_id,user_id,role) VALUES (%s,%s,%s,%s)",
        (str(uuid.uuid4()), team_id, target_user_id, role),
    )
    if ok:
        _log_activity("Líder", f"agregó a {display_name} al equipo", "equipo", team_name)
    return bool(ok), None


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
    """Elimina un equipo. Solo el creador puede hacerlo (verificado en la UI)."""
    ok = _exec("DELETE FROM teams WHERE id = %s", (team_id,))
    if ok:
        _log_activity("Usuario", "eliminó el equipo", "equipo", team_name)
    return bool(ok)


def db_is_team_owner(team_id: str) -> bool:
    """Verifica si el usuario actual es el creador del equipo."""
    user_id = auth_user_id()
    if not user_id:
        return False
    row = _exec("SELECT id FROM teams WHERE id = %s AND user_id = %s",
                (team_id, user_id), fetch="one")
    return bool(row)


# ══════════════════════════════════════════════
#  ACTIVIDAD
# ══════════════════════════════════════════════

def _log_activity(user_name: str, action: str, entity_type: str = "",
                  entity_name: str = "", detail: str = "") -> None:
    user_id = auth_user_id()
    _exec("""INSERT INTO activity_log (id,user_name,action,entity_type,entity_name,detail,user_id)
             VALUES (%s,%s,%s,%s,%s,%s,%s)""",
          (str(uuid.uuid4()), user_name, action, entity_type, entity_name, detail, user_id))


def db_load_activity(limit: int = 30) -> list:
    rows = _exec("SELECT * FROM activity_log ORDER BY created_at DESC LIMIT %s",
                 (limit,), fetch="all")
    for r in rows:
        if hasattr(r.get("created_at"), "isoformat"):
            r["created_at"] = r["created_at"].isoformat()
    return rows


# ══════════════════════════════════════════════
#  DATOS DE EJEMPLO (SEED)
# ══════════════════════════════════════════════

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
                     due_date,assignee,tags,created_at,user_id) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s,%s)""",
                  (t["id"], t["title"], t["description"], t["priority"], t["category"],
                   t["status"], t["due_date"], t["assignee"],
                   json.dumps(t["tags"]), t["created_at"], None))