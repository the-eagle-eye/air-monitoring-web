from fastapi import APIRouter

from app.api.v1.health import router as health_router

router = APIRouter(prefix="/api/v1")
# El modelo Random Forest (/predictions, /alerts) fue retirado por completo:
# reemplazado por el monitor de salud no supervisado (/health-monitor).
# Ver docs/spec-racionalizacion-dashboard-e-incidencias.md (Decisión C1).
router.include_router(health_router, prefix="/health-monitor", tags=["HealthMonitor"])
