from fastapi import APIRouter, Depends, Request, Response, status

from group_interview_arena_api.core.config import Settings
from group_interview_arena_api.core.errors import ApiError, ErrorCode, ErrorResponse
from group_interview_arena_api.identity.client_source import (
    InvalidClientSourceError,
    resolve_client_source,
)
from group_interview_arena_api.identity.cookies import (
    clear_session_cookie,
    set_session_cookie,
)
from group_interview_arena_api.identity.csrf import (
    CSRF_OPENAPI_EXTRA,
    create_browser_csrf_guard,
)
from group_interview_arena_api.identity.dependencies import (
    CurrentUserDependency,
    DatabaseSession,
    DatabaseSessionFactory,
    SessionToken,
)
from group_interview_arena_api.identity.rate_limits import (
    RATE_LIMIT_RETRY_AFTER_SECONDS,
    AuthRateLimitedError,
    AuthRateLimitPersistenceError,
    enforce_login_rate_limits,
    enforce_register_rate_limits,
)
from group_interview_arena_api.identity.schemas import (
    CurrentUserResponse,
    LoginRequest,
    RegisterRequest,
)
from group_interview_arena_api.identity.service import (
    AuthenticationPersistenceError,
    EnrollmentUnavailableError,
    InvalidCredentialsError,
    InvalidPasswordError,
    InvalidUsernameError,
    login_user,
    logout_session,
    register_user,
)


def _internal_auth_error() -> ApiError:
    return ApiError(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        code=ErrorCode.INTERNAL_ERROR,
        message="An internal error occurred.",
    )


def _rate_limited_error() -> ApiError:
    return ApiError(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        code=ErrorCode.AUTH_RATE_LIMITED,
        message="Authentication request rate limit exceeded.",
        headers={"Retry-After": str(RATE_LIMIT_RETRY_AFTER_SECONDS)},
    )


def _client_source_error() -> ApiError:
    return ApiError(
        status_code=status.HTTP_400_BAD_REQUEST,
        code=ErrorCode.VALIDATION_ERROR,
        message="Request could not be processed.",
    )


def create_auth_router(settings: Settings) -> APIRouter:
    router = APIRouter(prefix="/auth", tags=["auth"])
    require_browser_csrf = create_browser_csrf_guard(settings.cors_origins)

    @router.post(
        "/register",
        response_model=CurrentUserResponse,
        status_code=status.HTTP_201_CREATED,
        responses={
            403: {"model": ErrorResponse},
            409: {"model": ErrorResponse},
            429: {"model": ErrorResponse},
            422: {"model": ErrorResponse},
        },
        dependencies=[Depends(require_browser_csrf)],
        openapi_extra=CSRF_OPENAPI_EXTRA,
    )
    async def register(  # pyright: ignore[reportUnusedFunction]
        payload: RegisterRequest,
        request: Request,
        response: Response,
        session: DatabaseSession,
        session_factory: DatabaseSessionFactory,
    ) -> CurrentUserResponse:
        try:
            client_source = resolve_client_source(request, settings)
            await enforce_register_rate_limits(
                session_factory,
                settings,
                client_source=client_source,
                invite_code=payload.invite_code.get_secret_value(),
            )
            result = await register_user(
                session,
                username=payload.username,
                password=payload.password.get_secret_value(),
                invite_code=payload.invite_code.get_secret_value(),
            )
        except InvalidClientSourceError:
            raise _client_source_error() from None
        except AuthRateLimitedError:
            raise _rate_limited_error() from None
        except AuthRateLimitPersistenceError:
            raise _internal_auth_error() from None
        except InvalidUsernameError:
            raise ApiError(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                code=ErrorCode.INVALID_USERNAME,
                message="Username is invalid.",
            ) from None
        except InvalidPasswordError:
            raise ApiError(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                code=ErrorCode.INVALID_PASSWORD,
                message="Password does not meet the enrollment policy.",
            ) from None
        except EnrollmentUnavailableError:
            raise ApiError(
                status_code=status.HTTP_409_CONFLICT,
                code=ErrorCode.ENROLLMENT_UNAVAILABLE,
                message="Enrollment is unavailable.",
            ) from None
        except AuthenticationPersistenceError:
            raise _internal_auth_error() from None

        set_session_cookie(response, result.raw_session_token, settings)
        return CurrentUserResponse(id=result.user_id, username=result.username)

    @router.post(
        "/login",
        response_model=CurrentUserResponse,
        responses={
            403: {"model": ErrorResponse},
            401: {"model": ErrorResponse},
            422: {"model": ErrorResponse},
            429: {"model": ErrorResponse},
        },
        dependencies=[Depends(require_browser_csrf)],
        openapi_extra=CSRF_OPENAPI_EXTRA,
    )
    async def login(  # pyright: ignore[reportUnusedFunction]
        payload: LoginRequest,
        request: Request,
        response: Response,
        session: DatabaseSession,
        session_factory: DatabaseSessionFactory,
    ) -> CurrentUserResponse:
        try:
            client_source = resolve_client_source(request, settings)
            await enforce_login_rate_limits(
                session_factory,
                settings,
                client_source=client_source,
                username=payload.username,
            )
            result = await login_user(
                session,
                username=payload.username,
                password=payload.password.get_secret_value(),
            )
        except InvalidClientSourceError:
            raise _client_source_error() from None
        except AuthRateLimitedError:
            raise _rate_limited_error() from None
        except AuthRateLimitPersistenceError:
            raise _internal_auth_error() from None
        except InvalidCredentialsError:
            raise ApiError(
                status_code=status.HTTP_401_UNAUTHORIZED,
                code=ErrorCode.INVALID_CREDENTIALS,
                message="Invalid credentials.",
            ) from None
        except AuthenticationPersistenceError:
            raise _internal_auth_error() from None

        set_session_cookie(response, result.raw_session_token, settings)
        return CurrentUserResponse(id=result.user_id, username=result.username)

    @router.get(
        "/me",
        response_model=CurrentUserResponse,
        responses={401: {"model": ErrorResponse}},
    )
    async def me(  # pyright: ignore[reportUnusedFunction]
        user: CurrentUserDependency,
    ) -> CurrentUserResponse:
        return CurrentUserResponse(id=user.user_id, username=user.username)

    @router.post(
        "/logout",
        status_code=status.HTTP_204_NO_CONTENT,
        responses={
            204: {"description": "Session invalidated and Cookie cleared."},
            403: {"model": ErrorResponse},
            422: {"model": ErrorResponse},
        },
        dependencies=[Depends(require_browser_csrf)],
        openapi_extra=CSRF_OPENAPI_EXTRA,
    )
    async def logout(  # pyright: ignore[reportUnusedFunction]
        session: DatabaseSession,
        raw_token: SessionToken,
    ) -> Response:
        try:
            await logout_session(session, raw_token)
        except AuthenticationPersistenceError:
            raise _internal_auth_error() from None
        response = Response(status_code=status.HTTP_204_NO_CONTENT)
        clear_session_cookie(response, settings)
        return response

    return router
