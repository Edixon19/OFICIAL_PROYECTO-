"""
GestorPro — Módulo de Autenticación con Supabase Auth
======================================================
Maneja: Email/Password · Google OAuth · Registro · Recuperación de contraseña
"""

import streamlit as st
from supabase import create_client, Client

# ──────────────────────────────────────────────
# CONFIG
# ──────────────────────────────────────────────
SUPABASE_URL      = "https://wopthjsdceattleaeczt.supabase.co"
SUPABASE_ANON_KEY = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
    ".eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6IndvcHRoanNkY2VhdHRsZWFlY3p0Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzY3MzM3NjYsImV4cCI6MjA5MjMwOTc2Nn0"
    ".QNCHhCzedHSGPul5S-JWZUo3jEV6959tWoKEEeNHztA"
)
# ⚠️ Cambia esta URL a la de producción cuando despliegues
SITE_URL = "http://localhost:8501"


@st.cache_resource
def _sb() -> Client:
    """Instancia cacheada del cliente Supabase."""
    return create_client(SUPABASE_URL, SUPABASE_ANON_KEY)


# ══════════════════════════════════════════════
#  FUNCIONES DE AUTENTICACIÓN
# ══════════════════════════════════════════════

def auth_login(email: str, password: str):
    """
    Inicia sesión con email y contraseña.
    Retorna (user, session, error_str).
    """
    try:
        res = _sb().auth.sign_in_with_password({"email": email, "password": password})
        return res.user, res.session, None
    except Exception as e:
        err = str(e)
        if "Invalid login" in err or "invalid_credentials" in err:
            return None, None, "Correo o contraseña incorrectos."
        if "Email not confirmed" in err:
            return None, None, "Confirma tu correo electrónico antes de iniciar sesión."
        return None, None, "Error al iniciar sesión. Intenta de nuevo."


def auth_register(email: str, password: str, full_name: str):
    """
    Registra un nuevo usuario.
    Retorna (user, error_str).
    """
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
        if "already registered" in err or "already exists" in err:
            return None, "Este correo ya está registrado. Intenta iniciar sesión."
        if "Password" in err:
            return None, "La contraseña debe tener al menos 6 caracteres."
        return None, "Error al crear la cuenta. Intenta de nuevo."


def auth_reset_password(email: str):
    """
    Envía un correo de recuperación de contraseña.
    Retorna (ok, error_str).
    """
    try:
        _sb().auth.reset_password_email(
            email,
            options={"redirect_to": f"{SITE_URL}?reset=1"},
        )
        return True, None
    except Exception as e:
        return False, "No se pudo enviar el correo. Verifica la dirección."


def auth_get_google_url():
    """
    Genera la URL de autorización OAuth de Google.
    Retorna (url, error_str).
    """
    try:
        res = _sb().auth.sign_in_with_oauth({
            "provider": "google",
            "options": {
                "redirect_to": SITE_URL,
                "scopes": "email profile",
            },
        })
        return res.url, None
    except Exception as e:
        return None, str(e)


def auth_set_session(access_token: str, refresh_token: str) -> bool:
    """
    Restaura la sesión a partir de tokens OAuth (después del callback de Google).
    Retorna True si tuvo éxito.
    """
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
    """
    Obtiene el usuario actual de la sesión activa de Supabase.
    Retorna el objeto user o None.
    """
    try:
        res = _sb().auth.get_user()
        return res.user if res else None
    except Exception:
        return None


def auth_logout():
    """Cierra la sesión y limpia el estado de sesión."""
    try:
        _sb().auth.sign_out()
    except Exception:
        pass
    keys = [k for k in st.session_state if k.startswith("auth_") or k == "db_ok"]
    for k in keys:
        del st.session_state[k]


def auth_user_display(user) -> tuple:
    """
    Extrae nombre y email del objeto user de Supabase.
    Retorna (display_name, email).
    """
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
    """Retorna el UUID del usuario autenticado, o None."""
    user = st.session_state.get("auth_user")
    if user:
        return str(getattr(user, "id", None))
    return None


# ══════════════════════════════════════════════
#  CSS DE PÁGINAS DE AUTENTICACIÓN
# ══════════════════════════════════════════════

_AUTH_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Sora:wght@300;400;500;600;700&display=swap');

/* ── Fondo degradado ── */
html, body { font-family: 'Sora', sans-serif !important; }
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

/* ── Ocultar sidebar, menú y header ── */
section[data-testid="stSidebar"],
header[data-testid="stHeader"],
[data-testid="collapsedControl"],
[data-testid="stSidebarCollapseButton"],
[data-testid="stSidebarCollapsedControl"],
#MainMenu, footer, .stDeployButton {
    display: none !important;
    visibility: hidden !important;
}

/* ── Contenedor centrado tipo tarjeta ── */
.main .block-container {
    padding: 4vh 1rem 2rem !important;
    max-width: 440px !important;
    margin: 0 auto !important;
}

/* ── Card ── */
.auth-card {
    background: #ffffff;
    border-radius: 26px;
    padding: 2.5rem 2.25rem 2.25rem;
    box-shadow: 0 24px 70px rgba(0,0,0,0.13);
    font-family: 'Sora', sans-serif;
}

/* ── Logo ── */
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
    color: white; font-weight: 700; font-size: 1.15rem;
    font-family: 'Sora', sans-serif;
    margin-bottom: 0.8rem;
    box-shadow: 0 6px 22px rgba(229,90,43,0.30);
}
.auth-app-title {
    font-size: 1.45rem; font-weight: 700;
    color: #0f172a; font-family: 'Sora', sans-serif;
}
.auth-app-sub {
    font-size: 0.81rem; color: #64748b;
    font-family: 'Sora', sans-serif; margin-top: 0.15rem;
}

/* ── Inputs ── */
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
    background: #fff !important;
}
.stTextInput label {
    font-size: 0.84rem !important;
    font-weight: 500 !important;
    color: #1e293b !important;
    font-family: 'Sora', sans-serif !important;
}

/* ── Botón principal CTA ── */
.st-key-auth_login_btn button,
.st-key-auth_register_btn button,
.st-key-auth_reset_btn button {
    background: linear-gradient(135deg, #e55a2b 0%, #c94d22 100%) !important;
    color: white !important;
    border: none !important;
    border-radius: 12px !important;
    font-family: 'Sora', sans-serif !important;
    font-weight: 600 !important;
    font-size: 0.92rem !important;
    height: 48px !important;
    box-shadow: 0 4px 16px rgba(229,90,43,0.38) !important;
    letter-spacing: 0.01em !important;
    transition: all 0.2s !important;
}
.st-key-auth_login_btn button:hover,
.st-key-auth_register_btn button:hover,
.st-key-auth_reset_btn button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 7px 22px rgba(229,90,43,0.48) !important;
}

/* ── Botones de proveedores OAuth ── */
.st-key-auth_google_btn button,
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
.st-key-auth_github_btn button:hover {
    border-color: #cbd5e1 !important;
    background: #f8fafc !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 3px 10px rgba(0,0,0,0.1) !important;
}

/* ── Botones de texto / navegación ── */
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
    transition: color 0.15s !important;
}
.st-key-auth_to_register button:hover,
.st-key-auth_to_login button:hover,
.st-key-auth_to_forgot button:hover,
.st-key-auth_back_login button:hover {
    color: #c94d22 !important;
    transform: none !important;
}

/* ── Checkbox ── */
.stCheckbox label, .stCheckbox span {
    font-size: 0.82rem !important;
    color: #475569 !important;
    font-family: 'Sora', sans-serif !important;
}

/* ── Separador "o continúa con" ── */
.auth-divider {
    display: flex; align-items: center; gap: 0.75rem;
    margin: 1.2rem 0;
    color: #94a3b8; font-size: 0.78rem;
    font-family: 'Sora', sans-serif;
}
.auth-divider::before, .auth-divider::after {
    content: ''; flex: 1;
    height: 1px; background: #e2e8f0;
}

/* ── Footer legal ── */
.auth-footer {
    text-align: center; margin-top: 1.75rem;
    font-size: 0.7rem; color: #94a3b8;
    font-family: 'Sora', sans-serif; line-height: 1.7;
}
.auth-footer a { color: #e55a2b; text-decoration: none; }

/* ── Alertas ── */
div[data-testid="stSuccess"],
div[data-testid="stError"],
div[data-testid="stInfo"],
div[data-testid="stWarning"] {
    border-radius: 10px !important;
    font-family: 'Sora', sans-serif !important;
    font-size: 0.84rem !important;
}
div[data-testid="stSuccess"] p,
div[data-testid="stError"] p,
div[data-testid="stInfo"] p { color: inherit !important; }

/* Scrollbar mínima */
::-webkit-scrollbar { width: 4px; }
::-webkit-scrollbar-thumb { background: #e2e8f0; border-radius: 2px; }
</style>
"""

# ══════════════════════════════════════════════
#  JAVASCRIPT: MANEJO DEL CALLBACK OAUTH
# ══════════════════════════════════════════════

_OAUTH_CALLBACK_JS = """
<script>
(function handleOAuthCallback() {
    /* Supabase devuelve los tokens en el hash (#) de la URL después de OAuth.
       Streamlit no puede leer el hash desde Python, así que lo convertimos
       a query params (?access_token=...) y recargamos la página. */
    var hash = window.location.hash;
    if (hash && hash.length > 1 && hash.includes('access_token')) {
        var params = new URLSearchParams(hash.substring(1));
        var at = params.get('access_token');
        var rt = params.get('refresh_token') || '';
        var tt = params.get('token_type')    || '';
        if (at) {
            var url = new URL(window.location.href);
            url.hash = '';
            url.searchParams.set('access_token',  at);
            url.searchParams.set('refresh_token', rt);
            window.location.replace(url.toString());
        }
    }
})();
</script>
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
        f'<p style="font-size:0.82rem;color:#475569;font-family:Sora,sans-serif;'
        f'margin:0.3rem 0 0;">{text}</p>',
        unsafe_allow_html=True,
    )


# ══════════════════════════════════════════════
#  PÁGINA: INICIO DE SESIÓN
# ══════════════════════════════════════════════

def _render_login():
    # ── Manejar redirect pendiente a Google (evita problemas de rerun) ──
    if "_redirect_to" in st.session_state:
        url = st.session_state.pop("_redirect_to")
        st.markdown(
            f'<script>window.top.location.replace("{url}");</script>',
            unsafe_allow_html=True,
        )
        st.markdown(
            f'Redirigiendo a Google… <a href="{url}" target="_self">Haz clic aquí</a> '
            f'si no redirige automáticamente.',
            unsafe_allow_html=True,
        )
        st.stop()

    # ── Manejar callback OAuth: tokens en query params ──
    params = st.query_params
    if "access_token" in params:
        at = params.get("access_token", "")
        rt = params.get("refresh_token", "")
        st.query_params.clear()
        if at and auth_set_session(at, rt):
            st.rerun()
        else:
            st.error("❌ Error al procesar la sesión de Google. Intenta de nuevo.")

    st.markdown(_logo("GestorPro", "Bienvenido de vuelta"), unsafe_allow_html=True)

    email    = st.text_input("Correo electrónico", placeholder="tu@email.com", key="login_email")
    password = st.text_input("Contraseña",         placeholder="••••••••",     key="login_pass", type="password")

    col_rem, col_forgot = st.columns([3, 2])
    with col_rem:
        st.checkbox("Recuérdame", key="login_remember")
    with col_forgot:
        _spacer(0.05)
        if st.button("¿Olvidaste tu contraseña?", key="auth_to_forgot"):
            st.session_state.auth_page = "forgot"
            st.rerun()

    _spacer(0.4)

    if st.button("→ Iniciar Sesión", key="auth_login_btn", use_container_width=True):
        if not email.strip():
            st.error("⚠️ Ingresa tu correo electrónico.")
        elif not password:
            st.error("⚠️ Ingresa tu contraseña.")
        else:
            with st.spinner(""):
                user, session, err = auth_login(email.strip(), password)
            if err:
                st.error(f"❌ {err}")
            else:
                st.session_state.auth_user    = user
                st.session_state.auth_session = session
                st.rerun()

    st.markdown('<div class="auth-divider">o continúa con</div>', unsafe_allow_html=True)

    col_g, col_gh = st.columns(2)
    with col_g:
        if st.button("🌐  Google", key="auth_google_btn", use_container_width=True):
            url, err = auth_get_google_url()
            if url:
                st.session_state._redirect_to = url
                st.rerun()
            else:
                st.error(f"❌ Error OAuth: {err}")
    with col_gh:
        if st.button("🐙  GitHub", key="auth_github_btn", use_container_width=True):
            st.info("GitHub OAuth próximamente.")

    _spacer(0.6)
    col_txt, col_btn = st.columns([5, 3])
    with col_txt:
        _small_text("¿No tienes una cuenta?")
    with col_btn:
        if st.button("Regístrate aquí", key="auth_to_register"):
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
    if "_redirect_to" in st.session_state:
        url = st.session_state.pop("_redirect_to")
        st.markdown(
            f'<script>window.top.location.replace("{url}");</script>',
            unsafe_allow_html=True,
        )
        st.stop()

    st.markdown(_logo("Crear cuenta", "Únete a GestorPro hoy"), unsafe_allow_html=True)

    full_name = st.text_input("Nombre completo",      placeholder="Ana García",           key="reg_name")
    email     = st.text_input("Correo electrónico",   placeholder="tu@email.com",         key="reg_email")
    password  = st.text_input("Contraseña",           placeholder="Mínimo 6 caracteres",  key="reg_pass",  type="password")
    password2 = st.text_input("Confirmar contraseña", placeholder="••••••••",              key="reg_pass2", type="password")

    _spacer(0.4)

    if st.button("✅ Crear cuenta", key="auth_register_btn", use_container_width=True):
        if not full_name.strip():
            st.error("⚠️ Ingresa tu nombre completo.")
        elif not email.strip():
            st.error("⚠️ Ingresa tu correo electrónico.")
        elif len(password) < 6:
            st.error("⚠️ La contraseña debe tener al menos 6 caracteres.")
        elif password != password2:
            st.error("⚠️ Las contraseñas no coinciden.")
        else:
            with st.spinner(""):
                user, err = auth_register(email.strip(), password, full_name.strip())
            if err:
                st.error(f"❌ {err}")
            else:
                st.success("✅ ¡Cuenta creada exitosamente!")
                st.info(
                    "📧 Revisa tu bandeja de entrada y confirma tu correo. "
                    "Después podrás iniciar sesión."
                )

    st.markdown('<div class="auth-divider">o continúa con</div>', unsafe_allow_html=True)

    col_g2, _ = st.columns([1, 1])
    with col_g2:
        if st.button("🌐  Google", key="auth_google_btn", use_container_width=True):
            url, err = auth_get_google_url()
            if url:
                st.session_state._redirect_to = url
                st.rerun()
            else:
                st.error(f"❌ {err}")

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

    email = st.text_input("Correo electrónico", placeholder="tu@email.com", key="forgot_email")

    _spacer(0.4)

    if st.button("📧 Enviar enlace de recuperación", key="auth_reset_btn", use_container_width=True):
        if not email.strip():
            st.error("⚠️ Ingresa tu correo electrónico.")
        else:
            with st.spinner(""):
                ok, err = auth_reset_password(email.strip())
            if ok:
                st.success(
                    "✅ Si ese correo está registrado, recibirás el enlace en breve. "
                    "Revisa también la carpeta de spam."
                )
            else:
                st.error(f"❌ {err}")

    _spacer(0.75)
    if st.button("← Volver al inicio de sesión", key="auth_back_login"):
        st.session_state.auth_page = "login"
        st.rerun()


# ══════════════════════════════════════════════
#  PUNTO DE ENTRADA PRINCIPAL
# ══════════════════════════════════════════════

def render_auth():
    """
    Renderiza la página de autenticación activa.
    Llama a esta función desde app.py cuando el usuario no está autenticado.
    """
    st.markdown(_AUTH_CSS,           unsafe_allow_html=True)
    st.markdown(_OAUTH_CALLBACK_JS,  unsafe_allow_html=True)

    if "auth_page" not in st.session_state:
        st.session_state.auth_page = "login"

    dispatch = {
        "login":    _render_login,
        "register": _render_register,
        "forgot":   _render_forgot,
    }
    dispatch.get(st.session_state.auth_page, _render_login)()