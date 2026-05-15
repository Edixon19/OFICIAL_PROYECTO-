import streamlit as st
import httpx
import time

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
    background: #f8fafc !important;
    border: 1.5px solid #e2e8f0 !important;
    border-radius: 11px !important;
    height: 46px !important;
    color: #0f172a !important;
    -webkit-text-fill-color: #0f172a !important;
}
.stTextInput > div > div > input::placeholder {
    color: #94a3b8 !important;
    -webkit-text-fill-color: #94a3b8 !important;
}
.stTextInput label { color: #0f172a !important; font-weight: 500 !important; }
.stButton button {
    background:linear-gradient(135deg,#e55a2b 0%,#c94d22 100%) !important;
    color:#fff !important;
    border-radius:12px !important;
    height:48px !important;
    font-weight:600 !important;
    border: none !important;
}
div[data-testid="stSuccess"] { background: #d1fae5; color: #065f46; border-radius: 10px; }
div[data-testid="stError"]   { background: #fee2e2; color: #991b1b; border-radius: 10px; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="auth-logo-wrap">
    <div class="auth-logo-icon">GP</div>
    <div class="auth-app-title">Nueva Contraseña</div>
    <div class="auth-app-sub">Ingresa tu nueva clave para GestorPro</div>
</div>
""", unsafe_allow_html=True)

# Leer el token numérico (OTP) que manda Supabase con {{ .Token }}
otp_token  = st.query_params.get("access_token", "")
token_type = st.query_params.get("type", "recovery")

if not otp_token:
    st.error("❌ El enlace es inválido o ha expirado.")
    if st.button("Volver al inicio"):
        st.switch_page("app.py")
    st.stop()

# Necesitamos también el email del usuario para verificar el OTP.
# Lo pedimos en pantalla si no lo tenemos aún.
if "access_token_jwt" not in st.session_state:
    email = st.text_input("Confirma tu correo electrónico", placeholder="tucorreo@gmail.com")

    if st.button("Continuar", use_container_width=True):
        if not email:
            st.error("⚠️ Ingresa tu correo.")
        else:
            try:
                resp = httpx.post(
                    f"{SUPABASE_URL}/auth/v1/verify",
                    headers={
                        "apikey": SUPABASE_ANON_KEY,
                        "Content-Type": "application/json"
                    },
                    json={
                        "type": "recovery",
                        "token": otp_token,
                        "email": email
                    }
                )
                if resp.status_code == 200:
                    data = resp.json()
                    st.session_state["access_token_jwt"] = data["access_token"]
                    st.rerun()
                else:
                    msg = resp.json().get("msg", resp.text)
                    st.error(f"❌ {msg}")
            except Exception as e:
                st.error(f"Error: {str(e)}")
    st.stop()

# Ya tenemos el JWT real — mostrar formulario de nueva contraseña
access_token = st.session_state["access_token_jwt"]

new_pw     = st.text_input("Nueva contraseña",     type="password", placeholder="Mínimo 6 caracteres")
confirm_pw = st.text_input("Confirmar contraseña", type="password", placeholder="Repite tu contraseña")

if st.button("Actualizar contraseña", use_container_width=True):
    if len(new_pw) < 6:
        st.error("⚠️ La contraseña debe tener al menos 6 caracteres.")
    elif new_pw != confirm_pw:
        st.error("⚠️ Las contraseñas no coinciden.")
    else:
        try:
            response = httpx.put(
                f"{SUPABASE_URL}/auth/v1/user",
                headers={
                    "apikey": SUPABASE_ANON_KEY,
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json"
                },
                json={"password": new_pw}
            )
            if response.status_code == 200:
                st.success("🎉 ¡Contraseña actualizada con éxito!")
                st.balloons()
                time.sleep(2)
                st.switch_page("app.py")
            else:
                st.error(f"Error: {response.json().get('msg', response.text)}")
        except Exception as e:
            st.error(f"Error al actualizar: {str(e)}")