"""
P2 — Falsos positivos ambientales (SPEC §8, regla equipo-vs-ambiente §2.1 / ml.md).

Regla: un pico de SO2_PPB (evento AMBIENTAL — concentración del gas medido) NO debe
disparar una alerta de salud salvo que coincida con una señal de SALUD del equipo
(flow / internal_temp / lamp_int anómalos). Un pico de contaminación no es una falla.

Métrica: de todas las alertas del ensemble, ¿qué fracción son "ambientales puras"
(dominadas por SO2_PPB con las señales de salud dentro de rango)? Esa fracción son
falsos positivos ambientales — se busca minimizarla.

Descomponemos el error de reconstrucción por feature: una alerta es "ambiental pura"
si SO2_PPB es el mayor contribuyente al error Y ninguna señal de salud contribuye
por encima de un umbral relativo.

Salida: reports/health_monitor_ensemble/environmental_fp.md (+ .json)
"""
import importlib.util
import json
import os

import joblib
import numpy as np

ART = 'services/ml-service/ml_artifacts_ensemble_v1'
DATASET = '/tmp/hm_ensemble_dataset.joblib'
REPORT_DIR = 'reports/health_monitor_ensemble'

FEATS = ['SO2_PPB', 'SO2_FLOW', 'SO2_INTERNAL_TEMP', 'SO2_LAMP_INT', 'hours_since_prev']
PPB_IDX = FEATS.index('SO2_PPB')
HEALTH_IDX = [FEATS.index(c) for c in ('SO2_FLOW', 'SO2_INTERNAL_TEMP', 'SO2_LAMP_INT')]
WARMUP_ROWS = 4032
THETA_PCT = 95
# una señal de salud "contribuye" si su error escalado supera este umbral
HEALTH_CONTRIB_MIN = 1.0

_spec = importlib.util.spec_from_file_location('ens', f'{os.path.dirname(__file__)}/04_ensemble.py')
ens = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(ens)


def analyze_station(g):
    sid = g['station_id'].iloc[0]
    scaler = joblib.load(f'{ART}/scaler_{sid}.pkl')
    ae = joblib.load(f'{ART}/autoencoder_{sid}.pkl')
    iforest = joblib.load(f'{ART}/iforest_{sid}.pkl')

    te = g[(g['split'] == 'test') & (g['valido'] == 1)].copy()
    te = te[te[FEATS].notna().all(axis=1)].sort_values('date')
    if len(te) < 500:
        return None

    X = scaler.transform(te[FEATS].values)
    Xhat = ae.predict(X)
    sqerr = (X - Xhat) ** 2
    err = sqerr.mean(axis=1)
    ifa = (iforest.predict(X) == -1)
    warm = min(WARMUP_ROWS, len(err) // 4)
    theta = float(np.percentile(err[:warm], THETA_PCT))
    alert = (err > theta) & ifa
    n_alert = int(alert.sum())
    if n_alert == 0:
        return {'station_id': sid, 'n_alerts': 0, 'env_fp': 0,
                'env_fp_pct': 0.0}

    a = sqerr[alert]
    # ambiental pura: SO2_PPB domina el error Y ninguna señal de salud contribuye
    ppb_dominant = a.argmax(axis=1) == PPB_IDX
    health_quiet = (a[:, HEALTH_IDX] < HEALTH_CONTRIB_MIN).all(axis=1)
    env_fp = int((ppb_dominant & health_quiet).sum())

    return {
        'station_id': sid,
        'n_alerts': n_alert,
        'ppb_mean_contrib': round(float(a[:, PPB_IDX].mean()), 3),
        'health_mean_contrib': round(float(a[:, HEALTH_IDX].mean()), 3),
        'alerts_ppb_dominant': int(ppb_dominant.sum()),
        'env_fp': env_fp,
        'env_fp_pct': round(100 * env_fp / n_alert, 2),
    }


def main():
    df = joblib.load(DATASET)
    results = [r for r in (analyze_station(g) for _, g in df.groupby('station_id')) if r]

    total_alerts = sum(r['n_alerts'] for r in results)
    total_fp = sum(r['env_fp'] for r in results)
    overall = round(100 * total_fp / total_alerts, 2) if total_alerts else 0.0

    out = {
        'rule': ('Alerta ambiental pura = SO2_PPB domina el error de reconstrucción Y '
                 'ninguna señal de salud (flow/temp/lamp) contribuye por encima de '
                 f'{HEALTH_CONTRIB_MIN}. Estas son falsos positivos ambientales.'),
        'health_contrib_min': HEALTH_CONTRIB_MIN,
        'overall_env_fp_pct': overall,
        'total_alerts': total_alerts,
        'total_env_fp': total_fp,
        'stations': results,
    }
    with open(f'{REPORT_DIR}/environmental_fp.json', 'w') as f:
        json.dump(out, f, indent=2)

    print(f"{'estación':13s} {'alertas':>8s} {'ppb_contrib':>12s} "
          f"{'salud_contrib':>13s} {'FP_amb':>7s} {'FP_amb%':>8s}")
    for r in results:
        print(f"{r['station_id']:13s} {r['n_alerts']:>8} "
              f"{r.get('ppb_mean_contrib', 0):>12.3f} "
              f"{r.get('health_mean_contrib', 0):>13.3f} "
              f"{r['env_fp']:>7} {r['env_fp_pct']:>7.1f}%")
    print(f"\nFalsos positivos ambientales GLOBAL: {total_fp}/{total_alerts} ({overall}%)")
    print(f"JSON en {REPORT_DIR}/environmental_fp.json")


if __name__ == '__main__':
    main()
