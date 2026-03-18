from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.alerta import AlertaListResponse, AlertaResponse
from app.services.alert_service import get_alerts, get_alerts_by_device, deactivate_alerts

router = APIRouter()


@router.get("", response_model=AlertaListResponse)
def list_alerts(
    device_id: str | None = Query(None),
    estado: str | None = Query(None),
    nivel_riesgo: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    items, total = get_alerts(db, device_id, estado, nivel_riesgo, page, page_size)
    return AlertaListResponse(
        items=[AlertaResponse.model_validate(a) for a in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.patch("/deactivate/{device_id}")
def deactivate_device_alerts(device_id: str, db: Session = Depends(get_db)):
    count = deactivate_alerts(db, device_id)
    return {"device_id": device_id, "deactivated": count}


@router.get("/{device_id}", response_model=list[AlertaResponse])
def alerts_by_device(device_id: str, db: Session = Depends(get_db)):
    alerts = get_alerts_by_device(db, device_id)
    return [AlertaResponse.model_validate(a) for a in alerts]
