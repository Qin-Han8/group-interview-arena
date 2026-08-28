from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid5

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from group_interview_arena_api.db import (
    DiscussionEvent,
    FloorGrant,
    FloorRelease,
    SessionAction,
    SessionParticipant,
    SimulationSession,
)
from group_interview_arena_api.modules.ai_runtime.composition import (
    drive_configured_ai_session,
)
from group_interview_arena_api.modules.ai_runtime.continuous import (
    ContinuousAiDriveResult,
)
from group_interview_arena_api.modules.ai_runtime.orchestration import (
    has_resumable_ai_work,
)
from group_interview_arena_api.modules.discussion_sessions.domain import (
    NEXT_DEADLINE_STATUS,
    SessionStatus,
    SessionTransitionTrigger,
)
from group_interview_arena_api.modules.discussion_sessions.utterances import (
    derive_human_utterance_id,
    human_utterance_command_digest,
    participant_utterance_created_event,
)
from group_interview_arena_api.modules.floor_control.domain import (
    FLOOR_ENABLED_PHASES,
    FloorReleaseReason,
    ParticipantActorKind,
    ParticipantAvailability,
    ParticipationRole,
)
from group_interview_arena_api.modules.floor_control.progression import (
    InitialPhaseEntryProof,
    InitialSchedulerCheckpointResult,
    ReleasedFloorProof,
    SchedulerCheckpointIdentities,
    SchedulerCheckpointOutcome,
    SchedulerCheckpointResult,
    drive_initial_scheduler_checkpoint,
    drive_scheduler_checkpoint,
)
from group_interview_arena_api.modules.floor_control.scheduler import (
    V0_1_SCHEDULER_POLICY,
)

_HUMAN_PROGRESSION_NAMESPACE = UUID("9b347f1a-48fc-58d1-a1d3-e71e4ee861b4")

_INITIAL_PROGRESSION_NAMESPACE = UUID("6a45d9ab-1d5d-5c96-b791-f82b884b20d8")


class DiscussionProgressionOutcome(StrEnum):
    NO_WORK = "no_work"
    NEXT_HUMAN_GRANTED = "next_human_granted"
    AI_DRIVE_COMPLETED = "ai_drive_completed"
    NO_GRANT = "no_grant"
    INTERVENTION_REQUESTED = "intervention_requested"
    RECONCILIATION_REQUIRED = "reconciliation_required"
    STATE_CHANGED = "state_changed"


@dataclass(frozen=True)
class DiscussionProgressionResult:
    outcome: DiscussionProgressionOutcome
    released_floor_grant_id: UUID | None = None
    scheduler_result: (
        SchedulerCheckpointResult | InitialSchedulerCheckpointResult | None
    ) = None
    ai_drive_result: ContinuousAiDriveResult | None = None


@dataclass(frozen=True)
class _HumanCheckpoint:
    released_floor: ReleasedFloorProof
    identities: SchedulerCheckpointIdentities


class _HumanCheckpointState(StrEnum):
    ABSENT = "absent"
    EXACT = "exact"
    INCONSISTENT = "inconsistent"


def _deterministic_uuid4(name: str) -> UUID:
    derived = uuid5(_HUMAN_PROGRESSION_NAMESPACE, name)
    return UUID(bytes=derived.bytes, version=4)


def derive_human_scheduler_identities(
    *,
    session_id: UUID,
    released_floor_grant_id: UUID,
) -> SchedulerCheckpointIdentities:
    prefix = f"human-post-release:{session_id}:{released_floor_grant_id}"
    return SchedulerCheckpointIdentities(
        schedule_action_id=_deterministic_uuid4(f"{prefix}:schedule-action"),
        decision_id=_deterministic_uuid4(f"{prefix}:decision"),
        next_floor_grant_id=_deterministic_uuid4(f"{prefix}:next-floor-grant"),
        intervention_id=_deterministic_uuid4(f"{prefix}:intervention"),
    )


class _InitialPhaseCheckpointState(StrEnum):
    ABSENT = "absent"
    EXACT = "exact"
    INCONSISTENT = "inconsistent"


def _initial_deterministic_uuid4(name: str) -> UUID:
    derived = uuid5(_INITIAL_PROGRESSION_NAMESPACE, name)
    return UUID(bytes=derived.bytes, version=4)


def derive_initial_scheduler_identities(
    *,
    session_id: UUID,
    phase: SessionStatus,
    phase_entry_sequence: int,
) -> SchedulerCheckpointIdentities:
    prefix = f"initial-phase:{session_id}:{phase.value}:{phase_entry_sequence}"
    return SchedulerCheckpointIdentities(
        schedule_action_id=_initial_deterministic_uuid4(f"{prefix}:schedule-action"),
        decision_id=_initial_deterministic_uuid4(f"{prefix}:decision"),
        next_floor_grant_id=_initial_deterministic_uuid4(f"{prefix}:next-floor-grant"),
        intervention_id=_initial_deterministic_uuid4(f"{prefix}:intervention"),
    )


def _canonical_event_timestamp(value: datetime) -> str:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Phase-entry timestamp must be timezone-aware.")
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _previous_deadline_phase(phase: SessionStatus) -> SessionStatus:
    for previous, current in NEXT_DEADLINE_STATUS.items():
        if current is phase:
            return previous
    raise ValueError("Phase entry has no durable predecessor.")


async def _initial_phase_entry_checkpoint(
    session: AsyncSession,
    *,
    owner_id: UUID,
    aggregate: SimulationSession,
) -> tuple[_InitialPhaseCheckpointState, InitialPhaseEntryProof | None]:
    try:
        phase = SessionStatus(aggregate.status)
    except ValueError:
        return _InitialPhaseCheckpointState.INCONSISTENT, None
    if (
        aggregate.owner_user_id != owner_id
        or phase not in FLOOR_ENABLED_PHASES
        or aggregate.current_floor_grant_id is not None
    ):
        return _InitialPhaseCheckpointState.ABSENT, None

    event = await session.scalar(
        select(DiscussionEvent)
        .where(
            DiscussionEvent.session_id == aggregate.id,
            DiscussionEvent.event_type == "session.state_changed",
        )
        .order_by(DiscussionEvent.sequence.desc())
        .limit(1)
    )
    if event is None:
        return _InitialPhaseCheckpointState.ABSENT, None
    if event.sequence > aggregate.last_sequence:
        return _InitialPhaseCheckpointState.INCONSISTENT, None
    if event.sequence < aggregate.last_sequence:
        latest_event = await session.get(
            DiscussionEvent,
            (aggregate.id, aggregate.last_sequence),
        )
        identities = derive_initial_scheduler_identities(
            session_id=aggregate.id,
            phase=phase,
            phase_entry_sequence=event.sequence,
        )
        existing_action = await session.get(
            SessionAction,
            (aggregate.id, identities.schedule_action_id),
        )
        if latest_event is None or existing_action is None:
            return _InitialPhaseCheckpointState.INCONSISTENT, None
    if aggregate.phase_started_at is None or aggregate.phase_deadline_at is None:
        return _InitialPhaseCheckpointState.INCONSISTENT, None
    try:
        expected_payload = {
            "previous_status": _previous_deadline_phase(phase).value,
            "status": phase.value,
            "trigger": SessionTransitionTrigger.PHASE_DEADLINE.value,
            "phase_started_at": _canonical_event_timestamp(aggregate.phase_started_at),
            "phase_deadline_at": _canonical_event_timestamp(
                aggregate.phase_deadline_at
            ),
        }
        _canonical_event_timestamp(event.occurred_at)
    except ValueError:
        return _InitialPhaseCheckpointState.INCONSISTENT, None
    if not (
        event.event_version == 2
        and event.event_type == "session.state_changed"
        and event.causation_action_id is None
        and event.payload == expected_payload
    ):
        return _InitialPhaseCheckpointState.INCONSISTENT, None

    return (
        _InitialPhaseCheckpointState.EXACT,
        InitialPhaseEntryProof(
            phase=phase,
            event_sequence=event.sequence,
            occurred_at=event.occurred_at,
            phase_started_at=aggregate.phase_started_at,
            phase_deadline_at=aggregate.phase_deadline_at,
        ),
    )


async def _latest_human_checkpoint(
    session: AsyncSession,
    *,
    owner_id: UUID,
    session_id: UUID,
) -> tuple[_HumanCheckpointState, _HumanCheckpoint | None]:
    release_event = await session.scalar(
        select(DiscussionEvent)
        .where(
            DiscussionEvent.session_id == session_id,
            DiscussionEvent.event_type == "floor.released",
        )
        .order_by(DiscussionEvent.sequence.desc())
        .limit(1)
    )
    if release_event is None:
        return _HumanCheckpointState.ABSENT, None
    try:
        grant_id = UUID(str(release_event.payload["grant_id"]))
    except KeyError, TypeError, ValueError:
        return _HumanCheckpointState.INCONSISTENT, None

    grant = await session.get(FloorGrant, grant_id)
    participant = (
        await session.get(SessionParticipant, grant.participant_id)
        if grant is not None
        else None
    )
    release = await session.get(FloorRelease, grant_id)
    if (
        grant is None
        or grant.session_id != session_id
        or participant is None
        or participant.session_id != session_id
    ):
        return _HumanCheckpointState.INCONSISTENT, None
    if participant.actor_kind != ParticipantActorKind.HUMAN.value:
        return _HumanCheckpointState.ABSENT, None
    if (
        release is None
        or release.reason_code != FloorReleaseReason.SPEAKER_FINISHED.value
    ):
        return _HumanCheckpointState.ABSENT, None

    action_id = release.causation_action_id
    action = (
        await session.get(SessionAction, (session_id, action_id))
        if action_id is not None
        else None
    )
    utterance_event = await session.get(
        DiscussionEvent,
        (session_id, release_event.sequence - 1),
    )
    if action_id is None or action is None or utterance_event is None:
        return _HumanCheckpointState.INCONSISTENT, None
    content = utterance_event.payload.get("content")
    if not isinstance(content, str):
        return _HumanCheckpointState.INCONSISTENT, None
    expected_utterance_id = derive_human_utterance_id(
        session_id=session_id,
        action_id=action_id,
    )
    phase = SessionStatus(grant.phase)
    expected_utterance = participant_utterance_created_event(
        utterance_id=expected_utterance_id,
        participant_id=participant.id,
        actor_kind=ParticipantActorKind.HUMAN,
        floor_grant_id=grant.id,
        phase=phase,
        content=content,
    )
    expected_release_payload = {
        "grant_id": str(grant.id),
        "participant_id": str(participant.id),
        "phase": phase.value,
        "reason_code": FloorReleaseReason.SPEAKER_FINISHED.value,
    }
    exact = (
        participant.user_id == owner_id
        and participant.participation_role == ParticipationRole.CANDIDATE.value
        and release_event.event_version == 2
        and release_event.causation_action_id == action_id
        and release_event.payload == expected_release_payload
        and utterance_event.event_version == 1
        and utterance_event.event_type == "participant.utterance.created"
        and utterance_event.causation_action_id == action_id
        and utterance_event.payload == expected_utterance.payload
        and action.command_version == 1
        and action.command_type == "participant.utterance.submit"
        and action.payload_digest
        == human_utterance_command_digest(floor_grant_id=grant.id, content=content)
    )
    if not exact:
        return _HumanCheckpointState.INCONSISTENT, None
    return (
        _HumanCheckpointState.EXACT,
        _HumanCheckpoint(
            released_floor=ReleasedFloorProof(
                floor_grant_id=grant.id,
                release_action_id=action_id,
                release_command_type="participant.utterance.submit",
                allowed_reasons=frozenset({FloorReleaseReason.SPEAKER_FINISHED}),
            ),
            identities=derive_human_scheduler_identities(
                session_id=session_id,
                released_floor_grant_id=grant.id,
            ),
        ),
    )


async def _current_floor_kind(
    session: AsyncSession,
    *,
    aggregate: SimulationSession,
) -> ParticipantActorKind | None:
    grant_id = aggregate.current_floor_grant_id
    if grant_id is None:
        return None
    grant = await session.get(FloorGrant, grant_id)
    participant = (
        await session.get(SessionParticipant, grant.participant_id)
        if grant is not None
        else None
    )
    if (
        grant is None
        or grant.session_id != aggregate.id
        or grant.phase != aggregate.status
        or participant is None
        or participant.session_id != aggregate.id
        or participant.participation_role != ParticipationRole.CANDIDATE.value
        or participant.availability != ParticipantAvailability.AVAILABLE.value
    ):
        raise ValueError("Current floor is inconsistent.")
    return ParticipantActorKind(participant.actor_kind)


async def _drive_configured(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    owner_id: UUID,
    session_id: UUID,
    released_floor_grant_id: UUID | None = None,
    scheduler_result: SchedulerCheckpointResult
    | InitialSchedulerCheckpointResult
    | None = None,
) -> DiscussionProgressionResult:
    ai_result = await drive_configured_ai_session(
        session_factory,
        owner_id=owner_id,
        session_id=session_id,
    )
    return DiscussionProgressionResult(
        outcome=DiscussionProgressionOutcome.AI_DRIVE_COMPLETED,
        released_floor_grant_id=released_floor_grant_id,
        scheduler_result=scheduler_result,
        ai_drive_result=ai_result,
    )


async def resume_discussion_progression(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    owner_id: UUID,
    session_id: UUID,
) -> DiscussionProgressionResult:
    checkpoint_state = _HumanCheckpointState.ABSENT
    checkpoint: _HumanCheckpoint | None = None
    initial_state = _InitialPhaseCheckpointState.ABSENT
    initial_proof: InitialPhaseEntryProof | None = None
    try:
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
            ):
                return DiscussionProgressionResult(
                    outcome=DiscussionProgressionOutcome.NO_WORK
                )
            current_kind = await _current_floor_kind(session, aggregate=aggregate)
            if current_kind is ParticipantActorKind.HUMAN:
                return DiscussionProgressionResult(
                    outcome=DiscussionProgressionOutcome.NO_WORK
                )
            if current_kind is ParticipantActorKind.AI:
                drive_current_ai = True
            else:
                drive_current_ai = False
                checkpoint_state, checkpoint = await _latest_human_checkpoint(
                    session,
                    owner_id=owner_id,
                    session_id=session_id,
                )
                if checkpoint_state is _HumanCheckpointState.ABSENT:
                    (
                        initial_state,
                        initial_proof,
                    ) = await _initial_phase_entry_checkpoint(
                        session,
                        owner_id=owner_id,
                        aggregate=aggregate,
                    )
    except ValueError:
        return DiscussionProgressionResult(
            outcome=DiscussionProgressionOutcome.RECONCILIATION_REQUIRED
        )

    if drive_current_ai:
        return await _drive_configured(
            session_factory,
            owner_id=owner_id,
            session_id=session_id,
        )
    if checkpoint_state is _HumanCheckpointState.INCONSISTENT:
        return DiscussionProgressionResult(
            outcome=DiscussionProgressionOutcome.RECONCILIATION_REQUIRED
        )
    if checkpoint is None:
        if await has_resumable_ai_work(
            session_factory,
            owner_id=owner_id,
            session_id=session_id,
        ):
            return await _drive_configured(
                session_factory,
                owner_id=owner_id,
                session_id=session_id,
            )
        if (
            initial_state is not _InitialPhaseCheckpointState.EXACT
            or initial_proof is None
        ):
            return DiscussionProgressionResult(
                outcome=DiscussionProgressionOutcome.RECONCILIATION_REQUIRED
            )
        identities = derive_initial_scheduler_identities(
            session_id=session_id,
            phase=initial_proof.phase,
            phase_entry_sequence=initial_proof.event_sequence,
        )
        initial_result = await drive_initial_scheduler_checkpoint(
            session_factory,
            owner_id=owner_id,
            session_id=session_id,
            phase_entry=initial_proof,
            identities=identities,
            scheduling_policy=V0_1_SCHEDULER_POLICY,
        )
        if initial_result.outcome is SchedulerCheckpointOutcome.NEXT_AI_GRANTED:
            return await _drive_configured(
                session_factory,
                owner_id=owner_id,
                session_id=session_id,
                scheduler_result=initial_result,
            )
        initial_outcome_map = {
            SchedulerCheckpointOutcome.NEXT_HUMAN_GRANTED: (
                DiscussionProgressionOutcome.NEXT_HUMAN_GRANTED
            ),
            SchedulerCheckpointOutcome.NO_GRANT: DiscussionProgressionOutcome.NO_GRANT,
            SchedulerCheckpointOutcome.INTERVENTION_REQUESTED: (
                DiscussionProgressionOutcome.INTERVENTION_REQUESTED
            ),
            SchedulerCheckpointOutcome.RECONCILIATION_REQUIRED: (
                DiscussionProgressionOutcome.RECONCILIATION_REQUIRED
            ),
            SchedulerCheckpointOutcome.STATE_CHANGED: (
                DiscussionProgressionOutcome.STATE_CHANGED
            ),
        }
        return DiscussionProgressionResult(
            outcome=initial_outcome_map[initial_result.outcome],
            scheduler_result=initial_result,
        )

    scheduler_result = await drive_scheduler_checkpoint(
        session_factory,
        owner_id=owner_id,
        session_id=session_id,
        released_floor=checkpoint.released_floor,
        identities=checkpoint.identities,
        scheduling_policy=V0_1_SCHEDULER_POLICY,
    )
    released_grant_id = checkpoint.released_floor.floor_grant_id
    if scheduler_result.outcome is SchedulerCheckpointOutcome.NEXT_AI_GRANTED:
        return await _drive_configured(
            session_factory,
            owner_id=owner_id,
            session_id=session_id,
            released_floor_grant_id=released_grant_id,
            scheduler_result=scheduler_result,
        )
    outcome_map = {
        SchedulerCheckpointOutcome.NEXT_HUMAN_GRANTED: (
            DiscussionProgressionOutcome.NEXT_HUMAN_GRANTED
        ),
        SchedulerCheckpointOutcome.NO_GRANT: DiscussionProgressionOutcome.NO_GRANT,
        SchedulerCheckpointOutcome.INTERVENTION_REQUESTED: (
            DiscussionProgressionOutcome.INTERVENTION_REQUESTED
        ),
        SchedulerCheckpointOutcome.RECONCILIATION_REQUIRED: (
            DiscussionProgressionOutcome.RECONCILIATION_REQUIRED
        ),
        SchedulerCheckpointOutcome.STATE_CHANGED: (
            DiscussionProgressionOutcome.STATE_CHANGED
        ),
    }
    return DiscussionProgressionResult(
        outcome=outcome_map[scheduler_result.outcome],
        released_floor_grant_id=released_grant_id,
        scheduler_result=scheduler_result,
    )
