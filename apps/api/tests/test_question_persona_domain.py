from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, cast
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from group_interview_arena_api.modules.question_personas.domain import (
    PersonaAssignmentDefinition,
    PersonaTemplateDefinition,
    PriorityDimension,
    PrivateStanceDefinition,
    PublishedQuestionBundle,
    QuestionVersionContent,
)


def _persona(**overrides: object) -> PersonaTemplateDefinition:
    values: dict[str, object] = {
        "id": uuid4(),
        "code": "LOGIC_ANALYST",
        "display_name": "逻辑分析者",
        "speech_style_code": "STRUCTURED",
        "initiative": Decimal("0.600"),
        "interrupt_tendency": Decimal("0.200"),
        "average_turn_seconds": 40,
        "stance_stability": Decimal("0.750"),
        "persuasion_threshold": Decimal("0.700"),
        "novel_idea_rate": Decimal("0.350"),
        "summary_tendency": Decimal("0.600"),
        "time_awareness": Decimal("0.650"),
        "detail_focus": Decimal("0.800"),
        "cooperation": Decimal("0.600"),
        "support_user_bias": Decimal("0.000"),
        "error_rate": Decimal("0.100"),
        "off_topic_rate": Decimal("0.050"),
        "created_at": datetime(2026, 8, 17, tzinfo=UTC),
    }
    values.update(overrides)
    return PersonaTemplateDefinition.model_validate(values)


def _content(**overrides: object) -> QuestionVersionContent:
    values: dict[str, object] = {
        "title": "内部验证：资源安排",
        "question_type_code": "RESOURCE_ALLOCATION",
        "background_domain_code": "GENERAL",
        "difficulty_code": "STANDARD",
        "scenario": "团队需要在有限资源下完成三项工作。",
        "objective": "形成可解释且满足硬约束的资源方案。",
        "estimated_minutes": 25,
        "hard_constraints": [{"key": "BUDGET", "text": "总资源不得超过 100。"}],
        "soft_constraints": [{"key": "BALANCE", "text": "兼顾短期与长期价值。"}],
        "stakeholders": [
            {"key": "TEAM", "name": "项目团队", "description": "负责执行方案。"}
        ],
        "options": [
            {"key": "A", "label": "方案 A", "description": "优先保障核心交付。"},
            {"key": "B", "label": "方案 B", "description": "优先投资长期能力。"},
        ],
        "reference_dimensions": [
            {"key": "FEASIBILITY", "name": "可行性", "description": "能否落地。"}
        ],
        "hidden_conflicts": [{"key": "TIME_VALUE", "text": "短期与长期价值冲突。"}],
        "acceptable_outcome_patterns": [
            {"key": "TRACEABLE", "text": "方案明确引用约束和取舍。"}
        ],
        "phase_prompts": {
            "PREPARATION": "识别硬约束。",
            "CONVERGENCE": "收敛到一个可执行方案。",
        },
        "safety_tags": ["NO_REAL_COMPANY_CONFIDENTIAL"],
    }
    values.update(overrides)
    return QuestionVersionContent.model_validate(values)


def _assignment(slot: int) -> PersonaAssignmentDefinition:
    return PersonaAssignmentDefinition(
        id=uuid4(),
        slot=slot,
        persona_template_id=uuid4(),
        private_stance=PrivateStanceDefinition(
            initial_position=f"初始立场 {slot}",
            priority_dimensions=(
                PriorityDimension(code="FEASIBILITY", weight=Decimal("0.800")),
            ),
            concession_conditions=("出现可验证的新证据。",),
            private_information=None,
            red_lines=("不得突破硬约束。",),
            preferred_group_role=None,
        ),
    )


def test_question_content_rejects_unknown_or_unregistered_structure() -> None:
    with pytest.raises(ValidationError):
        _content(arbitrary_metadata={"free_form": True})

    with pytest.raises(ValidationError):
        _content(question_type_code="FUTURE_UNREGISTERED")

    with pytest.raises(ValidationError):
        _content(phase_prompts={"SECRET_PHASE": "不可接受。"})

    with pytest.raises(ValidationError):
        _content(options=[{"key": "A", "label": "A", "description": "only"}])


def test_phase_prompts_cannot_be_mutated_after_validation() -> None:
    content = _content()

    with pytest.raises(TypeError):
        cast(Any, content.phase_prompts)["SECRET_PHASE"] = "注入非法 phase"
    with pytest.raises(ValidationError):
        content.phase_prompts.preparation = "注入后的非法覆盖"
    assert not hasattr(content.phase_prompts, "SECRET_PHASE")


def test_question_content_rejects_duplicate_item_identity() -> None:
    duplicate = {"key": "SAME", "text": "first"}
    with pytest.raises(ValidationError):
        _content(hard_constraints=[duplicate, {"key": "SAME", "text": "second"}])


def test_short_and_long_text_reject_whitespace_only_values() -> None:
    with pytest.raises(ValidationError):
        _content(title="   ")
    with pytest.raises(ValidationError):
        _content(scenario="\t\r\n")
    with pytest.raises(ValidationError):
        _content(hard_constraints=[{"key": "BUDGET", "text": "   "}])
    with pytest.raises(ValidationError):
        _persona(display_name="   ")
    with pytest.raises(ValidationError):
        PrivateStanceDefinition(
            initial_position="   ",
            priority_dimensions=(
                PriorityDimension(code="VALUE", weight=Decimal("0.500")),
            ),
        )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("initiative", Decimal("-0.001")),
        ("initiative", Decimal("1.001")),
        ("initiative", Decimal("0.0001")),
        ("support_user_bias", Decimal("-1.001")),
        ("support_user_bias", Decimal("1.001")),
        ("average_turn_seconds", 9),
        ("average_turn_seconds", 91),
        ("initiative", Decimal("NaN")),
        ("initiative", Decimal("Infinity")),
        ("initiative", True),
    ],
)
def test_persona_numeric_boundary_rejects_invalid_values(
    field: str,
    value: object,
) -> None:
    with pytest.raises(ValidationError):
        _persona(**{field: value})


def test_persona_template_has_no_question_specific_viewpoint_field() -> None:
    with pytest.raises(ValidationError):
        _persona(initial_position="应优先选择方案 A")


def test_private_stance_rejects_duplicate_or_overprecise_priorities() -> None:
    with pytest.raises(ValidationError):
        PrivateStanceDefinition(
            initial_position="立场",
            priority_dimensions=(
                PriorityDimension(code="VALUE", weight=Decimal("0.500")),
                PriorityDimension(code="VALUE", weight=Decimal("0.400")),
            ),
            concession_conditions=("条件",),
            red_lines=("底线",),
        )

    with pytest.raises(ValidationError):
        PriorityDimension(code="VALUE", weight=Decimal("0.5001"))


def test_published_bundle_requires_exact_three_distinct_slots_and_personas() -> None:
    assignments = (_assignment(1), _assignment(2), _assignment(3))
    bundle = PublishedQuestionBundle(
        template_id=uuid4(),
        template_code="INTERNAL_VALIDATION_RESOURCE_ALLOCATION",
        version_id=uuid4(),
        version_number=1,
        content=_content(),
        assignments=assignments,
        created_at=datetime(2026, 8, 17, tzinfo=UTC),
        published_at=datetime(2026, 8, 17, tzinfo=UTC),
    )

    assert [assignment.slot for assignment in bundle.assignments] == [1, 2, 3]

    with pytest.raises(ValidationError):
        PublishedQuestionBundle(
            template_id=uuid4(),
            template_code="INTERNAL_VALIDATION_RESOURCE_ALLOCATION",
            version_id=uuid4(),
            version_number=1,
            content=_content(),
            assignments=assignments[:2],
            created_at=datetime(2026, 8, 17, tzinfo=UTC),
            published_at=datetime(2026, 8, 17, tzinfo=UTC),
        )

    duplicate_persona = assignments[0].model_copy(update={"id": uuid4(), "slot": 2})
    with pytest.raises(ValidationError):
        PublishedQuestionBundle(
            template_id=uuid4(),
            template_code="INTERNAL_VALIDATION_RESOURCE_ALLOCATION",
            version_id=uuid4(),
            version_number=1,
            content=_content(),
            assignments=(assignments[0], duplicate_persona, assignments[2]),
            created_at=datetime(2026, 8, 17, tzinfo=UTC),
            published_at=datetime(2026, 8, 17, tzinfo=UTC),
        )


def test_domain_requires_uuid4_and_timezone_aware_timestamps() -> None:
    with pytest.raises(ValidationError):
        _persona(id=UUID("00000000-0000-5000-8000-000000000001"))

    with pytest.raises(ValidationError):
        _persona(created_at=datetime(2026, 8, 17))


def test_persona_retirement_cannot_precede_creation() -> None:
    with pytest.raises(ValidationError):
        _persona(retired_at=datetime(2026, 8, 16, tzinfo=UTC))
