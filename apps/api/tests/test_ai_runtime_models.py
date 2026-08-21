from typing import cast

from sqlalchemy import Enum, ForeignKeyConstraint, Table

from group_interview_arena_api.db import (
    AiUtterance,
    LlmGenerationRequest,
    PersonaTemplate,
    PromptVersion,
)


def _constraint_names(table: Table) -> set[str]:
    return {str(item.name) for item in table.constraints}


def test_prompt_version_is_an_independent_immutable_asset_shape() -> None:
    prompt = cast(Table, PromptVersion.__table__)
    persona = cast(Table, PersonaTemplate.__table__)

    assert list(prompt.c.keys()) == [
        "id",
        "prompt_key",
        "version_number",
        "purpose_code",
        "template_text",
        "content_digest",
        "created_at",
        "published_at",
        "retired_at",
    ]
    assert "updated_at" not in prompt.c
    assert "uq_prompt_versions_key_version" in _constraint_names(prompt)
    assert "prompt" not in persona.c
    assert "provider_secret" not in prompt.c
    assert "api_key" not in prompt.c


def test_generation_request_uses_varchar_lifecycle_and_closed_metadata() -> None:
    table = cast(Table, LlmGenerationRequest.__table__)

    assert not any(isinstance(column.type, Enum) for column in table.columns)
    assert {
        "ck_llm_generation_requests_status_allowed",
        "ck_llm_generation_requests_status_timing_consistent",
        "ck_llm_generation_requests_request_metadata_safe_shape",
        "ck_llm_generation_requests_request_digest_sha256",
    } <= _constraint_names(table)
    forbidden = {
        "provider_secret",
        "api_key",
        "private_stance",
        "persona_calibration",
        "hidden_ranking",
        "internal_prompt_variables",
        "token_count",
        "cost",
    }
    assert forbidden.isdisjoint(table.c.keys())


def test_utterance_requires_matching_completed_generation_context() -> None:
    table = cast(Table, AiUtterance.__table__)
    generation_fk = next(
        item
        for item in table.constraints
        if isinstance(item, ForeignKeyConstraint)
        and item.name == "fk_ai_utterances_session_id_llm_generation_requests"
    )

    assert [column.name for column in generation_fk.columns] == [
        "session_id",
        "generation_request_id",
        "participant_id",
        "floor_grant_id",
        "generation_request_status",
    ]
    assert generation_fk.deferrable is True
    assert generation_fk.initially == "DEFERRED"
    assert "ck_ai_utterances_successful_generation_required" in _constraint_names(table)
    assert "uq_ai_utterances_generation_request" in _constraint_names(table)
    assert "uq_ai_utterances_floor_grant" in _constraint_names(table)
    assert "updated_at" not in table.c
