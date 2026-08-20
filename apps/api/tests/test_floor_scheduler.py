from dataclasses import replace
from datetime import UTC, datetime, timedelta
from itertools import permutations
from uuid import UUID

import pytest

from group_interview_arena_api.modules.discussion_sessions.domain import SessionStatus
from group_interview_arena_api.modules.floor_control.domain import (
    FloorDecisionOutcome,
    FloorInterventionKind,
    FloorPolicyReason,
    ParticipantActorKind,
    ParticipantAvailability,
    ParticipationRole,
    SpeakingOpportunityKind,
)
from group_interview_arena_api.modules.floor_control.scheduler import (
    V0_1_SCHEDULER_POLICY,
    SchedulerGrantHistory,
    SchedulerInput,
    SchedulerOpportunity,
    SchedulerParticipant,
    SchedulerPolicy,
    decide_floor,
)

NOW = datetime(2026, 8, 20, 8, 0, tzinfo=UTC)


def _uuid(value: int) -> UUID:
    return UUID(int=value)


def _participant(
    value: int,
    seat: int,
    *,
    actor: ParticipantActorKind = ParticipantActorKind.AI,
    role: ParticipationRole = ParticipationRole.CANDIDATE,
    availability: ParticipantAvailability = ParticipantAvailability.AVAILABLE,
) -> SchedulerParticipant:
    return SchedulerParticipant(
        participant_id=_uuid(value),
        actor_kind=actor,
        participation_role=role,
        availability=availability,
        seat_order=seat,
    )


def _grant(
    value: int,
    participant: SchedulerParticipant,
    *,
    minutes_ago: int,
    phase: SessionStatus = SessionStatus.EXPLORATION,
) -> SchedulerGrantHistory:
    granted_at = NOW - timedelta(minutes=minutes_ago)
    return SchedulerGrantHistory(
        grant_id=_uuid(value),
        participant_id=participant.participant_id,
        phase=phase,
        granted_at=granted_at,
        released_at=granted_at + timedelta(seconds=10),
    )


def _input(
    participants: tuple[SchedulerParticipant, ...],
    *,
    phase: SessionStatus = SessionStatus.EXPLORATION,
    opportunities: tuple[SchedulerOpportunity, ...] = (),
    history: tuple[SchedulerGrantHistory, ...] = (),
    now: datetime = NOW,
) -> SchedulerInput:
    return SchedulerInput(
        decision_id=_uuid(900),
        phase=phase,
        expected_last_sequence=7,
        now=now,
        phase_started_at=NOW - timedelta(minutes=10),
        phase_deadline_at=NOW + timedelta(minutes=10),
        participants=participants,
        opportunities=opportunities,
        grant_history=history,
    )


def test_identical_and_shuffled_inputs_have_identical_decision_semantics() -> None:
    participants = (
        _participant(10, 3),
        _participant(11, 1),
        _participant(12, 2),
    )
    opportunity = SchedulerOpportunity(
        opportunity_id=_uuid(100),
        participant_id=participants[2].participant_id,
        kind=SpeakingOpportunityKind.EXPLICIT_REQUEST,
        created_at=NOW - timedelta(seconds=5),
    )
    expected = decide_floor(
        _input(participants, opportunities=(opportunity,)),
        V0_1_SCHEDULER_POLICY,
    )

    for ordering in permutations(participants):
        actual = decide_floor(
            _input(tuple(ordering), opportunities=(opportunity,)),
            V0_1_SCHEDULER_POLICY,
        )
        assert actual == expected
    assert expected.selected_participant_id == participants[2].participant_id


def test_first_opportunity_precedes_already_granted_candidate() -> None:
    previous = _participant(20, 1)
    first = _participant(21, 2)
    decision = decide_floor(
        _input((previous, first), history=(_grant(200, previous, minutes_ago=4),)),
        V0_1_SCHEDULER_POLICY,
    )

    assert decision.selected_participant_id == first.participant_id
    assert decision.primary_reason is FloorPolicyReason.MONOPOLY_PREVENTION
    assert FloorPolicyReason.FIRST_OPPORTUNITY in decision.supporting_reasons
    assert decision.metadata.first_opportunity_unmet is True


def test_unavailable_and_moderator_participants_never_enter_candidates() -> None:
    unavailable = _participant(
        30,
        1,
        availability=ParticipantAvailability.UNAVAILABLE,
    )
    moderator = _participant(
        31,
        2,
        actor=ParticipantActorKind.SYSTEM,
        role=ParticipationRole.MODERATOR,
    )
    human = _participant(32, 3, actor=ParticipantActorKind.HUMAN)

    decision = decide_floor(
        _input((unavailable, moderator, human)),
        V0_1_SCHEDULER_POLICY,
    )

    assert decision.selected_participant_id == human.participant_id


def test_monopoly_guard_blocks_previous_owner_when_unmet_alternative_exists() -> None:
    previous = _participant(40, 1)
    alternative = _participant(41, 2)
    decision = decide_floor(
        _input(
            (previous, alternative), history=(_grant(400, previous, minutes_ago=2),)
        ),
        V0_1_SCHEDULER_POLICY,
    )

    assert decision.selected_participant_id == alternative.participant_id
    assert decision.primary_reason is FloorPolicyReason.MONOPOLY_PREVENTION
    assert decision.metadata.previous_owner_was_selected is False


def test_phase_aware_order_and_stable_tie_break() -> None:
    older = _participant(50, 2)
    newer = _participant(51, 1)
    history = (
        _grant(500, older, minutes_ago=8),
        _grant(501, newer, minutes_ago=4),
    )

    discussion = decide_floor(
        _input((newer, older), history=history),
        V0_1_SCHEDULER_POLICY,
    )
    opening = decide_floor(
        _input(
            (newer, older),
            phase=SessionStatus.OPENING_STATEMENTS,
            history=tuple(
                replace(item, phase=SessionStatus.OPENING_STATEMENTS)
                for item in history
            ),
        ),
        V0_1_SCHEDULER_POLICY,
    )

    assert discussion.selected_participant_id == older.participant_id
    assert opening.selected_participant_id == newer.participant_id
    assert opening.metadata.tie_break_class == "SEAT_ORDER"


def test_shuffled_history_cannot_change_fairness_result() -> None:
    first = _participant(55, 1)
    second = _participant(56, 2)
    third = _participant(57, 3)
    history = (
        _grant(550, first, minutes_ago=9),
        _grant(551, second, minutes_ago=7),
        _grant(552, first, minutes_ago=5),
        _grant(553, third, minutes_ago=3),
    )
    expected = decide_floor(
        _input((first, second, third), history=history),
        V0_1_SCHEDULER_POLICY,
    )

    for ordering in permutations(history):
        actual = decide_floor(
            _input((third, first, second), history=tuple(ordering)),
            V0_1_SCHEDULER_POLICY,
        )
        assert actual == expected
    assert expected.selected_participant_id == second.participant_id


def test_uuid_is_final_tie_break_when_slots_are_equal() -> None:
    higher = _participant(61, 1)
    lower = _participant(60, 1)

    decision = decide_floor(
        _input((higher, lower)),
        V0_1_SCHEDULER_POLICY,
    )

    assert decision.selected_participant_id == lower.participant_id
    assert decision.metadata.tie_break_class == "PARTICIPANT_ID"


def test_deadline_pressure_precedes_grant_and_is_explainable() -> None:
    scheduler_input = replace(
        _input((_participant(70, 1),)),
        phase_deadline_at=NOW + timedelta(seconds=10),
    )

    decision = decide_floor(scheduler_input, V0_1_SCHEDULER_POLICY)

    assert decision.outcome is FloorDecisionOutcome.REQUEST_INTERVENTION
    assert decision.intervention_kind is FloorInterventionKind.DEADLINE
    assert decision.primary_reason is FloorPolicyReason.DEADLINE_RECOVERY


def test_silence_intervention_after_all_candidates_reach_phase_cap() -> None:
    participant = _participant(80, 1)
    history = (_grant(800, participant, minutes_ago=2),)
    policy = replace(
        V0_1_SCHEDULER_POLICY,
        max_phase_grants=1,
        silence_threshold=timedelta(seconds=30),
    )

    decision = decide_floor(
        _input((participant,), history=history),
        policy,
    )

    assert decision.outcome is FloorDecisionOutcome.REQUEST_INTERVENTION
    assert decision.intervention_kind is FloorInterventionKind.SILENCE
    assert decision.primary_reason is FloorPolicyReason.SILENCE_RECOVERY


def test_consecutive_cap_is_hard_even_without_an_alternative() -> None:
    participant = _participant(85, 1)
    history = (
        _grant(850, participant, minutes_ago=2),
        _grant(851, participant, minutes_ago=1),
    )
    policy = replace(
        V0_1_SCHEDULER_POLICY,
        silence_threshold=timedelta(minutes=10),
    )

    decision = decide_floor(_input((participant,), history=history), policy)

    assert decision.outcome is FloorDecisionOutcome.NO_GRANT
    assert decision.selected_participant_id is None


def test_empty_ordinary_roster_requests_no_eligible_intervention() -> None:
    moderator = _participant(
        86,
        1,
        actor=ParticipantActorKind.SYSTEM,
        role=ParticipationRole.MODERATOR,
    )

    decision = decide_floor(_input((moderator,)), V0_1_SCHEDULER_POLICY)

    assert decision.outcome is FloorDecisionOutcome.REQUEST_INTERVENTION
    assert decision.intervention_kind is FloorInterventionKind.NO_ELIGIBLE_PARTICIPANT
    assert decision.primary_reason is FloorPolicyReason.NO_ELIGIBLE_PARTICIPANT


def test_convergence_mandated_opportunity_has_summary_reason() -> None:
    first = _participant(87, 1)
    second = _participant(88, 2)
    history = (
        _grant(
            870,
            first,
            minutes_ago=3,
            phase=SessionStatus.CONVERGENCE,
        ),
        _grant(
            871,
            second,
            minutes_ago=2,
            phase=SessionStatus.CONVERGENCE,
        ),
    )
    opportunity = SchedulerOpportunity(
        opportunity_id=_uuid(872),
        participant_id=first.participant_id,
        kind=SpeakingOpportunityKind.PHASE_MANDATED,
        created_at=NOW - timedelta(minutes=1),
    )

    decision = decide_floor(
        _input(
            (second, first),
            phase=SessionStatus.CONVERGENCE,
            opportunities=(opportunity,),
            history=history,
        ),
        V0_1_SCHEDULER_POLICY,
    )

    assert decision.selected_participant_id == first.participant_id
    assert decision.primary_reason is FloorPolicyReason.PHASE_SUMMARY_OPPORTUNITY


def test_no_candidate_before_silence_threshold_is_audited_without_event_target() -> (
    None
):
    participant = _participant(90, 1)
    history = (_grant(900, participant, minutes_ago=1),)
    policy = replace(V0_1_SCHEDULER_POLICY, max_phase_grants=1)
    scheduler_input = replace(
        _input((participant,), history=history),
        now=history[0].released_at + timedelta(seconds=5),  # type: ignore[operator]
    )

    decision = decide_floor(scheduler_input, policy)

    assert decision.outcome is FloorDecisionOutcome.NO_GRANT
    assert decision.selected_participant_id is None
    assert decision.primary_reason is FloorPolicyReason.NO_ELIGIBLE_PARTICIPANT


def test_policy_is_closed_typed_and_safe_audit_contains_no_hidden_inputs() -> None:
    with pytest.raises(ValueError):
        SchedulerPolicy(
            version="invalid",
            opportunity_order=(SpeakingOpportunityKind.FAIRNESS,),
            max_consecutive_grants=1,
            max_phase_grants=1,
            silence_threshold=timedelta(seconds=1),
            deadline_intervention_threshold=timedelta(seconds=1),
        )

    decision = decide_floor(
        _input((_participant(100, 1),)),
        V0_1_SCHEDULER_POLICY,
    )
    serialized = repr(decision).lower()
    for forbidden in (
        "private_stance",
        "persona_calibration",
        "prompt",
        "provider",
        "score",
        "ranking",
        "weight",
    ):
        assert forbidden not in serialized
