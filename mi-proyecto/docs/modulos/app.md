# 📋 Módulo: app.py

`app.py` es el punto de entrada de GestorPro. Contiene toda la configuración de Streamlit, el sistema de temas, los componentes de UI reutilizables y las páginas de la aplicación.

---

## Constantes globales

```python
PRIORITIES     = ["High", "Medium", "Low"]
CATEGORIES     = ["Trabajo", "Personal", "Compras", "Diseño", "Desarrollo", "Otro"]
STATUS_OPTIONS = ["Pendiente", "Activa", "Completada"]
TEAM_ROLES     = ["Líder", "Miembro", "Editor", "Viewer"]
```

Los colores de cada prioridad y categoría están en `PRIORITY_COLORS` y `CATEGORY_COLORS`.

---

## Función: `init_session_state()`

Inicializa todos los valores del `st.session_state` con sus defaults si no existen, conecta la base de datos y carga tareas y equipos.

```python
def init_session_state() -> None:
    defaults = {
        "dark_mode": False,
        "active_page": "Dashboard",
        "filter_status": "Todas",
        ...
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
```

!!! warning "Llamada en cada rerun"
    `init_session_state()` se invoca en cada rerun de Streamlit, por lo que `db_load_tasks()` y `db_load_teams()` se ejecutan siempre para mantener la UI sincronizada con la BD.

---

## Función: `inject_css()`

Genera e inyecta el CSS global y el JavaScript MutationObserver. Recibe el tema activo del estado y construye las variables CSS:

```python
def inject_css() -> None:
    theme    = THEMES["dark"] if st.session_state.dark_mode else THEMES["light"]
    css_vars = "\n".join(f"    {k}: {v};" for k, v in theme.items())
    # Genera <style>...</style> con todas las reglas
    st.markdown(css, unsafe_allow_html=True)
    st.markdown(js,  unsafe_allow_html=True)
```

---

## Componentes de UI

### `render_task_card(task: dict)`

Renderiza una tarjeta de tarea con:
- Título, descripción, badges de prioridad/estado y etiquetas
- Botones de acción: ✓ Completar / ↩ Reactivar, ✏️ Editar, 🗑️ Eliminar
- Flujo de confirmación de borrado inline
- Formulario de edición desplegable (llama a `render_edit_form`)

### `render_edit_form(task: dict)`

Formulario inline para editar todos los campos de una tarea. Se muestra bajo la tarjeta cuando `st.session_state.editing_task_id == task["id"]`.

### `render_new_task_form()`

Formulario de creación de tarea nueva con todos los campos. Se muestra en la parte superior de la página Tareas cuando `st.session_state.show_new_task_form == True`.

---

## Función: `render_sidebar()`

Renderiza el panel lateral con:
- Logo **GestorPro**
- Indicador de estado de BD (🟢/🔴)
- Botones de navegación para las 6 páginas principales
- Toggle de modo oscuro
- Botón de Configuración
- Resumen rápido de estadísticas (total, completadas, pendientes, tasa)

---

## Páginas

| Función | Ruta | Descripción |
|---|---|---|
| `render_dashboard()` | Dashboard | Acciones rápidas, 4 KPIs, gráfica de categorías, distribución por estado, tareas recientes |
| `render_tasks_page()` | Tareas | Listado con búsqueda, filtros por estado y categoría, CRUD completo |
| `render_calendar_page()` | Calendario | Tareas agrupadas cronológicamente por `due_date` |
| `render_team_page()` | Equipo | CRUD de equipos, gestión de miembros con roles, mover entre equipos |
| `render_reminders_page()` | Recordatorios | Tareas con `due_date` ordenadas; alertas para vencidas y de hoy |
| `render_activity_page()` | Actividad | Log de las últimas 30 acciones con iconos y tiempo relativo |
| `render_config_page()` | Configuración | Perfil, notificaciones, apariencia, exportación JSON, reconexión BD |

---

## Función: `main()`

Punto de entrada de la aplicación:

```python
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
```

Usa un diccionario de funciones para despachar la página activa sin `if/elif` anidados.
