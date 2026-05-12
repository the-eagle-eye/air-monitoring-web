from datetime import datetime
from pydantic import BaseModel


class RepuestoCreate(BaseModel):
    nombre: str
    categoria: str


class RepuestoUpdate(BaseModel):
    nombre: str | None = None
    categoria: str | None = None
    estado: str | None = None


class RepuestoResponse(BaseModel):
    id: int
    nombre: str
    categoria: str
    estado: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ProveedorCreate(BaseModel):
    nombre: str


class ProveedorUpdate(BaseModel):
    nombre: str | None = None
    estado: str | None = None


class ProveedorResponse(BaseModel):
    id: int
    nombre: str
    estado: str
    created_at: datetime

    model_config = {"from_attributes": True}
