import asyncio
from typing import cast
from uuid import UUID

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient, Response

from group_interview_arena_api.app import create_app
from group_interview_arena_api.core.config import Environment, Settings


async def _get(application: FastAPI, path: str) -> Response:
    async with AsyncClient(
        transport=ASGITransport(app=application), base_url="http://testserver"
    ) as client:
        return await client.get(path)


def test_missing_route_uses_safe_error_envelope() -> None:
    application = create_app(Settings(environment=Environment.TEST))
    response = asyncio.run(_get(application, "/does-not-exist"))

    body = cast(dict[str, object], response.json())
    error = cast(dict[str, object], body["error"])

    assert response.status_code == 404
    assert error["code"] == "NOT_FOUND"
    assert error["message"] == "Resource not found."
    assert error["request_id"] == response.headers["X-Request-ID"]
    assert UUID(cast(str, error["request_id"])).version == 4
    assert "traceback" not in response.text.lower()
    assert "group_interview_arena_api" not in response.text


def test_unexpected_error_handler_hides_exception_details() -> None:
    application = create_app(Settings(environment=Environment.TEST))

    def fail() -> None:
        raise RuntimeError("secret filesystem detail")

    application.add_api_route("/failure", fail, methods=["GET"])
    response = asyncio.run(_get(application, "/failure"))
    body = cast(dict[str, object], response.json())
    error = cast(dict[str, object], body["error"])

    assert response.status_code == 500
    assert error["code"] == "INTERNAL_ERROR"
    assert error["message"] == "An internal error occurred."
    assert error["request_id"] == response.headers["X-Request-ID"]
    assert UUID(cast(str, error["request_id"])).version == 4
    assert "secret filesystem detail" not in response.text
