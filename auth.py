"""
GestorPro — Módulo de Autenticación con Supabase Auth
======================================================
Maneja: Email/Password · Google OAuth · Registro · Recuperación de contraseña
v3.4 — Fix URL OAuth (sin doble codificación)
"""

from pandas.core import window
import streamlit as st
from supabase import create_client, Client

import os

# ──────────────────────────────────────────────
# CONFIG
# ──────────────────────────────────────────────
SUPABASE_URL = os.getenv("SUPABASE_PUBLIC_URL", "https://wopthjsdceattleaeczt.supabase.co")
SUPABASE_ANON_KEY = os.getenv(
    "SUPABASE_ANON_KEY",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
    ".eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6IndvcHRoanNkY2VhdHRsZWFlY3p0Iiw"
    "icm9sZSI6ImFub24iLCJpYXQiOjE3NzY3MzM3NjYsImV4cCI6MjA5MjMwOTc2Nn0"
    ".QNCHhCzedHSGPul5S-JWZUo3jEV6959tWoKEEeNHztA"
)

SITE_URL  = os.getenv("SITE_URL", "https://gestorpro.streamlit.app")
RESET_URL = os.getenv("RESET_URL", f"{SITE_URL}/reset_password")


@st.cache_resource
def _sb() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_ANON_KEY)


# ══════════════════════════════════════════════
#  FUNCIONES DE AUTENTICACIÓN
# ══════════════════════════════════════════════

def auth_login(email: str, password: str):
    try:
        res = _sb().auth.sign_in_with_password({"email": email, "password": password})
        return res.user, res.session, None
    except Exception as e:
        err = str(e)
        if "Invalid login" in err or "invalid_credentials" in err:
            return None, None, "Correo o contraseña incorrectos."
        if "Email not confirmed" in err:
            return None, None, "Confirma tu correo electrónico antes de iniciar sesión."
        return None, None, "Error al iniciar sesión. Inténtalo de nuevo."


def auth_register(email: str, password: str, full_name: str):
    try:
        res = _sb().auth.sign_up({
            "email": email,
            "password": password,
            "options": {
                "data": {"full_name": full_name, "display_name": full_name}
            },
        })
        return res.user, None
    except Exception as e:
        err = str(e)
        print(err) 
        if "already registered" in err or "already exists" in err:
            return None, "Este correo ya está registrado. Intenta iniciar sesión."
        if "Password" in err:
            return None, "La contraseña debe tener al menos 6 caracteres."
        return None, "Error al crear la cuenta. Inténtalo de nuevo."


def auth_reset_password(email: str):
    try:
        _sb().auth.reset_password_email(
            email,
            options={"redirect_to": RESET_URL},
        )
        return True, None
    except Exception as e:
        return False, str(e)


def auth_get_google_url():
    """
    Construye la URL OAuth de Google SIN codificar el redirect_to.
    El navegador se encarga de la codificación al hacer la solicitud HTTP.
    Codificarlo manualmente causa doble codificación → 403 Forbidden.
    """
    try:
        url = f"{SUPABASE_URL}/auth/v1/authorize?provider=google&redirect_to={SITE_URL}"
        return url, None
    except Exception as e:
        return None, str(e)


def auth_set_session(access_token: str, refresh_token: str) -> bool:
    try:
        res = _sb().auth.set_session(access_token, refresh_token)
        if res and res.user:
            st.session_state.auth_user    = res.user
            st.session_state.auth_session = res.session
            return True
    except Exception:
        pass
    return False


def auth_current_user():
    try:
        res = _sb().auth.get_user()
        return res.user if res else None
    except Exception:
        return None


def auth_logout():
    try:
        _sb().auth.sign_out()
    except Exception:
        pass
    keys = [k for k in st.session_state if k.startswith("auth_") or k == "db_ok"]
    for k in keys:
        del st.session_state[k]


def auth_user_display(user) -> tuple:
    if not user:
        return "Usuario", ""
    email = getattr(user, "email", "") or ""
    meta  = getattr(user, "user_metadata", {}) or {}
    name  = (
        meta.get("full_name")
        or meta.get("name")
        or email.split("@")[0].capitalize()
    )
    return name, email


def auth_user_id() -> str | None:
    user = st.session_state.get("auth_user")
    if user:
        return str(getattr(user, "id", None))
    return None


# ══════════════════════════════════════════════
#  CSS
# ══════════════════════════════════════════════

_AUTH_CSS = """
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
[data-testid="stSidebarCollapseButton"],
[data-testid="stSidebarCollapsedControl"],
#MainMenu, footer, .stDeployButton {
    display: none !important;
    visibility: hidden !important;
}

.main .block-container {
    padding: 4vh 2rem 2rem !important;
}

.auth-card {
    background: rgba(255,255,255,0.72);
    backdrop-filter: blur(18px);
    -webkit-backdrop-filter: blur(18px);
    border: 1px solid rgba(255,255,255,0.55);
    border-radius: 20px;
    box-shadow: 0 8px 40px rgba(0,0,0,0.10), 0 1.5px 6px rgba(0,0,0,0.06);
    padding: 2.4rem 2rem 2rem;
    max-width: 400px;
    width: 100%;
    margin: 0 auto;
}

.main p,
.main span:not([class*="st-"]),
.main div:not([data-testid]),
.main label,
.main h1, .main h2, .main h3, .main h4 {
    color: #0f172a;
}

.stTextInput label,
.stTextInput label p,
.stTextInput label span,
.stTextArea label,
.stTextArea label p {
    color: #1e293b !important;
    font-size: 0.84rem !important;
    font-weight: 600 !important;
    font-family: 'Sora', sans-serif !important;
}

.stCheckbox label,
.stCheckbox label span,
.stCheckbox label p {
    color: #334155 !important;
    font-size: 0.82rem !important;
    font-family: 'Sora', sans-serif !important;
}

div[data-testid="stSuccess"] p,
div[data-testid="stSuccess"] span,
div[data-testid="stError"] p,
div[data-testid="stError"] span,
div[data-testid="stInfo"] p,
div[data-testid="stInfo"] span,
div[data-testid="stWarning"] p,
div[data-testid="stWarning"] span {
    color: inherit !important;
}

.stTextInput > div > div > input {
    background: #f8fafc !important;
    border: 1.5px solid #e2e8f0 !important;
    border-radius: 11px !important;
    color: #0f172a !important;
    font-family: 'Sora', sans-serif !important;
    font-size: 0.88rem !important;
    height: 46px !important;
    box-shadow: none !important;
}
.stTextInput > div > div > input:focus {
    border-color: #e55a2b !important;
    box-shadow: 0 0 0 3px rgba(229,90,43,0.1) !important;
    background: #ffffff !important;
}
.stTextInput > div > div > input::placeholder {
    color: #94a3b8 !important;
}

.st-key-auth_login_btn button,
.st-key-auth_register_btn button,
.st-key-auth_reset_btn button {
    background: linear-gradient(135deg, #e55a2b 0%, #c94d22 100%) !important;
    color: #ffffff !important;
    border: none !important;
    border-radius: 12px !important;
    font-family: 'Sora', sans-serif !important;
    font-weight: 600 !important;
    font-size: 0.92rem !important;
    height: 48px !important;
    box-shadow: 0 4px 16px rgba(229,90,43,0.35) !important;
    transition: all 0.2s !important;
    letter-spacing: 0.01em !important;
}
.st-key-auth_login_btn button:hover,
.st-key-auth_register_btn button:hover,
.st-key-auth_reset_btn button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 7px 22px rgba(229,90,43,0.45) !important;
}

.st-key-auth_google_btn button,
.st-key-auth_google_btn2 button,
.st-key-auth_github_btn button {
    background: #ffffff !important;
    color: #1e293b !important;
    border: 1.5px solid #e2e8f0 !important;
    border-radius: 12px !important;
    font-family: 'Sora', sans-serif !important;
    font-weight: 500 !important;
    font-size: 0.88rem !important;
    height: 46px !important;
    box-shadow: 0 1px 4px rgba(0,0,0,0.06) !important;
    transition: all 0.2s !important;
}
.st-key-auth_google_btn button:hover,
.st-key-auth_google_btn2 button:hover,
.st-key-auth_github_btn button:hover {
    border-color: #cbd5e1 !important;
    background: #f8fafc !important;
    transform: translateY(-1px) !important;
}

.st-key-auth_to_register button,
.st-key-auth_to_login button,
.st-key-auth_to_forgot button,
.st-key-auth_back_login button {
    background: transparent !important;
    color: #e55a2b !important;
    border: none !important;
    font-family: 'Sora', sans-serif !important;
    font-size: 0.84rem !important;
    font-weight: 600 !important;
    padding: 0 4px !important;
    box-shadow: none !important;
    text-decoration: underline !important;
    min-height: auto !important;
    height: auto !important;
}
.st-key-auth_to_register button:hover,
.st-key-auth_to_login button:hover,
.st-key-auth_to_forgot button:hover,
.st-key-auth_back_login button:hover {
    color: #c94d22 !important;
    transform: none !important;
}

.st-key-auth_to_forgot {
    display: flex !important;
    justify-content: center !important;
}

.auth-divider {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    margin: 1.2rem 0;
    color: #64748b;
    font-size: 0.78rem;
    font-family: 'Sora', sans-serif;
}
.auth-divider::before, .auth-divider::after {
    content: '';
    flex: 1;
    height: 1px;
    background: #e2e8f0;
}

.auth-logo-wrap {
    display: flex;
    flex-direction: column;
    align-items: center;
    margin-bottom: 1.8rem;
}
.auth-logo-icon {
    width: 58px; height: 58px;
    background: linear-gradient(135deg, #e55a2b 0%, #0d9488 100%);
    border-radius: 16px;
    display: flex; align-items: center; justify-content: center;
    color: #ffffff !important;
    font-weight: 700; font-size: 1.15rem;
    font-family: 'Sora', sans-serif;
    margin-bottom: 0.8rem;
    box-shadow: 0 6px 22px rgba(229,90,43,0.30);
}
.auth-app-title {
    font-size: 1.45rem;
    font-weight: 700;
    color: #0f172a !important;
    font-family: 'Sora', sans-serif;
}
.auth-app-sub {
    font-size: 0.81rem;
    color: #475569 !important;
    font-family: 'Sora', sans-serif;
    margin-top: 0.15rem;
}

.auth-info-box {
    background: rgba(13,148,136,0.07);
    border: 1px solid rgba(13,148,136,0.22);
    border-radius: 10px;
    padding: 0.8rem 1rem;
    margin-bottom: 1.25rem;
    font-size: 0.82rem;
    color: #0f4c45 !important;
    font-family: 'Sora', sans-serif;
    line-height: 1.55;
}

.pw-strength-bar {
    height: 4px;
    border-radius: 2px;
    margin-top: 0.35rem;
    background: #e2e8f0;
    overflow: hidden;
}
.pw-strength-fill {
    height: 100%;
    border-radius: 2px;
    transition: width 0.3s, background 0.3s;
}
.pw-strength-label {
    font-size: 0.71rem;
    margin-top: 0.2rem;
    font-family: 'Sora', sans-serif;
}

.auth-footer {
    text-align: center;
    margin-top: 1.75rem;
    font-size: 0.7rem;
    color: #64748b !important;
    font-family: 'Sora', sans-serif;
    line-height: 1.7;
}
.auth-footer a {
    color: #e55a2b !important;
    text-decoration: none;
    font-weight: 600;
}

div[data-testid="stSuccess"],
div[data-testid="stError"],
div[data-testid="stInfo"],
div[data-testid="stWarning"] {
    border-radius: 10px !important;
    font-family: 'Sora', sans-serif !important;
    font-size: 0.84rem !important;
}

::-webkit-scrollbar { width: 4px; }
::-webkit-scrollbar-thumb { background: #e2e8f0; border-radius: 2px; }
</style>
"""


# ══════════════════════════════════════════════
#  HELPERS DE UI
# ══════════════════════════════════════════════

def _logo(title: str, subtitle: str) -> str:
    return f"""
    <div class="auth-logo-wrap">
        <div class="auth-logo-icon">GP</div>
        <div class="auth-app-title">{title}</div>
        <div class="auth-app-sub">{subtitle}</div>
    </div>
    """


def _spacer(rem: float = 0.5):
    st.markdown(f"<div style='height:{rem}rem'></div>", unsafe_allow_html=True)


def _small_text(text: str):
    st.markdown(
        f'<p style="font-size:0.82rem;color:#334155 !important;'
        f'font-family:Sora,sans-serif;margin:0.3rem 0 0;">{text}</p>',
        unsafe_allow_html=True,
    )


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
    <div class="pw-strength-label" style="color:{color} !important;">{label}</div>
    """


def _google_redirect():
    """Obtiene la URL de Google y redirige con meta refresh."""
    url, err = auth_get_google_url()
    if url:
        st.markdown(
            f'<meta http-equiv="refresh" content="0; url={url}">',
            unsafe_allow_html=True,
        )
        st.stop()
    else:
        st.error(f"Error OAuth: {err}")


# ══════════════════════════════════════════════
#  PÁGINA: INICIO DE SESIÓN
# ══════════════════════════════════════════════

def _render_login():
    # ── Callback OAuth de Google ───────────────────────────────────────────
    params = st.query_params
    if "access_token" in params and params.get("type", "") not in ("recovery",):
        at = params.get("access_token", "")
        rt = params.get("refresh_token", "")
        st.query_params.clear()
        if at and auth_set_session(at, rt):
            st.rerun()
        else:
            st.error("Error al procesar la sesión de Google. Inténtalo de nuevo.")
        return

    # ── Formulario ────────────────────────────────────────────────────────
    st.markdown(_logo("GestorPro", "Bienvenido de vuelta"), unsafe_allow_html=True)

    email    = st.text_input("Correo electrónico", placeholder="tu@email.com", key="login_email")
    password = st.text_input(
        "Contraseña", placeholder="••••••••", key="login_pass", type="password"
    )

    col_rem, col_forgot = st.columns([3, 2])
    with col_rem:
        st.checkbox("Recuérdame", key="login_remember")
    with col_forgot:
        _spacer(0.05)
        if st.button("¿Olvidaste tu contraseña?", key="auth_to_forgot"):
            st.session_state.auth_page = "forgot"
            st.rerun()

    _spacer(0.4)

    if st.button("Iniciar sesión", key="auth_login_btn", use_container_width=True):
        if not email.strip():
            st.error("Ingresa tu correo electrónico.")
        elif not password:
            st.error("Ingresa tu contraseña.")
        else:
            with st.spinner(""):
                user, session, err = auth_login(email.strip(), password)
            if err:
                st.error(err)
            else:
                st.session_state.auth_user    = user
                st.session_state.auth_session = session
                st.rerun()

    st.markdown('<div class="auth-divider">o continúa con</div>', unsafe_allow_html=True)

    col_g, col_gh = st.columns(2)
    with col_g:
        if st.button("🔵  Google", key="auth_google_btn", use_container_width=True):
            _google_redirect()
    with col_gh:
        if st.button("GitHub", key="auth_github_btn", use_container_width=True):
            st.info("GitHub OAuth próximamente disponible.")

    _spacer(0.6)
    col_txt, col_btn = st.columns([5, 3])
    with col_txt:
        _small_text("¿No tienes una cuenta?")
    with col_btn:
        if st.button("Regístrate aquí", key="auth_to_register", use_container_width=True):
            st.session_state.auth_page = "register"
            st.rerun()

    st.markdown(
        '<div class="auth-footer">'
        'Al continuar, aceptas nuestros '
        '<a href="#">Términos de Servicio</a> y '
        '<a href="#">Política de Privacidad</a>'
        '</div>',
        unsafe_allow_html=True,
    )


# ══════════════════════════════════════════════
#  PÁGINA: REGISTRO
# ══════════════════════════════════════════════

def _render_register():
    st.markdown(_logo("Crear cuenta", "Únete a GestorPro hoy"), unsafe_allow_html=True)

    full_name = st.text_input("Nombre completo", placeholder="Ana García", key="reg_name")
    email     = st.text_input("Correo electrónico", placeholder="tu@email.com", key="reg_email")
    password  = st.text_input(
        "Contraseña", placeholder="Mínimo 6 caracteres", key="reg_pass", type="password"
    )
    if password:
        st.markdown(_pw_strength(password), unsafe_allow_html=True)
    _spacer(0.1)
    password2 = st.text_input(
        "Confirmar contraseña", placeholder="Repite la contraseña",
        key="reg_pass2", type="password"
    )

    _spacer(0.4)

    if st.button("Crear cuenta", key="auth_register_btn", use_container_width=True):
        if not full_name.strip():
            st.error("Ingresa tu nombre completo.")
        elif not email.strip():
            st.error("Ingresa tu correo electrónico.")
        elif len(password) < 6:
            st.error("La contraseña debe tener al menos 6 caracteres.")
        elif password != password2:
            st.error("Las contraseñas no coinciden.")
        else:
            with st.spinner(""):
                user, err = auth_register(email.strip(), password, full_name.strip())
            if err:
                st.error(err)
            else:
                st.success("Cuenta creada correctamente.")
                st.info(
                    "Revisa tu bandeja de entrada y confirma tu correo. "
                    "Después podrás iniciar sesión."
                )

    st.markdown('<div class="auth-divider">o continúa con</div>', unsafe_allow_html=True)

    col_g2, _ = st.columns([1, 1])
    with col_g2:
        if st.button("🔵  Google", key="auth_google_btn2", use_container_width=True):
            _google_redirect()

    _spacer(0.6)
    col_txt2, col_btn2 = st.columns([5, 3])
    with col_txt2:
        _small_text("¿Ya tienes una cuenta?")
    with col_btn2:
        if st.button("Iniciar sesión", key="auth_to_login"):
            st.session_state.auth_page = "login"
            st.rerun()


# ══════════════════════════════════════════════
#  PÁGINA: RECUPERAR CONTRASEÑA
# ══════════════════════════════════════════════

def _render_forgot():
    st.markdown(
        _logo("Recuperar contraseña", "Te enviaremos un enlace por correo"),
        unsafe_allow_html=True,
    )

    st.markdown("""
    <div class="auth-info-box">
        Ingresa el correo asociado a tu cuenta y te enviaremos un enlace para
        restablecer tu contraseña. Revisa también la carpeta de spam.
    </div>
    """, unsafe_allow_html=True)

    email = st.text_input("Correo electrónico", placeholder="tu@email.com", key="forgot_email")

    _spacer(0.4)

    if st.button("Enviar enlace de recuperación", key="auth_reset_btn", use_container_width=True):
        if not email.strip():
            st.error("Ingresa tu correo electrónico.")
        else:
            with st.spinner("Enviando..."):
                ok, err = auth_reset_password(email.strip())
            if ok:
                st.success("Correo enviado. Revisa tu bandeja de entrada y también la carpeta de spam.")
            else:
                err_lower = (err or "").lower()
                if "rate limit" in err_lower:
                    st.warning(
                        "Límite de correos alcanzado. "
                        "Supabase permite máximo 2 correos por hora en el plan gratuito. "
                        "Espera unos minutos e inténtalo de nuevo."
                    )
                else:
                    st.error(f"No se pudo enviar el correo: {err}")

    _spacer(0.75)
    if st.button("Volver al inicio de sesión", key="auth_back_login"):
        st.session_state.auth_page = "login"
        st.rerun()


# ══════════════════════════════════════════════
#  PUNTO DE ENTRADA PRINCIPAL
# ══════════════════════════════════════════════

def render_auth():
    st.markdown(_AUTH_CSS, unsafe_allow_html=True)

    if "auth_page" not in st.session_state:
        st.session_state.auth_page = "login"

    dispatch = {
        "login":    _render_login,
        "register": _render_register,
        "forgot":   _render_forgot,
    }

    # Center the card using columns and wrap content in the auth-card div
    _, col, _ = st.columns([1, 2, 1])
    with col:
         dispatch.get(st.session_state.auth_page, _render_login)()
