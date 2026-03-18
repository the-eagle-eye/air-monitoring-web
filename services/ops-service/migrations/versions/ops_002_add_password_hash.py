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
        '$2b$12$X1ieno/YuY/0U.VY7ULcTu2v5NBRQO9RrC5prBmaJ1pGeiGYE4AbO'
        WHERE email = 'admin@oefa.gob.pe'"""
    )
    # tecnico123
    op.execute(
        """UPDATE usuarios SET password_hash =
        '$2b$12$uKau3IuYPf40xYk51oEKDeqzdBbfhn6qzcIWKwHrR5NItvssLNhY.'
        WHERE email = 'tecnico1@oefa.gob.pe'"""
    )
    # coord123
    op.execute(
        """UPDATE usuarios SET password_hash =
        '$2b$12$UC9.5dKsgjVao7X91sZ9seaIVIYBMbArWZVILChhk3C06XTT5l8Ba'
        WHERE email = 'coordinador1@oefa.gob.pe'"""
    )


def downgrade() -> None:
    op.drop_column("usuarios", "password_hash")
