from datetime import datetime
from pydantic import BaseModel


class PrediccionRunRequest(BaseModel):
    device_id: str | None = None


class PrediccionResponse(BaseModel):
    id: int
    device_id: str
    model_version: str
    prediction_timestamp: datetime
    failure_probability: float
    remaining_useful_life_days: int
    risk_level: str
    created_at: datetime

    model_config = {"from_attributes": True}


class PrediccionDetail(PrediccionResponse):
    feature_snapshot: dict | None = None


class PrediccionListResponse(BaseModel):
    items: list[PrediccionResponse]
    total: int
    page: int
    page_size: int
