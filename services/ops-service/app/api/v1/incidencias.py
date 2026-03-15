from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.config import settings
from app.schemas.incidencia import (
    IncidenciaCreate,
    IncidenciaUpdate,
    IncidenciaResponse,
    IncidenciaListResponse,
)
from app.schemas.mantenimiento import MantenimientoCreate, MantenimientoResponse
from app.services import incidencia_service, mantenimiento_service

router = APIRouter()


@router.get("", response_model=IncidenciaListResponse)
def list_incidencias(
    device_id: str | None = Query(None),
    tipo: str | None = Query(None),
    estado: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    items, total = incidencia_service.list_incidencias(
        db, device_id, tipo, estado, page, page_size
    )
    return IncidenciaListResponse(
        items=[IncidenciaResponse.model_validate(i) for i in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=IncidenciaResponse, status_code=201)
def create_incidencia(data: IncidenciaCreate, db: Session = Depends(get_db)):
    incidencia = incidencia_service.create_incidencia(db, data)
    return IncidenciaResponse.model_validate(incidencia)


@router.get("/{incidencia_id}", response_model=IncidenciaResponse)
def get_incidencia(incidencia_id: int, db: Session = Depends(get_db)):
    incidencia = incidencia_service.get_incidencia(db, incidencia_id)
    if not incidencia:
        raise HTTPException(
            status_code=404, detail="Incidencia no encontrada"
        )
    return IncidenciaResponse.model_validate(incidencia)


@router.put("/{incidencia_id}", response_model=IncidenciaResponse)
def update_incidencia(
    incidencia_id: int,
    data: IncidenciaUpdate,
    db: Session = Depends(get_db),
):
    incidencia = incidencia_service.update_incidencia(db, incidencia_id, data)
    if not incidencia:
        raise HTTPException(
            status_code=404, detail="Incidencia no encontrada"
        )
    return IncidenciaResponse.model_validate(incidencia)


@router.post(
    "/{incidencia_id}/mantenimiento",
    response_model=MantenimientoResponse,
    status_code=201,
)
def submit_mantenimiento(
    incidencia_id: int,
    data: MantenimientoCreate,
    db: Session = Depends(get_db),
):
    mantenimiento = mantenimiento_service.submit_mantenimiento(
        db, incidencia_id, data
    )
    return MantenimientoResponse.model_validate(mantenimiento)


@router.post("/evaluar", response_model=list[IncidenciaResponse])
def evaluar_alertas(db: Session = Depends(get_db)):
    created = incidencia_service.evaluate_alerts(db, settings.ML_SERVICE_URL)
    return [IncidenciaResponse.model_validate(i) for i in created]
