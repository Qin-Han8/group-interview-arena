import asyncio
import re
from collections.abc import Callable, Coroutine
from contextlib import asynccontextmanager
from datetime import UTC, datetime
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
from group_interview_arena_api.db.models import (
    DiscussionEvent,
    SessionAction,
    SimulationSession,
)
from group_interview_arena_api.modules.question_personas.seed import (
    INTERNAL_VALIDATION_BUNDLE,
    seed_question_persona_foundation,
)
from tests.auth_test_helpers import create_test_invitation

pytestmark = pytest.mark.integration

TRUSTED_ORIGIN = "http://localhost:3000"
AUTH_HEADERS = {"Origin": TRUSTED_ORIGIN, "X-GIA-CSRF": "1"}
VALID_PASSWORD = "Session API integration 1!"


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


async def _register(
    application: FastAPI,
    client: AsyncClient,
    username: str,
) -> UUID:
    response = await client.post(
        "/auth/register",
        headers=AUTH_HEADERS,
        json={
            "username": username,
            "password": VALID_PASSWORD,
            "invite_code": await create_test_invitation(_factory(application)),
        },
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
            missing_transcript_auth = await unauthenticated.get(
                f"/sessions/{uuid4()}/utterances"
            )
            _assert_safe_error(
                missing_transcript_auth,
                401,
                "AUTHENTICATION_REQUIRED",
            )

        async with AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as owner:
            owner_id = await _register(application, owner, "session_owner")
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
                "phase_started_at",
                "phase_deadline_at",
                "server_now",
                "created_at",
                "updated_at",
                "last_sequence",
                "floor",
            }
            assert snapshot["floor"]["current_grant"] is None
            assert snapshot["floor"]["latest_event"] is None
            assert [
                (participant["actor_kind"], participant["seat_order"])
                for participant in snapshot["floor"]["participants"]
            ] == [("HUMAN", 1), ("AI", 2), ("AI", 3), ("AI", 4)]
            assert snapshot["phase_started_at"] is None
            assert snapshot["phase_deadline_at"] is None
            assert re.fullmatch(
                r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z",
                snapshot["server_now"],
            )
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
            loaded_snapshot = loaded.json()
            assert loaded_snapshot["server_now"] >= snapshot["server_now"]
            loaded_snapshot["server_now"] = snapshot["server_now"]
            assert loaded_snapshot == snapshot

            action_id = uuid4()
            started = await owner.post(
                f"/sessions/{session_id}/start",
                headers=AUTH_HEADERS,
                json={"action_id": str(action_id)},
            )
            assert started.status_code == 200
            started_snapshot = started.json()
            assert started_snapshot["status"] == "PREPARATION"
            assert started_snapshot["last_sequence"] == 2
            assert started_snapshot["phase_started_at"] is not None
            assert started_snapshot["phase_deadline_at"] is not None
            assert (
                started_snapshot["phase_started_at"]
                < started_snapshot["phase_deadline_at"]
            )

            duplicate_start = await owner.post(
                f"/sessions/{session_id}/start",
                headers=AUTH_HEADERS,
                json={"action_id": str(action_id)},
            )
            assert duplicate_start.status_code == 200
            assert duplicate_start.json()["last_sequence"] == 2

            stale_start = await owner.post(
                f"/sessions/{session_id}/start",
                headers=AUTH_HEADERS,
                json={"action_id": str(uuid4())},
            )
            _assert_safe_error(stale_start, 409, "INVALID_SESSION_STATE")

            human_action_id = uuid4()
            human_utterance_id = uuid4()
            ai_utterance_id = uuid4()
            human_participant_id = UUID(
                started_snapshot["floor"]["participants"][0]["participant_id"]
            )
            ai_participant_id = UUID(
                started_snapshot["floor"]["participants"][1]["participant_id"]
            )
            human_grant_id = uuid4()
            ai_grant_id = uuid4()
            occurred_at = datetime(2026, 8, 25, 4, 0, tzinfo=UTC)
            async with _factory(application)() as session:
                async with session.begin():
                    aggregate = await session.get(SimulationSession, session_id)
                    assert aggregate is not None
                    session.add(
                        SessionAction(
                            session_id=session_id,
                            action_id=human_action_id,
                            command_version=1,
                            command_type="participant.utterance.submit",
                            payload_digest=b"h" * 32,
                            created_at=occurred_at,
                        )
                    )
                    await session.flush()
                    session.add_all(
                        [
                            DiscussionEvent(
                                session_id=session_id,
                                sequence=4,
                                event_version=1,
                                event_type="participant.utterance.created",
                                causation_action_id=human_action_id,
                                payload={
                                    "utterance_id": str(human_utterance_id),
                                    "participant_id": str(human_participant_id),
                                    "actor_kind": "HUMAN",
                                    "floor_grant_id": str(human_grant_id),
                                    "phase": "OPENING_STATEMENTS",
                                    "content": "Human transcript item.",
                                },
                                occurred_at=occurred_at,
                            ),
                            DiscussionEvent(
                                session_id=session_id,
                                sequence=7,
                                event_version=1,
                                event_type="participant.utterance.created",
                                causation_action_id=None,
                                payload={
                                    "utterance_id": str(ai_utterance_id),
                                    "participant_id": str(ai_participant_id),
                                    "actor_kind": "AI",
                                    "floor_grant_id": str(ai_grant_id),
                                    "phase": "OPENING_STATEMENTS",
                                    "content": "AI transcript item.",
                                },
                                occurred_at=occurred_at,
                            ),
                        ]
                    )
                    aggregate.last_sequence = 7

            transcript = await owner.get(
                f"/sessions/{session_id}/utterances",
                params={"limit": 1},
            )
            assert transcript.status_code == 200
            first_page = transcript.json()
            assert first_page["next_after_sequence"] == 4
            assert first_page["items"] == [
                {
                    "utterance_id": str(human_utterance_id),
                    "sequence": 4,
                    "occurred_at": "2026-08-25T04:00:00Z",
                    "action_id": str(human_action_id),
                    "participant_id": str(human_participant_id),
                    "actor_kind": "HUMAN",
                    "floor_grant_id": str(human_grant_id),
                    "phase": "OPENING_STATEMENTS",
                    "content": "Human transcript item.",
                }
            ]
            second_page = await owner.get(
                f"/sessions/{session_id}/utterances",
                params={"after_sequence": 4},
            )
            assert second_page.status_code == 200
            assert second_page.json()["next_after_sequence"] is None
            assert [item["sequence"] for item in second_page.json()["items"]] == [7]
            assert second_page.json()["items"][0]["action_id"] is None
            for invalid_params in (
                {"after_sequence": -1},
                {"limit": 0},
                {"limit": 201},
            ):
                invalid = await owner.get(
                    f"/sessions/{session_id}/utterances",
                    params=invalid_params,
                )
                assert invalid.status_code == 422

            missing = await owner.get(f"/sessions/{uuid4()}")
            _assert_safe_error(missing, 404, "SESSION_NOT_FOUND")

            async with AsyncClient(
                transport=transport,
                base_url="http://testserver",
            ) as non_owner:
                await _register(application, non_owner, "session_non_owner")
                hidden = await non_owner.get(f"/sessions/{session_id}")
                _assert_safe_error(hidden, 404, "SESSION_NOT_FOUND")
                assert (
                    hidden.json()["error"]["message"]
                    == missing.json()["error"]["message"]
                )
                hidden_transcript = await non_owner.get(
                    f"/sessions/{session_id}/utterances"
                )
                _assert_safe_error(hidden_transcript, 404, "SESSION_NOT_FOUND")
                missing_transcript = await owner.get(f"/sessions/{uuid4()}/utterances")
                _assert_safe_error(missing_transcript, 404, "SESSION_NOT_FOUND")
                assert (
                    hidden_transcript.json()["error"]["message"]
                    == missing_transcript.json()["error"]["message"]
                )

        async with _factory(application)() as session:
            stored = await session.get(SimulationSession, session_id)
            assert stored is not None
            assert stored.owner_user_id == owner_id
            assert stored.question_version_id == INTERNAL_VALIDATION_BUNDLE.version_id
            assert stored.status == "PREPARATION"
            assert stored.phase_started_at is not None
            assert stored.phase_deadline_at is not None
            assert stored.phase_duration_plan is not None
            assert set(stored.phase_duration_plan) == {
                "PREPARATION",
                "OPENING_STATEMENTS",
                "EXPLORATION",
                "CONFLICT_AND_EVALUATION",
                "CONVERGENCE",
                "FINAL_SUMMARY",
            }
            assert stored.last_sequence == 7
            assert (
                await session.scalar(
                    select(func.count())
                    .select_from(DiscussionEvent)
                    .where(DiscussionEvent.session_id == session_id)
                )
                == 4
            )


def test_authenticated_create_and_owner_snapshot_rest_contract(
    migrated_database: TemporaryDatabaseContext,
) -> None:
    run_async(lambda: _verify_rest_contract(migrated_database))
