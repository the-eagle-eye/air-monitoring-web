from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.proveedor_calibracion import ProveedorCalibracion
from app.schemas.repuesto import ProveedorCreate, ProveedorResponse, ProveedorUpdate

router = APIRouter()

_NOT_FOUND = "Proveedor no encontrado"
_NOT_FOUND_RESPONSE = {404: {"description": _NOT_FOUND}}


@router.get("", response_model=list[ProveedorResponse])
def list_proveedores(db: Session = Depends(get_db)):
    items = (
        db.query(ProveedorCalibracion)
        .filter(ProveedorCalibracion.estado == "activo")
        .order_by(ProveedorCalibracion.nombre)
        .all()
    )
    return [ProveedorResponse.model_validate(p) for p in items]


@router.post("", response_model=ProveedorResponse, status_code=201)
def create_proveedor(data: ProveedorCreate, db: Session = Depends(get_db)):
    proveedor = ProveedorCalibracion(nombre=data.nombre)
    db.add(proveedor)
    db.commit()
    db.refresh(proveedor)
    return ProveedorResponse.model_validate(proveedor)


@router.get(
    "/{proveedor_id}",
    response_model=ProveedorResponse,
    responses=_NOT_FOUND_RESPONSE,
)
def get_proveedor(proveedor_id: int, db: Session = Depends(get_db)):
    proveedor = (
        db.query(ProveedorCalibracion)
        .filter(ProveedorCalibracion.id == proveedor_id)
        .first()
    )
    if not proveedor:
        raise HTTPException(status_code=404, detail=_NOT_FOUND)
    return ProveedorResponse.model_validate(proveedor)


@router.put(
    "/{proveedor_id}",
    response_model=ProveedorResponse,
    responses=_NOT_FOUND_RESPONSE,
)
def update_proveedor(
    proveedor_id: int, data: ProveedorUpdate, db: Session = Depends(get_db)
):
    proveedor = (
        db.query(ProveedorCalibracion)
        .filter(ProveedorCalibracion.id == proveedor_id)
        .first()
    )
    if not proveedor:
        raise HTTPException(status_code=404, detail=_NOT_FOUND)
    updates = data.model_dump(exclude_unset=True)
    for key, value in updates.items():
        setattr(proveedor, key, value)
    db.commit()
    db.refresh(proveedor)
    return ProveedorResponse.model_validate(proveedor)


@router.delete(
    "/{proveedor_id}", status_code=204, responses=_NOT_FOUND_RESPONSE
)
def delete_proveedor(proveedor_id: int, db: Session = Depends(get_db)):
    proveedor = (
        db.query(ProveedorCalibracion)
        .filter(ProveedorCalibracion.id == proveedor_id)
        .first()
    )
    if not proveedor:
        raise HTTPException(status_code=404, detail=_NOT_FOUND)
    proveedor.estado = "inactivo"
    db.commit()
