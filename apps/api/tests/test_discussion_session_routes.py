from group_interview_arena_api.app import create_app
from group_interview_arena_api.core.config import Environment, Settings


def test_session_rest_contract_is_cookie_secured_and_bodyless_in_openapi() -> None:
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

    assert "requestBody" not in create_operation
    assert create_operation["security"] == [{"SessionCookie": []}]
    assert create_operation["responses"]["201"]["content"]["application/json"][
        "schema"
    ] == {"$ref": "#/components/schemas/SessionSnapshotResponse"}
    assert snapshot_operation["security"] == [{"SessionCookie": []}]
    assert "X-GIA-CSRF" not in str(snapshot_operation)
    assert schema["components"]["securitySchemes"]["SessionCookie"] == {
        "type": "apiKey",
        "description": (
            "Opaque server-side session token stored in an HttpOnly Cookie."
        ),
        "in": "cookie",
        "name": "gia_session",
    }
