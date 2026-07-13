import httpx
from fastapi import APIRouter, Request, Response

from app.config import settings
from app.auth.jwt_handler import verify_token
from app.auth.rbac import is_public_route, check_write_permission, check_read_permission
from app.services.ml_adapter import adapt_json_bytes

router = APIRouter()

_JSON_MEDIA_TYPE = "application/json"

# Rutas del backend v3 de detección de anomalías por episodios
# (ml-service-isolation), seleccionable con ML_BACKEND=isolation. El modelo
# Random Forest que servía estas rutas en el ml-service "legacy" fue RETIRADO
# (C2); con ML_BACKEND=legacy (default) el ml-service ya no las expone.
_ML_ROUTE_PREFIXES = ("/api/v1/predictions", "/api/v1/alerts")

# Non-ML routes.
_STATIC_SERVICE_MAP = {
    "/api/v1/iot": settings.IOT_SERVICE_URL,
    "/api/v1/equipos": settings.OPS_SERVICE_URL,
    "/api/v1/incidencias": settings.OPS_SERVICE_URL,
    "/api/v1/problemas": settings.OPS_SERVICE_URL,
    "/api/v1/calibraciones": settings.OPS_SERVICE_URL,
    "/api/v1/dashboard": settings.OPS_SERVICE_URL,
    "/api/v1/usuarios": settings.OPS_SERVICE_URL,
    "/api/v1/repuestos": settings.OPS_SERVICE_URL,
    "/api/v1/proveedores": settings.OPS_SERVICE_URL,
    "/api/v1/reportes": settings.OPS_SERVICE_URL,
    # Monitor de salud no supervisado (ensemble AE+IF+AND). Va directo al
    # ml-service sin la adaptación de respuesta de _ML_ROUTE_PREFIXES.
    "/api/v1/health-monitor": settings.ML_SERVICE_URL,
}


def _ml_upstream() -> str:
    if settings.ML_BACKEND == "isolation":
        return settings.ML_ISOLATION_SERVICE_URL
    return settings.ML_SERVICE_URL


def _resolve_upstream(path: str) -> str | None:
    for prefix in _ML_ROUTE_PREFIXES:
        if path.startswith(prefix):
            return _ml_upstream()
    for prefix, url in _STATIC_SERVICE_MAP.items():
        if path.startswith(prefix):
            return url
    return None


def _should_adapt_ml_response(path: str) -> bool:
    if settings.ML_BACKEND != "isolation":
        return False
    return any(path.startswith(p) for p in _ML_ROUTE_PREFIXES)


def _authenticate(request: Request) -> dict | None:
    auth_header = request.headers.get("authorization", "")
    if not auth_header.startswith("Bearer "):
        return None
    token = auth_header[7:]
    return verify_token(token, expected_type="access")


@router.api_route(
    "/api/v1/{path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
)
async def proxy(request: Request, path: str):
    full_path = f"/api/v1/{path}"

    # Skip routes handled by dedicated routers (auth, dashboard/kpis)
    if full_path.startswith("/api/v1/auth") or full_path == "/api/v1/dashboard/kpis":
        return Response(
            content='{"detail": "Not found"}',
            status_code=404,
            media_type=_JSON_MEDIA_TYPE,
        )

    upstream = _resolve_upstream(full_path)
    if upstream is None:
        return Response(
            content='{"detail": "Service not found"}',
            status_code=404,
            media_type=_JSON_MEDIA_TYPE,
        )

    # Auth check
    user = None
    if not is_public_route(full_path, request.method):
        user = _authenticate(request)
        if user is None:
            return Response(
                content='{"detail": "No autenticado"}',
                status_code=401,
                media_type=_JSON_MEDIA_TYPE,
            )
        # RBAC check for write operations
        if not check_write_permission(full_path, request.method, user["rol"]):
            return Response(
                content='{"detail": "No tiene permisos para esta accion"}',
                status_code=403,
                media_type=_JSON_MEDIA_TYPE,
            )
        # RBAC check for read-restricted routes
        if not check_read_permission(full_path, user["rol"]):
            return Response(
                content='{"detail": "No tiene permisos para esta accion"}',
                status_code=403,
                media_type=_JSON_MEDIA_TYPE,
            )

    target_url = f"{upstream}{full_path}"
    if request.url.query:
        target_url += f"?{request.url.query}"

    body = await request.body()
    headers = dict(request.headers)
    headers.pop("host", None)

    # Forward user info to downstream services
    if user:
        headers["x-user-id"] = str(user.get("user_id", ""))
        headers["x-user-rol"] = user.get("rol", "")
        headers["x-user-email"] = user.get("sub", "")

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.request(
            method=request.method,
            url=target_url,
            content=body,
            headers=headers,
        )

    content = resp.content
    if _should_adapt_ml_response(full_path) and resp.status_code < 400:
        content = adapt_json_bytes(content)

    return Response(
        content=content,
        status_code=resp.status_code,
        media_type=resp.headers.get("content-type", _JSON_MEDIA_TYPE),
    )
