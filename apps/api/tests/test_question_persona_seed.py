import json
from decimal import Decimal

from group_interview_arena_api.app import create_app
from group_interview_arena_api.core.config import Environment, Settings
from group_interview_arena_api.modules.question_personas.seed import (
    INTERNAL_VALIDATION_BUNDLE,
    V01_PERSONA_TEMPLATES,
)


def test_v01_seed_contains_exactly_four_stable_personas() -> None:
    assert [
        (persona.code, persona.display_name) for persona in V01_PERSONA_TEMPLATES
    ] == [
        ("LOGIC_ANALYST", "逻辑分析者"),
        ("CREATIVE_DIVERGER", "创意发散者"),
        ("GENTLE_COORDINATOR", "温和协调者"),
        ("ASSERTIVE_FACILITATOR", "强势控场者"),
    ]
    assert len({persona.id for persona in V01_PERSONA_TEMPLATES}) == 4
    assert all(
        persona.support_user_bias == Decimal("0.000")
        for persona in V01_PERSONA_TEMPLATES
    )


def test_seed_question_is_one_internal_fixture_not_formal_question_content() -> None:
    assert (
        INTERNAL_VALIDATION_BUNDLE.template_code
        == "INTERNAL_VALIDATION_RESOURCE_ALLOCATION"
    )
    assert INTERNAL_VALIDATION_BUNDLE.version_number == 1
    assert len(INTERNAL_VALIDATION_BUNDLE.assignments) == 3
    assert "内部验证" in INTERNAL_VALIDATION_BUNDLE.content.title
    assert {
        assignment.persona_template_id
        for assignment in INTERNAL_VALIDATION_BUNDLE.assignments
    }.issubset({persona.id for persona in V01_PERSONA_TEMPLATES})


def test_private_stance_is_absent_from_current_browser_api_contract() -> None:
    application = create_app(
        Settings(
            environment=Environment.TEST,
            cors_origins=("http://localhost:3000",),
        )
    )
    openapi = json.dumps(application.openapi(), ensure_ascii=False)

    assert "private_information" not in openapi
    assert "initial_position" not in openapi
    assert "priority_dimensions" not in openapi
