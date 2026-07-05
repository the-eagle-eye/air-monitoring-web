"""Replace fixed sensor columns with a flexible sensors JSONB column.

Revision ID: 004
Revises: 003
Create Date: 2026-06-13
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None

_OLD_COLUMNS = [
    "so2_ppb", "h2s_ppb", "reaction_temp", "izs_temp", "pmt_temp",
    "sample_flow", "pressure", "uv_lamp_intensity", "box_temp",
    "hvps_v", "conv_temp", "ozone_flow",
]


def upgrade() -> None:
    op.add_column(
        "lecturas_iot",
        sa.Column("sensors", postgresql.JSONB(), nullable=True),
    )

    op.execute("""
        UPDATE lecturas_iot SET sensors = jsonb_strip_nulls(jsonb_build_object(
            'SO2_ppb',          so2_ppb,
            'H2S_ppb',          h2s_ppb,
            'Reaction_Temp',    reaction_temp,
            'IZS_Temp',         izs_temp,
            'PMT_Temp',         pmt_temp,
            'SampleFlow',       sample_flow,
            'Pressure',         pressure,
            'UVLampIntensity',  uv_lamp_intensity,
            'Box_Temp',         box_temp,
            'HVPS_V',           hvps_v,
            'Conv_Temp',        conv_temp,
            'Ozone_flow',       ozone_flow
        ))
    """)

    op.alter_column("lecturas_iot", "sensors", nullable=False,
                    server_default=sa.text("'{}'::jsonb"))

    for col in _OLD_COLUMNS:
        op.drop_column("lecturas_iot", col)


def downgrade() -> None:
    for col in _OLD_COLUMNS:
        op.add_column("lecturas_iot", sa.Column(col, sa.Numeric(), nullable=True))

    op.execute("""
        UPDATE lecturas_iot SET
            so2_ppb           = (sensors->>'SO2_ppb')::numeric,
            h2s_ppb           = (sensors->>'H2S_ppb')::numeric,
            reaction_temp     = (sensors->>'Reaction_Temp')::numeric,
            izs_temp          = (sensors->>'IZS_Temp')::numeric,
            pmt_temp          = (sensors->>'PMT_Temp')::numeric,
            sample_flow       = (sensors->>'SampleFlow')::numeric,
            pressure          = (sensors->>'Pressure')::numeric,
            uv_lamp_intensity = (sensors->>'UVLampIntensity')::numeric,
            box_temp          = (sensors->>'Box_Temp')::numeric,
            hvps_v            = (sensors->>'HVPS_V')::numeric,
            conv_temp         = (sensors->>'Conv_Temp')::numeric,
            ozone_flow        = (sensors->>'Ozone_flow')::numeric
    """)

    op.drop_column("lecturas_iot", "sensors")
