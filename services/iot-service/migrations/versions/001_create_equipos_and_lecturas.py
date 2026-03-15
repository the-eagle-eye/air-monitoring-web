"""create equipos and lecturas_iot tables

Revision ID: 001
Revises:
Create Date: 2026-03-15

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "equipos",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("device_id", sa.String(), nullable=False),
        sa.Column("nombre", sa.String(), nullable=True),
        sa.Column("tipo", sa.String(), nullable=True),
        sa.Column("ubicacion", sa.String(), nullable=True),
        sa.Column("estado", sa.String(), nullable=False, server_default="activo"),
        sa.Column(
            "fecha_registro",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("fecha_actualizacion", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("device_id"),
    )
    op.create_index("ix_equipos_device_id", "equipos", ["device_id"])

    op.create_table(
        "lecturas_iot",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("device_id", sa.Integer(), nullable=False),
        sa.Column("timestamp_lectura", sa.DateTime(timezone=True), nullable=False),
        sa.Column("so2_ppb", sa.Numeric(), nullable=True),
        sa.Column("h2s_ppb", sa.Numeric(), nullable=True),
        sa.Column("reaction_temp", sa.Numeric(), nullable=True),
        sa.Column("izs_temp", sa.Numeric(), nullable=True),
        sa.Column("pmt_temp", sa.Numeric(), nullable=True),
        sa.Column("sample_flow", sa.Numeric(), nullable=True),
        sa.Column("pressure", sa.Numeric(), nullable=True),
        sa.Column("uv_lamp_intensity", sa.Numeric(), nullable=True),
        sa.Column("box_temp", sa.Numeric(), nullable=True),
        sa.Column("hvps_v", sa.Numeric(), nullable=True),
        sa.Column("conv_temp", sa.Numeric(), nullable=True),
        sa.Column("ozone_flow", sa.Numeric(), nullable=True),
        sa.Column("raw_payload", postgresql.JSONB(), nullable=True),
        sa.Column("procesado", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["device_id"], ["equipos.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_lecturas_iot_device_id", "lecturas_iot", ["device_id"])
    op.create_index(
        "ix_lecturas_iot_timestamp_lectura", "lecturas_iot", ["timestamp_lectura"]
    )

    # Seed: 3 equipos de prueba
    op.execute(
        """
        INSERT INTO equipos (device_id, nombre, tipo, ubicacion, estado)
        VALUES
            ('T101', 'Analizador SO2/H2S #1', 'Thermo 450i', 'Estacion La Oroya', 'activo'),
            ('T102', 'Analizador SO2/H2S #2', 'Thermo 450i', 'Estacion Huanchan', 'activo'),
            ('T103', 'Analizador SO2/H2S #3', 'Thermo 450i', 'Estacion Sindicato', 'activo')
        """
    )


def downgrade() -> None:
    op.drop_table("lecturas_iot")
    op.drop_table("equipos")
