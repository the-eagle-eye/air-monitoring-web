from datetime import datetime
from pydantic import BaseModel, Field


class LecturaIoTCreate(BaseModel):
    """Maps the CR310 datalogger JSON payload."""

    equipo: str = Field(..., description="Device ID, e.g. 'T101'")
    SO2_ppb: float
    H2S_ppb: float
    Reaction_Temp: float
    IZS_Temp: float
    PMT_Temp: float
    SampleFlow: float
    Pressure: float
    UVLampIntensity: float
    Box_Temp: float
    HVPS_V: float
    Conv_Temp: float
    Ozone_flow: float
    timestamp: str = Field(
        ..., description="Timestamp in 'YYYY-MM-DD HH:MM:SS' format"
    )


class LecturaIoTResponse(BaseModel):
    id: int
    device_id: int
    equipo_device_id: str = Field(..., alias="equipo_device_id")
    timestamp_lectura: datetime
    so2_ppb: float | None = None
    h2s_ppb: float | None = None
    reaction_temp: float | None = None
    izs_temp: float | None = None
    pmt_temp: float | None = None
    sample_flow: float | None = None
    pressure: float | None = None
    uv_lamp_intensity: float | None = None
    box_temp: float | None = None
    hvps_v: float | None = None
    conv_temp: float | None = None
    ozone_flow: float | None = None
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
