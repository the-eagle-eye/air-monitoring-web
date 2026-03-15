from datetime import datetime
from pydantic import BaseModel


class RepuestoResponse(BaseModel):
    id: int
    nombre: str
    categoria: str
    estado: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ProveedorResponse(BaseModel):
    id: int
    nombre: str
    estado: str
    created_at: datetime

    model_config = {"from_attributes": True}
