# -*- coding: utf-8 -*-
"""
Regeneración de datos de demo alineados al ensemble no supervisado (v3).

CONTEXTO: el sistema abandonó el modelo RUL supervisado (predicciones RF + RUL en
días) por el ensemble no supervisado (AE+IF+AND → estados SANO/OBSERVADO/EN_RIESGO/
CRITICO/SIN_DATOS). Los datos de demo actuales (equipos T101-T109 + predicciones RUL)
son incoherentes con el sistema nuevo. Este script los regenera con datos REALES.

QUÉ PRESERVA (datos maestro — NO se tocan):
  - usuarios + password_hash (auth)
  - proveedores_calibracion, repuestos, dataloggers (catálogos)

QUÉ REGENERA (en orden de dependencias):
  1. equipos          → T101-T109 fuera; 5 estaciones reales CA-* dentro
  2. lecturas_iot     → replay de tramos de los CSV reales por estación
  3. health_readings + health_device_state → pasando lecturas por el ensemble
  4. incidencias/calibraciones → derivadas de rachas CRITICO/EN_RIESGO
  5. purga            → predicciones + alertas del modelo RUL viejo (ya no aplican)

USO (requiere stack Docker arriba, BD accesible):
    python scripts/regenerate_demo_data.py --confirm
    python scripts/regenerate_demo_data.py --confirm --rows 800   # lecturas/estación

Es idempotente: re-ejecutar deja el mismo estado (borra lo regenerado antes de recrear).
"""
from __future__ import annotations

import argparse
import json
import os
import sys

import joblib
import numpy as np
import pandas as pd
from sqlalchemy import create_engine, text

# --- ensemble: reutilizar la lógica de evaluación del servicio ---
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'services', 'ml-service'))

DB_URL = os.environ.get(
    'DATABASE_URL', 'postgresql://airmon:airmon123@localhost:5432/airmonitoring')
# Rutas configurables por env (para correr dentro del contenedor, donde difieren).
DATASET_DIR = os.environ.get('DEMO_DATASET_DIR', 'services/ml-proposal/dataset')
ART_DIR = os.environ.get('ENSEMBLE_ARTIFACTS_PATH',
                         'services/ml-service/ml_artifacts_ensemble_v1')
ENSEMBLE_MODULE = os.environ.get(
    'ENSEMBLE_MODULE', 'services/ml-service/scripts/ensemble/04_ensemble.py')
FEATS = ['SO2_PPB', 'SO2_FLOW', 'SO2_INTERNAL_TEMP', 'SO2_LAMP_INT', 'hours_since_prev']
MODEL_VERSION = 'vigishield-ensemble-v1'  # coherente con health_service.py

# device_id = código de estación real (decisión: migrar T10x -> CA-*).
STATIONS = [
    {'device_id': 'CA-ILO-01', 'nombre': 'Estación Bolognesi - Ilo',
     'ubicacion': 'Bolognesi, Ilo, Moquegua', 'serie': '1200416204',
     'codigo_interno': '61-0028', 'csv': 'CA-ILO-01_BOLOGNESI_DATASET.csv'},
    {'device_id': 'CA-CC-01', 'nombre': 'Estación La Oroya',
     'ubicacion': 'La Oroya, Junín', 'serie': 'CC01-SO2',
     'codigo_interno': '61-0031', 'csv': 'CA-CC-01_OROYA_DATASET.csv'},
    {'device_id': 'CA-CH-04', 'nombre': 'Estación Grau',
     'ubicacion': 'Grau', 'serie': 'CH04-SO2',
     'codigo_interno': '61-0044', 'csv': 'CA-CH-04_GRAU_DATASET.csv'},
    {'device_id': 'CA-CH-05', 'nombre': 'Estación Garcilaso',
     'ubicacion': 'Garcilaso', 'serie': 'CH05-SO2',
     'codigo_interno': '61-0045', 'csv': 'CA-CH-05_GARCILASO_DATASET.csv'},
    {'device_id': 'CA-UCHU-01', 'nombre': 'Estación Uchucarcco',
     'ubicacion': 'Uchucarcco, Cusco', 'serie': 'UCHU-SO2',
     'codigo_interno': '61-0071', 'csv': 'CA-UCHU-01_UCHUCARCCO_DATASET.csv'},
]
MODELO, MARCA, PARAM, RANGO = 'Thermo 43i', 'Thermo Scientific', 'SO2', '0-1000 ppb'


def load_ensemble():
    import importlib.util
    spec = importlib.util.spec_from_file_location('ens', ENSEMBLE_MODULE)
    ens = importlib.util.module_from_spec(spec); spec.loader.exec_module(ens)
    return ens


def read_station_csv(csv_name):
    path = os.path.join(DATASET_DIR, csv_name)
    base = ['SO2_PPB', 'SO2_FLOW', 'SO2_INTERNAL_TEMP', 'SO2_LAMP_INT']
    df = pd.read_csv(path, usecols=lambda c: c in (['date', 'valido'] + base))
    df['date'] = pd.to_datetime(df['date'], errors='coerce')
    df = df.dropna(subset=['date'])
    df['valido'] = df['valido'].astype(bool).astype(int)
    df = df.sort_values('date').drop_duplicates('date').reset_index(drop=True)
    for c in base:
        df[c] = pd.to_numeric(df[c], errors='coerce')
    return df


def pick_representative_window(df, rows):
    """Elige la ventana de `rows` filas con MAYOR % de transmisión (valido=1),
    preferiendo las más recientes en caso de empate. Evita apagones terminales
    (p.ej. el CSV de UCHU-01 termina en 3 días sin transmisión) sin dejar de usar
    datos reales. Recorre en pasos para no ser O(n²)."""
    n = len(df)
    if n <= rows:
        return df.reset_index(drop=True)
    valido = df['valido'].values
    step = max(1, rows // 8)
    best_start, best_score = 0, -1.0
    for start in range(0, n - rows + 1, step):
        score = valido[start:start + rows].mean()
        # >= favorece ventanas más recientes ante empate
        if score >= best_score:
            best_score, best_start = score, start
    return df.iloc[best_start:best_start + rows].reset_index(drop=True)


def hours_since_prev_offline(df):
    isf = (df['valido'].values == 0); n = len(df)
    hsp = np.full(n, np.nan); le = None; inf = False
    for i in range(n):
        if isf[i]:
            inf = True
        else:
            if inf:
                le = i
            inf = False
            if le is not None:
                hsp[i] = (i - le) * 5 / 60
    return hsp


# --------------------------------------------------------------------------
# Fases de regeneración
# --------------------------------------------------------------------------
def purge_transactional(conn):
    """Borra datos transaccionales regenerables (respetando FK). Preserva maestros."""
    print('  Purgando datos transaccionales...')
    # dependientes primero
    for tbl in ['health_readings', 'health_device_state',
                'alertas', 'predicciones',
                'mantenimiento_repuestos', 'mantenimientos_correctivos',
                'calibraciones', 'incidencias',
                'lecturas_iot']:
        try:
            conn.execute(text(f'DELETE FROM {tbl}'))
            print(f'    {tbl}: limpiada')
        except Exception as e:
            print(f'    {tbl}: omitida ({type(e).__name__})')


def regen_equipos(conn):
    """T10x fuera, 5 estaciones CA-* dentro. Devuelve {device_id: id}."""
    print('  Regenerando equipos (T10x -> CA-*)...')
    conn.execute(text('DELETE FROM equipos'))
    ids = {}
    for s in STATIONS:
        r = conn.execute(text("""
            INSERT INTO equipos (device_id, nombre, tipo, ubicacion, estado,
                serie, codigo_interno, modelo, marca, parametro_medicion, rango_medicion)
            VALUES (:d, :n, :t, :u, 'activo', :se, :ci, :mo, :ma, :pa, :ra)
            RETURNING id
        """), {'d': s['device_id'], 'n': s['nombre'], 't': MODELO,
               'u': s['ubicacion'], 'se': s['serie'], 'ci': s['codigo_interno'],
               'mo': MODELO, 'ma': MARCA, 'pa': PARAM, 'ra': RANGO})
        ids[s['device_id']] = r.scalar()
    print(f'    {len(ids)} estaciones creadas: {list(ids)}')
    return ids


def regen_readings_and_health(conn, equipo_ids, ens, rows):
    """Replay del tail de cada CSV -> lecturas_iot + health_readings + estado.
    Devuelve, por estación, la secuencia de estados publicados (para derivar incidencias)."""
    print(f'  Regenerando lecturas + salud (replay {rows} filas/estación)...')
    cfg = ens.load_config()
    seq_by_device = {}
    for s in STATIONS:
        dev = s['device_id']
        eq_id = equipo_ids[dev]
        theta = ens.load_theta(dev)
        if theta is None:
            print(f'    {dev}: sin artefactos de ensemble, omitida')
            continue
        scaler = joblib.load(f'{ART_DIR}/scaler_{dev}.pkl')
        ae = joblib.load(f'{ART_DIR}/autoencoder_{dev}.pkl')
        iforest = joblib.load(f'{ART_DIR}/iforest_{dev}.pkl')

        df = read_station_csv(s['csv'])
        df['hours_since_prev'] = hours_since_prev_offline(df)
        med = df['hours_since_prev'].median()
        df['hours_since_prev'] = df['hours_since_prev'].fillna(med)
        # ventana representativa (más transmisión), no el tail ciego
        tail = pick_representative_window(df, rows)

        states = []
        for _, row in tail.iterrows():
            ts = row['date']
            valido = int(row['valido'])
            feats_ok = all(pd.notna(row[c]) for c in
                           ['SO2_PPB', 'SO2_FLOW', 'SO2_INTERNAL_TEMP', 'SO2_LAMP_INT'])
            # lectura IoT cruda (esquema real: sensores en JSON `sensors`)
            sensors = json.dumps({
                'so2_ppb': _f(row['SO2_PPB']), 'so2_flow': _f(row['SO2_FLOW']),
                'so2_internal_temp': _f(row['SO2_INTERNAL_TEMP']),
                'so2_lamp_int': _f(row['SO2_LAMP_INT']), 'valido': valido,
            })
            conn.execute(text("""
                INSERT INTO lecturas_iot (device_id, timestamp_lectura, sensors,
                    raw_payload, procesado)
                VALUES (:d, :ts, CAST(:sensors AS JSON), CAST(:raw AS JSON), true)
            """), {'d': eq_id, 'ts': ts, 'sensors': sensors, 'raw': sensors})

            # evaluar por el ensemble
            if valido == 0 or not feats_ok:
                out = ens.evaluate_reading(0, None, None, theta, cfg)
                hsp = None
            else:
                X = scaler.transform([[row['SO2_PPB'], row['SO2_FLOW'],
                                       row['SO2_INTERNAL_TEMP'], row['SO2_LAMP_INT'],
                                       row['hours_since_prev']]])
                err = float(np.mean((X - ae.predict(X)) ** 2))
                ifa = bool(iforest.predict(X)[0] == -1)
                out = ens.evaluate_reading(1, err, ifa, theta, cfg)
                hsp = float(row['hours_since_prev'])
            states.append(out['health_state'])

            conn.execute(text("""
                INSERT INTO health_readings (device_id, reading_timestamp, recon_error,
                    theta, if_anomaly, and_alert, severity, health_state,
                    hours_since_prev, model_version)
                VALUES (:d, :ts, :re, :th, :ifa, :aa, :sev, :hs, :hsp, :mv)
            """), {'d': dev, 'ts': ts, 're': out['recon_error'], 'th': theta,
                   'ifa': out['if_anomaly'], 'aa': out['and_alert'],
                   'sev': out['severity'], 'hs': out['health_state'],
                   'hsp': hsp, 'mv': MODEL_VERSION})

        # estado vigente = último
        last = states[-1] if states else 'SIN_DATOS'
        conn.execute(text("""
            INSERT INTO health_device_state (device_id, health_state, updated_at)
            VALUES (:d, :hs, :ts)
        """), {'d': dev, 'hs': last, 'ts': tail['date'].iloc[-1]})
        seq_by_device[dev] = states
        n_alert = sum(1 for st in states if st in ('OBSERVADO', 'EN_RIESGO', 'CRITICO'))
        print(f'    {dev}: {len(states)} lecturas, estado final={last}, {n_alert} en alerta')
    return seq_by_device


def derive_incidencias(conn, seq_by_device):
    """Deriva incidencias correctivas de EPISODIOS de alerta (EN_RIESGO/CRITICO
    sostenidos). Un episodio tolera huecos cortos (GAP_TOL lecturas no-alerta) para
    no partirse por una sola lectura que volvió a SANO — lo que importa es la
    persistencia del problema, no que sea estrictamente contiguo."""
    print('  Derivando incidencias/calibraciones de los estados...')
    RACHA_MIN = 6   # nº de lecturas de alerta que definen un episodio
    GAP_TOL = 2     # huecos cortos tolerados dentro del episodio
    n_inc = 0
    for dev, states in seq_by_device.items():
        run = 0          # lecturas de alerta acumuladas en el episodio
        gap = 0          # huecos consecutivos no-alerta
        triggered = False
        for st in states:
            if st in ('EN_RIESGO', 'CRITICO'):
                run += 1
                gap = 0
                if run >= RACHA_MIN and not triggered:
                    conn.execute(text("""
                        INSERT INTO incidencias (device_id, tipo, descripcion, estado, prioridad)
                        VALUES (:d, 'correctiva',
                            'Anomalía de salud sostenida detectada por el monitor predictivo (ensemble).',
                            'pendiente', :p)
                    """), {'d': dev, 'p': 'alta' if 'CRITICO' in states else 'media'})
                    n_inc += 1
                    triggered = True
            else:
                gap += 1
                if gap > GAP_TOL:   # episodio cerrado -> reset
                    run = 0
    print(f'    {n_inc} incidencias correctivas derivadas.')


def _f(v):
    return float(v) if pd.notna(v) else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--confirm', action='store_true',
                    help='requerido: confirma que se borrarán datos transaccionales')
    ap.add_argument('--rows', type=int, default=800,
                    help='lecturas por estación a reproducir (default 800 = ~3 días)')
    ap.add_argument('--db', default=DB_URL)
    args = ap.parse_args()

    if not args.confirm:
        print('ABORTADO: este script BORRA datos transaccionales. Re-ejecuta con --confirm.')
        print('  Preserva: usuarios, proveedores, repuestos, dataloggers.')
        print('  Regenera: equipos (CA-*), lecturas, salud, incidencias.')
        sys.exit(1)

    ens = load_ensemble()
    engine = create_engine(args.db)
    print(f'Conectando a {args.db.split("@")[-1]}...')
    with engine.begin() as conn:
        purge_transactional(conn)
        equipo_ids = regen_equipos(conn)
        seq = regen_readings_and_health(conn, equipo_ids, ens, args.rows)
        derive_incidencias(conn, seq)
    print('\n✓ Regeneración completa. Datos maestro preservados.')


if __name__ == '__main__':
    main()
