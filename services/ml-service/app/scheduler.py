"""Scheduler del ml-service (APScheduler).

Hoy corre una sola tarea: el watchdog de transmisión cada 5 min
(docs/spec-transmision-y-reentrenamiento.md §1). Deja el enganche listo para
futuras tareas programadas (recalibración de θ mensual, §2).

Se controla con env var WATCHDOG_ENABLED (default "1"); en tests se apaga para
no arrancar hilos de fondo.
"""
import logging
import os

from apscheduler.schedulers.background import BackgroundScheduler

from app.database import SessionLocal
from app.services import watchdog_service

logger = logging.getLogger(__name__)

WATCHDOG_ENABLED = os.environ.get("WATCHDOG_ENABLED", "1") == "1"
WATCHDOG_INTERVAL_MIN = int(os.environ.get("WATCHDOG_INTERVAL_MIN", "5"))

_scheduler: BackgroundScheduler | None = None


def _watchdog_job() -> None:
    """Ejecuta el watchdog con su propia sesión (fuera del request-path)."""
    db = SessionLocal()
    try:
        watchdog_service.run_watchdog(db)
    except Exception:
        logger.exception("Error ejecutando el watchdog programado")
    finally:
        db.close()


def start_scheduler() -> BackgroundScheduler | None:
    """Arranca el scheduler si está habilitado. Idempotente."""
    global _scheduler
    if not WATCHDOG_ENABLED:
        logger.info("Watchdog deshabilitado (WATCHDOG_ENABLED=0)")
        return None
    if _scheduler is not None:
        return _scheduler

    _scheduler = BackgroundScheduler(timezone="UTC")
    _scheduler.add_job(
        _watchdog_job,
        trigger="interval",
        minutes=WATCHDOG_INTERVAL_MIN,
        id="transmission_watchdog",
        replace_existing=True,
        max_instances=1,          # no solapar corridas
        coalesce=True,            # si se atrasa, correr una sola vez
    )
    _scheduler.start()
    logger.info(
        "Watchdog de transmisión programado cada %d min", WATCHDOG_INTERVAL_MIN
    )
    return _scheduler


def shutdown_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
