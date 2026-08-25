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
    transcript_operation = paths["/sessions/{session_id}/utterances"]["get"]

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
    assert transcript_operation["security"] == [{"SessionCookie": []}]
    assert "X-GIA-CSRF" not in str(transcript_operation)
    assert transcript_operation["responses"]["200"]["content"]["application/json"][
        "schema"
    ] == {"$ref": "#/components/schemas/TranscriptResponse"}
    transcript_parameters = {
        parameter["name"]: parameter for parameter in transcript_operation["parameters"]
    }
    assert transcript_parameters["after_sequence"]["schema"] == {
        "type": "integer",
        "minimum": 0,
        "default": 0,
        "title": "After Sequence",
    }
    assert transcript_parameters["limit"]["schema"] == {
        "type": "integer",
        "maximum": 200,
        "minimum": 1,
        "default": 100,
        "title": "Limit",
    }
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
        "floor",
    }
    assert snapshot_schema["required"] == [
        "id",
        "question_version_id",
        "status",
        "phase_started_at",
        "phase_deadline_at",
        "server_now",
        "created_at",
        "updated_at",
        "last_sequence",
        "floor",
    ]
    floor_schema = schema["components"]["schemas"]["FloorSnapshotResponse"]
    assert set(floor_schema["properties"]) == {
        "participants",
        "current_grant",
        "latest_event",
    }
    serialized_schema = (
        str(floor_schema)
        + str(schema["components"]["schemas"]["CurrentFloorGrantResponse"])
        + str(schema["components"]["schemas"]["FloorLifecycleResponse"])
    )
    for forbidden in (
        "decision_id",
        "policy_version",
        "metadata",
        "ranking",
        "weight",
        "stance",
        "persona",
        "prompt",
        "score",
    ):
        assert forbidden not in serialized_schema.lower()
    transcript_schema = schema["components"]["schemas"]["TranscriptResponse"]
    assert set(transcript_schema["properties"]) == {
        "items",
        "next_after_sequence",
    }
    assert transcript_schema["required"] == ["items", "next_after_sequence"]
    transcript_item_schema = schema["components"]["schemas"][
        "TranscriptUtteranceResponse"
    ]
    assert set(transcript_item_schema["properties"]) == {
        "utterance_id",
        "sequence",
        "occurred_at",
        "action_id",
        "participant_id",
        "actor_kind",
        "floor_grant_id",
        "phase",
        "content",
    }
    assert transcript_item_schema["properties"]["actor_kind"] == {
        "$ref": "#/components/schemas/TranscriptActorKind"
    }
    assert schema["components"]["schemas"]["TranscriptActorKind"]["enum"] == [
        "HUMAN",
        "AI",
    ]
    assert transcript_item_schema["properties"]["phase"] == {
        "$ref": "#/components/schemas/TranscriptPhase"
    }
    assert schema["components"]["schemas"]["TranscriptPhase"]["enum"] == [
        "OPENING_STATEMENTS",
        "EXPLORATION",
        "CONFLICT_AND_EVALUATION",
        "CONVERGENCE",
        "FINAL_SUMMARY",
    ]
