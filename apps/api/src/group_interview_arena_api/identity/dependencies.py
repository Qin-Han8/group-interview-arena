from typing import Annotated

from fastapi import Depends, Security, status
from fastapi.security import APIKeyCookie
from sqlalchemy.ext.asyncio import AsyncSession

from group_interview_arena_api.core.errors import ApiError, ErrorCode
from group_interview_arena_api.db.dependencies import get_database_session
from group_interview_arena_api.identity.cookies import SESSION_COOKIE_NAME
from group_interview_arena_api.identity.service import (
    AuthenticationPersistenceError,
    CurrentUser,
    get_current_user,
)

_session_cookie = APIKeyCookie(
    name=SESSION_COOKIE_NAME,
    scheme_name="SessionCookie",
    description="Opaque server-side session token stored in an HttpOnly Cookie.",
    auto_error=False,
)

DatabaseSession = Annotated[AsyncSession, Depends(get_database_session)]
SessionToken = Annotated[str | None, Security(_session_cookie)]


async def require_current_user(
    session: DatabaseSession,
    raw_token: SessionToken,
) -> CurrentUser:
    try:
        user = await get_current_user(session, raw_token)
    except AuthenticationPersistenceError:
        raise ApiError(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code=ErrorCode.INTERNAL_ERROR,
            message="An internal error occurred.",
        ) from None
    if user is None:
        raise ApiError(
            status_code=status.HTTP_401_UNAUTHORIZED,
            code=ErrorCode.AUTHENTICATION_REQUIRED,
            message="Authentication is required.",
        )
    return user


CurrentUserDependency = Annotated[CurrentUser, Depends(require_current_user)]
