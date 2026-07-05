"""create problemas table (ITIL v4 gestión de problemas)

Revision ID: ops_006
Revises: ops_005
Create Date: 2026-07-05

Tabla de Problemas (causa raíz de incidentes recurrentes). Se crea ANTES de
agregar la FK incidencias.problema_id (ops_007).
docs/spec-itil-v4-incidencias.md §5.
"""
from alembic import op
import sqlalchemy as sa

revision = "ops_006"
down_revision = "ops_005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "problemas",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("device_id", sa.String(), nullable=True),
        sa.Column("titulo", sa.String(), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=True),
        sa.Column("estado", sa.String(), nullable=False, server_default="abierto"),
        sa.Column("causa_raiz", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_problemas_device_id", "problemas", ["device_id"])


def downgrade() -> None:
    op.drop_index("ix_problemas_device_id", table_name="problemas")
    op.drop_table("problemas")
