from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.repuesto import Repuesto
from app.schemas.repuesto import RepuestoCreate, RepuestoResponse, RepuestoUpdate

router = APIRouter()

_NOT_FOUND = "Repuesto no encontrado"
_NOT_FOUND_RESPONSE = {404: {"description": _NOT_FOUND}}


@router.get("", response_model=list[RepuestoResponse])
def list_repuestos(
    categoria: str | None = Query(None),
    db: Session = Depends(get_db),
):
    query = db.query(Repuesto).filter(Repuesto.estado == "activo")
    if categoria:
        query = query.filter(Repuesto.categoria == categoria)
    items = query.order_by(Repuesto.categoria, Repuesto.nombre).all()
    return [RepuestoResponse.model_validate(r) for r in items]


@router.post("", response_model=RepuestoResponse, status_code=201)
def create_repuesto(data: RepuestoCreate, db: Session = Depends(get_db)):
    repuesto = Repuesto(nombre=data.nombre, categoria=data.categoria)
    db.add(repuesto)
    db.commit()
    db.refresh(repuesto)
    return RepuestoResponse.model_validate(repuesto)


@router.get(
    "/{repuesto_id}",
    response_model=RepuestoResponse,
    responses=_NOT_FOUND_RESPONSE,
)
def get_repuesto(repuesto_id: int, db: Session = Depends(get_db)):
    repuesto = db.query(Repuesto).filter(Repuesto.id == repuesto_id).first()
    if not repuesto:
        raise HTTPException(status_code=404, detail=_NOT_FOUND)
    return RepuestoResponse.model_validate(repuesto)


@router.put(
    "/{repuesto_id}",
    response_model=RepuestoResponse,
    responses=_NOT_FOUND_RESPONSE,
)
def update_repuesto(
    repuesto_id: int, data: RepuestoUpdate, db: Session = Depends(get_db)
):
    repuesto = db.query(Repuesto).filter(Repuesto.id == repuesto_id).first()
    if not repuesto:
        raise HTTPException(status_code=404, detail=_NOT_FOUND)
    updates = data.model_dump(exclude_unset=True)
    for key, value in updates.items():
        setattr(repuesto, key, value)
    db.commit()
    db.refresh(repuesto)
    return RepuestoResponse.model_validate(repuesto)


@router.delete(
    "/{repuesto_id}", status_code=204, responses=_NOT_FOUND_RESPONSE
)
def delete_repuesto(repuesto_id: int, db: Session = Depends(get_db)):
    repuesto = db.query(Repuesto).filter(Repuesto.id == repuesto_id).first()
    if not repuesto:
        raise HTTPException(status_code=404, detail=_NOT_FOUND)
    repuesto.estado = "inactivo"
    db.commit()
