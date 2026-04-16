"""
Demo data para EERR Cockpit — Distribuidora Austral S.A.
Empresa ficticia de distribución de alimentos y bebidas, Argentina.
Datos realistas: 2024 completo + 2025 completo + 2026 Ene/Feb/Mar.
"""
from __future__ import annotations
import pandas as pd

# ── Parámetros mensuales: (ventas_M_ARS, cogs_pct, ebitda_pct, fin_pct) ──

# 2024: año de crecimiento moderado, márgenes estables 13-16%
_P24 = [
    ( 490, 0.635, 0.135, -0.028),  # Ene
    ( 452, 0.638, 0.130, -0.028),  # Feb
    ( 538, 0.632, 0.138, -0.027),  # Mar
    ( 565, 0.630, 0.142, -0.027),  # Abr
    ( 598, 0.628, 0.146, -0.027),  # May
    ( 645, 0.626, 0.150, -0.026),  # Jun
    ( 621, 0.633, 0.138, -0.028),  # Jul
    ( 668, 0.630, 0.142, -0.028),  # Ago
    ( 715, 0.625, 0.148, -0.027),  # Sep
    ( 761, 0.627, 0.147, -0.027),  # Oct
    ( 806, 0.630, 0.143, -0.029),  # Nov
    ( 905, 0.624, 0.155, -0.026),  # Dic
]

# 2025: crecimiento nominal ~73% vs 2024 (inflación + volumen), márgenes 15-19%
_P25 = [
    ( 850, 0.620, 0.160, -0.030),  # Ene
    ( 782, 0.625, 0.155, -0.031),  # Feb
    ( 926, 0.618, 0.165, -0.030),  # Mar
    ( 977, 0.615, 0.170, -0.029),  # Abr
    (1028, 0.612, 0.175, -0.029),  # May
    (1113, 0.610, 0.180, -0.028),  # Jun
    (1071, 0.618, 0.165, -0.030),  # Jul
    (1148, 0.615, 0.170, -0.030),  # Ago
    (1232, 0.608, 0.178, -0.029),  # Sep
    (1309, 0.610, 0.177, -0.029),  # Oct
    (1386, 0.613, 0.172, -0.031),  # Nov
    (1555, 0.608, 0.185, -0.028),  # Dic
]

# 2026 Q1: crecimiento nominal ~65% vs Q1 2025 (inflación + volumen)
# Presión de márgenes: COGS sube más que ventas, EBITDA margin cae a 13-14%
_P26 = [
    (1402, 0.640, 0.130, -0.040),  # Ene — +65% vs Ene 2025
    (1290, 0.645, 0.124, -0.041),  # Feb — +65% vs Feb 2025
    (1527, 0.638, 0.136, -0.039),  # Mar — +65% vs Mar 2025
]

# ── Esquema de líneas del EERR ────────────────────────────────────────
# (code, name, tag, value_key, is_subtotal, is_margin)
_SCHEMA = [
    (10,  "Ventas",                           "Ingresos",   "ventas",     True,  False),
    (11,  "Canal Distribución",               "Ingresos",   "dist",       False, False),
    (12,  "Canal Supermercados",              "Ingresos",   "superm",     False, False),
    (13,  "Exportaciones",                    "Ingresos",   "export",     False, False),
    (20,  "Costo de Ventas",                  "Costos",     "cogs",       True,  False),
    (21,  "Compras Netas",                    "Costos",     "compras",    False, False),
    (22,  "Variación de Inventarios",         "Costos",     "var_inv",    False, False),
    (23,  "Flete y Distribución",             "Costos",     "flete",      False, False),
    (30,  "Utilidad Bruta",                   "Resultado",  "util_bruta", True,  False),
    (40,  "Gastos Comerciales",               "Gastos",     "com",        True,  False),
    (41,  "Sueldos Comerciales",              "Gastos",     "sc",         False, False),
    (42,  "Comisiones sobre Ventas",          "Gastos",     "cs",         False, False),
    (43,  "Publicidad y Promoción",           "Gastos",     "pub",        False, False),
    (44,  "Gastos de Viaje y Representación", "Gastos",     "gv",         False, False),
    (50,  "Gastos de Administración",         "Gastos",     "adm",        True,  False),
    (51,  "Sueldos Administrativos",          "Gastos",     "sa",         False, False),
    (52,  "Alquileres",                       "Gastos",     "alq",        False, False),
    (53,  "Servicios y Utilities",            "Gastos",     "srv",        False, False),
    (54,  "Honorarios Profesionales",         "Gastos",     "hon",        False, False),
    (55,  "Seguros y Otros Gastos",           "Gastos",     "seg",        False, False),
    (60,  "EBITDA",                           "Resultado",  "ebitda",     True,  False),
    (61,  "Depreciaciones y Amortizaciones",  "Gastos",     "da",         False, False),
    (70,  "Resultado Operativo",              "Resultado",  "ebit",       True,  False),
    (80,  "Resultado Financiero",             "Financiero", "fin",        True,  False),
    (81,  "Ingresos Financieros",             "Financiero", "ing_fin",    False, False),
    (82,  "Gastos Financieros",               "Financiero", "gst_fin",    False, False),
    (83,  "Resultado por Tipo de Cambio",     "Financiero", "tcambio",    False, False),
    (90,  "Resultado antes de Impuestos",     "Resultado",  "ebt",        True,  False),
    (91,  "Impuesto a las Ganancias",         "Impuestos",  "tax",        False, False),
    (100, "Utilidad Neta",                    "Resultado",  "net",        True,  False),
    (101, "Margen EBITDA",                    "Margen",     "ebm",        True,  True),
    (102, "Margen Neto",                      "Margen",     "nm",         True,  True),
]


def _compute(v: float, cogs_p: float, ebitda_p: float, fin_p: float) -> dict:
    """Calcula todos los valores del EERR para un mes dado. v en millones de ARS."""
    v = int(v) * 1_000_000

    # Ingresos
    dist   = round(v * 0.600)
    superm = round(v * 0.330)
    export = v - dist - superm          # residual → suma exacta = ventas

    # Costo de Ventas
    cogs    = round(v * cogs_p)
    compras = round(cogs * 0.840)
    var_inv = round(cogs * 0.050)
    flete   = cogs - compras - var_inv  # residual → suma exacta = cogs

    util_bruta = v - cogs

    # EBITDA exacto según parámetro
    ebitda = round(v * ebitda_p)

    # Gastos operativos = Utilidad Bruta - EBITDA  (split 45% com / 55% adm)
    gop = util_bruta - ebitda
    com = round(gop * 0.45)
    adm = gop - com

    # Desglose comercial
    sc  = round(com * 0.45)
    cs  = round(com * 0.30)
    pub = round(com * 0.15)
    gv  = com - sc - cs - pub

    # Desglose administrativo
    sa  = round(adm * 0.50)
    alq = round(adm * 0.20)
    srv = round(adm * 0.14)
    hon = round(adm * 0.10)
    seg = adm - sa - alq - srv - hon

    # D&A y EBIT
    da   = round(v * 0.020)
    ebit = ebitda - da

    # Resultado Financiero (negativo en Argentina: intereses + FX)
    fin     = round(v * fin_p)           # ej. -26 — negativo
    ing_fin = round(v * 0.010)           # +9  — ingresos por colocaciones
    gst_fin = -round(v * 0.028)          # -24 — intereses bancarios (negativo)
    tcambio = fin - ing_fin - gst_fin    # residual, negativo (pérdida FX)

    # EBT, Impuesto, Utilidad Neta
    ebt = ebit + fin
    tax = round(ebt * 0.35) if ebt > 0 else 0
    net = ebt - tax

    # Márgenes (en %)
    ebm = round(ebitda / v * 100, 1)
    nm  = round(net    / v * 100, 1)

    return {
        "ventas": v, "dist": dist, "superm": superm, "export": export,
        "cogs": cogs, "compras": compras, "var_inv": var_inv, "flete": flete,
        "util_bruta": util_bruta,
        "com": com, "sc": sc, "cs": cs, "pub": pub, "gv": gv,
        "adm": adm, "sa": sa, "alq": alq, "srv": srv, "hon": hon, "seg": seg,
        "ebitda": ebitda, "da": da, "ebit": ebit,
        "fin": fin, "ing_fin": ing_fin, "gst_fin": gst_fin, "tcambio": tcambio,
        "ebt": ebt, "tax": tax, "net": net,
        "ebm": ebm, "nm": nm,
    }


def _build_df(params: list[tuple], year: str) -> pd.DataFrame:
    """Construye el DataFrame del EERR a partir de los parámetros mensuales."""
    months_data = [_compute(*p) for p in params]
    n = len(months_data)

    rows = []
    for code, name, tag, key, is_sub, is_margin in _SCHEMA:
        monthly_12 = [float(m[key]) for m in months_data] + [0.0] * (12 - n)

        if is_margin:
            # Márgenes: % ponderado por ventas para quarters y año
            ventas_12 = [float(m["ventas"]) for m in months_data] + [0.0] * (12 - n)
            num_key   = "ebitda" if key == "ebm" else "net"
            num_12    = [float(m[num_key]) for m in months_data] + [0.0] * (12 - n)

            def _wmean(sl_n, sl_d):
                d = sum(sl_d)
                return round(sum(sl_n) / d * 100, 1) if d else 0.0

            quarters = [
                _wmean(num_12[0:3],  ventas_12[0:3]),
                _wmean(num_12[3:6],  ventas_12[3:6]),
                _wmean(num_12[6:9],  ventas_12[6:9]),
                _wmean(num_12[9:12], ventas_12[9:12]),
            ]
            year_val = _wmean(num_12, ventas_12)
        else:
            quarters = [
                sum(monthly_12[0:3]),
                sum(monthly_12[3:6]),
                sum(monthly_12[6:9]),
                sum(monthly_12[9:12]),
            ]
            year_val = sum(monthly_12)

        row: dict = {
            "code":       code,
            "name":       name,
            "tag":        tag,
            "is_subtotal": is_sub,
            "level":      0 if is_sub else 1,
        }
        for i, val in enumerate(monthly_12, 1):
            row[f"month_{i:02d}"] = val
        for i, q in enumerate(quarters, 1):
            row[f"quarter_0{i}"] = float(q)
        row["year_00"] = float(year_val)
        rows.append(row)

    return pd.DataFrame(rows)


def get_demo_raw_2025() -> dict:
    """
    EERR 2025 completo con 2024 como año de comparación.
      { 'ARS': { '2024': df_2024_full, '2025': df_2025_full } }
    """
    df24 = _build_df(_P24, "2024")
    df25 = _build_df(_P25, "2025")
    return {"ARS": {"2024": df24, "2025": df25}}


def get_demo_raw_2026(months: int) -> dict:
    """
    EERR 2026 acumulado (n meses) con 2025 completo como comparación.
      { 'ARS': { '2025': df_2025_full, '2026': df_2026_n_months } }
    """
    df25 = _build_df(_P25, "2025")
    df26 = _build_df(_P26[:months], "2026")
    return {"ARS": {"2025": df25, "2026": df26}}


def ensure_demo_data(storage_module, demo_user: str = "demo") -> None:
    """
    Crea los uploads demo si no existen. Idempotente.

    Uploads generados:
      - Diciembre 2025 → 2025 completo vs 2024 completo
      - Enero 2026     → 2026 Ene vs 2025 completo
      - Febrero 2026   → 2026 Ene+Feb vs 2025 completo
      - Marzo 2026     → 2026 Ene+Feb+Mar vs 2025 completo
    """
    existing = {(u["year"], u["month"]) for u in storage_module.list_uploads(demo_user)}

    if (2025, 12) not in existing:
        storage_module.save_upload(demo_user, 2025, 12, get_demo_raw_2025())

    for month, n_months in [(1, 1), (2, 2), (3, 3)]:
        if (2026, month) not in existing:
            storage_module.save_upload(demo_user, 2026, month, get_demo_raw_2026(n_months))
