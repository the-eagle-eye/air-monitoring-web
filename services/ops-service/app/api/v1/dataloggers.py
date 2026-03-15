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


@router.get("", response_model=list[DataloggerResponse])
def list_dataloggers(db: Session = Depends(get_db)):
    items = db.query(Datalogger).order_by(Datalogger.nombre).all()
    return [DataloggerResponse.model_validate(d) for d in items]


@router.post("", response_model=DataloggerResponse, status_code=201)
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


@router.get("/{datalogger_id}", response_model=DataloggerResponse)
def get_datalogger(datalogger_id: int, db: Session = Depends(get_db)):
    dl = db.query(Datalogger).filter(Datalogger.id == datalogger_id).first()
    if not dl:
        raise HTTPException(status_code=404, detail="Datalogger no encontrado")
    return DataloggerResponse.model_validate(dl)


@router.put("/{datalogger_id}", response_model=DataloggerResponse)
def update_datalogger(
    datalogger_id: int, data: DataloggerUpdate, db: Session = Depends(get_db)
):
    dl = db.query(Datalogger).filter(Datalogger.id == datalogger_id).first()
    if not dl:
        raise HTTPException(status_code=404, detail="Datalogger no encontrado")

    update_fields = data.model_dump(exclude_unset=True)
    for field, value in update_fields.items():
        setattr(dl, field, value)
    dl.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(dl)
    return DataloggerResponse.model_validate(dl)
