from datetime import datetime
from pydantic import BaseModel


class AdjuntoInput(BaseModel):
    filename: str
    file_url: str


class MantenimientoCreate(BaseModel):
    diagnostico: str | None = None
    acciones_realizadas: str | None = None
    conclusion: str | None = None
    fecha_ejecucion: datetime | None = None
    repuesto_ids: list[int] = []
    adjuntos: list[AdjuntoInput] = []


class RepuestoUsado(BaseModel):
    id: int
    nombre: str
    categoria: str

    model_config = {"from_attributes": True}


class AdjuntoResponse(BaseModel):
    id: int
    filename: str
    file_url: str

    model_config = {"from_attributes": True}


class MantenimientoResponse(BaseModel):
    id: int
    incidencia_id: int
    diagnostico: str | None = None
    acciones_realizadas: str | None = None
    conclusion: str | None = None
    fecha_ejecucion: datetime | None = None
    repuestos: list[RepuestoUsado] = []
    adjuntos: list[AdjuntoResponse] = []
    created_at: datetime

    model_config = {"from_attributes": True}
