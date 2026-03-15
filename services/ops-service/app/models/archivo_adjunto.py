from datetime import datetime, timezone

from sqlalchemy import Integer, String, DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column

from shared.models.base import Base


class ArchivoAdjunto(Base):
    __tablename__ = "archivos_adjuntos"
    __table_args__ = (
        Index("ix_archivos_entidad", "entidad_tipo", "entidad_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    entidad_tipo: Mapped[str] = mapped_column(String, nullable=False)
    entidad_id: Mapped[int] = mapped_column(Integer, nullable=False)
    filename: Mapped[str] = mapped_column(String, nullable=False)
    file_url: Mapped[str] = mapped_column(String, nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
