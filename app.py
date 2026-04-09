"""
Ascent EERR Cockpit — Demo
streamlit run app.py
"""
from __future__ import annotations
import base64
import datetime as _dt
import os
from pathlib import Path
from typing import Optional

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from eerr_cockpit import auth, storage
from eerr_cockpit.agent import build_context, stream_response
from eerr_cockpit.config import KPI_DEFINITIONS, MONTH_LABELS_ES, QUARTER_LABELS_ES
from eerr_cockpit.guantex_parser import GuantexParser, is_guantex_format
from eerr_cockpit.hierarchy import detect_hierarchy, get_period_columns
from eerr_cockpit.kpis import calc_delta, fmt_currency, fmt_percent, get_kpis, get_top_variations
from eerr_cockpit.parser import EERRParser
from eerr_cockpit.pdf_export import create_pdf_report

# ── Brand palette ────────────────────────────────────────────────
CN   = "#0F1F4A"   # navy
CB   = "#1E3A8A"   # blue
CM   = "#3B6CB7"   # mid blue
CL   = "#5B8DD9"   # light blue
CP   = "#C5D5EE"   # pale blue
CBG  = "#EEF2FA"   # page bg
CG   = "#15803D"   # green
CGS  = "#DCFCE7"   # green soft
CR   = "#B91C1C"   # red
CRS  = "#FEE2E2"   # red soft
CMU  = "#64748B"   # muted
CBRD = "#D1DDEF"   # border

# ── Mes labels (en español, usados en sidebar y upload tab) ──────
_MONTHS_ES = [
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
]

# ── Page config ───────────────────────────────────────────────────
st.set_page_config(
    page_title="Ascent EERR Cockpit",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS ──────────────────────────────────────────────────────────
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');

/* ── Reset & base ── */
html, body, [data-testid="stAppViewContainer"] {{
    background: {CBG};
    font-family: 'Inter', system-ui, sans-serif;
    color: {CN};
}}
.block-container {{ padding: 0 2rem 2rem !important; max-width: 100% !important; }}
[data-testid="stAppViewContainer"] > section.main > div.block-container {{ padding-top: 0 !important; }}
/* Remove Streamlit's default top gap */
[data-testid="stAppViewMain"] {{ padding-top: 0 !important; }}

/* ── Hide Streamlit chrome ── */
#MainMenu, footer, [data-testid="stToolbar"],
[data-testid="stDecoration"],
[data-testid="stHeader"],
[data-testid="stAppDeployButton"],
.stAppHeader {{ display: none !important; height: 0 !important; }}

/* ── Sidebar ── */
[data-testid="stSidebar"] {{
    background: linear-gradient(180deg, {CN} 0%, {CB} 60%, #1a3366 100%);
    border-right: none;
    box-shadow: 4px 0 24px rgba(15,31,74,.18);
    min-width: 264px !important;
    max-width: 264px !important;
}}
[data-testid="stSidebar"] > div:first-child {{
    padding: 0 !important;
    overflow-x: hidden;
}}
/* All Streamlit widgets inside sidebar get horizontal padding */
[data-testid="stSidebar"] .stRadio,
[data-testid="stSidebar"] .stSelectbox,
[data-testid="stSidebar"] .stSlider,
[data-testid="stSidebar"] hr {{
    padding-left: 20px !important;
    padding-right: 20px !important;
}}
/* Sidebar — fixed, no collapse, no header strip */
[data-testid="stSidebarCollapseButton"],
[data-testid="collapsedControl"],
[data-testid="stSidebarHeader"],
[data-testid="stLogoSpacer"] {{
    display: none !important;
}}
/* Sidebar widget labels → white */
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] .stRadio label,
[data-testid="stSidebar"] .stSelectbox label,
[data-testid="stSidebar"] .stSlider label,
[data-testid="stSidebar"] p {{
    color: rgba(255,255,255,.85) !important;
    font-size: 13px !important;
}}
/* Radio option text */
[data-testid="stSidebar"] .stRadio > div label {{
    color: rgba(255,255,255,.9) !important;
    font-weight: 500 !important;
    font-size: 13px !important;
}}
/* Selectbox styling */
[data-testid="stSidebar"] .stSelectbox > div > div {{
    background: rgba(255,255,255,.1) !important;
    border: 1px solid rgba(255,255,255,.2) !important;
    border-radius: 8px !important;
    color: white !important;
}}
[data-testid="stSidebar"] .stSelectbox > div > div > div {{
    color: white !important;
}}
/* Slider track */
[data-testid="stSidebar"] [data-testid="stSlider"] > div > div > div > div {{
    background: rgba(255,255,255,.3) !important;
}}
[data-testid="stSidebar"] [data-testid="stSlider"] > div > div > div > div:nth-child(2) {{
    background: {CL} !important;
}}
/* Sidebar hr */
[data-testid="stSidebar"] hr {{
    border-color: rgba(255,255,255,.15) !important;
}}
/* Sidebar buttons (ej: Cerrar sesión) */
[data-testid="stSidebar"] .stButton button {{
    background: rgba(255,255,255,.15) !important;
    color: white !important;
    border: 1px solid rgba(255,255,255,.3) !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    font-size: 13px !important;
    transition: background .15s;
}}
[data-testid="stSidebar"] .stButton button:hover {{
    background: rgba(255,255,255,.25) !important;
    border-color: rgba(255,255,255,.5) !important;
}}

/* Section labels inside sidebar */
.sb-section {{
    font-size: 9px; font-weight: 800; letter-spacing: 1.5px;
    text-transform: uppercase; color: rgba(255,255,255,.4);
    margin: 18px 0 10px; padding: 0 20px;
}}
.sb-logo-wrap {{
    padding: 22px 20px 18px;
    border-bottom: 1px solid rgba(255,255,255,.12);
    margin-bottom: 8px;
    display: flex; align-items: center; gap: 12px;
}}
.sb-logo-title {{
    font-size: 13px; font-weight: 800; color: white; letter-spacing: .2px; line-height: 1.2;
}}
.sb-logo-sub {{
    font-size: 9.5px; color: rgba(255,255,255,.45); letter-spacing: 3px; margin-top: 1px;
}}
.sb-widget {{ padding: 0 16px; }}

/* ── Header ── */
.app-header {{
    background: linear-gradient(135deg, {CN} 0%, {CB} 55%, {CM} 100%);
    border-radius: 18px;
    padding: 0 28px;
    height: 72px;
    display: flex;
    align-items: center;
    gap: 20px;
    box-shadow: 0 8px 32px rgba(15,31,74,.22);
    margin-bottom: 0;
}}
.app-header-logo {{ display: flex; align-items: center; }}
.app-header-divider {{
    width: 1px; height: 36px;
    background: rgba(255,255,255,.2);
    margin: 0 4px;
}}
.app-header-text {{
    display: flex; flex-direction: column;
    justify-content: center; gap: 0;
    transform: translateY(-3px);
}}
.app-header-text h1 {{
    color: white; font-size: 18px; font-weight: 800;
    margin: 0 0 1px; letter-spacing: -.3px; line-height: 1;
}}
.app-header-text p {{
    color: rgba(255,255,255,.55);
    font-size: 11px; margin: 0; line-height: 1;
}}
.header-right {{ margin-left: auto; display: flex; align-items: center; gap: 10px; }}
/* ── Header nominal/real toggle ── */
.hdr-toggle-wrap {{
    display: flex; align-items: center; gap: 8px;
    color: rgba(255,255,255,.9);
    font-size: 11.5px; font-weight: 600;
    letter-spacing: .1px;
    cursor: pointer;
    user-select: none;
}}
.hdr-toggle-wrap input[type=checkbox] {{ display: none; }}
.hdr-toggle-track {{
    position: relative;
    width: 38px; height: 22px;
    background: rgba(255,255,255,.22);
    border: 1px solid rgba(255,255,255,.35);
    border-radius: 11px;
    transition: background .2s, border-color .2s;
    flex-shrink: 0;
}}
.hdr-toggle-track::before {{
    content: '';
    position: absolute;
    width: 16px; height: 16px;
    left: 2px; top: 2px;
    background: white;
    border-radius: 50%;
    box-shadow: 0 1px 4px rgba(0,0,0,.25);
    transition: transform .2s;
}}
.hdr-toggle-wrap input:checked ~ .hdr-toggle-track {{
    background: #22c55e;
    border-color: #22c55e;
}}
.hdr-toggle-wrap input:checked ~ .hdr-toggle-track::before {{
    transform: translateX(16px);
}}
.hdr-toggle-lbl-on  {{ color: rgba(255,255,255,.4); }}
.hdr-toggle-wrap input:checked ~ .hdr-toggle-lbl-off {{ color: rgba(255,255,255,.4); }}
.hdr-toggle-wrap input:checked ~ .hdr-toggle-lbl-on  {{ color: rgba(255,255,255,.95); }}


/* ── Tabs ── */
[data-testid="stTabs"] [role="tablist"] {{
    border-bottom: 2px solid {CBRD};
    gap: 2px;
    background: transparent;
}}
[data-testid="stTabs"] button[role="tab"] {{
    color: {CMU} !important;
    font-weight: 600 !important;
    font-size: 13px !important;
    padding: 9px 20px !important;
    border-radius: 8px 8px 0 0 !important;
    border: none !important;
    background: transparent !important;
    transition: color .15s;
}}
[data-testid="stTabs"] button[role="tab"][aria-selected="true"] {{
    color: {CN} !important;
    background: white !important;
    border-bottom: 3px solid {CM} !important;
}}

/* ── KPI cards ── */
.kpi-wrap {{ height: 116px; }}
.kpi-card {{
    background: white;
    border: 1px solid {CBRD};
    border-radius: 14px;
    padding: 16px 16px 12px;
    box-shadow: 0 2px 12px rgba(15,31,74,.06);
    position: relative;
    overflow: hidden;
    height: 116px;
    box-sizing: border-box;
}}
.kpi-card::before {{
    content: '';
    position: absolute; top: 0; left: 0; right: 0; height: 3px;
    background: linear-gradient(90deg, {CM}, {CL});
}}
.kpi-lbl {{
    font-size: 10px; font-weight: 700; color: {CMU};
    text-transform: uppercase; letter-spacing: .7px; margin-bottom: 6px;
}}
.kpi-val {{
    font-size: 22px; font-weight: 900; color: {CN};
    line-height: 1; margin-bottom: 8px; letter-spacing: -1px;
}}
.kpi-badge {{
    display: inline-flex; align-items: center; gap: 3px;
    font-size: 11px; font-weight: 700;
    padding: 3px 8px; border-radius: 20px;
}}
.kpi-badge.pos {{ color: {CG}; background: {CGS}; }}
.kpi-badge.neg {{ color: {CR}; background: {CRS}; }}
.kpi-badge.neu {{ color: {CMU}; background: #F1F5F9; }}

/* ── AI Insight card ── */
.ai-insight-card {{
    background: linear-gradient(135deg, #F0F4FF 0%, #EEF2FA 100%);
    border: 1px solid {CP};
    border-left: 4px solid {CM};
    border-radius: 14px;
    padding: 18px 22px;
    position: relative;
    margin-top: 2px;
}}
.ai-badge {{
    display: inline-flex; align-items: center; gap: 5px;
    background: linear-gradient(90deg, {CB}, {CM});
    color: white; font-size: 9.5px; font-weight: 800;
    letter-spacing: 1px; text-transform: uppercase;
    padding: 3px 9px; border-radius: 20px;
    margin-bottom: 10px;
}}
.ai-insight-text {{
    font-size: 14px; line-height: 1.75; color: #1E293B;
    font-style: italic; margin: 0;
}}
.ai-insight-text b {{ font-style: normal; color: {CN}; }}

/* ── Section header ── */
.sec-hdr {{
    font-size: 13px; font-weight: 700; color: {CN};
    margin: 0 0 12px; padding-bottom: 10px;
    border-bottom: 1px solid {CBRD};
}}

/* ── Alert rows ── */
.alert-row {{
    display: flex; align-items: center; justify-content: space-between;
    padding: 9px 14px; border-radius: 10px; margin-bottom: 6px; border: 1px solid;
}}
.alert-row.pos {{ background: #F0FDF4; border-color: #86EFAC; }}
.alert-row.neg {{ background: #FFF1F2; border-color: #FECACA; }}
.alert-name  {{ font-size: 13px; font-weight: 600; color: {CN}; }}
.alert-tag   {{ font-size: 10px; color: {CMU}; background: #F1F5F9;
               padding: 2px 7px; border-radius: 10px; margin-left: 6px; }}
.alert-delta {{ font-size: 13px; font-weight: 700; }}
.alert-delta.pos {{ color: {CG}; }}
.alert-delta.neg {{ color: {CR}; }}

/* ── EERR table ── */
table.eerr {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
table.eerr thead tr {{ background: {CN}; color: white; }}
table.eerr thead th {{
    padding: 10px 12px; font-weight: 600; font-size: 11px;
    text-transform: uppercase; letter-spacing: .5px; white-space: nowrap;
}}
table.eerr tbody tr:hover {{ background: #EEF3FB !important; }}
table.eerr tbody tr.sub {{ background: #EEF2FF !important; font-weight: 700; }}
table.eerr tbody tr.sub td {{ color: {CN}; }}
table.eerr tbody td {{ padding: 7px 12px; border-bottom: 1px solid #F1F5F9; color: #334155; }}
table.eerr tbody td.num {{ text-align: right; font-variant-numeric: tabular-nums; }}
.tag-pill {{
    background: {CP}; color: {CB};
    font-size: 10px; font-weight: 700;
    padding: 2px 6px; border-radius: 8px; margin-left: 5px;
}}
.pos-txt {{ color: {CG}; font-weight: 700; }}
.neg-txt {{ color: {CR}; font-weight: 700; }}
</style>
""", unsafe_allow_html=True)


# ── Helpers ──────────────────────────────────────────────────────
def _logo_b64() -> Optional[str]:
    p = Path(__file__).parent / "assets" / "logo.png"
    return base64.b64encode(p.read_bytes()).decode() if p.exists() else None

def _pl(col: str) -> str:
    if col.startswith("month_"):   return MONTH_LABELS_ES[int(col.split("_")[1]) - 1]
    if col.startswith("quarter_"): return QUARTER_LABELS_ES[int(col.split("_")[1]) - 1]
    if col.startswith("year_"):    return "Año"
    if col == "__ytd__":           return "YTD"
    return col

def _sorted_p(cols: list) -> list:
    return (sorted(c for c in cols if c.startswith("month_")) +
            sorted(c for c in cols if c.startswith("quarter_")) +
            [c for c in cols if c.startswith("year_")])

def _ytd(df: pd.DataFrame, m: int) -> pd.Series:
    avail = [f"month_{i:02d}" for i in range(1, m + 1) if f"month_{i:02d}" in df.columns]
    return df[avail].fillna(0).sum(axis=1) if avail else pd.Series([0.] * len(df))


# ── Load & prepare data ───────────────────────────────────────────
def _process_raw(raw: dict) -> dict:
    """Normalise column names and detect hierarchy for a raw data dict."""
    from eerr_cockpit.config import PERIOD_MAP
    out: dict = {}
    for cur, yrs in raw.items():
        out[cur] = {}
        for yr, df in yrs.items():
            if df is None:
                continue
            col_map = {}
            for col in df.columns:
                cl = col.lower().strip()
                if cl in PERIOD_MAP:
                    pt, pn = PERIOD_MAP[cl]
                    col_map[col] = f"{pt}_{pn:02d}"
                elif cl in ["1 trim", "2 trim", "3 trim", "4 trim"]:
                    col_map[col] = f"quarter_{int(cl[0]):02d}"
                elif cl in ["año", "year", "total"]:
                    col_map[col] = "year_00"
            df2 = df.rename(columns=col_map)
            pc = get_period_columns(df2)
            if "is_subtotal" not in df2.columns:
                df2 = detect_hierarchy(df2, pc)
            df2[pc] = df2[pc].fillna(0)
            out[cur][yr] = df2
    return out


# ── Consolidación de sociedades ───────────────────────────────────────
def _consolidate(df: pd.DataFrame) -> pd.DataFrame:
    """Suma columnas numéricas de todas las sociedades agrupando por (code, name).
    Preserva el orden de filas de la primera sociedad encontrada."""
    num_cols = [c for c in df.columns if c.startswith(("month_", "quarter_", "year_"))]
    meta = ["tag", "is_subtotal", "level"]
    agg: dict = {c: "sum" for c in num_cols}
    for m in meta:
        if m in df.columns:
            agg[m] = "first"
    agg["code"] = "first"
    agg["name"] = "first"

    df = df.copy()
    df["_gk"] = (
        df["code"].apply(lambda x: str(int(x)) if pd.notna(x) and x != "" else "")
        + "|"
        + df["name"].fillna("")
    )
    result = df.groupby("_gk", as_index=False, sort=False).agg(agg)
    return result.drop(columns=["_gk"])


def _filter_sociedad(df: pd.DataFrame, sociedad: str) -> pd.DataFrame:
    """Filtra o consolida el DataFrame según la sociedad seleccionada."""
    if df is None or "_sociedad" not in df.columns:
        return df
    if sociedad == "Consolidado":
        return _consolidate(df)
    return df[df["_sociedad"] == sociedad].copy()


@st.cache_data(show_spinner=False)
def _load(username: str, year: int, month: int) -> Optional[dict]:
    """Load the EERR data for a specific uploaded period."""
    raw = storage.load_upload(username, year, month)
    if raw is None:
        return None
    return _process_raw(raw)


# ── Plotly base theme ─────────────────────────────────────────────
_PB = dict(
    plot_bgcolor="white", paper_bgcolor="white",
    font=dict(family="Inter, system-ui, sans-serif", color=CN),
    margin=dict(l=4, r=4, t=40, b=4),
    hoverlabel=dict(bgcolor="white", font_size=12, font_family="Inter", bordercolor=CBRD),
    legend=dict(orientation="h", x=1, xanchor="right", y=1.14,
                font_size=12, bgcolor="rgba(0,0,0,0)"),
)


# ── Header ───────────────────────────────────────────────────────
def _header(period: str, currency: str) -> None:
    b64 = _logo_b64()
    # Logo nuevo: fondo transparente, diseñado para bg oscuro — sin filtros
    logo_html = (
        f'<img src="data:image/png;base64,{b64}" '
        f'style="height:46px;width:auto;" />'
        if b64 else
        '<div style="line-height:1.1">'
        '<div style="font-size:15px;font-weight:900;color:white;letter-spacing:3px">ASCENT</div>'
        '<div style="font-size:8.5px;color:rgba(255,255,255,.55);letter-spacing:5px;margin-top:1px">ADVISORS</div>'
        '</div>'
    )
    st.markdown(f"""
    <div class="app-header">
        <div class="app-header-logo">{logo_html}</div>
        <div class="app-header-divider"></div>
        <div class="app-header-text">
            <h1>EERR Cockpit</h1>
            <p>Estado de Resultados · Análisis Ejecutivo</p>
        </div>
        <div class="header-right">
            <label class="hdr-toggle-wrap">
                <input type="checkbox" id="hdr-toggle-chk">
                <span class="hdr-toggle-lbl-off">Nominal</span>
                <span class="hdr-toggle-track"></span>
                <span class="hdr-toggle-lbl-on">Real</span>
            </label>
        </div>
    </div>""", unsafe_allow_html=True)


# ── Sidebar ────────────────────────────────────────────────────────
def _sidebar(data: dict, uploads: list) -> tuple:
    """Renders navigation sidebar.
    Returns (currency, sel_key, sel_label, top_n, alert_mode, sociedad).
    sociedad is None when data has no _sociedad column.
    """
    with st.sidebar:
        # ── Logo / branding ───────────────────────────────────────
        b64 = _logo_b64()
        if b64:
            # Logo presente: mostrarlo centrado y grande
            st.markdown(
                f'<div class="sb-logo-wrap" style="justify-content:center;flex-direction:column;'
                f'align-items:center;padding:28px 20px 20px;">'
                f'  <img src="data:image/png;base64,{b64}" '
                f'       style="width:160px;height:auto;margin-bottom:10px;" />'
                f'  <div style="font-size:10px;font-weight:700;color:rgba(255,255,255,.35);'
                f'       letter-spacing:2px;text-transform:uppercase">EERR Cockpit</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f'<div class="sb-logo-wrap">'
                f'  <div class="sb-logo-title">ASCENT<br>'
                f'  <span class="sb-logo-sub">ADVISORS</span></div>'
                f'  <div style="margin-left:8px">'
                f'    <div class="sb-logo-title">EERR Cockpit</div>'
                f'    <div class="sb-logo-sub">DASHBOARD</div>'
                f'  </div>'
                f'</div>',
                unsafe_allow_html=True,
            )

        # ── ARCHIVO EERR ──────────────────────────────────────────
        st.markdown('<div class="sb-section">Archivo EERR</div>', unsafe_allow_html=True)
        _ul = {
            f"{_MONTHS_ES[u['month']-1]} {u['year']}": u
            for u in reversed(uploads)
        }
        st.selectbox("Período cargado", list(_ul.keys()), key="sb_upload")

        # ── CONFIGURACIÓN ─────────────────────────────────────────
        st.markdown('<div class="sb-section">Configuración</div>', unsafe_allow_html=True)

        currency = st.radio(
            "Moneda", list(data.keys()), horizontal=True, key="sb_currency",
        )

        # Period options: use the most recent year available for this currency
        _yr_latest = max(data[currency].keys()) if data[currency] else "2025"
        df25_c = data[currency].get(_yr_latest)
        pcols  = _sorted_p(get_period_columns(df25_c)) if df25_c is not None else []

        # Solo mostrar períodos que tienen datos reales (suma absoluta > 0)
        def _has_data(col: str, df) -> bool:
            if df is None or col not in df.columns:
                return False
            return float(df[col].abs().sum()) > 0

        popts: dict[str, str] = {}
        for p in pcols:
            if _has_data(p, df25_c):
                popts[p] = _pl(p)
        for mc in [p for p in pcols if p.startswith("month_") and _has_data(p, df25_c)]:
            n = int(mc.split("_")[1])
            popts[f"ytd_{n:02d}"] = f"YTD {MONTH_LABELS_ES[n-1]}"

        sel_label = st.selectbox("Período", list(popts.values()), key="sb_period")
        sel_key   = next((k for k, v in popts.items() if v == sel_label), None)

        st.markdown('<div style="height:4px"></div>', unsafe_allow_html=True)

        # ── SOCIEDAD (solo cuando los datos tienen columna _sociedad) ─────
        _yr_latest2 = max(data[currency].keys()) if data[currency] else None
        _df_check   = data[currency].get(_yr_latest2) if _yr_latest2 else None
        _has_soc    = _df_check is not None and "_sociedad" in _df_check.columns
        if _has_soc:
            _socs = sorted(_df_check["_sociedad"].dropna().unique().tolist())
            st.markdown('<div class="sb-section">Sociedad</div>', unsafe_allow_html=True)
            sociedad = st.radio(
                "Vista", ["Consolidado"] + _socs, key="sb_sociedad",
            )
        else:
            sociedad = None

        # ── ALERTAS ───────────────────────────────────────────────
        st.markdown('<div class="sb-section">Alertas</div>', unsafe_allow_html=True)

        top_n      = st.slider("Top variaciones", 3, 12, 5, key="sb_topn")
        alert_mode = st.radio(
            "Tipo", ["Todos", "Positivos", "Negativos"], key="sb_mode",
        )

        # ── USUARIO ───────────────────────────────────────────────
        st.markdown('<div style="height:6px"></div>', unsafe_allow_html=True)
        st.divider()
        username = auth.current_user()
        dname    = auth.display_name(username)
        st.markdown(
            f'<div style="padding:0 4px 10px;font-size:11px;color:rgba(255,255,255,.65);">'
            f'👤 &nbsp;<b>{dname}</b></div>',
            unsafe_allow_html=True,
        )
        if st.button("Cerrar sesión", use_container_width=True, key="sb_logout"):
            auth.logout()

        st.markdown(
            f'<div style="padding:6px 4px 0;font-size:10px;color:rgba(255,255,255,.3);'
            f'line-height:1.6">Ascent Advisors · EERR Cockpit</div>',
            unsafe_allow_html=True,
        )

    return currency, sel_key, sel_label, top_n, alert_mode, sociedad


# ── KPI cards ────────────────────────────────────────────────────
def _kpi_cards(kpis: list, currency: str) -> None:
    found = [k for k in kpis if k["found"]]
    if not found:
        st.warning("KPIs no encontrados. Verificá los nombres del EERR.")
        return
    cols = st.columns(len(found), gap="small")
    for i, k in enumerate(found):
        with cols[i]:
            v = fmt_percent(k["value_2025"]) if k["is_margin"] else fmt_currency(k["value_2025"], currency, compact=True)
            if k["delta_pct"] not in (None, float("inf")):
                pct = k["delta_pct"]
                arrow, cls = ("↑", "pos") if pct >= 0 else ("↓", "neg")
                badge = f'<span class="kpi-badge {cls}">{arrow} {abs(pct):.1f}%</span>'
            else:
                badge = '<span class="kpi-badge neu">–</span>'
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-lbl">{k["icon"]} &nbsp;{k["label"]}</div>
                <div class="kpi-val">{v}</div>
                {badge}
            </div>""", unsafe_allow_html=True)
    st.markdown("<div style='margin-bottom:18px'></div>", unsafe_allow_html=True)


# ── Comparativo chart ─────────────────────────────────────────────
def _chart_comparativo(kpis: list, currency: str,
                       yr_cur: str = "2025", yr_prev: str = "2024") -> None:
    nm = [k for k in kpis if k["found"] and not k["is_margin"] and k["value_2024"] is not None]
    if not nm:
        return
    labels = [k["label"] for k in nm]
    v25    = [k["value_2025"] for k in nm]
    v24    = [k["value_2024"] for k in nm]
    c25    = [CL if v25[i] >= v24[i] else "#F87171" for i in range(len(v25))]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name=yr_prev, x=labels, y=v24,
        marker=dict(color=CP, line=dict(width=0), cornerradius=6),
        width=0.34, offset=-0.18,
        hovertemplate=f"<b>{yr_prev}</b>  %{{x}}<br>%{{customdata}}<extra></extra>",
        customdata=[fmt_currency(v, currency, compact=True) for v in v24],
    ))
    fig.add_trace(go.Bar(
        name=yr_cur, x=labels, y=v25,
        marker=dict(color=c25, line=dict(width=0), cornerradius=6),
        width=0.34, offset=0.18,
        text=[fmt_currency(v, currency, compact=True) for v in v25],
        textposition="outside",
        textfont=dict(size=10, color=CN, family="Inter"),
        hovertemplate=f"<b>{yr_cur}</b>  %{{x}}<br>%{{customdata}}<extra></extra>",
        customdata=[fmt_currency(v, currency, compact=True) for v in v25],
    ))
    fig.update_layout(
        **_PB, barmode="overlay", height=280,
        title=dict(text=f"<b>KPIs {yr_cur} vs {yr_prev}</b>",
                   font=dict(size=13, color=CN), x=0, xanchor="left"),
        xaxis=dict(showgrid=False, tickfont=dict(size=12), showline=False, zeroline=False),
        yaxis=dict(showgrid=True, gridcolor="rgba(0,0,0,0.04)",
                   showticklabels=False, showline=False,
                   zeroline=True, zerolinecolor=CBRD, zerolinewidth=1),
        bargap=0.28,
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


# ── Waterfall bridge ──────────────────────────────────────────────
def _chart_waterfall(kpis: list, currency: str, yr_prev: str = "2024") -> None:
    items = [(k["label"], k["delta_abs"]) for k in kpis
             if k["found"] and not k["is_margin"] and k["delta_abs"] is not None]
    if not items:
        return
    labels, deltas = zip(*items)
    fig = go.Figure(go.Waterfall(
        orientation="v", x=list(labels), y=list(deltas),
        connector=dict(line=dict(color=CBRD, width=1.5, dash="dot")),
        increasing=dict(marker=dict(color=CL, line=dict(width=0))),
        decreasing=dict(marker=dict(color="#F87171", line=dict(width=0))),
        text=[fmt_currency(d, currency, compact=True) for d in deltas],
        textfont=dict(size=10, color=CN, family="Inter"),
        textposition="outside",
        hovertemplate="<b>%{x}</b><br>%{customdata}<extra></extra>",
        customdata=[fmt_currency(d, currency, compact=True) for d in deltas],
    ))
    fig.update_layout(
        **_PB, height=280, showlegend=False,
        title=dict(text=f"<b>Bridge vs {yr_prev}</b>",
                   font=dict(size=13, color=CN), x=0, xanchor="left"),
        xaxis=dict(showgrid=False, tickfont=dict(size=11), showline=False),
        yaxis=dict(showgrid=True, gridcolor="rgba(0,0,0,0.04)",
                   showticklabels=False, zeroline=True,
                   zerolinecolor=CBRD, showline=False),
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


# ── Alerts ───────────────────────────────────────────────────────
def _alerts(df25, df24, col, currency, n, mode) -> None:
    mm  = {"Todos": "all", "Positivos": "positive", "Negativos": "negative"}
    top = get_top_variations(df25, df24, col, n, mm.get(mode, "all"))
    if top.empty:
        st.info("Sin variaciones para mostrar.")
        return
    for _, r in top.iterrows():
        pos   = float(r["delta_abs"]) >= 0
        cls   = "pos" if pos else "neg"
        arrow = "↑" if pos else "↓"
        dp    = r["delta_pct"]
        dp_s  = f"{dp:+.1f}%" if dp not in (None, float("inf")) else ""
        da_s  = fmt_currency(abs(r["delta_abs"]), currency, compact=True)
        tag_s = f'<span class="alert-tag">{r["tag"]}</span>' if r.get("tag") else ""
        st.markdown(f"""
        <div class="alert-row {cls}">
          <div>
            <span class="alert-name">{r.get("name","")}</span>{tag_s}
          </div>
          <div class="alert-delta {cls}">
            {arrow} {da_s}
            <span style="opacity:.65;font-size:11px;margin-left:4px">{dp_s}</span>
          </div>
        </div>""", unsafe_allow_html=True)


# ── EERR table ────────────────────────────────────────────────────
def _table(df25, df24, col, currency, only_sub=False,
           yr_cur: str = "2025", yr_prev: str = "2024") -> None:
    rows = []
    for _, row in df25.iterrows():
        is_sub = bool(row.get("is_subtotal", False))
        if only_sub and not is_sub:
            continue
        level  = int(row.get("level", 1))
        indent = "&nbsp;&nbsp;&nbsp;&nbsp;" * (0 if is_sub else level)
        v25    = float(row.get(col, 0) or 0)
        v24    = None
        if df24 is not None and col in df24.columns:
            mask = ((df24["code"].astype(str) == str(row.get("code", ""))) &
                    (df24["name"] == row.get("name", "")))
            if mask.any():
                v24 = float(df24[mask][col].iloc[0] or 0)
        is_pct = "%" in str(row.get("name", "")) or "margen" in str(row.get("name", "")).lower()
        v25_s  = fmt_percent(v25) if is_pct else fmt_currency(v25, currency, compact=True)
        da_s   = dp_s = "–"
        dp_cls = ""
        if v24 is not None:
            da, dp = calc_delta(v25, v24)
            da_s = fmt_percent(da) if is_pct else fmt_currency(da, currency, compact=True)
            if dp not in (None, float("inf")):
                dp_s  = f"{dp:+.1f}%"
                dp_cls = "pos-txt" if dp >= 0 else "neg-txt"
        tag_s  = f'<span class="tag-pill">{row.get("tag","")}</span>' if row.get("tag") else ""
        code_s = str(row.get("code", "")) if row.get("code") is not None else ""
        rows.append(
            f'<tr class="{"sub" if is_sub else ""}">'
            f'<td style="color:{CMU};font-size:11px">{code_s}</td>'
            f'<td>{indent}{row.get("name","")}{tag_s}</td>'
            f'<td class="num">{v25_s}</td>'
            f'<td class="num">{da_s}</td>'
            f'<td class="num {dp_cls}">{dp_s}</td>'
            f'</tr>'
        )
    st.markdown(
        '<table class="eerr"><thead><tr>'
        '<th style="width:62px">Código</th><th>Nombre</th>'
        f'<th style="text-align:right;width:130px">{yr_cur}</th>'
        f'<th style="text-align:right;width:130px">Δ vs {yr_prev}</th>'
        '<th style="text-align:right;width:72px">Δ %</th>'
        f'</tr></thead><tbody>{"".join(rows)}</tbody></table>',
        unsafe_allow_html=True,
    )


# ── Drilldown helpers ──────────────────────────────────────────────

def _dd_fmt(val: float, is_pct: bool, currency: str) -> str:
    return fmt_percent(val) if is_pct else fmt_currency(val, currency, compact=True)


def _dd_extract(df25, df24, code_s, name_s):
    """Returns (v25, v24, labels) or None."""
    avail = [c for c in [f"month_{m:02d}" for m in range(1, 13)] if c in df25.columns]
    if not avail:
        return None
    mask25 = (df25["code"].astype(str) == code_s) & (df25["name"] == name_s)
    if not mask25.any():
        return None
    r25 = df25[mask25].iloc[0]
    v25 = [float(r25.get(c, 0) or 0) for c in avail]
    v24 = [0.] * len(avail)
    if df24 is not None:
        mask24 = (df24["code"].astype(str) == code_s) & (df24["name"] == name_s)
        if mask24.any():
            r24 = df24[mask24].iloc[0]
            v24 = [float(r24.get(c, 0) or 0) for c in avail]
    labels = [MONTH_LABELS_ES[int(c.split("_")[1]) - 1] for c in avail]
    return v25, v24, labels


def _dd_stats(v25, v24, currency, is_pct,
              yr_cur: str = "2025", yr_prev: str = "2024") -> None:
    """6 stat chips: annual totals, delta, best/worst month, H2 vs H1."""
    total25 = sum(v25)
    total24 = sum(v24)
    da = total25 - total24
    dp = (da / abs(total24) * 100) if abs(total24) > 0.01 else 0.
    best_i  = max(range(len(v25)), key=lambda i: abs(v25[i]))
    worst_i = min(range(len(v25)), key=lambda i: abs(v25[i]))
    h1 = sum(v25[:6]);  h2 = sum(v25[6:])
    trend_p = (h2 - h1) / abs(h1) * 100 if abs(h1) > 0.01 else 0.

    def _chip(lbl, val, cls):
        c = {"+": CG, "-": CR, "~": CN}[cls]
        return (
            f'<div style="background:white;border:1px solid {CBRD};border-radius:12px;'
            f'padding:14px 16px;box-shadow:0 2px 8px rgba(15,31,74,.05);">'
            f'<div style="font-size:9px;font-weight:800;color:{CMU};text-transform:uppercase;'
            f'letter-spacing:.8px;margin-bottom:6px">{lbl}</div>'
            f'<div style="font-size:16px;font-weight:900;color:{c};line-height:1">{val}</div>'
            f'</div>'
        )

    f = lambda v: _dd_fmt(v, is_pct, currency)
    chips = [
        (f"Total Año {yr_cur}",  f(total25), "~"),
        (f"Total Año {yr_prev}", f(total24), "~"),
        ("Δ Absoluto",      ("+" if da >= 0 else "") + f(da),    "+" if da >= 0 else "-"),
        ("Δ %",             f"{'↑' if dp >= 0 else '↓'} {abs(dp):.1f}%", "+" if dp >= 0 else "-"),
        ("Mejor mes",       f"{MONTH_LABELS_ES[best_i]}  {f(v25[best_i])}",  "~"),
        ("Semestre H2 vs H1", f"{'↑' if trend_p >= 0 else '↓'} {abs(trend_p):.1f}%", "+" if trend_p >= 0 else "-"),
    ]
    cols = st.columns(6, gap="small")
    for i, (lbl, val, cls) in enumerate(chips):
        with cols[i]:
            st.markdown(_chip(lbl, val, cls), unsafe_allow_html=True)
    st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)


def _dd_monthly_chart(v25, v24, labels, name_s, currency, is_pct,
                      yr_cur: str = "2025", yr_prev: str = "2024") -> None:
    """Monthly evolution: area prev year + bars current year + trend + Δ% right axis."""
    dpcts = [(v25[i]-v24[i])/abs(v24[i])*100 if abs(v24[i]) > 0.01 else 0. for i in range(len(labels))]
    bar_c = [CL if v25[i] >= v24[i] else "#F87171" for i in range(len(labels))]
    f = lambda v: _dd_fmt(v, is_pct, currency)
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        name=yr_prev, x=labels, y=v24, mode="lines",
        line=dict(color=CP, width=0),
        fill="tozeroy", fillcolor="rgba(197,213,238,.3)",
        hovertemplate=f"<b>{yr_prev}</b> %{{x}}: %{{customdata}}<extra></extra>",
        customdata=[f(v) for v in v24],
    ))
    fig.add_trace(go.Bar(
        name=yr_cur, x=labels, y=v25,
        marker=dict(color=bar_c, line=dict(width=0), cornerradius=6, opacity=0.88),
        width=0.54,
        hovertemplate=f"<b>{yr_cur}</b> %{{x}}: %{{customdata}}<extra></extra>",
        customdata=[f(v) for v in v25],
    ))
    fig.add_trace(go.Scatter(
        name="Tendencia", x=labels, y=v25, mode="lines+markers",
        line=dict(color=CN, width=2.5),
        marker=dict(size=6, color=CN, line=dict(color="white", width=2)),
        hoverinfo="skip",
    ))
    fig.add_trace(go.Scatter(
        name=f"Δ% vs {yr_prev}", x=labels, y=dpcts, mode="lines+markers",
        line=dict(color="#F59E0B", width=2, dash="dot"),
        marker=dict(size=5, color="#F59E0B"),
        yaxis="y2",
        hovertemplate=f"%{{x}}: %{{y:.1f}}%<extra>Δ% vs {yr_prev}</extra>",
    ))
    yt = "%" if is_pct else f"$ ({currency})"
    fig.update_layout(
        **_PB, barmode="overlay", height=360,
        title=dict(text=f"<b>Evolución mensual</b> — {name_s}",
                   font=dict(size=13, color=CN), x=0, xanchor="left"),
        xaxis=dict(showgrid=False, tickfont=dict(size=12), showline=False),
        yaxis=dict(title=yt, showgrid=True, gridcolor="rgba(0,0,0,0.04)",
                   tickfont=dict(size=10), showline=False, zeroline=False),
        yaxis2=dict(title="Δ %", overlaying="y", side="right", showgrid=False,
                    tickfont=dict(size=10, color="#F59E0B"), ticksuffix="%",
                    showline=False, zeroline=False),
        bargap=0.24,
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


def _dd_quarterly_chart(v25, v24, currency, is_pct,
                        yr_cur: str = "2025", yr_prev: str = "2024") -> None:
    """Quarterly grouped bars prev year vs current year."""
    ql = ["1° Trim", "2° Trim", "3° Trim", "4° Trim"]
    q25 = [sum(v25[i*3:(i+1)*3]) for i in range(4)]
    q24 = [sum(v24[i*3:(i+1)*3]) for i in range(4)]
    f = lambda v: _dd_fmt(v, is_pct, currency)
    fig = go.Figure()
    fig.add_trace(go.Bar(
        name=yr_prev, x=ql, y=q24,
        marker=dict(color=CP, line=dict(width=0), cornerradius=6),
        width=0.32, offset=-0.17,
        customdata=[f(v) for v in q24],
        hovertemplate=f"<b>{yr_prev}</b> %{{x}}<br>%{{customdata}}<extra></extra>",
    ))
    fig.add_trace(go.Bar(
        name=yr_cur, x=ql, y=q25,
        marker=dict(color=[CL if q25[i] >= q24[i] else "#F87171" for i in range(4)],
                    line=dict(width=0), cornerradius=6),
        width=0.32, offset=0.17,
        text=[f(v) for v in q25], textposition="outside",
        textfont=dict(size=10, color=CN, family="Inter"),
        customdata=[f(v) for v in q25],
        hovertemplate=f"<b>{yr_cur}</b> %{{x}}<br>%{{customdata}}<extra></extra>",
    ))
    # Δ% annotations
    for i, (a, b) in enumerate(zip(q25, q24)):
        if abs(b) > 0.01:
            dp = (a - b) / abs(b) * 100
            fig.add_annotation(x=ql[i], y=max(a, b) * 1.08 if max(a, b) > 0 else min(a, b) * 1.08,
                               text=f"{dp:+.1f}%",
                               font=dict(size=10, color=CG if dp >= 0 else CR, family="Inter"),
                               showarrow=False)
    fig.update_layout(
        **_PB, barmode="overlay", height=300,
        title=dict(text="<b>Comparativo trimestral</b>",
                   font=dict(size=13, color=CN), x=0, xanchor="left"),
        xaxis=dict(showgrid=False, tickfont=dict(size=12), showline=False),
        yaxis=dict(showgrid=True, gridcolor="rgba(0,0,0,0.04)",
                   showticklabels=False, showline=False,
                   zeroline=True, zerolinecolor=CBRD),
        bargap=0.3,
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


def _dd_month_table(v25, v24, labels, currency, is_pct,
                    yr_cur: str = "2025", yr_prev: str = "2024") -> None:
    """Month-by-month detail table."""
    f = lambda v: _dd_fmt(v, is_pct, currency)
    has24 = any(abs(v) > 0.01 for v in v24)
    rows = []
    for i, lbl in enumerate(labels):
        da = v25[i] - v24[i]
        dp = (da / abs(v24[i]) * 100) if abs(v24[i]) > 0.01 else None
        pos = da >= 0
        dp_cls = "pos-txt" if pos else "neg-txt"
        dp_s = f"{dp:+.1f}%" if dp is not None else "–"
        da_s = ("+" if pos else "") + f(da) if has24 else "–"
        rows.append(
            f'<tr>'
            f'<td style="font-weight:600;color:{CN};width:42px">{lbl}</td>'
            f'<td class="num">{f(v25[i])}</td>'
            f'<td class="num" style="color:{CMU}">{f(v24[i]) if has24 else "–"}</td>'
            f'<td class="num {dp_cls if has24 else ""}">{da_s}</td>'
            f'<td class="num {dp_cls if has24 else ""}">{dp_s if has24 else "–"}</td>'
            f'</tr>'
        )
    st.markdown(
        '<table class="eerr" style="font-size:12px"><thead><tr>'
        f'<th>Mes</th><th style="text-align:right">{yr_cur}</th>'
        f'<th style="text-align:right;color:#94A3B8">{yr_prev}</th>'
        '<th style="text-align:right">Δ Abs</th>'
        '<th style="text-align:right">Δ %</th>'
        f'</tr></thead><tbody>{"".join(rows)}</tbody></table>',
        unsafe_allow_html=True,
    )


def _dd_sublíneas_chart(df25, df24, code_s, v25, avail, currency, is_pct,
                        yr_cur: str = "2025", yr_prev: str = "2024") -> None:
    """Horizontal bar chart of children lines with prior-year comparison."""
    try:
        ci = int(code_s)
        prefix = ci // 100
        children = df25[df25["code"].apply(
            lambda c: str(c).isdigit() and int(str(c)) // 100 == prefix
                      and int(str(c)) != ci if c is not None else False
        )]
        if children.empty:
            return
        names, vals25, vals24 = [], [], []
        for _, cr in children.iterrows():
            cv25 = sum(float(cr.get(c, 0) or 0) for c in avail)
            cv24 = 0.
            if df24 is not None:
                m24 = (df24["code"].astype(str) == str(cr.get("code", ""))) & (df24["name"] == cr.get("name", ""))
                if m24.any():
                    r24c = df24[m24].iloc[0]
                    cv24 = sum(float(r24c.get(c, 0) or 0) for c in avail)
            names.append(cr.get("name", ""))
            vals25.append(cv25)
            vals24.append(cv24)

        f = lambda v: _dd_fmt(v, is_pct, currency)
        fig = go.Figure()
        fig.add_trace(go.Bar(
            name=yr_prev, y=names, x=vals24, orientation="h",
            marker=dict(color=CP, line=dict(width=0), cornerradius=4),
            customdata=[f(v) for v in vals24],
            hovertemplate=f"<b>{yr_prev}</b> %{{y}}<br>%{{customdata}}<extra></extra>",
        ))
        fig.add_trace(go.Bar(
            name=yr_cur, y=names, x=vals25, orientation="h",
            marker=dict(color=CL, line=dict(width=0), cornerradius=4, opacity=0.9),
            text=[f(v) for v in vals25], textposition="outside",
            textfont=dict(size=10, color=CN),
            customdata=[f(v) for v in vals25],
            hovertemplate=f"<b>{yr_cur}</b> %{{y}}<br>%{{customdata}}<extra></extra>",
        ))
        fig.update_layout(
            **_PB, barmode="overlay", height=max(180, len(names) * 58),
            title=dict(text=f"<b>Sublíneas — anual {yr_prev} vs {yr_cur}</b>",
                       font=dict(size=13, color=CN), x=0, xanchor="left"),
            xaxis=dict(showgrid=True, gridcolor="rgba(0,0,0,.04)",
                       showticklabels=False, showline=False, zeroline=False),
            yaxis=dict(showgrid=False, tickfont=dict(size=11),
                       showline=False, automargin=True),
            margin=dict(l=4, r=70, t=44, b=4),
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    except (ValueError, TypeError):
        pass


# ── Drilldown (kept as thin wrapper for backward compat) ──────────
def _drilldown(df25, df24, code_s, name_s, currency) -> None:
    dd = _dd_extract(df25, df24, code_s, name_s)
    if dd is None:
        st.warning("Línea no encontrada.")
        return
    v25, v24, labels = dd
    _dd_monthly_chart(v25, v24, labels, name_s, currency, "%" in name_s or "margen" in name_s.lower())


# ── AI Insight ────────────────────────────────────────────────────
def _ai_insight(kpis: list, top_vars, currency: str, period_label: str,
                yr_prev: str = "2024") -> None:
    """Renders an AI-style narrative insight paragraph."""
    kpi_map = {k["key"]: k for k in kpis if k["found"]}

    def _v(key):
        return kpi_map[key]["value_2025"] if key in kpi_map else None

    def _dp(key):
        return kpi_map[key]["delta_pct"] if key in kpi_map else None

    def _dpp(key):            # delta in percentage points (for margins)
        k = kpi_map.get(key)
        return k["delta_abs"] if k else None

    sentences = []

    # ── Ventas ───────────────────────────────────────────────────
    v_ventas = _v("ventas")
    dp_ventas = _dp("ventas")
    if v_ventas is not None and dp_ventas is not None:
        v_s  = fmt_currency(v_ventas, currency, compact=True)
        dir_ = "crecimiento" if dp_ventas >= 0 else "retroceso"
        adj  = ("destacado" if abs(dp_ventas) > 30
                else "sólido" if abs(dp_ventas) > 10
                else "moderado")
        sentences.append(
            f"En <b>{period_label}</b>, las Ventas alcanzaron <b>{v_s}</b> "
            f"(<b>{dp_ventas:+.1f}%</b> vs. {yr_prev}), evidenciando un {adj} {dir_} de ingresos."
        )

    # ── EBITDA / margen ───────────────────────────────────────────
    v_ebitda = _v("ebitda")
    v_mebitda = _v("ebitda_margin")
    dpp_mebitda = _dpp("ebitda_margin")
    if v_ebitda is not None and v_mebitda is not None:
        e_s = fmt_currency(v_ebitda, currency, compact=True)
        m_s = fmt_percent(v_mebitda)
        if dpp_mebitda is not None and abs(dpp_mebitda) > 0.01:
            sign  = "expansión" if dpp_mebitda >= 0 else "compresión"
            pp_s  = f"{abs(dpp_mebitda):.1f} pp"
            sentences.append(
                f"El EBITDA llegó a <b>{e_s}</b> con un margen de <b>{m_s}</b>, "
                f"mostrando una <b>{sign} de {pp_s}</b> en rentabilidad operativa respecto al año anterior."
            )
        else:
            sentences.append(
                f"El EBITDA llegó a <b>{e_s}</b> con un margen de <b>{m_s}</b>, "
                f"manteniendo la rentabilidad operativa en línea con {yr_prev}."
            )

    # ── Top driver ────────────────────────────────────────────────
    if top_vars is not None and not top_vars.empty:
        row   = top_vars.iloc[0]
        sign  = "positivo" if row["delta_abs"] >= 0 else "negativo"
        dp_v  = row["delta_pct"]
        dp_s  = f"{dp_v:+.1f}%" if dp_v not in (None, float("inf")) else ""
        sentences.append(
            f"El principal driver <b>{sign}</b> del período es <b>{row['name']}</b> "
            f"({dp_s}), que concentra la mayor variación absoluta respecto al ejercicio anterior."
        )

        # Second negative driver if exists and different sign
        neg_rows = top_vars[top_vars["delta_abs"] < 0] if row["delta_abs"] >= 0 else top_vars[top_vars["delta_abs"] >= 0]
        if not neg_rows.empty:
            row2   = neg_rows.iloc[0]
            sign2  = "presión" if row2["delta_abs"] < 0 else "impulso"
            dp2_s  = f"{row2['delta_pct']:+.1f}%" if row2["delta_pct"] not in (None, float("inf")) else ""
            sentences.append(
                f"Se observa <b>{sign2}</b> en <b>{row2['name']}</b> ({dp2_s}), "
                f"un factor a monitorear en los próximos períodos."
            )

    # ── Utilidad Neta / cierre ─────────────────────────────────
    v_un  = _v("utilidad_neta")
    v_mn  = _v("margen_neto")
    dp_un = _dp("utilidad_neta")
    if v_un is not None and v_mn is not None:
        u_s = fmt_currency(v_un, currency, compact=True)
        m_s = fmt_percent(v_mn)
        calidad = "favorable" if v_un > 0 else "negativo"
        dp_u_s = f" ({dp_un:+.1f}% vs. {yr_prev})" if dp_un is not None else ""
        sentences.append(
            f"La Utilidad Neta de <b>{u_s}</b>{dp_u_s} con margen <b>{m_s}</b> "
            f"consolida un resultado <b>{calidad}</b> para el período analizado."
        )

    if not sentences:
        return

    body = " ".join(sentences)
    st.markdown(
        f'<div class="ai-insight-card">'
        f'  <div class="ai-badge">✦ &nbsp;Lectura IA</div>'
        f'  <p class="ai-insight-text">{body}</p>'
        f'</div>',
        unsafe_allow_html=True,
    )


# ── Validate ──────────────────────────────────────────────────────
def _validate(df25, df24, period_cols, yr_prev: str = "2024") -> dict:
    checks = []
    pcols  = [c for c in period_cols if c in df25.columns]
    nan_n  = int(df25[pcols].isna().sum().sum()) if pcols else 0
    checks.append({"label": "Sin valores NaN", "passed": nan_n == 0,
                   "detail": f"{nan_n} NaN reemplazados" if nan_n else "OK"})
    for nm, pats in [("Ventas", ["venta", "ingreso"]),
                     ("EBITDA", ["ebitda"]),
                     ("Utilidad Neta", ["utilidad neta", "resultado neto"])]:
        found = any(df25["name"].str.lower().str.contains(p, na=False).any() for p in pats)
        checks.append({"label": f"Línea '{nm}' presente", "passed": found,
                       "detail": "Encontrada" if found else "No encontrada"})
    months = [c for c in period_cols if c.startswith("month_")]
    checks.append({"label": "Columnas mensuales", "passed": bool(months),
                   "detail": f"{len(months)} mes(es)" if months else "Ninguno"})
    checks.append({"label": f"Datos {yr_prev} disponibles", "passed": df24 is not None,
                   "detail": "OK" if df24 is not None else f"Sin datos {yr_prev}"})
    checks.append({"label": "Mínimo de líneas (≥5)", "passed": len(df25) >= 5,
                   "detail": f"{len(df25)} líneas"})
    n_sub = int(df25.get("is_subtotal", pd.Series([False] * len(df25))).sum())
    checks.append({"label": "Subtotales detectados", "passed": n_sub >= 1,
                   "detail": f"{n_sub} subtotales"})
    ok = all(c["passed"] for c in checks)
    return {"checks": checks, "all_passed": ok,
            "status": "Listo para publicar" if ok else "Requiere revisión"}


# ── Session state ─────────────────────────────────────────────────
def _init() -> None:
    if "mapping_df" not in st.session_state:
        st.session_state.mapping_df = pd.DataFrame(
            columns=["Cuenta", "Descripción", "Línea EERR", "Regla"])
    if "kpi_codes" not in st.session_state:
        st.session_state.kpi_codes = {k: "" for k in KPI_DEFINITIONS}


# ════════════════════════════════════════════════════════════════
# UPLOAD TAB
# ════════════════════════════════════════════════════════════════

def _render_upload_tab(username: str) -> None:
    """Render the 'Cargar EERR' tab with deduplication logic."""
    uploads = storage.list_uploads(username)

    # ── Historial de cargas ───────────────────────────────────────
    with st.container(border=True):
        st.markdown('<div class="sec-hdr">📁 Historial de cargas</div>',
                    unsafe_allow_html=True)
        if not uploads:
            st.info("Aún no hay estados de resultados cargados para este usuario.")
        else:
            rows = "".join(
                f'<tr>'
                f'<td style="font-weight:600">{_MONTHS_ES[u["month"]-1]} {u["year"]}</td>'
                f'<td style="color:#64748B;font-size:12px">'
                f'{u["uploaded_at"][:16].replace("T", " ")}</td>'
                f'<td><span style="background:#DCFCE7;color:#15803D;'
                f'border-radius:20px;padding:2px 10px;font-size:11px;font-weight:700">'
                f'✓ Cargado</span></td>'
                f'</tr>'
                for u in uploads
            )
            st.markdown(
                '<table class="eerr" style="font-size:13px"><thead><tr>'
                '<th>Período</th><th>Fecha de carga</th><th>Estado</th>'
                f'</tr></thead><tbody>{rows}</tbody></table>',
                unsafe_allow_html=True,
            )

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    # ── Formulario de nueva carga ─────────────────────────────────
    with st.container(border=True):
        st.markdown('<div class="sec-hdr">⬆️ Nueva carga</div>',
                    unsafe_allow_html=True)
        col_m, col_y, col_f = st.columns([2, 1, 3])
        with col_m:
            sel_month_name = st.selectbox("Mes", _MONTHS_ES, key="up_month")
            sel_month = _MONTHS_ES.index(sel_month_name) + 1
        with col_y:
            sel_year = st.number_input(
                "Año", min_value=2020, max_value=2030,
                value=_dt.date.today().year, step=1, key="up_year",
            )
        with col_f:
            uploaded_file = st.file_uploader(
                "Archivo Excel (.xlsx)", type=["xlsx", "xls"], key="up_file",
            )

        already = storage.upload_exists(username, int(sel_year), sel_month)
        if already:
            st.warning(
                f"Ya existe un EERR cargado para "
                f"**{sel_month_name} {sel_year}**. "
                f"No se puede volver a subir el mismo período."
            )

        btn = st.button(
            "Guardar EERR",
            type="primary",
            disabled=(uploaded_file is None or already),
            key="up_submit",
        )

        if btn and uploaded_file is not None and not already:
            with st.spinner("Procesando archivo…"):
                try:
                    # Detectar formato: Guantex o genérico
                    uploaded_file.seek(0)
                    if is_guantex_format(uploaded_file):
                        uploaded_file.seek(0)
                        parser = GuantexParser()
                        raw = parser.load(uploaded_file)
                        fmt_label = "Guantex"
                    else:
                        uploaded_file.seek(0)
                        parser = EERRParser()
                        raw = parser.load(uploaded_file)
                        fmt_label = "genérico"

                    if parser.warnings:
                        for w in parser.warnings:
                            st.warning(w)
                    storage.save_upload(username, int(sel_year), sel_month, raw)
                    # Limpiar caché y estado para que el dashboard recargue el nuevo archivo
                    _load.clear()
                    for _k in ["sb_upload", "sb_currency", "sb_period",
                               "sb_sociedad", "_go_upload"]:
                        st.session_state.pop(_k, None)
                    st.success(
                        f"✅ EERR {fmt_label} de **{sel_month_name} {sel_year}** guardado correctamente."
                    )
                    st.rerun()
                except Exception as exc:
                    st.error(f"Error procesando el archivo: {exc}")


# ════════════════════════════════════════════════════════════════
# MAIN
# ════════════════════════════════════════════════════════════════
def _render_no_data_screen(username: str) -> None:
    """Pantalla inicial cuando el usuario no tiene ERRRs cargados."""
    _b64 = _logo_b64()
    _logo_html = (
        f'<img src="data:image/png;base64,{_b64}" style="height:52px;width:auto" />'
        if _b64 else
        '<div style="font-size:22px;font-weight:900;color:#0F1F4A;letter-spacing:3px">ASCENT</div>'
    )
    dname = auth.display_name(username)
    st.markdown(f"""
    <div style="max-width:520px;margin:80px auto 0;text-align:center;">
      {_logo_html}
      <h2 style="font-size:22px;font-weight:800;color:{CN};margin:24px 0 8px;">
        Bienvenido, {dname}
      </h2>
      <p style="color:{CMU};font-size:15px;margin:0 0 32px;">
        Todavía no cargaste ningún Estado de Resultados.<br>
        Subí tu primer archivo para comenzar el análisis.
      </p>
    </div>
    """, unsafe_allow_html=True)
    _, col, _ = st.columns([1, 2, 1])
    with col:
        if st.button("📁  Cargar mi primer EERR", type="primary", use_container_width=True):
            st.session_state["_go_upload"] = True
            st.rerun()
    # Si se hizo click en el botón, mostramos el formulario de carga directamente
    if st.session_state.get("_go_upload"):
        st.markdown("---")
        _render_upload_tab(username)


# ════════════════════════════════════════════════════════════════
# CHAT / ANALISTA IA
# ════════════════════════════════════════════════════════════════

_QUICK_PROMPTS = [
    "¿Cómo vienen las ventas MoM en los últimos meses?",
    "¿Cuál es la tendencia del EBITDA?",
    "¿Qué línea de costos creció más en el período?",
    "Comparame las ventas de este año vs el año anterior.",
    "¿Cuál es el margen neto actual y cómo evolucionó?",
    "Dame un resumen ejecutivo del EERR en pocas palabras.",
]


def _get_api_key(provider: str) -> str:
    """Lee la API key del provider desde st.secrets → env var → session_state."""
    from eerr_cockpit.agent import PROVIDERS
    env_key = PROVIDERS[provider]["env_key"]
    return (
        st.secrets.get(env_key, "")
        or os.environ.get(env_key, "")
        or st.session_state.get(f"_chat_api_key_{provider}", "")
    )


def _render_chat_tab(
    df25: pd.DataFrame,
    df24,
    currency: str,
    yr_cur: str,
    yr_prev: str,
    sel_label: str,
) -> None:
    """Renderiza el tab de chat con el analista IA."""
    from eerr_cockpit.agent import PROVIDERS

    # ── Selector de provider ──────────────────────────────────────
    provider_options = {v["label"]: k for k, v in PROVIDERS.items()}
    provider_label = st.radio(
        "Modelo",
        list(provider_options.keys()),
        horizontal=True,
        key="_chat_provider",
        index=1,  # Groq por defecto
    )
    provider = provider_options[provider_label]

    # ── API key ──────────────────────────────────────────────────
    api_key = _get_api_key(provider)

    if not api_key:
        prov_info = PROVIDERS[provider]
        placeholder = "gsk_..." if provider == "groq" else "sk-ant-..."
        st.warning(
            f"Para usar **{prov_info['label']}** necesitás una API key. "
            f"Obtené una gratis en {'console.groq.com' if provider == 'groq' else 'console.anthropic.com'} "
            f"e ingresala acá, o agregala en `.streamlit/secrets.toml` como `{prov_info['env_key']}`."
        )
        col_k, col_b = st.columns([3, 1])
        with col_k:
            key_input = st.text_input(
                f"API Key ({prov_info['label']})",
                type="password",
                placeholder=placeholder,
                key=f"_chat_key_input_{provider}",
                label_visibility="collapsed",
            )
        with col_b:
            if st.button("Confirmar", type="primary", key=f"_chat_key_btn_{provider}"):
                if key_input.strip():
                    st.session_state[f"_chat_api_key_{provider}"] = key_input.strip()
                    st.rerun()
                else:
                    st.error("Ingresá una key válida.")
        return

    # ── Contexto EERR ────────────────────────────────────────────
    ctx_key = f"_chat_ctx_{currency}_{yr_cur}_{sel_label}"
    if ctx_key not in st.session_state:
        st.session_state[ctx_key] = build_context(
            df25, df24, currency, yr_cur, yr_prev, sel_label
        )
    eerr_context = st.session_state[ctx_key]

    # ── Historial (por provider para no mezclar conversaciones) ──
    hist_key = f"chat_messages_{provider}"
    if hist_key not in st.session_state:
        st.session_state[hist_key] = []

    # ── Prompt a procesar (viene de quick-prompt o de chat_input) ─
    # Se guarda antes de renderizar para no depender del rerun.
    pending_prompt: str | None = st.session_state.pop("_chat_prompt", None)

    # ── Layout ──────────────────────────────────────────────────
    col_chat, col_info = st.columns([3, 1])

    with col_info:
        prov_cfg = PROVIDERS[provider]
        st.markdown(
            f"""
            <div style="background:#EEF2FA;border:1px solid #D1DDEF;border-radius:14px;
                        padding:18px 16px;font-size:12px;color:#334155;line-height:1.7">
                <div style="font-weight:700;color:#0F1F4A;margin-bottom:8px">📊 Contexto activo</div>
                <b>Período:</b> {sel_label}<br>
                <b>Moneda:</b> {currency}<br>
                <b>Año actual:</b> {yr_cur}<br>
                <b>Año anterior:</b> {yr_prev}<br>
                <b>Líneas cargadas:</b> {len(df25)}<br>
                <b>Modelo:</b> {prov_cfg['model']}
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

        if st.button("🗑️ Limpiar chat", use_container_width=True, key="_chat_clear"):
            st.session_state[hist_key] = []
            st.rerun()

        st.markdown(
            '<div style="font-size:11px;color:#64748B;margin-top:14px;line-height:1.6">'
            "💡 <b>Preguntas sugeridas:</b>"
            "</div>",
            unsafe_allow_html=True,
        )
        for qp in _QUICK_PROMPTS:
            if st.button(qp, use_container_width=True, key=f"qp_{qp[:20]}"):
                st.session_state["_chat_prompt"] = qp
                st.rerun()

    with col_chat:
        # ── Mostrar historial ─────────────────────────────────────
        if not st.session_state[hist_key] and not pending_prompt:
            st.markdown(
                f"""
                <div style="text-align:center;padding:48px 24px;color:#64748B">
                    <div style="font-size:40px;margin-bottom:12px">💬</div>
                    <div style="font-size:16px;font-weight:700;color:#0F1F4A;margin-bottom:8px">
                        Analista IA
                    </div>
                    <div style="font-size:13px;line-height:1.7">
                        Preguntame lo que quieras sobre el EERR de <b>{sel_label}</b>.<br>
                        Podés usar las preguntas sugeridas de la derecha<br>
                        o escribir la tuya propia.
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            for msg in st.session_state[hist_key]:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])

        # ── Input del usuario ─────────────────────────────────────
        user_input = st.chat_input("Preguntá sobre el EERR…")
        prompt = user_input or pending_prompt

        # ── Generar respuesta ─────────────────────────────────────
        if prompt:
            # Mostrar mensaje del usuario inmediatamente
            with st.chat_message("user"):
                st.markdown(prompt)
            st.session_state[hist_key].append({"role": "user", "content": prompt})

            # Stream de respuesta
            with st.chat_message("assistant"):
                response_chunks: list[str] = []

                def _gen():
                    for chunk in stream_response(
                        st.session_state[hist_key],
                        eerr_context,
                        api_key,
                        provider=provider,
                    ):
                        response_chunks.append(chunk)
                        yield chunk

                st.write_stream(_gen())

            st.session_state[hist_key].append(
                {"role": "assistant", "content": "".join(response_chunks)}
            )


def main() -> None:
    # ── Auth gate ────────────────────────────────────────────────
    if not auth.is_authenticated():
        auth.render_login()
        return

    _init()
    username = auth.current_user()
    uploads  = storage.list_uploads(username)

    # ── Sin datos: pantalla de bienvenida ────────────────────────
    if not uploads:
        _render_no_data_screen(username)
        return

    # ── Selección de archivo EERR (via session_state del widget) ─
    # El selectbox "sb_upload" se renderiza en _sidebar; leemos aquí
    # su valor para saber qué cargar antes de renderizar el resto.
    _ul_map = {
        f"{_MONTHS_ES[u['month']-1]} {u['year']}": u
        for u in reversed(uploads)
    }
    _default_label = list(_ul_map.keys())[0]
    _sel_label     = st.session_state.get("sb_upload", _default_label)
    _sel_upload    = _ul_map.get(_sel_label, list(_ul_map.values())[0])

    data = _load(username, _sel_upload["year"], _sel_upload["month"])
    if data is None:
        st.error("No se pudo cargar el EERR seleccionado.")
        return

    # ── Sidebar (currency, period, alerts, sociedad) ─────────────
    currency, sel_key, sel_label, top_n, alert_mode, sociedad = _sidebar(data, uploads)

    # ── Dynamic year detection ────────────────────────────────────
    avail_years = sorted(data.get(currency, {}).keys())
    yr_cur  = avail_years[-1] if avail_years else "2025"
    yr_prev = avail_years[-2] if len(avail_years) > 1 else str(int(yr_cur) - 1)

    df25_c = data[currency].get(yr_cur)
    df24_c = data[currency].get(yr_prev)

    if df25_c is None or sel_key is None:
        st.error("Error cargando datos.")
        return

    # ── Header ───────────────────────────────────────────────────
    _header(sel_label, currency)

    # ── Prepare DataFrames (con filtro de sociedad) ───────────────
    df25 = _filter_sociedad(df25_c.copy(), sociedad) if sociedad else df25_c.copy()
    df24 = (_filter_sociedad(df24_c.copy(), sociedad) if sociedad else df24_c.copy()) \
           if df24_c is not None else None

    if sel_key.startswith("ytd_"):
        m_num = int(sel_key.split("_")[1])
        df25["__ytd__"] = _ytd(df25, m_num)
        if df24 is not None:
            df24["__ytd__"] = _ytd(df24, m_num)
        actual_col = "__ytd__"
    else:
        actual_col = sel_key

    if actual_col not in df25.columns:
        st.error(f"Columna `{actual_col}` no encontrada.")
        return

    period_cols_all = get_period_columns(df25)

    # ── Tabs ─────────────────────────────────────────────────────
    t1, t2, t3, t4, t5, t6, t7, t8 = st.tabs([
        "📋  Resumen ejecutivo",
        "📊  EERR",
        "🔍  Drilldown",
        "✅  Checklist",
        "🗺️  Mapping Studio",
        "📤  Exportar",
        "📁  Cargar EERR",
        "💬  Analista IA",
    ])

    # ── TAB 1: RESUMEN ───────────────────────────────────────────
    with t1:
        kpis = get_kpis(df25, df24, actual_col, currency, st.session_state.kpi_codes)
        _kpi_cards(kpis, currency)

        col_a, col_b = st.columns([3, 2], gap="large")
        with col_a:
            with st.container(border=True):
                _chart_comparativo(kpis, currency, yr_cur, yr_prev)
        with col_b:
            with st.container(border=True):
                _chart_waterfall(kpis, currency, yr_prev)

        st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
        with st.container(border=True):
            st.markdown(
                f'<div class="sec-hdr">🚨 Top Variaciones vs {yr_prev}</div>',
                unsafe_allow_html=True,
            )
            if df24 is None or actual_col not in df24.columns:
                st.info("Sin datos comparativos para este período.")
            else:
                top_vars = get_top_variations(df25, df24, actual_col, top_n,
                                              {"Todos": "all", "Positivos": "positive",
                                               "Negativos": "negative"}.get(alert_mode, "all"))
                _alerts(df25, df24, actual_col, currency, top_n, alert_mode)

        st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
        _ai_insight(kpis,
                    top_vars if (df24 is not None and actual_col in df24.columns) else None,
                    currency, sel_label, yr_prev)

    # ── TAB 2: EERR ──────────────────────────────────────────────
    with t2:
        c1, _, c3 = st.columns([5, 2, 1])
        with c1:
            only_sub = st.checkbox("Solo subtotales / KPIs", False)
        with c3:
            st.caption(f"{len(df25)} líneas")
        with st.container(border=True):
            _table(df25, df24, actual_col, currency, only_sub, yr_cur, yr_prev)

    # ── TAB 3: DRILLDOWN ─────────────────────────────────────────
    with t3:
        line_opts = [f"{r.get('code','')} — {r.get('name','')}" for _, r in df25.iterrows()]
        sel_line  = st.selectbox("Línea:", line_opts, key="dd_line")
        if sel_line:
            parts = sel_line.split(" — ", 1)
            sc    = parts[0].strip()
            sn    = parts[1].strip() if len(parts) > 1 else ""
            is_pct_dd = "%" in sn or "margen" in sn.lower()

            dd = _dd_extract(df25, df24, sc, sn)
            if dd is None:
                st.warning("Línea no encontrada.")
            else:
                v25_dd, v24_dd, labels_dd = dd

                # ── Stats chips ───────────────────────────────────
                _dd_stats(v25_dd, v24_dd, currency, is_pct_dd, yr_cur, yr_prev)

                # ── Monthly evolution chart ───────────────────────
                with st.container(border=True):
                    _dd_monthly_chart(v25_dd, v24_dd, labels_dd, sn, currency,
                                      is_pct_dd, yr_cur, yr_prev)

                # ── Quarterly + month table ───────────────────────
                col_q, col_t = st.columns([3, 2], gap="large")
                with col_q:
                    with st.container(border=True):
                        _dd_quarterly_chart(v25_dd, v24_dd, currency, is_pct_dd,
                                            yr_cur, yr_prev)
                with col_t:
                    with st.container(border=True):
                        st.markdown('<div class="sec-hdr">Detalle mensual</div>',
                                    unsafe_allow_html=True)
                        _dd_month_table(v25_dd, v24_dd, labels_dd, currency,
                                        is_pct_dd, yr_cur, yr_prev)

                # ── Sublíneas horizontal chart ────────────────────
                avail_dd = [c for c in [f"month_{m:02d}" for m in range(1, 13)]
                            if c in df25.columns]
                with st.container(border=True):
                    _dd_sublíneas_chart(df25, df24, sc, v25_dd, avail_dd,
                                        currency, is_pct_dd, yr_cur, yr_prev)

    # ── TAB 4: CHECKLIST ─────────────────────────────────────────
    with t4:
        val = _validate(df25, df24, period_cols_all, yr_prev)
        if val["all_passed"]:
            st.success(f"✅ **{val['status']}**")
        else:
            st.warning(f"⚠️ **{val['status']}**")
        with st.container(border=True):
            for chk in val["checks"]:
                c1, c2 = st.columns([1, 9])
                with c1:
                    st.markdown("✅" if chk["passed"] else "❌")
                with c2:
                    st.markdown(f"**{chk['label']}** — {chk['detail']}")

    # ── TAB 5: MAPPING STUDIO ────────────────────────────────────
    with t5:
        with st.container(border=True):
            st.markdown('<div class="sec-hdr">🗺️ Mapping Studio — ERP → Línea EERR</div>', unsafe_allow_html=True)
            st.caption("Placeholder editable · Integración ERP en roadmap")
            eerr_lines = [f"{r.get('code','')} — {r.get('name','')}" for _, r in df25.iterrows()]
            col_ed, col_io = st.columns([3, 1])
            with col_ed:
                edited = st.data_editor(
                    st.session_state.mapping_df, num_rows="dynamic",
                    column_config={
                        "Cuenta":      st.column_config.TextColumn("Cuenta ERP",  width="medium"),
                        "Descripción": st.column_config.TextColumn("Descripción", width="large"),
                        "Línea EERR":  st.column_config.SelectboxColumn(
                            "Línea EERR", options=[""] + eerr_lines, width="large"),
                        "Regla":       st.column_config.TextColumn("Regla", width="medium"),
                    }, use_container_width=True, key="map_ed")
                st.session_state.mapping_df = edited
                if not edited.empty:
                    mapped = edited["Línea EERR"].notna().sum()
                    total  = len(edited)
                    st.metric("Cobertura",
                              f"{mapped/total*100:.1f}%" if total else "0%",
                              f"{mapped}/{total} cuentas mapeadas")
            with col_io:
                if not st.session_state.mapping_df.empty:
                    st.download_button("📥 CSV",
                                       data=st.session_state.mapping_df.to_csv(index=False),
                                       file_name="mapping.csv", mime="text/csv")
                    st.download_button("📥 JSON",
                                       data=st.session_state.mapping_df.to_json(
                                           orient="records", force_ascii=False),
                                       file_name="mapping.json", mime="application/json")
                imp = st.file_uploader("Importar", type=["csv", "json"], key="map_imp")
                if imp:
                    try:
                        st.session_state.mapping_df = (
                            pd.read_csv(imp) if imp.name.endswith(".csv") else pd.read_json(imp))
                        st.success("✅")
                        st.rerun()
                    except Exception as exc:
                        st.error(str(exc))

    # ── TAB 6: EXPORTAR ──────────────────────────────────────────
    with t6:
        with st.container(border=True):
            st.markdown('<div class="sec-hdr">📤 Pack Mensual PDF</div>', unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            with c1:
                company = st.text_input("Empresa:", value="Ascent Advisors")
            with c2:
                st.info(f"Archivo: `EERR_{currency}_{sel_label}.pdf`")
            st.markdown("Incluye **KPIs · Top variaciones · Tabla EERR**")
            if st.button("📄 Generar PDF", type="primary"):
                with st.spinner("Generando…"):
                    try:
                        kpis_pdf = get_kpis(df25, df24, actual_col, currency,
                                            st.session_state.kpi_codes)
                        tv_pdf   = (get_top_variations(df25, df24, actual_col, top_n, "all")
                                    if df24 is not None else pd.DataFrame())
                        pdf = create_pdf_report(df25, df24, actual_col, sel_label,
                                                currency, kpis_pdf, tv_pdf, company)
                        st.download_button(
                            f"⬇️ EERR_{currency}_{sel_label}.pdf",
                            data=pdf,
                            file_name=f"EERR_{currency}_{sel_label}.pdf",
                            mime="application/pdf",
                        )
                        st.success("✅ PDF listo.")
                    except Exception as exc:
                        st.error(f"Error: {exc}")
                        import traceback; st.code(traceback.format_exc())

        with st.container(border=True):
            st.markdown('<div class="sec-hdr">📊 Export PPT</div>', unsafe_allow_html=True)
            st.info("🚧 En desarrollo · 3 slides: Resumen · EERR · Top variaciones")
            st.button("📑 Generar PPT", disabled=True)

    # ── TAB 7: CARGAR EERR ───────────────────────────────────────
    with t7:
        _render_upload_tab(username)

    # ── TAB 8: ANALISTA IA ───────────────────────────────────────
    with t8:
        _render_chat_tab(df25, df24, currency, yr_cur, yr_prev, sel_label)


if __name__ == "__main__":
    main()
