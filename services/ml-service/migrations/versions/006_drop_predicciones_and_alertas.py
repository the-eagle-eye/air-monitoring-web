"""drop predicciones and alertas tables (C2 — retiro físico del Random Forest)

Revision ID: ml_006
Revises: ml_005
Create Date: 2026-07-05

El modelo Random Forest (predicciones RUL/prob_falla y alertas nivel_riesgo) fue
retirado por completo del producto; lo reemplazó el monitor de salud no supervisado
(ensemble AE+IF → health_readings / health_device_state / incidencias del monitor).

No se elimina la migración ml_001 (es la raíz de la cadena alembic: ml_002…ml_005
descienden de ella); en su lugar esta revisión suelta físicamente las tablas huérfanas.
El downgrade las recrea con el mismo esquema que definía ml_001.

Ver docs/spec-racionalizacion-dashboard-e-incidencias.md (Decisión C1).
"""
from alembic import op
import sqlalchemy as sa

revision = "ml_006"
down_revision = "ml_005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_index("ix_alertas_device_id_created_at", table_name="alertas")
    op.drop_table("alertas")
    op.drop_index(
        "ix_predicciones_device_id_timestamp", table_name="predicciones"
    )
    op.drop_table("predicciones")


def downgrade() -> None:
    op.create_table(
        "predicciones",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("device_id", sa.String(), nullable=False),
        sa.Column("model_version", sa.String(), nullable=False),
        sa.Column(
            "prediction_timestamp", sa.DateTime(timezone=True), nullable=False
        ),
        sa.Column("failure_probability", sa.Numeric(), nullable=False),
        sa.Column("remaining_useful_life_days", sa.Integer(), nullable=False),
        sa.Column("risk_level", sa.String(), nullable=False),
        sa.Column("feature_snapshot", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_predicciones_device_id_timestamp",
        "predicciones",
        ["device_id", "prediction_timestamp"],
    )
    op.create_table(
        "alertas",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("device_id", sa.String(), nullable=False),
        sa.Column("prediccion_id", sa.Integer(), nullable=False),
        sa.Column("nivel_riesgo", sa.String(), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=True),
        sa.Column(
            "estado", sa.String(), nullable=False, server_default="activa"
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["prediccion_id"], ["predicciones.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_alertas_device_id_created_at",
        "alertas",
        ["device_id", "created_at"],
    )
