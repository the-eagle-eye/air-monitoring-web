from datetime import datetime, timezone

from sqlalchemy import Integer, Boolean, DateTime, ForeignKey, JSON
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

    sensors: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    raw_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    procesado: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    equipo = relationship("Equipo", back_populates="lecturas")
