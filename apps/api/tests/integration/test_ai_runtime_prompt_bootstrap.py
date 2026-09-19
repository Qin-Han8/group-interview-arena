import asyncio
import hashlib
from collections.abc import Callable, Coroutine
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import UUID

import pytest
from sqlalchemy import URL, func, select

import group_interview_arena_api.app as app_module
from group_interview_arena_api.app import create_app
from group_interview_arena_api.core.config import (
    DatabaseSettings,
    Environment,
    Settings,
)
from group_interview_arena_api.db import PromptVersion
from group_interview_arena_api.db.dependencies import (
    DATABASE_SESSION_FACTORY_STATE_KEY,
)
from group_interview_arena_api.db.runtime import (
    create_database_engine,
    create_database_session_factory,
    dispose_database_engine,
)
from group_interview_arena_api.modules.ai_runtime.domain import (
    PromptVersionDefinition,
    PromptVersionMutationError,
)
from group_interview_arena_api.modules.ai_runtime.seed import (
    AI_CANDIDATE_TURN_V2,
    AI_CANDIDATE_TURN_V3,
    AI_CANDIDATE_TURN_V4,
    DISCUSSION_MEMORY_UPDATE_V1,
    DISCUSSION_MEMORY_UPDATE_V2,
)
from group_interview_arena_api.modules.ai_runtime.service import publish_prompt_version

pytestmark = pytest.mark.integration


class TemporaryDatabaseContext(Protocol):
    database_name: str
    database_url: URL

    def database_settings(self) -> DatabaseSettings: ...


def run_async[T](operation: Callable[[], Coroutine[Any, Any, T]]) -> T:
    return asyncio.run(operation(), loop_factory=asyncio.SelectorEventLoop)


def _v1_definition() -> PromptVersionDefinition:
    return PromptVersionDefinition(
        id=UUID("56000000-0000-4000-8000-000000000001"),
        prompt_key="AI_CANDIDATE_TURN",
        version_number=1,
        purpose_code="CANDIDATE_UTTERANCE",
        template_text="Immutable historical prompt v1.",
        created_at=datetime(2026, 8, 24, 8, 0, tzinfo=UTC),
        published_at=datetime(2026, 8, 24, 8, 0, tzinfo=UTC),
    )


def _prompt_snapshot(row: PromptVersion) -> tuple[object, ...]:
    return (
        row.id,
        row.prompt_key,
        row.version_number,
        row.purpose_code,
        row.template_text,
        row.content_digest,
        row.created_at,
        row.published_at,
        row.retired_at,
    )


async def _verify_normal_lifespan_publication(
    temporary_database: TemporaryDatabaseContext,
) -> None:
    application = create_app(
        Settings(environment=Environment.TEST),
        temporary_database.database_settings(),
    )

    expected = AI_CANDIDATE_TURN_V2
    expected_digest = hashlib.sha256(expected.template_text.encode("utf-8")).digest()
    first_snapshot: tuple[object, ...] | None = None
    for _startup in range(2):
        async with application.router.lifespan_context(application):
            session_factory = getattr(
                application.state,
                DATABASE_SESSION_FACTORY_STATE_KEY,
            )
            async with session_factory() as session:
                row = await session.get(PromptVersion, expected.id)
                count = await session.scalar(
                    select(func.count()).select_from(PromptVersion)
                )
                v3 = await session.get(PromptVersion, AI_CANDIDATE_TURN_V3.id)
                v4 = await session.get(PromptVersion, AI_CANDIDATE_TURN_V4.id)
                memory_prompt = await session.get(
                    PromptVersion, DISCUSSION_MEMORY_UPDATE_V1.id
                )
                memory_prompt_v2 = await session.get(
                    PromptVersion, DISCUSSION_MEMORY_UPDATE_V2.id
                )
            assert row is not None
            assert count == 5
            assert v3 is not None
            assert v4 is not None
            assert memory_prompt is not None
            assert memory_prompt_v2 is not None
            snapshot = _prompt_snapshot(row)
            assert snapshot == (
                expected.id,
                expected.prompt_key,
                expected.version_number,
                expected.purpose_code,
                expected.template_text,
                expected_digest,
                expected.created_at,
                expected.published_at,
                None,
            )
            if first_snapshot is None:
                first_snapshot = snapshot
            else:
                assert snapshot == first_snapshot


def test_normal_production_lifespan_publishes_v2_and_restart_is_exact_noop(
    migrated_database: TemporaryDatabaseContext,
) -> None:
    run_async(lambda: _verify_normal_lifespan_publication(migrated_database))


async def _verify_v1_is_immutable_during_bootstrap(
    temporary_database: TemporaryDatabaseContext,
) -> None:
    engine = create_database_engine(temporary_database.database_settings())
    session_factory = create_database_session_factory(engine)
    try:
        async with session_factory() as session:
            assert await publish_prompt_version(session, _v1_definition()) is True
        async with session_factory() as session:
            before = await session.get(PromptVersion, _v1_definition().id)
            assert before is not None
            before_snapshot = _prompt_snapshot(before)
    finally:
        await dispose_database_engine(engine)

    application = create_app(
        Settings(environment=Environment.TEST),
        temporary_database.database_settings(),
    )
    async with application.router.lifespan_context(application):
        live_session_factory = getattr(
            application.state,
            DATABASE_SESSION_FACTORY_STATE_KEY,
        )
        async with live_session_factory() as session:
            after = await session.get(PromptVersion, _v1_definition().id)
            v2 = await session.get(PromptVersion, AI_CANDIDATE_TURN_V2.id)
            count = await session.scalar(
                select(func.count()).select_from(PromptVersion)
            )
        assert after is not None
        assert v2 is not None
        assert count == 6
        assert _prompt_snapshot(after) == before_snapshot


def test_production_bootstrap_never_mutates_or_retires_v1(
    migrated_database: TemporaryDatabaseContext,
) -> None:
    run_async(lambda: _verify_v1_is_immutable_during_bootstrap(migrated_database))


async def _verify_conflict_aborts_before_recovery(
    temporary_database: TemporaryDatabaseContext,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    conflicting = PromptVersionDefinition(
        id=AI_CANDIDATE_TURN_V2.id,
        prompt_key="CONFLICTING_PROMPT",
        version_number=1,
        purpose_code="CANDIDATE_UTTERANCE",
        template_text="Conflicting immutable identity.",
        created_at=AI_CANDIDATE_TURN_V2.created_at,
        published_at=AI_CANDIDATE_TURN_V2.published_at,
    )
    engine = create_database_engine(temporary_database.database_settings())
    session_factory = create_database_session_factory(engine)
    try:
        async with session_factory() as session:
            assert await publish_prompt_version(session, conflicting) is True
    finally:
        await dispose_database_engine(engine)

    recovery_called = False
    runtime_started = False

    async def recover(_session_factory: object) -> int:
        nonlocal recovery_called
        recovery_called = True
        return 0

    def start(_session_factory: object) -> object:
        nonlocal runtime_started
        runtime_started = True
        return object()

    monkeypatch.setattr(app_module, "recover_due_sessions", recover)
    monkeypatch.setattr(app_module, "start_deadline_recovery_runtime", start)
    application = create_app(
        Settings(environment=Environment.TEST),
        temporary_database.database_settings(),
    )

    with pytest.raises(PromptVersionMutationError):
        async with application.router.lifespan_context(application):
            pass

    assert recovery_called is False
    assert runtime_started is False


def test_conflicting_v2_identity_aborts_production_startup_before_recovery(
    migrated_database: TemporaryDatabaseContext,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_async(
        lambda: _verify_conflict_aborts_before_recovery(
            migrated_database,
            monkeypatch,
        )
    )
