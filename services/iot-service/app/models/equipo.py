from datetime import date, datetime, timezone

from sqlalchemy import Date, String, Integer, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.models.base import Base


class Equipo(Base):
    __tablename__ = "equipos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    device_id: Mapped[str] = mapped_column(
        String, unique=True, nullable=False, index=True
    )
    nombre: Mapped[str | None] = mapped_column(String, nullable=True)
    tipo: Mapped[str | None] = mapped_column(String, nullable=True)
    ubicacion: Mapped[str | None] = mapped_column(String, nullable=True)
    estado: Mapped[str] = mapped_column(String, nullable=False, default="activo")
    fecha_registro: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    fecha_actualizacion: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Campos expandidos Sprint 3
    serie: Mapped[str | None] = mapped_column(String, nullable=True)
    codigo_interno: Mapped[str | None] = mapped_column(String, nullable=True)
    modelo: Mapped[str | None] = mapped_column(String, nullable=True)
    marca: Mapped[str | None] = mapped_column(String, nullable=True)
    fecha_ingreso: Mapped[date | None] = mapped_column(Date, nullable=True)
    rango_medicion: Mapped[str | None] = mapped_column(String, nullable=True)
    parametro_medicion: Mapped[str | None] = mapped_column(String, nullable=True)
    foto_equipo: Mapped[str | None] = mapped_column(String, nullable=True)
    datalogger_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # ITIL v4: criticidad del equipo = IMPACTO para la matriz impacto×urgencia.
    # alta = estación crítica (p.ej. zona poblada), baja = secundaria. Default media.
    criticidad: Mapped[str] = mapped_column(
        String, nullable=False, default="media", server_default="media"
    )

    lecturas = relationship("LecturaIoT", back_populates="equipo")
