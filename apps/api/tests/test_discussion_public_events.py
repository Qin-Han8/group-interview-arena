from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from group_interview_arena_api.modules.discussion_sessions.domain import StoredEvent
from group_interview_arena_api.modules.discussion_sessions.public_events import (
    PublicEventProjectionError,
    project_public_event,
)


def _floor_event(
    *,
    version: int,
    causation_action_id: UUID | None,
    event_type: str = "floor.released",
) -> StoredEvent:
    grant_id = uuid4()
    participant_id = uuid4()
    if event_type == "floor.released":
        payload: dict[str, object] = {
            "grant_id": str(grant_id),
            "participant_id": str(participant_id),
            "phase": "OPENING_STATEMENTS",
            "reason_code": "SPEAKER_FINISHED",
        }
    elif event_type == "floor.granted":
        payload = {
            "grant_id": str(grant_id),
            "decision_id": str(uuid4()),
            "participant_id": str(participant_id),
            "phase": "OPENING_STATEMENTS",
            "opportunity_id": None,
            "reason_code": "FIRST_OPPORTUNITY",
            "policy_version": "v0.1-floor-1",
        }
    else:
        payload = {
            "intervention_id": str(uuid4()),
            "decision_id": str(uuid4()),
            "phase": "OPENING_STATEMENTS",
            "intervention_kind": "SILENCE",
            "reason_code": "SILENCE_RECOVERY",
            "policy_version": "v0.1-floor-1",
        }
    return StoredEvent(
        event_version=version,
        event_type=event_type,
        session_id=uuid4(),
        sequence=7,
        occurred_at=datetime(2026, 8, 25, 1, 2, 3, tzinfo=UTC),
        causation_action_id=causation_action_id,
        payload=payload,
    )


def _utterance_event(
    *,
    actor_kind: str,
    causation_action_id: UUID | None,
) -> StoredEvent:
    return StoredEvent(
        event_version=1,
        event_type="participant.utterance.created",
        session_id=uuid4(),
        sequence=8,
        occurred_at=datetime(2026, 8, 25, 1, 2, 4, tzinfo=UTC),
        causation_action_id=causation_action_id,
        payload={
            "utterance_id": str(uuid4()),
            "participant_id": str(uuid4()),
            "actor_kind": actor_kind,
            "floor_grant_id": str(uuid4()),
            "phase": "OPENING_STATEMENTS",
            "content": "Public content only.",
        },
    )


def test_historical_floor_v1_preserves_private_durable_causation_publicly() -> None:
    action_id = uuid4()
    event = _floor_event(version=1, causation_action_id=action_id)

    projected = project_public_event(event, causation_command_type="floor.release")

    assert projected.schema_version == 1
    assert projected.action_id == action_id


@pytest.mark.parametrize(
    ("event_type", "command_type"),
    [
        ("floor.granted", "floor.schedule"),
        ("floor.released", "floor.release"),
        ("floor.intervention_requested", "floor.schedule"),
    ],
)
def test_floor_v2_redacts_internal_automatic_causation(
    event_type: str,
    command_type: str,
) -> None:
    event = _floor_event(
        version=2,
        causation_action_id=uuid4(),
        event_type=event_type,
    )

    projected = project_public_event(
        event,
        causation_command_type=command_type,
    )

    assert projected.schema_version == 2
    assert projected.action_id is None


def test_floor_v2_exposes_only_direct_human_submit_causation() -> None:
    action_id = uuid4()
    event = _floor_event(version=2, causation_action_id=action_id)

    projected = project_public_event(
        event,
        causation_command_type="participant.utterance.submit",
    )

    assert projected.action_id == action_id


def test_utterance_projection_requires_exact_human_action_and_null_ai_action() -> None:
    action_id = uuid4()

    human = project_public_event(
        _utterance_event(actor_kind="HUMAN", causation_action_id=action_id),
        causation_command_type="participant.utterance.submit",
    )
    ai = project_public_event(
        _utterance_event(actor_kind="AI", causation_action_id=None),
        causation_command_type=None,
    )

    assert human.action_id == action_id
    assert ai.action_id is None


@pytest.mark.parametrize(
    ("event_kind", "command_type"),
    [
        ("human_without_action", None),
        ("ai_with_action", "floor.release"),
        ("v2_floor_without_action_fact", None),
    ],
)
def test_projection_fails_closed_for_missing_or_contradictory_durable_causation(
    event_kind: str,
    command_type: str | None,
) -> None:
    if event_kind == "human_without_action":
        event = _utterance_event(actor_kind="HUMAN", causation_action_id=None)
    elif event_kind == "ai_with_action":
        event = _utterance_event(actor_kind="AI", causation_action_id=uuid4())
    else:
        event = _floor_event(version=2, causation_action_id=uuid4())

    with pytest.raises(PublicEventProjectionError):
        project_public_event(event, causation_command_type=command_type)


@pytest.mark.parametrize("invalid_kind", ["phase", "uuid", "version"])
def test_envelope_and_payload_validation_failures_use_projection_taxonomy(
    invalid_kind: str,
) -> None:
    action_id = uuid4()
    event = _utterance_event(actor_kind="HUMAN", causation_action_id=action_id)
    if invalid_kind == "phase":
        event.payload["phase"] = "CREATED"
    elif invalid_kind == "uuid":
        event.payload["floor_grant_id"] = "not-a-uuid"
    else:
        event = StoredEvent(
            event_version=2,
            event_type=event.event_type,
            session_id=event.session_id,
            sequence=event.sequence,
            occurred_at=event.occurred_at,
            causation_action_id=event.causation_action_id,
            payload=event.payload,
        )

    with pytest.raises(PublicEventProjectionError):
        project_public_event(
            event,
            causation_command_type="participant.utterance.submit",
        )
