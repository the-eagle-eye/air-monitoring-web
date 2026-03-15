from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.prediccion import (
    PrediccionDetail,
    PrediccionListResponse,
    PrediccionResponse,
    PrediccionRunRequest,
)
from app.services.prediction_service import (
    get_latest_prediction,
    get_predictions,
    run_all_predictions,
    run_prediction,
)

router = APIRouter()


def _prediccion_to_dict(p) -> dict:
    return {
        "id": p.id,
        "device_id": p.device_id,
        "model_version": p.model_version,
        "prediction_timestamp": p.prediction_timestamp,
        "failure_probability": float(p.failure_probability),
        "remaining_useful_life_days": p.remaining_useful_life_days,
        "risk_level": p.risk_level,
        "created_at": p.created_at,
    }


@router.post("/run", response_model=list[PrediccionResponse])
def run_predictions(
    request: PrediccionRunRequest = PrediccionRunRequest(),
    db: Session = Depends(get_db),
):
    if request.device_id:
        pred = run_prediction(db, request.device_id)
        return [_prediccion_to_dict(pred)]
    else:
        preds = run_all_predictions(db)
        return [_prediccion_to_dict(p) for p in preds]


@router.get("/{device_id}", response_model=PrediccionListResponse)
def list_predictions(
    device_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    items, total = get_predictions(db, device_id, page, page_size)
    return PrediccionListResponse(
        items=[_prediccion_to_dict(p) for p in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{device_id}/latest", response_model=PrediccionDetail)
def latest_prediction(device_id: str, db: Session = Depends(get_db)):
    pred = get_latest_prediction(db, device_id)
    if not pred:
        raise HTTPException(
            status_code=404,
            detail=f"No hay predicciones para '{device_id}'",
        )
    data = _prediccion_to_dict(pred)
    data["feature_snapshot"] = pred.feature_snapshot
    return data
