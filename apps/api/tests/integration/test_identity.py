import asyncio
from collections.abc import Callable, Coroutine
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import UUID, uuid4

import pytest
from sqlalchemy import URL, select, text
from sqlalchemy.exc import IntegrityError

from group_interview_arena_api.core.config import DatabaseSettings
from group_interview_arena_api.db.models import AuthSession, User
from group_interview_arena_api.db.runtime import (
    create_database_engine,
    create_database_session_factory,
    dispose_database_engine,
)
from group_interview_arena_api.identity.credentials import (
    hash_password,
    normalize_username,
    verify_password,
)
from group_interview_arena_api.identity.sessions import (
    digest_session_token,
    generate_session_token,
    session_expires_at,
)

pytestmark = pytest.mark.integration


class TemporaryDatabaseContext(Protocol):
    database_name: str
    database_url: URL

    def database_settings(self) -> DatabaseSettings: ...


def run_async[T](operation: Callable[[], Coroutine[Any, Any, T]]) -> T:
    return asyncio.run(operation(), loop_factory=asyncio.SelectorEventLoop)


async def _exercise_identity_schema(
    temporary_database: TemporaryDatabaseContext,
) -> None:
    engine = create_database_engine(temporary_database.database_settings())
    session_factory = create_database_session_factory(engine)
    plaintext_password = "integration-only password phrase"
    password_hash = hash_password(plaintext_password)
    canonical_username = normalize_username("Integration_User")

    try:
        async with session_factory() as session:
            user = User(
                username=canonical_username,
                password_hash=password_hash,
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)

            assert isinstance(user.id, UUID)
            assert user.id.version == 4
            assert user.username == canonical_username
            assert user.password_hash != plaintext_password
            assert verify_password(plaintext_password, user.password_hash) is True
            assert user.created_at.utcoffset() == UTC.utcoffset(user.created_at)
            assert user.updated_at.utcoffset() == UTC.utcoffset(user.updated_at)
            user_id = user.id

            duplicate_user = User(
                username=canonical_username,
                password_hash=hash_password("another integration password"),
            )
            session.add(duplicate_user)
            with pytest.raises(IntegrityError):
                await session.commit()
            await session.rollback()

            invalid_session = AuthSession(
                user_id=uuid4(),
                token_hash=digest_session_token("invalid-user-session-token"),
                expires_at=session_expires_at(datetime(2026, 8, 14, tzinfo=UTC)),
            )
            session.add(invalid_session)
            with pytest.raises(IntegrityError):
                await session.commit()
            await session.rollback()

            raw_token = generate_session_token()
            token_hash = digest_session_token(raw_token)
            expires_at = session_expires_at(datetime(2026, 8, 14, tzinfo=UTC))
            auth_session = AuthSession(
                user_id=user_id,
                token_hash=token_hash,
                expires_at=expires_at,
            )
            session.add(auth_session)
            await session.commit()
            await session.refresh(auth_session)

            assert auth_session.token_hash == token_hash
            assert len(auth_session.token_hash) == 32
            assert auth_session.token_hash != raw_token.encode()
            assert auth_session.expires_at == expires_at
            assert auth_session.expires_at.utcoffset() == UTC.utcoffset(expires_at)

            duplicate_digest = AuthSession(
                user_id=user_id,
                token_hash=token_hash,
                expires_at=expires_at,
            )
            session.add(duplicate_digest)
            with pytest.raises(IntegrityError):
                await session.commit()
            await session.rollback()

            stored_user = await session.scalar(select(User).where(User.id == user_id))
            assert stored_user is not None
            await session.delete(stored_user)
            await session.commit()

            assert await session.scalar(select(AuthSession.id)) is None

        async with engine.connect() as connection:
            column_result = await connection.execute(
                text(
                    "SELECT table_name, column_name, data_type, "
                    "character_maximum_length, is_nullable "
                    "FROM information_schema.columns "
                    "WHERE table_schema = 'public' "
                    "AND table_name IN ('users', 'auth_sessions')"
                )
            )
            columns = {
                (
                    str(row[0]),
                    str(row[1]),
                    str(row[2]),
                    None if row[3] is None else int(row[3]),
                    str(row[4]),
                )
                for row in column_result
            }
            assert columns == {
                ("auth_sessions", "created_at", "timestamp with time zone", None, "NO"),
                ("auth_sessions", "expires_at", "timestamp with time zone", None, "NO"),
                ("auth_sessions", "id", "uuid", None, "NO"),
                ("auth_sessions", "token_hash", "bytea", None, "NO"),
                ("auth_sessions", "user_id", "uuid", None, "NO"),
                ("users", "created_at", "timestamp with time zone", None, "NO"),
                ("users", "id", "uuid", None, "NO"),
                ("users", "password_hash", "text", None, "NO"),
                ("users", "updated_at", "timestamp with time zone", None, "NO"),
                ("users", "username", "character varying", 32, "NO"),
            }

            constraint_result = await connection.execute(
                text(
                    "SELECT relation.relname, constraint_record.conname, "
                    "constraint_record.contype, constraint_record.confdeltype "
                    "FROM pg_constraint AS constraint_record "
                    "JOIN pg_class AS relation "
                    "ON relation.oid = constraint_record.conrelid "
                    "JOIN pg_namespace AS namespace "
                    "ON namespace.oid = relation.relnamespace "
                    "WHERE namespace.nspname = 'public' "
                    "AND relation.relname IN ('users', 'auth_sessions') "
                    "AND constraint_record.contype IN ('p', 'u', 'f')"
                )
            )
            constraints = {
                (str(row[0]), str(row[1]), str(row[2]), str(row[3]))
                for row in constraint_result
            }
            assert {(table, name, kind) for table, name, kind, _ in constraints} == {
                ("auth_sessions", "fk_auth_sessions_user_id_users", "f"),
                ("auth_sessions", "pk_auth_sessions", "p"),
                ("auth_sessions", "uq_auth_sessions_token_hash", "u"),
                ("users", "pk_users", "p"),
                ("users", "uq_users_username", "u"),
            }
            assert (
                "auth_sessions",
                "fk_auth_sessions_user_id_users",
                "f",
                "c",
            ) in constraints

            index_names = await connection.execute(
                text(
                    "SELECT indexname FROM pg_indexes "
                    "WHERE schemaname = 'public' "
                    "AND tablename IN ('users', 'auth_sessions')"
                )
            )
            assert set(index_names.scalars()) == {
                "ix_auth_sessions_expires_at",
                "pk_auth_sessions",
                "pk_users",
                "uq_auth_sessions_token_hash",
                "uq_users_username",
            }
    finally:
        await dispose_database_engine(engine)


def test_identity_schema_enforces_persistence_and_security_boundaries(
    migrated_database: TemporaryDatabaseContext,
) -> None:
    assert set(User.__table__.columns.keys()) == {
        "created_at",
        "id",
        "password_hash",
        "updated_at",
        "username",
    }
    assert set(AuthSession.__table__.columns.keys()) == {
        "created_at",
        "expires_at",
        "id",
        "token_hash",
        "user_id",
    }
    assert "password" not in User.__table__.columns
    assert "raw_token" not in AuthSession.__table__.columns

    run_async(lambda: _exercise_identity_schema(migrated_database))
