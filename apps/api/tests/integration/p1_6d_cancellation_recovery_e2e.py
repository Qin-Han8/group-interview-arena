import asyncio
import json
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path
from typing import Any

import psycopg
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
    P1_6D_BROWSER_DATABASE_PREFIX,
    IntegrationDatabaseSettings,
    TemporaryDatabase,
    migrate_database,
    temporary_database_context,
)
from sqlalchemy import update

from group_interview_arena_api.db import PersonaPrivateStance
from group_interview_arena_api.db.runtime import (
    create_database_engine,
    create_database_session_factory,
    dispose_database_engine,
)
from group_interview_arena_api.modules.ai_runtime.seed import (
    seed_ai_runtime_prompt_versions,
)
from group_interview_arena_api.modules.question_personas.seed import (
    INTERNAL_VALIDATION_BUNDLE,
    seed_question_persona_foundation,
)

PRIVATE_SENTINELS = (
    "P16D_D2D3_PRIVATE_ALPHA_DO_NOT_DISCLOSE",
    "P16D_D2D3_PRIVATE_BRAVO_DO_NOT_DISCLOSE",
    "P16D_D2D3_PRIVATE_CHARLIE_DO_NOT_DISCLOSE",
)


def _provider_module_source() -> str:
    return textwrap.dedent(
        """
        import asyncio
        import json
        import os
        from pathlib import Path

        import psycopg

        from group_interview_arena_api.modules.ai_runtime import composition
        from group_interview_arena_api.modules.ai_runtime.generation import RawGenerationSuccess

        PRIVATE_SENTINELS = (
            "P16D_D2D3_PRIVATE_ALPHA_DO_NOT_DISCLOSE",
            "P16D_D2D3_PRIVATE_BRAVO_DO_NOT_DISCLOSE",
            "P16D_D2D3_PRIVATE_CHARLIE_DO_NOT_DISCLOSE",
        )

        def _database_url():
            return os.environ["GIA_API_DATABASE_URL"].replace(
                "postgresql+psycopg://", "postgresql://", 1
            )

        def _append(row):
            with Path(os.environ["GIA_P16D_D2D3_PROVIDER_CALLS"]).open(
                "a", encoding="utf-8"
            ) as stream:
                stream.write(json.dumps(row, sort_keys=True) + "\\n")

        class NetworkFreeP16DCancellationProvider:
            async def invoke(self, invocation):
                prompt = invocation.rendered_prompt
                if any(sentinel in prompt for sentinel in PRIVATE_SENTINELS):
                    raise RuntimeError("Private stance reached MemoryDerivationInput.")
                marker = "Public derivation input:\\n"
                derivation_input = json.loads(prompt.rsplit(marker, 1)[1])
                sequences = [
                    item["sequence"]
                    for item in derivation_input.get("utterances", [])
                    if isinstance(item.get("sequence"), int)
                ]
                return RawGenerationSuccess(content=json.dumps({
                    "patches": [{
                        "operation": "ADD",
                        "kind": "PROPOSAL",
                        "target_memory_item_id": None,
                        "canonical_text": "D2-D3 public cancellation context",
                        "source_sequences": sequences[-32:],
                    }]
                }))

            async def __call__(self, generation_input):
                floor_grant_id = str(generation_input.floor_grant_id)
                request_id = str(generation_input.generation_request_id)
                prompt = generation_input.rendered_prompt
                sentinel_indexes = [
                    index
                    for index, sentinel in enumerate(PRIVATE_SENTINELS)
                    if sentinel in prompt
                ]
                if len(sentinel_indexes) != 1:
                    raise RuntimeError(
                        "Candidate prompt did not contain exactly one private stance."
                    )
                _append({
                    "workload": "candidate",
                    "generation_request_id": request_id,
                    "floor_grant_id": floor_grant_id,
                    "participant_id": str(generation_input.participant_id),
                })

                arm = Path(os.environ["GIA_P16D_D2D3_BLOCK_ARM"])
                claimed = Path(os.environ["GIA_P16D_D2D3_BLOCK_CLAIMED"])
                should_block = False
                try:
                    arm.replace(claimed)
                    should_block = True
                except FileNotFoundError:
                    pass

                if should_block:
                    with psycopg.connect(_database_url()) as connection:
                        durable_rows = connection.execute(
                            "SELECT status, failure_code FROM llm_generation_requests "
                            "WHERE id = %s AND floor_grant_id = %s",
                            (generation_input.generation_request_id,
                             generation_input.floor_grant_id),
                        ).fetchall()
                    if durable_rows != [("RUNNING", None)]:
                        raise RuntimeError(
                            f"Blocked provider durable state mismatch: {durable_rows!r}"
                        )
                    blocked = {
                        "generation_request_id": request_id,
                        "floor_grant_id": floor_grant_id,
                        "request_status": "RUNNING",
                    }
                    Path(os.environ["GIA_P16D_D2D3_PROVIDER_BLOCKED"]).write_text(
                        json.dumps(blocked, sort_keys=True), encoding="utf-8"
                    )
                    try:
                        await asyncio.Event().wait()
                    except asyncio.CancelledError:
                        Path(
                            os.environ["GIA_P16D_D2D3_PROVIDER_CANCELLED"]
                        ).write_text(
                            json.dumps({
                                "generation_request_id": request_id,
                                "floor_grant_id": floor_grant_id,
                            }, sort_keys=True),
                            encoding="utf-8",
                        )
                        raise

                prefix = (
                    f"P16D_D2D3_AI_PUBLIC:{generation_input.participant_id}:"
                    f"{generation_input.floor_grant_id}:"
                )
                return RawGenerationSuccess(
                    content=prefix + "A" * max(1, 900 - len(prefix))
                )

        _provider = NetworkFreeP16DCancellationProvider()

        def _provider_factory(_settings):
            return _provider

        composition.ZhipuGenerationProvider = _provider_factory

        from group_interview_arena_api.app import app
        """
    )


def _database_connection(
    temporary_database: TemporaryDatabase,
) -> psycopg.Connection[Any]:
    url = temporary_database.database_url
    return psycopg.connect(
        host=url.host,
        port=url.port,
        dbname=url.database,
        user=url.username,
        password=url.password,
    )


def _read_json_lines(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line
    ]


def _assert_private_absent(value: object, evidence_name: str) -> None:
    serialized = json.dumps(value, sort_keys=True, default=str)
    if any(sentinel in serialized for sentinel in PRIVATE_SENTINELS):
        raise RuntimeError(f"Private stance leaked into {evidence_name}.")


def _verify_durable_result(
    temporary_database: TemporaryDatabase,
    *,
    blocked: dict[str, Any],
    cancelled: dict[str, Any],
    provider_calls: list[dict[str, Any]],
) -> None:
    if blocked["floor_grant_id"] != cancelled["floor_grant_id"]:
        raise RuntimeError("Blocked and cancelled provider grants did not match.")
    if blocked["generation_request_id"] != cancelled["generation_request_id"]:
        raise RuntimeError("Blocked and cancelled generation requests did not match.")
    if blocked["request_status"] != "RUNNING":
        raise RuntimeError("Provider did not prove a durable RUNNING request.")

    cancelled_grant_id = str(cancelled["floor_grant_id"])
    cancelled_request_id = str(cancelled["generation_request_id"])
    with _database_connection(temporary_database) as connection:
        session_rows = connection.execute(
            "SELECT id, status, last_sequence FROM simulation_sessions"
        ).fetchall()
        if len(session_rows) != 1:
            raise RuntimeError(f"Expected one D2-D3 session, got {session_rows!r}.")
        session_id, status, last_sequence = session_rows[0]
        if status in ("PREPARATION", "COMPLETED"):
            raise RuntimeError(f"D2-D3 lifecycle was not active: {session_rows[0]!r}")

        events = connection.execute(
            "SELECT sequence, event_type, payload FROM discussion_events "
            "WHERE session_id = %s ORDER BY sequence",
            (session_id,),
        ).fetchall()
        if [row[0] for row in events] != list(range(1, int(last_sequence) + 1)):
            raise RuntimeError("D2-D3 DiscussionEvent sequence is not contiguous.")

        cancelled_requests = connection.execute(
            "SELECT id::text, status, failure_code, started_at, failed_at "
            "FROM llm_generation_requests WHERE session_id = %s "
            "AND floor_grant_id::text = %s",
            (session_id, cancelled_grant_id),
        ).fetchall()
        if len(cancelled_requests) != 1:
            raise RuntimeError(
                f"Cancelled grant request count mismatch: {cancelled_requests!r}"
            )
        request_id, request_status, failure_code, started_at, failed_at = (
            cancelled_requests[0]
        )
        if (
            request_id != cancelled_request_id
            or request_status != "FAILED"
            or failure_code != "INTERNAL_ERROR"
            or started_at is None
            or failed_at is None
            or failed_at < started_at
        ):
            raise RuntimeError(
                f"Cancelled request terminal state mismatch: {cancelled_requests!r}"
            )

        cancelled_utterances = connection.execute(
            "SELECT count(*) FROM ai_utterances WHERE session_id = %s "
            "AND floor_grant_id::text = %s",
            (session_id, cancelled_grant_id),
        ).fetchone()
        cancelled_releases = connection.execute(
            "SELECT reason_code FROM floor_releases WHERE session_id = %s "
            "AND grant_id::text = %s",
            (session_id, cancelled_grant_id),
        ).fetchall()
        cancelled_public_utterances = connection.execute(
            "SELECT count(*) FROM discussion_events WHERE session_id = %s "
            "AND event_type = 'participant.utterance.created' "
            "AND payload->>'floor_grant_id' = %s",
            (session_id, cancelled_grant_id),
        ).fetchone()
        cancelled_public_releases = connection.execute(
            "SELECT payload->>'reason_code' FROM discussion_events "
            "WHERE session_id = %s AND event_type = 'floor.released' "
            "AND payload->>'grant_id' = %s",
            (session_id, cancelled_grant_id),
        ).fetchall()
        if cancelled_utterances != (0,) or cancelled_public_utterances != (0,):
            raise RuntimeError("Cancelled generation persisted an utterance.")
        if cancelled_releases != [("INTERRUPTED",)]:
            raise RuntimeError(
                f"Cancelled floor release mismatch: {cancelled_releases!r}"
            )
        if cancelled_public_releases != [("INTERRUPTED",)]:
            raise RuntimeError(
                "Cancelled public floor release was not exactly-once INTERRUPTED."
            )

        duplicate_requests = connection.execute(
            "SELECT floor_grant_id, count(*) FROM llm_generation_requests "
            "WHERE session_id = %s GROUP BY floor_grant_id HAVING count(*) > 1",
            (session_id,),
        ).fetchall()
        duplicate_utterances = connection.execute(
            "SELECT floor_grant_id, count(*) FROM ai_utterances "
            "WHERE session_id = %s GROUP BY floor_grant_id HAVING count(*) > 1",
            (session_id,),
        ).fetchall()
        duplicate_releases = connection.execute(
            "SELECT grant_id, count(*) FROM floor_releases "
            "WHERE session_id = %s GROUP BY grant_id HAVING count(*) > 1",
            (session_id,),
        ).fetchall()
        if duplicate_requests or duplicate_utterances or duplicate_releases:
            raise RuntimeError(
                "D2-D3 replay produced duplicate durable side effects: "
                f"{duplicate_requests!r}, {duplicate_utterances!r}, "
                f"{duplicate_releases!r}"
            )

        utterance_contents = connection.execute(
            "SELECT content FROM ai_utterances WHERE session_id = %s",
            (session_id,),
        ).fetchall()
        _assert_private_absent([row[2] for row in events], "public events")
        _assert_private_absent(utterance_contents, "durable transcript")

    cancelled_provider_calls = [
        row for row in provider_calls if row.get("floor_grant_id") == cancelled_grant_id
    ]
    if len(cancelled_provider_calls) != 1:
        raise RuntimeError(
            "Repeated recovery invoked the cancelled provider grant more than once."
        )
    _assert_private_absent(blocked, "provider blocked evidence")
    _assert_private_absent(cancelled, "provider cancellation evidence")
    _assert_private_absent(provider_calls, "provider call evidence")


async def _seed_question_async(temporary_database: TemporaryDatabase) -> None:
    engine = create_database_engine(temporary_database.database_settings())
    session_factory = create_database_session_factory(engine)
    try:
        await seed_question_persona_foundation(session_factory)
        await seed_ai_runtime_prompt_versions(session_factory)
        async with session_factory() as session:
            async with session.begin():
                for assignment, sentinel in zip(
                    INTERNAL_VALIDATION_BUNDLE.assignments,
                    PRIVATE_SENTINELS,
                    strict=True,
                ):
                    await session.execute(
                        update(PersonaPrivateStance)
                        .where(PersonaPrivateStance.assignment_id == assignment.id)
                        .values(
                            initial_position=sentinel,
                            private_information=sentinel,
                            preferred_group_role=sentinel,
                        )
                    )
    finally:
        await dispose_database_engine(engine)


def _seed_question(temporary_database: TemporaryDatabase) -> None:
    asyncio.run(
        _seed_question_async(temporary_database),
        loop_factory=asyncio.SelectorEventLoop,
    )


def _run_playwright(environment_overrides: dict[str, str]) -> None:
    pnpm = shutil.which("pnpm.cmd" if os.name == "nt" else "pnpm")
    if pnpm is None:
        raise RuntimeError("pnpm is required to run the D2-D3 Browser scenario.")
    environment = os.environ.copy()
    environment["CI"] = "true"
    environment.update(environment_overrides)
    completed = subprocess.run(
        [
            pnpm,
            "exec",
            "playwright",
            "test",
            "e2e/p1-6d-cancellation-recovery.spec.ts",
        ],
        cwd=WEB_ROOT,
        env=environment,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"D2-D3 Playwright scenario failed with exit code {completed.returncode}."
        )


def _run_browser_flow(temporary_database: TemporaryDatabase) -> None:
    _require_available_port(WEB_PORT)
    _require_available_port(API_PORT)
    node = shutil.which("node.exe" if os.name == "nt" else "node")
    if node is None:
        raise RuntimeError("Node.js is required to run the D2-D3 Web server.")
    next_cli = WEB_ROOT / "node_modules" / "next" / "dist" / "bin" / "next"
    if not next_cli.is_file():
        raise RuntimeError("Next.js is not installed; run the frozen install gate.")

    database_url = temporary_database.database_settings().database_url
    with tempfile.TemporaryDirectory(prefix="gia_p16d_d2d3_") as directory:
        temporary_path = Path(directory)
        api_log = temporary_path / "api.log"
        web_log = temporary_path / "web.log"
        provider_calls = temporary_path / "provider-calls.jsonl"
        block_arm = temporary_path / "provider-block.arm"
        block_claimed = temporary_path / "provider-block.claimed"
        provider_blocked = temporary_path / "provider-blocked.json"
        provider_cancelled = temporary_path / "provider-cancelled.json"
        fake_app_module = temporary_path / "gia_p16d_d2d3_fake_provider_app.py"
        block_arm.write_text("armed", encoding="utf-8")
        fake_app_module.write_text(_provider_module_source(), encoding="utf-8")

        api_environment = {
            "GIA_API_CORS_ORIGINS": f'["{WEB_ORIGIN}"]',
            "GIA_API_DATABASE_URL": database_url.get_secret_value(),
            "GIA_API_ENVIRONMENT": "test",
            "GIA_API_SESSION_COOKIE_SECURE": "false",
            "GIA_API_ZHIPU_API_KEY": "p1-6d-network-free-placeholder",
            "GIA_API_ZHIPU_MODEL": "p1-6d-network-free-model",
            "GIA_API_SESSION_PHASE_DURATIONS": (
                '{"preparation_seconds":1,'
                '"opening_statements_seconds":8,'
                '"exploration_seconds":30,'
                '"conflict_and_evaluation_seconds":30,'
                '"convergence_seconds":30,'
                '"final_summary_seconds":30}'
            ),
            "GIA_P16D_D2D3_BLOCK_ARM": str(block_arm),
            "GIA_P16D_D2D3_BLOCK_CLAIMED": str(block_claimed),
            "GIA_P16D_D2D3_PROVIDER_BLOCKED": str(provider_blocked),
            "GIA_P16D_D2D3_PROVIDER_CALLS": str(provider_calls),
            "GIA_P16D_D2D3_PROVIDER_CANCELLED": str(provider_cancelled),
            "PYTHONPATH": os.pathsep.join(
                filter(None, (str(temporary_path), os.environ.get("PYTHONPATH")))
            ),
            "PYTHONUNBUFFERED": "1",
        }
        api_command = [
            sys.executable,
            "-m",
            "uvicorn",
            "gia_p16d_d2d3_fake_provider_app:app",
            "--host",
            "localhost",
            "--port",
            str(API_PORT),
            "--loop",
            "group_interview_arena_api.core.event_loop:create_runtime_event_loop",
        ]

        try:
            with _server_process(
                api_command,
                cwd=API_ROOT,
                environment=api_environment,
                log_path=api_log,
            ) as api_process:
                _wait_for_http(f"{API_ORIGIN}/health", api_process, api_log)
                with _server_process(
                    [node, str(next_cli), "dev"],
                    cwd=WEB_ROOT,
                    environment={"NEXT_PUBLIC_API_BASE_URL": API_ORIGIN},
                    log_path=web_log,
                ) as web_process:
                    _wait_for_http(WEB_ORIGIN, web_process, web_log)
                    _run_playwright(
                        {
                            "GIA_P16D_D2D3_API_LOG": str(api_log),
                            "GIA_P16D_D2D3_API_ORIGIN": API_ORIGIN,
                            "GIA_P16D_D2D3_PROVIDER_BLOCKED": str(provider_blocked),
                            "GIA_P16D_D2D3_PROVIDER_CALLS": str(provider_calls),
                            "GIA_P16D_D2D3_PROVIDER_CANCELLED": str(provider_cancelled),
                        }
                    )
        except Exception:
            print("D2-D3 API server log tail:", file=sys.stderr)
            print(_log_tail(api_log), file=sys.stderr)
            print("D2-D3 Web server log tail:", file=sys.stderr)
            print(_log_tail(web_log), file=sys.stderr)
            if provider_calls.exists():
                print("D2-D3 provider calls:", file=sys.stderr)
                print(provider_calls.read_text(encoding="utf-8"), file=sys.stderr)
            raise
        finally:
            _wait_for_port_release(WEB_PORT)
            _wait_for_port_release(API_PORT)

        required_evidence = (provider_blocked, provider_cancelled, provider_calls)
        if not all(path.exists() for path in required_evidence):
            raise RuntimeError("D2-D3 provider evidence is incomplete.")
        _verify_durable_result(
            temporary_database,
            blocked=json.loads(provider_blocked.read_text(encoding="utf-8")),
            cancelled=json.loads(provider_cancelled.read_text(encoding="utf-8")),
            provider_calls=_read_json_lines(provider_calls),
        )


def main() -> int:
    database_settings = IntegrationDatabaseSettings()  # pyright: ignore[reportCallIssue]
    with temporary_database_context(
        database_settings,
        P1_6D_BROWSER_DATABASE_PREFIX,
    ) as temporary_database:
        migrate_database(temporary_database)
        _seed_question(temporary_database)
        _run_browser_flow(temporary_database)
    print(
        "P1-6D D2-D3 passed: durable RUNNING generation cancellation, FAILED terminal "
        "recovery, exactly-once INTERRUPTED release, reconnect consistency, private "
        "stance isolation, and repeated recovery without duplicate side effects."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
