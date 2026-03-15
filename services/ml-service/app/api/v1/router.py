from fastapi import APIRouter

from app.api.v1.predictions import router as predictions_router
from app.api.v1.alerts import router as alerts_router

router = APIRouter(prefix="/api/v1")
router.include_router(predictions_router, prefix="/predictions", tags=["Predictions"])
router.include_router(alerts_router, prefix="/alerts", tags=["Alerts"])
