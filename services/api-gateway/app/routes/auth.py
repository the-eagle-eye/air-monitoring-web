import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.auth.jwt_handler import (
    create_access_token,
    create_refresh_token,
    verify_token,
)
from app.auth.password import verify_password
from app.auth.dependencies import get_current_user
from app.config import settings

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str | None = None
    token_type: str = "bearer"
    usuario: dict | None = None


class RefreshRequest(BaseModel):
    refresh_token: str


@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest):
    ops_url = f"{settings.OPS_SERVICE_URL}/api/v1/usuarios/by-email/{data.email}"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(ops_url)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Servicio de usuarios no disponible",
        )

    if resp.status_code == 404:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales invalidas",
        )
    if resp.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Error al consultar usuario",
        )

    user_data = resp.json()

    if not user_data.get("password_hash"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario sin password configurado",
        )

    if not verify_password(data.password, user_data["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales invalidas",
        )

    if user_data.get("estado") != "activo":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario inactivo",
        )

    token_data = {
        "sub": user_data["email"],
        "user_id": user_data["id"],
        "rol": user_data["rol"],
    }

    return TokenResponse(
        access_token=create_access_token(token_data),
        refresh_token=create_refresh_token(token_data),
        usuario={
            "id": user_data["id"],
            "email": user_data["email"],
            "nombre": user_data["nombre"],
            "apellido": user_data["apellido"],
            "rol": user_data["rol"],
        },
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(data: RefreshRequest):
    payload = verify_token(data.refresh_token, expected_type="refresh")
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token invalido o expirado",
        )

    token_data = {
        "sub": payload["sub"],
        "user_id": payload["user_id"],
        "rol": payload["rol"],
    }

    return TokenResponse(
        access_token=create_access_token(token_data),
    )


@router.post("/logout")
async def logout():
    return {"detail": "Sesion cerrada"}


@router.get("/me")
async def me(user: dict = Depends(get_current_user)):
    ops_url = f"{settings.OPS_SERVICE_URL}/api/v1/usuarios/by-email/{user['email']}"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(ops_url)
        if resp.status_code == 200:
            user_data = resp.json()
            return {
                "id": user_data["id"],
                "email": user_data["email"],
                "nombre": user_data["nombre"],
                "apellido": user_data["apellido"],
                "rol": user_data["rol"],
                "estado": user_data["estado"],
            }
    except Exception:
        pass

    return user
