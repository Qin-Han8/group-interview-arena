from uuid import uuid4

import pytest

from group_interview_arena_api.modules.discussion_sessions.domain import SessionStatus
from group_interview_arena_api.modules.floor_control.domain import (
    FloorDecisionOutcome,
    FloorDecisionRecord,
    FloorInterventionKind,
    FloorPolicyReason,
    FloorReleaseReason,
    IneligibleParticipantError,
    InvalidFloorStateError,
    ParticipantActorKind,
    ParticipantAvailability,
    ParticipationRole,
    SafeDecisionMetadata,
    StaleFloorDecisionError,
    floor_granted_event,
    floor_intervention_requested_event,
    floor_released_event,
    require_floor_phase,
    require_fresh_sequence,
    require_ordinary_floor_eligibility,
)


def _metadata() -> SafeDecisionMetadata:
    return SafeDecisionMetadata(
        current_phase_grant_count=0,
        first_opportunity_unmet=True,
        previous_owner_was_selected=False,
        consecutive_grant_count=0,
        tie_break_class="SEAT_ORDER",
    )


def _grant_decision() -> FloorDecisionRecord:
    return FloorDecisionRecord(
        decision_id=uuid4(),
        phase=SessionStatus.OPENING_STATEMENTS,
        expected_last_sequence=3,
        outcome=FloorDecisionOutcome.GRANT,
        selected_participant_id=uuid4(),
        opportunity_id=None,
        intervention_kind=None,
        policy_version="v0.1-floor-1",
        primary_reason=FloorPolicyReason.FIRST_OPPORTUNITY,
        supporting_reasons=(FloorPolicyReason.PHASE_MANDATED_TURN,),
        metadata=_metadata(),
    )


@pytest.mark.parametrize(
    "actor_kind",
    [ParticipantActorKind.AI, ParticipantActorKind.HUMAN],
)
def test_available_ai_and_human_candidates_are_eligible(
    actor_kind: ParticipantActorKind,
) -> None:
    require_ordinary_floor_eligibility(
        actor_kind=actor_kind,
        participation_role=ParticipationRole.CANDIDATE,
        availability=ParticipantAvailability.AVAILABLE,
    )


@pytest.mark.parametrize(
    ("actor_kind", "role", "availability"),
    [
        (
            ParticipantActorKind.SYSTEM,
            ParticipationRole.MODERATOR,
            ParticipantAvailability.AVAILABLE,
        ),
        (
            ParticipantActorKind.HUMAN,
            ParticipationRole.MODERATOR,
            ParticipantAvailability.AVAILABLE,
        ),
        (
            ParticipantActorKind.AI,
            ParticipationRole.CANDIDATE,
            ParticipantAvailability.UNAVAILABLE,
        ),
    ],
)
def test_non_candidate_or_unavailable_participant_is_ineligible(
    actor_kind: ParticipantActorKind,
    role: ParticipationRole,
    availability: ParticipantAvailability,
) -> None:
    with pytest.raises(IneligibleParticipantError):
        require_ordinary_floor_eligibility(
            actor_kind=actor_kind,
            participation_role=role,
            availability=availability,
        )


@pytest.mark.parametrize(
    "status",
    [
        SessionStatus.CREATED,
        SessionStatus.PREPARATION,
        *SessionStatus.__members__.values(),
    ],
)
def test_only_frozen_floor_phases_are_accepted(status: SessionStatus) -> None:
    enabled = {
        SessionStatus.OPENING_STATEMENTS,
        SessionStatus.EXPLORATION,
        SessionStatus.CONFLICT_AND_EVALUATION,
        SessionStatus.CONVERGENCE,
        SessionStatus.FINAL_SUMMARY,
    }
    if status in enabled:
        require_floor_phase(status)
    else:
        with pytest.raises(InvalidFloorStateError):
            require_floor_phase(status)


def test_stale_floor_sequence_is_rejected() -> None:
    require_fresh_sequence(actual=4, expected=4)
    with pytest.raises(StaleFloorDecisionError):
        require_fresh_sequence(actual=5, expected=4)
    with pytest.raises(ValueError):
        require_fresh_sequence(actual=4, expected=True)


def test_decision_metadata_is_closed_and_floor_event_is_safe() -> None:
    decision = _grant_decision()
    event = floor_granted_event(grant_id=uuid4(), decision=decision)

    assert decision.metadata.to_json() == {
        "current_phase_grant_count": 0,
        "first_opportunity_unmet": True,
        "previous_owner_was_selected": False,
        "consecutive_grant_count": 0,
        "tie_break_class": "SEAT_ORDER",
    }
    assert set(event.payload) == {
        "grant_id",
        "decision_id",
        "participant_id",
        "phase",
        "opportunity_id",
        "reason_code",
        "policy_version",
    }
    serialized = repr(event.payload).lower()
    for forbidden in ("private", "persona", "prompt", "score", "ranking", "weight"):
        assert forbidden not in serialized


def test_new_floor_event_factories_emit_additive_v2() -> None:
    decision = _grant_decision()
    assert decision.selected_participant_id is not None
    granted = floor_granted_event(grant_id=uuid4(), decision=decision)
    released = floor_released_event(
        grant_id=uuid4(),
        participant_id=decision.selected_participant_id,
        phase=decision.phase,
        reason=FloorReleaseReason.SPEAKER_FINISHED,
    )
    intervention_decision = FloorDecisionRecord(
        decision_id=uuid4(),
        phase=SessionStatus.OPENING_STATEMENTS,
        expected_last_sequence=2,
        outcome=FloorDecisionOutcome.REQUEST_INTERVENTION,
        selected_participant_id=None,
        opportunity_id=None,
        intervention_kind=FloorInterventionKind.SILENCE,
        policy_version="v0.1-floor-1",
        primary_reason=FloorPolicyReason.SILENCE_RECOVERY,
        supporting_reasons=(),
        metadata=_metadata(),
    )
    intervention = floor_intervention_requested_event(
        intervention_id=uuid4(),
        decision=intervention_decision,
    )

    assert [
        granted.event_version,
        released.event_version,
        intervention.event_version,
    ] == [
        2,
        2,
        2,
    ]


def test_invalid_decision_target_and_metadata_are_rejected() -> None:
    with pytest.raises(ValueError):
        SafeDecisionMetadata(
            current_phase_grant_count=-1,
            first_opportunity_unmet=True,
            previous_owner_was_selected=False,
            consecutive_grant_count=0,
            tie_break_class="SEAT_ORDER",
        )
    with pytest.raises(ValueError):
        SafeDecisionMetadata(
            current_phase_grant_count=True,
            first_opportunity_unmet=True,
            previous_owner_was_selected=False,
            consecutive_grant_count=0,
            tie_break_class="SEAT_ORDER",
        )
    with pytest.raises(ValueError):
        FloorDecisionRecord(
            decision_id=uuid4(),
            phase=SessionStatus.PREPARATION,
            expected_last_sequence=0,
            outcome=FloorDecisionOutcome.REQUEST_INTERVENTION,
            selected_participant_id=None,
            opportunity_id=None,
            intervention_kind=FloorInterventionKind.SILENCE,
            policy_version="v1",
            primary_reason=FloorPolicyReason.SILENCE_RECOVERY,
            supporting_reasons=(),
            metadata=_metadata(),
        )
