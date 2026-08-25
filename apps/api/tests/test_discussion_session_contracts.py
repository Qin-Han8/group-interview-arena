import json
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from group_interview_arena_api.modules.discussion_sessions.contracts import (
    CurrentFloorGrantResponse,
    FloorLifecycleResponse,
    FloorParticipantResponse,
    FloorSnapshotResponse,
    FormalEventEnvelope,
    ParticipantUtteranceSubmitCommand,
    SessionAbortCommand,
    SessionSnapshotResponse,
    SessionStartCommand,
    WsErrorDetail,
    WsErrorEnvelope,
)
from group_interview_arena_api.modules.discussion_sessions.domain import SessionStatus
from group_interview_arena_api.modules.floor_control.domain import (
    FloorPolicyReason,
    ParticipantActorKind,
)


def test_abort_command_accepts_only_the_exact_v1_envelope() -> None:
    session_id = uuid4()
    action_id = uuid4()

    command = SessionAbortCommand.model_validate_json(
        json.dumps(
            {
                "schema_version": 1,
                "type": "session.abort",
                "session_id": str(session_id),
                "action_id": str(action_id),
                "payload": {},
            }
        )
    )

    assert command.session_id == session_id
    assert command.action_id == action_id
    assert command.semantic_payload() == {
        "schema_version": 1,
        "type": "session.abort",
        "payload": {},
    }


def test_start_command_accepts_only_the_exact_v1_envelope() -> None:
    session_id = uuid4()
    action_id = uuid4()

    command = SessionStartCommand.model_validate_json(
        json.dumps(
            {
                "schema_version": 1,
                "type": "session.start",
                "session_id": str(session_id),
                "action_id": str(action_id),
                "payload": {},
            }
        )
    )

    assert command.session_id == session_id
    assert command.action_id == action_id
    assert command.semantic_payload() == {
        "schema_version": 1,
        "type": "session.start",
        "payload": {},
    }


@pytest.mark.parametrize(
    "mutation",
    [
        {"schema_version": 2},
        {"type": "session.pause"},
        {"action_id": "00000000-0000-0000-0000-000000000001"},
        {"payload": {"reason": "not-allowed"}},
        {"unexpected": True},
    ],
)
def test_abort_command_rejects_unsupported_or_extra_content(
    mutation: dict[str, object],
) -> None:
    payload: dict[str, object] = {
        "schema_version": 1,
        "type": "session.abort",
        "session_id": str(uuid4()),
        "action_id": str(uuid4()),
        "payload": {},
    }
    payload.update(mutation)

    with pytest.raises(ValidationError):
        SessionAbortCommand.model_validate(payload)


def test_snapshot_and_formal_events_emit_exact_utc_z_contracts() -> None:
    session_id = uuid4()
    action_id = uuid4()
    occurred_at = datetime(2026, 8, 16, 1, 2, 3, tzinfo=UTC)
    snapshot = SessionSnapshotResponse(
        id=session_id,
        question_version_id=None,
        status=SessionStatus.CREATED,
        phase_started_at=None,
        phase_deadline_at=None,
        server_now=occurred_at,
        created_at=occurred_at,
        updated_at=occurred_at,
        last_sequence=1,
        floor=FloorSnapshotResponse(
            participants=[],
            current_grant=None,
            latest_event=None,
        ),
    )
    event = FormalEventEnvelope(
        schema_version=1,
        type="session.state_changed",
        session_id=session_id,
        sequence=2,
        occurred_at=occurred_at,
        action_id=action_id,
        payload={
            "previous_status": "CREATED",
            "status": "ABORTED_USER",
        },
    )

    assert snapshot.model_dump(mode="json") == {
        "id": str(session_id),
        "question_version_id": None,
        "status": "CREATED",
        "phase_started_at": None,
        "phase_deadline_at": None,
        "server_now": "2026-08-16T01:02:03Z",
        "created_at": "2026-08-16T01:02:03Z",
        "updated_at": "2026-08-16T01:02:03Z",
        "last_sequence": 1,
        "floor": {
            "participants": [],
            "current_grant": None,
            "latest_event": None,
        },
    }
    assert event.model_dump(mode="json") == {
        "schema_version": 1,
        "type": "session.state_changed",
        "session_id": str(session_id),
        "sequence": 2,
        "occurred_at": "2026-08-16T01:02:03Z",
        "action_id": str(action_id),
        "payload": {
            "previous_status": "CREATED",
            "status": "ABORTED_USER",
        },
    }


def test_v2_formal_event_payload_is_closed_and_timing_authoritative() -> None:
    session_id = uuid4()
    action_id = uuid4()
    occurred_at = datetime(2026, 8, 20, 1, 0, tzinfo=UTC)

    event = FormalEventEnvelope(
        schema_version=2,
        type="session.state_changed",
        session_id=session_id,
        sequence=2,
        occurred_at=occurred_at,
        action_id=action_id,
        payload={
            "previous_status": "CREATED",
            "status": "PREPARATION",
            "trigger": "USER_START",
            "phase_started_at": "2026-08-20T01:00:00Z",
            "phase_deadline_at": "2026-08-20T01:04:00Z",
        },
    )

    assert event.model_dump(mode="json")["payload"] == {
        "previous_status": "CREATED",
        "status": "PREPARATION",
        "trigger": "USER_START",
        "phase_started_at": "2026-08-20T01:00:00Z",
        "phase_deadline_at": "2026-08-20T01:04:00Z",
    }

    with pytest.raises(ValidationError):
        FormalEventEnvelope(
            schema_version=2,
            type="session.state_changed",
            session_id=session_id,
            sequence=3,
            occurred_at=occurred_at,
            action_id=action_id,
            payload={
                "previous_status": "CREATED",
                "status": "PREPARATION",
                "trigger": "USER_START",
                "phase_started_at": "2026-08-20T01:00:00Z",
                "phase_deadline_at": "2026-08-20T01:04:00Z",
                "next_status": "EXPLORATION",
            },
        )


def test_formal_event_payload_and_error_envelope_are_closed_and_distinct() -> None:
    session_id = uuid4()
    occurred_at = datetime.now(UTC)

    with pytest.raises(ValidationError):
        FormalEventEnvelope(
            schema_version=1,
            type="session.created",
            session_id=session_id,
            sequence=1,
            occurred_at=occurred_at,
            action_id=None,
            payload={"status": "ABORTED_USER"},
        )

    error = WsErrorEnvelope(
        schema_version=1,
        type="error",
        session_id=session_id,
        action_id=None,
        occurred_at=occurred_at,
        error=WsErrorDetail(
            code="PROTOCOL_ERROR",
            message="Realtime command could not be processed.",
            request_id=uuid4(),
        ),
    ).model_dump(mode="json")

    assert "sequence" not in error
    assert UUID(error["error"]["request_id"]).version == 4


def test_floor_snapshot_projection_is_closed_safe_and_human_compatible() -> None:
    occurred_at = datetime(2026, 8, 20, 1, 2, 3, tzinfo=UTC)
    participant_id = uuid4()
    grant_id = uuid4()

    projection = FloorSnapshotResponse(
        participants=[
            FloorParticipantResponse(
                participant_id=participant_id,
                actor_kind=ParticipantActorKind.HUMAN,
                seat_order=1,
            )
        ],
        current_grant=CurrentFloorGrantResponse(
            grant_id=grant_id,
            participant_id=participant_id,
            phase=SessionStatus.OPENING_STATEMENTS,
            reason_code=FloorPolicyReason.FIRST_OPPORTUNITY,
            granted_at=occurred_at,
        ),
        latest_event=FloorLifecycleResponse(
            type="floor.granted",
            sequence=4,
            occurred_at=occurred_at,
            phase=SessionStatus.OPENING_STATEMENTS,
            reason_code=FloorPolicyReason.FIRST_OPPORTUNITY,
            grant_id=grant_id,
            participant_id=participant_id,
        ),
    ).model_dump(mode="json")

    assert projection == {
        "participants": [
            {
                "participant_id": str(participant_id),
                "actor_kind": "HUMAN",
                "seat_order": 1,
            }
        ],
        "current_grant": {
            "grant_id": str(grant_id),
            "participant_id": str(participant_id),
            "phase": "OPENING_STATEMENTS",
            "reason_code": "FIRST_OPPORTUNITY",
            "granted_at": "2026-08-20T01:02:03Z",
        },
        "latest_event": {
            "type": "floor.granted",
            "sequence": 4,
            "occurred_at": "2026-08-20T01:02:03Z",
            "phase": "OPENING_STATEMENTS",
            "reason_code": "FIRST_OPPORTUNITY",
            "grant_id": str(grant_id),
            "participant_id": str(participant_id),
            "intervention_id": None,
            "intervention_kind": None,
        },
    }
    serialized = json.dumps(projection)
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
        assert forbidden not in serialized.lower()

    with pytest.raises(ValidationError):
        FloorLifecycleResponse.model_validate(
            {
                **projection["latest_event"],
                "hidden_ranking": [0.99],
            }
        )


def test_participant_utterance_submit_accepts_only_the_closed_v1_shape() -> None:
    session_id = uuid4()
    action_id = uuid4()
    floor_grant_id = uuid4()
    original = "  保留首尾空白的意见。  "

    command = ParticipantUtteranceSubmitCommand.model_validate(
        {
            "schema_version": 1,
            "type": "participant.utterance.submit",
            "session_id": str(session_id),
            "action_id": str(action_id),
            "payload": {
                "floor_grant_id": str(floor_grant_id),
                "content": original,
            },
        }
    )

    assert command.payload.content == original
    assert command.payload.floor_grant_id == floor_grant_id
    assert command.semantic_payload() == {
        "schema_version": 1,
        "type": "participant.utterance.submit",
        "payload": {
            "floor_grant_id": str(floor_grant_id),
            "content": original,
        },
    }


@pytest.mark.parametrize(
    "mutation",
    [
        {"schema_version": 2},
        {"type": "participant.utterance.create"},
        {"participant_id": str(uuid4())},
        {"payload": {"content": "valid"}},
        {
            "payload": {
                "floor_grant_id": str(uuid4()),
                "content": "valid",
                "participant_id": str(uuid4()),
            }
        },
        {"payload": {"floor_grant_id": str(uuid4()), "content": 42}},
    ],
)
def test_participant_utterance_submit_rejects_authority_and_shape_drift(
    mutation: dict[str, object],
) -> None:
    data: dict[str, object] = {
        "schema_version": 1,
        "type": "participant.utterance.submit",
        "session_id": str(uuid4()),
        "action_id": str(uuid4()),
        "payload": {"floor_grant_id": str(uuid4()), "content": "valid"},
    }
    data.update(mutation)

    with pytest.raises(ValidationError):
        ParticipantUtteranceSubmitCommand.model_validate(data)


def test_semantically_invalid_string_content_remains_a_parseable_command() -> None:
    for content in ("   ", "contains\x00nul", "x" * 4001):
        parsed = ParticipantUtteranceSubmitCommand.model_validate(
            {
                "schema_version": 1,
                "type": "participant.utterance.submit",
                "session_id": str(uuid4()),
                "action_id": str(uuid4()),
                "payload": {
                    "floor_grant_id": str(uuid4()),
                    "content": content,
                },
            }
        )
        assert parsed.payload.content == content


def test_participant_utterance_created_v1_is_exact_for_human_and_ai() -> None:
    occurred_at = datetime(2026, 8, 25, 4, 5, 6, tzinfo=UTC)
    payload: dict[str, object] = {
        "utterance_id": str(uuid4()),
        "participant_id": str(uuid4()),
        "actor_kind": "HUMAN",
        "floor_grant_id": str(uuid4()),
        "phase": "EXPLORATION",
        "content": "A durable public contribution.",
    }
    common: dict[str, object] = {
        "schema_version": 1,
        "type": "participant.utterance.created",
        "session_id": str(uuid4()),
        "sequence": 8,
        "occurred_at": occurred_at,
        "payload": payload,
    }
    action_id = uuid4()

    human = FormalEventEnvelope.model_validate({**common, "action_id": str(action_id)})
    ai = FormalEventEnvelope.model_validate(
        {
            **common,
            "action_id": None,
            "payload": {**payload, "actor_kind": "AI"},
        }
    )

    assert human.action_id == action_id
    assert ai.action_id is None
    assert set(human.payload) == {
        "utterance_id",
        "participant_id",
        "actor_kind",
        "floor_grant_id",
        "phase",
        "content",
    }


@pytest.mark.parametrize(
    ("schema_version", "actor_kind", "action_id", "extra"),
    [
        (1, "HUMAN", None, {}),
        (1, "AI", "uuid", {}),
        (2, "HUMAN", "uuid", {}),
        (1, "SYSTEM", "uuid", {}),
        (1, "HUMAN", "uuid", {"provider_identifier": "private"}),
    ],
)
def test_participant_utterance_created_rejects_version_action_and_payload_drift(
    schema_version: int,
    actor_kind: str,
    action_id: str | None,
    extra: dict[str, object],
) -> None:
    resolved_action_id = None if action_id is None else str(uuid4())
    with pytest.raises(ValidationError):
        FormalEventEnvelope.model_validate(
            {
                "schema_version": schema_version,
                "type": "participant.utterance.created",
                "session_id": str(uuid4()),
                "sequence": 9,
                "occurred_at": datetime.now(UTC),
                "action_id": resolved_action_id,
                "payload": {
                    "utterance_id": str(uuid4()),
                    "participant_id": str(uuid4()),
                    "actor_kind": actor_kind,
                    "floor_grant_id": str(uuid4()),
                    "phase": "OPENING_STATEMENTS",
                    "content": "Public only.",
                    **extra,
                },
            }
        )


def test_utterance_rejected_error_contract_is_safe_and_recoverable() -> None:
    error = WsErrorEnvelope(
        schema_version=1,
        type="error",
        session_id=uuid4(),
        action_id=uuid4(),
        occurred_at=datetime.now(UTC),
        error=WsErrorDetail(
            code="UTTERANCE_REJECTED",
            message="You cannot submit an utterance right now.",
            request_id=uuid4(),
        ),
    ).model_dump(mode="json")

    assert error["error"]["code"] == "UTTERANCE_REJECTED"
    assert error["error"]["message"] == "You cannot submit an utterance right now."
