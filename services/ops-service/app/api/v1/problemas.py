from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.problema import (
    ProblemaCreate,
    ProblemaListResponse,
    ProblemaResponse,
    ProblemaUpdate,
)
from app.schemas.incidencia import IncidenciaResponse
from app.services import problema_service

router = APIRouter()

_NOT_FOUND = "Problema no encontrado"
_NOT_FOUND_RESPONSE = {404: {"description": _NOT_FOUND}}


@router.get("", response_model=ProblemaListResponse)
def list_problemas(
    estado: str | None = Query(None),
    device_id: str | None = Query(None),
    db: Session = Depends(get_db),
):
    items, total = problema_service.list_problemas(db, estado, device_id)
    return ProblemaListResponse(
        items=[ProblemaResponse.model_validate(p) for p in items],
        total=total,
    )


@router.post("", response_model=ProblemaResponse, status_code=201)
def create_problema(data: ProblemaCreate, db: Session = Depends(get_db)):
    return ProblemaResponse.model_validate(
        problema_service.create_problema(db, data))


# ITIL: equipos con correctivas recurrentes -> SUGERENCIA de abrir un Problema.
# Debe ir ANTES de /{problema_id} para no ser capturada como problema_id.
@router.get("/reincidentes")
def reincidentes(
    dias: int = Query(90, ge=1, le=365),
    min_correctivas: int = Query(3, ge=2, le=20),
    db: Session = Depends(get_db),
):
    return {
        "dias": dias,
        "min_correctivas": min_correctivas,
        "items": problema_service.detect_reincidentes(db, dias, min_correctivas),
    }


@router.get("/resumen")
def resumen(db: Session = Depends(get_db)):
    return problema_service.problemas_resumen(db)


@router.get(
    "/{problema_id}",
    response_model=ProblemaResponse,
    responses=_NOT_FOUND_RESPONSE,
)
def get_problema(problema_id: int, db: Session = Depends(get_db)):
    problema = problema_service.get_problema(db, problema_id)
    if not problema:
        raise HTTPException(status_code=404, detail=_NOT_FOUND)
    return ProblemaResponse.model_validate(problema)


@router.get(
    "/{problema_id}/incidencias",
    response_model=list[IncidenciaResponse],
    responses=_NOT_FOUND_RESPONSE,
)
def get_incidencias(problema_id: int, db: Session = Depends(get_db)):
    if problema_service.get_problema(db, problema_id) is None:
        raise HTTPException(status_code=404, detail=_NOT_FOUND)
    return [
        IncidenciaResponse.model_validate(i)
        for i in problema_service.get_incidencias_of_problema(db, problema_id)
    ]


@router.put(
    "/{problema_id}",
    response_model=ProblemaResponse,
    responses=_NOT_FOUND_RESPONSE,
)
def update_problema(problema_id: int, data: ProblemaUpdate,
                    db: Session = Depends(get_db)):
    problema = problema_service.update_problema(db, problema_id, data)
    if not problema:
        raise HTTPException(status_code=404, detail=_NOT_FOUND)
    return ProblemaResponse.model_validate(problema)
