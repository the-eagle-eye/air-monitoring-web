"""create model_metrics table (C6 — métricas de monitoreo del modelo)

Revision ID: ml_005
Revises: ml_004
Create Date: 2026-07-04

Persiste la salud operativa del ensemble por estación y ventana (tasa de alerta,
θ vigente). Prerequisito del reentrenamiento por degradación (C5).
"""
from alembic import op
import sqlalchemy as sa

revision = "ml_005"
down_revision = "ml_004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "model_metrics",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("station_id", sa.String(), nullable=False),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("window_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("total_readings", sa.Integer(), nullable=False,
                  server_default="0"),
        sa.Column("anomaly_readings", sa.Integer(), nullable=False,
                  server_default="0"),
        sa.Column("alert_rate", sa.Float(), nullable=False, server_default="0"),
        sa.Column("theta", sa.Float(), nullable=True),
        sa.Column("model_version", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_model_metrics_station_id", "model_metrics",
                    ["station_id"])
    op.create_index("ix_model_metrics_window_start", "model_metrics",
                    ["window_start"])


def downgrade() -> None:
    op.drop_index("ix_model_metrics_window_start", table_name="model_metrics")
    op.drop_index("ix_model_metrics_station_id", table_name="model_metrics")
    op.drop_table("model_metrics")
