"""
Cálculo de KPIs y utilidades de formato numérico.
"""

from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd

from .config import KPI_DEFINITIONS


# ----------------------------------------------------------------
# Formato numérico (separadores latinoamericanos: . miles, , decimal)
# ----------------------------------------------------------------

def _latam(val: float, decimals: int = 0) -> str:
    """Formatea número con punto como separador de miles y coma decimal."""
    fmt = f"{val:,.{decimals}f}"          # "1,234,567.89"
    # swap: , → X → . y . → ,  luego X → .
    fmt = fmt.replace(",", "X").replace(".", ",").replace("X", ".")
    return fmt


def fmt_currency(val: float, currency: str = "ARS", compact: bool = False) -> str:
    """Formatea valor monetario. compact=True usa K/M/B."""
    if pd.isna(val):
        return "–"
    symbol = "$"
    suffix = " USD" if currency == "USD" else ""
    if compact:
        if abs(val) >= 1_000_000_000:
            return f"{symbol}{_latam(val / 1_000_000_000, 1)}B{suffix}"
        if abs(val) >= 1_000_000:
            return f"{symbol}{_latam(val / 1_000_000, 1)}M{suffix}"
        if abs(val) >= 1_000:
            return f"{symbol}{_latam(val / 1_000, 1)}K{suffix}"
    return f"{symbol}{_latam(val, 0)}{suffix}"


def fmt_percent(val: float) -> str:
    if pd.isna(val):
        return "–"
    return f"{_latam(val, 1)}%"


def calc_delta(v2025: float, v2024: float) -> tuple[float, float]:
    """Retorna (delta_abs, delta_pct). delta_pct = inf si base=0."""
    d = v2025 - v2024
    pct = (d / abs(v2024) * 100) if abs(v2024) > 0.01 else (float("inf") if abs(d) > 0 else 0.0)
    return d, pct


# ----------------------------------------------------------------
# Búsqueda de línea KPI
# ----------------------------------------------------------------

def _find_row(df: pd.DataFrame, kpi_key: str, custom_codes: dict) -> Optional[pd.Series]:
    """Busca la fila KPI por código (prioridad) o patrón de nombre."""
    kpi_def = KPI_DEFINITIONS[kpi_key]

    # Código configurado por el usuario
    user_code = (custom_codes or {}).get(kpi_key)
    if user_code:
        mask = df["code"].astype(str) == str(user_code)
        if mask.any():
            return df[mask].iloc[0]

    # Códigos por defecto
    for code in kpi_def.get("codes", []):
        if code:
            mask = df["code"].astype(str) == str(code)
            if mask.any():
                return df[mask].iloc[0]

    # Búsqueda por nombre
    for pattern in kpi_def["name_patterns"]:
        mask = df["name"].str.lower().str.contains(re.escape(pattern.lower()), na=False, regex=True)
        if mask.any():
            # Preferir match exacto sobre match parcial (evita "EBITDA Ajustado" vs "EBITDA")
            exact = df["name"].str.lower() == pattern.lower()
            if exact.any():
                return df[exact].iloc[0]
            return df[mask].iloc[0]

    return None


import re  # noqa: E402 (necesario para la función anterior)


# ----------------------------------------------------------------
# Cálculo de KPIs
# ----------------------------------------------------------------

def get_kpis(
    df25: pd.DataFrame,
    df24: Optional[pd.DataFrame],
    period_col: str,
    currency: str,
    custom_codes: Optional[dict] = None,
) -> list[dict]:
    """Calcula los KPIs para el período indicado."""
    results = []
    for key, kpi_def in KPI_DEFINITIONS.items():
        row25 = _find_row(df25, key, custom_codes or {})
        row24 = _find_row(df24, key, custom_codes or {}) if df24 is not None else None

        def _get_val(row, col):
            if row is None:
                return None
            if col not in row.index:
                return None
            v = row[col]
            return float(v) if pd.notna(v) else 0.0

        v25 = _get_val(row25, period_col)
        v24 = _get_val(row24, period_col)

        d_abs = d_pct = None
        if v25 is not None and v24 is not None:
            d_abs, d_pct = calc_delta(v25, v24)

        results.append({
            "key":        key,
            "label":      kpi_def["label"],
            "icon":       kpi_def.get("icon", ""),
            "is_margin":  kpi_def["is_margin"],
            "found":      row25 is not None,
            "value_2025": v25 if v25 is not None else 0.0,
            "value_2024": v24,
            "delta_abs":  d_abs,
            "delta_pct":  d_pct,
            "currency":   currency,
        })
    return results


# ----------------------------------------------------------------
# Top variaciones
# ----------------------------------------------------------------

def get_top_variations(
    df25: pd.DataFrame,
    df24: pd.DataFrame,
    period_col: str,
    n: int = 5,
    mode: str = "all",     # 'all' | 'positive' | 'negative'
) -> pd.DataFrame:
    """Top N líneas por variación absoluta vs 2024."""
    if df24 is None or period_col not in df25.columns or period_col not in df24.columns:
        return pd.DataFrame()

    merged = pd.merge(
        df25[["code", "name", "tag", period_col]].rename(columns={period_col: "v25"}),
        df24[["code", "name", period_col]].rename(columns={period_col: "v24"}),
        on=["code", "name"],
        how="inner",
    )

    # Excluir líneas de margen/porcentaje
    merged = merged[~merged["name"].str.lower().str.contains(r"margen|%|margin", na=False, regex=True)]

    merged["delta_abs"] = merged["v25"] - merged["v24"]
    merged["delta_pct"] = merged.apply(
        lambda r: (r["delta_abs"] / abs(r["v24"]) * 100) if abs(r["v24"]) > 0.01 else 0.0,
        axis=1,
    )
    merged["_abs"] = merged["delta_abs"].abs()

    if mode == "positive":
        merged = merged[merged["delta_abs"] > 0]
    elif mode == "negative":
        merged = merged[merged["delta_abs"] < 0]

    top = merged.nlargest(n, "_abs")
    return top[["code", "name", "tag", "v25", "v24", "delta_abs", "delta_pct"]].reset_index(drop=True)
