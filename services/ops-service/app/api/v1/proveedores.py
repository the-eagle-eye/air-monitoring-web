from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.proveedor_calibracion import ProveedorCalibracion
from app.schemas.repuesto import ProveedorResponse

router = APIRouter()


@router.get("", response_model=list[ProveedorResponse])
def list_proveedores(db: Session = Depends(get_db)):
    items = (
        db.query(ProveedorCalibracion)
        .filter(ProveedorCalibracion.estado == "activo")
        .order_by(ProveedorCalibracion.nombre)
        .all()
    )
    return [ProveedorResponse.model_validate(p) for p in items]
