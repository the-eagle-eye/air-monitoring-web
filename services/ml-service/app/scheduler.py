"""Scheduler del ml-service (APScheduler).

Jobs programados (cada uno con su flag *_ENABLED, apagados en tests):
  - Watchdog de transmisión, cada 5 min (spec-transmision §1).
  - Métricas del modelo (C6), diarias.
  - Recalibración de θ (C4), mensual.

El scheduler arranca si AL MENOS un job está habilitado.
"""
import logging
import os

from apscheduler.schedulers.background import BackgroundScheduler

from app.database import SessionLocal
from app.services import (
    autoclose_service,
    metrics_service,
    retrain_service,
    theta_service,
    watchdog_service,
)

logger = logging.getLogger(__name__)

WATCHDOG_ENABLED = os.environ.get("WATCHDOG_ENABLED", "1") == "1"
WATCHDOG_INTERVAL_MIN = int(os.environ.get("WATCHDOG_INTERVAL_MIN", "5"))
METRICS_ENABLED = os.environ.get("METRICS_ENABLED", "1") == "1"
METRICS_INTERVAL_HOURS = int(os.environ.get("METRICS_INTERVAL_HOURS", "24"))
THETA_RECAL_ENABLED = os.environ.get("THETA_RECAL_ENABLED", "1") == "1"
# Reentrenamiento por degradación: opt-in (costoso). Chequea a diario y solo
# entrena si should_retrain Y RETRAIN_ENABLED.
RETRAIN_CHECK_ENABLED = os.environ.get("RETRAIN_CHECK_ENABLED", "0") == "1"
# Auto-cierre ITIL de incidencias en 'resuelto' (I2.7/I2.8).
AUTOCLOSE_ENABLED = os.environ.get("AUTOCLOSE_ENABLED", "1") == "1"
AUTOCLOSE_INTERVAL_MIN = int(os.environ.get("AUTOCLOSE_INTERVAL_MIN", "15"))

_scheduler: BackgroundScheduler | None = None


def _watchdog_job() -> None:
    db = SessionLocal()
    try:
        watchdog_service.run_watchdog(db)
    except Exception:
        logger.exception("Error ejecutando el watchdog programado")
    finally:
        db.close()


def _metrics_job() -> None:
    db = SessionLocal()
    try:
        metrics_service.compute_and_store_metrics(db)
    except Exception:
        logger.exception("Error calculando métricas del modelo programadas")
    finally:
        db.close()


def _theta_recal_job() -> None:
    db = SessionLocal()
    try:
        theta_service.recalibrate_all(db)
    except Exception:
        logger.exception("Error recalibrando θ (programado)")
    finally:
        db.close()


def _retrain_check_job() -> None:
    """Evalúa degradación (C5) y, si RETRAIN_ENABLED, dispara reentrenamiento."""
    db = SessionLocal()
    try:
        for r in retrain_service.evaluate_all(db):
            if r["retrain"]:
                logger.warning("Degradación en %s: %s", r["station_id"],
                               "; ".join(r["reasons"]))
                retrain_service.retrain_station(db, r["station_id"])
    except Exception:
        logger.exception("Error en el chequeo de reentrenamiento programado")
    finally:
        db.close()


def _autoclose_job() -> None:
    """Auto-cierre ITIL de incidencias en 'resuelto' (I2.7/I2.8)."""
    db = SessionLocal()
    try:
        autoclose_service.run_autoclose(db)
    except Exception:
        logger.exception("Error en el auto-cierre programado")
    finally:
        db.close()


def start_scheduler() -> BackgroundScheduler | None:
    """Arranca el scheduler con los jobs habilitados. Idempotente."""
    global _scheduler
    if not (WATCHDOG_ENABLED or METRICS_ENABLED or THETA_RECAL_ENABLED
            or RETRAIN_CHECK_ENABLED or AUTOCLOSE_ENABLED):
        logger.info("Scheduler deshabilitado (todos los jobs off)")
        return None
    if _scheduler is not None:
        return _scheduler

    _scheduler = BackgroundScheduler(timezone="UTC")

    if WATCHDOG_ENABLED:
        _scheduler.add_job(
            _watchdog_job, trigger="interval", minutes=WATCHDOG_INTERVAL_MIN,
            id="transmission_watchdog", replace_existing=True,
            max_instances=1, coalesce=True,
        )
        logger.info("Watchdog programado cada %d min", WATCHDOG_INTERVAL_MIN)

    if METRICS_ENABLED:
        _scheduler.add_job(
            _metrics_job, trigger="interval", hours=METRICS_INTERVAL_HOURS,
            id="model_metrics", replace_existing=True,
            max_instances=1, coalesce=True,
        )
        logger.info("Métricas del modelo programadas cada %d h",
                    METRICS_INTERVAL_HOURS)

    if THETA_RECAL_ENABLED:
        # mensual: día 1 a las 03:00 UTC (fuera de horas de mayor tráfico)
        _scheduler.add_job(
            _theta_recal_job, trigger="cron", day=1, hour=3,
            id="theta_recalibration", replace_existing=True,
            max_instances=1, coalesce=True,
        )
        logger.info("Recalibración de θ programada mensual (día 1, 03:00 UTC)")

    if RETRAIN_CHECK_ENABLED:
        # chequeo diario de degradación (04:00 UTC); solo entrena si RETRAIN_ENABLED
        _scheduler.add_job(
            _retrain_check_job, trigger="cron", hour=4,
            id="retrain_degradation_check", replace_existing=True,
            max_instances=1, coalesce=True,
        )
        logger.info(
            "Chequeo de degradación/reentrenamiento programado diario (04:00 UTC)"
        )

    if AUTOCLOSE_ENABLED:
        _scheduler.add_job(
            _autoclose_job, trigger="interval", minutes=AUTOCLOSE_INTERVAL_MIN,
            id="itil_autoclose", replace_existing=True,
            max_instances=1, coalesce=True,
        )
        logger.info("Auto-cierre ITIL programado cada %d min", AUTOCLOSE_INTERVAL_MIN)

    _scheduler.start()
    return _scheduler


def shutdown_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
