from datetime import datetime, timezone

from sqlalchemy import Integer, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.models.base import Base


class MantenimientoCorrectivo(Base):
    __tablename__ = "mantenimientos_correctivos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    incidencia_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("incidencias.id"), unique=True, nullable=False
    )
    diagnostico: Mapped[str | None] = mapped_column(Text, nullable=True)
    acciones_realizadas: Mapped[str | None] = mapped_column(Text, nullable=True)
    conclusion: Mapped[str | None] = mapped_column(Text, nullable=True)
    fecha_ejecucion: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    incidencia = relationship("Incidencia", back_populates="mantenimiento_correctivo")
    repuestos_usados = relationship(
        "MantenimientoRepuesto", back_populates="mantenimiento"
    )


class MantenimientoRepuesto(Base):
    __tablename__ = "mantenimiento_repuestos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    mantenimiento_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("mantenimientos_correctivos.id"), nullable=False
    )
    repuesto_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("repuestos.id"), nullable=False
    )

    mantenimiento = relationship(
        "MantenimientoCorrectivo", back_populates="repuestos_usados"
    )
    repuesto = relationship("Repuesto")
