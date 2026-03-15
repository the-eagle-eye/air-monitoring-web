from datetime import datetime
from pydantic import BaseModel


class UsuarioCreate(BaseModel):
    email: str
    nombre: str
    apellido: str
    rol: str


class UsuarioResponse(BaseModel):
    id: int
    email: str
    nombre: str
    apellido: str
    rol: str
    estado: str
    created_at: datetime

    model_config = {"from_attributes": True}
