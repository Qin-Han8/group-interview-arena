"""Application-owned OpenTelemetry tracing runtime."""

import asyncio
import logging
from collections.abc import Generator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from os import environ

from opentelemetry.context import Context
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.environment_variables import (
    OTEL_EXPORTER_OTLP_CLIENT_CERTIFICATE,
    OTEL_EXPORTER_OTLP_CLIENT_KEY,
    OTEL_EXPORTER_OTLP_HEADERS,
    OTEL_EXPORTER_OTLP_TRACES_CLIENT_CERTIFICATE,
    OTEL_EXPORTER_OTLP_TRACES_CLIENT_KEY,
    OTEL_EXPORTER_OTLP_TRACES_HEADERS,
    OTEL_SDK_DISABLED,
)
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, SpanExporter
from opentelemetry.sdk.trace.sampling import ALWAYS_ON, ParentBased
from opentelemetry.trace import Span, SpanKind, Status, StatusCode, Tracer
from opentelemetry.trace.propagation.tracecontext import (
    TraceContextTextMapPropagator,
)

from group_interview_arena_api.core.config import Settings
from group_interview_arena_api.core.logging import log_event

logger = logging.getLogger(__name__)

_INSTRUMENTATION_SCOPE_NAME = "group_interview_arena_api"
_UNMATCHED_ROUTE = "<unmatched>"
_EXPORT_TIMEOUT_MILLIS = 5_000
_EXPORT_TIMEOUT_SECONDS = _EXPORT_TIMEOUT_MILLIS / 1_000
_TRACE_CONTEXT_PROPAGATOR = TraceContextTextMapPropagator()
_OTEL_HTTP_TRACES_CREDENTIAL_PROVIDER = (
    "OTEL_PYTHON_EXPORTER_OTLP_HTTP_TRACES_CREDENTIAL_PROVIDER"
)
_UNSUPPORTED_AMBIENT_EXPORTER_AUTH_VARIABLES = (
    OTEL_EXPORTER_OTLP_HEADERS,
    OTEL_EXPORTER_OTLP_TRACES_HEADERS,
    OTEL_EXPORTER_OTLP_CLIENT_KEY,
    OTEL_EXPORTER_OTLP_TRACES_CLIENT_KEY,
    OTEL_EXPORTER_OTLP_CLIENT_CERTIFICATE,
    OTEL_EXPORTER_OTLP_TRACES_CLIENT_CERTIFICATE,
    _OTEL_HTTP_TRACES_CREDENTIAL_PROVIDER,
)


@dataclass(frozen=True)
class TracingRuntime:
    enabled: bool
    provider: TracerProvider | None = None
    tracer: Tracer | None = None

    @contextmanager
    def start_server_span(
        self,
        carrier: Mapping[str, str],
        *,
        method: str,
    ) -> Generator[Span | None]:
        if self.tracer is None:
            yield None
            return

        try:
            traceparent = carrier.get("traceparent")
            trace_carrier = (
                {"traceparent": traceparent} if traceparent is not None else {}
            )
            parent_context = _TRACE_CONTEXT_PROPAGATOR.extract(trace_carrier)
        except Exception:
            parent_context = Context()

        provisional_name = f"{method} {_UNMATCHED_ROUTE}"
        with self.tracer.start_as_current_span(
            provisional_name,
            context=parent_context,
            kind=SpanKind.SERVER,
            attributes={"http.request.method": method},
            record_exception=False,
            set_status_on_exception=False,
        ) as span:
            yield span

    def finish_server_span(
        self,
        span: Span | None,
        *,
        method: str,
        route: str | None,
        status_code: int,
        exception_category: str | None,
    ) -> None:
        if span is None:
            return

        span.update_name(f"{method} {route or _UNMATCHED_ROUTE}")
        if route is not None:
            span.set_attribute("http.route", route)
        span.set_attribute("http.response.status_code", status_code)
        if exception_category is not None:
            span.set_attribute("error.type", exception_category)
        if status_code >= 500:
            span.set_status(Status(StatusCode.ERROR))

    def shutdown(self) -> None:
        if self.provider is None:
            return

        try:
            flushed = self.provider.force_flush(timeout_millis=_EXPORT_TIMEOUT_MILLIS)
            if not flushed:
                log_event(
                    logger,
                    logging.ERROR,
                    "telemetry.export.failed",
                    exception_category="flush_timeout",
                )
        except Exception:
            log_event(
                logger,
                logging.ERROR,
                "telemetry.export.failed",
                exception_category="flush_error",
            )

        try:
            self.provider.shutdown()
        except Exception:
            log_event(
                logger,
                logging.ERROR,
                "telemetry.export.failed",
                exception_category="shutdown_error",
            )


def create_tracing_runtime(
    settings: Settings,
    *,
    span_exporter: SpanExporter | None = None,
) -> TracingRuntime:
    if not settings.otel_tracing_enabled:
        return TracingRuntime(enabled=False)

    _validate_enabled_ambient_environment()

    endpoint = settings.otel_otlp_http_endpoint
    if endpoint is None:
        raise ValueError("Tracing requires an OTLP HTTP endpoint")

    exporter = span_exporter or OTLPSpanExporter(
        endpoint=str(endpoint),
        timeout=_EXPORT_TIMEOUT_SECONDS,
    )
    provider = TracerProvider(
        sampler=ParentBased(ALWAYS_ON),
        resource=Resource(attributes={"service.name": settings.otel_service_name}),
    )
    provider.add_span_processor(
        BatchSpanProcessor(
            exporter,
            export_timeout_millis=_EXPORT_TIMEOUT_MILLIS,
        )
    )
    tracer = provider.get_tracer(_INSTRUMENTATION_SCOPE_NAME)
    return TracingRuntime(enabled=True, provider=provider, tracer=tracer)


def _validate_enabled_ambient_environment() -> None:
    sdk_disabled = environ.get(OTEL_SDK_DISABLED, "")
    if sdk_disabled.lower().strip() == "true":
        raise ValueError(
            "Ambient OpenTelemetry SDK disablement conflicts with project tracing"
        )

    if any(
        variable_name in environ
        for variable_name in _UNSUPPORTED_AMBIENT_EXPORTER_AUTH_VARIABLES
    ):
        raise ValueError(
            "Unsupported ambient OpenTelemetry exporter authentication configuration"
        )


async def shutdown_tracing_runtime(runtime: TracingRuntime) -> None:
    await asyncio.to_thread(runtime.shutdown)
