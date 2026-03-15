import httpx
from fastapi import APIRouter, Request, Response

from app.config import settings

router = APIRouter()

SERVICE_MAP = {
    "/api/v1/iot": settings.IOT_SERVICE_URL,
    "/api/v1/predictions": settings.ML_SERVICE_URL,
    "/api/v1/alerts": settings.ML_SERVICE_URL,
    "/api/v1/equipos": settings.OPS_SERVICE_URL,
    "/api/v1/incidencias": settings.OPS_SERVICE_URL,
    "/api/v1/calibraciones": settings.OPS_SERVICE_URL,
    "/api/v1/dashboard": settings.OPS_SERVICE_URL,
}


def _resolve_upstream(path: str) -> str | None:
    for prefix, url in SERVICE_MAP.items():
        if path.startswith(prefix):
            return url
    return None


@router.api_route(
    "/api/v1/{path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
)
async def proxy(request: Request, path: str):
    full_path = f"/api/v1/{path}"
    upstream = _resolve_upstream(full_path)
    if upstream is None:
        return Response(
            content='{"detail": "Service not found"}',
            status_code=404,
            media_type="application/json",
        )

    target_url = f"{upstream}{full_path}"
    if request.url.query:
        target_url += f"?{request.url.query}"

    body = await request.body()
    headers = dict(request.headers)
    headers.pop("host", None)

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.request(
            method=request.method,
            url=target_url,
            content=body,
            headers=headers,
        )

    return Response(
        content=resp.content,
        status_code=resp.status_code,
        media_type=resp.headers.get("content-type", "application/json"),
    )
