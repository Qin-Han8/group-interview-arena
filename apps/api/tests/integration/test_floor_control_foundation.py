import asyncio
from collections.abc import Callable, Coroutine
from contextlib import asynccontextmanager
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from typing import Any, Protocol
from uuid import UUID, uuid4

import pytest
from sqlalchemy import URL, delete, func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from group_interview_arena_api.core.config import DatabaseSettings
from group_interview_arena_api.db import (
    DiscussionEvent,
    FloorDecision,
    FloorGrant,
    FloorIntervention,
    FloorRelease,
    SessionAction,
    SessionParticipant,
    SimulationSession,
    SpeakingOpportunity,
    User,
)
from group_interview_arena_api.db.runtime import (
    create_database_engine,
    create_database_session_factory,
    dispose_database_engine,
)
from group_interview_arena_api.modules.discussion_sessions.domain import (
    PendingEvent,
    PhaseDurationPlan,
    SessionCommand,
    SessionStatus,
)
from group_interview_arena_api.modules.discussion_sessions.service import (
    ActionIdConflictError,
    SessionPersistenceError,
    apply_session_command,
    create_session,
    get_session_snapshot,
    reconcile_session_deadline,
)
from group_interview_arena_api.modules.floor_control import service
from group_interview_arena_api.modules.floor_control.domain import (
    FloorDecisionOutcome,
    FloorDecisionRecord,
    FloorInterventionKind,
    FloorPolicyReason,
    FloorReleaseReason,
    GrantFloorCommand,
    IneligibleParticipantError,
    InvalidFloorStateError,
    ReleaseFloorCommand,
    RequestFloorInterventionCommand,
    SafeDecisionMetadata,
    StaleFloorDecisionError,
)
from group_interview_arena_api.modules.floor_control.scheduler import (
    V0_1_SCHEDULER_POLICY,
    ScheduleFloorCommand,
)
from group_interview_arena_api.modules.floor_control.service import (
    apply_floor_command,
    apply_scheduler_command,
)
from group_interview_arena_api.modules.question_personas.seed import (
    INTERNAL_VALIDATION_BUNDLE,
    seed_question_persona_foundation,
)

pytestmark = pytest.mark.integration
PLAN = PhaseDurationPlan.from_seconds(
    {
        SessionStatus.PREPARATION: 1,
        SessionStatus.OPENING_STATEMENTS: 2,
        SessionStatus.EXPLORATION: 3,
        SessionStatus.CONFLICT_AND_EVALUATION: 4,
        SessionStatus.CONVERGENCE: 5,
        SessionStatus.FINAL_SUMMARY: 6,
    }
)


class TemporaryDatabaseContext(Protocol):
    database_name: str
    database_url: URL

    def database_settings(self) -> DatabaseSettings: ...


def run_async[T](operation: Callable[[], Coroutine[Any, Any, T]]) -> T:
    return asyncio.run(operation(), loop_factory=asyncio.SelectorEventLoop)


@asynccontextmanager
async def _session_factory(temporary_database: TemporaryDatabaseContext):
    engine = create_database_engine(temporary_database.database_settings())
    session_factory = create_database_session_factory(engine)
    try:
        await seed_question_persona_foundation(session_factory)
        yield session_factory
    finally:
        await dispose_database_engine(engine)


async def _seed_user(session_factory: async_sessionmaker[AsyncSession]) -> UUID:
    user_id = uuid4()
    async with session_factory() as session:
        async with session.begin():
            session.add(
                User(
                    id=user_id,
                    username=f"floor_{user_id.hex[:12]}",
                    password_hash="test-only-password-hash",
                )
            )
    return user_id


async def _active_session(
    session_factory: async_sessionmaker[AsyncSession],
) -> tuple[UUID, UUID, list[SessionParticipant]]:
    owner_id = await _seed_user(session_factory)
    async with session_factory() as session:
        snapshot = await create_session(
            session,
            owner_id=owner_id,
            question_version_id=INTERNAL_VALIDATION_BUNDLE.version_id,
        )
    async with session_factory() as session:
        await apply_session_command(
            session,
            owner_id=owner_id,
            command=SessionCommand(
                schema_version=1,
                command_type="session.start",
                session_id=snapshot.session_id,
                action_id=uuid4(),
                payload={},
            ),
            duration_plan=PLAN,
        )
    async with session_factory() as session:
        started = await get_session_snapshot(
            session,
            owner_id=owner_id,
            session_id=snapshot.session_id,
        )
    assert started.phase_deadline_at is not None
    async with session_factory() as session:
        events = await reconcile_session_deadline(
            session,
            owner_id=owner_id,
            session_id=snapshot.session_id,
            now=started.phase_deadline_at,
        )
    assert [event.event_type for event in events] == ["session.state_changed"]
    async with session_factory() as session:
        participants = list(
            (
                await session.scalars(
                    select(SessionParticipant)
                    .where(SessionParticipant.session_id == snapshot.session_id)
                    .order_by(SessionParticipant.seat_order)
                )
            ).all()
        )
    return owner_id, snapshot.session_id, participants


def _metadata() -> SafeDecisionMetadata:
    return SafeDecisionMetadata(
        current_phase_grant_count=0,
        first_opportunity_unmet=True,
        previous_owner_was_selected=False,
        consecutive_grant_count=0,
        tie_break_class="SEAT_ORDER",
    )


def _grant(
    session_id: UUID,
    participant_id: UUID,
    *,
    action_id: UUID | None = None,
    grant_id: UUID | None = None,
    decision_id: UUID | None = None,
    expected_sequence: int = 3,
) -> GrantFloorCommand:
    return GrantFloorCommand(
        session_id=session_id,
        action_id=action_id or uuid4(),
        grant_id=grant_id or uuid4(),
        decision=FloorDecisionRecord(
            decision_id=decision_id or uuid4(),
            phase=SessionStatus.OPENING_STATEMENTS,
            expected_last_sequence=expected_sequence,
            outcome=FloorDecisionOutcome.GRANT,
            selected_participant_id=participant_id,
            opportunity_id=None,
            intervention_kind=None,
            policy_version="v0.1-floor-1",
            primary_reason=FloorPolicyReason.FIRST_OPPORTUNITY,
            supporting_reasons=(FloorPolicyReason.PHASE_MANDATED_TURN,),
            metadata=_metadata(),
        ),
    )


def _schedule(
    session_id: UUID,
    *,
    evaluated_at: datetime,
    expected_sequence: int = 3,
    action_id: UUID | None = None,
    decision_id: UUID | None = None,
    grant_id: UUID | None = None,
    intervention_id: UUID | None = None,
) -> ScheduleFloorCommand:
    return ScheduleFloorCommand(
        session_id=session_id,
        action_id=action_id or uuid4(),
        decision_id=decision_id or uuid4(),
        grant_id=grant_id or uuid4(),
        intervention_id=intervention_id or uuid4(),
        expected_phase=SessionStatus.OPENING_STATEMENTS,
        expected_last_sequence=expected_sequence,
        expected_current_floor_grant_id=None,
        evaluated_at=evaluated_at,
        policy=replace(
            V0_1_SCHEDULER_POLICY,
            deadline_intervention_threshold=timedelta(milliseconds=100),
        ),
    )


async def _verify_roster_and_lifecycle(
    temporary_database: TemporaryDatabaseContext,
) -> None:
    async with _session_factory(temporary_database) as session_factory:
        owner_id, session_id, participants = await _active_session(session_factory)
        assert [
            (item.actor_kind, item.participation_role, item.seat_order)
            for item in participants
        ] == [
            ("HUMAN", "CANDIDATE", 1),
            ("AI", "CANDIDATE", 2),
            ("AI", "CANDIDATE", 3),
            ("AI", "CANDIDATE", 4),
        ]
        assert participants[0].user_id == owner_id
        assert all(item.availability == "AVAILABLE" for item in participants)

        command = _grant(session_id, participants[1].id)
        async with session_factory() as session:
            granted = await apply_floor_command(
                session,
                owner_id=owner_id,
                command=command,
            )
        async with session_factory() as session:
            duplicate = await apply_floor_command(
                session,
                owner_id=owner_id,
                command=command,
            )
        assert granted == duplicate
        assert [(event.sequence, event.event_type) for event in granted] == [
            (4, "floor.granted")
        ]
        async with session_factory() as session:
            grant_snapshot = await get_session_snapshot(
                session,
                owner_id=owner_id,
                session_id=session_id,
            )
        assert [
            (item.actor_kind, item.seat_order)
            for item in grant_snapshot.floor.participants
        ] == [("HUMAN", 1), ("AI", 2), ("AI", 3), ("AI", 4)]
        assert grant_snapshot.floor.current_grant is not None
        assert grant_snapshot.floor.current_grant.grant_id == command.grant_id
        assert grant_snapshot.floor.current_grant.participant_id == participants[1].id
        assert grant_snapshot.floor.current_grant.reason_code == "FIRST_OPPORTUNITY"
        assert grant_snapshot.floor.latest_event is not None
        assert grant_snapshot.floor.latest_event.event_type == "floor.granted"
        assert grant_snapshot.floor.latest_event.sequence == 4

        conflict = _grant(
            session_id,
            participants[1].id,
            action_id=command.action_id,
        )
        async with session_factory() as session:
            with pytest.raises(ActionIdConflictError):
                await apply_floor_command(session, owner_id=owner_id, command=conflict)

        release = ReleaseFloorCommand(
            session_id=session_id,
            action_id=uuid4(),
            grant_id=command.grant_id,
            expected_phase=SessionStatus.OPENING_STATEMENTS,
            expected_last_sequence=4,
            reason=FloorReleaseReason.SPEAKER_FINISHED,
        )
        async with session_factory() as session:
            released = await apply_floor_command(
                session,
                owner_id=owner_id,
                command=release,
            )
        async with session_factory() as session:
            assert released == await apply_floor_command(
                session,
                owner_id=owner_id,
                command=release,
            )
        assert [(event.sequence, event.event_type) for event in released] == [
            (5, "floor.released")
        ]

        intervention = RequestFloorInterventionCommand(
            session_id=session_id,
            action_id=uuid4(),
            intervention_id=uuid4(),
            decision=FloorDecisionRecord(
                decision_id=uuid4(),
                phase=SessionStatus.OPENING_STATEMENTS,
                expected_last_sequence=5,
                outcome=FloorDecisionOutcome.REQUEST_INTERVENTION,
                selected_participant_id=None,
                opportunity_id=None,
                intervention_kind=FloorInterventionKind.SILENCE,
                policy_version="v0.1-floor-1",
                primary_reason=FloorPolicyReason.SILENCE_RECOVERY,
                supporting_reasons=(),
                metadata=_metadata(),
            ),
        )
        async with session_factory() as session:
            intervention_events = await apply_floor_command(
                session,
                owner_id=owner_id,
                command=intervention,
            )
        assert [
            (event.sequence, event.event_type) for event in intervention_events
        ] == [(6, "floor.intervention_requested")]

        async with session_factory() as session:
            restored_snapshot = await get_session_snapshot(
                session,
                owner_id=owner_id,
                session_id=session_id,
            )
        assert restored_snapshot.floor.current_grant is None
        assert restored_snapshot.floor.latest_event is not None
        assert (
            restored_snapshot.floor.latest_event.event_type
            == "floor.intervention_requested"
        )
        assert restored_snapshot.floor.latest_event.sequence == 6
        assert restored_snapshot.floor.latest_event.intervention_kind == "SILENCE"
        assert restored_snapshot.floor.latest_event.reason_code == "SILENCE_RECOVERY"

        async with session_factory() as session:
            aggregate = await session.get(SimulationSession, session_id)
            decision = await session.get(FloorDecision, command.decision.decision_id)
            grant = await session.get(FloorGrant, command.grant_id)
            release_row = await session.get(FloorRelease, command.grant_id)
            assert aggregate is not None and aggregate.current_floor_grant_id is None
            assert (
                decision is not None and grant is not None and release_row is not None
            )
            assert decision.decision_metadata == _metadata().to_json()
            assert decision.selected_participant_id == participants[1].id
            assert grant.decision_id == decision.id
            assert release_row.reason_code == "SPEAKER_FINISHED"
            assert (
                await session.scalar(
                    select(func.count()).select_from(FloorIntervention)
                )
                == 1
            )
            events = list(
                (
                    await session.scalars(
                        select(DiscussionEvent)
                        .where(DiscussionEvent.session_id == session_id)
                        .order_by(DiscussionEvent.sequence)
                    )
                ).all()
            )
            assert [item.sequence for item in events] == [1, 2, 3, 4, 5, 6]
            serialized = repr(
                [decision.decision_metadata, *[item.payload for item in events]]
            ).lower()
            for forbidden in (
                "private_stance",
                "persona_calibration",
                "policy_weights",
                "score",
            ):
                assert forbidden not in serialized

        async with session_factory() as session:
            with pytest.raises(IntegrityError):
                await session.execute(
                    update(FloorDecision)
                    .where(FloorDecision.id == command.decision.decision_id)
                    .values(
                        decision_metadata={
                            **_metadata().to_json(),
                            "private_stance": "must-not-persist",
                        }
                    )
                )
                await session.commit()
            await session.rollback()


def test_roster_grant_release_intervention_idempotency_and_audit_are_durable(
    migrated_database: TemporaryDatabaseContext,
) -> None:
    run_async(lambda: _verify_roster_and_lifecycle(migrated_database))


async def _verify_concurrent_grants(
    temporary_database: TemporaryDatabaseContext,
) -> None:
    async with _session_factory(temporary_database) as session_factory:
        owner_id, session_id, participants = await _active_session(session_factory)
        commands = [_grant(session_id, item.id) for item in participants[1:3]]

        async def apply(command: GrantFloorCommand) -> object:
            try:
                async with session_factory() as session:
                    return await apply_floor_command(
                        session,
                        owner_id=owner_id,
                        command=command,
                    )
            except Exception as exception:
                return exception

        outcomes = await asyncio.gather(*(apply(command) for command in commands))
        assert sum(isinstance(item, list) for item in outcomes) == 1
        assert sum(isinstance(item, StaleFloorDecisionError) for item in outcomes) == 1

        async with session_factory() as session:
            aggregate = await session.get(SimulationSession, session_id)
            assert (
                aggregate is not None and aggregate.current_floor_grant_id is not None
            )
            assert (
                await session.scalar(
                    select(func.count())
                    .select_from(FloorGrant)
                    .where(FloorGrant.session_id == session_id)
                )
                == 1
            )
            assert (
                await session.scalar(
                    select(func.count())
                    .select_from(FloorDecision)
                    .where(FloorDecision.session_id == session_id)
                )
                == 1
            )
            assert (
                await session.scalar(
                    select(func.count())
                    .select_from(SessionAction)
                    .where(SessionAction.session_id == session_id)
                )
                == 2
            )
            sequences = list(
                (
                    await session.scalars(
                        select(DiscussionEvent.sequence)
                        .where(DiscussionEvent.session_id == session_id)
                        .order_by(DiscussionEvent.sequence)
                    )
                ).all()
            )
            assert sequences == [1, 2, 3, 4]


def test_concurrent_grants_produce_one_active_floor_and_contiguous_sequence(
    migrated_database: TemporaryDatabaseContext,
) -> None:
    run_async(lambda: _verify_concurrent_grants(migrated_database))


async def _verify_concurrent_releases(
    temporary_database: TemporaryDatabaseContext,
) -> None:
    async with _session_factory(temporary_database) as session_factory:
        owner_id, session_id, participants = await _active_session(session_factory)
        grant = _grant(session_id, participants[1].id)
        async with session_factory() as session:
            await apply_floor_command(session, owner_id=owner_id, command=grant)

        commands = [
            ReleaseFloorCommand(
                session_id=session_id,
                action_id=uuid4(),
                grant_id=grant.grant_id,
                expected_phase=SessionStatus.OPENING_STATEMENTS,
                expected_last_sequence=4,
                reason=FloorReleaseReason.SPEAKER_FINISHED,
            )
            for _ in range(2)
        ]

        async def apply(command: ReleaseFloorCommand) -> object:
            try:
                async with session_factory() as session:
                    return await apply_floor_command(
                        session,
                        owner_id=owner_id,
                        command=command,
                    )
            except Exception as exception:
                return exception

        outcomes = await asyncio.gather(*(apply(command) for command in commands))
        assert sum(isinstance(item, list) for item in outcomes) == 1
        assert sum(isinstance(item, StaleFloorDecisionError) for item in outcomes) == 1

        async with session_factory() as session:
            aggregate = await session.get(SimulationSession, session_id)
            assert aggregate is not None and aggregate.current_floor_grant_id is None
            assert (
                await session.scalar(
                    select(func.count())
                    .select_from(FloorRelease)
                    .where(FloorRelease.session_id == session_id)
                )
                == 1
            )
            sequences = list(
                (
                    await session.scalars(
                        select(DiscussionEvent.sequence)
                        .where(DiscussionEvent.session_id == session_id)
                        .order_by(DiscussionEvent.sequence)
                    )
                ).all()
            )
            assert sequences == [1, 2, 3, 4, 5]


def test_concurrent_releases_produce_one_release_and_contiguous_sequence(
    migrated_database: TemporaryDatabaseContext,
) -> None:
    run_async(lambda: _verify_concurrent_releases(migrated_database))


async def _verify_phase_cleanup_and_terminal_protection(
    temporary_database: TemporaryDatabaseContext,
) -> None:
    async with _session_factory(temporary_database) as session_factory:
        owner_id, session_id, participants = await _active_session(session_factory)
        command = _grant(session_id, participants[1].id)
        async with session_factory() as session:
            await apply_floor_command(session, owner_id=owner_id, command=command)
        async with session_factory() as session:
            snapshot = await get_session_snapshot(
                session,
                owner_id=owner_id,
                session_id=session_id,
            )
        assert snapshot.phase_deadline_at is not None
        async with session_factory() as session:
            events = await reconcile_session_deadline(
                session,
                owner_id=owner_id,
                session_id=session_id,
                now=snapshot.phase_deadline_at,
            )
        assert [(item.sequence, item.event_type) for item in events] == [
            (5, "floor.released"),
            (6, "session.state_changed"),
        ]
        async with session_factory() as session:
            aggregate = await session.get(SimulationSession, session_id)
            release = await session.get(FloorRelease, command.grant_id)
            assert aggregate is not None
            assert aggregate.status == SessionStatus.EXPLORATION.value
            assert aggregate.current_floor_grant_id is None
            assert release is not None and release.reason_code == "PHASE_CHANGED"

        async with session_factory() as session:
            await apply_session_command(
                session,
                owner_id=owner_id,
                command=SessionCommand(
                    schema_version=1,
                    command_type="session.abort",
                    session_id=session_id,
                    action_id=uuid4(),
                    payload={},
                ),
            )
        stale_terminal = _grant(
            session_id,
            participants[2].id,
            expected_sequence=7,
        )
        stale_terminal = GrantFloorCommand(
            session_id=stale_terminal.session_id,
            action_id=stale_terminal.action_id,
            grant_id=stale_terminal.grant_id,
            decision=FloorDecisionRecord(
                decision_id=stale_terminal.decision.decision_id,
                phase=SessionStatus.EXPLORATION,
                expected_last_sequence=stale_terminal.decision.expected_last_sequence,
                outcome=stale_terminal.decision.outcome,
                selected_participant_id=(
                    stale_terminal.decision.selected_participant_id
                ),
                opportunity_id=stale_terminal.decision.opportunity_id,
                intervention_kind=stale_terminal.decision.intervention_kind,
                policy_version=stale_terminal.decision.policy_version,
                primary_reason=stale_terminal.decision.primary_reason,
                supporting_reasons=stale_terminal.decision.supporting_reasons,
                metadata=stale_terminal.decision.metadata,
            ),
        )
        async with session_factory() as session:
            with pytest.raises(InvalidFloorStateError):
                await apply_floor_command(
                    session,
                    owner_id=owner_id,
                    command=stale_terminal,
                )


def test_phase_transition_releases_floor_without_changing_state_machine_semantics(
    migrated_database: TemporaryDatabaseContext,
) -> None:
    run_async(lambda: _verify_phase_cleanup_and_terminal_protection(migrated_database))


async def _verify_ineligible_and_rollback(
    temporary_database: TemporaryDatabaseContext,
) -> None:
    async with _session_factory(temporary_database) as session_factory:
        owner_id, session_id, participants = await _active_session(session_factory)
        moderator_id = uuid4()
        async with session_factory() as session:
            async with session.begin():
                session.add(
                    SessionParticipant(
                        id=moderator_id,
                        session_id=session_id,
                        actor_kind="SYSTEM",
                        participation_role="MODERATOR",
                        seat_order=5,
                        availability="AVAILABLE",
                        user_id=None,
                        question_persona_assignment_id=None,
                    )
                )
        async with session_factory() as session:
            with pytest.raises(IneligibleParticipantError):
                await apply_floor_command(
                    session,
                    owner_id=owner_id,
                    command=_grant(session_id, moderator_id),
                )

        original = service.floor_granted_event
        service.floor_granted_event = lambda **_: PendingEvent(  # type: ignore[assignment]
            event_type="floor.granted",
            payload={},
            event_version=0,
        )
        command = _grant(session_id, participants[1].id)
        try:
            async with session_factory() as session:
                with pytest.raises(SessionPersistenceError):
                    await apply_floor_command(
                        session,
                        owner_id=owner_id,
                        command=command,
                    )
        finally:
            service.floor_granted_event = original

        async with session_factory() as session:
            aggregate = await session.get(SimulationSession, session_id)
            assert aggregate is not None
            assert aggregate.current_floor_grant_id is None
            assert aggregate.last_sequence == 3
            assert (
                await session.get(SessionAction, (session_id, command.action_id))
                is None
            )
            assert (
                await session.get(FloorDecision, command.decision.decision_id) is None
            )
            assert await session.get(FloorGrant, command.grant_id) is None


def test_system_moderator_is_supported_but_ineligible_for_ordinary_floor_and_rollback_is_atomic(
    migrated_database: TemporaryDatabaseContext,
) -> None:
    run_async(lambda: _verify_ineligible_and_rollback(migrated_database))


async def _verify_cross_session_active_pointer_rejected(
    temporary_database: TemporaryDatabaseContext,
) -> None:
    async with _session_factory(temporary_database) as session_factory:
        owner_id, first_session_id, participants = await _active_session(
            session_factory
        )
        command = _grant(first_session_id, participants[1].id)
        async with session_factory() as session:
            await apply_floor_command(session, owner_id=owner_id, command=command)

        second_owner_id, second_session_id, _ = await _active_session(session_factory)
        async with session_factory() as session:
            second = await session.get(SimulationSession, second_session_id)
            assert second is not None
            second.current_floor_grant_id = command.grant_id
            with pytest.raises(IntegrityError):
                await session.commit()
            await session.rollback()

        async with session_factory() as session:
            second = await session.get(SimulationSession, second_session_id)
            assert second is not None and second.current_floor_grant_id is None
            assert second.owner_user_id == second_owner_id


def test_database_rejects_cross_session_current_floor_pointer(
    migrated_database: TemporaryDatabaseContext,
) -> None:
    run_async(lambda: _verify_cross_session_active_pointer_rejected(migrated_database))


async def _verify_session_deletion_cascades_floor_history(
    temporary_database: TemporaryDatabaseContext,
) -> None:
    async with _session_factory(temporary_database) as session_factory:
        owner_id, session_id, participants = await _active_session(session_factory)
        command = _grant(session_id, participants[1].id)
        async with session_factory() as session:
            await apply_floor_command(session, owner_id=owner_id, command=command)

        async with session_factory() as session:
            await session.execute(delete(User).where(User.id == owner_id))
            await session.commit()

        async with session_factory() as session:
            assert await session.get(SimulationSession, session_id) is None
            for model in (
                SessionParticipant,
                FloorDecision,
                FloorGrant,
                FloorRelease,
                FloorIntervention,
                SessionAction,
                DiscussionEvent,
            ):
                assert (
                    await session.scalar(
                        select(func.count())
                        .select_from(model)
                        .where(model.session_id == session_id)
                    )
                    == 0
                )


def test_owner_deletion_cascades_session_and_floor_history_without_orphans(
    migrated_database: TemporaryDatabaseContext,
) -> None:
    run_async(
        lambda: _verify_session_deletion_cascades_floor_history(migrated_database)
    )


async def _verify_scheduler_retry_fairness_and_audit(
    temporary_database: TemporaryDatabaseContext,
) -> None:
    async with _session_factory(temporary_database) as session_factory:
        owner_id, session_id, participants = await _active_session(session_factory)
        async with session_factory() as session:
            aggregate = await session.get(SimulationSession, session_id)
            assert aggregate is not None and aggregate.phase_started_at is not None
            evaluated_at = datetime.now(UTC)
        opportunity_id = uuid4()
        async with session_factory() as session:
            async with session.begin():
                session.add(
                    SpeakingOpportunity(
                        id=opportunity_id,
                        session_id=session_id,
                        participant_id=participants[2].id,
                        phase=SessionStatus.OPENING_STATEMENTS.value,
                        opportunity_kind="EXPLICIT_REQUEST",
                        created_at=evaluated_at,
                    )
                )

        first = _schedule(session_id, evaluated_at=evaluated_at)
        async with session_factory() as session:
            first_events = await apply_scheduler_command(
                session,
                owner_id=owner_id,
                command=first,
            )
        async with session_factory() as session:
            duplicate_events = await apply_scheduler_command(
                session,
                owner_id=owner_id,
                command=first,
            )
        assert duplicate_events == first_events
        assert [(item.sequence, item.event_type) for item in first_events] == [
            (4, "floor.granted")
        ]
        assert first_events[0].payload["participant_id"] == str(participants[2].id)
        assert first_events[0].payload["opportunity_id"] == str(opportunity_id)

        conflict = _schedule(
            session_id,
            evaluated_at=evaluated_at,
            action_id=first.action_id,
        )
        async with session_factory() as session:
            with pytest.raises(ActionIdConflictError):
                await apply_scheduler_command(
                    session,
                    owner_id=owner_id,
                    command=conflict,
                )

        release = ReleaseFloorCommand(
            session_id=session_id,
            action_id=uuid4(),
            grant_id=first.grant_id,
            expected_phase=SessionStatus.OPENING_STATEMENTS,
            expected_last_sequence=4,
            reason=FloorReleaseReason.SPEAKER_FINISHED,
        )
        async with session_factory() as session:
            await apply_floor_command(session, owner_id=owner_id, command=release)

        second = _schedule(
            session_id,
            evaluated_at=datetime.now(UTC),
            expected_sequence=5,
        )
        async with session_factory() as session:
            second_events = await apply_scheduler_command(
                session,
                owner_id=owner_id,
                command=second,
            )
        assert [(item.sequence, item.event_type) for item in second_events] == [
            (6, "floor.granted")
        ]
        assert second_events[0].payload["participant_id"] == str(participants[0].id)
        assert second_events[0].payload["reason_code"] == "MONOPOLY_PREVENTION"

        async with session_factory() as session:
            first_decision = await session.get(FloorDecision, first.decision_id)
            second_decision = await session.get(FloorDecision, second.decision_id)
            aggregate = await session.get(SimulationSession, session_id)
            assert first_decision is not None and second_decision is not None
            assert aggregate is not None
            assert aggregate.current_floor_grant_id == second.grant_id
            assert first_decision.primary_reason_code == "FIRST_OPPORTUNITY"
            assert first_decision.supporting_reason_codes == ["EXPLICIT_OPPORTUNITY"]
            assert second_decision.primary_reason_code == "MONOPOLY_PREVENTION"
            assert second_decision.decision_metadata == {
                "current_phase_grant_count": 0,
                "first_opportunity_unmet": True,
                "previous_owner_was_selected": False,
                "consecutive_grant_count": 0,
                "tie_break_class": "SEAT_ORDER",
            }
            sequences = list(
                (
                    await session.scalars(
                        select(DiscussionEvent.sequence)
                        .where(DiscussionEvent.session_id == session_id)
                        .order_by(DiscussionEvent.sequence)
                    )
                ).all()
            )
            assert sequences == [1, 2, 3, 4, 5, 6]


def test_scheduler_retry_digest_fairness_restart_and_audit_are_durable(
    migrated_database: TemporaryDatabaseContext,
) -> None:
    run_async(lambda: _verify_scheduler_retry_fairness_and_audit(migrated_database))


async def _verify_concurrent_scheduling(
    temporary_database: TemporaryDatabaseContext,
) -> None:
    async with _session_factory(temporary_database) as session_factory:
        owner_id, session_id, _ = await _active_session(session_factory)
        async with session_factory() as session:
            aggregate = await session.get(SimulationSession, session_id)
            assert aggregate is not None and aggregate.phase_started_at is not None
            evaluated_at = datetime.now(UTC)
        commands = [
            _schedule(session_id, evaluated_at=evaluated_at),
            _schedule(session_id, evaluated_at=evaluated_at),
        ]

        async def apply(command: ScheduleFloorCommand) -> object:
            try:
                async with session_factory() as session:
                    return await apply_scheduler_command(
                        session,
                        owner_id=owner_id,
                        command=command,
                    )
            except Exception as exception:
                return exception

        outcomes = await asyncio.gather(*(apply(command) for command in commands))
        assert sum(isinstance(item, list) for item in outcomes) == 1
        assert sum(isinstance(item, StaleFloorDecisionError) for item in outcomes) == 1

        async with session_factory() as session:
            aggregate = await session.get(SimulationSession, session_id)
            assert aggregate is not None
            assert aggregate.current_floor_grant_id is not None
            assert aggregate.last_sequence == 4
            assert (
                await session.scalar(
                    select(func.count())
                    .select_from(FloorGrant)
                    .where(FloorGrant.session_id == session_id)
                )
                == 1
            )
            assert (
                await session.scalar(
                    select(func.count())
                    .select_from(FloorDecision)
                    .where(FloorDecision.session_id == session_id)
                )
                == 1
            )


def test_concurrent_scheduler_calls_produce_one_active_grant(
    migrated_database: TemporaryDatabaseContext,
) -> None:
    run_async(lambda: _verify_concurrent_scheduling(migrated_database))


async def _verify_scheduler_deadline_intervention(
    temporary_database: TemporaryDatabaseContext,
) -> None:
    async with _session_factory(temporary_database) as session_factory:
        owner_id, session_id, _ = await _active_session(session_factory)
        async with session_factory() as session:
            aggregate = await session.get(SimulationSession, session_id)
            assert aggregate is not None and aggregate.phase_deadline_at is not None
            evaluated_at = aggregate.phase_deadline_at - timedelta(milliseconds=50)
        command = _schedule(session_id, evaluated_at=evaluated_at)

        async with session_factory() as session:
            events = await apply_scheduler_command(
                session,
                owner_id=owner_id,
                command=command,
            )
        async with session_factory() as session:
            duplicate = await apply_scheduler_command(
                session,
                owner_id=owner_id,
                command=command,
            )

        assert duplicate == events
        assert [(item.sequence, item.event_type) for item in events] == [
            (4, "floor.intervention_requested")
        ]
        assert events[0].payload["intervention_kind"] == "DEADLINE"
        assert events[0].payload["reason_code"] == "DEADLINE_RECOVERY"
        async with session_factory() as session:
            aggregate = await session.get(SimulationSession, session_id)
            decision = await session.get(FloorDecision, command.decision_id)
            intervention = await session.get(
                FloorIntervention,
                command.intervention_id,
            )
            assert aggregate is not None
            assert aggregate.current_floor_grant_id is None
            assert aggregate.status == SessionStatus.OPENING_STATEMENTS.value
            assert decision is not None and intervention is not None
            assert decision.outcome_kind == "REQUEST_INTERVENTION"
            assert intervention.decision_id == decision.id


def test_scheduler_deadline_intervention_is_atomic_and_idempotent(
    migrated_database: TemporaryDatabaseContext,
) -> None:
    run_async(lambda: _verify_scheduler_deadline_intervention(migrated_database))


async def _verify_scheduler_phase_boundary_and_rollback(
    temporary_database: TemporaryDatabaseContext,
) -> None:
    async with _session_factory(temporary_database) as session_factory:
        owner_id, session_id, _ = await _active_session(session_factory)
        async with session_factory() as session:
            aggregate = await session.get(SimulationSession, session_id)
            assert aggregate is not None and aggregate.phase_deadline_at is not None
            deadline = aggregate.phase_deadline_at
        stale = _schedule(session_id, evaluated_at=deadline)
        async with session_factory() as session:
            with pytest.raises(StaleFloorDecisionError):
                await apply_scheduler_command(
                    session,
                    owner_id=owner_id,
                    command=stale,
                )
        async with session_factory() as session:
            aggregate = await session.get(SimulationSession, session_id)
            assert aggregate is not None
            assert aggregate.status == SessionStatus.EXPLORATION.value
            assert aggregate.last_sequence == 4
            assert aggregate.current_floor_grant_id is None
            assert await session.get(FloorDecision, stale.decision_id) is None
            assert await session.get(FloorGrant, stale.grant_id) is None

        assert aggregate.phase_started_at is not None
        rollback = ScheduleFloorCommand(
            session_id=session_id,
            action_id=uuid4(),
            decision_id=uuid4(),
            grant_id=uuid4(),
            intervention_id=uuid4(),
            expected_phase=SessionStatus.EXPLORATION,
            expected_last_sequence=4,
            expected_current_floor_grant_id=None,
            evaluated_at=datetime.now(UTC),
            policy=replace(
                V0_1_SCHEDULER_POLICY,
                deadline_intervention_threshold=timedelta(milliseconds=100),
            ),
        )
        original = service.floor_granted_event
        service.floor_granted_event = lambda **_: PendingEvent(  # type: ignore[assignment]
            event_type="floor.granted",
            payload={},
            event_version=0,
        )
        try:
            async with session_factory() as session:
                with pytest.raises(SessionPersistenceError):
                    await apply_scheduler_command(
                        session,
                        owner_id=owner_id,
                        command=rollback,
                    )
        finally:
            service.floor_granted_event = original

        async with session_factory() as session:
            aggregate = await session.get(SimulationSession, session_id)
            assert aggregate is not None
            assert aggregate.last_sequence == 4
            assert aggregate.current_floor_grant_id is None
            assert (
                await session.get(SessionAction, (session_id, rollback.action_id))
                is None
            )
            assert await session.get(FloorDecision, rollback.decision_id) is None
            assert await session.get(FloorGrant, rollback.grant_id) is None


def test_scheduler_phase_transition_wins_and_rollback_is_atomic(
    migrated_database: TemporaryDatabaseContext,
) -> None:
    run_async(lambda: _verify_scheduler_phase_boundary_and_rollback(migrated_database))
