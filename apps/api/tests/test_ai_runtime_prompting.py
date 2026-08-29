from decimal import Decimal
from uuid import uuid4

import pytest

from group_interview_arena_api.modules.ai_runtime.prompting import (
    PROMPT_VARIABLES,
    AuthorizedGenerationContext,
    AuthorizedPersonaContext,
    AuthorizedQuestionContext,
    PromptRenderError,
    prompt_variables,
    render_prompt,
)
from group_interview_arena_api.modules.question_personas.domain import (
    PriorityDimension,
    PrivateStanceDefinition,
)


def test_prompt_renderer_is_closed_fail_closed_and_byte_stable() -> None:
    variables = {
        "session_id": str(uuid4()),
        "participant_id": str(uuid4()),
        "floor_grant_id": str(uuid4()),
        "phase": "EXPLORATION",
        "question_context": '{"objective":"Reach one decision."}',
        "persona_context": '{"code":"LOGIC_ANALYST"}',
        "private_stance": '{"initial_position":"Prefer option A."}',
        "phase_instruction": "Compare the hard constraints.",
        "recent_discussion": "你：先比较成本。",
        "persona_behavior": "说话有结构，但保持口语讨论，不写成报告。",
    }
    template = (
        "Session ${session_id}\n"
        "Phase $phase\n"
        "Question $question_context\n"
        "Persona $persona_context\n"
        "Private $private_stance\n"
        "Instruction $phase_instruction\n"
        "Literal dollar: $$"
    )

    first = render_prompt(template, variables)
    second = render_prompt(template, dict(reversed(tuple(variables.items()))))

    assert first == second
    assert first.encode("utf-8") == second.encode("utf-8")
    assert first.endswith("Literal dollar: $")
    assert frozenset(variables) == PROMPT_VARIABLES


def test_authorized_context_supplies_exact_ten_prompt_variables() -> None:
    context = AuthorizedGenerationContext(
        session_id=uuid4(),
        participant_id=uuid4(),
        floor_grant_id=uuid4(),
        phase="EXPLORATION",
        question=AuthorizedQuestionContext(
            version_id=uuid4(),
            title="题目",
            question_type_code="RESOURCE_ALLOCATION",
            background_domain_code="GENERAL",
            difficulty_code="STANDARD",
            scenario="背景",
            objective="目标",
            hard_constraints=(),
            soft_constraints=(),
            stakeholders=(),
            options=(),
        ),
        persona=AuthorizedPersonaContext(
            assignment_id=uuid4(),
            persona_template_id=uuid4(),
            code="LOGIC_ANALYST",
            display_name="逻辑分析者",
            speech_style_code="STRUCTURED",
            initiative=Decimal("0.600"),
            interrupt_tendency=Decimal("0.200"),
            average_turn_seconds=40,
            stance_stability=Decimal("0.750"),
            persuasion_threshold=Decimal("0.700"),
            novel_idea_rate=Decimal("0.350"),
            summary_tendency=Decimal("0.600"),
            time_awareness=Decimal("0.650"),
            detail_focus=Decimal("0.800"),
            cooperation=Decimal("0.600"),
            support_user_bias=Decimal("0"),
            error_rate=Decimal("0.100"),
            off_topic_rate=Decimal("0.050"),
        ),
        private_stance=PrivateStanceDefinition(
            initial_position="支持方案 A",
            priority_dimensions=(PriorityDimension(code="COST", weight=Decimal("1")),),
            concession_conditions=(),
            private_information=None,
            red_lines=(),
            preferred_group_role=None,
        ),
        phase_instruction="比较硬约束。",
        recent_discussion="你：先比较成本。",
        persona_behavior="说话有结构，但保持口语讨论，不写成报告。",
    )

    variables = prompt_variables(context)

    assert (
        frozenset(variables)
        == PROMPT_VARIABLES
        == frozenset(
            {
                "session_id",
                "participant_id",
                "floor_grant_id",
                "phase",
                "question_context",
                "persona_context",
                "private_stance",
                "phase_instruction",
                "recent_discussion",
                "persona_behavior",
            }
        )
    )
    assert variables["recent_discussion"] == "你：先比较成本。"
    assert variables["persona_behavior"] == "说话有结构，但保持口语讨论，不写成报告。"


@pytest.mark.parametrize(
    ("template", "variables"),
    [
        ("$unknown_variable", {}),
        ("$session_id $phase", {"session_id": "known"}),
        ("${private_stance.__class__}", {}),
        ("dangling $", {}),
        ("constant", {"provider_secret": "must-not-enter"}),
    ],
)
def test_prompt_renderer_rejects_unknown_missing_invalid_or_extra_values(
    template: str,
    variables: dict[str, str],
) -> None:
    with pytest.raises(PromptRenderError):
        render_prompt(template, variables)
