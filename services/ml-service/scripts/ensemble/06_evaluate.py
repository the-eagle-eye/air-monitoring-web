"""
Fase 3 — Evaluación no supervisada del ensemble (por estación).

Métricas (SPEC §8), sobre holdout test:
  - especificidad (proxy) = % rows con transmisión NO marcadas como alerta   (meta ≥91%)
  - tasa de alerta        = % rows evaluables con and_alert=True             (~5%)
  - distribución de estados por estación
  - comparación θ-fijo (train) vs θ-recalibrado (warm-up en sitio)

θ-recalibrado (umbral adaptativo, Anexo slide 9): P95 del recon_error sobre las
primeras WARMUP_ROWS lecturas del test (calibración en sitio del régimen actual).
Es lo que un sistema en producción haría al desplegarse en una estación.

Salidas:
  reports/health_monitor_ensemble/metrics.json
  reports/health_monitor_ensemble/README.md
"""
import importlib.util
import json
import os
from collections import Counter

import joblib
import numpy as np

ART = 'services/ml-service/ml_artifacts_ensemble_v1'
DATASET = '/tmp/hm_ensemble_dataset.joblib'
REPORT_DIR = 'reports/health_monitor_ensemble'
os.makedirs(REPORT_DIR, exist_ok=True)

FEATS = ['SO2_PPB', 'SO2_FLOW', 'SO2_INTERNAL_TEMP', 'SO2_LAMP_INT', 'hours_since_prev']
WARMUP_ROWS = 4032          # 2 semanas a 5 min — ventana de calibración en sitio
THETA_PERCENTILE = 95
SPEC_TARGET = 91.0          # especificidad meta (SPEC §8)

_spec = importlib.util.spec_from_file_location('ens', f'{os.path.dirname(__file__)}/04_ensemble.py')
ens = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(ens)


def eval_station(g, cfg):
    sid = g['station_id'].iloc[0]
    scaler = joblib.load(f'{ART}/scaler_{sid}.pkl')
    ae = joblib.load(f'{ART}/autoencoder_{sid}.pkl')
    iforest = joblib.load(f'{ART}/iforest_{sid}.pkl')
    theta_fixed = ens.load_theta_train(sid)  # θ original del train (columna comparativa)

    te = g[g['split'] == 'test'].copy().sort_values('date')
    n_test = len(te)
    # gate §3.0: evaluable = valido=1 Y features completas; el resto -> SIN_DATOS
    feat_ok = te[FEATS].notna().all(axis=1).values
    evaluable = (te['valido'].values == 1) & feat_ok
    n_sin_datos = int((~evaluable).sum())

    if evaluable.sum() < 100:
        return None

    X = scaler.transform(te.loc[evaluable, FEATS].values)
    err = ens.compute_recon_error(ae, X)
    ifa = (iforest.predict(X) == -1)

    # θ recalibrado: P95 del error en la ventana warm-up del test
    warm = min(WARMUP_ROWS, len(err) // 4)
    theta_recal = float(np.percentile(err[:warm], THETA_PERCENTILE))

    def states_and_specificity(theta):
        states = Counter({'SIN_DATOS': n_sin_datos})
        for e, a in zip(err, ifa):
            out = ens.evaluate_reading(1, e, a, theta, cfg)
            states[out['health_state']] += 1
        n_eval = int(evaluable.sum())
        alert = sum(v for k, v in states.items()
                    if k in ('OBSERVADO', 'EN_RIESGO', 'CRITICO'))
        specificity = 100.0 * (1 - alert / n_eval)   # % evaluables sin alerta
        return dict(states), round(specificity, 2), round(100 * alert / n_eval, 2)

    st_fix, spec_fix, alert_fix = states_and_specificity(theta_fixed)
    st_rec, spec_rec, alert_rec = states_and_specificity(theta_recal)

    return {
        'station_id': sid,
        'n_test': n_test,
        'n_evaluable': int(evaluable.sum()),
        'n_sin_datos': n_sin_datos,
        'theta_fixed': round(theta_fixed, 6),
        'theta_recalibrated': round(theta_recal, 6),
        'specificity_fixed_pct': spec_fix,
        'specificity_recal_pct': spec_rec,
        'alert_rate_fixed_pct': alert_fix,
        'alert_rate_recal_pct': alert_rec,
        'meets_target_recal': spec_rec >= SPEC_TARGET,
        'states_recal': st_rec,
    }


def main():
    df = joblib.load(DATASET)
    cfg = ens.load_config()
    results = []
    for sid, g in df.groupby('station_id'):
        r = eval_station(g, cfg)
        if r:
            results.append(r)

    n_ok = sum(1 for r in results if r['meets_target_recal'])
    metrics = {
        'warmup_rows': WARMUP_ROWS,
        'theta_percentile': THETA_PERCENTILE,
        'specificity_target_pct': SPEC_TARGET,
        'stations_meeting_target_recal': f'{n_ok}/{len(results)}',
        'stations': results,
    }
    with open(f'{REPORT_DIR}/metrics.json', 'w') as f:
        json.dump(metrics, f, indent=2)

    # consola
    print(f"{'estación':13s} {'espec_fijo':>10s} {'espec_recal':>11s} "
          f"{'alerta_recal':>12s} {'meta≥91%':>9s}")
    for r in results:
        ok = 'SÍ' if r['meets_target_recal'] else 'NO'
        print(f"{r['station_id']:13s} {r['specificity_fixed_pct']:9.1f}% "
              f"{r['specificity_recal_pct']:10.1f}% {r['alert_rate_recal_pct']:11.1f}% {ok:>9s}")
    print(f"\nEstaciones que cumplen (θ recalibrado): {n_ok}/{len(results)}")
    print(f"Métricas en {REPORT_DIR}/metrics.json")


if __name__ == '__main__':
    main()
