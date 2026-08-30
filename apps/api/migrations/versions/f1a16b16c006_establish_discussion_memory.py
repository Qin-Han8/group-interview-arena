"""establish structured discussion memory

Revision ID: f1a16b16c006
Revises: f1a15b15c005
Create Date: 2026-08-30 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "f1a16b16c006"
down_revision: str | Sequence[str] | None = "f1a15b15c005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_V1_METADATA = (
    "jsonb_typeof(request_metadata) = 'object' AND "
    "request_metadata ?& ARRAY['schema_version', 'configuration_version'] AND "
    "request_metadata - ARRAY['schema_version', 'configuration_version'] = '{}'::jsonb AND "
    "jsonb_typeof(request_metadata->'schema_version') = 'number' AND "
    "request_metadata->>'schema_version' = '1' AND "
    "jsonb_typeof(request_metadata->'configuration_version') = 'string' AND "
    "length(request_metadata->>'configuration_version') > 0"
)

_V1_OR_V2_METADATA = (
    "jsonb_typeof(request_metadata) = 'object' AND (("
    "request_metadata ?& ARRAY['schema_version', 'configuration_version'] AND "
    "request_metadata - ARRAY['schema_version', 'configuration_version'] = '{}'::jsonb AND "
    "request_metadata->>'schema_version' = '1' AND "
    "jsonb_typeof(request_metadata->'configuration_version') = 'string' AND "
    "length(request_metadata->>'configuration_version') > 0) OR ("
    "request_metadata ?& ARRAY['schema_version', 'configuration_version', "
    "'working_context_version', 'context_mode', 'memory_revision', "
    "'memory_source_through_sequence', 'context_source_through_sequence'] AND "
    "request_metadata - ARRAY['schema_version', 'configuration_version', "
    "'working_context_version', 'context_mode', 'memory_revision', "
    "'memory_source_through_sequence', 'context_source_through_sequence'] = '{}'::jsonb AND "
    "request_metadata->>'schema_version' = '2' AND "
    "jsonb_typeof(request_metadata->'configuration_version') = 'string' AND "
    "length(request_metadata->>'configuration_version') > 0 AND "
    "jsonb_typeof(request_metadata->'working_context_version') = 'string' AND "
    "length(request_metadata->>'working_context_version') > 0 AND "
    "request_metadata->>'context_mode' IN ('MEMORY_WITH_RAW_TAIL', 'SAFE_RAW_FALLBACK') AND "
    "request_metadata->>'memory_revision' ~ '^[0-9]+$' AND "
    "request_metadata->>'memory_source_through_sequence' ~ '^[0-9]+$' AND "
    "request_metadata->>'context_source_through_sequence' ~ '^[0-9]+$' AND "
    "(request_metadata->>'context_source_through_sequence')::bigint >= "
    "(request_metadata->>'memory_source_through_sequence')::bigint))"
)


def upgrade() -> None:
    op.create_table(
        "discussion_memory_states",
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("revision", sa.BigInteger(), nullable=False),
        sa.Column("source_through_sequence", sa.BigInteger(), nullable=False),
        sa.Column("schema_version", sa.SmallInteger(), nullable=False),
        sa.Column("derivation_version", sa.String(length=128), nullable=False),
        sa.Column("projection_version", sa.String(length=128), nullable=False),
        sa.Column(
            "structured_state", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "revision >= 0",
            name=op.f("ck_discussion_memory_states_revision_non_negative"),
        ),
        sa.CheckConstraint(
            "source_through_sequence >= 0",
            name=op.f(
                "ck_discussion_memory_states_source_through_sequence_non_negative"
            ),
        ),
        sa.CheckConstraint(
            "schema_version > 0",
            name=op.f("ck_discussion_memory_states_schema_version_positive"),
        ),
        sa.CheckConstraint(
            "length(derivation_version) > 0 AND length(projection_version) > 0",
            name=op.f("ck_discussion_memory_states_version_identifiers_non_empty"),
        ),
        sa.CheckConstraint(
            "jsonb_typeof(structured_state) = 'object'",
            name=op.f("ck_discussion_memory_states_structured_state_object"),
        ),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["simulation_sessions.id"],
            name=op.f("fk_discussion_memory_states_session_id_simulation_sessions"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("session_id", name=op.f("pk_discussion_memory_states")),
    )
    op.create_table(
        "discussion_memory_revisions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("revision", sa.BigInteger(), nullable=False),
        sa.Column("base_revision", sa.BigInteger(), nullable=False),
        sa.Column("source_from_sequence", sa.BigInteger(), nullable=False),
        sa.Column("source_through_sequence", sa.BigInteger(), nullable=False),
        sa.Column("patches", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("schema_version", sa.SmallInteger(), nullable=False),
        sa.Column("derivation_version", sa.String(length=128), nullable=False),
        sa.Column("projection_version", sa.String(length=128), nullable=False),
        sa.Column("derivation_input_digest", sa.LargeBinary(length=32), nullable=False),
        sa.Column("prompt_version_id", sa.Uuid(), nullable=True),
        sa.Column("provider_identifier", sa.String(length=128), nullable=True),
        sa.Column("model_identifier", sa.String(length=128), nullable=True),
        sa.Column("configuration_version", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "revision > 0",
            name=op.f("ck_discussion_memory_revisions_revision_positive"),
        ),
        sa.CheckConstraint(
            "base_revision >= 0",
            name=op.f("ck_discussion_memory_revisions_base_revision_non_negative"),
        ),
        sa.CheckConstraint(
            "revision = base_revision + 1",
            name=op.f("ck_discussion_memory_revisions_revision_advances_once"),
        ),
        sa.CheckConstraint(
            "source_from_sequence > 0 AND source_through_sequence >= source_from_sequence",
            name=op.f("ck_discussion_memory_revisions_source_range_valid"),
        ),
        sa.CheckConstraint(
            "jsonb_typeof(patches) = 'array'",
            name=op.f("ck_discussion_memory_revisions_patches_array"),
        ),
        sa.CheckConstraint(
            "schema_version > 0",
            name=op.f("ck_discussion_memory_revisions_schema_version_positive"),
        ),
        sa.CheckConstraint(
            "length(derivation_version) > 0 AND length(projection_version) > 0",
            name=op.f("ck_discussion_memory_revisions_version_identifiers_non_empty"),
        ),
        sa.CheckConstraint(
            "octet_length(derivation_input_digest) = 32",
            name=op.f("ck_discussion_memory_revisions_derivation_input_digest_sha256"),
        ),
        sa.CheckConstraint(
            "(prompt_version_id IS NULL AND provider_identifier IS NULL AND model_identifier IS NULL AND configuration_version IS NULL) OR (prompt_version_id IS NOT NULL AND provider_identifier IS NOT NULL AND model_identifier IS NOT NULL AND configuration_version IS NOT NULL AND length(provider_identifier) > 0 AND length(model_identifier) > 0 AND length(configuration_version) > 0)",
            name=op.f(
                "ck_discussion_memory_revisions_semantic_provenance_group_complete"
            ),
        ),
        sa.ForeignKeyConstraint(
            ["prompt_version_id"],
            ["prompt_versions.id"],
            name=op.f(
                "fk_discussion_memory_revisions_prompt_version_id_prompt_versions"
            ),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["simulation_sessions.id"],
            name=op.f("fk_discussion_memory_revisions_session_id_simulation_sessions"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_discussion_memory_revisions")),
        sa.UniqueConstraint(
            "session_id",
            "revision",
            name="uq_discussion_memory_revisions_session_revision",
        ),
    )
    op.create_index(
        "ix_discussion_memory_revisions_session_source",
        "discussion_memory_revisions",
        ["session_id", "source_through_sequence", "revision"],
        unique=False,
    )
    op.drop_constraint(
        op.f("ck_llm_generation_requests_request_metadata_safe_shape"),
        "llm_generation_requests",
        type_="check",
    )
    op.create_check_constraint(
        op.f("ck_llm_generation_requests_request_metadata_safe_shape"),
        "llm_generation_requests",
        _V1_OR_V2_METADATA,
    )


def downgrade() -> None:
    op.drop_constraint(
        op.f("ck_llm_generation_requests_request_metadata_safe_shape"),
        "llm_generation_requests",
        type_="check",
    )
    op.create_check_constraint(
        op.f("ck_llm_generation_requests_request_metadata_safe_shape"),
        "llm_generation_requests",
        _V1_METADATA,
    )
    op.drop_index(
        "ix_discussion_memory_revisions_session_source",
        table_name="discussion_memory_revisions",
    )
    op.drop_table("discussion_memory_revisions")
    op.drop_table("discussion_memory_states")
