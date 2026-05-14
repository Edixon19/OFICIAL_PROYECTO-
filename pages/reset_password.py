import streamlit as st
from supabase import create_client
import urllib.parse
import time

# ============================================
# CONFIGURACIÓN DE CREDENCIALES (SECRETS)
# ============================================
try:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_ANON_KEY = st.secrets["SUPABASE_KEY"]
except:
    SUPABASE_URL = "https://wopthjsdceattleaeczt.supabase.co"
    SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6IndvcHRoanNkY2VhdHRsZWFlY3p0Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzY3MzM3NjYsImV4cCI6MjA5MjMwOTc2Nn0.QNCHhCzedHSGPul5S-JWZUo3jEV6959tWoKEEeNHztA"

st.set_page_config(page_title="Nueva Contraseña — GestorPro", page_icon="🔐", layout="centered")

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
.stButton button {
    background:linear-gradient(135deg,#e55a2b 0%,#c94d22 100%) !important;
    color:#fff !important;
    border-radius:12px !important;
    height:48px !important;
    font-weight:600 !important;
    border: none !important;
}
div[data-testid="stSuccess"] { background: #d1fae5; color: #065f46; border-radius: 10px; }
div[data-testid="stError"] { background: #fee2e2; color: #991b1b; border-radius: 10px; }
</style>
""", unsafe_allow_html=True)

@st.cache_resource
def get_supabase():
    return create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

# ============================================
# LOGO / HEADER
# ============================================
st.markdown("""
<div class="auth-logo-wrap">
    <div class="auth-logo-icon">GP</div>
    <div class="auth-app-title">Nueva Contraseña</div>
    <div class="auth-app-sub">Ingresa tu nueva clave para GestorPro</div>
</div>
""", unsafe_allow_html=True)

# ============================================
# ESTRATEGIA: leer access_token directo desde query params
# Supabase puede enviar los tokens como query params si se configura
# "flowType: pkce" — pero también los manda como hash.
# La única forma de capturar el hash en Streamlit es con st.markdown JS
# que haga un top-level redirect.
# ============================================

# Intentar leer desde query params normales primero
# (cuando ya hicimos la redirección desde el JS)
access_token  = st.query_params.get("access_token", "")
refresh_token = st.query_params.get("refresh_token", "")
token_type    = st.query_params.get("type", "")

if not access_token:
    # El JS de st.markdown SÍ corre en el contexto top-level de la página
    # (a diferencia de components.html que usa un iframe sandboxed).
    # Este script lee el hash y redirige con los params en la query string.
    st.markdown("""
    <script>
        (function() {
            const hash = window.location.hash.substring(1);
            if (!hash) return;
            const params = new URLSearchParams(hash);
            const token = params.get('access_token');
            if (!token) return;
            // Construir nueva URL con los tokens como query params normales
            const base = window.location.origin + window.location.pathname;
            const newUrl = base
                + '?access_token=' + encodeURIComponent(token)
                + '&refresh_token=' + encodeURIComponent(params.get('refresh_token') || '')
                + '&type=' + encodeURIComponent(params.get('type') || '');
            window.location.replace(newUrl);
        })();
    </script>
    <div style="text-align:center; margin-top: 2rem; color:#475569; font-size:0.9rem;">
        ⏳ Validando el enlace de recuperación...
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# ============================================
# FORMULARIO DE NUEVA CONTRASEÑA
# ============================================
if access_token and token_type in ("recovery", "signup"):
    new_pw     = st.text_input("Nueva contraseña",     type="password", placeholder="Mínimo 6 caracteres")
    confirm_pw = st.text_input("Confirmar contraseña", type="password", placeholder="Repite tu contraseña")

    if st.button("Actualizar contraseña", use_container_width=True):
        if len(new_pw) < 6:
            st.error("⚠️ La contraseña debe tener al menos 6 caracteres.")
        elif new_pw != confirm_pw:
            st.error("⚠️ Las contraseñas no coinciden.")
        else:
            try:
                sb = get_supabase()
                sb.auth.set_session(access_token, refresh_token)
                sb.auth.update_user({"password": new_pw})

                st.success("🎉 ¡Contraseña actualizada con éxito!")
                st.balloons()
                time.sleep(2)
                st.markdown('<meta http-equiv="refresh" content="0; url=/" />', unsafe_allow_html=True)
                st.stop()
            except Exception as e:
                st.error(f"Huда un problema al actualizar: {str(e)}")
else:
    st.error("❌ El enlace es inválido o ha expirado. Por favor solicita uno nuevo.")
    if st.button("Volver al inicio"):
        st.markdown('<meta http-equiv="refresh" content="0; url=/" />', unsafe_allow_html=True)