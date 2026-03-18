import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routes.auth import router as auth_router
from app.routes.dashboard import router as dashboard_router
from app.routes.proxy import router as proxy_router

app = FastAPI(
    title="Air Monitoring - API Gateway",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Auth routes (login, refresh, logout, me) — before proxy catch-all
app.include_router(auth_router)
app.include_router(dashboard_router)
app.include_router(proxy_router)


@app.get("/health")
async def health():
    services_status = {}
    for name, url in [
        ("iot-service", settings.IOT_SERVICE_URL),
        ("ml-service", settings.ML_SERVICE_URL),
        ("ops-service", settings.OPS_SERVICE_URL),
    ]:
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.get(f"{url}/health")
                services_status[name] = resp.json().get("status", "unknown")
        except Exception:
            services_status[name] = "unavailable"

    return {
        "status": "ok",
        "service": settings.SERVICE_NAME,
        "services": services_status,
    }
