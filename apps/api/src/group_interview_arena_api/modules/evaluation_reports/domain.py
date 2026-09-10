from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Annotated, Literal, Self
from uuid import UUID

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

from group_interview_arena_api.modules.floor_control.domain import (
    ParticipantActorKind,
)

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
PreservedNonBlankText = Annotated[str, AfterValidator(_preserve_non_blank_quote)]


class EvaluationReportDomainModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class EvaluationPipelineModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


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


class ReportQuestionConstraint(EvaluationPipelineModel):
    key: PreservedNonBlankText
    text: PreservedNonBlankText


class ReportQuestionStakeholder(EvaluationPipelineModel):
    key: PreservedNonBlankText
    name: PreservedNonBlankText
    description: PreservedNonBlankText


class ReportQuestionOption(EvaluationPipelineModel):
    key: PreservedNonBlankText
    label: PreservedNonBlankText
    description: PreservedNonBlankText


class ReportQuestionSnapshot(EvaluationPipelineModel):
    id: UUID
    question_template_id: UUID
    version_number: int = Field(gt=0)
    title: PreservedNonBlankText
    question_type: PreservedNonBlankText
    background_domain: PreservedNonBlankText
    difficulty: PreservedNonBlankText
    estimated_minutes: int = Field(ge=5, le=180)
    scenario: PreservedNonBlankText
    objective: PreservedNonBlankText
    hard_constraints: tuple[ReportQuestionConstraint, ...]
    soft_constraints: tuple[ReportQuestionConstraint, ...]
    stakeholders: tuple[ReportQuestionStakeholder, ...]
    options: tuple[ReportQuestionOption, ...]


class ReportParticipantSource(EvaluationPipelineModel):
    participant_id: UUID
    actor_kind: ParticipantActorKind
    seat_order: int = Field(gt=0)


class ReportUtteranceSource(EvaluationPipelineModel):
    utterance_id: UUID
    source_event_sequence: int = Field(gt=0)
    occurred_at: datetime
    participant_id: UUID
    actor_kind: Literal[
        ParticipantActorKind.HUMAN,
        ParticipantActorKind.AI,
    ]
    floor_grant_id: UUID
    phase: EvidencePhase
    content: str

    @field_validator("occurred_at")
    @classmethod
    def require_aware_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("utterance timestamp must be timezone-aware")
        return value


class ReportSourceSnapshot(EvaluationPipelineModel):
    source_contract_version: Literal[1]
    report_id: UUID
    session_id: UUID
    report_schema_version: int = Field(gt=0)
    derivation_version: PreservedNonBlankText
    source_through_sequence: int = Field(ge=0)
    question: ReportQuestionSnapshot
    participants: tuple[ReportParticipantSource, ...]
    utterances: tuple[ReportUtteranceSource, ...]

    @model_validator(mode="after")
    def validate_trusted_source_shape(self) -> Self:
        participant_ids = [item.participant_id for item in self.participants]
        seat_orders = [item.seat_order for item in self.participants]
        if len(participant_ids) != len(set(participant_ids)):
            raise ValueError("participant identities must be unique")
        if len(seat_orders) != len(set(seat_orders)):
            raise ValueError("participant seat order must be unique")
        if list(self.participants) != sorted(
            self.participants,
            key=lambda item: (item.seat_order, item.participant_id),
        ):
            raise ValueError("participants must be ordered by seat and identity")
        if (
            sum(
                item.actor_kind is ParticipantActorKind.HUMAN
                for item in self.participants
            )
            != 1
        ):
            raise ValueError("report source requires exactly one Human participant")

        roster = {item.participant_id: item.actor_kind for item in self.participants}
        sequences = [item.source_event_sequence for item in self.utterances]
        if sequences != sorted(sequences) or len(sequences) != len(set(sequences)):
            raise ValueError("utterances must have unique event-sequence order")
        for utterance in self.utterances:
            if utterance.source_event_sequence > self.source_through_sequence:
                raise ValueError("utterance exceeds the frozen source watermark")
            if roster.get(utterance.participant_id) is not utterance.actor_kind:
                raise ValueError("utterance actor does not match the trusted roster")
        return self


class EvidenceProposal(EvaluationPipelineModel):
    source_participant_id: UUID
    source_utterance_id: UUID
    source_event_sequence: int = Field(gt=0)
    phase: EvidencePhase
    quote: ExactEvidenceQuote
    interpretation: NonEmptyEvidenceText
    confidence: Decimal = Field(ge=0, le=1, decimal_places=3)


class ReportEvaluationProposal(EvaluationPipelineModel):
    evaluation_contract_version: Literal[1]
    overall_summary: NonEmptyEvidenceText
    strengths: tuple[EvidenceProposal, ...] = Field(max_length=3)
    improvements: tuple[EvidenceProposal, ...] = Field(max_length=3)
    priority_improvement: NonEmptyEvidenceText


class ComposedReport(EvaluationPipelineModel):
    report_id: UUID
    session_id: UUID
    overall_summary: NonEmptyEvidenceText
    priority_improvement: NonEmptyEvidenceText
    evidence_items: tuple[EvidenceItemDraft, ...]


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
