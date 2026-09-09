from typing import cast

from sqlalchemy import CheckConstraint, Table, UniqueConstraint

from group_interview_arena_api.db.models import (
    DiscussionMemoryRevision,
    DiscussionMemoryState,
    LlmGenerationRequest,
)


def test_memory_state_is_one_materialized_row_per_session() -> None:
    table = cast(Table, DiscussionMemoryState.__table__)
    assert table.name == "discussion_memory_states"
    assert table.primary_key.columns.keys() == ["session_id"]
    assert set(table.columns.keys()) == {
        "session_id",
        "revision",
        "source_through_sequence",
        "schema_version",
        "derivation_version",
        "projection_version",
        "structured_state",
        "updated_at",
    }


def test_revision_is_append_only_patch_journal_with_additive_provenance() -> None:
    table = cast(Table, DiscussionMemoryRevision.__table__)
    assert table.name == "discussion_memory_revisions"
    assert set(table.columns.keys()) == {
        "id",
        "session_id",
        "revision",
        "base_revision",
        "source_from_sequence",
        "source_through_sequence",
        "patches",
        "schema_version",
        "derivation_version",
        "projection_version",
        "derivation_input_digest",
        "prompt_version_id",
        "provider_identifier",
        "model_identifier",
        "configuration_version",
        "created_at",
    }
    uniques = {
        tuple(item.columns.keys())
        for item in table.constraints
        if isinstance(item, UniqueConstraint)
    }
    assert ("session_id", "revision") in uniques


def test_generation_metadata_constraint_accepts_additive_v2_shape() -> None:
    table = cast(Table, LlmGenerationRequest.__table__)
    sql = " ".join(
        str(item.sqltext)
        for item in table.constraints
        if isinstance(item, CheckConstraint)
        and "request_metadata_safe_shape" in str(item.name)
    )
    assert all(
        token in sql
        for token in (
            "schema_version",
            "working_context_version",
            "memory_revision",
            "context_source_through_sequence",
            "jsonb_typeof(request_metadata->'schema_version') = 'number'",
            "jsonb_typeof(request_metadata->'context_mode') = 'string'",
            "jsonb_typeof(request_metadata->'memory_revision') = 'number'",
            "jsonb_typeof(request_metadata->'memory_source_through_sequence') = 'number'",
            "jsonb_typeof(request_metadata->'context_source_through_sequence') = 'number'",
        )
    )
