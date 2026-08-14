from typing import Annotated

from fastapi import APIRouter, Depends, Response, Security, status
from fastapi.security import APIKeyCookie
from sqlalchemy.ext.asyncio import AsyncSession

from group_interview_arena_api.core.config import Settings
from group_interview_arena_api.core.errors import ApiError, ErrorCode, ErrorResponse
from group_interview_arena_api.db.dependencies import get_database_session
from group_interview_arena_api.identity.cookies import (
    SESSION_COOKIE_NAME,
    clear_session_cookie,
    set_session_cookie,
)
from group_interview_arena_api.identity.csrf import (
    CSRF_OPENAPI_EXTRA,
    create_browser_csrf_guard,
)
from group_interview_arena_api.identity.schemas import (
    CurrentUserResponse,
    LoginRequest,
    RegisterRequest,
)
from group_interview_arena_api.identity.service import (
    AuthenticationPersistenceError,
    InvalidCredentialsError,
    InvalidPasswordError,
    InvalidUsernameError,
    UsernameUnavailableError,
    get_current_user,
    login_user,
    logout_session,
    register_user,
)

_session_cookie = APIKeyCookie(
    name=SESSION_COOKIE_NAME,
    scheme_name="SessionCookie",
    description="Opaque server-side session token stored in an HttpOnly Cookie.",
    auto_error=False,
)

DatabaseSession = Annotated[AsyncSession, Depends(get_database_session)]
SessionToken = Annotated[str | None, Security(_session_cookie)]


def _internal_auth_error() -> ApiError:
    return ApiError(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        code=ErrorCode.INTERNAL_ERROR,
        message="An internal error occurred.",
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
            422: {"model": ErrorResponse},
        },
        dependencies=[Depends(require_browser_csrf)],
        openapi_extra=CSRF_OPENAPI_EXTRA,
    )
    async def register(  # pyright: ignore[reportUnusedFunction]
        payload: RegisterRequest,
        response: Response,
        session: DatabaseSession,
    ) -> CurrentUserResponse:
        try:
            result = await register_user(
                session,
                username=payload.username,
                password=payload.password.get_secret_value(),
            )
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
        except UsernameUnavailableError:
            raise ApiError(
                status_code=status.HTTP_409_CONFLICT,
                code=ErrorCode.USERNAME_UNAVAILABLE,
                message="Username is unavailable.",
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
        },
        dependencies=[Depends(require_browser_csrf)],
        openapi_extra=CSRF_OPENAPI_EXTRA,
    )
    async def login(  # pyright: ignore[reportUnusedFunction]
        payload: LoginRequest,
        response: Response,
        session: DatabaseSession,
    ) -> CurrentUserResponse:
        try:
            result = await login_user(
                session,
                username=payload.username,
                password=payload.password.get_secret_value(),
            )
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
        session: DatabaseSession,
        raw_token: SessionToken,
    ) -> CurrentUserResponse:
        try:
            user = await get_current_user(session, raw_token)
        except AuthenticationPersistenceError:
            raise _internal_auth_error() from None
        if user is None:
            raise ApiError(
                status_code=status.HTTP_401_UNAUTHORIZED,
                code=ErrorCode.AUTHENTICATION_REQUIRED,
                message="Authentication is required.",
            )
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
