"""
Agente conversacional para EERR Cockpit.
Soporta Anthropic (claude-opus-4-6) y Groq (llama-3.3-70b) como providers.
"""

from __future__ import annotations

import os
from typing import Iterator, Optional

import pandas as pd

from .config import MONTH_LABELS_ES, QUARTER_LABELS_ES

# ── Modelos por provider ─────────────────────────────────────────────
PROVIDERS = {
    "anthropic": {
        "label": "Anthropic (Claude)",
        "model": "claude-opus-4-6",
        "env_key": "ANTHROPIC_API_KEY",
    },
    "groq": {
        "label": "Groq (LLaMA 3.3 · gratis)",
        "model": "llama-3.3-70b-versatile",
        "env_key": "GROQ_API_KEY",
    },
}

# Máximo de columnas de período a incluir en el contexto
_MAX_PERIOD_COLS = 3

# ── System prompt ────────────────────────────────────────────────────
_SYSTEM = """\
Sos un analista financiero experto en EERR. Ayudás a usuarios no técnicos.
Respondé en español rioplatense, de forma clara y concisa.
Usá formato numérico latinoamericano (punto miles, coma decimal).
Solo usá los datos del contexto. No inventes cifras.
Si algo es llamativo, mencionalo brevemente al final.
"""


# ── Helpers de formato ────────────────────────────────────────────────

def _fmt(v: float) -> str:
    try:
        s = f"{abs(v):,.0f}".replace(",", "X").replace(".", ",").replace("X", ".")
        return f"-{s}" if v < 0 else s
    except Exception:
        return str(v)


def _col_label(col: str) -> str:
    if col.startswith("month_"):
        n = int(col.split("_")[1])
        return MONTH_LABELS_ES[n - 1]
    if col.startswith("quarter_"):
        n = int(col.split("_")[1])
        return QUARTER_LABELS_ES[n - 1]
    if col.startswith("year_"):
        return "Año"
    return col


def _available_period_cols(df: pd.DataFrame) -> list[str]:
    cols = []
    for c in df.columns:
        if c.startswith(("month_", "quarter_", "year_")):
            if float(df[c].abs().sum()) > 0:
                cols.append(c)
    months   = sorted([c for c in cols if c.startswith("month_")])
    quarters = sorted([c for c in cols if c.startswith("quarter_")])
    years    = sorted([c for c in cols if c.startswith("year_")])
    return months + quarters + years


# ── Construcción del contexto ─────────────────────────────────────────

def _trim_period_cols(all_cols: list[str], max_cols: int = _MAX_PERIOD_COLS) -> list[str]:
    """
    Selecciona los períodos más relevantes para el contexto:
    - Siempre incluye el año total (year_00) si existe
    - Luego los últimos meses disponibles hasta completar max_cols
    - Si sobran slots, agrega trimestres
    """
    years    = [c for c in all_cols if c.startswith("year_")]
    months   = [c for c in all_cols if c.startswith("month_")]
    quarters = [c for c in all_cols if c.startswith("quarter_")]

    selected: list[str] = []
    slots = max_cols

    # Año total primero
    for y in years:
        if slots > 0:
            selected.append(y)
            slots -= 1

    # Últimos meses (los más recientes)
    for m in reversed(months):
        if slots > 0:
            selected.insert(len(years), m)   # antes de los años ya agregados no, insertamos al frente de meses
            slots -= 1
        else:
            break

    # Si quedan slots, trimestres
    for q in reversed(quarters):
        if slots > 0:
            selected.append(q)
            slots -= 1
        else:
            break

    # Reordenar: meses → trimestres → año
    def _sort_key(c):
        if c.startswith("month_"):   return (0, c)
        if c.startswith("quarter_"): return (1, c)
        return (2, c)

    return sorted(selected, key=_sort_key)


def _df_to_table(df: pd.DataFrame, period_cols: list[str], year_label: str) -> list[str]:
    """
    Genera la tabla del EERR.
    Incluye TODAS las filas con al menos un valor no cero,
    omitiendo filas completamente vacías para reducir tokens.
    """
    col_labels = [_col_label(c) for c in period_cols]
    lines = [
        f"### Datos {year_label}",
        "| Línea | " + " | ".join(col_labels) + " |",
        "|" + "---|" * (len(col_labels) + 1),
    ]
    for _, row in df.iterrows():
        name = str(row.get("name", "")).strip()
        if not name:
            continue
        vals = []
        row_total = 0.0
        for c in period_cols:
            v = row.get(c, 0)
            try:
                fv = float(v)
                row_total += abs(fv)
                vals.append(_fmt(fv))
            except Exception:
                vals.append("–")
        if row_total == 0:
            continue
        lines.append(f"| {name} | " + " | ".join(vals) + " |")
    return lines


def build_context(
    df_cur: pd.DataFrame,
    df_prev: Optional[pd.DataFrame],
    currency: str,
    yr_cur: str,
    yr_prev: str,
    sel_label: str,
) -> str:
    all_cols     = _available_period_cols(df_cur)
    period_cols  = _trim_period_cols(all_cols, _MAX_PERIOD_COLS)

    lines: list[str] = [
        f"## Estado de Resultados — Moneda: {currency}",
        f"Período visualizado actualmente: {sel_label}",
        f"Año principal: {yr_cur}  |  Año comparación: {yr_prev}",
        f"(Nota: se muestran los {len(period_cols)} períodos más recientes con datos)",
        "",
    ]

    lines += _df_to_table(df_cur, period_cols, yr_cur)
    lines.append("")

    if df_prev is not None:
        prev_cols    = _available_period_cols(df_prev)
        common       = [c for c in period_cols if c in prev_cols]
        common_trim  = _trim_period_cols(common, _MAX_PERIOD_COLS)
        if common_trim:
            lines += _df_to_table(df_prev, common_trim, yr_prev)
            lines.append("")

    lines += ["---", "Usá estos datos para responder las preguntas del usuario."]
    return "\n".join(lines)


# ── Streaming por provider ────────────────────────────────────────────

def _stream_anthropic(messages: list[dict], system: str, api_key: str) -> Iterator[str]:
    import anthropic
    client = anthropic.Anthropic(api_key=api_key)
    with client.messages.stream(
        model=PROVIDERS["anthropic"]["model"],
        max_tokens=1024,
        system=system,
        messages=messages,
    ) as stream:
        for text in stream.text_stream:
            yield text


def _stream_groq(messages: list[dict], system: str, api_key: str) -> Iterator[str]:
    from groq import Groq
    client = Groq(api_key=api_key)
    all_msgs = [{"role": "system", "content": system}] + messages
    stream = client.chat.completions.create(
        model=PROVIDERS["groq"]["model"],
        messages=all_msgs,
        max_tokens=600,   # reducido para respetar TPM del free tier
        stream=True,
    )
    for chunk in stream:
        delta = chunk.choices[0].delta.content
        if delta:
            yield delta


def stream_response(
    messages: list[dict],
    eerr_context: str,
    api_key: str,
    provider: str = "anthropic",
) -> Iterator[str]:
    """Genera respuesta en streaming para el provider indicado."""
    system = f"{_SYSTEM}\n\n{eerr_context}"
    if provider == "groq":
        yield from _stream_groq(messages, system, api_key)
    else:
        yield from _stream_anthropic(messages, system, api_key)
