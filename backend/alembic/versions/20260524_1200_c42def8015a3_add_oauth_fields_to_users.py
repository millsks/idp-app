"""add oauth fields to users

Revision ID: c42def8015a3
Revises: a21bac96042f
Create Date: 2026-05-24 12:00:00.000000+00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c42def8015a3"
down_revision: str | Sequence[str] | None = "a21bac96042f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema: add OAuth columns + composite unique index to users table."""
    op.add_column("users", sa.Column("oauth_provider", sa.String(length=50), nullable=True))
    op.add_column("users", sa.Column("oauth_provider_id", sa.String(length=255), nullable=True))
    op.add_column("users", sa.Column("avatar_url", sa.String(length=500), nullable=True))
    op.create_index(
        "ix_users_oauth_provider_id",
        "users",
        ["oauth_provider", "oauth_provider_id"],
        unique=True,
    )


def downgrade() -> None:
    """Downgrade schema: remove OAuth columns and index from users table."""
    op.drop_index("ix_users_oauth_provider_id", table_name="users")
    op.drop_column("users", "avatar_url")
    op.drop_column("users", "oauth_provider_id")
    op.drop_column("users", "oauth_provider")
