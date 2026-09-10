import asyncio
from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from pydantic import ValidationError

from group_interview_arena_api.modules.evaluation_reports.domain import (
    EvidenceKind,
    EvidencePhase,
    EvidenceProposal,
    ReportEvaluationProposal,
    ReportParticipantSource,
    ReportQuestionConstraint,
    ReportQuestionOption,
    ReportQuestionSnapshot,
    ReportQuestionStakeholder,
    ReportSourceSnapshot,
    ReportUtteranceSource,
)
from group_interview_arena_api.modules.evaluation_reports.evaluation import (
    DeterministicReportEvaluator,
    EvidenceRejectionCode,
    EvidenceValidationError,
    EvidenceValidator,
    ReportComposer,
)
from group_interview_arena_api.modules.floor_control.domain import (
    ParticipantActorKind,
)

NOW = datetime(2026, 9, 10, 12, 0, tzinfo=UTC)


def _question() -> ReportQuestionSnapshot:
    return ReportQuestionSnapshot(
        id=uuid4(),
        question_template_id=uuid4(),
        version_number=1,
        title="Resource allocation exercise",
        question_type="RESOURCE_ALLOCATION",
        background_domain="GENERAL",
        difficulty="STANDARD",
        estimated_minutes=30,
        scenario="Allocate limited resources.",
        objective="Reach a justified group decision.",
        hard_constraints=(
            ReportQuestionConstraint(key="BUDGET", text="Stay within budget."),
        ),
        soft_constraints=(),
        stakeholders=(
            ReportQuestionStakeholder(
                key="COMMUNITY",
                name="Community",
                description="People affected by the decision.",
            ),
        ),
        options=(
            ReportQuestionOption(
                key="OPTION_A",
                label="Option A",
                description="First allocation option.",
            ),
            ReportQuestionOption(
                key="OPTION_B",
                label="Option B",
                description="Second allocation option.",
            ),
        ),
    )


def _source() -> ReportSourceSnapshot:
    report_id = uuid4()
    session_id = uuid4()
    human_id = uuid4()
    ai_id = uuid4()
    return ReportSourceSnapshot(
        source_contract_version=1,
        report_id=report_id,
        session_id=session_id,
        report_schema_version=1,
        derivation_version="basic-report/v1",
        source_through_sequence=12,
        question=_question(),
        participants=(
            ReportParticipantSource(
                participant_id=human_id,
                actor_kind=ParticipantActorKind.HUMAN,
                seat_order=1,
            ),
            ReportParticipantSource(
                participant_id=ai_id,
                actor_kind=ParticipantActorKind.AI,
                seat_order=2,
            ),
        ),
        utterances=(
            ReportUtteranceSource(
                utterance_id=uuid4(),
                source_event_sequence=4,
                occurred_at=NOW,
                participant_id=human_id,
                actor_kind=ParticipantActorKind.HUMAN,
                floor_grant_id=uuid4(),
                phase=EvidencePhase.OPENING_STATEMENTS,
                content="  exact human contribution\n",
            ),
            ReportUtteranceSource(
                utterance_id=uuid4(),
                source_event_sequence=7,
                occurred_at=NOW,
                participant_id=ai_id,
                actor_kind=ParticipantActorKind.AI,
                floor_grant_id=uuid4(),
                phase=EvidencePhase.EXPLORATION,
                content="AI contribution",
            ),
        ),
    )


def _evidence_payload(source: ReportSourceSnapshot) -> dict[str, object]:
    utterance = source.utterances[0]
    return {
        "source_participant_id": utterance.participant_id,
        "source_utterance_id": utterance.utterance_id,
        "source_event_sequence": utterance.source_event_sequence,
        "phase": utterance.phase,
        "quote": "  exact human contribution\n",
        "interpretation": "States a concrete proposal.",
        "confidence": Decimal("0.875"),
    }


def test_source_snapshot_is_closed_immutable_and_public_only() -> None:
    source = _source()
    payload = source.model_dump(mode="json")

    assert set(payload) == {
        "source_contract_version",
        "report_id",
        "session_id",
        "report_schema_version",
        "derivation_version",
        "source_through_sequence",
        "question",
        "participants",
        "utterances",
    }
    assert set(payload["question"]) == {
        "id",
        "question_template_id",
        "version_number",
        "title",
        "question_type",
        "background_domain",
        "difficulty",
        "estimated_minutes",
        "scenario",
        "objective",
        "hard_constraints",
        "soft_constraints",
        "stakeholders",
        "options",
    }
    serialized = source.model_dump_json()
    for forbidden in (
        "reference_dimensions",
        "hidden_conflicts",
        "acceptable_outcome_patterns",
        "private_stance",
        "calibration",
        "memory",
        "prompt",
        "credential",
    ):
        assert forbidden not in serialized.lower()

    with pytest.raises(ValidationError):
        ReportSourceSnapshot.model_validate({**source.model_dump(), "memory": {}})

    with pytest.raises(ValidationError):
        source.source_through_sequence = 13  # pyright: ignore[reportAttributeAccessIssue]


@pytest.mark.parametrize(
    "field",
    [
        "score",
        "total_score",
        "dimension",
        "dimension_score",
        "percentile",
        "ranking",
        "hire_probability",
        "personality_type",
        "metric",
        "score_effect",
    ],
)
def test_evaluation_proposal_rejects_unsupported_surface(field: str) -> None:
    with pytest.raises(ValidationError):
        ReportEvaluationProposal.model_validate(
            {
                "evaluation_contract_version": 1,
                "overall_summary": "The participant contributed constructively.",
                "strengths": (),
                "improvements": (),
                "priority_improvement": "State trade-offs more explicitly.",
                field: 1,
            }
        )


@pytest.mark.parametrize("field", ["strengths", "improvements"])
def test_evaluation_proposal_rejects_more_than_three_items(field: str) -> None:
    source = _source()
    item = _evidence_payload(source)
    payload: dict[str, object] = {
        "evaluation_contract_version": 1,
        "overall_summary": "Summary",
        "strengths": (),
        "improvements": (),
        "priority_improvement": "Priority",
    }
    payload[field] = (item, item, item, item)

    with pytest.raises(ValidationError):
        ReportEvaluationProposal.model_validate(payload)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("evaluation_contract_version", 2),
        ("overall_summary", "   "),
        ("priority_improvement", ""),
    ],
)
def test_evaluation_proposal_rejects_invalid_required_values(
    field: str, value: object
) -> None:
    payload: dict[str, object] = {
        "evaluation_contract_version": 1,
        "overall_summary": "Summary",
        "strengths": (),
        "improvements": (),
        "priority_improvement": "Priority",
    }
    payload[field] = value

    with pytest.raises(ValidationError):
        ReportEvaluationProposal.model_validate(payload)


@pytest.mark.parametrize(
    "raw_quote",
    ["  exact source text  ", "\tfirst line\nsecond line\t"],
)
def test_evidence_proposal_preserves_exact_quote(raw_quote: str) -> None:
    source = _source()
    proposal = _evidence_payload(source)
    proposal["quote"] = raw_quote

    result = ReportEvaluationProposal.model_validate(
        {
            "evaluation_contract_version": 1,
            "overall_summary": "Summary",
            "strengths": (proposal,),
            "improvements": (),
            "priority_improvement": "Priority",
        }
    )

    assert result.strengths[0].quote == raw_quote


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("quote", ""),
        ("quote", "   \t\n"),
        ("confidence", Decimal("-0.001")),
        ("confidence", Decimal("1.001")),
    ],
)
def test_evidence_proposal_rejects_invalid_values(field: str, value: object) -> None:
    source = _source()
    proposal = _evidence_payload(source)
    proposal[field] = value

    with pytest.raises(ValidationError):
        ReportEvaluationProposal.model_validate(
            {
                "evaluation_contract_version": 1,
                "overall_summary": "Summary",
                "strengths": (proposal,),
                "improvements": (),
                "priority_improvement": "Priority",
            }
        )


def test_deterministic_evaluator_is_network_free_and_preserves_source_quote() -> None:
    source = _source()
    evaluator = DeterministicReportEvaluator()

    proposal = asyncio.run(evaluator.evaluate(source))

    assert evaluator.evaluation_count == 1
    assert proposal.evaluation_contract_version == 1
    assert len(proposal.strengths) == 1
    assert proposal.improvements == ()
    assert proposal.strengths[0].quote == source.utterances[0].content


def _evidence(source: ReportSourceSnapshot, **overrides: object) -> EvidenceProposal:
    payload = _evidence_payload(source)
    payload.update(overrides)
    return EvidenceProposal.model_validate(payload)


def _proposal(
    *,
    strengths: tuple[EvidenceProposal, ...] = (),
    improvements: tuple[EvidenceProposal, ...] = (),
) -> ReportEvaluationProposal:
    return ReportEvaluationProposal(
        evaluation_contract_version=1,
        overall_summary="The participant contributed a clear decision criterion.",
        strengths=strengths,
        improvements=improvements,
        priority_improvement="Explain the trade-off before recommending an option.",
    )


@pytest.mark.parametrize(
    ("overrides", "code"),
    [
        ({"source_event_sequence": 13}, EvidenceRejectionCode.ABOVE_WATERMARK),
        ({"source_event_sequence": 6}, EvidenceRejectionCode.SOURCE_NOT_FOUND),
        ({"source_utterance_id": uuid4()}, EvidenceRejectionCode.UTTERANCE_MISMATCH),
        (
            {"source_participant_id": uuid4()},
            EvidenceRejectionCode.PARTICIPANT_NOT_IN_ROSTER,
        ),
        ({"phase": EvidencePhase.EXPLORATION}, EvidenceRejectionCode.PHASE_MISMATCH),
        (
            {"quote": "   exact human contribution\n"},
            EvidenceRejectionCode.QUOTE_MISMATCH,
        ),
        ({"quote": "exact human contribution "}, EvidenceRejectionCode.QUOTE_MISMATCH),
        ({"quote": "exact  human contribution"}, EvidenceRejectionCode.QUOTE_MISMATCH),
        ({"quote": "cafe\u0301"}, EvidenceRejectionCode.QUOTE_MISMATCH),
    ],
)
def test_evidence_validator_rejects_untrusted_provenance_without_repair(
    overrides: dict[str, object],
    code: EvidenceRejectionCode,
) -> None:
    source = _source()
    if overrides.get("quote") == "cafe\u0301":
        utterance = source.utterances[0].model_copy(update={"content": "café"})
        source = source.model_copy(update={"utterances": (utterance,)})

    with pytest.raises(EvidenceValidationError) as captured:
        EvidenceValidator().validate(
            source,
            _evidence(source, **overrides),
            EvidenceKind.STRENGTH,
        )

    assert captured.value.code is code


def test_evidence_validator_rejects_ai_evidence() -> None:
    source = _source()
    ai = source.utterances[1]

    with pytest.raises(EvidenceValidationError) as captured:
        EvidenceValidator().validate(
            source,
            EvidenceProposal(
                source_participant_id=ai.participant_id,
                source_utterance_id=ai.utterance_id,
                source_event_sequence=ai.source_event_sequence,
                phase=ai.phase,
                quote=ai.content,
                interpretation="AI output is not candidate evidence.",
                confidence=Decimal("1.000"),
            ),
            EvidenceKind.IMPROVEMENT,
        )

    assert captured.value.code is EvidenceRejectionCode.NON_HUMAN_SOURCE


def test_evidence_validator_rejects_actor_mismatch() -> None:
    source = _source()
    human = source.utterances[0]
    mismatched = human.model_copy(update={"actor_kind": ParticipantActorKind.AI})
    malformed_source = source.model_copy(update={"utterances": (mismatched,)})

    with pytest.raises(EvidenceValidationError) as captured:
        EvidenceValidator().validate(
            malformed_source,
            _evidence(source),
            EvidenceKind.STRENGTH,
        )

    assert captured.value.code is EvidenceRejectionCode.ACTOR_MISMATCH


def test_evidence_validator_uses_trusted_binding_and_exact_quote() -> None:
    source = _source()
    proposal = _evidence(source, quote="exact human contribution")

    draft = EvidenceValidator().validate(
        source,
        proposal,
        EvidenceKind.IMPROVEMENT,
    )

    assert draft.report_id == source.report_id
    assert draft.session_id == source.session_id
    assert draft.kind is EvidenceKind.IMPROVEMENT
    assert draft.quote == proposal.quote


def test_blank_quote_is_rejected_before_evidence_validation() -> None:
    source = _source()

    with pytest.raises(ValidationError):
        _evidence(source, quote=" \t\n")


def test_report_composer_accepts_empty_evidence_collections() -> None:
    source = _source()

    result = ReportComposer().compose(source, _proposal())

    assert result.report_id == source.report_id
    assert result.session_id == source.session_id
    assert result.evidence_items == ()


@pytest.mark.parametrize(
    ("strength_count", "improvement_count"), [(1, 0), (3, 0), (0, 1), (0, 3), (2, 2)]
)
def test_report_composer_assigns_trusted_kinds(
    strength_count: int,
    improvement_count: int,
) -> None:
    source = _source()
    item = _evidence(source, quote="exact human contribution")

    result = ReportComposer().compose(
        source,
        _proposal(
            strengths=(item,) * strength_count,
            improvements=(item,) * improvement_count,
        ),
    )

    assert [draft.kind for draft in result.evidence_items] == [
        *([EvidenceKind.STRENGTH] * strength_count),
        *([EvidenceKind.IMPROVEMENT] * improvement_count),
    ]


def test_report_composer_fails_whole_result_for_any_invalid_evidence() -> None:
    source = _source()
    valid = _evidence(source, quote="exact human contribution")
    invalid = _evidence(source, quote="normalized source text")

    with pytest.raises(EvidenceValidationError):
        ReportComposer().compose(
            source,
            _proposal(strengths=(valid,), improvements=(invalid,)),
        )


def test_composed_report_has_no_scoring_surface() -> None:
    result = ReportComposer().compose(_source(), _proposal())

    assert set(result.model_dump()) == {
        "report_id",
        "session_id",
        "overall_summary",
        "priority_improvement",
        "evidence_items",
    }
    for forbidden in ("score", "dimension", "ranking", "metric"):
        assert forbidden not in result.model_dump_json().lower()
