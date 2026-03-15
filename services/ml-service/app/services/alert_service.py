from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.alerta import Alerta
from app.models.prediccion import Prediccion

RISK_DESCRIPTIONS = {
    "alta": (
        "ALERTA ALTA: RUL <= 30 dias. "
        "Se requiere intervencion inmediata para evitar falla del equipo."
    ),
    "media": (
        "ALERTA MEDIA: RUL entre 31 y 69 dias. "
        "Programar mantenimiento preventivo en las proximas semanas."
    ),
    "baja": (
        "ALERTA BAJA: RUL >= 70 dias. "
        "Equipo en condiciones normales de operacion."
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
    return alerta


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


def get_alerts_by_device(db: Session, device_id: str) -> list[Alerta]:
    """Get all alerts for a specific device."""
    return (
        db.query(Alerta)
        .filter(Alerta.device_id == device_id)
        .order_by(desc(Alerta.created_at))
        .all()
    )
