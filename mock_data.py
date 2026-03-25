"""
Datos mock para demo Ascent EERR Cockpit.
Genera DataFrames realistas de una distribuidora argentina (ARS y USD, 2024 y 2025).
"""
from __future__ import annotations
import pandas as pd
import numpy as np

# ── Definición del EERR ──────────────────────────────────────────
LINES = [
    # (código, nombre, tag, es_subtotal)
    (1000,  "Ventas Netas",                    "Ingresos",   True),
    (1100,  "Ventas Línea Autopartes",          "Ingresos",   False),
    (1200,  "Ventas Línea Lubricantes",         "Ingresos",   False),
    (1300,  "Ventas Línea Neumáticos",          "Ingresos",   False),
    (2000,  "Costo de Mercadería Vendida",      "Costos",     True),
    (2100,  "Costo Autopartes",                 "Costos",     False),
    (2200,  "Costo Lubricantes",                "Costos",     False),
    (2300,  "Costo Neumáticos",                 "Costos",     False),
    (3000,  "Utilidad Bruta",                   "KPI",        True),
    (4000,  "Gastos Operativos",                "Gastos",     True),
    (4100,  "Sueldos y Cargas Sociales",        "Gastos",     False),
    (4200,  "Alquileres",                       "Gastos",     False),
    (4300,  "Servicios y Utilities",            "Gastos",     False),
    (4400,  "Publicidad y Marketing",           "Gastos",     False),
    (4500,  "Logística y Distribución",         "Gastos",     False),
    (5000,  "EBITDA",                           "KPI",        True),
    (5001,  "Margen EBITDA %",                  "KPI",        False),
    (6000,  "Depreciaciones y Amortizaciones",  "Gastos",     False),
    (7000,  "Resultado Operativo (EBIT)",        "KPI",        True),
    (8000,  "Resultado Financiero",             "Financiero", True),
    (8100,  "Intereses Bancarios",              "Financiero", False),
    (8200,  "Diferencias de Cambio",            "Financiero", False),
    (9000,  "Resultado antes de Impuestos",     "KPI",        True),
    (9100,  "Impuesto a las Ganancias",         "Impuestos",  False),
    (10000, "Utilidad Neta",                    "KPI",        True),
    (10001, "Margen Neto %",                    "KPI",        False),
]

MONTHS = ["Ene","Feb","Mar","Abr","May","Jun","Jul","Ago","Sep","Oct","Nov","Dic"]
FX = {"2025": 1_050, "2024": 820}   # ARS por USD

# ── Ventas mensuales base (ARS, M) ──────────────────────────────
_VENTAS_2025 = [280,295,320,345,362,378,395,412,435,458,475,498]   # total ~4,453M
_VENTAS_2024 = [190,198,210,221,231,242,254,265,278,291,303,317]   # total ~3,000M

def _build_year(year: str) -> dict[int, list[float]]:
    base  = _VENTAS_2025 if year == "2025" else _VENTAS_2024
    np.random.seed({"2025":42,"2024":7}[year])
    noise = lambda v, s=0.02: [x*(1+np.random.uniform(-s,s)) for x in v]

    ventas = [v*1e6 for v in noise(base)]
    a  = [v*0.52 for v in ventas]   # Autopartes  52%
    b  = [v*0.27 for v in ventas]   # Lubricantes 27%
    c  = [v*0.21 for v in ventas]   # Neumáticos  21%

    costo_pct = 0.38 if year=="2025" else 0.41
    ca,cb,cc = [-x*costo_pct for x in a],[-x*costo_pct for x in b],[-x*costo_pct for x in c]
    cmv = [ca[i]+cb[i]+cc[i] for i in range(12)]
    ub  = [ventas[i]+cmv[i] for i in range(12)]

    sue = [-v*0.14 for v in ventas]
    alq = [-v*0.055 for v in ventas]
    srv = [-v*0.035 for v in ventas]
    pub = [-v*0.032 for v in ventas]
    log = [-v*0.038 for v in ventas]
    go  = [sue[i]+alq[i]+srv[i]+pub[i]+log[i] for i in range(12)]

    ebitda = [ub[i]+go[i] for i in range(12)]
    m_ebitda = [ebitda[i]/ventas[i]*100 for i in range(12)]

    depre = [-v*0.025 for v in ventas]
    ebit  = [ebitda[i]+depre[i] for i in range(12)]

    int_  = [-v*0.035 for v in ventas]
    fx_   = [-v*0.012 for v in ventas]
    rfin  = [int_[i]+fx_[i] for i in range(12)]

    eai   = [ebit[i]+rfin[i] for i in range(12)]
    imp   = [x*-0.35 if x>0 else 0 for x in eai]
    un    = [eai[i]+imp[i] for i in range(12)]
    m_net = [un[i]/ventas[i]*100 for i in range(12)]

    return {
        1000:ventas, 1100:a,    1200:b,    1300:c,
        2000:cmv,    2100:ca,   2200:cb,   2300:cc,
        3000:ub,
        4000:go,     4100:sue,  4200:alq,  4300:srv, 4400:pub, 4500:log,
        5000:ebitda, 5001:m_ebitda,
        6000:depre,
        7000:ebit,
        8000:rfin,   8100:int_, 8200:fx_,
        9000:eai,
        9100:imp,
        10000:un,    10001:m_net,
    }


def _make_df(year: str, currency: str) -> pd.DataFrame:
    monthly = _build_year(year)
    fx = FX[year]
    rows = []
    for code, name, tag, is_sub in LINES:
        vals = [v/fx if currency=="USD" else v for v in monthly[code]]
        q1,q2,q3,q4 = sum(vals[:3]),sum(vals[3:6]),sum(vals[6:9]),sum(vals[9:])
        row = {"code":code,"name":name,"tag":tag,"is_subtotal":is_sub,"level":0 if is_sub else 1}
        for i,m in enumerate(MONTHS):
            row[m] = round(vals[i],2)
        row.update({"1 Trim":round(q1,2),"2 Trim":round(q2,2),
                    "3 Trim":round(q3,2),"4 Trim":round(q4,2),
                    "Año":round(sum(vals),2)})
        rows.append(row)
    return pd.DataFrame(rows)


def get_mock_data() -> dict:
    """Retorna {currency: {'2025': df, '2024': df}}"""
    return {
        "ARS": {"2025": _make_df("2025","ARS"), "2024": _make_df("2024","ARS")},
        "USD": {"2025": _make_df("2025","USD"), "2024": _make_df("2024","USD")},
    }
