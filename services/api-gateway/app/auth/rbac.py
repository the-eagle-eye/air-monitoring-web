from fastapi import Depends, HTTPException, status

from app.auth.dependencies import get_current_user


def require_roles(*roles: str):
    async def _check(user: dict = Depends(get_current_user)):
        if user["rol"] not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tiene permisos para esta accion",
            )
        return user
    return _check


# Route-level RBAC rules
PUBLIC_PATHS = {
    "/api/v1/auth/login",
    "/api/v1/auth/refresh",
    "/health",
}

PUBLIC_PREFIXES = [
    "/api/v1/iot/readings",  # IoT devices POST readings without auth
]

WRITE_RESTRICTED = {
    "/api/v1/usuarios": {"administrador"},
    "/api/v1/incidencias": {"tecnico", "administrador"},
    "/api/v1/calibraciones": {"tecnico", "administrador"},
    "/api/v1/equipos": {"tecnico", "administrador"},
}


def is_public_route(path: str, method: str) -> bool:
    if path in PUBLIC_PATHS:
        return True
    if method == "POST":
        for prefix in PUBLIC_PREFIXES:
            if path.startswith(prefix):
                return True
    return False


def check_write_permission(path: str, method: str, user_rol: str) -> bool:
    if method in ("GET", "HEAD", "OPTIONS"):
        return True
    for prefix, allowed_roles in WRITE_RESTRICTED.items():
        if path.startswith(prefix):
            return user_rol in allowed_roles
    return True
