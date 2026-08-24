from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from group_interview_arena_api.modules.ai_runtime.orchestration import (
    SingleAiTurnOutcome,
    SingleAiTurnResult,
    derive_automatic_turn_identities,
)


def test_automatic_turn_identities_are_stable_distinct_and_uuid4_compatible() -> None:
    session_id = uuid4()
    floor_grant_id = uuid4()

    first = derive_automatic_turn_identities(
        session_id=session_id,
        floor_grant_id=floor_grant_id,
    )
    replay = derive_automatic_turn_identities(
        session_id=session_id,
        floor_grant_id=floor_grant_id,
    )
    other_grant = derive_automatic_turn_identities(
        session_id=session_id,
        floor_grant_id=uuid4(),
    )

    assert replay == first

    values = tuple(first.model_dump().values())
    assert len(values) == 7
    assert len(set(values)) == len(values)
    assert all(isinstance(value, UUID) and value.version == 4 for value in values)
    assert other_grant != first


def test_single_ai_turn_result_is_a_closed_frozen_provider_neutral_contract() -> None:
    assert {outcome.value for outcome in SingleAiTurnOutcome} == {
        "waiting_for_human",
        "no_current_work",
        "not_applicable",
        "next_ai_granted",
        "next_human_granted",
        "no_grant",
        "intervention_requested",
        "reconciliation_required",
        "state_changed",
    }

    result = SingleAiTurnResult(outcome=SingleAiTurnOutcome.WAITING_FOR_HUMAN)

    assert result.model_dump(exclude_none=True) == {"outcome": "waiting_for_human"}
    assert not (
        {"provider", "provider_identifier", "model_identifier"}
        & set(SingleAiTurnResult.model_fields)
    )

    with pytest.raises(ValidationError):
        SingleAiTurnResult.model_validate(
            {
                "outcome": SingleAiTurnOutcome.NO_CURRENT_WORK,
                "provider_identifier": "must-not-leak",
            }
        )

    with pytest.raises(ValidationError):
        result.outcome = SingleAiTurnOutcome.NO_CURRENT_WORK
