"""
P4 — Persistir θ recalibrado (warm-up) como el umbral ACTIVO de producción.

Motivación (README §3): con θ-train fijo, CA-ILO-01 daba 58% de especificidad por
drift temporal; con θ recalibrado sobre el régimen actual (warm-up 2 semanas del
holdout) sube a 98%. En producción el sistema debe usar el θ recalibrado.

Este script recalcula θ por estación sobre la ventana warm-up y reescribe cada
theta_<station>.json conservando trazabilidad:
  {
    "station_id", "theta"  (= el ACTIVO, recalibrado),
    "theta_train"          (el original del train, para auditoría),
    "theta_recalibrated"   (= theta),
    "theta_source": "recalibrated_warmup",
    "warmup_rows", "theta_percentile", ...
  }

El servicio de inferencia sigue leyendo la clave "theta" -> ahora es el recalibrado.
"""
import importlib.util
import json
import os

import joblib
import numpy as np

ART = 'services/ml-service/ml_artifacts_ensemble_v1'
DATASET = '/tmp/hm_ensemble_dataset.joblib'
FEATS = ['SO2_PPB', 'SO2_FLOW', 'SO2_INTERNAL_TEMP', 'SO2_LAMP_INT', 'hours_since_prev']
WARMUP_ROWS = 4032
THETA_PCT = 95

_spec = importlib.util.spec_from_file_location('ens', f'{os.path.dirname(__file__)}/04_ensemble.py')
ens = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(ens)


def recalibrate_station(g):
    sid = g['station_id'].iloc[0]
    theta_path = os.path.join(ART, f'theta_{sid}.json')
    if not os.path.exists(theta_path):
        return None
    with open(theta_path) as f:
        meta = json.load(f)

    scaler = joblib.load(f'{ART}/scaler_{sid}.pkl')
    ae = joblib.load(f'{ART}/autoencoder_{sid}.pkl')

    # warm-up = primeras WARMUP_ROWS lecturas del régimen actual (holdout test, valido=1)
    te = g[(g['split'] == 'test') & (g['valido'] == 1)].copy()
    te = te[te[FEATS].notna().all(axis=1)].sort_values('date')
    warm = min(WARMUP_ROWS, len(te) // 4)
    if warm < 100:
        return None
    X = scaler.transform(te[FEATS].iloc[:warm].values)
    err = ens.compute_recon_error(ae, X)
    theta_recal = float(np.percentile(err, THETA_PCT))

    theta_train = meta.get('theta_train', meta['theta'])  # idempotente en re-runs
    new_meta = {
        'station_id': sid,
        'theta': theta_recal,                 # ACTIVO (leído por el servicio)
        'theta_train': theta_train,           # original, para auditoría
        'theta_recalibrated': theta_recal,
        'theta_source': 'recalibrated_warmup',
        'warmup_rows': int(warm),
        'theta_percentile': THETA_PCT,
        'train_normal_rows': meta.get('train_normal_rows'),
    }
    with open(theta_path, 'w') as f:
        json.dump(new_meta, f, indent=2)
    return {'station_id': sid, 'theta_train': round(theta_train, 4),
            'theta_recal': round(theta_recal, 4), 'warmup_rows': int(warm)}


def main():
    df = joblib.load(DATASET)
    rows = [r for r in (recalibrate_station(g) for _, g in df.groupby('station_id')) if r]
    print(f"{'estación':13s} {'θ_train':>9s} {'θ_recal':>9s} {'warmup':>8s}")
    for r in rows:
        print(f"{r['station_id']:13s} {r['theta_train']:>9.4f} "
              f"{r['theta_recal']:>9.4f} {r['warmup_rows']:>8}")
    print(f"\n{len(rows)} estaciones: theta_<station>.json ahora usa θ recalibrado como activo.")
    print("theta_train conservado para auditoría.")


if __name__ == '__main__':
    main()
