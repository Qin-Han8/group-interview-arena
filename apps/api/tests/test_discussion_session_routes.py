from group_interview_arena_api.app import create_app
from group_interview_arena_api.core.config import Environment, Settings


def test_session_rest_contract_is_cookie_secured_and_version_bound_in_openapi() -> None:
    application = create_app(
        Settings(
            environment=Environment.TEST,
            cors_origins=("http://localhost:3000",),
        )
    )

    schema = application.openapi()
    paths = schema["paths"]
    create_operation = paths["/sessions"]["post"]
    snapshot_operation = paths["/sessions/{session_id}"]["get"]
    start_operation = paths["/sessions/{session_id}/start"]["post"]

    assert create_operation["requestBody"]["required"] is True
    assert create_operation["requestBody"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/SessionCreateRequest"
    }
    assert create_operation["security"] == [{"SessionCookie": []}]
    assert create_operation["responses"]["201"]["content"]["application/json"][
        "schema"
    ] == {"$ref": "#/components/schemas/SessionSnapshotResponse"}
    assert snapshot_operation["security"] == [{"SessionCookie": []}]
    assert "X-GIA-CSRF" not in str(snapshot_operation)
    assert start_operation["requestBody"]["required"] is True
    assert start_operation["requestBody"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/SessionStartRequest"
    }
    assert start_operation["security"] == [{"SessionCookie": []}]
    assert "X-GIA-CSRF" in str(start_operation)
    assert schema["components"]["securitySchemes"]["SessionCookie"] == {
        "type": "apiKey",
        "description": (
            "Opaque server-side session token stored in an HttpOnly Cookie."
        ),
        "in": "cookie",
        "name": "gia_session",
    }

    request_schema = schema["components"]["schemas"]["SessionCreateRequest"]
    assert request_schema["required"] == ["question_version_id"]
    assert set(request_schema["properties"]) == {"question_version_id"}
    start_request_schema = schema["components"]["schemas"]["SessionStartRequest"]
    assert start_request_schema["required"] == ["action_id"]
    assert set(start_request_schema["properties"]) == {"action_id"}
    snapshot_schema = schema["components"]["schemas"]["SessionSnapshotResponse"]
    assert set(snapshot_schema["properties"]) == {
        "id",
        "question_version_id",
        "status",
        "phase_started_at",
        "phase_deadline_at",
        "server_now",
        "created_at",
        "updated_at",
        "last_sequence",
    }
