from fastapi import APIRouter

from app.api.v1.dataloggers import router as dataloggers_router
from app.api.v1.incidencias import router as incidencias_router
from app.api.v1.calibraciones import router as calibraciones_router
from app.api.v1.repuestos import router as repuestos_router
from app.api.v1.usuarios import router as usuarios_router
from app.api.v1.proveedores import router as proveedores_router
from app.api.v1.reportes import router as reportes_router

router = APIRouter(prefix="/api/v1")

router.include_router(dataloggers_router, prefix="/dataloggers", tags=["Dataloggers"])
router.include_router(incidencias_router, prefix="/incidencias", tags=["Incidencias"])
router.include_router(
    calibraciones_router, prefix="/calibraciones", tags=["Calibraciones"]
)
router.include_router(repuestos_router, prefix="/repuestos", tags=["Repuestos"])
router.include_router(usuarios_router, prefix="/usuarios", tags=["Usuarios"])
router.include_router(proveedores_router, prefix="/proveedores", tags=["Proveedores"])
router.include_router(reportes_router, prefix="/reportes", tags=["Reportes"])
