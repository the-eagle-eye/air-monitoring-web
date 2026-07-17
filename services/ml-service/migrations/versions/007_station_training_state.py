"""station_training_state — máquina de warm-up C11 (auto-training onboarding)

Revision ID: ml_007
Revises: ml_006
Create Date: 2026-07-16

Ver docs/spec-auto-training-onboarding.md §4.1 (máquina de estados) y §12
(impacto). El seed inicial marca las 5 estaciones vigentes como 'entrenado'
para preservar CA-15 (no regresión).
"""
from alembic import op
import sqlalchemy as sa

from app.models.station_training import SEEDED_STATIONS

revision = "ml_007"
down_revision = "ml_006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "station_training_state",
        sa.Column("device_id", sa.String(), nullable=False),
        sa.Column(
            "state",
            sa.String(),
            nullable=False,
            server_default="nueva",
        ),
        sa.Column(
            "readings_valid_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "training_started_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "training_completed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column("model_version", sa.String(), nullable=True),
        sa.Column(
            "attempts",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("device_id"),
    )
    op.create_index(
        "ix_station_training_state_state",
        "station_training_state",
        ["state"],
    )

    # Seed de las 5 estaciones vigentes como 'entrenado'. Sus artefactos existen
    # en ml_artifacts_ensemble_v1/ desde el POC del ensemble; el trigger de
    # warm-up nunca debe volver a entrenarlas (CA-15).
    bind = op.get_bind()
    for sid in SEEDED_STATIONS:
        bind.execute(
            sa.text(
                "INSERT INTO station_training_state "
                "(device_id, state, readings_valid_count, attempts, updated_at) "
                "VALUES (:sid, 'entrenado', 0, 0, now())"
            ),
            {"sid": sid},
        )


def downgrade() -> None:
    op.drop_index(
        "ix_station_training_state_state",
        table_name="station_training_state",
    )
    op.drop_table("station_training_state")
