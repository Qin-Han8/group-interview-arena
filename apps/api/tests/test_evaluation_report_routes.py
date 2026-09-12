import json

from group_interview_arena_api.app import create_app
from group_interview_arena_api.core.config import Environment, Settings


def test_report_openapi_is_owner_authenticated_closed_and_private_free() -> None:
    application = create_app(
        Settings(
            environment=Environment.TEST,
            cors_origins=("http://localhost:3000",),
        )
    )

    schema = application.openapi()
    operation = schema["paths"]["/sessions/{session_id}/report"]["get"]
    assert operation["security"] == [{"SessionCookie": []}]
    assert "X-GIA-CSRF" not in json.dumps(operation)
    assert set(operation["responses"]) == {"200", "401", "404", "422", "500"}

    generate_operation = schema["paths"]["/sessions/{session_id}/report"]["post"]
    assert generate_operation["security"] == [{"SessionCookie": []}]
    parameters = {item["name"]: item for item in generate_operation["parameters"]}
    assert parameters["session_id"]["in"] == "path"
    assert parameters["session_id"]["required"] is True
    assert parameters["session_id"]["schema"]["format"] == "uuid4"
    assert parameters["X-GIA-CSRF"]["in"] == "header"
    assert parameters["X-GIA-CSRF"]["required"] is True
    assert parameters["X-GIA-CSRF"]["schema"] == {"type": "string", "const": "1"}
    assert "requestBody" not in generate_operation
    assert set(generate_operation["responses"]) == {
        "200",
        "401",
        "403",
        "404",
        "409",
        "422",
        "500",
    }

    schemas = schema["components"]["schemas"]
    assert set(schemas["ReportMetadataResponse"]["properties"]) == {
        "report_id",
        "session_id",
        "status",
        "report_schema_version",
        "derivation_version",
        "source_through_sequence",
        "created_at",
        "completed_at",
    }
    assert schemas["ReportGenerationStatus"]["enum"] == [
        "REQUESTED",
        "RUNNING",
        "COMPLETED",
        "FAILED",
    ]
    assert set(schemas["EvidenceCardResponse"]["properties"]) == {
        "kind",
        "source_participant_id",
        "source_utterance_id",
        "source_event_sequence",
        "phase",
        "quote",
        "interpretation",
        "confidence",
    }
    assert set(schemas["SessionOverviewResponse"]["properties"]) == {
        "session_status",
        "question",
        "participant_count",
        "human_utterance_count",
        "ai_utterance_count",
        "total_utterance_count",
        "covered_phases",
        "summary",
    }
    assert set(schemas["CompletedReportContentResponse"]["properties"]) == {
        "overview",
        "strengths",
        "improvements",
        "priority_improvement",
    }
    serialized = json.dumps(
        {
            name: definition
            for name, definition in schemas.items()
            if name
            in {
                "ReportViewResponse",
                "ReportMetadataResponse",
                "CompletedReportContentResponse",
                "SessionOverviewResponse",
                "EvidenceCardResponse",
            }
        }
    ).lower()
    for forbidden in (
        "started_at",
        "failed_at",
        "private_stance",
        "reference_dimensions",
        "hidden_conflicts",
        "acceptable_outcome_patterns",
        "phase_prompts",
        "safety_tags",
        "score",
        "rank",
    ):
        assert forbidden not in serialized
