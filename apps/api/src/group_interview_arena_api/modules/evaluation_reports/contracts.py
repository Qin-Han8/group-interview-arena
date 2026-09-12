from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import UUID4, BaseModel, ConfigDict, Field

from group_interview_arena_api.modules.evaluation_reports.domain import (
    EvidenceKind,
    EvidencePhase,
    ReportGenerationStatus,
)
from group_interview_arena_api.modules.question_personas.contracts import (
    QuestionDetailResponse,
)


class _ClosedModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ReportMetadataResponse(_ClosedModel):
    report_id: UUID4
    session_id: UUID4
    status: ReportGenerationStatus
    report_schema_version: int = Field(gt=0)
    derivation_version: str
    source_through_sequence: int = Field(ge=0)
    created_at: datetime
    completed_at: datetime | None


class EvidenceCardResponse(_ClosedModel):
    kind: EvidenceKind
    source_participant_id: UUID4
    source_utterance_id: UUID4
    source_event_sequence: int = Field(gt=0)
    phase: EvidencePhase
    quote: str
    interpretation: str
    confidence: Decimal = Field(ge=0, le=1, decimal_places=3)


class SessionOverviewResponse(_ClosedModel):
    session_status: Literal["COMPLETED"]
    question: QuestionDetailResponse
    participant_count: int = Field(ge=1)
    human_utterance_count: int = Field(ge=0)
    ai_utterance_count: int = Field(ge=0)
    total_utterance_count: int = Field(ge=0)
    covered_phases: tuple[EvidencePhase, ...]
    summary: str


class CompletedReportContentResponse(_ClosedModel):
    overview: SessionOverviewResponse
    strengths: tuple[EvidenceCardResponse, ...] = Field(max_length=3)
    improvements: tuple[EvidenceCardResponse, ...] = Field(max_length=3)
    priority_improvement: str


class ReportViewResponse(_ClosedModel):
    report: ReportMetadataResponse
    content: CompletedReportContentResponse | None
