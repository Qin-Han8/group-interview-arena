import asyncio
from collections.abc import AsyncGenerator, Callable, Coroutine
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from typing import Any, Protocol, cast

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient, Response
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher
from sqlalchemy import URL, func, select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from group_interview_arena_api import app as app_module
from group_interview_arena_api.app import create_app
from group_interview_arena_api.core.config import (
    DatabaseSettings,
    Environment,
    Settings,
)
from group_interview_arena_api.db.dependencies import (
    DATABASE_SESSION_FACTORY_STATE_KEY,
)
from group_interview_arena_api.db.models import AuthSession, User
from group_interview_arena_api.db.runtime import dispose_database_engine
from group_interview_arena_api.identity import service as auth_service
from group_interview_arena_api.identity.cookies import (
    SESSION_COOKIE_MAX_AGE,
    SESSION_COOKIE_NAME,
)
from group_interview_arena_api.identity.credentials import (
    ARGON2_HASH_LENGTH,
    ARGON2_SALT_LENGTH,
    verify_password,
)
from group_interview_arena_api.identity.service import DUMMY_PASSWORD_HASH
from group_interview_arena_api.identity.sessions import (
    SESSION_DURATION,
    digest_session_token,
    session_expires_at,
)

pytestmark = pytest.mark.integration

VALID_PASSWORD = "integration-only password phrase"


class TemporaryDatabaseContext(Protocol):
    database_name: str
    database_url: URL

    def database_settings(self) -> DatabaseSettings: ...


def run_async[T](operation: Callable[[], Coroutine[Any, Any, T]]) -> T:
    return asyncio.run(operation(), loop_factory=asyncio.SelectorEventLoop)


def _session_factory(application: FastAPI) -> async_sessionmaker[AsyncSession]:
    candidate = getattr(
        application.state,
        DATABASE_SESSION_FACTORY_STATE_KEY,
    )
    assert isinstance(candidate, async_sessionmaker)
    return cast(async_sessionmaker[AsyncSession], candidate)


@asynccontextmanager
async def _auth_client(
    temporary_database: TemporaryDatabaseContext,
    *,
    settings: Settings | None = None,
) -> AsyncGenerator[tuple[FastAPI, AsyncClient]]:
    application = create_app(
        settings or Settings(environment=Environment.TEST),
        temporary_database.database_settings(),
    )
    async with application.router.lifespan_context(application):
        async with AsyncClient(
            transport=ASGITransport(app=application),
            base_url="http://testserver",
        ) as client:
            yield application, client


def _cookie_value(response: Response) -> str:
    value = response.cookies.get(SESSION_COOKIE_NAME)
    assert value is not None
    assert value
    return value


def _assert_safe_error(response: Response, status_code: int, code: str) -> None:
    assert response.status_code == status_code
    assert response.json()["error"]["code"] == code
    assert VALID_PASSWORD not in response.text


async def _identity_counts(application: FastAPI) -> tuple[int, int]:
    async with _session_factory(application)() as session:
        users = await session.scalar(select(func.count()).select_from(User))
        auth_sessions = await session.scalar(
            select(func.count()).select_from(AuthSession)
        )
    return int(users or 0), int(auth_sessions or 0)


async def _register_persists_session_and_resolves_me(
    temporary_database: TemporaryDatabaseContext,
    disposed_engines: list[AsyncEngine],
) -> None:
    async with _auth_client(temporary_database) as (application, client):
        assert isinstance(application.state.database_engine, AsyncEngine)

        response = await client.post(
            "/auth/register",
            json={"username": "Register_User", "password": VALID_PASSWORD},
        )
        assert response.status_code == 201
        assert response.json()["username"] == "register_user"
        assert set(response.json()) == {"id", "username"}
        raw_token = _cookie_value(response)
        assert raw_token not in response.text
        assert VALID_PASSWORD not in response.text

        cookie_header = response.headers["set-cookie"].lower()
        assert "httponly" in cookie_header
        assert "samesite=lax" in cookie_header
        assert "path=/" in cookie_header
        assert f"max-age={SESSION_COOKIE_MAX_AGE}" in cookie_header
        assert "domain=" not in cookie_header
        assert "secure" not in cookie_header

        async with _session_factory(application)() as session:
            user = await session.scalar(
                select(User).where(User.username == "register_user")
            )
            assert user is not None
            stored_session = await session.scalar(
                select(AuthSession).where(AuthSession.user_id == user.id)
            )
            assert stored_session is not None
            initial_expiry = stored_session.expires_at
            assert stored_session.token_hash == digest_session_token(raw_token)
            assert stored_session.token_hash != raw_token.encode()
            assert user.password_hash != VALID_PASSWORD
            assert verify_password(VALID_PASSWORD, user.password_hash) is True
            assert (
                timedelta(days=6, hours=23)
                < (stored_session.expires_at - datetime.now(UTC))
                <= SESSION_DURATION
            )

        me_response = await client.get("/auth/me")
        assert me_response.status_code == 200
        assert me_response.json() == response.json()

        async with _session_factory(application)() as session:
            unchanged_expiry = await session.scalar(
                select(AuthSession.expires_at).where(
                    AuthSession.token_hash == digest_session_token(raw_token)
                )
            )
        assert unchanged_expiry == initial_expiry

        health_response = await client.get("/health")
        assert health_response.status_code == 200
        assert health_response.json() == {"status": "ok"}

    assert len(disposed_engines) == 1


def test_register_lifecycle_cookie_persistence_and_me(
    migrated_database: TemporaryDatabaseContext,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    disposed_engines: list[AsyncEngine] = []

    async def tracked_dispose(engine: AsyncEngine) -> None:
        await dispose_database_engine(engine)
        disposed_engines.append(engine)

    monkeypatch.setattr(app_module, "dispose_database_engine", tracked_dispose)
    run_async(
        lambda: _register_persists_session_and_resolves_me(
            migrated_database,
            disposed_engines,
        )
    )


async def _exercise_registration_failures(
    temporary_database: TemporaryDatabaseContext,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async with _auth_client(temporary_database) as (application, client):
        invalid_username = await client.post(
            "/auth/register",
            json={"username": "not valid", "password": VALID_PASSWORD},
        )
        _assert_safe_error(invalid_username, 422, "INVALID_USERNAME")

        invalid_password_value = "too short"
        invalid_password = await client.post(
            "/auth/register",
            json={"username": "valid_user", "password": invalid_password_value},
        )
        _assert_safe_error(invalid_password, 422, "INVALID_PASSWORD")
        assert invalid_password_value not in invalid_password.text

        first = await client.post(
            "/auth/register",
            json={"username": "Duplicate_User", "password": VALID_PASSWORD},
        )
        assert first.status_code == 201
        duplicate = await client.post(
            "/auth/register",
            json={
                "username": "duplicate_user",
                "password": "another integration password",
            },
        )
        _assert_safe_error(duplicate, 409, "USERNAME_UNAVAILABLE")

        collision_token = "integration-only-collision-token"
        monkeypatch.setattr(
            auth_service,
            "generate_session_token",
            lambda: collision_token,
        )
        seed = await client.post(
            "/auth/register",
            json={"username": "collision_seed", "password": VALID_PASSWORD},
        )
        assert seed.status_code == 201
        counts_before = await _identity_counts(application)

        rollback = await client.post(
            "/auth/register",
            json={
                "username": "rollback_user",
                "password": "rollback integration password",
            },
        )
        _assert_safe_error(rollback, 500, "INTERNAL_ERROR")

        assert await _identity_counts(application) == counts_before
        async with _session_factory(application)() as session:
            assert (
                await session.scalar(
                    select(User).where(User.username == "rollback_user")
                )
                is None
            )


def test_register_validation_duplicate_and_atomic_rollback(
    migrated_database: TemporaryDatabaseContext,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_async(lambda: _exercise_registration_failures(migrated_database, monkeypatch))


async def _exercise_login_contract(
    temporary_database: TemporaryDatabaseContext,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async with _auth_client(temporary_database) as (application, client):
        registered = await client.post(
            "/auth/register",
            json={"username": "Login_User", "password": VALID_PASSWORD},
        )
        assert registered.status_code == 201
        prelogin_token = _cookie_value(registered)

        login = await client.post(
            "/auth/login",
            json={"username": "LOGIN_USER", "password": VALID_PASSWORD},
        )
        assert login.status_code == 200
        assert login.json()["username"] == "login_user"
        login_token = _cookie_value(login)
        assert login_token != prelogin_token
        assert await _identity_counts(application) == (1, 2)

        wrong_password = await client.post(
            "/auth/login",
            json={
                "username": "login_user",
                "password": "incorrect integration password",
            },
        )
        _assert_safe_error(wrong_password, 401, "INVALID_CREDENTIALS")

        verify_calls: list[tuple[str, str]] = []
        real_verify = auth_service.verify_password_and_update

        def tracked_verify(
            password: str, password_hash: str
        ) -> tuple[bool, str | None]:
            verify_calls.append((password, password_hash))
            return real_verify(password, password_hash)

        monkeypatch.setattr(
            auth_service,
            "verify_password_and_update",
            tracked_verify,
        )
        unknown_user = await client.post(
            "/auth/login",
            json={
                "username": "unknown_user",
                "password": "incorrect integration password",
            },
        )
        _assert_safe_error(unknown_user, 401, "INVALID_CREDENTIALS")
        assert (
            unknown_user.json()["error"]["message"]
            == wrong_password.json()["error"]["message"]
        )
        assert len(verify_calls) == 1
        assert verify_calls[0][1] == DUMMY_PASSWORD_HASH


def test_login_generic_failure_dummy_work_and_session_fixation_defense(
    migrated_database: TemporaryDatabaseContext,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_async(lambda: _exercise_login_contract(migrated_database, monkeypatch))


def _old_password_hash(password: str) -> str:
    return PasswordHash(
        (
            Argon2Hasher(
                time_cost=2,
                memory_cost=32_768,
                parallelism=2,
                hash_len=ARGON2_HASH_LENGTH,
                salt_len=ARGON2_SALT_LENGTH,
            ),
        )
    ).hash(password)


async def _exercise_rehash_and_rollback(
    temporary_database: TemporaryDatabaseContext,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async with _auth_client(temporary_database) as (application, client):
        old_hash = _old_password_hash(VALID_PASSWORD)
        rollback_hash = _old_password_hash("rollback rehash password")
        collision_token = "integration-only-rehash-collision"

        async with _session_factory(application)() as session:
            async with session.begin():
                rehash_user = User(username="rehash_user", password_hash=old_hash)
                rollback_user = User(
                    username="rehash_rollback",
                    password_hash=rollback_hash,
                )
                session.add_all([rehash_user, rollback_user])
                await session.flush()
                session.add(
                    AuthSession(
                        user_id=rehash_user.id,
                        token_hash=digest_session_token(collision_token),
                        expires_at=session_expires_at(),
                    )
                )

        login = await client.post(
            "/auth/login",
            json={"username": "rehash_user", "password": VALID_PASSWORD},
        )
        assert login.status_code == 200
        async with _session_factory(application)() as session:
            updated_user = await session.scalar(
                select(User).where(User.username == "rehash_user")
            )
            assert updated_user is not None
            assert updated_user.password_hash != old_hash
            assert verify_password(VALID_PASSWORD, updated_user.password_hash) is True
            assert (
                await session.scalar(
                    select(func.count())
                    .select_from(AuthSession)
                    .where(AuthSession.user_id == updated_user.id)
                )
                == 2
            )

        monkeypatch.setattr(
            auth_service,
            "generate_session_token",
            lambda: collision_token,
        )
        failed_login = await client.post(
            "/auth/login",
            json={
                "username": "rehash_rollback",
                "password": "rollback rehash password",
            },
        )
        _assert_safe_error(failed_login, 500, "INTERNAL_ERROR")

        async with _session_factory(application)() as session:
            unchanged_user = await session.scalar(
                select(User).where(User.username == "rehash_rollback")
            )
            assert unchanged_user is not None
            assert unchanged_user.password_hash == rollback_hash
            assert (
                await session.scalar(
                    select(func.count())
                    .select_from(AuthSession)
                    .where(AuthSession.user_id == unchanged_user.id)
                )
                == 0
            )


def test_login_rehash_and_session_failure_rollback_are_atomic(
    migrated_database: TemporaryDatabaseContext,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_async(lambda: _exercise_rehash_and_rollback(migrated_database, monkeypatch))


async def _exercise_me_failures(
    temporary_database: TemporaryDatabaseContext,
) -> None:
    async with _auth_client(temporary_database) as (application, client):
        missing = await client.get("/auth/me")
        _assert_safe_error(missing, 401, "AUTHENTICATION_REQUIRED")

        client.cookies.set(SESSION_COOKIE_NAME, "unknown-session-token")
        unknown = await client.get("/auth/me")
        _assert_safe_error(unknown, 401, "AUTHENTICATION_REQUIRED")

        expired_raw_token = "integration-only-expired-token"
        async with _session_factory(application)() as session:
            async with session.begin():
                user = User(
                    username="expired_user",
                    password_hash=_old_password_hash(VALID_PASSWORD),
                )
                session.add(user)
                await session.flush()
                session.add(
                    AuthSession(
                        user_id=user.id,
                        token_hash=digest_session_token(expired_raw_token),
                        expires_at=datetime.now(UTC) - timedelta(seconds=1),
                    )
                )

        client.cookies.set(SESSION_COOKIE_NAME, expired_raw_token)
        expired = await client.get("/auth/me")
        _assert_safe_error(expired, 401, "AUTHENTICATION_REQUIRED")


def test_me_rejects_missing_unknown_and_expired_sessions(
    migrated_database: TemporaryDatabaseContext,
) -> None:
    run_async(lambda: _exercise_me_failures(migrated_database))


async def _exercise_logout_contract(
    temporary_database: TemporaryDatabaseContext,
) -> None:
    async with _auth_client(temporary_database) as (application, client):
        registered = await client.post(
            "/auth/register",
            json={"username": "logout_user", "password": VALID_PASSWORD},
        )
        old_token = _cookie_value(registered)
        login = await client.post(
            "/auth/login",
            json={"username": "logout_user", "password": VALID_PASSWORD},
        )
        current_token = _cookie_value(login)
        assert current_token != old_token

        logout = await client.post("/auth/logout")
        assert logout.status_code == 204
        assert logout.content == b""
        clear_header = logout.headers["set-cookie"].lower()
        assert clear_header.startswith(f'{SESSION_COOKIE_NAME}=""')
        assert "max-age=0" in clear_header
        assert "path=/" in clear_header

        async with _session_factory(application)() as session:
            digests = set((await session.scalars(select(AuthSession.token_hash))).all())
        assert digest_session_token(current_token) not in digests
        assert digest_session_token(old_token) in digests

        after_logout = await client.get("/auth/me")
        _assert_safe_error(after_logout, 401, "AUTHENTICATION_REQUIRED")

        async with AsyncClient(
            transport=ASGITransport(app=application),
            base_url="http://testserver",
        ) as old_session_client:
            old_session_client.cookies.set(SESSION_COOKIE_NAME, old_token)
            old_me = await old_session_client.get("/auth/me")
            assert old_me.status_code == 200
            assert old_me.json()["username"] == "logout_user"

        async with AsyncClient(
            transport=ASGITransport(app=application),
            base_url="http://testserver",
        ) as idempotent_client:
            missing = await idempotent_client.post("/auth/logout")
            assert missing.status_code == 204
            assert "max-age=0" in missing.headers["set-cookie"].lower()

            idempotent_client.cookies.set(
                SESSION_COOKIE_NAME,
                "unknown-session-token",
            )
            unknown = await idempotent_client.post("/auth/logout")
            assert unknown.status_code == 204

        async with _session_factory(application)() as session:
            assert (
                await session.scalar(select(func.count()).select_from(AuthSession)) == 1
            )


def test_logout_deletes_exact_session_and_is_idempotent(
    migrated_database: TemporaryDatabaseContext,
) -> None:
    run_async(lambda: _exercise_logout_contract(migrated_database))
