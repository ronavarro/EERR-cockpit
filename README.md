---
title: Ascent EERR Cockpit
emoji: 📊
colorFrom: blue
colorTo: indigo
sdk: streamlit
sdk_version: 1.45.0
app_file: app.py
pinned: true
---

# Ascent EERR Cockpit

Dashboard ejecutivo para análisis de Estados de Resultados (EERR), desarrollado por **Ascent Advisors**.

## Demo

**Usuario:** `demo`  
**Contraseña:** `demo123`

Los datos de demo corresponden a *Distribuidora Austral S.A.*, una empresa ficticia con:
- **2025 completo** (12 meses) — año de referencia
- **2026 Ene / Feb / Mar** — año en curso con comparativo

## Funcionalidades

- KPIs ejecutivos (Ventas, EBITDA, Margen, Utilidad Neta) con variación vs año anterior
- Gráficos comparativos y waterfall
- Top variaciones por línea
- Tabla EERR completa con drilldown por línea
- Análisis mensual, trimestral y YTD
- Analista IA conversacional (requiere GROQ_API_KEY)
- Exportación PDF
- Carga de archivos EERR propios (formatos genérico y Guantex)

## Configuración (para el Analista IA)

Agregar en **Settings → Repository secrets**:

```
GROQ_API_KEY = gsk_...
```

Obtené tu key gratuita en [console.groq.com](https://console.groq.com).
