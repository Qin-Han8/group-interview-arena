"""Establish database baseline.

Revision ID: 7c6ccd86b3c5
Revises:
Create Date: 2026-08-13 22:31:01.719686

"""

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "7c6ccd86b3c5"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
