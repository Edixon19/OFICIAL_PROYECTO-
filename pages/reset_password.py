import streamlit as st
from supabase import create_client, Client

SUPABASE_URL = "https://wopthjsdceattleaeczt.supabase.co"
SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6IndvcHRoanNkY2VhdHRsZWFlY3p0Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzY3MzM3NjYsImV4cCI6MjA5MjMwOTc2Nn0.QNCHhCzedHSGPul5S-JWZUo3jEV6959tWoKEEeNHztA"

st.set_page_config(page_title="Nueva contraseña — GestorPro", page_icon="🔐", layout="centered")

# ============================================
# 🔥 NUEVO: JavaScript que FUERZA la conversión del hash
# ============================================
st.markdown("""
<script>
(function() {
    // Si ya hay query params o ya se procesó, salir
    if (window.location.search.length > 0 || window._hash_processed) return;
    
    var hash = window.location.hash;
    if (hash && hash.includes('access_token')) {
        window._hash_processed = true;
        // Convertir #access_token=xxx&type=recovery a ?access_token=xxx&type=recovery
        var newUrl = window.location.pathname + '?' + hash.substring(1);
        window.location.replace(newUrl);
    }
})();
</script>
""", unsafe_allow_html=True)

@st.cache_resource
def _sb() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

# CSS
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Sora:wght@300;400;500;600;700&display=swap');
html, body { font-family: 'Sora', sans-serif !important; }
.stApp {
    background: linear-gradient(145deg,#f2c4b5 0%,#e8b2a0 18%,#d4bdd8 42%,#aac4d8 68%,#8db4c8 100%) !important;
    min-height: 100vh !important;
}
section[data-testid="stSidebar"], header[data-testid="stHeader"],
[data-testid="collapsedControl"], #MainMenu, footer, .stDeployButton {
    display: none !important;
}
.main .block-container {
    padding: 6vh 1rem 2rem !important;
    max-width: 440px !important;
    margin: 0 auto !important;
}
.auth-logo-wrap { display:flex; flex-direction:column; align-items:center; margin-bottom:1.8rem; }
.auth-logo-icon {
    width:58px; height:58px;
    background:linear-gradient(135deg,#e55a2b 0%,#0d9488 100%);
    border-radius:16px; display:flex; align-items:center; justify-content:center;
    color:#fff; font-weight:700; font-size:1.15rem;
    margin-bottom:0.8rem; box-shadow:0 6px 22px rgba(229,90,43,0.30);
}
.auth-app-title { font-size:1.45rem; font-weight:700; color:#0f172a; }
.auth-app-sub   { font-size:0.81rem; color:#475569; margin-top:0.15rem; text-align:center; }
.auth-info-box {
    background:rgba(13,148,136,0.07); border:1px solid rgba(13,148,136,0.22);
    border-radius:10px; padding:0.8rem 1rem; margin-bottom:1.25rem;
    font-size:0.82rem; color:#0f4c45; line-height:1.55;
}
.stTextInput > div > div > input {
    background:#f8fafc !important; border:1.5px solid #e2e8f0 !important;
    border-radius:11px !important; height:46px !important;
}
.st-key-update_pw_btn button {
    background:linear-gradient(135deg,#e55a2b 0%,#c94d22 100%) !important;
    color:#fff !important; border-radius:12px !important;
    height:48px !important; font-weight:600 !important;
}
</style>
""", unsafe_allow_html=True)

# ============================================
# LÓGICA PRINCIPAL
# ============================================

def logo():
    st.markdown("""
    <div class="auth-logo-wrap">
        <div class="auth-logo-icon">GP</div>
        <div class="auth-app-title">Nueva contraseña</div>
        <div class="auth-app-sub">Elige una contraseña segura</div>
    </div>
    """, unsafe_allow_html=True)

logo()

params = st.query_params

# Verificar si tenemos el token después de la conversión
if "access_token" in params and params.get("type") == "recovery":
    st.success("✅ Enlace válido. Ingresa tu nueva contraseña.")
    
    # Mostrar email del usuario (opcional)
    try:
        # Decodificar el token JWT para obtener el email (sin validar, solo para mostrar)
        import jwt
        token = params["access_token"]
        decoded = jwt.decode(token, options={"verify_signature": False})
        user_email = decoded.get("email", "")
        if user_email:
            st.info(f"Cuenta: {user_email}")
    except:
        pass
    
    new_pw = st.text_input("Nueva contraseña", type="password", placeholder="Mínimo 6 caracteres")
    confirm_pw = st.text_input("Confirmar contraseña", type="password", placeholder="Repite la contraseña")
    
    if st.button("Actualizar contraseña", key="update_pw_btn", use_container_width=True):
        if not new_pw or len(new_pw) < 6:
            st.error("La contraseña debe tener al menos 6 caracteres")
        elif new_pw != confirm_pw:
            st.error("Las contraseñas no coinciden")
        else:
            try:
                # Usar el token para actualizar la contraseña
                at = params["access_token"]
                rt = params.get("refresh_token", "")
                
                # Establecer sesión con el token
                session = _sb().auth.set_session(at, rt)
                if session and session.user:
                    # Actualizar contraseña
                    _sb().auth.update_user({"password": new_pw})
                    st.success("✅ ¡Contraseña actualizada correctamente!")
                    st.balloons()
                    st.markdown("Redirigiendo al inicio de sesión en 3 segundos...")
                    st.query_params.clear()
                    import time
                    time.sleep(3)
                    st.markdown('<meta http-equiv="refresh" content="0; url=/" />', unsafe_allow_html=True)
                else:
                    st.error("No se pudo establecer la sesión. Token inválido.")
            except Exception as e:
                error_msg = str(e).lower()
                if "same password" in error_msg:
                    st.error("La nueva contraseña no puede ser igual a la anterior")
                elif "weak" in error_msg:
                    st.error("La contraseña es muy débil. Usa al menos 8 caracteres con mayúsculas y números")
                else:
                    st.error(f"Error: {str(e)}")

elif "code" in params:
    st.info("Procesando código de verificación...")
    try:
        result = _sb().auth.exchange_code_for_session({"auth_code": params["code"]})
        if result and result.user:
            st.success("Sesión establecida. Ahora puedes cambiar tu contraseña.")
            st.rerun()
    except:
        st.error("Error al procesar el código")

else:
    st.warning("⚠️ Enlace inválido o expirado. Solicita un nuevo restablecimiento.")
    if st.button("Volver al inicio de sesión", use_container_width=True):
        st.markdown('<meta http-equiv="refresh" content="0; url=/" />', unsafe_allow_html=True)