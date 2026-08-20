import hashlib
import json
from datetime import UTC, datetime
from typing import Never
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from group_interview_arena_api.db.models import (
    DiscussionEvent,
    FloorDecision,
    FloorGrant,
    FloorIntervention,
    FloorRelease,
    SessionAction,
    SessionParticipant,
    SimulationSession,
    SpeakingOpportunity,
)
from group_interview_arena_api.modules.discussion_sessions.domain import (
    PendingEvent,
    SessionStatus,
    StoredEvent,
)
from group_interview_arena_api.modules.discussion_sessions.service import (
    ActionIdConflictError,
    SessionNotFoundError,
    SessionPersistenceError,
    reconcile_due_for_locked_aggregate,
)
from group_interview_arena_api.modules.floor_control.domain import (
    FloorCommand,
    FloorDecisionOutcome,
    FloorDecisionRecord,
    GrantFloorCommand,
    IneligibleParticipantError,
    InvalidFloorStateError,
    ParticipantActorKind,
    ParticipantAvailability,
    ParticipationRole,
    ReleaseFloorCommand,
    RequestFloorInterventionCommand,
    SpeakingOpportunityKind,
    StaleFloorDecisionError,
    floor_granted_event,
    floor_intervention_requested_event,
    require_command_version,
    require_floor_phase,
    require_fresh_sequence,
    require_ordinary_floor_eligibility,
)
from group_interview_arena_api.modules.floor_control.lifecycle import (
    release_active_floor_for_lifecycle,
)
from group_interview_arena_api.modules.floor_control.scheduler import (
    ScheduleFloorCommand,
    SchedulerGrantHistory,
    SchedulerInput,
    SchedulerOpportunity,
    SchedulerParticipant,
    decide_floor,
)


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _raise_persistence_error() -> Never:
    raise SessionPersistenceError from None


def _stored_event(row: DiscussionEvent) -> StoredEvent:
    return StoredEvent(
        event_version=row.event_version,
        event_type=row.event_type,
        session_id=row.session_id,
        sequence=row.sequence,
        occurred_at=row.occurred_at,
        action_id=row.causation_action_id,
        payload=row.payload,
    )


def _decision_payload(decision: FloorDecisionRecord) -> dict[str, object]:
    return {
        "decision_id": str(decision.decision_id),
        "phase": decision.phase.value,
        "expected_last_sequence": decision.expected_last_sequence,
        "outcome": decision.outcome.value,
        "selected_participant_id": (
            str(decision.selected_participant_id)
            if decision.selected_participant_id is not None
            else None
        ),
        "opportunity_id": (
            str(decision.opportunity_id)
            if decision.opportunity_id is not None
            else None
        ),
        "intervention_kind": (
            decision.intervention_kind.value
            if decision.intervention_kind is not None
            else None
        ),
        "policy_version": decision.policy_version,
        "primary_reason": decision.primary_reason.value,
        "supporting_reasons": [item.value for item in decision.supporting_reasons],
        "metadata": decision.metadata.to_json(),
    }


def _semantic_payload(command: FloorCommand) -> dict[str, object]:
    if isinstance(command, GrantFloorCommand):
        payload: dict[str, object] = {
            "grant_id": str(command.grant_id),
            "decision": _decision_payload(command.decision),
        }
    elif isinstance(command, ReleaseFloorCommand):
        payload = {
            "grant_id": str(command.grant_id),
            "expected_phase": command.expected_phase.value,
            "expected_last_sequence": command.expected_last_sequence,
            "reason": command.reason.value,
        }
    else:
        payload = {
            "intervention_id": str(command.intervention_id),
            "decision": _decision_payload(command.decision),
        }
    return {
        "schema_version": command.schema_version,
        "type": command.command_type,
        "payload": payload,
    }


def _command_digest(command: FloorCommand) -> bytes:
    encoded = json.dumps(
        _semantic_payload(command),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).digest()


def _schedule_payload(command: ScheduleFloorCommand) -> dict[str, object]:
    policy = command.policy
    return {
        "schema_version": command.schema_version,
        "type": command.command_type,
        "payload": {
            "decision_id": str(command.decision_id),
            "grant_id": str(command.grant_id),
            "intervention_id": str(command.intervention_id),
            "expected_phase": command.expected_phase.value,
            "expected_last_sequence": command.expected_last_sequence,
            "expected_current_floor_grant_id": (
                str(command.expected_current_floor_grant_id)
                if command.expected_current_floor_grant_id is not None
                else None
            ),
            "evaluated_at": command.evaluated_at.isoformat(),
            "policy": {
                "version": policy.version,
                "opportunity_order": [item.value for item in policy.opportunity_order],
                "max_consecutive_grants": policy.max_consecutive_grants,
                "max_phase_grants": policy.max_phase_grants,
                "silence_threshold_seconds": policy.silence_threshold.total_seconds(),
                "deadline_intervention_threshold_seconds": (
                    policy.deadline_intervention_threshold.total_seconds()
                ),
            },
        },
    }


def _schedule_digest(command: ScheduleFloorCommand) -> bytes:
    encoded = json.dumps(
        _schedule_payload(command),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).digest()


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


def _event_rows(
    *,
    session_id: UUID,
    first_sequence: int,
    events: list[PendingEvent],
    occurred_at: datetime,
    action_id: UUID,
) -> list[DiscussionEvent]:
    return [
        DiscussionEvent(
            session_id=session_id,
            sequence=first_sequence + offset,
            event_version=event.event_version,
            event_type=event.event_type,
            causation_action_id=action_id,
            payload=event.payload,
            occurred_at=occurred_at,
        )
        for offset, event in enumerate(events)
    ]


def _expected_sequence(command: FloorCommand) -> int:
    if isinstance(command, ReleaseFloorCommand):
        return command.expected_last_sequence
    return command.decision.expected_last_sequence


def _expected_phase(command: FloorCommand) -> SessionStatus:
    if isinstance(command, ReleaseFloorCommand):
        return command.expected_phase
    return command.decision.phase


def _decision_row(
    *,
    session_id: UUID,
    decision: FloorDecisionRecord,
    decided_at: datetime,
) -> FloorDecision:
    return FloorDecision(
        id=decision.decision_id,
        session_id=session_id,
        phase=decision.phase.value,
        expected_last_sequence=decision.expected_last_sequence,
        outcome_kind=decision.outcome.value,
        selected_participant_id=decision.selected_participant_id,
        opportunity_id=decision.opportunity_id,
        intervention_kind=(
            decision.intervention_kind.value
            if decision.intervention_kind is not None
            else None
        ),
        policy_version=decision.policy_version,
        primary_reason_code=decision.primary_reason.value,
        supporting_reason_codes=[item.value for item in decision.supporting_reasons],
        decision_metadata=decision.metadata.to_json(),
        decided_at=decided_at,
    )


async def _grant_floor(
    session: AsyncSession,
    aggregate: SimulationSession,
    command: GrantFloorCommand,
    *,
    now: datetime,
) -> PendingEvent:
    decision = command.decision
    if decision.outcome is not FloorDecisionOutcome.GRANT:
        raise ValueError("Grant command requires a grant decision.")
    if aggregate.current_floor_grant_id is not None:
        raise InvalidFloorStateError("Session already has an active floor grant.")
    participant_id = decision.selected_participant_id
    if participant_id is None:
        raise ValueError("Grant decision is missing its participant.")
    participant = await session.get(SessionParticipant, participant_id)
    if participant is None or participant.session_id != aggregate.id:
        raise IneligibleParticipantError("Participant does not belong to session.")
    require_ordinary_floor_eligibility(
        actor_kind=ParticipantActorKind(participant.actor_kind),
        participation_role=ParticipationRole(participant.participation_role),
        availability=ParticipantAvailability(participant.availability),
    )

    if decision.opportunity_id is not None:
        opportunity = await session.get(SpeakingOpportunity, decision.opportunity_id)
        if (
            opportunity is None
            or opportunity.session_id != aggregate.id
            or opportunity.participant_id != participant.id
            or opportunity.phase != decision.phase.value
        ):
            raise InvalidFloorStateError("Speaking opportunity is not applicable.")

    session.add(
        _decision_row(session_id=aggregate.id, decision=decision, decided_at=now)
    )
    await session.flush()
    grant = FloorGrant(
        id=command.grant_id,
        session_id=aggregate.id,
        participant_id=participant.id,
        decision_id=decision.decision_id,
        opportunity_id=decision.opportunity_id,
        phase=decision.phase.value,
        granted_at=now,
    )
    session.add(grant)
    await session.flush()
    aggregate.current_floor_grant_id = grant.id
    return floor_granted_event(grant_id=grant.id, decision=decision)


async def _release_floor(
    session: AsyncSession,
    aggregate: SimulationSession,
    command: ReleaseFloorCommand,
    *,
    now: datetime,
) -> PendingEvent:
    if aggregate.current_floor_grant_id != command.grant_id:
        raise InvalidFloorStateError("Floor release does not match current grant.")
    event = await release_active_floor_for_lifecycle(
        session,
        aggregate,
        reason=command.reason,
        occurred_at=now,
        action_id=command.action_id,
    )
    if event is None:
        raise InvalidFloorStateError("Session has no active floor grant.")
    return event


async def _request_intervention(
    session: AsyncSession,
    aggregate: SimulationSession,
    command: RequestFloorInterventionCommand,
    *,
    now: datetime,
) -> PendingEvent:
    decision = command.decision
    if decision.outcome is not FloorDecisionOutcome.REQUEST_INTERVENTION:
        raise ValueError("Intervention command requires an intervention decision.")
    if decision.intervention_kind is None:
        raise ValueError("Intervention decision is missing its kind.")
    session.add(
        _decision_row(session_id=aggregate.id, decision=decision, decided_at=now)
    )
    await session.flush()
    session.add(
        FloorIntervention(
            id=command.intervention_id,
            session_id=aggregate.id,
            decision_id=decision.decision_id,
            intervention_kind=decision.intervention_kind.value,
            requested_at=now,
        )
    )
    return floor_intervention_requested_event(
        intervention_id=command.intervention_id,
        decision=decision,
    )


async def _scheduler_input(
    session: AsyncSession,
    aggregate: SimulationSession,
    command: ScheduleFloorCommand,
) -> SchedulerInput:
    phase = SessionStatus(aggregate.status)
    if aggregate.phase_started_at is None or aggregate.phase_deadline_at is None:
        raise InvalidFloorStateError("Floor-enabled phase timing is missing.")

    participant_rows = list(
        (
            await session.scalars(
                select(SessionParticipant)
                .where(SessionParticipant.session_id == aggregate.id)
                .order_by(
                    SessionParticipant.seat_order,
                    SessionParticipant.id,
                )
            )
        ).all()
    )
    consumed_opportunity_ids = set(
        (
            await session.scalars(
                select(FloorGrant.opportunity_id).where(
                    FloorGrant.session_id == aggregate.id,
                    FloorGrant.opportunity_id.is_not(None),
                )
            )
        ).all()
    )
    opportunity_rows = list(
        (
            await session.scalars(
                select(SpeakingOpportunity)
                .where(
                    SpeakingOpportunity.session_id == aggregate.id,
                    SpeakingOpportunity.phase == phase.value,
                )
                .order_by(
                    SpeakingOpportunity.created_at,
                    SpeakingOpportunity.id,
                )
            )
        ).all()
    )
    history_rows = list(
        (
            await session.execute(
                select(FloorGrant, FloorRelease)
                .outerjoin(FloorRelease, FloorRelease.grant_id == FloorGrant.id)
                .where(FloorGrant.session_id == aggregate.id)
                .order_by(FloorGrant.granted_at, FloorGrant.id)
            )
        ).all()
    )
    return SchedulerInput(
        decision_id=command.decision_id,
        phase=phase,
        expected_last_sequence=command.expected_last_sequence,
        now=command.evaluated_at,
        phase_started_at=aggregate.phase_started_at,
        phase_deadline_at=aggregate.phase_deadline_at,
        participants=tuple(
            SchedulerParticipant(
                participant_id=row.id,
                actor_kind=ParticipantActorKind(row.actor_kind),
                participation_role=ParticipationRole(row.participation_role),
                availability=ParticipantAvailability(row.availability),
                seat_order=row.seat_order,
            )
            for row in participant_rows
        ),
        opportunities=tuple(
            SchedulerOpportunity(
                opportunity_id=row.id,
                participant_id=row.participant_id,
                kind=SpeakingOpportunityKind(row.opportunity_kind),
                created_at=row.created_at,
            )
            for row in opportunity_rows
            if row.id not in consumed_opportunity_ids
        ),
        grant_history=tuple(
            SchedulerGrantHistory(
                grant_id=grant.id,
                participant_id=grant.participant_id,
                phase=SessionStatus(grant.phase),
                granted_at=grant.granted_at,
                released_at=(release.released_at if release is not None else None),
            )
            for grant, release in history_rows
        ),
    )


async def apply_scheduler_command(
    session: AsyncSession,
    *,
    owner_id: UUID,
    command: ScheduleFloorCommand,
) -> list[StoredEvent]:
    digest = _schedule_digest(command)
    pending_error: Exception | None = None
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

            system_event_rows = await reconcile_due_for_locked_aggregate(
                session,
                aggregate,
                now=command.evaluated_at,
            )
            if system_event_rows:
                session.add_all(system_event_rows)
                await session.flush()

            try:
                require_floor_phase(SessionStatus(aggregate.status))
                if SessionStatus(aggregate.status) is not command.expected_phase:
                    raise StaleFloorDecisionError("Floor decision phase is stale.")
                require_fresh_sequence(
                    actual=aggregate.last_sequence,
                    expected=command.expected_last_sequence,
                )
                if (
                    aggregate.current_floor_grant_id
                    != command.expected_current_floor_grant_id
                ):
                    raise StaleFloorDecisionError(
                        "Current floor precondition is stale."
                    )
                if aggregate.current_floor_grant_id is not None:
                    raise InvalidFloorStateError(
                        "Cannot schedule while a floor grant is active."
                    )
            except (InvalidFloorStateError, StaleFloorDecisionError) as exception:
                pending_error = exception
            else:
                scheduler_input = await _scheduler_input(session, aggregate, command)
                decision = decide_floor(scheduler_input, command.policy)
                session.add(
                    SessionAction(
                        session_id=command.session_id,
                        action_id=command.action_id,
                        command_version=command.schema_version,
                        command_type=command.command_type,
                        payload_digest=digest,
                        created_at=command.evaluated_at,
                    )
                )
                await session.flush()

                event: PendingEvent | None
                if decision.outcome is FloorDecisionOutcome.GRANT:
                    event = await _grant_floor(
                        session,
                        aggregate,
                        GrantFloorCommand(
                            session_id=command.session_id,
                            action_id=command.action_id,
                            grant_id=command.grant_id,
                            decision=decision,
                        ),
                        now=command.evaluated_at,
                    )
                elif decision.outcome is FloorDecisionOutcome.REQUEST_INTERVENTION:
                    event = await _request_intervention(
                        session,
                        aggregate,
                        RequestFloorInterventionCommand(
                            session_id=command.session_id,
                            action_id=command.action_id,
                            intervention_id=command.intervention_id,
                            decision=decision,
                        ),
                        now=command.evaluated_at,
                    )
                else:
                    session.add(
                        _decision_row(
                            session_id=aggregate.id,
                            decision=decision,
                            decided_at=command.evaluated_at,
                        )
                    )
                    event = None

                aggregate.updated_at = command.evaluated_at
                if event is not None:
                    first_sequence = aggregate.last_sequence + 1
                    aggregate.last_sequence = first_sequence
                    event_rows = _event_rows(
                        session_id=command.session_id,
                        first_sequence=first_sequence,
                        events=[event],
                        occurred_at=command.evaluated_at,
                        action_id=command.action_id,
                    )
                    session.add_all(event_rows)
                    await session.flush()
                    stored_events = [_stored_event(row) for row in event_rows]
                else:
                    await session.flush()
    except (
        SessionNotFoundError,
        ActionIdConflictError,
        InvalidFloorStateError,
        StaleFloorDecisionError,
        IneligibleParticipantError,
    ):
        raise
    except ValueError:
        _raise_persistence_error()
    except SQLAlchemyError:
        _raise_persistence_error()
    if pending_error is not None:
        raise pending_error
    return stored_events


async def apply_floor_command(
    session: AsyncSession,
    *,
    owner_id: UUID,
    command: FloorCommand,
) -> list[StoredEvent]:
    require_command_version(command)
    digest = _command_digest(command)
    pending_error: Exception | None = None
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
                require_floor_phase(SessionStatus(aggregate.status))
                if SessionStatus(aggregate.status) is not _expected_phase(command):
                    raise StaleFloorDecisionError("Floor decision phase is stale.")
                require_fresh_sequence(
                    actual=aggregate.last_sequence,
                    expected=_expected_sequence(command),
                )
            except (InvalidFloorStateError, StaleFloorDecisionError) as exception:
                pending_error = exception
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

                if isinstance(command, GrantFloorCommand):
                    event = await _grant_floor(session, aggregate, command, now=now)
                elif isinstance(command, ReleaseFloorCommand):
                    event = await _release_floor(session, aggregate, command, now=now)
                else:
                    event = await _request_intervention(
                        session,
                        aggregate,
                        command,
                        now=now,
                    )

                first_sequence = aggregate.last_sequence + 1
                aggregate.last_sequence = first_sequence
                aggregate.updated_at = now
                event_rows = _event_rows(
                    session_id=command.session_id,
                    first_sequence=first_sequence,
                    events=[event],
                    occurred_at=now,
                    action_id=command.action_id,
                )
                session.add_all(event_rows)
                await session.flush()
                stored_events = [_stored_event(row) for row in event_rows]
    except (
        SessionNotFoundError,
        ActionIdConflictError,
        InvalidFloorStateError,
        StaleFloorDecisionError,
        IneligibleParticipantError,
    ):
        raise
    except ValueError:
        _raise_persistence_error()
    except SQLAlchemyError:
        _raise_persistence_error()
    if pending_error is not None:
        raise pending_error
    return stored_events
