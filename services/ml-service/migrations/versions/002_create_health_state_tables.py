"""create health_readings and health_device_state tables (ensemble monitor)

Revision ID: ml_002
Revises: ml_001
Create Date: 2026-07-04

Tablas del monitor de salud no supervisado (SPEC §6.3):
  - health_readings: serie histórica de recon_error + estado por lectura
  - health_device_state: estado vigente por equipo + memoria para hours_since_prev
    online y anti-parpadeo
"""
from alembic import op
import sqlalchemy as sa

revision = "ml_002"
down_revision = "ml_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "health_readings",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("device_id", sa.String(), nullable=False),
        sa.Column("reading_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("recon_error", sa.Float(), nullable=True),
        sa.Column("theta", sa.Float(), nullable=True),
        sa.Column("if_anomaly", sa.Boolean(), nullable=True),
        sa.Column("and_alert", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("severity", sa.String(), nullable=True),
        sa.Column("health_state", sa.String(), nullable=False),
        sa.Column("hours_since_prev", sa.Float(), nullable=True),
        sa.Column("model_version", sa.String(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_health_readings_device_id_timestamp",
        "health_readings",
        ["device_id", "reading_timestamp"],
    )
    op.create_index(
        "ix_health_readings_health_state", "health_readings", ["health_state"]
    )

    op.create_table(
        "health_device_state",
        sa.Column("device_id", sa.String(), nullable=False),
        sa.Column("health_state", sa.String(), nullable=False),
        sa.Column("last_recon_error", sa.Float(), nullable=True),
        sa.Column("theta", sa.Float(), nullable=True),
        sa.Column("hours_since_prev", sa.Float(), nullable=True),
        sa.Column("last_fail_end_ts", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_valido", sa.Integer(), nullable=True),
        sa.Column("candidate_state", sa.String(), nullable=True),
        sa.Column("candidate_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("device_id"),
    )


def downgrade() -> None:
    op.drop_table("health_device_state")
    op.drop_index("ix_health_readings_health_state", table_name="health_readings")
    op.drop_index(
        "ix_health_readings_device_id_timestamp", table_name="health_readings"
    )
    op.drop_table("health_readings")
