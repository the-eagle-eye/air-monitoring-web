"""add raw_state to health_readings (regla de consolidacion)

Revision ID: ml_003
Revises: ml_002
Create Date: 2026-07-04

La regla de consolidacion de alertas cuenta lecturas anomalas por su estado
crudo (antes del anti-parpadeo §5.1), no por el estado publicado. Se agrega
raw_state para poder contar correctamente en la ventana de 24h.
"""
from alembic import op
import sqlalchemy as sa

revision = "ml_003"
down_revision = "ml_002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "health_readings",
        sa.Column("raw_state", sa.String(), nullable=True),
    )
    op.create_index(
        "ix_health_readings_raw_state", "health_readings", ["raw_state"]
    )
    # backfill: para lecturas historicas, el mejor proxy del estado crudo es el
    # estado publicado (no tenemos el crudo retroactivamente)
    op.execute("UPDATE health_readings SET raw_state = health_state")


def downgrade() -> None:
    op.drop_index("ix_health_readings_raw_state", table_name="health_readings")
    op.drop_column("health_readings", "raw_state")
