import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from time import perf_counter

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import RequestResponseEndpoint
from starlette.responses import Response
from starlette.routing import BaseRoute

from group_interview_arena_api.api.health import router as health_router
from group_interview_arena_api.core.config import DatabaseSettings, Settings
from group_interview_arena_api.core.errors import (
    ApiError,
    api_error_handler,
    http_exception_handler,
    unexpected_exception_handler,
    validation_exception_handler,
)
from group_interview_arena_api.core.logging import configure_logging, log_event
from group_interview_arena_api.core.request_id import (
    create_request_id,
    reset_request_id,
    set_request_id,
)
from group_interview_arena_api.core.tracing import (
    TracingRuntime,
    create_tracing_runtime,
    shutdown_tracing_runtime,
)
from group_interview_arena_api.db.dependencies import (
    DATABASE_SESSION_FACTORY_STATE_KEY,
)
from group_interview_arena_api.db.runtime import (
    create_database_engine,
    create_database_session_factory,
    dispose_database_engine,
)
from group_interview_arena_api.identity.routes import create_auth_router
from group_interview_arena_api.modules.discussion_sessions.realtime import (
    create_realtime_router,
)
from group_interview_arena_api.modules.discussion_sessions.routes import (
    create_discussion_session_router,
)

logger = logging.getLogger(__name__)


def _resolved_route(request: Request) -> tuple[str | None, str]:
    route = request.scope.get("route")
    if isinstance(route, BaseRoute):
        route_template = getattr(route, "path", None)
        if isinstance(route_template, str):
            return route_template, "matched"
    return None, "unmatched"


def create_app(
    settings: Settings | None = None,
    database_settings: DatabaseSettings | None = None,
) -> FastAPI:
    resolved_settings = settings or Settings()
    configure_logging(resolved_settings.log_level)

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncGenerator[None]:
        tracing_runtime = create_tracing_runtime(resolved_settings)
        application.state.tracing_runtime = tracing_runtime
        engine = None
        try:
            resolved_database_settings = (
                database_settings or DatabaseSettings()  # pyright: ignore[reportCallIssue]
            )
            engine = create_database_engine(resolved_database_settings)
            session_factory = create_database_session_factory(engine)
            application.state.database_engine = engine
            setattr(
                application.state,
                DATABASE_SESSION_FACTORY_STATE_KEY,
                session_factory,
            )
            log_event(logger, logging.INFO, "app.startup.completed")
            yield
        finally:
            if hasattr(application.state, DATABASE_SESSION_FACTORY_STATE_KEY):
                delattr(application.state, DATABASE_SESSION_FACTORY_STATE_KEY)
            try:
                await shutdown_tracing_runtime(tracing_runtime)
            except Exception:
                log_event(
                    logger,
                    logging.ERROR,
                    "telemetry.export.failed",
                    exception_category="shutdown_error",
                )
            if engine is not None:
                if hasattr(application.state, "database_engine"):
                    del application.state.database_engine
                await dispose_database_engine(engine)
            if hasattr(application.state, "tracing_runtime"):
                del application.state.tracing_runtime
            log_event(logger, logging.INFO, "app.shutdown.completed")

    application = FastAPI(title="AI 群面训练场 API", lifespan=lifespan)
    application.state.tracing_runtime = TracingRuntime(enabled=False)
    application.include_router(health_router)
    application.include_router(create_auth_router(resolved_settings))
    application.include_router(create_discussion_session_router(resolved_settings))
    application.include_router(create_realtime_router(resolved_settings))

    application.add_exception_handler(ApiError, api_error_handler)
    application.add_exception_handler(StarletteHTTPException, http_exception_handler)
    application.add_exception_handler(
        RequestValidationError, validation_exception_handler
    )

    async def _request_context(
        request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        request_id = create_request_id()
        token = set_request_id(request_id)
        started_at = perf_counter()

        try:
            candidate = getattr(request.app.state, "tracing_runtime", None)
            tracing_runtime = (
                candidate
                if isinstance(candidate, TracingRuntime)
                else TracingRuntime(enabled=False)
            )
            with tracing_runtime.start_server_span(
                request.headers,
                method=request.method,
            ) as span:
                event = "http.request.completed"
                level = logging.INFO
                exception_category = None
                try:
                    response = await call_next(request)
                except Exception as exception:
                    response = await unexpected_exception_handler(request, exception)
                    event = "http.request.failed"
                    level = logging.ERROR
                    exception_category = "unhandled_exception"

                duration_ms = round((perf_counter() - started_at) * 1000, 3)
                response.headers["X-Request-ID"] = request_id
                route, route_classification = _resolved_route(request)
                tracing_runtime.finish_server_span(
                    span,
                    method=request.method,
                    route=route,
                    status_code=response.status_code,
                    exception_category=exception_category,
                )
                log_event(
                    logger,
                    level,
                    event,
                    request_id=request_id,
                    method=request.method,
                    route=route,
                    route_classification=route_classification,
                    status_code=response.status_code,
                    duration_ms=duration_ms,
                    exception_category=exception_category,
                )
                return response
        finally:
            reset_request_id(token)

    application.middleware("http")(_request_context)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=list(resolved_settings.cors_origins),
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type", "X-GIA-CSRF"],
        expose_headers=["X-Request-ID"],
    )

    return application


app = create_app()
