# 🎯 GestorPro

**GestorPro** es una aplicación web de gestión de tareas y equipos construida con **Streamlit** y **Supabase (PostgreSQL)**, desarrollada por el equipo del segundo semestre de **UTEDÉ**.

---

## ¿Qué es GestorPro?

GestorPro permite a equipos y usuarios individuales organizar su trabajo de forma visual e intuitiva. Ofrece un panel de control en tiempo real, filtrado de tareas, gestión de equipos con roles, recordatorios por fecha, registro de actividad y configuración personalizada.

---

## ✨ Características principales

| Módulo | Descripción |
|---|---|
| 📊 **Dashboard** | Resumen de productividad con estadísticas en tiempo real y gráficas |
| ✅ **Tareas** | CRUD completo con prioridades, categorías, etiquetas y fechas |
| 📅 **Calendario** | Vista cronológica de tareas organizadas por fecha límite |
| 👥 **Equipos** | Creación y gestión de equipos con roles (Líder, Editor, Miembro, Viewer) |
| 🔔 **Recordatorios** | Alertas visuales para tareas vencidas o con vencimiento hoy |
| ⚡ **Actividad** | Log en tiempo real de todas las acciones del sistema |
| ⚙️ **Configuración** | Perfil, notificaciones, apariencia y gestión de datos |

---

## 🛠️ Stack tecnológico

- **Frontend / UI:** [Streamlit](https://streamlit.io) con CSS personalizado y tipografía *Sora*
- **Base de datos:** [Supabase](https://supabase.com) (PostgreSQL) vía Pooler
- **Conector BD:** `psycopg2`
- **Lenguaje:** Python 3.x
- **Documentación:** [MkDocs Material](https://squidfunk.github.io/mkdocs-material/)

---

## 📁 Estructura del proyecto

```
OFICIAL_PROYECTO-/
├── app.py           # Aplicación principal (UI + páginas)
├── database.py      # Capa de acceso a datos (Supabase)
├── logic.py         # Lógica de negocio y helpers
├── requirements.txt # Dependencias Python
├── .venv/           # Entorno virtual
└── mi-proyecto/     # Documentación MkDocs
    ├── mkdocs.yml
    └── docs/
```

---

## 🚀 Inicio rápido

```bash
# 1. Clonar el repositorio
git clone https://github.com/Edixon19/OFICIAL_PROYECTO-.git
cd OFICIAL_PROYECTO-

# 2. Crear y activar entorno virtual
python3 -m venv .venv
source .venv/bin/activate  # Mac/Linux
# .venv\Scripts\activate   # Windows

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Ejecutar la aplicación
streamlit run app.py
```

La aplicación estará disponible en **http://localhost:8501**.

---

> 🎓 Proyecto académico — Segundo semestre UTEDÉ · Versión 1.2