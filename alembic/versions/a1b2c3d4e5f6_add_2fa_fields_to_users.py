"""add 2fa fields to users

Revision ID: a1b2c3d4e5f6
Revises: 7b9d1693fa48
Create Date: 2026-05-21 22:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "7b9d1693fa48"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("otp_secret", sa.String(64), nullable=True))
    op.add_column("users", sa.Column("otp_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    op.add_column("users", sa.Column("otp_verified", sa.Boolean(), nullable=False, server_default=sa.text("false")))


def downgrade() -> None:
    op.drop_column("users", "otp_verified")
    op.drop_column("users", "otp_enabled")
    op.drop_column("users", "otp_secret")
