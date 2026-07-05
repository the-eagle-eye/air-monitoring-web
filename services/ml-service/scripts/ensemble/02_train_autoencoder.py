"""
Fase 2.1–2.2 — Autoencoder por estación + umbral θ.

AE = sklearn.neural_network.MLPRegressor(hidden_layer_sizes=(3,)) que reconstruye
X -> X (autoencoder no lineal 5→3→5, SPEC §3.2). Se entrena SOLO con rows normales
(is_normal) de train, con las features escaladas por el scaler de la estación.

θ = percentil configurable (default P95) del recon_error sobre train-normal,
    por estación (SPEC §3.2, decisión §8.4). Se guarda theta_<station>.json.

Salidas:
  ml_artifacts_ensemble_v1/autoencoder_<station>.pkl
  ml_artifacts_ensemble_v1/theta_<station>.json
  ml_artifacts_ensemble_v1/ensemble_config.json
"""
import json
import os
import time

import joblib
import numpy as np
from sklearn.neural_network import MLPRegressor

RANDOM_SEED = 42
np.random.seed(RANDOM_SEED)

ART_DIR = 'services/ml-service/ml_artifacts_ensemble_v1'
DATASET = '/tmp/hm_ensemble_dataset.joblib'
REPORT_DIR = 'reports/health_monitor_ensemble'
os.makedirs(ART_DIR, exist_ok=True)

ENSEMBLE_FEATURES = ['SO2_PPB', 'SO2_FLOW', 'SO2_INTERNAL_TEMP', 'SO2_LAMP_INT',
                     'hours_since_prev']

CONFIG = {
    'contamination': 0.05,
    'theta_percentile': 95,
    'severity_multipliers': {'observado': 1.0, 'en_riesgo': 2.0, 'critico': 3.0},
    'features': ENSEMBLE_FEATURES,
    'random_seed': RANDOM_SEED,
}


def train_station_ae(X_train_norm):
    """MLPRegressor 5→3→5 reconstruyendo X→X, solo-normal."""
    ae = MLPRegressor(
        hidden_layer_sizes=(3,),
        activation='relu',
        solver='adam',
        max_iter=300,
        early_stopping=True,
        n_iter_no_change=15,
        random_state=RANDOM_SEED,
    )
    ae.fit(X_train_norm, X_train_norm)
    return ae


def recon_error(ae, X):
    X_hat = ae.predict(X)
    return np.mean((X - X_hat) ** 2, axis=1)


def main():
    df = joblib.load(DATASET)
    # persistir config global del ensemble (contamination/θ configurables)
    with open(os.path.join(ART_DIR, 'ensemble_config.json'), 'w') as f:
        json.dump(CONFIG, f, indent=2)

    p = CONFIG['theta_percentile']
    summary = []
    for sid, g in df.groupby('station_id'):
        scaler = joblib.load(os.path.join(ART_DIR, f'scaler_{sid}.pkl'))
        train_norm = g[(g['split'] == 'train') & (g['is_normal'])]
        X = scaler.transform(train_norm[ENSEMBLE_FEATURES].values)

        t0 = time.time()
        ae = train_station_ae(X)
        dt = time.time() - t0

        err = recon_error(ae, X)
        theta = float(np.percentile(err, p))

        joblib.dump(ae, os.path.join(ART_DIR, f'autoencoder_{sid}.pkl'))
        with open(os.path.join(ART_DIR, f'theta_{sid}.json'), 'w') as f:
            json.dump({'station_id': sid, 'theta': theta,
                       'theta_percentile': p,
                       'train_normal_rows': int(len(train_norm)),
                       'recon_error_mean': float(err.mean()),
                       'recon_error_p50': float(np.percentile(err, 50))}, f, indent=2)

        summary.append({'station_id': sid, 'theta': round(theta, 6),
                        'err_mean': round(float(err.mean()), 6),
                        'train_normal': int(len(train_norm)),
                        'train_time_s': round(dt, 1)})
        print(f"  {sid:12s} θ(P{p})={theta:.6f} err_mean={err.mean():.6f} "
              f"n={len(train_norm):>6} ({dt:.1f}s)")

    with open(os.path.join(REPORT_DIR, 'autoencoder_summary.json'), 'w') as f:
        json.dump(summary, f, indent=2)
    print(f'\nAutoencoders + θ por estación guardados en {ART_DIR}')
    print(f'Config del ensemble en {ART_DIR}/ensemble_config.json')


if __name__ == '__main__':
    main()
