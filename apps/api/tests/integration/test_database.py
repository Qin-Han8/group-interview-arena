import asyncio
from collections.abc import Callable, Coroutine
from typing import Any, Protocol

import pytest
from sqlalchemy import URL, text

from group_interview_arena_api.core.config import DatabaseSettings
from group_interview_arena_api.db.runtime import (
    create_database_engine,
    create_database_session_factory,
    dispose_database_engine,
)

pytestmark = pytest.mark.integration


class TemporaryDatabaseContext(Protocol):
    database_name: str
    database_url: URL

    def database_settings(self) -> DatabaseSettings: ...


def run_async[T](operation: Callable[[], Coroutine[Any, Any, T]]) -> T:
    return asyncio.run(operation(), loop_factory=asyncio.SelectorEventLoop)


async def _verify_engine_and_session(
    temporary_database: TemporaryDatabaseContext,
) -> None:
    engine = create_database_engine(temporary_database.database_settings())
    session_factory = create_database_session_factory(engine)

    try:
        async with engine.connect() as connection:
            assert await connection.scalar(text("SELECT 1")) == 1
            server_version_num = await connection.scalar(
                text("SHOW server_version_num")
            )
            assert int(str(server_version_num)) // 10_000 == 18

        async with session_factory() as session:
            assert await session.scalar(text("SELECT 1")) == 1
    finally:
        await dispose_database_engine(engine)


async def _verify_commit(temporary_database: TemporaryDatabaseContext) -> None:
    engine = create_database_engine(temporary_database.database_settings())
    session_factory = create_database_session_factory(engine)

    try:
        async with engine.begin() as connection:
            await connection.execute(
                text("CREATE TABLE gia_test_transaction_probe (value integer NOT NULL)")
            )

        async with session_factory() as session:
            await session.execute(
                text("INSERT INTO gia_test_transaction_probe (value) VALUES (1)")
            )
            await session.commit()

        async with session_factory() as session:
            assert (
                await session.scalar(
                    text("SELECT count(*) FROM gia_test_transaction_probe")
                )
                == 1
            )
    finally:
        await dispose_database_engine(engine)


async def _verify_rollback(temporary_database: TemporaryDatabaseContext) -> None:
    engine = create_database_engine(temporary_database.database_settings())
    session_factory = create_database_session_factory(engine)

    try:
        async with engine.begin() as connection:
            await connection.execute(
                text("CREATE TABLE gia_test_transaction_probe (value integer NOT NULL)")
            )

        async with session_factory() as session:
            await session.execute(
                text("INSERT INTO gia_test_transaction_probe (value) VALUES (1)")
            )
            await session.rollback()

        async with session_factory() as session:
            assert (
                await session.scalar(
                    text("SELECT count(*) FROM gia_test_transaction_probe")
                )
                == 0
            )
    finally:
        await dispose_database_engine(engine)


def test_async_engine_and_session_connect_to_postgresql(
    temporary_database: TemporaryDatabaseContext,
) -> None:
    run_async(lambda: _verify_engine_and_session(temporary_database))


def test_async_session_commit_is_persisted(
    temporary_database: TemporaryDatabaseContext,
) -> None:
    run_async(lambda: _verify_commit(temporary_database))


def test_async_session_rollback_is_not_persisted(
    temporary_database: TemporaryDatabaseContext,
) -> None:
    run_async(lambda: _verify_rollback(temporary_database))


def test_database_guard_rejects_development_database(
    protected_database_name: str,
    temporary_database_name_guard: Callable[[str, str], None],
) -> None:
    with pytest.raises(ValueError, match="Unsafe temporary database name"):
        temporary_database_name_guard(
            protected_database_name,
            protected_database_name,
        )


@pytest.mark.parametrize(
    "unsafe_database_name",
    ["postgres", "template0", "template1", "test_db"],
)
def test_database_guard_rejects_system_or_unprefixed_database(
    unsafe_database_name: str,
    protected_database_name: str,
    temporary_database_name_guard: Callable[[str, str], None],
) -> None:
    with pytest.raises(ValueError, match="Unsafe temporary database name"):
        temporary_database_name_guard(
            unsafe_database_name,
            protected_database_name,
        )


def test_database_guard_accepts_exact_p1_1d_browser_database_name(
    protected_database_name: str,
    temporary_database_name_guard: Callable[[str, str], None],
) -> None:
    temporary_database_name_guard(
        "gia_p11d_012345abcdef",
        protected_database_name,
    )
