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
from uuid import UUID

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
    "P16D_PRIVATE_ALPHA_DO_NOT_DISCLOSE",
    "P16D_PRIVATE_BRAVO_DO_NOT_DISCLOSE",
    "P16D_PRIVATE_CHARLIE_DO_NOT_DISCLOSE",
)
V3_PROMPT_ID = UUID("56000000-0000-4000-8000-000000000003")


def _provider_module_source() -> str:
    return textwrap.dedent(
        """
        import json
        import os
        import time
        from pathlib import Path

        import psycopg

        from group_interview_arena_api.modules.ai_runtime import composition
        from group_interview_arena_api.modules.ai_runtime.generation import RawGenerationSuccess

        PRIVATE_SENTINELS = (
            "P16D_PRIVATE_ALPHA_DO_NOT_DISCLOSE",
            "P16D_PRIVATE_BRAVO_DO_NOT_DISCLOSE",
            "P16D_PRIVATE_CHARLIE_DO_NOT_DISCLOSE",
        )

        def _database_url():
            return os.environ["GIA_API_DATABASE_URL"].replace(
                "postgresql+psycopg://", "postgresql://", 1
            )

        def _append(row):
            row["occurred_at"] = time.time()
            with Path(os.environ["GIA_P16D_PROVIDER_CALLS"]).open(
                "a", encoding="utf-8"
            ) as stream:
                stream.write(json.dumps(row, sort_keys=True) + "\\n")

        class NetworkFreeP16DHappyPathProvider:
            async def invoke(self, invocation):
                prompt = invocation.rendered_prompt
                if any(sentinel in prompt for sentinel in PRIVATE_SENTINELS):
                    raise RuntimeError("Private stance reached MemoryDerivationInput.")
                marker = "Public derivation input:\\n"
                if marker not in prompt:
                    raise RuntimeError("Semantic prompt omitted public derivation input.")
                derivation_input = json.loads(prompt.rsplit(marker, 1)[1])
                sequences = [
                    item["sequence"]
                    for item in derivation_input.get("utterances", [])
                    if isinstance(item.get("sequence"), int)
                ]
                if not sequences:
                    raise RuntimeError("Semantic derivation received no public evidence.")
                _append({
                    "workload": "semantic",
                    "source_sequences": sequences,
                    "provider_identifier": invocation.provider_identifier,
                    "model_identifier": invocation.model_identifier,
                    "configuration_version": invocation.configuration_version,
                })
                return RawGenerationSuccess(content=json.dumps({
                    "patches": [{
                        "operation": "ADD",
                        "kind": "PROPOSAL",
                        "target_memory_item_id": None,
                        "canonical_text": "P1-6D public deterministic memory",
                        "source_sequences": sequences[-32:],
                    }]
                }))

            async def __call__(self, generation_input):
                prompt = generation_input.rendered_prompt
                sentinel_indexes = [
                    index
                    for index, sentinel in enumerate(PRIVATE_SENTINELS)
                    if sentinel in prompt
                ]
                required_sections = (
                    "结构化公开讨论记忆（可能为空；它是派生上下文，不是原始证据）：",
                    "记忆游标之后的完整公开发言尾部（可能为空）：",
                    "当前阶段剩余秒数（未知时为 UNKNOWN）：",
                )
                if len(sentinel_indexes) != 1:
                    raise RuntimeError(
                        "Candidate prompt did not contain exactly one private stance."
                    )
                if not all(section in prompt for section in required_sections):
                    raise RuntimeError("Candidate V3 context contract was incomplete.")
                if (
                    str(generation_input.prompt_version_id)
                    != "56000000-0000-4000-8000-000000000003"
                    or generation_input.prompt_version_number != 3
                    or generation_input.prompt_key != "AI_CANDIDATE_TURN"
                ):
                    raise RuntimeError("Candidate generation did not use accepted prompt V3.")
                with psycopg.connect(_database_url()) as connection:
                    row = connection.execute(
                        "SELECT status, request_metadata FROM llm_generation_requests "
                        "WHERE id = %s",
                        (generation_input.generation_request_id,),
                    ).fetchone()
                if row is None or row[0] != "RUNNING":
                    raise RuntimeError(
                        f"Candidate request was not durable RUNNING: {row!r}"
                    )
                call = {
                    "workload": "candidate",
                    "generation_request_id": str(
                        generation_input.generation_request_id
                    ),
                    "participant_id": str(generation_input.participant_id),
                    "floor_grant_id": str(generation_input.floor_grant_id),
                    "phase": str(generation_input.phase),
                    "prompt_version_id": str(generation_input.prompt_version_id),
                    "prompt_version_number": generation_input.prompt_version_number,
                    "prompt_key": generation_input.prompt_key,
                    "private_sentinel_index": sentinel_indexes[0],
                    "request_metadata": row[1],
                }
                _append(call)
                prefix = (
                    f"P16D_AI_PUBLIC:{generation_input.participant_id}:"
                    f"{generation_input.phase}:{generation_input.floor_grant_id}:"
                )
                return RawGenerationSuccess(
                    content=prefix + "A" * max(1, 1_400 - len(prefix))
                )

        _provider = NetworkFreeP16DHappyPathProvider()

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


def _assert_no_private_sentinel(value: object, evidence_name: str) -> None:
    serialized = json.dumps(value, sort_keys=True, default=str)
    if any(sentinel in serialized for sentinel in PRIVATE_SENTINELS):
        raise RuntimeError(f"Private sentinel leaked into {evidence_name}.")


def _verify_durable_result(
    temporary_database: TemporaryDatabase,
    provider_calls: list[dict[str, Any]],
) -> None:
    with _database_connection(temporary_database) as connection:
        session_rows = connection.execute(
            "SELECT id, status, last_sequence, current_floor_grant_id "
            "FROM simulation_sessions"
        ).fetchall()
        if len(session_rows) != 1:
            raise RuntimeError(f"Expected one D2-D1 session, got {session_rows!r}.")
        session_id, status, last_sequence, current_grant = session_rows[0]
        if status != "EXPLORATION" or current_grant is None:
            raise RuntimeError(
                "D2-D1 did not reach the stable EXPLORATION Human floor: "
                f"{session_rows[0]!r}"
            )

        participants = connection.execute(
            "SELECT id, actor_kind, seat_order, question_persona_assignment_id "
            "FROM session_participants WHERE session_id = %s ORDER BY seat_order",
            (session_id,),
        ).fetchall()
        candidates = [row for row in participants if row[1] in ("HUMAN", "AI")]
        ai_rows = [row for row in candidates if row[1] == "AI"]
        human_rows = [row for row in candidates if row[1] == "HUMAN"]
        if len(candidates) != 4 or len(ai_rows) != 3 or len(human_rows) != 1:
            raise RuntimeError(f"D2-D1 authoritative roster mismatch: {participants!r}")
        grant_owner = connection.execute(
            "SELECT participant_id FROM floor_grants WHERE id = %s",
            (current_grant,),
        ).fetchone()
        if grant_owner is None or grant_owner[0] != human_rows[0][0]:
            raise RuntimeError("D2-D1 did not stop at the expected Human floor.")
        ai_ids = {str(row[0]) for row in ai_rows}
        expected_private_index = {
            str(row[0]): int(str(row[3])[-1]) - 1 for row in ai_rows
        }

        events = connection.execute(
            "SELECT sequence, event_type, payload FROM discussion_events "
            "WHERE session_id = %s ORDER BY sequence",
            (session_id,),
        ).fetchall()
        if [row[0] for row in events] != list(range(1, int(last_sequence) + 1)):
            raise RuntimeError("DiscussionEvent sequence is not contiguous.")
        utterance_events = [
            row for row in events if row[1] == "participant.utterance.created"
        ]
        human_events = [
            row for row in utterance_events if row[2]["actor_kind"] == "HUMAN"
        ]
        ai_events = [row for row in utterance_events if row[2]["actor_kind"] == "AI"]
        if (
            not human_events
            or {row[2]["participant_id"] for row in ai_events} != ai_ids
        ):
            raise RuntimeError("D2-D1 did not include Human and all three AI speakers.")

        lifecycle = [
            row[2]["status"] for row in events if row[1] == "session.state_changed"
        ]
        try:
            opening_index = lifecycle.index("OPENING_STATEMENTS")
            exploration_index = lifecycle.index("EXPLORATION")
        except ValueError as exception:
            raise RuntimeError(
                f"D2-D1 lifecycle evidence is incomplete: {lifecycle!r}"
            ) from exception
        if opening_index >= exploration_index:
            raise RuntimeError(f"D2-D1 lifecycle order is invalid: {lifecycle!r}")

        memory_state = connection.execute(
            "SELECT revision, source_through_sequence, structured_state "
            "FROM discussion_memory_states WHERE session_id = %s",
            (session_id,),
        ).fetchone()
        memory_revisions = connection.execute(
            "SELECT revision, base_revision, patches FROM discussion_memory_revisions "
            "WHERE session_id = %s ORDER BY revision",
            (session_id,),
        ).fetchall()
        if memory_state is None or memory_state[0] < 1 or not memory_revisions:
            raise RuntimeError("D2-D1 did not persist a durable Memory revision.")

        requests = connection.execute(
            "SELECT request.id, request.participant_id, request.floor_grant_id, "
            "request.status, request.request_metadata, request.prompt_version_id, "
            "prompt.prompt_key, prompt.version_number "
            "FROM llm_generation_requests AS request "
            "JOIN prompt_versions AS prompt ON prompt.id = request.prompt_version_id "
            "WHERE request.session_id = %s ORDER BY request.requested_at, request.id",
            (session_id,),
        ).fetchall()
        request_counts = connection.execute(
            "SELECT floor_grant_id, count(id) FROM llm_generation_requests "
            "WHERE session_id = %s GROUP BY floor_grant_id",
            (session_id,),
        ).fetchall()
        if not request_counts or any(row[1] != 1 for row in request_counts):
            raise RuntimeError(
                f"D2-D1 request count per AI grant was not one: {request_counts!r}"
            )
        if any(row[3] != "COMPLETED" for row in requests):
            raise RuntimeError(
                f"D2-D1 retained a non-completed AI request: {requests!r}"
            )
        memory_backed = [
            row
            for row in requests
            if row[4].get("schema_version") == 2
            and row[4].get("memory_revision", 0) > 0
            and row[5] == V3_PROMPT_ID
            and row[6:8] == ("AI_CANDIDATE_TURN", 3)
        ]
        if not memory_backed:
            raise RuntimeError(
                "No completed candidate consumed Memory + V3 + Metadata V2."
            )

        exact_once_rows = connection.execute(
            "SELECT request.floor_grant_id, count(DISTINCT utterance.id), "
            "count(DISTINCT event.sequence), count(DISTINCT release.grant_id), "
            "min(release.reason_code) FROM llm_generation_requests AS request "
            "LEFT JOIN ai_utterances AS utterance "
            "ON utterance.generation_request_id = request.id "
            "LEFT JOIN discussion_events AS event "
            "ON event.session_id = request.session_id "
            "AND event.event_type = 'participant.utterance.created' "
            "AND event.payload->>'floor_grant_id' = request.floor_grant_id::text "
            "LEFT JOIN floor_releases AS release "
            "ON release.session_id = request.session_id "
            "AND release.grant_id = request.floor_grant_id "
            "WHERE request.session_id = %s GROUP BY request.floor_grant_id",
            (session_id,),
        ).fetchall()
        if not exact_once_rows or any(
            row[1:] != (1, 1, 1, "SPEAKER_FINISHED") for row in exact_once_rows
        ):
            raise RuntimeError(
                f"D2-D1 AI exact-once evidence mismatch: {exact_once_rows!r}"
            )

        _assert_no_private_sentinel([row[2] for row in events], "DiscussionEvent")
        _assert_no_private_sentinel(memory_state[2], "structured Memory")
        _assert_no_private_sentinel(
            [row[2] for row in memory_revisions], "Memory patch journal"
        )

    candidate_calls = [row for row in provider_calls if row["workload"] == "candidate"]
    semantic_calls = [row for row in provider_calls if row["workload"] == "semantic"]
    if not candidate_calls or not semantic_calls:
        raise RuntimeError("D2-D1 did not exercise candidate and semantic workloads.")
    candidate_grants = [row["floor_grant_id"] for row in candidate_calls]
    if len(candidate_grants) != len(set(candidate_grants)):
        raise RuntimeError("A D2-D1 AI grant reached the provider more than once.")
    if set(candidate_grants) != {str(row[2]) for row in requests}:
        raise RuntimeError("Provider calls did not map one-to-one to AI requests.")
    if {row["participant_id"] for row in candidate_calls} != ai_ids:
        raise RuntimeError("Provider calls did not cover all three AI seats.")
    for row in candidate_calls:
        participant_id = str(row["participant_id"])
        if row["private_sentinel_index"] != expected_private_index[participant_id]:
            raise RuntimeError(
                "An AI candidate received another seat's private stance."
            )
    _assert_no_private_sentinel(provider_calls, "provider evidence log")


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
        raise RuntimeError("pnpm is required to run the D2-D1 Browser scenario.")
    environment = os.environ.copy()
    environment["CI"] = "true"
    environment.update(environment_overrides)
    completed = subprocess.run(
        [pnpm, "exec", "playwright", "test", "e2e/p1-6d-happy-path.spec.ts"],
        cwd=WEB_ROOT,
        env=environment,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"D2-D1 Playwright scenario failed with exit code {completed.returncode}."
        )


def _run_browser_flow(temporary_database: TemporaryDatabase) -> None:
    _require_available_port(WEB_PORT)
    _require_available_port(API_PORT)
    node = shutil.which("node.exe" if os.name == "nt" else "node")
    if node is None:
        raise RuntimeError("Node.js is required to run the D2-D1 Web server.")
    next_cli = WEB_ROOT / "node_modules" / "next" / "dist" / "bin" / "next"
    if not next_cli.is_file():
        raise RuntimeError("Next.js is not installed; run the frozen install gate.")

    database_url = temporary_database.database_settings().database_url
    with tempfile.TemporaryDirectory(prefix="gia_p16d_d2d1_") as directory:
        temporary_path = Path(directory)
        api_log = temporary_path / "api.log"
        web_log = temporary_path / "web.log"
        provider_calls = temporary_path / "provider-calls.jsonl"
        fake_app_module = temporary_path / "gia_p16d_d2d1_fake_provider_app.py"
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
            "GIA_P16D_PROVIDER_CALLS": str(provider_calls),
            "PYTHONPATH": os.pathsep.join(
                filter(None, (str(temporary_path), os.environ.get("PYTHONPATH")))
            ),
            "PYTHONUNBUFFERED": "1",
        }
        api_command = [
            sys.executable,
            "-m",
            "uvicorn",
            "gia_p16d_d2d1_fake_provider_app:app",
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
                            "GIA_P16D_API_ORIGIN": API_ORIGIN,
                            "GIA_P16D_PROVIDER_CALLS": str(provider_calls),
                        }
                    )
        except Exception:
            print("D2-D1 API server log tail:", file=sys.stderr)
            print(_log_tail(api_log), file=sys.stderr)
            print("D2-D1 Web server log tail:", file=sys.stderr)
            print(_log_tail(web_log), file=sys.stderr)
            if provider_calls.exists():
                print("D2-D1 provider calls:", file=sys.stderr)
                print(provider_calls.read_text(encoding="utf-8"), file=sys.stderr)
            raise
        finally:
            _wait_for_port_release(WEB_PORT)
            _wait_for_port_release(API_PORT)

        if not provider_calls.exists():
            raise RuntimeError("D2-D1 provider evidence was not created.")
        _verify_durable_result(
            temporary_database,
            _read_json_lines(provider_calls),
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
        "P1-6D D2-D1 passed: real UI Human plus exactly three AI, network-free "
        "candidate/semantic workloads, contiguous public evidence, durable Memory + "
        "V3/V2 provenance, private-stance isolation, EXPLORATION progression, "
        "exact-once persistence, and dedicated PostgreSQL/server cleanup."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
