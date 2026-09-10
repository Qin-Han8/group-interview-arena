from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from group_interview_arena_api.db.models import EvaluationReport, EvidenceItem
from group_interview_arena_api.modules.evaluation_reports.domain import (
    ComposedReport,
    EvaluationReportSnapshot,
    ReportGenerationStatus,
)
from group_interview_arena_api.modules.evaluation_reports.evaluation import (
    ReportComposer,
    ReportEvaluator,
)
from group_interview_arena_api.modules.evaluation_reports.service import (
    get_or_create_eligible_report,
)
from group_interview_arena_api.modules.evaluation_reports.source import (
    ReportSourceCollector,
)


class ReportGenerationPersistenceError(RuntimeError):
    pass


class ReportGenerationInvariantError(ReportGenerationPersistenceError):
    pass


class ReportClaimTimeError(ValueError):
    pass


class ReportGenerationError(RuntimeError):
    pass


@dataclass(frozen=True)
class ReportGenerationClaim:
    claimed: bool
    report: EvaluationReportSnapshot
    claimant_token: datetime | None


def _snapshot(row: EvaluationReport) -> EvaluationReportSnapshot:
    return EvaluationReportSnapshot(
        report_id=row.id,
        session_id=row.session_id,
        report_schema_version=row.report_schema_version,
        derivation_version=row.derivation_version,
        source_through_sequence=row.source_through_sequence,
        status=ReportGenerationStatus(row.status),
        overall_summary=row.overall_summary,
        priority_improvement=row.priority_improvement,
        created_at=row.created_at,
        started_at=row.started_at,
        completed_at=row.completed_at,
        failed_at=row.failed_at,
    )


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ReportClaimTimeError("generation timestamps must be timezone-aware")
    return value.astimezone(UTC)


def _require_positive_lease(value: timedelta) -> timedelta:
    if value.total_seconds() <= 0:
        raise ValueError("generation lease must be positive")
    return value


class ReportGenerationPersistence:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        *,
        evidence_id_factory: Callable[[], UUID] = uuid4,
    ) -> None:
        self._session_factory = session_factory
        self._evidence_id_factory = evidence_id_factory

    async def _has_evidence(
        self,
        session: AsyncSession,
        report_id: UUID,
    ) -> bool:
        return (
            await session.scalar(
                select(EvidenceItem.id)
                .where(EvidenceItem.report_id == report_id)
                .limit(1)
            )
            is not None
        )

    async def claim(
        self,
        *,
        report_id: UUID,
        session_id: UUID,
        lease_duration: timedelta,
        now: datetime,
    ) -> ReportGenerationClaim:
        lease = _require_positive_lease(lease_duration)
        claimed_at = _utc(now)
        try:
            async with self._session_factory() as session, session.begin():
                row = await session.scalar(
                    select(EvaluationReport)
                    .where(
                        EvaluationReport.id == report_id,
                        EvaluationReport.session_id == session_id,
                    )
                    .with_for_update()
                )
                if row is None:
                    raise ReportGenerationPersistenceError("report identity not found")
                status = ReportGenerationStatus(row.status)
                if status is ReportGenerationStatus.COMPLETED:
                    return ReportGenerationClaim(False, _snapshot(row), None)
                if await self._has_evidence(session, report_id):
                    raise ReportGenerationInvariantError(
                        "pre-completion report already has evidence"
                    )

                previous_token = row.started_at
                if status is ReportGenerationStatus.RUNNING:
                    if previous_token is None:
                        raise ReportGenerationInvariantError(
                            "running report is missing its claim token"
                        )
                    previous_token = _utc(previous_token)
                    if claimed_at < previous_token + lease:
                        return ReportGenerationClaim(False, _snapshot(row), None)
                if previous_token is not None and claimed_at <= _utc(previous_token):
                    raise ReportClaimTimeError(
                        "a replacement claim token must be strictly newer"
                    )

                updated = (
                    await session.execute(
                        update(EvaluationReport)
                        .where(
                            EvaluationReport.id == report_id,
                            EvaluationReport.session_id == session_id,
                            EvaluationReport.status == status.value,
                        )
                        .values(
                            status=ReportGenerationStatus.RUNNING.value,
                            started_at=claimed_at,
                            completed_at=None,
                            failed_at=None,
                            overall_summary=None,
                            priority_improvement=None,
                        )
                        .returning(EvaluationReport)
                    )
                ).scalar_one()
                if updated.started_at is None:
                    raise ReportGenerationInvariantError(
                        "database did not return a claim token"
                    )
                claimant_token = _utc(updated.started_at)
                return ReportGenerationClaim(
                    True,
                    _snapshot(updated),
                    claimant_token,
                )
        except (
            ReportClaimTimeError,
            ReportGenerationInvariantError,
            ReportGenerationPersistenceError,
        ):
            raise
        except (SQLAlchemyError, ValueError) as error:
            raise ReportGenerationPersistenceError from error

    async def complete(
        self,
        *,
        report_id: UUID,
        session_id: UUID,
        claimant_token: datetime,
        composition: ComposedReport,
        now: datetime,
    ) -> EvaluationReportSnapshot | None:
        token = _utc(claimant_token)
        completed_at = _utc(now)
        if composition.report_id != report_id or composition.session_id != session_id:
            raise ReportGenerationInvariantError(
                "composition does not match the claimed report identity"
            )
        try:
            async with self._session_factory() as session, session.begin():
                updated = (
                    await session.execute(
                        update(EvaluationReport)
                        .where(
                            EvaluationReport.id == report_id,
                            EvaluationReport.session_id == session_id,
                            EvaluationReport.status
                            == ReportGenerationStatus.RUNNING.value,
                            EvaluationReport.started_at == token,
                        )
                        .values(
                            status=ReportGenerationStatus.COMPLETED.value,
                            overall_summary=composition.overall_summary,
                            priority_improvement=composition.priority_improvement,
                            completed_at=completed_at,
                            failed_at=None,
                        )
                        .returning(EvaluationReport)
                    )
                ).scalar_one_or_none()
                if updated is None:
                    return None
                if await self._has_evidence(session, report_id):
                    raise ReportGenerationInvariantError(
                        "pre-completion report already has evidence"
                    )
                for draft in composition.evidence_items:
                    if draft.report_id != report_id or draft.session_id != session_id:
                        raise ReportGenerationInvariantError(
                            "evidence does not match the claimed report identity"
                        )
                    session.add(
                        EvidenceItem(
                            id=self._evidence_id_factory(),
                            session_id=draft.session_id,
                            report_id=draft.report_id,
                            kind=draft.kind.value,
                            source_participant_id=draft.source_participant_id,
                            source_utterance_id=draft.source_utterance_id,
                            source_event_sequence=draft.source_event_sequence,
                            phase=draft.phase.value,
                            quote=draft.quote,
                            interpretation=draft.interpretation,
                            confidence=draft.confidence,
                            created_at=completed_at,
                        )
                    )
                await session.flush()
                return _snapshot(updated)
        except ReportGenerationInvariantError:
            raise
        except (SQLAlchemyError, ValueError) as error:
            raise ReportGenerationPersistenceError from error

    async def fail(
        self,
        *,
        report_id: UUID,
        session_id: UUID,
        claimant_token: datetime,
        now: datetime,
    ) -> EvaluationReportSnapshot | None:
        token = _utc(claimant_token)
        failed_at = _utc(now)
        try:
            async with self._session_factory() as session, session.begin():
                updated = (
                    await session.execute(
                        update(EvaluationReport)
                        .where(
                            EvaluationReport.id == report_id,
                            EvaluationReport.session_id == session_id,
                            EvaluationReport.status
                            == ReportGenerationStatus.RUNNING.value,
                            EvaluationReport.started_at == token,
                        )
                        .values(
                            status=ReportGenerationStatus.FAILED.value,
                            overall_summary=None,
                            priority_improvement=None,
                            completed_at=None,
                            failed_at=failed_at,
                        )
                        .returning(EvaluationReport)
                    )
                ).scalar_one_or_none()
                if updated is None:
                    return None
                if await self._has_evidence(session, report_id):
                    raise ReportGenerationInvariantError(
                        "pre-completion report already has evidence"
                    )
                return _snapshot(updated)
        except ReportGenerationInvariantError:
            raise
        except (SQLAlchemyError, ValueError) as error:
            raise ReportGenerationPersistenceError from error

    async def load(
        self,
        *,
        report_id: UUID,
        session_id: UUID,
    ) -> EvaluationReportSnapshot:
        try:
            async with self._session_factory() as session:
                row = await session.scalar(
                    select(EvaluationReport).where(
                        EvaluationReport.id == report_id,
                        EvaluationReport.session_id == session_id,
                    )
                )
                if row is None:
                    raise ReportGenerationPersistenceError("report identity not found")
                return _snapshot(row)
        except ReportGenerationPersistenceError:
            raise
        except (SQLAlchemyError, ValueError) as error:
            raise ReportGenerationPersistenceError from error


class ReportGenerationCoordinator:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        *,
        collector: ReportSourceCollector | None = None,
        composer: ReportComposer | None = None,
        persistence: ReportGenerationPersistence | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._collector = collector or ReportSourceCollector()
        self._composer = composer or ReportComposer()
        self._persistence = persistence or ReportGenerationPersistence(session_factory)
        self._clock = clock or (lambda: datetime.now(UTC))

    def _now(self, explicit: datetime | None) -> datetime:
        return _utc(self._clock() if explicit is None else explicit)

    async def generate(
        self,
        *,
        owner_id: UUID,
        session_id: UUID,
        report_schema_version: int,
        derivation_version: str,
        evaluator: ReportEvaluator,
        lease_duration: timedelta,
        now: datetime | None = None,
    ) -> EvaluationReportSnapshot:
        lease = _require_positive_lease(lease_duration)
        operation_time = self._now(now)

        async with self._session_factory() as session:
            allocated = await get_or_create_eligible_report(
                session,
                owner_id=owner_id,
                session_id=session_id,
                report_schema_version=report_schema_version,
                derivation_version=derivation_version,
                now=operation_time,
            )

        claim = await self._persistence.claim(
            report_id=allocated.report_id,
            session_id=allocated.session_id,
            lease_duration=lease,
            now=operation_time,
        )
        if not claim.claimed:
            return claim.report
        claimant_token = claim.claimant_token
        if claimant_token is None:
            raise ReportGenerationInvariantError(
                "a successful claim must include its database token"
            )

        try:
            async with self._session_factory() as session:
                source = await self._collector.collect(
                    session,
                    report_id=claim.report.report_id,
                    session_id=claim.report.session_id,
                )

            proposal = await evaluator.evaluate(source)
            composition = self._composer.compose(source, proposal)
            completed = await self._persistence.complete(
                report_id=claim.report.report_id,
                session_id=claim.report.session_id,
                claimant_token=claimant_token,
                composition=composition,
                now=self._now(now),
            )
            if completed is not None:
                return completed
            return await self._persistence.load(
                report_id=claim.report.report_id,
                session_id=claim.report.session_id,
            )
        except Exception as error:
            try:
                failed = await self._persistence.fail(
                    report_id=claim.report.report_id,
                    session_id=claim.report.session_id,
                    claimant_token=claimant_token,
                    now=self._now(now),
                )
            except Exception as failure_error:
                raise ReportGenerationError(
                    "report generation and durable failure transition both failed"
                ) from failure_error
            if failed is None:
                return await self._persistence.load(
                    report_id=claim.report.report_id,
                    session_id=claim.report.session_id,
                )
            raise ReportGenerationError("report generation failed") from error
