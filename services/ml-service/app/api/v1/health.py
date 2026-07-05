from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.health import (
    HealthDeviceStateResponse,
    HealthEvaluateRequest,
    HealthEvaluateResponse,
    HealthReadingsResponse,
    AutocloseResponse,
    MetricsRunResponse,
    ModelMetricsResponse,
    NoTransmissionResponse,
    RetrainCheckResponse,
    ThetaRecalResponse,
    WatchdogRunResponse,
)
from app.services.health_service import evaluate, get_device_state, get_readings
from app.services import (
    autoclose_service,
    metrics_service,
    retrain_service,
    theta_service,
    watchdog_service,
)

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
                "if_anomaly": r.if_anomaly,  # M3: veredicto Isolation Forest
                "severity": r.severity,      # M3: severidad de la lectura
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


@router.get("/metrics", response_model=ModelMetricsResponse)
def model_metrics(device_id: str | None = None, limit: int = 100,
                  db: Session = Depends(get_db)):
    """Serie histórica de métricas del modelo (C6) por estación."""
    rows = metrics_service.get_metrics(db, device_id, limit)
    return {"items": rows}


@router.post("/run-metrics", response_model=MetricsRunResponse)
def run_metrics_now(db: Session = Depends(get_db)):
    """Calcula y persiste las métricas del modelo on-demand. El scheduler ya las
    corre a diario."""
    stations = metrics_service.compute_and_store_metrics(db)
    return {"computed": len(stations), "stations": stations}


@router.post("/recalibrate-theta", response_model=ThetaRecalResponse)
def recalibrate_theta_now(db: Session = Depends(get_db)):
    """Recalibra θ de todas las estaciones desde la BD (C4) on-demand. El
    scheduler ya lo corre mensualmente."""
    return {"results": theta_service.recalibrate_all(db)}


@router.get("/should-retrain", response_model=RetrainCheckResponse)
def should_retrain_check(db: Session = Depends(get_db)):
    """Diagnóstico C5: evalúa criterios de degradación por estación (spec §2.3)
    sin disparar reentrenamiento. Devuelve qué estaciones lo necesitarían."""
    return {"results": retrain_service.evaluate_all(db)}


@router.post("/run-autoclose", response_model=AutocloseResponse)
def run_autoclose_now(db: Session = Depends(get_db)):
    """Auto-cierre ITIL on-demand (I2.7): cierra incidencias en 'resuelto' con
    lecturas SANO confirmadas o timeout. El scheduler ya lo corre cada 15 min."""
    return autoclose_service.run_autoclose(db)
