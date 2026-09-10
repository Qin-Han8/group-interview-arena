from __future__ import annotations

from decimal import Decimal
from enum import StrEnum
from typing import Protocol

from group_interview_arena_api.modules.evaluation_reports.domain import (
    ComposedReport,
    EvidenceItemDraft,
    EvidenceKind,
    EvidenceProposal,
    ReportEvaluationProposal,
    ReportSourceSnapshot,
)
from group_interview_arena_api.modules.floor_control.domain import (
    ParticipantActorKind,
)


class ReportEvaluator(Protocol):
    async def evaluate(
        self,
        source: ReportSourceSnapshot,
        /,
    ) -> ReportEvaluationProposal: ...


class EvidenceRejectionCode(StrEnum):
    ABOVE_WATERMARK = "ABOVE_WATERMARK"
    SOURCE_NOT_FOUND = "SOURCE_NOT_FOUND"
    UTTERANCE_MISMATCH = "UTTERANCE_MISMATCH"
    PARTICIPANT_NOT_IN_ROSTER = "PARTICIPANT_NOT_IN_ROSTER"
    PARTICIPANT_MISMATCH = "PARTICIPANT_MISMATCH"
    ACTOR_MISMATCH = "ACTOR_MISMATCH"
    NON_HUMAN_SOURCE = "NON_HUMAN_SOURCE"
    NON_HUMAN_ROSTER = "NON_HUMAN_ROSTER"
    PHASE_MISMATCH = "PHASE_MISMATCH"
    QUOTE_MISMATCH = "QUOTE_MISMATCH"


class EvidenceValidationError(ValueError):
    def __init__(self, code: EvidenceRejectionCode) -> None:
        super().__init__("Evidence proposal does not match authoritative source.")
        self.code = code


class EvidenceValidator:
    def validate(
        self,
        source: ReportSourceSnapshot,
        proposal: EvidenceProposal,
        expected_kind: EvidenceKind,
        /,
    ) -> EvidenceItemDraft:
        if proposal.source_event_sequence > source.source_through_sequence:
            raise EvidenceValidationError(EvidenceRejectionCode.ABOVE_WATERMARK)

        roster = {item.participant_id: item for item in source.participants}
        participant = roster.get(proposal.source_participant_id)
        if participant is None:
            raise EvidenceValidationError(
                EvidenceRejectionCode.PARTICIPANT_NOT_IN_ROSTER
            )

        utterance = next(
            (
                item
                for item in source.utterances
                if item.source_event_sequence == proposal.source_event_sequence
            ),
            None,
        )
        if utterance is None:
            raise EvidenceValidationError(EvidenceRejectionCode.SOURCE_NOT_FOUND)
        if utterance.utterance_id != proposal.source_utterance_id:
            raise EvidenceValidationError(EvidenceRejectionCode.UTTERANCE_MISMATCH)
        if utterance.participant_id != proposal.source_participant_id:
            raise EvidenceValidationError(EvidenceRejectionCode.PARTICIPANT_MISMATCH)
        if participant.actor_kind is not utterance.actor_kind:
            raise EvidenceValidationError(EvidenceRejectionCode.ACTOR_MISMATCH)
        if utterance.actor_kind is not ParticipantActorKind.HUMAN:
            raise EvidenceValidationError(EvidenceRejectionCode.NON_HUMAN_SOURCE)
        if participant.actor_kind is not ParticipantActorKind.HUMAN:
            raise EvidenceValidationError(EvidenceRejectionCode.NON_HUMAN_ROSTER)
        if utterance.phase is not proposal.phase:
            raise EvidenceValidationError(EvidenceRejectionCode.PHASE_MISMATCH)
        if proposal.quote not in utterance.content:
            raise EvidenceValidationError(EvidenceRejectionCode.QUOTE_MISMATCH)

        return EvidenceItemDraft(
            report_id=source.report_id,
            session_id=source.session_id,
            kind=expected_kind,
            source_participant_id=proposal.source_participant_id,
            source_utterance_id=proposal.source_utterance_id,
            source_event_sequence=proposal.source_event_sequence,
            phase=proposal.phase,
            quote=proposal.quote,
            interpretation=proposal.interpretation,
            confidence=proposal.confidence,
        )


class ReportComposer:
    def __init__(self, validator: EvidenceValidator | None = None) -> None:
        self._validator = validator or EvidenceValidator()

    def compose(
        self,
        source: ReportSourceSnapshot,
        proposal: ReportEvaluationProposal,
        /,
    ) -> ComposedReport:
        evidence_items: list[EvidenceItemDraft] = []
        for item in proposal.strengths:
            evidence_items.append(
                self._validator.validate(source, item, EvidenceKind.STRENGTH)
            )
        for item in proposal.improvements:
            evidence_items.append(
                self._validator.validate(source, item, EvidenceKind.IMPROVEMENT)
            )
        return ComposedReport(
            report_id=source.report_id,
            session_id=source.session_id,
            overall_summary=proposal.overall_summary,
            priority_improvement=proposal.priority_improvement,
            evidence_items=tuple(evidence_items),
        )


class DeterministicReportEvaluator:
    def __init__(self) -> None:
        self.evaluation_count = 0

    async def evaluate(
        self,
        source: ReportSourceSnapshot,
        /,
    ) -> ReportEvaluationProposal:
        self.evaluation_count += 1
        human_source = next(
            (
                item
                for item in source.utterances
                if item.actor_kind is ParticipantActorKind.HUMAN
                and item.content.strip()
            ),
            None,
        )
        strengths: tuple[EvidenceProposal, ...] = ()
        if human_source is not None:
            strengths = (
                EvidenceProposal(
                    source_participant_id=human_source.participant_id,
                    source_utterance_id=human_source.utterance_id,
                    source_event_sequence=human_source.source_event_sequence,
                    phase=human_source.phase,
                    quote=human_source.content,
                    interpretation="States a concrete contribution for group evaluation.",
                    confidence=Decimal("1.000"),
                ),
            )
        return ReportEvaluationProposal(
            evaluation_contract_version=1,
            overall_summary="The report is derived from authoritative public discussion history.",
            strengths=strengths,
            improvements=(),
            priority_improvement=(
                "Make the next contribution explicitly connect evidence, trade-offs, "
                "and the group decision."
            ),
        )
