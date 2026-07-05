"""
Fase 2.3 — Isolation Forest por estación.

IF = sklearn.ensemble.IsolationForest(contamination configurable, default 0.05,
n_estimators=200, random_state=42), entrenado SOLO con rows normales de train
(features escaladas por el scaler de la estación). SPEC §3.3.

Salida: ml_artifacts_ensemble_v1/iforest_<station>.pkl
"""
import json
import os
import time

import joblib
import numpy as np
from sklearn.ensemble import IsolationForest

RANDOM_SEED = 42
np.random.seed(RANDOM_SEED)

ART_DIR = 'services/ml-service/ml_artifacts_ensemble_v1'
DATASET = '/tmp/hm_ensemble_dataset.joblib'
REPORT_DIR = 'reports/health_monitor_ensemble'

ENSEMBLE_FEATURES = ['SO2_PPB', 'SO2_FLOW', 'SO2_INTERNAL_TEMP', 'SO2_LAMP_INT',
                     'hours_since_prev']
N_ESTIMATORS = 200


def load_contamination():
    with open(os.path.join(ART_DIR, 'ensemble_config.json')) as f:
        return json.load(f)['contamination']


def main():
    df = joblib.load(DATASET)
    contamination = load_contamination()

    summary = []
    for sid, g in df.groupby('station_id'):
        scaler = joblib.load(os.path.join(ART_DIR, f'scaler_{sid}.pkl'))
        train_norm = g[(g['split'] == 'train') & (g['is_normal'])]
        X = scaler.transform(train_norm[ENSEMBLE_FEATURES].values)

        t0 = time.time()
        iforest = IsolationForest(
            n_estimators=N_ESTIMATORS,
            contamination=contamination,
            random_state=RANDOM_SEED,
            n_jobs=-1,
        )
        iforest.fit(X)
        dt = time.time() - t0

        # predict: +1 normal, -1 anómalo. % anómalo sobre train-normal ≈ contamination.
        pred = iforest.predict(X)
        pct_anom = float((pred == -1).mean() * 100)

        joblib.dump(iforest, os.path.join(ART_DIR, f'iforest_{sid}.pkl'))
        summary.append({'station_id': sid, 'contamination': contamination,
                        'pct_anom_train': round(pct_anom, 2),
                        'train_normal': int(len(train_norm)),
                        'train_time_s': round(dt, 1)})
        print(f"  {sid:12s} contam={contamination} anom_train={pct_anom:4.1f}% "
              f"n={len(train_norm):>6} ({dt:.1f}s)")

    with open(os.path.join(REPORT_DIR, 'iforest_summary.json'), 'w') as f:
        json.dump(summary, f, indent=2)
    print(f'\nIsolation Forests por estación guardados en {ART_DIR}')


if __name__ == '__main__':
    main()
