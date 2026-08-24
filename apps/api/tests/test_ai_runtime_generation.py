import asyncio
from uuid import uuid4

import pytest
from pydantic import ValidationError

from group_interview_arena_api.modules.ai_runtime.domain import GenerationFailureCode
from group_interview_arena_api.modules.ai_runtime.generation import (
    DeterministicGenerationHarness,
    DeterministicGenerationMode,
    RuntimeGenerationInput,
    validate_generation_result,
)


def _input() -> RuntimeGenerationInput:
    return RuntimeGenerationInput(
        generation_request_id=uuid4(),
        session_id=uuid4(),
        participant_id=uuid4(),
        floor_grant_id=uuid4(),
        phase="EXPLORATION",
        prompt_version_id=uuid4(),
        prompt_key="AI_CANDIDATE_TURN",
        prompt_version_number=1,
        rendered_prompt="Use only this authorized deterministic context.",
        provider_identifier="local-deterministic-executor",
        model_identifier="p1-5c-harness-v1",
        configuration_version="P1_5C_DETERMINISTIC",
    )


def test_generation_input_is_typed_immutable_and_has_no_secret_escape_hatch() -> None:
    generation_input = _input()

    with pytest.raises(ValidationError):
        generation_input.phase = "CONVERGENCE"  # pyright: ignore[reportAttributeAccessIssue]

    forbidden = {
        "provider_secret",
        "credential",
        "headers",
        "body",
        "cookie",
        "database_url",
        "private_db_model",
        "scoring_state",
    }
    assert forbidden.isdisjoint(RuntimeGenerationInput.model_fields)


def test_deterministic_harness_success_is_stable() -> None:
    generation_input = _input()
    harness = DeterministicGenerationHarness(DeterministicGenerationMode.SUCCESS)

    first = asyncio.run(harness(generation_input))
    second = asyncio.run(harness(generation_input))

    assert first == second
    validated = validate_generation_result(first)
    assert validated.content is not None
    assert validated.failure_code is None
    assert str(generation_input.participant_id) in validated.content


@pytest.mark.parametrize(
    ("mode", "failure_code"),
    [
        (DeterministicGenerationMode.TIMEOUT, GenerationFailureCode.TIMEOUT),
        (
            DeterministicGenerationMode.PROVIDER_UNAVAILABLE,
            GenerationFailureCode.PROVIDER_UNAVAILABLE,
        ),
        (DeterministicGenerationMode.RATE_LIMIT, GenerationFailureCode.RATE_LIMIT),
        (
            DeterministicGenerationMode.PARTIAL_GENERATION,
            GenerationFailureCode.PARTIAL_GENERATION,
        ),
        (
            DeterministicGenerationMode.INTERNAL_FAILURE,
            GenerationFailureCode.INTERNAL_ERROR,
        ),
        (
            DeterministicGenerationMode.INVALID_OUTPUT,
            GenerationFailureCode.INVALID_OUTPUT,
        ),
    ],
)
def test_deterministic_harness_failure_modes_are_safe_and_typed(
    mode: DeterministicGenerationMode,
    failure_code: GenerationFailureCode,
) -> None:
    raw = asyncio.run(DeterministicGenerationHarness(mode)(_input()))
    validated = validate_generation_result(raw)

    assert validated.content is None
    assert validated.failure_code is failure_code
    assert "exception" not in repr(validated).lower()
