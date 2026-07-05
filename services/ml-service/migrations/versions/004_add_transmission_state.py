"""add transmission channel to health_device_state (watchdog)

Revision ID: ml_004
Revises: ml_003
Create Date: 2026-07-04

Watchdog de perdida de transmision (docs/spec-transmision-y-reentrenamiento.md §1).
Canal operativo separado del canal de salud: OK | SIN_TRANSMISION, con severidad
por duracion del corte (baja/media/alta) y el instante de la ultima lectura.
"""
from alembic import op
import sqlalchemy as sa

revision = "ml_004"
down_revision = "ml_003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "health_device_state",
        sa.Column("transmission_state", sa.String(), nullable=False,
                  server_default="OK"),
    )
    op.add_column(
        "health_device_state",
        sa.Column("transmission_severity", sa.String(), nullable=True),
    )
    op.add_column(
        "health_device_state",
        sa.Column("last_reading_ts", sa.DateTime(timezone=True), nullable=True),
    )
    # backfill: last_reading_ts = updated_at para el estado existente
    op.execute(
        "UPDATE health_device_state SET last_reading_ts = updated_at "
        "WHERE last_reading_ts IS NULL"
    )


def downgrade() -> None:
    op.drop_column("health_device_state", "last_reading_ts")
    op.drop_column("health_device_state", "transmission_severity")
    op.drop_column("health_device_state", "transmission_state")
