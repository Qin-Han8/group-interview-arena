import asyncio
from collections.abc import Callable, Coroutine
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import timedelta
from typing import Any, Protocol
from uuid import UUID, uuid4

import pytest
from sqlalchemy import URL, func, select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

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
    User,
)
from group_interview_arena_api.db.runtime import (
    create_database_engine,
    create_database_session_factory,
    dispose_database_engine,
)
from group_interview_arena_api.modules.ai_runtime.continuous import (
    ContinuousAiDriveOutcome,
    ContinuousAiDriveResult,
)
from group_interview_arena_api.modules.discussion_sessions import progression
from group_interview_arena_api.modules.discussion_sessions.domain import (
    PhaseDurationPlan,
    SessionCommand,
    SessionStatus,
)
from group_interview_arena_api.modules.discussion_sessions.service import (
    apply_session_command,
    create_session,
    get_session_snapshot,
    reconcile_session_deadline,
)
from group_interview_arena_api.modules.discussion_sessions.utterances import (
    SubmitHumanUtterance,
    submit_human_utterance,
)
from group_interview_arena_api.modules.floor_control import (
    progression as floor_progression,
)
from group_interview_arena_api.modules.floor_control.domain import (
    FLOOR_ENABLED_PHASES,
    FloorDecisionOutcome,
    FloorDecisionRecord,
    FloorPolicyReason,
    FloorReleaseReason,
    GrantFloorCommand,
    ParticipantActorKind,
    ParticipantAvailability,
    ReleaseFloorCommand,
    SafeDecisionMetadata,
)
from group_interview_arena_api.modules.floor_control.scheduler import (
    V0_1_SCHEDULER_POLICY,
    V0_1_SCHEDULER_POLICY_V1,
    V0_1_SCHEDULER_POLICY_V2,
    ScheduleFloorCommand,
)
from group_interview_arena_api.modules.floor_control.service import apply_floor_command
from group_interview_arena_api.modules.question_personas.seed import (
    INTERNAL_VALIDATION_BUNDLE,
    seed_question_persona_foundation,
)

pytestmark = pytest.mark.integration

PLAN = PhaseDurationPlan.from_seconds(
    {
        SessionStatus.PREPARATION: 1,
        SessionStatus.OPENING_STATEMENTS: 300,
        SessionStatus.EXPLORATION: 300,
        SessionStatus.CONFLICT_AND_EVALUATION: 300,
        SessionStatus.CONVERGENCE: 300,
        SessionStatus.FINAL_SUMMARY: 300,
    }
)


class TemporaryDatabaseContext(Protocol):
    database_name: str
    database_url: URL

    def database_settings(self) -> DatabaseSettings: ...


def run_async[T](operation: Callable[[], Coroutine[Any, Any, T]]) -> T:
    return asyncio.run(operation(), loop_factory=asyncio.SelectorEventLoop)


@dataclass(frozen=True)
class ReleasedHumanContext:
    engine: AsyncEngine
    session_factory: async_sessionmaker[AsyncSession]
    owner_id: UUID
    session_id: UUID
    human_participant_id: UUID
    ai_participant_id: UUID
    human_grant_id: UUID
    human_release_sequence: int
    prior_ai_grant_id: UUID | None


def _grant_decision(
    *, participant_id: UUID, expected_last_sequence: int
) -> FloorDecisionRecord:
    return FloorDecisionRecord(
        decision_id=uuid4(),
        phase=SessionStatus.OPENING_STATEMENTS,
        expected_last_sequence=expected_last_sequence,
        outcome=FloorDecisionOutcome.GRANT,
        selected_participant_id=participant_id,
        opportunity_id=None,
        intervention_kind=None,
        policy_version="v0.1-floor-1",
        primary_reason=FloorPolicyReason.FIRST_OPPORTUNITY,
        supporting_reasons=(FloorPolicyReason.PHASE_MANDATED_TURN,),
        metadata=SafeDecisionMetadata(
            current_phase_grant_count=0,
            first_opportunity_unmet=True,
            previous_owner_was_selected=False,
            consecutive_grant_count=0,
            tie_break_class="SEAT_ORDER",
        ),
    )


async def _grant(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    owner_id: UUID,
    session_id: UUID,
    participant_id: UUID,
) -> UUID:
    async with session_factory() as session:
        aggregate = await session.get(SimulationSession, session_id)
    assert aggregate is not None
    grant_id = uuid4()
    async with session_factory() as session:
        await apply_floor_command(
            session,
            owner_id=owner_id,
            command=GrantFloorCommand(
                session_id=session_id,
                action_id=uuid4(),
                grant_id=grant_id,
                decision=_grant_decision(
                    participant_id=participant_id,
                    expected_last_sequence=aggregate.last_sequence,
                ),
            ),
        )
    return grant_id


async def _release(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    owner_id: UUID,
    session_id: UUID,
    grant_id: UUID,
) -> None:
    async with session_factory() as session:
        aggregate = await session.get(SimulationSession, session_id)
    assert aggregate is not None
    async with session_factory() as session:
        await apply_floor_command(
            session,
            owner_id=owner_id,
            command=ReleaseFloorCommand(
                session_id=session_id,
                action_id=uuid4(),
                grant_id=grant_id,
                expected_phase=SessionStatus(aggregate.status),
                expected_last_sequence=aggregate.last_sequence,
                reason=FloorReleaseReason.SPEAKER_FINISHED,
            ),
        )


@asynccontextmanager
async def _released_human_context(
    temporary_database: TemporaryDatabaseContext,
    *,
    prior_ai_release: bool = False,
    disable_other_ai: bool = False,
):
    engine = create_database_engine(temporary_database.database_settings())
    session_factory = create_database_session_factory(engine)
    try:
        await seed_question_persona_foundation(session_factory)
        owner_id = uuid4()
        async with session_factory() as session:
            async with session.begin():
                session.add(
                    User(
                        id=owner_id,
                        username=f"progression_{owner_id.hex[:10]}",
                        password_hash="test-only-password-hash",
                    )
                )
        async with session_factory() as session:
            created = await create_session(
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
                    session_id=created.session_id,
                    action_id=uuid4(),
                    payload={},
                ),
                duration_plan=PLAN,
            )
        async with session_factory() as session:
            prepared = await get_session_snapshot(
                session,
                owner_id=owner_id,
                session_id=created.session_id,
            )
        assert prepared.phase_deadline_at is not None
        async with session_factory() as session:
            await reconcile_session_deadline(
                session,
                owner_id=owner_id,
                session_id=created.session_id,
                now=prepared.phase_deadline_at,
            )
        async with session_factory() as session:
            active = await get_session_snapshot(
                session,
                owner_id=owner_id,
                session_id=created.session_id,
            )
            participants = tuple(
                (
                    await session.scalars(
                        select(SessionParticipant)
                        .where(SessionParticipant.session_id == created.session_id)
                        .order_by(SessionParticipant.seat_order)
                    )
                ).all()
            )
        assert active.phase_deadline_at is not None
        if disable_other_ai:
            async with session_factory() as session:
                async with session.begin():
                    for participant in participants[2:]:
                        stored = await session.get(SessionParticipant, participant.id)
                        assert stored is not None
                        stored.availability = ParticipantAvailability.UNAVAILABLE

        prior_ai_grant_id = None
        if prior_ai_release:
            prior_ai_grant_id = await _grant(
                session_factory,
                owner_id=owner_id,
                session_id=created.session_id,
                participant_id=participants[1].id,
            )
            await _release(
                session_factory,
                owner_id=owner_id,
                session_id=created.session_id,
                grant_id=prior_ai_grant_id,
            )

        human_grant_id = await _grant(
            session_factory,
            owner_id=owner_id,
            session_id=created.session_id,
            participant_id=participants[0].id,
        )
        async with session_factory() as session:
            committed = await submit_human_utterance(
                session,
                owner_id=owner_id,
                command=SubmitHumanUtterance(
                    session_id=created.session_id,
                    action_id=uuid4(),
                    floor_grant_id=human_grant_id,
                    content="Human release checkpoint.",
                    received_at=active.phase_deadline_at - timedelta(seconds=1),
                ),
            )
        yield ReleasedHumanContext(
            engine=engine,
            session_factory=session_factory,
            owner_id=owner_id,
            session_id=created.session_id,
            human_participant_id=participants[0].id,
            ai_participant_id=participants[1].id,
            human_grant_id=human_grant_id,
            human_release_sequence=committed.events[1].sequence,
            prior_ai_grant_id=prior_ai_grant_id,
        )
    finally:
        await dispose_database_engine(engine)


def test_human_scheduler_identity_bytes_are_frozen() -> None:
    identities = progression.derive_human_scheduler_identities(
        session_id=UUID("10000000-0000-4000-8000-000000000001"),
        released_floor_grant_id=UUID("30000000-0000-4000-8000-000000000003"),
    )

    assert identities == progression.SchedulerCheckpointIdentities(
        schedule_action_id=UUID("2942fbe2-dc6e-4e40-9997-55ad6e53cc19"),
        decision_id=UUID("eda3a8d8-e7aa-456b-9d63-9db184342fcc"),
        next_floor_grant_id=UUID("2602d299-3d19-4383-991a-66045389b840"),
        intervention_id=UUID("fecb3822-68f4-4103-9a5c-ed5e2610e43d"),
    )


def test_human_release_schedules_then_invokes_configured_ai_once(
    migrated_database: TemporaryDatabaseContext,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def exercise() -> None:
        configured_calls = 0

        async def configured_drive(*_args: object, **_kwargs: object):
            nonlocal configured_calls
            configured_calls += 1
            return ContinuousAiDriveResult(
                outcome=ContinuousAiDriveOutcome.WAITING_FOR_HUMAN,
                automated_ai_turns_advanced=1,
            )

        monkeypatch.setattr(
            progression,
            "drive_configured_ai_session",
            configured_drive,
        )
        async with _released_human_context(migrated_database) as context:
            result = await progression.resume_discussion_progression(
                context.session_factory,
                owner_id=context.owner_id,
                session_id=context.session_id,
            )
            identities = progression.derive_human_scheduler_identities(
                session_id=context.session_id,
                released_floor_grant_id=context.human_grant_id,
            )
            async with context.session_factory() as session:
                schedule = await session.get(
                    SessionAction,
                    (context.session_id, identities.schedule_action_id),
                )
                aggregate = await session.get(SimulationSession, context.session_id)

            assert result.outcome.value == "ai_drive_completed", result
            assert configured_calls == 1
            assert schedule is not None
            assert aggregate is not None
            assert aggregate.current_floor_grant_id == identities.next_floor_grant_id

    run_async(exercise)


def test_human_checkpoint_recovery_uses_event_sequence_not_release_timestamp(
    migrated_database: TemporaryDatabaseContext,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def exercise() -> None:
        configured_calls = 0

        async def configured_drive(*_args: object, **_kwargs: object):
            nonlocal configured_calls
            configured_calls += 1
            return ContinuousAiDriveResult(
                outcome=ContinuousAiDriveOutcome.WAITING_FOR_HUMAN,
                automated_ai_turns_advanced=1,
            )

        monkeypatch.setattr(
            progression,
            "drive_configured_ai_session",
            configured_drive,
        )
        async with _released_human_context(
            migrated_database,
            prior_ai_release=True,
        ) as context:
            assert context.prior_ai_grant_id is not None
            async with context.session_factory() as session:
                async with session.begin():
                    earlier = await session.get(FloorRelease, context.prior_ai_grant_id)
                    later = await session.get(FloorRelease, context.human_grant_id)
                    assert earlier is not None
                    assert later is not None
                    earlier.released_at = later.released_at + timedelta(seconds=1)

            result = await progression.resume_discussion_progression(
                context.session_factory,
                owner_id=context.owner_id,
                session_id=context.session_id,
            )

            assert result.released_floor_grant_id == context.human_grant_id
            assert result.outcome.value == "ai_drive_completed", result
            assert configured_calls == 1

    run_async(exercise)


def test_concurrent_human_progression_has_one_durable_scheduler_checkpoint(
    migrated_database: TemporaryDatabaseContext,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def exercise() -> None:
        async def configured_drive(*_args: object, **_kwargs: object):
            return ContinuousAiDriveResult(
                outcome=ContinuousAiDriveOutcome.WAITING_FOR_HUMAN,
                automated_ai_turns_advanced=0,
            )

        monkeypatch.setattr(
            progression,
            "drive_configured_ai_session",
            configured_drive,
        )
        async with _released_human_context(migrated_database) as context:

            async def resume():
                return await progression.resume_discussion_progression(
                    context.session_factory,
                    owner_id=context.owner_id,
                    session_id=context.session_id,
                )

            results = await asyncio.gather(resume(), resume())
            identities = progression.derive_human_scheduler_identities(
                session_id=context.session_id,
                released_floor_grant_id=context.human_grant_id,
            )
            async with context.session_factory() as session:
                schedule_count = await session.scalar(
                    select(func.count())
                    .select_from(SessionAction)
                    .where(
                        SessionAction.session_id == context.session_id,
                        SessionAction.action_id == identities.schedule_action_id,
                    )
                )

            assert schedule_count == 1
            assert all(
                result.outcome.value == "ai_drive_completed" for result in results
            )

    run_async(exercise)


def test_inconsistent_latest_human_checkpoint_fails_closed_without_ai_drive(
    migrated_database: TemporaryDatabaseContext,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def exercise() -> None:
        configured_calls = 0

        async def configured_drive(*_args: object, **_kwargs: object):
            nonlocal configured_calls
            configured_calls += 1
            return ContinuousAiDriveResult(
                outcome=ContinuousAiDriveOutcome.WAITING_FOR_HUMAN,
                automated_ai_turns_advanced=0,
            )

        monkeypatch.setattr(
            progression,
            "drive_configured_ai_session",
            configured_drive,
        )
        async with _released_human_context(migrated_database) as context:
            async with context.session_factory() as session:
                async with session.begin():
                    release_event = await session.get(
                        DiscussionEvent,
                        (context.session_id, context.human_release_sequence),
                    )
                    assert release_event is not None
                    release_event.payload = {
                        **release_event.payload,
                        "reason_code": "INTERRUPTED",
                    }

            result = await progression.resume_discussion_progression(
                context.session_factory,
                owner_id=context.owner_id,
                session_id=context.session_id,
            )

            assert result.outcome.value == "reconciliation_required"
            assert configured_calls == 0

    run_async(exercise)


@dataclass(frozen=True)
class InitialPhaseContext:
    engine: AsyncEngine
    session_factory: async_sessionmaker[AsyncSession]
    owner_id: UUID
    session_id: UUID
    human_participant_id: UUID
    ai_participant_id: UUID


@asynccontextmanager
async def _initial_phase_context(
    temporary_database: TemporaryDatabaseContext,
    *,
    phase: SessionStatus = SessionStatus.OPENING_STATEMENTS,
):
    engine = create_database_engine(temporary_database.database_settings())
    session_factory = create_database_session_factory(engine)
    try:
        await seed_question_persona_foundation(session_factory)
        owner_id = uuid4()
        async with session_factory() as session:
            async with session.begin():
                session.add(
                    User(
                        id=owner_id,
                        username=f"initial_progression_{owner_id.hex[:10]}",
                        password_hash="test-only-password-hash",
                    )
                )
        async with session_factory() as session:
            created = await create_session(
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
                    session_id=created.session_id,
                    action_id=uuid4(),
                    payload={},
                ),
                duration_plan=PLAN,
            )

        while True:
            async with session_factory() as session:
                snapshot = await get_session_snapshot(
                    session,
                    owner_id=owner_id,
                    session_id=created.session_id,
                )
            if snapshot.status is phase:
                break
            assert snapshot.phase_deadline_at is not None
            async with session_factory() as session:
                await reconcile_session_deadline(
                    session,
                    owner_id=owner_id,
                    session_id=created.session_id,
                    now=snapshot.phase_deadline_at,
                )

        async with session_factory() as session:
            participants = tuple(
                (
                    await session.scalars(
                        select(SessionParticipant)
                        .where(SessionParticipant.session_id == created.session_id)
                        .order_by(SessionParticipant.seat_order)
                    )
                ).all()
            )
        yield InitialPhaseContext(
            engine=engine,
            session_factory=session_factory,
            owner_id=owner_id,
            session_id=created.session_id,
            human_participant_id=participants[0].id,
            ai_participant_id=participants[1].id,
        )
    finally:
        await dispose_database_engine(engine)


def test_initial_phase_scheduler_identity_bytes_are_frozen() -> None:
    identities = progression.derive_initial_scheduler_identities(
        session_id=UUID("10000000-0000-4000-8000-000000000001"),
        phase=SessionStatus.OPENING_STATEMENTS,
        phase_entry_sequence=7,
    )

    assert identities == progression.SchedulerCheckpointIdentities(
        schedule_action_id=UUID("db89ee13-0f75-4051-a44f-129d09737589"),
        decision_id=UUID("497e178f-b910-4042-8a4c-e2f782971fbb"),
        next_floor_grant_id=UUID("456e1223-cbb7-420b-ba03-6c30f67222a4"),
        intervention_id=UUID("5bc66d02-c623-4177-bdc8-4f409d0d7b86"),
    )


@pytest.mark.parametrize("phase", tuple(FLOOR_ENABLED_PHASES))
def test_exact_initial_phase_entry_proof_covers_every_floor_enabled_phase(
    migrated_database: TemporaryDatabaseContext,
    phase: SessionStatus,
) -> None:
    async def exercise() -> None:
        async with _initial_phase_context(migrated_database, phase=phase) as context:
            async with context.session_factory() as session:
                aggregate = await session.get(SimulationSession, context.session_id)
                assert aggregate is not None
                state, proof = await progression._initial_phase_entry_checkpoint(  # pyright: ignore[reportPrivateUsage]
                    session,
                    owner_id=context.owner_id,
                    aggregate=aggregate,
                )
                event = await session.get(
                    DiscussionEvent,
                    (context.session_id, aggregate.last_sequence),
                )

            assert state is progression._InitialPhaseCheckpointState.EXACT  # pyright: ignore[reportPrivateUsage]
            assert proof is not None
            assert event is not None
            assert proof.phase is phase
            assert proof.event_sequence == aggregate.last_sequence
            assert proof.occurred_at == event.occurred_at
            assert proof.phase_started_at == aggregate.phase_started_at
            assert proof.phase_deadline_at == aggregate.phase_deadline_at

    run_async(exercise)


@pytest.mark.parametrize(
    "mutation",
    (
        "missing",
        "sequence",
        "version",
        "type",
        "status",
        "previous_status",
        "trigger",
        "phase_started_at",
        "phase_deadline_at",
        "extra_payload",
    ),
)
def test_initial_phase_entry_proof_drift_fails_closed_without_schedule(
    migrated_database: TemporaryDatabaseContext,
    mutation: str,
) -> None:
    async def exercise() -> None:
        async with _initial_phase_context(migrated_database) as context:
            async with context.session_factory() as session:
                aggregate = await session.get(SimulationSession, context.session_id)
                assert aggregate is not None
                state, proof = await progression._initial_phase_entry_checkpoint(  # pyright: ignore[reportPrivateUsage]
                    session,
                    owner_id=context.owner_id,
                    aggregate=aggregate,
                )
                assert state is progression._InitialPhaseCheckpointState.EXACT  # pyright: ignore[reportPrivateUsage]
                assert proof is not None

            async with context.session_factory() as session:
                async with session.begin():
                    aggregate = await session.get(
                        SimulationSession,
                        context.session_id,
                    )
                    assert aggregate is not None
                    event = await session.get(
                        DiscussionEvent,
                        (context.session_id, aggregate.last_sequence),
                    )
                    assert event is not None
                    if mutation == "missing":
                        await session.delete(event)
                    elif mutation == "sequence":
                        aggregate.last_sequence += 1
                    elif mutation == "version":
                        event.event_version = 1
                    elif mutation == "type":
                        event.event_type = "session.created"
                    else:
                        payload = dict(event.payload)
                        if mutation == "status":
                            payload["status"] = SessionStatus.EXPLORATION.value
                        elif mutation == "previous_status":
                            payload["previous_status"] = SessionStatus.CREATED.value
                        elif mutation == "trigger":
                            payload["trigger"] = "USER_START"
                        elif mutation == "phase_started_at":
                            payload["phase_started_at"] = "2026-01-01T00:00:00Z"
                        elif mutation == "phase_deadline_at":
                            payload["phase_deadline_at"] = "2026-01-01T00:00:01Z"
                        elif mutation == "extra_payload":
                            payload["unexpected"] = True
                        event.payload = payload

            identities = progression.derive_initial_scheduler_identities(
                session_id=context.session_id,
                phase=proof.phase,
                phase_entry_sequence=proof.event_sequence,
            )
            result = await floor_progression.drive_initial_scheduler_checkpoint(
                context.session_factory,
                owner_id=context.owner_id,
                session_id=context.session_id,
                phase_entry=proof,
                identities=identities,
                scheduling_policy=V0_1_SCHEDULER_POLICY,
            )
            async with context.session_factory() as session:
                action = await session.get(
                    SessionAction,
                    (context.session_id, identities.schedule_action_id),
                )

            assert (
                result.outcome
                is floor_progression.SchedulerCheckpointOutcome.RECONCILIATION_REQUIRED
            )
            assert action is None

    run_async(exercise)


def test_initial_driver_persists_exact_command_then_replays_without_recomputing(
    migrated_database: TemporaryDatabaseContext,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def exercise() -> None:
        captured_commands: list[ScheduleFloorCommand] = []
        real_apply = floor_progression.apply_scheduler_command

        async def capture_command(
            session: AsyncSession,
            *,
            owner_id: UUID,
            command: ScheduleFloorCommand,
        ):
            captured_commands.append(command)
            return await real_apply(session, owner_id=owner_id, command=command)

        monkeypatch.setattr(
            floor_progression,
            "apply_scheduler_command",
            capture_command,
        )
        async with _initial_phase_context(migrated_database) as context:
            async with context.session_factory() as session:
                aggregate = await session.get(SimulationSession, context.session_id)
                assert aggregate is not None
                state, proof = await progression._initial_phase_entry_checkpoint(  # pyright: ignore[reportPrivateUsage]
                    session,
                    owner_id=context.owner_id,
                    aggregate=aggregate,
                )
            assert state is progression._InitialPhaseCheckpointState.EXACT  # pyright: ignore[reportPrivateUsage]
            assert proof is not None
            identities = progression.derive_initial_scheduler_identities(
                session_id=context.session_id,
                phase=proof.phase,
                phase_entry_sequence=proof.event_sequence,
            )

            first = await floor_progression.drive_initial_scheduler_checkpoint(
                context.session_factory,
                owner_id=context.owner_id,
                session_id=context.session_id,
                phase_entry=proof,
                identities=identities,
                scheduling_policy=V0_1_SCHEDULER_POLICY,
            )
            second = await floor_progression.drive_initial_scheduler_checkpoint(
                context.session_factory,
                owner_id=context.owner_id,
                session_id=context.session_id,
                phase_entry=proof,
                identities=identities,
                scheduling_policy=V0_1_SCHEDULER_POLICY,
            )

            assert first == second
            assert len(captured_commands) == 1
            command = captured_commands[0]
            assert command.expected_phase is proof.phase
            assert command.expected_last_sequence == proof.event_sequence
            assert command.expected_current_floor_grant_id is None
            assert command.evaluated_at == proof.occurred_at
            assert command.policy is V0_1_SCHEDULER_POLICY

            async with context.session_factory() as session:
                action_count = await session.scalar(
                    select(func.count())
                    .select_from(SessionAction)
                    .where(
                        SessionAction.session_id == context.session_id,
                        SessionAction.action_id == identities.schedule_action_id,
                    )
                )
                decision_count = await session.scalar(
                    select(func.count())
                    .select_from(FloorDecision)
                    .where(FloorDecision.id == identities.decision_id)
                )
                grant_count = await session.scalar(
                    select(func.count())
                    .select_from(FloorGrant)
                    .where(FloorGrant.id == identities.next_floor_grant_id)
                )
                persisted_decision = await session.get(
                    FloorDecision,
                    identities.decision_id,
                )

            assert action_count == 1
            assert decision_count == 1
            assert grant_count == 1
            assert persisted_decision is not None
            assert persisted_decision.policy_version == "v0.1-floor-2"

    run_async(exercise)


def test_initial_checkpoint_replays_persisted_v1_under_current_v2_without_rewrite(
    migrated_database: TemporaryDatabaseContext,
) -> None:
    async def exercise() -> None:
        async with _initial_phase_context(migrated_database) as context:
            async with context.session_factory() as session:
                aggregate = await session.get(SimulationSession, context.session_id)
                assert aggregate is not None
                state, proof = await progression._initial_phase_entry_checkpoint(  # pyright: ignore[reportPrivateUsage]
                    session,
                    owner_id=context.owner_id,
                    aggregate=aggregate,
                )
            assert state is progression._InitialPhaseCheckpointState.EXACT  # pyright: ignore[reportPrivateUsage]
            assert proof is not None
            identities = progression.derive_initial_scheduler_identities(
                session_id=context.session_id,
                phase=proof.phase,
                phase_entry_sequence=proof.event_sequence,
            )

            first = await floor_progression.drive_initial_scheduler_checkpoint(
                context.session_factory,
                owner_id=context.owner_id,
                session_id=context.session_id,
                phase_entry=proof,
                identities=identities,
                scheduling_policy=V0_1_SCHEDULER_POLICY_V1,
            )
            replay = await floor_progression.drive_initial_scheduler_checkpoint(
                context.session_factory,
                owner_id=context.owner_id,
                session_id=context.session_id,
                phase_entry=proof,
                identities=identities,
                scheduling_policy=V0_1_SCHEDULER_POLICY_V2,
            )

            async with context.session_factory() as session:
                decision = await session.get(FloorDecision, identities.decision_id)
            assert replay == first
            assert decision is not None
            assert decision.policy_version == "v0.1-floor-1"

    run_async(exercise)


def test_released_checkpoint_replays_persisted_v1_under_current_v2_without_rewrite(
    migrated_database: TemporaryDatabaseContext,
) -> None:
    async def exercise() -> None:
        async with _released_human_context(migrated_database) as context:
            async with context.session_factory() as session:
                release = await session.get(FloorRelease, context.human_grant_id)
            assert release is not None
            assert release.causation_action_id is not None
            released_floor = floor_progression.ReleasedFloorProof(
                floor_grant_id=context.human_grant_id,
                release_action_id=release.causation_action_id,
                release_command_type="participant.utterance.submit",
                allowed_reasons=frozenset({FloorReleaseReason.SPEAKER_FINISHED}),
            )
            identities = progression.derive_human_scheduler_identities(
                session_id=context.session_id,
                released_floor_grant_id=context.human_grant_id,
            )

            first = await floor_progression.drive_scheduler_checkpoint(
                context.session_factory,
                owner_id=context.owner_id,
                session_id=context.session_id,
                released_floor=released_floor,
                identities=identities,
                scheduling_policy=V0_1_SCHEDULER_POLICY_V1,
            )
            replay = await floor_progression.drive_scheduler_checkpoint(
                context.session_factory,
                owner_id=context.owner_id,
                session_id=context.session_id,
                released_floor=released_floor,
                identities=identities,
                scheduling_policy=V0_1_SCHEDULER_POLICY_V2,
            )

            async with context.session_factory() as session:
                decision = await session.get(FloorDecision, identities.decision_id)
            assert replay == first
            assert decision is not None
            assert decision.policy_version == "v0.1-floor-1"

    run_async(exercise)


def test_resume_progression_naturally_grants_initial_human_floor(
    migrated_database: TemporaryDatabaseContext,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def exercise() -> None:
        configured_calls = 0

        async def configured_drive(*_args: object, **_kwargs: object):
            nonlocal configured_calls
            configured_calls += 1
            return ContinuousAiDriveResult(
                outcome=ContinuousAiDriveOutcome.WAITING_FOR_HUMAN,
                automated_ai_turns_advanced=0,
            )

        monkeypatch.setattr(
            progression,
            "drive_configured_ai_session",
            configured_drive,
        )
        async with _initial_phase_context(migrated_database) as context:
            result = await progression.resume_discussion_progression(
                context.session_factory,
                owner_id=context.owner_id,
                session_id=context.session_id,
            )
            async with context.session_factory() as session:
                aggregate = await session.get(SimulationSession, context.session_id)
                assert aggregate is not None
                assert aggregate.current_floor_grant_id is not None
                grant = await session.get(
                    FloorGrant,
                    aggregate.current_floor_grant_id,
                )
                assert grant is not None
                participant = await session.get(
                    SessionParticipant,
                    grant.participant_id,
                )

            assert (
                result.outcome
                is progression.DiscussionProgressionOutcome.NEXT_HUMAN_GRANTED
            )
            assert result.scheduler_result is not None
            assert result.scheduler_result.next_participant_id == (
                context.human_participant_id
            )
            assert participant is not None
            assert participant.id == context.human_participant_id
            assert configured_calls == 0

    run_async(exercise)


def test_resume_progression_naturally_grants_initial_ai_floor(
    migrated_database: TemporaryDatabaseContext,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def exercise() -> None:
        configured_calls = 0

        async def configured_drive(*_args: object, **_kwargs: object):
            nonlocal configured_calls
            configured_calls += 1
            return ContinuousAiDriveResult(
                outcome=ContinuousAiDriveOutcome.WAITING_FOR_HUMAN,
                automated_ai_turns_advanced=0,
            )

        monkeypatch.setattr(
            progression,
            "drive_configured_ai_session",
            configured_drive,
        )
        async with _initial_phase_context(migrated_database) as context:
            async with context.session_factory() as session:
                async with session.begin():
                    human = await session.get(
                        SessionParticipant,
                        context.human_participant_id,
                    )
                    assert human is not None
                    human.availability = ParticipantAvailability.UNAVAILABLE

            result = await progression.resume_discussion_progression(
                context.session_factory,
                owner_id=context.owner_id,
                session_id=context.session_id,
            )
            async with context.session_factory() as session:
                aggregate = await session.get(SimulationSession, context.session_id)
                assert aggregate is not None
                assert aggregate.current_floor_grant_id is not None
                grant = await session.get(
                    FloorGrant,
                    aggregate.current_floor_grant_id,
                )
                assert grant is not None
                participant = await session.get(
                    SessionParticipant,
                    grant.participant_id,
                )

            assert (
                result.outcome
                is progression.DiscussionProgressionOutcome.AI_DRIVE_COMPLETED
            )
            assert result.scheduler_result is not None
            assert result.scheduler_result.next_participant_id == grant.participant_id
            assert participant is not None
            assert participant.actor_kind == ParticipantActorKind.AI
            assert configured_calls == 1

    run_async(exercise)


def test_repeated_initial_progression_converges_to_one_durable_checkpoint(
    migrated_database: TemporaryDatabaseContext,
) -> None:
    async def exercise() -> None:
        async with _initial_phase_context(migrated_database) as context:
            async with context.session_factory() as session:
                aggregate = await session.get(SimulationSession, context.session_id)
                assert aggregate is not None
                phase = SessionStatus(aggregate.status)
                phase_entry_sequence = aggregate.last_sequence
            identities = progression.derive_initial_scheduler_identities(
                session_id=context.session_id,
                phase=phase,
                phase_entry_sequence=phase_entry_sequence,
            )

            first = await progression.resume_discussion_progression(
                context.session_factory,
                owner_id=context.owner_id,
                session_id=context.session_id,
            )
            second = await progression.resume_discussion_progression(
                context.session_factory,
                owner_id=context.owner_id,
                session_id=context.session_id,
            )

            async with context.session_factory() as session:
                action_count = await session.scalar(
                    select(func.count())
                    .select_from(SessionAction)
                    .where(
                        SessionAction.session_id == context.session_id,
                        SessionAction.action_id == identities.schedule_action_id,
                    )
                )
                decision_count = await session.scalar(
                    select(func.count())
                    .select_from(FloorDecision)
                    .where(FloorDecision.id == identities.decision_id)
                )
                active_grant_count = await session.scalar(
                    select(func.count())
                    .select_from(FloorGrant)
                    .outerjoin(
                        FloorRelease,
                        FloorRelease.grant_id == FloorGrant.id,
                    )
                    .where(
                        FloorGrant.session_id == context.session_id,
                        FloorRelease.grant_id.is_(None),
                    )
                )

            assert (
                first.outcome
                is progression.DiscussionProgressionOutcome.NEXT_HUMAN_GRANTED
            )
            assert second.outcome is progression.DiscussionProgressionOutcome.NO_WORK
            assert action_count == 1
            assert decision_count == 1
            assert active_grant_count is not None
            assert active_grant_count <= 1

    run_async(exercise)


def test_initial_intervention_replays_from_latest_current_phase_entry(
    migrated_database: TemporaryDatabaseContext,
) -> None:
    async def exercise() -> None:
        async with _initial_phase_context(migrated_database) as context:
            async with context.session_factory() as session, session.begin():
                aggregate = await session.get(SimulationSession, context.session_id)
                assert aggregate is not None
                phase = SessionStatus(aggregate.status)
                phase_entry_sequence = aggregate.last_sequence
                participants = tuple(
                    (
                        await session.scalars(
                            select(SessionParticipant).where(
                                SessionParticipant.session_id == context.session_id
                            )
                        )
                    ).all()
                )
                for participant in participants:
                    participant.availability = ParticipantAvailability.UNAVAILABLE

            identities = progression.derive_initial_scheduler_identities(
                session_id=context.session_id,
                phase=phase,
                phase_entry_sequence=phase_entry_sequence,
            )

            first = await progression.resume_discussion_progression(
                context.session_factory,
                owner_id=context.owner_id,
                session_id=context.session_id,
            )

            async with context.session_factory() as session:
                aggregate = await session.get(SimulationSession, context.session_id)
                assert aggregate is not None
                intervention_event = await session.scalar(
                    select(DiscussionEvent).where(
                        DiscussionEvent.session_id == context.session_id,
                        DiscussionEvent.event_type == "floor.intervention_requested",
                    )
                )
                assert intervention_event is not None
                assert intervention_event.sequence > phase_entry_sequence
                assert aggregate.last_sequence == intervention_event.sequence

            second = await progression.resume_discussion_progression(
                context.session_factory,
                owner_id=context.owner_id,
                session_id=context.session_id,
            )

            async with context.session_factory() as session:
                schedule_actions = tuple(
                    (
                        await session.scalars(
                            select(SessionAction).where(
                                SessionAction.session_id == context.session_id,
                                SessionAction.command_type == "floor.schedule",
                            )
                        )
                    ).all()
                )
                decision_count = await session.scalar(
                    select(func.count())
                    .select_from(FloorDecision)
                    .where(FloorDecision.session_id == context.session_id)
                )
                intervention_count = await session.scalar(
                    select(func.count())
                    .select_from(FloorIntervention)
                    .where(FloorIntervention.session_id == context.session_id)
                )
                grant_count = await session.scalar(
                    select(func.count())
                    .select_from(FloorGrant)
                    .where(FloorGrant.session_id == context.session_id)
                )
                intervention_event_count = await session.scalar(
                    select(func.count())
                    .select_from(DiscussionEvent)
                    .where(
                        DiscussionEvent.session_id == context.session_id,
                        DiscussionEvent.event_type == "floor.intervention_requested",
                    )
                )

            assert (
                first.outcome
                is progression.DiscussionProgressionOutcome.INTERVENTION_REQUESTED
            )
            assert second == first
            assert len(schedule_actions) == 1
            assert schedule_actions[0].action_id == identities.schedule_action_id
            assert decision_count == 1
            assert intervention_count == 1
            assert grant_count == 0
            assert intervention_event_count == 1

    run_async(exercise)
