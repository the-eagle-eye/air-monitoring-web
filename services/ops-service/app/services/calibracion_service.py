from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.incidencia import Incidencia
from app.models.calibracion import Calibracion
from app.schemas.calibracion import CalibracionCreate, CalibracionUpdate


def create_calibracion(db: Session, data: CalibracionCreate) -> Calibracion:
    incidencia_id = data.incidencia_id

    if incidencia_id is None:
        # Auto-crear incidencia de calibracion
        incidencia = Incidencia(
            device_id=data.device_id,
            tipo="calibracion",
            descripcion="Calibracion programada",
            prioridad="media",
        )
        db.add(incidencia)
        db.flush()
        incidencia_id = incidencia.id

    calibracion = Calibracion(
        incidencia_id=incidencia_id,
        device_id=data.device_id,
        fecha_calibracion=data.fecha_calibracion,
        nota=data.nota,
        certificado_url=data.certificado_url,
        proveedor_id=data.proveedor_id,
    )
    db.add(calibracion)
    db.commit()
    db.refresh(calibracion)
    return calibracion


def get_calibracion(db: Session, calibracion_id: int) -> Calibracion | None:
    return (
        db.query(Calibracion)
        .filter(Calibracion.id == calibracion_id)
        .first()
    )


def list_calibraciones(
    db: Session,
    device_id: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[Calibracion], int]:
    query = db.query(Calibracion)

    if device_id:
        query = query.filter(Calibracion.device_id == device_id)

    query = query.order_by(desc(Calibracion.created_at))
    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    return items, total


def update_calibracion(
    db: Session, calibracion_id: int, data: CalibracionUpdate
) -> Calibracion | None:
    calibracion = db.query(Calibracion).filter(
        Calibracion.id == calibracion_id
    ).first()
    if not calibracion:
        return None

    update_fields = data.model_dump(exclude_unset=True)
    for field, value in update_fields.items():
        setattr(calibracion, field, value)

    db.commit()
    db.refresh(calibracion)
    return calibracion
