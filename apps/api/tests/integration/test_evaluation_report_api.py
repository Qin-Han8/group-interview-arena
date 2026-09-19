import asyncio
from collections.abc import Awaitable, Callable
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from decimal import Decimal
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
    EvaluationReport,
    EvidenceItem,
    SessionAction,
    SessionParticipant,
    SimulationSession,
)
from group_interview_arena_api.modules.evaluation_reports import routes as report_routes
from group_interview_arena_api.modules.evaluation_reports.query import (
    ReportViewPersistenceError,
)
from group_interview_arena_api.modules.question_personas.seed import (
    INTERNAL_VALIDATION_BUNDLE,
    seed_question_persona_foundation,
)

pytestmark = pytest.mark.integration

NOW = datetime(2026, 9, 12, 8, 0, tzinfo=UTC)
TRUSTED_ORIGIN = "http://localhost:3000"
AUTH_HEADERS = {"Origin": TRUSTED_ORIGIN, "X-GIA-CSRF": "1"}
PASSWORD = "Report API integration 1!"


class TemporaryDatabaseContext(Protocol):
    database_name: str
    database_url: URL

    def database_settings(self) -> DatabaseSettings: ...


def _run(operation: Callable[[], Awaitable[None]]) -> None:
    asyncio.run(operation(), loop_factory=asyncio.SelectorEventLoop)


def _factory(application: FastAPI) -> async_sessionmaker[AsyncSession]:
    candidate = getattr(application.state, DATABASE_SESSION_FACTORY_STATE_KEY)
    assert isinstance(candidate, async_sessionmaker)
    return cast(async_sessionmaker[AsyncSession], candidate)


@asynccontextmanager
async def _application(temporary_database: TemporaryDatabaseContext):
    application = create_app(
        Settings(environment=Environment.TEST, cors_origins=(TRUSTED_ORIGIN,)),
        temporary_database.database_settings(),
    )
    async with application.router.lifespan_context(application):
        await seed_question_persona_foundation(_factory(application))
        yield application


async def _register(client: AsyncClient, username: str) -> UUID:
    response = await client.post(
        "/auth/register",
        headers=AUTH_HEADERS,
        json={"username": username, "password": PASSWORD},
    )
    assert response.status_code == 201
    return UUID(response.json()["id"])


def _assert_error(response: Any, status_code: int, code: str) -> None:
    assert response.status_code == status_code
    assert response.json()["error"]["code"] == code


async def _seed_completed_session(
    factory: async_sessionmaker[AsyncSession],
    owner_id: UUID,
    *,
    with_source: bool,
) -> tuple[UUID, UUID, tuple[UUID, UUID]]:
    session_id = uuid4()
    human_id = uuid4()
    human_utterance_ids = (uuid4(), uuid4())
    ai_ids = (uuid4(), uuid4(), uuid4())
    last_sequence = 4 if with_source else 0
    async with factory() as session, session.begin():
        session.add(
            SimulationSession(
                id=session_id,
                owner_user_id=owner_id,
                status="COMPLETED",
                last_sequence=last_sequence,
                question_version_id=INTERNAL_VALIDATION_BUNDLE.version_id,
                created_at=NOW,
                updated_at=NOW,
            )
        )
        await session.flush()
        session.add_all(
            [
                SessionParticipant(
                    id=human_id,
                    session_id=session_id,
                    actor_kind="HUMAN",
                    participation_role="CANDIDATE",
                    seat_order=1,
                    availability="AVAILABLE",
                    user_id=owner_id,
                    question_persona_assignment_id=None,
                    created_at=NOW,
                ),
                *(
                    SessionParticipant(
                        id=participant_id,
                        session_id=session_id,
                        actor_kind="AI",
                        participation_role="CANDIDATE",
                        seat_order=seat,
                        availability="AVAILABLE",
                        user_id=None,
                        question_persona_assignment_id=assignment.id,
                        created_at=NOW,
                    )
                    for participant_id, seat, assignment in zip(
                        ai_ids,
                        (2, 3, 4),
                        INTERNAL_VALIDATION_BUNDLE.assignments,
                        strict=True,
                    )
                ),
            ]
        )
        if with_source:
            action_ids = (uuid4(), uuid4())
            session.add_all(
                [
                    SessionAction(
                        session_id=session_id,
                        action_id=action_id,
                        command_version=1,
                        command_type="participant.utterance.submit",
                        payload_digest=bytes([index]) * 32,
                        created_at=NOW + timedelta(seconds=index),
                    )
                    for index, action_id in enumerate(action_ids, start=1)
                ]
            )
            await session.flush()
            session.add_all(
                [
                    DiscussionEvent(
                        session_id=session_id,
                        sequence=1,
                        event_version=2,
                        event_type="session.state_changed",
                        causation_action_id=None,
                        payload={"status": "COMPLETED"},
                        occurred_at=NOW,
                    ),
                    DiscussionEvent(
                        session_id=session_id,
                        sequence=2,
                        event_version=1,
                        event_type="participant.utterance.created",
                        causation_action_id=action_ids[0],
                        payload={
                            "utterance_id": str(human_utterance_ids[0]),
                            "participant_id": str(human_id),
                            "actor_kind": "HUMAN",
                            "floor_grant_id": str(uuid4()),
                            "phase": "OPENING_STATEMENTS",
                            "content": "  exact opening source\n",
                        },
                        occurred_at=NOW + timedelta(seconds=1),
                    ),
                    DiscussionEvent(
                        session_id=session_id,
                        sequence=3,
                        event_version=1,
                        event_type="participant.utterance.created",
                        causation_action_id=action_ids[1],
                        payload={
                            "utterance_id": str(human_utterance_ids[1]),
                            "participant_id": str(human_id),
                            "actor_kind": "HUMAN",
                            "floor_grant_id": str(uuid4()),
                            "phase": "CONVERGENCE",
                            "content": "second exact source",
                        },
                        occurred_at=NOW + timedelta(seconds=2),
                    ),
                    DiscussionEvent(
                        session_id=session_id,
                        sequence=4,
                        event_version=1,
                        event_type="participant.utterance.created",
                        causation_action_id=None,
                        payload={
                            "utterance_id": str(uuid4()),
                            "participant_id": str(ai_ids[0]),
                            "actor_kind": "AI",
                            "floor_grant_id": str(uuid4()),
                            "phase": "FINAL_SUMMARY",
                            "content": "above the report watermark",
                        },
                        occurred_at=NOW + timedelta(seconds=3),
                    ),
                ]
            )
    return session_id, human_id, human_utterance_ids


async def _add_report(
    factory: async_sessionmaker[AsyncSession],
    *,
    session_id: UUID,
    status: str,
    created_at: datetime,
    report_schema_version: int,
    source_through_sequence: int,
) -> UUID:
    report_id = uuid4()
    started_at = None if status == "REQUESTED" else created_at + timedelta(seconds=1)
    completed_at = created_at + timedelta(seconds=2) if status == "COMPLETED" else None
    failed_at = created_at + timedelta(seconds=2) if status == "FAILED" else None
    async with factory() as session, session.begin():
        session.add(
            EvaluationReport(
                id=report_id,
                session_id=session_id,
                report_schema_version=report_schema_version,
                derivation_version=f"basic-report/v{report_schema_version}",
                source_through_sequence=source_through_sequence,
                status=status,
                overall_summary=(
                    "Exact completed summary." if status == "COMPLETED" else None
                ),
                priority_improvement=(
                    "Use explicit criteria next time."
                    if status == "COMPLETED"
                    else None
                ),
                created_at=created_at,
                started_at=started_at,
                completed_at=completed_at,
                failed_at=failed_at,
            )
        )
    return report_id


@pytest.mark.parametrize("report_status", ["REQUESTED", "RUNNING", "FAILED"])
def test_non_completed_report_returns_metadata_without_content(
    migrated_database: TemporaryDatabaseContext,
    report_status: str,
) -> None:
    async def verify() -> None:
        async with _application(migrated_database) as application:
            factory = _factory(application)
            transport = ASGITransport(app=application)
            async with AsyncClient(
                transport=transport, base_url="http://test"
            ) as client:
                owner_id = await _register(client, f"report_{report_status.lower()}")
                session_id, _, _ = await _seed_completed_session(
                    factory, owner_id, with_source=False
                )
                report_id = await _add_report(
                    factory,
                    session_id=session_id,
                    status=report_status,
                    created_at=NOW,
                    report_schema_version=1,
                    source_through_sequence=0,
                )
                response = await client.get(f"/sessions/{session_id}/report")

            assert response.status_code == 200
            assert response.json()["report"]["report_id"] == str(report_id)
            assert response.json()["report"]["status"] == report_status
            assert response.json()["content"] is None

    _run(verify)


def test_latest_report_is_selected_without_completed_fallback(
    migrated_database: TemporaryDatabaseContext,
) -> None:
    async def verify() -> None:
        async with _application(migrated_database) as application:
            factory = _factory(application)
            transport = ASGITransport(app=application)
            async with AsyncClient(
                transport=transport, base_url="http://test"
            ) as client:
                owner_id = await _register(client, "report_latest")
                session_id, _, _ = await _seed_completed_session(
                    factory, owner_id, with_source=False
                )
                await _add_report(
                    factory,
                    session_id=session_id,
                    status="COMPLETED",
                    created_at=NOW,
                    report_schema_version=1,
                    source_through_sequence=0,
                )
                latest_id = await _add_report(
                    factory,
                    session_id=session_id,
                    status="FAILED",
                    created_at=NOW + timedelta(minutes=1),
                    report_schema_version=2,
                    source_through_sequence=0,
                )
                response = await client.get(f"/sessions/{session_id}/report")

            assert response.status_code == 200
            assert response.json()["report"]["report_id"] == str(latest_id)
            assert response.json()["report"]["status"] == "FAILED"
            assert response.json()["content"] is None

    _run(verify)


def test_completed_report_projects_exact_public_source_and_ordered_evidence(
    migrated_database: TemporaryDatabaseContext,
) -> None:
    async def verify() -> None:
        async with _application(migrated_database) as application:
            factory = _factory(application)
            transport = ASGITransport(app=application)
            async with AsyncClient(
                transport=transport, base_url="http://test"
            ) as client:
                owner_id = await _register(client, "report_completed")
                session_id, human_id, utterance_ids = await _seed_completed_session(
                    factory, owner_id, with_source=True
                )
                report_id = await _add_report(
                    factory,
                    session_id=session_id,
                    status="COMPLETED",
                    created_at=NOW + timedelta(minutes=1),
                    report_schema_version=1,
                    source_through_sequence=3,
                )
                async with factory() as session, session.begin():
                    session.add_all(
                        [
                            EvidenceItem(
                                id=UUID("40000000-0000-4000-8000-000000000003"),
                                session_id=session_id,
                                report_id=report_id,
                                kind="STRENGTH",
                                source_participant_id=human_id,
                                source_utterance_id=utterance_ids[1],
                                source_event_sequence=3,
                                phase="CONVERGENCE",
                                quote="second exact source",
                                interpretation="Closed toward a decision.",
                                confidence=Decimal("0.800"),
                                created_at=NOW + timedelta(minutes=2),
                            ),
                            EvidenceItem(
                                id=UUID("40000000-0000-4000-8000-000000000002"),
                                session_id=session_id,
                                report_id=report_id,
                                kind="STRENGTH",
                                source_participant_id=human_id,
                                source_utterance_id=utterance_ids[0],
                                source_event_sequence=2,
                                phase="OPENING_STATEMENTS",
                                quote="  exact opening source\n",
                                interpretation="Opened with a concrete contribution.",
                                confidence=Decimal("1.000"),
                                created_at=NOW + timedelta(minutes=2),
                            ),
                            EvidenceItem(
                                id=UUID("40000000-0000-4000-8000-000000000001"),
                                session_id=session_id,
                                report_id=report_id,
                                kind="IMPROVEMENT",
                                source_participant_id=human_id,
                                source_utterance_id=utterance_ids[1],
                                source_event_sequence=3,
                                phase="CONVERGENCE",
                                quote="second exact source",
                                interpretation="Make the decision criterion explicit.",
                                confidence=Decimal("0.600"),
                                created_at=NOW + timedelta(minutes=2),
                            ),
                        ]
                    )
                response = await client.get(f"/sessions/{session_id}/report")

            assert response.status_code == 200
            body = response.json()
            assert set(body) == {"report", "content"}
            assert set(body["report"]) == {
                "report_id",
                "session_id",
                "status",
                "report_schema_version",
                "derivation_version",
                "source_through_sequence",
                "created_at",
                "completed_at",
            }
            content = body["content"]
            assert content["overview"]["session_status"] == "COMPLETED"
            assert content["overview"]["participant_count"] == 4
            assert content["overview"]["human_utterance_count"] == 2
            assert content["overview"]["ai_utterance_count"] == 0
            assert content["overview"]["total_utterance_count"] == 2
            assert content["overview"]["covered_phases"] == [
                "OPENING_STATEMENTS",
                "CONVERGENCE",
            ]
            assert content["overview"]["summary"] == "Exact completed summary."
            assert content["overview"]["question"]["id"] == str(
                INTERNAL_VALIDATION_BUNDLE.version_id
            )
            assert [item["source_event_sequence"] for item in content["strengths"]] == [
                2,
                3,
            ]
            assert content["strengths"][0]["quote"] == "  exact opening source\n"
            assert len(content["improvements"]) == 1
            assert content["priority_improvement"] == "Use explicit criteria next time."
            serialized = response.text.lower()
            assert "above the report watermark" not in serialized
            for forbidden in (
                "started_at",
                "failed_at",
                "private_stance",
                "reference_dimensions",
                "hidden_conflicts",
                "acceptable_outcome_patterns",
                "phase_prompts",
                "safety_tags",
            ):
                assert forbidden not in serialized

    _run(verify)


def test_report_read_is_owner_only_not_found_and_mutation_free(
    migrated_database: TemporaryDatabaseContext,
) -> None:
    async def verify() -> None:
        async with _application(migrated_database) as application:
            factory = _factory(application)
            transport = ASGITransport(app=application)
            async with AsyncClient(
                transport=transport, base_url="http://test"
            ) as guest:
                _assert_error(
                    await guest.get(f"/sessions/{uuid4()}/report"),
                    401,
                    "AUTHENTICATION_REQUIRED",
                )
            async with AsyncClient(
                transport=transport, base_url="http://test"
            ) as owner:
                owner_id = await _register(owner, "report_owner")
                session_id, _, _ = await _seed_completed_session(
                    factory, owner_id, with_source=False
                )
                _assert_error(
                    await owner.get(f"/sessions/{session_id}/report"),
                    404,
                    "REPORT_NOT_FOUND",
                )
                malformed = await owner.get("/sessions/not-a-uuid/report")
                _assert_error(malformed, 422, "VALIDATION_ERROR")
            async with AsyncClient(
                transport=transport, base_url="http://test"
            ) as other:
                await _register(other, "report_other")
                _assert_error(
                    await other.get(f"/sessions/{session_id}/report"),
                    404,
                    "REPORT_NOT_FOUND",
                )

            async with factory() as session:
                assert (
                    await session.scalar(
                        select(func.count()).select_from(EvaluationReport)
                    )
                    == 0
                )
                assert (
                    await session.scalar(select(func.count()).select_from(EvidenceItem))
                    == 0
                )

    _run(verify)


def test_report_read_maps_internal_failure_to_safe_error(
    migrated_database: TemporaryDatabaseContext,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    private_sentinel = "PRIVATE_REPORT_FAILURE_MUST_NOT_LEAK"

    async def fail_read(*_args: object, **_kwargs: object) -> None:
        raise ReportViewPersistenceError(private_sentinel)

    monkeypatch.setattr(report_routes, "load_current_report_view", fail_read)

    async def verify() -> None:
        async with _application(migrated_database) as application:
            transport = ASGITransport(app=application)
            async with AsyncClient(
                transport=transport, base_url="http://test"
            ) as client:
                await _register(client, "report_safe_error")
                response = await client.get(f"/sessions/{uuid4()}/report")
        _assert_error(response, 500, "INTERNAL_ERROR")
        assert private_sentinel not in response.text

    _run(verify)


def test_report_generation_command_uses_server_identity_and_is_idempotent(
    migrated_database: TemporaryDatabaseContext,
) -> None:
    async def verify() -> None:
        async with _application(migrated_database) as application:
            factory = _factory(application)
            transport = ASGITransport(app=application)
            async with AsyncClient(
                transport=transport, base_url="http://test"
            ) as client:
                owner_id = await _register(client, "report_generate")
                session_id, _, _ = await _seed_completed_session(
                    factory, owner_id, with_source=True
                )

                first = await client.post(
                    f"/sessions/{session_id}/report", headers=AUTH_HEADERS
                )
                second = await client.post(
                    f"/sessions/{session_id}/report", headers=AUTH_HEADERS
                )
                read = await client.get(f"/sessions/{session_id}/report")

            assert first.status_code == second.status_code == 200
            assert first.json() == second.json()
            assert first.json()["status"] == "COMPLETED"
            assert first.json()["report_schema_version"] == 1
            assert first.json()["derivation_version"] == "basic-report/v1"
            assert first.json()["source_through_sequence"] == 4
            assert read.status_code == 200
            assert read.json()["report"] == first.json()
            assert read.json()["content"]["strengths"][0]["quote"] == (
                "  exact opening source\n"
            )

            async with factory() as session:
                assert (
                    await session.scalar(
                        select(func.count()).select_from(EvaluationReport)
                    )
                    == 1
                )
                assert (
                    await session.scalar(select(func.count()).select_from(EvidenceItem))
                    == 1
                )

    _run(verify)


def test_report_generation_command_enforces_csrf_owner_and_completed_session(
    migrated_database: TemporaryDatabaseContext,
) -> None:
    async def verify() -> None:
        async with _application(migrated_database) as application:
            factory = _factory(application)
            transport = ASGITransport(app=application)
            async with AsyncClient(
                transport=transport, base_url="http://test"
            ) as owner:
                owner_id = await _register(owner, "report_generate_owner")
                session_id, _, _ = await _seed_completed_session(
                    factory, owner_id, with_source=False
                )
                _assert_error(
                    await owner.post(f"/sessions/{session_id}/report"),
                    403,
                    "CSRF_REJECTED",
                )

                for ineligible_status in ("CREATED", "ABORTED_USER"):
                    async with factory() as session, session.begin():
                        candidate = await session.get(SimulationSession, session_id)
                        assert candidate is not None
                        candidate.status = ineligible_status

                    _assert_error(
                        await owner.post(
                            f"/sessions/{session_id}/report", headers=AUTH_HEADERS
                        ),
                        409,
                        "INVALID_SESSION_STATE",
                    )

            async with AsyncClient(
                transport=transport, base_url="http://test"
            ) as other:
                await _register(other, "report_generate_other")
                _assert_error(
                    await other.post(
                        f"/sessions/{session_id}/report", headers=AUTH_HEADERS
                    ),
                    404,
                    "REPORT_NOT_FOUND",
                )

    _run(verify)
