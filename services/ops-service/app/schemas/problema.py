from datetime import datetime
from typing import Literal

from pydantic import BaseModel

EstadoProblema = Literal["abierto", "investigacion", "resuelto", "cerrado"]


class ProblemaCreate(BaseModel):
    titulo: str
    device_id: str | None = None
    descripcion: str | None = None
    causa_raiz: str | None = None


class ProblemaUpdate(BaseModel):
    titulo: str | None = None
    descripcion: str | None = None
    estado: EstadoProblema | None = None
    causa_raiz: str | None = None


class ProblemaResponse(BaseModel):
    id: int
    device_id: str | None = None
    titulo: str
    descripcion: str | None = None
    estado: str
    causa_raiz: str | None = None
    created_at: datetime
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class ProblemaListResponse(BaseModel):
    items: list[ProblemaResponse]
    total: int
