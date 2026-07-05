from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import router as v1_router
from app.config import settings
from app.scheduler import shutdown_scheduler, start_scheduler

app = FastAPI(
    title="Air Monitoring - ML Service",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(v1_router)


@app.on_event("startup")
def on_startup():
    # El modelo Random Forest fue retirado; el servicio sólo expone el monitor
    # de salud no supervisado (ensemble AE+IF), que carga sus artefactos on-demand.
    # watchdog de transmisión (docs/spec-transmision-y-reentrenamiento.md §1)
    start_scheduler()


@app.on_event("shutdown")
def stop_scheduler():
    shutdown_scheduler()


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": settings.SERVICE_NAME,
    }
