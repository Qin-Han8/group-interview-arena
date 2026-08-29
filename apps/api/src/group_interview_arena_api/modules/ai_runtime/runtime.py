import asyncio
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from uuid import UUID

from pydantic import UUID4, field_validator
from sqlalchemy import and_, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from group_interview_arena_api.db import (
    AiUtterance,
    DiscussionEvent,
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
    render_recent_discussion,
    select_recent_public_discussion,
)
from group_interview_arena_api.modules.ai_runtime.domain import (
    AiRuntimePersistenceError,
    ClosedDomainModel,
    FailGenerationCommand,
    GenerationContextError,
    GenerationFailureCode,
    GenerationRequestConflictError,
    GenerationRequestMetadata,
    GenerationRequestSnapshot,
    GenerationRequestStatus,
    GenerationStateError,
    Identifier,
    PersistUtteranceCommand,
    RequestGenerationCommand,
    StartGenerationCommand,
)
from group_interview_arena_api.modules.ai_runtime.generation import (
    GenerationExecutor,
    RawGenerationFailure,
    RuntimeGenerationInput,
    validate_generation_result,
)
from group_interview_arena_api.modules.ai_runtime.prompting import (
    AuthorizedGenerationContext,
    AuthorizedPersonaContext,
    AuthorizedQuestionContext,
    PromptRenderError,
    PromptTemplateAsset,
    render_authorized_prompt,
)
from group_interview_arena_api.modules.ai_runtime.service import (
    claim_generation_request,
    complete_generation_request,
    create_generation_request,
    fail_generation_request,
)
from group_interview_arena_api.modules.discussion_sessions.domain import (
    ACTIVE_PHASES,
    SessionStatus,
    StoredEvent,
)
from group_interview_arena_api.modules.discussion_sessions.public_events import (
    PublicEventProjectionError,
    project_public_events,
)
from group_interview_arena_api.modules.floor_control.domain import (
    FLOOR_ENABLED_PHASES,
    ParticipantActorKind,
)
from group_interview_arena_api.modules.question_personas.domain import (
    ConstraintItem,
    PriorityDimension,
    PrivateStanceDefinition,
    QuestionOption,
    StakeholderItem,
)


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
    request_metadata: GenerationRequestMetadata
    occurred_at: datetime

    @field_validator("occurred_at")
    @classmethod
    def validate_occurred_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamp must be timezone-aware")
        return value.astimezone(UTC)

    def request_command(self) -> RequestGenerationCommand:
        return RequestGenerationCommand(
            request_id=self.generation_request_id,
            session_id=self.session_id,
            participant_id=self.participant_id,
            floor_grant_id=self.floor_grant_id,
            prompt_version_id=self.prompt_version_id,
            provider_identifier=self.provider_identifier,
            model_identifier=self.model_identifier,
            request_metadata=self.request_metadata,
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


async def _load_recent_public_discussion(
    session: AsyncSession,
    *,
    session_id: UUID,
) -> tuple[PublicDiscussionUtterance, ...]:
    rows = tuple(
        (
            await session.scalars(
                select(DiscussionEvent)
                .where(
                    DiscussionEvent.session_id == session_id,
                    DiscussionEvent.event_type == "participant.utterance.created",
                )
                .order_by(DiscussionEvent.sequence.desc())
            )
        ).all()
    )
    stored_events = tuple(
        StoredEvent(
            event_version=row.event_version,
            event_type=row.event_type,
            session_id=row.session_id,
            sequence=row.sequence,
            occurred_at=row.occurred_at,
            causation_action_id=row.causation_action_id,
            payload=row.payload,
        )
        for row in rows
    )
    try:
        projected = await project_public_events(session, stored_events)
        participant_ids = {
            UUID(str(event.payload["participant_id"])) for event in projected
        }
        participants = {
            participant.id: participant
            for participant in (
                await session.scalars(
                    select(SessionParticipant).where(
                        SessionParticipant.session_id == session_id,
                        SessionParticipant.id.in_(participant_ids),
                    )
                )
            ).all()
        }
        items: list[PublicDiscussionUtterance] = []
        for event in projected:
            participant_id = UUID(str(event.payload["participant_id"]))
            participant = participants.get(participant_id)
            actor_kind = ParticipantActorKind(str(event.payload["actor_kind"]))
            phase = SessionStatus(str(event.payload["phase"]))
            content = event.payload["content"]
            if (
                event.schema_version != 1
                or event.type != "participant.utterance.created"
                or event.session_id != session_id
                or participant is None
                or participant.actor_kind != actor_kind.value
                or participant.seat_order <= 0
                or phase not in FLOOR_ENABLED_PHASES
                or not isinstance(content, str)
            ):
                raise ValueError("Durable public discussion fact is invalid.")
            items.append(
                PublicDiscussionUtterance(
                    sequence=event.sequence,
                    participant_id=participant_id,
                    actor_kind=actor_kind,
                    seat_order=participant.seat_order,
                    phase=phase,
                    content=content,
                )
            )
        return select_recent_public_discussion(tuple(items))
    except (PublicEventProjectionError, KeyError, TypeError, ValueError) as error:
        raise GenerationContextError("Recent public discussion is invalid.") from error


async def _assemble_generation_input(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    owner_id: UUID,
    command: GenerateAiUtteranceCommand,
) -> RuntimeGenerationInput:
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
                recent_public_discussion = await _load_recent_public_discussion(
                    session,
                    session_id=command.session_id,
                )
    except SQLAlchemyError as error:
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
    authorized_context = AuthorizedGenerationContext(
        session_id=aggregate.id,
        participant_id=participant.id,
        floor_grant_id=grant.id,
        phase=aggregate.status,
        question=question_context,
        persona=persona_context,
        private_stance=private_stance,
        phase_instruction=question.phase_prompts.get(aggregate.status, ""),
        recent_discussion=render_recent_discussion(recent_public_discussion),
        persona_behavior=render_persona_behavior(persona_context),
    )
    asset = PromptTemplateAsset(
        id=prompt.id,
        prompt_key=prompt.prompt_key,
        version_number=prompt.version_number,
        template_text=prompt.template_text,
    )
    return RuntimeGenerationInput(
        generation_request_id=command.generation_request_id,
        session_id=command.session_id,
        participant_id=command.participant_id,
        floor_grant_id=command.floor_grant_id,
        phase=aggregate.status,
        prompt_version_id=prompt.id,
        prompt_key=prompt.prompt_key,
        prompt_version_number=prompt.version_number,
        rendered_prompt=render_authorized_prompt(asset, authorized_context),
        provider_identifier=command.provider_identifier,
        model_identifier=command.model_identifier,
        configuration_version=command.request_metadata.configuration_version,
    )


async def _request_identity_exists(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    owner_id: UUID,
    command: GenerateAiUtteranceCommand,
) -> bool:
    try:
        async with session_factory() as session:
            request_id = await session.scalar(
                select(LlmGenerationRequest.id)
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
    except SQLAlchemyError as error:
        raise AiRuntimePersistenceError("Generation request lookup failed.") from error
    return request_id is not None


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
    try:
        request_exists = await _request_identity_exists(
            session_factory,
            owner_id=owner_id,
            command=command,
        )
    except AiRuntimePersistenceError:
        return _result(command, RuntimeGenerationOutcome.INTERNAL_ERROR)

    if not request_exists:
        try:
            generation_input = await _assemble_generation_input(
                session_factory,
                owner_id=owner_id,
                command=command,
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
                command=command.request_command(),
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
            generation_input = await _assemble_generation_input(
                session_factory,
                owner_id=owner_id,
                command=command,
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

    try:
        try:
            raw_result = await executor(generation_input)
        except Exception:
            raw_result = RawGenerationFailure(
                failure_code=GenerationFailureCode.INTERNAL_ERROR
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

        return _result(
            command,
            RuntimeGenerationOutcome.COMPLETED,
            request_status=completed.status,
            utterance_id=completed.utterance_id,
        )
    except asyncio.CancelledError:
        await _fail_generation(
            session_factory,
            owner_id=owner_id,
            command=command,
            failure_code=GenerationFailureCode.INTERNAL_ERROR,
        )
        raise
