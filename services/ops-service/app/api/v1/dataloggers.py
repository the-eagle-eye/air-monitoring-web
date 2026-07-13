from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.datalogger import Datalogger
from app.schemas.datalogger import (
    DataloggerCreate,
    DataloggerUpdate,
    DataloggerResponse,
)

router = APIRouter()

_NOT_FOUND = "Datalogger no encontrado"
_NOT_FOUND_RESPONSE = {404: {"description": _NOT_FOUND}}
_CONFLICT_RESPONSE = {409: {"description": "Codigo interno ya existe"}}


@router.get("", response_model=list[DataloggerResponse])
def list_dataloggers(db: Session = Depends(get_db)):
    items = db.query(Datalogger).order_by(Datalogger.nombre).all()
    return [DataloggerResponse.model_validate(d) for d in items]


@router.post(
    "",
    response_model=DataloggerResponse,
    status_code=201,
    responses=_CONFLICT_RESPONSE,
)
def create_datalogger(data: DataloggerCreate, db: Session = Depends(get_db)):
    existing = (
        db.query(Datalogger)
        .filter(Datalogger.codigo_interno == data.codigo_interno)
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=409, detail="Codigo interno ya existe"
        )

    dl = Datalogger(**data.model_dump())
    db.add(dl)
    db.commit()
    db.refresh(dl)
    return DataloggerResponse.model_validate(dl)


@router.get(
    "/{datalogger_id}",
    response_model=DataloggerResponse,
    responses=_NOT_FOUND_RESPONSE,
)
def get_datalogger(datalogger_id: int, db: Session = Depends(get_db)):
    dl = db.query(Datalogger).filter(Datalogger.id == datalogger_id).first()
    if not dl:
        raise HTTPException(status_code=404, detail=_NOT_FOUND)
    return DataloggerResponse.model_validate(dl)


@router.put(
    "/{datalogger_id}",
    response_model=DataloggerResponse,
    responses=_NOT_FOUND_RESPONSE,
)
def update_datalogger(
    datalogger_id: int, data: DataloggerUpdate, db: Session = Depends(get_db)
):
    dl = db.query(Datalogger).filter(Datalogger.id == datalogger_id).first()
    if not dl:
        raise HTTPException(status_code=404, detail=_NOT_FOUND)

    update_fields = data.model_dump(exclude_unset=True)
    for field, value in update_fields.items():
        setattr(dl, field, value)
    dl.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(dl)
    return DataloggerResponse.model_validate(dl)
