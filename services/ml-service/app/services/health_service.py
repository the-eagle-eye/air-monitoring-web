"""
Fase 4 — Servicio de inferencia del ensemble no supervisado (streaming).

Implementa el flujo del SPEC por lectura:
  §3.0  gate de transmisión (valido=0 o feature faltante -> SIN_DATOS, sin ejecutar)
  §4.4  hours_since_prev online sobre timestamps reales
  §3.4  compuerta AND (AE error>θ  ∧  IF anómalo)
  §3.5  graduación de severidad (θ, 2θ, 3θ)
  §5.1  estabilización anti-parpadeo (N_CONSEC lecturas antes de bajar severidad)

Artefactos por estación en ml_artifacts_ensemble_v1/ (Fase 2). θ recalibrable
(decisión: se usa el θ persistido por estación; en producción se recalibra en sitio).
"""
import json
import logging
import os
from datetime import datetime, timedelta, timezone

import httpx
import joblib
import numpy as np
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.health_state import HealthDeviceState, HealthReading

logger = logging.getLogger(__name__)

ART_DIR = os.environ.get(
    "ENSEMBLE_ARTIFACTS_PATH",
    "services/ml-service/ml_artifacts_ensemble_v1",
)
FEATURES = ["so2_ppb", "so2_flow", "so2_internal_temp", "so2_lamp_int",
            "hours_since_prev"]
MODEL_VERSION = "vigishield-ensemble-v1"

# Estados (SPEC §5)
SIN_DATOS, SANO, OBSERVADO, EN_RIESGO, CRITICO = (
    "SIN_DATOS", "SANO", "OBSERVADO", "EN_RIESGO", "CRITICO")
SEVERITY_ORDER = {SIN_DATOS: 0, SANO: 0, OBSERVADO: 1, EN_RIESGO: 2, CRITICO: 3}

N_CONSEC = 3  # anti-parpadeo (§5.1)

# --- Regla de consolidacion de alertas (docs/regla-consolidacion-alertas.md) ---
WINDOW_HOURS = 24  # ventana fija con reinicio (no deslizante)
# umbral de lecturas anomalas en la ventana (por estado crudo) que dispara
# evaluar creacion/escalada de incidencia
ALERT_THRESHOLDS = {OBSERVADO: 5, EN_RIESGO: 3, CRITICO: 1}
OPS_SERVICE_URL = os.environ.get("OPS_SERVICE_URL", "http://ops-service:8003")


def _window_start(ts: datetime) -> datetime:
    """Inicio de la ventana fija de 24h (bucket alineado a medianoche UTC)."""
    ts = _as_utc(ts)
    midnight = ts.replace(hour=0, minute=0, second=0, microsecond=0)
    buckets = int((ts - midnight).total_seconds() // (WINDOW_HOURS * 3600))
    return midnight + timedelta(hours=WINDOW_HOURS * buckets)


def _count_in_window(db: Session, device_id: str, raw_state: str,
                     ts: datetime) -> int:
    """Cuenta lecturas anomalas (AND=True) de un equipo, por estado crudo de la
    lectura, dentro de la ventana fija de 24h que contiene ts. Cuenta sobre
    raw_state (severidad real de la lectura, no el estado publicado tras el
    anti-parpadeo). CA-08: independiente por nivel."""
    start = _window_start(ts)
    return (
        db.query(func.count(HealthReading.id))
        .filter(
            HealthReading.device_id == device_id,
            HealthReading.raw_state == raw_state,
            HealthReading.and_alert.is_(True),
            HealthReading.reading_timestamp >= start,
        )
        .scalar()
    ) or 0


def _maybe_trigger_incidencia(db: Session, device_id: str, raw_state: str,
                              ts: datetime) -> None:
    """Si el conteo de la ventana cruza el umbral del nivel, llama a ops-service
    para crear/escalar la incidencia del monitor (fire-and-forget)."""
    threshold = ALERT_THRESHOLDS.get(raw_state)
    if threshold is None:
        return
    count = _count_in_window(db, device_id, raw_state, ts)
    if count < threshold:
        return
    try:
        resp = httpx.post(
            f"{OPS_SERVICE_URL}/api/v1/incidencias/monitor-alert",
            json={"device_id": device_id, "severidad": raw_state},
            timeout=10.0,
        )
        accion = resp.json().get("accion") if resp.content else None
        logger.info(
            "monitor-alert device=%s sev=%s count=%d/%d -> %s (%s)",
            device_id, raw_state, count, threshold, resp.status_code, accion,
        )
    except Exception:
        logger.exception(
            "Error llamando monitor-alert para %s (sev=%s)", device_id, raw_state
        )


class EnsembleRegistry:
    """Carga perezosa de los artefactos por estación."""

    def __init__(self, art_dir=ART_DIR):
        self.art_dir = art_dir
        self._cache = {}
        self.config = self._load_config()

    def _load_config(self):
        path = os.path.join(self.art_dir, "ensemble_config.json")
        if os.path.exists(path):
            with open(path) as f:
                return json.load(f)
        return {"severity_multipliers": {"observado": 1.0, "en_riesgo": 2.0,
                                         "critico": 3.0}}

    def available(self, station_id):
        return os.path.exists(os.path.join(self.art_dir, f"scaler_{station_id}.pkl"))

    def get(self, station_id):
        if station_id in self._cache:
            return self._cache[station_id]
        if not self.available(station_id):
            self._cache[station_id] = None
            return None
        scaler = joblib.load(os.path.join(self.art_dir, f"scaler_{station_id}.pkl"))
        ae = joblib.load(os.path.join(self.art_dir, f"autoencoder_{station_id}.pkl"))
        iforest = joblib.load(os.path.join(self.art_dir, f"iforest_{station_id}.pkl"))
        with open(os.path.join(self.art_dir, f"theta_{station_id}.json")) as f:
            theta = json.load(f)["theta"]
        bundle = {"scaler": scaler, "ae": ae, "iforest": iforest, "theta": theta}
        self._cache[station_id] = bundle
        return bundle

    def invalidate(self, station_id: str | None = None):
        """Descarta el bundle cacheado para que la próxima lectura recargue los
        artefactos desde disco (p.ej. tras recalibrar θ o reentrenar).
        Sin argumento, invalida todas las estaciones."""
        if station_id is None:
            self._cache.clear()
        else:
            self._cache.pop(station_id, None)


registry = EnsembleRegistry()


def _grade(recon_error, theta, mult):
    """SPEC §3.5 — severidad para una lectura que pasó el AND."""
    if recon_error <= theta * mult["observado"]:
        return SANO, None
    if recon_error <= theta * mult["en_riesgo"]:
        return OBSERVADO, "Advertencia"
    if recon_error <= theta * mult["critico"]:
        return EN_RIESGO, "Alerta"
    return CRITICO, "Crítico"


def _as_utc(ts: datetime) -> datetime:
    return ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)


def _hours_since_prev_online(state: HealthDeviceState, ts: datetime, valido: int):
    """SPEC §4.4 — horas desde el fin de la última falla, sobre timestamps reales.

    Actualiza la memoria (last_fail_end_ts) según la transición de valido y
    devuelve hours_since_prev para esta lectura (None si en falla o sin historial)."""
    ts = _as_utc(ts)
    prev_valido = state.last_valido if state else None

    if valido == 0:
        # en falla: no se calcula hsp; last_fail_end_ts se fija al recuperar tx
        return None

    # valido == 1
    if prev_valido == 0:
        # transición 0->1: aquí TERMINÓ la falla -> reset a 0
        state.last_fail_end_ts = ts
        return 0.0
    if state and state.last_fail_end_ts is not None:
        delta = (ts - _as_utc(state.last_fail_end_ts)).total_seconds() / 3600.0
        return max(0.0, delta)
    # nunca hubo falla previa -> se rellena luego con mediana de entrenamiento
    return None


def _stabilize(state: HealthDeviceState, raw_state: str) -> str:
    """SPEC §5.1 — anti-parpadeo. Subir a CRITICO es inmediato; el resto requiere
    N_CONSEC lecturas consecutivas del mismo estado candidato antes de publicarlo."""
    current = state.health_state if state and state.health_state else SANO
    if raw_state == current:
        state.candidate_state = None
        state.candidate_count = 0
        return current

    # escalada inmediata a CRITICO
    if SEVERITY_ORDER[raw_state] > SEVERITY_ORDER[current] and raw_state == CRITICO:
        state.candidate_state = None
        state.candidate_count = 0
        return CRITICO

    # SIN_DATOS es cambio de canal, inmediato (§5.1)
    if raw_state == SIN_DATOS or current == SIN_DATOS:
        state.candidate_state = None
        state.candidate_count = 0
        return raw_state

    # resto: acumular N_CONSEC antes de cambiar
    if state.candidate_state == raw_state:
        state.candidate_count += 1
    else:
        state.candidate_state = raw_state
        state.candidate_count = 1
    if state.candidate_count >= N_CONSEC:
        state.candidate_state = None
        state.candidate_count = 0
        return raw_state
    return current  # aún no confirma el cambio


def evaluate(db: Session, req) -> dict:
    """Evalúa UNA lectura, persiste y devuelve el contrato SPEC §6.2."""
    station = req.device_id
    ts = _as_utc(req.timestamp)

    state = db.get(HealthDeviceState, station)
    if state is None:
        state = HealthDeviceState(device_id=station, health_state=SANO,
                                  candidate_count=0)
        db.add(state)

    bundle = registry.get(station)
    theta = bundle["theta"] if bundle else None
    mult = registry.config["severity_multipliers"]

    # hours_since_prev online (actualiza memoria)
    hsp = _hours_since_prev_online(state, ts, req.valido)

    feats = [req.so2_ppb, req.so2_flow, req.so2_internal_temp, req.so2_lamp_int]
    feats_ok = all(v is not None for v in feats)

    # GATE §3.0: sin transmisión, sin features, o sin modelo -> SIN_DATOS
    if req.valido == 0 or not feats_ok or bundle is None:
        recon_error, if_anomaly, and_alert, severity = None, None, False, None
        raw_state = SIN_DATOS
    else:
        hsp_val = hsp if hsp is not None else 0.0  # fallback si no hay historial
        X = bundle["scaler"].transform([[*feats, hsp_val]])
        X_hat = bundle["ae"].predict(X)
        recon_error = float(np.mean((X - X_hat) ** 2))
        if_anomaly = bool(bundle["iforest"].predict(X)[0] == -1)
        and_alert = bool(recon_error > theta and if_anomaly)
        if and_alert:
            raw_state, severity = _grade(recon_error, theta, mult)
        else:
            raw_state, severity = SANO, None

    published = _stabilize(state, raw_state)

    # persistir estado vigente
    state.health_state = published
    state.last_recon_error = recon_error
    state.theta = theta
    state.hours_since_prev = hsp
    state.last_valido = req.valido
    state.last_reading_ts = ts
    # al recibir una lectura, la transmision esta viva -> limpiar canal (CT-04)
    if state.transmission_state != "OK":
        state.transmission_state = "OK"
        state.transmission_severity = None
    state.updated_at = datetime.now(timezone.utc)

    # persistir la lectura (serie histórica)
    db.add(HealthReading(
        device_id=station, reading_timestamp=ts, recon_error=recon_error,
        theta=theta, if_anomaly=if_anomaly, and_alert=and_alert,
        severity=severity, health_state=published, raw_state=raw_state,
        hours_since_prev=hsp, model_version=MODEL_VERSION,
    ))
    db.commit()

    # Regla de consolidacion: contar lecturas anomalas de la ventana y, si cruza
    # el umbral del nivel, crear/escalar incidencia en ops-service (fire-and-forget).
    # Se cuenta sobre raw_state (severidad real de la lectura), no el publicado.
    if and_alert and raw_state in ALERT_THRESHOLDS:
        _maybe_trigger_incidencia(db, station, raw_state, ts)

    return {
        "device_id": station,
        "timestamp": ts,
        "recon_error": recon_error,
        "theta": theta,
        "if_anomaly": if_anomaly,
        "and_alert": and_alert,
        "severity": severity,
        "health_state": published,
        "hours_since_prev": hsp,
        "model_version": MODEL_VERSION,
    }


def get_device_state(db: Session, device_id: str):
    return db.get(HealthDeviceState, device_id)


def get_readings(db: Session, device_id: str, limit: int = 300):
    """Serie histórica de health_readings (más recientes primero -> se devuelve
    en orden cronológico para el gráfico de recon_error + θ)."""
    rows = (
        db.query(HealthReading)
        .filter(HealthReading.device_id == device_id)
        .order_by(HealthReading.reading_timestamp.desc())
        .limit(limit)
        .all()
    )
    return list(reversed(rows))
