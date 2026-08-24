from enum import StrEnum
from typing import Protocol, Self

from pydantic import UUID4, TypeAdapter, ValidationError, model_validator

from group_interview_arena_api.modules.ai_runtime.domain import (
    ClosedDomainModel,
    Code,
    GenerationFailureCode,
    Identifier,
    PromptText,
    UtteranceText,
)


class RuntimeGenerationInput(ClosedDomainModel):
    generation_request_id: UUID4
    session_id: UUID4
    participant_id: UUID4
    floor_grant_id: UUID4
    phase: Code
    prompt_version_id: UUID4
    prompt_key: Code
    prompt_version_number: int
    rendered_prompt: PromptText
    provider_identifier: Identifier
    model_identifier: Identifier
    configuration_version: Code


class RawGenerationSuccess(ClosedDomainModel):
    content: str


class RawGenerationFailure(ClosedDomainModel):
    failure_code: GenerationFailureCode


type RawGenerationResult = RawGenerationSuccess | RawGenerationFailure


class GenerationProvider(Protocol):
    async def __call__(
        self,
        generation_input: RuntimeGenerationInput,
        /,
    ) -> RawGenerationResult: ...


type GenerationExecutor = GenerationProvider


class ValidatedGenerationResult(ClosedDomainModel):
    content: UtteranceText | None = None
    failure_code: GenerationFailureCode | None = None

    @model_validator(mode="after")
    def require_exactly_one_outcome(self) -> Self:
        if (self.content is None) == (self.failure_code is None):
            raise ValueError("Generation result must be success or failure.")
        return self


_UTTERANCE_ADAPTER: TypeAdapter[str] = TypeAdapter(UtteranceText)


def validate_generation_result(
    result: object,
) -> ValidatedGenerationResult:
    if isinstance(result, RawGenerationFailure):
        return ValidatedGenerationResult(failure_code=result.failure_code)
    if not isinstance(result, RawGenerationSuccess):
        return ValidatedGenerationResult(
            failure_code=GenerationFailureCode.INVALID_OUTPUT
        )
    try:
        content: str = _UTTERANCE_ADAPTER.validate_python(
            result.content,
            strict=True,
        )
    except ValidationError:
        return ValidatedGenerationResult(
            failure_code=GenerationFailureCode.INVALID_OUTPUT
        )
    return ValidatedGenerationResult(content=content)


class DeterministicGenerationMode(StrEnum):
    SUCCESS = "SUCCESS"
    TIMEOUT = "TIMEOUT"
    PROVIDER_UNAVAILABLE = "PROVIDER_UNAVAILABLE"
    RATE_LIMIT = "RATE_LIMIT"
    INVALID_OUTPUT = "INVALID_OUTPUT"
    PARTIAL_GENERATION = "PARTIAL_GENERATION"
    INTERNAL_FAILURE = "INTERNAL_FAILURE"


class DeterministicGenerationHarness:
    """Network-free P1-5C runtime harness, not a provider adapter."""

    def __init__(self, mode: DeterministicGenerationMode) -> None:
        self._mode = mode

    async def __call__(
        self,
        generation_input: RuntimeGenerationInput,
    ) -> RawGenerationResult:
        if self._mode is DeterministicGenerationMode.SUCCESS:
            return RawGenerationSuccess(
                content=(
                    "Deterministic contribution for participant "
                    f"{generation_input.participant_id} in phase "
                    f"{generation_input.phase}."
                )
            )
        if self._mode is DeterministicGenerationMode.INVALID_OUTPUT:
            return RawGenerationSuccess(content="   ")
        failure_codes = {
            DeterministicGenerationMode.TIMEOUT: GenerationFailureCode.TIMEOUT,
            DeterministicGenerationMode.PROVIDER_UNAVAILABLE: (
                GenerationFailureCode.PROVIDER_UNAVAILABLE
            ),
            DeterministicGenerationMode.RATE_LIMIT: GenerationFailureCode.RATE_LIMIT,
            DeterministicGenerationMode.PARTIAL_GENERATION: (
                GenerationFailureCode.PARTIAL_GENERATION
            ),
            DeterministicGenerationMode.INTERNAL_FAILURE: (
                GenerationFailureCode.INTERNAL_ERROR
            ),
        }
        return RawGenerationFailure(failure_code=failure_codes[self._mode])
