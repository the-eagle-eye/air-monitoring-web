# Frontend v3 fitness — audit and fix plan

**Status:** deferred. Audit performed on 2026-07-04. To be executed after the
upcoming presentation. Legacy backend is the currently-active default.

## Context

The v3 anomaly-detection backend (`ml-service-isolation`) is fully implemented,
tested, and integrated end-to-end via the api-gateway `ML_BACKEND` feature flag.
On the frontend side, the dashboard still assumes v1 (RUL / failure_probability)
semantics. This document lists every place that must change and groups the fixes
into tiers.

## What the audit found

### Category A — Runtime crashes / broken renders
**Status: RESOLVED in the Stage 2 session.**
- `EquipoCard` no longer renders empty gaps or NaN%
- `KpiCards` "RUL Promedio" shows `n/a` instead of `0 dias`
- `HealthSemaforo` weighted score handles null RUL
- `equipos/[deviceId]` "Prediccion Actual" panel handles v3 shape
- `PrediccionesTable`, `PrediccionCard`, `dashboard-tecnico` handle null RUL

Files touched (already merged in session):
- `frontend/src/lib/api/predicciones.ts` (route through gateway)
- `frontend/src/types/prediccion.ts` (v3 optional fields + nullable legacy)
- `frontend/src/types/dashboard.ts` (`rulPromedio: number | null`)
- `frontend/src/components/dashboard/{EquipoCard,HealthSemaforo,KpiCards,PredictionTrendsChart}.tsx`
- `frontend/src/components/predicciones/{PrediccionCard,PrediccionesTable}.tsx`
- `frontend/src/app/dashboard/page.tsx`
- `frontend/src/app/dashboard-tecnico/page.tsx`
- `frontend/src/app/equipos/[deviceId]/page.tsx`

### Category B — Semantic misfits (data flows but the UI still speaks v1)

| # | Component | Problem | Proposed fix |
|---|---|---|---|
| B1 | `KpiCards` "RUL Promedio" | Always "n/a" under v3 — wasted slot | Swap the card, when v3 is detected, for "Anomalías activas" (count of predictions with `anomaly_detected=true`). Detection: check if any prediction has `anomaly_score != null && remaining_useful_life_days == null`. |
| B2 | `RiskDistributionChart` | Shows "Alta (100%)" when only 1 equipo has predictions | Compute counts against `totalEquipos`, not against equipos with predictions. Add a grey "Sin datos" slice for equipos without a prediction row. |
| B3 | `PredictionTrendsChart` RUL axis | Always null under v3 → chart line is missing | Detect v3 mode (rul all null across the series). Rebuild chart: left axis = `anomaly_score` on **log scale**, right axis = `risk_level` as discrete bands. |
| B4 | Reference lines "Crítico 30d" / "Precaución 60d" | RUL bands — not meaningful under v3 | Under v3: replace with a horizontal `ae_threshold` line (typical value ~0.4). Above threshold = shaded "alert" band. |
| B5 | `PrediccionesTable` column "RUL / Score" | Same column shows two very different quantities | Split into two columns: `RUL (v1)` and `Score (v3)`. Show a hyphen for the inapplicable side. |
| B6 | Default equipo selector = T101 | T101 has no v3 predictions → chart empty on first load | Pick default = first equipo whose `latestPredictions[device_id]` exists, fallback to first equipo. |
| B7 | HealthSemaforo score weights | Currently: alta 40, media 15, rul<30 15, incidencias 30. RUL weight is dead under v3. | Redistribute: alta 50, media 20, incidencias 30 (drop RUL weight entirely). |

### Category C — Missing v3-native fields on the UI

| # | Field | Where it belongs |
|---|---|---|
| C1 | `anomaly_detected` boolean | Equipo detail header (badge "Anomalía activa" / "Estable"). Tooltip on EquipoCard. |
| C2 | `ae_threshold` context (this station's P95 during training) | Equipo detail Resumen tab, next to the anomaly_score value. Displayed as "0.43 (umbral 0.38)". |
| C3 | `iso_forest_anomaly` confirmation flag | Debug/detail view — small icon in the "Prediccion Actual" panel. Not required for main flow. |
| C4 | `station_code` (which of 6 models served) | Equipo detail header. Also on the prediction row of `PrediccionesTable`. |
| C5 | `episode_id` grouping | Alerta detail. New "Ver otras alertas del episodio" link. |

### Category D — Framing / narrative (thesis-relevant)

| # | Missing | Where |
|---|---|---|
| D1 | Banner: "Sistema de alerta temprana basado en detección de anomalías. Anticipación 2–3 días. Especificidad ~92%. NO predice días exactos ni detecta fallas súbitas." | Top of `/dashboard` (dismissible), always visible on `/equipos/[id]` |
| D2 | Alertas caveat: "Precisión variable por estación (2%–82%). Falsos positivos son parte esperada del sistema." | Top of `/alertas` |
| D3 | Anomaly episode explorer | New page `/episodios` (list of open + closed episodes, with sample count, peak score, ops_notified) |

### Category E — Pre-existing bugs unrelated to v3

| # | Bug | Notes |
|---|---|---|
| E1 | `Tendencias de Sensores` retains stale readings when switching device with no readings | Reproducible on legacy too. Fix: reset chart data on selector change. |
| E2 | Sensor chart 3/18 timestamps sometimes leak into later views | Same root cause as E1. |

## Fix plan — tiered scope

### Tier 1: MVP fixes (~2 hours)
Delivers a v3 dashboard that no longer looks broken.
- **B1** — replace "RUL Promedio" KPI with "Anomalías activas"
- **B2** — add "Sin datos" slice to risk pie
- **B3** — rebuild `PredictionTrendsChart` for v3 (log-scale anomaly_score + threshold line)
- **B4** — v3-appropriate reference line (`ae_threshold` instead of 30/60 days)
- **B6** — smart default selector
- **B7** — HealthSemaforo scoring without RUL
- **D1** — banner explaining early-warning framing

### Tier 2: v3-native display (~1.5 hours on top of Tier 1)
Surfaces the model's own vocabulary.
- **C1** — anomaly_detected badge + tooltip
- **C2** — ae_threshold context
- **C4** — station_code on equipo detail
- **B5** — split RUL/Score columns
- **D2** — alerts caveat banner

### Tier 3: Full v3 UI (~1.5 hours on top of Tier 2)
Turns anomaly episodes into a first-class concept.
- **C3** — iso_forest_anomaly indicator
- **C5** — episode_id links on alertas
- **D3** — new `/episodios` page: episode explorer

### Tier E: Non-v3 hygiene (~30 min)
- **E1/E2** — reset sensor chart on selector change

## Detection heuristic for "v3 mode" on the client

Instead of adding a new frontend env var, detect the mode from the response
shape itself:

```ts
function isV3Prediction(p: Prediccion): boolean {
  return (
    p.anomaly_score != null || p.remaining_useful_life_days == null
  );
}
```

This works because:
- Legacy `ml-service` always returns numeric `remaining_useful_life_days`.
- v3 (via api-gateway adapter) returns `remaining_useful_life_days: null` and
  populates `anomaly_score`, `ae_threshold`, `station_code`, etc.

The dashboard can look at the first available prediction and decide which UI to
render. No global feature flag needed on the frontend side — pure data-driven
rendering.

## Migration order (recommended)

1. **Tier 1** before v3 goes to production traffic (so the demo/observers don't
   see the misleading fields).
2. **Tier 2** after v3 backfill has populated `predicciones_v3` for all equipos
   (so `station_code` and `ae_threshold` are informative).
3. **Tier 3** as a Sprint 5+ feature — episode explorer is genuinely new
   functionality, not a fix.
4. **Tier E** any time — independent of v3.

## Related
- [ML v3 validation results](ml-v3-validation.md)
- [ml-service-isolation source](../services/ml-service-isolation/)
- [api-gateway adapter](../services/api-gateway/app/services/ml_adapter.py)
