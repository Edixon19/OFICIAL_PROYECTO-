import streamlit as st

st.title("Mi Proyecto")
st.text("Bienvenido al primer proyecto del segundo semestre")

usuario = st.text_input("Ingresa tu usuario")
contraseña = st.text_input("Ingresa tu contraseña", type="password")

if st.button("Iniciar sesión"):
    if usuario and contraseña:
        st.success(f"Hola {usuario}, me alegra saludarte. ¡Bienvenido!")
    else:
        st.error("Por favor completa todos los campos antes de continuar.")

