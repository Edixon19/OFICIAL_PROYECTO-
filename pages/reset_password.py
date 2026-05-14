"""
GestorPro — Página de restablecimiento de contraseña
=====================================================
Ubicación obligatoria: pages/reset_password.py

Supabase (implicit flow) redirige a esta página con el token en el HASH:
    /reset_password#access_token=xxx&refresh_token=yyy&type=recovery

El hash nunca llega a Python. Este archivo usa un JS mínimo y focalizado
que lo convierte a query params normales (?access_token=...) en una sola
redirección, tras lo cual Python puede leerlo con st.query_params.

Configuración requerida en Supabase Dashboard:
  Authentication → URL Configuration → Redirect URLs:
    https://gestorpro.streamlit.app/reset_password
    https://gestorpro.streamlit.app/**
  Authentication → Email Templates → Reset Password:
    <a href="{{ .ConfirmationURL }}">Reset Password</a>
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

st.set_page_config(
    page_title="Nueva contraseña — GestorPro",
    page_icon="🔐",
    layout="centered",
)


@st.cache_resource
def _sb() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_ANON_KEY)


# ──────────────────────────────────────────────
# CSS
# ──────────────────────────────────────────────
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
    display: none !important; visibility: hidden !important;
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
    color:#fff; font-weight:700; font-size:1.15rem; font-family:'Sora',sans-serif;
    margin-bottom:0.8rem; box-shadow:0 6px 22px rgba(229,90,43,0.30);
}
.auth-app-title { font-size:1.45rem; font-weight:700; color:#0f172a; font-family:'Sora',sans-serif; }
.auth-app-sub   { font-size:0.81rem; color:#475569; font-family:'Sora',sans-serif; margin-top:0.15rem; text-align:center; }
.auth-info-box {
    background:rgba(13,148,136,0.07); border:1px solid rgba(13,148,136,0.22);
    border-radius:10px; padding:0.8rem 1rem; margin-bottom:1.25rem;
    font-size:0.82rem; color:#0f4c45; font-family:'Sora',sans-serif; line-height:1.55;
}
.auth-error-box {
    background:rgba(239,68,68,0.07); border:1px solid rgba(239,68,68,0.25);
    border-radius:10px; padding:0.9rem 1rem; margin-bottom:1rem;
    font-size:0.84rem; color:#7f1d1d; font-family:'Sora',sans-serif; line-height:1.55;
}
.pw-strength-bar  { height:4px; border-radius:2px; margin-top:0.35rem; background:#e2e8f0; overflow:hidden; }
.pw-strength-fill { height:100%; border-radius:2px; }
.pw-strength-label{ font-size:0.71rem; margin-top:0.2rem; font-family:'Sora',sans-serif; }
.stTextInput label {
    color:#1e293b !important; font-size:0.84rem !important;
    font-weight:600 !important; font-family:'Sora',sans-serif !important;
}
.stTextInput > div > div > input {
    background:#f8fafc !important; border:1.5px solid #e2e8f0 !important;
    border-radius:11px !important; color:#0f172a !important;
    font-family:'Sora',sans-serif !important; font-size:0.88rem !important;
    height:46px !important; box-shadow:none !important;
}
.stTextInput > div > div > input:focus {
    border-color:#e55a2b !important;
    box-shadow:0 0 0 3px rgba(229,90,43,0.1) !important;
    background:#ffffff !important;
}
.st-key-update_pw_btn button {
    background:linear-gradient(135deg,#e55a2b 0%,#c94d22 100%) !important;
    color:#fff !important; border:none !important; border-radius:12px !important;
    font-family:'Sora',sans-serif !important; font-weight:600 !important;
    font-size:0.92rem !important; height:48px !important;
    box-shadow:0 4px 16px rgba(229,90,43,0.35) !important; transition:all 0.2s !important;
}
.st-key-update_pw_btn button:hover { transform:translateY(-2px) !important; box-shadow:0 7px 22px rgba(229,90,43,0.45) !important; }
.st-key-go_login button, .st-key-go_login_ok button {
    background:transparent !important; color:#e55a2b !important;
    border:1.5px solid #e55a2b !important; border-radius:10px !important;
    font-family:'Sora',sans-serif !important; font-size:0.84rem !important;
    font-weight:600 !important; box-shadow:none !important; transition:all 0.2s !important;
}
.st-key-go_login button:hover, .st-key-go_login_ok button:hover {
    background:rgba(229,90,43,0.07) !important;
}
div[data-testid="stSuccess"], div[data-testid="stError"], div[data-testid="stInfo"] {
    border-radius:10px !important;
}
div[data-testid="stSuccess"] p, div[data-testid="stError"] p, div[data-testid="stInfo"] p {
    color:inherit !important; font-family:'Sora',sans-serif !important; font-size:0.84rem !important;
}
</style>
""", unsafe_allow_html=True)


# ──────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────

def _logo():
    st.markdown("""
    <div class="auth-logo-wrap">
        <div class="auth-logo-icon">GP</div>
        <div class="auth-app-title">Nueva contraseña</div>
        <div class="auth-app-sub">Elige una contraseña segura para tu cuenta</div>
    </div>
    """, unsafe_allow_html=True)


def _spacer(rem: float = 0.5):
    st.markdown(f"<div style='height:{rem}rem'></div>", unsafe_allow_html=True)


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
    return f"""
    <div class="pw-strength-bar">
        <div class="pw-strength-fill" style="width:{score*25}%;background:{color};"></div>
    </div>
    <div class="pw-strength-label" style="color:{color};">{label}</div>
    """


def _redirect_login():
    st.markdown('<meta http-equiv="refresh" content="0; url=/">', unsafe_allow_html=True)
    st.stop()


def _show_invalid():
    _logo()
    st.markdown("""
    <div class="auth-error-box">
        ⚠️ <strong>Enlace inválido o expirado.</strong><br><br>
        El enlace de recuperación ya fue utilizado o ha caducado.
        Solicita uno nuevo desde el inicio de sesión.
    </div>
    """, unsafe_allow_html=True)
    _spacer(0.5)
    if st.button("Volver al inicio de sesión", key="go_login", use_container_width=True):
        _redirect_login()
    st.stop()


# ══════════════════════════════════════════════
#  LÓGICA PRINCIPAL
# ══════════════════════════════════════════════

_logo()

params = st.query_params

# ─────────────────────────────────────────────────────────────────────────────
# FASE 1 — Convertir hash a query params (solo si aún no tenemos sesión)
#
# Supabase envía:  /reset_password#access_token=xxx&refresh_token=yyy&type=recovery
# El hash (#) nunca llega a Python. El JS de abajo lo lee del navegador y hace
# una única redirección a:  /reset_password?access_token=xxx&...&type=recovery
# En esa segunda carga, st.query_params ya tiene los valores y Python los lee.
# ─────────────────────────────────────────────────────────────────────────────

if not st.session_state.get("_rp_session_ok") and "access_token" not in params and "code" not in params:

    # Si el JS ya corrió y no encontró hash, mostramos error
    if params.get("_rp_no_token") == "1":
        _show_invalid()

    # Primera carga: inyectar JS que lee el hash y redirige con query params
    st.markdown("""
    <div style="text-align:center;padding:2.5rem 0;font-family:'Sora',sans-serif;
                color:#475569;font-size:0.9rem;">
        🔐 Verificando enlace de recuperación…
    </div>

    <script>
    (function () {
        var hash = window.location.hash;          // "#access_token=...&type=recovery"

        if (!hash || hash.indexOf('access_token') === -1) {
            // Sin token en el hash → marcar error y recargar
            var path = window.location.pathname;
            window.location.replace(path + '?_rp_no_token=1');
            return;
        }

        // Quitar el '#' inicial y usar el resto como query string
        var qs   = hash.substring(1);
        var path = window.location.pathname;
        window.location.replace(path + '?' + qs);
    })();
    </script>
    """, unsafe_allow_html=True)

    st.stop()   # Detener Python; el JS hará la redirección


# ─────────────────────────────────────────────────────────────────────────────
# FASE 2 — Establecer sesión con los tokens recibidos (query params o hash)
# ─────────────────────────────────────────────────────────────────────────────

if not st.session_state.get("_rp_session_ok"):

    # ─── NUEVO: Caso con ?token= (recuperación estándar de Supabase) ───
    if "token" in params and params.get("type") == "recovery":
        token = params["token"]
        try:
            # Verificar el token OTP manualmente
            result = _sb().auth.verify_otp({
                "token": token,
                "type": "recovery",
                "email": ""  # Supabase deduce el email del token
            })
            if result and result.user:
                st.session_state["_rp_session_ok"] = True
                st.session_state["_rp_user_email"] = result.user.email
                st.query_params.clear()
            else:
                _show_invalid()
        except Exception as e:
            st.error(f"Error al verificar token: {str(e)[:100]}")
            _show_invalid()

    # Caso A: PKCE flow → ?code= (menos común para recovery)
    elif "code" in params:
        try:
            result = _sb().auth.exchange_code_for_session({"auth_code": params["code"]})
            if result and result.user:
                st.session_state["_rp_session_ok"] = True
                st.session_state["_rp_user_email"] = result.user.email
                st.query_params.clear()
            else:
                _show_invalid()
        except Exception:
            _show_invalid()

    # Caso B: Implicit flow → ?access_token= (desde hash convertido por JS)
    elif "access_token" in params and params.get("type") == "recovery":
        at = params.get("access_token", "")
        rt = params.get("refresh_token", "")
        try:
            result = _sb().auth.set_session(at, rt)
            if result and result.user:
                st.session_state["_rp_session_ok"] = True
                st.session_state["_rp_user_email"] = result.user.email
                st.query_params.clear()
            else:
                _show_invalid()
        except Exception:
            _show_invalid()

    else:
        _show_invalid()


# ─────────────────────────────────────────────────────────────────────────────
# FASE 3 — Formulario de nueva contraseña
# Solo llegamos aquí si la sesión fue establecida correctamente
# ─────────────────────────────────────────────────────────────────────────────

if not st.session_state.get("_rp_session_ok"):
    _show_invalid()

st.markdown("""
<div class="auth-info-box">
    Ingresa tu nueva contraseña. Debe tener al menos 6 caracteres.
</div>
""", unsafe_allow_html=True)

user_email = st.session_state.get("_rp_user_email", "")
if user_email:
    st.markdown(
        f'<p style="font-size:0.8rem;color:#475569;font-family:Sora,sans-serif;'
        f'margin-bottom:1rem;">Cuenta: <strong>{user_email}</strong></p>',
        unsafe_allow_html=True,
    )

new_pw = st.text_input(
    "Nueva contraseña", type="password",
    placeholder="Mínimo 6 caracteres", key="rp_pw1",
)
if new_pw:
    st.markdown(_pw_strength(new_pw), unsafe_allow_html=True)

_spacer(0.15)

conf_pw = st.text_input(
    "Confirmar contraseña", type="password",
    placeholder="Repite la contraseña", key="rp_pw2",
)

_spacer(0.5)

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
            st.session_state.pop("_rp_session_ok", None)
            st.session_state.pop("_rp_user_email", None)

            # Cerrar sesión de recovery para que no interfiera con el login
            try:
                _sb().auth.sign_out()
            except Exception:
                pass

            st.success(
                "✅ Contraseña actualizada correctamente. "
                "Ya puedes iniciar sesión con tu nueva contraseña."
            )
            _spacer(0.5)
            if st.button("Ir al inicio de sesión", key="go_login_ok", use_container_width=True):
                _redirect_login()

        except Exception as e:
            err = str(e).lower()
            if "same password" in err:
                st.error("La nueva contraseña no puede ser igual a la anterior.")
            elif "weak" in err or "short" in err:
                st.error("La contraseña es muy débil. Intenta con al menos 8 caracteres.")
            else:
                st.error("No se pudo actualizar la contraseña. Inténtalo de nuevo.")