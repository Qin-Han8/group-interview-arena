import json
from types import SimpleNamespace
from uuid import uuid4

import pytest
from pydantic import ValidationError

from group_interview_arena_api.modules.discussion_memory.derivation import (
    DeterministicFakeMemoryDeriver,
    MemoryDerivationInput,
    MemoryDerivationResult,
    PublicMemoryQuestionContext,
    PublicMemoryUtterance,
    parse_memory_derivation_text,
    project_public_memory_question_context,
    validate_memory_derivation_result,
)
from group_interview_arena_api.modules.discussion_memory.domain import (
    DiscussionMemoryProjection,
    MemoryPatchOperation,
    MemoryPolicy,
)


def _input() -> MemoryDerivationInput:
    session_id = uuid4()
    return MemoryDerivationInput(
        session_id=session_id,
        previous_memory=DiscussionMemoryProjection.empty(),
        utterances=(
            PublicMemoryUtterance(
                session_id=session_id,
                sequence=3,
                participant_id=uuid4(),
                seat_order=1,
                actor_kind="HUMAN",
                phase="EXPLORATION",
                content="先比较成本。",
            ),
            PublicMemoryUtterance(
                session_id=session_id,
                sequence=5,
                participant_id=uuid4(),
                seat_order=2,
                actor_kind="AI",
                phase="EXPLORATION",
                content="还要比较覆盖面。",
            ),
        ),
        question_context=PublicMemoryQuestionContext(
            question_version_id=uuid4(),
            title="公开标题",
            scenario="公开情境",
            objective="公开目标",
            hard_constraints=({"text": "预算有限"},),
            soft_constraints=(),
            stakeholders=(),
            options=(),
        ),
    )


def test_question_projection_is_explicit_public_allowlist() -> None:
    row = SimpleNamespace(
        id=uuid4(),
        title="title",
        scenario="scenario",
        objective="objective",
        hard_constraints=[{"text": "hard"}],
        soft_constraints=[{"text": "soft"}],
        stakeholders=[{"name": "public"}],
        options=[{"name": "A"}],
        reference_dimensions=[{"secret": "REFERENCE_SENTINEL"}],
        hidden_conflicts=[{"secret": "HIDDEN_SENTINEL"}],
        acceptable_outcome_patterns=[{"secret": "EVALUATOR_SENTINEL"}],
        phase_prompts={"EXPLORATION": "SYSTEM_SENTINEL"},
    )
    projected = project_public_memory_question_context(row)
    surface = projected.model_dump_json()
    assert set(type(projected).model_fields) == {
        "question_version_id",
        "title",
        "scenario",
        "objective",
        "hard_constraints",
        "soft_constraints",
        "stakeholders",
        "options",
    }
    assert not any(
        token in surface
        for token in (
            "REFERENCE_SENTINEL",
            "HIDDEN_SENTINEL",
            "EVALUATOR_SENTINEL",
            "SYSTEM_SENTINEL",
        )
    )


def test_closed_input_rejects_private_or_candidate_context() -> None:
    payload = _input().model_dump()
    payload["private_stance"] = "PRIVATE_STANCE_SENTINEL"
    with pytest.raises(ValidationError):
        MemoryDerivationInput.model_validate(payload)


def test_strict_parser_and_deterministic_fake_return_patches_only() -> None:
    source = _input()
    first = DeterministicFakeMemoryDeriver().derive(source)
    assert first == DeterministicFakeMemoryDeriver().derive(source)
    assert first.patches[0].operation is MemoryPatchOperation.ADD
    assert first.patches[0].target_memory_item_id is None
    parsed = parse_memory_derivation_text(json.dumps(first.model_dump(mode="json")))
    assert parsed == first
    with pytest.raises(ValueError):
        parse_memory_derivation_text('{"patches": [], "revision": 99}')


def test_provenance_validator_rejects_hallucinated_or_cross_session_sources() -> None:
    source = _input()
    valid = DeterministicFakeMemoryDeriver().derive(source)
    assert (
        validate_memory_derivation_result(source, valid, policy=MemoryPolicy()) == valid
    )
    hallucinated = MemoryDerivationResult(
        patches=(valid.patches[0].model_copy(update={"source_sequences": (999,)}),)
    )
    with pytest.raises(ValueError, match="provenance"):
        validate_memory_derivation_result(source, hallucinated, policy=MemoryPolicy())
    cross_session = source.model_copy(
        update={
            "utterances": (
                source.utterances[0].model_copy(update={"session_id": uuid4()}),
            )
        }
    )
    with pytest.raises(ValidationError):
        MemoryDerivationInput.model_validate(cross_session.model_dump())
