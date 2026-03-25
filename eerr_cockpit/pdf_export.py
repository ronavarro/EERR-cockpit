"""
Generación de PDF del pack mensual.
Usa reportlab Platypus para layout.
"""

from __future__ import annotations

import io
from typing import Optional

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from .kpis import calc_delta, fmt_currency, fmt_percent

# Paleta de colores Ascent
_DARK  = colors.HexColor("#1a1a2e")
_MID   = colors.HexColor("#2d2d5e")
_LIGHT = colors.HexColor("#f0f0f8")
_POS   = colors.HexColor("#2e7d32")
_NEG   = colors.HexColor("#c62828")
_GREY  = colors.HexColor("#cccccc")
_WHITE = colors.white


def _style(name, parent, **kw):
    s = getSampleStyleSheet()[parent]
    return ParagraphStyle(name, parent=s, **kw)


def create_pdf_report(
    df25: pd.DataFrame,
    df24: Optional[pd.DataFrame],
    period_col: str,
    period_label: str,
    currency: str,
    kpis: list[dict],
    top_variations: pd.DataFrame,
    company_name: str = "Ascent EERR Cockpit",
) -> bytes:
    """Genera el PDF y retorna bytes."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=1.5 * cm,
        rightMargin=1.5 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
    )

    styles = getSampleStyleSheet()
    title_s    = _style("T",  "Title",   fontSize=20, textColor=_DARK,  spaceAfter=4)
    sub_s      = _style("S",  "Normal",  fontSize=11, textColor=_MID,   spaceAfter=10)
    section_s  = _style("H",  "Heading2", fontSize=12, textColor=_MID,  spaceBefore=10, spaceAfter=4)
    footer_s   = _style("F",  "Normal",  fontSize=8,  textColor=colors.grey, alignment=TA_CENTER)

    elements = []

    # --------------------------------------------------------
    # Encabezado
    # --------------------------------------------------------
    elements.append(Paragraph(company_name, title_s))
    elements.append(Paragraph(f"Estado de Resultados {currency} — {period_label}", sub_s))
    elements.append(HRFlowable(width="100%", thickness=2, color=_MID))
    elements.append(Spacer(1, 0.3 * cm))

    # --------------------------------------------------------
    # KPIs
    # --------------------------------------------------------
    elements.append(Paragraph("Resumen Ejecutivo", section_s))
    kpi_rows = [["KPI", "2025", "Δ Absoluto", "Δ %"]]
    for k in kpis:
        if not k["found"]:
            continue
        v = fmt_percent(k["value_2025"]) if k["is_margin"] else fmt_currency(k["value_2025"], currency, compact=True)
        da = "–"
        dp = "–"
        if k["delta_abs"] is not None:
            if k["is_margin"]:
                da = f"{k['delta_abs']:+.1f} pp"
            else:
                da = fmt_currency(k["delta_abs"], currency, compact=True)
                da = ("+" if k["delta_abs"] >= 0 else "") + da
            if k["delta_pct"] not in (None, float("inf")):
                dp = f"{k['delta_pct']:+.1f}%"
        kpi_rows.append([k["label"], v, da, dp])

    if len(kpi_rows) > 1:
        t = Table(kpi_rows, colWidths=[5 * cm, 3.5 * cm, 3.5 * cm, 3 * cm])
        t.setStyle(TableStyle([
            ("BACKGROUND",   (0, 0), (-1, 0), _MID),
            ("TEXTCOLOR",    (0, 0), (-1, 0), _WHITE),
            ("FONTNAME",     (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE",     (0, 0), (-1, -1), 9),
            ("ALIGN",        (1, 0), (-1, -1), "RIGHT"),
            ("ALIGN",        (0, 0), (0, -1), "LEFT"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [_WHITE, _LIGHT]),
            ("GRID",         (0, 0), (-1, -1), 0.5, _GREY),
            ("TOPPADDING",   (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING",(0, 0), (-1, -1), 4),
        ]))
        elements.append(t)

    elements.append(Spacer(1, 0.4 * cm))

    # --------------------------------------------------------
    # Top variaciones
    # --------------------------------------------------------
    if top_variations is not None and not top_variations.empty:
        elements.append(Paragraph("Top Variaciones vs 2024", section_s))
        var_rows = [["Código", "Nombre", "Tag", "2025", "2024", "Δ Abs", "Δ %"]]
        for _, r in top_variations.iterrows():
            dp_str = f"{r['delta_pct']:+.1f}%" if r["delta_pct"] not in (None, float("inf")) else "N/A"
            var_rows.append([
                str(r.get("code", "")),
                str(r.get("name", ""))[:38],
                str(r.get("tag", "")),
                fmt_currency(r["v25"], currency, compact=True),
                fmt_currency(r["v24"], currency, compact=True),
                fmt_currency(r["delta_abs"], currency, compact=True),
                dp_str,
            ])
        t = Table(var_rows, colWidths=[1.5*cm, 5*cm, 2*cm, 2.5*cm, 2.5*cm, 2.5*cm, 1.5*cm])
        t.setStyle(TableStyle([
            ("BACKGROUND",   (0, 0), (-1, 0), _MID),
            ("TEXTCOLOR",    (0, 0), (-1, 0), _WHITE),
            ("FONTNAME",     (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE",     (0, 0), (-1, -1), 8),
            ("ALIGN",        (3, 0), (-1, -1), "RIGHT"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [_WHITE, _LIGHT]),
            ("GRID",         (0, 0), (-1, -1), 0.4, _GREY),
            ("TOPPADDING",   (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING",(0, 0), (-1, -1), 3),
        ]))
        elements.append(t)
        elements.append(Spacer(1, 0.4 * cm))

    # --------------------------------------------------------
    # Tabla EERR
    # --------------------------------------------------------
    elements.append(Paragraph("Estado de Resultados", section_s))
    eerr_rows = [["Código", "Nombre", "Tag", "2025", "Δ vs 2024 ($)", "Δ %"]]

    for _, row in df25.iterrows():
        v25 = float(row.get(period_col, 0) or 0)
        v24 = 0.0
        if df24 is not None and period_col in df24.columns:
            mask = (df24["code"].astype(str) == str(row.get("code", ""))) & \
                   (df24["name"] == row.get("name", ""))
            if mask.any():
                v24 = float(df24[mask][period_col].iloc[0] or 0)

        da_str = dp_str = "–"
        if v24 != 0:
            da, dp = calc_delta(v25, v24)
            da_str = fmt_currency(da, currency, compact=True)
            dp_str = f"{dp:+.1f}%" if dp not in (None, float("inf")) else "N/A"

        is_sub = bool(row.get("is_subtotal", False))
        eerr_rows.append([
            str(row.get("code", "")),
            str(row.get("name", ""))[:42],
            str(row.get("tag", "")),
            fmt_currency(v25, currency, compact=True),
            da_str,
            dp_str,
        ])

    if len(eerr_rows) > 1:
        # Determinar filas subtotales para negritas
        style_cmds = [
            ("BACKGROUND",   (0, 0), (-1, 0), _MID),
            ("TEXTCOLOR",    (0, 0), (-1, 0), _WHITE),
            ("FONTNAME",     (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE",     (0, 0), (-1, -1), 7),
            ("ALIGN",        (3, 0), (-1, -1), "RIGHT"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [_WHITE, colors.HexColor("#f8f8ff")]),
            ("GRID",         (0, 0), (-1, -1), 0.3, _GREY),
            ("TOPPADDING",   (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING",(0, 0), (-1, -1), 2),
        ]
        for data_i, (_, row) in enumerate(df25.iterrows(), start=1):
            if bool(row.get("is_subtotal", False)):
                style_cmds.append(("FONTNAME", (0, data_i), (-1, data_i), "Helvetica-Bold"))
                style_cmds.append(("BACKGROUND", (0, data_i), (-1, data_i), _LIGHT))

        t = Table(
            eerr_rows,
            colWidths=[1.5*cm, 6.5*cm, 1.8*cm, 2.8*cm, 2.8*cm, 2*cm],
        )
        t.setStyle(TableStyle(style_cmds))
        elements.append(t)

    # --------------------------------------------------------
    # Footer
    # --------------------------------------------------------
    elements.append(Spacer(1, 0.4 * cm))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=_GREY))
    elements.append(Paragraph(
        f"Generado por Ascent EERR Cockpit | {pd.Timestamp.now().strftime('%d/%m/%Y %H:%M')}",
        footer_s,
    ))

    doc.build(elements)
    return buf.getvalue()
