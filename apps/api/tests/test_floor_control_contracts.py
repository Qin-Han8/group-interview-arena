from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from group_interview_arena_api.modules.discussion_sessions.contracts import (
    FormalEventEnvelope,
)


def _envelope(event_type: str, payload: dict[str, object]) -> dict[str, object]:
    return {
        "schema_version": 1,
        "type": event_type,
        "session_id": str(uuid4()),
        "sequence": 4,
        "occurred_at": datetime.now(UTC),
        "action_id": str(uuid4()),
        "payload": payload,
    }


def test_floor_event_contracts_accept_exact_safe_payloads() -> None:
    grant_id = uuid4()
    participant_id = uuid4()
    grant = FormalEventEnvelope.model_validate(
        _envelope(
            "floor.granted",
            {
                "grant_id": str(grant_id),
                "decision_id": str(uuid4()),
                "participant_id": str(participant_id),
                "phase": "OPENING_STATEMENTS",
                "opportunity_id": None,
                "reason_code": "FIRST_OPPORTUNITY",
                "policy_version": "v0.1-floor-1",
            },
        )
    )
    release_data = _envelope(
        "floor.released",
        {
            "grant_id": str(grant_id),
            "participant_id": str(participant_id),
            "phase": "OPENING_STATEMENTS",
            "reason_code": "SPEAKER_FINISHED",
        },
    )
    release_data["action_id"] = None
    release = FormalEventEnvelope.model_validate(release_data)
    intervention = FormalEventEnvelope.model_validate(
        _envelope(
            "floor.intervention_requested",
            {
                "intervention_id": str(uuid4()),
                "decision_id": str(uuid4()),
                "phase": "CONVERGENCE",
                "intervention_kind": "DEADLINE",
                "reason_code": "DEADLINE_RECOVERY",
                "policy_version": "v0.1-floor-1",
            },
        )
    )

    assert grant.type == "floor.granted"
    assert release.type == "floor.released"
    assert intervention.type == "floor.intervention_requested"


@pytest.mark.parametrize("private_key", ["private_stance", "policy_weights", "score"])
def test_floor_event_contract_rejects_private_or_internal_extra_fields(
    private_key: str,
) -> None:
    payload: dict[str, object] = {
        "grant_id": str(uuid4()),
        "decision_id": str(uuid4()),
        "participant_id": str(uuid4()),
        "phase": "EXPLORATION",
        "opportunity_id": None,
        "reason_code": "FIRST_OPPORTUNITY",
        "policy_version": "v0.1-floor-1",
        private_key: "sentinel",
    }
    with pytest.raises(ValidationError):
        FormalEventEnvelope.model_validate(_envelope("floor.granted", payload))


def test_floor_event_contract_rejects_non_floor_phase_and_wrong_version() -> None:
    data = _envelope(
        "floor.granted",
        {
            "grant_id": str(uuid4()),
            "decision_id": str(uuid4()),
            "participant_id": str(uuid4()),
            "phase": "PREPARATION",
            "opportunity_id": None,
            "reason_code": "FIRST_OPPORTUNITY",
            "policy_version": "v0.1-floor-1",
        },
    )
    with pytest.raises(ValidationError):
        FormalEventEnvelope.model_validate(data)
    data["schema_version"] = 2
    data["payload"] = {**data["payload"], "phase": "EXPLORATION"}  # type: ignore[dict-item]
    with pytest.raises(ValidationError):
        FormalEventEnvelope.model_validate(data)
