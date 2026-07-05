"""ITIL v4 — Gestión de Problemas (docs/spec-itil-v4-incidencias.md §5).

Un Problema es la causa raíz de uno o más incidentes recurrentes. Las
incidencias se vinculan vía `incidencias.problema_id`.
"""
from datetime import datetime, timezone

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.models.problema import Problema
from app.models.incidencia import Incidencia
from app.schemas.problema import ProblemaCreate, ProblemaUpdate


def create_problema(db: Session, data: ProblemaCreate) -> Problema:
    problema = Problema(
        titulo=data.titulo,
        device_id=data.device_id,
        descripcion=data.descripcion,
        causa_raiz=data.causa_raiz,
    )
    db.add(problema)
    db.commit()
    db.refresh(problema)
    return problema


def get_problema(db: Session, problema_id: int) -> Problema | None:
    return db.query(Problema).filter(Problema.id == problema_id).first()


def list_problemas(db: Session, estado: str | None = None,
                   device_id: str | None = None) -> tuple[list[Problema], int]:
    query = db.query(Problema)
    if estado:
        query = query.filter(Problema.estado == estado)
    if device_id:
        query = query.filter(Problema.device_id == device_id)
    query = query.order_by(desc(Problema.created_at))
    items = query.all()
    return items, len(items)


def update_problema(db: Session, problema_id: int,
                    data: ProblemaUpdate) -> Problema | None:
    problema = get_problema(db, problema_id)
    if not problema:
        return None
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(problema, field, value)
    problema.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(problema)
    return problema


def link_incidencia(db: Session, incidencia_id: int,
                    problema_id: int | None) -> Incidencia | None:
    """Vincula (o desvincula si problema_id=None) una incidencia a un problema."""
    incidencia = db.query(Incidencia).filter(
        Incidencia.id == incidencia_id).first()
    if not incidencia:
        return None
    if problema_id is not None and get_problema(db, problema_id) is None:
        return None
    incidencia.problema_id = problema_id
    incidencia.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(incidencia)
    return incidencia


def get_incidencias_of_problema(db: Session, problema_id: int) -> list[Incidencia]:
    return (
        db.query(Incidencia)
        .filter(Incidencia.problema_id == problema_id)
        .order_by(desc(Incidencia.created_at))
        .all()
    )
