from datetime import datetime
from pydantic import BaseModel


class DataloggerCreate(BaseModel):
    nombre: str
    codigo_interno: str
    numero_serie: str | None = None
    ubicacion: str | None = None
    estado: str = "activo"


class DataloggerUpdate(BaseModel):
    nombre: str | None = None
    numero_serie: str | None = None
    ubicacion: str | None = None
    estado: str | None = None


class DataloggerResponse(BaseModel):
    id: int
    nombre: str
    codigo_interno: str
    numero_serie: str | None = None
    ubicacion: str | None = None
    estado: str
    created_at: datetime
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}
