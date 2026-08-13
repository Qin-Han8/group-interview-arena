from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from group_interview_arena_api.core.config import DatabaseSettings

_DATABASE_DRIVERNAME = "postgresql+psycopg"


def create_database_engine(settings: DatabaseSettings) -> AsyncEngine:
    try:
        database_url = make_url(settings.database_url.get_secret_value())
    except ArgumentError:
        raise ValueError("Database URL must be a valid SQLAlchemy URL.") from None

    if database_url.drivername != _DATABASE_DRIVERNAME:
        raise ValueError("Database URL must use postgresql+psycopg.")

    return create_async_engine(database_url, echo=False)


def create_database_session_factory(
    engine: AsyncEngine,
) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


async def dispose_database_engine(engine: AsyncEngine) -> None:
    await engine.dispose()
