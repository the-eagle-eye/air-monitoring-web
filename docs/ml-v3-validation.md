# ML v3 (isolation) — validation results

## Approach
- 6 per-station bundles: Autoencoder (MLPRegressor, cuello de botella) + IsolationForest, entrenados sobre operación normal (`valido=True` and `rul_days > 5`).
- Detección primaria unsupervised. RUL regressor evaluado como control — **no se sirve** en producción (R² per-cycle negativo en las 6 estaciones).
- Puntos de falla reconstruidos desde saltos de `rul_days` (fin de ciclo).
- Ventana de detección temprana = 72 h antes de cada falla documentada.

## Training results (from `ml_artifacts_v3/<station>/model_card.json`)

| Estación | Sensores | Fallas | R² random | R² per-cycle | Detección | Anticip. | Precisión | Especificidad |
|---|---|---|---|---|---|---|---|---|
| CA-CHILLO-01 | 7 | 8  | 0.982 | −1.05  | 6/8 (75%)   | 2.7 d | 10% | 91% |
| CA-CC-01     | 7 | 1  | 0.976 | −0.40  | 1/1 (100%)  | 2.6 d | 5%  | 92% |
| CA-UCHU-01   | 7 | 23 | 0.969 | −55.98 | 21/23 (91%) | 2.6 d | 82% | 92% |
| CA-CH-05     | 6 | 4  | 0.985 | −5.44  | 2/4 (50%)   | 2.9 d | 7%  | 92% |
| CA-CH-04     | 6 | 4  | 0.989 | −47.14 | 4/4 (100%)  | 2.6 d | 2%  | 91% |
| CA-ILO-01    | 4 | 16 | 0.977 | −0.46  | 15/16 (94%) | 2.5 d | 5%  | 92% |

Aggregate: **49 / 56 fallas detectadas (87.5%)**, especificidad estable **91–92%**, anticipación 2.5–2.9 días.

## Layered test suite (Stage 1)

| Layer | Tests | Purpose |
|---|---|---|
| 1 Unit | ~20 | Registry, sensor alias, episode logic, composite risk rule |
| 2 Artifact | 14 | All 6 bundles load, scaler shape matches sensor list |
| 3 Behavioral | 11 pass, 1 skip | Real pre-failure and healthy CSV slices → expected outcomes |
| 4 Integration | 8 | End-to-end `run_prediction` with mocked iot-service, episode lifecycle, alert dedup, ops notify |
| 5 API contract | 6 | HTTP shape of `/predictions/*`, `/alerts`, `/health` |
| 6 Gateway | 15 | ML_BACKEND flag routing + v3→legacy adapter |
| **Total** | **~74 pytest** | |

Also: `scripts/replay_validation.py` — manual, full-CSV replay comparing against `model_card` metrics.

## Behavioral (Layer 3) acceptance criteria
- Every station's 72h pre-failure fixture must trigger ≥1 anomaly.
- Every station's 72h healthy fixture must keep normal fraction ≥ 70%.
- `CA-CH-05` skipped for pre-failure because its 4 failures are ambiguous — matches the 50% training detection.

## Non-goals
- We do **not** benchmark v3 against a fixed R² / F1 target — the model does not predict RUL.
- Acceptance criteria are operational: detection ≥ 80% aggregate, specificity ≥ 85% per station.

## How to re-verify
```bash
# Retrain (if needed)
python services/ml-service-isolation/scripts/train_all.py

# Refresh fixtures
python services/ml-service-isolation/scripts/extract_fixtures.py

# Run test suite
cd services/ml-service-isolation
PYTHONPATH=../.. python -m pytest tests/

# Full-CSV replay
python services/ml-service-isolation/scripts/replay_validation.py
```

## Cutover checklist (Stage 4)
- [ ] Deploy ml-service-isolation on :8004
- [ ] Run backfill: `scripts/backfill_predictions.py --iot-url ... --ml-iso-url ...`
- [ ] Flip `ML_BACKEND=isolation` on api-gateway
- [ ] Verify dashboard renders with adapter output
- [ ] Announce deprecation window for legacy ml-service
