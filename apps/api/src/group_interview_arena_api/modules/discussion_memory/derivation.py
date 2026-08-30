from __future__ import annotations

import json
from string import Template
from typing import Any, Literal, Protocol, Self
from uuid import UUID

from pydantic import Field, ValidationError, model_validator

from group_interview_arena_api.modules.ai_runtime.generation import (
    ModelInvocationInput,
    ModelInvoker,
    ModelOutputExpectation,
    RawGenerationSuccess,
)
from group_interview_arena_api.modules.discussion_memory.domain import (
    DiscussionMemoryProjection,
    MemoryDomainModel,
    MemoryItemKind,
    MemoryPatch,
    MemoryPatchOperation,
    MemoryPolicy,
)


class PublicMemoryQuestionContext(MemoryDomainModel):
    question_version_id: UUID
    title: str = Field(min_length=1, max_length=200)
    scenario: str = Field(min_length=1, max_length=20_000)
    objective: str = Field(min_length=1, max_length=10_000)
    hard_constraints: tuple[dict[str, object], ...] = Field(max_length=64)
    soft_constraints: tuple[dict[str, object], ...] = Field(max_length=64)
    stakeholders: tuple[dict[str, object], ...] = Field(max_length=64)
    options: tuple[dict[str, object], ...] = Field(max_length=64)


def project_public_memory_question_context(
    question: Any,
) -> PublicMemoryQuestionContext:
    """Deliberate allowlist projection; never forwards an ORM/generic dump."""
    return PublicMemoryQuestionContext(
        question_version_id=question.id,
        title=question.title,
        scenario=question.scenario,
        objective=question.objective,
        hard_constraints=tuple(question.hard_constraints),
        soft_constraints=tuple(question.soft_constraints),
        stakeholders=tuple(question.stakeholders),
        options=tuple(question.options),
    )


class PublicMemoryUtterance(MemoryDomainModel):
    session_id: UUID
    sequence: int = Field(gt=0)
    participant_id: UUID
    seat_order: int = Field(gt=0)
    actor_kind: Literal["HUMAN", "AI"]
    phase: str = Field(min_length=1, max_length=64)
    content: str = Field(min_length=1, max_length=20_000)


class MemoryDerivationInput(MemoryDomainModel):
    session_id: UUID
    previous_memory: DiscussionMemoryProjection
    utterances: tuple[PublicMemoryUtterance, ...] = Field(min_length=1, max_length=64)
    question_context: PublicMemoryQuestionContext | None = None

    @model_validator(mode="after")
    def validate_public_episode(self) -> Self:
        sequences = tuple(item.sequence for item in self.utterances)
        if tuple(sorted(set(sequences))) != sequences:
            raise ValueError("public utterances must be strictly ordered and unique")
        if any(item.session_id != self.session_id for item in self.utterances):
            raise ValueError("public utterance crosses session boundary")
        return self


class MemoryDerivationResult(MemoryDomainModel):
    patches: tuple[MemoryPatch, ...] = Field(max_length=128)


class MemoryDeriver(Protocol):
    def derive(
        self, derivation_input: MemoryDerivationInput, /
    ) -> MemoryDerivationResult: ...


class MemoryDerivationUnavailable(RuntimeError):
    pass


class ModelBackedMemoryDeriver:
    """Public-only semantic adapter over the shared project-owned transport."""

    def __init__(
        self,
        *,
        invoker: ModelInvoker,
        template_text: str,
        provider_identifier: str,
        model_identifier: str,
        configuration_version: str,
    ) -> None:
        self._invoker = invoker
        self._template_text = template_text
        self._provider_identifier = provider_identifier
        self._model_identifier = model_identifier
        self._configuration_version = configuration_version

    async def derive(
        self, derivation_input: MemoryDerivationInput
    ) -> MemoryDerivationResult:
        template = Template(self._template_text)
        if not template.is_valid() or frozenset(
            template.get_identifiers()
        ) != frozenset({"memory_derivation_input"}):
            raise MemoryDerivationUnavailable("semantic prompt contract is invalid")
        rendered = template.substitute(
            memory_derivation_input=json.dumps(
                derivation_input.model_dump(mode="json"),
                ensure_ascii=False,
                separators=(",", ":"),
                sort_keys=True,
            )
        )
        raw = await self._invoker.invoke(
            ModelInvocationInput(
                rendered_prompt=rendered,
                provider_identifier=self._provider_identifier,
                model_identifier=self._model_identifier,
                configuration_version=self._configuration_version,
                temperature=0.2,
                max_output_tokens=1024,
                output_expectation=ModelOutputExpectation.JSON_OBJECT,
            )
        )
        if not isinstance(raw, RawGenerationSuccess):
            raise MemoryDerivationUnavailable("semantic model invocation failed")
        try:
            return parse_memory_derivation_text(raw.content)
        except ValueError as error:
            raise MemoryDerivationUnavailable(
                "semantic model output is invalid"
            ) from error


class DeterministicFakeMemoryDeriver:
    """Network-free stable semantic fake used by correctness tests."""

    def derive(self, derivation_input: MemoryDerivationInput) -> MemoryDerivationResult:
        sequences = tuple(item.sequence for item in derivation_input.utterances)
        text = "；".join(item.content for item in derivation_input.utterances)
        return MemoryDerivationResult(
            patches=(
                MemoryPatch(
                    operation=MemoryPatchOperation.ADD,
                    kind=MemoryItemKind.PROPOSAL,
                    canonical_text=text,
                    source_sequences=sequences,
                ),
            )
        )


def parse_memory_derivation_text(text: str) -> MemoryDerivationResult:
    try:
        payload = json.loads(text)
        return MemoryDerivationResult.model_validate(payload)
    except (json.JSONDecodeError, ValidationError, TypeError, ValueError) as error:
        raise ValueError("invalid closed memory derivation output") from error


def validate_memory_derivation_result(
    derivation_input: MemoryDerivationInput,
    result: MemoryDerivationResult,
    *,
    policy: MemoryPolicy,
) -> MemoryDerivationResult:
    if len(result.patches) > policy.max_patch_operations:
        raise ValueError("derivation patch bound exceeded")
    visible = {item.sequence for item in derivation_input.utterances}
    for patch in result.patches:
        if not set(patch.source_sequences).issubset(visible):
            raise ValueError(
                "patch provenance does not resolve to visible public utterances"
            )
        if len(patch.source_sequences) > policy.max_source_refs_per_item:
            raise ValueError("patch provenance bound exceeded")
        if (
            patch.canonical_text is not None
            and len(patch.canonical_text) > policy.max_canonical_text_codepoints
        ):
            raise ValueError("patch text bound exceeded")
    return result
