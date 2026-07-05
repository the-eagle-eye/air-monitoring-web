from datetime import datetime, timezone

from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc

from app.models.calibracion import Calibracion
from app.models.incidencia import Incidencia
from app.schemas.calibracion import CalibracionCreate, CalibracionUpdate


def create_calibracion(db: Session, data: CalibracionCreate) -> Calibracion:
    calibracion = Calibracion(
        incidencia_id=data.incidencia_id,
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
        .options(joinedload(Calibracion.incidencia))
        .filter(Calibracion.id == calibracion_id)
        .first()
    )


def list_calibraciones(
    db: Session,
    device_id: str | None = None,
    page: int = 1,
    page_size: int = 50,
    responsable_id: int | None = None,
) -> tuple[list[Calibracion], int]:
    query = db.query(Calibracion).options(joinedload(Calibracion.incidencia))

    if device_id:
        query = query.filter(Calibracion.device_id == device_id)

    # El técnico solo ve las calibraciones de SUS incidencias asignadas.
    if responsable_id is not None:
        query = query.join(
            Incidencia, Calibracion.incidencia_id == Incidencia.id
        ).filter(Incidencia.responsable_id == responsable_id)

    query = query.order_by(desc(Calibracion.created_at))
    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    return items, total


def update_calibracion(
    db: Session, calibracion_id: int, data: CalibracionUpdate
) -> Calibracion | None:
    calibracion = (
        db.query(Calibracion)
        .options(joinedload(Calibracion.incidencia))
        .filter(Calibracion.id == calibracion_id)
        .first()
    )
    if not calibracion:
        return None

    update_fields = data.model_dump(exclude_unset=True)
    for field, value in update_fields.items():
        setattr(calibracion, field, value)

    # Auto-completar si los 4 campos obligatorios estan llenos
    if (
        calibracion.fecha_calibracion
        and calibracion.nota
        and calibracion.certificado_url
        and calibracion.proveedor_id
    ):
        calibracion.estado = "completada"
        if calibracion.incidencia:
            calibracion.incidencia.estado = "finalizado"
            calibracion.incidencia.updated_at = datetime.now(timezone.utc)

    db.commit()
    # Re-fetch con joinedload para que la relacion incidencia este disponible
    return (
        db.query(Calibracion)
        .options(joinedload(Calibracion.incidencia))
        .filter(Calibracion.id == calibracion_id)
        .first()
    )
