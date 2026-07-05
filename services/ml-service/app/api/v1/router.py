from fastapi import APIRouter

from app.api.v1.predictions import router as predictions_router
from app.api.v1.alerts import router as alerts_router
from app.api.v1.health import router as health_router

router = APIRouter(prefix="/api/v1")
# DEPRECADO (retiro del modelo Random Forest): /predictions y /alerts pertenecen
# al modelo RF, reemplazado por el monitor de salud no supervisado (/health-monitor).
# Se marcan deprecated y ya no crean incidencias. Retiro físico: PR dedicado.
# Ver docs/spec-racionalizacion-dashboard-e-incidencias.md (Decisión C1).
router.include_router(predictions_router, prefix="/predictions",
                      tags=["Predictions (deprecated)"], deprecated=True)
router.include_router(alerts_router, prefix="/alerts",
                      tags=["Alerts (deprecated)"], deprecated=True)
router.include_router(health_router, prefix="/health-monitor", tags=["HealthMonitor"])
