from datetime import date, datetime
from pydantic import BaseModel


class EquipoBase(BaseModel):
    device_id: str
    nombre: str | None = None
    tipo: str | None = None
    ubicacion: str | None = None
    estado: str = "activo"
    serie: str | None = None
    codigo_interno: str | None = None
    modelo: str | None = None
    marca: str | None = None
    fecha_ingreso: date | None = None
    rango_medicion: str | None = None
    parametro_medicion: str | None = None
    foto_equipo: str | None = None
    datalogger_id: int | None = None
    criticidad: str = "media"  # ITIL v4: impacto (alta|media|baja)


class EquipoCreate(EquipoBase):
    pass


class EquipoUpdate(BaseModel):
    nombre: str | None = None
    tipo: str | None = None
    ubicacion: str | None = None
    estado: str | None = None
    serie: str | None = None
    codigo_interno: str | None = None
    modelo: str | None = None
    marca: str | None = None
    fecha_ingreso: date | None = None
    rango_medicion: str | None = None
    parametro_medicion: str | None = None
    foto_equipo: str | None = None
    datalogger_id: int | None = None
    criticidad: str | None = None


class EquipoResponse(EquipoBase):
    id: int
    fecha_registro: datetime
    fecha_actualizacion: datetime | None = None

    model_config = {"from_attributes": True}
