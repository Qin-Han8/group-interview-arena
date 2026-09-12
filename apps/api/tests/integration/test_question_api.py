import asyncio
from collections.abc import Callable, Coroutine
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any, Protocol, cast
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import URL, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from group_interview_arena_api.app import create_app
from group_interview_arena_api.core.config import (
    DatabaseSettings,
    Environment,
    Settings,
)
from group_interview_arena_api.db import (
    PersonaPrivateStance,
    PersonaTemplate,
    QuestionTemplate,
    QuestionVersion,
    SimulationSession,
)
from group_interview_arena_api.db.dependencies import (
    DATABASE_SESSION_FACTORY_STATE_KEY,
)
from group_interview_arena_api.modules.question_personas.seed import (
    INTERNAL_VALIDATION_BUNDLE,
    V01_QUESTION_BUNDLES,
    persist_published_question_bundle,
    seed_question_persona_foundation,
)

pytestmark = pytest.mark.integration

TRUSTED_ORIGIN = "http://localhost:3000"
AUTH_HEADERS = {"Origin": TRUSTED_ORIGIN, "X-GIA-CSRF": "1"}
VALID_PASSWORD = "question api integration password"
PRIVATE_SENTINEL = "P1_2C_PRIVATE_SENTINEL_DO_NOT_DISCLOSE"


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


def _public_summary_keys() -> set[str]:
    return {
        "id",
        "question_template_id",
        "version_number",
        "title",
        "question_type",
        "background_domain",
        "difficulty",
        "estimated_minutes",
    }


async def _insert_draft(session_factory: async_sessionmaker[AsyncSession]) -> UUID:
    content = INTERNAL_VALIDATION_BUNDLE.content
    template_id = uuid4()
    version_id = uuid4()
    async with session_factory() as session:
        async with session.begin():
            session.add(
                QuestionTemplate(
                    id=template_id,
                    code=f"DRAFT_{template_id.hex.upper()}",
                    created_at=INTERNAL_VALIDATION_BUNDLE.created_at,
                )
            )
            session.add(
                QuestionVersion(
                    id=version_id,
                    question_template_id=template_id,
                    version_number=1,
                    title="draft sentinel title",
                    question_type_code=content.question_type_code,
                    background_domain_code=content.background_domain_code,
                    difficulty_code=content.difficulty_code,
                    scenario=content.scenario,
                    objective=content.objective,
                    estimated_minutes=content.estimated_minutes,
                    hard_constraints=[
                        item.model_dump(mode="json")
                        for item in content.hard_constraints
                    ],
                    soft_constraints=[
                        item.model_dump(mode="json")
                        for item in content.soft_constraints
                    ],
                    stakeholders=[
                        item.model_dump(mode="json") for item in content.stakeholders
                    ],
                    options=[item.model_dump(mode="json") for item in content.options],
                    reference_dimensions=[
                        item.model_dump(mode="json")
                        for item in content.reference_dimensions
                    ],
                    hidden_conflicts=[
                        item.model_dump(mode="json")
                        for item in content.hidden_conflicts
                    ],
                    acceptable_outcome_patterns=[
                        item.model_dump(mode="json")
                        for item in content.acceptable_outcome_patterns
                    ],
                    phase_prompts=content.phase_prompts.model_dump(
                        mode="json", by_alias=True, exclude_none=True
                    ),
                    safety_tags=list(content.safety_tags),
                    created_at=INTERNAL_VALIDATION_BUNDLE.created_at,
                    published_at=None,
                )
            )
    return version_id


async def _install_private_sentinel(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        async with session.begin():
            await session.execute(
                update(QuestionVersion)
                .where(QuestionVersion.id == INTERNAL_VALIDATION_BUNDLE.version_id)
                .values(
                    reference_dimensions=[
                        {
                            "key": "PRIVATE_SENTINEL",
                            "name": PRIVATE_SENTINEL,
                            "description": PRIVATE_SENTINEL,
                        }
                    ],
                    hidden_conflicts=[
                        {"key": "PRIVATE_SENTINEL", "text": PRIVATE_SENTINEL}
                    ],
                    acceptable_outcome_patterns=[
                        {"key": "PRIVATE_SENTINEL", "text": PRIVATE_SENTINEL}
                    ],
                    phase_prompts={"PREPARATION": PRIVATE_SENTINEL},
                    safety_tags=[PRIVATE_SENTINEL],
                )
            )
            await session.execute(
                update(PersonaPrivateStance).values(
                    initial_position=PRIVATE_SENTINEL,
                    private_information=PRIVATE_SENTINEL,
                    preferred_group_role=PRIVATE_SENTINEL,
                )
            )


async def _verify_discovery_detail_and_nondisclosure(
    temporary_database: TemporaryDatabaseContext,
) -> None:
    async with _application(temporary_database) as application:
        session_factory = _factory(application)
        draft_id = await _insert_draft(session_factory)
        await _install_private_sentinel(session_factory)
        transport = ASGITransport(app=application)

        async with AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as guest:
            _assert_safe_error(
                await guest.get("/questions"), 401, "AUTHENTICATION_REQUIRED"
            )

        async with AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as client:
            await _register(client, "question_reader")
            discovered = await client.get("/questions")
            assert discovered.status_code == 200
            assert len(discovered.json()) == 12
            summary = discovered.json()[0]
            assert set(summary) == _public_summary_keys()
            assert {item["id"] for item in discovered.json()} == {
                str(bundle.version_id) for bundle in V01_QUESTION_BUNDLES
            }

            detail = await client.get(
                f"/questions/{INTERNAL_VALIDATION_BUNDLE.version_id}"
            )
            assert detail.status_code == 200
            assert set(detail.json()) == _public_summary_keys() | {
                "scenario",
                "objective",
                "hard_constraints",
                "soft_constraints",
                "stakeholders",
                "options",
            }
            serialized = detail.text + discovered.text
            assert PRIVATE_SENTINEL not in serialized
            for private_name in (
                "persona",
                "private_stance",
                "reference_dimensions",
                "hidden_conflicts",
                "acceptable_outcome_patterns",
                "phase_prompts",
                "safety_tags",
            ):
                assert private_name not in serialized

            for bundle in V01_QUESTION_BUNDLES:
                public = await client.get(f"/questions/{bundle.version_id}")
                assert public.status_code == 200
                assert set(public.json()) == _public_summary_keys() | {
                    "scenario",
                    "objective",
                    "hard_constraints",
                    "soft_constraints",
                    "stakeholders",
                    "options",
                }
                created = await client.post(
                    "/sessions",
                    headers=AUTH_HEADERS,
                    json={"question_version_id": str(bundle.version_id)},
                )
                assert created.status_code == 201

            draft = await client.get(f"/questions/{draft_id}")
            missing = await client.get(f"/questions/{uuid4()}")
            _assert_safe_error(draft, 404, "QUESTION_NOT_FOUND")
            _assert_safe_error(missing, 404, "QUESTION_NOT_FOUND")
            assert (
                draft.json()["error"]["message"] == missing.json()["error"]["message"]
            )

            for unavailable_id in (draft_id, uuid4()):
                rejected = await client.post(
                    "/sessions",
                    headers=AUTH_HEADERS,
                    json={"question_version_id": str(unavailable_id)},
                )
                _assert_safe_error(rejected, 404, "QUESTION_NOT_FOUND")

            extra_alias = await client.post(
                "/sessions",
                headers=AUTH_HEADERS,
                json={
                    "question_version_id": str(INTERNAL_VALIDATION_BUNDLE.version_id),
                    "latest": True,
                },
            )
            _assert_safe_error(extra_alias, 422, "VALIDATION_ERROR")


def test_question_discovery_detail_draft_missing_and_private_isolation(
    migrated_database: TemporaryDatabaseContext,
    capsys: pytest.CaptureFixture[str],
) -> None:
    run_async(lambda: _verify_discovery_detail_and_nondisclosure(migrated_database))
    captured = capsys.readouterr()
    assert PRIVATE_SENTINEL not in captured.out + captured.err


async def _verify_retired_persona_blocks_new_selection(
    temporary_database: TemporaryDatabaseContext,
) -> None:
    async with _application(temporary_database) as application:
        session_factory = _factory(application)
        retired_at = datetime(2026, 8, 18, 12, tzinfo=UTC)
        async with session_factory() as session:
            async with session.begin():
                await session.execute(
                    update(PersonaTemplate)
                    .where(
                        PersonaTemplate.id
                        == INTERNAL_VALIDATION_BUNDLE.assignments[0].persona_template_id
                    )
                    .values(retired_at=retired_at)
                )

        transport = ASGITransport(app=application)
        async with AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as client:
            await _register(client, "retired_persona_reader")
            discovered = await client.get("/questions")
            assert discovered.status_code == 200
            retired_persona_id = INTERNAL_VALIDATION_BUNDLE.assignments[
                0
            ].persona_template_id
            expected_available = {
                str(bundle.version_id)
                for bundle in V01_QUESTION_BUNDLES
                if retired_persona_id
                not in {
                    assignment.persona_template_id for assignment in bundle.assignments
                }
            }
            assert {item["id"] for item in discovered.json()} == expected_available
            historical_read = await client.get(
                f"/questions/{INTERNAL_VALIDATION_BUNDLE.version_id}"
            )
            assert historical_read.status_code == 200
            rejected = await client.post(
                "/sessions",
                headers=AUTH_HEADERS,
                json={
                    "question_version_id": str(INTERNAL_VALIDATION_BUNDLE.version_id)
                },
            )
            _assert_safe_error(rejected, 404, "QUESTION_NOT_FOUND")


def test_retired_persona_removes_version_from_new_training_only(
    migrated_database: TemporaryDatabaseContext,
) -> None:
    run_async(lambda: _verify_retired_persona_blocks_new_selection(migrated_database))


async def _verify_immutable_historical_binding(
    temporary_database: TemporaryDatabaseContext,
) -> None:
    async with _application(temporary_database) as application:
        session_factory = _factory(application)
        transport = ASGITransport(app=application)
        async with AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as client:
            owner_id = await _register(client, "history_owner")
            created = await client.post(
                "/sessions",
                headers=AUTH_HEADERS,
                json={
                    "question_version_id": str(INTERNAL_VALIDATION_BUNDLE.version_id)
                },
            )
            assert created.status_code == 201
            snapshot = created.json()
            assert snapshot["question_version_id"] == str(
                INTERNAL_VALIDATION_BUNDLE.version_id
            )

            second_bundle = INTERNAL_VALIDATION_BUNDLE.model_copy(
                update={
                    "version_id": uuid4(),
                    "version_number": 2,
                    "content": INTERNAL_VALIDATION_BUNDLE.content.model_copy(
                        update={"title": "内部验证：第二不可变版本"}
                    ),
                    "assignments": tuple(
                        item.model_copy(update={"id": uuid4()})
                        for item in INTERNAL_VALIDATION_BUNDLE.assignments
                    ),
                }
            )
            async with session_factory() as session:
                async with session.begin():
                    assert await persist_published_question_bundle(
                        session, second_bundle
                    )

            retired_at = datetime(2026, 8, 18, 12, tzinfo=UTC)
            async with session_factory() as session:
                async with session.begin():
                    await session.execute(
                        update(QuestionVersion)
                        .where(
                            QuestionVersion.id == INTERNAL_VALIDATION_BUNDLE.version_id
                        )
                        .values(retired_at=retired_at)
                    )

            discovered = await client.get("/questions")
            same_template_versions = [
                item
                for item in discovered.json()
                if item["question_template_id"]
                == str(INTERNAL_VALIDATION_BUNDLE.template_id)
            ]
            assert [item["id"] for item in same_template_versions] == [
                str(second_bundle.version_id)
            ]
            historical_detail = await client.get(
                f"/questions/{INTERNAL_VALIDATION_BUNDLE.version_id}"
            )
            assert historical_detail.status_code == 200
            assert (
                historical_detail.json()["title"]
                == INTERNAL_VALIDATION_BUNDLE.content.title
            )

            loaded = await client.get(f"/sessions/{snapshot['id']}")
            assert loaded.status_code == 200
            assert loaded.json()["question_version_id"] == str(
                INTERNAL_VALIDATION_BUNDLE.version_id
            )
            assert loaded.json()["question_version_id"] != str(second_bundle.version_id)

            retired_create = await client.post(
                "/sessions",
                headers=AUTH_HEADERS,
                json={
                    "question_version_id": str(INTERNAL_VALIDATION_BUNDLE.version_id)
                },
            )
            _assert_safe_error(retired_create, 404, "QUESTION_NOT_FOUND")

            legacy_id = uuid4()
            async with session_factory() as session:
                async with session.begin():
                    session.add(
                        SimulationSession(
                            id=legacy_id,
                            owner_user_id=owner_id,
                            question_version_id=None,
                            status="CREATED",
                            last_sequence=0,
                        )
                    )
            legacy = await client.get(f"/sessions/{legacy_id}")
            assert legacy.status_code == 200
            assert legacy.json()["question_version_id"] is None

        async with session_factory() as session:
            rows = list((await session.scalars(select(SimulationSession))).all())
            assert len(rows) == 2
            bound = next(row for row in rows if row.id == UUID(snapshot["id"]))
            assert bound.question_version_id == INTERNAL_VALIDATION_BUNDLE.version_id
            assert (
                await session.scalar(
                    select(func.count()).select_from(SimulationSession)
                )
                == 2
            )


def test_session_binding_survives_new_version_retirement_and_legacy_null(
    migrated_database: TemporaryDatabaseContext,
) -> None:
    run_async(lambda: _verify_immutable_historical_binding(migrated_database))
