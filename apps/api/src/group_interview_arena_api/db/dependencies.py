from collections.abc import AsyncIterator
from typing import cast

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

DATABASE_SESSION_FACTORY_STATE_KEY = "database_session_factory"


async def get_database_session(request: Request) -> AsyncIterator[AsyncSession]:
    """Yield one request-scoped session from the initialized app runtime."""
    candidate = getattr(
        request.app.state,
        DATABASE_SESSION_FACTORY_STATE_KEY,
        None,
    )
    if not isinstance(candidate, async_sessionmaker):
        raise RuntimeError("Database runtime is not initialized.")

    session_factory = cast(async_sessionmaker[AsyncSession], candidate)
    session = session_factory()
    try:
        yield session
    finally:
        if session.in_transaction():
            await session.rollback()
        await session.close()
