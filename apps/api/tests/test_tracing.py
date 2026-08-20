import asyncio
import io
import json
import logging
import threading
from collections.abc import Generator
from contextlib import contextmanager
from importlib.util import find_spec
from typing import Any, cast

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient, Response
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult
from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
    InMemorySpanExporter,
)
from opentelemetry.trace import SpanKind, StatusCode
from pydantic import AnyHttpUrl, SecretStr

import group_interview_arena_api.app as app_module
from group_interview_arena_api.app import create_app
from group_interview_arena_api.core import tracing as tracing_module
from group_interview_arena_api.core.config import (
    DatabaseSettings,
    Environment,
    Settings,
)
from group_interview_arena_api.core.logging import JsonFormatter
from tests.deadline_recovery_test_helpers import disable_deadline_recovery_runtime

APPLICATION_LOGGER_NAME = "group_interview_arena_api"
TEST_DATABASE_URL = (
    "postgresql+psycopg://tracing-user:tracing-password@127.0.0.1:5432/"
    "tracing_not_connected"
)
VALID_TRACE_ID = "0123456789abcdef0123456789abcdef"
VALID_PARENT_SPAN_ID = "0123456789abcdef"
VALID_TRACEPARENT = f"00-{VALID_TRACE_ID}-{VALID_PARENT_SPAN_ID}-01"
UNSUPPORTED_AMBIENT_EXPORTER_AUTH_VARIABLES = (
    "OTEL_EXPORTER_OTLP_HEADERS",
    "OTEL_EXPORTER_OTLP_TRACES_HEADERS",
    "OTEL_EXPORTER_OTLP_CLIENT_KEY",
    "OTEL_EXPORTER_OTLP_TRACES_CLIENT_KEY",
    "OTEL_EXPORTER_OTLP_CLIENT_CERTIFICATE",
    "OTEL_EXPORTER_OTLP_TRACES_CLIENT_CERTIFICATE",
    "OTEL_PYTHON_EXPORTER_OTLP_HTTP_TRACES_CREDENTIAL_PROVIDER",
)


@pytest.fixture(autouse=True)
def _disable_deadline_recovery_for_tracing_tests(  # pyright: ignore[reportUnusedFunction]
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    disable_deadline_recovery_runtime(monkeypatch)


def _require_tracing_api() -> tuple[Any, Any]:
    assert hasattr(tracing_module, "TracingRuntime")
    assert hasattr(tracing_module, "create_tracing_runtime")
    return tracing_module.TracingRuntime, tracing_module.create_tracing_runtime


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
    return [
        cast(dict[str, object], json.loads(line))
        for line in stream.getvalue().splitlines()
    ]


async def _request(
    application: FastAPI,
    method: str,
    path: str,
    *,
    json_body: dict[str, object] | None = None,
    headers: dict[str, str] | None = None,
) -> Response:
    async with AsyncClient(
        transport=ASGITransport(app=application),
        base_url="http://testserver",
    ) as client:
        return await client.request(
            method,
            path,
            json=json_body,
            headers=headers,
        )


def _enabled_settings() -> Settings:
    return Settings(
        environment=Environment.TEST,
        otel_tracing_enabled=True,
        otel_otlp_http_endpoint=AnyHttpUrl("http://localhost:4318/v1/traces"),
    )


def _safe_span_text(span: Any) -> str:
    return repr(
        (
            span.name,
            dict(span.attributes or {}),
            tuple(span.events),
            span.status,
            dict(span.resource.attributes),
        )
    )


def test_project_owned_tracing_module_exists() -> None:
    assert find_spec("group_interview_arena_api.core.tracing") is not None


def test_disabled_runtime_does_not_construct_exporter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, create_tracing_runtime = _require_tracing_api()
    assert app_module.app.state.tracing_runtime.enabled is False
    assert app_module.app.state.tracing_runtime.provider is None

    def fail_if_constructed(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("Disabled tracing constructed an exporter")

    monkeypatch.setattr(
        tracing_module,
        "OTLPSpanExporter",
        fail_if_constructed,
    )
    runtime = create_tracing_runtime(
        Settings(
            environment=Environment.TEST,
            otel_tracing_enabled=False,
            otel_otlp_http_endpoint=AnyHttpUrl("http://localhost:4318/v1/traces"),
        )
    )

    assert runtime.enabled is False
    assert runtime.provider is None
    assert runtime.tracer is None


def test_enabled_runtime_fails_closed_when_otel_sdk_is_ambiently_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, create_tracing_runtime = _require_tracing_api()
    construction_calls: list[str] = []
    monkeypatch.setenv("OTEL_SDK_DISABLED", " TrUe ")

    def fail_exporter_construction(*_args: object, **_kwargs: object) -> None:
        construction_calls.append("exporter")
        raise AssertionError("Exporter construction must not be reached")

    def fail_provider_construction(*_args: object, **_kwargs: object) -> None:
        construction_calls.append("provider")
        raise AssertionError("Provider construction must not be reached")

    monkeypatch.setattr(
        tracing_module,
        "OTLPSpanExporter",
        fail_exporter_construction,
    )
    monkeypatch.setattr(
        tracing_module,
        "TracerProvider",
        fail_provider_construction,
    )

    with pytest.raises(ValueError) as error:
        create_tracing_runtime(_enabled_settings())

    assert str(error.value) == (
        "Ambient OpenTelemetry SDK disablement conflicts with project tracing"
    )
    assert construction_calls == []


def test_project_sampler_ignores_ambient_always_off(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, create_tracing_runtime = _require_tracing_api()
    exporter = InMemorySpanExporter()
    monkeypatch.setenv("OTEL_TRACES_SAMPLER", "always_off")
    monkeypatch.setenv("OTEL_TRACES_SAMPLER_ARG", "0")
    runtime = create_tracing_runtime(_enabled_settings(), span_exporter=exporter)

    with runtime.start_server_span({}, method="GET") as span:
        assert span is not None
        runtime.finish_server_span(
            span,
            method="GET",
            route="/health",
            status_code=200,
            exception_category=None,
        )

    assert runtime.provider is not None
    assert runtime.provider.force_flush(timeout_millis=1000)
    assert len(exporter.get_finished_spans()) == 1
    runtime.shutdown()


@pytest.mark.parametrize(
    "variable_name",
    UNSUPPORTED_AMBIENT_EXPORTER_AUTH_VARIABLES,
)
def test_enabled_runtime_rejects_ambient_exporter_auth_before_construction(
    monkeypatch: pytest.MonkeyPatch,
    variable_name: str,
) -> None:
    _, create_tracing_runtime = _require_tracing_api()
    construction_calls: list[str] = []
    monkeypatch.setenv(variable_name, "ambient-auth-sensitive-sentinel")

    def fail_exporter_construction(*_args: object, **_kwargs: object) -> None:
        construction_calls.append("exporter")
        raise AssertionError("Exporter construction must not be reached")

    def fail_provider_construction(*_args: object, **_kwargs: object) -> None:
        construction_calls.append("provider")
        raise AssertionError("Provider construction must not be reached")

    monkeypatch.setattr(
        tracing_module,
        "OTLPSpanExporter",
        fail_exporter_construction,
    )
    monkeypatch.setattr(
        tracing_module,
        "TracerProvider",
        fail_provider_construction,
    )

    with pytest.raises(ValueError) as error:
        create_tracing_runtime(_enabled_settings())

    assert str(error.value) == (
        "Unsupported ambient OpenTelemetry exporter authentication configuration"
    )
    assert "ambient-auth-sensitive-sentinel" not in str(error.value)
    assert construction_calls == []


def test_disabled_runtime_ignores_ambient_exporter_auth(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, create_tracing_runtime = _require_tracing_api()
    for variable_name in UNSUPPORTED_AMBIENT_EXPORTER_AUTH_VARIABLES:
        monkeypatch.setenv(variable_name, "ambient-auth-sensitive-sentinel")

    def fail_if_constructed(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("Disabled tracing constructed an exporter or provider")

    monkeypatch.setattr(tracing_module, "OTLPSpanExporter", fail_if_constructed)
    monkeypatch.setattr(tracing_module, "TracerProvider", fail_if_constructed)
    runtime = create_tracing_runtime(
        Settings(
            environment=Environment.TEST,
            otel_tracing_enabled=False,
            otel_otlp_http_endpoint=AnyHttpUrl("http://localhost:4318/v1/traces"),
        )
    )

    assert runtime == tracing_module.TracingRuntime(enabled=False)


def test_app_owned_provider_creates_safe_w3c_server_span() -> None:
    _, create_tracing_runtime = _require_tracing_api()
    exporter = InMemorySpanExporter()
    runtime = create_tracing_runtime(_enabled_settings(), span_exporter=exporter)

    with runtime.start_server_span(
        {"traceparent": VALID_TRACEPARENT},
        method="GET",
    ) as span:
        assert span is not None
        runtime.finish_server_span(
            span,
            method="GET",
            route="/resources/{resource_id}",
            status_code=200,
            exception_category=None,
        )

    assert runtime.provider is not None
    assert runtime.provider.force_flush(timeout_millis=1000)
    finished = exporter.get_finished_spans()
    assert len(finished) == 1
    exported = finished[0]
    assert exported.context is not None
    assert exported.kind is SpanKind.SERVER
    assert exported.name == "GET /resources/{resource_id}"
    assert exported.context.trace_id == int(VALID_TRACE_ID, 16)
    assert exported.context.span_id != int(VALID_PARENT_SPAN_ID, 16)
    assert exported.parent is not None
    assert exported.parent.span_id == int(VALID_PARENT_SPAN_ID, 16)
    assert exported.attributes == {
        "http.request.method": "GET",
        "http.route": "/resources/{resource_id}",
        "http.response.status_code": 200,
    }
    assert exported.status.status_code is StatusCode.UNSET
    assert not exported.events
    assert exported.resource.attributes["service.name"] == ("group-interview-arena-api")
    runtime.shutdown()


def test_invalid_traceparent_creates_new_root_without_failure() -> None:
    _, create_tracing_runtime = _require_tracing_api()
    exporter = InMemorySpanExporter()
    runtime = create_tracing_runtime(_enabled_settings(), span_exporter=exporter)

    with runtime.start_server_span(
        {"traceparent": "malformed-sensitive-parent"},
        method="GET",
    ) as span:
        assert span is not None
        runtime.finish_server_span(
            span,
            method="GET",
            route="/health",
            status_code=200,
            exception_category=None,
        )

    assert runtime.provider is not None
    assert runtime.provider.force_flush(timeout_millis=1000)
    exported = exporter.get_finished_spans()[0]
    assert exported.context is not None
    assert exported.parent is None
    assert exported.context.trace_id != 0
    assert "malformed-sensitive-parent" not in _safe_span_text(exported)
    runtime.shutdown()


def test_enabled_request_exports_correlated_span_and_log(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, create_tracing_runtime = _require_tracing_api()
    assert hasattr(app_module, "create_tracing_runtime")
    exporter = InMemorySpanExporter()
    runtimes: list[Any] = []

    def runtime_factory(settings: Settings) -> Any:
        runtime = create_tracing_runtime(settings, span_exporter=exporter)
        runtimes.append(runtime)
        return runtime

    monkeypatch.setattr(app_module, "create_tracing_runtime", runtime_factory)
    application = create_app(
        _enabled_settings(),
        DatabaseSettings(database_url=SecretStr(TEST_DATABASE_URL)),
    )

    async def exercise() -> Response:
        async with application.router.lifespan_context(application):
            return await _request(
                application,
                "GET",
                "/health",
                headers={"traceparent": VALID_TRACEPARENT},
            )

    with _captured_application_logs() as stream:
        response = asyncio.run(exercise())

    assert response.status_code == 200
    assert len(runtimes) == 1
    finished = exporter.get_finished_spans()
    assert len(finished) == 1
    exported = finished[0]
    assert exported.context is not None
    completed = next(
        payload
        for payload in _payloads(stream)
        if payload.get("event") == "http.request.completed"
    )
    assert completed["request_id"] == response.headers["X-Request-ID"]
    assert completed["trace_id"] == f"{exported.context.trace_id:032x}"
    assert completed["span_id"] == f"{exported.context.span_id:016x}"
    assert exported.name == "GET /health"
    assert exported.context.trace_id == int(VALID_TRACE_ID, 16)
    assert not hasattr(application.state, "tracing_runtime")


def test_request_inherits_traceparent_without_accepting_tracestate(
    monkeypatch: pytest.MonkeyPatch,
    capsys: Any,
) -> None:
    _, create_tracing_runtime = _require_tracing_api()
    exporter = InMemorySpanExporter()
    tracestate_sentinel = "tracestate-sensitive-sentinel"

    def runtime_factory(settings: Settings) -> Any:
        return create_tracing_runtime(settings, span_exporter=exporter)

    monkeypatch.setattr(app_module, "create_tracing_runtime", runtime_factory)
    application = create_app(
        _enabled_settings(),
        DatabaseSettings(database_url=SecretStr(TEST_DATABASE_URL)),
    )

    async def exercise() -> Response:
        async with application.router.lifespan_context(application):
            return await _request(
                application,
                "GET",
                "/health",
                headers={
                    "traceparent": VALID_TRACEPARENT,
                    "tracestate": f"vendor={tracestate_sentinel}",
                },
            )

    response = asyncio.run(exercise())
    captured = capsys.readouterr()
    exported = exporter.get_finished_spans()[0]

    assert exported.context is not None
    assert exported.context.trace_id == int(VALID_TRACE_ID, 16)
    assert exported.parent is not None
    assert exported.parent.span_id == int(VALID_PARENT_SPAN_ID, 16)
    assert len(exported.context.trace_state) == 0
    combined = (
        repr(exported.context)
        + _safe_span_text(exported)
        + captured.out
        + captured.err
        + response.text
    )
    assert tracestate_sentinel not in combined


def test_runtime_resource_ignores_ambient_otel_resource_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, create_tracing_runtime = _require_tracing_api()
    exporter = InMemorySpanExporter()
    resource_sentinel = "resource-sensitive-sentinel"
    ambient_service_sentinel = "ambient-service-sentinel"
    project_service_name = "project-owned-api"
    monkeypatch.setenv(
        "OTEL_RESOURCE_ATTRIBUTES",
        f"custom.secret={resource_sentinel}",
    )
    monkeypatch.setenv("OTEL_SERVICE_NAME", ambient_service_sentinel)
    runtime = create_tracing_runtime(
        Settings(
            environment=Environment.TEST,
            otel_tracing_enabled=True,
            otel_service_name=project_service_name,
            otel_otlp_http_endpoint=AnyHttpUrl("http://localhost:4318/v1/traces"),
        ),
        span_exporter=exporter,
    )

    with runtime.start_server_span({}, method="GET") as span:
        assert span is not None
        runtime.finish_server_span(
            span,
            method="GET",
            route="/health",
            status_code=200,
            exception_category=None,
        )

    assert runtime.provider is not None
    assert runtime.provider.force_flush(timeout_millis=1000)
    exported = exporter.get_finished_spans()[0]
    assert exported.resource.attributes == {"service.name": project_service_name}
    safe_span_text = _safe_span_text(exported)
    assert resource_sentinel not in safe_span_text
    assert ambient_service_sentinel not in safe_span_text
    runtime.shutdown()


def test_unmatched_and_exception_paths_do_not_leak_sensitive_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, create_tracing_runtime = _require_tracing_api()
    exporter = InMemorySpanExporter()

    def runtime_factory(settings: Settings) -> Any:
        return create_tracing_runtime(settings, span_exporter=exporter)

    monkeypatch.setattr(app_module, "create_tracing_runtime", runtime_factory)
    application = create_app(
        _enabled_settings(),
        DatabaseSettings(database_url=SecretStr(TEST_DATABASE_URL)),
    )
    sentinels = (
        "query-sensitive-sentinel",
        "body-sensitive-sentinel",
        "header-sensitive-sentinel",
        "cookie-sensitive-sentinel",
        "authorization-sensitive-sentinel",
        "csrf-sensitive-sentinel",
        "dynamic-path-sensitive-sentinel",
        "exception-sensitive-sentinel",
        TEST_DATABASE_URL,
        "unmatched-sensitive-sentinel",
        "baggage-sensitive-sentinel",
    )

    @application.post("/trace-safety/{resource_id}")
    async def trace_failure(  # pyright: ignore[reportUnusedFunction]
        resource_id: str,
        payload: dict[str, object],
    ) -> None:
        del resource_id, payload
        raise RuntimeError(f"{sentinels[7]} {sentinels[8]}")

    async def exercise() -> tuple[Response, Response]:
        async with application.router.lifespan_context(application):
            unmatched = await _request(
                application,
                "GET",
                f"/{sentinels[9]}?secret={sentinels[0]}",
                headers={"X-Arbitrary": sentinels[2]},
            )
            failed = await _request(
                application,
                "POST",
                f"/trace-safety/{sentinels[6]}?secret={sentinels[0]}",
                json_body={"secret": sentinels[1]},
                headers={
                    "X-Arbitrary": sentinels[2],
                    "Cookie": f"gia_session={sentinels[3]}",
                    "Authorization": f"Bearer {sentinels[4]}",
                    "X-GIA-CSRF": sentinels[5],
                    "baggage": f"user.id={sentinels[10]}",
                },
            )
            return unmatched, failed

    with _captured_application_logs() as stream:
        unmatched, failed = asyncio.run(exercise())

    assert unmatched.status_code == 404
    assert failed.status_code == 500
    spans = exporter.get_finished_spans()
    assert len(spans) == 2
    assert spans[0].name == "GET <unmatched>"
    assert "http.route" not in (spans[0].attributes or {})
    assert spans[0].status.status_code is StatusCode.UNSET
    assert spans[1].name == "POST /trace-safety/{resource_id}"
    assert spans[1].status.status_code is StatusCode.ERROR
    assert spans[1].attributes is not None
    assert spans[1].attributes["error.type"] == "unhandled_exception"
    assert all(not span.events for span in spans)

    combined = (
        stream.getvalue()
        + unmatched.text
        + failed.text
        + "".join(_safe_span_text(span) for span in spans)
    )
    assert all(sentinel not in combined for sentinel in sentinels)


class FailingSpanExporter(SpanExporter):
    def export(self, spans: Any) -> SpanExportResult:
        del spans
        return SpanExportResult.FAILURE

    def shutdown(self) -> None:
        return None


def test_export_failure_does_not_break_request_or_shutdown(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, create_tracing_runtime = _require_tracing_api()

    def runtime_factory(settings: Settings) -> Any:
        return create_tracing_runtime(
            settings,
            span_exporter=FailingSpanExporter(),
        )

    monkeypatch.setattr(app_module, "create_tracing_runtime", runtime_factory)
    application = create_app(
        _enabled_settings(),
        DatabaseSettings(database_url=SecretStr(TEST_DATABASE_URL)),
    )

    async def exercise() -> Response:
        async with application.router.lifespan_context(application):
            return await _request(application, "GET", "/health")

    response = asyncio.run(exercise())

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_flush_timeout_emits_only_the_controlled_safe_event(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, create_tracing_runtime = _require_tracing_api()
    runtime = create_tracing_runtime(
        _enabled_settings(),
        span_exporter=InMemorySpanExporter(),
    )
    assert runtime.provider is not None

    def fail_flush(timeout_millis: int = 30_000) -> bool:
        del timeout_millis
        return False

    monkeypatch.setattr(runtime.provider, "force_flush", fail_flush)

    with _captured_application_logs() as stream:
        runtime.shutdown()

    payloads = _payloads(stream)
    failure = next(
        payload
        for payload in payloads
        if payload.get("event") == "telemetry.export.failed"
    )
    assert failure["exception_category"] == "flush_timeout"
    assert set(failure) == {
        "timestamp",
        "level",
        "event",
        "logger",
        "exception_category",
    }


def test_each_app_lifespan_owns_an_independent_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, create_tracing_runtime = _require_tracing_api()
    existing_thread_ids = {thread.ident for thread in threading.enumerate()}
    runtimes: list[Any] = []

    def runtime_factory(settings: Settings) -> Any:
        runtime = create_tracing_runtime(
            settings,
            span_exporter=InMemorySpanExporter(),
        )
        runtimes.append(runtime)
        return runtime

    monkeypatch.setattr(app_module, "create_tracing_runtime", runtime_factory)
    applications = [
        create_app(
            _enabled_settings(),
            DatabaseSettings(database_url=SecretStr(TEST_DATABASE_URL)),
        )
        for _ in range(2)
    ]

    async def run_lifespans() -> None:
        for application in applications:
            async with application.router.lifespan_context(application):
                assert application.state.tracing_runtime.enabled

    asyncio.run(run_lifespans())

    assert len(runtimes) == 2
    assert runtimes[0].provider is not runtimes[1].provider
    assert all(not hasattr(app.state, "tracing_runtime") for app in applications)
    leaked_processor_threads = [
        thread
        for thread in threading.enumerate()
        if thread.ident not in existing_thread_ids
        and thread.name == "OtelBatchSpanRecordProcessor"
    ]
    assert leaked_processor_threads == []


def test_tracing_shutdown_failure_does_not_skip_database_dispose(
    monkeypatch: pytest.MonkeyPatch,
    capsys: Any,
) -> None:
    assert hasattr(app_module, "shutdown_tracing_runtime")
    calls: list[str] = []

    async def failing_shutdown(_runtime: object) -> None:
        calls.append("tracing")
        raise RuntimeError("shutdown-sensitive-sentinel")

    async def record_dispose(_engine: object) -> None:
        calls.append("database")

    monkeypatch.setattr(app_module, "shutdown_tracing_runtime", failing_shutdown)
    monkeypatch.setattr(app_module, "dispose_database_engine", record_dispose)
    application = create_app(
        Settings(environment=Environment.TEST),
        DatabaseSettings(database_url=SecretStr(TEST_DATABASE_URL)),
    )

    async def exercise() -> None:
        async with application.router.lifespan_context(application):
            pass

    asyncio.run(exercise())

    assert calls == ["tracing", "database"]
    captured = capsys.readouterr()
    assert "shutdown-sensitive-sentinel" not in captured.out
    assert "shutdown-sensitive-sentinel" not in captured.err
    failure = next(
        payload
        for payload in (
            cast(dict[str, object], json.loads(line))
            for line in captured.err.splitlines()
        )
        if payload.get("event") == "telemetry.export.failed"
    )
    assert failure["exception_category"] == "shutdown_error"
