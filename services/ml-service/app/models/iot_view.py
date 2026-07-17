"""Mirrors mínimos de las tablas de iot-service (lecturas_iot, equipos) para que
training_service pueda leer la fuente de datos histórica sin acoplar módulos.

Los servicios comparten el Postgres físico en producción; estos modelos declaran
sólo las columnas que training_service necesita, evitando duplicar la totalidad
del esquema. En SQLite (tests) sirve como definición de tabla; en producción se
mapea a las tablas reales creadas por las migraciones de iot-service.
"""
from datetime import datetime

from sqlalchemy import DateTime, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from shared.models.base import Base


class EquipoView(Base):
    __tablename__ = "equipos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    device_id: Mapped[str] = mapped_column(
        String, unique=True, nullable=False, index=True
    )
    estado: Mapped[str] = mapped_column(String, nullable=False, default="activo")


class LecturaIoTView(Base):
    __tablename__ = "lecturas_iot"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    device_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    timestamp_lectura: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    sensors: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
