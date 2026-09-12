from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from group_interview_arena_api.db.models import (
    EvaluationReport,
    EvidenceItem,
    SimulationSession,
)
from group_interview_arena_api.modules.evaluation_reports.domain import (
    EvidenceKind,
    EvidencePhase,
    ReportGenerationStatus,
    ReportQuestionSnapshot,
)
from group_interview_arena_api.modules.evaluation_reports.source import (
    ReportSourceCollectionError,
    ReportSourceCollector,
)
from group_interview_arena_api.modules.floor_control.domain import (
    ParticipantActorKind,
)


class ReportViewNotFoundError(Exception):
    pass


class ReportViewPersistenceError(Exception):
    pass


@dataclass(frozen=True)
class ReportMetadataView:
    report_id: UUID
    session_id: UUID
    status: ReportGenerationStatus
    report_schema_version: int
    derivation_version: str
    source_through_sequence: int
    created_at: datetime
    completed_at: datetime | None


@dataclass(frozen=True)
class EvidenceCardView:
    kind: EvidenceKind
    source_participant_id: UUID
    source_utterance_id: UUID
    source_event_sequence: int
    phase: EvidencePhase
    quote: str
    interpretation: str
    confidence: Decimal


@dataclass(frozen=True)
class SessionOverviewView:
    question: ReportQuestionSnapshot
    participant_count: int
    human_utterance_count: int
    ai_utterance_count: int
    covered_phases: tuple[EvidencePhase, ...]
    summary: str

    @property
    def total_utterance_count(self) -> int:
        return self.human_utterance_count + self.ai_utterance_count


@dataclass(frozen=True)
class CompletedReportContentView:
    overview: SessionOverviewView
    strengths: tuple[EvidenceCardView, ...]
    improvements: tuple[EvidenceCardView, ...]
    priority_improvement: str


@dataclass(frozen=True)
class ReportView:
    report: ReportMetadataView
    content: CompletedReportContentView | None


def _metadata(report: EvaluationReport) -> ReportMetadataView:
    return ReportMetadataView(
        report_id=report.id,
        session_id=report.session_id,
        status=ReportGenerationStatus(report.status),
        report_schema_version=report.report_schema_version,
        derivation_version=report.derivation_version,
        source_through_sequence=report.source_through_sequence,
        created_at=report.created_at,
        completed_at=report.completed_at,
    )


def _evidence_card(item: EvidenceItem) -> EvidenceCardView:
    return EvidenceCardView(
        kind=EvidenceKind(item.kind),
        source_participant_id=item.source_participant_id,
        source_utterance_id=item.source_utterance_id,
        source_event_sequence=item.source_event_sequence,
        phase=EvidencePhase(item.phase),
        quote=item.quote,
        interpretation=item.interpretation,
        confidence=item.confidence,
    )


async def load_current_report_view(
    session: AsyncSession,
    *,
    owner_id: UUID,
    session_id: UUID,
) -> ReportView:
    """Load the newest durable report without generating or mutating anything."""

    try:
        report = await session.scalar(
            select(EvaluationReport)
            .join(
                SimulationSession,
                SimulationSession.id == EvaluationReport.session_id,
            )
            .where(
                EvaluationReport.session_id == session_id,
                SimulationSession.id == session_id,
                SimulationSession.owner_user_id == owner_id,
            )
            .order_by(
                EvaluationReport.created_at.desc(),
                EvaluationReport.id.desc(),
            )
            .limit(1)
        )
        if report is None:
            raise ReportViewNotFoundError

        metadata = _metadata(report)
        if metadata.status is not ReportGenerationStatus.COMPLETED:
            return ReportView(report=metadata, content=None)
        if (
            report.completed_at is None
            or report.overall_summary is None
            or report.priority_improvement is None
        ):
            raise ReportViewPersistenceError

        source = await ReportSourceCollector().collect(
            session,
            report_id=report.id,
            session_id=session_id,
        )
        evidence_rows = tuple(
            (
                await session.scalars(
                    select(EvidenceItem)
                    .where(
                        EvidenceItem.session_id == session_id,
                        EvidenceItem.report_id == report.id,
                    )
                    .order_by(
                        EvidenceItem.source_event_sequence.asc(),
                        EvidenceItem.id.asc(),
                    )
                )
            ).all()
        )
        strengths = tuple(
            _evidence_card(item)
            for item in evidence_rows
            if item.kind == EvidenceKind.STRENGTH.value
        )
        improvements = tuple(
            _evidence_card(item)
            for item in evidence_rows
            if item.kind == EvidenceKind.IMPROVEMENT.value
        )
        if len(strengths) > 3 or len(improvements) > 3:
            raise ReportViewPersistenceError

        human_count = sum(
            utterance.actor_kind is ParticipantActorKind.HUMAN
            for utterance in source.utterances
        )
        ai_count = sum(
            utterance.actor_kind is ParticipantActorKind.AI
            for utterance in source.utterances
        )
        present_phases = {item.phase for item in source.utterances}
        covered_phases = tuple(
            phase for phase in EvidencePhase if phase in present_phases
        )
        overview = SessionOverviewView(
            question=source.question,
            participant_count=len(source.participants),
            human_utterance_count=human_count,
            ai_utterance_count=ai_count,
            covered_phases=covered_phases,
            summary=report.overall_summary,
        )
        return ReportView(
            report=metadata,
            content=CompletedReportContentView(
                overview=overview,
                strengths=strengths,
                improvements=improvements,
                priority_improvement=report.priority_improvement,
            ),
        )
    except ReportViewNotFoundError:
        raise
    except ReportViewPersistenceError:
        raise
    except (
        ReportSourceCollectionError,
        SQLAlchemyError,
        TypeError,
        ValueError,
    ) as error:
        raise ReportViewPersistenceError from error
