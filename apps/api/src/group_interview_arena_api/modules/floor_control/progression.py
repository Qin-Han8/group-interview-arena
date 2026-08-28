from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from group_interview_arena_api.db import (
    DiscussionEvent,
    FloorDecision,
    FloorGrant,
    FloorIntervention,
    FloorRelease,
    SessionAction,
    SessionParticipant,
    SimulationSession,
)
from group_interview_arena_api.modules.discussion_sessions.domain import (
    NEXT_DEADLINE_STATUS,
    SessionStatus,
    SessionTransitionTrigger,
)
from group_interview_arena_api.modules.discussion_sessions.service import (
    ActionIdConflictError,
    SessionNotFoundError,
    SessionPersistenceError,
)
from group_interview_arena_api.modules.floor_control.domain import (
    FLOOR_ENABLED_PHASES,
    FloorDecisionOutcome,
    FloorReleaseReason,
    InvalidFloorStateError,
    ParticipantActorKind,
    ParticipantAvailability,
    ParticipationRole,
    StaleFloorDecisionError,
)
from group_interview_arena_api.modules.floor_control.scheduler import (
    ScheduleFloorCommand,
    SchedulerPolicy,
)
from group_interview_arena_api.modules.floor_control.service import (
    apply_scheduler_command,
)


class SchedulerCheckpointOutcome(StrEnum):
    NEXT_AI_GRANTED = "next_ai_granted"
    NEXT_HUMAN_GRANTED = "next_human_granted"
    NO_GRANT = "no_grant"
    INTERVENTION_REQUESTED = "intervention_requested"
    RECONCILIATION_REQUIRED = "reconciliation_required"
    STATE_CHANGED = "state_changed"


@dataclass(frozen=True)
class SchedulerCheckpointIdentities:
    schedule_action_id: UUID
    decision_id: UUID
    next_floor_grant_id: UUID
    intervention_id: UUID


@dataclass(frozen=True)
class InitialPhaseEntryProof:
    phase: SessionStatus
    event_sequence: int
    occurred_at: datetime
    phase_started_at: datetime
    phase_deadline_at: datetime


@dataclass(frozen=True)
class InitialSchedulerCheckpointResult:
    outcome: SchedulerCheckpointOutcome
    processed_phase: SessionStatus
    phase_entry_sequence: int
    identities: SchedulerCheckpointIdentities
    next_floor_grant_id: UUID | None = None
    next_participant_id: UUID | None = None
    intervention_id: UUID | None = None


@dataclass(frozen=True)
class ReleasedFloorProof:
    floor_grant_id: UUID
    release_action_id: UUID
    release_command_type: str
    allowed_reasons: frozenset[FloorReleaseReason]


@dataclass(frozen=True)
class SchedulerCheckpointResult:
    outcome: SchedulerCheckpointOutcome
    processed_floor_grant_id: UUID
    identities: SchedulerCheckpointIdentities
    next_floor_grant_id: UUID | None = None
    next_participant_id: UUID | None = None
    intervention_id: UUID | None = None


def _result(
    outcome: SchedulerCheckpointOutcome,
    *,
    released_floor: ReleasedFloorProof,
    identities: SchedulerCheckpointIdentities,
    next_floor_grant_id: UUID | None = None,
    next_participant_id: UUID | None = None,
    intervention_id: UUID | None = None,
) -> SchedulerCheckpointResult:
    return SchedulerCheckpointResult(
        outcome=outcome,
        processed_floor_grant_id=released_floor.floor_grant_id,
        identities=identities,
        next_floor_grant_id=next_floor_grant_id,
        next_participant_id=next_participant_id,
        intervention_id=intervention_id,
    )


async def _release_proof_is_exact(
    session: AsyncSession,
    *,
    owner_id: UUID,
    session_id: UUID,
    released_floor: ReleasedFloorProof,
) -> bool:
    aggregate = await session.scalar(
        select(SimulationSession).where(
            SimulationSession.id == session_id,
            SimulationSession.owner_user_id == owner_id,
        )
    )
    grant = await session.get(FloorGrant, released_floor.floor_grant_id)
    release = await session.get(FloorRelease, released_floor.floor_grant_id)
    release_action = await session.get(
        SessionAction,
        (session_id, released_floor.release_action_id),
    )
    return bool(
        aggregate is not None
        and grant is not None
        and grant.session_id == session_id
        and release is not None
        and release.session_id == session_id
        and release.causation_action_id == released_floor.release_action_id
        and release.reason_code in released_floor.allowed_reasons
        and release_action is not None
        and release_action.command_version == 1
        and release_action.command_type == released_floor.release_command_type
    )


async def _recover_scheduler_result(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    owner_id: UUID,
    session_id: UUID,
    released_floor: ReleasedFloorProof,
    identities: SchedulerCheckpointIdentities,
    scheduling_policy: SchedulerPolicy,
) -> SchedulerCheckpointResult | None:
    async with session_factory() as session:
        if not await _release_proof_is_exact(
            session,
            owner_id=owner_id,
            session_id=session_id,
            released_floor=released_floor,
        ):
            return _result(
                SchedulerCheckpointOutcome.RECONCILIATION_REQUIRED,
                released_floor=released_floor,
                identities=identities,
            )
        aggregate = await session.scalar(
            select(SimulationSession).where(
                SimulationSession.id == session_id,
                SimulationSession.owner_user_id == owner_id,
            )
        )
        action = await session.get(
            SessionAction,
            (session_id, identities.schedule_action_id),
        )
        decision = await session.get(FloorDecision, identities.decision_id)
        next_grant = await session.get(FloorGrant, identities.next_floor_grant_id)
        intervention = await session.get(FloorIntervention, identities.intervention_id)
        if action is None:
            if (
                decision is not None
                or next_grant is not None
                or intervention is not None
            ):
                return _result(
                    SchedulerCheckpointOutcome.RECONCILIATION_REQUIRED,
                    released_floor=released_floor,
                    identities=identities,
                )
            return None
        if not (
            aggregate is not None
            and action.command_version == 1
            and action.command_type == "floor.schedule"
            and decision is not None
            and decision.session_id == session_id
            and decision.policy_version == scheduling_policy.version
        ):
            return _result(
                SchedulerCheckpointOutcome.RECONCILIATION_REQUIRED,
                released_floor=released_floor,
                identities=identities,
            )

        if decision.outcome_kind == FloorDecisionOutcome.GRANT:
            if not (
                next_grant is not None
                and next_grant.session_id == session_id
                and next_grant.decision_id == identities.decision_id
                and next_grant.participant_id == decision.selected_participant_id
                and intervention is None
            ):
                return _result(
                    SchedulerCheckpointOutcome.RECONCILIATION_REQUIRED,
                    released_floor=released_floor,
                    identities=identities,
                )
            participant = await session.scalar(
                select(SessionParticipant).where(
                    SessionParticipant.id == next_grant.participant_id,
                    SessionParticipant.session_id == session_id,
                )
            )
            if aggregate.current_floor_grant_id != next_grant.id:
                return _result(
                    SchedulerCheckpointOutcome.STATE_CHANGED,
                    released_floor=released_floor,
                    identities=identities,
                    next_floor_grant_id=next_grant.id,
                    next_participant_id=next_grant.participant_id,
                )
            if participant is None or not (
                participant.participation_role == ParticipationRole.CANDIDATE
                and participant.availability == ParticipantAvailability.AVAILABLE
            ):
                return _result(
                    SchedulerCheckpointOutcome.RECONCILIATION_REQUIRED,
                    released_floor=released_floor,
                    identities=identities,
                )
            if participant.actor_kind == ParticipantActorKind.HUMAN:
                outcome = SchedulerCheckpointOutcome.NEXT_HUMAN_GRANTED
            elif participant.actor_kind == ParticipantActorKind.AI:
                outcome = SchedulerCheckpointOutcome.NEXT_AI_GRANTED
            else:
                return _result(
                    SchedulerCheckpointOutcome.RECONCILIATION_REQUIRED,
                    released_floor=released_floor,
                    identities=identities,
                )
            return _result(
                outcome,
                released_floor=released_floor,
                identities=identities,
                next_floor_grant_id=next_grant.id,
                next_participant_id=participant.id,
            )

        if decision.outcome_kind == FloorDecisionOutcome.REQUEST_INTERVENTION:
            if not (
                intervention is not None
                and intervention.session_id == session_id
                and intervention.decision_id == identities.decision_id
                and next_grant is None
                and aggregate.current_floor_grant_id is None
            ):
                return _result(
                    SchedulerCheckpointOutcome.RECONCILIATION_REQUIRED,
                    released_floor=released_floor,
                    identities=identities,
                )
            return _result(
                SchedulerCheckpointOutcome.INTERVENTION_REQUESTED,
                released_floor=released_floor,
                identities=identities,
                intervention_id=intervention.id,
            )

        if decision.outcome_kind == FloorDecisionOutcome.NO_GRANT:
            if (
                next_grant is not None
                or intervention is not None
                or aggregate.current_floor_grant_id is not None
            ):
                return _result(
                    SchedulerCheckpointOutcome.RECONCILIATION_REQUIRED,
                    released_floor=released_floor,
                    identities=identities,
                )
            return _result(
                SchedulerCheckpointOutcome.NO_GRANT,
                released_floor=released_floor,
                identities=identities,
            )

        return _result(
            SchedulerCheckpointOutcome.RECONCILIATION_REQUIRED,
            released_floor=released_floor,
            identities=identities,
        )


async def _classify_unresolved_checkpoint(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    owner_id: UUID,
    session_id: UUID,
    released_floor: ReleasedFloorProof,
    identities: SchedulerCheckpointIdentities,
) -> SchedulerCheckpointResult:
    async with session_factory() as session:
        aggregate = await session.scalar(
            select(SimulationSession).where(
                SimulationSession.id == session_id,
                SimulationSession.owner_user_id == owner_id,
            )
        )
        grant = await session.get(FloorGrant, released_floor.floor_grant_id)
        release_is_exact = await _release_proof_is_exact(
            session,
            owner_id=owner_id,
            session_id=session_id,
            released_floor=released_floor,
        )
        if (
            aggregate is None
            or grant is None
            or grant.session_id != session_id
            or aggregate.status != grant.phase
            or SessionStatus(aggregate.status) not in FLOOR_ENABLED_PHASES
            or aggregate.current_floor_grant_id is not None
            or not release_is_exact
        ):
            outcome = SchedulerCheckpointOutcome.STATE_CHANGED
        else:
            outcome = SchedulerCheckpointOutcome.RECONCILIATION_REQUIRED
    return _result(
        outcome,
        released_floor=released_floor,
        identities=identities,
    )


async def drive_scheduler_checkpoint(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    owner_id: UUID,
    session_id: UUID,
    released_floor: ReleasedFloorProof,
    identities: SchedulerCheckpointIdentities,
    scheduling_policy: SchedulerPolicy,
) -> SchedulerCheckpointResult:
    recovered = await _recover_scheduler_result(
        session_factory,
        owner_id=owner_id,
        session_id=session_id,
        released_floor=released_floor,
        identities=identities,
        scheduling_policy=scheduling_policy,
    )
    if recovered is not None:
        return recovered

    async with session_factory() as session:
        aggregate = await session.scalar(
            select(SimulationSession).where(
                SimulationSession.id == session_id,
                SimulationSession.owner_user_id == owner_id,
            )
        )
        if (
            aggregate is None
            or SessionStatus(aggregate.status) not in FLOOR_ENABLED_PHASES
            or aggregate.current_floor_grant_id is not None
        ):
            return _result(
                SchedulerCheckpointOutcome.STATE_CHANGED,
                released_floor=released_floor,
                identities=identities,
            )
        command = ScheduleFloorCommand(
            session_id=session_id,
            action_id=identities.schedule_action_id,
            decision_id=identities.decision_id,
            grant_id=identities.next_floor_grant_id,
            intervention_id=identities.intervention_id,
            expected_phase=SessionStatus(aggregate.status),
            expected_last_sequence=aggregate.last_sequence,
            expected_current_floor_grant_id=None,
            evaluated_at=datetime.now(UTC),
            policy=scheduling_policy,
        )

    try:
        async with session_factory() as session:
            await apply_scheduler_command(session, owner_id=owner_id, command=command)
    except (
        ActionIdConflictError,
        InvalidFloorStateError,
        SessionNotFoundError,
        SessionPersistenceError,
        StaleFloorDecisionError,
    ):
        pass

    recovered = await _recover_scheduler_result(
        session_factory,
        owner_id=owner_id,
        session_id=session_id,
        released_floor=released_floor,
        identities=identities,
        scheduling_policy=scheduling_policy,
    )
    if recovered is not None:
        return recovered
    return await _classify_unresolved_checkpoint(
        session_factory,
        owner_id=owner_id,
        session_id=session_id,
        released_floor=released_floor,
        identities=identities,
    )


def _initial_result(
    outcome: SchedulerCheckpointOutcome,
    *,
    phase_entry: InitialPhaseEntryProof,
    identities: SchedulerCheckpointIdentities,
    next_floor_grant_id: UUID | None = None,
    next_participant_id: UUID | None = None,
    intervention_id: UUID | None = None,
) -> InitialSchedulerCheckpointResult:
    return InitialSchedulerCheckpointResult(
        outcome=outcome,
        processed_phase=phase_entry.phase,
        phase_entry_sequence=phase_entry.event_sequence,
        identities=identities,
        next_floor_grant_id=next_floor_grant_id,
        next_participant_id=next_participant_id,
        intervention_id=intervention_id,
    )


def _canonical_phase_timestamp(value: datetime) -> str:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Phase-entry timestamp must be timezone-aware.")
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _previous_deadline_phase(phase: SessionStatus) -> SessionStatus:
    for previous, current in NEXT_DEADLINE_STATUS.items():
        if current is phase:
            return previous
    raise ValueError("Phase entry has no durable predecessor.")


async def _initial_phase_proof_is_exact(
    session: AsyncSession,
    *,
    owner_id: UUID,
    session_id: UUID,
    phase_entry: InitialPhaseEntryProof,
    allow_later_events: bool,
) -> bool:
    aggregate = await session.scalar(
        select(SimulationSession).where(
            SimulationSession.id == session_id,
            SimulationSession.owner_user_id == owner_id,
        )
    )
    event = await session.get(
        DiscussionEvent,
        (session_id, phase_entry.event_sequence),
    )
    latest_state_change = await session.scalar(
        select(DiscussionEvent)
        .where(
            DiscussionEvent.session_id == session_id,
            DiscussionEvent.event_type == "session.state_changed",
        )
        .order_by(DiscussionEvent.sequence.desc())
        .limit(1)
    )
    if (
        aggregate is None
        or event is None
        or latest_state_change is None
        or latest_state_change.sequence != phase_entry.event_sequence
        or aggregate.status != phase_entry.phase.value
        or aggregate.phase_started_at != phase_entry.phase_started_at
        or aggregate.phase_deadline_at != phase_entry.phase_deadline_at
        or (
            aggregate.last_sequence < phase_entry.event_sequence
            if allow_later_events
            else aggregate.last_sequence != phase_entry.event_sequence
        )
    ):
        return False
    try:
        expected_payload = {
            "previous_status": _previous_deadline_phase(phase_entry.phase).value,
            "status": phase_entry.phase.value,
            "trigger": SessionTransitionTrigger.PHASE_DEADLINE.value,
            "phase_started_at": _canonical_phase_timestamp(
                phase_entry.phase_started_at
            ),
            "phase_deadline_at": _canonical_phase_timestamp(
                phase_entry.phase_deadline_at
            ),
        }
        _canonical_phase_timestamp(phase_entry.occurred_at)
    except ValueError:
        return False
    return bool(
        phase_entry.phase in FLOOR_ENABLED_PHASES
        and phase_entry.event_sequence > 0
        and event.event_version == 2
        and event.event_type == "session.state_changed"
        and event.causation_action_id is None
        and event.occurred_at == phase_entry.occurred_at
        and event.payload == expected_payload
    )


async def _recover_initial_scheduler_result(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    owner_id: UUID,
    session_id: UUID,
    phase_entry: InitialPhaseEntryProof,
    identities: SchedulerCheckpointIdentities,
    scheduling_policy: SchedulerPolicy,
) -> InitialSchedulerCheckpointResult | None:
    async with session_factory() as session:
        aggregate = await session.scalar(
            select(SimulationSession).where(
                SimulationSession.id == session_id,
                SimulationSession.owner_user_id == owner_id,
            )
        )
        action = await session.get(
            SessionAction,
            (session_id, identities.schedule_action_id),
        )
        decision = await session.get(FloorDecision, identities.decision_id)
        next_grant = await session.get(FloorGrant, identities.next_floor_grant_id)
        intervention = await session.get(FloorIntervention, identities.intervention_id)
        if action is None:
            if (
                decision is not None
                or next_grant is not None
                or intervention is not None
            ):
                return _initial_result(
                    SchedulerCheckpointOutcome.RECONCILIATION_REQUIRED,
                    phase_entry=phase_entry,
                    identities=identities,
                )
            return None
        if not (
            aggregate is not None
            and action.command_version == 1
            and action.command_type == "floor.schedule"
            and action.created_at == phase_entry.occurred_at
            and decision is not None
            and decision.session_id == session_id
            and decision.phase == phase_entry.phase.value
            and decision.expected_last_sequence == phase_entry.event_sequence
            and decision.policy_version == scheduling_policy.version
            and decision.decided_at == phase_entry.occurred_at
        ):
            return _initial_result(
                SchedulerCheckpointOutcome.RECONCILIATION_REQUIRED,
                phase_entry=phase_entry,
                identities=identities,
            )
        if aggregate.status != phase_entry.phase.value:
            return _initial_result(
                SchedulerCheckpointOutcome.STATE_CHANGED,
                phase_entry=phase_entry,
                identities=identities,
            )

        if decision.outcome_kind == FloorDecisionOutcome.GRANT:
            if not (
                next_grant is not None
                and next_grant.session_id == session_id
                and next_grant.decision_id == identities.decision_id
                and next_grant.participant_id == decision.selected_participant_id
                and next_grant.phase == phase_entry.phase.value
                and next_grant.granted_at == phase_entry.occurred_at
                and intervention is None
            ):
                return _initial_result(
                    SchedulerCheckpointOutcome.RECONCILIATION_REQUIRED,
                    phase_entry=phase_entry,
                    identities=identities,
                )
            participant = await session.scalar(
                select(SessionParticipant).where(
                    SessionParticipant.id == next_grant.participant_id,
                    SessionParticipant.session_id == session_id,
                )
            )
            if aggregate.current_floor_grant_id != next_grant.id:
                return _initial_result(
                    SchedulerCheckpointOutcome.STATE_CHANGED,
                    phase_entry=phase_entry,
                    identities=identities,
                    next_floor_grant_id=next_grant.id,
                    next_participant_id=next_grant.participant_id,
                )
            if participant is None or not (
                participant.participation_role == ParticipationRole.CANDIDATE
                and participant.availability == ParticipantAvailability.AVAILABLE
            ):
                return _initial_result(
                    SchedulerCheckpointOutcome.RECONCILIATION_REQUIRED,
                    phase_entry=phase_entry,
                    identities=identities,
                )
            if participant.actor_kind == ParticipantActorKind.HUMAN:
                outcome = SchedulerCheckpointOutcome.NEXT_HUMAN_GRANTED
            elif participant.actor_kind == ParticipantActorKind.AI:
                outcome = SchedulerCheckpointOutcome.NEXT_AI_GRANTED
            else:
                return _initial_result(
                    SchedulerCheckpointOutcome.RECONCILIATION_REQUIRED,
                    phase_entry=phase_entry,
                    identities=identities,
                )
            return _initial_result(
                outcome,
                phase_entry=phase_entry,
                identities=identities,
                next_floor_grant_id=next_grant.id,
                next_participant_id=participant.id,
            )

        if decision.outcome_kind == FloorDecisionOutcome.REQUEST_INTERVENTION:
            if not (
                intervention is not None
                and intervention.session_id == session_id
                and intervention.decision_id == identities.decision_id
                and intervention.requested_at == phase_entry.occurred_at
                and next_grant is None
                and aggregate.current_floor_grant_id is None
            ):
                return _initial_result(
                    SchedulerCheckpointOutcome.RECONCILIATION_REQUIRED,
                    phase_entry=phase_entry,
                    identities=identities,
                )
            return _initial_result(
                SchedulerCheckpointOutcome.INTERVENTION_REQUESTED,
                phase_entry=phase_entry,
                identities=identities,
                intervention_id=intervention.id,
            )

        if decision.outcome_kind == FloorDecisionOutcome.NO_GRANT:
            if (
                next_grant is not None
                or intervention is not None
                or aggregate.current_floor_grant_id is not None
            ):
                return _initial_result(
                    SchedulerCheckpointOutcome.RECONCILIATION_REQUIRED,
                    phase_entry=phase_entry,
                    identities=identities,
                )
            return _initial_result(
                SchedulerCheckpointOutcome.NO_GRANT,
                phase_entry=phase_entry,
                identities=identities,
            )

        return _initial_result(
            SchedulerCheckpointOutcome.RECONCILIATION_REQUIRED,
            phase_entry=phase_entry,
            identities=identities,
        )


async def _classify_unresolved_initial_checkpoint(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    owner_id: UUID,
    session_id: UUID,
    phase_entry: InitialPhaseEntryProof,
    identities: SchedulerCheckpointIdentities,
) -> InitialSchedulerCheckpointResult:
    async with session_factory() as session:
        aggregate = await session.scalar(
            select(SimulationSession).where(
                SimulationSession.id == session_id,
                SimulationSession.owner_user_id == owner_id,
            )
        )
        state_changed = bool(
            aggregate is None or aggregate.status != phase_entry.phase.value
        )
    return _initial_result(
        (
            SchedulerCheckpointOutcome.STATE_CHANGED
            if state_changed
            else SchedulerCheckpointOutcome.RECONCILIATION_REQUIRED
        ),
        phase_entry=phase_entry,
        identities=identities,
    )


async def drive_initial_scheduler_checkpoint(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    owner_id: UUID,
    session_id: UUID,
    phase_entry: InitialPhaseEntryProof,
    identities: SchedulerCheckpointIdentities,
    scheduling_policy: SchedulerPolicy,
) -> InitialSchedulerCheckpointResult:
    async with session_factory() as session:
        existing_action = await session.get(
            SessionAction,
            (session_id, identities.schedule_action_id),
        )
        proof_is_exact = await _initial_phase_proof_is_exact(
            session,
            owner_id=owner_id,
            session_id=session_id,
            phase_entry=phase_entry,
            allow_later_events=existing_action is not None,
        )
    if not proof_is_exact:
        return await _classify_unresolved_initial_checkpoint(
            session_factory,
            owner_id=owner_id,
            session_id=session_id,
            phase_entry=phase_entry,
            identities=identities,
        )

    command = ScheduleFloorCommand(
        session_id=session_id,
        action_id=identities.schedule_action_id,
        decision_id=identities.decision_id,
        grant_id=identities.next_floor_grant_id,
        intervention_id=identities.intervention_id,
        expected_phase=phase_entry.phase,
        expected_last_sequence=phase_entry.event_sequence,
        expected_current_floor_grant_id=None,
        evaluated_at=phase_entry.occurred_at,
        policy=scheduling_policy,
    )
    try:
        async with session_factory() as session:
            await apply_scheduler_command(session, owner_id=owner_id, command=command)
    except ActionIdConflictError:
        return _initial_result(
            SchedulerCheckpointOutcome.RECONCILIATION_REQUIRED,
            phase_entry=phase_entry,
            identities=identities,
        )
    except (
        InvalidFloorStateError,
        SessionNotFoundError,
        SessionPersistenceError,
        StaleFloorDecisionError,
    ):
        pass

    recovered = await _recover_initial_scheduler_result(
        session_factory,
        owner_id=owner_id,
        session_id=session_id,
        phase_entry=phase_entry,
        identities=identities,
        scheduling_policy=scheduling_policy,
    )
    if recovered is not None:
        return recovered
    return await _classify_unresolved_initial_checkpoint(
        session_factory,
        owner_id=owner_id,
        session_id=session_id,
        phase_entry=phase_entry,
        identities=identities,
    )
