"""make calibraciones.incidencia_id nullable

Revision ID: ops_003
Revises: ops_002
Create Date: 2026-03-17

"""
from alembic import op
import sqlalchemy as sa

revision = "ops_003"
down_revision = "ops_002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "calibraciones",
        "incidencia_id",
        existing_type=sa.Integer(),
        nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "calibraciones",
        "incidencia_id",
        existing_type=sa.Integer(),
        nullable=False,
    )
