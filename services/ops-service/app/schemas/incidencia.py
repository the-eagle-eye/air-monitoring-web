from datetime import datetime
from typing import Literal
from pydantic import BaseModel

from app.schemas.mantenimiento import MantenimientoResponse


class IncidenciaCreate(BaseModel):
    device_id: str
    tipo: Literal["correctiva", "calibracion"]
    descripcion: str | None = None
    prioridad: Literal["alta", "media", "baja"] = "media"
    origen: Literal["manual", "monitor_salud", "prediccion_rul"] = "manual"
    responsable_id: int | None = None


class IncidenciaUpdate(BaseModel):
    estado: Literal[
        "pendiente", "en_ejecucion", "finalizado", "cancelado"
    ] | None = None
    responsable_id: int | None = None
    descripcion: str | None = None


class IncidenciaResponse(BaseModel):
    id: int
    device_id: str
    tipo: str
    descripcion: str | None = None
    estado: str
    prioridad: str
    origen: str = "manual"
    responsable_id: int | None = None
    created_at: datetime
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class IncidenciaDetailResponse(IncidenciaResponse):
    mantenimiento_correctivo: MantenimientoResponse | None = None


class IncidenciaListResponse(BaseModel):
    items: list[IncidenciaResponse]
    total: int
    page: int
    page_size: int
