"""add password_hash to usuarios

Revision ID: ops_002
Revises: ops_001
Create Date: 2026-03-15

"""
from alembic import op
import sqlalchemy as sa

revision = "ops_002"
down_revision = "ops_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "usuarios",
        sa.Column("password_hash", sa.String(), nullable=True),
    )

    # Seed default passwords (bcrypt hashes)
    # admin123
    op.execute(
        """UPDATE usuarios SET password_hash =
        '$2b$12$LJ3m4ys3Lz0QqV9FKBR8geZPZOkKyNJiPGHXlNqUjKEoG6/.KxMi'
        WHERE email = 'admin@oefa.gob.pe'"""
    )
    # tecnico123
    op.execute(
        """UPDATE usuarios SET password_hash =
        '$2b$12$8K1p/a0dL1LXMIgoEDFrwOf5g4fWzIMaJhKJqFCEElrkfYAjCWmy2'
        WHERE email = 'tecnico1@oefa.gob.pe'"""
    )
    # coord123
    op.execute(
        """UPDATE usuarios SET password_hash =
        '$2b$12$X.Hy5TFqL6tU8gTQuI6dmOaFSTM8K6Z9Dv8.X1eLPYWR9q4L5VUuy'
        WHERE email = 'coordinador1@oefa.gob.pe'"""
    )


def downgrade() -> None:
    op.drop_column("usuarios", "password_hash")
