import streamlit as st
from supabase import create_client, Client
import re

SUPABASE_URL = "https://wopthjsdceattleaeczt.supabase.co"
SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6IndvcHRoanNkY2VhdHRsZWFlY3p0Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzY3MzM3NjYsImV4cCI6MjA5MjMwOTc2Nn0.QNCHhCzedHSGPul5S-JWZUo3jEV6959tWoKEEeNHztA"

st.set_page_config(page_title="Nueva Contraseña", page_icon="🔐", layout="centered")

@st.cache_resource
def get_supabase():
    return create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

sb = get_supabase()

# CSS básico
st.markdown("""
<style>
.stApp { background: linear-gradient(145deg, #f2c4b5 0%, #8db4c8 100%); }
.main .block-container { max-width: 500px; padding: 2rem; background: white; border-radius: 20px; margin-top: 3rem; box-shadow: 0 10px 30px rgba(0,0,0,0.1); }
h1 { color: #0f172a; text-align: center; }
button { background: linear-gradient(135deg,#e55a2b 0%,#c94d22 100%) !important; color: white !important; border: none !important; border-radius: 10px !important; padding: 0.6rem 1rem !important; font-weight: bold !important; }
</style>
""", unsafe_allow_html=True)

# ============================================
# Título y logo
# ============================================
st.markdown("""
<div style="text-align: center; margin-bottom: 2rem;">
    <div style="width: 70px; height: 70px; background: linear-gradient(135deg,#e55a2b 0%,#0d9488 100%);
                border-radius: 20px; margin: 0 auto 1rem; display: flex; align-items: center; justify-content: center;">
        <span style="color: white; font-size: 2rem; font-weight: bold;">GP</span>
    </div>
    <h1 style="margin: 0; font-size: 1.8rem;">Restablecer contraseña</h1>
    <p style="color: #64748b;">Ingresa tu nueva contraseña</p>
</div>
""", unsafe_allow_html=True)

# ============================================
# Obtener tokens de la URL (múltiples métodos)
# ============================================

access_token = None
refresh_token = None
user_email = None

# Método 1: Intentar leer de st.query_params
params = st.query_params

if "access_token" in params:
    access_token = params["access_token"]
    refresh_token = params.get("refresh_token", "")
    st.success("✅ Token encontrado en query params")

# Método 2: Si no hay, buscar en el hash usando JavaScript
if not access_token:
    # Inyectar JavaScript que extrae el hash y lo guarda en sessionStorage
    st.markdown("""
    <script>
    // Función para extraer parámetros del hash
    function getHashParams() {
        var hash = window.location.hash;
        if (hash && hash.includes('access_token')) {
            var params = hash.substring(1).split('&');
            var paramObj = {};
            for (var i = 0; i < params.length; i++) {
                var pair = params[i].split('=');
                paramObj[pair[0]] = decodeURIComponent(pair[1]);
            }
            sessionStorage.setItem('supabase_tokens', JSON.stringify(paramObj));
            return true;
        }
        return false;
    }
    
    // Si hay hash, redirigir a la misma página sin hash pero con query params
    var hash = window.location.hash;
    if (hash && hash.includes('access_token') && !window.location.search) {
        var queryString = hash.substring(1);
        var newUrl = window.location.pathname + '?' + queryString;
        window.location.replace(newUrl);
    } else if (!window.location.search && sessionStorage.getItem('supabase_tokens')) {
        // Restaurar desde sessionStorage en la segunda carga
        var tokens = JSON.parse(sessionStorage.getItem('supabase_tokens'));
        var queryString = new URLSearchParams(tokens).toString();
        sessionStorage.removeItem('supabase_tokens');
        window.location.replace(window.location.pathname + '?' + queryString);
    }
    </script>
    """, unsafe_allow_html=True)
    
    # Mostrar mensaje de carga mientras se procesa
    if "access_token" not in st.session_state:
        st.info("🔄 Procesando enlace de recuperación...")
        st.session_state["waiting_for_token"] = True
        st.rerun()

# ============================================
# FORMULARIO DE CAMBIO DE CONTRASEÑA
# ============================================

# Si tenemos access_token, mostrar el formulario
if access_token:
    st.session_state["waiting_for_token"] = False
    
    # Opcional: Decodificar token para mostrar el email
    try:
        import base64
        import json
        
        # Decodificar JWT para obtener el email (solo para mostrar)
        parts = access_token.split('.')
        if len(parts) >= 2:
            # Añadir padding si es necesario
            payload = parts[1]
            payload += '=' * (4 - len(payload) % 4)
            decoded = base64.b64decode(payload)
            user_data = json.loads(decoded)
            user_email = user_data.get('email', '')
            
            if user_email:
                st.info(f"📧 Restableciendo contraseña para: **{user_email}**")
    except Exception as e:
        pass  # Si no se puede decodificar, no importa
    
    # FORMULARIO DE NUEVA CONTRASEÑA
    with st.form(key="reset_form"):
        col1, col2 = st.columns([1, 3])
        with col2:
            new_password = st.text_input(
                "Nueva contraseña",
                type="password",
                placeholder="Mínimo 6 caracteres",
                help="Usa al menos 6 caracteres, incluye mayúsculas y números para mayor seguridad"
            )
            
            confirm_password = st.text_input(
                "Confirmar contraseña",
                type="password",
                placeholder="Repite la contraseña"
            )
            
            submitted = st.form_submit_button("🔐 Actualizar contraseña", use_container_width=True)
    
    if submitted:
        # Validaciones
        if not new_password:
            st.error("❌ Ingresa una nueva contraseña")
        elif len(new_password) < 6:
            st.error("❌ La contraseña debe tener al menos 6 caracteres")
        elif new_password != confirm_password:
            st.error("❌ Las contraseñas no coinciden")
        else:
            try:
                # Intentar actualizar la contraseña
                with st.spinner("Actualizando contraseña..."):
                    # Establecer sesión con el token
                    result = sb.auth.set_session(access_token, refresh_token)
                    
                    if result and result.user:
                        # Actualizar la contraseña
                        sb.auth.update_user({"password": new_password})
                        
                        # Limpiar tokens y sesión
                        sb.auth.sign_out()
                        
                        st.success("✅ ¡Contraseña actualizada exitosamente!")
                        st.balloons()
                        st.markdown("---")
                        st.info("🔐 Redirigiendo al inicio de sesión en 3 segundos...")
                        
                        # Limpiar query params
                        st.query_params.clear()
                        
                        # Redirigir al login
                        import time
                        time.sleep(3)
                        st.markdown('<meta http-equiv="refresh" content="0; url=/" />', unsafe_allow_html=True)
                    else:
                        st.error("❌ No se pudo establecer la sesión. El enlace podría haber expirado.")
            except Exception as e:
                error_msg = str(e).lower()
                if "same password" in error_msg:
                    st.error("❌ La nueva contraseña no puede ser igual a la anterior")
                elif "weak password" in error_msg:
                    st.error("❌ Contraseña muy débil. Usa al menos 8 caracteres, mayúsculas, minúsculas y números")
                elif "expired" in error_msg:
                    st.error("❌ El enlace ha expirado. Solicita un nuevo restablecimiento de contraseña")
                else:
                    st.error(f"❌ Error al actualizar: {str(e)[:150]}")
                    st.info("💡 Sugerencia: Solicita un nuevo enlace de restablecimiento desde el login")

# Si no hay token, mostrar botón para volver al login
elif not st.session_state.get("waiting_for_token"):
    st.warning("⚠️ No se encontró un enlace válido de restablecimiento")
    st.markdown("""
    ### ¿Qué puedes hacer?
    1. Solicita un nuevo **restablecimiento de contraseña** desde el inicio de sesión
    2. Asegúrate de usar el enlace más reciente del correo
    3. Los enlaces expiran después de 1 hora por seguridad
    """)
    
    if st.button("← Volver al inicio de sesión", use_container_width=True):
        st.markdown('<meta http-equiv="refresh" content="0; url=/" />', unsafe_allow_html=True)