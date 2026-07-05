from datetime import datetime
from typing import Literal
from pydantic import BaseModel

from app.schemas.mantenimiento import MantenimientoResponse


Categoria = Literal["sensor", "transmision", "calibracion", "energia", "otro"]
Nivel = Literal["alta", "media", "baja"]
# ITIL: estado ahora incluye 'resuelto' (sub-estado antes del cierre verificado)
EstadoIncidencia = Literal[
    "pendiente", "en_ejecucion", "resuelto", "finalizado", "cancelado"
]


class IncidenciaCreate(BaseModel):
    device_id: str
    tipo: Literal["correctiva", "calibracion"]
    descripcion: str | None = None
    # prioridad ITIL: si no se envía, se DERIVA de impacto×urgencia (I2.4)
    prioridad: Nivel | None = None
    impacto: Nivel | None = None    # default = criticidad del equipo
    urgencia: Nivel = "media"
    categoria: Categoria = "otro"
    origen: Literal["manual", "monitor_salud", "prediccion_rul"] = "manual"
    responsable_id: int | None = None


class IncidenciaUpdate(BaseModel):
    estado: EstadoIncidencia | None = None
    responsable_id: int | None = None
    descripcion: str | None = None
    categoria: Categoria | None = None
    impacto: Nivel | None = None
    urgencia: Nivel | None = None
    problema_id: int | None = None


class IncidenciaResponse(BaseModel):
    id: int
    device_id: str
    tipo: str
    descripcion: str | None = None
    estado: str
    prioridad: str
    impacto: str = "media"
    urgencia: str = "media"
    categoria: str = "otro"
    origen: str = "manual"
    problema_id: int | None = None
    responsable_id: int | None = None
    created_at: datetime
    updated_at: datetime | None = None
    fecha_asignacion: datetime | None = None
    fecha_resolucion: datetime | None = None
    fecha_cierre: datetime | None = None

    model_config = {"from_attributes": True}


class IncidenciaDetailResponse(IncidenciaResponse):
    mantenimiento_correctivo: MantenimientoResponse | None = None


class IncidenciaListResponse(BaseModel):
    items: list[IncidenciaResponse]
    total: int
    page: int
    page_size: int
