from group_interview_arena_api.modules.discussion_sessions.domain import (
    InvalidSessionStateError,
    SessionStatus,
    abort_session,
)


def test_abort_transitions_created_session_with_list_valued_event_outcome() -> None:
    outcome = abort_session(SessionStatus.CREATED)

    assert outcome.status is SessionStatus.ABORTED_USER
    assert isinstance(outcome.events, list)
    assert len(outcome.events) == 1
    assert outcome.events[0].event_type == "session.state_changed"
    assert outcome.events[0].payload == {
        "previous_status": "CREATED",
        "status": "ABORTED_USER",
    }


def test_abort_rejects_an_already_aborted_session_without_an_event() -> None:
    try:
        abort_session(SessionStatus.ABORTED_USER)
    except InvalidSessionStateError as exception:
        assert exception.status is SessionStatus.ABORTED_USER
    else:
        raise AssertionError("Expected invalid state rejection")
