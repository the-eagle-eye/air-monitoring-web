from datetime import datetime, timezone

from sqlalchemy import Integer, Numeric, String, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.models.base import Base


class Prediccion(Base):
    __tablename__ = "predicciones"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    device_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    model_version: Mapped[str] = mapped_column(String, nullable=False)
    prediction_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    failure_probability: Mapped[float] = mapped_column(Numeric, nullable=False)
    remaining_useful_life_days: Mapped[int] = mapped_column(Integer, nullable=False)
    risk_level: Mapped[str] = mapped_column(String, nullable=False)
    feature_snapshot: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    alertas = relationship("Alerta", back_populates="prediccion")
