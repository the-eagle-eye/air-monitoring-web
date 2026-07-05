from datetime import datetime, timezone, timedelta

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.equipo import Equipo
from app.models.lectura_iot import LecturaIoT
from app.schemas.lectura_iot import LecturaIoTCreate

PERU_TZ = timezone(timedelta(hours=-5))


def validate_and_store_reading(db: Session, payload: LecturaIoTCreate) -> LecturaIoT:
    equipo = db.query(Equipo).filter(Equipo.device_id == payload.equipo).first()
    if not equipo:
        raise HTTPException(
            status_code=404,
            detail=f"Equipo '{payload.equipo}' no encontrado",
        )

    timestamp_lectura = (
        datetime.strptime(payload.timestamp, "%Y-%m-%d %H:%M:%S")
        .replace(tzinfo=PERU_TZ)
        .astimezone(timezone.utc)
    )

    lectura = LecturaIoT(
        device_id=equipo.id,
        timestamp_lectura=timestamp_lectura,
        sensors=payload.sensors,
        raw_payload=payload.model_dump(),
    )

    db.add(lectura)
    db.commit()
    db.refresh(lectura)

    return lectura
