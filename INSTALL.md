# Ascent EERR Cockpit — Instrucciones de instalación

## Requisitos

- Python 3.9 o superior
- pip3

## Instalación rápida

```bash
# 1. Clonar o descomprimir el proyecto
cd EERR-cockpit

# 2. Instalar dependencias
pip3 install -r requirements.txt

# 3. Ejecutar la app
streamlit run app.py
```

La app abre en `http://localhost:8501`.

## Generar un Excel de muestra

```bash
python3 create_sample_excel.py
# → crea eerr_sample.xlsx con 4 hojas: EERR 2025 ARS / EERR 2024 ARS / EERR 2025 USD / EERR 2024 USD
```

## Formato esperado del Excel

| Columna        | Descripción |
|----------------|-------------|
| `Código`       | Número de línea (ej: 1000, 5000). Opcional pero mejora la jerarquía. |
| `Nombre`       | Descripción de la línea EERR |
| `Tag`          | Categoría opcional (Ingresos, Gastos, KPI…) |
| `Ene`…`Dic`   | Valores mensuales |
| `1 Trim`…`4 Trim` | Trimestres (opcional) |
| `Año`          | Total anual (opcional) |

**Nombres de hoja:** deben contener `ARS` o `USD` y el año (`2025`, `2024`).

Ejemplos válidos:
- `EERR 2025 ARS`, `EERR 2024 ARS`
- `2025 USD`, `2024 USD`
- `Estado Resultados ARS 2025`

## Casos de uso implementados

| UC | Descripción | Estado |
|----|-------------|--------|
| UC-1.1 | Subir Excel (upload + path) | ✅ |
| UC-1.2 | Detección automática ARS/USD | ✅ |
| UC-1.3 | Detección de períodos (meses/trimestres/año) | ✅ |
| UC-1.4 | Lectura de códigos + nombres + tags | ✅ |
| UC-2.1 | Jerarquía heurística (keywords + código + valor) | ✅ |
| UC-2.2 | Tabla con indentación visual y subtotales en negrita | ✅ |
| UC-3.1 | Selector de moneda ARS/USD | ✅ |
| UC-3.2 | Selector de período (mes/trimestre/año) | ✅ |
| UC-3.3 | Modo YTD acumulado | ✅ |
| UC-4.1 | KPI tiles (Ventas, EBITDA, Margen EBITDA, Utilidad Neta, Margen Neto) | ✅ |
| UC-4.2 | Alertas top variaciones vs 2024 (pos/neg/todos) | ✅ |
| UC-5.1 | Dropdown buscable para seleccionar línea | ✅ |
| UC-5.2 | Gráfico mensual 2024 vs 2025 | ✅ |
| UC-5.3 | Tabla de sublíneas con contribución % | ✅ |
| UC-6.1 | Checklist de cierre con estado | ✅ |
| UC-6.2 | Registro de advertencias del parser | ✅ |
| UC-7.1 | Mapping Studio (tabla editable + import/export CSV/JSON) | ✅ |
| UC-7.2 | Cobertura de mapping % | ✅ |
| UC-8.1 | Export PDF pack mensual | ✅ |
| UC-8.2 | Export PPT | 🚧 Coming soon |

## Estructura del proyecto

```
EERR-cockpit/
├── app.py                    # App principal (streamlit run app.py)
├── create_sample_excel.py    # Generador de Excel de muestra
├── requirements.txt
├── eerr_sample.xlsx          # (generado por create_sample_excel.py)
└── eerr_cockpit/
    ├── config.py             # Constantes, KPI definitions, mapas de período
    ├── parser.py             # Lectura y detección del Excel (UC-1.x)
    ├── hierarchy.py          # Detección heurística de jerarquía (UC-2.x)
    ├── kpis.py               # Cálculo de KPIs y formato numérico (UC-4.x)
    └── pdf_export.py         # Generación de PDF con reportlab (UC-8.1)
```
