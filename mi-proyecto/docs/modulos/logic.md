# ⚙️ Módulo: logic.py

`logic.py` contiene la lógica de negocio de GestorPro. Actúa como intermediario entre `app.py` y `database.py`, garantizando que `st.session_state.tasks` siempre refleje el estado real de la base de datos tras cada operación.

---

## Helpers CRUD

Todos los helpers CRUD de este módulo:
1. Llaman a la función correspondiente de `database.py`
2. Si la operación fue exitosa, refrescan `st.session_state.tasks`

### `add_task(title, description, priority, category, status, due_date, assignee, tags) → None`

```python
def add_task(...) -> None:
    if db_add_task(...):
        st.session_state.tasks = db_load_tasks()
```

Crea una nueva tarea y sincroniza la lista en sesión.

### `update_task(task_id, **kwargs) → None`

Actualiza los campos especificados de la tarea y recarga la lista.

### `delete_task(task_id, task_title="") → None`

Elimina la tarea y recarga la lista.

### `toggle_task_status(task_id, current_status, title="") → None`

Alterna el estado de la tarea entre `"Activa"` y `"Completada"`.

---

## Filtrado y Estadísticas

### `get_filtered_tasks(status_filter, category_filter, search) → list`

```python
def get_filtered_tasks(status_filter="Todas", category_filter="Todas", search="") -> list:
```

Filtra `st.session_state.tasks` en memoria (sin consultar la BD) y retorna la lista ordenada por prioridad:

| Filtro | Comportamiento |
|---|---|
| `status_filter` | Filtra por campo `"status"` si ≠ `"Todas"` |
| `category_filter` | Filtra por campo `"category"` si ≠ `"Todas"` |
| `search` | Busca en `title`, `description` y `tags` (case-insensitive) |

El resultado se ordena: **High → Medium → Low**.

### `get_stats() → dict`

Calcula estadísticas de las tareas en sesión:

```python
{
    "total":           int,   # Total de tareas
    "completed":       int,   # Tareas con status == "Completada"
    "pending":         int,   # Tareas con status == "Pendiente"
    "active":          int,   # Tareas con status == "Activa"
    "completion_rate": int,   # % de tareas completadas (0-100)
}
```

---

## Badges HTML

Estas funciones retornan HTML seguro para renderizar con `unsafe_allow_html=True`.

### `render_priority_badge(priority: str) → str`

Genera un badge con color y emoji según la prioridad:

| Prioridad | Emoji | Clase CSS |
|---|---|---|
| High | 🔴 | `badge-priority-high` |
| Medium | 🟡 | `badge-priority-medium` |
| Low | 🟢 | `badge-priority-low` |

### `render_status_badge(status: str) → str`

Genera un badge para el estado de la tarea:

| Estado | Emoji | Clase CSS |
|---|---|---|
| Pendiente | ⏳ | `badge-status-pendiente` |
| Activa | 🔵 | `badge-status-activa` |
| Completada | ✅ | `badge-status-completada` |

### `render_tag_badge(tag: str) → str`

Genera un badge gris con el texto `#tag`.

### `render_role_badge(role: str) → str`

Genera un badge con el color del rol de equipo:

| Rol | Color |
|---|---|
| Líder | `#e55a2b` (naranja) |
| Editor | `#0d9488` (teal) |
| Miembro | `#3b82f6` (azul) |
| Viewer | `#6b7280` (gris) |

---

## Utilidades de formato

### `_hex_to_rgb(hex_color: str) → tuple`

```python
_hex_to_rgb("#e55a2b")  # → (229, 90, 43)
```

Convierte un color HEX a tupla RGB para usarla en `rgba()` en CSS inline.

### `_time_ago(created_at_str: str) → str`

Convierte una fecha ISO a texto relativo legible:

| Diferencia | Salida |
|---|---|
| < 60 seg | `"Hace N seg"` |
| < 1 hora | `"Hace N min"` |
| < 1 día | `"Hace N h"` |
| ≥ 1 día | `"Hace N días"` |
| Error | `"Recientemente"` |
