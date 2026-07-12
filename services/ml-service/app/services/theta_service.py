"""C4 — Recalibración automática de θ desde la BD (docs/plan-c1-c6-c4-c5.md).

Recalcula el umbral θ por estación como el P95 del error de reconstrucción sobre
las lecturas normales recientes (ventana warm-up) tomadas de `health_readings`
—la fuente viva, alimentada por C1—. Conserva θ_train para trazabilidad ISO 17025
y actualiza `theta_<sid>.json`, invalidando el cache del registry para que el θ
nuevo surta efecto sin reiniciar el servicio.

Análogo a scripts/ensemble/09_recalibrate_theta.py, pero desde la BD en vez del
dataset joblib offline.
"""
import json
import logging
import os
from datetime import datetime, timedelta, timezone

import numpy as np
from sqlalchemy.orm import Session

from app.models.health_state import HealthDeviceState, HealthReading
from app.services.health_service import registry

logger = logging.getLogger(__name__)

WINDOW_DAYS = int(os.environ.get("THETA_RECAL_WINDOW_DAYS", "14"))
THETA_PERCENTILE = int(os.environ.get("THETA_PERCENTILE", "95"))
# mínimo de lecturas normales para recalibrar (evita θ espurio con pocos datos)
MIN_NORMAL_READINGS = int(os.environ.get("THETA_MIN_NORMAL_READINGS", "50"))


def _as_utc(ts: datetime) -> datetime:
    return ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)


def _normal_recon_errors(db: Session, station_id: str,
                         since: datetime) -> list[float]:
    """recon_error de lecturas NO anómalas (operación normal) en la ventana."""
    rows = (
        db.query(HealthReading.recon_error)
        .filter(
            HealthReading.device_id == station_id,
            HealthReading.reading_timestamp >= since,
            HealthReading.and_alert.is_(False),
            HealthReading.recon_error.isnot(None),
        )
        .all()
    )
    return [r[0] for r in rows if r[0] is not None]


def recalibrate_theta(db: Session, station_id: str,
                      window_days: int = WINDOW_DAYS,
                      now: datetime | None = None) -> dict:
    """Recalibra θ de una estación desde la BD. Devuelve un resumen con acción.

    No recalibra (acción 'skipped') si no hay modelo o hay muy pocas lecturas
    normales — un θ calculado con pocos datos sería poco fiable (guarda C4.2)."""
    now = _as_utc(now or datetime.now(timezone.utc))
    since = now - timedelta(days=window_days)

    theta_path = os.path.join(registry.art_dir, f"theta_{station_id}.json")
    if not os.path.exists(theta_path):
        return {"station_id": station_id, "action": "skipped",
                "reason": "sin modelo/θ"}

    errors = _normal_recon_errors(db, station_id, since)
    if len(errors) < MIN_NORMAL_READINGS:
        return {
            "station_id": station_id,
            "action": "skipped",
            "reason": (
                f"pocas lecturas normales "
                f"({len(errors)} < {MIN_NORMAL_READINGS})"
            ),
        }

    theta_new = float(np.percentile(errors, THETA_PERCENTILE))

    with open(theta_path) as f:
        meta = json.load(f)
    # conservar θ_train original (idempotente en re-runs)
    theta_train = meta.get("theta_train", meta.get("theta"))

    meta.update({
        "station_id": station_id,
        "theta": theta_new,                 # ACTIVO (lo lee el servicio)
        "theta_train": theta_train,         # original, auditoría
        "theta_recalibrated": theta_new,
        "theta_source": "recalibrated_db",
        "theta_percentile": THETA_PERCENTILE,
        "warmup_rows": len(errors),
        "recalibrated_at": now.isoformat(),
    })
    with open(theta_path, "w") as f:
        json.dump(meta, f, indent=2)

    registry.invalidate(station_id)  # el θ nuevo surte efecto sin reiniciar
    logger.info("θ recalibrado %s: %.4f (train %.4f, %d rows)",
                station_id, theta_new, theta_train or 0.0, len(errors))
    return {"station_id": station_id, "action": "recalibrated",
            "theta": round(theta_new, 4),
            "theta_train": round(theta_train, 4) if theta_train else None,
            "warmup_rows": len(errors)}


def recalibrate_all(db: Session, window_days: int = WINDOW_DAYS,
                    now: datetime | None = None) -> list[dict]:
    """Recalibra θ de todas las estaciones con estado. Resumen por estación."""
    states = db.query(HealthDeviceState).all()
    results = [recalibrate_theta(db, st.device_id, window_days, now)
               for st in states]
    recal = sum(1 for r in results if r["action"] == "recalibrated")
    logger.info("Recalibración de θ: %d/%d estaciones actualizadas",
                recal, len(results))
    return results
