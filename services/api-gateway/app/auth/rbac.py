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
    "/api/v1/proveedores": {"administrador"},
    "/api/v1/repuestos": {"tecnico", "administrador"},
    "/api/v1/incidencias": {"coordinador", "administrador"},
    "/api/v1/problemas": {"coordinador", "administrador"},
    "/api/v1/calibraciones": {"coordinador", "administrador"},
    "/api/v1/equipos": {"administrador"},
}

# Excepciones de escritura por ruta específica (más permisivas que WRITE_RESTRICTED).
# `methods` opcional: si se define, la excepción solo aplica a esos métodos.
WRITE_EXCEPTIONS = [
    {
        "pattern": "/api/v1/incidencias/",
        "suffix": "/mantenimiento",
        "roles": {"tecnico", "coordinador", "administrador"},
    },
    # El técnico puede COMPLETAR (PUT) calibraciones de sus incidencias asignadas,
    # pero NO crear (POST) — eso queda para coordinador/admin.
    {
        "pattern": "/api/v1/calibraciones/",
        "suffix": "",
        "methods": {"PUT"},
        "roles": {"tecnico", "coordinador", "administrador"},
    },
]


READ_RESTRICTED = {
    "/api/v1/reportes": {"administrador", "coordinador"},
}


def check_read_permission(path: str, user_rol: str) -> bool:
    for prefix, allowed_roles in READ_RESTRICTED.items():
        if path.startswith(prefix):
            return user_rol in allowed_roles
    return True


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
    # Check specific route exceptions first
    for exc in WRITE_EXCEPTIONS:
        if not (path.startswith(exc["pattern"]) and path.endswith(exc["suffix"])):
            continue
        # si la excepción restringe métodos, respetarlo
        if "methods" in exc and method not in exc["methods"]:
            continue
        return user_rol in exc["roles"]
    for prefix, allowed_roles in WRITE_RESTRICTED.items():
        if path.startswith(prefix):
            return user_rol in allowed_roles
    return True
