import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import router as v1_router
from app.config import settings
from app.ml.model_interface import model_manager
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
def load_models():
    artifacts_path = settings.ML_ARTIFACTS_PATH
    if os.path.exists(os.path.join(artifacts_path, "rul_model.pkl")):
        model_manager.load(artifacts_path)
        print(f"ML models loaded (version: {model_manager.model_version})")
    else:
        print(f"WARNING: No model artifacts found at {artifacts_path}")
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
        "models_loaded": model_manager.is_loaded,
    }
