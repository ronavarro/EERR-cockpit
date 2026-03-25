"""
Parser de Excel EERR estilo Ascent.

Detecta automáticamente:
 - Hojas por moneda (ARS / USD) y año (2024 / 2025)
 - Fila de encabezados de períodos
 - Columnas de código, nombre, tag
 - Columnas de meses, trimestres y año

Retorna:
  {
    'ARS': {'2025': DataFrame | None, '2024': DataFrame | None},
    'USD': {'2025': DataFrame | None, '2024': DataFrame | None},
  }
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Optional

import numpy as np
import pandas as pd

from .config import (
    CODE_COL_NAMES,
    NAME_COL_NAMES,
    PERIOD_MAP,
    TAG_COL_NAMES,
    YEAR_LABELS,
)

# ----------------------------------------------------------------
# Helpers de parseo numérico
# ----------------------------------------------------------------

def _parse_num(val) -> float:
    """Convierte una celda Excel a float. Maneja ARS y US formats."""
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)
    s = str(val).strip()
    if not s or s.lower() in {"-", "n/a", "na", "#n/a", "#div/0!", "#value!", "#ref!"}:
        return 0.0
    # Quitar símbolos de moneda
    s = re.sub(r"[$€£¥\s]", "", s)
    # Paréntesis → negativo
    if s.startswith("(") and s.endswith(")"):
        s = "-" + s[1:-1]
    # Detectar formato: 1.234.567,89 (latam) vs 1,234,567.89 (US)
    comma_pos = [i for i, c in enumerate(s) if c == ","]
    dot_pos   = [i for i, c in enumerate(s) if c == "."]
    if comma_pos and dot_pos:
        if comma_pos[-1] > dot_pos[-1]:   # latam: 1.234,56
            s = s.replace(".", "").replace(",", ".")
        else:                               # US: 1,234.56
            s = s.replace(",", "")
    elif len(comma_pos) > 1:              # 1,234,567
        s = s.replace(",", "")
    elif len(dot_pos) > 1:                # 1.234.567
        s = s.replace(".", "")
    try:
        return float(s)
    except ValueError:
        return 0.0


# ----------------------------------------------------------------
# Detección de hojas
# ----------------------------------------------------------------

def _detect_sheets(xl: pd.ExcelFile) -> dict[str, tuple[str, str]]:
    """
    Retorna {sheet_name: (currency, year)} donde year puede ser '2025'|'2024'|'unknown'.
    Heurística: busca 'ARS'/'USD'/'PESOS'/'DOLAR' y '2024'/'2025' en el nombre.
    """
    result: dict[str, tuple[str, str]] = {}

    for name in xl.sheet_names:
        up = name.upper()

        # Moneda
        if any(k in up for k in ("USD", "DOLAR", "DÓLARES", "US$", "U$S", "U$D")):
            currency = "USD"
        elif any(k in up for k in ("ARS", "PESOS", "PES", "$AR", "ARS$")):
            currency = "ARS"
        else:
            # Si no detecta moneda, saltear (podría ser hoja de metadatos)
            # salvo que sea la única hoja
            currency = "ARS"  # asumir ARS por defecto

        # Año
        if "2025" in up:
            year = "2025"
        elif "2024" in up:
            year = "2024"
        else:
            year = "unknown"

        result[name] = (currency, year)

    return result


def _resolve_year_unknowns(
    sheets_meta: dict[str, tuple[str, str]]
) -> dict[str, tuple[str, str]]:
    """
    Si hay hojas con año desconocido, las asigna: la primera → 2025, la segunda → 2024.
    """
    unknown = [s for s, (_, y) in sheets_meta.items() if y == "unknown"]
    if not unknown:
        return sheets_meta

    resolved = dict(sheets_meta)
    years_to_assign = ["2025", "2024"]
    for i, sheet in enumerate(unknown):
        curr = resolved[sheet][0]
        yr = years_to_assign[i] if i < len(years_to_assign) else "2025"
        resolved[sheet] = (curr, yr)
    return resolved


# ----------------------------------------------------------------
# Detección de encabezados
# ----------------------------------------------------------------

def _find_header_row(df_raw: pd.DataFrame) -> int:
    """Busca la fila donde están los encabezados de período."""
    for i in range(min(15, len(df_raw))):
        row = df_raw.iloc[i]
        str_vals = [str(v).lower().strip() for v in row if pd.notna(v)]

        period_hits = 0
        for v in str_vals:
            v_clean = re.sub(r"[°\.\(\)\-\/]", " ", v).strip()
            v_clean = re.sub(r"\s+", " ", v_clean)
            if v_clean in PERIOD_MAP:
                period_hits += 1
            elif any(yl in v_clean for yl in YEAR_LABELS):
                period_hits += 1
            elif isinstance(df_raw.iloc[i].iloc[0], datetime):
                period_hits += 1

        name_hits = sum(
            1 for v in str_vals
            if any(n in v for n in NAME_COL_NAMES + CODE_COL_NAMES)
        )
        if period_hits >= 2 or name_hits >= 1:
            return i
    return 0


def _detect_columns(
    header: pd.Series,
) -> tuple[Optional[int], Optional[int], Optional[int], dict[str, int]]:
    """
    Detecta índices de columnas de código, nombre, tag y períodos.
    Retorna (code_idx, name_idx, tag_idx, {period_key: col_idx}).
    """
    code_idx = name_idx = tag_idx = None
    period_cols: dict[str, int] = {}

    for col_i, raw_val in enumerate(header):
        if pd.isna(raw_val):
            continue

        # Si es datetime, es columna de mes
        if isinstance(raw_val, datetime):
            key = f"month_{raw_val.month:02d}"
            period_cols.setdefault(key, col_i)
            continue

        v = str(raw_val).lower().strip()
        v_clean = re.sub(r"[°\.\(\)\-\/]", " ", v).strip()
        v_clean = re.sub(r"\s+", " ", v_clean)

        # Columna de código
        if code_idx is None and any(c == v_clean or c in v_clean for c in CODE_COL_NAMES):
            code_idx = col_i
            continue

        # Columna de nombre
        if name_idx is None and any(n == v_clean or n in v_clean for n in NAME_COL_NAMES):
            name_idx = col_i
            continue

        # Columna de tag
        if tag_idx is None and any(t == v_clean or t in v_clean for t in TAG_COL_NAMES):
            tag_idx = col_i
            continue

        # Columna de período — match directo
        if v_clean in PERIOD_MAP:
            ptype, pnum = PERIOD_MAP[v_clean]
            period_cols.setdefault(f"{ptype}_{pnum:02d}", col_i)
            continue

        # Columna de período — match parcial
        matched = False
        for key_pattern, (ptype, pnum) in PERIOD_MAP.items():
            if v_clean.startswith(key_pattern) or v_clean == key_pattern[:3]:
                period_cols.setdefault(f"{ptype}_{pnum:02d}", col_i)
                matched = True
                break
        if matched:
            continue

        # Año / total
        if any(yl in v_clean for yl in YEAR_LABELS) or v_clean in {"2025", "2024", "total"}:
            period_cols.setdefault("year_00", col_i)
            continue

        # Año numérico suelto
        if re.fullmatch(r"20\d\d", v_clean):
            period_cols.setdefault("year_00", col_i)

    # Fallback: si no detectó código/nombre, usar las primeras columnas no-período
    used = set(period_cols.values())
    free = [i for i in range(len(header)) if i not in used]
    if code_idx is None and free:
        code_idx = free.pop(0)
    if name_idx is None and free:
        name_idx = free.pop(0)
    if tag_idx is None and free:
        tag_idx = free.pop(0)

    return code_idx, name_idx, tag_idx, period_cols


# ----------------------------------------------------------------
# Parser principal
# ----------------------------------------------------------------

class EERRParser:
    def __init__(self) -> None:
        self.warnings: list[str] = []

    def _parse_sheet(
        self, xl: pd.ExcelFile, sheet_name: str, currency: str, year: str
    ) -> Optional[pd.DataFrame]:
        try:
            df_raw = xl.parse(sheet_name, header=None, dtype=object)
        except Exception as exc:
            self.warnings.append(f"[{sheet_name}] No se pudo leer la hoja: {exc}")
            return None

        if df_raw.empty:
            self.warnings.append(f"[{sheet_name}] La hoja está vacía.")
            return None

        header_row_i = _find_header_row(df_raw)
        header       = df_raw.iloc[header_row_i]
        code_idx, name_idx, tag_idx, period_cols = _detect_columns(header)

        if not period_cols:
            self.warnings.append(
                f"[{sheet_name}] No se detectaron columnas de período. "
                "Verificá encabezados (Ene, Feb, … o 1 Trim, Año, etc.)."
            )
            return None

        rows: list[dict] = []
        for row_i in range(header_row_i + 1, len(df_raw)):
            row = df_raw.iloc[row_i]

            # Código
            code = None
            if code_idx is not None and code_idx < len(row):
                raw_code = row.iloc[code_idx]
                if pd.notna(raw_code) and str(raw_code).strip() not in ("", "nan"):
                    try:
                        code = int(float(str(raw_code)))
                    except (ValueError, TypeError):
                        code = str(raw_code).strip()

            # Nombre
            name = ""
            if name_idx is not None and name_idx < len(row):
                raw_name = row.iloc[name_idx]
                if pd.notna(raw_name):
                    name = str(raw_name).strip()

            if not name and code is None:
                continue  # fila vacía

            # Tag
            tag = ""
            if tag_idx is not None and tag_idx < len(row):
                raw_tag = row.iloc[tag_idx]
                if pd.notna(raw_tag):
                    tag = str(raw_tag).strip()

            # Períodos
            pv: dict[str, float] = {}
            for pk, ci in period_cols.items():
                pv[pk] = _parse_num(row.iloc[ci]) if ci < len(row) else 0.0

            rows.append({"code": code, "name": name, "tag": tag, **pv})

        if not rows:
            self.warnings.append(
                f"[{sheet_name}] No se encontraron filas de datos después del encabezado."
            )
            return None

        df = pd.DataFrame(rows)
        df["_currency"] = currency
        df["_year"]     = year
        return df

    def load(self, source) -> dict[str, dict[str, Optional[pd.DataFrame]]]:
        """
        Carga el Excel y retorna:
          { currency: { '2025': df | None, '2024': df | None } }
        """
        self.warnings = []

        try:
            xl = pd.ExcelFile(source)
        except Exception as exc:
            raise ValueError(f"No se pudo abrir el archivo Excel: {exc}") from exc

        sheets_meta = _detect_sheets(xl)
        sheets_meta = _resolve_year_unknowns(sheets_meta)

        # Estructura de resultado
        result: dict[str, dict[str, Optional[pd.DataFrame]]] = {}

        for sheet_name, (currency, year) in sheets_meta.items():
            df = self._parse_sheet(xl, sheet_name, currency, year)
            if df is None:
                continue
            if currency not in result:
                result[currency] = {"2025": None, "2024": None}
            if year in ("2025", "2024"):
                if result[currency][year] is None:
                    result[currency][year] = df
                else:
                    self.warnings.append(
                        f"[{sheet_name}] Ya existe una hoja para {currency}/{year}. Se ignora."
                    )
            else:
                # año desconocido → llenar 2025 primero, luego 2024
                for yr in ("2025", "2024"):
                    if result[currency].get(yr) is None:
                        result[currency][yr] = df
                        break

        if not result:
            raise ValueError(
                "No se pudo parsear ninguna hoja. "
                "Verificá que los nombres de hoja contengan ARS/USD y los encabezados de período."
            )

        return result
