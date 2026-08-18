import json

from group_interview_arena_api.app import create_app
from group_interview_arena_api.core.config import Environment, Settings

PRIVATE_FIELD_NAMES = {
    "persona_template_id",
    "initial_position",
    "priority_dimensions",
    "concession_conditions",
    "private_information",
    "red_lines",
    "preferred_group_role",
    "reference_dimensions",
    "hidden_conflicts",
    "acceptable_outcome_patterns",
    "phase_prompts",
    "safety_tags",
    "initiative",
    "support_user_bias",
}


def test_question_openapi_is_authenticated_allowlisted_and_private_free() -> None:
    application = create_app(
        Settings(
            environment=Environment.TEST,
            cors_origins=("http://localhost:3000",),
        )
    )
    schema = application.openapi()

    list_operation = schema["paths"]["/questions"]["get"]
    detail_operation = schema["paths"]["/questions/{question_version_id}"]["get"]
    assert list_operation["security"] == [{"SessionCookie": []}]
    assert detail_operation["security"] == [{"SessionCookie": []}]
    assert "X-GIA-CSRF" not in json.dumps(
        {"list": list_operation, "detail": detail_operation}
    )

    schemas = schema["components"]["schemas"]
    assert set(schemas["QuestionSummaryResponse"]["properties"]) == {
        "id",
        "question_template_id",
        "version_number",
        "title",
        "question_type",
        "background_domain",
        "difficulty",
        "estimated_minutes",
    }
    assert set(schemas["QuestionDetailResponse"]["properties"]) == {
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
    serialized = json.dumps(schema)
    for private_name in PRIVATE_FIELD_NAMES:
        assert private_name not in serialized
