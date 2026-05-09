# 🏗️ Arquitectura del Sistema

Esta sección describe cómo está organizado GestorPro internamente: sus módulos, flujo de datos y decisiones de diseño.

---

## Diagrama general

```
┌─────────────────────────────────────────────────────┐
│                     app.py                          │
│   (Streamlit UI · Páginas · CSS · Session State)    │
│                                                     │
│  Dashboard │ Tareas │ Calendario │ Equipos │ ...     │
└────────────────────┬────────────────────────────────┘
                     │ importa
         ┌───────────┴───────────┐
         │                       │
   ┌─────▼──────┐         ┌──────▼──────┐
   │  logic.py  │         │ database.py │
   │  (CRUD     │─────────│  (SQL +     │
   │  + helpers │ importa │  Supabase)  │
   │  + badges) │         │             │
   └────────────┘         └──────┬──────┘
                                 │ psycopg2
                          ┌──────▼──────┐
                          │  Supabase   │
                          │ (PostgreSQL)│
                          └─────────────┘
```

---

## Responsabilidades por módulo

| Módulo | Responsabilidad |
|---|---|
| `app.py` | Configuración de Streamlit, inyección de CSS/JS, renderizado de páginas, gestión de `session_state` |
| `logic.py` | Wrappers CRUD que sincronizan `session_state`, filtrado de tareas, estadísticas, badges HTML |
| `database.py` | Conexión a Supabase, ejecución SQL, serialización de datos (JSON, fechas) |

---

## Flujo de datos

```
Usuario hace clic (ej: "Crear Tarea")
        │
        ▼
 app.py recibe el evento
        │
        ▼
 logic.py :: add_task()
   └─ database.py :: db_add_task()   ← INSERT en Supabase
   └─ database.py :: db_load_tasks() ← SELECT para refrescar
   └─ st.session_state.tasks = [...]  ← cache en memoria
        │
        ▼
 app.py llama st.rerun()  → UI se actualiza
```

---

## Gestión de estado (`session_state`)

GestorPro usa `st.session_state` como store en memoria. Los campos principales son:

| Clave | Tipo | Descripción |
|---|---|---|
| `tasks` | `list[dict]` | Lista completa de tareas cargadas desde BD |
| `teams` | `list[dict]` | Lista de equipos con sus miembros |
| `active_page` | `str` | Página activa del sidebar |
| `dark_mode` | `bool` | Tema claro/oscuro |
| `db_ok` | `bool` | Estado de conexión a Supabase |
| `editing_task_id` | `str\|None` | ID de la tarea en edición |
| `confirm_delete_id` | `str\|None` | ID de tarea pendiente de confirmar borrado |
| `show_new_task_form` | `bool` | Visibilidad del formulario de nueva tarea |
| `show_new_team_form` | `bool` | Visibilidad del formulario de nuevo equipo |
| `managing_team_id` | `str\|None` | Equipo con panel de gestión abierto |

---

## Conexión a Supabase

La conexión se gestiona en `database.py` con `@st.cache_resource(ttl=600)` para reutilizar la misma conexión durante 10 minutos:

```python
@st.cache_resource(ttl=600)
def get_connection():
    conn = psycopg2.connect(dsn, sslmode="require")
    conn.autocommit = False
    return conn
```

Todas las operaciones SQL pasan por la función genérica `_exec(sql, params, fetch)` que maneja commit, rollback y cierre de cursor automáticamente.

---

## Sistema de temas

Los temas (claro/oscuro) se implementan mediante **variables CSS personalizadas** (`--bg-main`, `--text-primary`, etc.) inyectadas dinámicamente con `st.markdown()` en cada rerun:

```python
THEMES = {
    "light": { "--bg-main": "#f8fafc", "--accent-primary": "#e55a2b", ... },
    "dark":  { "--bg-main": "#0f172a", "--accent-primary": "#e55a2b", ... },
}
```

---

## Jerarquía de botones (UI)

Los botones tienen 4 niveles cognitivos implementados con selectores CSS `.st-key-*`:

| Nivel | Estilo | Uso |
|---|---|---|
| **Primary** | Gradiente naranja-teal oscuro | Crear tarea, Crear equipo |
| **Secondary** | Borde teal, fondo transparente | Acciones secundarias (default) |
| **Ghost** | Borde sutil, texto muted | Cancelar, bajo peso visual |
| **Danger** | Rojo | Eliminar, acciones destructivas |

---

## Sidebar fijo

El sidebar usa 3 capas para permanecer siempre visible:

1. **CSS exhaustivo** — oculta el botón de colapsar con `display:none`
2. **CSS aria-expanded** — revierte el estado colapsado
3. **JavaScript MutationObserver** — elimina el botón en tiempo real tras cada rerun
