import streamlit as st
from supabase import create_client, Client
import urllib.parse

SUPABASE_URL = "https://wopthjsdceattleaeczt.supabase.co"
SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6IndvcHRoanNkY2VhdHRsZWFlY3p0Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzY3MzM3NjYsImV4cCI6MjA5MjMwOTc2Nn0.QNCHhCzedHSGPul5S-JWZUo3jEV6959tWoKEEeNHztA"

st.set_page_config(page_title="Nueva Contraseña — GestorPro", page_icon="🔐", layout="centered")

# CSS con tus colores originales
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
.stTextInput > div > div > input {
    background:#f8fafc !important;
    border:1.5px solid #e2e8f0 !important;
    border-radius:11px !important;
    height:46px !important;
}
.st-key-update_pw_btn button {
    background:linear-gradient(135deg,#e55a2b 0%,#c94d22 100%) !important;
    color:#fff !important;
    border-radius:12px !important;
    height:48px !important;
    font-weight:600 !important;
}
div[data-testid="stSuccess"] { background: #d1fae5; color: #065f46; }
div[data-testid="stError"] { background: #fee2e2; color: #991b1b; }
</style>
""", unsafe_allow_html=True)

@st.cache_resource
def get_supabase():
    return create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

# ============================================
# TRUCO: Usar un parámetro especial para forzar la lectura del hash
# ============================================

# Si no hay token y no estamos en modo de espera, inyectar JS que redirige
if "access_token" not in st.query_params and "token" not in st.query_params:
    if not st.session_state.get("hash_processed"):
        st.session_state["hash_processed"] = True
        
        # JavaScript que lee el hash y redirige a la misma página con query params
        st.markdown("""
        <script>
        (function() {
            var hash = window.location.hash;
            if (hash && hash.includes('access_token')) {
                var new_url = window.location.pathname + '?access_token=1&_hash=' + encodeURIComponent(hash.substring(1));
                window.location.replace(new_url);
            }
        })();
        </script>
        """, unsafe_allow_html=True)
        
        # Mostrar mensaje de carga
        st.markdown("""
        <div class="auth-logo-wrap">
            <div class="auth-logo-icon">GP</div>
            <div class="auth-app-title">Restablecer contraseña</div>
            <div class="auth-app-sub">Verificando enlace...</div>
        </div>
        """, unsafe_allow_html=True)
        st.stop()

# ============================================
# Procesar el hash que llegó como query param
# ============================================

if "_hash" in st.query_params:
    hash_raw = st.query_params["_hash"]
    # Parsear el hash
    hash_params = {}
    for item in hash_raw.split('&'):
        if '=' in item:
            key, value = item.split('=', 1)
            hash_params[key] = urllib.parse.unquote(value)
    
    # Guardar en session_state para usarlo
    if "access_token" in hash_params:
        st.session_state["reset_access_token"] = hash_params["access_token"]
        st.session_state["reset_refresh_token"] = hash_params.get("refresh_token", "")
        st.session_state["reset_type"] = hash_params.get("type", "")
        # Limpiar query params
        st.query_params.clear()

# ============================================
# MOSTRAR FORMULARIO
# ============================================

st.markdown("""
<div class="auth-logo-wrap">
    <div class="auth-logo-icon">GP</div>
    <div class="auth-app-title">Restablecer contraseña</div>
    <div class="auth-app-sub">Elige una contraseña segura</div>
</div>
""", unsafe_allow_html=True)

# Verificar si tenemos token en session_state
access_token = st.session_state.get("reset_access_token", "")
refresh_token = st.session_state.get("reset_refresh_token", "")
token_type = st.session_state.get("reset_type", "")

if access_token and token_type == "recovery":
    # Mostrar email si podemos decodificar
    try:
        import jwt
        decoded = jwt.decode(access_token, options={"verify_signature": False})
        user_email = decoded.get("email", "")
        st.success(f"✅ Restableciendo para: **{user_email}**")
    except:
        st.success("✅ Enlace verificado correctamente")
    
    # Formulario
    new_pw = st.text_input("Nueva contraseña", type="password", placeholder="Mínimo 6 caracteres", key="new_pw")
    confirm_pw = st.text_input("Confirmar contraseña", type="password", placeholder="Repite la contraseña", key="confirm_pw")
    
    if st.button("Actualizar contraseña", key="update_pw_btn", use_container_width=True):
        if not new_pw or len(new_pw) < 6:
            st.error("La contraseña debe tener al menos 6 caracteres")
        elif new_pw != confirm_pw:
            st.error("Las contraseñas no coinciden")
        else:
            try:
                sb = get_supabase()
                session = sb.auth.set_session(access_token, refresh_token)
                if session and session.user:
                    sb.auth.update_user({"password": new_pw})
                    sb.auth.sign_out()
                    st.success("✅ ¡Contraseña actualizada exitosamente!")
                    st.balloons()
                    # Limpiar session_state
                    del st.session_state["reset_access_token"]
                    del st.session_state["reset_refresh_token"]
                    del st.session_state["reset_type"]
                    st.markdown('<meta http-equiv="refresh" content="2; url=/" />', unsafe_allow_html=True)
                else:
                    st.error("❌ Enlace inválido o expirado")
            except Exception as e:
                error_msg = str(e).lower()
                if "same password" in error_msg:
                    st.error("❌ La nueva contraseña no puede ser igual a la anterior")
                else:
                    st.error(f"❌ Error: {error_msg[:100]}")
else:
    st.error("❌ Enlace inválido o expirado")
    if st.button("Volver al inicio de sesión", use_container_width=True):
        st.markdown('<meta http-equiv="refresh" content="0; url=/" />', unsafe_allow_html=True)