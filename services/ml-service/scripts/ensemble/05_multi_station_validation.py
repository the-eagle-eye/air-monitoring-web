"""
Fase 3.5 — Validación multi-estación (leave-one-station-out).

Compara dos estrategias sobre las 5 estaciones entrenadas:

  A (por-estación, sistema en producción): el ensemble de CADA estación evaluado
    sobre su propio holdout, con θ recalibrado (warm-up). Ya calculado en Fase 3;
    se re-reporta aquí como línea base.

  B (unificado leave-one-station-out): para cada estación held-out, se entrena un
    AE + IF + scaler con las OTRAS 4 estaciones (train-normal) y se evalúa sobre la
    estación held-out completa. Prueba la GENERALIZACIÓN a un analizador no visto.

Objetivo: cuantificar el shift de distribución entre estaciones (SPEC §9.1/§9.2) y
decidir si B es viable (≥91% en held-out) o si el sistema debe quedarse en A.

Salida: reports/health_monitor_ensemble/multi_station_validation.md (+ .json)
"""
import importlib.util
import json
import os

import joblib
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.neural_network import MLPRegressor
from sklearn.preprocessing import StandardScaler

RANDOM_SEED = 42
np.random.seed(RANDOM_SEED)

ART = 'services/ml-service/ml_artifacts_ensemble_v1'
DATASET = '/tmp/hm_ensemble_dataset.joblib'
REPORT_DIR = 'reports/health_monitor_ensemble'

FEATS = ['SO2_PPB', 'SO2_FLOW', 'SO2_INTERNAL_TEMP', 'SO2_LAMP_INT', 'hours_since_prev']
WARMUP_ROWS = 4032
THETA_PCT = 95
CONTAMINATION = 0.05
SPEC_TARGET = 91.0

_spec = importlib.util.spec_from_file_location('ens', f'{os.path.dirname(__file__)}/04_ensemble.py')
ens = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(ens)


def train_unified(X_norm):
    """Entrena AE(5→3→5)+IF sobre train-normal combinado de N-1 estaciones."""
    scaler = StandardScaler().fit(X_norm)
    Xs = scaler.transform(X_norm)
    ae = MLPRegressor(hidden_layer_sizes=(3,), activation='relu', solver='adam',
                      max_iter=300, early_stopping=True, n_iter_no_change=15,
                      random_state=RANDOM_SEED).fit(Xs, Xs)
    iforest = IsolationForest(n_estimators=200, contamination=CONTAMINATION,
                              random_state=RANDOM_SEED, n_jobs=-1).fit(Xs)
    return scaler, ae, iforest


def specificity_on(df_station, scaler, ae, iforest, cfg):
    """Evalúa el ensemble sobre una estación (holdout completo, valido=1 + feat ok),
    con θ recalibrado por warm-up. Devuelve (especificidad%, n_eval)."""
    g = df_station.sort_values('date')
    feat_ok = g[FEATS].notna().all(axis=1).values
    evaluable = (g['valido'].values == 1) & feat_ok
    if evaluable.sum() < 200:
        return None, 0
    X = scaler.transform(g.loc[evaluable, FEATS].values)
    err = ens.compute_recon_error(ae, X)
    ifa = (iforest.predict(X) == -1)
    warm = min(WARMUP_ROWS, len(err) // 4)
    theta = float(np.percentile(err[:warm], THETA_PCT))
    alert = int(np.sum((err > theta) & ifa))
    n = int(evaluable.sum())
    return round(100 * (1 - alert / n), 2), n


def main():
    df = joblib.load(DATASET)
    cfg = ens.load_config()
    stations = sorted(df['station_id'].unique())

    # --- Estrategia A: re-leer especificidad recalibrada de Fase 3 (metrics.json) ---
    with open(f'{REPORT_DIR}/metrics.json') as f:
        fase3 = {r['station_id']: r for r in json.load(f)['stations']}

    rows = []
    for held in stations:
        # B: entrenar con las otras estaciones (train-normal), evaluar en held-out
        others = df[(df['station_id'] != held) & (df['split'] == 'train') & (df['is_normal'])]
        X_norm = others[FEATS].values
        scaler_u, ae_u, if_u = train_unified(X_norm)
        held_df = df[df['station_id'] == held]
        spec_b, n_b = specificity_on(held_df, scaler_u, ae_u, if_u, cfg)

        spec_a = fase3.get(held, {}).get('specificity_recal_pct')
        rows.append({
            'held_out_station': held,
            'A_per_station_specificity_pct': spec_a,
            'B_leave_one_out_specificity_pct': spec_b,
            'B_n_eval': n_b,
            'B_meets_target': (spec_b is not None and spec_b >= SPEC_TARGET),
            'A_minus_B_pct': (round(spec_a - spec_b, 2)
                              if (spec_a is not None and spec_b is not None) else None),
        })
        print(f"  held={held:12s} A(por-est)={spec_a:6.1f}%  "
              f"B(LOSO)={spec_b:6.1f}%  Δ(A-B)={rows[-1]['A_minus_B_pct']:+.1f}")

    b_ok = sum(1 for r in rows if r['B_meets_target'])
    result = {
        'strategy_A': 'por-estación (θ recalibrado) — sistema en producción',
        'strategy_B': 'leave-one-station-out unificado (generalización)',
        'stations_evaluated': stations,
        'B_stations_meeting_target': f'{b_ok}/{len(rows)}',
        'spec_target_pct': SPEC_TARGET,
        'rows': rows,
    }
    with open(f'{REPORT_DIR}/multi_station_validation.json', 'w') as f:
        json.dump(result, f, indent=2)

    print(f"\nEstrategia B (generalización) cumple en {b_ok}/{len(rows)} estaciones held-out.")
    print(f"JSON en {REPORT_DIR}/multi_station_validation.json")
    return result


if __name__ == '__main__':
    main()
