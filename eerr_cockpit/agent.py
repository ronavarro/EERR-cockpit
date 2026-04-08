"""
Agente conversacional para EERR Cockpit.
Usa el SDK de Anthropic para responder preguntas en lenguaje natural
sobre el Estado de Resultados cargado por el usuario.
"""

from __future__ import annotations

import os
from typing import Iterator, Optional

import pandas as pd

from .config import MONTH_LABELS_ES, QUARTER_LABELS_ES

# ── Modelo ───────────────────────────────────────────────────────────
_MODEL = "claude-opus-4-6"

# ── System prompt ────────────────────────────────────────────────────
_SYSTEM = """\
Sos un analista financiero experto en Estados de Resultados (EERR), \
especializado en ayudar a usuarios no técnicos a entender sus resultados empresariales.

Tu tarea es responder preguntas sobre el Estado de Resultados de la empresa \
usando los datos reales que se te proveen en el contexto.

Reglas:
- Respondé siempre en español rioplatense (Argentina).
- Usá lenguaje claro, simple y directo — evitá jerga técnica innecesaria.
- Cuando des cifras, usá formato latinoamericano: punto para miles, coma para decimales \
  (ej: $1.234.567,89).
- Cuando hagas comparaciones MoM o YoY, señalá si la variación es positiva o negativa \
  con palabras claras ("creció", "cayó", "se mantuvo estable").
- Si la pregunta requiere datos que no están en el contexto, decilo honestamente.
- Sé conciso: respondé lo que se pregunta sin agregar análisis no solicitados, \
  a menos que sean muy relevantes.
- No inventes cifras. Solo usá los datos del contexto.
- Si detectás algo llamativo en los datos (caída brusca, crecimiento inusual), \
  podés mencionarlo brevemente al final como "Dato destacado".
"""


# ── Helpers de formato ────────────────────────────────────────────────

def _fmt(v: float) -> str:
    """Número con punto miles y coma decimal."""
    try:
        s = f"{abs(v):,.0f}".replace(",", "X").replace(".", ",").replace("X", ".")
        return f"-{s}" if v < 0 else s
    except Exception:
        return str(v)


def _col_label(col: str) -> str:
    """month_01 → Ene, quarter_01 → T1, year_00 → Año."""
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
    """Columnas de período que tienen datos (suma absoluta > 0)."""
    cols = []
    for c in df.columns:
        if c.startswith(("month_", "quarter_", "year_")):
            if float(df[c].abs().sum()) > 0:
                cols.append(c)
    # Orden: meses → trimestres → año
    months   = sorted([c for c in cols if c.startswith("month_")])
    quarters = sorted([c for c in cols if c.startswith("quarter_")])
    years    = sorted([c for c in cols if c.startswith("year_")])
    return months + quarters + years


# ── Construcción del contexto ─────────────────────────────────────────

def build_context(
    df_cur: pd.DataFrame,
    df_prev: Optional[pd.DataFrame],
    currency: str,
    yr_cur: str,
    yr_prev: str,
    sel_label: str,
) -> str:
    """
    Construye un texto estructurado con los datos del EERR para pasarle
    al modelo como contexto.
    """
    period_cols = _available_period_cols(df_cur)

    lines: list[str] = []
    lines.append(f"## Estado de Resultados — Moneda: {currency}")
    lines.append(f"Período visualizado actualmente: {sel_label}")
    lines.append(f"Año principal: {yr_cur}  |  Año comparación: {yr_prev}")
    lines.append("")

    # ── Tabla EERR año actual ──────────────────────────────────────
    header_cols = period_cols
    col_labels  = [_col_label(c) for c in header_cols]

    lines.append(f"### Datos {yr_cur}")
    header_row = "| Línea | " + " | ".join(col_labels) + " |"
    sep_row    = "|" + "---|" * (len(col_labels) + 1)
    lines.append(header_row)
    lines.append(sep_row)

    for _, row in df_cur.iterrows():
        name = str(row.get("name", "")).strip()
        if not name:
            continue
        vals = []
        for c in header_cols:
            v = row.get(c, 0)
            try:
                vals.append(_fmt(float(v)))
            except Exception:
                vals.append("–")
        lines.append(f"| {name} | " + " | ".join(vals) + " |")

    lines.append("")

    # ── Tabla EERR año anterior ────────────────────────────────────
    if df_prev is not None:
        prev_cols = _available_period_cols(df_prev)
        common    = [c for c in header_cols if c in prev_cols]
        if common:
            col_labels_prev = [_col_label(c) for c in common]
            lines.append(f"### Datos {yr_prev}")
            lines.append("| Línea | " + " | ".join(col_labels_prev) + " |")
            lines.append("|" + "---|" * (len(col_labels_prev) + 1))
            for _, row in df_prev.iterrows():
                name = str(row.get("name", "")).strip()
                if not name:
                    continue
                vals = []
                for c in common:
                    v = row.get(c, 0)
                    try:
                        vals.append(_fmt(float(v)))
                    except Exception:
                        vals.append("–")
                lines.append(f"| {name} | " + " | ".join(vals) + " |")
            lines.append("")

    lines.append("---")
    lines.append("Usá estos datos para responder las preguntas del usuario.")

    return "\n".join(lines)


# ── Llamada al modelo ─────────────────────────────────────────────────

def stream_response(
    messages: list[dict],
    eerr_context: str,
    api_key: str,
) -> Iterator[str]:
    """
    Genera la respuesta del modelo en streaming.
    `messages` es la lista de mensajes de la conversación (sin el system prompt).
    Yields: chunks de texto a medida que llegan.
    """
    try:
        import anthropic
    except ImportError:
        yield "Error: instalá el paquete `anthropic` (`pip install anthropic`)."
        return

    client = anthropic.Anthropic(api_key=api_key)

    system_with_context = f"{_SYSTEM}\n\n{eerr_context}"

    with client.messages.stream(
        model=_MODEL,
        max_tokens=1024,
        system=system_with_context,
        messages=messages,
    ) as stream:
        for text in stream.text_stream:
            yield text
