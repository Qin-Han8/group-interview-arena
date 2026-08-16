import asyncio
from collections.abc import Callable, Coroutine
from contextlib import asynccontextmanager
from typing import Any, Protocol
from uuid import UUID, uuid4

import pytest
from sqlalchemy import URL, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from group_interview_arena_api.core.config import DatabaseSettings
from group_interview_arena_api.db import (
    DiscussionEvent,
    SessionAction,
    SimulationSession,
    User,
)
from group_interview_arena_api.db.runtime import (
    create_database_engine,
    create_database_session_factory,
    dispose_database_engine,
)
from group_interview_arena_api.modules.discussion_sessions import service
from group_interview_arena_api.modules.discussion_sessions.domain import (
    InvalidSessionStateError,
    PendingEvent,
    SessionCommand,
    SessionCommandOutcome,
    SessionStatus,
)
from group_interview_arena_api.modules.discussion_sessions.service import (
    ActionIdConflictError,
    SessionNotFoundError,
    apply_session_command,
    create_session,
    get_session_snapshot,
)

pytestmark = pytest.mark.integration


class TemporaryDatabaseContext(Protocol):
    database_name: str
    database_url: URL

    def database_settings(self) -> DatabaseSettings: ...


def run_async[T](operation: Callable[[], Coroutine[Any, Any, T]]) -> T:
    return asyncio.run(operation(), loop_factory=asyncio.SelectorEventLoop)


@asynccontextmanager
async def _session_factory(
    temporary_database: TemporaryDatabaseContext,
):
    engine = create_database_engine(temporary_database.database_settings())
    session_factory = create_database_session_factory(engine)
    try:
        yield session_factory
    finally:
        await dispose_database_engine(engine)


async def _seed_user(session_factory: async_sessionmaker[AsyncSession]) -> UUID:
    user_id = uuid4()
    async with session_factory() as session:
        async with session.begin():
            session.add(
                User(
                    id=user_id,
                    username=f"session_{user_id.hex[:12]}",
                    password_hash="test-only-password-hash",
                )
            )
    return user_id


def _abort(session_id: UUID, action_id: UUID | None = None) -> SessionCommand:
    return SessionCommand(
        schema_version=1,
        command_type="session.abort",
        session_id=session_id,
        action_id=action_id or uuid4(),
        payload={},
    )


async def _verify_creation_and_owner_snapshot(
    temporary_database: TemporaryDatabaseContext,
) -> None:
    async with _session_factory(temporary_database) as session_factory:
        owner_id = await _seed_user(session_factory)
        other_user_id = await _seed_user(session_factory)

        async with session_factory() as session:
            snapshot = await create_session(session, owner_id=owner_id)

        assert snapshot.status is SessionStatus.CREATED
        assert snapshot.last_sequence == 1
        assert snapshot.created_at == snapshot.updated_at

        async with session_factory() as session:
            loaded = await get_session_snapshot(
                session,
                owner_id=owner_id,
                session_id=snapshot.session_id,
            )
            assert loaded == snapshot
            event = await session.scalar(
                select(DiscussionEvent).where(
                    DiscussionEvent.session_id == snapshot.session_id
                )
            )
            assert event is not None
            assert event.sequence == 1
            assert event.event_type == "session.created"
            assert event.causation_action_id is None
            assert event.payload == {"status": "CREATED"}

        async with session_factory() as session:
            with pytest.raises(SessionNotFoundError):
                await get_session_snapshot(
                    session,
                    owner_id=other_user_id,
                    session_id=snapshot.session_id,
                )


def test_creation_event_and_owner_snapshot_are_authoritative(
    migrated_database: TemporaryDatabaseContext,
) -> None:
    run_async(lambda: _verify_creation_and_owner_snapshot(migrated_database))


async def _verify_idempotency_conflict_and_invalid_state(
    temporary_database: TemporaryDatabaseContext,
) -> None:
    async with _session_factory(temporary_database) as session_factory:
        owner_id = await _seed_user(session_factory)
        async with session_factory() as session:
            snapshot = await create_session(session, owner_id=owner_id)

        action_id = uuid4()
        command = _abort(snapshot.session_id, action_id)
        async with session_factory() as session:
            accepted = await apply_session_command(
                session,
                owner_id=owner_id,
                command=command,
            )
        async with session_factory() as session:
            duplicate = await apply_session_command(
                session,
                owner_id=owner_id,
                command=command,
            )

        assert accepted == duplicate
        assert [event.sequence for event in accepted] == [2]
        assert accepted[0].action_id == action_id

        conflict = SessionCommand(
            schema_version=1,
            command_type="session.abort",
            session_id=snapshot.session_id,
            action_id=action_id,
            payload={"different": True},
        )
        async with session_factory() as session:
            with pytest.raises(ActionIdConflictError):
                await apply_session_command(
                    session,
                    owner_id=owner_id,
                    command=conflict,
                )

        async with session_factory() as session:
            with pytest.raises(InvalidSessionStateError):
                await apply_session_command(
                    session,
                    owner_id=owner_id,
                    command=_abort(snapshot.session_id),
                )

        async with session_factory() as session:
            persisted = await session.get(SimulationSession, snapshot.session_id)
            assert persisted is not None
            assert persisted.status == "ABORTED_USER"
            assert persisted.last_sequence == 2
            assert (
                await session.scalar(
                    select(func.count())
                    .select_from(SessionAction)
                    .where(SessionAction.session_id == snapshot.session_id)
                )
                == 1
            )
            assert (
                await session.scalar(
                    select(func.count())
                    .select_from(DiscussionEvent)
                    .where(DiscussionEvent.session_id == snapshot.session_id)
                )
                == 2
            )


def test_durable_idempotency_conflict_and_invalid_state_are_atomic(
    migrated_database: TemporaryDatabaseContext,
) -> None:
    run_async(lambda: _verify_idempotency_conflict_and_invalid_state(migrated_database))


async def _verify_concurrent_commands(
    temporary_database: TemporaryDatabaseContext,
) -> None:
    async with _session_factory(temporary_database) as session_factory:
        owner_id = await _seed_user(session_factory)
        async with session_factory() as session:
            same_snapshot = await create_session(session, owner_id=owner_id)
        same_command = _abort(same_snapshot.session_id)

        async def apply(command: SessionCommand):
            async with session_factory() as session:
                return await apply_session_command(
                    session,
                    owner_id=owner_id,
                    command=command,
                )

        same_results = await asyncio.gather(apply(same_command), apply(same_command))
        assert same_results[0] == same_results[1]
        assert [event.sequence for event in same_results[0]] == [2]

        async with session_factory() as session:
            distinct_snapshot = await create_session(session, owner_id=owner_id)
        distinct_results = await asyncio.gather(
            apply(_abort(distinct_snapshot.session_id)),
            apply(_abort(distinct_snapshot.session_id)),
            return_exceptions=True,
        )
        assert sum(isinstance(result, list) for result in distinct_results) == 1
        assert (
            sum(
                isinstance(result, InvalidSessionStateError)
                for result in distinct_results
            )
            == 1
        )

        async with session_factory() as session:
            for session_id in (same_snapshot.session_id, distinct_snapshot.session_id):
                sequences = list(
                    (
                        await session.scalars(
                            select(DiscussionEvent.sequence)
                            .where(DiscussionEvent.session_id == session_id)
                            .order_by(DiscussionEvent.sequence)
                        )
                    ).all()
                )
                assert sequences == [1, 2]


def test_row_lock_serializes_same_and_distinct_concurrent_actions(
    migrated_database: TemporaryDatabaseContext,
) -> None:
    run_async(lambda: _verify_concurrent_commands(migrated_database))


async def _verify_multi_event_reservation_and_rollback(
    temporary_database: TemporaryDatabaseContext,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async with _session_factory(temporary_database) as session_factory:
        owner_id = await _seed_user(session_factory)
        async with session_factory() as session:
            multi_snapshot = await create_session(session, owner_id=owner_id)

        def two_event_outcome(
            _status: SessionStatus,
            _command: SessionCommand,
        ) -> SessionCommandOutcome:
            return SessionCommandOutcome(
                status=SessionStatus.ABORTED_USER,
                events=[
                    PendingEvent(
                        event_type="session.state_changed",
                        payload={
                            "previous_status": "CREATED",
                            "status": "ABORTED_USER",
                        },
                    ),
                    PendingEvent(
                        event_type="session.state_changed",
                        payload={
                            "previous_status": "CREATED",
                            "status": "ABORTED_USER",
                        },
                    ),
                ],
            )

        monkeypatch.setattr(service, "decide_session_command", two_event_outcome)
        async with session_factory() as session:
            events = await apply_session_command(
                session,
                owner_id=owner_id,
                command=_abort(multi_snapshot.session_id),
            )
        assert [event.sequence for event in events] == [2, 3]
        assert len({event.action_id for event in events}) == 1

        async with session_factory() as session:
            rollback_snapshot = await create_session(session, owner_id=owner_id)

        def unserializable_outcome(
            _status: SessionStatus,
            _command: SessionCommand,
        ) -> SessionCommandOutcome:
            return SessionCommandOutcome(
                status=SessionStatus.ABORTED_USER,
                events=[PendingEvent("session.state_changed", {"bad": object()})],
            )

        monkeypatch.setattr(service, "decide_session_command", unserializable_outcome)
        async with session_factory() as session:
            with pytest.raises(TypeError):
                await apply_session_command(
                    session,
                    owner_id=owner_id,
                    command=_abort(rollback_snapshot.session_id),
                )

        async with session_factory() as session:
            persisted = await session.get(
                SimulationSession,
                rollback_snapshot.session_id,
            )
            assert persisted is not None
            assert persisted.status == "CREATED"
            assert persisted.last_sequence == 1
            assert (
                await session.scalar(
                    select(func.count())
                    .select_from(SessionAction)
                    .where(SessionAction.session_id == rollback_snapshot.session_id)
                )
                == 0
            )
            assert (
                await session.scalar(
                    select(func.count())
                    .select_from(DiscussionEvent)
                    .where(DiscussionEvent.session_id == rollback_snapshot.session_id)
                )
                == 1
            )


def test_multi_event_reservation_is_contiguous_and_failure_rolls_back(
    migrated_database: TemporaryDatabaseContext,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_async(
        lambda: _verify_multi_event_reservation_and_rollback(
            migrated_database,
            monkeypatch,
        )
    )
