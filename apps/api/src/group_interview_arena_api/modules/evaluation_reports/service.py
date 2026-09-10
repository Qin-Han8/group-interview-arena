from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from group_interview_arena_api.db.models import EvaluationReport, SimulationSession
from group_interview_arena_api.modules.discussion_sessions.domain import SessionStatus
from group_interview_arena_api.modules.evaluation_reports.domain import (
    EvaluationReportSnapshot,
    ReportGenerationIdentity,
    ReportGenerationStatus,
)

GENERATION_IDENTITY_CONSTRAINT = "uq_evaluation_reports_generation_identity"


class ReportSessionNotFoundError(ValueError):
    pass


class ReportSessionIneligibleError(ValueError):
    pass


class EvaluationReportPersistenceError(RuntimeError):
    pass


async def _load_eligible_session(
    session: AsyncSession,
    *,
    owner_id: UUID,
    session_id: UUID,
) -> SimulationSession:
    row = await session.scalar(
        select(SimulationSession)
        .where(
            SimulationSession.id == session_id,
            SimulationSession.owner_user_id == owner_id,
        )
        .with_for_update(read=True)
    )
    if row is None:
        raise ReportSessionNotFoundError
    if row.status != SessionStatus.COMPLETED.value:
        raise ReportSessionIneligibleError
    return row


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


async def get_or_create_eligible_report(
    session: AsyncSession,
    *,
    owner_id: UUID,
    session_id: UUID,
    report_schema_version: int,
    derivation_version: str,
    now: datetime | None = None,
) -> EvaluationReportSnapshot:
    created_at = datetime.now(UTC) if now is None else now
    try:
        async with session.begin():
            aggregate = await _load_eligible_session(
                session,
                owner_id=owner_id,
                session_id=session_id,
            )
            identity = ReportGenerationIdentity(
                session_id=aggregate.id,
                report_schema_version=report_schema_version,
                derivation_version=derivation_version,
                source_through_sequence=aggregate.last_sequence,
            )
            proposed_id = uuid4()
            inserted_id = (
                await session.execute(
                    insert(EvaluationReport)
                    .values(
                        id=proposed_id,
                        session_id=identity.session_id,
                        report_schema_version=identity.report_schema_version,
                        derivation_version=identity.derivation_version,
                        source_through_sequence=identity.source_through_sequence,
                        status=ReportGenerationStatus.REQUESTED.value,
                        overall_summary=None,
                        priority_improvement=None,
                        created_at=created_at,
                        started_at=None,
                        completed_at=None,
                        failed_at=None,
                    )
                    .on_conflict_do_nothing(constraint=GENERATION_IDENTITY_CONSTRAINT)
                    .returning(EvaluationReport.id)
                )
            ).scalar_one_or_none()
            if inserted_id is not None:
                row = await session.scalar(
                    select(EvaluationReport).where(EvaluationReport.id == inserted_id)
                )
            else:
                row = await session.scalar(
                    select(EvaluationReport).where(
                        EvaluationReport.session_id == identity.session_id,
                        EvaluationReport.report_schema_version
                        == identity.report_schema_version,
                        EvaluationReport.derivation_version
                        == identity.derivation_version,
                        EvaluationReport.source_through_sequence
                        == identity.source_through_sequence,
                    )
                )
            if row is None:
                raise EvaluationReportPersistenceError
    except ReportSessionNotFoundError, ReportSessionIneligibleError:
        raise
    except (SQLAlchemyError, ValueError) as error:
        raise EvaluationReportPersistenceError from error
    return _snapshot(row)
