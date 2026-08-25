import asyncio
from collections.abc import Callable, Coroutine
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
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
from group_interview_arena_api.modules.discussion_sessions import utterances
from group_interview_arena_api.modules.discussion_sessions.domain import (
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
from group_interview_arena_api.modules.floor_control.domain import (
    FloorDecisionOutcome,
    FloorDecisionRecord,
    FloorPolicyReason,
    FloorReleaseReason,
    GrantFloorCommand,
    ParticipantActorKind,
    ParticipantAvailability,
    ParticipationRole,
    ReleaseFloorCommand,
    SafeDecisionMetadata,
)
from group_interview_arena_api.modules.floor_control.service import apply_floor_command
from group_interview_arena_api.modules.question_personas.seed import (
    INTERNAL_VALIDATION_BUNDLE,
    seed_question_persona_foundation,
)

pytestmark = pytest.mark.integration

NOW = datetime(2026, 8, 25, 3, 0, tzinfo=UTC)
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
class HumanFloorContext:
    engine: AsyncEngine
    session_factory: async_sessionmaker[AsyncSession]
    owner_id: UUID
    other_user_id: UUID
    session_id: UUID
    human_participant_id: UUID
    ai_participant_id: UUID
    floor_grant_id: UUID
    phase_deadline_at: datetime


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


@asynccontextmanager
async def _human_floor_context(
    temporary_database: TemporaryDatabaseContext,
    *,
    grant_ai: bool = False,
):
    engine = create_database_engine(temporary_database.database_settings())
    session_factory = create_database_session_factory(engine)
    try:
        await seed_question_persona_foundation(session_factory)
        owner_id = uuid4()
        other_user_id = uuid4()
        async with session_factory() as session:
            async with session.begin():
                session.add_all(
                    [
                        User(
                            id=owner_id,
                            username=f"utterance_owner_{owner_id.hex[:10]}",
                            password_hash="test-only-password-hash",
                        ),
                        User(
                            id=other_user_id,
                            username=f"utterance_other_{other_user_id.hex[:10]}",
                            password_hash="test-only-password-hash",
                        ),
                    ]
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
        assert active.phase_deadline_at is not None
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
            aggregate = await session.get(SimulationSession, created.session_id)
        assert aggregate is not None
        grant_participant = participants[1] if grant_ai else participants[0]
        grant_id = uuid4()
        async with session_factory() as session:
            await apply_floor_command(
                session,
                owner_id=owner_id,
                command=GrantFloorCommand(
                    session_id=created.session_id,
                    action_id=uuid4(),
                    grant_id=grant_id,
                    decision=_grant_decision(
                        participant_id=grant_participant.id,
                        expected_last_sequence=aggregate.last_sequence,
                    ),
                ),
            )
        yield HumanFloorContext(
            engine=engine,
            session_factory=session_factory,
            owner_id=owner_id,
            other_user_id=other_user_id,
            session_id=created.session_id,
            human_participant_id=participants[0].id,
            ai_participant_id=participants[1].id,
            floor_grant_id=grant_id,
            phase_deadline_at=active.phase_deadline_at,
        )
    finally:
        await dispose_database_engine(engine)


@pytest.mark.parametrize(
    "content",
    ["", "   \t\n", "\x00", "a\x00b", "x" * 4001],
)
def test_human_content_policy_rejects_invalid_semantics(content: str) -> None:
    with pytest.raises(utterances.UtteranceRejectedError):
        utterances.validate_human_utterance_content(content)


def test_human_content_policy_preserves_exact_valid_text_and_uuid_golden() -> None:
    content = "  \u3000Preserve me exactly.\n"
    session_id = UUID("10000000-0000-4000-8000-000000000001")
    action_id = UUID("20000000-0000-4000-8000-000000000002")

    assert utterances.validate_human_utterance_content(content) == content
    assert utterances.validate_human_utterance_content("x" * 4000) == "x" * 4000
    assert utterances.derive_human_utterance_id(
        session_id=session_id,
        action_id=action_id,
    ) == UUID("b79517b0-c03c-4426-ae05-3e245bd5ce1d")


def test_human_submit_commits_exact_n_n_plus_one_and_strict_replay(
    migrated_database: TemporaryDatabaseContext,
) -> None:
    async def exercise() -> None:
        async with _human_floor_context(migrated_database) as context:
            action_id = uuid4()
            content = "  Exact Human content.\n"
            command = utterances.SubmitHumanUtterance(
                session_id=context.session_id,
                action_id=action_id,
                floor_grant_id=context.floor_grant_id,
                content=content,
                received_at=NOW,
            )
            async with context.session_factory() as session:
                first = await utterances.submit_human_utterance(
                    session,
                    owner_id=context.owner_id,
                    command=command,
                )
            async with context.session_factory() as session:
                replay = await utterances.submit_human_utterance(
                    session,
                    owner_id=context.owner_id,
                    command=command,
                )
                action = await session.get(
                    SessionAction, (context.session_id, action_id)
                )
                release = await session.get(FloorRelease, context.floor_grant_id)
                aggregate = await session.get(SimulationSession, context.session_id)
                rows = tuple(
                    (
                        await session.scalars(
                            select(DiscussionEvent)
                            .where(
                                DiscussionEvent.session_id == context.session_id,
                                DiscussionEvent.causation_action_id == action_id,
                            )
                            .order_by(DiscussionEvent.sequence)
                        )
                    ).all()
                )

            assert first.replayed is False
            assert replay.replayed is True
            assert first.utterance_id == replay.utterance_id
            assert first.events == replay.events
            assert [row.event_type for row in rows] == [
                "participant.utterance.created",
                "floor.released",
            ]
            assert [row.event_version for row in rows] == [1, 2]
            assert rows[1].sequence == rows[0].sequence + 1
            assert rows[0].payload == {
                "utterance_id": str(first.utterance_id),
                "participant_id": str(context.human_participant_id),
                "actor_kind": ParticipantActorKind.HUMAN.value,
                "floor_grant_id": str(context.floor_grant_id),
                "phase": SessionStatus.OPENING_STATEMENTS.value,
                "content": content,
            }
            assert action is not None
            assert action.command_type == "participant.utterance.submit"
            assert release is not None
            assert release.causation_action_id == action_id
            assert release.reason_code == "SPEAKER_FINISHED"
            assert aggregate is not None
            assert aggregate.current_floor_grant_id is None
            assert aggregate.last_sequence == rows[1].sequence

            conflicting = utterances.SubmitHumanUtterance(
                session_id=context.session_id,
                action_id=action_id,
                floor_grant_id=context.floor_grant_id,
                content="Different semantic content.",
                received_at=NOW + timedelta(seconds=5),
            )
            async with context.session_factory() as session:
                with pytest.raises(ActionIdConflictError):
                    await utterances.submit_human_utterance(
                        session,
                        owner_id=context.owner_id,
                        command=conflicting,
                    )

            different_floor = utterances.SubmitHumanUtterance(
                session_id=context.session_id,
                action_id=action_id,
                floor_grant_id=uuid4(),
                content=content,
                received_at=NOW + timedelta(seconds=10),
            )
            async with context.session_factory() as session:
                with pytest.raises(ActionIdConflictError):
                    await utterances.submit_human_utterance(
                        session,
                        owner_id=context.owner_id,
                        command=different_floor,
                    )

    run_async(exercise)


@pytest.mark.parametrize(
    "case",
    ["wrong_owner", "ai_floor", "no_floor", "unavailable", "non_candidate"],
)
def test_human_submit_rejects_untrusted_or_stale_authority(
    migrated_database: TemporaryDatabaseContext,
    case: str,
) -> None:
    async def exercise() -> None:
        async with _human_floor_context(
            migrated_database,
            grant_ai=case == "ai_floor",
        ) as context:
            if case == "no_floor":
                async with context.session_factory() as session:
                    async with session.begin():
                        aggregate = await session.get(
                            SimulationSession, context.session_id
                        )
                        assert aggregate is not None
                        aggregate.current_floor_grant_id = None
            if case == "unavailable":
                async with context.session_factory() as session:
                    async with session.begin():
                        participant = await session.get(
                            SessionParticipant, context.human_participant_id
                        )
                        assert participant is not None
                        participant.availability = ParticipantAvailability.UNAVAILABLE
            if case == "non_candidate":
                async with context.session_factory() as session:
                    async with session.begin():
                        participant = await session.get(
                            SessionParticipant, context.human_participant_id
                        )
                        assert participant is not None
                        participant.participation_role = ParticipationRole.MODERATOR

            owner_id = (
                context.other_user_id if case == "wrong_owner" else context.owner_id
            )
            async with context.session_factory() as session:
                with pytest.raises(utterances.UtteranceRejectedError):
                    await utterances.submit_human_utterance(
                        session,
                        owner_id=owner_id,
                        command=utterances.SubmitHumanUtterance(
                            session_id=context.session_id,
                            action_id=uuid4(),
                            floor_grant_id=context.floor_grant_id,
                            content="Rejected content must not become a fact.",
                            received_at=NOW,
                        ),
                    )
            async with context.session_factory() as session:
                count = await session.scalar(
                    select(func.count())
                    .select_from(DiscussionEvent)
                    .where(
                        DiscussionEvent.session_id == context.session_id,
                        DiscussionEvent.event_type == "participant.utterance.created",
                    )
                )
            assert count == 0

    run_async(exercise)


def test_stale_human_floor_binding_cannot_submit_during_later_grant(
    migrated_database: TemporaryDatabaseContext,
) -> None:
    async def exercise() -> None:
        async with _human_floor_context(migrated_database) as context:
            stale_grant_id = context.floor_grant_id
            async with context.session_factory() as session:
                aggregate = await session.get(SimulationSession, context.session_id)
            assert aggregate is not None
            async with context.session_factory() as session:
                await apply_floor_command(
                    session,
                    owner_id=context.owner_id,
                    command=ReleaseFloorCommand(
                        session_id=context.session_id,
                        action_id=uuid4(),
                        grant_id=stale_grant_id,
                        expected_phase=SessionStatus(aggregate.status),
                        expected_last_sequence=aggregate.last_sequence,
                        reason=FloorReleaseReason.SPEAKER_FINISHED,
                    ),
                )

            later_grant_id = uuid4()
            async with context.session_factory() as session:
                aggregate = await session.get(SimulationSession, context.session_id)
            assert aggregate is not None
            async with context.session_factory() as session:
                await apply_floor_command(
                    session,
                    owner_id=context.owner_id,
                    command=GrantFloorCommand(
                        session_id=context.session_id,
                        action_id=uuid4(),
                        grant_id=later_grant_id,
                        decision=_grant_decision(
                            participant_id=context.human_participant_id,
                            expected_last_sequence=aggregate.last_sequence,
                        ),
                    ),
                )

            stale_action_id = uuid4()
            async with context.session_factory() as session:
                with pytest.raises(utterances.UtteranceRejectedError):
                    await utterances.submit_human_utterance(
                        session,
                        owner_id=context.owner_id,
                        command=utterances.SubmitHumanUtterance(
                            session_id=context.session_id,
                            action_id=stale_action_id,
                            floor_grant_id=stale_grant_id,
                            content="This stale command must never bind to G2.",
                            received_at=NOW,
                        ),
                    )

            async with context.session_factory() as session:
                aggregate = await session.get(SimulationSession, context.session_id)
                action = await session.get(
                    SessionAction, (context.session_id, stale_action_id)
                )
                stale_event_count = await session.scalar(
                    select(func.count())
                    .select_from(DiscussionEvent)
                    .where(
                        DiscussionEvent.session_id == context.session_id,
                        DiscussionEvent.causation_action_id == stale_action_id,
                    )
                )
                later_release = await session.get(FloorRelease, later_grant_id)
            assert aggregate is not None
            assert aggregate.current_floor_grant_id == later_grant_id
            assert action is None
            assert stale_event_count == 0
            assert later_release is None

    run_async(exercise)


def test_deadline_reconciliation_commits_before_human_rejection(
    migrated_database: TemporaryDatabaseContext,
) -> None:
    async def exercise() -> None:
        async with _human_floor_context(migrated_database) as context:
            async with context.session_factory() as session:
                with pytest.raises(utterances.UtteranceRejectedError):
                    await utterances.submit_human_utterance(
                        session,
                        owner_id=context.owner_id,
                        command=utterances.SubmitHumanUtterance(
                            session_id=context.session_id,
                            action_id=uuid4(),
                            floor_grant_id=context.floor_grant_id,
                            content="Arrived after authoritative deadline.",
                            received_at=context.phase_deadline_at,
                        ),
                    )
            async with context.session_factory() as session:
                aggregate = await session.get(SimulationSession, context.session_id)
                release = await session.get(FloorRelease, context.floor_grant_id)
                human_event_count = await session.scalar(
                    select(func.count())
                    .select_from(DiscussionEvent)
                    .where(
                        DiscussionEvent.session_id == context.session_id,
                        DiscussionEvent.event_type == "participant.utterance.created",
                    )
                )
            assert aggregate is not None
            assert aggregate.status == SessionStatus.EXPLORATION
            assert release is not None
            assert release.reason_code == "PHASE_CHANGED"
            assert release.causation_action_id is None
            assert human_event_count == 0

    run_async(exercise)


def test_concurrent_duplicate_human_submit_converges_to_one_commit(
    migrated_database: TemporaryDatabaseContext,
) -> None:
    async def exercise() -> None:
        async with _human_floor_context(migrated_database) as context:
            command = utterances.SubmitHumanUtterance(
                session_id=context.session_id,
                action_id=uuid4(),
                floor_grant_id=context.floor_grant_id,
                content="Concurrent exact replay.",
                received_at=NOW,
            )

            async def submit():
                async with context.session_factory() as session:
                    return await utterances.submit_human_utterance(
                        session,
                        owner_id=context.owner_id,
                        command=command,
                    )

            first, second = await asyncio.gather(submit(), submit())
            async with context.session_factory() as session:
                rows = tuple(
                    (
                        await session.scalars(
                            select(DiscussionEvent).where(
                                DiscussionEvent.session_id == context.session_id,
                                DiscussionEvent.causation_action_id
                                == command.action_id,
                            )
                        )
                    ).all()
                )
            assert {first.replayed, second.replayed} == {False, True}
            assert first.utterance_id == second.utterance_id
            assert len(rows) == 2

    run_async(exercise)


def test_injected_failure_rolls_back_action_events_release_and_watermark(
    migrated_database: TemporaryDatabaseContext,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def exercise() -> None:
        async with _human_floor_context(migrated_database) as context:
            async with context.session_factory() as session:
                before = await session.get(SimulationSession, context.session_id)
                assert before is not None
                prior_watermark = before.last_sequence

            async def injected_failure(*_args: object, **_kwargs: object):
                raise ValueError("test-only rollback injection")

            monkeypatch.setattr(
                utterances,
                "release_active_floor_for_lifecycle",
                injected_failure,
            )
            action_id = uuid4()
            async with context.session_factory() as session:
                with pytest.raises(SessionPersistenceError):
                    await utterances.submit_human_utterance(
                        session,
                        owner_id=context.owner_id,
                        command=utterances.SubmitHumanUtterance(
                            session_id=context.session_id,
                            action_id=action_id,
                            floor_grant_id=context.floor_grant_id,
                            content="Rollback all facts.",
                            received_at=NOW,
                        ),
                    )
            async with context.session_factory() as session:
                aggregate = await session.get(SimulationSession, context.session_id)
                action = await session.get(
                    SessionAction, (context.session_id, action_id)
                )
                release = await session.get(FloorRelease, context.floor_grant_id)
                count = await session.scalar(
                    select(func.count())
                    .select_from(DiscussionEvent)
                    .where(
                        DiscussionEvent.session_id == context.session_id,
                        DiscussionEvent.causation_action_id == action_id,
                    )
                )
            assert aggregate is not None
            assert aggregate.last_sequence == prior_watermark
            assert aggregate.current_floor_grant_id == context.floor_grant_id
            assert action is None
            assert release is None
            assert count == 0

    run_async(exercise)
