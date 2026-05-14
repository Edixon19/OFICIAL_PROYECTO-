import streamlit as st
from supabase import create_client, Client
import urllib.parse

SUPABASE_URL = "https://wopthjsdceattleaeczt.supabase.co"
SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6IndvcHRoanNkY2VhdHRsZWFlY3p0Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzY3MzM3NjYsImV4cCI6MjA5MjMwOTc2Nn0.QNCHhCzedHSGPul5S-JWZUo3jEV6959tWoKEEeNHztA"

st.set_page_config(page_title="Reset Password", page_icon="🔐")

# Leer el hash manualmente desde la URL usando JavaScript
hash_params = st.query_params

# Si no hay params, inyectar JS para recargar con params
if not hash_params:
    st.markdown("""
    <script>
    if (window.location.hash) {
        var hash = window.location.hash.substring(1);
        var url = window.location.pathname + '?' + hash;
        window.location.replace(url);
    }
    </script>
    """, unsafe_allow_html=True)
    st.info("Procesando enlace de recuperación...")
    st.stop()

# Si llegamos aquí, tenemos params
st.title("Restablecer contraseña")

if "access_token" in hash_params:
    sb = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
    
    new_pw = st.text_input("Nueva contraseña", type="password")
    confirm = st.text_input("Confirmar contraseña", type="password")
    
    if st.button("Actualizar"):
        if new_pw and new_pw == confirm and len(new_pw) >= 6:
            try:
                sb.auth.set_session(hash_params["access_token"], hash_params.get("refresh_token", ""))
                sb.auth.update_user({"password": new_pw})
                st.success("Contraseña actualizada")
                st.balloons()
            except Exception as e:
                st.error(f"Error: {e}")
        else:
            st.error("Verifica que las contraseñas coincidan y tengan mínimo 6 caracteres")
else:
    st.error("Enlace inválido")