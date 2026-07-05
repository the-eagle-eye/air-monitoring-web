from datetime import datetime, timezone

from sqlalchemy import Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.models.base import Base


class Incidencia(Base):
    __tablename__ = "incidencias"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    device_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    tipo: Mapped[str] = mapped_column(String, nullable=False)
    descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)
    estado: Mapped[str] = mapped_column(
        String, nullable=False, default="pendiente"
    )
    prioridad: Mapped[str] = mapped_column(
        String, nullable=False, default="media"
    )
    # origen del incidente: manual | monitor_salud | prediccion_rul
    # permite el dedup selectivo de la regla de consolidacion (solo mira monitor_salud)
    origen: Mapped[str] = mapped_column(
        String, nullable=False, default="manual"
    )
    responsable_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("usuarios.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    responsable = relationship("Usuario")
    mantenimiento_correctivo = relationship(
        "MantenimientoCorrectivo", back_populates="incidencia", uselist=False
    )
    calibracion = relationship(
        "Calibracion", back_populates="incidencia", uselist=False
    )
