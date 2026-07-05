"""C6 — Métricas de monitoreo del modelo (docs/plan-c1-c6-c4-c5.md).

Agrega `health_readings` por estación en una ventana y persiste una fila en
`model_metrics`: tasa de alerta, conteos y θ vigente. Es la base para detectar
degradación y disparar el reentrenamiento (C5).
"""
import logging
import os
from datetime import datetime, timedelta, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.health_state import HealthDeviceState, HealthReading
from app.models.model_metric import ModelMetric

logger = logging.getLogger(__name__)

METRICS_WINDOW_HOURS = int(os.environ.get("METRICS_WINDOW_HOURS", "24"))


def _as_utc(ts: datetime) -> datetime:
    return ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)


def compute_station_metric(db: Session, station_id: str,
                           window_start: datetime, window_end: datetime,
                           theta: float | None = None) -> ModelMetric:
    """Calcula (sin persistir) la métrica de una estación en la ventana."""
    window_start = _as_utc(window_start)
    window_end = _as_utc(window_end)

    base = db.query(func.count(HealthReading.id)).filter(
        HealthReading.device_id == station_id,
        HealthReading.reading_timestamp >= window_start,
        HealthReading.reading_timestamp < window_end,
    )
    total = base.scalar() or 0
    anomaly = (
        base.filter(HealthReading.and_alert.is_(True)).scalar() or 0
    )
    alert_rate = (anomaly / total) if total > 0 else 0.0

    return ModelMetric(
        station_id=station_id,
        window_start=window_start,
        window_end=window_end,
        total_readings=total,
        anomaly_readings=anomaly,
        alert_rate=alert_rate,
        theta=theta,
    )


def compute_and_store_metrics(db: Session, now: datetime | None = None,
                              window_hours: int = METRICS_WINDOW_HOURS) -> list[dict]:
    """Para cada estación con estado, calcula y persiste su métrica de ventana.

    Devuelve un resumen (una entrada por estación)."""
    now = _as_utc(now or datetime.now(timezone.utc))
    window_start = now - timedelta(hours=window_hours)

    states = db.query(HealthDeviceState).all()
    summary = []
    for st in states:
        metric = compute_station_metric(
            db, st.device_id, window_start, now, theta=st.theta
        )
        db.add(metric)
        summary.append({
            "station_id": st.device_id,
            "total_readings": metric.total_readings,
            "anomaly_readings": metric.anomaly_readings,
            "alert_rate": round(metric.alert_rate, 4),
            "theta": st.theta,
        })
    db.commit()
    logger.info("Métricas del modelo calculadas para %d estaciones", len(summary))
    return summary


def get_metrics(db: Session, station_id: str | None = None,
                limit: int = 100) -> list[ModelMetric]:
    """Serie histórica de métricas (más recientes primero)."""
    q = db.query(ModelMetric)
    if station_id:
        q = q.filter(ModelMetric.station_id == station_id)
    return q.order_by(ModelMetric.window_start.desc()).limit(limit).all()
