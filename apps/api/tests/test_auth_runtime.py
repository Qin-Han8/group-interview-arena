import asyncio
from collections.abc import AsyncIterator
from typing import cast
from uuid import uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from httpx import Response as HttpxResponse
from pydantic import SecretStr, ValidationError
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker
from starlette.responses import Response

import group_interview_arena_api.app as app_module
from group_interview_arena_api.app import create_app
from group_interview_arena_api.core.config import (
    DatabaseSettings,
    Environment,
    Settings,
)
from group_interview_arena_api.db.dependencies import (
    DATABASE_SESSION_FACTORY_STATE_KEY,
    get_database_session,
    get_database_session_factory,
)
from group_interview_arena_api.identity.cookies import (
    SESSION_COOKIE_MAX_AGE,
    SESSION_COOKIE_NAME,
    clear_session_cookie,
    set_session_cookie,
)
from group_interview_arena_api.identity.credentials import (
    ARGON2_MEMORY_COST,
    ARGON2_PARALLELISM,
    ARGON2_TIME_COST,
)
from group_interview_arena_api.identity.schemas import LoginRequest, RegisterRequest
from group_interview_arena_api.identity.service import (
    DUMMY_PASSWORD_HASH,
    AuthenticationResult,
)
from tests.deadline_recovery_test_helpers import disable_deadline_recovery_runtime

TEST_DATABASE_URL = (
    "postgresql+psycopg://test-user:test-password@127.0.0.1:5432/"
    "not_connected_by_unit_tests"
)
PLAINTEXT_PASSWORD = "unit-only password phrase"
PLAINTEXT_INVITE = "unit-only invitation secret"
TRUSTED_ORIGIN = "http://localhost:3000"
AUTH_POST_HEADERS = {"Origin": TRUSTED_ORIGIN, "X-GIA-CSRF": "1"}


def test_authentication_result_repr_redacts_raw_session_token() -> None:
    raw_session_token = "unit-only-raw-session-token"
    result = AuthenticationResult(
        user_id=uuid4(),
        username="test_user",
        raw_session_token=raw_session_token,
    )

    assert raw_session_token not in repr(result)
    assert result.raw_session_token == raw_session_token


def test_dummy_password_hash_matches_current_argon2_cost() -> None:
    algorithm = DUMMY_PASSWORD_HASH.split("$", maxsplit=3)[1]
    parameters = DUMMY_PASSWORD_HASH.split("$", maxsplit=4)[3]

    assert algorithm == "argon2id"
    assert parameters == (
        f"m={ARGON2_MEMORY_COST},t={ARGON2_TIME_COST},p={ARGON2_PARALLELISM}"
    )


async def _request(
    application: FastAPI,
    method: str,
    path: str,
    *,
    json: dict[str, object] | None = None,
    headers: dict[str, str] | None = None,
) -> HttpxResponse:
    async with AsyncClient(
        transport=ASGITransport(app=application),
        base_url="http://testserver",
    ) as client:
        return await client.request(method, path, json=json, headers=headers)


def test_auth_request_schema_repr_and_json_redact_password() -> None:
    register = RegisterRequest(
        username="test_user",
        password=SecretStr(PLAINTEXT_PASSWORD),
        invite_code=SecretStr(PLAINTEXT_INVITE),
    )
    login = LoginRequest(
        username="test_user",
        password=SecretStr(PLAINTEXT_PASSWORD),
    )

    assert PLAINTEXT_PASSWORD not in repr(register)
    assert PLAINTEXT_PASSWORD not in register.model_dump_json()
    assert PLAINTEXT_INVITE not in repr(register)
    assert PLAINTEXT_INVITE not in register.model_dump_json()
    assert PLAINTEXT_PASSWORD not in repr(login)
    assert PLAINTEXT_PASSWORD not in login.model_dump_json()


def test_login_schema_rejects_passwords_over_128_unicode_code_points() -> None:
    with pytest.raises(ValidationError):
        LoginRequest(username="test_user", password=SecretStr("界" * 129))


def test_validation_error_response_does_not_echo_password() -> None:
    application = create_app(
        Settings(
            environment=Environment.TEST,
            cors_origins=(TRUSTED_ORIGIN,),
        )
    )

    async def unused_session() -> AsyncIterator[object]:
        yield object()

    application.dependency_overrides[get_database_session] = unused_session
    application.dependency_overrides[get_database_session_factory] = lambda: object()

    response = asyncio.run(
        _request(
            application,
            "POST",
            "/auth/register",
            json={"password": PLAINTEXT_PASSWORD},
            headers=AUTH_POST_HEADERS,
        )
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert PLAINTEXT_PASSWORD not in response.text


def test_session_cookie_helpers_apply_local_and_production_flags() -> None:
    local_response = Response()
    set_session_cookie(
        local_response,
        "unit-only-raw-token",
        Settings(environment=Environment.TEST, session_cookie_secure=False),
    )
    local_header = local_response.headers["set-cookie"]
    local_header_lower = local_header.lower()

    assert local_header.startswith(f"{SESSION_COOKIE_NAME}=")
    assert "httponly" in local_header_lower
    assert "samesite=lax" in local_header_lower
    assert "path=/" in local_header_lower
    assert f"max-age={SESSION_COOKIE_MAX_AGE}" in local_header_lower
    assert "domain=" not in local_header_lower
    assert "secure" not in local_header_lower

    production_response = Response()
    set_session_cookie(
        production_response,
        "unit-only-raw-token",
        Settings(
            environment=Environment.PRODUCTION,
            session_cookie_secure=True,
            auth_trusted_caddy_mode=True,
            auth_rate_limit_hmac_key=SecretStr("x" * 32),
        ),
    )
    assert "secure" in production_response.headers["set-cookie"].lower()


def test_session_cookie_clear_matches_cookie_identity_and_security() -> None:
    response = Response()
    clear_session_cookie(
        response,
        Settings(
            environment=Environment.PRODUCTION,
            session_cookie_secure=True,
            auth_trusted_caddy_mode=True,
            auth_rate_limit_hmac_key=SecretStr("x" * 32),
        ),
    )
    header = response.headers["set-cookie"].lower()

    assert header.startswith(f'{SESSION_COOKIE_NAME}=""')
    assert "max-age=0" in header
    assert "path=/" in header
    assert "httponly" in header
    assert "samesite=lax" in header
    assert "secure" in header
    assert "domain=" not in header


def test_openapi_generation_is_database_environment_independent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("GIA_API_DATABASE_URL", raising=False)
    application = create_app(Settings(environment=Environment.TEST))

    schema = application.openapi()

    assert set(schema["paths"]) == {
        "/auth/login",
        "/auth/logout",
        "/auth/me",
        "/auth/register",
        "/health",
        "/questions",
        "/questions/{question_version_id}",
        "/sessions",
        "/sessions/{session_id}",
        "/sessions/{session_id}/report",
        "/sessions/{session_id}/start",
        "/sessions/{session_id}/utterances",
    }
    security_schemes = schema["components"]["securitySchemes"]
    assert security_schemes == {
        "SessionCookie": {
            "type": "apiKey",
            "description": (
                "Opaque server-side session token stored in an HttpOnly Cookie."
            ),
            "in": "cookie",
            "name": SESSION_COOKIE_NAME,
        }
    }
    assert schema["paths"]["/auth/me"]["get"]["security"] == [{"SessionCookie": []}]
    assert "bearer" not in str(schema).lower()
    assert "jwt" not in str(schema).lower()


def test_lifespan_requires_database_configuration_at_runtime(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("GIA_API_DATABASE_URL", raising=False)
    application = create_app(Settings(environment=Environment.TEST))

    async def enter_lifespan() -> None:
        async with application.router.lifespan_context(application):
            pass

    with pytest.raises(ValidationError):
        asyncio.run(enter_lifespan())


def test_lifespan_initializes_and_cleans_database_runtime_without_connecting(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    disable_deadline_recovery_runtime(monkeypatch)
    application = create_app(
        Settings(environment=Environment.TEST),
        DatabaseSettings(database_url=SecretStr(TEST_DATABASE_URL)),
    )

    async def inspect_lifespan() -> None:
        async with application.router.lifespan_context(application):
            assert isinstance(application.state.database_engine, AsyncEngine)
            candidate = getattr(
                application.state,
                DATABASE_SESSION_FACTORY_STATE_KEY,
            )
            assert isinstance(candidate, async_sessionmaker)

        assert not hasattr(application.state, "database_engine")
        assert not hasattr(
            application.state,
            DATABASE_SESSION_FACTORY_STATE_KEY,
        )

    asyncio.run(inspect_lifespan())


def test_auth_dependency_without_lifespan_fails_with_safe_envelope() -> None:
    application = create_app(Settings(environment=Environment.TEST))

    response = asyncio.run(_request(application, "GET", "/auth/me"))
    body = cast(dict[str, object], response.json())
    error = cast(dict[str, object], body["error"])

    assert response.status_code == 500
    assert error["code"] == "INTERNAL_ERROR"
    assert "Database runtime" not in response.text
    assert TEST_DATABASE_URL not in response.text


def test_lifespan_publishes_prompt_before_recovery_and_runtime_start(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[str] = []

    class _Runtime:
        async def stop(self) -> None:
            events.append("stop")

    async def seed(_session_factory: object) -> bool:
        events.append("seed")
        return True

    async def recover(_session_factory: object) -> int:
        events.append("recover")
        return 0

    def start(_session_factory: object) -> _Runtime:
        events.append("start")
        return _Runtime()

    monkeypatch.setattr(app_module, "seed_ai_runtime_prompt_versions", seed)
    monkeypatch.setattr(app_module, "recover_due_sessions", recover)
    monkeypatch.setattr(app_module, "start_deadline_recovery_runtime", start)
    application = create_app(
        Settings(environment=Environment.TEST),
        DatabaseSettings(database_url=SecretStr(TEST_DATABASE_URL)),
    )

    async def enter_lifespan() -> None:
        async with application.router.lifespan_context(application):
            assert events == ["seed", "recover", "start"]

    asyncio.run(enter_lifespan())

    assert events == ["seed", "recover", "start", "stop"]


def test_lifespan_prompt_publication_failure_aborts_before_recovery(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[str] = []

    async def seed(_session_factory: object) -> bool:
        events.append("seed")
        raise RuntimeError("prompt publication conflict")

    async def recover(_session_factory: object) -> int:
        events.append("recover")
        return 0

    def start(_session_factory: object) -> object:
        events.append("start")
        return object()

    monkeypatch.setattr(app_module, "seed_ai_runtime_prompt_versions", seed)
    monkeypatch.setattr(app_module, "recover_due_sessions", recover)
    monkeypatch.setattr(app_module, "start_deadline_recovery_runtime", start)
    application = create_app(
        Settings(environment=Environment.TEST),
        DatabaseSettings(database_url=SecretStr(TEST_DATABASE_URL)),
    )

    async def enter_lifespan() -> None:
        async with application.router.lifespan_context(application):
            pass

    with pytest.raises(RuntimeError, match="prompt publication conflict"):
        asyncio.run(enter_lifespan())

    assert events == ["seed"]
    assert not hasattr(application.state, "deadline_recovery_runtime")
