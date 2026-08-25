from dataclasses import dataclass
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
from group_interview_arena_api.modules.discussion_sessions.domain import SessionStatus
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
    ReleasedFloorProof,
    SchedulerCheckpointIdentities,
    SchedulerCheckpointOutcome,
    SchedulerCheckpointResult,
    drive_scheduler_checkpoint,
)
from group_interview_arena_api.modules.floor_control.scheduler import (
    V0_1_SCHEDULER_POLICY,
)

_HUMAN_PROGRESSION_NAMESPACE = UUID("9b347f1a-48fc-58d1-a1d3-e71e4ee861b4")


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
    scheduler_result: SchedulerCheckpointResult | None = None
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
    scheduler_result: SchedulerCheckpointResult | None = None,
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
        return DiscussionProgressionResult(outcome=DiscussionProgressionOutcome.NO_WORK)

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
