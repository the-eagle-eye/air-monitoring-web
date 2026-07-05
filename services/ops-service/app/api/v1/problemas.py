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


@router.get("/{problema_id}", response_model=ProblemaResponse)
def get_problema(problema_id: int, db: Session = Depends(get_db)):
    problema = problema_service.get_problema(db, problema_id)
    if not problema:
        raise HTTPException(status_code=404, detail="Problema no encontrado")
    return ProblemaResponse.model_validate(problema)


@router.get("/{problema_id}/incidencias", response_model=list[IncidenciaResponse])
def get_incidencias(problema_id: int, db: Session = Depends(get_db)):
    if problema_service.get_problema(db, problema_id) is None:
        raise HTTPException(status_code=404, detail="Problema no encontrado")
    return [
        IncidenciaResponse.model_validate(i)
        for i in problema_service.get_incidencias_of_problema(db, problema_id)
    ]


@router.put("/{problema_id}", response_model=ProblemaResponse)
def update_problema(problema_id: int, data: ProblemaUpdate,
                    db: Session = Depends(get_db)):
    problema = problema_service.update_problema(db, problema_id, data)
    if not problema:
        raise HTTPException(status_code=404, detail="Problema no encontrado")
    return ProblemaResponse.model_validate(problema)
