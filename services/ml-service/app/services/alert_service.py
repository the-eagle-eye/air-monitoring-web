import logging

from sqlalchemy.orm import Session
from sqlalchemy import desc

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

    # DEPRECADO (retiro del RF): la creación de incidencias correctivas la hace
    # ahora EXCLUSIVAMENTE el monitor de salud (ensemble) vía la regla de
    # consolidación (ops /incidencias/monitor-alert). El flujo RF ya no dispara
    # incidencias para no duplicar. Ver docs/spec-racionalizacion-dashboard-e-incidencias.md
    # (Decisión B1 + C1). La Alerta se persiste solo por compatibilidad histórica.

    return alerta


def _notify_ops_alert(device_id: str, nivel_riesgo: str = "alta") -> None:
    """DEPRECADO — el RF ya no crea incidencias (lo hace el monitor de salud).

    Se conserva la función como no-op para no romper referencias externas.
    Ver docs/spec-racionalizacion-dashboard-e-incidencias.md.
    """
    logger.warning(
        "_notify_ops_alert está deprecado (retiro RF); no se creó incidencia "
        "para %s (nivel %s). Las incidencias las crea el monitor de salud.",
        device_id, nivel_riesgo,
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
