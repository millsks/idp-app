"""drop users email uniqueness

Revision ID: d51e9c7b4a22
Revises: c42def8015a3
Create Date: 2026-05-24 19:15:00.000000+00:00

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d51e9c7b4a22"
down_revision: str | Sequence[str] | None = "c42def8015a3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema: allow same email across separate OAuth provider accounts."""
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=False)


def downgrade() -> None:
    """Downgrade schema: restore unique email index."""
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)
