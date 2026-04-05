# Gestor de Tareas con inicio de sesión en Streamlit y con MySQL

## Instalación y ejecución

## 1. Clonar el repositorio

git clone <https://github.com/Edixon19/OFICIAL_PROYECTO-.git>
cd OFICIAL_PROYECTO-

## 2. Levantar la base de datos con Docker

Debes de tener Docker y Docker Compose instalados, además, debes tener el programa docker abierto
Ejecuta:
docker compose up -d
Esto creará un contenedor MySQL con la base de datos testdb.

## 3. Crear entorno virtual e instalar dependencias

Poner los códigos en la terminal:
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

## 4. Ejecutar la aplicación

pon el código en la terminal:
streamlit run app.py

La aplicación se abrirá en tu navegador en <http://localhost:8501>.

## Funcionalidades

Login básico para acceder al gestor.

## Crear tareas con

Título

Estado (Pendiente / Hecha)

Importancia (Alta / Media / Baja)

Editar título e importancia de una tarea.

Marcar tareas como hechas.

Eliminar tareas.
