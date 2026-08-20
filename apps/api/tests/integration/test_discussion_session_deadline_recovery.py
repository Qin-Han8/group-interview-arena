import asyncio
from collections.abc import Callable, Coroutine
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from typing import Any, Protocol
from uuid import UUID, uuid4

import pytest
from sqlalchemy import URL, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from starlette.testclient import TestClient

from group_interview_arena_api.app import create_app
from group_interview_arena_api.core.config import (
    DatabaseSettings,
    Environment,
    Settings,
)
from group_interview_arena_api.db import DiscussionEvent, SimulationSession, User
from group_interview_arena_api.db.runtime import (
    create_database_engine,
    create_database_session_factory,
    dispose_database_engine,
)
from group_interview_arena_api.modules.discussion_sessions.deadline_recovery import (
    recover_due_sessions,
)
from group_interview_arena_api.modules.discussion_sessions.domain import (
    TIMED_PHASES,
    PhaseDurationPlan,
    SessionCommand,
)
from group_interview_arena_api.modules.discussion_sessions.service import (
    apply_session_command,
    create_session,
)
from group_interview_arena_api.modules.question_personas.seed import (
    INTERNAL_VALIDATION_BUNDLE,
    seed_question_persona_foundation,
)

pytestmark = pytest.mark.integration
LONG_PLAN = PhaseDurationPlan.from_seconds({status: 60 for status in TIMED_PHASES})


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
        await seed_question_persona_foundation(session_factory)
        yield session_factory
    finally:
        await dispose_database_engine(engine)


async def _seed_due_preparation(
    session_factory: async_sessionmaker[AsyncSession],
) -> tuple[UUID, UUID]:
    owner_id = uuid4()
    async with session_factory() as session:
        async with session.begin():
            session.add(
                User(
                    id=owner_id,
                    username=f"deadline_{owner_id.hex[:12]}",
                    password_hash="test-only-password-hash",
                )
            )
    async with session_factory() as session:
        snapshot = await create_session(
            session,
            owner_id=owner_id,
            question_version_id=INTERNAL_VALIDATION_BUNDLE.version_id,
        )
    async with session_factory() as session:
        await apply_session_command(
            session,
            owner_id=owner_id,
            command=SessionCommand(
                schema_version=1,
                command_type="session.start",
                session_id=snapshot.session_id,
                action_id=uuid4(),
                payload={},
            ),
            duration_plan=LONG_PLAN,
        )
    due_at = datetime.now(UTC) - timedelta(seconds=1)
    started_at = due_at - timedelta(seconds=60)
    async with session_factory() as session:
        async with session.begin():
            await session.execute(
                update(SimulationSession)
                .where(SimulationSession.id == snapshot.session_id)
                .values(
                    phase_started_at=started_at,
                    phase_deadline_at=due_at,
                )
            )
    return owner_id, snapshot.session_id


async def _event_sequences(
    session_factory: async_sessionmaker[AsyncSession],
    session_id: UUID,
) -> list[int]:
    async with session_factory() as session:
        return list(
            (
                await session.scalars(
                    select(DiscussionEvent.sequence)
                    .where(DiscussionEvent.session_id == session_id)
                    .order_by(DiscussionEvent.sequence)
                )
            ).all()
        )


async def _status(
    session_factory: async_sessionmaker[AsyncSession],
    session_id: UUID,
) -> str:
    async with session_factory() as session:
        row = await session.get(SimulationSession, session_id)
        assert row is not None
        return row.status


def test_startup_recovery_uses_durable_deadline_once(
    migrated_database: TemporaryDatabaseContext,
) -> None:
    async def scenario() -> tuple[UUID, list[int], str]:
        async with _session_factory(migrated_database) as session_factory:
            _owner_id, session_id = await _seed_due_preparation(session_factory)
            return (
                session_id,
                await _event_sequences(session_factory, session_id),
                await _status(session_factory, session_id),
            )

    session_id, before_sequences, before_status = run_async(scenario)
    assert before_sequences == [1, 2]
    assert before_status == "PREPARATION"

    application = create_app(
        Settings(environment=Environment.TEST),
        migrated_database.database_settings(),
    )
    with TestClient(
        application,
        backend_options={"loop_factory": asyncio.SelectorEventLoop},
    ):
        pass

    async def verify_once() -> tuple[list[int], str]:
        async with _session_factory(migrated_database) as session_factory:
            return (
                await _event_sequences(session_factory, session_id),
                await _status(session_factory, session_id),
            )

    after_sequences, after_status = run_async(verify_once)
    assert after_sequences == [1, 2, 3]
    assert after_status == "OPENING_STATEMENTS"

    with TestClient(
        application,
        backend_options={"loop_factory": asyncio.SelectorEventLoop},
    ):
        pass

    repeated_sequences, repeated_status = run_async(verify_once)
    assert repeated_sequences == [1, 2, 3]
    assert repeated_status == "OPENING_STATEMENTS"


def test_recover_due_sessions_is_idempotent_under_repeated_callers(
    migrated_database: TemporaryDatabaseContext,
) -> None:
    async def scenario() -> tuple[int, int, list[int], str]:
        async with _session_factory(migrated_database) as session_factory:
            _owner_id, session_id = await _seed_due_preparation(session_factory)
            changed_once = await recover_due_sessions(session_factory)
            changed_twice = await recover_due_sessions(session_factory)
            return (
                changed_once,
                changed_twice,
                await _event_sequences(session_factory, session_id),
                await _status(session_factory, session_id),
            )

    changed_once, changed_twice, sequences, status = run_async(scenario)
    assert changed_once == 1
    assert changed_twice == 0
    assert sequences == [1, 2, 3]
    assert status == "OPENING_STATEMENTS"
