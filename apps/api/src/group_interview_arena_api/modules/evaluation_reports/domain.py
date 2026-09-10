from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Annotated
from uuid import UUID

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, StringConstraints

NonEmptyVersion = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=128),
]
NonEmptyEvidenceText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1),
]


def _preserve_non_blank_quote(value: str) -> str:
    if not value.strip():
        raise ValueError("quote must contain non-whitespace content")
    return value


ExactEvidenceQuote = Annotated[str, AfterValidator(_preserve_non_blank_quote)]


class EvaluationReportDomainModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ReportGenerationStatus(StrEnum):
    REQUESTED = "REQUESTED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class EvidenceKind(StrEnum):
    STRENGTH = "STRENGTH"
    IMPROVEMENT = "IMPROVEMENT"


class EvidencePhase(StrEnum):
    OPENING_STATEMENTS = "OPENING_STATEMENTS"
    EXPLORATION = "EXPLORATION"
    CONFLICT_AND_EVALUATION = "CONFLICT_AND_EVALUATION"
    CONVERGENCE = "CONVERGENCE"
    FINAL_SUMMARY = "FINAL_SUMMARY"


class ReportGenerationIdentity(EvaluationReportDomainModel):
    session_id: UUID
    report_schema_version: int = Field(gt=0)
    derivation_version: NonEmptyVersion
    source_through_sequence: int = Field(ge=0)


class EvaluationReportSnapshot(ReportGenerationIdentity):
    report_id: UUID
    status: ReportGenerationStatus
    overall_summary: str | None = None
    priority_improvement: str | None = None
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    failed_at: datetime | None = None


class EvidenceItemDraft(EvaluationReportDomainModel):
    report_id: UUID
    session_id: UUID
    kind: EvidenceKind
    source_participant_id: UUID
    source_utterance_id: UUID
    source_event_sequence: int = Field(gt=0)
    phase: EvidencePhase
    quote: ExactEvidenceQuote
    interpretation: NonEmptyEvidenceText
    confidence: Decimal = Field(ge=0, le=1, decimal_places=3)
