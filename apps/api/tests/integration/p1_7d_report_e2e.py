import asyncio
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

from browser_e2e import (
    API_ORIGIN,
    API_PORT,
    API_ROOT,
    WEB_ORIGIN,
    WEB_PORT,
    WEB_ROOT,
    _log_tail,  # pyright: ignore[reportPrivateUsage]
    _require_available_port,  # pyright: ignore[reportPrivateUsage]
    _server_process,  # pyright: ignore[reportPrivateUsage]
    _wait_for_http,  # pyright: ignore[reportPrivateUsage]
    _wait_for_port_release,  # pyright: ignore[reportPrivateUsage]
)
from conftest import (
    QUESTION_BROWSER_DATABASE_PREFIX,
    IntegrationDatabaseSettings,
    TemporaryDatabase,
    migrate_database,
    temporary_database_context,
)

from group_interview_arena_api.db.models import (
    DiscussionEvent,
    SessionAction,
    SessionParticipant,
    SimulationSession,
    User,
)
from group_interview_arena_api.db.runtime import (
    create_database_engine,
    create_database_session_factory,
    dispose_database_engine,
)
from group_interview_arena_api.identity.credentials import hash_password
from group_interview_arena_api.modules.question_personas.seed import (
    INTERNAL_VALIDATION_BUNDLE,
    seed_question_persona_foundation,
)

NOW = datetime(2026, 9, 12, 10, 0, tzinfo=UTC)
OWNER_USERNAME = "p17d_report_owner"
OTHER_USERNAME = "p17d_report_other"
PASSWORD = "P1-7D browser report password"


async def _seed(temporary_database: TemporaryDatabase) -> UUID:
    engine = create_database_engine(temporary_database.database_settings())
    factory = create_database_session_factory(engine)
    try:
        await seed_question_persona_foundation(factory)
        owner_id, other_id, session_id, human_id = (uuid4() for _ in range(4))
        utterance_id, action_id = (uuid4() for _ in range(2))
        ai_ids = (uuid4(), uuid4(), uuid4())
        async with factory() as session, session.begin():
            session.add_all(
                [
                    User(
                        id=owner_id,
                        username=OWNER_USERNAME,
                        password_hash=hash_password(PASSWORD),
                    ),
                    User(
                        id=other_id,
                        username=OTHER_USERNAME,
                        password_hash=hash_password(PASSWORD),
                    ),
                ]
            )
            await session.flush()
            session.add(
                SimulationSession(
                    id=session_id,
                    owner_user_id=owner_id,
                    status="COMPLETED",
                    last_sequence=2,
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
            session.add(
                SessionAction(
                    session_id=session_id,
                    action_id=action_id,
                    command_version=1,
                    command_type="participant.utterance.submit",
                    payload_digest=b"x" * 32,
                    created_at=NOW + timedelta(seconds=1),
                )
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
                        causation_action_id=action_id,
                        payload={
                            "utterance_id": str(utterance_id),
                            "participant_id": str(human_id),
                            "actor_kind": "HUMAN",
                            "floor_grant_id": str(uuid4()),
                            "phase": "OPENING_STATEMENTS",
                            "content": "  exact opening source\n",
                        },
                        occurred_at=NOW + timedelta(seconds=1),
                    ),
                ]
            )
        return session_id
    finally:
        await dispose_database_engine(engine)


def _run(temporary_database: TemporaryDatabase, session_id: UUID) -> None:
    _require_available_port(API_PORT)
    _require_available_port(WEB_PORT)
    node = shutil.which("node.exe" if os.name == "nt" else "node")
    pnpm = shutil.which("pnpm.cmd" if os.name == "nt" else "pnpm")
    if node is None or pnpm is None:
        raise RuntimeError("Node.js and pnpm are required for P1-7D browser E2E.")
    next_cli = WEB_ROOT / "node_modules" / "next" / "dist" / "bin" / "next"
    with tempfile.TemporaryDirectory(prefix="gia_p17d_report_e2e_") as directory:
        api_log = Path(directory) / "api.log"
        web_log = Path(directory) / "web.log"
        api_environment = {
            "GIA_API_CORS_ORIGINS": f'["{WEB_ORIGIN}"]',
            "GIA_API_DATABASE_URL": temporary_database.database_settings().database_url.get_secret_value(),
            "GIA_API_ENVIRONMENT": "test",
            "GIA_API_SESSION_COOKIE_SECURE": "false",
            "GIA_API_ZHIPU_API_KEY": "network-free-unused-placeholder",
            "GIA_API_ZHIPU_MODEL": "network-free-unused-model",
        }
        try:
            with _server_process(
                [
                    sys.executable,
                    "-m",
                    "uvicorn",
                    "group_interview_arena_api.app:app",
                    "--host",
                    "localhost",
                    "--port",
                    str(API_PORT),
                    "--loop",
                    "group_interview_arena_api.core.event_loop:create_runtime_event_loop",
                ],
                cwd=API_ROOT,
                environment=api_environment,
                log_path=api_log,
            ) as api:
                _wait_for_http(f"{API_ORIGIN}/health", api, api_log)
                with _server_process(
                    [node, str(next_cli), "dev"],
                    cwd=WEB_ROOT,
                    environment={"NEXT_PUBLIC_API_BASE_URL": API_ORIGIN},
                    log_path=web_log,
                ) as web:
                    _wait_for_http(WEB_ORIGIN, web, web_log)
                    environment = os.environ.copy()
                    environment.update(
                        {
                            "CI": "true",
                            "GIA_E2E_API_ORIGIN": API_ORIGIN,
                            "GIA_P17D_SESSION_ID": str(session_id),
                            "GIA_P17D_OWNER_USERNAME": OWNER_USERNAME,
                            "GIA_P17D_OTHER_USERNAME": OTHER_USERNAME,
                            "GIA_P17D_PASSWORD": PASSWORD,
                        }
                    )
                    completed = subprocess.run(
                        [pnpm, "exec", "playwright", "test", "e2e/report.spec.ts"],
                        cwd=WEB_ROOT,
                        env=environment,
                        check=False,
                    )
                    if completed.returncode != 0:
                        raise RuntimeError(
                            f"P1-7D Playwright failed with {completed.returncode}."
                        )
        except Exception:
            print(_log_tail(api_log), file=sys.stderr)
            print(_log_tail(web_log), file=sys.stderr)
            raise
        finally:
            _wait_for_port_release(API_PORT)
            _wait_for_port_release(WEB_PORT)


def main() -> int:
    settings = IntegrationDatabaseSettings()  # pyright: ignore[reportCallIssue]
    with temporary_database_context(
        settings, QUESTION_BROWSER_DATABASE_PREFIX
    ) as database:
        migrate_database(database)
        session_id = asyncio.run(
            _seed(database), loop_factory=asyncio.SelectorEventLoop
        )
        _run(database, session_id)
    print(
        "P1-7D report browser E2E passed: completed-session CTA, coordinator generation, durable report, owner view, exact provenance, reload, non-owner isolation, no provider call, and cleanup."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
