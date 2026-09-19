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
    V0_1_SCHEDULER_POLICY_V1,
    V0_1_SCHEDULER_POLICY_V2,
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


SESSION_ID = _uuid(899)


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
    session_id: UUID = SESSION_ID,
) -> SchedulerInput:
    return SchedulerInput(
        session_id=session_id,
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


@pytest.mark.parametrize(
    "kind",
    (
        SpeakingOpportunityKind.PHASE_MANDATED,
        SpeakingOpportunityKind.EXPLICIT_REQUEST,
        SpeakingOpportunityKind.NOMINATION,
    ),
)
def test_real_opportunity_priority_precedes_equal_human_participation(
    kind: SpeakingOpportunityKind,
) -> None:
    human = _participant(13, 1, actor=ParticipantActorKind.HUMAN)
    ai = _participant(14, 2)
    opportunity = SchedulerOpportunity(
        opportunity_id=_uuid(101),
        participant_id=ai.participant_id,
        kind=kind,
        created_at=NOW - timedelta(seconds=5),
    )

    decision = decide_floor(
        _input((human, ai), opportunities=(opportunity,)),
        V0_1_SCHEDULER_POLICY,
    )

    assert decision.selected_participant_id == ai.participant_id
    assert decision.opportunity_id == opportunity.opportunity_id


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
    assert opening.selected_participant_id in {
        newer.participant_id,
        older.participant_id,
    }
    assert opening.metadata.tie_break_class == "PARTICIPANT_ID"


def test_human_keeps_equal_priority_before_session_shuffled_ai_order() -> None:
    human = _participant(52, 4, actor=ParticipantActorKind.HUMAN)
    ai_participants = tuple(_participant(index, index) for index in range(53, 56))

    decision = decide_floor(
        _input((ai_participants[2], human, *ai_participants[:2])),
        V0_1_SCHEDULER_POLICY,
    )

    assert decision.selected_participant_id == human.participant_id
    assert decision.metadata.tie_break_class == "NOT_APPLICABLE"


def test_final_tie_break_is_retry_stable_but_session_and_phase_aware() -> None:
    participants = tuple(_participant(index, index) for index in range(1, 5))
    baseline = _input(participants, phase=SessionStatus.OPENING_STATEMENTS)

    first = decide_floor(baseline, V0_1_SCHEDULER_POLICY)
    retry = decide_floor(
        replace(baseline, participants=tuple(reversed(participants))),
        V0_1_SCHEDULER_POLICY,
    )
    different_decision_id = decide_floor(
        replace(baseline, decision_id=_uuid(999)),
        V0_1_SCHEDULER_POLICY,
    )
    alternatives = {
        decide_floor(
            replace(baseline, session_id=_uuid(session_number)),
            V0_1_SCHEDULER_POLICY,
        ).selected_participant_id
        for session_number in range(901, 921)
    }
    later_phase = decide_floor(
        replace(baseline, phase=SessionStatus.FINAL_SUMMARY),
        V0_1_SCHEDULER_POLICY,
    )
    phase_pairs = {
        (
            decide_floor(
                replace(baseline, session_id=_uuid(session_number)),
                V0_1_SCHEDULER_POLICY,
            ).selected_participant_id,
            decide_floor(
                replace(
                    baseline,
                    session_id=_uuid(session_number),
                    phase=SessionStatus.FINAL_SUMMARY,
                ),
                V0_1_SCHEDULER_POLICY,
            ).selected_participant_id,
        )
        for session_number in range(901, 921)
    }

    assert retry == first
    assert (
        different_decision_id.selected_participant_id == first.selected_participant_id
    )
    assert len(alternatives) > 1
    assert any(opening != final for opening, final in phase_pairs)
    assert later_phase.selected_participant_id in {
        participant.participant_id for participant in participants
    }
    assert first.metadata.tie_break_class == "PARTICIPANT_ID"


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


def test_participant_identity_is_stable_final_tie_break_when_slots_are_equal() -> None:
    higher = _participant(61, 1)
    lower = _participant(60, 1)

    decision = decide_floor(
        _input((higher, lower)),
        V0_1_SCHEDULER_POLICY,
    )

    assert decision.selected_participant_id in {
        lower.participant_id,
        higher.participant_id,
    }
    assert decide_floor(_input((lower, higher)), V0_1_SCHEDULER_POLICY) == decision
    assert decision.metadata.tie_break_class == "PARTICIPANT_ID"


def test_new_scheduler_decisions_publish_distinct_v2_policy_identity() -> None:
    decision = decide_floor(
        _input((_participant(1, 1), _participant(2, 2))),
        V0_1_SCHEDULER_POLICY,
    )

    assert V0_1_SCHEDULER_POLICY.version == "v0.1-floor-2"
    assert V0_1_SCHEDULER_POLICY is V0_1_SCHEDULER_POLICY_V2
    assert decision.policy_version == "v0.1-floor-2"


def test_legacy_v1_policy_preserves_seat_then_uuid_tie_break() -> None:
    lower_seat = _participant(1, 1)
    higher_seat = _participant(2, 2)
    scheduler_input = _input(
        (higher_seat, lower_seat),
        phase=SessionStatus.OPENING_STATEMENTS,
    )

    decision = decide_floor(scheduler_input, V0_1_SCHEDULER_POLICY_V1)
    current = decide_floor(scheduler_input, V0_1_SCHEDULER_POLICY_V2)

    assert decision.selected_participant_id == lower_seat.participant_id
    assert decision.policy_version == "v0.1-floor-1"
    assert decision.metadata.tie_break_class == "SEAT_ORDER"
    assert current.selected_participant_id == higher_seat.participant_id
    assert current.policy_version == "v0.1-floor-2"
    assert current.metadata.tie_break_class == "PARTICIPANT_ID"


def test_legacy_v1_policy_preserves_public_deadline_intervention() -> None:
    scheduler_input = replace(
        _input((_participant(69, 1),)),
        phase_deadline_at=NOW + timedelta(seconds=10),
    )

    decision = decide_floor(scheduler_input, V0_1_SCHEDULER_POLICY_V1)

    assert decision.outcome is FloorDecisionOutcome.REQUEST_INTERVENTION
    assert decision.intervention_kind is FloorInterventionKind.DEADLINE
    assert decision.primary_reason is FloorPolicyReason.DEADLINE_RECOVERY
    assert decision.policy_version == "v0.1-floor-1"


def test_deadline_pressure_pauses_scheduling_without_public_intervention() -> None:
    scheduler_input = replace(
        _input((_participant(70, 1),)),
        phase_deadline_at=NOW + timedelta(seconds=10),
    )

    decision = decide_floor(scheduler_input, V0_1_SCHEDULER_POLICY)

    assert decision.outcome is FloorDecisionOutcome.NO_GRANT
    assert decision.intervention_kind is None
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
