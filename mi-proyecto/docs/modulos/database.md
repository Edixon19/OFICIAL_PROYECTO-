# 🗄️ Módulo: database.py

`database.py` es la capa de acceso a datos de GestorPro. Gestiona la conexión a Supabase (PostgreSQL) y expone funciones para cada operación CRUD sobre tareas, equipos, miembros y el log de actividad.

---

## Conexión

### `_get_dsn() → str`

Obtiene la cadena de conexión con la siguiente prioridad:

1. `st.secrets["supabase"]["url"]` (Streamlit Secrets)
2. Variable de entorno `DATABASE_URL`
3. URL de fallback hardcoded (solo desarrollo)

### `get_connection()`

```python
@st.cache_resource(ttl=600)
def get_connection():
    """Abre y mantiene la conexión al Pooler de Supabase."""
```

La conexión se cachea durante **10 minutos** con `@st.cache_resource`. Usa `sslmode="require"` y `autocommit=False`.

### `get_cursor(conn)`

Retorna un `RealDictCursor` que convierte las filas de PostgreSQL en diccionarios Python.

### `close_conn(conn)`

Cierra la conexión de forma segura, suprimiendo excepciones.

### `init_db() → bool`

Verifica que se puede obtener una conexión. Devuelve `True` si la BD está accesible.

---

## Función genérica: `_exec()`

```python
def _exec(sql: str, params=(), fetch: str = "none"):
```

Función central que ejecuta cualquier SQL. Maneja automáticamente:

| Parámetro `fetch` | Comportamiento |
|---|---|
| `"none"` | Ejecuta sin retorno (INSERT/UPDATE/DELETE) |
| `"all"` | Retorna lista de dicts con `fetchall()` |
| `"one"` | Retorna un dict con `fetchone()` |

En caso de error hace **rollback** y muestra `st.error()`.

---

## Operaciones de Tareas

### `db_load_tasks() → list`

Carga todas las tareas ordenadas por prioridad (High → Medium → Low) y fecha de creación descendente. Deserializa el campo `tags` (JSONB → lista Python) y normaliza fechas a string ISO.

### `db_add_task(title, description, priority, category, status, due_date, assignee, tags) → bool`

```python
# Genera UUID, inserta en PostgreSQL y registra en activity_log
task_id = str(uuid.uuid4())
_exec("INSERT INTO tasks (...) VALUES (...)", (...))
_log_activity(assignee, "creó la tarea", "tarea", title)
```

### `db_update_task(task_id: str, **kwargs) → bool`

Actualiza solo los campos pasados como `kwargs`. Serializa `tags` a JSON si está en los kwargs. Registra la acción en el log.

### `db_delete_task(task_id: str, task_title: str = "") → bool`

Elimina la tarea por ID y registra la acción en el log.

### `db_toggle_task_status(task_id: str, current_status: str, title: str = "") → bool`

Alterna el estado entre `"Completada"` y `"Activa"`. Registra la acción correspondiente en el log.

---

## Operaciones de Equipos

### `db_load_teams() → list`

Carga todos los equipos con sus miembros anidados en `team["members"]`.

### `db_create_team(name, description, leader_name) → bool`

Crea el equipo e inserta automáticamente al `leader_name` como `"Líder"`.

### `db_add_member(team_id, member_name, role, team_name) → bool`

Agrega un miembro con rol especificado a un equipo.

### `db_update_member_role(member_id, new_role, member_name) → bool`

Actualiza el rol de un miembro.

### `db_move_member(member_id, new_team_id, member_name, new_team_name) → bool`

Mueve un miembro a otro equipo, reiniciando su rol a `"Miembro"`.

### `db_remove_member(member_id, member_name, team_name) → bool`

Elimina un miembro de su equipo.

### `db_delete_team(team_id, team_name) → bool`

Elimina el equipo y todos sus miembros (por `ON DELETE CASCADE`).

---

## Actividad

### `_log_activity(user_name, action, entity_type, entity_name, detail) → None`

Función privada que inserta un registro en `activity_log`. Es llamada por todas las funciones CRUD.

### `db_load_activity(limit: int = 30) → list`

Retorna los últimos `limit` registros de actividad ordenados por fecha descendente.

---

## Datos de ejemplo (seed)

### `seed_sample_data() → None`

Si la tabla `tasks` está vacía, inserta 3 tareas de ejemplo:

- 🎨 **Diseñar interfaz de usuario** (High · Activa)
- 📄 **Revisar documentación del proyecto** (Medium · Activa)
- 🛒 **Comprar suministros de oficina** (Low · Pendiente)
