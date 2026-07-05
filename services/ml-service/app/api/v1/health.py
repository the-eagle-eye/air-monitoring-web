from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.health import (
    HealthDeviceStateResponse,
    HealthEvaluateRequest,
    HealthEvaluateResponse,
    HealthReadingsResponse,
    NoTransmissionResponse,
    WatchdogRunResponse,
)
from app.services.health_service import evaluate, get_device_state, get_readings
from app.services import watchdog_service

router = APIRouter()


@router.post("/evaluate", response_model=HealthEvaluateResponse)
def evaluate_reading(req: HealthEvaluateRequest, db: Session = Depends(get_db)):
    """Evalúa una lectura con el ensemble no supervisado (SPEC §6.1 -> §6.2)."""
    return evaluate(db, req)


@router.get("/{device_id}/readings", response_model=HealthReadingsResponse)
def device_readings(device_id: str, limit: int = 300, db: Session = Depends(get_db)):
    """Serie histórica de recon_error + θ para el gráfico de tendencia."""
    rows = get_readings(db, device_id, limit)
    return {
        "device_id": device_id,
        "points": [
            {
                "timestamp": r.reading_timestamp,
                "recon_error": r.recon_error,
                "theta": r.theta,
                "health_state": r.health_state,
                "and_alert": r.and_alert,
            }
            for r in rows
        ],
    }


@router.get("/{device_id}/state", response_model=HealthDeviceStateResponse)
def device_state(device_id: str, db: Session = Depends(get_db)):
    state = get_device_state(db, device_id)
    if state is None:
        raise HTTPException(status_code=404,
                            detail=f"Sin estado de salud para '{device_id}'")
    return {
        "device_id": state.device_id,
        "health_state": state.health_state,
        "last_recon_error": state.last_recon_error,
        "theta": state.theta,
        "hours_since_prev": state.hours_since_prev,
        "transmission_state": state.transmission_state,
        "transmission_severity": state.transmission_severity,
        "last_reading_ts": state.last_reading_ts,
        "updated_at": state.updated_at,
    }


@router.get("/transmission/no-transmission", response_model=NoTransmissionResponse)
def no_transmission(db: Session = Depends(get_db)):
    """Equipos en SIN_TRANSMISION (canal del watchdog §1.2) para el dashboard."""
    rows = watchdog_service.get_no_transmission(db)
    return {
        "items": [
            {
                "device_id": r.device_id,
                "transmission_severity": r.transmission_severity,
                "last_reading_ts": r.last_reading_ts,
                "updated_at": r.updated_at,
            }
            for r in rows
        ]
    }


@router.post("/run-watchdog", response_model=WatchdogRunResponse)
def run_watchdog_now(db: Session = Depends(get_db)):
    """Ejecuta el watchdog on-demand (debug / cron externo). El scheduler ya lo
    corre cada 5 min automáticamente."""
    return watchdog_service.run_watchdog(db)
