from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.equipo import Equipo
from app.models.lectura_iot import LecturaIoT
from app.schemas.equipo import EquipoCreate, EquipoResponse, EquipoUpdate
from app.schemas.lectura_iot import (
    LecturaIoTCreate,
    LecturaIoTDetail,
    LecturaIoTListResponse,
    LecturaIoTResponse,
)
from app.services.ingestion_service import validate_and_store_reading

router = APIRouter()


def _lectura_to_response(lectura: LecturaIoT) -> dict:
    """Convert a LecturaIoT ORM instance to a dict with equipo_device_id."""
    return {
        "id": lectura.id,
        "device_id": lectura.device_id,
        "equipo_device_id": lectura.equipo.device_id,
        "timestamp_lectura": lectura.timestamp_lectura,
        "so2_ppb": float(lectura.so2_ppb) if lectura.so2_ppb is not None else None,
        "h2s_ppb": float(lectura.h2s_ppb) if lectura.h2s_ppb is not None else None,
        "reaction_temp": (
            float(lectura.reaction_temp)
            if lectura.reaction_temp is not None
            else None
        ),
        "izs_temp": (
            float(lectura.izs_temp) if lectura.izs_temp is not None else None
        ),
        "pmt_temp": (
            float(lectura.pmt_temp) if lectura.pmt_temp is not None else None
        ),
        "sample_flow": (
            float(lectura.sample_flow) if lectura.sample_flow is not None else None
        ),
        "pressure": (
            float(lectura.pressure) if lectura.pressure is not None else None
        ),
        "uv_lamp_intensity": (
            float(lectura.uv_lamp_intensity)
            if lectura.uv_lamp_intensity is not None
            else None
        ),
        "box_temp": (
            float(lectura.box_temp) if lectura.box_temp is not None else None
        ),
        "hvps_v": float(lectura.hvps_v) if lectura.hvps_v is not None else None,
        "conv_temp": (
            float(lectura.conv_temp) if lectura.conv_temp is not None else None
        ),
        "ozone_flow": (
            float(lectura.ozone_flow) if lectura.ozone_flow is not None else None
        ),
        "procesado": lectura.procesado,
        "created_at": lectura.created_at,
    }


@router.post("/readings", response_model=LecturaIoTResponse)
def create_reading(payload: LecturaIoTCreate, db: Session = Depends(get_db)):
    lectura = validate_and_store_reading(db, payload)
    return _lectura_to_response(lectura)


@router.get("/readings/{device_id}", response_model=LecturaIoTListResponse)
def get_readings(
    device_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=300),
    db: Session = Depends(get_db),
):
    equipo = db.query(Equipo).filter(Equipo.device_id == device_id).first()
    if not equipo:
        raise HTTPException(status_code=404, detail=f"Equipo '{device_id}' no encontrado")

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


@router.get("/readings/{device_id}/latest", response_model=LecturaIoTDetail)
def get_latest_reading(device_id: str, db: Session = Depends(get_db)):
    equipo = db.query(Equipo).filter(Equipo.device_id == device_id).first()
    if not equipo:
        raise HTTPException(status_code=404, detail=f"Equipo '{device_id}' no encontrado")

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


@router.get("/equipos/{device_id}", response_model=EquipoResponse)
def get_equipo(device_id: str, db: Session = Depends(get_db)):
    equipo = db.query(Equipo).filter(Equipo.device_id == device_id).first()
    if not equipo:
        raise HTTPException(
            status_code=404, detail=f"Equipo '{device_id}' no encontrado"
        )
    return equipo


@router.post("/equipos", response_model=EquipoResponse, status_code=201)
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


@router.put("/equipos/{device_id}", response_model=EquipoResponse)
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


@router.delete("/equipos/{device_id}")
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
