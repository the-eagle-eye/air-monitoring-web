"""expand equipos table with additional fields

Revision ID: 002
Revises: 001
Create Date: 2026-03-15

"""
from alembic import op
import sqlalchemy as sa

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("equipos", sa.Column("serie", sa.String(), nullable=True))
    op.add_column("equipos", sa.Column("codigo_interno", sa.String(), nullable=True))
    op.add_column("equipos", sa.Column("modelo", sa.String(), nullable=True))
    op.add_column("equipos", sa.Column("marca", sa.String(), nullable=True))
    op.add_column("equipos", sa.Column("fecha_ingreso", sa.Date(), nullable=True))
    op.add_column("equipos", sa.Column("rango_medicion", sa.String(), nullable=True))
    op.add_column(
        "equipos", sa.Column("parametro_medicion", sa.String(), nullable=True)
    )
    op.add_column("equipos", sa.Column("foto_equipo", sa.String(), nullable=True))
    op.add_column(
        "equipos", sa.Column("datalogger_id", sa.Integer(), nullable=True)
    )

    # Seed expanded data for existing equipos
    op.execute(
        """
        UPDATE equipos SET
            serie = 'SN-T101-88421',
            codigo_interno = 'EQ7K2M8A5Q',
            modelo = 'T101',
            marca = 'Teledyne API',
            fecha_ingreso = '2023-03-14',
            rango_medicion = '0 - 500 ppb',
            parametro_medicion = 'SO2'
        WHERE device_id = 'T101'
        """
    )
    op.execute(
        """
        UPDATE equipos SET
            serie = 'SN-T102-77154',
            codigo_interno = 'EQ4P9L2T6Z',
            modelo = 'T102',
            marca = 'Teledyne API',
            fecha_ingreso = '2022-11-02',
            rango_medicion = '0 - 1000 ppb',
            parametro_medicion = 'NO / NO2 / NOx'
        WHERE device_id = 'T102'
        """
    )
    op.execute(
        """
        UPDATE equipos SET
            serie = 'SN-T103-66390',
            codigo_interno = 'EQ8C1R5Y3N',
            modelo = 'T103',
            marca = 'Teledyne API',
            fecha_ingreso = '2024-01-21',
            rango_medicion = '0 - 20 ppm',
            parametro_medicion = 'CO'
        WHERE device_id = 'T103'
        """
    )


def downgrade() -> None:
    op.drop_column("equipos", "datalogger_id")
    op.drop_column("equipos", "foto_equipo")
    op.drop_column("equipos", "parametro_medicion")
    op.drop_column("equipos", "rango_medicion")
    op.drop_column("equipos", "fecha_ingreso")
    op.drop_column("equipos", "marca")
    op.drop_column("equipos", "modelo")
    op.drop_column("equipos", "codigo_interno")
    op.drop_column("equipos", "serie")
