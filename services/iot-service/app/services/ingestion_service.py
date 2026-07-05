from datetime import datetime, timezone, timedelta

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.equipo import Equipo
from app.models.lectura_iot import LecturaIoT
from app.schemas.lectura_iot import LecturaIoTCreate
from app.services.ensemble_notify_service import notify_ensemble
from app.services.device_onboarding import (
    is_valid_device_id,
    ESTADO_NO_CONFIRMADO,
)

import logging

logger = logging.getLogger(__name__)

PERU_TZ = timezone(timedelta(hours=-5))


def validate_and_store_reading(db: Session, payload: LecturaIoTCreate) -> LecturaIoT:
    equipo = db.query(Equipo).filter(Equipo.device_id == payload.equipo).first()
    if not equipo:
        # C8: onboarding automático en cuarentena. Si el device_id cumple el formato
        # de estación OEFA, se auto-crea 'no_confirmado' (no operativo hasta que un
        # coordinador lo apruebe). Si NO cumple el formato (typo/basura), se rechaza.
        if not is_valid_device_id(payload.equipo):
            raise HTTPException(
                status_code=404,
                detail=(
                    f"Equipo '{payload.equipo}' no encontrado y su formato no "
                    f"corresponde a una estación válida (esperado T### o CA-XXX-##)"
                ),
            )
        equipo = Equipo(
            device_id=payload.equipo,
            estado=ESTADO_NO_CONFIRMADO,
        )
        db.add(equipo)
        db.commit()
        db.refresh(equipo)
        logger.info(
            "C8: equipo '%s' auto-creado en cuarentena (no_confirmado)",
            payload.equipo,
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

    # C1: notificar al ensemble de salud (fire-and-forget; no rompe la ingesta).
    notify_ensemble(payload.equipo, timestamp_lectura, payload.sensors)

    return lectura
