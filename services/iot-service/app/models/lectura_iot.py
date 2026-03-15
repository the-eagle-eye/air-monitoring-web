from datetime import datetime, timezone

from sqlalchemy import Integer, Numeric, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.models.base import Base


class LecturaIoT(Base):
    __tablename__ = "lecturas_iot"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    device_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("equipos.id"), nullable=False, index=True
    )
    timestamp_lectura: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )

    # 13 sensor fields from CR310 payload
    so2_ppb: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    h2s_ppb: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    reaction_temp: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    izs_temp: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    pmt_temp: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    sample_flow: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    pressure: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    uv_lamp_intensity: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    box_temp: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    hvps_v: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    conv_temp: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    ozone_flow: Mapped[float | None] = mapped_column(Numeric, nullable=True)

    raw_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    procesado: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    equipo = relationship("Equipo", back_populates="lecturas")
