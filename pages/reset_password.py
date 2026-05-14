import streamlit as st
from supabase import create_client, Client

# ──────────────────────────────────────────────
# CONFIG
# ──────────────────────────────────────────────
SUPABASE_URL = st.secrets["supabase"]["url"]
SUPABASE_KEY = st.secrets["supabase"]["key"]

st.set_page_config(
    page_title="Nueva contraseña — GestorPro",
    page_icon="🔐",
    layout="centered",
)

# ──────────────────────────────────────────────
# CSS (mismo estilo que auth.py)
# ──────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Sora:wght@300;400;500;600;700&display=swap');

html, body { font-family: 'Sora', sans-serif !important; }

.stApp {
    background: linear-gradient(
        145deg,
        #f2c4b5 0%, #e8b2a0 18%,
        #d4bdd8 42%, #aac4d8 68%,
        #8db4c8 100%
    ) !important;
    min-height: 100vh !important;
}

section[data-testid="stSidebar"],
header[data-testid="stHeader"],
[data-testid="collapsedControl"],
#MainMenu, footer, .stDeployButton {
    display: none !important;
    visibility: hidden !important;
}

.main .block-container {
    padding: 6vh 1rem 2rem !important;
    max-width: 440px !important;
    margin: 0 auto !important;
}

.auth-logo-wrap {
    display: flex; flex-direction: column;
    align-items: center; margin-bottom: 1.8rem;
}
.auth-logo-icon {
    width: 58px; height: 58px;
    background: linear-gradient(135deg, #e55a2b 0%, #0d9488 100%);
    border-radius: 16px;
    display: flex; align-items: center; justify-content: center;
    color: #ffffff; font-weight: 700; font-size: 1.15rem;
    font-family: 'Sora', sans-serif; margin-bottom: 0.8rem;
    box-shadow: 0 6px 22px rgba(229,90,43,0.30);
}
.auth-app-title {
    font-size: 1.45rem; font-weight: 700;
    color: #0f172a; font-family: 'Sora', sans-serif;
}
.auth-app-sub {
    font-size: 0.81rem; color: #475569;
    font-family: 'Sora', sans-serif; margin-top: 0.15rem;
}
.auth-info-box {
    background: rgba(13,148,136,0.07);
    border: 1px solid rgba(13,148,136,0.22);
    border-radius: 10px; padding: 0.8rem 1rem;
    margin-bottom: 1.25rem; font-size: 0.82rem;
    color: #0f4c45; font-family: 'Sora', sans-serif; line-height: 1.55;
}
.pw-strength-bar {
    height: 4px; border-radius: 2px; margin-top: 0.35rem;
    background: #e2e8f0; overflow: hidden;
}
.pw-strength-fill { height: 100%; border-radius: 2px; transition: width 0.3s, background 0.3s; }
.pw-strength-label { font-size: 0.71rem; margin-top: 0.2rem; font-family: 'Sora', sans-serif; }

.stTextInput label {
    color: #1e293b !important; font-size: 0.84rem !important;
    font-weight: 600 !important; font-family: 'Sora', sans-serif !important;
}
.stTextInput > div > div > input {
    background: #f8fafc !important; border: 1.5px solid #e2e8f0 !important;
    border-radius: 11px !important; color: #0f172a !important;
    font-family: 'Sora', sans-serif !important; font-size: 0.88rem !important; height: 46px !important;
}
.stTextInput > div > div > input:focus {
    border-color: #e55a2b !important;
    box-shadow: 0 0 0 3px rgba(229,90,43,0.1) !important;
    background: #ffffff !important;
}

.st-key-update_pw_btn button {
    background: linear-gradient(135deg, #e55a2b 0%, #c94d22 100%) !important;
    color: #ffffff !important; border: none !important; border-radius: 12px !important;
    font-family: 'Sora', sans-serif !important; font-weight: 600 !important;
    font-size: 0.92rem !important; height: 48px !important;
    box-shadow: 0 4px 16px rgba(229,90,43,0.35) !important;
}
.st-key-update_pw_btn button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 7px 22px rgba(229,90,43,0.45) !important;
}
.st-key-go_to_login button {
    background: transparent !important; color: #e55a2b !important;
    border: none !important; font-family: 'Sora', sans-serif !important;
    font-size: 0.84rem !important; font-weight: 600 !important;
    text-decoration: underline !important; box-shadow: none !important;
}
div[data-testid="stSuccess"] p,
div[data-testid="stError"] p,
div[data-testid="stInfo"] p {
    color: inherit !important; font-family: 'Sora', sans-serif !important;
}
</style>
""", unsafe_allow_html=True)


# ──────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────

@st.cache_resource
def _sb() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def _logo():
    st.markdown("""
    <div class="auth-logo-wrap">
        <div class="auth-logo-icon">GP</div>
        <div class="auth-app-title">Nueva contraseña</div>
        <div class="auth-app-sub">Elige una contraseña segura para tu cuenta</div>
    </div>
    """, unsafe_allow_html=True)


def _pw_strength(pw: str) -> str:
    if not pw:
        return ""
    score = sum([
        len(pw) >= 8,
        any(c.isupper() for c in pw),
        any(c.isdigit() for c in pw),
        any(c in "!@#$%^&*()-_=+" for c in pw),
    ])
    colors = ["#ef4444", "#f59e0b", "#22c55e", "#0d9488"]
    labels = ["Muy débil", "Débil", "Buena", "Segura"]
    color  = colors[score - 1] if score else "#ef4444"
    label  = labels[score - 1] if score else "Muy débil"
    width  = score * 25
    return f"""
    <div class="pw-strength-bar">
        <div class="pw-strength-fill" style="width:{width}%;background:{color};"></div>
    </div>
    <div class="pw-strength-label" style="color:{color};">{label}</div>
    """


def _go_to_login():
    """Redirige al usuario a la app principal."""
    st.markdown(
        '<meta http-equiv="refresh" content="0; url=/">',
        unsafe_allow_html=True,
    )
    st.stop()


# ──────────────────────────────────────────────
# LÓGICA PRINCIPAL
# ──────────────────────────────────────────────

_logo()

params = st.query_params

# ── Caso 1: llegó con `code` (PKCE flow — el más común y recomendado) ──────
if "code" in params:
    code = params.get("code", "")

    # Intercambiar el code por una sesión activa (solo una vez)
    if not st.session_state.get("_recovery_session_ok"):
        try:
            result = _sb().auth.exchange_code_for_session({"auth_code": code})
            if result and result.user:
                st.session_state._recovery_session_ok = True
                st.session_state._recovery_user_email = result.user.email
            else:
                st.error(
                    "El enlace de recuperación no es válido o ya fue utilizado. "
                    "Solicita uno nuevo."
                )
                if st.button("Volver al inicio", key="go_to_login"):
                    _go_to_login()
                st.stop()
        except Exception as e:
            err = str(e)
            if "expired" in err.lower() or "invalid" in err.lower():
                st.error("El enlace ha expirado. Solicita un nuevo correo de recuperación.")
            else:
                st.error(f"Error al validar el enlace: {err}")
            if st.button("Volver al inicio", key="go_to_login"):
                _go_to_login()
            st.stop()

# ── Caso 2: llegó con `access_token` directamente (implicit flow — fallback) ──
elif "access_token" in params and params.get("type") == "recovery":
    at = params.get("access_token", "")
    rt = params.get("refresh_token", "")

    if not st.session_state.get("_recovery_session_ok"):
        try:
            result = _sb().auth.set_session(at, rt)
            if result and result.user:
                st.session_state._recovery_session_ok = True
                st.session_state._recovery_user_email = result.user.email
            else:
                raise ValueError("Sesión inválida")
        except Exception as e:
            st.error("El enlace de recuperación no es válido o ha expirado.")
            if st.button("Volver al inicio", key="go_to_login"):
                _go_to_login()
            st.stop()

# ── Sin parámetros válidos ─────────────────────────────────────────────────
else:
    st.error(
        "Esta página solo es accesible desde el enlace de recuperación "
        "que Supabase envía a tu correo."
    )
    if st.button("Ir al inicio de sesión", key="go_to_login"):
        _go_to_login()
    st.stop()


# ── Formulario de nueva contraseña ────────────────────────────────────────
st.markdown("""
<div class="auth-info-box">
    Ingresa tu nueva contraseña. Debe tener al menos 6 caracteres.
</div>
""", unsafe_allow_html=True)

user_email = st.session_state.get("_recovery_user_email", "")
if user_email:
    st.markdown(
        f'<p style="font-size:0.8rem;color:#475569;font-family:Sora,sans-serif;'
        f'margin-bottom:1rem;">Cuenta: <strong>{user_email}</strong></p>',
        unsafe_allow_html=True,
    )

new_pw = st.text_input(
    "Nueva contraseña",
    type="password",
    placeholder="Mínimo 6 caracteres",
    key="recovery_pw1",
)
if new_pw:
    st.markdown(_pw_strength(new_pw), unsafe_allow_html=True)

st.markdown("<div style='height:0.15rem'></div>", unsafe_allow_html=True)

conf_pw = st.text_input(
    "Confirmar contraseña",
    type="password",
    placeholder="Repite la contraseña",
    key="recovery_pw2",
)

st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)

if st.button("Actualizar contraseña", key="update_pw_btn", use_container_width=True):
    if not new_pw:
        st.error("Ingresa una nueva contraseña.")
    elif len(new_pw) < 6:
        st.error("La contraseña debe tener al menos 6 caracteres.")
    elif new_pw != conf_pw:
        st.error("Las contraseñas no coinciden.")
    else:
        try:
            _sb().auth.update_user({"password": new_pw})

            # Limpiar estado de recovery
            st.session_state.pop("_recovery_session_ok", None)
            st.session_state.pop("_recovery_user_email", None)
            st.query_params.clear()

            st.success(
                "✅ Contraseña actualizada correctamente. "
                "Ya puedes iniciar sesión con tu nueva contraseña."
            )
            st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
            if st.button("Ir al inicio de sesión", key="go_to_login_success"):
                _go_to_login()

        except Exception as e:
            err = str(e)
            if "same password" in err.lower():
                st.error("La nueva contraseña no puede ser igual a la anterior.")
            elif "weak" in err.lower() or "short" in err.lower():
                st.error("La contraseña es demasiado débil. Usa al menos 8 caracteres.")
            else:
                st.error(f"No se pudo actualizar la contraseña: {err}")