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
    assert response.headers["Access-Control-Allow-Credentials"] == "true"


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


def test_allowed_auth_post_preflight_has_exact_browser_contract() -> None:
    response = asyncio.run(
        _request(
            _application(),
            "OPTIONS",
            origin=ALLOWED_ORIGIN,
            headers={
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type,x-gia-csrf",
            },
        )
    )

    assert response.status_code == 200
    assert response.headers["Access-Control-Allow-Origin"] == ALLOWED_ORIGIN
    assert response.headers["Access-Control-Allow-Credentials"] == "true"
    assert set(response.headers["Access-Control-Allow-Methods"].split(", ")) == {
        "GET",
        "POST",
    }
    allowed_headers = {
        value.strip().lower()
        for value in response.headers["Access-Control-Allow-Headers"].split(",")
    }
    assert {"content-type", "x-gia-csrf"} <= allowed_headers
    assert "authorization" not in allowed_headers


def test_unapproved_request_header_preflight_is_rejected() -> None:
    response = asyncio.run(
        _request(
            _application(),
            "OPTIONS",
            origin=ALLOWED_ORIGIN,
            headers={
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "authorization",
            },
        )
    )

    assert response.status_code == 400


def test_disallowed_auth_post_preflight_is_rejected() -> None:
    response = asyncio.run(
        _request(
            _application(),
            "OPTIONS",
            origin=DISALLOWED_ORIGIN,
            headers={
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type,x-gia-csrf",
            },
        )
    )

    assert response.status_code == 400
    assert "Access-Control-Allow-Origin" not in response.headers
