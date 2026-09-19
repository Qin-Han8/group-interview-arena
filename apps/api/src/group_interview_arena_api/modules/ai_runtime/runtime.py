import asyncio
import logging
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from time import perf_counter
from typing import cast
from uuid import UUID

from pydantic import UUID4, field_validator
from sqlalchemy import and_, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from group_interview_arena_api.core.logging import log_event
from group_interview_arena_api.db import (
    AiUtterance,
    FloorGrant,
    LlmGenerationRequest,
    PersonaPrivateStance,
    PersonaTemplate,
    PromptVersion,
    QuestionPersonaAssignment,
    QuestionVersion,
    SessionParticipant,
    SimulationSession,
)
from group_interview_arena_api.modules.ai_runtime.conversation_context import (
    PublicDiscussionUtterance,
    render_persona_behavior,
    select_recent_public_discussion,
)
from group_interview_arena_api.modules.ai_runtime.domain import (
    AiRuntimePersistenceError,
    ClosedDomainModel,
    FailGenerationCommand,
    GenerationContextError,
    GenerationFailureCode,
    GenerationRequestConflictError,
    GenerationRequestMetadataAny,
    GenerationRequestMetadataV2,
    GenerationRequestSnapshot,
    GenerationRequestStatus,
    GenerationStateError,
    Identifier,
    PersistUtteranceCommand,
    RequestGenerationCommand,
    StartGenerationCommand,
    parse_generation_request_metadata,
)
from group_interview_arena_api.modules.ai_runtime.generation import (
    GenerationExecutor,
    ModelInvoker,
    RawGenerationFailure,
    RuntimeGenerationInput,
    validate_generation_result,
)
from group_interview_arena_api.modules.ai_runtime.prompting import (
    AuthorizedGenerationContext,
    AuthorizedPersonaContext,
    AuthorizedQuestionContext,
    MemoryBackedAuthorizedGenerationContext,
    PromptRenderError,
    PromptTemplateAsset,
    render_authorized_prompt,
    render_memory_backed_authorized_prompt,
)
from group_interview_arena_api.modules.ai_runtime.seed import (
    DISCUSSION_MEMORY_UPDATE_V2,
)
from group_interview_arena_api.modules.ai_runtime.service import (
    claim_generation_request,
    complete_generation_request,
    create_generation_request,
    fail_generation_request,
)
from group_interview_arena_api.modules.discussion_memory.application import (
    DiscussionMemoryPersistenceError,
    MemorySemanticProvenance,
    load_discussion_memory_projection,
    load_discussion_memory_projection_at_revision,
    load_public_memory_utterances,
    maintain_discussion_memory,
)
from group_interview_arena_api.modules.discussion_memory.derivation import (
    MemoryDerivationInput,
    MemoryDerivationResult,
    MemoryDerivationUnavailable,
    ModelBackedMemoryDeriver,
)
from group_interview_arena_api.modules.discussion_memory.domain import (
    DEFAULT_MEMORY_POLICY,
    DiscussionContextMode,
)
from group_interview_arena_api.modules.discussion_memory.working_context import (
    DISCUSSION_WORKING_CONTEXT_V1,
    DiscussionWorkingContextUnavailable,
    build_discussion_working_context,
    render_structured_discussion_memory,
    render_working_context_recent_discussion,
)
from group_interview_arena_api.modules.discussion_sessions.domain import (
    ACTIVE_PHASES,
    SessionStatus,
)
from group_interview_arena_api.modules.floor_control.domain import ParticipantActorKind
from group_interview_arena_api.modules.question_personas.domain import (
    ConstraintItem,
    PriorityDimension,
    PrivateStanceDefinition,
    QuestionOption,
    StakeholderItem,
)

logger = logging.getLogger(__name__)


class RuntimeGenerationOutcome(StrEnum):
    COMPLETED = "COMPLETED"
    COMPLETED_REPLAY = "COMPLETED_REPLAY"
    FAILED = "FAILED"
    FAILED_REPLAY = "FAILED_REPLAY"
    RECONCILIATION_REQUIRED = "RECONCILIATION_REQUIRED"
    CONTEXT_REJECTED = "CONTEXT_REJECTED"
    REQUEST_CONFLICT = "REQUEST_CONFLICT"
    STALE_RESULT = "STALE_RESULT"
    SUPERSEDED = "SUPERSEDED"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class GenerateAiUtteranceCommand(ClosedDomainModel):
    generation_request_id: UUID4
    utterance_id: UUID4
    session_id: UUID4
    participant_id: UUID4
    floor_grant_id: UUID4
    prompt_version_id: UUID4
    provider_identifier: Identifier
    model_identifier: Identifier
    request_metadata: GenerationRequestMetadataAny
    occurred_at: datetime

    @field_validator("occurred_at")
    @classmethod
    def validate_occurred_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamp must be timezone-aware")
        return value.astimezone(UTC)

    def request_command(
        self, request_metadata: GenerationRequestMetadataAny | None = None
    ) -> RequestGenerationCommand:
        return RequestGenerationCommand(
            request_id=self.generation_request_id,
            session_id=self.session_id,
            participant_id=self.participant_id,
            floor_grant_id=self.floor_grant_id,
            prompt_version_id=self.prompt_version_id,
            provider_identifier=self.provider_identifier,
            model_identifier=self.model_identifier,
            request_metadata=request_metadata or self.request_metadata,
            requested_at=self.occurred_at,
        )

    def start_command(self) -> StartGenerationCommand:
        return StartGenerationCommand(
            session_id=self.session_id,
            generation_request_id=self.generation_request_id,
            started_at=self.occurred_at,
        )


class GenerateAiUtteranceResult(ClosedDomainModel):
    generation_request_id: UUID4
    outcome: RuntimeGenerationOutcome
    request_status: GenerationRequestStatus | None = None
    utterance_id: UUID4 | None = None
    failure_code: GenerationFailureCode | None = None


def _result(
    command: GenerateAiUtteranceCommand,
    outcome: RuntimeGenerationOutcome,
    *,
    request_status: GenerationRequestStatus | None = None,
    utterance_id: UUID | None = None,
    failure_code: GenerationFailureCode | None = None,
) -> GenerateAiUtteranceResult:
    return GenerateAiUtteranceResult(
        generation_request_id=command.generation_request_id,
        outcome=outcome,
        request_status=request_status,
        utterance_id=utterance_id,
        failure_code=failure_code,
    )


def _terminal_result(
    command: GenerateAiUtteranceCommand,
    snapshot: GenerationRequestSnapshot,
) -> GenerateAiUtteranceResult | None:
    if snapshot.status is GenerationRequestStatus.COMPLETED:
        return _result(
            command,
            RuntimeGenerationOutcome.COMPLETED_REPLAY,
            request_status=snapshot.status,
            utterance_id=snapshot.utterance_id,
        )
    if snapshot.status is GenerationRequestStatus.FAILED:
        return _result(
            command,
            RuntimeGenerationOutcome.FAILED_REPLAY,
            request_status=snapshot.status,
            failure_code=snapshot.failure_code,
        )
    if snapshot.status is GenerationRequestStatus.RUNNING:
        return _result(
            command,
            RuntimeGenerationOutcome.RECONCILIATION_REQUIRED,
            request_status=snapshot.status,
        )
    return None


def _confirmed_failure_result(
    command: GenerateAiUtteranceCommand,
    failed: GenerationRequestSnapshot | None,
    *,
    confirmed_outcome: RuntimeGenerationOutcome,
) -> GenerateAiUtteranceResult:
    if failed is None or failed.status is not GenerationRequestStatus.FAILED:
        return _result(
            command,
            RuntimeGenerationOutcome.RECONCILIATION_REQUIRED,
            request_status=(None if failed is None else failed.status),
        )
    return _result(
        command,
        confirmed_outcome,
        request_status=failed.status,
        failure_code=failed.failure_code,
    )


def _priority_dimension(item: dict[str, object]) -> PriorityDimension:
    if set(item) != {"code", "weight"} or not isinstance(item["code"], str):
        raise ValueError("Persisted private stance shape is invalid.")
    weight = item["weight"]
    if isinstance(weight, bool):
        raise ValueError("Persisted private stance shape is invalid.")
    try:
        return PriorityDimension(
            code=item["code"],
            weight=Decimal(str(weight)),
        )
    except (InvalidOperation, TypeError, ValueError) as error:
        raise ValueError("Persisted private stance shape is invalid.") from error


async def _load_recent_public_discussion(  # pyright: ignore[reportUnusedFunction]
    session: AsyncSession, *, session_id: UUID
) -> tuple[PublicDiscussionUtterance, ...]:
    """Historical P1-5 raw-window seam over the safe public memory loader."""
    try:
        history = await load_public_memory_utterances(session, session_id=session_id)
    except DiscussionMemoryPersistenceError as error:
        raise GenerationContextError("Recent public discussion is invalid.") from error
    newest_first = tuple(
        PublicDiscussionUtterance(
            sequence=item.sequence,
            participant_id=item.participant_id,
            actor_kind=ParticipantActorKind(item.actor_kind),
            seat_order=item.seat_order,
            phase=SessionStatus(item.phase),
            content=item.content,
        )
        for item in reversed(history)
    )
    return select_recent_public_discussion(newest_first)


async def _assemble_generation_input(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    owner_id: UUID,
    command: GenerateAiUtteranceCommand,
    compaction_failed: bool = False,
    persisted_metadata: GenerationRequestMetadataV2 | None = None,
) -> tuple[RuntimeGenerationInput, GenerationRequestMetadataV2]:
    statement = (
        select(
            SimulationSession,
            FloorGrant,
            SessionParticipant,
            QuestionVersion,
            QuestionPersonaAssignment,
            PersonaTemplate,
            PersonaPrivateStance,
            PromptVersion,
        )
        .select_from(SimulationSession)
        .join(
            FloorGrant,
            and_(
                FloorGrant.session_id == SimulationSession.id,
                FloorGrant.id == command.floor_grant_id,
            ),
        )
        .join(
            SessionParticipant,
            and_(
                SessionParticipant.session_id == SimulationSession.id,
                SessionParticipant.id == command.participant_id,
            ),
        )
        .join(
            QuestionVersion,
            QuestionVersion.id == SimulationSession.question_version_id,
        )
        .join(
            QuestionPersonaAssignment,
            and_(
                QuestionPersonaAssignment.id
                == SessionParticipant.question_persona_assignment_id,
                QuestionPersonaAssignment.question_version_id == QuestionVersion.id,
            ),
        )
        .join(
            PersonaTemplate,
            PersonaTemplate.id == QuestionPersonaAssignment.persona_template_id,
        )
        .join(
            PersonaPrivateStance,
            PersonaPrivateStance.assignment_id == QuestionPersonaAssignment.id,
        )
        .join(PromptVersion, PromptVersion.id == command.prompt_version_id)
        .where(
            SimulationSession.id == command.session_id,
            SimulationSession.owner_user_id == owner_id,
            SimulationSession.current_floor_grant_id == command.floor_grant_id,
            SimulationSession.status.in_(item.value for item in ACTIVE_PHASES),
            SessionParticipant.actor_kind == "AI",
            SessionParticipant.participation_role == "CANDIDATE",
            SessionParticipant.availability == "AVAILABLE",
            FloorGrant.participant_id == command.participant_id,
            FloorGrant.phase == SimulationSession.status,
        )
    )
    try:
        async with session_factory() as session:
            async with session.begin():
                row = (await session.execute(statement)).one_or_none()
                public_history = await load_public_memory_utterances(
                    session, session_id=command.session_id
                )
                if persisted_metadata is None:
                    memory_projection = await load_discussion_memory_projection(
                        session, session_id=command.session_id
                    )
                else:
                    if (
                        persisted_metadata.working_context_version
                        != DISCUSSION_WORKING_CONTEXT_V1
                    ):
                        raise GenerationContextError(
                            "Persisted Working Context version is unsupported."
                        )
                    if (
                        persisted_metadata.context_mode
                        is DiscussionContextMode.MEMORY_WITH_RAW_TAIL
                    ):
                        memory_projection = (
                            await load_discussion_memory_projection_at_revision(
                                session,
                                session_id=command.session_id,
                                revision=persisted_metadata.memory_revision,
                            )
                        )
                        if (
                            memory_projection.source_through_sequence
                            != persisted_metadata.memory_source_through_sequence
                        ):
                            raise GenerationContextError(
                                "Persisted memory cursor does not match its revision."
                            )
                        public_history = tuple(
                            item
                            for item in public_history
                            if (
                                memory_projection.source_through_sequence
                                < item.sequence
                                <= persisted_metadata.context_source_through_sequence
                            )
                        )
                        if (
                            persisted_metadata.context_source_through_sequence
                            > memory_projection.source_through_sequence
                            and (
                                not public_history
                                or public_history[-1].sequence
                                != persisted_metadata.context_source_through_sequence
                            )
                        ):
                            raise GenerationContextError(
                                "Persisted raw-tail cursor is unavailable."
                            )
                        compaction_failed = False
                    else:
                        if (
                            persisted_metadata.memory_revision != 0
                            or persisted_metadata.memory_source_through_sequence != 0
                        ):
                            raise GenerationContextError(
                                "Persisted raw fallback cannot reference memory."
                            )
                        memory_projection = (
                            await load_discussion_memory_projection_at_revision(
                                session,
                                session_id=command.session_id,
                                revision=0,
                            )
                        )
                        public_history = tuple(
                            item
                            for item in public_history
                            if item.sequence
                            <= persisted_metadata.context_source_through_sequence
                        )
                        if persisted_metadata.context_source_through_sequence > 0 and (
                            not public_history
                            or public_history[-1].sequence
                            != persisted_metadata.context_source_through_sequence
                        ):
                            raise GenerationContextError(
                                "Persisted raw fallback cursor is unavailable."
                            )
                        compaction_failed = True
    except (DiscussionMemoryPersistenceError, SQLAlchemyError) as error:
        raise AiRuntimePersistenceError(
            "Generation context transaction failed."
        ) from error
    if row is None:
        raise GenerationContextError("Generation context is unavailable.")

    (
        aggregate,
        grant,
        participant,
        question,
        assignment,
        persona,
        stance,
        prompt,
    ) = row
    if (
        prompt.published_at > command.occurred_at
        or (prompt.retired_at is not None and prompt.retired_at <= command.occurred_at)
        or question.published_at is None
        or grant.participant_id != participant.id
        or assignment.id != participant.question_persona_assignment_id
    ):
        raise GenerationContextError("Generation context is unavailable.")

    try:
        working_context = build_discussion_working_context(
            projection=memory_projection,
            complete_public_history=public_history,
            phase=aggregate.status,
            now=command.occurred_at,
            phase_deadline_at=aggregate.phase_deadline_at,
            policy=DEFAULT_MEMORY_POLICY,
            compaction_failed=compaction_failed,
        )
    except DiscussionWorkingContextUnavailable as error:
        raise GenerationContextError(
            "Discussion working context is unavailable."
        ) from error

    question_context = AuthorizedQuestionContext(
        version_id=question.id,
        title=question.title,
        question_type_code=question.question_type_code,
        background_domain_code=question.background_domain_code,
        difficulty_code=question.difficulty_code,
        scenario=question.scenario,
        objective=question.objective,
        hard_constraints=tuple(
            ConstraintItem.model_validate(item) for item in question.hard_constraints
        ),
        soft_constraints=tuple(
            ConstraintItem.model_validate(item) for item in question.soft_constraints
        ),
        stakeholders=tuple(
            StakeholderItem.model_validate(item) for item in question.stakeholders
        ),
        options=tuple(QuestionOption.model_validate(item) for item in question.options),
    )
    persona_context = AuthorizedPersonaContext(
        assignment_id=assignment.id,
        persona_template_id=persona.id,
        code=persona.code,
        display_name=persona.display_name,
        speech_style_code=persona.speech_style_code,
        initiative=persona.initiative,
        interrupt_tendency=persona.interrupt_tendency,
        average_turn_seconds=persona.average_turn_seconds,
        stance_stability=persona.stance_stability,
        persuasion_threshold=persona.persuasion_threshold,
        novel_idea_rate=persona.novel_idea_rate,
        summary_tendency=persona.summary_tendency,
        time_awareness=persona.time_awareness,
        detail_focus=persona.detail_focus,
        cooperation=persona.cooperation,
        support_user_bias=persona.support_user_bias,
        error_rate=persona.error_rate,
        off_topic_rate=persona.off_topic_rate,
    )
    private_stance = PrivateStanceDefinition(
        initial_position=stance.initial_position,
        priority_dimensions=tuple(
            _priority_dimension(item) for item in stance.priority_dimensions
        ),
        concession_conditions=tuple(stance.concession_conditions),
        private_information=stance.private_information,
        red_lines=tuple(stance.red_lines),
        preferred_group_role=stance.preferred_group_role,
    )
    context_values = dict(
        session_id=aggregate.id,
        participant_id=participant.id,
        floor_grant_id=grant.id,
        phase=aggregate.status,
        question=question_context,
        persona=persona_context,
        private_stance=private_stance,
        phase_instruction=question.phase_prompts.get(aggregate.status, ""),
        recent_discussion=render_working_context_recent_discussion(working_context),
        persona_behavior=render_persona_behavior(persona_context),
    )
    asset = PromptTemplateAsset(
        id=prompt.id,
        prompt_key=prompt.prompt_key,
        version_number=prompt.version_number,
        template_text=prompt.template_text,
    )
    if prompt.prompt_key == "AI_CANDIDATE_TURN" and prompt.version_number >= 3:
        rendered_prompt = render_memory_backed_authorized_prompt(
            asset,
            MemoryBackedAuthorizedGenerationContext(
                **context_values,
                discussion_memory=render_structured_discussion_memory(working_context),
                time_remaining_seconds=(
                    "UNKNOWN"
                    if working_context.remaining_time_seconds is None
                    else str(working_context.remaining_time_seconds)
                ),
            ),
        )
    else:
        rendered_prompt = render_authorized_prompt(
            asset, AuthorizedGenerationContext(**context_values)
        )
    generation_input = RuntimeGenerationInput(
        generation_request_id=command.generation_request_id,
        session_id=command.session_id,
        participant_id=command.participant_id,
        floor_grant_id=command.floor_grant_id,
        phase=aggregate.status,
        prompt_version_id=prompt.id,
        prompt_key=prompt.prompt_key,
        prompt_version_number=prompt.version_number,
        rendered_prompt=rendered_prompt,
        provider_identifier=command.provider_identifier,
        model_identifier=command.model_identifier,
        configuration_version=(
            persisted_metadata.configuration_version
            if persisted_metadata is not None
            else command.request_metadata.configuration_version
        ),
    )
    metadata = GenerationRequestMetadataV2(
        configuration_version=(
            persisted_metadata.configuration_version
            if persisted_metadata is not None
            else command.request_metadata.configuration_version
        ),
        working_context_version=working_context.working_context_version,
        context_mode=working_context.context_mode,
        memory_revision=working_context.memory_revision,
        memory_source_through_sequence=working_context.memory_source_through_sequence,
        context_source_through_sequence=working_context.context_source_through_sequence,
    )
    if persisted_metadata is not None and metadata != persisted_metadata:
        raise GenerationContextError(
            "Recovered Working Context does not match persisted provenance."
        )
    return generation_input, metadata


class _UnavailableMemoryDeriver:
    def derive(self, _input: MemoryDerivationInput) -> MemoryDerivationResult:
        raise MemoryDerivationUnavailable("shared semantic transport is unavailable")


async def _maintain_for_generation(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    command: GenerateAiUtteranceCommand,
    executor: GenerationExecutor,
) -> bool:
    invoke = getattr(executor, "invoke", None)
    if callable(invoke):
        deriver = ModelBackedMemoryDeriver(
            invoker=cast(ModelInvoker, executor),
            template_text=DISCUSSION_MEMORY_UPDATE_V2.template_text,
            provider_identifier=command.provider_identifier,
            model_identifier=command.model_identifier,
            configuration_version=command.request_metadata.configuration_version,
        )
        provenance = MemorySemanticProvenance(
            prompt_version_id=DISCUSSION_MEMORY_UPDATE_V2.id,
            provider_identifier=command.provider_identifier,
            model_identifier=command.model_identifier,
            configuration_version=command.request_metadata.configuration_version,
        )
    else:
        deriver = _UnavailableMemoryDeriver()
        provenance = MemorySemanticProvenance()
    try:
        await maintain_discussion_memory(
            session_factory,
            session_id=command.session_id,
            deriver=deriver,
            provenance=provenance,
            policy=DEFAULT_MEMORY_POLICY,
            now=command.occurred_at,
        )
        return False
    except DiscussionMemoryPersistenceError, MemoryDerivationUnavailable, ValueError:
        return True


async def _load_request_identity_metadata(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    owner_id: UUID,
    command: GenerateAiUtteranceCommand,
) -> GenerationRequestMetadataAny | None:
    try:
        async with session_factory() as session:
            metadata = await session.scalar(
                select(LlmGenerationRequest.request_metadata)
                .join(
                    SimulationSession,
                    SimulationSession.id == LlmGenerationRequest.session_id,
                )
                .where(
                    LlmGenerationRequest.id == command.generation_request_id,
                    LlmGenerationRequest.session_id == command.session_id,
                    SimulationSession.owner_user_id == owner_id,
                )
            )
    except (SQLAlchemyError, ValueError) as error:
        raise AiRuntimePersistenceError("Generation request lookup failed.") from error
    if metadata is None:
        return None
    try:
        return parse_generation_request_metadata(metadata)
    except ValueError as error:
        raise AiRuntimePersistenceError(
            "Generation request metadata is invalid."
        ) from error


async def _fail_generation(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    owner_id: UUID,
    command: GenerateAiUtteranceCommand,
    failure_code: GenerationFailureCode,
) -> GenerationRequestSnapshot | None:
    try:
        async with session_factory() as session:
            return await fail_generation_request(
                session,
                owner_id=owner_id,
                command=FailGenerationCommand(
                    session_id=command.session_id,
                    generation_request_id=command.generation_request_id,
                    failure_code=failure_code,
                    failed_at=command.occurred_at,
                ),
            )
    except (
        AiRuntimePersistenceError,
        GenerationContextError,
        GenerationRequestConflictError,
        GenerationStateError,
    ):
        return None


async def _existing_floor_utterance(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    session_id: UUID,
    floor_grant_id: UUID,
) -> UUID | None:
    try:
        async with session_factory() as session:
            return await session.scalar(
                select(AiUtterance.id).where(
                    AiUtterance.session_id == session_id,
                    AiUtterance.floor_grant_id == floor_grant_id,
                )
            )
    except SQLAlchemyError:
        return None


async def generate_ai_utterance(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    owner_id: UUID,
    command: GenerateAiUtteranceCommand,
    executor: GenerationExecutor,
) -> GenerateAiUtteranceResult:
    generation_input: RuntimeGenerationInput | None = None
    effective_metadata: GenerationRequestMetadataAny = command.request_metadata
    try:
        stored_metadata = await _load_request_identity_metadata(
            session_factory,
            owner_id=owner_id,
            command=command,
        )
    except AiRuntimePersistenceError:
        return _result(command, RuntimeGenerationOutcome.INTERNAL_ERROR)
    request_exists = stored_metadata is not None
    if stored_metadata is not None:
        effective_metadata = stored_metadata

    if not request_exists:
        try:
            compaction_failed = await _maintain_for_generation(
                session_factory, command=command, executor=executor
            )
            generation_input, effective_metadata = await _assemble_generation_input(
                session_factory,
                owner_id=owner_id,
                command=command,
                compaction_failed=compaction_failed,
            )
        except GenerationContextError, PromptRenderError, ValueError:
            return _result(command, RuntimeGenerationOutcome.CONTEXT_REJECTED)
        except AiRuntimePersistenceError:
            return _result(command, RuntimeGenerationOutcome.INTERNAL_ERROR)

    try:
        async with session_factory() as session:
            request = await create_generation_request(
                session,
                owner_id=owner_id,
                command=command.request_command(effective_metadata),
            )
    except GenerationRequestConflictError:
        return _result(command, RuntimeGenerationOutcome.REQUEST_CONFLICT)
    except GenerationContextError:
        return _result(command, RuntimeGenerationOutcome.CONTEXT_REJECTED)
    except AiRuntimePersistenceError:
        return _result(command, RuntimeGenerationOutcome.INTERNAL_ERROR)

    terminal = _terminal_result(command, request)
    if terminal is not None:
        return terminal

    if generation_input is None:
        try:
            generation_input, _ = await _assemble_generation_input(
                session_factory,
                owner_id=owner_id,
                command=command,
                persisted_metadata=(
                    effective_metadata
                    if isinstance(effective_metadata, GenerationRequestMetadataV2)
                    else None
                ),
            )
        except GenerationContextError:
            failed = await _fail_generation(
                session_factory,
                owner_id=owner_id,
                command=command,
                failure_code=GenerationFailureCode.INTERNAL_ERROR,
            )
            return _confirmed_failure_result(
                command,
                failed,
                confirmed_outcome=RuntimeGenerationOutcome.STALE_RESULT,
            )
        except PromptRenderError, ValueError:
            failed = await _fail_generation(
                session_factory,
                owner_id=owner_id,
                command=command,
                failure_code=GenerationFailureCode.INVALID_OUTPUT,
            )
            return _confirmed_failure_result(
                command,
                failed,
                confirmed_outcome=RuntimeGenerationOutcome.FAILED,
            )
        except AiRuntimePersistenceError:
            return _result(command, RuntimeGenerationOutcome.INTERNAL_ERROR)

    try:
        async with session_factory() as session:
            claim = await claim_generation_request(
                session,
                owner_id=owner_id,
                command=command.start_command(),
            )
    except GenerationContextError:
        return _result(command, RuntimeGenerationOutcome.CONTEXT_REJECTED)
    except AiRuntimePersistenceError:
        return _result(command, RuntimeGenerationOutcome.INTERNAL_ERROR)

    if not claim.claimed:
        terminal = _terminal_result(command, claim.snapshot)
        if terminal is not None:
            return terminal
        return _result(
            command,
            RuntimeGenerationOutcome.RECONCILIATION_REQUIRED,
            request_status=claim.snapshot.status,
        )

    provider_started = perf_counter()
    log_event(
        logger,
        logging.INFO,
        "ai.generation.started",
        session_id=str(command.session_id),
        generation_request_id=str(command.generation_request_id),
        floor_grant_id=str(command.floor_grant_id),
        participant_id=str(command.participant_id),
    )
    try:
        try:
            raw_result = await executor(generation_input)
        except Exception:
            raw_result = RawGenerationFailure(
                failure_code=GenerationFailureCode.INTERNAL_ERROR
            )
        provider_duration_ms = (perf_counter() - provider_started) * 1_000
        log_event(
            logger,
            logging.INFO,
            "ai.provider.completed",
            duration_ms=provider_duration_ms,
            session_id=str(command.session_id),
            generation_request_id=str(command.generation_request_id),
            floor_grant_id=str(command.floor_grant_id),
            participant_id=str(command.participant_id),
        )
        validated = validate_generation_result(raw_result)
        if validated.failure_code is not None:
            failed = await _fail_generation(
                session_factory,
                owner_id=owner_id,
                command=command,
                failure_code=validated.failure_code,
            )
            return _confirmed_failure_result(
                command,
                failed,
                confirmed_outcome=RuntimeGenerationOutcome.FAILED,
            )
        assert validated.content is not None

        try:
            async with session_factory() as session:
                completed = await complete_generation_request(
                    session,
                    owner_id=owner_id,
                    command=PersistUtteranceCommand(
                        utterance_id=command.utterance_id,
                        session_id=command.session_id,
                        generation_request_id=command.generation_request_id,
                        content=validated.content,
                        persisted_at=command.occurred_at,
                    ),
                )
        except GenerationContextError:
            failed = await _fail_generation(
                session_factory,
                owner_id=owner_id,
                command=command,
                failure_code=GenerationFailureCode.INTERNAL_ERROR,
            )
            return _confirmed_failure_result(
                command,
                failed,
                confirmed_outcome=RuntimeGenerationOutcome.STALE_RESULT,
            )
        except GenerationRequestConflictError:
            return _result(command, RuntimeGenerationOutcome.REQUEST_CONFLICT)
        except AiRuntimePersistenceError:
            winning_utterance_id = await _existing_floor_utterance(
                session_factory,
                session_id=command.session_id,
                floor_grant_id=command.floor_grant_id,
            )
            failed = await _fail_generation(
                session_factory,
                owner_id=owner_id,
                command=command,
                failure_code=GenerationFailureCode.INTERNAL_ERROR,
            )
            if winning_utterance_id is not None:
                return _confirmed_failure_result(
                    command,
                    failed,
                    confirmed_outcome=RuntimeGenerationOutcome.SUPERSEDED,
                )
            return _confirmed_failure_result(
                command,
                failed,
                confirmed_outcome=RuntimeGenerationOutcome.FAILED,
            )

        result = _result(
            command,
            RuntimeGenerationOutcome.COMPLETED,
            request_status=completed.status,
            utterance_id=completed.utterance_id,
        )
        log_event(
            logger,
            logging.INFO,
            "ai.utterance.committed",
            duration_ms=(perf_counter() - provider_started) * 1_000,
            session_id=str(command.session_id),
            generation_request_id=str(command.generation_request_id),
            floor_grant_id=str(command.floor_grant_id),
            participant_id=str(command.participant_id),
        )
        return result
    except asyncio.CancelledError:
        await _fail_generation(
            session_factory,
            owner_id=owner_id,
            command=command,
            failure_code=GenerationFailureCode.INTERNAL_ERROR,
        )
        raise
