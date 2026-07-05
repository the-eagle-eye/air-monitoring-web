from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from shared.models.base import Base


class ModelMetric(Base):
    """C6 — Métrica de monitoreo del modelo por estación y ventana.

    Persiste la salud operativa del ensemble en el tiempo (docs/plan-c1-c6-c4-c5.md
    fase C6). Es el prerequisito para el reentrenamiento por degradación (C5):
    permite detectar cuándo la tasa de alerta se dispara o θ se aleja de su base.
    Se agrega desde `health_readings` por ventana (p.ej. 24h)."""

    __tablename__ = "model_metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    station_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    window_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    window_end: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    total_readings: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    anomaly_readings: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # tasa de alerta = anomaly_readings / total_readings (0 si no hay lecturas)
    alert_rate: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    # θ vigente de la estación al momento del cálculo (para detectar drift)
    theta: Mapped[float | None] = mapped_column(Float, nullable=True)
    model_version: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
