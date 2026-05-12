from datetime import datetime, timezone, timedelta

PERU_TZ = timezone(timedelta(hours=-5))

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.equipo import Equipo
from app.models.lectura_iot import LecturaIoT
from app.schemas.lectura_iot import LecturaIoTCreate


def validate_and_store_reading(db: Session, payload: LecturaIoTCreate) -> LecturaIoT:
    equipo = db.query(Equipo).filter(Equipo.device_id == payload.equipo).first()
    if not equipo:
        raise HTTPException(
            status_code=404,
            detail=f"Equipo '{payload.equipo}' no encontrado",
        )

    timestamp_lectura = datetime.strptime(
        payload.timestamp, "%Y-%m-%d %H:%M:%S"
    ).replace(tzinfo=PERU_TZ).astimezone(timezone.utc)

    lectura = LecturaIoT(
        device_id=equipo.id,
        timestamp_lectura=timestamp_lectura,
        so2_ppb=payload.SO2_ppb,
        h2s_ppb=payload.H2S_ppb,
        reaction_temp=payload.Reaction_Temp,
        izs_temp=payload.IZS_Temp,
        pmt_temp=payload.PMT_Temp,
        sample_flow=payload.SampleFlow,
        pressure=payload.Pressure,
        uv_lamp_intensity=payload.UVLampIntensity,
        box_temp=payload.Box_Temp,
        hvps_v=payload.HVPS_V,
        conv_temp=payload.Conv_Temp,
        ozone_flow=payload.Ozone_flow,
        raw_payload=payload.model_dump(),
    )

    db.add(lectura)
    db.commit()
    db.refresh(lectura)

    return lectura
