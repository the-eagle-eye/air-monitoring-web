"""update fecha_ingreso seed data for annual calibration testing

Revision ID: 003
Revises: 002
Create Date: 2026-03-15

"""
from alembic import op

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "UPDATE equipos SET fecha_ingreso = '2025-03-20' WHERE device_id = 'T101'"
    )
    op.execute(
        "UPDATE equipos SET fecha_ingreso = '2025-06-15' WHERE device_id = 'T102'"
    )
    op.execute(
        "UPDATE equipos SET fecha_ingreso = '2025-03-10' WHERE device_id = 'T103'"
    )


def downgrade() -> None:
    op.execute(
        "UPDATE equipos SET fecha_ingreso = '2023-03-14' WHERE device_id = 'T101'"
    )
    op.execute(
        "UPDATE equipos SET fecha_ingreso = '2022-11-02' WHERE device_id = 'T102'"
    )
    op.execute(
        "UPDATE equipos SET fecha_ingreso = '2024-01-21' WHERE device_id = 'T103'"
    )
