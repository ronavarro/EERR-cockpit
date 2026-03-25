"""
Detección heurística de jerarquía en el EERR.

Estrategias (en orden de prioridad):
  1. Match de palabras clave en el nombre (total, ebitda, resultado…)
  2. Código "redondo" divisible por 100 o 1000
  3. Valor ≈ suma de filas anteriores (dentro de ventana)

Agrega columnas 'is_subtotal' (bool) y 'level' (0=subtotal, 1=detalle).
"""

from __future__ import annotations

import re

import numpy as np
import pandas as pd

from .config import SUBTOTAL_KEYWORDS


def get_period_columns(df: pd.DataFrame) -> list[str]:
    """Retorna todas las columnas de período en orden lógico."""
    cols = [c for c in df.columns if c.startswith(("month_", "quarter_", "year_"))]
    return sorted(cols)


def detect_hierarchy(
    df: pd.DataFrame,
    period_cols: list[str],
    tolerance: float = 0.04,
) -> pd.DataFrame:
    """
    Detecta subtotales y asigna niveles jerárquicos.
    Retorna copia con columnas 'is_subtotal' y 'level'.
    """
    df = df.copy().reset_index(drop=True)
    df["is_subtotal"] = False
    df["level"] = 1  # default: detalle

    if df.empty or not period_cols:
        return df

    # --------------------------------------------------------
    # Estrategia 1: palabras clave en el nombre
    # --------------------------------------------------------
    for idx, row in df.iterrows():
        name_lower = str(row.get("name", "")).lower()
        if any(kw in name_lower for kw in SUBTOTAL_KEYWORDS):
            df.at[idx, "is_subtotal"] = True

    # --------------------------------------------------------
    # Estrategia 2: código redondo (ej: 1000, 2000, 3000)
    # --------------------------------------------------------
    for idx, row in df.iterrows():
        code = row.get("code")
        if code is None:
            continue
        try:
            code_int = int(str(code).split(".")[0])
            if code_int > 0 and (code_int % 100 == 0):
                df.at[idx, "is_subtotal"] = True
        except (ValueError, TypeError):
            pass

    # --------------------------------------------------------
    # Estrategia 3: valor ≈ suma de filas anteriores
    # (usa primera columna de período disponible como proxy)
    # --------------------------------------------------------
    ref_col = next((c for c in period_cols if c.startswith("month_")), period_cols[0])
    if ref_col in df.columns:
        vals = df[ref_col].fillna(0).astype(float).tolist()
        n = len(vals)
        for i in range(2, n):
            if df.at[i, "is_subtotal"]:
                continue
            target = abs(vals[i])
            if target < 1.0:
                continue
            for window in range(2, min(i + 1, 20)):
                window_vals = [v for v in vals[max(0, i - window) : i] if abs(v) > 0.1]
                if not window_vals:
                    continue
                ws = sum(window_vals)
                if abs(ws) > 0.1 and abs(ws - vals[i]) / target < tolerance:
                    df.at[i, "is_subtotal"] = True
                    break

    # Asignar nivel
    df.loc[df["is_subtotal"], "level"] = 0
    df.loc[~df["is_subtotal"], "level"] = 1

    return df
