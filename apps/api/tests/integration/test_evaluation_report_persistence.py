import asyncio
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Protocol
from uuid import UUID, uuid4

import pytest
from sqlalchemy import URL, func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from group_interview_arena_api.core.config import DatabaseSettings
from group_interview_arena_api.db.models import (
    DiscussionEvent,
    EvaluationReport,
    EvidenceItem,
    SessionParticipant,
    SimulationSession,
    User,
)
from group_interview_arena_api.db.runtime import (
    create_database_engine,
    create_database_session_factory,
    dispose_database_engine,
)
from group_interview_arena_api.modules.evaluation_reports import (
    service as report_service,
)
from group_interview_arena_api.modules.evaluation_reports.domain import (
    ReportGenerationStatus,
)
from group_interview_arena_api.modules.evaluation_reports.service import (
    ReportSessionIneligibleError,
    ReportSessionNotFoundError,
    get_or_create_eligible_report,
)

pytestmark = pytest.mark.integration


class TemporaryDatabaseContext(Protocol):
    database_name: str
    database_url: URL

    def database_settings(self) -> DatabaseSettings: ...


def _run(operation: Callable[[], Awaitable[None]]) -> None:
    asyncio.run(operation(), loop_factory=asyncio.SelectorEventLoop)


async def _seed_session(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    status: str,
    last_sequence: int = 7,
) -> tuple[UUID, UUID, UUID, int]:
    now = datetime.now(UTC)
    owner_id = uuid4()
    session_id = uuid4()
    participant_id = uuid4()
    phase_values: dict[str, object] = {}
    if status in {
        "PREPARATION",
        "OPENING_STATEMENTS",
        "EXPLORATION",
        "CONFLICT_AND_EVALUATION",
        "CONVERGENCE",
        "FINAL_SUMMARY",
    }:
        phase_values = {
            "phase_started_at": now,
            "phase_deadline_at": now + timedelta(minutes=1),
            "phase_duration_plan": {
                "PREPARATION": 60,
                "OPENING_STATEMENTS": 60,
                "EXPLORATION": 60,
                "CONFLICT_AND_EVALUATION": 60,
                "CONVERGENCE": 60,
                "FINAL_SUMMARY": 60,
            },
        }
    async with session_factory() as session, session.begin():
        session.add(
            User(
                id=owner_id,
                username=f"r-{owner_id.hex[:24]}",
                password_hash="hash",
                created_at=now,
                updated_at=now,
            )
        )
        await session.flush()
        session.add(
            SimulationSession(
                id=session_id,
                owner_user_id=owner_id,
                status=status,
                last_sequence=last_sequence,
                created_at=now,
                updated_at=now,
                **phase_values,
            )
        )
        await session.flush()
        session.add(
            SessionParticipant(
                id=participant_id,
                session_id=session_id,
                actor_kind="HUMAN",
                participation_role="CANDIDATE",
                seat_order=1,
                availability="AVAILABLE",
                user_id=owner_id,
                question_persona_assignment_id=None,
                created_at=now,
            )
        )
        if last_sequence > 0:
            session.add(
                DiscussionEvent(
                    session_id=session_id,
                    sequence=last_sequence,
                    event_version=1,
                    event_type="participant.utterance.created",
                    causation_action_id=None,
                    payload={
                        "utterance_id": str(uuid4()),
                        "participant_id": str(participant_id),
                        "actor_kind": "HUMAN",
                        "phase": "FINAL_SUMMARY",
                        "content": "A source utterance.",
                    },
                    occurred_at=now,
                )
            )
    return owner_id, session_id, participant_id, last_sequence


def test_only_completed_session_is_eligible(
    migrated_database: TemporaryDatabaseContext,
) -> None:
    async def verify() -> None:
        engine = create_database_engine(migrated_database.database_settings())
        session_factory = create_database_session_factory(engine)
        try:
            owner_id, session_id, _, watermark = await _seed_session(
                session_factory,
                status="COMPLETED",
            )
            async with session_factory() as session:
                result = await get_or_create_eligible_report(
                    session,
                    owner_id=owner_id,
                    session_id=session_id,
                    report_schema_version=1,
                    derivation_version="basic-evidence/v1",
                )
            assert result.session_id == session_id
            assert result.source_through_sequence == watermark
            assert result.status is ReportGenerationStatus.REQUESTED
            assert result.overall_summary is None
            assert result.priority_improvement is None
        finally:
            await dispose_database_engine(engine)

    _run(verify)


@pytest.mark.parametrize(
    "status",
    ["CREATED", "OPENING_STATEMENTS", "ABORTED_USER"],
)
def test_non_completed_session_is_rejected(
    migrated_database: TemporaryDatabaseContext,
    status: str,
) -> None:
    async def verify() -> None:
        engine = create_database_engine(migrated_database.database_settings())
        session_factory = create_database_session_factory(engine)
        try:
            owner_id, session_id, _, _ = await _seed_session(
                session_factory,
                status=status,
            )
            async with session_factory() as session:
                with pytest.raises(ReportSessionIneligibleError):
                    await get_or_create_eligible_report(
                        session,
                        owner_id=owner_id,
                        session_id=session_id,
                        report_schema_version=1,
                        derivation_version="basic-evidence/v1",
                    )
        finally:
            await dispose_database_engine(engine)

    _run(verify)


def test_missing_or_wrong_owner_session_is_not_disclosed(
    migrated_database: TemporaryDatabaseContext,
) -> None:
    async def verify() -> None:
        engine = create_database_engine(migrated_database.database_settings())
        session_factory = create_database_session_factory(engine)
        try:
            owner_id, session_id, _, _ = await _seed_session(
                session_factory,
                status="COMPLETED",
            )
            async with session_factory() as session:
                for requested_owner, requested_session in (
                    (uuid4(), session_id),
                    (owner_id, uuid4()),
                ):
                    with pytest.raises(ReportSessionNotFoundError):
                        await get_or_create_eligible_report(
                            session,
                            owner_id=requested_owner,
                            session_id=requested_session,
                            report_schema_version=1,
                            derivation_version="basic-evidence/v1",
                        )
        finally:
            await dispose_database_engine(engine)

    _run(verify)


def test_generation_identity_is_idempotent_and_versioned(
    migrated_database: TemporaryDatabaseContext,
) -> None:
    async def verify() -> None:
        engine = create_database_engine(migrated_database.database_settings())
        session_factory = create_database_session_factory(engine)
        try:
            owner_id, session_id, participant_id, watermark = await _seed_session(
                session_factory,
                status="COMPLETED",
            )
            async with session_factory() as session:
                first = await get_or_create_eligible_report(
                    session,
                    owner_id=owner_id,
                    session_id=session_id,
                    report_schema_version=1,
                    derivation_version="basic-evidence/v1",
                )
                replay = await get_or_create_eligible_report(
                    session,
                    owner_id=owner_id,
                    session_id=session_id,
                    report_schema_version=1,
                    derivation_version="basic-evidence/v1",
                )
                evolved = await get_or_create_eligible_report(
                    session,
                    owner_id=owner_id,
                    session_id=session_id,
                    report_schema_version=1,
                    derivation_version="basic-evidence/v2",
                )
                async with session.begin():
                    aggregate = await session.get(SimulationSession, session_id)
                    assert aggregate is not None
                    aggregate.last_sequence = watermark + 1
                    session.add(
                        DiscussionEvent(
                            session_id=session_id,
                            sequence=watermark + 1,
                            event_version=1,
                            event_type="participant.utterance.created",
                            causation_action_id=None,
                            payload={
                                "utterance_id": str(uuid4()),
                                "participant_id": str(participant_id),
                                "actor_kind": "HUMAN",
                                "phase": "FINAL_SUMMARY",
                                "content": "A later source utterance.",
                            },
                            occurred_at=datetime.now(UTC),
                        )
                    )
                new_watermark = await get_or_create_eligible_report(
                    session,
                    owner_id=owner_id,
                    session_id=session_id,
                    report_schema_version=1,
                    derivation_version="basic-evidence/v1",
                )
                count = await session.scalar(
                    select(func.count()).select_from(EvaluationReport)
                )
            assert first.report_id == replay.report_id
            assert evolved.report_id != first.report_id
            assert new_watermark.report_id not in {
                first.report_id,
                evolved.report_id,
            }
            assert new_watermark.source_through_sequence == watermark + 1
            assert count == 3
        finally:
            await dispose_database_engine(engine)

    _run(verify)


@pytest.mark.parametrize(
    "overrides",
    [
        {"status": "BOGUS"},
        {"source_through_sequence": -1},
        {
            "status": "COMPLETED",
            "started_at": datetime.now(UTC),
            "completed_at": datetime.now(UTC),
        },
    ],
)
def test_report_constraints_reject_invalid_rows(
    migrated_database: TemporaryDatabaseContext,
    overrides: dict[str, object],
) -> None:
    async def verify() -> None:
        engine = create_database_engine(migrated_database.database_settings())
        session_factory = create_database_session_factory(engine)
        try:
            _, session_id, _, watermark = await _seed_session(
                session_factory,
                status="COMPLETED",
            )
            values: dict[str, object] = {
                "id": uuid4(),
                "session_id": session_id,
                "report_schema_version": 1,
                "derivation_version": "basic-evidence/v1",
                "source_through_sequence": watermark,
                "status": "REQUESTED",
                "created_at": datetime.now(UTC),
            }
            values.update(overrides)
            with pytest.raises(IntegrityError):
                async with session_factory() as session, session.begin():
                    session.add(EvaluationReport(**values))
        finally:
            await dispose_database_engine(engine)

    _run(verify)


@pytest.mark.parametrize(
    ("case", "override"),
    [
        ("kind", {"kind": "SCORE"}),
        ("confidence-low", {"confidence": Decimal("-0.001")}),
        ("confidence-high", {"confidence": Decimal("1.001")}),
        ("phase", {"phase": "PREPARATION"}),
        ("participant", {}),
        ("event", {}),
        ("report", {}),
    ],
)
def test_evidence_constraints_reject_invalid_rows(
    migrated_database: TemporaryDatabaseContext,
    case: str,
    override: dict[str, object],
) -> None:
    async def verify() -> None:
        engine = create_database_engine(migrated_database.database_settings())
        session_factory = create_database_session_factory(engine)
        try:
            owner_one, session_one, participant_one, sequence_one = await _seed_session(
                session_factory, status="COMPLETED"
            )
            _, session_two, participant_two, sequence_two = await _seed_session(
                session_factory,
                status="COMPLETED",
                last_sequence=8,
            )
            async with session_factory() as session:
                report = await get_or_create_eligible_report(
                    session,
                    owner_id=owner_one,
                    session_id=session_one,
                    report_schema_version=1,
                    derivation_version="basic-evidence/v1",
                )
            values: dict[str, object] = {
                "id": uuid4(),
                "session_id": session_one,
                "report_id": report.report_id,
                "kind": "STRENGTH",
                "source_participant_id": participant_one,
                "source_utterance_id": uuid4(),
                "source_event_sequence": sequence_one,
                "phase": "FINAL_SUMMARY",
                "quote": "A source utterance.",
                "interpretation": "A concise contribution.",
                "confidence": Decimal("0.875"),
                "created_at": datetime.now(UTC),
            }
            values.update(override)
            if case == "participant":
                values["source_participant_id"] = participant_two
            elif case == "event":
                values["source_event_sequence"] = sequence_two
            elif case == "report":
                values.update(
                    session_id=session_two,
                    source_participant_id=participant_two,
                    source_event_sequence=sequence_two,
                )
            with pytest.raises(IntegrityError):
                async with session_factory() as session, session.begin():
                    session.add(EvidenceItem(**values))
        finally:
            await dispose_database_engine(engine)

    _run(verify)


def test_concurrent_generation_identity_has_one_healthy_winner(
    migrated_database: TemporaryDatabaseContext,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def verify() -> None:
        engine = create_database_engine(migrated_database.database_settings())
        session_factory = create_database_session_factory(engine)
        try:
            owner_id, session_id, _, _ = await _seed_session(
                session_factory,
                status="COMPLETED",
            )
            original = report_service._load_eligible_session  # pyright: ignore[reportPrivateUsage]
            ready = asyncio.Event()
            arrival_lock = asyncio.Lock()
            arrivals = 0

            async def synchronized_load(
                session: AsyncSession,
                *,
                owner_id: UUID,
                session_id: UUID,
            ) -> SimulationSession:
                nonlocal arrivals
                row = await original(
                    session,
                    owner_id=owner_id,
                    session_id=session_id,
                )
                async with arrival_lock:
                    arrivals += 1
                    if arrivals == 2:
                        ready.set()
                await asyncio.wait_for(ready.wait(), timeout=5)
                return row

            monkeypatch.setattr(
                report_service,
                "_load_eligible_session",
                synchronized_load,
            )

            async def allocate() -> tuple[UUID, int]:
                async with session_factory() as session:
                    result = await get_or_create_eligible_report(
                        session,
                        owner_id=owner_id,
                        session_id=session_id,
                        report_schema_version=1,
                        derivation_version="basic-evidence/v1",
                    )
                    healthy = await session.scalar(text("SELECT 1"))
                    return result.report_id, int(healthy or 0)

            results = await asyncio.gather(allocate(), allocate())
            async with session_factory() as session:
                count = await session.scalar(
                    select(func.count()).select_from(EvaluationReport)
                )
            assert results[0][0] == results[1][0]
            assert [result[1] for result in results] == [1, 1]
            assert count == 1
        finally:
            await dispose_database_engine(engine)

    _run(verify)
