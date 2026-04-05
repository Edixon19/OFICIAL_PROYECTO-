import streamlit as st
import mysql.connector

# --- Conexión a MySQL ---
def get_connection():
    return mysql.connector.connect(
        host="localhost",
        port=3306,
        database="testdb",
        user="testuser",
        password="testpass"
    )

# --- Inicializar tabla ---
def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tareas (
            id INT AUTO_INCREMENT PRIMARY KEY,
            titulo VARCHAR(200),
            estado VARCHAR(50),
            importancia VARCHAR(50)
        )
    """)
    conn.commit()
    cursor.close()
    conn.close()

init_db()

# --- Estado de sesión ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

# --- Pantalla de login ---
if not st.session_state.logged_in:
    st.title("Mi Proyecto")
    usuario = st.text_input("Ingresa tu usuario")
    contraseña = st.text_input("Ingresa tu contraseña", type="password")

    if st.button("Iniciar sesión"):
        if usuario and contraseña:
            st.session_state.logged_in = True
            st.rerun()
        else:
            st.error("Por favor completa todos los campos antes de continuar.")

# --- Gestor de tareas ---
if st.session_state.logged_in:
    st.header("📝 Gestor de Tareas")

    # Botón de cerrar sesión
    if st.button("🚪 Cerrar sesión"):
        st.session_state.logged_in = False
        st.rerun()

    # Formulario para agregar tarea
    with st.form("nueva_tarea"):
        titulo = st.text_input("Título de la tarea")
        importancia = st.selectbox("Nivel de importancia", ["Alta", "Media", "Baja"])
        submitted = st.form_submit_button("Agregar")
        if submitted and titulo:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO tareas (titulo, estado, importancia) VALUES (%s, %s, %s)",
                (titulo, "Pendiente", importancia)
            )
            conn.commit()
            cursor.close()
            conn.close()
            st.success(f"Tarea '{titulo}' agregada con importancia {importancia}.")
            st.rerun()

    # Mostrar tareas
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, titulo, estado, importancia FROM tareas")
    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    st.subheader("Lista de tareas")
    for row in rows:
        id, titulo, estado, importancia = row
        col1, col2, col3, col4, col5 = st.columns([3,2,2,2,2])
        col1.write(titulo)
        col2.write(estado)
        col3.write(importancia)

        if col4.button("✔ Hecha", key=f"done_{id}"):
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("UPDATE tareas SET estado=%s WHERE id=%s", ("Hecha", id))
            conn.commit()
            cursor.close()
            conn.close()
            st.rerun()

        if col5.button("✏ Editar", key=f"edit_{id}"):
            nuevo_titulo = st.text_input(f"Nuevo título para tarea {id}", value=titulo, key=f"input_{id}")
            nueva_importancia = st.selectbox(
                f"Nuevo nivel de importancia para tarea {id}",
                ["Alta", "Media", "Baja"],
                index=["Alta","Media","Baja"].index(importancia),
                key=f"imp_{id}"
            )
            if st.button(f"Guardar cambios {id}", key=f"save_{id}"):
                conn = get_connection()
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE tareas SET titulo=%s, importancia=%s WHERE id=%s",
                    (nuevo_titulo, nueva_importancia, id)
                )
                conn.commit()
                cursor.close()
                conn.close()
                st.rerun()

        if st.button("🗑 Eliminar", key=f"del_{id}"):
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM tareas WHERE id=%s", (id,))
            conn.commit()
            cursor.close()
            conn.close()
            st.rerun()
