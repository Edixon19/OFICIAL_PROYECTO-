import streamlit as st
from supabase import create_client

SUPABASE_URL = st.secrets["supabase"]["url"]
SUPABASE_KEY = st.secrets["supabase"]["key"]

supabase = create_client(
    SUPABASE_URL,
    SUPABASE_KEY
)

st.set_page_config(page_title="Restablecer contraseña")

st.title("Nueva contraseña")

params = st.query_params

access_token = params.get("access_token")
refresh_token = params.get("refresh_token")

# DEBUG
st.write("Params:", params)

if not access_token:
    st.error("Enlace inválido o expirado.")
    st.stop()

try:
    supabase.auth.set_session(
        access_token,
        refresh_token
    )
except Exception as e:
    st.error(f"Error de sesión: {e}")
    st.stop()

new_password = st.text_input(
    "Nueva contraseña",
    type="password"
)

confirm_password = st.text_input(
    "Confirmar contraseña",
    type="password"
)

if st.button("Actualizar contraseña"):

    if len(new_password) < 6:
        st.error("La contraseña debe tener mínimo 6 caracteres.")

    elif new_password != confirm_password:
        st.error("Las contraseñas no coinciden.")

    else:

        try:
            supabase.auth.update_user({
                "password": new_password
            })

            st.success("Contraseña actualizada correctamente.")

        except Exception as e:
            st.error(f"Error: {e}")