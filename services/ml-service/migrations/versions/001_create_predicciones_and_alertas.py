"""create predicciones and alertas tables

Revision ID: 001
Revises:
Create Date: 2026-03-15

"""
from alembic import op
import sqlalchemy as sa

revision = "ml_001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
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
            "estado",
            sa.String(),
            nullable=False,
            server_default="activa",
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


def downgrade() -> None:
    op.drop_table("alertas")
    op.drop_table("predicciones")
