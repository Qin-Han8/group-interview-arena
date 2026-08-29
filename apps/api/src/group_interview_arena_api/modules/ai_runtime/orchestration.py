from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid5

from pydantic import UUID4
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from group_interview_arena_api.db import (
    AiUtterance,
    FloorGrant,
    FloorRelease,
    LlmGenerationRequest,
    PromptVersion,
    SessionAction,
    SessionParticipant,
    SimulationSession,
)
from group_interview_arena_api.modules.ai_runtime.domain import (
    ClosedDomainModel,
    GenerationFailureCode,
    GenerationRequestMetadata,
    GenerationRequestStatus,
)
from group_interview_arena_api.modules.ai_runtime.generation import GenerationProvider
from group_interview_arena_api.modules.ai_runtime.runtime import (
    GenerateAiUtteranceCommand,
    RuntimeGenerationOutcome,
    generate_ai_utterance,
)
from group_interview_arena_api.modules.discussion_sessions.domain import SessionStatus
from group_interview_arena_api.modules.discussion_sessions.service import (
    ActionIdConflictError,
    SessionNotFoundError,
    SessionPersistenceError,
)
from group_interview_arena_api.modules.floor_control.domain import (
    FLOOR_ENABLED_PHASES,
    FloorReleaseReason,
    InvalidFloorStateError,
    ParticipantActorKind,
    ParticipantAvailability,
    ParticipationRole,
    ReleaseFloorCommand,
    StaleFloorDecisionError,
)
from group_interview_arena_api.modules.floor_control.progression import (
    ReleasedFloorProof,
    SchedulerCheckpointIdentities,
    SchedulerCheckpointOutcome,
    drive_scheduler_checkpoint,
)
from group_interview_arena_api.modules.floor_control.scheduler import (
    SchedulerPolicy,
)
from group_interview_arena_api.modules.floor_control.service import (
    apply_floor_command,
)

_AUTOMATIC_TURN_NAMESPACE = UUID("b86d84b9-05fc-5d65-8170-b1158545c91f")


class _CheckpointResolution(StrEnum):
    READY_TO_APPLY = "ready_to_apply"
    EXPECTED_DURABLE_RESULT = "expected_durable_result"
    STATE_CHANGED = "state_changed"
    RECONCILIATION_REQUIRED = "reconciliation_required"


class SingleAiTurnOutcome(StrEnum):
    WAITING_FOR_HUMAN = "waiting_for_human"
    NO_CURRENT_WORK = "no_current_work"
    NOT_APPLICABLE = "not_applicable"
    NEXT_AI_GRANTED = "next_ai_granted"
    NEXT_HUMAN_GRANTED = "next_human_granted"
    NO_GRANT = "no_grant"
    INTERVENTION_REQUESTED = "intervention_requested"
    RECONCILIATION_REQUIRED = "reconciliation_required"
    STATE_CHANGED = "state_changed"


class AutomaticTurnIdentities(ClosedDomainModel):
    generation_request_id: UUID4
    utterance_id: UUID4
    release_action_id: UUID4
    schedule_action_id: UUID4
    decision_id: UUID4
    next_floor_grant_id: UUID4
    intervention_id: UUID4


class SingleAiTurnResult(ClosedDomainModel):
    outcome: SingleAiTurnOutcome
    processed_floor_grant_id: UUID4 | None = None
    generation_request_id: UUID4 | None = None
    utterance_id: UUID4 | None = None
    release_action_id: UUID4 | None = None
    schedule_action_id: UUID4 | None = None
    decision_id: UUID4 | None = None
    next_floor_grant_id: UUID4 | None = None
    next_participant_id: UUID4 | None = None
    intervention_id: UUID4 | None = None
    runtime_outcome: RuntimeGenerationOutcome | None = None
    failure_code: GenerationFailureCode | None = None


def _deterministic_uuid4(name: str) -> UUID:
    derived = uuid5(_AUTOMATIC_TURN_NAMESPACE, name)
    return UUID(bytes=derived.bytes, version=4)


def derive_automatic_turn_identities(
    *,
    session_id: UUID,
    floor_grant_id: UUID,
) -> AutomaticTurnIdentities:
    prefix = f"single-ai-turn:{session_id}:{floor_grant_id}"

    return AutomaticTurnIdentities(
        generation_request_id=_deterministic_uuid4(f"{prefix}:generation-request"),
        utterance_id=_deterministic_uuid4(f"{prefix}:utterance"),
        release_action_id=_deterministic_uuid4(f"{prefix}:release-action"),
        schedule_action_id=_deterministic_uuid4(f"{prefix}:schedule-action"),
        decision_id=_deterministic_uuid4(f"{prefix}:decision"),
        next_floor_grant_id=_deterministic_uuid4(f"{prefix}:next-floor-grant"),
        intervention_id=_deterministic_uuid4(f"{prefix}:intervention"),
    )


async def _select_effective_prompt_version(
    session: AsyncSession,
    *,
    prompt_key: str,
    purpose_code: str,
    effective_at: datetime,
) -> PromptVersion | None:
    return await session.scalar(
        select(PromptVersion)
        .where(
            PromptVersion.prompt_key == prompt_key,
            PromptVersion.purpose_code == purpose_code,
            PromptVersion.published_at <= effective_at,
            or_(
                PromptVersion.retired_at.is_(None),
                PromptVersion.retired_at > effective_at,
            ),
        )
        .order_by(PromptVersion.version_number.desc(), PromptVersion.id.asc())
        .limit(1)
    )


async def _resolve_release_checkpoint(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    owner_id: UUID,
    session_id: UUID,
    floor_grant_id: UUID,
    action_id: UUID,
    reason: FloorReleaseReason,
) -> _CheckpointResolution:
    async with session_factory() as session:
        release = await session.get(FloorRelease, floor_grant_id)
        release_action = await session.get(SessionAction, (session_id, action_id))
        release_matches = bool(
            release is not None
            and release.session_id == session_id
            and release.causation_action_id == action_id
            and release.reason_code == reason
        )
        if release_matches:
            if (
                release_action is not None
                and release_action.command_version == 1
                and release_action.command_type == "floor.release"
            ):
                return _CheckpointResolution.EXPECTED_DURABLE_RESULT
            return _CheckpointResolution.RECONCILIATION_REQUIRED
        if release is not None:
            return _CheckpointResolution.STATE_CHANGED
        simulation_session = await session.scalar(
            select(SimulationSession).where(
                SimulationSession.id == session_id,
                SimulationSession.owner_user_id == owner_id,
            )
        )
        grant = await session.get(FloorGrant, floor_grant_id)
        if (
            simulation_session is None
            or simulation_session.current_floor_grant_id != floor_grant_id
            or SessionStatus(simulation_session.status) not in FLOOR_ENABLED_PHASES
            or (
                grant is not None
                and (
                    grant.session_id != session_id
                    or simulation_session.status != grant.phase
                )
            )
        ):
            return _CheckpointResolution.STATE_CHANGED
        return _CheckpointResolution.READY_TO_APPLY


async def _classify_original_grant_after_runtime_stop(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    owner_id: UUID,
    session_id: UUID,
    floor_grant_id: UUID,
    expected_phase: SessionStatus,
) -> SingleAiTurnOutcome:
    async with session_factory() as session:
        simulation_session = await session.scalar(
            select(SimulationSession).where(
                SimulationSession.id == session_id,
                SimulationSession.owner_user_id == owner_id,
            )
        )
        if (
            simulation_session is None
            or simulation_session.current_floor_grant_id != floor_grant_id
            or simulation_session.status != expected_phase
            or SessionStatus(simulation_session.status) not in FLOOR_ENABLED_PHASES
        ):
            return SingleAiTurnOutcome.STATE_CHANGED
        return SingleAiTurnOutcome.RECONCILIATION_REQUIRED


async def _release_terminal_grant(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    owner_id: UUID,
    session_id: UUID,
    floor_grant_id: UUID,
    action_id: UUID,
    reason: FloorReleaseReason,
) -> _CheckpointResolution:
    initial_resolution = await _resolve_release_checkpoint(
        session_factory,
        owner_id=owner_id,
        session_id=session_id,
        floor_grant_id=floor_grant_id,
        action_id=action_id,
        reason=reason,
    )
    if initial_resolution is not _CheckpointResolution.READY_TO_APPLY:
        return initial_resolution

    async with session_factory() as session:
        simulation_session = await session.scalar(
            select(SimulationSession).where(
                SimulationSession.id == session_id,
                SimulationSession.owner_user_id == owner_id,
            )
        )
        grant = await session.get(FloorGrant, floor_grant_id)
        if (
            simulation_session is None
            or simulation_session.current_floor_grant_id != floor_grant_id
            or SessionStatus(simulation_session.status) not in FLOOR_ENABLED_PHASES
        ):
            return _CheckpointResolution.STATE_CHANGED
        if grant is None or grant.session_id != session_id:
            return _CheckpointResolution.RECONCILIATION_REQUIRED
        if simulation_session.status != grant.phase:
            return _CheckpointResolution.STATE_CHANGED
        command = ReleaseFloorCommand(
            session_id=session_id,
            action_id=action_id,
            grant_id=floor_grant_id,
            expected_phase=SessionStatus(simulation_session.status),
            expected_last_sequence=simulation_session.last_sequence,
            reason=reason,
        )

    try:
        async with session_factory() as session:
            await apply_floor_command(session, owner_id=owner_id, command=command)
    except (
        ActionIdConflictError,
        InvalidFloorStateError,
        SessionNotFoundError,
        SessionPersistenceError,
        StaleFloorDecisionError,
    ):
        pass

    return await _resolve_release_checkpoint(
        session_factory,
        owner_id=owner_id,
        session_id=session_id,
        floor_grant_id=floor_grant_id,
        action_id=action_id,
        reason=reason,
    )


async def _drive_scheduler_checkpoint(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    owner_id: UUID,
    session_id: UUID,
    processed_floor_grant_id: UUID,
    identities: AutomaticTurnIdentities,
    scheduling_policy: SchedulerPolicy,
) -> SingleAiTurnResult:
    checkpoint = await drive_scheduler_checkpoint(
        session_factory,
        owner_id=owner_id,
        session_id=session_id,
        released_floor=ReleasedFloorProof(
            floor_grant_id=processed_floor_grant_id,
            release_action_id=identities.release_action_id,
            release_command_type="floor.release",
            allowed_reasons=frozenset(
                {
                    FloorReleaseReason.SPEAKER_FINISHED,
                    FloorReleaseReason.INTERRUPTED,
                }
            ),
        ),
        identities=SchedulerCheckpointIdentities(
            schedule_action_id=identities.schedule_action_id,
            decision_id=identities.decision_id,
            next_floor_grant_id=identities.next_floor_grant_id,
            intervention_id=identities.intervention_id,
        ),
        scheduling_policy=scheduling_policy,
    )
    outcome = SingleAiTurnOutcome(checkpoint.outcome.value)
    return SingleAiTurnResult(
        outcome=outcome,
        processed_floor_grant_id=processed_floor_grant_id,
        schedule_action_id=(
            identities.schedule_action_id
            if checkpoint.outcome
            in {
                SchedulerCheckpointOutcome.NEXT_AI_GRANTED,
                SchedulerCheckpointOutcome.NEXT_HUMAN_GRANTED,
                SchedulerCheckpointOutcome.NO_GRANT,
                SchedulerCheckpointOutcome.INTERVENTION_REQUESTED,
            }
            else None
        ),
        decision_id=(
            identities.decision_id
            if checkpoint.outcome
            in {
                SchedulerCheckpointOutcome.NEXT_AI_GRANTED,
                SchedulerCheckpointOutcome.NEXT_HUMAN_GRANTED,
                SchedulerCheckpointOutcome.NO_GRANT,
                SchedulerCheckpointOutcome.INTERVENTION_REQUESTED,
            }
            else None
        ),
        next_floor_grant_id=checkpoint.next_floor_grant_id,
        next_participant_id=checkpoint.next_participant_id,
        intervention_id=checkpoint.intervention_id,
    )


async def _find_resumable_release(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    owner_id: UUID,
    session_id: UUID,
) -> tuple[UUID, AutomaticTurnIdentities] | None:
    async with session_factory() as session:
        owns_session = await session.scalar(
            select(SimulationSession.id).where(
                SimulationSession.id == session_id,
                SimulationSession.owner_user_id == owner_id,
            )
        )
        if owns_session is None:
            return None
        row = (
            await session.execute(
                select(FloorRelease, FloorGrant)
                .join(
                    FloorGrant,
                    and_(
                        FloorGrant.id == FloorRelease.grant_id,
                        FloorGrant.session_id == FloorRelease.session_id,
                    ),
                )
                .where(FloorRelease.session_id == session_id)
                .order_by(FloorRelease.released_at.desc(), FloorRelease.grant_id.desc())
                .limit(1)
            )
        ).one_or_none()
        if row is None:
            return None
        release, grant = row
        identities = derive_automatic_turn_identities(
            session_id=session_id,
            floor_grant_id=grant.id,
        )
        release_action = await session.get(
            SessionAction,
            (session_id, identities.release_action_id),
        )
        if not (
            release.causation_action_id == identities.release_action_id
            and release.reason_code
            in {
                FloorReleaseReason.SPEAKER_FINISHED,
                FloorReleaseReason.INTERRUPTED,
            }
            and release_action is not None
            and release_action.command_version == 1
            and release_action.command_type == "floor.release"
        ):
            return None
        request = await session.get(
            LlmGenerationRequest,
            identities.generation_request_id,
        )
        if request is None or not (
            request.session_id == session_id
            and request.floor_grant_id == grant.id
            and request.participant_id == grant.participant_id
        ):
            return None
        if release.reason_code == FloorReleaseReason.SPEAKER_FINISHED:
            utterance = await session.get(AiUtterance, identities.utterance_id)
            deterministic_success = bool(
                request.status == GenerationRequestStatus.COMPLETED
                and utterance is not None
                and utterance.generation_request_id == request.id
                and utterance.floor_grant_id == grant.id
            )
            if not deterministic_success:
                winning_utterance = await session.scalar(
                    select(AiUtterance).where(
                        AiUtterance.session_id == session_id,
                        AiUtterance.floor_grant_id == grant.id,
                    )
                )
                winning_request = (
                    None
                    if winning_utterance is None
                    else await session.get(
                        LlmGenerationRequest,
                        winning_utterance.generation_request_id,
                    )
                )
                if not (
                    request.status == GenerationRequestStatus.FAILED
                    and winning_utterance is not None
                    and winning_utterance.participant_id == grant.participant_id
                    and winning_request is not None
                    and winning_request.session_id == session_id
                    and winning_request.participant_id == grant.participant_id
                    and winning_request.floor_grant_id == grant.id
                    and winning_request.status == GenerationRequestStatus.COMPLETED
                ):
                    return None
        elif request.status != GenerationRequestStatus.FAILED:
            return None
        return grant.id, identities


async def has_resumable_ai_work(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    owner_id: UUID,
    session_id: UUID,
) -> bool:
    return (
        await _find_resumable_release(
            session_factory,
            owner_id=owner_id,
            session_id=session_id,
        )
        is not None
    )


async def drive_single_ai_turn(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    owner_id: UUID,
    session_id: UUID,
    provider: GenerationProvider,
    provider_identifier: str,
    model_identifier: str,
    configuration_version: str,
    scheduling_policy: SchedulerPolicy,
) -> SingleAiTurnResult:
    async with session_factory() as session:
        simulation_session = await session.scalar(
            select(SimulationSession).where(
                SimulationSession.id == session_id,
                SimulationSession.owner_user_id == owner_id,
            )
        )
        if simulation_session is None:
            return SingleAiTurnResult(outcome=SingleAiTurnOutcome.NO_CURRENT_WORK)
        if SessionStatus(simulation_session.status) not in FLOOR_ENABLED_PHASES:
            return SingleAiTurnResult(outcome=SingleAiTurnOutcome.NOT_APPLICABLE)
        if simulation_session.current_floor_grant_id is None:
            resumable = await _find_resumable_release(
                session_factory,
                owner_id=owner_id,
                session_id=session_id,
            )
            if resumable is None:
                return SingleAiTurnResult(outcome=SingleAiTurnOutcome.NO_CURRENT_WORK)
            released_grant_id, released_identities = resumable
            return await _drive_scheduler_checkpoint(
                session_factory,
                owner_id=owner_id,
                session_id=session_id,
                processed_floor_grant_id=released_grant_id,
                identities=released_identities,
                scheduling_policy=scheduling_policy,
            )

        grant = await session.scalar(
            select(FloorGrant).where(
                FloorGrant.id == simulation_session.current_floor_grant_id,
                FloorGrant.session_id == session_id,
            )
        )
        if grant is None or grant.phase != simulation_session.status:
            return SingleAiTurnResult(
                outcome=SingleAiTurnOutcome.RECONCILIATION_REQUIRED,
                processed_floor_grant_id=simulation_session.current_floor_grant_id,
            )
        participant = await session.scalar(
            select(SessionParticipant).where(
                SessionParticipant.id == grant.participant_id,
                SessionParticipant.session_id == session_id,
            )
        )
        if participant is None:
            return SingleAiTurnResult(
                outcome=SingleAiTurnOutcome.RECONCILIATION_REQUIRED,
                processed_floor_grant_id=grant.id,
            )
        if (
            participant.actor_kind == ParticipantActorKind.HUMAN
            and participant.participation_role == ParticipationRole.CANDIDATE
            and participant.availability == ParticipantAvailability.AVAILABLE
        ):
            return SingleAiTurnResult(
                outcome=SingleAiTurnOutcome.WAITING_FOR_HUMAN,
                processed_floor_grant_id=grant.id,
            )
        if not (
            participant.actor_kind == ParticipantActorKind.AI
            and participant.participation_role == ParticipationRole.CANDIDATE
            and participant.availability == ParticipantAvailability.AVAILABLE
        ):
            return SingleAiTurnResult(
                outcome=SingleAiTurnOutcome.NOT_APPLICABLE,
                processed_floor_grant_id=grant.id,
            )

        identities = derive_automatic_turn_identities(
            session_id=session_id,
            floor_grant_id=grant.id,
        )
        existing_request = await session.get(
            LlmGenerationRequest,
            identities.generation_request_id,
        )
        prompt_version_id: UUID
        requested_at = grant.granted_at
        if existing_request is None:
            prompt = await _select_effective_prompt_version(
                session,
                prompt_key="AI_CANDIDATE_TURN",
                purpose_code="CANDIDATE_UTTERANCE",
                effective_at=grant.granted_at,
            )
            if prompt is None:
                return SingleAiTurnResult(
                    outcome=SingleAiTurnOutcome.RECONCILIATION_REQUIRED,
                    processed_floor_grant_id=grant.id,
                    generation_request_id=identities.generation_request_id,
                )
            prompt_version_id = prompt.id
        else:
            metadata = existing_request.request_metadata
            if (
                existing_request.session_id != session_id
                or existing_request.participant_id != participant.id
                or existing_request.floor_grant_id != grant.id
                or existing_request.provider_identifier != provider_identifier
                or existing_request.model_identifier != model_identifier
                or metadata.get("configuration_version") != configuration_version
            ):
                return SingleAiTurnResult(
                    outcome=SingleAiTurnOutcome.RECONCILIATION_REQUIRED,
                    processed_floor_grant_id=grant.id,
                    generation_request_id=identities.generation_request_id,
                )
            prompt_version_id = existing_request.prompt_version_id
            requested_at = existing_request.requested_at

    runtime_result = await generate_ai_utterance(
        session_factory,
        owner_id=owner_id,
        command=GenerateAiUtteranceCommand(
            generation_request_id=identities.generation_request_id,
            utterance_id=identities.utterance_id,
            session_id=session_id,
            participant_id=participant.id,
            floor_grant_id=grant.id,
            prompt_version_id=prompt_version_id,
            provider_identifier=provider_identifier,
            model_identifier=model_identifier,
            request_metadata=GenerationRequestMetadata(
                configuration_version=configuration_version
            ),
            occurred_at=requested_at,
        ),
        executor=provider,
    )

    release_reason: FloorReleaseReason | None = None
    durable_utterance_id = runtime_result.utterance_id
    if runtime_result.outcome in {
        RuntimeGenerationOutcome.COMPLETED,
        RuntimeGenerationOutcome.COMPLETED_REPLAY,
    }:
        async with session_factory() as session:
            request = await session.get(
                LlmGenerationRequest,
                identities.generation_request_id,
            )
            utterance = await session.get(AiUtterance, identities.utterance_id)
        if not (
            request is not None
            and request.session_id == session_id
            and request.participant_id == participant.id
            and request.floor_grant_id == grant.id
            and request.status == GenerationRequestStatus.COMPLETED
            and utterance is not None
            and utterance.session_id == session_id
            and utterance.participant_id == participant.id
            and utterance.floor_grant_id == grant.id
            and utterance.generation_request_id == identities.generation_request_id
        ):
            return SingleAiTurnResult(
                outcome=SingleAiTurnOutcome.RECONCILIATION_REQUIRED,
                processed_floor_grant_id=grant.id,
                generation_request_id=identities.generation_request_id,
                runtime_outcome=runtime_result.outcome,
            )
        release_reason = FloorReleaseReason.SPEAKER_FINISHED
    elif runtime_result.outcome in {
        RuntimeGenerationOutcome.FAILED,
        RuntimeGenerationOutcome.FAILED_REPLAY,
    }:
        async with session_factory() as session:
            request = await session.get(
                LlmGenerationRequest,
                identities.generation_request_id,
            )
        if not (
            request is not None
            and request.session_id == session_id
            and request.participant_id == participant.id
            and request.floor_grant_id == grant.id
            and request.status == GenerationRequestStatus.FAILED
            and request.failure_code is not None
            and request.failure_code == runtime_result.failure_code
        ):
            return SingleAiTurnResult(
                outcome=SingleAiTurnOutcome.RECONCILIATION_REQUIRED,
                processed_floor_grant_id=grant.id,
                generation_request_id=identities.generation_request_id,
                runtime_outcome=runtime_result.outcome,
            )
        release_reason = FloorReleaseReason.INTERRUPTED
    elif runtime_result.outcome is RuntimeGenerationOutcome.SUPERSEDED:
        async with session_factory() as session:
            winning_utterance = await session.scalar(
                select(AiUtterance).where(
                    AiUtterance.session_id == session_id,
                    AiUtterance.floor_grant_id == grant.id,
                )
            )
            winning_request = (
                None
                if winning_utterance is None
                else await session.get(
                    LlmGenerationRequest,
                    winning_utterance.generation_request_id,
                )
            )
        if not (
            winning_utterance is not None
            and winning_utterance.participant_id == participant.id
            and winning_request is not None
            and winning_request.session_id == session_id
            and winning_request.participant_id == participant.id
            and winning_request.floor_grant_id == grant.id
            and winning_request.status == GenerationRequestStatus.COMPLETED
        ):
            return SingleAiTurnResult(
                outcome=SingleAiTurnOutcome.RECONCILIATION_REQUIRED,
                processed_floor_grant_id=grant.id,
                generation_request_id=identities.generation_request_id,
                runtime_outcome=runtime_result.outcome,
                failure_code=runtime_result.failure_code,
            )
        durable_utterance_id = winning_utterance.id
        release_reason = FloorReleaseReason.SPEAKER_FINISHED
    else:
        if runtime_result.outcome in {
            RuntimeGenerationOutcome.CONTEXT_REJECTED,
            RuntimeGenerationOutcome.STALE_RESULT,
        }:
            outcome = await _classify_original_grant_after_runtime_stop(
                session_factory,
                owner_id=owner_id,
                session_id=session_id,
                floor_grant_id=grant.id,
                expected_phase=SessionStatus(grant.phase),
            )
        else:
            outcome = SingleAiTurnOutcome.RECONCILIATION_REQUIRED
        return SingleAiTurnResult(
            outcome=outcome,
            processed_floor_grant_id=grant.id,
            generation_request_id=identities.generation_request_id,
            utterance_id=runtime_result.utterance_id,
            runtime_outcome=runtime_result.outcome,
            failure_code=runtime_result.failure_code,
        )

    release_resolution = await _release_terminal_grant(
        session_factory,
        owner_id=owner_id,
        session_id=session_id,
        floor_grant_id=grant.id,
        action_id=identities.release_action_id,
        reason=release_reason,
    )
    if release_resolution is not _CheckpointResolution.EXPECTED_DURABLE_RESULT:
        outcome = (
            SingleAiTurnOutcome.STATE_CHANGED
            if release_resolution is _CheckpointResolution.STATE_CHANGED
            else SingleAiTurnOutcome.RECONCILIATION_REQUIRED
        )
        return SingleAiTurnResult(
            outcome=outcome,
            processed_floor_grant_id=grant.id,
            generation_request_id=identities.generation_request_id,
            utterance_id=runtime_result.utterance_id,
            runtime_outcome=runtime_result.outcome,
            failure_code=runtime_result.failure_code,
        )
    scheduled = await _drive_scheduler_checkpoint(
        session_factory,
        owner_id=owner_id,
        session_id=session_id,
        processed_floor_grant_id=grant.id,
        identities=identities,
        scheduling_policy=scheduling_policy,
    )
    return scheduled.model_copy(
        update={
            "generation_request_id": identities.generation_request_id,
            "utterance_id": durable_utterance_id,
            "release_action_id": identities.release_action_id,
            "runtime_outcome": runtime_result.outcome,
            "failure_code": runtime_result.failure_code,
        }
    )
