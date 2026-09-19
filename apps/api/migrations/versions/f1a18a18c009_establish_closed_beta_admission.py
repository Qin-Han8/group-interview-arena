"""establish closed beta admission

Revision ID: f1a18a18c009
Revises: f1a17b17c008
Create Date: 2026-09-19 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "f1a18a18c009"
down_revision: str | Sequence[str] | None = "f1a17b17c008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "beta_invitations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("code_digest", sa.LargeBinary(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("consumed_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("operator_label", sa.String(length=64), nullable=False),
        sa.CheckConstraint(
            "octet_length(code_digest) = 32",
            name=op.f("ck_beta_invitations_code_digest_sha256"),
        ),
        sa.CheckConstraint(
            "expires_at > created_at",
            name=op.f("ck_beta_invitations_expires_after_creation"),
        ),
        sa.CheckConstraint(
            "(consumed_at IS NULL) = (consumed_by_user_id IS NULL)",
            name=op.f("ck_beta_invitations_consumption_pair_consistent"),
        ),
        sa.CheckConstraint(
            "NOT (consumed_at IS NOT NULL AND revoked_at IS NOT NULL)",
            name=op.f("ck_beta_invitations_single_terminal_state"),
        ),
        sa.CheckConstraint(
            "consumed_at IS NULL OR consumed_at >= created_at",
            name=op.f("ck_beta_invitations_consumed_after_creation"),
        ),
        sa.CheckConstraint(
            "revoked_at IS NULL OR revoked_at >= created_at",
            name=op.f("ck_beta_invitations_revoked_after_creation"),
        ),
        sa.CheckConstraint(
            "length(btrim(operator_label)) BETWEEN 1 AND 64",
            name=op.f("ck_beta_invitations_operator_label_non_empty"),
        ),
        sa.ForeignKeyConstraint(
            ["consumed_by_user_id"],
            ["users.id"],
            name=op.f("fk_beta_invitations_consumed_by_user_id_users"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_beta_invitations")),
        sa.UniqueConstraint(
            "code_digest",
            name=op.f("uq_beta_invitations_code_digest"),
        ),
    )
    op.create_index(
        op.f("ix_beta_invitations_expires_at"),
        "beta_invitations",
        ["expires_at"],
        unique=False,
    )
    op.create_table(
        "auth_rate_limit_buckets",
        sa.Column("scope", sa.String(length=32), nullable=False),
        sa.Column("key_digest", sa.LargeBinary(length=32), nullable=False),
        sa.Column("window_started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("attempt_count", sa.BigInteger(), nullable=False),
        sa.Column("blocked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "scope IN ('REGISTER_GLOBAL', 'REGISTER_SOURCE', "
            "'REGISTER_INVITE', 'LOGIN_GLOBAL', 'LOGIN_SOURCE', "
            "'LOGIN_ACCOUNT_SHARD')",
            name=op.f("ck_auth_rate_limit_buckets_scope_allowed"),
        ),
        sa.CheckConstraint(
            "octet_length(key_digest) = 32",
            name=op.f("ck_auth_rate_limit_buckets_key_digest_hmac_sha256"),
        ),
        sa.CheckConstraint(
            "attempt_count >= 0",
            name=op.f("ck_auth_rate_limit_buckets_attempt_count_non_negative"),
        ),
        sa.CheckConstraint(
            "updated_at >= window_started_at",
            name=op.f("ck_auth_rate_limit_buckets_updated_after_window_start"),
        ),
        sa.CheckConstraint(
            "blocked_until IS NULL OR blocked_until >= window_started_at",
            name=op.f("ck_auth_rate_limit_buckets_blocked_after_window_start"),
        ),
        sa.PrimaryKeyConstraint(
            "scope",
            "key_digest",
            name=op.f("pk_auth_rate_limit_buckets"),
        ),
    )
    op.create_index(
        op.f("ix_auth_rate_limit_buckets_updated_at"),
        "auth_rate_limit_buckets",
        ["updated_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_auth_rate_limit_buckets_updated_at"),
        table_name="auth_rate_limit_buckets",
    )
    op.drop_table("auth_rate_limit_buckets")
    op.drop_index(
        op.f("ix_beta_invitations_expires_at"),
        table_name="beta_invitations",
    )
    op.drop_table("beta_invitations")
