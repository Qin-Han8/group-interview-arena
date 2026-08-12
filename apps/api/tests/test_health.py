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


def test_health_endpoint() -> None:
    application = create_app(Settings(environment=Environment.TEST))
    response = asyncio.run(_get(application, "/health"))

    assert response.status_code == 200
    assert cast(dict[str, object], response.json()) == {"status": "ok"}
    assert response.headers["content-type"].startswith("application/json")

    request_id = UUID(response.headers["X-Request-ID"])
    assert request_id.version == 4
