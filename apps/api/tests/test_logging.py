import asyncio
import json
import logging
from typing import cast

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient, Response

from group_interview_arena_api.app import create_app
from group_interview_arena_api.core.config import Environment, Settings
from group_interview_arena_api.core.logging import JsonFormatter


async def _get(application: FastAPI, path: str) -> Response:
    async with AsyncClient(
        transport=ASGITransport(app=application), base_url="http://testserver"
    ) as client:
        return await client.get(path)


class RecordHandler(logging.Handler):
    def __init__(self) -> None:
        super().__init__()
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)


def test_request_completion_log_is_structured() -> None:
    application = create_app(Settings(environment=Environment.TEST))
    handler = RecordHandler()
    application_logger = logging.getLogger("group_interview_arena_api.app")
    application_logger.addHandler(handler)

    try:
        response = asyncio.run(_get(application, "/health"))
    finally:
        application_logger.removeHandler(handler)

    record = next(
        item for item in handler.records if item.getMessage() == "Request completed"
    )
    payload = cast(dict[str, object], json.loads(JsonFormatter().format(record)))

    assert payload["request_id"] == response.headers["X-Request-ID"]
    assert payload["method"] == "GET"
    assert payload["path"] == "/health"
    assert payload["status_code"] == 200
    assert isinstance(payload["duration_ms"], float)
