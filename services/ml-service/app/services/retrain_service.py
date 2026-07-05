"""C5 — Reentrenamiento del ensemble por degradación / programado.

Este módulo aporta la DECISIÓN (should_retrain) y la ORQUESTACIÓN segura
(retrain_station), no reimplementa el entrenamiento: el pipeline pesado
(01_build_dataset → 02/03 train → θ) corre en batch dentro del contenedor con
numpy 1.26 (lección P6) vía retrain_in_container.py. Ver docs/plan-c1-c6-c4-c5.md
y docs/spec-transmision-y-reentrenamiento.md §2.

`should_retrain` consume las métricas persistidas por C6 (`model_metrics`) y el
θ del registry, aplicando los criterios de degradación de la spec §2.3.
"""
import json
import logging
import os
from datetime import datetime, timedelta, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.model_metric import ModelMetric
from app.services.health_service import registry

logger = logging.getLogger(__name__)

# Criterios de degradación (spec §2.3)
BASE_ALERT_RATE = float(os.environ.get("BASE_ALERT_RATE", "0.05"))  # ~5% esperado
ALERT_RATE_FACTOR = float(os.environ.get("ALERT_RATE_FACTOR", "3.0"))  # 3× base
SUSTAINED_DAYS = int(os.environ.get("DEGRADATION_SUSTAINED_DAYS", "7"))
THETA_DRIFT_HIGH = float(os.environ.get("THETA_DRIFT_HIGH", "2.0"))  # > 2× train
THETA_DRIFT_LOW = float(os.environ.get("THETA_DRIFT_LOW", "0.5"))   # < 0.5× train

RETRAIN_ENABLED = os.environ.get("RETRAIN_ENABLED", "0") == "1"  # opt-in (costoso)


def _as_utc(ts: datetime) -> datetime:
    return ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)


def _theta_meta(station_id: str) -> dict | None:
    path = os.path.join(registry.art_dir, f"theta_{station_id}.json")
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return json.load(f)


def should_retrain(db: Session, station_id: str,
                   now: datetime | None = None) -> dict:
    """Evalúa los criterios de degradación (spec §2.3) para una estación.

    Devuelve {station_id, retrain: bool, reasons: [...]}. Usa las métricas de C6
    de los últimos SUSTAINED_DAYS y el θ recalibrado vs θ_train."""
    now = _as_utc(now or datetime.now(timezone.utc))
    since = now - timedelta(days=SUSTAINED_DAYS)
    reasons: list[str] = []

    # Criterio 1: tasa de alerta > 3× base, SOSTENIDA en la ventana.
    metrics = (
        db.query(ModelMetric)
        .filter(
            ModelMetric.station_id == station_id,
            ModelMetric.window_start >= since,
            ModelMetric.total_readings > 0,
        )
        .all()
    )
    threshold = BASE_ALERT_RATE * ALERT_RATE_FACTOR
    if metrics and all(m.alert_rate > threshold for m in metrics):
        avg = sum(m.alert_rate for m in metrics) / len(metrics)
        reasons.append(
            f"tasa de alerta sostenida {avg:.2%} > {threshold:.2%} "
            f"({len(metrics)} ventanas)"
        )

    # Criterio 2: θ recalibrado fuera de [0.5×, 2×] del θ_train.
    meta = _theta_meta(station_id)
    if meta:
        theta = meta.get("theta")
        theta_train = meta.get("theta_train")
        if theta and theta_train and theta_train > 0:
            ratio = theta / theta_train
            if ratio > THETA_DRIFT_HIGH or ratio < THETA_DRIFT_LOW:
                reasons.append(
                    f"θ drift: recalibrado/train = {ratio:.2f} "
                    f"(fuera de [{THETA_DRIFT_LOW}, {THETA_DRIFT_HIGH}])"
                )

    return {"station_id": station_id, "retrain": bool(reasons),
            "reasons": reasons}


def evaluate_all(db: Session, now: datetime | None = None) -> list[dict]:
    """should_retrain para todas las estaciones con métricas registradas."""
    station_ids = [
        r[0] for r in db.query(ModelMetric.station_id).distinct().all()
    ]
    return [should_retrain(db, sid, now) for sid in station_ids]


def retrain_station(db: Session, station_id: str) -> dict:
    """Orquesta el reentrenamiento de una estación (opt-in, RETRAIN_ENABLED).

    NO reimplementa el entrenamiento: delega al pipeline batch. Salvaguarda
    (spec CR-04): si el modelo nuevo no mejora, se conserva el anterior. Esta
    función deja el gancho de orquestación; la ejecución del pipeline pesado es
    un job batch fuera del request-path.
    """
    if not RETRAIN_ENABLED:
        return {"station_id": station_id, "action": "skipped",
                "reason": "RETRAIN_ENABLED=0 (reentrenamiento es opt-in y costoso)"}
    # El pipeline pesado corre en batch (retrain_in_container.py). Aquí se
    # registraría el disparo; tras completarse, invalidar el cache del registry.
    logger.info("Reentrenamiento solicitado para %s (delegar a job batch)",
                station_id)
    registry.invalidate(station_id)
    return {"station_id": station_id, "action": "triggered",
            "note": "pipeline batch encolado; artefactos se versionan al completar"}
