from starlette.responses import Response

from group_interview_arena_api.core.config import Settings
from group_interview_arena_api.identity.sessions import SESSION_DURATION

SESSION_COOKIE_NAME = "gia_session"
SESSION_COOKIE_MAX_AGE = int(SESSION_DURATION.total_seconds())


def set_session_cookie(
    response: Response,
    raw_token: str,
    settings: Settings,
) -> None:
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=raw_token,
        max_age=SESSION_COOKIE_MAX_AGE,
        path="/",
        secure=settings.session_cookie_secure,
        httponly=True,
        samesite="lax",
    )


def clear_session_cookie(response: Response, settings: Settings) -> None:
    response.delete_cookie(
        key=SESSION_COOKIE_NAME,
        path="/",
        secure=settings.session_cookie_secure,
        httponly=True,
        samesite="lax",
    )
