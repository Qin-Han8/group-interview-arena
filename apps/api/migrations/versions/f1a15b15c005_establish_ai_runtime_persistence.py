"""establish ai runtime persistence foundation

Revision ID: f1a15b15c005
Revises: f1a14b15c004
Create Date: 2026-08-21 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "f1a15b15c005"
down_revision: str | Sequence[str] | None = "f1a14b15c004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "prompt_versions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("prompt_key", sa.String(length=64), nullable=False),
        sa.Column("version_number", sa.SmallInteger(), nullable=False),
        sa.Column("purpose_code", sa.String(length=64), nullable=False),
        sa.Column("template_text", sa.Text(), nullable=False),
        sa.Column("content_digest", sa.LargeBinary(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("retired_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "octet_length(content_digest) = 32",
            name=op.f("ck_prompt_versions_content_digest_sha256"),
        ),
        sa.CheckConstraint(
            "length(prompt_key) > 0",
            name=op.f("ck_prompt_versions_prompt_key_non_empty"),
        ),
        sa.CheckConstraint(
            "length(purpose_code) > 0",
            name=op.f("ck_prompt_versions_purpose_code_non_empty"),
        ),
        sa.CheckConstraint(
            "published_at >= created_at",
            name=op.f("ck_prompt_versions_publication_after_creation"),
        ),
        sa.CheckConstraint(
            "retired_at IS NULL OR retired_at >= published_at",
            name=op.f("ck_prompt_versions_retirement_after_publication"),
        ),
        sa.CheckConstraint(
            "length(template_text) > 0",
            name=op.f("ck_prompt_versions_template_text_non_empty"),
        ),
        sa.CheckConstraint(
            "version_number > 0",
            name=op.f("ck_prompt_versions_version_number_positive"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_prompt_versions")),
        sa.UniqueConstraint(
            "prompt_key", "version_number", name="uq_prompt_versions_key_version"
        ),
    )
    op.create_table(
        "llm_generation_requests",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("participant_id", sa.Uuid(), nullable=False),
        sa.Column("floor_grant_id", sa.Uuid(), nullable=False),
        sa.Column("prompt_version_id", sa.Uuid(), nullable=False),
        sa.Column("provider_identifier", sa.String(length=128), nullable=False),
        sa.Column("model_identifier", sa.String(length=128), nullable=False),
        sa.Column(
            "request_metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("request_digest", sa.LargeBinary(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failure_code", sa.String(length=32), nullable=True),
        sa.CheckConstraint(
            "completed_at IS NULL OR completed_at >= started_at",
            name=op.f("ck_llm_generation_requests_completed_after_started"),
        ),
        sa.CheckConstraint(
            "failed_at IS NULL OR failed_at >= requested_at",
            name=op.f("ck_llm_generation_requests_failed_after_requested"),
        ),
        sa.CheckConstraint(
            "failure_code IS NULL OR failure_code IN "
            "('TIMEOUT', 'PROVIDER_UNAVAILABLE', 'RATE_LIMIT', "
            "'PARTIAL_GENERATION', 'INVALID_OUTPUT', 'INTERNAL_ERROR')",
            name=op.f("ck_llm_generation_requests_failure_code_allowed"),
        ),
        sa.CheckConstraint(
            "length(provider_identifier) > 0 AND length(model_identifier) > 0",
            name=op.f(
                "ck_llm_generation_requests_provider_model_identifiers_non_empty"
            ),
        ),
        sa.CheckConstraint(
            "octet_length(request_digest) = 32",
            name=op.f("ck_llm_generation_requests_request_digest_sha256"),
        ),
        sa.CheckConstraint(
            "jsonb_typeof(request_metadata) = 'object' AND "
            "request_metadata ?& ARRAY['schema_version', 'configuration_version'] "
            "AND request_metadata - ARRAY['schema_version', 'configuration_version'] "
            "= '{}'::jsonb AND "
            "jsonb_typeof(request_metadata->'schema_version') = 'number' AND "
            "request_metadata->>'schema_version' = '1' AND "
            "jsonb_typeof(request_metadata->'configuration_version') = 'string' AND "
            "length(request_metadata->>'configuration_version') > 0",
            name=op.f("ck_llm_generation_requests_request_metadata_safe_shape"),
        ),
        sa.CheckConstraint(
            "started_at IS NULL OR started_at >= requested_at",
            name=op.f("ck_llm_generation_requests_started_after_requested"),
        ),
        sa.CheckConstraint(
            "status IN ('REQUESTED', 'RUNNING', 'COMPLETED', 'FAILED')",
            name=op.f("ck_llm_generation_requests_status_allowed"),
        ),
        sa.CheckConstraint(
            "(status = 'REQUESTED' AND started_at IS NULL "
            "AND completed_at IS NULL AND failed_at IS NULL "
            "AND failure_code IS NULL) OR "
            "(status = 'RUNNING' AND started_at IS NOT NULL "
            "AND completed_at IS NULL AND failed_at IS NULL "
            "AND failure_code IS NULL) OR "
            "(status = 'COMPLETED' AND started_at IS NOT NULL "
            "AND completed_at IS NOT NULL AND failed_at IS NULL "
            "AND failure_code IS NULL) OR "
            "(status = 'FAILED' AND completed_at IS NULL "
            "AND failed_at IS NOT NULL AND failure_code IS NOT NULL)",
            name=op.f("ck_llm_generation_requests_status_timing_consistent"),
        ),
        sa.ForeignKeyConstraint(
            ["prompt_version_id"],
            ["prompt_versions.id"],
            name=op.f("fk_llm_generation_requests_prompt_version_id_prompt_versions"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["session_id", "floor_grant_id"],
            ["floor_grants.session_id", "floor_grants.id"],
            name=op.f("fk_llm_generation_requests_session_id_floor_grants"),
            deferrable=True,
            initially="DEFERRED",
        ),
        sa.ForeignKeyConstraint(
            ["session_id", "participant_id"],
            ["session_participants.session_id", "session_participants.id"],
            name=op.f("fk_llm_generation_requests_session_id_session_participants"),
            deferrable=True,
            initially="DEFERRED",
        ),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["simulation_sessions.id"],
            name=op.f("fk_llm_generation_requests_session_id_simulation_sessions"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_llm_generation_requests")),
        sa.UniqueConstraint(
            "session_id", "id", name="uq_llm_generation_requests_session_id"
        ),
        sa.UniqueConstraint(
            "session_id",
            "id",
            "participant_id",
            "floor_grant_id",
            "status",
            name="uq_llm_generation_requests_utterance_context",
        ),
    )
    op.create_index(
        "ix_llm_generation_requests_session_requested",
        "llm_generation_requests",
        ["session_id", "requested_at", "id"],
        unique=False,
    )
    op.create_table(
        "ai_utterances",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("participant_id", sa.Uuid(), nullable=False),
        sa.Column("floor_grant_id", sa.Uuid(), nullable=False),
        sa.Column("generation_request_id", sa.Uuid(), nullable=False),
        sa.Column("generation_request_status", sa.String(length=16), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("content_digest", sa.LargeBinary(), nullable=False),
        sa.Column("persisted_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "length(content) > 0",
            name=op.f("ck_ai_utterances_content_non_empty"),
        ),
        sa.CheckConstraint(
            "octet_length(content_digest) = 32",
            name=op.f("ck_ai_utterances_content_digest_sha256"),
        ),
        sa.CheckConstraint(
            "generation_request_status = 'COMPLETED'",
            name=op.f("ck_ai_utterances_successful_generation_required"),
        ),
        sa.ForeignKeyConstraint(
            [
                "session_id",
                "generation_request_id",
                "participant_id",
                "floor_grant_id",
                "generation_request_status",
            ],
            [
                "llm_generation_requests.session_id",
                "llm_generation_requests.id",
                "llm_generation_requests.participant_id",
                "llm_generation_requests.floor_grant_id",
                "llm_generation_requests.status",
            ],
            name=op.f("fk_ai_utterances_session_id_llm_generation_requests"),
            deferrable=True,
            initially="DEFERRED",
        ),
        sa.ForeignKeyConstraint(
            ["session_id", "floor_grant_id"],
            ["floor_grants.session_id", "floor_grants.id"],
            name=op.f("fk_ai_utterances_session_id_floor_grants"),
            deferrable=True,
            initially="DEFERRED",
        ),
        sa.ForeignKeyConstraint(
            ["session_id", "participant_id"],
            ["session_participants.session_id", "session_participants.id"],
            name=op.f("fk_ai_utterances_session_id_session_participants"),
            deferrable=True,
            initially="DEFERRED",
        ),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["simulation_sessions.id"],
            name=op.f("fk_ai_utterances_session_id_simulation_sessions"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ai_utterances")),
        sa.UniqueConstraint(
            "session_id", "floor_grant_id", name="uq_ai_utterances_floor_grant"
        ),
        sa.UniqueConstraint(
            "generation_request_id", name="uq_ai_utterances_generation_request"
        ),
    )
    op.create_index(
        "ix_ai_utterances_session_persisted",
        "ai_utterances",
        ["session_id", "persisted_at", "id"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_ai_utterances_session_persisted", table_name="ai_utterances")
    op.drop_table("ai_utterances")
    op.drop_index(
        "ix_llm_generation_requests_session_requested",
        table_name="llm_generation_requests",
    )
    op.drop_table("llm_generation_requests")
    op.drop_table("prompt_versions")
