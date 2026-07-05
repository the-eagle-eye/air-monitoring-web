"""add origen field to incidencias

Revision ID: ops_005
Revises: ops_004
Create Date: 2026-07-04

Soporta la regla de consolidacion de alertas del monitor de salud:
el dedup/escalada solo mira incidentes con origen='monitor_salud'.

"""
from alembic import op
import sqlalchemy as sa

revision = "ops_005"
down_revision = "ops_004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "incidencias",
        sa.Column("origen", sa.String(), nullable=False, server_default="manual"),
    )
    # backfill: todo lo existente queda como 'manual'
    op.execute("UPDATE incidencias SET origen = 'manual' WHERE origen IS NULL")


def downgrade() -> None:
    op.drop_column("incidencias", "origen")
