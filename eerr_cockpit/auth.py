"""Authentication module for EERR Cockpit."""
from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path
from typing import Optional

import streamlit as st

DATA_DIR = Path(__file__).parent.parent / "data"
USERS_FILE = DATA_DIR / "users.json"

# ── Brand palette (mirrored from app.py for the login page) ─────────
_CN  = "#0F1F4A"
_CB  = "#1E3A8A"
_CM  = "#3B6CB7"
_CBG = "#EEF2FA"
_CMU = "#64748B"
_CBRD = "#D1DDEF"


def _hash(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def _users() -> dict:
    if not USERS_FILE.exists():
        return {}
    return json.loads(USERS_FILE.read_text(encoding="utf-8"))


def authenticate(username: str, password: str) -> bool:
    u = _users()
    if username not in u:
        return False
    return u[username]["password_hash"] == _hash(password)


def display_name(username: str) -> str:
    return _users().get(username, {}).get("display_name", username)


def is_authenticated() -> bool:
    return bool(st.session_state.get("authenticated"))


def current_user() -> str:
    return st.session_state.get("username", "")


def logout() -> None:
    st.session_state.pop("authenticated", None)
    st.session_state.pop("username", None)
    st.rerun()


def _logo_b64() -> Optional[str]:
    # Preferir el logo azul para fondo blanco del login
    for name in ("LOGO azul.png", "logo.png"):
        p = Path(__file__).parent.parent / "assets" / name
        if p.exists():
            return base64.b64encode(p.read_bytes()).decode()
    return None


def render_login() -> None:
    """Render a centered login form. Calls st.stop() when not authenticated."""
    b64 = _logo_b64()
    logo_html = (
        f'<img src="data:image/png;base64,{b64}" style="height:110px;width:auto" />'
        if b64 else
        '<div style="font-size:20px;font-weight:900;color:#0F1F4A;letter-spacing:3px">ASCENT</div>'
    )

    st.markdown(f"""
    <style>
    html, body, [data-testid="stAppViewContainer"] {{
        background: {_CBG};
        font-family: 'Inter', system-ui, sans-serif;
    }}
    .block-container {{ padding: 2rem !important; max-width: 100% !important; }}
    #MainMenu, footer, [data-testid="stToolbar"],
    [data-testid="stDecoration"], [data-testid="stHeader"],
    [data-testid="stAppDeployButton"], .stAppHeader,
    [data-testid="stSidebar"] {{ display: none !important; }}
    .login-card {{
        background: white;
        border: 1px solid {_CBRD};
        border-radius: 20px;
        padding: 40px 36px 36px;
        box-shadow: 0 8px 40px rgba(15,31,74,.10);
        max-width: 400px;
        margin: 60px auto 0;
    }}
    .login-brand {{ text-align: center; margin-bottom: 28px; }}
    .login-title {{
        font-size: 20px; font-weight: 800; color: {_CN};
        margin: 10px 0 4px; letter-spacing: -.3px;
    }}
    .login-sub {{
        font-size: 12px; color: {_CMU}; margin: 0;
    }}
    </style>
    """, unsafe_allow_html=True)

    _, col, _ = st.columns([1, 1.6, 1])
    with col:
        st.markdown(f"""
        <div class="login-card">
          <div class="login-brand">
            {logo_html}
            <div class="login-title">EERR Cockpit</div>
            <p class="login-sub">Ascent Advisors · Análisis Ejecutivo</p>
          </div>
        </div>
        """, unsafe_allow_html=True)

        with st.form("login_form", clear_on_submit=False):
            username = st.text_input("Usuario", placeholder="usuario")
            password = st.text_input("Contraseña", type="password", placeholder="••••••••")
            submitted = st.form_submit_button("Ingresar", use_container_width=True)

        if submitted:
            if authenticate(username.strip(), password):
                st.session_state["authenticated"] = True
                st.session_state["username"] = username.strip()
                st.rerun()
            else:
                st.error("Usuario o contraseña incorrectos.")

    st.stop()
