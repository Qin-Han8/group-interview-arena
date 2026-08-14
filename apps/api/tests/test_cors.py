import asyncio

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient, Response

from group_interview_arena_api.app import create_app
from group_interview_arena_api.core.config import Environment, Settings

ALLOWED_ORIGIN = "http://localhost:3000"
DISALLOWED_ORIGIN = "https://example.invalid"


def _application() -> FastAPI:
    return create_app(
        Settings(
            environment=Environment.TEST,
            cors_origins=(ALLOWED_ORIGIN,),
        )
    )


async def _request(
    application: FastAPI,
    method: str,
    *,
    origin: str,
    headers: dict[str, str] | None = None,
) -> Response:
    async with AsyncClient(
        transport=ASGITransport(app=application), base_url="http://testserver"
    ) as client:
        return await client.request(
            method,
            "/health",
            headers={"Origin": origin, **(headers or {})},
        )


def test_allowed_origin_receives_cors_headers() -> None:
    response = asyncio.run(_request(_application(), "GET", origin=ALLOWED_ORIGIN))

    assert response.status_code == 200
    assert response.headers["Access-Control-Allow-Origin"] == ALLOWED_ORIGIN
    assert "X-Request-ID" in response.headers["Access-Control-Expose-Headers"]
    assert "Access-Control-Allow-Credentials" not in response.headers


def test_disallowed_origin_is_not_authorized() -> None:
    response = asyncio.run(_request(_application(), "GET", origin=DISALLOWED_ORIGIN))

    assert response.status_code == 200
    assert "Access-Control-Allow-Origin" not in response.headers


def test_allowed_get_preflight_succeeds() -> None:
    response = asyncio.run(
        _request(
            _application(),
            "OPTIONS",
            origin=ALLOWED_ORIGIN,
            headers={"Access-Control-Request-Method": "GET"},
        )
    )

    assert response.status_code == 200
    assert response.headers["Access-Control-Allow-Origin"] == ALLOWED_ORIGIN
    assert "GET" in response.headers["Access-Control-Allow-Methods"]
