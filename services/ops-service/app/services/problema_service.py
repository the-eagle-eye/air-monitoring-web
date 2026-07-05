"""ITIL v4 — Gestión de Problemas (docs/spec-itil-v4-incidencias.md §5).

Un Problema es la causa raíz de uno o más incidentes recurrentes. Las
incidencias se vinculan vía `incidencias.problema_id`.
"""
from datetime import datetime, timedelta, timezone

from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from app.models.problema import Problema
from app.models.incidencia import Incidencia
from app.schemas.problema import ProblemaCreate, ProblemaUpdate

# Estados de problema que cuentan como "ya gestionado" para excluir de sugerencias.
_PROBLEMA_OPEN_STATES = ("abierto", "investigacion")


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


def detect_reincidentes(
    db: Session, dias: int = 90, min_correctivas: int = 3,
) -> list[dict]:
    """ITIL: detecta equipos con correctivas RECURRENTES → sugiere abrir un Problema.

    Cuenta TODAS las correctivas (abiertas + cerradas) por equipo en la ventana
    `dias`. Devuelve los equipos con >= `min_correctivas`, ordenados por conteo desc.
    EXCLUYE equipos que ya tienen un Problema ABIERTO/en investigación (ya gestionado),
    para no sugerir lo que el coordinador ya está analizando.

    El sistema SUGIERE (no crea): un Problema implica análisis de causa raíz humano.
    Retorna [{device_id, correctivas, desde, incidencia_ids}].
    """
    desde = datetime.now(timezone.utc) - timedelta(days=dias)

    # equipos con un problema abierto/en investigación -> excluidos de la sugerencia
    con_problema = {
        row[0]
        for row in db.query(Problema.device_id)
        .filter(
            Problema.device_id.isnot(None),
            Problema.estado.in_(_PROBLEMA_OPEN_STATES),
        )
        .all()
    }

    # conteo de correctivas por equipo en la ventana
    rows = (
        db.query(
            Incidencia.device_id,
            func.count(Incidencia.id).label("n"),
            func.min(Incidencia.created_at).label("desde"),
        )
        .filter(
            Incidencia.tipo == "correctiva",
            Incidencia.created_at >= desde,
        )
        .group_by(Incidencia.device_id)
        .having(func.count(Incidencia.id) >= min_correctivas)
        .order_by(desc("n"))
        .all()
    )

    result: list[dict] = []
    for device_id, n, desde_min in rows:
        if device_id in con_problema:
            continue  # ya gestionado
        inc_ids = [
            i.id
            for i in db.query(Incidencia.id)
            .filter(
                Incidencia.tipo == "correctiva",
                Incidencia.device_id == device_id,
                Incidencia.created_at >= desde,
            )
            .order_by(desc(Incidencia.created_at))
            .all()
        ]
        result.append({
            "device_id": device_id,
            "correctivas": n,
            "desde": desde_min,
            "incidencia_ids": inc_ids,
        })
    return result


def problemas_resumen(db: Session) -> dict:
    """Conteo de problemas por estado (para el widget del dashboard)."""
    rows = (
        db.query(Problema.estado, func.count(Problema.id))
        .group_by(Problema.estado)
        .all()
    )
    por_estado = {estado: n for estado, n in rows}
    abiertos = por_estado.get("abierto", 0) + por_estado.get("investigacion", 0)
    return {
        "por_estado": por_estado,
        "abiertos": abiertos,
        "total": sum(por_estado.values()),
    }
