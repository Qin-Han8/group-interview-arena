from datetime import datetime
from typing import Literal, Self
from uuid import UUID

from pydantic import (
    UUID4,
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from group_interview_arena_api.modules.discussion_sessions.domain import SessionStatus
from group_interview_arena_api.modules.floor_control.domain import (
    FLOOR_ENABLED_PHASES,
    FloorInterventionKind,
    FloorPolicyReason,
    FloorReleaseReason,
    ParticipantActorKind,
)


def _require_aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Realtime timestamps must be timezone-aware.")
    return value


class _ClosedModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class EmptyPayload(_ClosedModel):
    pass


class SessionCreateRequest(_ClosedModel):
    question_version_id: UUID4


class SessionAbortCommand(_ClosedModel):
    schema_version: Literal[1]
    type: Literal["session.abort"]
    session_id: UUID4
    action_id: UUID4
    payload: EmptyPayload

    def semantic_payload(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "type": self.type,
            "payload": self.payload.model_dump(mode="json"),
        }


class SessionStartCommand(_ClosedModel):
    schema_version: Literal[1]
    type: Literal["session.start"]
    session_id: UUID4
    action_id: UUID4
    payload: EmptyPayload

    def semantic_payload(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "type": self.type,
            "payload": self.payload.model_dump(mode="json"),
        }


type RealtimeSessionCommand = SessionAbortCommand | SessionStartCommand


class SessionStartRequest(_ClosedModel):
    action_id: UUID4


class FloorParticipantResponse(_ClosedModel):
    participant_id: UUID4
    actor_kind: ParticipantActorKind
    seat_order: int = Field(gt=0)


class CurrentFloorGrantResponse(_ClosedModel):
    grant_id: UUID4
    participant_id: UUID4
    phase: SessionStatus
    reason_code: FloorPolicyReason
    granted_at: datetime

    @model_validator(mode="after")
    def validate_phase(self) -> Self:
        if self.phase not in FLOOR_ENABLED_PHASES:
            raise ValueError("Current floor requires a floor-enabled phase.")
        return self

    _validate_timestamp = field_validator("granted_at")(_require_aware)


class FloorLifecycleResponse(_ClosedModel):
    type: Literal[
        "floor.granted",
        "floor.released",
        "floor.intervention_requested",
    ]
    sequence: int = Field(gt=0)
    occurred_at: datetime
    phase: SessionStatus
    reason_code: FloorPolicyReason | FloorReleaseReason
    grant_id: UUID4 | None = None
    participant_id: UUID4 | None = None
    intervention_id: UUID4 | None = None
    intervention_kind: FloorInterventionKind | None = None

    @model_validator(mode="after")
    def validate_shape(self) -> Self:
        if self.phase not in FLOOR_ENABLED_PHASES:
            raise ValueError("Floor lifecycle requires a floor-enabled phase.")
        if self.type == "floor.granted":
            if (
                self.grant_id is None
                or self.participant_id is None
                or not isinstance(self.reason_code, FloorPolicyReason)
                or self.intervention_id is not None
                or self.intervention_kind is not None
            ):
                raise ValueError("Invalid granted floor projection.")
        elif self.type == "floor.released":
            if (
                self.grant_id is None
                or self.participant_id is None
                or not isinstance(self.reason_code, FloorReleaseReason)
                or self.intervention_id is not None
                or self.intervention_kind is not None
            ):
                raise ValueError("Invalid released floor projection.")
        elif (
            self.grant_id is not None
            or self.participant_id is not None
            or self.intervention_id is None
            or self.intervention_kind is None
            or not isinstance(self.reason_code, FloorPolicyReason)
        ):
            raise ValueError("Invalid intervention floor projection.")
        return self

    _validate_timestamp = field_validator("occurred_at")(_require_aware)


class FloorSnapshotResponse(_ClosedModel):
    participants: list[FloorParticipantResponse]
    current_grant: CurrentFloorGrantResponse | None
    latest_event: FloorLifecycleResponse | None


class SessionSnapshotResponse(_ClosedModel):
    id: UUID4
    question_version_id: UUID4 | None
    status: SessionStatus
    phase_started_at: datetime | None
    phase_deadline_at: datetime | None
    server_now: datetime
    created_at: datetime
    updated_at: datetime
    last_sequence: int = Field(ge=0)
    floor: FloorSnapshotResponse

    _validate_timestamps = field_validator(
        "phase_started_at",
        "phase_deadline_at",
        "server_now",
        "created_at",
        "updated_at",
    )(_require_aware)


class FormalEventEnvelope(_ClosedModel):
    schema_version: Literal[1, 2]
    type: Literal[
        "session.created",
        "session.state_changed",
        "floor.granted",
        "floor.released",
        "floor.intervention_requested",
    ]
    session_id: UUID4
    sequence: int = Field(gt=0)
    occurred_at: datetime
    action_id: UUID4 | None
    payload: dict[str, object]

    @model_validator(mode="after")
    def validate_event_shape(self) -> Self:
        if self.type.startswith("floor."):
            self._validate_floor_event()
        elif self.type == "session.created":
            if (
                self.schema_version != 1
                or self.action_id is not None
                or self.payload != {"status": "CREATED"}
            ):
                raise ValueError("Invalid session.created event.")
        elif self.schema_version == 1:
            if self.action_id is None or self.payload != {
                "previous_status": "CREATED",
                "status": "ABORTED_USER",
            }:
                raise ValueError("Invalid historical session.state_changed event.")
        else:
            if set(self.payload) != {
                "previous_status",
                "status",
                "trigger",
                "phase_started_at",
                "phase_deadline_at",
            }:
                raise ValueError("Invalid session.state_changed v2 payload.")
            previous_status = SessionStatus(str(self.payload["previous_status"]))
            status = SessionStatus(str(self.payload["status"]))
            trigger = self.payload["trigger"]
            if trigger not in {"USER_START", "USER_ABORT", "PHASE_DEADLINE"}:
                raise ValueError("Invalid session.state_changed v2 trigger.")
            if trigger in {"USER_START", "USER_ABORT"} and self.action_id is None:
                raise ValueError("User transition events require an action id.")
            if trigger == "PHASE_DEADLINE" and self.action_id is not None:
                raise ValueError("Deadline transition events must be system events.")
            if status in {SessionStatus.COMPLETED, SessionStatus.ABORTED_USER}:
                if (
                    self.payload["phase_started_at"] is not None
                    or self.payload["phase_deadline_at"] is not None
                ):
                    raise ValueError("Terminal events must not carry current timing.")
            elif not isinstance(
                self.payload["phase_started_at"], str
            ) or not isinstance(self.payload["phase_deadline_at"], str):
                raise ValueError("Active phase events require current timing.")
            if previous_status is status:
                raise ValueError("State change must change status.")
        return self

    def _validate_floor_event(self) -> None:
        if self.schema_version != 1:
            raise ValueError("Floor events require schema version 1.")
        if self.type == "floor.granted":
            if self.action_id is None or set(self.payload) != {
                "grant_id",
                "decision_id",
                "participant_id",
                "phase",
                "opportunity_id",
                "reason_code",
                "policy_version",
            }:
                raise ValueError("Invalid floor.granted event.")
            _require_uuid4(self.payload["grant_id"])
            _require_uuid4(self.payload["decision_id"])
            _require_uuid4(self.payload["participant_id"])
            opportunity_id = self.payload["opportunity_id"]
            if opportunity_id is not None:
                _require_uuid4(opportunity_id)
            FloorPolicyReason(str(self.payload["reason_code"]))
            _require_policy_version(self.payload["policy_version"])
        elif self.type == "floor.released":
            if set(self.payload) != {
                "grant_id",
                "participant_id",
                "phase",
                "reason_code",
            }:
                raise ValueError("Invalid floor.released event.")
            _require_uuid4(self.payload["grant_id"])
            _require_uuid4(self.payload["participant_id"])
            FloorReleaseReason(str(self.payload["reason_code"]))
        else:
            if self.action_id is None or set(self.payload) != {
                "intervention_id",
                "decision_id",
                "phase",
                "intervention_kind",
                "reason_code",
                "policy_version",
            }:
                raise ValueError("Invalid floor.intervention_requested event.")
            _require_uuid4(self.payload["intervention_id"])
            _require_uuid4(self.payload["decision_id"])
            FloorInterventionKind(str(self.payload["intervention_kind"]))
            FloorPolicyReason(str(self.payload["reason_code"]))
            _require_policy_version(self.payload["policy_version"])
        if SessionStatus(str(self.payload["phase"])) not in FLOOR_ENABLED_PHASES:
            raise ValueError("Floor event phase is not floor-enabled.")

    _validate_timestamp = field_validator("occurred_at")(_require_aware)


def _require_uuid4(value: object) -> UUID:
    parsed = UUID(str(value))
    if parsed.version != 4:
        raise ValueError("Floor event identities must be UUIDv4.")
    return parsed


def _require_policy_version(value: object) -> str:
    parsed = str(value)
    if not parsed or len(parsed) > 64:
        raise ValueError("Floor policy version is invalid.")
    return parsed


RealtimeErrorCode = Literal[
    "INVALID_SESSION_STATE",
    "ACTION_ID_CONFLICT",
    "PROTOCOL_ERROR",
    "SEQUENCE_AHEAD",
    "INTERNAL_ERROR",
]


class WsErrorDetail(_ClosedModel):
    code: RealtimeErrorCode
    message: str
    request_id: UUID4


class WsErrorEnvelope(_ClosedModel):
    schema_version: Literal[1]
    type: Literal["error"]
    session_id: UUID4
    action_id: UUID4 | None
    occurred_at: datetime
    error: WsErrorDetail

    _validate_timestamp = field_validator("occurred_at")(_require_aware)
