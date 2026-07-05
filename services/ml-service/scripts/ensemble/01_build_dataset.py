"""
Fase 1 — Construcción del dataset multi-estación para el ensemble no supervisado.

Lee las 6 estaciones SO2 de services/ml-proposal/dataset/, arma un DataFrame
unificado con:
  - station_id
  - las 5 features del ensemble (4 base + hours_since_prev)
  - máscara is_normal (valido=1 ∧ variables base dentro de L2–L3)
  - split temporal por estación (train/test, sin mezclar estaciones)
  - StandardScaler por estación ajustado SOLO con rows normales de train

Descarta explícitamente rul_days (data leakage — SPEC §4.2).

Salidas:
  /tmp/hm_ensemble_dataset.parquet
  services/ml-service/ml_artifacts_ensemble_v1/scaler_<station>.pkl

Referencia de diseño: docs/spec-health-monitor-unsupervised.md (§2.1, §4, §7)
                       docs/plan-health-monitor-unsupervised.md (Fase 1)
"""
import glob
import json
import os

import joblib
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler

RANDOM_SEED = 42
np.random.seed(RANDOM_SEED)

DATASET_DIR = 'services/ml-proposal/dataset'
# Artefacto intermedio del pipeline. Se usa joblib (pickle comprimido) en vez de
# parquet para no añadir dependencia (pyarrow/fastparquet no están en el entorno
# y el plan es no introducir dependencias nuevas). Lo leen las fases 2/3.
OUT_DATASET = '/tmp/hm_ensemble_dataset.joblib'
ART_DIR = 'services/ml-service/ml_artifacts_ensemble_v1'
REPORT_DIR = 'reports/health_monitor_ensemble'
os.makedirs(ART_DIR, exist_ok=True)
os.makedirs(REPORT_DIR, exist_ok=True)

# 4 features base comunes a las 6 estaciones (verificado en Fase 0.4).
BASE_FEATURES = ['SO2_PPB', 'SO2_FLOW', 'SO2_INTERNAL_TEMP', 'SO2_LAMP_INT']
# La 5.ª feature se calcula (hours_since_prev). Total = 5. (6.ª reservada, no v1.)
ENSEMBLE_FEATURES = BASE_FEATURES + ['hours_since_prev']

# Límites operativos L2–L3 (SPEC §2.1 / ml.md). Derivados de CA-ILO-01.
# NOTA (Fase 1, hallazgo): estos límites NO generalizan entre estaciones —
# p.ej. SO2_LAMP_INT en Grau/Garcilaso opera a ~102 (vs L3=100 de Ilo), lo que
# no es una falla sino otra escala de operación del equipo. Por eso, coherente
# con el enfoque NO supervisado, "normal" se define como valido=1 (transmisión
# válida) y NO por límites físicos globales. El filtro por límites queda
# disponible pero DESACTIVADO por defecto (evita sesgar a cero las estaciones
# con otra escala). Ver SPEC §9.1 (shift de distribución entre estaciones).
USE_LIMIT_FILTER = False
LIMITS_L2_L3 = {
    'SO2_PPB':           (1.0, 388.0),
    'SO2_FLOW':          (0.0, 2.5),
    'SO2_INTERNAL_TEMP': (8.0, 47.0),
    'SO2_LAMP_INT':      (20.0, 100.0),
}

SAMPLE_MINUTES = 5          # muestreo regular verificado (Fase 0.4)
TEST_FRACTION = 0.20        # último 20% de la línea de tiempo de CADA estación

# Estaciones excluidas del entrenamiento del ensemble v1 (con justificación).
# CA-CHILLO-01: varianza colapsada en su train (std SO2_FLOW≈0.033, LAMP_INT≈0.084)
#   -> el scaler/IF aprenden fronteras hiper-estrechas y marcan ~46% del test como
#   anómalo (artefacto de normalización, NO calidad de datos: 91.8% válido). Requiere
#   re-entrenamiento sobre ventana reciente. Ver reports/health_monitor_ensemble/README.md §4.
EXCLUDED_STATIONS = {'CA-CHILLO-01'}


def station_id_from_filename(path):
    """CA-ILO-01_BOLOGNESI_DATASET.csv -> CA-ILO-01"""
    base = os.path.basename(path)
    return base.split('_')[0]


def load_station(path):
    sid = station_id_from_filename(path)
    # Leer solo lo necesario: date, valido, features base. rul_days NO se lee
    # (anti-leakage). ciclo_id se conserva como metadato.
    wanted = ['date', 'valido', 'ciclo_id'] + BASE_FEATURES
    df = pd.read_csv(path, usecols=lambda c: c in wanted)
    df['station_id'] = sid
    df['date'] = pd.to_datetime(df['date'], errors='coerce')
    df = df.dropna(subset=['date'])
    # valido viene como bool (True/False) -> 0/1 entero
    df['valido'] = df['valido'].astype(bool).astype(int)
    df = (df.sort_values('date')
            .drop_duplicates(subset='date', keep='last')
            .reset_index(drop=True))
    for c in BASE_FEATURES:
        df[c] = pd.to_numeric(df[c], errors='coerce')
    return df


def build_hours_since_prev(df):
    """SPEC §4.3 — horas desde el fin de la última FALLA (valido 1->0->...->1).

    Offline, por conteo de filas × 5 min (muestreo regular verificado).
    Es un contador que se resetea a 0 al terminar cada falla y crece 5 min/fila.
    NaN antes de la primera falla.
    """
    df = df.sort_values('date').reset_index(drop=True)
    is_fail = (df['valido'].values == 0)
    n = len(df)
    hsp = np.full(n, np.nan)
    last_end = None
    in_fail = False
    for i in range(n):
        if is_fail[i]:
            in_fail = True
        else:
            if in_fail:              # esta fila (valido=1) marca el FIN de la falla
                last_end = i
            in_fail = False
            if last_end is not None:
                hsp[i] = (i - last_end) * SAMPLE_MINUTES / 60.0
    df['hours_since_prev'] = hsp
    return df


def build_is_normal(df):
    """is_normal = valido=1 (transmisión válida) y features base no-NaN.

    El filtro adicional por límites L2–L3 solo se aplica si USE_LIMIT_FILTER=True
    (desactivado por defecto: los límites de Ilo no generalizan entre estaciones,
    ver nota en LIMITS_L2_L3). El ensemble aprende el "normal" de cada estación
    desde sus propios datos, no desde límites físicos globales.
    """
    normal = (df['valido'].values == 1)
    # exigir features base presentes (no-NaN) para poder escalar/entrenar
    for col in BASE_FEATURES:
        normal &= ~np.isnan(df[col].values)
    if USE_LIMIT_FILTER:
        for col, (lo, hi) in LIMITS_L2_L3.items():
            v = df[col].values
            within = np.ones(len(df), dtype=bool)
            if lo is not None:
                within &= (v >= lo)
            if hi is not None:
                within &= (v <= hi)
            normal &= within
    df['is_normal'] = normal
    return df


def temporal_split(df):
    """Split temporal por estación: primeros 80% train, últimos 20% test.
    Nunca aleatorio, nunca mezcla estaciones."""
    df = df.sort_values('date').reset_index(drop=True)
    n = len(df)
    cut = int(n * (1 - TEST_FRACTION))
    split = np.array(['train'] * n, dtype=object)
    split[cut:] = 'test'
    df['split'] = split
    return df


def main():
    all_files = sorted(glob.glob(os.path.join(DATASET_DIR, '*.csv')))
    assert all_files, f'No se encontraron CSV en {DATASET_DIR}'
    files = [f for f in all_files
             if station_id_from_filename(f) not in EXCLUDED_STATIONS]
    excluded = sorted(EXCLUDED_STATIONS)
    print(f'Estaciones encontradas: {len(all_files)} | usadas: {len(files)} | '
          f'excluidas: {excluded}')

    frames = []
    summary = []
    for f in files:
        sid = station_id_from_filename(f)
        df = load_station(f)
        df = build_hours_since_prev(df)
        df = build_is_normal(df)
        df = temporal_split(df)

        # Scaler POR ESTACIÓN, ajustado solo con rows normales de TRAIN.
        # hours_since_prev NaN (antes de la 1.ª falla) -> mediana de train-normal.
        train_normal = df[(df['split'] == 'train') & (df['is_normal'])].copy()
        hsp_median = train_normal['hours_since_prev'].median()
        for part in (df, train_normal):
            part['hours_since_prev'] = part['hours_since_prev'].fillna(hsp_median)

        scaler = StandardScaler()
        scaler.fit(train_normal[ENSEMBLE_FEATURES].values)
        joblib.dump(scaler, os.path.join(ART_DIR, f'scaler_{sid}.pkl'))

        frames.append(df)
        summary.append({
            'station_id': sid,
            'rows': int(len(df)),
            'date_min': str(df['date'].min()),
            'date_max': str(df['date'].max()),
            'valido_1': int((df['valido'] == 1).sum()),
            'valido_0': int((df['valido'] == 0).sum()),
            'is_normal': int(df['is_normal'].sum()),
            'is_normal_pct': round(100 * df['is_normal'].mean(), 2),
            'train_rows': int((df['split'] == 'train').sum()),
            'test_rows': int((df['split'] == 'test').sum()),
            'train_normal_rows': int(len(train_normal)),
            'hsp_median_h': round(float(hsp_median), 2) if pd.notna(hsp_median) else None,
        })
        print(f"  {sid:12s} rows={len(df):>7} normal={df['is_normal'].mean()*100:5.1f}% "
              f"train_normal={len(train_normal):>6} hsp_med={hsp_median:.1f}h")

    full = pd.concat(frames, ignore_index=True)

    # Anti-leakage: garantizar que rul_days NO está entre las columnas.
    assert 'rul_days' not in full.columns, 'rul_days no debe estar en el dataset'
    assert all(c in full.columns for c in ENSEMBLE_FEATURES), 'faltan features del ensemble'

    joblib.dump(full, OUT_DATASET, compress=3)
    with open(os.path.join(REPORT_DIR, 'dataset_summary.json'), 'w') as fh:
        json.dump({
            'random_seed': RANDOM_SEED,
            'excluded_stations': sorted(EXCLUDED_STATIONS),
            'ensemble_features': ENSEMBLE_FEATURES,
            'sample_minutes': SAMPLE_MINUTES,
            'test_fraction': TEST_FRACTION,
            'use_limit_filter': USE_LIMIT_FILTER,
            'is_normal_definition': 'valido=1 & features base no-NaN'
                                    + (' & dentro de L2-L3' if USE_LIMIT_FILTER else ''),
            'rul_days_dropped': True,
            'stations': summary,
        }, fh, indent=2)

    print(f'\nDataset unificado: {len(full)} filas, {len(files)} estaciones')
    print(f'Guardado en {OUT_DATASET}')
    print(f'Scalers por estación en {ART_DIR}/scaler_<station>.pkl')
    print(f'Resumen en {REPORT_DIR}/dataset_summary.json')
    print('Anti-leakage OK: rul_days ausente; features del ensemble presentes.')


if __name__ == '__main__':
    main()
