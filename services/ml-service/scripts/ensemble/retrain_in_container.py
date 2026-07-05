"""
Re-entrena los artefactos del ensemble DENTRO del contenedor ml-service, para que
los pickles sean nativos a la numpy/sklearn del runtime (evita el error
'MT19937 is not a known BitGenerator' por mismatch de versiones local vs contenedor).

Self-contained (no depende de rutas del host). Rutas del contenedor:
  dataset CSV : /app/dataset_ensemble   (volumen ro de services/ml-proposal/dataset)
  artefactos  : /app/ml_artifacts_ensemble_v1

Reproduce Fases 1-2 (dataset + scaler + AE + IF + θ) para las 5 estaciones
entrenadas (Chillón excluida). Ejecutar:
  docker compose exec ml-service python scripts/ensemble/retrain_in_container.py
"""
import glob
import json
import os

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.neural_network import MLPRegressor
from sklearn.preprocessing import StandardScaler

RANDOM_SEED = 42
np.random.seed(RANDOM_SEED)

DATASET_DIR = '/app/dataset_ensemble'
ART_DIR = '/app/ml_artifacts_ensemble_v1'
BASE = ['SO2_PPB', 'SO2_FLOW', 'SO2_INTERNAL_TEMP', 'SO2_LAMP_INT']
FEATS = BASE + ['hours_since_prev']
EXCLUDED = {'CA-CHILLO-01'}
TEST_FRACTION = 0.20
CONTAM = 0.05
THETA_PCT = 95
WARMUP_ROWS = 4032


def station_id(path):
    return os.path.basename(path).split('_')[0]


def load(path):
    df = pd.read_csv(path, usecols=lambda c: c in (['date', 'valido'] + BASE))
    df['date'] = pd.to_datetime(df['date'], errors='coerce')
    df = df.dropna(subset=['date'])
    df['valido'] = df['valido'].astype(bool).astype(int)
    df = df.sort_values('date').drop_duplicates('date').reset_index(drop=True)
    for c in BASE:
        df[c] = pd.to_numeric(df[c], errors='coerce')
    return df


def hsp_offline(df):
    isf = (df['valido'].values == 0); n = len(df)
    h = np.full(n, np.nan); le = None; inf = False
    for i in range(n):
        if isf[i]:
            inf = True
        else:
            if inf:
                le = i
            inf = False
            if le is not None:
                h[i] = (i - le) * 5 / 60
    return h


def main():
    files = [f for f in sorted(glob.glob(f'{DATASET_DIR}/*.csv'))
             if station_id(f) not in EXCLUDED]
    print(f'Re-entrenando {len(files)} estaciones (numpy {np.__version__})')
    cfg = {
        'contamination': CONTAM, 'theta_percentile': THETA_PCT,
        'severity_multipliers': {'observado': 1.0, 'en_riesgo': 2.0, 'critico': 3.0},
        'features': FEATS, 'random_seed': RANDOM_SEED,
    }
    with open(f'{ART_DIR}/ensemble_config.json', 'w') as fh:
        json.dump(cfg, fh, indent=2)

    for f in files:
        sid = station_id(f)
        df = load(f)
        df['hours_since_prev'] = hsp_offline(df)
        n = len(df); cut = int(n * (1 - TEST_FRACTION))
        df['split'] = ['train'] * cut + ['test'] * (n - cut)
        tr = df[(df['split'] == 'train') & (df['valido'] == 1)].copy()
        tr = tr[tr[BASE].notna().all(axis=1)]
        med = tr['hours_since_prev'].median()
        tr['hours_since_prev'] = tr['hours_since_prev'].fillna(med)

        scaler = StandardScaler().fit(tr[FEATS].values)
        Xtr = scaler.transform(tr[FEATS].values)
        ae = MLPRegressor(hidden_layer_sizes=(3,), max_iter=300,
                          early_stopping=True, n_iter_no_change=15,
                          random_state=RANDOM_SEED).fit(Xtr, Xtr)
        iforest = IsolationForest(n_estimators=200, contamination=CONTAM,
                                  random_state=RANDOM_SEED, n_jobs=-1).fit(Xtr)

        # θ recalibrado (warm-up del test) — coherente con producción (P4)
        te = df[(df['split'] == 'test') & (df['valido'] == 1)].copy()
        te = te[te[BASE].notna().all(axis=1)].sort_values('date')
        te['hours_since_prev'] = te['hours_since_prev'].fillna(med)
        warm = min(WARMUP_ROWS, max(1, len(te) // 4))
        Xw = scaler.transform(te[FEATS].iloc[:warm].values)
        err_w = np.mean((Xw - ae.predict(Xw)) ** 2, axis=1)
        theta_recal = float(np.percentile(err_w, THETA_PCT))
        err_tr = np.mean((Xtr - ae.predict(Xtr)) ** 2, axis=1)
        theta_train = float(np.percentile(err_tr, THETA_PCT))

        joblib.dump(scaler, f'{ART_DIR}/scaler_{sid}.pkl')
        joblib.dump(ae, f'{ART_DIR}/autoencoder_{sid}.pkl')
        joblib.dump(iforest, f'{ART_DIR}/iforest_{sid}.pkl')
        with open(f'{ART_DIR}/theta_{sid}.json', 'w') as fh:
            json.dump({'station_id': sid, 'theta': theta_recal,
                       'theta_train': theta_train, 'theta_recalibrated': theta_recal,
                       'theta_source': 'recalibrated_warmup',
                       'theta_percentile': THETA_PCT}, fh, indent=2)
        print(f'  {sid:12s} θ_recal={theta_recal:.4f} (train n={len(tr)})')

    print(f'\nArtefactos re-entrenados en {ART_DIR} (nativos al contenedor).')


if __name__ == '__main__':
    main()
