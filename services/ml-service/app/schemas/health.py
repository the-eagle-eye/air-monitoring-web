from datetime import datetime

from pydantic import BaseModel


class HealthEvaluateRequest(BaseModel):
    """Entrada al ensemble por lectura (SPEC §6.1)."""

    device_id: str
    timestamp: datetime
    so2_ppb: float | None = None
    so2_flow: float | None = None
    so2_internal_temp: float | None = None
    so2_lamp_int: float | None = None
    valido: int  # 1 = transmisión válida, 0 = sin datos (gate §3.0)


class HealthEvaluateResponse(BaseModel):
    """Salida del ensemble por lectura (SPEC §6.2)."""

    device_id: str
    timestamp: datetime
    recon_error: float | None
    theta: float | None
    if_anomaly: bool | None
    and_alert: bool
    severity: str | None
    health_state: str
    hours_since_prev: float | None
    model_version: str


class HealthReadingPoint(BaseModel):
    """Un punto de la serie histórica (para el gráfico recon_error + θ)."""

    timestamp: datetime
    recon_error: float | None
    theta: float | None
    health_state: str
    and_alert: bool


class HealthReadingsResponse(BaseModel):
    device_id: str
    points: list[HealthReadingPoint]


class HealthDeviceStateResponse(BaseModel):
    """Estado vigente por equipo (para el semáforo del dashboard)."""

    device_id: str
    health_state: str
    last_recon_error: float | None
    theta: float | None
    hours_since_prev: float | None
    transmission_state: str = "OK"
    transmission_severity: str | None = None
    last_reading_ts: datetime | None = None
    updated_at: datetime


class NoTransmissionItem(BaseModel):
    """Equipo sin transmisión (canal del watchdog §1.2)."""

    device_id: str
    transmission_severity: str | None
    last_reading_ts: datetime | None
    updated_at: datetime


class NoTransmissionResponse(BaseModel):
    items: list[NoTransmissionItem]


class WatchdogRunResponse(BaseModel):
    evaluated: int
    marked: list[dict]
    cleared: list[str]
    silenced: list[str]
    ok: int
    ran_at: str


class ModelMetricItem(BaseModel):
    """Una fila de métrica del modelo (C6)."""

    station_id: str
    window_start: datetime
    window_end: datetime
    total_readings: int
    anomaly_readings: int
    alert_rate: float
    theta: float | None = None

    model_config = {"from_attributes": True}


class ModelMetricsResponse(BaseModel):
    items: list[ModelMetricItem]


class MetricsRunResponse(BaseModel):
    computed: int
    stations: list[dict]


class ThetaRecalResponse(BaseModel):
    results: list[dict]


class RetrainCheckResponse(BaseModel):
    results: list[dict]


class AutocloseResponse(BaseModel):
    finalizadas: list[int]
    canceladas: list[int]
    pendientes: list[int]
    ran_at: str
