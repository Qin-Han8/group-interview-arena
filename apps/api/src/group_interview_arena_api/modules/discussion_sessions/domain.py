from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from types import MappingProxyType
from uuid import UUID


class SessionStatus(StrEnum):
    CREATED = "CREATED"
    PREPARATION = "PREPARATION"
    OPENING_STATEMENTS = "OPENING_STATEMENTS"
    EXPLORATION = "EXPLORATION"
    CONFLICT_AND_EVALUATION = "CONFLICT_AND_EVALUATION"
    CONVERGENCE = "CONVERGENCE"
    FINAL_SUMMARY = "FINAL_SUMMARY"
    COMPLETED = "COMPLETED"
    ABORTED_USER = "ABORTED_USER"


class SessionTransitionTrigger(StrEnum):
    USER_START = "USER_START"
    USER_ABORT = "USER_ABORT"
    PHASE_DEADLINE = "PHASE_DEADLINE"


TIMED_PHASES: tuple[SessionStatus, ...] = (
    SessionStatus.PREPARATION,
    SessionStatus.OPENING_STATEMENTS,
    SessionStatus.EXPLORATION,
    SessionStatus.CONFLICT_AND_EVALUATION,
    SessionStatus.CONVERGENCE,
    SessionStatus.FINAL_SUMMARY,
)

ACTIVE_PHASES = frozenset(TIMED_PHASES)
TERMINAL_STATUSES = frozenset(
    {
        SessionStatus.COMPLETED,
        SessionStatus.ABORTED_USER,
    }
)
ABORTABLE_STATUSES = frozenset({SessionStatus.CREATED, *TIMED_PHASES})
NEXT_DEADLINE_STATUS: Mapping[SessionStatus, SessionStatus] = MappingProxyType(
    {
        SessionStatus.PREPARATION: SessionStatus.OPENING_STATEMENTS,
        SessionStatus.OPENING_STATEMENTS: SessionStatus.EXPLORATION,
        SessionStatus.EXPLORATION: SessionStatus.CONFLICT_AND_EVALUATION,
        SessionStatus.CONFLICT_AND_EVALUATION: SessionStatus.CONVERGENCE,
        SessionStatus.CONVERGENCE: SessionStatus.FINAL_SUMMARY,
        SessionStatus.FINAL_SUMMARY: SessionStatus.COMPLETED,
    }
)


def _require_aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Session timestamps must be timezone-aware.")
    return value.astimezone(UTC)


def _event_timestamp(value: datetime | None) -> str | None:
    if value is None:
        return None
    return _require_aware_utc(value).isoformat().replace("+00:00", "Z")


def _state_changed_payload(
    *,
    previous_status: SessionStatus,
    status: SessionStatus,
    trigger: SessionTransitionTrigger,
    phase_started_at: datetime | None,
    phase_deadline_at: datetime | None,
) -> dict[str, object]:
    return {
        "previous_status": previous_status.value,
        "status": status.value,
        "trigger": trigger.value,
        "phase_started_at": _event_timestamp(phase_started_at),
        "phase_deadline_at": _event_timestamp(phase_deadline_at),
    }


@dataclass(frozen=True)
class PendingEvent:
    event_type: str
    payload: dict[str, object]
    event_version: int = 2


@dataclass(frozen=True)
class PhaseDurationPlan:
    durations_seconds: Mapping[SessionStatus, int]

    @classmethod
    def from_seconds(
        cls, values: Mapping[str | SessionStatus, object]
    ) -> PhaseDurationPlan:
        normalized: dict[SessionStatus, int] = {}
        for key, seconds in values.items():
            status = key if isinstance(key, SessionStatus) else SessionStatus(key)
            if status not in ACTIVE_PHASES:
                raise ValueError("Duration plan contains an unsupported phase.")
            if (
                isinstance(seconds, bool)
                or not isinstance(seconds, int)
                or seconds <= 0
            ):
                raise ValueError(
                    "Duration plan values must be positive integer seconds."
                )
            normalized[status] = seconds

        if set(normalized) != set(TIMED_PHASES):
            raise ValueError("Duration plan must contain exactly the timed phases.")
        return cls(MappingProxyType(normalized))

    def duration_for(self, status: SessionStatus) -> int:
        if status not in ACTIVE_PHASES:
            raise ValueError("Status is not a timed phase.")
        return self.durations_seconds[status]

    def to_json(self) -> dict[str, int]:
        return {status.value: self.durations_seconds[status] for status in TIMED_PHASES}


@dataclass(frozen=True)
class SessionCommand:
    schema_version: int
    command_type: str
    session_id: UUID
    action_id: UUID
    payload: dict[str, object]


@dataclass(frozen=True)
class FloorParticipantSnapshot:
    participant_id: UUID
    actor_kind: str
    seat_order: int


@dataclass(frozen=True)
class CurrentFloorGrantSnapshot:
    grant_id: UUID
    participant_id: UUID
    phase: SessionStatus
    reason_code: str
    granted_at: datetime


@dataclass(frozen=True)
class FloorLifecycleSnapshot:
    event_type: str
    sequence: int
    occurred_at: datetime
    phase: SessionStatus
    reason_code: str
    grant_id: UUID | None = None
    participant_id: UUID | None = None
    intervention_id: UUID | None = None
    intervention_kind: str | None = None


@dataclass(frozen=True)
class FloorSnapshot:
    participants: tuple[FloorParticipantSnapshot, ...] = ()
    current_grant: CurrentFloorGrantSnapshot | None = None
    latest_event: FloorLifecycleSnapshot | None = None


@dataclass(frozen=True)
class SessionSnapshot:
    session_id: UUID
    question_version_id: UUID | None
    status: SessionStatus
    phase_started_at: datetime | None
    phase_deadline_at: datetime | None
    server_now: datetime
    created_at: datetime
    updated_at: datetime
    last_sequence: int
    floor: FloorSnapshot = FloorSnapshot()


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
    phase_started_at: datetime | None = None
    phase_deadline_at: datetime | None = None
    frozen_duration_plan: dict[str, int] | None = None


class InvalidSessionStateError(Exception):
    def __init__(self, status: SessionStatus) -> None:
        super().__init__("Session command is invalid for the current state.")
        self.status = status


def abort_session(status: SessionStatus) -> SessionCommandOutcome:
    if status not in ABORTABLE_STATUSES:
        raise InvalidSessionStateError(status)

    return SessionCommandOutcome(
        status=SessionStatus.ABORTED_USER,
        events=[
            PendingEvent(
                event_type="session.state_changed",
                payload=_state_changed_payload(
                    previous_status=status,
                    status=SessionStatus.ABORTED_USER,
                    trigger=SessionTransitionTrigger.USER_ABORT,
                    phase_started_at=None,
                    phase_deadline_at=None,
                ),
            )
        ],
    )


def start_session(
    status: SessionStatus,
    *,
    now: datetime,
    duration_plan: PhaseDurationPlan,
) -> SessionCommandOutcome:
    if status is not SessionStatus.CREATED:
        raise InvalidSessionStateError(status)

    phase_started_at = _require_aware_utc(now)
    phase_deadline_at = phase_started_at + timedelta(
        seconds=duration_plan.duration_for(SessionStatus.PREPARATION)
    )
    frozen_duration_plan = duration_plan.to_json()
    return SessionCommandOutcome(
        status=SessionStatus.PREPARATION,
        phase_started_at=phase_started_at,
        phase_deadline_at=phase_deadline_at,
        frozen_duration_plan=frozen_duration_plan,
        events=[
            PendingEvent(
                event_type="session.state_changed",
                payload=_state_changed_payload(
                    previous_status=SessionStatus.CREATED,
                    status=SessionStatus.PREPARATION,
                    trigger=SessionTransitionTrigger.USER_START,
                    phase_started_at=phase_started_at,
                    phase_deadline_at=phase_deadline_at,
                ),
            )
        ],
    )


@dataclass(frozen=True)
class DeadlineReconciliationOutcome:
    status: SessionStatus
    phase_started_at: datetime | None
    phase_deadline_at: datetime | None
    events: list[PendingEvent]


def reconcile_due_transitions(
    *,
    status: SessionStatus,
    phase_started_at: datetime | None,
    phase_deadline_at: datetime | None,
    duration_plan: PhaseDurationPlan | None,
    now: datetime,
) -> DeadlineReconciliationOutcome:
    current_status = status
    current_started_at = phase_started_at
    current_deadline_at = phase_deadline_at
    events: list[PendingEvent] = []
    effective_now = _require_aware_utc(now)

    while current_status in ACTIVE_PHASES:
        if current_started_at is None or current_deadline_at is None:
            raise ValueError("Active session is missing phase timing.")
        if duration_plan is None:
            raise ValueError("Active session is missing a duration plan.")

        current_deadline_at = _require_aware_utc(current_deadline_at)
        if current_deadline_at > effective_now:
            break

        previous_status = current_status
        next_status = NEXT_DEADLINE_STATUS[current_status]
        if next_status is SessionStatus.COMPLETED:
            current_status = next_status
            current_started_at = None
            current_deadline_at = None
        else:
            current_status = next_status
            current_started_at = current_deadline_at
            current_deadline_at = current_started_at + timedelta(
                seconds=duration_plan.duration_for(current_status)
            )

        events.append(
            PendingEvent(
                event_type="session.state_changed",
                payload=_state_changed_payload(
                    previous_status=previous_status,
                    status=current_status,
                    trigger=SessionTransitionTrigger.PHASE_DEADLINE,
                    phase_started_at=current_started_at,
                    phase_deadline_at=current_deadline_at,
                ),
            )
        )

    return DeadlineReconciliationOutcome(
        status=current_status,
        phase_started_at=current_started_at,
        phase_deadline_at=current_deadline_at,
        events=events,
    )


def decide_session_command(
    status: SessionStatus,
    command: SessionCommand,
    *,
    now: datetime,
    duration_plan: PhaseDurationPlan | None,
) -> SessionCommandOutcome:
    if command.schema_version != 1 or command.payload != {}:
        raise ValueError("Unsupported session command.")
    if command.command_type == "session.abort":
        return abort_session(status)
    if command.command_type == "session.start":
        if duration_plan is None:
            raise ValueError("Duration plan is required for session.start.")
        return start_session(status, now=now, duration_plan=duration_plan)
    raise ValueError("Unsupported session command.")
