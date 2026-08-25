import hashlib
import json
from datetime import UTC, datetime
from typing import Never
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from group_interview_arena_api.db.models import (
    DiscussionEvent,
    FloorDecision,
    FloorGrant,
    QuestionPersonaAssignment,
    SessionAction,
    SessionParticipant,
    SimulationSession,
)
from group_interview_arena_api.modules.discussion_sessions.domain import (
    CurrentFloorGrantSnapshot,
    DeadlineReconciliationOutcome,
    FloorLifecycleSnapshot,
    FloorParticipantSnapshot,
    FloorSnapshot,
    InvalidSessionStateError,
    PendingEvent,
    PhaseDurationPlan,
    SessionCommand,
    SessionSnapshot,
    SessionStatus,
    StoredEvent,
    decide_session_command,
    reconcile_due_transitions,
)
from group_interview_arena_api.modules.floor_control.domain import FloorReleaseReason
from group_interview_arena_api.modules.floor_control.lifecycle import (
    release_active_floor_for_lifecycle,
)
from group_interview_arena_api.modules.question_personas.service import (
    QuestionNotFoundError,
    QuestionPersistenceError,
    require_selectable_question_version,
)


class SessionNotFoundError(Exception):
    pass


class ActionIdConflictError(Exception):
    pass


class SequenceAheadError(Exception):
    pass


class SessionPersistenceError(Exception):
    pass


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _raise_persistence_error() -> Never:
    raise SessionPersistenceError from None


def _participant_snapshot(row: SessionParticipant) -> FloorParticipantSnapshot:
    return FloorParticipantSnapshot(
        participant_id=row.id,
        actor_kind=row.actor_kind,
        seat_order=row.seat_order,
    )


def _snapshot(
    row: SimulationSession,
    *,
    floor: FloorSnapshot | None = None,
) -> SessionSnapshot:
    server_now = _utc_now()
    return SessionSnapshot(
        session_id=row.id,
        question_version_id=row.question_version_id,
        status=SessionStatus(row.status),
        phase_started_at=row.phase_started_at,
        phase_deadline_at=row.phase_deadline_at,
        server_now=server_now,
        created_at=row.created_at,
        updated_at=row.updated_at,
        last_sequence=row.last_sequence,
        floor=floor or FloorSnapshot(),
    )


def _floor_lifecycle_snapshot(row: DiscussionEvent) -> FloorLifecycleSnapshot:
    payload = row.payload
    event_type = row.event_type
    return FloorLifecycleSnapshot(
        event_type=event_type,
        sequence=row.sequence,
        occurred_at=row.occurred_at,
        phase=SessionStatus(str(payload["phase"])),
        reason_code=str(payload["reason_code"]),
        grant_id=(
            UUID(str(payload["grant_id"]))
            if event_type in {"floor.granted", "floor.released"}
            else None
        ),
        participant_id=(
            UUID(str(payload["participant_id"]))
            if event_type in {"floor.granted", "floor.released"}
            else None
        ),
        intervention_id=(
            UUID(str(payload["intervention_id"]))
            if event_type == "floor.intervention_requested"
            else None
        ),
        intervention_kind=(
            str(payload["intervention_kind"])
            if event_type == "floor.intervention_requested"
            else None
        ),
    )


async def _load_floor_snapshot(
    session: AsyncSession,
    row: SimulationSession,
) -> FloorSnapshot:
    participants = tuple(
        _participant_snapshot(participant)
        for participant in (
            await session.scalars(
                select(SessionParticipant)
                .where(SessionParticipant.session_id == row.id)
                .order_by(SessionParticipant.seat_order, SessionParticipant.id)
            )
        ).all()
    )

    current_grant: CurrentFloorGrantSnapshot | None = None
    if row.current_floor_grant_id is not None:
        grant_result = (
            await session.execute(
                select(FloorGrant, FloorDecision)
                .join(FloorDecision, FloorDecision.id == FloorGrant.decision_id)
                .where(
                    FloorGrant.session_id == row.id,
                    FloorGrant.id == row.current_floor_grant_id,
                )
            )
        ).one()
        grant, decision = grant_result
        current_grant = CurrentFloorGrantSnapshot(
            grant_id=grant.id,
            participant_id=grant.participant_id,
            phase=SessionStatus(grant.phase),
            reason_code=decision.primary_reason_code,
            granted_at=grant.granted_at,
        )

    latest_event_row = await session.scalar(
        select(DiscussionEvent)
        .where(
            DiscussionEvent.session_id == row.id,
            DiscussionEvent.event_type.in_(
                (
                    "floor.granted",
                    "floor.released",
                    "floor.intervention_requested",
                )
            ),
        )
        .order_by(DiscussionEvent.sequence.desc())
        .limit(1)
    )
    return FloorSnapshot(
        participants=participants,
        current_grant=current_grant,
        latest_event=(
            _floor_lifecycle_snapshot(latest_event_row)
            if latest_event_row is not None
            else None
        ),
    )


def _stored_event(row: DiscussionEvent) -> StoredEvent:
    return StoredEvent(
        event_version=row.event_version,
        event_type=row.event_type,
        session_id=row.session_id,
        sequence=row.sequence,
        occurred_at=row.occurred_at,
        causation_action_id=row.causation_action_id,
        payload=row.payload,
    )


def _command_digest(command: SessionCommand) -> bytes:
    semantic_payload = {
        "schema_version": command.schema_version,
        "type": command.command_type,
        "payload": command.payload,
    }
    encoded = json.dumps(
        semantic_payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).digest()


def _duration_plan_from_row(row: SimulationSession) -> PhaseDurationPlan | None:
    if row.phase_duration_plan is None:
        return None
    return PhaseDurationPlan.from_seconds(row.phase_duration_plan)


def _apply_reconciliation_to_aggregate(
    aggregate: SimulationSession,
    outcome: DeadlineReconciliationOutcome,
    *,
    now: datetime,
    event_count: int,
) -> None:
    aggregate.status = outcome.status.value
    aggregate.phase_started_at = outcome.phase_started_at
    aggregate.phase_deadline_at = outcome.phase_deadline_at
    if event_count:
        aggregate.updated_at = now
        aggregate.last_sequence += event_count


def _event_rows(
    *,
    session_id: UUID,
    first_sequence: int,
    events: list[PendingEvent],
    occurred_at: datetime,
    action_id: UUID | None,
) -> list[DiscussionEvent]:
    return [
        DiscussionEvent(
            session_id=session_id,
            sequence=first_sequence + offset,
            event_version=pending.event_version,
            event_type=pending.event_type,
            causation_action_id=action_id,
            payload=pending.payload,
            occurred_at=occurred_at,
        )
        for offset, pending in enumerate(events)
    ]


async def reconcile_due_for_locked_aggregate(
    session: AsyncSession,
    aggregate: SimulationSession,
    *,
    now: datetime,
) -> list[DiscussionEvent]:
    outcome = reconcile_due_transitions(
        status=SessionStatus(aggregate.status),
        phase_started_at=aggregate.phase_started_at,
        phase_deadline_at=aggregate.phase_deadline_at,
        duration_plan=_duration_plan_from_row(aggregate),
        now=now,
    )
    if not outcome.events:
        return []

    pending_events: list[PendingEvent] = []
    release_event = await release_active_floor_for_lifecycle(
        session,
        aggregate,
        reason=FloorReleaseReason.PHASE_CHANGED,
        occurred_at=now,
        action_id=None,
    )
    if release_event is not None:
        pending_events.append(release_event)
    pending_events.extend(outcome.events)

    first_sequence = aggregate.last_sequence + 1
    _apply_reconciliation_to_aggregate(
        aggregate,
        outcome,
        now=now,
        event_count=len(pending_events),
    )
    return _event_rows(
        session_id=aggregate.id,
        first_sequence=first_sequence,
        events=pending_events,
        occurred_at=now,
        action_id=None,
    )


async def create_session(
    session: AsyncSession,
    *,
    owner_id: UUID,
    question_version_id: UUID,
) -> SessionSnapshot:
    now = _utc_now()
    row = SimulationSession(
        id=uuid4(),
        owner_user_id=owner_id,
        question_version_id=question_version_id,
        status=SessionStatus.CREATED.value,
        last_sequence=1,
        created_at=now,
        updated_at=now,
    )
    event = DiscussionEvent(
        session_id=row.id,
        sequence=1,
        event_version=1,
        event_type="session.created",
        causation_action_id=None,
        payload={"status": SessionStatus.CREATED.value},
        occurred_at=now,
    )
    try:
        async with session.begin():
            await require_selectable_question_version(session, question_version_id)
            session.add(row)
            await session.flush()
            assignments = list(
                (
                    await session.scalars(
                        select(QuestionPersonaAssignment)
                        .where(
                            QuestionPersonaAssignment.question_version_id
                            == question_version_id
                        )
                        .order_by(QuestionPersonaAssignment.slot)
                    )
                ).all()
            )
            if len(assignments) != 3 or [item.slot for item in assignments] != [
                1,
                2,
                3,
            ]:
                raise ValueError(
                    "Selectable question has an invalid participant roster."
                )
            human_participant = SessionParticipant(
                id=uuid4(),
                session_id=row.id,
                actor_kind="HUMAN",
                participation_role="CANDIDATE",
                seat_order=1,
                availability="AVAILABLE",
                user_id=owner_id,
                question_persona_assignment_id=None,
                created_at=now,
            )
            ai_participants = [
                SessionParticipant(
                    id=uuid4(),
                    session_id=row.id,
                    actor_kind="AI",
                    participation_role="CANDIDATE",
                    seat_order=assignment.slot + 1,
                    availability="AVAILABLE",
                    user_id=None,
                    question_persona_assignment_id=assignment.id,
                    created_at=now,
                )
                for assignment in assignments
            ]
            session.add(human_participant)
            session.add_all(ai_participants)
            session.add(event)
            await session.flush()
    except QuestionNotFoundError:
        raise
    except QuestionPersistenceError, SQLAlchemyError, ValueError:
        _raise_persistence_error()
    return _snapshot(
        row,
        floor=FloorSnapshot(
            participants=tuple(
                _participant_snapshot(participant)
                for participant in [human_participant, *ai_participants]
            )
        ),
    )


async def get_session_snapshot(
    session: AsyncSession,
    *,
    owner_id: UUID,
    session_id: UUID,
) -> SessionSnapshot:
    try:
        row = await session.scalar(
            select(SimulationSession)
            .where(
                SimulationSession.id == session_id,
                SimulationSession.owner_user_id == owner_id,
            )
            .with_for_update(read=True)
        )
    except SQLAlchemyError:
        _raise_persistence_error()
    if row is None:
        raise SessionNotFoundError
    try:
        floor = await _load_floor_snapshot(session, row)
    except SQLAlchemyError, KeyError, TypeError, ValueError:
        _raise_persistence_error()
    return _snapshot(row, floor=floor)


async def _events_for_action(
    session: AsyncSession,
    *,
    session_id: UUID,
    action_id: UUID,
) -> list[StoredEvent]:
    rows = list(
        (
            await session.scalars(
                select(DiscussionEvent)
                .where(
                    DiscussionEvent.session_id == session_id,
                    DiscussionEvent.causation_action_id == action_id,
                )
                .order_by(DiscussionEvent.sequence)
            )
        ).all()
    )
    return [_stored_event(row) for row in rows]


async def apply_session_command(
    session: AsyncSession,
    *,
    owner_id: UUID,
    command: SessionCommand,
    duration_plan: PhaseDurationPlan | None = None,
) -> list[StoredEvent]:
    digest = _command_digest(command)
    pending_invalid_state: InvalidSessionStateError | None = None
    stored_events: list[StoredEvent] = []
    try:
        async with session.begin():
            aggregate = await session.scalar(
                select(SimulationSession)
                .where(
                    SimulationSession.id == command.session_id,
                    SimulationSession.owner_user_id == owner_id,
                )
                .with_for_update()
            )
            if aggregate is None:
                raise SessionNotFoundError

            accepted_action = await session.get(
                SessionAction,
                (command.session_id, command.action_id),
            )
            if accepted_action is not None:
                if (
                    accepted_action.command_version != command.schema_version
                    or accepted_action.command_type != command.command_type
                    or accepted_action.payload_digest != digest
                ):
                    raise ActionIdConflictError
                return await _events_for_action(
                    session,
                    session_id=command.session_id,
                    action_id=command.action_id,
                )

            now = _utc_now()
            system_event_rows = await reconcile_due_for_locked_aggregate(
                session,
                aggregate,
                now=now,
            )
            if system_event_rows:
                session.add_all(system_event_rows)
                await session.flush()

            try:
                outcome = decide_session_command(
                    SessionStatus(aggregate.status),
                    command,
                    now=now,
                    duration_plan=duration_plan,
                )
            except InvalidSessionStateError as exception:
                pending_invalid_state = exception
                stored_events = [_stored_event(row) for row in system_event_rows]
            else:
                session.add(
                    SessionAction(
                        session_id=command.session_id,
                        action_id=command.action_id,
                        command_version=command.schema_version,
                        command_type=command.command_type,
                        payload_digest=digest,
                        created_at=now,
                    )
                )
                await session.flush()

                pending_events = list(outcome.events)
                if outcome.status in {
                    SessionStatus.COMPLETED,
                    SessionStatus.ABORTED_USER,
                }:
                    release_event = await release_active_floor_for_lifecycle(
                        session,
                        aggregate,
                        reason=FloorReleaseReason.SESSION_TERMINATED,
                        occurred_at=now,
                        action_id=command.action_id,
                    )
                    if release_event is not None:
                        pending_events.insert(0, release_event)

                first_sequence = aggregate.last_sequence + 1
                aggregate.status = outcome.status.value
                aggregate.phase_started_at = outcome.phase_started_at
                aggregate.phase_deadline_at = outcome.phase_deadline_at
                if outcome.frozen_duration_plan is not None:
                    aggregate.phase_duration_plan = outcome.frozen_duration_plan
                aggregate.updated_at = now
                aggregate.last_sequence += len(pending_events)
                event_rows = _event_rows(
                    session_id=command.session_id,
                    first_sequence=first_sequence,
                    events=pending_events,
                    occurred_at=now,
                    action_id=command.action_id,
                )
                session.add_all(event_rows)
                await session.flush()
                stored_events = [_stored_event(row) for row in event_rows]
    except SessionNotFoundError, ActionIdConflictError:
        raise
    except ValueError:
        _raise_persistence_error()
    except SQLAlchemyError:
        _raise_persistence_error()
    if pending_invalid_state is not None:
        raise pending_invalid_state
    return stored_events


async def reconcile_session_deadline(
    session: AsyncSession,
    *,
    owner_id: UUID,
    session_id: UUID,
    now: datetime | None = None,
) -> list[StoredEvent]:
    effective_now = _utc_now() if now is None else now
    try:
        async with session.begin():
            aggregate = await session.scalar(
                select(SimulationSession)
                .where(
                    SimulationSession.id == session_id,
                    SimulationSession.owner_user_id == owner_id,
                )
                .with_for_update()
            )
            if aggregate is None:
                raise SessionNotFoundError

            event_rows = await reconcile_due_for_locked_aggregate(
                session,
                aggregate,
                now=effective_now,
            )
            if event_rows:
                session.add_all(event_rows)
                await session.flush()
            stored_events = [_stored_event(row) for row in event_rows]
    except SessionNotFoundError:
        raise
    except ValueError:
        _raise_persistence_error()
    except SQLAlchemyError:
        _raise_persistence_error()
    return stored_events


async def load_reconnect_events(
    session: AsyncSession,
    *,
    owner_id: UUID,
    session_id: UUID,
    after_sequence: int,
) -> list[StoredEvent]:
    try:
        aggregate = await session.scalar(
            select(SimulationSession).where(
                SimulationSession.id == session_id,
                SimulationSession.owner_user_id == owner_id,
            )
        )
        if aggregate is None:
            raise SessionNotFoundError
        if after_sequence > aggregate.last_sequence:
            raise SequenceAheadError
        rows = list(
            (
                await session.scalars(
                    select(DiscussionEvent)
                    .where(
                        DiscussionEvent.session_id == session_id,
                        DiscussionEvent.sequence > after_sequence,
                    )
                    .order_by(DiscussionEvent.sequence)
                )
            ).all()
        )
    except SessionNotFoundError, SequenceAheadError:
        raise
    except SQLAlchemyError:
        _raise_persistence_error()
    return [_stored_event(row) for row in rows]
