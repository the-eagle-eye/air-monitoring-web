"""add ITIL fields to incidencias (categoria/impacto/urgencia/SLA/problema_id)

Revision ID: ops_007
Revises: ops_006
Create Date: 2026-07-05

Campos ITIL v4 (docs/spec-itil-v4-incidencias.md). Backfill IT-07: las
incidencias existentes conservan su prioridad; se les asigna impacto=media,
urgencia derivada de la prioridad actual, categoria=otro.
"""
from alembic import op
import sqlalchemy as sa

revision = "ops_007"
down_revision = "ops_006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("incidencias", sa.Column("categoria", sa.String(),
                  nullable=False, server_default="otro"))
    op.add_column("incidencias", sa.Column("impacto", sa.String(),
                  nullable=False, server_default="media"))
    op.add_column("incidencias", sa.Column("urgencia", sa.String(),
                  nullable=False, server_default="media"))
    op.add_column("incidencias", sa.Column("problema_id", sa.Integer(),
                  nullable=True))
    op.add_column("incidencias", sa.Column("fecha_asignacion",
                  sa.DateTime(timezone=True), nullable=True))
    op.add_column("incidencias", sa.Column("fecha_resolucion",
                  sa.DateTime(timezone=True), nullable=True))
    op.add_column("incidencias", sa.Column("fecha_cierre",
                  sa.DateTime(timezone=True), nullable=True))
    op.create_foreign_key(
        "fk_incidencias_problema", "incidencias", "problemas",
        ["problema_id"], ["id"],
    )
    # Backfill IT-07: urgencia derivada de la prioridad actual (la prioridad se
    # mantiene tal cual; a partir de ahora se deriva de impacto×urgencia).
    op.execute("UPDATE incidencias SET urgencia = prioridad WHERE urgencia = 'media'"
               " AND prioridad IN ('alta', 'baja')")


def downgrade() -> None:
    op.drop_constraint("fk_incidencias_problema", "incidencias",
                       type_="foreignkey")
    for col in ("fecha_cierre", "fecha_resolucion", "fecha_asignacion",
                "problema_id", "urgencia", "impacto", "categoria"):
        op.drop_column("incidencias", col)
