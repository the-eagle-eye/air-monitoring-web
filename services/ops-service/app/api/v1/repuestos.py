from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.repuesto import Repuesto
from app.schemas.repuesto import RepuestoResponse

router = APIRouter()


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
