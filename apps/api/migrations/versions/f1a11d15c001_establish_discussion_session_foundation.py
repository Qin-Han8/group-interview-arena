"""establish discussion session foundation

Revision ID: f1a11d15c001
Revises: 4fe43b42641b
Create Date: 2026-08-16 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "f1a11d15c001"
down_revision: str | Sequence[str] | None = "4fe43b42641b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "simulation_sessions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_user_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column(
            "last_sequence",
            sa.BigInteger(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "last_sequence >= 0",
            name=op.f("ck_simulation_sessions_last_sequence_non_negative"),
        ),
        sa.ForeignKeyConstraint(
            ["owner_user_id"],
            ["users.id"],
            name=op.f("fk_simulation_sessions_owner_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_simulation_sessions")),
    )
    op.create_table(
        "session_actions",
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("action_id", sa.Uuid(), nullable=False),
        sa.Column("command_version", sa.SmallInteger(), nullable=False),
        sa.Column("command_type", sa.String(length=64), nullable=False),
        sa.Column("payload_digest", sa.LargeBinary(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "command_version > 0",
            name=op.f("ck_session_actions_command_version_positive"),
        ),
        sa.CheckConstraint(
            "octet_length(payload_digest) = 32",
            name=op.f("ck_session_actions_payload_digest_sha256"),
        ),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["simulation_sessions.id"],
            name=op.f("fk_session_actions_session_id_simulation_sessions"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "session_id",
            "action_id",
            name=op.f("pk_session_actions"),
        ),
    )
    op.create_table(
        "discussion_events",
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("sequence", sa.BigInteger(), nullable=False),
        sa.Column("event_version", sa.SmallInteger(), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("causation_action_id", sa.Uuid(), nullable=True),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "event_version > 0",
            name=op.f("ck_discussion_events_event_version_positive"),
        ),
        sa.CheckConstraint(
            "sequence > 0",
            name=op.f("ck_discussion_events_sequence_positive"),
        ),
        sa.ForeignKeyConstraint(
            ["session_id", "causation_action_id"],
            ["session_actions.session_id", "session_actions.action_id"],
            name=op.f("fk_discussion_events_session_id_session_actions"),
        ),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["simulation_sessions.id"],
            name=op.f("fk_discussion_events_session_id_simulation_sessions"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "session_id",
            "sequence",
            name=op.f("pk_discussion_events"),
        ),
    )
    op.create_index(
        "ix_discussion_events_session_causation_sequence",
        "discussion_events",
        ["session_id", "causation_action_id", "sequence"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        "ix_discussion_events_session_causation_sequence",
        table_name="discussion_events",
    )
    op.drop_table("discussion_events")
    op.drop_table("session_actions")
    op.drop_table("simulation_sessions")
