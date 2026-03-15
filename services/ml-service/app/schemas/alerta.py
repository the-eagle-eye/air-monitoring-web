from datetime import datetime
from pydantic import BaseModel


class AlertaResponse(BaseModel):
    id: int
    device_id: str
    prediccion_id: int
    nivel_riesgo: str
    descripcion: str | None = None
    estado: str
    created_at: datetime

    model_config = {"from_attributes": True}


class AlertaListResponse(BaseModel):
    items: list[AlertaResponse]
    total: int
    page: int
    page_size: int
