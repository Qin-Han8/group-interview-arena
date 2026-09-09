"""tighten generation metadata JSON types

Revision ID: f1a16e16c007
Revises: f1a16b16c006
Create Date: 2026-09-08 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op

revision: str = "f1a16e16c007"
down_revision: str | Sequence[str] | None = "f1a16b16c006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_STRICT_V1_OR_V2_METADATA = (
    "jsonb_typeof(request_metadata) = 'object' AND (("
    "request_metadata ?& ARRAY['schema_version', 'configuration_version'] AND "
    "request_metadata - ARRAY['schema_version', 'configuration_version'] = '{}'::jsonb AND "
    "jsonb_typeof(request_metadata->'schema_version') = 'number' AND "
    "request_metadata->>'schema_version' = '1' AND "
    "jsonb_typeof(request_metadata->'configuration_version') = 'string' AND "
    "length(request_metadata->>'configuration_version') > 0) OR ("
    "request_metadata ?& ARRAY['schema_version', 'configuration_version', "
    "'working_context_version', 'context_mode', 'memory_revision', "
    "'memory_source_through_sequence', 'context_source_through_sequence'] AND "
    "request_metadata - ARRAY['schema_version', 'configuration_version', "
    "'working_context_version', 'context_mode', 'memory_revision', "
    "'memory_source_through_sequence', 'context_source_through_sequence'] = '{}'::jsonb AND "
    "jsonb_typeof(request_metadata->'schema_version') = 'number' AND "
    "request_metadata->>'schema_version' = '2' AND "
    "jsonb_typeof(request_metadata->'configuration_version') = 'string' AND "
    "length(request_metadata->>'configuration_version') > 0 AND "
    "jsonb_typeof(request_metadata->'working_context_version') = 'string' AND "
    "length(request_metadata->>'working_context_version') > 0 AND "
    "jsonb_typeof(request_metadata->'context_mode') = 'string' AND "
    "request_metadata->>'context_mode' IN ('MEMORY_WITH_RAW_TAIL', 'SAFE_RAW_FALLBACK') AND "
    "jsonb_typeof(request_metadata->'memory_revision') = 'number' AND "
    "request_metadata->>'memory_revision' ~ '^(0|[1-9][0-9]*)$' AND "
    "jsonb_typeof(request_metadata->'memory_source_through_sequence') = 'number' AND "
    "request_metadata->>'memory_source_through_sequence' ~ '^(0|[1-9][0-9]*)$' AND "
    "jsonb_typeof(request_metadata->'context_source_through_sequence') = 'number' AND "
    "request_metadata->>'context_source_through_sequence' ~ '^(0|[1-9][0-9]*)$' AND "
    "CASE WHEN "
    "jsonb_typeof(request_metadata->'memory_source_through_sequence') = 'number' AND "
    "request_metadata->>'memory_source_through_sequence' ~ '^(0|[1-9][0-9]*)$' AND "
    "jsonb_typeof(request_metadata->'context_source_through_sequence') = 'number' AND "
    "request_metadata->>'context_source_through_sequence' ~ '^(0|[1-9][0-9]*)$' "
    "THEN (request_metadata->>'context_source_through_sequence')::bigint >= "
    "(request_metadata->>'memory_source_through_sequence')::bigint ELSE FALSE END))"
)

_LEGACY_V1_OR_V2_METADATA = (
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
    op.drop_constraint(
        op.f("ck_llm_generation_requests_request_metadata_safe_shape"),
        "llm_generation_requests",
        type_="check",
    )
    op.create_check_constraint(
        op.f("ck_llm_generation_requests_request_metadata_safe_shape"),
        "llm_generation_requests",
        _STRICT_V1_OR_V2_METADATA,
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
        _LEGACY_V1_OR_V2_METADATA,
    )
