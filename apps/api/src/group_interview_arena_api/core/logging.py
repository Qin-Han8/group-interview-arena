import json
import logging
import sys
from datetime import UTC, datetime
from typing import cast
from uuid import UUID

from opentelemetry import trace

from group_interview_arena_api.core.config import LogLevel

_APPLICATION_LOGGER_NAME = "group_interview_arena_api"
_STDOUT_HANDLER_NAME = "gia.application.stdout"
_STDERR_HANDLER_NAME = "gia.application.stderr"
_INVALID_EVENT = "logging.record.invalid"
_APPLICATION_HANDLER_NAMES = frozenset({_STDOUT_HANDLER_NAME, _STDERR_HANDLER_NAME})
_OPTIONAL_FIELDS = (
    "request_id",
    "method",
    "route",
    "route_classification",
    "status_code",
    "duration_ms",
    "exception_category",
    "session_id",
    "connection_id",
    "action_id",
    "sequence",
    "generation_request_id",
    "floor_grant_id",
    "participant_id",
)


def _validated_uuid4(value: str | None) -> str | None:
    if value is None:
        return None
    try:
        parsed = UUID(value)
    except ValueError:
        return None
    if parsed.version != 4 or str(parsed) != value:
        return None
    return value


def _active_trace_fields() -> dict[str, str]:
    try:
        span_context = trace.get_current_span().get_span_context()
        if not span_context.is_valid:
            return {}
        return {
            "trace_id": trace.format_trace_id(span_context.trace_id),
            "span_id": trace.format_span_id(span_context.span_id),
        }
    except Exception:
        return {}


class _MaximumLevelFilter(logging.Filter):
    def __init__(self, maximum_level: int) -> None:
        super().__init__()
        self.maximum_level = maximum_level

    def filter(self, record: logging.LogRecord) -> bool:
        return record.levelno <= self.maximum_level


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        event = record.__dict__.get("event")
        if not isinstance(event, str) or not event:
            event = _INVALID_EVENT

        payload: dict[str, object] = {
            "timestamp": datetime.fromtimestamp(record.created, UTC)
            .isoformat(timespec="milliseconds")
            .replace("+00:00", "Z"),
            "level": record.levelname,
            "event": event,
            "logger": record.name,
        }

        for field in _OPTIONAL_FIELDS:
            value = cast(object | None, record.__dict__.get(field))
            if value is not None:
                payload[field] = value

        payload.update(_active_trace_fields())

        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def log_event(
    logger: logging.Logger,
    level: int,
    event: str,
    *,
    request_id: str | None = None,
    method: str | None = None,
    route: str | None = None,
    route_classification: str | None = None,
    status_code: int | None = None,
    duration_ms: float | None = None,
    exception_category: str | None = None,
    session_id: str | None = None,
    connection_id: str | None = None,
    action_id: str | None = None,
    sequence: int | None = None,
    generation_request_id: str | None = None,
    floor_grant_id: str | None = None,
    participant_id: str | None = None,
) -> None:
    extra: dict[str, object] = {"event": event}
    optional_fields: dict[str, object | None] = {
        "request_id": request_id,
        "method": method,
        "route": route,
        "route_classification": route_classification,
        "status_code": status_code,
        "duration_ms": duration_ms,
        "exception_category": exception_category,
        "session_id": _validated_uuid4(session_id),
        "connection_id": _validated_uuid4(connection_id),
        "action_id": _validated_uuid4(action_id),
        "sequence": sequence if isinstance(sequence, int) and sequence > 0 else None,
        "generation_request_id": _validated_uuid4(generation_request_id),
        "floor_grant_id": _validated_uuid4(floor_grant_id),
        "participant_id": _validated_uuid4(participant_id),
    }
    extra.update(
        {field: value for field, value in optional_fields.items() if value is not None}
    )
    try:
        logger.log(level, event, extra=extra)
    except Exception:
        # Application logging must never change request or persistence behavior.
        pass


def configure_logging(log_level: LogLevel) -> None:
    application_logger = logging.getLogger(_APPLICATION_LOGGER_NAME)
    for handler in tuple(application_logger.handlers):
        if handler.name in _APPLICATION_HANDLER_NAMES:
            application_logger.removeHandler(handler)
            handler.close()

    formatter = JsonFormatter()

    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.set_name(_STDOUT_HANDLER_NAME)
    stdout_handler.setLevel(logging.DEBUG)
    stdout_handler.addFilter(_MaximumLevelFilter(logging.WARNING))
    stdout_handler.setFormatter(formatter)

    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_handler.set_name(_STDERR_HANDLER_NAME)
    stderr_handler.setLevel(logging.ERROR)
    stderr_handler.setFormatter(formatter)

    application_logger.addHandler(stdout_handler)
    application_logger.addHandler(stderr_handler)
    application_logger.setLevel(log_level.value)
    application_logger.propagate = False
