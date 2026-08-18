from datetime import datetime
from typing import Literal, Self

from pydantic import (
    UUID4,
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from group_interview_arena_api.modules.discussion_sessions.domain import SessionStatus


def _require_aware(value: datetime) -> datetime:
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


class SessionSnapshotResponse(_ClosedModel):
    id: UUID4
    question_version_id: UUID4 | None
    status: SessionStatus
    created_at: datetime
    updated_at: datetime
    last_sequence: int = Field(ge=0)

    _validate_timestamps = field_validator("created_at", "updated_at")(_require_aware)


class FormalEventEnvelope(_ClosedModel):
    schema_version: Literal[1]
    type: Literal["session.created", "session.state_changed"]
    session_id: UUID4
    sequence: int = Field(gt=0)
    occurred_at: datetime
    action_id: UUID4 | None
    payload: dict[str, object]

    @model_validator(mode="after")
    def validate_event_shape(self) -> Self:
        if self.type == "session.created":
            if self.action_id is not None or self.payload != {"status": "CREATED"}:
                raise ValueError("Invalid session.created event.")
        elif self.action_id is None or self.payload != {
            "previous_status": "CREATED",
            "status": "ABORTED_USER",
        }:
            raise ValueError("Invalid session.state_changed event.")
        return self

    _validate_timestamp = field_validator("occurred_at")(_require_aware)


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
