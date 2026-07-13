from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.schemas.calibracion import (
    CalibracionCreate,
    CalibracionUpdate,
    CalibracionResponse,
    CalibracionListResponse,
)
from app.schemas.incidencia import IncidenciaResponse
from app.services import calibracion_service, incidencia_service

router = APIRouter()

_NOT_FOUND_RESPONSE = {404: {"description": "Calibracion no encontrada"}}


@router.post("/check-annual")
def check_annual_calibrations(db: Session = Depends(get_db)):
    created = incidencia_service.check_annual_calibrations(
        db, settings.IOT_SERVICE_URL
    )
    return {
        "created": len(created),
        "incidencias": [
            IncidenciaResponse.model_validate(i) for i in created
        ],
    }


def _calibracion_with_estado(cal) -> CalibracionResponse:
    resp = CalibracionResponse.model_validate(cal)
    if cal.incidencia:
        resp.incidencia_estado = cal.incidencia.estado
    return resp


@router.get("", response_model=CalibracionListResponse)
def list_calibraciones(
    device_id: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    x_user_rol: str | None = Header(None),
    x_user_id: str | None = Header(None),
    db: Session = Depends(get_db),
):
    # El técnico solo ve las calibraciones de sus incidencias asignadas.
    responsable_id = None
    if x_user_rol == "tecnico" and x_user_id:
        try:
            responsable_id = int(x_user_id)
        except ValueError:
            pass
    items, total = calibracion_service.list_calibraciones(
        db, device_id, page, page_size, responsable_id=responsable_id
    )
    return CalibracionListResponse(
        items=[_calibracion_with_estado(c) for c in items],
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


@router.get(
    "/{calibracion_id}",
    response_model=CalibracionResponse,
    responses=_NOT_FOUND_RESPONSE,
)
def get_calibracion(calibracion_id: int, db: Session = Depends(get_db)):
    calibracion = calibracion_service.get_calibracion(db, calibracion_id)
    if not calibracion:
        raise HTTPException(
            status_code=404, detail="Calibracion no encontrada"
        )
    return _calibracion_with_estado(calibracion)


@router.put(
    "/{calibracion_id}",
    response_model=CalibracionResponse,
    responses=_NOT_FOUND_RESPONSE,
)
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
    return _calibracion_with_estado(calibracion)
