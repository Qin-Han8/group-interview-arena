import asyncio
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


def test_independent_requests_receive_unique_request_ids() -> None:
    application = create_app(Settings(environment=Environment.TEST))
    first_response = asyncio.run(_get(application, "/health"))
    second_response = asyncio.run(_get(application, "/health"))

    first_request_id = UUID(first_response.headers["X-Request-ID"])
    second_request_id = UUID(second_response.headers["X-Request-ID"])

    assert first_request_id.version == 4
    assert second_request_id.version == 4
    assert first_request_id != second_request_id
