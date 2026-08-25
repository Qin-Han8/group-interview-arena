import asyncio
import json
import logging
from contextlib import suppress
from datetime import UTC, datetime
from typing import Annotated, cast
from uuid import UUID, uuid4

from fastapi import APIRouter, Query, WebSocket
from pydantic import UUID4, ValidationError
from starlette.websockets import WebSocketDisconnect

from group_interview_arena_api.core.config import Settings
from group_interview_arena_api.core.logging import log_event
from group_interview_arena_api.core.request_id import create_request_id
from group_interview_arena_api.db.dependencies import (
    get_database_session_factory_from_connection,
)
from group_interview_arena_api.identity.cookies import SESSION_COOKIE_NAME
from group_interview_arena_api.identity.csrf import has_exact_trusted_origin
from group_interview_arena_api.identity.service import (
    AuthenticationPersistenceError,
    CurrentUser,
    get_current_user,
)
from group_interview_arena_api.modules.ai_runtime.composition import (
    AiDriveCompositionError,
)
from group_interview_arena_api.modules.discussion_sessions.contracts import (
    FormalEventEnvelope,
    ParticipantUtteranceSubmitCommand,
    RealtimeErrorCode,
    RealtimeSessionCommand,
    SessionAbortCommand,
    SessionStartCommand,
    WsErrorDetail,
    WsErrorEnvelope,
)
from group_interview_arena_api.modules.discussion_sessions.domain import (
    InvalidSessionStateError,
    SessionCommand,
)
from group_interview_arena_api.modules.discussion_sessions.progression import (
    resume_discussion_progression,
)
from group_interview_arena_api.modules.discussion_sessions.public_events import (
    project_public_events,
)
from group_interview_arena_api.modules.discussion_sessions.service import (
    ActionIdConflictError,
    SequenceAheadError,
    SessionNotFoundError,
    SessionPersistenceError,
    apply_session_command,
    get_session_snapshot,
    load_reconnect_events,
    reconcile_session_deadline,
)
from group_interview_arena_api.modules.discussion_sessions.utterances import (
    SubmitHumanUtterance,
    UtteranceRejectedError,
    submit_human_utterance,
)

logger = logging.getLogger(__name__)

_ERROR_MESSAGES: dict[RealtimeErrorCode, str] = {
    "INVALID_SESSION_STATE": "Session command could not be applied.",
    "ACTION_ID_CONFLICT": "Action identity conflicts with an earlier command.",
    "UTTERANCE_REJECTED": "You cannot submit an utterance right now.",
    "PROTOCOL_ERROR": "Realtime command could not be processed.",
    "SEQUENCE_AHEAD": "Session history must be reloaded.",
    "INTERNAL_ERROR": "An internal error occurred.",
}


def _parse_command(text: str) -> RealtimeSessionCommand:
    raw = json.loads(text)
    if not isinstance(raw, dict):
        raise ValueError("Realtime command must be an object.")
    payload = cast(dict[str, object], raw)
    command_type = payload.get("type")
    if command_type == "session.abort":
        return SessionAbortCommand.model_validate(payload)
    if command_type == "session.start":
        return SessionStartCommand.model_validate(payload)
    if command_type == "participant.utterance.submit":
        return ParticipantUtteranceSubmitCommand.model_validate(payload)
    raise ValueError("Unsupported realtime command.")


def _error_event(
    *,
    code: RealtimeErrorCode,
    session_id: UUID,
    action_id: UUID | None,
    request_id: str,
) -> WsErrorEnvelope:
    return WsErrorEnvelope(
        schema_version=1,
        type="error",
        session_id=session_id,
        action_id=action_id,
        occurred_at=datetime.now(UTC),
        error=WsErrorDetail(
            code=code,
            message=_ERROR_MESSAGES[code],
            request_id=UUID(request_id),
        ),
    )


async def _send_error(
    websocket: WebSocket,
    *,
    code: RealtimeErrorCode,
    session_id: UUID,
    action_id: UUID | None,
    request_id: str,
) -> bool:
    try:
        await websocket.send_json(
            _error_event(
                code=code,
                session_id=session_id,
                action_id=action_id,
                request_id=request_id,
            ).model_dump(mode="json")
        )
    except Exception:
        return False
    return True


async def _deny(websocket: WebSocket) -> None:
    await websocket.close(code=1008)


async def _send_formal_event(
    websocket: WebSocket,
    event: FormalEventEnvelope,
) -> None:
    await websocket.send_json(event.model_dump(mode="json"))


async def _authorized_user(
    websocket: WebSocket,
    *,
    session_id: UUID,
) -> CurrentUser | None:
    session_factory = get_database_session_factory_from_connection(websocket)
    raw_token = websocket.cookies.get(SESSION_COOKIE_NAME)
    try:
        async with session_factory() as session:
            user = await get_current_user(session, raw_token)
            if user is None:
                return None
            await get_session_snapshot(
                session,
                owner_id=user.user_id,
                session_id=session_id,
            )
    except (
        AuthenticationPersistenceError,
        SessionNotFoundError,
        SessionPersistenceError,
    ):
        return None
    return user


def create_realtime_router(settings: Settings) -> APIRouter:
    router = APIRouter()

    @router.websocket("/ws/sessions/{session_id}")
    async def session_socket(  # pyright: ignore[reportUnusedFunction]
        websocket: WebSocket,
        session_id: UUID4,
        after_sequence: Annotated[int, Query(ge=0)],
    ) -> None:
        if not has_exact_trusted_origin(
            websocket.headers.getlist("origin"),
            settings.cors_origins,
        ):
            await _deny(websocket)
            return

        user = await _authorized_user(websocket, session_id=session_id)
        if user is None:
            await _deny(websocket)
            return

        connection_id = uuid4()
        session_factory = get_database_session_factory_from_connection(websocket)
        sequence_ahead = False
        try:
            async with session_factory() as session:
                await reconcile_session_deadline(
                    session,
                    owner_id=user.user_id,
                    session_id=session_id,
                )
            async with session_factory() as session:
                await load_reconnect_events(
                    session,
                    owner_id=user.user_id,
                    session_id=session_id,
                    after_sequence=after_sequence,
                )
        except SequenceAheadError:
            sequence_ahead = True
        except SessionNotFoundError, SessionPersistenceError:
            await _deny(websocket)
            return

        await websocket.accept()
        log_event(
            logger,
            logging.INFO,
            "realtime.connection.accepted",
            session_id=str(session_id),
            connection_id=str(connection_id),
        )

        if sequence_ahead:
            request_id = create_request_id()
            await _send_error(
                websocket,
                code="SEQUENCE_AHEAD",
                session_id=session_id,
                action_id=None,
                request_id=request_id,
            )
            log_event(
                logger,
                logging.WARNING,
                "realtime.connection.rejected",
                request_id=request_id,
                session_id=str(session_id),
                connection_id=str(connection_id),
                exception_category="sequence_ahead",
            )
            await websocket.close(code=1008)
            return

        active_action_id: UUID | None = None
        sent_sequence = after_sequence
        send_lock = asyncio.Lock()
        catchup_task: asyncio.Task[None] | None = None
        progression_task: asyncio.Task[None] | None = None
        progression_lock = asyncio.Lock()

        async def drain_committed_events() -> None:
            nonlocal sent_sequence
            async with send_lock:
                async with session_factory() as session:
                    events = await load_reconnect_events(
                        session,
                        owner_id=user.user_id,
                        session_id=session_id,
                        after_sequence=sent_sequence,
                    )
                    projected = (
                        await project_public_events(session, events) if events else []
                    )
                for event in projected:
                    await _send_formal_event(websocket, event)
                    sent_sequence = event.sequence

        async def run_progression_best_effort() -> None:
            try:
                result = await resume_discussion_progression(
                    session_factory,
                    owner_id=user.user_id,
                    session_id=session_id,
                )
            except asyncio.CancelledError:
                log_event(
                    logger,
                    logging.INFO,
                    "realtime.progression.stopped",
                    session_id=str(session_id),
                    connection_id=str(connection_id),
                    exception_category="progression_cancelled",
                )
                raise
            except AiDriveCompositionError:
                log_event(
                    logger,
                    logging.INFO,
                    "realtime.progression.stopped",
                    session_id=str(session_id),
                    connection_id=str(connection_id),
                    exception_category="provider_configuration_unavailable",
                )
            except Exception:
                log_event(
                    logger,
                    logging.ERROR,
                    "realtime.progression.failed",
                    session_id=str(session_id),
                    connection_id=str(connection_id),
                    exception_category="internal_error",
                )
            else:
                log_event(
                    logger,
                    logging.INFO,
                    "realtime.progression.stopped",
                    session_id=str(session_id),
                    connection_id=str(connection_id),
                    exception_category=f"progression_{result.outcome.value}",
                )

        async def kick_progression_best_effort() -> None:
            nonlocal progression_task
            async with progression_lock:
                if progression_task is not None:
                    if not progression_task.done():
                        return
                    await progression_task
                progression_task = asyncio.create_task(run_progression_best_effort())

        async def catchup_committed_events() -> None:
            try:
                while True:
                    await asyncio.sleep(0.25)
                    async with session_factory() as session:
                        await reconcile_session_deadline(
                            session,
                            owner_id=user.user_id,
                            session_id=session_id,
                        )
                    await drain_committed_events()
            except asyncio.CancelledError:
                raise
            except Exception:
                request_id = create_request_id()
                log_event(
                    logger,
                    logging.ERROR,
                    "realtime.catchup.failed",
                    request_id=request_id,
                    session_id=str(session_id),
                    connection_id=str(connection_id),
                    exception_category="internal_error",
                )
                async with send_lock:
                    await _send_error(
                        websocket,
                        code="INTERNAL_ERROR",
                        session_id=session_id,
                        action_id=None,
                        request_id=request_id,
                    )
                    with suppress(Exception):
                        await websocket.close(code=1011)

        try:
            await drain_committed_events()
            await kick_progression_best_effort()
            catchup_task = asyncio.create_task(catchup_committed_events())

            while True:
                message = await websocket.receive()
                if message["type"] == "websocket.disconnect":
                    return

                request_id = create_request_id()
                text = message.get("text")
                if not isinstance(text, str):
                    await _send_error(
                        websocket,
                        code="PROTOCOL_ERROR",
                        session_id=session_id,
                        action_id=None,
                        request_id=request_id,
                    )
                    await websocket.close(code=1008)
                    return

                try:
                    parsed = _parse_command(text)
                except json.JSONDecodeError, ValidationError, ValueError:
                    await _send_error(
                        websocket,
                        code="PROTOCOL_ERROR",
                        session_id=session_id,
                        action_id=None,
                        request_id=request_id,
                    )
                    log_event(
                        logger,
                        logging.WARNING,
                        "realtime.command.rejected",
                        request_id=request_id,
                        session_id=str(session_id),
                        connection_id=str(connection_id),
                        exception_category="protocol_error",
                    )
                    await websocket.close(code=1008)
                    return

                if parsed.session_id != session_id:
                    await _send_error(
                        websocket,
                        code="PROTOCOL_ERROR",
                        session_id=session_id,
                        action_id=parsed.action_id,
                        request_id=request_id,
                    )
                    await websocket.close(code=1008)
                    return

                active_action_id = parsed.action_id
                try:
                    if isinstance(parsed, ParticipantUtteranceSubmitCommand):
                        async with session_factory() as session:
                            committed = await submit_human_utterance(
                                session,
                                owner_id=user.user_id,
                                command=SubmitHumanUtterance(
                                    session_id=parsed.session_id,
                                    action_id=parsed.action_id,
                                    floor_grant_id=parsed.payload.floor_grant_id,
                                    content=parsed.payload.content,
                                    received_at=datetime.now(UTC),
                                ),
                            )
                        last_command_sequence = committed.events[-1].sequence
                    else:
                        command = SessionCommand(
                            schema_version=parsed.schema_version,
                            command_type=parsed.type,
                            session_id=parsed.session_id,
                            action_id=parsed.action_id,
                            payload=parsed.payload.model_dump(mode="json"),
                        )
                        async with session_factory() as session:
                            events = await apply_session_command(
                                session,
                                owner_id=user.user_id,
                                command=command,
                                duration_plan=(
                                    settings.session_phase_durations.to_duration_plan()
                                ),
                            )
                        last_command_sequence = events[-1].sequence if events else None
                except InvalidSessionStateError:
                    await _send_error(
                        websocket,
                        code="INVALID_SESSION_STATE",
                        session_id=session_id,
                        action_id=parsed.action_id,
                        request_id=request_id,
                    )
                    log_event(
                        logger,
                        logging.WARNING,
                        "realtime.command.rejected",
                        request_id=request_id,
                        session_id=str(session_id),
                        connection_id=str(connection_id),
                        action_id=str(parsed.action_id),
                        exception_category="invalid_session_state",
                    )
                    continue
                except UtteranceRejectedError:
                    await _send_error(
                        websocket,
                        code="UTTERANCE_REJECTED",
                        session_id=session_id,
                        action_id=parsed.action_id,
                        request_id=request_id,
                    )
                    log_event(
                        logger,
                        logging.WARNING,
                        "realtime.command.rejected",
                        request_id=request_id,
                        session_id=str(session_id),
                        connection_id=str(connection_id),
                        action_id=str(parsed.action_id),
                        exception_category="utterance_rejected",
                    )
                    continue
                except ActionIdConflictError:
                    await _send_error(
                        websocket,
                        code="ACTION_ID_CONFLICT",
                        session_id=session_id,
                        action_id=parsed.action_id,
                        request_id=request_id,
                    )
                    log_event(
                        logger,
                        logging.WARNING,
                        "realtime.command.rejected",
                        request_id=request_id,
                        session_id=str(session_id),
                        connection_id=str(connection_id),
                        action_id=str(parsed.action_id),
                        exception_category="action_id_conflict",
                    )
                    continue
                except Exception:
                    await _send_error(
                        websocket,
                        code="INTERNAL_ERROR",
                        session_id=session_id,
                        action_id=parsed.action_id,
                        request_id=request_id,
                    )
                    log_event(
                        logger,
                        logging.ERROR,
                        "realtime.command.failed",
                        request_id=request_id,
                        session_id=str(session_id),
                        connection_id=str(connection_id),
                        action_id=str(parsed.action_id),
                        exception_category="internal_error",
                    )
                    await websocket.close(code=1011)
                    return

                await drain_committed_events()
                log_event(
                    logger,
                    logging.INFO,
                    "realtime.command.completed",
                    request_id=request_id,
                    session_id=str(session_id),
                    connection_id=str(connection_id),
                    action_id=str(parsed.action_id),
                    sequence=last_command_sequence,
                )
                active_action_id = None
                if isinstance(parsed, ParticipantUtteranceSubmitCommand):
                    await kick_progression_best_effort()
        except WebSocketDisconnect:
            return
        except Exception:
            request_id = create_request_id()
            await _send_error(
                websocket,
                code="INTERNAL_ERROR",
                session_id=session_id,
                action_id=active_action_id,
                request_id=request_id,
            )
            log_event(
                logger,
                logging.ERROR,
                "realtime.connection.failed",
                request_id=request_id,
                session_id=str(session_id),
                connection_id=str(connection_id),
                action_id=(
                    str(active_action_id) if active_action_id is not None else None
                ),
                exception_category="internal_error",
            )
            try:
                await websocket.close(code=1011)
            except Exception:
                pass
        finally:
            if catchup_task is not None:
                catchup_task.cancel()
                with suppress(asyncio.CancelledError):
                    await catchup_task
            if progression_task is not None:
                progression_task.cancel()
                with suppress(asyncio.CancelledError):
                    await progression_task

    return router
