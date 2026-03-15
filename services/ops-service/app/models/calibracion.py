from datetime import datetime, timezone

from sqlalchemy import Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.models.base import Base


class Calibracion(Base):
    __tablename__ = "calibraciones"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    incidencia_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("incidencias.id"), unique=True, nullable=False
    )
    device_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    fecha_calibracion: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    nota: Mapped[str | None] = mapped_column(Text, nullable=True)
    certificado_url: Mapped[str | None] = mapped_column(String, nullable=True)
    proveedor_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("proveedores_calibracion.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    incidencia = relationship("Incidencia", back_populates="calibracion")
    proveedor = relationship("ProveedorCalibracion")
