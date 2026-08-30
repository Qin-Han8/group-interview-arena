import pytest
from pydantic import ValidationError

from group_interview_arena_api.modules.ai_runtime.domain import (
    DiscussionContextMode,
    GenerationRequestMetadata,
    GenerationRequestMetadataV2,
    parse_generation_request_metadata,
)


def test_historical_v1_remains_readable_and_closed() -> None:
    v1 = parse_generation_request_metadata(
        {"schema_version": 1, "configuration_version": "CFG"}
    )
    assert isinstance(v1, GenerationRequestMetadata)
    with pytest.raises(ValidationError):
        GenerationRequestMetadata.model_validate(
            {"schema_version": 1, "configuration_version": "CFG", "memory_revision": 0}
        )


def test_v2_is_closed_and_records_exact_working_context_boundaries() -> None:
    v2 = GenerationRequestMetadataV2(
        configuration_version="CFG",
        working_context_version="DISCUSSION_WORKING_CONTEXT_V1",
        context_mode=DiscussionContextMode.MEMORY_WITH_RAW_TAIL,
        memory_revision=2,
        memory_source_through_sequence=9,
        context_source_through_sequence=13,
    )
    assert parse_generation_request_metadata(v2.model_dump(mode="json")) == v2
    with pytest.raises(ValidationError):
        GenerationRequestMetadataV2(
            configuration_version="CFG",
            working_context_version="DISCUSSION_WORKING_CONTEXT_V1",
            context_mode=DiscussionContextMode.MEMORY_WITH_RAW_TAIL,
            memory_revision=2,
            memory_source_through_sequence=14,
            context_source_through_sequence=13,
        )
