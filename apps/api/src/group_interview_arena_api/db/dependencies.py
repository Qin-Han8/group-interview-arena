from collections.abc import AsyncIterator
from typing import cast

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from starlette.requests import HTTPConnection

DATABASE_SESSION_FACTORY_STATE_KEY = "database_session_factory"


def get_database_session_factory_from_connection(
    connection: HTTPConnection,
) -> async_sessionmaker[AsyncSession]:
    candidate = getattr(
        connection.app.state,
        DATABASE_SESSION_FACTORY_STATE_KEY,
        None,
    )
    if not isinstance(candidate, async_sessionmaker):
        raise RuntimeError("Database runtime is not initialized.")

    return cast(async_sessionmaker[AsyncSession], candidate)


def get_database_session_factory(
    request: Request,
) -> async_sessionmaker[AsyncSession]:
    return get_database_session_factory_from_connection(request)


async def get_database_session(request: Request) -> AsyncIterator[AsyncSession]:
    """Yield one request-scoped session from the initialized app runtime."""
    session_factory = get_database_session_factory(request)
    session = session_factory()
    try:
        yield session
    finally:
        if session.in_transaction():
            await session.rollback()
        await session.close()
