# Plan de implementación: C1 → C6 → C4 → C5

**Objetivo:** llevar el monitor de salud a operación real y auto-sostenible.
**Documentos asociados:** `docs/BACKLOG_POST_MVP.md`, `docs/spec-transmision-y-reentrenamiento.md`
**Versión:** 1.1 — ✅ TODAS LAS FASES IMPLEMENTADAS Y VERIFICADAS (2026-07-04)

## Estado final
- **C1** ✅ ingesta IoT dispara el ensemble (ensemble_notify_service, 12 tests, E2E)
- **C6** ✅ métricas del modelo (model_metrics/ml_005, metrics_service, 7 tests, E2E)
- **C4** ✅ recalibración θ desde BD (theta_service, invalidación cache, 9 tests, E2E)
- **C5** ✅ reentrenamiento por degradación (retrain_service, 11 tests, E2E)
- Scheduler unificado: watchdog(5min) + métricas(24h) + θ(mensual) + degradación(diario)
- Regresión: 316 backend + 40 e2e = 356 tests en verde.

## Decisiones de diseño
- **C1 disparo:** iot-service hace `POST` fire-and-forget a `ml-service /health-monitor/evaluate` tras guardar la lectura (patrón existente ml→ops). Mapea claves JSONB → features del ensemble.
- **Fuente de datos C4/C6:** `health_readings` en BD (fuente viva), no el joblib offline.

## Mapeo de claves (payload IoT JSONB → features ensemble)
| Feature ensemble | Clave payload IoT |
|---|---|
| `so2_ppb` | `SO2_ppb` |
| `so2_flow` | `SampleFlow` |
| `so2_lamp_int` | `UVLampIntensity` |
| `so2_internal_temp` | `Reaction_Temp` |

`valido`: derivado del payload (si las 4 features están presentes y son numéricas → 1, si no → 0).

---

## FASE C1 — Ingesta IoT dispara el ensemble

### Implementación
- [ ] **C1.1** `iot-service`: función `_map_to_ensemble_features(sensors: dict)` que extrae y mapea las 4 claves JSONB → dict del ensemble; determina `valido`.
- [ ] **C1.2** `iot-service`: `_notify_ensemble(device_id, timestamp, features, valido)` — `httpx.post` fire-and-forget a `ML_SERVICE_URL/api/v1/health-monitor/evaluate`, con `try/except` (un fallo NO rompe la ingesta). Env `ML_SERVICE_URL` ya existe.
- [ ] **C1.3** Llamar `_notify_ensemble` desde `validate_and_store_reading` (o desde la ruta) tras el commit de la lectura. Flag `ENSEMBLE_NOTIFY_ENABLED` (default on; off en tests) para no acoplar tests de ingesta a la red.
- [ ] **C1.4** Mapear el `timestamp_lectura` (UTC) al formato ISO que espera `HealthEvaluateRequest`.

### Tests
- [ ] **C1.T1** Unit `_map_to_ensemble_features`: mapea claves correctas; `valido=0` si falta alguna; tolera claves ausentes/no numéricas.
- [ ] **C1.T2** Unit `_notify_ensemble`: mockea `httpx.post`, verifica payload correcto; verifica que un error de red NO propaga (ingesta sobrevive).
- [ ] **C1.T3** Integración ruta `/readings`: con flag on + httpx mockeado, una lectura dispara 1 POST al ensemble con el payload mapeado.
- [ ] **C1.T4** Regresión: los tests de ingesta existentes siguen verdes (flag off por defecto en tests, sin llamadas de red).

---

## FASE C6 — Métricas de monitoreo del modelo persistidas

### Implementación
- [ ] **C6.1** `ml-service`: modelo `ModelMetric` (tabla `model_metrics`): `station_id`, `window_start`, `window_end`, `alert_rate`, `total_readings`, `anomaly_readings`, `theta`, `created_at`.
- [ ] **C6.2** Migración `ml_005_create_model_metrics`.
- [ ] **C6.3** `metrics_service.compute_and_store_metrics(db, now)`: por estación, agrega `health_readings` de la ventana (p.ej. 24h): tasa de alerta = anomaly/total, cuenta lecturas, θ vigente. Persiste una fila por estación/ventana.
- [ ] **C6.4** Endpoint `GET /health-monitor/metrics` (serie por estación) para dashboard/diagnóstico + `POST /health-monitor/run-metrics` (on-demand).
- [ ] **C6.5** Enganchar `compute_and_store_metrics` al scheduler (diario). Env `METRICS_ENABLED`.

### Tests
- [ ] **C6.T1** Unit `compute_and_store_metrics`: con health_readings sembradas, calcula alert_rate correcto por estación e independencia por estación.
- [ ] **C6.T2** Unit ventana: solo cuenta lecturas dentro de la ventana.
- [ ] **C6.T3** Endpoint metrics: 200 + estructura correcta.
- [ ] **C6.T4** Regresión suites.

---

## FASE C4 — Recalibración automática de θ (mensual)

### Implementación
- [ ] **C4.1** `theta_service.recalibrate_theta(db, station_id, window_days=14)`: lee `health_readings` recientes (SANO / no-anómalas) de la estación, calcula `θ = P95(recon_error)`, actualiza `theta_<sid>.json` conservando `theta_train` (trazabilidad). Basado en la lógica de `09_recalibrate_theta.py` pero **desde BD**.
- [ ] **C4.2** `EnsembleRegistry.invalidate(station_id)` / `reload(station_id)`: limpiar cache para que el θ nuevo surta efecto sin reiniciar el servicio.
- [ ] **C4.3** `recalibrate_all(db)`: itera estaciones con modelo; recalibra y logra resumen. Guardas: no recalibrar si hay < N lecturas normales (evita θ espurio).
- [ ] **C4.4** Endpoint `POST /health-monitor/recalibrate-theta` (on-demand) + enganche mensual al scheduler. Env `THETA_RECAL_ENABLED`.
- [ ] **C4.5** Registrar el evento de recalibración (opcional: fila en model_metrics o log estructurado) para auditoría ISO 17025.

### Tests
- [ ] **C4.T1** Unit `recalibrate_theta`: con readings sembradas, θ = P95 esperado; conserva `theta_train`; idempotente en re-runs.
- [ ] **C4.T2** Unit guarda: no recalibra si hay pocas lecturas normales.
- [ ] **C4.T3** Unit `registry.invalidate`: tras recalibrar, `get()` devuelve el θ nuevo.
- [ ] **C4.T4** Endpoint recalibrate: 200 + resumen.
- [ ] **C4.T5** Regresión suites.

---

## FASE C5 — Reentrenamiento completo del ensemble (trimestral / por degradación)

> Fase más pesada. El reentrenamiento en sí reusa el pipeline existente
> (`01_build_dataset`, `02_train_autoencoder`, `03_train_iforest`), que corre
> dentro del contenedor con numpy 1.26 (lección P6). Aquí se agrega el **disparo**
> y el **criterio de degradación**, no se reescribe el entrenamiento.

### Implementación
- [ ] **C5.1** `retrain_service.should_retrain(db, station_id)`: evalúa criterios de degradación (spec §2.3) usando `model_metrics`: tasa de alerta > 3× base sostenida ≥ 7 días; θ recalibrado fuera de [0.5×, 2×] del θ_train; (especificidad si hay holdout). Devuelve (bool, razón).
- [ ] **C5.2** `retrain_service.retrain_station(station_id, window_months=3..6)`: orquesta el pipeline de entrenamiento desde `health_readings`/dataset de la estación, versiona artefactos, compara especificidad nueva vs anterior sobre holdout; si empeora, conserva el anterior (spec CR-04). Actualiza `model_version`.
- [ ] **C5.2b** Decidir ejecución: el entrenamiento pesado corre como job batch (no en request-path). Puede ser un endpoint `POST /health-monitor/retrain` que lanza el proceso, o un script disparado por el scheduler trimestral.
- [ ] **C5.3** Enganche trimestral + por-degradación al scheduler (chequea `should_retrain` a diario; entrena si aplica). Env `RETRAIN_ENABLED` (default off — es costoso, opt-in explícito).
- [ ] **C5.4** Tras reentrenar, `registry.invalidate(station_id)`.

### Tests
- [ ] **C5.T1** Unit `should_retrain`: cada criterio de degradación dispara/no-dispara con métricas sembradas.
- [ ] **C5.T2** Unit "no degrada producción": si el modelo nuevo empeora especificidad, se conserva el anterior.
- [ ] **C5.T3** Unit versionado: `model_version` cambia tras reentrenar OK.
- [ ] **C5.T4** Regresión suites.

---

## Estrategia transversal de testing (aplica a TODAS las fases)
1. **Antes de cada fase:** correr la suite del servicio afectado para tener baseline verde.
2. **Después de cada cambio:** correr la suite afectada; no avanzar con rojos.
3. **Flags de entorno** (`*_ENABLED`) apagados en tests para no acoplar a red/scheduler.
4. **Al cerrar cada fase:** regresión completa (ml + ops + iot + gateway + e2e) en verde.
5. **Coverage:** cada función nueva con al menos un test de camino feliz + un borde (error/vacío/fuera de ventana).

## Orden de ejecución
C1 (habilita datos reales) → C6 (métricas, prerequisito de C5) → C4 (θ, barato) → C5 (reentrenamiento, depende de C6).
