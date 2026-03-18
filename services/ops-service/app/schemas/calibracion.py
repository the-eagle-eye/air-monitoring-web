from datetime import datetime
from pydantic import BaseModel


class CalibracionCreate(BaseModel):
    device_id: str
    incidencia_id: int | None = None
    fecha_calibracion: datetime | None = None
    nota: str | None = None
    certificado_url: str | None = None
    proveedor_id: int | None = None


class CalibracionUpdate(BaseModel):
    fecha_calibracion: datetime | None = None
    nota: str | None = None
    certificado_url: str | None = None
    proveedor_id: int | None = None


class CalibracionResponse(BaseModel):
    id: int
    incidencia_id: int | None = None
    device_id: str
    fecha_calibracion: datetime | None = None
    nota: str | None = None
    certificado_url: str | None = None
    proveedor_id: int | None = None
    estado: str
    incidencia_estado: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class CalibracionListResponse(BaseModel):
    items: list[CalibracionResponse]
    total: int
    page: int
    page_size: int
