"""add estado field to calibraciones

Revision ID: ops_004
Revises: ops_003
Create Date: 2026-03-17

"""
from alembic import op
import sqlalchemy as sa

revision = "ops_004"
down_revision = "ops_003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "calibraciones",
        sa.Column("estado", sa.String(), nullable=False, server_default="pendiente"),
    )
    # Set existing calibraciones with all 4 fields as completada
    op.execute(
        """UPDATE calibraciones SET estado = 'completada'
        WHERE fecha_calibracion IS NOT NULL
        AND nota IS NOT NULL
        AND certificado_url IS NOT NULL
        AND proveedor_id IS NOT NULL"""
    )


def downgrade() -> None:
    op.drop_column("calibraciones", "estado")
