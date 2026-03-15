from datetime import datetime, timezone

import httpx
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.config import settings
from app.ml.feature_engineering import compute_features_from_readings
from app.ml.model_interface import model_manager
from app.models.prediccion import Prediccion
from app.services.alert_service import evaluate_and_create_alert


def _fetch_readings(device_id: str, page_size: int = 200) -> list[dict]:
    """Fetch recent readings from iot-service for a device."""
    url = (
        f"{settings.IOT_SERVICE_URL}/api/v1/iot/readings/{device_id}"
        f"?page=1&page_size={page_size}"
    )
    try:
        resp = httpx.get(url, timeout=10.0)
        if resp.status_code == 404:
            raise HTTPException(
                status_code=404,
                detail=f"Equipo '{device_id}' no encontrado en iot-service",
            )
        resp.raise_for_status()
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Error conectando a iot-service: {e}",
        )

    data = resp.json()
    items = data.get("items", [])
    if not items:
        raise HTTPException(
            status_code=404,
            detail=f"No hay lecturas disponibles para '{device_id}'",
        )

    # Reverse to chronological order (API returns newest first)
    items.reverse()

    # Map API response keys to sensor field names
    readings = []
    for item in items:
        readings.append({
            "so2_ppb": item.get("so2_ppb"),
            "h2s_ppb": item.get("h2s_ppb"),
            "reaction_temp": item.get("reaction_temp"),
            "izs_temp": item.get("izs_temp"),
            "pmt_temp": item.get("pmt_temp"),
            "sample_flow": item.get("sample_flow"),
            "pressure": item.get("pressure"),
            "uv_lamp_intensity": item.get("uv_lamp_intensity"),
            "box_temp": item.get("box_temp"),
            "hvps_v": item.get("hvps_v"),
            "conv_temp": item.get("conv_temp"),
            "ozone_flow": item.get("ozone_flow"),
        })
    return readings


def _fetch_equipos() -> list[dict]:
    """Fetch all equipment from iot-service."""
    url = f"{settings.IOT_SERVICE_URL}/api/v1/iot/equipos"
    try:
        resp = httpx.get(url, timeout=10.0)
        resp.raise_for_status()
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Error conectando a iot-service: {e}",
        )
    return resp.json()


def run_prediction(db: Session, device_id: str) -> Prediccion:
    """Run prediction for a single device."""
    if not model_manager.is_loaded:
        raise HTTPException(
            status_code=503,
            detail="Modelos ML no cargados. Contacte al administrador.",
        )

    # Fetch readings from iot-service
    readings = _fetch_readings(device_id)

    # Compute features
    features = compute_features_from_readings(readings)

    # Run prediction
    result = model_manager.predict(features)

    # Skip if prediction unchanged from latest
    latest = get_latest_prediction(db, device_id)
    if latest and (
        float(latest.failure_probability) == result["failure_probability"]
        and latest.remaining_useful_life_days == result["remaining_useful_life_days"]
    ):
        return latest

    # Store prediction
    prediccion = Prediccion(
        device_id=device_id,
        model_version=model_manager.model_version,
        prediction_timestamp=datetime.now(timezone.utc),
        failure_probability=result["failure_probability"],
        remaining_useful_life_days=result["remaining_useful_life_days"],
        risk_level=result["risk_level"],
        feature_snapshot=features,
    )
    db.add(prediccion)
    db.commit()
    db.refresh(prediccion)

    # Create alert
    evaluate_and_create_alert(db, prediccion)

    return prediccion


def run_all_predictions(db: Session) -> list[Prediccion]:
    """Run predictions for all registered equipment."""
    equipos = _fetch_equipos()
    predictions = []
    for equipo in equipos:
        device_id = equipo["device_id"]
        try:
            pred = run_prediction(db, device_id)
            predictions.append(pred)
        except HTTPException:
            # Skip devices without readings
            continue
    return predictions


def get_predictions(
    db: Session, device_id: str, page: int = 1, page_size: int = 50
) -> tuple[list[Prediccion], int]:
    """Get paginated prediction history for a device."""
    query = (
        db.query(Prediccion)
        .filter(Prediccion.device_id == device_id)
        .order_by(Prediccion.prediction_timestamp.desc())
    )
    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    return items, total


def get_latest_prediction(db: Session, device_id: str) -> Prediccion | None:
    """Get the latest prediction for a device."""
    return (
        db.query(Prediccion)
        .filter(Prediccion.device_id == device_id)
        .order_by(Prediccion.prediction_timestamp.desc())
        .first()
    )
