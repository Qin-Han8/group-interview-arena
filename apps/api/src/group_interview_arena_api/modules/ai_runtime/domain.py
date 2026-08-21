from datetime import UTC, datetime
from enum import StrEnum
from typing import Annotated, Literal, Self

from pydantic import (
    UUID4,
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


def _reject_whitespace_only(value: str) -> str:
    if not value.strip():
        raise ValueError("text must contain a non-whitespace character")
    return value


def _require_aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamp must be timezone-aware")
    return value.astimezone(UTC)


Code = Annotated[str, Field(pattern=r"^[A-Z][A-Z0-9_]{0,63}$")]
Identifier = Annotated[
    str,
    Field(min_length=1, max_length=128),
    AfterValidator(_reject_whitespace_only),
]
PromptText = Annotated[
    str,
    Field(min_length=1, max_length=20_000),
    AfterValidator(_reject_whitespace_only),
]
UtteranceText = Annotated[
    str,
    Field(min_length=1, max_length=20_000),
    AfterValidator(_reject_whitespace_only),
]


class ClosedDomainModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class GenerationRequestStatus(StrEnum):
    REQUESTED = "REQUESTED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class GenerationFailureCode(StrEnum):
    TIMEOUT = "TIMEOUT"
    PROVIDER_UNAVAILABLE = "PROVIDER_UNAVAILABLE"
    RATE_LIMIT = "RATE_LIMIT"
    PARTIAL_GENERATION = "PARTIAL_GENERATION"
    INVALID_OUTPUT = "INVALID_OUTPUT"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class PromptVersionDefinition(ClosedDomainModel):
    id: UUID4
    prompt_key: Code
    version_number: Annotated[int, Field(gt=0, le=32_767)]
    purpose_code: Code
    template_text: PromptText
    created_at: datetime
    published_at: datetime
    retired_at: datetime | None = None

    @field_validator("created_at", "published_at", "retired_at")
    @classmethod
    def validate_timestamps(cls, value: datetime | None) -> datetime | None:
        return None if value is None else _require_aware_utc(value)

    @model_validator(mode="after")
    def validate_lifecycle(self) -> Self:
        if self.published_at < self.created_at:
            raise ValueError("publication cannot precede creation")
        if self.retired_at is not None and self.retired_at < self.published_at:
            raise ValueError("retirement cannot precede publication")
        return self


class GenerationRequestMetadata(ClosedDomainModel):
    schema_version: Literal[1] = 1
    configuration_version: Code


class RequestGenerationCommand(ClosedDomainModel):
    request_id: UUID4
    session_id: UUID4
    participant_id: UUID4
    floor_grant_id: UUID4
    prompt_version_id: UUID4
    provider_identifier: Identifier
    model_identifier: Identifier
    request_metadata: GenerationRequestMetadata
    requested_at: datetime

    @field_validator("requested_at")
    @classmethod
    def validate_requested_at(cls, value: datetime) -> datetime:
        return _require_aware_utc(value)


class PersistUtteranceCommand(ClosedDomainModel):
    utterance_id: UUID4
    session_id: UUID4
    generation_request_id: UUID4
    content: UtteranceText
    persisted_at: datetime

    @field_validator("persisted_at")
    @classmethod
    def validate_persisted_at(cls, value: datetime) -> datetime:
        return _require_aware_utc(value)


class StartGenerationCommand(ClosedDomainModel):
    session_id: UUID4
    generation_request_id: UUID4
    started_at: datetime

    @field_validator("started_at")
    @classmethod
    def validate_started_at(cls, value: datetime) -> datetime:
        return _require_aware_utc(value)


class FailGenerationCommand(ClosedDomainModel):
    session_id: UUID4
    generation_request_id: UUID4
    failure_code: GenerationFailureCode
    failed_at: datetime

    @field_validator("failed_at")
    @classmethod
    def validate_failed_at(cls, value: datetime) -> datetime:
        return _require_aware_utc(value)


class GenerationRequestSnapshot(ClosedDomainModel):
    request_id: UUID4
    session_id: UUID4
    participant_id: UUID4
    floor_grant_id: UUID4
    prompt_version_id: UUID4
    provider_identifier: Identifier
    model_identifier: Identifier
    request_metadata: GenerationRequestMetadata
    status: GenerationRequestStatus
    requested_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    failed_at: datetime | None
    failure_code: GenerationFailureCode | None
    utterance_id: UUID4 | None = None


class PromptVersionMutationError(RuntimeError):
    """A stable prompt identity already exists with different immutable content."""


class GenerationRequestConflictError(RuntimeError):
    """A request or utterance identity was replayed with different content."""


class GenerationContextError(RuntimeError):
    """The session, participant, prompt, or floor context is not eligible."""


class GenerationStateError(RuntimeError):
    """The requested lifecycle transition is invalid."""


class AiRuntimePersistenceError(RuntimeError):
    """The provider-neutral AI runtime transaction could not be persisted."""
