from datetime import datetime
from pydantic import BaseModel, Field


class UsuarioCreate(BaseModel):
    email: str
    nombre: str
    apellido: str
    rol: str
    password: str = Field(min_length=6)


class UsuarioResponse(BaseModel):
    id: int
    email: str
    nombre: str
    apellido: str
    rol: str
    estado: str
    created_at: datetime

    model_config = {"from_attributes": True}


class UsuarioUpdate(BaseModel):
    nombre: str | None = None
    apellido: str | None = None
    rol: str | None = None
    estado: str | None = None
    password: str | None = Field(None, min_length=6)


class UsuarioWithHash(UsuarioResponse):
    password_hash: str | None = None
