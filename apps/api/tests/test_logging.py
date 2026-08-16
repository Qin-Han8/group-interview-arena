import asyncio
import hashlib
import io
import json
import logging
import re
from collections.abc import Generator
from contextlib import contextmanager
from datetime import UTC, datetime
from typing import Any, cast
from uuid import uuid4

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient, Response
from opentelemetry import trace
from pydantic import SecretStr

from group_interview_arena_api.app import create_app
from group_interview_arena_api.core.config import (
    DatabaseSettings,
    Environment,
    LogLevel,
    Settings,
)
from group_interview_arena_api.core.logging import JsonFormatter, log_event

APPLICATION_LOGGER_NAME = "group_interview_arena_api"
TEST_DATABASE_URL = (
    "postgresql+psycopg://logging-user:logging-password@127.0.0.1:5432/"
    "logging_not_connected"
)


async def _request(
    application: FastAPI,
    method: str,
    path: str,
    *,
    json_body: dict[str, object] | None = None,
    headers: dict[str, str] | None = None,
) -> Response:
    async with AsyncClient(
        transport=ASGITransport(app=application), base_url="http://testserver"
    ) as client:
        return await client.request(
            method,
            path,
            json=json_body,
            headers=headers,
        )


@contextmanager
def _captured_application_logs() -> Generator[io.StringIO]:
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JsonFormatter())
    application_logger = logging.getLogger(APPLICATION_LOGGER_NAME)
    application_logger.addHandler(handler)
    try:
        yield stream
    finally:
        application_logger.removeHandler(handler)
        handler.close()


def _payloads(stream: io.StringIO) -> list[dict[str, object]]:
    lines = stream.getvalue().splitlines()
    assert lines
    return [cast(dict[str, object], json.loads(line)) for line in lines]


def _events(payloads: list[dict[str, object]], event: str) -> list[dict[str, object]]:
    return [payload for payload in payloads if payload.get("event") == event]


def _assert_values_absent(text: str, values: tuple[str, ...]) -> None:
    if any(value in text for value in values):
        raise AssertionError("Sensitive or attacker-controlled sentinel leaked")


def test_request_log_is_single_line_json_with_resolved_route_template() -> None:
    application = create_app(Settings(environment=Environment.TEST))

    @application.get("/resources/{resource_id}")
    async def resource(  # pyright: ignore[reportUnusedFunction]
        resource_id: str,
    ) -> dict[str, str]:
        return {"id": resource_id}

    raw_identifier = "private-route-identifier"
    query_sentinel = "private-query-value"
    with _captured_application_logs() as stream:
        response = asyncio.run(
            _request(
                application,
                "GET",
                f"/resources/{raw_identifier}?search={query_sentinel}",
            )
        )

    payloads = _payloads(stream)
    completed = _events(payloads, "http.request.completed")
    assert len(completed) == 1
    payload = completed[0]

    assert response.status_code == 200
    assert payload["request_id"] == response.headers["X-Request-ID"]
    assert payload["method"] == "GET"
    assert payload["route"] == "/resources/{resource_id}"
    assert payload["route_classification"] == "matched"
    assert payload["status_code"] == 200
    assert "trace_id" not in payload
    assert "span_id" not in payload
    assert isinstance(payload["duration_ms"], (int, float))
    assert cast(float, payload["duration_ms"]) >= 0
    assert payload["level"] == "INFO"
    assert payload["logger"] == "group_interview_arena_api.app"

    timestamp = cast(str, payload["timestamp"])
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z", timestamp)
    assert datetime.fromisoformat(timestamp.replace("Z", "+00:00")).tzinfo is UTC
    assert len(stream.getvalue().splitlines()) == len(payloads)
    _assert_values_absent(stream.getvalue(), (raw_identifier, query_sentinel))


def test_unmatched_request_uses_fixed_classification_without_path_derivatives() -> None:
    application = create_app(Settings(environment=Environment.TEST))
    raw_segment = "attacker-controlled-unmatched-segment"
    query_sentinel = "unmatched-query-value"
    raw_path = f"/{raw_segment}"
    path_hash = hashlib.sha256(raw_path.encode()).hexdigest()

    with _captured_application_logs() as stream:
        response = asyncio.run(
            _request(application, "GET", f"{raw_path}?lookup={query_sentinel}")
        )

    payloads = _payloads(stream)
    completed = _events(payloads, "http.request.completed")
    assert len(completed) == 1
    payload = completed[0]
    error = cast(dict[str, object], response.json()["error"])

    assert response.status_code == 404
    assert payload["status_code"] == 404
    assert payload["route_classification"] == "unmatched"
    assert "route" not in payload
    assert payload["request_id"] == response.headers["X-Request-ID"]
    assert payload["request_id"] == error["request_id"]
    _assert_values_absent(
        stream.getvalue(),
        (raw_segment, raw_segment[:12], query_sentinel, path_hash, path_hash[:12]),
    )


def test_handled_validation_response_is_completed_not_failed() -> None:
    application = create_app(Settings(environment=Environment.TEST))

    @application.get("/numbers/{value}")
    async def number(  # pyright: ignore[reportUnusedFunction]
        value: int,
    ) -> dict[str, int]:
        return {"value": value}

    with _captured_application_logs() as stream:
        response = asyncio.run(_request(application, "GET", "/numbers/not-a-number"))

    payloads = _payloads(stream)
    completed = _events(payloads, "http.request.completed")
    assert response.status_code == 422
    assert len(completed) == 1
    assert completed[0]["route"] == "/numbers/{value}"
    assert completed[0]["route_classification"] == "matched"
    assert not _events(payloads, "http.request.failed")


def test_unhandled_failure_is_safe_correlated_and_not_double_logged() -> None:
    application = create_app(Settings(environment=Environment.TEST))
    sentinels = (
        "body-password-sentinel",
        "raw-session-token-sentinel",
        "cookie-sentinel",
        "authorization-sentinel",
        "csrf-header-sentinel",
        "query-sentinel",
        "exception-message-sentinel",
        TEST_DATABASE_URL,
        "dynamic-path-sentinel",
    )

    @application.post("/safety/{resource_id}")
    async def failure(  # pyright: ignore[reportUnusedFunction]
        resource_id: str, payload: dict[str, object]
    ) -> None:
        del resource_id, payload
        raise RuntimeError(f"{sentinels[6]} {sentinels[7]}")

    with _captured_application_logs() as stream:
        response = asyncio.run(
            _request(
                application,
                "POST",
                f"/safety/{sentinels[8]}?secret={sentinels[5]}",
                json_body={"password": sentinels[0], "session": sentinels[1]},
                headers={
                    "Cookie": f"gia_session={sentinels[2]}",
                    "Authorization": f"Bearer {sentinels[3]}",
                    "X-GIA-CSRF": sentinels[4],
                },
            )
        )

    payloads = _payloads(stream)
    failed = _events(payloads, "http.request.failed")
    assert len(failed) == 1
    payload = failed[0]
    error = cast(dict[str, object], response.json()["error"])

    assert response.status_code == 500
    assert payload["request_id"] == response.headers["X-Request-ID"]
    assert payload["request_id"] == error["request_id"]
    assert payload["route"] == "/safety/{resource_id}"
    assert payload["route_classification"] == "matched"
    assert payload["status_code"] == 500
    assert payload["exception_category"] == "unhandled_exception"
    assert payload["level"] == "ERROR"
    assert not _events(payloads, "http.request.completed")
    assert "exception" not in payload
    _assert_values_absent(stream.getvalue(), sentinels)
    _assert_values_absent(response.text, sentinels)


def test_lifespan_emits_safe_startup_and_shutdown_events() -> None:
    application = create_app(
        Settings(environment=Environment.TEST),
        DatabaseSettings(database_url=SecretStr(TEST_DATABASE_URL)),
    )

    async def run_lifespan() -> None:
        async with application.router.lifespan_context(application):
            assert hasattr(application.state, "database_engine")

    with _captured_application_logs() as stream:
        asyncio.run(run_lifespan())

    payloads = _payloads(stream)
    assert len(_events(payloads, "app.startup.completed")) == 1
    assert len(_events(payloads, "app.shutdown.completed")) == 1
    assert not hasattr(application.state, "database_engine")
    _assert_values_absent(stream.getvalue(), (TEST_DATABASE_URL, "logging-password"))


def test_logging_configuration_splits_levels_without_mutating_root(
    capsys: Any,
) -> None:
    root_logger = logging.getLogger()
    root_handlers_before = tuple(root_logger.handlers)
    create_app(Settings(environment=Environment.TEST, log_level=LogLevel.DEBUG))
    create_app(Settings(environment=Environment.TEST, log_level=LogLevel.DEBUG))
    assert tuple(root_logger.handlers) == root_handlers_before

    application_logger = logging.getLogger(APPLICATION_LOGGER_NAME)
    owned_handlers = {
        handler.name for handler in application_logger.handlers if handler.name
    }
    assert {"gia.application.stdout", "gia.application.stderr"} <= owned_handlers
    assert (
        len(
            [
                handler
                for handler in application_logger.handlers
                if handler.name in {"gia.application.stdout", "gia.application.stderr"}
            ]
        )
        == 2
    )

    capsys.readouterr()
    test_logger = logging.getLogger(f"{APPLICATION_LOGGER_NAME}.level_test")
    for level in (
        logging.DEBUG,
        logging.INFO,
        logging.WARNING,
        logging.ERROR,
        logging.CRITICAL,
    ):
        test_logger.log(
            level,
            "logging.level.test",
            extra={"event": "logging.level.test"},
        )
    captured = capsys.readouterr()
    stdout_payloads = [json.loads(line) for line in captured.out.splitlines()]
    stderr_payloads = [json.loads(line) for line in captured.err.splitlines()]

    assert [payload["level"] for payload in stdout_payloads] == [
        "DEBUG",
        "INFO",
        "WARNING",
    ]
    assert [payload["level"] for payload in stderr_payloads] == [
        "ERROR",
        "CRITICAL",
    ]


def test_missing_or_malformed_event_uses_safe_json_fallback(capsys: Any) -> None:
    create_app(Settings(environment=Environment.TEST))
    logger = logging.getLogger(f"{APPLICATION_LOGGER_NAME}.invalid_record_test")
    sentinels = (
        "missing-event-message-sentinel",
        "none-event-message-sentinel",
        "numeric-event-message-sentinel",
        "empty-event-message-sentinel",
    )

    capsys.readouterr()
    logger.warning(sentinels[0])
    logger.warning(sentinels[1], extra={"event": None})
    logger.warning(sentinels[2], extra={"event": 7})
    logger.warning(sentinels[3], extra={"event": ""})
    captured = capsys.readouterr()
    combined_output = captured.out + captured.err

    if "--- Logging error ---" in combined_output:
        raise AssertionError("Formatter diagnostic escaped structured logging")
    _assert_values_absent(combined_output, sentinels)
    if captured.err:
        raise AssertionError("Warning-level fallback unexpectedly wrote to stderr")

    lines = captured.out.splitlines()
    assert len(lines) == 4
    payloads = [cast(dict[str, object], json.loads(line)) for line in lines]
    assert all(payload["event"] == "logging.record.invalid" for payload in payloads)
    assert all(payload["level"] == "WARNING" for payload in payloads)
    assert all(payload["logger"] == logger.name for payload in payloads)
    assert all(
        set(payload) == {"timestamp", "level", "event", "logger"}
        for payload in payloads
    )


def test_trace_fields_are_omitted_without_active_span_even_if_record_supplies_values() -> (
    None
):
    logger = logging.getLogger(f"{APPLICATION_LOGGER_NAME}.format_test")
    without_trace = logger.makeRecord(
        logger.name,
        logging.INFO,
        __file__,
        1,
        "http.request.completed",
        (),
        None,
        extra={"event": "http.request.completed"},
    )
    with_trace = logger.makeRecord(
        logger.name,
        logging.INFO,
        __file__,
        1,
        "http.request.completed",
        (),
        None,
        extra={
            "event": "http.request.completed",
            "trace_id": "0123456789abcdef0123456789abcdef",
            "span_id": "0123456789abcdef",
        },
    )

    without_payload = cast(
        dict[str, object], json.loads(JsonFormatter().format(without_trace))
    )
    with_payload = cast(
        dict[str, object], json.loads(JsonFormatter().format(with_trace))
    )
    assert "trace_id" not in without_payload
    assert "span_id" not in without_payload
    assert "trace_id" not in with_payload
    assert "span_id" not in with_payload


def test_trace_context_lookup_failure_keeps_safe_json_fallback(
    monkeypatch: Any,
) -> None:
    sentinel = "trace-lookup-message-sentinel"

    def fail_lookup() -> None:
        raise RuntimeError(sentinel)

    monkeypatch.setattr(trace, "get_current_span", fail_lookup)
    logger = logging.getLogger(f"{APPLICATION_LOGGER_NAME}.trace_lookup_test")
    record = logger.makeRecord(
        logger.name,
        logging.WARNING,
        __file__,
        1,
        sentinel,
        (),
        None,
    )

    encoded = JsonFormatter().format(record)
    payload = cast(dict[str, object], json.loads(encoded))

    assert payload["event"] == "logging.record.invalid"
    assert set(payload) == {"timestamp", "level", "event", "logger"}
    assert sentinel not in encoded


class FailingHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        del record
        raise RuntimeError("test logging handler failure")


def test_logging_handler_failure_does_not_break_request_handling() -> None:
    application = create_app(Settings(environment=Environment.TEST))
    application_logger = logging.getLogger(APPLICATION_LOGGER_NAME)
    handler = FailingHandler()
    application_logger.addHandler(handler)
    try:
        response = asyncio.run(_request(application, "GET", "/health"))
    finally:
        application_logger.removeHandler(handler)

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_realtime_correlation_fields_allow_only_validated_uuid4_and_sequence() -> None:
    logger = logging.getLogger(f"{APPLICATION_LOGGER_NAME}.realtime_test")
    session_id = str(uuid4())
    connection_id = str(uuid4())
    action_id = str(uuid4())

    with _captured_application_logs() as stream:
        log_event(
            logger,
            logging.INFO,
            "realtime.command.completed",
            session_id=session_id,
            connection_id=connection_id,
            action_id=action_id,
            sequence=2,
        )
        log_event(
            logger,
            logging.WARNING,
            "realtime.command.rejected",
            session_id="session-payload-sentinel",
            connection_id="connection-cookie-sentinel",
            action_id="action-origin-sentinel",
            sequence=-1,
        )

    payloads = _payloads(stream)
    assert payloads[0]["session_id"] == session_id
    assert payloads[0]["connection_id"] == connection_id
    assert payloads[0]["action_id"] == action_id
    assert payloads[0]["sequence"] == 2
    assert set(payloads[1]) == {"timestamp", "level", "event", "logger"}
    _assert_values_absent(
        stream.getvalue(),
        (
            "session-payload-sentinel",
            "connection-cookie-sentinel",
            "action-origin-sentinel",
        ),
    )
