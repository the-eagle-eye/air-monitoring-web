import logging

import httpx
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.config import settings
from app.models.alerta import Alerta
from app.models.prediccion import Prediccion

logger = logging.getLogger(__name__)

RISK_DESCRIPTIONS = {
    "alta": (
        "ALERTA ALTA: RUL < 30 dias. "
        "Se requiere intervencion inmediata para evitar falla del equipo."
    ),
    "media": (
        "ALERTA MEDIA: RUL entre 30 y 59 dias. "
        "Programar mantenimiento correctivo en las proximas semanas."
    ),
    "baja": (
        "ALERTA BAJA: RUL >= 60 dias. "
        "Equipo bajo monitoreo preventivo."
    ),
}


def evaluate_and_create_alert(db: Session, prediccion: Prediccion) -> Alerta:
    """Create an alert based on a prediction's risk level."""
    alerta = Alerta(
        device_id=prediccion.device_id,
        prediccion_id=prediccion.id,
        nivel_riesgo=prediccion.risk_level,
        descripcion=RISK_DESCRIPTIONS.get(
            prediccion.risk_level,
            f"Prediccion con RUL={prediccion.remaining_useful_life_days} dias.",
        ),
    )
    db.add(alerta)
    db.commit()
    db.refresh(alerta)

    if alerta.nivel_riesgo in ("alta", "media"):
        _notify_ops_alert(prediccion.device_id, alerta.nivel_riesgo)

    return alerta


def _notify_ops_alert(device_id: str, nivel_riesgo: str = "alta") -> None:
    """Notificar a ops-service para crear incidencia correctiva (fire-and-forget)."""
    try:
        resp = httpx.post(
            f"{settings.OPS_SERVICE_URL}/api/v1/incidencias/alert-trigger",
            json={"device_id": device_id, "nivel_riesgo": nivel_riesgo},
            timeout=10.0,
        )
        resp.raise_for_status()
        logger.info("ops-service notificado de alerta %s para %s", nivel_riesgo, device_id)
    except Exception:
        logger.exception(
            "Error notificando a ops-service de alerta %s para %s", nivel_riesgo, device_id
        )


def get_alerts(
    db: Session,
    device_id: str | None = None,
    estado: str | None = None,
    nivel_riesgo: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[Alerta], int]:
    """Get paginated and filtered alert list."""
    query = db.query(Alerta)

    if device_id:
        query = query.filter(Alerta.device_id == device_id)
    if estado:
        query = query.filter(Alerta.estado == estado)
    if nivel_riesgo:
        query = query.filter(Alerta.nivel_riesgo == nivel_riesgo)

    query = query.order_by(desc(Alerta.created_at))
    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    return items, total


def deactivate_alerts(db: Session, device_id: str) -> int:
    """Desactivar todas las alertas activas de un equipo."""
    count = (
        db.query(Alerta)
        .filter(Alerta.device_id == device_id, Alerta.estado == "activa")
        .update({"estado": "inactiva"})
    )
    db.commit()
    return count


def get_alerts_by_device(db: Session, device_id: str) -> list[Alerta]:
    """Get all alerts for a specific device."""
    return (
        db.query(Alerta)
        .filter(Alerta.device_id == device_id)
        .order_by(desc(Alerta.created_at))
        .all()
    )
