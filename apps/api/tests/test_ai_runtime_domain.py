from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from group_interview_arena_api.modules.ai_runtime.domain import (
    GenerationRequestMetadata,
    PromptVersionDefinition,
    RequestGenerationCommand,
)

NOW = datetime(2026, 8, 21, tzinfo=UTC)


def test_prompt_version_is_frozen_and_has_versioned_lifecycle() -> None:
    definition = PromptVersionDefinition(
        id=uuid4(),
        prompt_key="AI_CANDIDATE_TURN",
        version_number=1,
        purpose_code="CANDIDATE_UTTERANCE",
        template_text="Produce one discussion contribution.",
        created_at=NOW,
        published_at=NOW,
    )

    with pytest.raises(ValidationError):
        definition.template_text = "mutated"  # pyright: ignore[reportAttributeAccessIssue]

    with pytest.raises(ValidationError):
        PromptVersionDefinition(
            id=uuid4(),
            prompt_key="AI_CANDIDATE_TURN",
            version_number=1,
            purpose_code="CANDIDATE_UTTERANCE",
            template_text="Prompt",
            created_at=NOW,
            published_at=datetime(2026, 8, 20, tzinfo=UTC),
        )


def test_request_metadata_is_closed_and_cannot_carry_private_runtime_values() -> None:
    with pytest.raises(ValidationError):
        GenerationRequestMetadata.model_validate(
            {
                "schema_version": 1,
                "configuration_version": "V01_DEFAULT",
                "private_stance": "hidden",
            }
        )

    with pytest.raises(ValidationError):
        GenerationRequestMetadata.model_validate(
            {
                "schema_version": 1,
                "configuration_version": "V01_DEFAULT",
                "api_key": "must-not-persist",
            }
        )


def test_generation_request_is_provider_neutral_provenance_not_an_utterance() -> None:
    command = RequestGenerationCommand(
        request_id=uuid4(),
        session_id=uuid4(),
        participant_id=uuid4(),
        floor_grant_id=uuid4(),
        prompt_version_id=uuid4(),
        provider_identifier="enterprise-gateway",
        model_identifier="discussion-model-v3",
        request_metadata=GenerationRequestMetadata(configuration_version="V01_DEFAULT"),
        requested_at=NOW,
    )

    assert command.provider_identifier == "enterprise-gateway"
    assert "content" not in command.model_fields_set
    assert "provider_secret" not in RequestGenerationCommand.model_fields
