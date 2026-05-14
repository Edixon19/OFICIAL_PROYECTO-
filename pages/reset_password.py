import streamlit as st
import streamlit.components.v1 as components
from supabase import create_client
import urllib.parse
import time
import jwt

# =========================================================
# CONFIG
# =========================================================

SUPABASE_URL = "https://wopthjsdceattleaeczt.supabase.co"

SUPABASE_ANON_KEY = st.secrets["supabase"]["key"]

st.set_page_config(
    page_title="Nueva Contraseña — GestorPro",
    page_icon="🔐",
    layout="centered"
)

# =========================================================
# SUPABASE CLIENT
# =========================================================

@st.cache_resource
def get_supabase():
    return create_client(
        SUPABASE_URL,
        SUPABASE_ANON_KEY
    )

# =========================================================
# CSS
# =========================================================

st.markdown("""
<style>

@import url('https://fonts.googleapis.com/css2?family=Sora:wght@300;400;500;600;700&display=swap');

html, body {
    font-family: 'Sora', sans-serif !important;
}

.stApp {
    background: linear-gradient(
        145deg,
        #f2c4b5 0%,
        #e8b2a0 18%,
        #d4bdd8 42%,
        #aac4d8 68%,
        #8db4c8 100%
    ) !important;

    min-height: 100vh !important;
}

section[data-testid="stSidebar"],
header[data-testid="stHeader"],
[data-testid="collapsedControl"],
#MainMenu,
footer,
.stDeployButton {
    display: none !important;
}

.main .block-container {
    padding: 6vh 1rem 2rem !important;
    max-width: 440px !important;
    margin: 0 auto !important;
}

.auth-logo-wrap {
    display: flex;
    flex-direction: column;
    align-items: center;
    margin-bottom: 1.8rem;
}

.auth-logo-icon {
    width: 58px;
    height: 58px;

    background: linear-gradient(
        135deg,
        #e55a2b 0%,
        #0d9488 100%
    );

    border-radius: 16px;

    display: flex;
    align-items: center;
    justify-content: center;

    color: #fff;
    font-weight: 700;
    font-size: 1.15rem;

    margin-bottom: 0.8rem;

    box-shadow: 0 6px 22px rgba(229,90,43,0.30);
}

.auth-app-title {
    font-size: 1.45rem;
    font-weight: 700;
    color: #0f172a;
}

.auth-app-sub {
    font-size: 0.81rem;
    color: #475569;
    margin-top: 0.15rem;
    text-align: center;
}

.stTextInput > div > div > input {
    background: #f8fafc !important;

    border: 1.5px solid #e2e8f0 !important;

    border-radius: 11px !important;

    height: 46px !important;

    color: #0f172a !important;
}

.stButton > button {
    background: linear-gradient(
        135deg,
        #e55a2b 0%,
        #c94d22 100%
    ) !important;

    color: #fff !important;

    border: none !important;

    border-radius: 12px !important;

    height: 48px !important;

    font-weight: 600 !important;

    width: 100%;
}

.stButton > button:hover {
    opacity: 0.95;
}

div[data-testid="stSuccess"] {
    border-radius: 10px !important;
}

div[data-testid="stError"] {
    border-radius: 10px !important;
}

</style>
""", unsafe_allow_html=True)

# =========================================================
# EXTRAER HASH DE SUPABASE
# =========================================================

hash_value = st.query_params.get("_hash", "")

# =========================================================
# PRIMERA CARGA
# =========================================================

if not hash_value:

    components.html("""
    <script>

    const hash = window.parent.location.hash.substring(1);

    if (hash) {

        const url = new URL(window.parent.location.href);

        // eliminar hash visualmente
        url.hash = "";

        // guardar hash como query param
        url.searchParams.set("_hash", hash);

        // recargar
        window.parent.location.replace(url.toString());
    }

    </script>
    """, height=0)

    st.markdown("""
    <div class="auth-logo-wrap">
        <div class="auth-logo-icon">GP</div>

        <div class="auth-app-title">
            Restablecer contraseña
        </div>

        <div class="auth-app-sub">
            Verificando enlace...
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.stop()

# =========================================================
# PARSEAR HASH
# =========================================================

hash_params = {}

for item in hash_value.split("&"):

    if "=" in item:

        key, value = item.split("=", 1)

        hash_params[key] = urllib.parse.unquote(value)

# =========================================================
# DEBUG (puedes borrar luego)
# =========================================================

# st.write(hash_params)

# =========================================================
# VALIDAR TOKEN
# =========================================================

access_token = hash_params.get("access_token")
refresh_token = hash_params.get("refresh_token")

if not access_token:

    st.error("❌ Enlace inválido o expirado")

    st.stop()

# =========================================================
# HEADER
# =========================================================

st.markdown("""
<div class="auth-logo-wrap">

    <div class="auth-logo-icon">
        GP
    </div>

    <div class="auth-app-title">
        Nueva contraseña
    </div>

    <div class="auth-app-sub">
        Elige una contraseña segura
    </div>

</div>
""", unsafe_allow_html=True)

# =========================================================
# MOSTRAR EMAIL
# =========================================================

try:

    decoded = jwt.decode(
        access_token,
        options={"verify_signature": False}
    )

    user_email = decoded.get("email", "")

    if user_email:
        st.success(f"Recuperando cuenta: {user_email}")

except Exception:
    pass

# =========================================================
# FORM
# =========================================================

new_password = st.text_input(
    "Nueva contraseña",
    type="password",
    placeholder="Mínimo 6 caracteres"
)

confirm_password = st.text_input(
    "Confirmar contraseña",
    type="password",
    placeholder="Repite la contraseña"
)

# =========================================================
# UPDATE PASSWORD
# =========================================================

if st.button("Actualizar contraseña"):

    if not new_password:

        st.error("Ingresa una contraseña")

    elif len(new_password) < 6:

        st.error("La contraseña debe tener al menos 6 caracteres")

    elif new_password != confirm_password:

        st.error("Las contraseñas no coinciden")

    else:

        try:

            sb = get_supabase()

            # crear sesión recovery
            response = sb.auth.set_session(
                access_token,
                refresh_token
            )

            if not response or not response.user:

                st.error("El enlace expiró")

                st.stop()

            # actualizar password
            sb.auth.update_user({
                "password": new_password
            })

            # cerrar sesión recovery
            sb.auth.sign_out()

            st.success("✅ Contraseña actualizada correctamente")

            st.balloons()

            st.markdown("""
            <p style='text-align:center;color:#475569;'>
                Redirigiendo al inicio de sesión...
            </p>
            """, unsafe_allow_html=True)

            time.sleep(2)

            st.switch_page("app.py")

        except Exception as e:

            error_text = str(e)

            if "same password" in error_text.lower():

                st.error(
                    "La nueva contraseña no puede ser igual a la anterior"
                )

            elif "expired" in error_text.lower():

                st.error(
                    "El enlace ha expirado. Solicita uno nuevo."
                )

            else:

                st.error(f"Error: {error_text}")