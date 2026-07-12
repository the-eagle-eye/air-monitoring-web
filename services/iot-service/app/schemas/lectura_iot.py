from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class LecturaIoTCreate(BaseModel):
    """Flexible IoT payload — accepts sensor keys beyond `equipo`/`timestamp`."""

    model_config = ConfigDict(extra="allow")

    equipo: str = Field(..., description="Device ID, e.g. 'T101'")
    timestamp: str = Field(
        ..., description="Timestamp in 'YYYY-MM-DD HH:MM:SS' format"
    )

    @model_validator(mode="after")
    def _cache_sensors(self) -> "LecturaIoTCreate":
        object.__setattr__(self, "_sensors_cache", self._extract_sensors())
        return self

    def _extract_sensors(self) -> dict[str, Any]:
        skip = {"equipo", "timestamp"}
        return {
            k: v for k, v in (self.model_extra or {}).items()
            if k not in skip
        }

    @property
    def sensors(self) -> dict[str, Any]:
        return getattr(self, "_sensors_cache", self._extract_sensors())


class LecturaIoTResponse(BaseModel):
    id: int
    device_id: int
    equipo_device_id: str = Field(..., alias="equipo_device_id")
    timestamp_lectura: datetime
    sensors: dict[str, Any] = Field(default_factory=dict)
    procesado: bool
    created_at: datetime

    model_config = {"from_attributes": True, "populate_by_name": True}


class LecturaIoTDetail(LecturaIoTResponse):
    raw_payload: dict | None = None


class LecturaIoTListResponse(BaseModel):
    items: list[LecturaIoTResponse]
    total: int
    page: int
    page_size: int
