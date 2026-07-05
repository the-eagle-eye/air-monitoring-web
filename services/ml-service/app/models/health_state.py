from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from shared.models.base import Base


class HealthReading(Base):
    """Salida del ensemble por lectura (SPEC §6.3) — serie histórica para el
    gráfico de recon_error y el estado por equipo del dashboard."""

    __tablename__ = "health_readings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    device_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    reading_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    recon_error: Mapped[float | None] = mapped_column(Float, nullable=True)
    theta: Mapped[float | None] = mapped_column(Float, nullable=True)
    if_anomaly: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    and_alert: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    severity: Mapped[str | None] = mapped_column(String, nullable=True)
    health_state: Mapped[str] = mapped_column(String, nullable=False, index=True)
    # estado crudo de la lectura (antes del anti-parpadeo §5.1); la regla de
    # consolidacion cuenta sobre este, no sobre el estado publicado
    raw_state: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    hours_since_prev: Mapped[float | None] = mapped_column(Float, nullable=True)
    model_version: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )


class HealthDeviceState(Base):
    """Estado vigente por device_id (SPEC §6.3): semáforo + memoria para el cálculo
    online de hours_since_prev y la estabilización anti-parpadeo (§4.4, §5.1)."""

    __tablename__ = "health_device_state"

    device_id: Mapped[str] = mapped_column(String, primary_key=True)
    health_state: Mapped[str] = mapped_column(String, nullable=False)
    last_recon_error: Mapped[float | None] = mapped_column(Float, nullable=True)
    theta: Mapped[float | None] = mapped_column(Float, nullable=True)
    hours_since_prev: Mapped[float | None] = mapped_column(Float, nullable=True)
    # memoria para hours_since_prev online (§4.4): instante del fin de la última falla
    last_fail_end_ts: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_valido: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # anti-parpadeo (§5.1): estado candidato y cuántas lecturas consecutivas lleva
    candidate_state: Mapped[str | None] = mapped_column(String, nullable=True)
    candidate_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # canal de transmision (watchdog, docs/spec-transmision-y-reentrenamiento.md §1):
    # OK | SIN_TRANSMISION — separado del canal de salud (§1.2 CT-03)
    transmission_state: Mapped[str] = mapped_column(
        String, nullable=False, default="OK"
    )
    transmission_severity: Mapped[str | None] = mapped_column(
        String, nullable=True
    )
    # instante de la ultima lectura recibida (para el gap del watchdog)
    last_reading_ts: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
