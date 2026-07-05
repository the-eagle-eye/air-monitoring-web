# IMPLEMENTATION PLAN — Monitor de Salud No Supervisado (Ensemble AE + IF + AND)

**Documento de especificación asociado:** `docs/spec-health-monitor-unsupervised.md`
**Dataset base:** `CA-ILO-01` (Bolognesi-Ilo)
**Versión:** 1.0 — plan para aprobación previa a implementación

> **Regla de proceso (heredada del repo):** este plan **no se implementa** hasta aprobación explícita. No se sobrescriben artefactos de producción (`ml_artifacts*`); todo lo nuevo lleva sufijo `_ensemble_v1`. Ver §7 (rollback).

---

## 1. Confirmación de alcance

- **Dataset base:** `CA-ILO-01` (`services/ml-proposal/dataset/CA-ILO-01_BOLOGNESI_DATASET.csv`, ~148 k filas a 5 min).
- **Estaciones para validación cruzada:** 5 adicionales en `services/ml-proposal/dataset/` — `CA-CH-04` (Grau), `CA-CH-05` (Garcilaso), `CA-CHILLO-01` (Chillón), `CA-CC-01` (Oroya), `CA-UCHU-01` (Uchucarcco). Ver SPEC §9.1.
- **Variables del ensemble:** `SO2_PPB`, `SO2_FLOW`, `SO2_INTERNAL_TEMP`, `SO2_LAMP_INT`, `hours_since_prev` (+ 1 reservada; candidatas por-estación: `SO2_PMT_VOLTAGE`, `SO2_BENCH_TEMP/PRESS`, `SO2_CONV_TEMP`).
- **Flag de transmisión:** `valido` (0/1) en estos CSV — **no** `SO2_ESTADO`. El gate §3.0 y la definición de FALLA (§4.1) se re-mapean a la transición `valido` `1 → 0`.
- **Target de entrenamiento:** ninguno supervisado — se entrena **solo con operación normal**.
- **Feature clave:** `hours_since_prev` reemplaza a `rul_days` (que **sí viene en los CSV** pero se descarta por *data leakage*; ver SPEC §4.2).
- **Entregables:** modelos entrenados + validación multi-estación (leave-one-station-out) + endpoint de inferencia + documento de diseño de dashboard (no código de UI en esta fase).

---

## 2. Fases de implementación

### Fase 0 — Backup y preparación (bloqueante)

| # | Tarea | Detalle |
|---|---|---|
| 0.1 | Backup de artefactos ML | `cp -R services/ml-service/ml_artifacts* services/ml-service/ml_artifacts_backup_pre_ensemble_<TS>/` |
| 0.2 | Snapshot git | `git rev-parse HEAD` + `git stash push -u` si hay cambios sin commitear |
| 0.3 | Verificar dependencias | **Ninguna nueva** — el AE usa `sklearn.neural_network.MLPRegressor` (scikit-learn ya está en `requirements.txt`). Confirmar versión de sklearn instalada |
| 0.4 | Confirmar datasets | Validar que las 6 estaciones cargan (`services/ml-proposal/dataset/*.csv`); registrar filas, rango de fechas y columnas presentes por estación |

**Salida:** backup verificado, entorno reproducible (`RANDOM_SEED = 42`).

### Fase 1 — Dataset y features (offline)

| # | Tarea | Archivo |
|---|---|---|
| 1.1 | Cargador multi-estación: leer los 6 CSV (delimitador `,`), añadir `station_id`, parsear `date`, dedup por timestamp | `scripts/ensemble/01_build_dataset.py` |
| 1.2 | **Descartar `rul_days`** (leakage) de las features; conservar `ciclo_id`/`valido` como metadatos | idem |
| 1.3 | Máscara `is_normal` = `valido = 1` ∧ variables base dentro de L2–L3 | idem |
| 1.4 | Cálculo offline de `hours_since_prev` a partir de transiciones de `valido` (SPEC §4.3) | idem |
| 1.5 | Selección de features: 4 base comunes + `hours_since_prev` (+ extras por-estación si aplica) | idem |
| 1.6 | `StandardScaler` ajustado **solo con rows normales** — **por estación** (cada analizador tiene su propio nivel de ruido); persistir uno por estación | `scaler_<station>.pkl` |
| 1.7 | Split temporal por estación (nunca aleatorio, nunca mezclar estaciones en un mismo split) | idem |

**Salida:** `hm_ensemble_dataset.parquet` (con `station_id`), `scaler_<station>.pkl`.
**Verificación:** distribución de estados por estación, % rows normales, cero leakage (scaler no ve el test; `rul_days` no está entre las features).

### Fase 2 — Entrenar el ensemble (offline)

| # | Tarea | Archivo | Salida |
|---|---|---|---|
| 2.1 | Autoencoder `5→3→5` vía `MLPRegressor(hidden_layer_sizes=(3,))` reconstruyendo `X→X`, entrenar solo-normal, pérdida MSE | `scripts/ensemble/02_train_autoencoder.py` | `autoencoder_ensemble_v1.pkl` (joblib) |
| 2.2 | Calcular θ = P95 del `recon_error` sobre train-normal, **por estación** (θ configurable) | idem | `theta_<station>.json` |
| 2.3 | Isolation Forest `contamination` configurable (default 0.05), `n_estimators=200`, seed 42 | `scripts/ensemble/03_train_iforest.py` | `iforest_ensemble_v1.pkl` |
| 2.4 | Ensamblar lógica AND + graduación (θ, 2θ, 3θ); `contamination` y θ leídos de config | `scripts/ensemble/04_ensemble.py` | módulo compartido |

**Verificación:** el AE reconstruye rows normales con error bajo; θ separa razonablemente; IF marca ~5 %.
**Nota AE con MLPRegressor:** un `MLPRegressor` con una capa oculta de 3 neuronas y `X` como target actúa como autoencoder no lineal `5→3→5`. `recon_error = mean((X − X̂)², axis=1)` por fila. Se persiste con `joblib` (no `.keras`).

### Fase 3 — Evaluación no supervisada

| # | Tarea | Métrica (SPEC §8) |
|---|---|---|
| 3.1 | Especificidad proxy sobre holdout | ≥ 91 % |
| 3.2 | Tasa de alerta global | ≈ 5 % |
| 3.3 | Falsos positivos ambientales (regla equipo vs ambiente) | minimizar |
| 3.4 | Coincidencia de alertas con bitácora (cualitativo) | agrupamiento alrededor de eventos conocidos |
| 3.5 | Solapamiento con baseline RF M1 (precisión 98 % FALLA) | documentar |

**Salida:** `reports/health_monitor_ensemble/metrics.json` + `README.md`.

### Fase 3.5 — Validación multi-estación (leave-one-station-out)

Objetivo: probar que el ensemble **generaliza** a un analizador SO2 que nunca vio en entrenamiento — el argumento más fuerte de la tesis (no es un modelo sobreajustado a una estación).

| # | Tarea | Detalle |
|---|---|---|
| 3.5.1 | EDA comparativa entre estaciones | Distribución de las 4 features base por estación; ¿el "normal" de Ilo se parece al de Oroya? Documentar shift de distribución |
| 3.5.2 | Estrategia A — **por-estación** (default) | Un ensemble + θ por estación (recomendado: cada analizador tiene su ruido base). Baseline de referencia |
| 3.5.3 | Estrategia B — **leave-one-station-out** | Entrenar con 5 estaciones, evaluar en la 6.ª (rotando). Reportar especificidad y tasa de alerta en la estación held-out |
| 3.5.4 | Decisión de portabilidad | ¿El modelo unificado (B) mantiene especificidad ≥ 91 % en la estación no vista, o hace falta θ por-estación (A)? |
| 3.5.5 | Manejo de columnas heterogéneas | La estrategia unificada usa **solo el subconjunto común** de features (las 4 base + `hours_since_prev`); las extras (`PMT_VOLTAGE`, `BENCH_*`, `CONV_TEMP`) quedan para modelos por-estación |

**Salida:** `reports/health_monitor_ensemble/multi_station_validation.md` con la matriz de resultados (6×2: cada estación × estrategia) y la decisión A vs B.
**Nota de honestidad:** si B degrada mucho (shift de distribución alto), se documenta que el sistema es **por-estación** — sigue siendo válido, solo requiere entrenar el ensemble en cada nueva estación con su histórico normal.

### Fase 4 — Servicio de inferencia (streaming)

| # | Tarea | Archivo |
|---|---|---|
| 4.1 | Endpoint `POST /api/v1/health/evaluate` en `ml-service` | `services/ml-service/app/api/v1/health.py` |
| 4.2 | Estado por `device_id`: cálculo online de `hours_since_prev` sobre timestamps (SPEC §4.4) | servicio de estado |
| 4.3 | Persistencia en **tabla nueva** (`health_state`): `timestamp_fin_ultima_falla` + serie de `recon_error` + estado vigente por `device_id` | `models/health_state.py` + migración |
| 4.4 | Lógica de estabilización anti-parpadeo (`N_CONSEC=3`) | idem |
| 4.5 | Cargar `model_card.json` y exponer `model_version` en la respuesta | idem |

**Verificación:** enviar las lecturas del holdout una a una y confirmar que el estado en streaming coincide con la evaluación batch.

### Fase 5 — Diseño de dashboard (documento, no código)

Ver `docs/poc-dashboard-health-monitor.md`. En esta fase solo se **valida el diseño**; la implementación en Next.js es una fase posterior separada.

---

## 3. Orden de ejecución (resumen)

```
backup → cargar 6 estaciones (station_id, drop rul_days) → is_normal(valido=1) + hours_since_prev
      → scaler por-estación(solo-normal) → entrenar AE + θ → entrenar IF → AND + graduación
      → evaluar (especificidad, tasa alerta, bitácora, vs baseline RF)
      → validación multi-estación (leave-one-station-out: A por-estación vs B unificado)
      → endpoint streaming + estado por equipo → validar batch vs streaming
      → documento de diseño dashboard → (aprobación) → UI
```

---

## 4. Lista de archivos (crear / modificar / no tocar)

**Crear:**
- `services/ml-service/scripts/ensemble/01_build_dataset.py` — carga multi-estación + `hours_since_prev` offline + drop `rul_days`
- `services/ml-service/scripts/ensemble/02_train_autoencoder.py` — AE + θ (por estación)
- `services/ml-service/scripts/ensemble/03_train_iforest.py` — Isolation Forest
- `services/ml-service/scripts/ensemble/04_ensemble.py` — AND + graduación (módulo compartido)
- `services/ml-service/scripts/ensemble/05_multi_station_validation.py` — leave-one-station-out (Fase 3.5)
- `services/ml-service/ml_artifacts_ensemble_v1/` — `autoencoder_ensemble_v1.pkl` (MLPRegressor vía joblib), `iforest_ensemble_v1.pkl`, `scaler_<station>.pkl`, `theta_<station>.json`, `ensemble_config.json` (contamination/θ configurables), `model_card.json`
- `services/ml-service/app/api/v1/health.py` — endpoint de inferencia
- `services/ml-service/app/models/health_state.py` — modelo de tabla (estado + serie recon_error)
- `services/ml-service/alembic/versions/ml_XXX_health_state.py` — migración de la tabla
- `reports/health_monitor_ensemble/{metrics.json, README.md, multi_station_validation.md}` — resultados

**Modificar (mínimo, append):**
- `services/ml-service/app/main.py` — registrar el router `health`

> **Sin cambios en `requirements.txt`** — el AE usa `sklearn.MLPRegressor` (decisión §8.1).

**NO tocar:**
- `services/ml-service/ml_artifacts/`, `ml_artifacts_so2_v2/`, `ml_artifacts_h2s_v2/` (producción v2/v3)
- `reports/health_monitor_poc/` (baseline RF, se conserva para comparación)

---

## 5. Registro de riesgos

| Riesgo | Impacto | Mitigación |
|---|---|---|
| AE no converge / colapsa a la media | Error de reconstrucción sin señal | Arquitectura pequeña (cuello de botella 3), early stopping, normalización solo-normal, validar reconstrucción de rows normales |
| θ = P95 mal calibrado → demasiadas/pocas alertas | Semáforo ruidoso o ciego | Reportar tasa de alerta; exponer θ como parámetro; estabilización anti-parpadeo |
| Huecos de muestreo distorsionan `hours_since_prev` | Feature sesgado en producción | Cálculo online sobre timestamps reales (SPEC §4.4), no por conteo de filas |
| Sin ground-truth de falla | No hay recall verificable | Evaluación semi-cualitativa + solapamiento con baseline RF + bitácora |
| AE con `MLPRegressor` menos expresivo que un AE de Keras | Reconstrucción pobre → señal débil | Aceptado: el dataset es pequeño y las features pocas (5); un MLP `5→3→5` basta. Si la reconstrucción es insuficiente, escalar arquitectura (`5→4→3→4→5`) antes de considerar Keras. Sin dependencia nueva = sin riesgo de build |
| Falsos positivos por picos ambientales | Alertas espurias | Regla equipo-vs-ambiente: pico de `SO2_PPB` solo cuenta si coincide con señal de salud (flow/temp/lamp) |
| Shift de distribución entre estaciones (el "normal" de Ilo ≠ el de Oroya) | Modelo unificado (B) marca falsas anomalías en estación no vista | Estrategia A (θ + scaler por-estación) como default; B solo si la validación 3.5 confirma especificidad ≥ 91 % en la held-out |
| Columnas heterogéneas entre estaciones | Feature ausente rompe el modelo unificado | Usar solo el subconjunto común (4 base + `hours_since_prev`); extras solo en modelos por-estación |

## 6. Runtime y footprint estimados

- **Entrenamiento:** AE (`MLPRegressor`) ~1–2 min (CPU, dataset pequeño), IF ~30 s. Total < 5 min en laptop, sin GPU ni TensorFlow.
- **Inferencia:** < 10 ms por lectura (AE `predict` + IF score). Compatible con streaming a 5 min/lectura holgadamente.
- **Disco:** artefactos < 20 MB (MLP pequeño + IF 200 árboles + scaler por estación).

## 7. Plan de rollback

```bash
# restaurar artefactos ML
cp -R services/ml-service/ml_artifacts_backup_pre_ensemble_<TS>/* services/ml-service/
# revertir la migración de la tabla health_state (si se aplicó)
cd services/ml-service && PYTHONPATH=../.. alembic downgrade -1
# recuperar cambios stasheados
git stash pop
```

El ensemble vive en directorios `_ensemble_v1` aislados: eliminar la carpeta, revertir la migración y desregistrar el router revierte el componente sin afectar producción. **No se tocó `requirements.txt`** (sin dependencia nueva), así que no hay que revertirlo.

## 8. Decisiones cerradas (resueltas — 2026-07-04)

1. **Framework del Autoencoder → `sklearn.neural_network.MLPRegressor`.** Cero dependencia nueva (no TensorFlow/Keras). El AE se implementa como MLP que reconstruye su propia entrada (`X → X`). Elimina el riesgo de "NN rompe el build" y simplifica el despliegue.
2. **Número de features → 5** (`SO2_PPB`, `SO2_FLOW`, `SO2_INTERNAL_TEMP`, `SO2_LAMP_INT`, `hours_since_prev`). La 6.ª variable (multi-gas) queda **reservada** — se deja el hook en el pipeline pero no se entrena con ella en v1.
3. **Persistencia del estado → tabla nueva** en la BD del `ml-service` (no cache en memoria), para que el dashboard lea el histórico de `recon_error` y `health_state`.
4. **`contamination` y θ → configurables** desde el inicio (por estación), con default a los valores del Anexo (`0.05` / `P95`).
5. **Estrategia multi-estación → reportar ambos** (A por-estación y B leave-one-station-out). Se adopta A como sistema en producción y B como evidencia de generalización.

> Estas decisiones ya están reflejadas en las fases y la lista de archivos arriba.

---

## 9. Definición de "hecho" (Definition of Done)

- [ ] AE + IF entrenados solo-normal, artefactos versionados con `model_card.json`.
- [ ] `hours_since_prev` calculado online sobre timestamps, validado contra el cálculo offline.
- [ ] Especificidad ≥ 91 % en holdout; tasa de alerta reportada.
- [ ] `rul_days` confirmado ausente de las features (chequeo anti-leakage).
- [ ] Validación multi-estación ejecutada (matriz 6×2 A vs B) y decisión A/B documentada.
- [ ] Endpoint de inferencia responde el contrato de SPEC §6.2.
- [ ] Estado por equipo con estabilización anti-parpadeo funcionando en streaming.
- [ ] Solapamiento con baseline RF documentado.
- [ ] Documento de diseño de dashboard aprobado.
- [ ] Backup verificado y plan de rollback probado.
