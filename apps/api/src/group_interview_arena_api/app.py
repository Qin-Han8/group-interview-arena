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

from group_interview_arena_api.api.health import router as health_router
from group_interview_arena_api.core.config import DatabaseSettings, Settings
from group_interview_arena_api.core.errors import (
    ApiError,
    api_error_handler,
    http_exception_handler,
    unexpected_exception_handler,
    validation_exception_handler,
)
from group_interview_arena_api.core.logging import configure_logging
from group_interview_arena_api.core.request_id import (
    create_request_id,
    reset_request_id,
    set_request_id,
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

logger = logging.getLogger(__name__)


def create_app(
    settings: Settings | None = None,
    database_settings: DatabaseSettings | None = None,
) -> FastAPI:
    resolved_settings = settings or Settings()
    configure_logging(resolved_settings.log_level)

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncGenerator[None]:
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
        try:
            yield
        finally:
            delattr(application.state, DATABASE_SESSION_FACTORY_STATE_KEY)
            del application.state.database_engine
            await dispose_database_engine(engine)

    application = FastAPI(title="AI 群面训练场 API", lifespan=lifespan)
    application.include_router(health_router)
    application.include_router(create_auth_router(resolved_settings))

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
            try:
                response = await call_next(request)
            except Exception as exception:
                response = await unexpected_exception_handler(request, exception)

            duration_ms = round((perf_counter() - started_at) * 1000, 3)
            response.headers["X-Request-ID"] = request_id
            logger.info(
                "Request completed",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration_ms": duration_ms,
                },
            )
            return response
        finally:
            reset_request_id(token)

    application.middleware("http")(_request_context)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=list(resolved_settings.cors_origins),
        allow_credentials=False,
        allow_methods=["GET"],
        allow_headers=[],
        expose_headers=["X-Request-ID"],
    )

    return application


app = create_app()
