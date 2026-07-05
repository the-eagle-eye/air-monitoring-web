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
    # origen del incidente: manual | monitor_salud
    # permite el dedup selectivo de la regla de consolidacion (solo mira monitor_salud)
    origen: Mapped[str] = mapped_column(
        String, nullable=False, default="manual"
    )
    # --- ITIL v4 (docs/spec-itil-v4-incidencias.md) ---
    # categoria: sensor | transmision | calibracion | energia | otro
    categoria: Mapped[str] = mapped_column(
        String, nullable=False, default="otro", server_default="otro"
    )
    # impacto (criticidad del equipo) y urgencia (severidad); prioridad se DERIVA
    impacto: Mapped[str] = mapped_column(
        String, nullable=False, default="media", server_default="media"
    )
    urgencia: Mapped[str] = mapped_column(
        String, nullable=False, default="media", server_default="media"
    )
    # causa raiz (Gestion de Problemas): FK opcional a problemas
    problema_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("problemas.id"), nullable=True
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
    # timestamps SLA (ITIL): sellados al transicionar de estado
    fecha_asignacion: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    fecha_resolucion: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    fecha_cierre: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    responsable = relationship("Usuario")
    mantenimiento_correctivo = relationship(
        "MantenimientoCorrectivo", back_populates="incidencia", uselist=False
    )
    calibracion = relationship(
        "Calibracion", back_populates="incidencia", uselist=False
    )
    problema = relationship("Problema", back_populates="incidencias")
