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
    SessionStartRequest,
)
from group_interview_arena_api.modules.discussion_sessions.domain import (
    InvalidSessionStateError,
    SessionCommand,
    SessionSnapshot,
)
from group_interview_arena_api.modules.discussion_sessions.service import (
    ActionIdConflictError,
    SessionNotFoundError,
    SessionPersistenceError,
    apply_session_command,
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
        phase_started_at=snapshot.phase_started_at,
        phase_deadline_at=snapshot.phase_deadline_at,
        server_now=snapshot.server_now,
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


def _invalid_session_state() -> ApiError:
    return ApiError(
        status_code=status.HTTP_409_CONFLICT,
        code=ErrorCode.INVALID_SESSION_STATE,
        message="Session command could not be applied.",
    )


def _action_id_conflict() -> ApiError:
    return ApiError(
        status_code=status.HTTP_409_CONFLICT,
        code=ErrorCode.ACTION_ID_CONFLICT,
        message="Action identity conflicts with an earlier command.",
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

    @router.post(
        "/{session_id}/start",
        response_model=SessionSnapshotResponse,
        responses={
            200: {"model": SessionSnapshotResponse},
            401: {"model": ErrorResponse},
            403: {"model": ErrorResponse},
            404: {"model": ErrorResponse},
            409: {"model": ErrorResponse},
            422: {"model": ErrorResponse},
            500: {"model": ErrorResponse},
        },
        dependencies=[Depends(require_browser_csrf)],
        openapi_extra=CSRF_OPENAPI_EXTRA,
    )
    async def start(  # pyright: ignore[reportUnusedFunction]
        session_id: UUID4,
        request: SessionStartRequest,
        user: CurrentUserDependency,
        session_factory: DatabaseSessionFactory,
    ) -> SessionSnapshotResponse:
        try:
            async with session_factory() as session:
                await apply_session_command(
                    session,
                    owner_id=user.user_id,
                    command=SessionCommand(
                        schema_version=1,
                        command_type="session.start",
                        session_id=session_id,
                        action_id=request.action_id,
                        payload={},
                    ),
                    duration_plan=settings.session_phase_durations.to_duration_plan(),
                )
            async with session_factory() as session:
                result = await get_session_snapshot(
                    session,
                    owner_id=user.user_id,
                    session_id=session_id,
                )
        except SessionNotFoundError:
            raise _not_found() from None
        except InvalidSessionStateError:
            raise _invalid_session_state() from None
        except ActionIdConflictError:
            raise _action_id_conflict() from None
        except SessionPersistenceError:
            raise _internal_error() from None
        return _response(result)

    return router
