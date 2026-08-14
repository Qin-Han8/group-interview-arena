import asyncio
from collections.abc import AsyncIterator
from typing import cast

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient, Response

from group_interview_arena_api.app import create_app
from group_interview_arena_api.core.config import Environment, Settings
from group_interview_arena_api.db.dependencies import get_database_session

TRUSTED_ORIGIN = "http://localhost:3000"
UNTRUSTED_ORIGIN = "https://example.invalid"
AUTH_PAYLOAD = {
    "username": "csrf_user",
    "password": "csrf unit-only password phrase",
}


def _application() -> FastAPI:
    application = create_app(
        Settings(
            environment=Environment.TEST,
            cors_origins=(TRUSTED_ORIGIN,),
        )
    )

    async def database_must_not_be_resolved() -> AsyncIterator[object]:
        raise AssertionError("CSRF rejection reached the database dependency")
        yield object()

    application.dependency_overrides[get_database_session] = (
        database_must_not_be_resolved
    )
    return application


async def _post(
    application: FastAPI,
    path: str,
    *,
    headers: dict[str, str] | list[tuple[str, str]],
) -> Response:
    async with AsyncClient(
        transport=ASGITransport(app=application),
        base_url="http://testserver",
    ) as client:
        return await client.post(path, json=AUTH_PAYLOAD, headers=headers)


@pytest.mark.parametrize("path", ["/auth/register", "/auth/login", "/auth/logout"])
@pytest.mark.parametrize(
    "headers",
    [
        {},
        {"X-GIA-CSRF": "1"},
        {"Origin": "null", "X-GIA-CSRF": "1"},
        {"Origin": UNTRUSTED_ORIGIN, "X-GIA-CSRF": "1"},
        {"Origin": TRUSTED_ORIGIN},
        {"Origin": TRUSTED_ORIGIN, "X-GIA-CSRF": "0"},
        [("Origin", TRUSTED_ORIGIN), ("Origin", TRUSTED_ORIGIN), ("X-GIA-CSRF", "1")],
        [("Origin", TRUSTED_ORIGIN), ("X-GIA-CSRF", "1"), ("X-GIA-CSRF", "1")],
    ],
)
def test_unsafe_auth_requests_reject_invalid_browser_boundary_before_database(
    path: str,
    headers: dict[str, str] | list[tuple[str, str]],
) -> None:
    response = asyncio.run(_post(_application(), path, headers=headers))
    body = cast(dict[str, object], response.json())
    error = cast(dict[str, object], body["error"])

    assert response.status_code == 403
    assert error["code"] == "CSRF_REJECTED"
    assert set(error) == {"code", "message", "request_id"}


def test_me_does_not_require_browser_csrf_headers() -> None:
    application = create_app(Settings(environment=Environment.TEST))

    async def unused_session() -> AsyncIterator[object]:
        yield object()

    application.dependency_overrides[get_database_session] = unused_session

    async def get_me() -> Response:
        async with AsyncClient(
            transport=ASGITransport(app=application),
            base_url="http://testserver",
        ) as client:
            return await client.get("/auth/me")

    response = asyncio.run(get_me())

    assert response.status_code != 403


def test_openapi_marks_csrf_header_required_on_unsafe_auth_routes() -> None:
    schema = _application().openapi()

    for path in ("/auth/register", "/auth/login", "/auth/logout"):
        operation = schema["paths"][path]["post"]
        parameter = next(
            item for item in operation["parameters"] if item["name"] == "X-GIA-CSRF"
        )
        assert parameter["in"] == "header"
        assert parameter["required"] is True
        assert parameter["schema"] == {"type": "string", "const": "1"}

    assert "parameters" not in schema["paths"]["/auth/me"]["get"]
