"""
P1 / Fase 3.5 — Solapamiento del ensemble no supervisado vs baseline RF M1.

Pregunta que responde (SPEC §8): ¿el ensemble no supervisado detecta lo mismo que
el clasificador SUPERVISADO M1 (precisión 98% en FALLA), sin necesitar etiquetas de
falla? Es el argumento central de por qué el enfoque no supervisado es válido.

Metodología:
  - Estación común: CA-ILO-01 (única con la que M1 fue entrenado/validado).
  - Se reconstruyen las 27 features que espera M1 sobre el MISMO dataset del ensemble
    (mismo orden que 01_build_dataset.py del PoC).
  - Se comparan, sobre el holdout test con transmisión (valido=1):
      * M1: predice FALLA vs NORMAL
      * Ensemble: alerta (OBSERVADO/EN_RIESGO/CRITICO) vs SANO, con θ recalibrado
  - Matriz de acuerdo + métricas de solapamiento.

Salida: reports/health_monitor_ensemble/baseline_overlap.md (+ .json)
"""
import importlib.util
import json
import os
import warnings

import joblib
import numpy as np

warnings.filterwarnings('ignore')

ART = 'services/ml-service/ml_artifacts_ensemble_v1'
M1_PATH = 'services/ml-service/ml_artifacts_health_monitor/m1_binary.pkl'
DATASET = '/tmp/hm_ensemble_dataset.joblib'
REPORT_DIR = 'reports/health_monitor_ensemble'
STATION = 'CA-ILO-01'

ENS_FEATS = ['SO2_PPB', 'SO2_FLOW', 'SO2_INTERNAL_TEMP', 'SO2_LAMP_INT', 'hours_since_prev']
BASE = ['SO2_PPB', 'SO2_FLOW', 'SO2_INTERNAL_TEMP', 'SO2_LAMP_INT']
WARMUP_ROWS = 4032
THETA_PCT = 95

_spec = importlib.util.spec_from_file_location('ens', f'{os.path.dirname(__file__)}/04_ensemble.py')
ens = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(ens)


def build_m1_features(df):
    """Reconstruye las 27 features de M1 en el MISMO orden que el PoC
    (01_build_dataset.py build_features)."""
    df = df.sort_values('date').reset_index(drop=True).copy().set_index('date')
    cols = []
    # 12 medias (1h,6h,24h × 4 base)
    for win, n in [('1h', 12), ('6h', 72), ('24h', 288)]:
        for c in BASE:
            name = f'{c}_mean_{win}'
            df[name] = df[c].rolling(n, min_periods=max(2, n // 4)).mean()
            cols.append(name)
    # 8 std (1h,6h × 4 base)
    for win, n in [('1h', 12), ('6h', 72)]:
        for c in BASE:
            name = f'{c}_std_{win}'
            df[name] = df[c].rolling(n, min_periods=max(2, n // 4)).std()
            cols.append(name)
    # 2 ratios
    df['FLOW_per_LAMP'] = df['SO2_FLOW'] / df['SO2_LAMP_INT'].replace(0, np.nan)
    df['TEMP_per_LAMP'] = df['SO2_INTERNAL_TEMP'] / df['SO2_LAMP_INT'].replace(0, np.nan)
    cols += ['FLOW_per_LAMP', 'TEMP_per_LAMP']
    # op_point_dist (7d)
    op_window = 12 * 24 * 7
    op_dist = np.zeros(len(df))
    for c in BASE:
        ref = df[c].rolling(op_window, min_periods=288).median()
        sigma = df[c].rolling(op_window, min_periods=288).std()
        z = (df[c] - ref) / sigma.replace(0, np.nan)
        op_dist += np.abs(z.fillna(0))
    df['op_point_dist'] = op_dist
    cols.append('op_point_dist')
    # orden final M1: 4 base + los 23 anteriores = 27
    feat_order = BASE + cols
    return df.reset_index(), feat_order


def main():
    df_all = joblib.load(DATASET)
    g = df_all[df_all['station_id'] == STATION].copy()

    # --- features M1 (27) sobre CA-ILO-01 completo ---
    gm, feat_order = build_m1_features(g)
    assert len(feat_order) == 27, f'esperaba 27 features, hay {len(feat_order)}'

    # --- ensemble: cargar artefactos de la estación ---
    scaler = joblib.load(f'{ART}/scaler_{STATION}.pkl')
    ae = joblib.load(f'{ART}/autoencoder_{STATION}.pkl')
    iforest = joblib.load(f'{ART}/iforest_{STATION}.pkl')
    cfg = ens.load_config()

    # --- restringir al holdout test con transmisión y features completas ---
    te = gm[gm['split'] == 'test'].sort_values('date')
    m1_ok = te[feat_order].notna().all(axis=1).values
    ens_ok = te[ENS_FEATS].notna().all(axis=1).values
    valido = te['valido'].values == 1
    mask = valido & m1_ok & ens_ok
    sub = te[mask]
    n = len(sub)
    assert n > 1000, f'muy pocas filas comparables: {n}'

    # --- M1: FALLA=1, NORMAL=0 ---
    Xm1 = sub[feat_order].values
    m1 = joblib.load(M1_PATH)
    m1_pred = m1.predict(Xm1)
    m1_alert = (m1_pred == 'FALLA')

    # --- ensemble: alerta si and_alert (θ recalibrado warm-up) ---
    Xe = scaler.transform(sub[ENS_FEATS].values)
    err = ens.compute_recon_error(ae, Xe)
    ifa = (iforest.predict(Xe) == -1)
    warm = min(WARMUP_ROWS, len(err) // 4)
    theta = float(np.percentile(err[:warm], THETA_PCT))
    ens_alert = (err > theta) & ifa

    # --- matriz de acuerdo ---
    both = int(np.sum(m1_alert & ens_alert))
    only_m1 = int(np.sum(m1_alert & ~ens_alert))
    only_ens = int(np.sum(~m1_alert & ens_alert))
    neither = int(np.sum(~m1_alert & ~ens_alert))
    agree = both + neither
    # Jaccard sobre "alerta" (unión de positivos)
    union_pos = both + only_m1 + only_ens
    jaccard = both / union_pos if union_pos else 0.0
    # De lo que M1 marca como alerta, ¿qué fracción también marca el ensemble?
    recall_vs_m1 = both / (both + only_m1) if (both + only_m1) else 0.0

    result = {
        'station': STATION,
        'n_compared': n,
        'm1_alert_rate_pct': round(100 * m1_alert.mean(), 2),
        'ensemble_alert_rate_pct': round(100 * ens_alert.mean(), 2),
        'agreement_pct': round(100 * agree / n, 2),
        'jaccard_alerts': round(jaccard, 3),
        'ensemble_recall_vs_m1_pct': round(100 * recall_vs_m1, 2),
        'confusion': {
            'both_alert': both, 'only_m1': only_m1,
            'only_ensemble': only_ens, 'neither': neither,
        },
        'note': ('M1 alerta = clase FALLA (transmisión perdida, señal supervisada). '
                 'Ensemble alerta = anomalía de salud confirmada por AND. Son señales '
                 'RELACIONADAS pero no idénticas: M1 detecta pérdida de transmisión; '
                 'el ensemble detecta desviación de salud en operación normal.'),
    }
    with open(f'{REPORT_DIR}/baseline_overlap.json', 'w') as f:
        json.dump(result, f, indent=2)

    print(f"Estación: {STATION} | filas comparadas (test, valido=1): {n}")
    print(f"  Tasa alerta M1 (FALLA):      {result['m1_alert_rate_pct']:.2f}%")
    print(f"  Tasa alerta ensemble:        {result['ensemble_alert_rate_pct']:.2f}%")
    print(f"  Acuerdo global:              {result['agreement_pct']:.2f}%")
    print(f"  Jaccard (alertas):           {result['jaccard_alerts']:.3f}")
    print(f"  Recall ensemble vs M1-FALLA: {result['ensemble_recall_vs_m1_pct']:.2f}%")
    print(f"  Matriz: {result['confusion']}")
    print(f"\nJSON en {REPORT_DIR}/baseline_overlap.json")
    return result


if __name__ == '__main__':
    main()
