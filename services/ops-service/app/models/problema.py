from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.models.base import Base


class Problema(Base):
    """ITIL v4 — Gestión de Problemas (docs/spec-itil-v4-incidencias.md §5).

    Causa raíz de uno o más incidentes recurrentes (p.ej. una lámpara que falla
    repetidamente). Las incidencias se vinculan vía `incidencias.problema_id`."""

    __tablename__ = "problemas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    device_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    titulo: Mapped[str] = mapped_column(String, nullable=False)
    descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)
    # abierto | investigacion | resuelto | cerrado
    estado: Mapped[str] = mapped_column(
        String, nullable=False, default="abierto"
    )
    causa_raiz: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    incidencias = relationship("Incidencia", back_populates="problema")
