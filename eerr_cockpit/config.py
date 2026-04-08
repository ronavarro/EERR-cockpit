"""
Configuración central de Ascent EERR Cockpit.
Modifica esta sección para adaptar la app a cada cliente.
"""

# ----------------------------------------------------------------
# Mapeo de nombres de período a (tipo, número)
# tipo: 'month' | 'quarter' | 'year'
# ----------------------------------------------------------------
PERIOD_MAP: dict[str, tuple[str, int]] = {}

_MONTHS = [
    ("ene", "enero", "jan", "january"),
    ("feb", "febrero", "february"),
    ("mar", "marzo", "march"),
    ("abr", "abril", "apr", "april"),
    ("may", "mayo", "may"),
    ("jun", "junio", "june"),
    ("jul", "julio", "july"),
    ("ago", "agosto", "aug", "august"),
    ("sep", "sept", "septiembre", "sep.", "september"),
    ("oct", "octubre", "october"),
    ("nov", "noviembre", "november"),
    ("dic", "diciembre", "dec", "december"),
]
for _i, _aliases in enumerate(_MONTHS, 1):
    for _alias in _aliases:
        PERIOD_MAP[_alias] = ("month", _i)

_QUARTERS = [
    ("1 trim", "trim 1", "1° trim", "1er trim", "q1", "1t", "i trim",
     "ene-mar", "primer trimestre", "1trim", "t1"),
    ("2 trim", "trim 2", "2° trim", "2do trim", "q2", "2t", "ii trim",
     "abr-jun", "segundo trimestre", "2trim", "t2"),
    ("3 trim", "trim 3", "3° trim", "3er trim", "q3", "3t", "iii trim",
     "jul-sep", "tercer trimestre", "3trim", "t3"),
    ("4 trim", "trim 4", "4° trim", "4to trim", "q4", "4t", "iv trim",
     "oct-dic", "cuarto trimestre", "4trim", "t4"),
]
for _i, _aliases in enumerate(_QUARTERS, 1):
    for _alias in _aliases:
        PERIOD_MAP[_alias] = ("quarter", _i)

YEAR_LABELS: set[str] = {
    "año", "year", "anual", "total año", "total year", "ytd",
    "acumulado", "full year", "total anual", "total", "annual",
}

# Etiquetas de visualización en español
MONTH_LABELS_ES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun",
                   "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
QUARTER_LABELS_ES = ["1° Trim", "2° Trim", "3° Trim", "4° Trim"]

# ----------------------------------------------------------------
# Detección de columnas en el Excel
# ----------------------------------------------------------------
CODE_COL_NAMES   = ["código", "codigo", "code", "cod", "id", "cuenta", "cta", "item"]
NAME_COL_NAMES   = ["nombre", "name", "descripcion", "descripción",
                    "description", "concepto", "rubro", "línea", "linea"]
TAG_COL_NAMES    = ["tag", "tags", "categoria", "categoría", "category",
                    "tipo", "type", "grupo", "group", "rubro", "segmento"]

# ----------------------------------------------------------------
# Palabras clave → subtotales/encabezados
# ----------------------------------------------------------------
SUBTOTAL_KEYWORDS = [
    "total", "subtotal", "ebitda", "resultado", "margen",
    "utilidad", "ganancia", "pérdida", "perdida",
    "bruto", "neto", "gross", "contribucion", "contribución",
    "operativo", "financiero",
]

# ----------------------------------------------------------------
# Definición de KPIs (orden = orden de visualización)
# ----------------------------------------------------------------
KPI_DEFINITIONS: dict[str, dict] = {
    "ventas": {
        "label": "Ventas",
        "icon": "💰",
        "codes": [],
        "name_patterns": [
            "ventas netas", "total ventas", "ventas",
            "ingresos netos", "ingresos", "revenue", "sales",
        ],
        "is_margin": False,
    },
    "ebitda": {
        "label": "EBITDA",
        "icon": "📊",
        "codes": [],
        "name_patterns": ["ebitda"],
        "is_margin": False,
    },
    "ebitda_margin": {
        "label": "Margen EBITDA",
        "icon": "📈",
        "codes": [],
        "name_patterns": [
            "margen ebitda", "% ebitda", "ebitda margin",
            "margen sobre ebitda", "% ebitda s/ventas",
        ],
        "is_margin": True,
    },
    "utilidad_neta": {
        "label": "Utilidad Neta",
        "icon": "✅",
        "codes": [],
        "name_patterns": [
            "utilidad neta", "resultado neto", "ganancia neta",
            "resultado del ejercicio", "net income",
            "utilidad neta s/a",   # Guantex
        ],
        "is_margin": False,
    },
    "margen_neto": {
        "label": "Margen Neto",
        "icon": "📉",
        "codes": [],
        "name_patterns": [
            "margen neto", "% neto", "net margin",
            "margen utilidad neta", "margen sobre ventas",
        ],
        "is_margin": True,
    },
}
