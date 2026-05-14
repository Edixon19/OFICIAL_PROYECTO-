import streamlit as st
from supabase import create_client, Client
import time

SUPABASE_URL = "https://wopthjsdceattleaeczt.supabase.co"
SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6IndvcHRoanNkY2VhdHRsZWFlY3p0Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzY3MzM3NjYsImV4cCI6MjA5MjMwOTc2Nn0.QNCHhCzedHSGPul5S-JWZUo3jEV6959tWoKEEeNHztA"

st.set_page_config(page_title="Nueva contraseña — GestorPro", page_icon="🔐", layout="centered")

@st.cache_resource
def _sb() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

# ============================================
# MÉTODO 1: JavaScript con delay y sessionStorage
# ============================================
st.markdown("""
<script>
(function() {
    // Verificar si ya tenemos los params en sessionStorage
    if (sessionStorage.getItem('rp_params')) {
        return;
    }
    
    var hash = window.location.hash;
    if (hash && hash.includes('access_token')) {
        // Guardar en sessionStorage
        sessionStorage.setItem('rp_params', hash.substring(1));
        // Recargar sin hash pero con query string
        var newUrl = window.location.pathname + '?' + hash.substring(1);
        window.location.replace(newUrl);
    } else if (window.location.search.length === 0 && sessionStorage.getItem('rp_params')) {
        // Segunda carga: restaurar desde sessionStorage
        var params = sessionStorage.getItem('rp_params');
        sessionStorage.removeItem('rp_params');
        var newUrl = window.location.pathname + '?' + params;
        window.location.replace(newUrl);
    }
})();
</script>
""", unsafe_allow_html=True)

# CSS (simplificado para probar)
st.markdown("""
<style>
.stApp { background: linear-gradient(145deg, #f2c4b5 0%, #8db4c8 100%); }
.main .block-container { max-width: 440px; padding: 4rem 1rem; }
div[data-testid="stSuccess"] { background: #d1fae5; }
div[data-testid="stError"] { background: #fee2e2; }
</style>
""", unsafe_allow_html=True)

# ============================================
# LÓGICA PRINCIPAL CON RETRY
# ============================================

def show_logo():
    st.markdown("""
    <div style="text-align: center; margin-bottom: 2rem;">
        <div style="width: 60px; height: 60px; background: linear-gradient(135deg,#e55a2b 0%,#0d9488 100%);
                    border-radius: 16px; margin: 0 auto 1rem; display: flex; align-items: center; justify-content: center;">
            <span style="color: white; font-size: 1.5rem; font-weight: bold;">GP</span>
        </div>
        <h1 style="font-size: 1.8rem; color: #0f172a;">Nueva contraseña</h1>
        <p style="color: #475569;">Elige una contraseña segura</p>
    </div>
    """, unsafe_allow_html=True)

show_logo()

# Intentar leer query params de múltiples formas
params = st.query_params

# DEBUG: Mostrar qué params tenemos (para diagnóstico)
if not params:
    st.info("🔍 Procesando enlace... Espera 2 segundos")
    time.sleep(2)
    st.rerun()

# Verificar si tenemos los tokens
has_token = "access_token" in params or "token" in params

if has_token:
    st.success("✅ Enlace verificado correctamente")
    
    # Extraer tokens
    access_token = params.get("access_token", "")
    refresh_token = params.get("refresh_token", "")
    
    if access_token:
        st.info("Formulario de cambio de contraseña")
        
        new_pw = st.text_input("Nueva contraseña", type="password", placeholder="Mínimo 6 caracteres", key="pw1")
        confirm_pw = st.text_input("Confirmar contraseña", type="password", placeholder="Repite la contraseña", key="pw2")
        
        if st.button("Actualizar contraseña", type="primary", use_container_width=True):
            if not new_pw or len(new_pw) < 6:
                st.error("La contraseña debe tener al menos 6 caracteres")
            elif new_pw != confirm_pw:
                st.error("Las contraseñas no coinciden")
            else:
                try:
                    # Establecer sesión con el token
                    result = _sb().auth.set_session(access_token, refresh_token)
                    if result and result.user:
                        # Actualizar contraseña
                        _sb().auth.update_user({"password": new_pw})
                        st.success("✅ ¡Contraseña actualizada con éxito!")
                        st.balloons()
                        st.markdown("Redirigiendo al inicio de sesión...")
                        st.query_params.clear()
                        time.sleep(2)
                        st.markdown('<meta http-equiv="refresh" content="0; url=/" />', unsafe_allow_html=True)
                    else:
                        st.error("No se pudo establecer la sesión. Token inválido.")
                except Exception as e:
                    error_msg = str(e).lower()
                    if "same password" in error_msg:
                        st.error("La nueva contraseña no puede ser igual a la anterior")
                    elif "weak" in error_msg:
                        st.error("Contraseña muy débil. Usa mayúsculas, números y al menos 8 caracteres")
                    else:
                        st.error(f"Error: {error_msg[:150]}")
    else:
        st.warning("Formato de token no reconocido")
else:
    # Si no hay tokens y no estamos esperando, mostrar error
    if "waiting" not in st.session_state:
        st.error("⚠️ Enlace inválido o expirado")
        if st.button("Volver al inicio de sesión", use_container_width=True):
            st.markdown('<meta http-equiv="refresh" content="0; url=/" />', unsafe_allow_html=True)