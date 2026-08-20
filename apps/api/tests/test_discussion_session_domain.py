from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from group_interview_arena_api.modules.discussion_sessions.domain import (
    InvalidSessionStateError,
    PhaseDurationPlan,
    SessionCommand,
    SessionStatus,
    abort_session,
    decide_session_command,
    reconcile_due_transitions,
)

PLAN = PhaseDurationPlan.from_seconds(
    {
        SessionStatus.PREPARATION: 10,
        SessionStatus.OPENING_STATEMENTS: 20,
        SessionStatus.EXPLORATION: 30,
        SessionStatus.CONFLICT_AND_EVALUATION: 40,
        SessionStatus.CONVERGENCE: 50,
        SessionStatus.FINAL_SUMMARY: 60,
    }
)
NOW = datetime(2026, 8, 20, 1, 0, tzinfo=UTC)


def test_abort_transitions_created_session_with_list_valued_event_outcome() -> None:
    outcome = abort_session(SessionStatus.CREATED)

    assert outcome.status is SessionStatus.ABORTED_USER
    assert isinstance(outcome.events, list)
    assert len(outcome.events) == 1
    assert outcome.events[0].event_type == "session.state_changed"
    assert outcome.events[0].event_version == 2
    assert outcome.events[0].payload == {
        "previous_status": "CREATED",
        "status": "ABORTED_USER",
        "trigger": "USER_ABORT",
        "phase_started_at": None,
        "phase_deadline_at": None,
    }


@pytest.mark.parametrize(
    "status",
    [
        SessionStatus.CREATED,
        SessionStatus.PREPARATION,
        SessionStatus.OPENING_STATEMENTS,
        SessionStatus.EXPLORATION,
        SessionStatus.CONFLICT_AND_EVALUATION,
        SessionStatus.CONVERGENCE,
        SessionStatus.FINAL_SUMMARY,
    ],
)
def test_abort_is_legal_from_created_and_timed_active_phases(
    status: SessionStatus,
) -> None:
    assert abort_session(status).status is SessionStatus.ABORTED_USER


@pytest.mark.parametrize(
    "status",
    [SessionStatus.COMPLETED, SessionStatus.ABORTED_USER],
)
def test_abort_rejects_terminal_sessions_without_an_event(
    status: SessionStatus,
) -> None:
    try:
        abort_session(status)
    except InvalidSessionStateError as exception:
        assert exception.status is status
    else:
        raise AssertionError("Expected invalid state rejection")


def test_start_freezes_authoritative_duration_plan_and_first_deadline() -> None:
    outcome = decide_session_command(
        SessionStatus.CREATED,
        SessionCommand(
            schema_version=1,
            command_type="session.start",
            session_id=uuid4(),
            action_id=uuid4(),
            payload={},
        ),
        now=NOW,
        duration_plan=PLAN,
    )

    assert outcome.status is SessionStatus.PREPARATION
    assert outcome.phase_started_at == NOW
    assert outcome.phase_deadline_at == NOW + timedelta(seconds=10)
    assert outcome.frozen_duration_plan == {
        "PREPARATION": 10,
        "OPENING_STATEMENTS": 20,
        "EXPLORATION": 30,
        "CONFLICT_AND_EVALUATION": 40,
        "CONVERGENCE": 50,
        "FINAL_SUMMARY": 60,
    }
    assert outcome.events[0].payload == {
        "previous_status": "CREATED",
        "status": "PREPARATION",
        "trigger": "USER_START",
        "phase_started_at": "2026-08-20T01:00:00Z",
        "phase_deadline_at": "2026-08-20T01:00:10Z",
    }


@pytest.mark.parametrize(
    "status",
    [
        SessionStatus.PREPARATION,
        SessionStatus.OPENING_STATEMENTS,
        SessionStatus.EXPLORATION,
        SessionStatus.CONFLICT_AND_EVALUATION,
        SessionStatus.CONVERGENCE,
        SessionStatus.FINAL_SUMMARY,
        SessionStatus.COMPLETED,
        SessionStatus.ABORTED_USER,
    ],
)
def test_start_is_legal_only_from_created(status: SessionStatus) -> None:
    with pytest.raises(InvalidSessionStateError):
        decide_session_command(
            status,
            SessionCommand(
                schema_version=1,
                command_type="session.start",
                session_id=uuid4(),
                action_id=uuid4(),
                payload={},
            ),
            now=NOW,
            duration_plan=PLAN,
        )


def test_duration_plan_requires_exact_positive_timed_phase_map() -> None:
    with pytest.raises(ValueError):
        PhaseDurationPlan.from_seconds({"PREPARATION": 10})

    with pytest.raises(ValueError):
        PhaseDurationPlan.from_seconds(
            {
                **PLAN.to_json(),
                "DEVICE_CHECK": 10,
            }
        )

    with pytest.raises(ValueError):
        PhaseDurationPlan.from_seconds(
            {
                **PLAN.to_json(),
                "PREPARATION": 0,
            }
        )


def test_overdue_reconciliation_uses_persisted_deadlines_without_drift() -> None:
    outcome = reconcile_due_transitions(
        status=SessionStatus.PREPARATION,
        phase_started_at=NOW,
        phase_deadline_at=NOW + timedelta(seconds=10),
        duration_plan=PLAN,
        now=NOW + timedelta(seconds=65),
    )

    assert outcome.status is SessionStatus.CONFLICT_AND_EVALUATION
    assert outcome.phase_started_at == NOW + timedelta(seconds=60)
    assert outcome.phase_deadline_at == NOW + timedelta(seconds=100)
    assert [event.payload["status"] for event in outcome.events] == [
        "OPENING_STATEMENTS",
        "EXPLORATION",
        "CONFLICT_AND_EVALUATION",
    ]
    assert [event.payload["phase_started_at"] for event in outcome.events] == [
        "2026-08-20T01:00:10Z",
        "2026-08-20T01:00:30Z",
        "2026-08-20T01:01:00Z",
    ]


def test_overdue_reconciliation_can_complete_and_clear_current_timing() -> None:
    outcome = reconcile_due_transitions(
        status=SessionStatus.FINAL_SUMMARY,
        phase_started_at=NOW,
        phase_deadline_at=NOW + timedelta(seconds=60),
        duration_plan=PLAN,
        now=NOW + timedelta(seconds=60),
    )

    assert outcome.status is SessionStatus.COMPLETED
    assert outcome.phase_started_at is None
    assert outcome.phase_deadline_at is None
    assert outcome.events[0].payload == {
        "previous_status": "FINAL_SUMMARY",
        "status": "COMPLETED",
        "trigger": "PHASE_DEADLINE",
        "phase_started_at": None,
        "phase_deadline_at": None,
    }
