"""
GestorPro — Módulo de Autenticación con Supabase Auth
======================================================
Maneja: Email/Password · Google OAuth · Registro · Recuperación de contraseña
v2.1 — Detección de flujo recovery, textos con color fijo oscuro, menos emojis
"""

import streamlit as st
from supabase import create_client, Client

# ──────────────────────────────────────────────
# CONFIG
# ──────────────────────────────────────────────
SUPABASE_URL      = "https://wopthjsdceattleaeczt.supabase.co"
SUPABASE_ANON_KEY = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
    ".eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6IndvcHRoanNkY2VhdHRsZWFlY3p0Iiw"
    "icm9sZSI6ImFub24iLCJpYXQiOjE3NzY3MzM3NjYsImV4cCI6MjA5MjMwOTc2Nn0"
    ".QNCHhCzedHSGPul5S-JWZUo3jEV6959tWoKEEeNHztA"
)
# Cambia esta URL cuando despliegues en producción
SITE_URL = "https://gestorpro.streamlit.app/"


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
        return None, None, "Error al iniciar sesión. Inténtalo de nuevo."


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
        return None, "Error al crear la cuenta. Inténtalo de nuevo."


def auth_reset_password(email: str):
    """
    Envía un correo de recuperación de contraseña.
    Retorna (ok, error_str).

    IMPORTANTE sobre redirect_to:
      - La URL base debe estar registrada en Supabase →
        Authentication → URL Configuration → Redirect URLs.
      - Si redirect_to causa un error 422, se reintenta sin él
        (Supabase usará la Site URL configurada en el panel).
    """
    # Intento 1: con redirect_to explícito
    try:
        _sb().auth.reset_password_email(
            email,
            options={"redirect_to": f"{SITE_URL}?type=recovery"},
        )
        return True, None
    except Exception as e:
        err_msg = str(e)
        # Si el error es por redirect_to no permitida (422 / redirect_uri_mismatch)
        # reintentamos sin ese parámetro para no bloquear el envío
        if "redirect" in err_msg.lower() or "422" in err_msg or "url" in err_msg.lower():
            try:
                _sb().auth.reset_password_email(email)
                return True, None
            except Exception as e2:
                return False, str(e2)
        # Cualquier otro error: devolver el mensaje real para poder depurarlo
        return False, err_msg


def auth_update_password(new_password: str):
    """
    Actualiza la contraseña del usuario autenticado (flujo recovery).
    Requiere que la sesión ya esté establecida con auth_set_session.
    Retorna (ok, error_str).
    """
    try:
        _sb().auth.update_user({"password": new_password})
        return True, None
    except Exception as e:
        err = str(e)
        if "Password" in err or "short" in err.lower():
            return False, "La contraseña debe tener al menos 6 caracteres."
        return False, "No se pudo actualizar la contraseña. Inténtalo de nuevo."


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
    Restaura la sesión a partir de tokens OAuth (después del callback de Google o recovery).
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
#  CSS
# ══════════════════════════════════════════════

_AUTH_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Sora:wght@300;400;500;600;700&display=swap');

html, body { font-family: 'Sora', sans-serif !important; }

/* Fondo degradado */
.stApp {
    background: linear-gradient(
        145deg,
        #f2c4b5 0%, #e8b2a0 18%,
        #d4bdd8 42%, #aac4d8 68%,
        #8db4c8 100%
    ) !important;
    min-height: 100vh !important;
}

/* Ocultar elementos de Streamlit */
section[data-testid="stSidebar"],
header[data-testid="stHeader"],
[data-testid="collapsedControl"],
[data-testid="stSidebarCollapseButton"],
[data-testid="stSidebarCollapsedControl"],
#MainMenu, footer, .stDeployButton {
    display: none !important;
    visibility: hidden !important;
}

/* Contenedor centrado */
.main .block-container {
    padding: 4vh 1rem 2rem !important;
    max-width: 440px !important;
    margin: 0 auto !important;
}

/* ─────────────────────────────────────────────────────
   FIX GLOBAL: todos los textos nativos de Streamlit
   dentro del área principal con color oscuro fijo.
   Esto evita que hereden el blanco del tema oscuro
   cuando el fondo es claro (pantalla de auth).
──────────────────────────────────────────────────── */
.main p,
.main span:not([class*="st-"]),
.main div:not([data-testid]),
.main label,
.main h1, .main h2, .main h3, .main h4 {
    color: #0f172a;
}

/* Labels de inputs — selector específico para mayor peso */
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

/* Checkbox */
.stCheckbox label,
.stCheckbox label span,
.stCheckbox label p {
    color: #334155 !important;
    font-size: 0.82rem !important;
    font-family: 'Sora', sans-serif !important;
}

/* Textos dentro de mensajes de alerta: conservar color propio */
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

/* Inputs */
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

/* Botón CTA principal */
.st-key-auth_login_btn button,
.st-key-auth_register_btn button,
.st-key-auth_reset_btn button,
.st-key-auth_update_pw_btn button {
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
.st-key-auth_reset_btn button:hover,
.st-key-auth_update_pw_btn button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 7px 22px rgba(229,90,43,0.45) !important;
}

/* Botones OAuth */
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
}

/* Botones de navegación tipo enlace */
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

/* Divisor */
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

/* Logo */
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

/* Caja de info */
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

/* Indicador fortaleza de contraseña */
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

/* Footer legal */
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

/* Alertas de Streamlit */
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
#  JAVASCRIPT — convierte hash en query params
#  (necesario para OAuth y recovery desde email)
# ══════════════════════════════════════════════

_OAUTH_CALLBACK_JS = """
<script>
(function handleAuthCallback() {
    /*
     * Supabase devuelve tokens en el hash (#) de la URL tras OAuth o recovery.
     * Streamlit no puede leerlo desde Python, así que lo pasamos a query params.
     * El parámetro "type" se preserva para detectar el flujo de recuperación.
     */
    var hash = window.location.hash;
    if (hash && hash.length > 1 && hash.includes('access_token')) {
        var params = new URLSearchParams(hash.substring(1));
        var at   = params.get('access_token')  || '';
        var rt   = params.get('refresh_token') || '';
        var type = params.get('type')          || '';
        if (at) {
            var url = new URL(window.location.href);
            url.hash = '';
            url.searchParams.set('access_token',  at);
            url.searchParams.set('refresh_token', rt);
            if (type) url.searchParams.set('type', type);
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
        f'<p style="font-size:0.82rem;color:#334155 !important;'
        f'font-family:Sora,sans-serif;margin:0.3rem 0 0;">{text}</p>',
        unsafe_allow_html=True,
    )


def _pw_strength(pw: str) -> str:
    """Devuelve HTML del indicador de fortaleza de contraseña."""
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


# ══════════════════════════════════════════════
#  PANTALLA: NUEVA CONTRASEÑA (flujo recovery)
# ══════════════════════════════════════════════

def _render_reset_password(access_token: str, refresh_token: str):
    """
    Formulario para establecer una nueva contraseña después de hacer clic
    en el enlace del correo de recuperación.

    Pasos:
      1. Se establece la sesión con los tokens del enlace.
      2. El usuario ingresa y confirma su nueva contraseña.
      3. Se llama a auth.update_user({"password": ...}) para guardar el cambio.
    """
    # Establecer sesión con los tokens del enlace (solo una vez)
    if not st.session_state.get("_recovery_session_set"):
        ok = auth_set_session(access_token, refresh_token)
        if ok:
            st.session_state._recovery_session_set = True
        else:
            st.error(
                "El enlace de recuperación no es válido o ha expirado. "
                "Solicita uno nuevo desde la pantalla de inicio de sesión."
            )
            _spacer(0.75)
            if st.button("Volver al inicio de sesión", key="auth_back_login"):
                st.query_params.clear()
                st.session_state.pop("_recovery_session_set", None)
                st.session_state.auth_page = "login"
                st.rerun()
            return

    st.markdown(
        _logo("Nueva contraseña", "Elige una contraseña segura para tu cuenta"),
        unsafe_allow_html=True,
    )

    st.markdown("""
    <div class="auth-info-box">
        Ingresa tu nueva contraseña. Debe tener al menos 6 caracteres.
    </div>
    """, unsafe_allow_html=True)

    new_pw  = st.text_input(
        "Nueva contraseña",
        type="password",
        placeholder="Mínimo 6 caracteres",
        key="recovery_pw1",
    )
    if new_pw:
        st.markdown(_pw_strength(new_pw), unsafe_allow_html=True)

    _spacer(0.15)

    conf_pw = st.text_input(
        "Confirmar contraseña",
        type="password",
        placeholder="Repite la contraseña",
        key="recovery_pw2",
    )

    _spacer(0.5)

    if st.button("Actualizar contraseña", key="auth_update_pw_btn", use_container_width=True):
        if not new_pw:
            st.error("Ingresa una contraseña.")
        elif len(new_pw) < 6:
            st.error("La contraseña debe tener al menos 6 caracteres.")
        elif new_pw != conf_pw:
            st.error("Las contraseñas no coinciden.")
        else:
            ok, err = auth_update_password(new_pw)
            if ok:
                # Limpiar tokens de la URL y estado temporal
                st.query_params.clear()
                st.session_state.pop("_recovery_session_set", None)
                st.success(
                    "Contraseña actualizada correctamente. "
                    "Ya puedes iniciar sesión con tu nueva contraseña."
                )
                _spacer(0.5)
                # Cerrar la sesión de recovery para forzar login limpio
                try:
                    _sb().auth.sign_out()
                except Exception:
                    pass
                for k in [k for k in st.session_state if k.startswith("auth_")]:
                    del st.session_state[k]
                st.session_state.auth_page = "login"
                _spacer(0.25)
                if st.button("Ir al inicio de sesión", key="auth_back_login"):
                    st.rerun()
            else:
                st.error(err)


# ══════════════════════════════════════════════
#  PÁGINA: INICIO DE SESIÓN
# ══════════════════════════════════════════════

def _render_login():
    # Manejar redirect pendiente a Google
    if "_redirect_to" in st.session_state:
        url = st.session_state.pop("_redirect_to")
        st.markdown(
            f'<script>window.top.location.replace("{url}");</script>',
            unsafe_allow_html=True,
        )
        st.markdown(
            f'Redirigiendo a Google... '
            f'<a href="{url}" target="_self" '
            f'style="color:#e55a2b;font-weight:600;font-family:Sora,sans-serif;">'
            f'Haz clic aquí</a> si no redirige automáticamente.',
            unsafe_allow_html=True,
        )
        st.stop()

    # Manejar callback OAuth: tokens en query params
    params = st.query_params
    if "access_token" in params and params.get("type", "") != "recovery":
        at = params.get("access_token", "")
        rt = params.get("refresh_token", "")
        st.query_params.clear()
        if at and auth_set_session(at, rt):
            st.rerun()
        else:
            st.error("Error al procesar la sesión de Google. Inténtalo de nuevo.")

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
        if st.button("Google", key="auth_google_btn", use_container_width=True):
            url, err = auth_get_google_url()
            if url:
                st.session_state._redirect_to = url
                st.rerun()
            else:
                st.error(f"Error OAuth: {err}")
    with col_gh:
        if st.button("GitHub", key="auth_github_btn", use_container_width=True):
            st.info("GitHub OAuth próximamente disponible.")

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

    full_name = st.text_input(
        "Nombre completo", placeholder="Ana García", key="reg_name"
    )
    email = st.text_input(
        "Correo electrónico", placeholder="tu@email.com", key="reg_email"
    )
    password = st.text_input(
        "Contraseña", placeholder="Mínimo 6 caracteres",
        key="reg_pass", type="password"
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
        if st.button("Google", key="auth_google_btn", use_container_width=True):
            url, err = auth_get_google_url()
            if url:
                st.session_state._redirect_to = url
                st.rerun()
            else:
                st.error(f"Error OAuth: {err}")

    _spacer(0.6)
    col_txt2, col_btn2 = st.columns([5, 3])
    with col_txt2:
        _small_text("¿Ya tienes una cuenta?")
    with col_btn2:
        if st.button("Iniciar sesión", key="auth_to_login"):
            st.session_state.auth_page = "login"
            st.rerun()


# ══════════════════════════════════════════════
#  PÁGINA: RECUPERAR CONTRASEÑA (envío de correo)
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

    email = st.text_input(
        "Correo electrónico", placeholder="tu@email.com", key="forgot_email"
    )

    _spacer(0.4)

    if st.button("Enviar enlace de recuperación", key="auth_reset_btn", use_container_width=True):
        if not email.strip():
            st.error("Ingresa tu correo electrónico.")
        else:
            with st.spinner("Enviando..."):
                ok, err = auth_reset_password(email.strip())
            if ok:
                st.success(
                    "Correo enviado. Revisa tu bandeja de entrada y también la carpeta de spam."
                )
            else:
                # Mostramos el error técnico real para facilitar el diagnóstico
                st.error(
                    f"Error al enviar el correo: {err}\n\n"
                    "Verifica que el correo esté registrado y que la URL de "
                    "redirección esté permitida en Supabase → "
                    "Authentication → URL Configuration → Redirect URLs."
                )

    _spacer(0.75)
    if st.button("Volver al inicio de sesión", key="auth_back_login"):
        st.session_state.auth_page = "login"
        st.rerun()


# ══════════════════════════════════════════════
#  PUNTO DE ENTRADA PRINCIPAL
# ══════════════════════════════════════════════

def render_auth():
    """
    Renderiza la página de autenticación activa.
    Llama a esta función desde app.py cuando el usuario no está autenticado.

    Flujo de recuperación de contraseña:
      1. El usuario hace clic en "Olvidé mi contraseña" e ingresa su correo.
      2. Supabase envía un correo con un enlace que incluye type=recovery en el hash.
      3. El JS de _OAUTH_CALLBACK_JS convierte el hash en query params y recarga.
      4. render_auth() detecta type=recovery + access_token y muestra
         _render_reset_password() con el formulario de nueva contraseña.
      5. auth_update_password() llama a supabase.auth.update_user({"password": ...}).
    """
    st.markdown(_AUTH_CSS,          unsafe_allow_html=True)
    st.markdown(_OAUTH_CALLBACK_JS, unsafe_allow_html=True)

    if "auth_page" not in st.session_state:
        st.session_state.auth_page = "login"

    # ── Detectar flujo de recuperación de contraseña ──
    params   = st.query_params
    url_type = params.get("type", "")
    at       = params.get("access_token", "")
    rt       = params.get("refresh_token", "")

    if url_type == "recovery" and at:
        _render_reset_password(at, rt)
        return

    # ── Rutas normales ──
    dispatch = {
        "login":    _render_login,
        "register": _render_register,
        "forgot":   _render_forgot,
    }
    dispatch.get(st.session_state.auth_page, _render_login)()