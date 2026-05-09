# 🛠️ Instalación y Configuración

Esta guía te llevará paso a paso para poner en marcha GestorPro en tu máquina local.

---

## ✅ Requisitos previos

Antes de comenzar, asegúrate de tener instalado:

- **Python 3.9+** — [Descargar](https://www.python.org/downloads/)
- **Git** — [Descargar](https://git-scm.com/)
- Acceso a internet (para conectar con Supabase)

---

## 1. Clonar el repositorio

```bash
git clone https://github.com/Edixon19/OFICIAL_PROYECTO-.git
cd OFICIAL_PROYECTO-
```

---

## 2. Crear el entorno virtual

=== "Mac / Linux"
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    ```

=== "Windows"
    ```bat
    python -m venv .venv
    .venv\Scripts\activate
    ```

Una vez activado, verás el prefijo `(.venv)` en tu terminal.

---

## 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

Las dependencias principales son:

| Paquete | Versión | Uso |
|---|---|---|
| `streamlit` | ≥1.30 | Framework de UI |
| `psycopg2-binary` | ≥2.9 | Conector PostgreSQL |
| `pandas` | ≥2.0 | Visualización de datos |

---

## 4. Configurar la base de datos (Supabase)

La aplicación usa **Supabase** como backend de datos. La conexión se gestiona en `database.py` con la siguiente prioridad:

1. **`st.secrets["supabase"]["url"]`** — Recomendado para producción
2. **Variable de entorno `DATABASE_URL`**
3. **URL hardcoded de fallback** (solo desarrollo)

Para configurar tus propias credenciales, crea el archivo `.streamlit/secrets.toml`:

```toml
[supabase]
url = "postgresql://usuario:contraseña@host:puerto/database"
```

### Tablas requeridas en Supabase

```sql
-- Tabla de tareas
CREATE TABLE tasks (
    id          TEXT PRIMARY KEY,
    title       TEXT NOT NULL,
    description TEXT,
    priority    TEXT,    -- 'High' | 'Medium' | 'Low'
    category    TEXT,
    status      TEXT,    -- 'Pendiente' | 'Activa' | 'Completada'
    due_date    DATE,
    assignee    TEXT,
    tags        JSONB,
    created_at  TIMESTAMP
);

-- Tabla de equipos
CREATE TABLE teams (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    description TEXT,
    created_at  TIMESTAMP DEFAULT now()
);

-- Miembros de equipos
CREATE TABLE team_members (
    id          TEXT PRIMARY KEY,
    team_id     TEXT REFERENCES teams(id) ON DELETE CASCADE,
    member_name TEXT NOT NULL,
    role        TEXT,    -- 'Líder' | 'Miembro' | 'Editor' | 'Viewer'
    joined_at   TIMESTAMP DEFAULT now()
);

-- Log de actividad
CREATE TABLE activity_log (
    id          TEXT PRIMARY KEY,
    user_name   TEXT,
    action      TEXT,
    entity_type TEXT,
    entity_name TEXT,
    detail      TEXT,
    created_at  TIMESTAMP DEFAULT now()
);
```

---

## 5. Ejecutar la aplicación

```bash
streamlit run app.py
```

La aplicación se abrirá automáticamente en tu navegador en:

```
http://localhost:8501
```

---

## 6. (Opcional) Levantar la documentación

```bash
cd mi-proyecto
pip install mkdocs mkdocs-material
mkdocs serve
```

Documentación disponible en **http://127.0.0.1:8000**.

---

!!! tip "Datos de ejemplo"
    Si la base de datos está vacía, GestorPro inserta automáticamente 3 tareas de ejemplo al iniciar (`seed_sample_data()`). Puedes restaurarlos en cualquier momento desde **Configuración → Gestión de Datos**.
