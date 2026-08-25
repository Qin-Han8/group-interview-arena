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
from group_interview_arena_api.modules.floor_control.domain import (
    FloorDecisionOutcome,
    FloorDecisionRecord,
    FloorPolicyReason,
    FloorReleaseReason,
    GrantFloorCommand,
    ParticipantAvailability,
    ReleaseFloorCommand,
    SafeDecisionMetadata,
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
