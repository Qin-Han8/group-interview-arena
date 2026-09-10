from decimal import Decimal
from uuid import uuid4

import pytest
from pydantic import ValidationError

from group_interview_arena_api.modules.evaluation_reports.domain import (
    EvidenceItemDraft,
    EvidenceKind,
    EvidencePhase,
    ReportGenerationIdentity,
    ReportGenerationStatus,
)


def test_report_and_evidence_enums_are_closed() -> None:
    assert {item.value for item in ReportGenerationStatus} == {
        "REQUESTED",
        "RUNNING",
        "COMPLETED",
        "FAILED",
    }
    assert {item.value for item in EvidenceKind} == {
        "STRENGTH",
        "IMPROVEMENT",
    }
    assert {item.value for item in EvidencePhase} == {
        "OPENING_STATEMENTS",
        "EXPLORATION",
        "CONFLICT_AND_EVALUATION",
        "CONVERGENCE",
        "FINAL_SUMMARY",
    }

    with pytest.raises(ValueError):
        ReportGenerationStatus("PENDING")
    with pytest.raises(ValueError):
        EvidenceKind("SCORE")
    with pytest.raises(ValueError):
        EvidencePhase("PREPARATION")


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("report_schema_version", 0),
        ("derivation_version", "   "),
        ("source_through_sequence", -1),
    ],
)
def test_generation_identity_rejects_invalid_values(field: str, value: object) -> None:
    payload: dict[str, object] = {
        "session_id": uuid4(),
        "report_schema_version": 1,
        "derivation_version": "basic-evidence/v1",
        "source_through_sequence": 42,
    }
    payload[field] = value

    with pytest.raises(ValidationError):
        ReportGenerationIdentity.model_validate(payload)


@pytest.mark.parametrize(
    "confidence",
    [Decimal("-0.001"), Decimal("1.001"), Decimal("0.1234")],
)
def test_evidence_draft_rejects_invalid_confidence(confidence: Decimal) -> None:
    with pytest.raises(ValidationError):
        _evidence(confidence=confidence)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("source_event_sequence", 0),
        ("quote", ""),
        ("quote", "   "),
        ("interpretation", ""),
    ],
)
def test_evidence_draft_rejects_invalid_provenance_or_text(
    field: str, value: object
) -> None:
    with pytest.raises(ValidationError):
        _evidence(**{field: value})


@pytest.mark.parametrize(
    "raw_quote",
    [
        "  exact source text  ",
        "\tfirst authoritative line\nsecond authoritative line\t",
    ],
)
def test_evidence_draft_preserves_authoritative_quote_exactly(raw_quote: str) -> None:
    draft = _evidence(quote=raw_quote)

    assert draft.quote == raw_quote


def _evidence(**overrides: object) -> EvidenceItemDraft:
    payload: dict[str, object] = {
        "report_id": uuid4(),
        "session_id": uuid4(),
        "kind": EvidenceKind.STRENGTH,
        "source_participant_id": uuid4(),
        "source_utterance_id": uuid4(),
        "source_event_sequence": 1,
        "phase": EvidencePhase.OPENING_STATEMENTS,
        "quote": "I propose a shared criterion.",
        "interpretation": "Introduces a decision criterion.",
        "confidence": Decimal("0.875"),
    }
    payload.update(overrides)
    return EvidenceItemDraft.model_validate(payload)
