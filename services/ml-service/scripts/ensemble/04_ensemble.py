"""
Fase 2.4 — Módulo compartido del ensemble: gate + AND + graduación de severidad.

Implementa el flujo del SPEC:
  §3.0  gate de transmisión (valido=0 -> SIN_DATOS, sin ejecutar detectores)
  §3.4  compuerta AND (alerta solo si AE y IF coinciden)
  §3.5  graduación de severidad por múltiplos de θ (θ, 2θ, 3θ)

θ y contamination son CONFIGURABLES por estación (decisión §8.4 del plan),
leídos de ensemble_config.json + theta_<station>.json.

Este módulo NO entrena; lo consumen las fases 3 (evaluación) y 4 (inferencia).
"""
import json
import os

import joblib
import numpy as np

ART_DIR = os.environ.get('ENSEMBLE_ARTIFACTS_PATH',
                         'services/ml-service/ml_artifacts_ensemble_v1')

# Estados (SPEC §5). SIN_DATOS y SANO no son alerta.
STATE_SIN_DATOS = 'SIN_DATOS'
STATE_SANO = 'SANO'
STATE_OBSERVADO = 'OBSERVADO'    # θ < error <= 2θ  (Advertencia)
STATE_EN_RIESGO = 'EN_RIESGO'    # 2θ < error <= 3θ (Alerta)
STATE_CRITICO = 'CRITICO'        # error > 3θ        (Crítico)

DEFAULT_CONFIG = {
    'contamination': 0.05,       # SPEC §3.3 (default Anexo)
    'theta_percentile': 95,      # SPEC §3.2 (default Anexo)
    'severity_multipliers': {'observado': 1.0, 'en_riesgo': 2.0, 'critico': 3.0},
}


def load_config():
    path = os.path.join(ART_DIR, 'ensemble_config.json')
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return DEFAULT_CONFIG


def load_theta(station_id):
    """θ ACTIVO por estación (SPEC §3.2). Tras P4 es el recalibrado. Fallback None."""
    path = os.path.join(ART_DIR, f'theta_{station_id}.json')
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)['theta']
    return None


def load_theta_train(station_id):
    """θ original del train (para auditoría / comparación). Cae a 'theta' si no existe."""
    path = os.path.join(ART_DIR, f'theta_{station_id}.json')
    if os.path.exists(path):
        with open(path) as f:
            meta = json.load(f)
            return meta.get('theta_train', meta['theta'])
    return None


def grade_severity(recon_error, theta, mult):
    """SPEC §3.5 — devuelve (state, severity) para una lectura que YA pasó el gate
    y que el AND confirmó como alerta. Si error<=θ -> SANO (no pasa AND)."""
    if recon_error <= theta * mult['observado']:
        return STATE_SANO, None
    if recon_error <= theta * mult['en_riesgo']:
        return STATE_OBSERVADO, 'Advertencia'
    if recon_error <= theta * mult['critico']:
        return STATE_EN_RIESGO, 'Alerta'
    return STATE_CRITICO, 'Crítico'


def evaluate_reading(valido, recon_error, if_anomaly, theta, config=None):
    """Evalúa UNA lectura y devuelve el dict de salida (SPEC §6.2).

    valido      : int 0/1 (o bool) — flag de transmisión
    recon_error : float o None      — MSE del AE (None si gate cerrado)
    if_anomaly  : bool o None       — Isolation Forest marcó anómalo
    theta       : float             — umbral de la estación
    """
    config = config or DEFAULT_CONFIG
    mult = config['severity_multipliers']

    # §3.0 GATE de transmisión: valido=0 -> SIN_DATOS, sin alerta, sin ejecutar.
    if int(valido) == 0:
        return {
            'recon_error': None, 'theta': theta, 'if_anomaly': None,
            'and_alert': False, 'severity': None, 'health_state': STATE_SIN_DATOS,
        }

    # §3.4 compuerta AND: alerta solo si AE (error>θ) Y IF coinciden.
    ae_flag = recon_error > theta
    and_alert = bool(ae_flag and if_anomaly)

    if not and_alert:
        # SANO (o falso positivo evitado por el AND) — sin alerta.
        return {
            'recon_error': float(recon_error), 'theta': theta,
            'if_anomaly': bool(if_anomaly), 'and_alert': False,
            'severity': None, 'health_state': STATE_SANO,
        }

    # §3.5 graduación (solo si AND confirmó).
    state, severity = grade_severity(recon_error, theta, mult)
    return {
        'recon_error': float(recon_error), 'theta': theta,
        'if_anomaly': bool(if_anomaly), 'and_alert': True,
        'severity': severity, 'health_state': state,
    }


def compute_recon_error(autoencoder, X):
    """recon_error por fila = mean((X - X̂)^2, axis=1) (SPEC §3.2)."""
    X_hat = autoencoder.predict(X)
    return np.mean((X - X_hat) ** 2, axis=1)


if __name__ == '__main__':
    # Smoke test de la lógica de gate/AND/graduación con θ=0.02.
    cfg = DEFAULT_CONFIG
    theta = 0.02
    cases = [
        (0, None, None,  'sin transmisión -> SIN_DATOS'),
        (1, 0.010, True, 'error<θ -> SANO (no pasa AND)'),
        (1, 0.030, False, 'error>θ pero IF=No -> SANO (FP evitado)'),
        (1, 0.030, True, 'θ<error<=2θ + AND -> OBSERVADO'),
        (1, 0.050, True, '2θ<error<=3θ + AND -> EN_RIESGO'),
        (1, 0.080, True, 'error>3θ + AND -> CRITICO'),
    ]
    for valido, err, ifa, desc in cases:
        out = evaluate_reading(valido, err, ifa, theta, cfg)
        print(f"{desc:45s} -> {out['health_state']:10s} alert={out['and_alert']} sev={out['severity']}")
