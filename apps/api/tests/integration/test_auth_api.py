import asyncio
import logging
from collections.abc import AsyncGenerator, Callable, Coroutine
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from typing import Any, Protocol, cast

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient, Response
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher
from pydantic import SecretStr
from sqlalchemy import URL, event, func, select
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
from group_interview_arena_api.db.models import (
    AuthRateLimitBucket,
    AuthSession,
    BetaInvitation,
    User,
)
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
from group_interview_arena_api.identity.invitations import (
    digest_invitation_code,
    generate_invitations,
)
from group_interview_arena_api.identity.service import DUMMY_PASSWORD_HASH
from group_interview_arena_api.identity.sessions import (
    SESSION_DURATION,
    digest_session_token,
    session_expires_at,
)
from tests.auth_test_helpers import create_test_invitation

pytestmark = pytest.mark.integration

VALID_PASSWORD = "Integration-only password 1!"
TRUSTED_ORIGIN = "http://localhost:3000"
AUTH_POST_HEADERS = {"Origin": TRUSTED_ORIGIN, "X-GIA-CSRF": "1"}


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
        settings
        or Settings(
            environment=Environment.TEST,
            cors_origins=(TRUSTED_ORIGIN,),
        ),
        temporary_database.database_settings(),
    )
    async with application.router.lifespan_context(application):
        async with AsyncClient(
            transport=ASGITransport(app=application),
            base_url="http://testserver",
            headers=AUTH_POST_HEADERS,
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


async def _registration_payload(
    application: FastAPI,
    *,
    username: str,
    password: str,
) -> dict[str, str]:
    return {
        "username": username,
        "password": password,
        "invite_code": await create_test_invitation(_session_factory(application)),
    }


async def _register_persists_session_and_resolves_me(
    temporary_database: TemporaryDatabaseContext,
    disposed_engines: list[AsyncEngine],
) -> None:
    async with _auth_client(temporary_database) as (application, client):
        assert isinstance(application.state.database_engine, AsyncEngine)

        response = await client.post(
            "/auth/register",
            json=await _registration_payload(
                application,
                username="Register_User",
                password=VALID_PASSWORD,
            ),
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
            json=await _registration_payload(
                application,
                username="not valid",
                password=VALID_PASSWORD,
            ),
        )
        _assert_safe_error(invalid_username, 422, "INVALID_USERNAME")

        invalid_password_value = "too short"
        invalid_password = await client.post(
            "/auth/register",
            json=await _registration_payload(
                application,
                username="valid_user",
                password=invalid_password_value,
            ),
        )
        _assert_safe_error(invalid_password, 422, "INVALID_PASSWORD")
        assert invalid_password_value not in invalid_password.text

        first = await client.post(
            "/auth/register",
            json={
                "username": "Duplicate_User",
                "password": VALID_PASSWORD,
                "invite_code": await create_test_invitation(
                    _session_factory(application)
                ),
            },
        )
        assert first.status_code == 201
        duplicate_invite = await create_test_invitation(_session_factory(application))
        duplicate = await client.post(
            "/auth/register",
            json={
                "username": "duplicate_user",
                "password": "Another integration password 2!",
                "invite_code": duplicate_invite,
            },
        )
        _assert_safe_error(duplicate, 409, "ENROLLMENT_UNAVAILABLE")
        async with _session_factory(application)() as session:
            preserved_duplicate_invite = await session.scalar(
                select(BetaInvitation).where(
                    BetaInvitation.code_digest
                    == digest_invitation_code(duplicate_invite)
                )
            )
        assert preserved_duplicate_invite is not None
        assert preserved_duplicate_invite.consumed_at is None

        collision_token = "integration-only-collision-token"
        monkeypatch.setattr(
            auth_service,
            "generate_session_token",
            lambda: collision_token,
        )
        seed = await client.post(
            "/auth/register",
            json=await _registration_payload(
                application,
                username="collision_seed",
                password=VALID_PASSWORD,
            ),
        )
        assert seed.status_code == 201
        counts_before = await _identity_counts(application)
        rollback_invite = await create_test_invitation(_session_factory(application))

        rollback = await client.post(
            "/auth/register",
            json={
                "username": "rollback_user",
                "password": "Rollback integration password 3!",
                "invite_code": rollback_invite,
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
            preserved_rollback_invite = await session.scalar(
                select(BetaInvitation).where(
                    BetaInvitation.code_digest
                    == digest_invitation_code(rollback_invite)
                )
            )
            assert preserved_rollback_invite is not None
            assert preserved_rollback_invite.consumed_at is None


def test_register_validation_duplicate_and_atomic_rollback(
    migrated_database: TemporaryDatabaseContext,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_async(lambda: _exercise_registration_failures(migrated_database, monkeypatch))


async def _exercise_invitation_lifecycle_and_concurrency(
    temporary_database: TemporaryDatabaseContext,
    caplog: pytest.LogCaptureFixture,
) -> None:
    async with _auth_client(temporary_database) as (application, client):
        factory = _session_factory(application)
        now = datetime.now(UTC)
        invalid_code = "invalid-invitation-secret"
        invalid = await client.post(
            "/auth/register",
            json={
                "username": "invalid_invite",
                "password": VALID_PASSWORD,
                "invite_code": invalid_code,
            },
        )

        async with factory() as session:
            expired = await generate_invitations(
                session,
                count=1,
                expires_in_days=1,
                label="expired-test",
                reference_time=now - timedelta(days=2),
            )
        expired_code = expired[0].raw_code
        expired_response = await client.post(
            "/auth/register",
            json={
                "username": "expired_invite",
                "password": VALID_PASSWORD,
                "invite_code": expired_code,
            },
        )

        async with factory() as session:
            revoked_generated = await generate_invitations(
                session,
                count=1,
                label="revoked-test",
            )
            revoked_code = revoked_generated[0].raw_code
        async with factory() as session, session.begin():
            revoked_invitation = await session.scalar(
                select(BetaInvitation).where(
                    BetaInvitation.code_digest == digest_invitation_code(revoked_code)
                )
            )
            assert revoked_invitation is not None
            revoked_invitation.revoked_at = datetime.now(UTC)
        revoked_response = await client.post(
            "/auth/register",
            json={
                "username": "revoked_invite",
                "password": VALID_PASSWORD,
                "invite_code": revoked_code,
            },
        )

        reused_code = await create_test_invitation(factory)
        accepted = await client.post(
            "/auth/register",
            json={
                "username": "accepted_invite",
                "password": VALID_PASSWORD,
                "invite_code": reused_code,
            },
        )
        assert accepted.status_code == 201
        reused = await client.post(
            "/auth/register",
            json={
                "username": "reused_invite",
                "password": VALID_PASSWORD,
                "invite_code": reused_code,
            },
        )

        for response in (invalid, expired_response, revoked_response, reused):
            _assert_safe_error(response, 409, "ENROLLMENT_UNAVAILABLE")
            assert response.json()["error"]["message"] == "Enrollment is unavailable."

        concurrent_code = await create_test_invitation(factory)
        transport = ASGITransport(app=application)
        async with (
            AsyncClient(
                transport=transport,
                base_url="http://testserver",
                headers=AUTH_POST_HEADERS,
            ) as first_client,
            AsyncClient(
                transport=transport,
                base_url="http://testserver",
                headers=AUTH_POST_HEADERS,
            ) as second_client,
        ):
            first_response, second_response = await asyncio.gather(
                first_client.post(
                    "/auth/register",
                    json={
                        "username": "concurrent_first",
                        "password": VALID_PASSWORD,
                        "invite_code": concurrent_code,
                    },
                ),
                second_client.post(
                    "/auth/register",
                    json={
                        "username": "concurrent_second",
                        "password": VALID_PASSWORD,
                        "invite_code": concurrent_code,
                    },
                ),
            )
        assert sorted((first_response.status_code, second_response.status_code)) == [
            201,
            409,
        ]
        failed = (
            first_response if first_response.status_code == 409 else second_response
        )
        _assert_safe_error(failed, 409, "ENROLLMENT_UNAVAILABLE")

        async with factory() as session:
            invitation = await session.scalar(
                select(BetaInvitation).where(BetaInvitation.consumed_at.is_not(None))
            )
            concurrent_users = await session.scalar(
                select(func.count())
                .select_from(User)
                .where(User.username.in_(("concurrent_first", "concurrent_second")))
            )
        assert invitation is not None
        assert concurrent_users == 1

    for secret in (
        invalid_code,
        expired_code,
        revoked_code,
        reused_code,
        concurrent_code,
    ):
        assert secret not in caplog.text


def test_invitation_failures_are_generic_and_consumption_is_atomic(
    migrated_database: TemporaryDatabaseContext,
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.INFO)
    run_async(
        lambda: _exercise_invitation_lifecycle_and_concurrency(
            migrated_database,
            caplog,
        )
    )


async def _exercise_durable_rate_limits(
    temporary_database: TemporaryDatabaseContext,
) -> None:
    limiter_settings = Settings(
        environment=Environment.TEST,
        cors_origins=(TRUSTED_ORIGIN,),
        auth_rate_limit_hmac_key=SecretStr("unit-only-rate-limit-key-32-bytes"),
        auth_login_source_limit=1,
    )
    async with _auth_client(
        temporary_database,
        settings=limiter_settings,
    ) as (application, client):
        registered = await client.post(
            "/auth/register",
            json=await _registration_payload(
                application,
                username="limited_login",
                password=VALID_PASSWORD,
            ),
        )
        assert registered.status_code == 201
        client.cookies.clear()
        first = await client.post(
            "/auth/login",
            json={"username": "limited_login", "password": "wrong-password"},
        )
        _assert_safe_error(first, 401, "INVALID_CREDENTIALS")
        blocked = await client.post(
            "/auth/login",
            json={"username": "limited_login", "password": VALID_PASSWORD},
        )
        _assert_safe_error(blocked, 429, "AUTH_RATE_LIMITED")
        assert blocked.headers["retry-after"] == "900"
        async with _session_factory(application)() as session:
            source_bucket = await session.scalar(
                select(AuthRateLimitBucket).where(
                    AuthRateLimitBucket.scope == "LOGIN_SOURCE"
                )
            )
        assert source_bucket is not None
        assert source_bucket.attempt_count == 2
        assert source_bucket.blocked_until is not None

    async with _auth_client(
        temporary_database,
        settings=limiter_settings,
    ) as (restarted_application, restarted_client):
        still_blocked = await restarted_client.post(
            "/auth/login",
            json={"username": "limited_login", "password": VALID_PASSWORD},
        )
        _assert_safe_error(still_blocked, 429, "AUTH_RATE_LIMITED")
        async with _session_factory(restarted_application)() as session:
            persisted_source_bucket = await session.scalar(
                select(AuthRateLimitBucket).where(
                    AuthRateLimitBucket.scope == "LOGIN_SOURCE"
                )
            )
        assert persisted_source_bucket is not None
        assert persisted_source_bucket.attempt_count == 3
        assert persisted_source_bucket.blocked_until is not None


def test_login_rate_limit_is_durable_across_application_restart(
    migrated_database: TemporaryDatabaseContext,
) -> None:
    run_async(lambda: _exercise_durable_rate_limits(migrated_database))


def _limited_settings(
    key_suffix: str,
    *,
    register_global_limit: int = 200,
    register_source_limit: int = 20,
    register_invite_limit: int = 5,
    login_global_limit: int = 1_200,
    login_source_limit: int = 60,
    login_account_shard_limit: int = 10,
) -> Settings:
    return Settings(
        environment=Environment.TEST,
        cors_origins=(TRUSTED_ORIGIN,),
        auth_trusted_caddy_mode=True,
        auth_rate_limit_hmac_key=SecretStr(
            f"integration-rate-limit-key-{key_suffix}-32-bytes"
        ),
        auth_register_global_limit=register_global_limit,
        auth_register_source_limit=register_source_limit,
        auth_register_invite_limit=register_invite_limit,
        auth_login_global_limit=login_global_limit,
        auth_login_source_limit=login_source_limit,
        auth_login_account_shard_limit=login_account_shard_limit,
    )


def _source_headers(source: str) -> dict[str, str]:
    return {**AUTH_POST_HEADERS, "X-GIA-Client-IP": source}


def _assert_generic_rate_limit(response: Response) -> None:
    _assert_safe_error(response, 429, "AUTH_RATE_LIMITED")
    assert response.headers["retry-after"] == "900"
    assert response.json()["error"]["message"] == (
        "Authentication request rate limit exceeded."
    )


async def _rate_limit_scope_count(application: FastAPI, scope: str) -> int:
    async with _session_factory(application)() as session:
        count = await session.scalar(
            select(func.count())
            .select_from(AuthRateLimitBucket)
            .where(AuthRateLimitBucket.scope == scope)
        )
    assert count is not None
    return count


async def _exercise_register_global_denial_stops_source_bookkeeping(
    temporary_database: TemporaryDatabaseContext,
) -> None:
    settings = _limited_settings(
        "register-global-short-circuit",
        register_global_limit=1,
    )
    async with _auth_client(temporary_database, settings=settings) as (
        application,
        client,
    ):
        first = await client.post(
            "/auth/register",
            headers=_source_headers("192.0.2.70"),
            json={
                "username": "register_global_first",
                "password": VALID_PASSWORD,
                "invite_code": "unknown-register-global-first",
            },
        )
        _assert_safe_error(first, 409, "ENROLLMENT_UNAVAILABLE")

        for suffix in range(5):
            blocked = await client.post(
                "/auth/register",
                headers=_source_headers(f"198.51.100.{suffix + 1}"),
                json={
                    "username": f"register_global_blocked_{suffix}",
                    "password": VALID_PASSWORD,
                    "invite_code": f"unknown-register-global-{suffix}",
                },
            )
            _assert_generic_rate_limit(blocked)

        assert await _rate_limit_scope_count(application, "REGISTER_SOURCE") == 1


def test_register_global_denial_does_not_create_source_buckets(
    migrated_database: TemporaryDatabaseContext,
) -> None:
    run_async(
        lambda: _exercise_register_global_denial_stops_source_bookkeeping(
            migrated_database
        )
    )


async def _exercise_login_global_denial_stops_lower_priority_bookkeeping(
    temporary_database: TemporaryDatabaseContext,
) -> None:
    settings = _limited_settings(
        "login-global-short-circuit",
        login_global_limit=1,
        login_source_limit=200,
        login_account_shard_limit=200,
    )
    async with _auth_client(temporary_database, settings=settings) as (
        application,
        client,
    ):
        first = await client.post(
            "/auth/login",
            headers=_source_headers("192.0.2.80"),
            json={"username": "login_global_first", "password": "wrong-password"},
        )
        _assert_safe_error(first, 401, "INVALID_CREDENTIALS")

        for suffix in range(5):
            blocked = await client.post(
                "/auth/login",
                headers=_source_headers(f"203.0.113.{suffix + 1}"),
                json={
                    "username": f"login_global_blocked_{suffix}",
                    "password": "wrong-password",
                },
            )
            _assert_generic_rate_limit(blocked)

        assert await _rate_limit_scope_count(application, "LOGIN_SOURCE") == 1
        assert (
            await _rate_limit_scope_count(application, "LOGIN_ACCOUNT_SHARD") == 1
        )


def test_login_global_denial_does_not_create_lower_priority_buckets(
    migrated_database: TemporaryDatabaseContext,
) -> None:
    run_async(
        lambda: _exercise_login_global_denial_stops_lower_priority_bookkeeping(
            migrated_database
        )
    )


async def _exercise_login_source_denial_stops_account_shard_bookkeeping(
    temporary_database: TemporaryDatabaseContext,
) -> None:
    settings = _limited_settings(
        "login-source-short-circuit",
        login_global_limit=200,
        login_source_limit=1,
        login_account_shard_limit=200,
    )
    source_headers = _source_headers("192.0.2.90")
    async with _auth_client(temporary_database, settings=settings) as (
        application,
        client,
    ):
        first = await client.post(
            "/auth/login",
            headers=source_headers,
            json={"username": "login_source_first", "password": "wrong-password"},
        )
        _assert_safe_error(first, 401, "INVALID_CREDENTIALS")

        for suffix in range(20):
            blocked = await client.post(
                "/auth/login",
                headers=source_headers,
                json={
                    "username": f"login_source_blocked_{suffix}",
                    "password": "wrong-password",
                },
            )
            _assert_generic_rate_limit(blocked)

        assert (
            await _rate_limit_scope_count(application, "LOGIN_ACCOUNT_SHARD") == 1
        )


def test_login_source_denial_does_not_create_account_shard_buckets(
    migrated_database: TemporaryDatabaseContext,
) -> None:
    run_async(
        lambda: _exercise_login_source_denial_stops_account_shard_bookkeeping(
            migrated_database
        )
    )


async def _exercise_each_rate_limit_scope(
    temporary_database: TemporaryDatabaseContext,
) -> None:
    register_cases = (
        (
            _limited_settings("register-global", register_global_limit=1),
            _source_headers("192.0.2.10"),
            _source_headers("192.0.2.11"),
        ),
        (
            _limited_settings("register-source", register_source_limit=1),
            _source_headers("192.0.2.20"),
            _source_headers("192.0.2.20"),
        ),
    )
    for index, (settings, first_headers, second_headers) in enumerate(register_cases):
        async with _auth_client(temporary_database, settings=settings) as (
            _application,
            client,
        ):
            first = await client.post(
                "/auth/register",
                headers=first_headers,
                json={
                    "username": f"register_scope_{index}_first",
                    "password": VALID_PASSWORD,
                    "invite_code": f"unknown-invite-{index}-first",
                },
            )
            _assert_safe_error(first, 409, "ENROLLMENT_UNAVAILABLE")
            blocked = await client.post(
                "/auth/register",
                headers=second_headers,
                json={
                    "username": f"register_scope_{index}_second",
                    "password": VALID_PASSWORD,
                    "invite_code": f"unknown-invite-{index}-second",
                },
            )
            _assert_generic_rate_limit(blocked)

    invite_settings = _limited_settings(
        "register-invite",
        register_invite_limit=1,
    )
    async with _auth_client(temporary_database, settings=invite_settings) as (
        application,
        client,
    ):
        invite_code = await create_test_invitation(_session_factory(application))
        first = await client.post(
            "/auth/register",
            headers=_source_headers("192.0.2.30"),
            json={
                "username": "register_invite_first",
                "password": "too short",
                "invite_code": invite_code,
            },
        )
        _assert_safe_error(first, 422, "INVALID_PASSWORD")
        blocked = await client.post(
            "/auth/register",
            headers=_source_headers("192.0.2.31"),
            json={
                "username": "register_invite_second",
                "password": VALID_PASSWORD,
                "invite_code": invite_code,
            },
        )
        _assert_generic_rate_limit(blocked)

    login_cases = (
        (
            _limited_settings("login-global", login_global_limit=1),
            "login_global_first",
            "login_global_second",
            _source_headers("192.0.2.40"),
            _source_headers("192.0.2.41"),
        ),
        (
            _limited_settings("login-source", login_source_limit=1),
            "login_source_first",
            "login_source_second",
            _source_headers("192.0.2.50"),
            _source_headers("192.0.2.50"),
        ),
        (
            _limited_settings(
                "login-account-shard",
                login_account_shard_limit=1,
            ),
            "login_shard_user",
            "LOGIN_SHARD_USER",
            _source_headers("192.0.2.60"),
            _source_headers("192.0.2.61"),
        ),
    )
    for (
        settings,
        first_username,
        second_username,
        first_headers,
        second_headers,
    ) in login_cases:
        async with _auth_client(temporary_database, settings=settings) as (
            _application,
            client,
        ):
            first = await client.post(
                "/auth/login",
                headers=first_headers,
                json={"username": first_username, "password": "wrong-password"},
            )
            _assert_safe_error(first, 401, "INVALID_CREDENTIALS")
            blocked = await client.post(
                "/auth/login",
                headers=second_headers,
                json={"username": second_username, "password": "wrong-password"},
            )
            _assert_generic_rate_limit(blocked)


def test_each_register_and_login_rate_limit_scope_is_enforced_generically(
    migrated_database: TemporaryDatabaseContext,
) -> None:
    run_async(lambda: _exercise_each_rate_limit_scope(migrated_database))


async def _exercise_random_invite_cardinality(
    temporary_database: TemporaryDatabaseContext,
) -> None:
    settings = Settings(
        environment=Environment.TEST,
        cors_origins=(TRUSTED_ORIGIN,),
        auth_rate_limit_hmac_key=SecretStr("unit-only-rate-limit-key-32-bytes"),
    )
    async with _auth_client(temporary_database, settings=settings) as (
        application,
        client,
    ):
        for suffix in range(3):
            response = await client.post(
                "/auth/register",
                json={
                    "username": f"random_invite_{suffix}",
                    "password": VALID_PASSWORD,
                    "invite_code": f"random-secret-{suffix}",
                },
            )
            _assert_safe_error(response, 409, "ENROLLMENT_UNAVAILABLE")
        async with _session_factory(application)() as session:
            scopes = list(
                (
                    await session.scalars(
                        select(AuthRateLimitBucket.scope).where(
                            AuthRateLimitBucket.scope.like("REGISTER_%")
                        )
                    )
                ).all()
            )
            digests = list(
                (
                    await session.scalars(
                        select(AuthRateLimitBucket.key_digest).where(
                            AuthRateLimitBucket.scope.like("REGISTER_%")
                        )
                    )
                ).all()
            )
        assert sorted(scopes) == ["REGISTER_GLOBAL", "REGISTER_SOURCE"]
        assert all(len(value) == 32 for value in digests)
        assert all(b"127.0.0.1" not in value for value in digests)


def test_random_invites_do_not_create_unbounded_rate_limit_buckets(
    migrated_database: TemporaryDatabaseContext,
) -> None:
    run_async(lambda: _exercise_random_invite_cardinality(migrated_database))


async def _exercise_client_source_privacy(
    temporary_database: TemporaryDatabaseContext,
    caplog: pytest.LogCaptureFixture,
) -> None:
    raw_source = "2001:db8::10"
    raw_hmac_key = "privacy-only-rate-limit-key-32-bytes"
    settings = Settings(
        environment=Environment.TEST,
        cors_origins=(TRUSTED_ORIGIN,),
        auth_trusted_caddy_mode=True,
        auth_rate_limit_hmac_key=SecretStr(raw_hmac_key),
    )
    async with _auth_client(temporary_database, settings=settings) as (
        application,
        client,
    ):
        response = await client.post(
            "/auth/login",
            headers=_source_headers(raw_source),
            json={"username": "privacy_probe", "password": "wrong-password"},
        )
        _assert_safe_error(response, 401, "INVALID_CREDENTIALS")
        async with _session_factory(application)() as session:
            digests = list(
                (await session.scalars(select(AuthRateLimitBucket.key_digest))).all()
            )

    assert digests
    assert all(raw_source.encode() not in digest for digest in digests)
    assert raw_source not in caplog.text
    assert raw_hmac_key not in caplog.text
    assert raw_source not in response.text
    assert raw_hmac_key not in response.text


def test_raw_client_source_and_hmac_key_are_absent_from_logs_database_and_response(
    migrated_database: TemporaryDatabaseContext,
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.INFO)
    run_async(lambda: _exercise_client_source_privacy(migrated_database, caplog))


async def _exercise_register_limiter_precedes_invitation_lookup(
    temporary_database: TemporaryDatabaseContext,
) -> None:
    settings = Settings(
        environment=Environment.TEST,
        cors_origins=(TRUSTED_ORIGIN,),
        auth_rate_limit_hmac_key=SecretStr("unit-only-rate-limit-key-32-bytes"),
    )
    async with _auth_client(temporary_database, settings=settings) as (
        application,
        client,
    ):
        statements: list[str] = []
        engine = application.state.database_engine
        assert isinstance(engine, AsyncEngine)

        def record_statement(
            _connection: object,
            _cursor: object,
            statement: str,
            _parameters: object,
            _context: object,
            _executemany: bool,
        ) -> None:
            statements.append(statement.lower())

        event.listen(engine.sync_engine, "before_cursor_execute", record_statement)
        try:
            response = await client.post(
                "/auth/register",
                json={
                    "username": "ordering_probe",
                    "password": VALID_PASSWORD,
                    "invite_code": "unknown-ordering-probe",
                },
            )
        finally:
            event.remove(
                engine.sync_engine,
                "before_cursor_execute",
                record_statement,
            )

        _assert_safe_error(response, 409, "ENROLLMENT_UNAVAILABLE")
        limiter_write_index = next(
            index
            for index, statement in enumerate(statements)
            if "insert into auth_rate_limit_buckets" in statement
        )
        invitation_lookup_index = next(
            index
            for index, statement in enumerate(statements)
            if "from beta_invitations" in statement
        )
        assert limiter_write_index < invitation_lookup_index


def test_register_global_and_source_limits_precede_invitation_lookup(
    migrated_database: TemporaryDatabaseContext,
) -> None:
    run_async(
        lambda: _exercise_register_limiter_precedes_invitation_lookup(migrated_database)
    )


async def _exercise_login_contract(
    temporary_database: TemporaryDatabaseContext,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async with _auth_client(temporary_database) as (application, client):
        registered = await client.post(
            "/auth/register",
            json=await _registration_payload(
                application,
                username="Login_User",
                password=VALID_PASSWORD,
            ),
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


async def _exercise_legacy_password_login(
    temporary_database: TemporaryDatabaseContext,
) -> None:
    legacy_password = "legacy lowercase password phrase"
    async with _auth_client(temporary_database) as (application, client):
        async with _session_factory(application)() as session:
            async with session.begin():
                session.add(
                    User(
                        username="legacy_password_user",
                        password_hash=_old_password_hash(legacy_password),
                    )
                )

        login = await client.post(
            "/auth/login",
            json={
                "username": "legacy_password_user",
                "password": legacy_password,
            },
        )

        assert login.status_code == 200
        assert login.json()["username"] == "legacy_password_user"


def test_login_accepts_matching_historical_password_without_registration_policy(
    migrated_database: TemporaryDatabaseContext,
) -> None:
    run_async(lambda: _exercise_legacy_password_login(migrated_database))


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
            json=await _registration_payload(
                application,
                username="logout_user",
                password=VALID_PASSWORD,
            ),
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
            headers=AUTH_POST_HEADERS,
        ) as old_session_client:
            old_session_client.cookies.set(SESSION_COOKIE_NAME, old_token)
            old_me = await old_session_client.get("/auth/me")
            assert old_me.status_code == 200
            assert old_me.json()["username"] == "logout_user"

        async with AsyncClient(
            transport=ASGITransport(app=application),
            base_url="http://testserver",
            headers=AUTH_POST_HEADERS,
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
