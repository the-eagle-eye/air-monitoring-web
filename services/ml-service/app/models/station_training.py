from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from shared.models.base import Base


VALID_STATES: tuple[str, ...] = (
    "nueva",
    "recolectando",
    "entrenando",
    "entrenado",
    "error",
)

# Estaciones ya operativas con artefactos ensemble en ml_artifacts_ensemble_v1/.
# La migración ml_007 las inserta como 'entrenado' para que el trigger de warm-up
# no vuelva a dispararles training (CA-15 del spec). Cualquier estación nueva
# entra vía POST /iot/readings → C8 (catálogo) → _maybe_trigger_training.
SEEDED_STATIONS: tuple[str, ...] = (
    "CA-CC-01",
    "CA-CH-04",
    "CA-CH-05",
    "CA-ILO-01",
    "CA-UCHU-01",
)


class StationTrainingState(Base):
    """Máquina de estados del auto-training por warm-up (C11).

    Ver docs/spec-auto-training-onboarding.md §4.1. Ciclo:
        nueva → recolectando → entrenando → entrenado
                          ↓            ↓
                          └────→ error ─┘
    """

    __tablename__ = "station_training_state"

    device_id: Mapped[str] = mapped_column(String, primary_key=True)
    state: Mapped[str] = mapped_column(
        String, nullable=False, default="nueva", index=True
    )
    readings_valid_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    training_started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    training_completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    model_version: Mapped[str | None] = mapped_column(String, nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
