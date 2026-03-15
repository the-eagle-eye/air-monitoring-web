from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.calibracion import (
    CalibracionCreate,
    CalibracionUpdate,
    CalibracionResponse,
    CalibracionListResponse,
)
from app.services import calibracion_service

router = APIRouter()


@router.get("", response_model=CalibracionListResponse)
def list_calibraciones(
    device_id: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    items, total = calibracion_service.list_calibraciones(
        db, device_id, page, page_size
    )
    return CalibracionListResponse(
        items=[CalibracionResponse.model_validate(c) for c in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=CalibracionResponse, status_code=201)
def create_calibracion(
    data: CalibracionCreate, db: Session = Depends(get_db)
):
    calibracion = calibracion_service.create_calibracion(db, data)
    return CalibracionResponse.model_validate(calibracion)


@router.get("/{calibracion_id}", response_model=CalibracionResponse)
def get_calibracion(calibracion_id: int, db: Session = Depends(get_db)):
    calibracion = calibracion_service.get_calibracion(db, calibracion_id)
    if not calibracion:
        raise HTTPException(
            status_code=404, detail="Calibracion no encontrada"
        )
    return CalibracionResponse.model_validate(calibracion)


@router.put("/{calibracion_id}", response_model=CalibracionResponse)
def update_calibracion(
    calibracion_id: int,
    data: CalibracionUpdate,
    db: Session = Depends(get_db),
):
    calibracion = calibracion_service.update_calibracion(
        db, calibracion_id, data
    )
    if not calibracion:
        raise HTTPException(
            status_code=404, detail="Calibracion no encontrada"
        )
    return CalibracionResponse.model_validate(calibracion)
