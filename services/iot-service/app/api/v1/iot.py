from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.equipo import Equipo
from app.models.lectura_iot import LecturaIoT
from app.schemas.equipo import (
    EquipoConfirmar,
    EquipoCreate,
    EquipoResponse,
    EquipoUpdate,
)
from app.schemas.lectura_iot import (
    LecturaIoTCreate,
    LecturaIoTDetail,
    LecturaIoTListResponse,
    LecturaIoTResponse,
)
from app.services.ingestion_service import validate_and_store_reading
from app.services.device_onboarding import (
    ESTADO_NO_CONFIRMADO,
    ESTADO_ACTIVO,
)

router = APIRouter()

_EQUIPO_NOT_FOUND_RESPONSE = {404: {"description": "Equipo no encontrado"}}
_LATEST_READING_RESPONSES = {
    404: {"description": "Equipo o lecturas no encontradas"}
}
_EQUIPO_CONFLICT_RESPONSE = {
    409: {"description": "Equipo ya existe o no esta en cuarentena"}
}
_CONFIRMAR_RESPONSES = {
    **_EQUIPO_NOT_FOUND_RESPONSE,
    **_EQUIPO_CONFLICT_RESPONSE,
}


def _lectura_to_response(lectura: LecturaIoT) -> dict:
    """Convert a LecturaIoT ORM instance to a dict with equipo_device_id."""
    return {
        "id": lectura.id,
        "device_id": lectura.device_id,
        "equipo_device_id": lectura.equipo.device_id,
        "timestamp_lectura": lectura.timestamp_lectura,
        "sensors": lectura.sensors or {},
        "procesado": lectura.procesado,
        "created_at": lectura.created_at,
    }


@router.post("/readings", response_model=LecturaIoTResponse)
def create_reading(payload: LecturaIoTCreate, db: Session = Depends(get_db)):
    lectura = validate_and_store_reading(db, payload)
    return _lectura_to_response(lectura)


@router.get("/readings/all", response_model=list[LecturaIoTResponse])
def get_all_readings_unpaged(db: Session = Depends(get_db)):
    items = (
        db.query(LecturaIoT)
        .join(Equipo, LecturaIoT.device_id == Equipo.id)
        .order_by(LecturaIoT.timestamp_lectura.desc())
        .all()
    )
    return [_lectura_to_response(item) for item in items]


@router.get("/readings", response_model=LecturaIoTListResponse)
def get_all_readings(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=300),
    db: Session = Depends(get_db),
):
    query = (
        db.query(LecturaIoT)
        .join(Equipo, LecturaIoT.device_id == Equipo.id)
        .order_by(LecturaIoT.timestamp_lectura.desc())
    )
    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()

    return LecturaIoTListResponse(
        items=[_lectura_to_response(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/readings/{device_id}",
    response_model=LecturaIoTListResponse,
    responses=_EQUIPO_NOT_FOUND_RESPONSE,
)
def get_readings(
    device_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=300),
    db: Session = Depends(get_db),
):
    equipo = db.query(Equipo).filter(Equipo.device_id == device_id).first()
    if not equipo:
        raise HTTPException(
            status_code=404, detail=f"Equipo '{device_id}' no encontrado"
        )

    query = (
        db.query(LecturaIoT)
        .filter(LecturaIoT.device_id == equipo.id)
        .order_by(LecturaIoT.timestamp_lectura.desc())
    )
    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()

    return LecturaIoTListResponse(
        items=[_lectura_to_response(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/readings/{device_id}/latest",
    response_model=LecturaIoTDetail,
    responses=_LATEST_READING_RESPONSES,
)
def get_latest_reading(device_id: str, db: Session = Depends(get_db)):
    equipo = db.query(Equipo).filter(Equipo.device_id == device_id).first()
    if not equipo:
        raise HTTPException(
            status_code=404, detail=f"Equipo '{device_id}' no encontrado"
        )

    lectura = (
        db.query(LecturaIoT)
        .filter(LecturaIoT.device_id == equipo.id)
        .order_by(LecturaIoT.timestamp_lectura.desc())
        .first()
    )
    if not lectura:
        raise HTTPException(status_code=404, detail="No hay lecturas para este equipo")

    data = _lectura_to_response(lectura)
    data["raw_payload"] = lectura.raw_payload
    return data


@router.get("/equipos", response_model=list[EquipoResponse])
def list_equipos(db: Session = Depends(get_db)):
    return db.query(Equipo).order_by(Equipo.device_id).all()


# C8: equipos en cuarentena pendientes de confirmar. Debe ir ANTES de la ruta
# /equipos/{device_id} para no ser capturada como device_id="pendientes".
@router.get("/equipos/pendientes", response_model=list[EquipoResponse])
def list_equipos_pendientes(db: Session = Depends(get_db)):
    return (
        db.query(Equipo)
        .filter(Equipo.estado == ESTADO_NO_CONFIRMADO)
        .order_by(Equipo.fecha_registro.desc())
        .all()
    )


@router.get(
    "/equipos/{device_id}",
    response_model=EquipoResponse,
    responses=_EQUIPO_NOT_FOUND_RESPONSE,
)
def get_equipo(device_id: str, db: Session = Depends(get_db)):
    equipo = db.query(Equipo).filter(Equipo.device_id == device_id).first()
    if not equipo:
        raise HTTPException(
            status_code=404, detail=f"Equipo '{device_id}' no encontrado"
        )
    return equipo


@router.post(
    "/equipos",
    response_model=EquipoResponse,
    status_code=201,
    responses=_EQUIPO_CONFLICT_RESPONSE,
)
def create_equipo(data: EquipoCreate, db: Session = Depends(get_db)):
    existing = (
        db.query(Equipo).filter(Equipo.device_id == data.device_id).first()
    )
    if existing:
        raise HTTPException(
            status_code=409, detail=f"Equipo '{data.device_id}' ya existe"
        )
    equipo = Equipo(**data.model_dump())
    db.add(equipo)
    db.commit()
    db.refresh(equipo)
    return equipo


# C8: confirmar un equipo en cuarentena (no_confirmado -> activo). RBAC en el
# gateway lo restringe a coordinador/admin.
@router.post(
    "/equipos/{device_id}/confirmar",
    response_model=EquipoResponse,
    responses=_CONFIRMAR_RESPONSES,
)
def confirmar_equipo(
    device_id: str, data: EquipoConfirmar, db: Session = Depends(get_db)
):
    equipo = db.query(Equipo).filter(Equipo.device_id == device_id).first()
    if not equipo:
        raise HTTPException(
            status_code=404, detail=f"Equipo '{device_id}' no encontrado"
        )
    if equipo.estado != ESTADO_NO_CONFIRMADO:
        raise HTTPException(
            status_code=409,
            detail=(
                f"Equipo '{device_id}' no está en cuarentena "
                f"(estado: {equipo.estado})"
            ),
        )
    # completar metadatos provistos (solo los enviados) y activar
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(equipo, field, value)
    equipo.estado = ESTADO_ACTIVO
    equipo.fecha_actualizacion = datetime.now(timezone.utc)
    db.commit()
    db.refresh(equipo)
    return equipo


@router.put(
    "/equipos/{device_id}",
    response_model=EquipoResponse,
    responses=_EQUIPO_NOT_FOUND_RESPONSE,
)
def update_equipo(
    device_id: str, data: EquipoUpdate, db: Session = Depends(get_db)
):
    equipo = db.query(Equipo).filter(Equipo.device_id == device_id).first()
    if not equipo:
        raise HTTPException(
            status_code=404, detail=f"Equipo '{device_id}' no encontrado"
        )
    update_fields = data.model_dump(exclude_unset=True)
    for field, value in update_fields.items():
        setattr(equipo, field, value)
    equipo.fecha_actualizacion = datetime.now(timezone.utc)
    db.commit()
    db.refresh(equipo)
    return equipo


@router.delete(
    "/equipos/{device_id}", responses=_EQUIPO_NOT_FOUND_RESPONSE
)
def delete_equipo(device_id: str, db: Session = Depends(get_db)):
    equipo = db.query(Equipo).filter(Equipo.device_id == device_id).first()
    if not equipo:
        raise HTTPException(
            status_code=404, detail=f"Equipo '{device_id}' no encontrado"
        )
    equipo.estado = "inactivo"
    equipo.fecha_actualizacion = datetime.now(timezone.utc)
    db.commit()
    return {"detail": "Equipo eliminado"}
