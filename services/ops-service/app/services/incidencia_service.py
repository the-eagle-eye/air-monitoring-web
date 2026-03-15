from datetime import datetime, timezone, timedelta

import httpx
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc, func

from app.models.incidencia import Incidencia
from app.models.calibracion import Calibracion
from app.schemas.incidencia import IncidenciaCreate, IncidenciaUpdate


def create_incidencia(db: Session, data: IncidenciaCreate) -> Incidencia:
    incidencia = Incidencia(
        device_id=data.device_id,
        tipo=data.tipo,
        descripcion=data.descripcion,
        prioridad=data.prioridad,
        responsable_id=data.responsable_id,
    )
    db.add(incidencia)
    db.commit()
    db.refresh(incidencia)
    return incidencia


def get_incidencia(db: Session, incidencia_id: int) -> Incidencia | None:
    return (
        db.query(Incidencia)
        .options(
            joinedload(Incidencia.mantenimiento_correctivo),
            joinedload(Incidencia.calibracion),
            joinedload(Incidencia.responsable),
        )
        .filter(Incidencia.id == incidencia_id)
        .first()
    )


def list_incidencias(
    db: Session,
    device_id: str | None = None,
    tipo: str | None = None,
    estado: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[Incidencia], int]:
    query = db.query(Incidencia)

    if device_id:
        query = query.filter(Incidencia.device_id == device_id)
    if tipo:
        query = query.filter(Incidencia.tipo == tipo)
    if estado:
        query = query.filter(Incidencia.estado == estado)

    query = query.order_by(desc(Incidencia.created_at))
    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    return items, total


def update_incidencia(
    db: Session, incidencia_id: int, data: IncidenciaUpdate
) -> Incidencia | None:
    incidencia = db.query(Incidencia).filter(
        Incidencia.id == incidencia_id
    ).first()
    if not incidencia:
        return None

    update_fields = data.model_dump(exclude_unset=True)
    for field, value in update_fields.items():
        setattr(incidencia, field, value)
    incidencia.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(incidencia)

    # Regla: si correctiva se finaliza, auto-crear incidencia de calibracion
    if (
        incidencia.tipo == "correctiva"
        and incidencia.estado == "finalizado"
    ):
        _auto_create_calibracion(db, incidencia)

    return incidencia


def _auto_create_calibracion(
    db: Session, correctiva: Incidencia
) -> Incidencia:
    """Crear incidencia de calibracion cuando una correctiva finaliza."""
    cal_incidencia = Incidencia(
        device_id=correctiva.device_id,
        tipo="calibracion",
        descripcion=(
            f"Calibracion requerida post-mantenimiento correctivo "
            f"(incidencia #{correctiva.id})"
        ),
        prioridad="alta",
    )
    db.add(cal_incidencia)
    db.commit()
    db.refresh(cal_incidencia)

    calibracion = Calibracion(
        incidencia_id=cal_incidencia.id,
        device_id=correctiva.device_id,
    )
    db.add(calibracion)
    db.commit()
    return cal_incidencia


def evaluate_alerts(db: Session, ml_service_url: str) -> list[Incidencia]:
    """Evaluar alertas del ml-service y crear incidencias automaticas."""
    try:
        response = httpx.get(
            f"{ml_service_url}/api/v1/alerts",
            params={"estado": "activa", "nivel_riesgo": "alta", "page_size": "200"},
            timeout=10.0,
        )
        response.raise_for_status()
        data = response.json()
    except (httpx.HTTPError, Exception):
        return []

    alertas = data.get("items", [])
    today_start = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    )

    # Agrupar alertas de hoy por device_id
    device_counts: dict[str, int] = {}
    for alerta in alertas:
        created = alerta.get("created_at", "")
        try:
            created_dt = datetime.fromisoformat(created)
            if created_dt >= today_start:
                did = alerta["device_id"]
                device_counts[did] = device_counts.get(did, 0) + 1
        except (ValueError, KeyError):
            continue

    created_incidencias: list[Incidencia] = []
    for device_id, count in device_counts.items():
        if count < 2:
            continue

        # Verificar si ya existe incidencia correctiva hoy para este equipo
        existing = (
            db.query(Incidencia)
            .filter(
                Incidencia.device_id == device_id,
                Incidencia.tipo == "correctiva",
                Incidencia.created_at >= today_start,
            )
            .first()
        )
        if existing:
            continue

        incidencia = Incidencia(
            device_id=device_id,
            tipo="correctiva",
            descripcion=(
                f"Incidencia automatica: {count} alertas altas detectadas "
                f"para equipo {device_id} en el dia de hoy"
            ),
            prioridad="alta",
        )
        db.add(incidencia)
        db.commit()
        db.refresh(incidencia)
        created_incidencias.append(incidencia)

    return created_incidencias
