import asyncio
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Protocol
from uuid import UUID, uuid4

import pytest
from sqlalchemy import URL, func, select
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
from group_interview_arena_api.modules.evaluation_reports.coordinator import (
    ReportClaimTimeError,
    ReportGenerationPersistence,
    ReportGenerationPersistenceError,
)
from group_interview_arena_api.modules.evaluation_reports.domain import (
    ComposedReport,
    EvidenceItemDraft,
    EvidenceKind,
    EvidencePhase,
    ReportGenerationStatus,
)

pytestmark = pytest.mark.integration

T0 = datetime(2026, 9, 10, 12, 0, tzinfo=UTC)


class TemporaryDatabaseContext(Protocol):
    database_name: str
    database_url: URL

    def database_settings(self) -> DatabaseSettings: ...


def _run(operation: Callable[[], Awaitable[None]]) -> None:
    asyncio.run(operation(), loop_factory=asyncio.SelectorEventLoop)


async def _seed_report(
    factory: async_sessionmaker[AsyncSession],
    *,
    status: ReportGenerationStatus = ReportGenerationStatus.REQUESTED,
    started_at: datetime | None = None,
    failed_at: datetime | None = None,
) -> tuple[UUID, UUID, UUID, UUID, UUID]:
    owner_id = uuid4()
    session_id = uuid4()
    participant_id = uuid4()
    utterance_id = uuid4()
    report_id = uuid4()
    async with factory() as session, session.begin():
        session.add(
            User(
                id=owner_id,
                username=f"lifecycle-{owner_id.hex[:20]}",
                password_hash="hash",
                created_at=T0,
                updated_at=T0,
            )
        )
        await session.flush()
        session.add(
            SimulationSession(
                id=session_id,
                owner_user_id=owner_id,
                status="COMPLETED",
                last_sequence=1,
                created_at=T0,
                updated_at=T0,
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
                created_at=T0,
            )
        )
        session.add(
            DiscussionEvent(
                session_id=session_id,
                sequence=1,
                event_version=1,
                event_type="participant.utterance.created",
                causation_action_id=None,
                payload={"fixture": True},
                occurred_at=T0,
            )
        )
        session.add(
            EvaluationReport(
                id=report_id,
                session_id=session_id,
                report_schema_version=1,
                derivation_version="basic-report/v1",
                source_through_sequence=1,
                status=status.value,
                overall_summary=None,
                priority_improvement=None,
                created_at=T0,
                started_at=started_at,
                completed_at=None,
                failed_at=failed_at,
            )
        )
    return owner_id, session_id, report_id, participant_id, utterance_id


def _composition(
    *,
    report_id: UUID,
    session_id: UUID,
    participant_id: UUID,
    utterance_id: UUID,
    evidence_count: int = 1,
) -> ComposedReport:
    draft = EvidenceItemDraft(
        report_id=report_id,
        session_id=session_id,
        kind=EvidenceKind.STRENGTH,
        source_participant_id=participant_id,
        source_utterance_id=utterance_id,
        source_event_sequence=1,
        phase=EvidencePhase.OPENING_STATEMENTS,
        quote="Exact source",
        interpretation="Concrete contribution.",
        confidence=Decimal("1.000"),
    )
    return ComposedReport(
        report_id=report_id,
        session_id=session_id,
        overall_summary="Complete summary.",
        priority_improvement="Make the next trade-off explicit.",
        evidence_items=(draft,) * evidence_count,
    )


def test_claim_transitions_requested_fresh_running_and_completed(
    migrated_database: TemporaryDatabaseContext,
) -> None:
    async def verify() -> None:
        engine = create_database_engine(migrated_database.database_settings())
        factory = create_database_session_factory(engine)
        try:
            _, session_id, report_id, participant_id, utterance_id = await _seed_report(
                factory
            )
            persistence = ReportGenerationPersistence(factory)
            first = await persistence.claim(
                report_id=report_id,
                session_id=session_id,
                lease_duration=timedelta(minutes=5),
                now=T0 + timedelta(minutes=1),
            )
            assert first.claimed is True
            assert first.claimant_token == T0 + timedelta(minutes=1)
            assert first.report.status is ReportGenerationStatus.RUNNING
            first_token = first.claimant_token
            assert first_token is not None

            fresh = await persistence.claim(
                report_id=report_id,
                session_id=session_id,
                lease_duration=timedelta(minutes=5),
                now=T0 + timedelta(minutes=2),
            )
            assert fresh.claimed is False
            assert fresh.claimant_token is None
            assert fresh.report.started_at == first.claimant_token

            completed = await persistence.complete(
                report_id=report_id,
                session_id=session_id,
                claimant_token=first_token,
                composition=_composition(
                    report_id=report_id,
                    session_id=session_id,
                    participant_id=participant_id,
                    utterance_id=utterance_id,
                ),
                now=T0 + timedelta(minutes=3),
            )
            assert completed is not None
            assert completed.status is ReportGenerationStatus.COMPLETED

            immutable = await persistence.claim(
                report_id=report_id,
                session_id=session_id,
                lease_duration=timedelta(minutes=5),
                now=T0 + timedelta(minutes=20),
            )
            assert immutable.claimed is False
            assert immutable.report.status is ReportGenerationStatus.COMPLETED
        finally:
            await dispose_database_engine(engine)

    _run(verify)


def test_failed_retry_and_deterministic_stale_claim_cas(
    migrated_database: TemporaryDatabaseContext,
) -> None:
    async def verify() -> None:
        engine = create_database_engine(migrated_database.database_settings())
        factory = create_database_session_factory(engine)
        try:
            _, session_id, report_id, participant_id, utterance_id = await _seed_report(
                factory,
                status=ReportGenerationStatus.FAILED,
                started_at=T0 + timedelta(minutes=1),
                failed_at=T0 + timedelta(minutes=2),
            )
            persistence = ReportGenerationPersistence(factory)
            retry = await persistence.claim(
                report_id=report_id,
                session_id=session_id,
                lease_duration=timedelta(minutes=5),
                now=T0 + timedelta(minutes=3),
            )
            assert retry.claimed is True
            assert retry.report.failed_at is None
            retry_token = retry.claimant_token
            assert retry_token is not None

            takeover = await persistence.claim(
                report_id=report_id,
                session_id=session_id,
                lease_duration=timedelta(minutes=5),
                now=T0 + timedelta(minutes=8),
            )
            assert takeover.claimed is True
            assert takeover.claimant_token != retry.claimant_token
            takeover_token = takeover.claimant_token
            assert takeover_token is not None

            composition = _composition(
                report_id=report_id,
                session_id=session_id,
                participant_id=participant_id,
                utterance_id=utterance_id,
            )
            assert (
                await persistence.complete(
                    report_id=report_id,
                    session_id=session_id,
                    claimant_token=retry_token,
                    composition=composition,
                    now=T0 + timedelta(minutes=9),
                )
                is None
            )
            assert (
                await persistence.fail(
                    report_id=report_id,
                    session_id=session_id,
                    claimant_token=retry_token,
                    now=T0 + timedelta(minutes=9),
                )
                is None
            )
            completed = await persistence.complete(
                report_id=report_id,
                session_id=session_id,
                claimant_token=takeover_token,
                composition=composition,
                now=T0 + timedelta(minutes=9),
            )
            assert completed is not None
            assert completed.status is ReportGenerationStatus.COMPLETED
        finally:
            await dispose_database_engine(engine)

    _run(verify)


def test_stale_claimant_observes_winner_completed_with_evidence(
    migrated_database: TemporaryDatabaseContext,
) -> None:
    async def verify() -> None:
        engine = create_database_engine(migrated_database.database_settings())
        factory = create_database_session_factory(engine)
        try:
            _, session_id, report_id, participant_id, utterance_id = await _seed_report(
                factory
            )
            persistence = ReportGenerationPersistence(factory)
            first = await persistence.claim(
                report_id=report_id,
                session_id=session_id,
                lease_duration=timedelta(minutes=5),
                now=T0 + timedelta(minutes=1),
            )
            first_token = first.claimant_token
            assert first_token is not None

            winner = await persistence.claim(
                report_id=report_id,
                session_id=session_id,
                lease_duration=timedelta(minutes=5),
                now=T0 + timedelta(minutes=6),
            )
            winner_token = winner.claimant_token
            assert winner.claimed is True
            assert winner_token is not None
            winner_composition = _composition(
                report_id=report_id,
                session_id=session_id,
                participant_id=participant_id,
                utterance_id=utterance_id,
            )
            completed = await persistence.complete(
                report_id=report_id,
                session_id=session_id,
                claimant_token=winner_token,
                composition=winner_composition,
                now=T0 + timedelta(minutes=7),
            )
            assert completed is not None

            async with factory() as session:
                evidence_before = tuple(
                    (
                        await session.scalars(
                            select(EvidenceItem)
                            .where(EvidenceItem.report_id == report_id)
                            .order_by(EvidenceItem.id)
                        )
                    ).all()
                )
            assert len(evidence_before) == 1

            assert (
                await persistence.complete(
                    report_id=report_id,
                    session_id=session_id,
                    claimant_token=first_token,
                    composition=winner_composition,
                    now=T0 + timedelta(minutes=8),
                )
                is None
            )
            assert (
                await persistence.fail(
                    report_id=report_id,
                    session_id=session_id,
                    claimant_token=first_token,
                    now=T0 + timedelta(minutes=8),
                )
                is None
            )

            durable = await persistence.load(
                report_id=report_id,
                session_id=session_id,
            )
            assert durable.status is ReportGenerationStatus.COMPLETED
            assert durable.started_at == winner_token
            assert durable.overall_summary == winner_composition.overall_summary
            assert (
                durable.priority_improvement == winner_composition.priority_improvement
            )
            async with factory() as session:
                evidence_after = tuple(
                    (
                        await session.scalars(
                            select(EvidenceItem)
                            .where(EvidenceItem.report_id == report_id)
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


def test_failed_retry_rejects_non_monotonic_claim_token(
    migrated_database: TemporaryDatabaseContext,
) -> None:
    async def verify() -> None:
        engine = create_database_engine(migrated_database.database_settings())
        factory = create_database_session_factory(engine)
        try:
            _, session_id, report_id, _, _ = await _seed_report(
                factory,
                status=ReportGenerationStatus.FAILED,
                started_at=T0 + timedelta(minutes=2),
                failed_at=T0 + timedelta(minutes=3),
            )
            with pytest.raises(ReportClaimTimeError):
                await ReportGenerationPersistence(factory).claim(
                    report_id=report_id,
                    session_id=session_id,
                    lease_duration=timedelta(minutes=5),
                    now=T0 + timedelta(minutes=2),
                )
        finally:
            await dispose_database_engine(engine)

    _run(verify)


def test_atomic_completion_rolls_back_all_evidence_on_insert_failure(
    migrated_database: TemporaryDatabaseContext,
) -> None:
    async def verify() -> None:
        engine = create_database_engine(migrated_database.database_settings())
        factory = create_database_session_factory(engine)
        try:
            _, session_id, report_id, participant_id, utterance_id = await _seed_report(
                factory
            )
            duplicate_id = uuid4()
            persistence = ReportGenerationPersistence(
                factory,
                evidence_id_factory=lambda: duplicate_id,
            )
            claim = await persistence.claim(
                report_id=report_id,
                session_id=session_id,
                lease_duration=timedelta(minutes=5),
                now=T0 + timedelta(minutes=1),
            )
            claim_token = claim.claimant_token
            assert claim_token is not None
            with pytest.raises(ReportGenerationPersistenceError):
                await persistence.complete(
                    report_id=report_id,
                    session_id=session_id,
                    claimant_token=claim_token,
                    composition=_composition(
                        report_id=report_id,
                        session_id=session_id,
                        participant_id=participant_id,
                        utterance_id=utterance_id,
                        evidence_count=2,
                    ),
                    now=T0 + timedelta(minutes=2),
                )

            async with factory() as session:
                report = await session.get(EvaluationReport, report_id)
                evidence_count = await session.scalar(
                    select(func.count())
                    .select_from(EvidenceItem)
                    .where(EvidenceItem.report_id == report_id)
                )
            assert report is not None
            assert report.status == ReportGenerationStatus.RUNNING.value
            assert report.completed_at is None
            assert evidence_count == 0

            failed = await persistence.fail(
                report_id=report_id,
                session_id=session_id,
                claimant_token=claim_token,
                now=T0 + timedelta(minutes=3),
            )
            assert failed is not None
            assert failed.status is ReportGenerationStatus.FAILED
            async with factory() as session:
                assert (
                    await session.scalar(
                        select(func.count())
                        .select_from(EvidenceItem)
                        .where(EvidenceItem.report_id == report_id)
                    )
                    == 0
                )
        finally:
            await dispose_database_engine(engine)

    _run(verify)
