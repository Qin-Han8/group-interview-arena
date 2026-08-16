import hashlib
import json
from datetime import UTC, datetime
from typing import Never
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from group_interview_arena_api.db.models import (
    DiscussionEvent,
    SessionAction,
    SimulationSession,
)
from group_interview_arena_api.modules.discussion_sessions.domain import (
    SessionCommand,
    SessionSnapshot,
    SessionStatus,
    StoredEvent,
    decide_session_command,
)


class SessionNotFoundError(Exception):
    pass


class ActionIdConflictError(Exception):
    pass


class SequenceAheadError(Exception):
    pass


class SessionPersistenceError(Exception):
    pass


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _raise_persistence_error() -> Never:
    raise SessionPersistenceError from None


def _snapshot(row: SimulationSession) -> SessionSnapshot:
    return SessionSnapshot(
        session_id=row.id,
        status=SessionStatus(row.status),
        created_at=row.created_at,
        updated_at=row.updated_at,
        last_sequence=row.last_sequence,
    )


def _stored_event(row: DiscussionEvent) -> StoredEvent:
    return StoredEvent(
        event_version=row.event_version,
        event_type=row.event_type,
        session_id=row.session_id,
        sequence=row.sequence,
        occurred_at=row.occurred_at,
        action_id=row.causation_action_id,
        payload=row.payload,
    )


def _command_digest(command: SessionCommand) -> bytes:
    semantic_payload = {
        "schema_version": command.schema_version,
        "type": command.command_type,
        "payload": command.payload,
    }
    encoded = json.dumps(
        semantic_payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).digest()


async def create_session(
    session: AsyncSession,
    *,
    owner_id: UUID,
) -> SessionSnapshot:
    now = _utc_now()
    row = SimulationSession(
        id=uuid4(),
        owner_user_id=owner_id,
        status=SessionStatus.CREATED.value,
        last_sequence=1,
        created_at=now,
        updated_at=now,
    )
    event = DiscussionEvent(
        session_id=row.id,
        sequence=1,
        event_version=1,
        event_type="session.created",
        causation_action_id=None,
        payload={"status": SessionStatus.CREATED.value},
        occurred_at=now,
    )
    try:
        async with session.begin():
            session.add(row)
            await session.flush()
            session.add(event)
            await session.flush()
    except SQLAlchemyError:
        _raise_persistence_error()
    return _snapshot(row)


async def get_session_snapshot(
    session: AsyncSession,
    *,
    owner_id: UUID,
    session_id: UUID,
) -> SessionSnapshot:
    try:
        row = await session.scalar(
            select(SimulationSession).where(
                SimulationSession.id == session_id,
                SimulationSession.owner_user_id == owner_id,
            )
        )
    except SQLAlchemyError:
        _raise_persistence_error()
    if row is None:
        raise SessionNotFoundError
    return _snapshot(row)


async def _events_for_action(
    session: AsyncSession,
    *,
    session_id: UUID,
    action_id: UUID,
) -> list[StoredEvent]:
    rows = list(
        (
            await session.scalars(
                select(DiscussionEvent)
                .where(
                    DiscussionEvent.session_id == session_id,
                    DiscussionEvent.causation_action_id == action_id,
                )
                .order_by(DiscussionEvent.sequence)
            )
        ).all()
    )
    return [_stored_event(row) for row in rows]


async def apply_session_command(
    session: AsyncSession,
    *,
    owner_id: UUID,
    command: SessionCommand,
) -> list[StoredEvent]:
    digest = _command_digest(command)
    try:
        async with session.begin():
            aggregate = await session.scalar(
                select(SimulationSession)
                .where(
                    SimulationSession.id == command.session_id,
                    SimulationSession.owner_user_id == owner_id,
                )
                .with_for_update()
            )
            if aggregate is None:
                raise SessionNotFoundError

            accepted_action = await session.get(
                SessionAction,
                (command.session_id, command.action_id),
            )
            if accepted_action is not None:
                if (
                    accepted_action.command_version != command.schema_version
                    or accepted_action.command_type != command.command_type
                    or accepted_action.payload_digest != digest
                ):
                    raise ActionIdConflictError
                return await _events_for_action(
                    session,
                    session_id=command.session_id,
                    action_id=command.action_id,
                )

            outcome = decide_session_command(
                SessionStatus(aggregate.status),
                command,
            )
            now = _utc_now()
            session.add(
                SessionAction(
                    session_id=command.session_id,
                    action_id=command.action_id,
                    command_version=command.schema_version,
                    command_type=command.command_type,
                    payload_digest=digest,
                    created_at=now,
                )
            )
            await session.flush()

            first_sequence = aggregate.last_sequence + 1
            aggregate.status = outcome.status.value
            aggregate.updated_at = now
            aggregate.last_sequence += len(outcome.events)
            event_rows = [
                DiscussionEvent(
                    session_id=command.session_id,
                    sequence=first_sequence + offset,
                    event_version=1,
                    event_type=pending.event_type,
                    causation_action_id=command.action_id,
                    payload=pending.payload,
                    occurred_at=now,
                )
                for offset, pending in enumerate(outcome.events)
            ]
            session.add_all(event_rows)
            await session.flush()
            stored_events = [_stored_event(row) for row in event_rows]
    except SessionNotFoundError, ActionIdConflictError:
        raise
    except SQLAlchemyError:
        _raise_persistence_error()
    return stored_events


async def load_reconnect_events(
    session: AsyncSession,
    *,
    owner_id: UUID,
    session_id: UUID,
    after_sequence: int,
) -> list[StoredEvent]:
    try:
        aggregate = await session.scalar(
            select(SimulationSession).where(
                SimulationSession.id == session_id,
                SimulationSession.owner_user_id == owner_id,
            )
        )
        if aggregate is None:
            raise SessionNotFoundError
        if after_sequence > aggregate.last_sequence:
            raise SequenceAheadError
        rows = list(
            (
                await session.scalars(
                    select(DiscussionEvent)
                    .where(
                        DiscussionEvent.session_id == session_id,
                        DiscussionEvent.sequence > after_sequence,
                    )
                    .order_by(DiscussionEvent.sequence)
                )
            ).all()
        )
    except SessionNotFoundError, SequenceAheadError:
        raise
    except SQLAlchemyError:
        _raise_persistence_error()
    return [_stored_event(row) for row in rows]
