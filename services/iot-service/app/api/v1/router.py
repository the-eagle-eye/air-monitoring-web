from fastapi import APIRouter

from app.api.v1.iot import router as iot_router

router = APIRouter(prefix="/api/v1")
router.include_router(iot_router, prefix="/iot", tags=["IoT"])
