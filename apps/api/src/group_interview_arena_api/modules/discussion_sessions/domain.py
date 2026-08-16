from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID


class SessionStatus(StrEnum):
    CREATED = "CREATED"
    ABORTED_USER = "ABORTED_USER"


@dataclass(frozen=True)
class PendingEvent:
    event_type: str
    payload: dict[str, object]


@dataclass(frozen=True)
class SessionCommand:
    schema_version: int
    command_type: str
    session_id: UUID
    action_id: UUID
    payload: dict[str, object]


@dataclass(frozen=True)
class SessionSnapshot:
    session_id: UUID
    status: SessionStatus
    created_at: datetime
    updated_at: datetime
    last_sequence: int


@dataclass(frozen=True)
class StoredEvent:
    event_version: int
    event_type: str
    session_id: UUID
    sequence: int
    occurred_at: datetime
    action_id: UUID | None
    payload: dict[str, object]


@dataclass(frozen=True)
class SessionCommandOutcome:
    status: SessionStatus
    events: list[PendingEvent]


class InvalidSessionStateError(Exception):
    def __init__(self, status: SessionStatus) -> None:
        super().__init__("Session command is invalid for the current state.")
        self.status = status


def abort_session(status: SessionStatus) -> SessionCommandOutcome:
    if status is not SessionStatus.CREATED:
        raise InvalidSessionStateError(status)

    return SessionCommandOutcome(
        status=SessionStatus.ABORTED_USER,
        events=[
            PendingEvent(
                event_type="session.state_changed",
                payload={
                    "previous_status": SessionStatus.CREATED.value,
                    "status": SessionStatus.ABORTED_USER.value,
                },
            )
        ],
    )


def decide_session_command(
    status: SessionStatus,
    command: SessionCommand,
) -> SessionCommandOutcome:
    if (
        command.schema_version != 1
        or command.command_type != "session.abort"
        or command.payload != {}
    ):
        raise ValueError("Unsupported session command.")
    return abort_session(status)
