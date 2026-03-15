from datetime import datetime, timezone

from sqlalchemy import Integer, String, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from shared.models.base import Base


class Datalogger(Base):
    __tablename__ = "dataloggers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String, nullable=False)
    codigo_interno: Mapped[str] = mapped_column(
        String, unique=True, nullable=False
    )
    numero_serie: Mapped[str | None] = mapped_column(String, nullable=True)
    ubicacion: Mapped[str | None] = mapped_column(String, nullable=True)
    estado: Mapped[str] = mapped_column(
        String, nullable=False, default="activo"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
