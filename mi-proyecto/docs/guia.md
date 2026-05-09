# 🚀 Guía de Uso — GestorPro

Esta guía explica cómo usar cada sección de GestorPro paso a paso.

---

## 📊 Dashboard

Al abrir la aplicación aterrizas en el **Dashboard**. Aquí encontrarás:

- **Acciones rápidas** — Botones para crear una tarea o un equipo en un clic
- **4 KPIs en tiempo real** — Tareas completadas, pendientes, activas y tasa de finalización
- **Gráfica de barras** — Distribución de tareas por categoría
- **Distribución por estado** — Barras de progreso con porcentajes
- **Tareas recientes** — Las últimas 4 tareas creadas

---

## ✅ Tareas

### Crear una tarea

1. Haz clic en **➕ Nueva Tarea** (arriba a la derecha)
2. Rellena el formulario:
   - **Título** *(obligatorio)*
   - Descripción, asignado a, prioridad, categoría, estado inicial, fecha límite
   - Etiquetas separadas por coma (ej: `diseño, urgente`)
3. Haz clic en **✅ Crear Tarea**

### Filtrar tareas

- Usa la **barra de búsqueda** para filtrar por título, descripción o etiquetas
- Selecciona un **estado** con los botones de radio (Todas / Activa / Pendiente / Completada)
- Usa el **selector de categoría** para filtrar por área

### Completar una tarea

Haz clic en **✓ Completar** en la tarjeta de la tarea. La tarjeta aparecerá con texto tachado y opacidad reducida. Para revertirla haz clic en **↩ Reactivar**.

### Editar una tarea

1. Haz clic en **✏️ Editar** en la tarjeta
2. Modifica los campos en el formulario desplegable
3. Haz clic en **💾 Guardar**

### Eliminar una tarea

1. Haz clic en **🗑️ Eliminar**
2. Confirma haciendo clic en **Sí, eliminar** en la caja de confirmación

!!! danger "Atención"
    La eliminación de tareas es permanente y no se puede deshacer.

---

## 📅 Calendario

Muestra todas las tareas que tienen fecha límite asignada, agrupadas por día en orden cronológico. Las tareas del **día de hoy** se marcan con 🔵 HOY. Cada tarea muestra un borde de color según su categoría.

---

## 👥 Equipos

### Crear un equipo

1. Haz clic en **➕ Nuevo Equipo**
2. Ingresa nombre, descripción y tu nombre (serás el Líder)
3. Haz clic en **✅ Crear Equipo**

### Gestionar un equipo

Haz clic en **⚙️ Gestionar** en la tarjeta del equipo para abrir el panel:

=== "Agregar miembro"
    - Ingresa el nombre del miembro
    - Selecciona su rol: Líder, Miembro, Editor o Viewer
    - Haz clic en **Agregar**

=== "Gestionar miembros"
    - **Cambiar rol**: Selecciona el nuevo rol en el desplegable y confirma con ✓
    - **Mover a otro equipo**: Selecciona el equipo destino y haz clic en ↗ Mover
    - **Remover**: Haz clic en ✕ junto al miembro

### Roles disponibles

| Rol | Permisos |
|---|---|
| 👑 **Líder** | Gestiona el equipo y sus miembros |
| ✏️ **Editor** | Puede editar tareas del equipo |
| 👤 **Miembro** | Participa en el equipo |
| 👁️ **Viewer** | Solo lectura |

---

## 🔔 Recordatorios

Lista todas las tareas con fecha límite ordenadas cronológicamente:

- 🚨 **Fondo rojo** — Tarea vencida (fecha pasada y no completada)
- ⏰ **Fondo amarillo** — Tarea con vencimiento hoy
- 🔔 **Normal** — Tarea futura

---

## ⚡ Actividad

Muestra el log de las últimas **30 acciones** realizadas en el sistema (crear, editar, completar, eliminar tareas y equipos). Incluye:
- Quién realizó la acción
- Qué se hizo y sobre qué objeto
- Cuándo ocurrió (tiempo relativo)

Haz clic en **🔄 Actualizar** para forzar un refresco.

---

## ⚙️ Configuración

| Sección | Qué puedes hacer |
|---|---|
| 👤 Perfil | Editar nombre y email (demo) |
| 🔔 Notificaciones | Activar/desactivar tipos de notificación |
| 🎨 Apariencia | Alternar modo oscuro/claro |
| 🗄️ Gestión de Datos | Exportar tareas a JSON · Restaurar datos de ejemplo |
| 🔌 Base de Datos | Ver estado de conexión · Reconectar a Supabase |
