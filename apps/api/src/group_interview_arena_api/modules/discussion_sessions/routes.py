from typing import Annotated

from fastapi import APIRouter, Depends, status
from pydantic import UUID4
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from group_interview_arena_api.core.config import Settings
from group_interview_arena_api.core.errors import ApiError, ErrorCode, ErrorResponse
from group_interview_arena_api.db.dependencies import get_database_session_factory
from group_interview_arena_api.identity.csrf import (
    CSRF_OPENAPI_EXTRA,
    create_browser_csrf_guard,
)
from group_interview_arena_api.identity.dependencies import CurrentUserDependency
from group_interview_arena_api.modules.discussion_sessions.contracts import (
    SessionCreateRequest,
    SessionSnapshotResponse,
)
from group_interview_arena_api.modules.discussion_sessions.domain import SessionSnapshot
from group_interview_arena_api.modules.discussion_sessions.service import (
    SessionNotFoundError,
    SessionPersistenceError,
    create_session,
    get_session_snapshot,
)
from group_interview_arena_api.modules.question_personas.service import (
    QuestionNotFoundError,
)

DatabaseSessionFactory = Annotated[
    async_sessionmaker[AsyncSession],
    Depends(get_database_session_factory),
]


def _response(snapshot: SessionSnapshot) -> SessionSnapshotResponse:
    return SessionSnapshotResponse(
        id=snapshot.session_id,
        question_version_id=snapshot.question_version_id,
        status=snapshot.status,
        created_at=snapshot.created_at,
        updated_at=snapshot.updated_at,
        last_sequence=snapshot.last_sequence,
    )


def _internal_error() -> ApiError:
    return ApiError(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        code=ErrorCode.INTERNAL_ERROR,
        message="An internal error occurred.",
    )


def _not_found() -> ApiError:
    return ApiError(
        status_code=status.HTTP_404_NOT_FOUND,
        code=ErrorCode.SESSION_NOT_FOUND,
        message="Session not found.",
    )


def _question_not_found() -> ApiError:
    return ApiError(
        status_code=status.HTTP_404_NOT_FOUND,
        code=ErrorCode.QUESTION_NOT_FOUND,
        message="Question not found.",
    )


def create_discussion_session_router(settings: Settings) -> APIRouter:
    router = APIRouter(prefix="/sessions", tags=["sessions"])
    require_browser_csrf = create_browser_csrf_guard(settings.cors_origins)

    @router.post(
        "",
        response_model=SessionSnapshotResponse,
        status_code=status.HTTP_201_CREATED,
        responses={
            401: {"model": ErrorResponse},
            403: {"model": ErrorResponse},
            404: {"model": ErrorResponse},
            422: {"model": ErrorResponse},
            500: {"model": ErrorResponse},
        },
        dependencies=[Depends(require_browser_csrf)],
        openapi_extra=CSRF_OPENAPI_EXTRA,
    )
    async def create(  # pyright: ignore[reportUnusedFunction]
        request: SessionCreateRequest,
        user: CurrentUserDependency,
        session_factory: DatabaseSessionFactory,
    ) -> SessionSnapshotResponse:
        try:
            async with session_factory() as session:
                snapshot = await create_session(
                    session,
                    owner_id=user.user_id,
                    question_version_id=request.question_version_id,
                )
        except QuestionNotFoundError:
            raise _question_not_found() from None
        except SessionPersistenceError:
            raise _internal_error() from None
        return _response(snapshot)

    @router.get(
        "/{session_id}",
        response_model=SessionSnapshotResponse,
        responses={
            401: {"model": ErrorResponse},
            404: {"model": ErrorResponse},
            422: {"model": ErrorResponse},
            500: {"model": ErrorResponse},
        },
    )
    async def snapshot(  # pyright: ignore[reportUnusedFunction]
        session_id: UUID4,
        user: CurrentUserDependency,
        session_factory: DatabaseSessionFactory,
    ) -> SessionSnapshotResponse:
        try:
            async with session_factory() as session:
                result = await get_session_snapshot(
                    session,
                    owner_id=user.user_id,
                    session_id=session_id,
                )
        except SessionNotFoundError:
            raise _not_found() from None
        except SessionPersistenceError:
            raise _internal_error() from None
        return _response(result)

    return router
