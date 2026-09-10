import asyncio
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Protocol
from uuid import UUID, uuid4

import pytest
from sqlalchemy import URL, func, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from group_interview_arena_api.core.config import DatabaseSettings
from group_interview_arena_api.db.models import (
    DiscussionEvent,
    EvaluationReport,
    EvidenceItem,
    PersonaPrivateStance,
    QuestionVersion,
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
from group_interview_arena_api.modules.evaluation_reports.coordinator import (
    ReportGenerationCoordinator,
    ReportGenerationError,
)
from group_interview_arena_api.modules.evaluation_reports.domain import (
    EvidencePhase,
    EvidenceProposal,
    ReportEvaluationProposal,
    ReportGenerationStatus,
    ReportSourceSnapshot,
)
from group_interview_arena_api.modules.evaluation_reports.evaluation import (
    DeterministicReportEvaluator,
)
from group_interview_arena_api.modules.evaluation_reports.source import (
    ReportSourceCollectionError,
    ReportSourceCollector,
)
from group_interview_arena_api.modules.question_personas.seed import (
    INTERNAL_VALIDATION_BUNDLE,
    seed_question_persona_foundation,
)

pytestmark = pytest.mark.integration

NOW = datetime(2026, 9, 10, 12, 0, tzinfo=UTC)
PRIVATE_SENTINEL = "P1_7C_PRIVATE_SENTINEL_DO_NOT_DISCLOSE"


class TemporaryDatabaseContext(Protocol):
    database_name: str
    database_url: URL

    def database_settings(self) -> DatabaseSettings: ...


def _run(operation: Callable[[], Awaitable[None]]) -> None:
    asyncio.run(operation(), loop_factory=asyncio.SelectorEventLoop)


async def _seed_source(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    include_report: bool = True,
) -> tuple[UUID, UUID, UUID, UUID]:
    await seed_question_persona_foundation(session_factory)
    owner_id = uuid4()
    session_id = uuid4()
    report_id = uuid4()
    human_id = uuid4()
    ai_ids = (uuid4(), uuid4(), uuid4())
    action_id = uuid4()
    floor_ids = (uuid4(), uuid4(), uuid4())
    async with session_factory() as session, session.begin():
        session.add(
            User(
                id=owner_id,
                username=f"collector-{owner_id.hex[:20]}",
                password_hash="hash",
                created_at=NOW,
                updated_at=NOW,
            )
        )
        await session.flush()
        session.add(
            SimulationSession(
                id=session_id,
                owner_user_id=owner_id,
                status="COMPLETED",
                last_sequence=4,
                question_version_id=INTERNAL_VALIDATION_BUNDLE.version_id,
                created_at=NOW,
                updated_at=NOW,
            )
        )
        await session.flush()
        session.add_all(
            [
                SessionParticipant(
                    id=human_id,
                    session_id=session_id,
                    actor_kind="HUMAN",
                    participation_role="CANDIDATE",
                    seat_order=1,
                    availability="AVAILABLE",
                    user_id=owner_id,
                    question_persona_assignment_id=None,
                    created_at=NOW,
                ),
                *(
                    SessionParticipant(
                        id=participant_id,
                        session_id=session_id,
                        actor_kind="AI",
                        participation_role="CANDIDATE",
                        seat_order=seat,
                        availability="AVAILABLE",
                        user_id=None,
                        question_persona_assignment_id=assignment.id,
                        created_at=NOW,
                    )
                    for participant_id, seat, assignment in zip(
                        ai_ids,
                        (2, 3, 4),
                        INTERNAL_VALIDATION_BUNDLE.assignments,
                        strict=True,
                    )
                ),
            ]
        )
        session.add(
            SessionAction(
                session_id=session_id,
                action_id=action_id,
                command_version=1,
                command_type="participant.utterance.submit",
                payload_digest=b"\x00" * 32,
                created_at=NOW,
            )
        )
        await session.flush()
        session.add_all(
            [
                DiscussionEvent(
                    session_id=session_id,
                    sequence=1,
                    event_version=2,
                    event_type="session.state_changed",
                    causation_action_id=None,
                    payload={"not": "an utterance"},
                    occurred_at=NOW,
                ),
                DiscussionEvent(
                    session_id=session_id,
                    sequence=2,
                    event_version=1,
                    event_type="participant.utterance.created",
                    causation_action_id=action_id,
                    payload={
                        "utterance_id": str(uuid4()),
                        "participant_id": str(human_id),
                        "actor_kind": "HUMAN",
                        "floor_grant_id": str(floor_ids[0]),
                        "phase": "OPENING_STATEMENTS",
                        "content": "  exact Human source\n",
                    },
                    occurred_at=NOW + timedelta(seconds=1),
                ),
                DiscussionEvent(
                    session_id=session_id,
                    sequence=3,
                    event_version=1,
                    event_type="participant.utterance.created",
                    causation_action_id=None,
                    payload={
                        "utterance_id": str(uuid4()),
                        "participant_id": str(ai_ids[0]),
                        "actor_kind": "AI",
                        "floor_grant_id": str(floor_ids[1]),
                        "phase": "EXPLORATION",
                        "content": "AI source",
                    },
                    occurred_at=NOW + timedelta(seconds=2),
                ),
                DiscussionEvent(
                    session_id=session_id,
                    sequence=4,
                    event_version=1,
                    event_type="participant.utterance.created",
                    causation_action_id=None,
                    payload={
                        "utterance_id": str(uuid4()),
                        "participant_id": str(ai_ids[1]),
                        "actor_kind": "AI",
                        "floor_grant_id": str(floor_ids[2]),
                        "phase": "CONVERGENCE",
                        "content": "Above report watermark",
                    },
                    occurred_at=NOW + timedelta(seconds=3),
                ),
            ]
        )
        if include_report:
            session.add(
                EvaluationReport(
                    id=report_id,
                    session_id=session_id,
                    report_schema_version=1,
                    derivation_version="basic-report/v1",
                    source_through_sequence=3,
                    status="REQUESTED",
                    overall_summary=None,
                    priority_improvement=None,
                    created_at=NOW,
                    started_at=None,
                    completed_at=None,
                    failed_at=None,
                )
            )
        await session.execute(
            update(QuestionVersion)
            .where(QuestionVersion.id == INTERNAL_VALIDATION_BUNDLE.version_id)
            .values(
                reference_dimensions=[
                    {
                        "key": "PRIVATE_SENTINEL",
                        "name": PRIVATE_SENTINEL,
                        "description": PRIVATE_SENTINEL,
                    }
                ],
                hidden_conflicts=[
                    {"key": "PRIVATE_SENTINEL", "text": PRIVATE_SENTINEL}
                ],
                acceptable_outcome_patterns=[
                    {"key": "PRIVATE_SENTINEL", "text": PRIVATE_SENTINEL}
                ],
                phase_prompts={"PREPARATION": PRIVATE_SENTINEL},
            )
        )
        await session.execute(
            update(PersonaPrivateStance).values(
                initial_position=PRIVATE_SENTINEL,
                private_information=PRIVATE_SENTINEL,
            )
        )
    return owner_id, session_id, report_id, human_id


def test_collector_builds_ordered_public_only_immutable_snapshot(
    migrated_database: TemporaryDatabaseContext,
) -> None:
    async def verify() -> None:
        engine = create_database_engine(migrated_database.database_settings())
        factory = create_database_session_factory(engine)
        try:
            _, session_id, report_id, human_id = await _seed_source(factory)
            async with factory() as session:
                snapshot = await ReportSourceCollector().collect(
                    session,
                    report_id=report_id,
                    session_id=session_id,
                )
                stored_report = await session.get(EvaluationReport, report_id)
                stored_session = await session.get(SimulationSession, session_id)

            assert snapshot.report_id == report_id
            assert snapshot.session_id == session_id
            assert snapshot.source_contract_version == 1
            assert snapshot.source_through_sequence == 3
            assert [item.seat_order for item in snapshot.participants] == [1, 2, 3, 4]
            assert (
                sum(item.actor_kind.value == "HUMAN" for item in snapshot.participants)
                == 1
            )
            assert snapshot.participants[0].participant_id == human_id
            assert [item.source_event_sequence for item in snapshot.utterances] == [
                2,
                3,
            ]
            assert snapshot.utterances[0].content == "  exact Human source\n"
            assert snapshot.utterances[0].phase.value == "OPENING_STATEMENTS"
            assert snapshot.utterances[1].actor_kind.value == "AI"
            assert stored_report is not None
            assert stored_report.source_through_sequence == 3
            assert stored_report.status == "REQUESTED"
            assert stored_session is not None
            assert stored_session.last_sequence == 4

            serialized = snapshot.model_dump_json()
            assert PRIVATE_SENTINEL not in serialized
            for forbidden in (
                "reference_dimensions",
                "hidden_conflicts",
                "acceptable_outcome_patterns",
                "private_stance",
                "calibration",
                "memory",
            ):
                assert forbidden not in serialized.lower()
        finally:
            await dispose_database_engine(engine)

    _run(verify)


class _InvalidQuoteEvaluator:
    async def evaluate(
        self,
        source: ReportSourceSnapshot,
        /,
    ) -> ReportEvaluationProposal:
        human = next(item for item in source.utterances if item.actor_kind == "HUMAN")
        return ReportEvaluationProposal(
            evaluation_contract_version=1,
            overall_summary="Untrusted summary",
            strengths=(
                EvidenceProposal(
                    source_participant_id=human.participant_id,
                    source_utterance_id=human.utterance_id,
                    source_event_sequence=human.source_event_sequence,
                    phase=EvidencePhase.OPENING_STATEMENTS,
                    quote="not an exact source substring",
                    interpretation="Untrusted interpretation",
                    confidence=Decimal("0.500"),
                ),
            ),
            improvements=(),
            priority_improvement="Untrusted priority",
        )


class _PausingEvaluator:
    def __init__(self, started: asyncio.Event, release: asyncio.Event) -> None:
        self._started = started
        self._release = release
        self.evaluation_count = 0

    async def evaluate(
        self,
        source: ReportSourceSnapshot,
        /,
    ) -> ReportEvaluationProposal:
        self.evaluation_count += 1
        self._started.set()
        await self._release.wait()
        return await DeterministicReportEvaluator().evaluate(source)


def test_coordinator_fails_invalid_proposal_then_retries_and_is_idempotent(
    migrated_database: TemporaryDatabaseContext,
) -> None:
    async def verify() -> None:
        engine = create_database_engine(migrated_database.database_settings())
        factory = create_database_session_factory(engine)
        try:
            owner_id, session_id, _, _ = await _seed_source(
                factory,
                include_report=False,
            )
            coordinator = ReportGenerationCoordinator(factory)
            with pytest.raises(ReportGenerationError):
                await coordinator.generate(
                    owner_id=owner_id,
                    session_id=session_id,
                    report_schema_version=1,
                    derivation_version="basic-report/v1",
                    evaluator=_InvalidQuoteEvaluator(),
                    lease_duration=timedelta(minutes=5),
                    now=NOW + timedelta(minutes=1),
                )

            async with factory() as session:
                failed = await session.scalar(
                    select(EvaluationReport).where(
                        EvaluationReport.session_id == session_id
                    )
                )
                assert failed is not None
                failed_id = failed.id
                assert failed.status == ReportGenerationStatus.FAILED.value
                assert (
                    await session.scalar(
                        select(func.count())
                        .select_from(EvidenceItem)
                        .where(EvidenceItem.report_id == failed_id)
                    )
                    == 0
                )

            evaluator = DeterministicReportEvaluator()
            completed = await coordinator.generate(
                owner_id=owner_id,
                session_id=session_id,
                report_schema_version=1,
                derivation_version="basic-report/v1",
                evaluator=evaluator,
                lease_duration=timedelta(minutes=5),
                now=NOW + timedelta(minutes=2),
            )
            assert completed.report_id == failed_id
            assert completed.status is ReportGenerationStatus.COMPLETED
            assert evaluator.evaluation_count == 1

            async with factory() as session:
                evidence_before = tuple(
                    (
                        await session.scalars(
                            select(EvidenceItem)
                            .where(EvidenceItem.report_id == failed_id)
                            .order_by(EvidenceItem.id)
                        )
                    ).all()
                )
            assert len(evidence_before) == 1
            assert evidence_before[0].quote == "  exact Human source\n"

            completed_again = await coordinator.generate(
                owner_id=owner_id,
                session_id=session_id,
                report_schema_version=1,
                derivation_version="basic-report/v1",
                evaluator=evaluator,
                lease_duration=timedelta(minutes=5),
                now=NOW + timedelta(minutes=3),
            )
            assert completed_again == completed
            assert evaluator.evaluation_count == 1
            async with factory() as session:
                evidence_after = tuple(
                    (
                        await session.scalars(
                            select(EvidenceItem)
                            .where(EvidenceItem.report_id == failed_id)
                            .order_by(EvidenceItem.id)
                        )
                    ).all()
                )
            assert [item.id for item in evidence_after] == [
                item.id for item in evidence_before
            ]
        finally:
            await dispose_database_engine(engine)

    _run(verify)


def test_coordinator_rejects_invalid_lease_before_report_allocation(
    migrated_database: TemporaryDatabaseContext,
) -> None:
    async def verify() -> None:
        engine = create_database_engine(migrated_database.database_settings())
        factory = create_database_session_factory(engine)
        try:
            owner_id, session_id, _, _ = await _seed_source(
                factory,
                include_report=False,
            )
            with pytest.raises(ValueError, match="lease"):
                await ReportGenerationCoordinator(factory).generate(
                    owner_id=owner_id,
                    session_id=session_id,
                    report_schema_version=1,
                    derivation_version="basic-report/v1",
                    evaluator=DeterministicReportEvaluator(),
                    lease_duration=timedelta(0),
                    now=NOW + timedelta(minutes=1),
                )
            async with factory() as session:
                assert (
                    await session.scalar(
                        select(func.count()).select_from(EvaluationReport)
                    )
                    == 0
                )
        finally:
            await dispose_database_engine(engine)

    _run(verify)


def test_coordinator_allows_one_fresh_claimant_without_holding_db_scope(
    migrated_database: TemporaryDatabaseContext,
) -> None:
    async def verify() -> None:
        engine = create_database_engine(migrated_database.database_settings())
        factory = create_database_session_factory(engine)
        try:
            owner_id, session_id, _, _ = await _seed_source(
                factory,
                include_report=False,
            )
            coordinator = ReportGenerationCoordinator(factory)
            started = asyncio.Event()
            release = asyncio.Event()
            first_evaluator = _PausingEvaluator(started, release)
            skipped_evaluator = DeterministicReportEvaluator()
            first = asyncio.create_task(
                coordinator.generate(
                    owner_id=owner_id,
                    session_id=session_id,
                    report_schema_version=1,
                    derivation_version="basic-report/v1",
                    evaluator=first_evaluator,
                    lease_duration=timedelta(minutes=5),
                    now=NOW + timedelta(minutes=1),
                )
            )
            await started.wait()

            async with factory() as independent_session:
                assert await independent_session.scalar(text("SELECT 1")) == 1

            second = await coordinator.generate(
                owner_id=owner_id,
                session_id=session_id,
                report_schema_version=1,
                derivation_version="basic-report/v1",
                evaluator=skipped_evaluator,
                lease_duration=timedelta(minutes=5),
                now=NOW + timedelta(minutes=1, seconds=1),
            )
            assert second.status is ReportGenerationStatus.RUNNING
            assert skipped_evaluator.evaluation_count == 0
            release.set()
            completed = await first
            assert completed.status is ReportGenerationStatus.COMPLETED
            assert first_evaluator.evaluation_count == 1

            async with factory() as session:
                assert (
                    await session.scalar(
                        select(func.count()).select_from(EvaluationReport)
                    )
                    == 1
                )
                assert (
                    await session.scalar(select(func.count()).select_from(EvidenceItem))
                    == 1
                )
                assert await session.scalar(text("SELECT 1")) == 1
        finally:
            await dispose_database_engine(engine)

    _run(verify)


def test_stale_coordinator_returns_completed_winner_after_lease_takeover(
    migrated_database: TemporaryDatabaseContext,
) -> None:
    async def verify() -> None:
        engine = create_database_engine(migrated_database.database_settings())
        factory = create_database_session_factory(engine)
        try:
            owner_id, session_id, _, _ = await _seed_source(
                factory,
                include_report=False,
            )
            coordinator = ReportGenerationCoordinator(factory)
            started = asyncio.Event()
            release = asyncio.Event()
            stale_evaluator = _PausingEvaluator(started, release)
            winner_evaluator = DeterministicReportEvaluator()
            stale_task = asyncio.create_task(
                coordinator.generate(
                    owner_id=owner_id,
                    session_id=session_id,
                    report_schema_version=1,
                    derivation_version="basic-report/v1",
                    evaluator=stale_evaluator,
                    lease_duration=timedelta(minutes=5),
                    now=NOW + timedelta(minutes=1),
                )
            )
            await started.wait()

            winner = await coordinator.generate(
                owner_id=owner_id,
                session_id=session_id,
                report_schema_version=1,
                derivation_version="basic-report/v1",
                evaluator=winner_evaluator,
                lease_duration=timedelta(minutes=5),
                now=NOW + timedelta(minutes=6),
            )
            assert winner.status is ReportGenerationStatus.COMPLETED
            assert winner_evaluator.evaluation_count == 1

            release.set()
            stale_result = await stale_task
            assert stale_result == winner
            assert stale_evaluator.evaluation_count == 1

            async with factory() as session:
                report = await session.scalar(
                    select(EvaluationReport).where(
                        EvaluationReport.session_id == session_id
                    )
                )
                evidence = tuple(
                    (
                        await session.scalars(
                            select(EvidenceItem).where(
                                EvidenceItem.session_id == session_id
                            )
                        )
                    ).all()
                )
            assert report is not None
            assert report.status == ReportGenerationStatus.COMPLETED.value
            assert report.started_at == NOW + timedelta(minutes=6)
            assert len(evidence) == 1
        finally:
            await dispose_database_engine(engine)

    _run(verify)


@pytest.mark.parametrize(
    "corruption",
    [
        "wrong_session",
        "missing_question",
        "malformed_event",
        "missing_participant",
        "actor_mismatch",
    ],
)
def test_collector_fails_closed_for_invalid_authoritative_source(
    migrated_database: TemporaryDatabaseContext,
    corruption: str,
) -> None:
    async def verify() -> None:
        engine = create_database_engine(migrated_database.database_settings())
        factory = create_database_session_factory(engine)
        try:
            _, session_id, report_id, human_id = await _seed_source(factory)
            requested_session_id = session_id
            if corruption == "wrong_session":
                requested_session_id = uuid4()
            elif corruption == "missing_question":
                async with factory() as session, session.begin():
                    await session.execute(
                        update(SimulationSession)
                        .where(SimulationSession.id == session_id)
                        .values(question_version_id=None)
                    )
            else:
                async with factory() as session, session.begin():
                    event = await session.scalar(
                        select(DiscussionEvent).where(
                            DiscussionEvent.session_id == session_id,
                            DiscussionEvent.sequence == 3,
                        )
                    )
                    assert event is not None
                    payload = dict(event.payload)
                    if corruption == "malformed_event":
                        payload.pop("floor_grant_id")
                    elif corruption == "missing_participant":
                        payload["participant_id"] = str(uuid4())
                    else:
                        payload["participant_id"] = str(human_id)
                    event.payload = payload

            async with factory() as session:
                with pytest.raises(ReportSourceCollectionError):
                    await ReportSourceCollector().collect(
                        session,
                        report_id=report_id,
                        session_id=requested_session_id,
                    )
        finally:
            await dispose_database_engine(engine)

    _run(verify)
