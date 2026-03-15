from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.incidencia import Incidencia
from app.models.mantenimiento import MantenimientoCorrectivo, MantenimientoRepuesto
from app.models.archivo_adjunto import ArchivoAdjunto
from app.schemas.mantenimiento import MantenimientoCreate


def submit_mantenimiento(
    db: Session, incidencia_id: int, data: MantenimientoCreate
) -> MantenimientoCorrectivo:
    incidencia = db.query(Incidencia).filter(
        Incidencia.id == incidencia_id
    ).first()
    if not incidencia:
        raise HTTPException(status_code=404, detail="Incidencia no encontrada")

    if incidencia.tipo != "correctiva":
        raise HTTPException(
            status_code=400,
            detail="Solo incidencias de tipo correctiva aceptan mantenimiento",
        )

    existing = (
        db.query(MantenimientoCorrectivo)
        .filter(MantenimientoCorrectivo.incidencia_id == incidencia_id)
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=409,
            detail="Ya existe un mantenimiento para esta incidencia",
        )

    mantenimiento = MantenimientoCorrectivo(
        incidencia_id=incidencia_id,
        diagnostico=data.diagnostico,
        acciones_realizadas=data.acciones_realizadas,
        conclusion=data.conclusion,
        fecha_ejecucion=data.fecha_ejecucion,
    )
    db.add(mantenimiento)
    db.flush()

    for repuesto_id in data.repuesto_ids:
        junction = MantenimientoRepuesto(
            mantenimiento_id=mantenimiento.id,
            repuesto_id=repuesto_id,
        )
        db.add(junction)

    for adjunto in data.adjuntos:
        archivo = ArchivoAdjunto(
            entidad_tipo="mantenimiento",
            entidad_id=mantenimiento.id,
            filename=adjunto.filename,
            file_url=adjunto.file_url,
        )
        db.add(archivo)

    db.commit()
    db.refresh(mantenimiento)
    return mantenimiento
