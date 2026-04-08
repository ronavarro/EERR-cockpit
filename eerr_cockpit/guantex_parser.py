"""
Parser específico para el archivo Excel de Guantex (P y B Guantex 20XX).

Estructura esperada:
- Hojas relevantes: "GTX (20XX)", "ZB (20XX)"  (se ignoran "(C)", Cover, Master, etc.)
- Fila de encabezado: primera fila donde la columna 3 (enero) es un datetime
- Columnas fijas:
    0  → code
    1  → name
    2  → signo/tag
    3-14 → month_01..month_12
    16   → year_00
    18/20/22/24 → quarter_01..quarter_04  (columnas impares son separadores vacíos)
- Sección de % Ventas: empieza cuando col[3] vuelve a ser datetime (segunda aparición)
  → se para el parseo ahí

Retorna el mismo formato que EERRParser:
  { 'ARS': { '2025': DataFrame, '2026': DataFrame } }

Cada DataFrame incluye además la columna '_sociedad' ('GTX' o 'ZB') que permite
filtrar por sociedad en el dashboard.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Optional

import pandas as pd

from .parser import _parse_num  # reusar el parser numérico existente

# ── Patrón para hojas relevantes ─────────────────────────────────────
# Matchea: "GTX (2025)", "ZB (2026)", etc.  Excluye "GTX(C)", "ZB(C)".
_SHEET_RE = re.compile(r"^(GTX|ZB)\s*\((\d{4})\)$", re.IGNORECASE)

# ── Posiciones de columnas (0-indexed, fijas en el formato Guantex) ──
_C_CODE = 0
_C_NAME = 1
_C_SIGN = 2
_MONTH_RANGE = range(3, 15)      # cols 3-14 → meses 1-12
_C_YEAR = 16
_QUARTER_MAP: dict[int, str] = {  # col → key
    18: "quarter_01",
    20: "quarter_02",
    22: "quarter_03",
    24: "quarter_04",
}

# ── Keywords de subtotales (específicos para Guantex) ─────────────────
# Se usan substrings: un nombre es subtotal si contiene alguno de estos.
# Se excluyen keywords genéricos como "bruto" o "financiero" que matchean
# líneas de detalle como "Ingresos Brutos" o "Intereses financieros".
_SUBTOTAL_KWS: frozenset[str] = frozenset([
    "ingresos netos",
    "ganancia despues",   # "Ganancia despues de Gastos de Op." — evita "Impuesto a las ganancias"
    "ebitda",
    "ebit",
    "utilidad",
    "margen",
    "gastos operativos",
    "gastos centrales",
    "gastos de comercialización",
    "gastos de comercializacion",
    "gasto de personal",
    "gasto de operaciones",
    "otros ingresos y egresos",
    "resultado financiero",
    "resultado operativo",
    "resultado antes",
    "total",
])


def _is_subtotal(name: str) -> bool:
    n = name.lower()
    return any(kw in n for kw in _SUBTOTAL_KWS)


def is_guantex_format(source) -> bool:
    """Devuelve True si el archivo tiene hojas con formato Guantex (GTX/ZB (20XX))."""
    try:
        xl = pd.ExcelFile(source)
        return any(_SHEET_RE.match(s.strip()) for s in xl.sheet_names)
    except Exception:
        return False


class GuantexParser:
    def __init__(self) -> None:
        self.warnings: list[str] = []

    # ── Helpers internos ──────────────────────────────────────────────

    def _find_header_row(self, df_raw: pd.DataFrame) -> Optional[int]:
        """Primera fila donde col[3] es un datetime (= fila de enero)."""
        for i in range(min(20, len(df_raw))):
            if isinstance(df_raw.iloc[i, _C_SIGN + 1], datetime):  # col 3
                return i
        return None

    def _parse_sheet(
        self, df_raw: pd.DataFrame, sociedad: str, year: str
    ) -> Optional[pd.DataFrame]:
        header_row = self._find_header_row(df_raw)
        if header_row is None:
            self.warnings.append(
                f"[{sociedad} {year}] No se encontró fila de encabezado con fechas."
            )
            return None

        rows: list[dict] = []

        for i in range(header_row + 1, len(df_raw)):
            row = df_raw.iloc[i]

            # ── Detectar inicio de sección %: col[3] vuelve a ser datetime ──
            if isinstance(row.iloc[3], datetime):
                break  # fin de la sección de valores absolutos

            # ── Código ───────────────────────────────────────────────────────
            raw_code = row.iloc[_C_CODE]
            code: Optional[int | str] = None
            if pd.notna(raw_code) and str(raw_code).strip() not in ("", "nan"):
                try:
                    code = int(float(str(raw_code)))
                except (ValueError, TypeError):
                    code = str(raw_code).strip()

            # ── Nombre ───────────────────────────────────────────────────────
            raw_name = row.iloc[_C_NAME]
            name = str(raw_name).strip() if pd.notna(raw_name) else ""
            if not name:
                continue  # fila separadora sin nombre → saltar

            # ── Tag / signo ───────────────────────────────────────────────────
            raw_sign = row.iloc[_C_SIGN]
            tag = str(raw_sign).strip() if pd.notna(raw_sign) else ""

            # ── Meses ─────────────────────────────────────────────────────────
            months: dict[str, float] = {}
            for col_i, m_num in zip(_MONTH_RANGE, range(1, 13)):
                months[f"month_{m_num:02d}"] = (
                    _parse_num(row.iloc[col_i]) if col_i < len(row) else 0.0
                )

            # ── Total año ─────────────────────────────────────────────────────
            year_val = _parse_num(row.iloc[_C_YEAR]) if _C_YEAR < len(row) else 0.0

            # ── Trimestres ────────────────────────────────────────────────────
            quarters: dict[str, float] = {
                qkey: (_parse_num(row.iloc[col_i]) if col_i < len(row) else 0.0)
                for col_i, qkey in _QUARTER_MAP.items()
            }

            is_sub = _is_subtotal(name)

            rows.append({
                "code":        code,
                "name":        name,
                "tag":         tag,
                **months,
                "year_00":     year_val,
                **quarters,
                "is_subtotal": is_sub,
                "level":       0 if is_sub else 1,
                "_sociedad":   sociedad,
                "_currency":   "ARS",
                "_year":       year,
            })

        if not rows:
            self.warnings.append(
                f"[{sociedad} {year}] No se encontraron filas de datos después del encabezado."
            )
            return None

        return pd.DataFrame(rows)

    # ── API pública ───────────────────────────────────────────────────

    def load(self, source) -> dict[str, dict[str, Optional[pd.DataFrame]]]:
        """
        Parsea el archivo Guantex y retorna:
          { 'ARS': { '2025': df_concat, '2026': df_concat } }

        Cada df_concat combina GTX y ZB con la columna '_sociedad'.
        """
        self.warnings = []

        try:
            xl = pd.ExcelFile(source)
        except Exception as exc:
            raise ValueError(f"No se pudo abrir el archivo Excel: {exc}") from exc

        by_year: dict[str, list[pd.DataFrame]] = {}

        for sheet_name in xl.sheet_names:
            m = _SHEET_RE.match(sheet_name.strip())
            if not m:
                continue  # hoja ignorada (Cover, Master, GTX(C), etc.)

            sociedad = m.group(1).upper()
            year = m.group(2)

            try:
                df_raw = xl.parse(sheet_name, header=None, dtype=object)
            except Exception as exc:
                self.warnings.append(f"[{sheet_name}] Error leyendo hoja: {exc}")
                continue

            df = self._parse_sheet(df_raw, sociedad, year)
            if df is None:
                continue

            by_year.setdefault(year, []).append(df)

        if not by_year:
            raise ValueError(
                "No se encontraron hojas Guantex válidas. "
                "Verificá que el archivo tenga hojas con nombres 'GTX (20XX)' o 'ZB (20XX)'."
            )

        # Concatenar todas las sociedades para cada año
        result: dict[str, Optional[pd.DataFrame]] = {
            year: pd.concat(dfs, ignore_index=True)
            for year, dfs in by_year.items()
        }

        return {"ARS": result}
