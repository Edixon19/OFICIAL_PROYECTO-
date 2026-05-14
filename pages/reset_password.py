import streamlit as st
from supabase import create_client, Client

SUPABASE_URL = "https://wopthjsdceattleaeczt.supabase.co"
SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6IndvcHRoanNkY2VhdHRsZWFlY3p0Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzY3MzM3NjYsImV4cCI6MjA5MjMwOTc2Nn0.QNCHhCzedHSGPul5S-JWZUo3jEV6959tWoKEEeNHztA"

st.set_page_config(page_title="Nueva Contraseña", page_icon="🔐", layout="centered")

@st.cache_resource
def get_supabase():
    return create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

# ============================================
# JAVASCRIPT: Convertir hash a query params SOLO UNA VEZ
# ============================================
st.markdown("""
<script>
// Si ya hay query params, no hacer nada
if (window.location.search.length === 0 && window.location.hash) {
    var hash = window.location.hash.substring(1);
    if (hash) {
        window.location.replace(window.location.pathname + '?' + hash);
    }
}
</script>
""", unsafe_allow_html=True)

# ============================================
# LEER TOKEN (después de la redirección)
# ============================================
params = st.query_params

# Si NO hay token, mostrar error y botón
if "access_token" not in params and "token" not in params:
    st.title("🔐 Restablecer contraseña")
    st.error("❌ Enlace inválido o expirado")
    st.info("""
    ### ¿Qué hacer?
    - Solicita un nuevo **restablecimiento de contraseña** desde el login
    - Los enlaces expiran después de 1 hora
    - Asegúrate de usar el enlace más reciente del correo
    """)
    if st.button("← Volver al inicio de sesión"):
        st.markdown('<meta http-equiv="refresh" content="0; url=/" />', unsafe_allow_html=True)
    st.stop()

# ============================================
# SI HAY TOKEN: Mostrar formulario
# ============================================
st.title("🔐 Restablecer contraseña")

# Obtener tokens
access_token = params.get("access_token", "")
refresh_token = params.get("refresh_token", "")

# Mostrar email del usuario (decodificando el token)
try:
    import jwt
    decoded = jwt.decode(access_token, options={"verify_signature": False})
    user_email = decoded.get("email", "")
    if user_email:
        st.success(f"✅ Restableciendo para: **{user_email}**")
except:
    st.success("✅ Enlace verificado correctamente")

st.markdown("---")

# Formulario de nueva contraseña
with st.form("reset_password_form"):
    new_password = st.text_input(
        "📝 Nueva contraseña",
        type="password",
        placeholder="Mínimo 6 caracteres",
        help="Usa al menos 6 caracteres"
    )
    
    confirm_password = st.text_input(
        "✅ Confirmar contraseña",
        type="password",
        placeholder="Repite la contraseña"
    )
    
    submitted = st.form_submit_button("Actualizar contraseña", use_container_width=True, type="primary")

if submitted:
    # Validaciones
    if not new_password:
        st.error("❌ Ingresa una contraseña")
    elif len(new_password) < 6:
        st.error("❌ La contraseña debe tener al menos 6 caracteres")
    elif new_password != confirm_password:
        st.error("❌ Las contraseñas no coinciden")
    else:
        try:
            sb = get_supabase()
            
            # Establecer sesión con el token
            session = sb.auth.set_session(access_token, refresh_token)
            
            if session and session.user:
                # Actualizar contraseña
                sb.auth.update_user({"password": new_password})
                
                # Cerrar sesión
                sb.auth.sign_out()
                
                # Mostrar éxito y redirigir
                st.success("✅ ¡Contraseña actualizada exitosamente!")
                st.balloons()
                st.info("🔄 Redirigiendo al inicio de sesión...")
                
                # Limpiar parámetros
                st.query_params.clear()
                
                # Redirigir después de 2 segundos
                import time
                time.sleep(2)
                st.markdown('<meta http-equiv="refresh" content="0; url=/" />', unsafe_allow_html=True)
            else:
                st.error("❌ No se pudo establecer la sesión. El enlace podría haber expirado.")
                
        except Exception as e:
            error = str(e).lower()
            if "same password" in error:
                st.error("❌ La nueva contraseña no puede ser igual a la anterior")
            elif "weak" in error:
                st.error("❌ Contraseña muy débil. Usa mayúsculas, minúsculas y números")
            else:
                st.error(f"❌ Error: {str(e)}")