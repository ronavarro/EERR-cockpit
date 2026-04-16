"""
Demo data para EERR Cockpit — Distribuidora Austral S.A.
Empresa ficticia de distribución de alimentos y bebidas, Argentina.
Datos realistas: 2025 completo + 2026 Ene/Feb/Mar.
"""
from __future__ import annotations
import pandas as pd

# ── Parámetros mensuales: (ventas_M_ARS, cogs_pct, ebitda_pct, fin_pct) ──
# 2025: crecimiento sostenido a lo largo del año, márgenes sólidos 15-19%
_P25 = [
    ( 850, 0.620, 0.160, -0.030),  # Ene — arranque del año
    ( 782, 0.625, 0.155, -0.031),  # Feb — mes corto, margen algo menor
    ( 926, 0.618, 0.165, -0.030),  # Mar — recuperación
    ( 977, 0.615, 0.170, -0.029),  # Abr — buena temporada
    (1028, 0.612, 0.175, -0.029),  # May — acelerando
    (1113, 0.610, 0.180, -0.028),  # Jun — pico H1
    (1071, 0.618, 0.165, -0.030),  # Jul — pausa estacional
    (1148, 0.615, 0.170, -0.030),  # Ago — retoma
    (1232, 0.608, 0.178, -0.029),  # Sep — fuerte
    (1309, 0.610, 0.177, -0.029),  # Oct — pre-temporada alta
    (1386, 0.613, 0.172, -0.031),  # Nov — Black Friday
    (1555, 0.608, 0.185, -0.028),  # Dic — mejor mes del año
]

# 2026 Q1: crecimiento nominal ~65% vs Q1 2025 (inflación + volumen)
# Presión de márgenes: COGS sube más que ventas, EBITDA margin cae a 13-14%
_P26 = [
    (1402, 0.640, 0.130, -0.040),  # Ene 2026 — +65% vs Ene 2025
    (1290, 0.645, 0.124, -0.041),  # Feb 2026 — +65% vs Feb 2025
    (1527, 0.638, 0.136, -0.039),  # Mar 2026 — +65% vs Mar 2025
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
    """Calcula todos los valores del EERR para un mes dado."""
    v = int(v)

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


def get_demo_raw(months_2026: int = 3) -> dict:
    """
    Retorna el dict raw listo para pasar a storage.save_upload():
      { 'ARS': { '2025': df_full, '2026': df_with_n_months } }
    """
    df25 = _build_df(_P25, "2025")
    df26 = _build_df(_P26[:months_2026], "2026")
    return {"ARS": {"2025": df25, "2026": df26}}


def ensure_demo_data(storage_module, demo_user: str = "demo") -> None:
    """
    Crea los uploads demo para el usuario 'demo' si no existen.
    Se llama al inicio de la app — es idempotente.
    """
    existing = {(u["year"], u["month"]) for u in storage_module.list_uploads(demo_user)}
    for year, month, n_months in [(2026, 1, 1), (2026, 2, 2), (2026, 3, 3)]:
        if (year, month) not in existing:
            storage_module.save_upload(demo_user, year, month, get_demo_raw(n_months))
