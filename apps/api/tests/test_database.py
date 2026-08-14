import asyncio

import pytest
from pydantic import SecretStr
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from group_interview_arena_api.core.config import DatabaseSettings
from group_interview_arena_api.db.base import NAMING_CONVENTION, Base
from group_interview_arena_api.db.runtime import (
    create_database_engine,
    create_database_session_factory,
    dispose_database_engine,
)

DATABASE_PASSWORD = "engine-factory-secret"
DATABASE_URL = (
    "postgresql+psycopg://group_interview_arena:"
    f"{DATABASE_PASSWORD}@127.0.0.1:5432/group_interview_arena"
)
EXPECTED_NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


def _database_settings(database_url: str = DATABASE_URL) -> DatabaseSettings:
    return DatabaseSettings(database_url=SecretStr(database_url))


def test_base_is_sqlalchemy_declarative_base() -> None:
    assert issubclass(Base, DeclarativeBase)


def test_metadata_naming_convention_matches_baseline() -> None:
    assert NAMING_CONVENTION == EXPECTED_NAMING_CONVENTION
    assert dict(Base.metadata.naming_convention) == EXPECTED_NAMING_CONVENTION


def test_base_metadata_has_exact_identity_tables() -> None:
    assert set(Base.metadata.tables) == {"auth_sessions", "users"}


def test_psycopg_url_creates_async_engine() -> None:
    engine = create_database_engine(_database_settings())

    try:
        assert isinstance(engine, AsyncEngine)
        assert engine.url.drivername == "postgresql+psycopg"
        assert engine.dialect.name == "postgresql"
        assert engine.dialect.driver == "psycopg"
        assert engine.dialect.is_async is True
        assert engine.echo is False
    finally:
        asyncio.run(dispose_database_engine(engine))


def test_engine_repr_redacts_database_password() -> None:
    engine = create_database_engine(_database_settings())

    try:
        assert DATABASE_PASSWORD not in repr(engine)
        assert DATABASE_PASSWORD not in repr(engine.url)
        assert DATABASE_PASSWORD not in str(engine.url)
    finally:
        asyncio.run(dispose_database_engine(engine))


@pytest.mark.parametrize(
    "database_url",
    [
        "sqlite:///:memory:",
        "postgresql+asyncpg://user:wrong-driver-secret@127.0.0.1/database",
        "not a valid SQLAlchemy URL with malformed-secret",
    ],
)
def test_engine_factory_rejects_unsupported_or_malformed_urls(
    database_url: str,
) -> None:
    with pytest.raises(ValueError) as error:
        create_database_engine(_database_settings(database_url))

    assert "secret" not in str(error.value)


def test_engine_can_be_disposed_without_connecting() -> None:
    engine = create_database_engine(_database_settings())

    asyncio.run(dispose_database_engine(engine))


def test_session_factory_uses_async_session_defaults() -> None:
    engine = create_database_engine(_database_settings())
    session_factory = create_database_session_factory(engine)
    session = session_factory()

    try:
        assert isinstance(session_factory, async_sessionmaker)
        assert isinstance(session, AsyncSession)
        assert session.bind is engine
        assert session.sync_session.expire_on_commit is False
        assert session.sync_session.autoflush is True
    finally:
        asyncio.run(session.close())
        asyncio.run(dispose_database_engine(engine))
