from uuid import uuid4

from group_interview_arena_api.modules.ai_runtime.generation import (
    ModelInvocationInput,
    ModelOutputExpectation,
    RuntimeGenerationInput,
)


def test_candidate_adapts_to_minimal_shared_transport_without_fake_identity() -> None:
    candidate = RuntimeGenerationInput(
        generation_request_id=uuid4(),
        session_id=uuid4(),
        participant_id=uuid4(),
        floor_grant_id=uuid4(),
        phase="EXPLORATION",
        prompt_version_id=uuid4(),
        prompt_key="AI_CANDIDATE_TURN",
        prompt_version_number=3,
        rendered_prompt="candidate",
        provider_identifier="zhipu",
        model_identifier="model",
        configuration_version="CFG",
    )
    invocation = candidate.to_model_invocation()
    assert isinstance(invocation, ModelInvocationInput)
    assert set(type(invocation).model_fields) == {
        "rendered_prompt",
        "provider_identifier",
        "model_identifier",
        "configuration_version",
        "temperature",
        "max_output_tokens",
        "output_expectation",
    }
    assert invocation.output_expectation is ModelOutputExpectation.TEXT
    assert "participant_id" not in invocation.model_dump()


def test_memory_can_use_json_expectation_and_its_own_bounded_options() -> None:
    invocation = ModelInvocationInput(
        rendered_prompt="memory",
        provider_identifier="zhipu",
        model_identifier="model",
        configuration_version="CFG",
        temperature=0.2,
        max_output_tokens=1024,
        output_expectation=ModelOutputExpectation.JSON_OBJECT,
    )
    assert (invocation.temperature, invocation.max_output_tokens) == (0.2, 1024)
