import asyncio
from collections.abc import Callable, Coroutine
from hashlib import sha256
from typing import Any, Protocol
from uuid import UUID, uuid4

import pytest
from sqlalchemy import URL, delete, func, select
from sqlalchemy.exc import IntegrityError
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

pytestmark = pytest.mark.integration

ACTION_PAYLOAD_DIGEST = sha256(
    b'{"payload":{},"schema_version":1,"type":"session.abort"}'
).digest()


class TemporaryDatabaseContext(Protocol):
    database_name: str
    database_url: URL

    def database_settings(self) -> DatabaseSettings: ...


def run_async[T](operation: Callable[[], Coroutine[Any, Any, T]]) -> T:
    return asyncio.run(operation(), loop_factory=asyncio.SelectorEventLoop)


async def _seed_session(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    last_sequence: int = 0,
) -> tuple[UUID, UUID]:
    user_id = uuid4()
    session_id = uuid4()
    async with session_factory() as database_session:
        async with database_session.begin():
            user = User(
                id=user_id,
                username=f"user_{user_id.hex[:12]}",
                password_hash="test-only-password-hash",
            )
            database_session.add(user)
            await database_session.flush()
            database_session.add(
                SimulationSession(
                    id=session_id,
                    owner_user_id=user_id,
                    status="CREATED",
                    last_sequence=last_sequence,
                )
            )
    return user_id, session_id


def _action(session_id: UUID, action_id: UUID | None = None) -> SessionAction:
    return SessionAction(
        session_id=session_id,
        action_id=action_id or uuid4(),
        command_version=1,
        command_type="session.abort",
        payload_digest=ACTION_PAYLOAD_DIGEST,
    )


def _event(
    session_id: UUID,
    sequence: int,
    *,
    action_id: UUID | None = None,
) -> DiscussionEvent:
    return DiscussionEvent(
        session_id=session_id,
        sequence=sequence,
        event_version=1,
        event_type="session.state_changed",
        causation_action_id=action_id,
        payload={"status": "ABORTED_USER"},
    )


async def _verify_owner_and_database_constraints(
    temporary_database: TemporaryDatabaseContext,
) -> None:
    engine = create_database_engine(temporary_database.database_settings())
    session_factory = create_database_session_factory(engine)

    try:
        user_id, session_id = await _seed_session(session_factory)

        async with session_factory() as database_session:
            database_session.add(
                SimulationSession(
                    id=uuid4(),
                    owner_user_id=uuid4(),
                    status="CREATED",
                )
            )
            with pytest.raises(IntegrityError):
                await database_session.commit()
            await database_session.rollback()

        action_id = uuid4()
        async with session_factory() as database_session:
            database_session.add(_action(session_id, action_id))
            await database_session.commit()

        async with session_factory() as database_session:
            database_session.add(_action(session_id, action_id))
            with pytest.raises(IntegrityError):
                await database_session.commit()
            await database_session.rollback()

        async with session_factory() as database_session:
            database_session.add(_event(session_id, 1))
            await database_session.commit()

        async with session_factory() as database_session:
            database_session.add(_event(session_id, 1))
            with pytest.raises(IntegrityError):
                await database_session.commit()
            await database_session.rollback()

        invalid_rows = [
            SimulationSession(
                id=uuid4(),
                owner_user_id=user_id,
                status="CREATED",
                last_sequence=-1,
            ),
            SessionAction(
                session_id=session_id,
                action_id=uuid4(),
                command_version=0,
                command_type="session.abort",
                payload_digest=ACTION_PAYLOAD_DIGEST,
            ),
            SessionAction(
                session_id=session_id,
                action_id=uuid4(),
                command_version=1,
                command_type="session.abort",
                payload_digest=b"short",
            ),
            _event(session_id, 0),
            DiscussionEvent(
                session_id=session_id,
                sequence=2,
                event_version=0,
                event_type="session.state_changed",
                causation_action_id=None,
                payload={"status": "ABORTED_USER"},
            ),
        ]
        for invalid_row in invalid_rows:
            async with session_factory() as database_session:
                database_session.add(invalid_row)
                with pytest.raises(IntegrityError):
                    await database_session.commit()
                await database_session.rollback()
    finally:
        await dispose_database_engine(engine)


async def _verify_durable_watermark_and_one_to_many_causation(
    temporary_database: TemporaryDatabaseContext,
) -> None:
    engine = create_database_engine(temporary_database.database_settings())
    session_factory = create_database_session_factory(engine)

    try:
        user_id, session_id = await _seed_session(session_factory)
        action_id = uuid4()
        async with session_factory() as database_session:
            async with database_session.begin():
                simulation_session = await database_session.get(
                    SimulationSession,
                    session_id,
                    with_for_update=True,
                )
                assert simulation_session is not None
                simulation_session.last_sequence = 2
                database_session.add(_action(session_id, action_id))
                await database_session.flush()
                database_session.add_all(
                    [
                        _event(session_id, 1, action_id=action_id),
                        _event(session_id, 2, action_id=action_id),
                    ]
                )

        async with session_factory() as database_session:
            persisted = await database_session.get(SimulationSession, session_id)
            assert persisted is not None
            assert persisted.last_sequence == 2
            stored_sequences = list(
                (
                    await database_session.scalars(
                        select(DiscussionEvent.sequence)
                        .where(
                            DiscussionEvent.session_id == session_id,
                            DiscussionEvent.causation_action_id == action_id,
                        )
                        .order_by(DiscussionEvent.sequence)
                    )
                ).all()
            )
            assert stored_sequences == [1, 2]

        async with session_factory() as database_session:
            await database_session.execute(delete(User).where(User.id == user_id))
            await database_session.commit()

        async with session_factory() as database_session:
            assert await database_session.get(SimulationSession, session_id) is None
            assert (
                await database_session.scalar(
                    select(func.count())
                    .select_from(SessionAction)
                    .where(SessionAction.session_id == session_id)
                )
                == 0
            )
            assert (
                await database_session.scalar(
                    select(func.count())
                    .select_from(DiscussionEvent)
                    .where(DiscussionEvent.session_id == session_id)
                )
                == 0
            )
    finally:
        await dispose_database_engine(engine)


async def _verify_concurrent_sequence_allocation(
    temporary_database: TemporaryDatabaseContext,
) -> None:
    engine = create_database_engine(temporary_database.database_settings())
    session_factory = create_database_session_factory(engine)
    first_has_lock = asyncio.Event()
    release_first = asyncio.Event()
    second_attempting_lock = asyncio.Event()

    try:
        _, session_id = await _seed_session(session_factory)

        async def allocate(action_id: UUID, *, hold_lock: bool) -> int:
            async with session_factory() as database_session:
                async with database_session.begin():
                    if not hold_lock:
                        second_attempting_lock.set()
                    simulation_session = await database_session.scalar(
                        select(SimulationSession)
                        .where(SimulationSession.id == session_id)
                        .with_for_update()
                    )
                    assert simulation_session is not None
                    if hold_lock:
                        first_has_lock.set()
                        await release_first.wait()
                    sequence = simulation_session.last_sequence + 1
                    simulation_session.last_sequence = sequence
                    database_session.add(_action(session_id, action_id))
                    await database_session.flush()
                    database_session.add(
                        _event(session_id, sequence, action_id=action_id)
                    )
                return sequence

        first = asyncio.create_task(allocate(uuid4(), hold_lock=True))
        await first_has_lock.wait()
        second = asyncio.create_task(allocate(uuid4(), hold_lock=False))
        await second_attempting_lock.wait()
        await asyncio.sleep(0)
        assert second.done() is False
        release_first.set()

        allocated = sorted(await asyncio.gather(first, second))
        assert allocated == [1, 2]

        async with session_factory() as database_session:
            persisted = await database_session.get(SimulationSession, session_id)
            assert persisted is not None
            assert persisted.last_sequence == 2
            sequences = list(
                (
                    await database_session.scalars(
                        select(DiscussionEvent.sequence)
                        .where(DiscussionEvent.session_id == session_id)
                        .order_by(DiscussionEvent.sequence)
                    )
                ).all()
            )
            assert sequences == [1, 2]
    finally:
        await dispose_database_engine(engine)


async def _verify_rollback_is_atomic(
    temporary_database: TemporaryDatabaseContext,
) -> None:
    engine = create_database_engine(temporary_database.database_settings())
    session_factory = create_database_session_factory(engine)

    class RollbackProbe(Exception):
        pass

    try:
        _, session_id = await _seed_session(session_factory)
        action_id = uuid4()
        with pytest.raises(RollbackProbe):
            async with session_factory() as database_session:
                async with database_session.begin():
                    simulation_session = await database_session.scalar(
                        select(SimulationSession)
                        .where(SimulationSession.id == session_id)
                        .with_for_update()
                    )
                    assert simulation_session is not None
                    simulation_session.last_sequence = 1
                    database_session.add(_action(session_id, action_id))
                    await database_session.flush()
                    database_session.add(_event(session_id, 1, action_id=action_id))
                    await database_session.flush()
                    raise RollbackProbe

        async with session_factory() as database_session:
            persisted = await database_session.get(SimulationSession, session_id)
            assert persisted is not None
            assert persisted.last_sequence == 0
            assert (
                await database_session.scalar(
                    select(func.count())
                    .select_from(SessionAction)
                    .where(SessionAction.session_id == session_id)
                )
                == 0
            )
            assert (
                await database_session.scalar(
                    select(func.count())
                    .select_from(DiscussionEvent)
                    .where(DiscussionEvent.session_id == session_id)
                )
                == 0
            )
    finally:
        await dispose_database_engine(engine)


def test_owner_fk_uniqueness_and_checks_are_database_enforced(
    migrated_database: TemporaryDatabaseContext,
) -> None:
    run_async(lambda: _verify_owner_and_database_constraints(migrated_database))


def test_last_sequence_and_action_to_events_are_durable(
    migrated_database: TemporaryDatabaseContext,
) -> None:
    run_async(
        lambda: _verify_durable_watermark_and_one_to_many_causation(migrated_database)
    )


def test_locked_session_row_serializes_concurrent_sequence_allocation(
    migrated_database: TemporaryDatabaseContext,
) -> None:
    run_async(lambda: _verify_concurrent_sequence_allocation(migrated_database))


def test_transaction_rollback_leaves_no_action_event_or_watermark_change(
    migrated_database: TemporaryDatabaseContext,
) -> None:
    run_async(lambda: _verify_rollback_is_atomic(migrated_database))
