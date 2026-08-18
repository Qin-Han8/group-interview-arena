import asyncio
import re
from collections.abc import Callable, Coroutine
from contextlib import asynccontextmanager
from typing import Any, Protocol, cast
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import URL, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from group_interview_arena_api.app import create_app
from group_interview_arena_api.core.config import (
    DatabaseSettings,
    Environment,
    Settings,
)
from group_interview_arena_api.db.dependencies import (
    DATABASE_SESSION_FACTORY_STATE_KEY,
)
from group_interview_arena_api.db.models import DiscussionEvent, SimulationSession
from group_interview_arena_api.modules.question_personas.seed import (
    INTERNAL_VALIDATION_BUNDLE,
    seed_question_persona_foundation,
)

pytestmark = pytest.mark.integration

TRUSTED_ORIGIN = "http://localhost:3000"
AUTH_HEADERS = {"Origin": TRUSTED_ORIGIN, "X-GIA-CSRF": "1"}
VALID_PASSWORD = "session api integration password"


class TemporaryDatabaseContext(Protocol):
    database_name: str
    database_url: URL

    def database_settings(self) -> DatabaseSettings: ...


def run_async[T](operation: Callable[[], Coroutine[Any, Any, T]]) -> T:
    return asyncio.run(operation(), loop_factory=asyncio.SelectorEventLoop)


def _factory(application: FastAPI) -> async_sessionmaker[AsyncSession]:
    candidate = getattr(application.state, DATABASE_SESSION_FACTORY_STATE_KEY)
    assert isinstance(candidate, async_sessionmaker)
    return cast(async_sessionmaker[AsyncSession], candidate)


@asynccontextmanager
async def _application(
    temporary_database: TemporaryDatabaseContext,
):
    application = create_app(
        Settings(
            environment=Environment.TEST,
            cors_origins=(TRUSTED_ORIGIN,),
        ),
        temporary_database.database_settings(),
    )
    async with application.router.lifespan_context(application):
        await seed_question_persona_foundation(_factory(application))
        yield application


async def _register(client: AsyncClient, username: str) -> UUID:
    response = await client.post(
        "/auth/register",
        headers=AUTH_HEADERS,
        json={"username": username, "password": VALID_PASSWORD},
    )
    assert response.status_code == 201
    return UUID(response.json()["id"])


def _assert_safe_error(response: Any, status_code: int, code: str) -> None:
    assert response.status_code == status_code
    body = response.json()
    assert set(body) == {"error"}
    assert body["error"]["code"] == code
    assert UUID(body["error"]["request_id"]).version == 4


async def _verify_rest_contract(
    temporary_database: TemporaryDatabaseContext,
) -> None:
    async with _application(temporary_database) as application:
        transport = ASGITransport(app=application)
        async with AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as unauthenticated:
            missing_auth = await unauthenticated.post(
                "/sessions",
                headers=AUTH_HEADERS,
                json={
                    "question_version_id": str(INTERNAL_VALIDATION_BUNDLE.version_id)
                },
            )
            _assert_safe_error(missing_auth, 401, "AUTHENTICATION_REQUIRED")

        async with AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as owner:
            owner_id = await _register(owner, "session_owner")
            missing_csrf = await owner.post(
                "/sessions",
                json={
                    "question_version_id": str(INTERNAL_VALIDATION_BUNDLE.version_id)
                },
            )
            _assert_safe_error(missing_csrf, 403, "CSRF_REJECTED")

            created = await owner.post(
                "/sessions",
                headers=AUTH_HEADERS,
                json={
                    "question_version_id": str(INTERNAL_VALIDATION_BUNDLE.version_id)
                },
            )
            assert created.status_code == 201
            snapshot = created.json()
            session_id = UUID(snapshot["id"])
            assert session_id.version == 4
            assert snapshot["status"] == "CREATED"
            assert snapshot["last_sequence"] == 1
            assert set(snapshot) == {
                "id",
                "question_version_id",
                "status",
                "created_at",
                "updated_at",
                "last_sequence",
            }
            assert snapshot["question_version_id"] == str(
                INTERNAL_VALIDATION_BUNDLE.version_id
            )
            assert snapshot["created_at"] == snapshot["updated_at"]
            assert re.fullmatch(
                r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z",
                snapshot["created_at"],
            )

            loaded = await owner.get(f"/sessions/{session_id}")
            assert loaded.status_code == 200
            assert loaded.json() == snapshot

            missing = await owner.get(f"/sessions/{uuid4()}")
            _assert_safe_error(missing, 404, "SESSION_NOT_FOUND")

            async with AsyncClient(
                transport=transport,
                base_url="http://testserver",
            ) as non_owner:
                await _register(non_owner, "session_non_owner")
                hidden = await non_owner.get(f"/sessions/{session_id}")
                _assert_safe_error(hidden, 404, "SESSION_NOT_FOUND")
                assert (
                    hidden.json()["error"]["message"]
                    == missing.json()["error"]["message"]
                )

        async with _factory(application)() as session:
            stored = await session.get(SimulationSession, session_id)
            assert stored is not None
            assert stored.owner_user_id == owner_id
            assert stored.question_version_id == INTERNAL_VALIDATION_BUNDLE.version_id
            assert stored.last_sequence == 1
            assert (
                await session.scalar(
                    select(func.count())
                    .select_from(DiscussionEvent)
                    .where(DiscussionEvent.session_id == session_id)
                )
                == 1
            )


def test_authenticated_create_and_owner_snapshot_rest_contract(
    migrated_database: TemporaryDatabaseContext,
) -> None:
    run_async(lambda: _verify_rest_contract(migrated_database))
