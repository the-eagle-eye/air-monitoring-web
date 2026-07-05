"""add criticidad to equipos (ITIL v4 impacto)

Revision ID: 005
Revises: 004
Create Date: 2026-07-05

Criticidad del equipo = IMPACTO para la matriz impacto×urgencia de ITIL v4
(docs/spec-itil-v4-incidencias.md §2). alta|media|baja, default media.
"""
from alembic import op
import sqlalchemy as sa

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "equipos",
        sa.Column("criticidad", sa.String(), nullable=False,
                  server_default="media"),
    )


def downgrade() -> None:
    op.drop_column("equipos", "criticidad")
