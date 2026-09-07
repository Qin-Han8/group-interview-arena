import json
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
import threading
from pathlib import Path
from typing import Any, BinaryIO

import psycopg
from browser_e2e import (
    API_ORIGIN,
    API_PORT,
    API_RESTART_DOWNTIME_SECONDS,
    API_ROOT,
    SHUTDOWN_TIMEOUT_SECONDS,
    WEB_ORIGIN,
    WEB_PORT,
    WEB_ROOT,
    _log_tail,  # pyright: ignore[reportPrivateUsage]
    _require_available_port,  # pyright: ignore[reportPrivateUsage]
    _start_server_process,  # pyright: ignore[reportPrivateUsage]
    _stop_server_process,  # pyright: ignore[reportPrivateUsage]
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
from p1_6d_happy_path_e2e import (
    PRIVATE_SENTINELS,
    _seed_question,  # pyright: ignore[reportPrivateUsage]
)


def _provider_module_source() -> str:
    sentinels = repr(PRIVATE_SENTINELS)
    return textwrap.dedent(
        f"""
        import asyncio
        import json
        import os
        import time
        from pathlib import Path

        import psycopg

        from group_interview_arena_api.modules.ai_runtime import composition
        from group_interview_arena_api.modules.ai_runtime.generation import RawGenerationSuccess

        PRIVATE_SENTINELS = {sentinels}

        def _database_url():
            return os.environ["GIA_API_DATABASE_URL"].replace(
                "postgresql+psycopg://", "postgresql://", 1
            )

        def _append(row):
            row["occurred_at"] = time.time()
            with Path(os.environ["GIA_P16D_FINAL_PROVIDER_CALLS"]).open(
                "a", encoding="utf-8"
            ) as stream:
                stream.write(json.dumps(row, sort_keys=True) + "\\n")

        class NetworkFreeP16DFinalProvider:
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
                _append({{
                    "workload": "semantic",
                    "source_sequences": sequences,
                    "provider_identifier": invocation.provider_identifier,
                    "model_identifier": invocation.model_identifier,
                    "configuration_version": invocation.configuration_version,
                }})
                return RawGenerationSuccess(content=json.dumps({{
                    "patches": [{{
                        "operation": "ADD",
                        "kind": "PROPOSAL",
                        "target_memory_item_id": None,
                        "canonical_text": "P1-6D final public deterministic memory",
                        "source_sequences": sequences[-32:],
                    }}]
                }}))

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
                    raise RuntimeError("Candidate generation did not use accepted V3.")

                with psycopg.connect(_database_url()) as connection:
                    row = connection.execute(
                        "SELECT status, request_metadata FROM llm_generation_requests "
                        "WHERE id = %s",
                        (generation_input.generation_request_id,),
                    ).fetchone()
                if row is None or row[0] != "RUNNING":
                    raise RuntimeError(
                        f"Candidate request was not durable RUNNING: {{row!r}}"
                    )

                request_id = str(generation_input.generation_request_id)
                floor_grant_id = str(generation_input.floor_grant_id)
                _append({{
                    "workload": "candidate",
                    "generation_request_id": request_id,
                    "participant_id": str(generation_input.participant_id),
                    "floor_grant_id": floor_grant_id,
                    "phase": str(generation_input.phase),
                    "prompt_version_id": str(generation_input.prompt_version_id),
                    "prompt_version_number": generation_input.prompt_version_number,
                    "prompt_key": generation_input.prompt_key,
                    "private_sentinel_index": sentinel_indexes[0],
                    "request_metadata": row[1],
                }})

                arm = Path(os.environ["GIA_P16D_FINAL_CANCELLATION_ARM"])
                claimed = Path(os.environ["GIA_P16D_FINAL_CANCELLATION_CLAIMED"])
                should_block = False
                try:
                    arm.replace(claimed)
                    should_block = True
                except FileNotFoundError:
                    pass

                if should_block:
                    evidence = {{
                        "generation_request_id": request_id,
                        "floor_grant_id": floor_grant_id,
                        "request_status": "RUNNING",
                    }}
                    Path(os.environ["GIA_P16D_FINAL_PROVIDER_BLOCKED"]).write_text(
                        json.dumps(evidence, sort_keys=True), encoding="utf-8"
                    )
                    try:
                        await asyncio.Event().wait()
                    except asyncio.CancelledError:
                        Path(
                            os.environ["GIA_P16D_FINAL_PROVIDER_CANCELLED"]
                        ).write_text(
                            json.dumps(evidence, sort_keys=True), encoding="utf-8"
                        )
                        raise

                prefix = (
                    f"P16D_FINAL_AI_PUBLIC:{{generation_input.participant_id}}:"
                    f"{{generation_input.phase}}:{{generation_input.floor_grant_id}}:"
                )
                return RawGenerationSuccess(
                    content=prefix + "A" * max(1, 1_400 - len(prefix))
                )

        _provider = NetworkFreeP16DFinalProvider()

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
    blocked: dict[str, Any],
    cancelled: dict[str, Any],
    provider_calls: list[dict[str, Any]],
) -> None:
    cancelled_request_id = str(cancelled["generation_request_id"])
    cancelled_grant_id = str(cancelled["floor_grant_id"])
    if blocked != cancelled:
        raise RuntimeError("Blocked/cancelled provider evidence did not match.")

    with _database_connection(temporary_database) as connection:
        session_rows = connection.execute(
            "SELECT id, status, last_sequence, current_floor_grant_id, "
            "phase_started_at, phase_deadline_at FROM simulation_sessions"
        ).fetchall()
        if len(session_rows) != 1:
            raise RuntimeError(f"Expected one final session, got {session_rows!r}.")
        session_id, status, last_sequence, current_grant, started_at, deadline_at = (
            session_rows[0]
        )
        if (
            status != "COMPLETED"
            or current_grant is not None
            or started_at is not None
            or deadline_at is not None
        ):
            raise RuntimeError(
                f"Final session state was not terminal: {session_rows!r}."
            )

        participants = connection.execute(
            "SELECT id, actor_kind FROM session_participants WHERE session_id = %s",
            (session_id,),
        ).fetchall()
        human_ids = {str(row[0]) for row in participants if row[1] == "HUMAN"}
        ai_ids = {str(row[0]) for row in participants if row[1] == "AI"}
        if len(human_ids) != 1 or len(ai_ids) != 3:
            raise RuntimeError(
                f"Final authoritative roster mismatch: {participants!r}."
            )

        events = connection.execute(
            "SELECT sequence, event_type, payload FROM discussion_events "
            "WHERE session_id = %s ORDER BY sequence",
            (session_id,),
        ).fetchall()
        if [row[0] for row in events] != list(range(1, int(last_sequence) + 1)):
            raise RuntimeError("Final DiscussionEvent sequence is not contiguous.")
        lifecycle = [
            row[2].get("status") for row in events if row[1] == "session.state_changed"
        ]
        expected_lifecycle = [
            "PREPARATION",
            "OPENING_STATEMENTS",
            "EXPLORATION",
            "CONFLICT_AND_EVALUATION",
            "CONVERGENCE",
            "FINAL_SUMMARY",
            "COMPLETED",
        ]
        if lifecycle != expected_lifecycle:
            raise RuntimeError(f"Final lifecycle mismatch: {lifecycle!r}.")
        terminal_lifecycle_events = [
            row
            for row in events
            if row[1] == "session.state_changed"
            and row[2].get("previous_status") == "FINAL_SUMMARY"
            and row[2].get("status") == "COMPLETED"
            and row[2].get("trigger") == "PHASE_DEADLINE"
        ]
        if len(terminal_lifecycle_events) != 1:
            raise RuntimeError(
                "Final durable lifecycle event mismatch: "
                f"{terminal_lifecycle_events!r}."
            )

        memory_state = connection.execute(
            "SELECT revision FROM discussion_memory_states WHERE session_id = %s",
            (session_id,),
        ).fetchone()
        memory_revisions = connection.execute(
            "SELECT revision, patches FROM discussion_memory_revisions "
            "WHERE session_id = %s ORDER BY revision",
            (session_id,),
        ).fetchall()
        if memory_state is None or memory_state[0] < 1 or not memory_revisions:
            raise RuntimeError("Final acceptance did not persist Memory revision >= 1.")

        requests = connection.execute(
            "SELECT request.id, request.floor_grant_id, request.participant_id, "
            "request.status, request.failure_code, request.request_metadata, "
            "prompt.prompt_key, prompt.version_number "
            "FROM llm_generation_requests AS request "
            "JOIN prompt_versions AS prompt ON prompt.id = request.prompt_version_id "
            "WHERE request.session_id = %s ORDER BY request.requested_at, request.id",
            (session_id,),
        ).fetchall()
        counts = connection.execute(
            "SELECT floor_grant_id, count(id) FROM llm_generation_requests "
            "WHERE session_id = %s GROUP BY floor_grant_id",
            (session_id,),
        ).fetchall()
        if any(row[1] != 1 for row in counts):
            raise RuntimeError(f"Duplicate generation request: {counts!r}.")
        if any(row[3] in ("REQUESTED", "RUNNING") for row in requests):
            raise RuntimeError("Final session retained a live generation request.")

        completed = [row for row in requests if row[3] == "COMPLETED"]
        completed_ai_ids = {str(row[2]) for row in completed}
        if not ai_ids.issubset(completed_ai_ids):
            raise RuntimeError("Not all three AI participants completed a generation.")
        memory_backed_v3 = [
            row
            for row in completed
            if row[6] == "AI_CANDIDATE_TURN"
            and row[7] == 3
            and row[5].get("schema_version") == 2
            and row[5].get("memory_revision", 0) > 0
        ]
        if not memory_backed_v3:
            raise RuntimeError("No completed V3/metadata-V2 Memory-backed request.")

        exact_once = connection.execute(
            "SELECT request.id, count(DISTINCT utterance.id), "
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
            "WHERE request.session_id = %s AND request.status = 'COMPLETED' "
            "GROUP BY request.id",
            (session_id,),
        ).fetchall()
        if not exact_once or any(
            row[1:] != (1, 1, 1, "SPEAKER_FINISHED") for row in exact_once
        ):
            raise RuntimeError(f"Completed AI exact-once mismatch: {exact_once!r}.")

        cancelled_rows = [
            row
            for row in requests
            if str(row[0]) == cancelled_request_id and str(row[1]) == cancelled_grant_id
        ]
        if len(cancelled_rows) != 1 or cancelled_rows[0][3:5] != (
            "FAILED",
            "INTERNAL_ERROR",
        ):
            raise RuntimeError(f"Cancelled request mismatch: {cancelled_rows!r}.")
        cancelled_metadata = cancelled_rows[0][5]
        if (
            cancelled_rows[0][6:] != ("AI_CANDIDATE_TURN", 3)
            or cancelled_metadata.get("schema_version") != 2
            or cancelled_metadata.get("memory_revision", 0) < 1
        ):
            raise RuntimeError(
                "Cancelled request was not a Memory-backed V3/metadata-V2 candidate: "
                f"{cancelled_rows!r}."
            )
        cancelled_shape = connection.execute(
            "SELECT count(DISTINCT utterance.id), count(DISTINCT event.sequence), "
            "count(DISTINCT release.grant_id), min(release.reason_code) "
            "FROM llm_generation_requests AS request "
            "LEFT JOIN ai_utterances AS utterance "
            "ON utterance.generation_request_id = request.id "
            "LEFT JOIN discussion_events AS event "
            "ON event.session_id = request.session_id "
            "AND event.event_type = 'participant.utterance.created' "
            "AND event.payload->>'floor_grant_id' = request.floor_grant_id::text "
            "LEFT JOIN floor_releases AS release "
            "ON release.session_id = request.session_id "
            "AND release.grant_id = request.floor_grant_id "
            "WHERE request.id = %s",
            (cancelled_request_id,),
        ).fetchone()
        if cancelled_shape != (0, 0, 1, "INTERRUPTED"):
            raise RuntimeError(f"Cancelled exact-once mismatch: {cancelled_shape!r}.")

        duplicate_events = connection.execute(
            "SELECT event_type, payload->>'grant_id', count(*) "
            "FROM discussion_events WHERE session_id = %s "
            "AND event_type IN ('floor.granted', 'floor.released') "
            "GROUP BY event_type, payload->>'grant_id' HAVING count(*) > 1",
            (session_id,),
        ).fetchall()
        if duplicate_events:
            raise RuntimeError(f"Duplicate floor event: {duplicate_events!r}.")

    candidate_calls = [row for row in provider_calls if row["workload"] == "candidate"]
    semantic_calls = [row for row in provider_calls if row["workload"] == "semantic"]
    candidate_grants = [row["floor_grant_id"] for row in candidate_calls]
    if len(candidate_grants) != len(set(candidate_grants)):
        raise RuntimeError("A final AI grant reached the provider more than once.")
    if candidate_grants.count(cancelled_grant_id) != 1 or not semantic_calls:
        raise RuntimeError("Final provider workload/cancellation evidence mismatch.")
    if {row["private_sentinel_index"] for row in candidate_calls} != {0, 1, 2}:
        raise RuntimeError("Final provider did not isolate all three private stances.")

    _assert_private_absent(events, "public DiscussionEvent ledger")
    _assert_private_absent(memory_revisions, "Memory patch journal")
    _assert_private_absent(provider_calls, "provider evidence")
    _assert_private_absent(blocked, "provider blocked evidence")
    _assert_private_absent(cancelled, "provider cancellation evidence")


def _run_playwright(environment: dict[str, str]) -> None:
    pnpm = shutil.which("pnpm.cmd" if os.name == "nt" else "pnpm")
    if pnpm is None:
        raise RuntimeError("pnpm is required for P1-6D final acceptance.")
    process_environment = os.environ.copy()
    process_environment["CI"] = "true"
    process_environment.update(environment)
    completed = subprocess.run(
        [pnpm, "exec", "playwright", "test", "e2e/p1-6d-final-acceptance.spec.ts"],
        cwd=WEB_ROOT,
        env=process_environment,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"P1-6D final Playwright failed with exit code {completed.returncode}."
        )


def _run_final_flow(temporary_database: TemporaryDatabase) -> None:
    _require_available_port(WEB_PORT)
    _require_available_port(API_PORT)
    node = shutil.which("node.exe" if os.name == "nt" else "node")
    if node is None:
        raise RuntimeError("Node.js is required for P1-6D final acceptance.")
    next_cli = WEB_ROOT / "node_modules" / "next" / "dist" / "bin" / "next"
    if not next_cli.is_file():
        raise RuntimeError("Next.js is not installed; run the frozen install gate.")

    database_url = temporary_database.database_settings().database_url
    with tempfile.TemporaryDirectory(prefix="gia_p16d_final_") as directory:
        temporary_path = Path(directory)
        api_log = temporary_path / "api.log"
        web_log = temporary_path / "web.log"
        restart_request = temporary_path / "restart-api.request"
        restart_ready = temporary_path / "restart-api.ready"
        provider_calls = temporary_path / "provider-calls.jsonl"
        cancellation_arm = temporary_path / "cancellation.arm"
        cancellation_claimed = temporary_path / "cancellation.claimed"
        provider_blocked = temporary_path / "provider-blocked.json"
        provider_cancelled = temporary_path / "provider-cancelled.json"
        fake_app = temporary_path / "gia_p16d_final_provider_app.py"
        fake_app.write_text(_provider_module_source(), encoding="utf-8")

        api_environment = {
            "GIA_API_CORS_ORIGINS": f'["{WEB_ORIGIN}"]',
            "GIA_API_DATABASE_URL": database_url.get_secret_value(),
            "GIA_API_ENVIRONMENT": "test",
            "GIA_API_SESSION_COOKIE_SECURE": "false",
            "GIA_API_ZHIPU_API_KEY": "p1-6d-network-free-placeholder",
            "GIA_API_ZHIPU_MODEL": "p1-6d-network-free-model",
            "GIA_API_SESSION_PHASE_DURATIONS": (
                '{"preparation_seconds":1,'
                '"opening_statements_seconds":1,'
                '"exploration_seconds":30,'
                '"conflict_and_evaluation_seconds":1,'
                '"convergence_seconds":1,'
                '"final_summary_seconds":1}'
            ),
            "GIA_P16D_FINAL_PROVIDER_CALLS": str(provider_calls),
            "GIA_P16D_FINAL_CANCELLATION_ARM": str(cancellation_arm),
            "GIA_P16D_FINAL_CANCELLATION_CLAIMED": str(cancellation_claimed),
            "GIA_P16D_FINAL_PROVIDER_BLOCKED": str(provider_blocked),
            "GIA_P16D_FINAL_PROVIDER_CANCELLED": str(provider_cancelled),
            "PYTHONPATH": os.pathsep.join(
                filter(None, (str(temporary_path), os.environ.get("PYTHONPATH")))
            ),
            "PYTHONUNBUFFERED": "1",
        }
        api_command = [
            sys.executable,
            "-m",
            "uvicorn",
            "gia_p16d_final_provider_app:app",
            "--host",
            "localhost",
            "--port",
            str(API_PORT),
            "--loop",
            "group_interview_arena_api.core.event_loop:create_runtime_event_loop",
        ]
        current_api: list[tuple[subprocess.Popen[bytes], BinaryIO] | None] = [
            _start_server_process(
                api_command,
                cwd=API_ROOT,
                environment=api_environment,
                log_path=api_log,
            )
        ]
        coordinator_errors: list[BaseException] = []
        coordinator_stop = threading.Event()

        def coordinate_api_restart() -> None:
            try:
                while not coordinator_stop.is_set():
                    if not restart_request.exists():
                        coordinator_stop.wait(0.05)
                        continue
                    running = current_api[0]
                    if running is None:
                        raise RuntimeError(
                            "Final API restart lacked a running process."
                        )
                    _stop_server_process(*running)
                    current_api[0] = None
                    _wait_for_port_release(API_PORT)
                    if coordinator_stop.wait(API_RESTART_DOWNTIME_SECONDS):
                        return
                    restarted = _start_server_process(
                        api_command,
                        cwd=API_ROOT,
                        environment=api_environment,
                        log_path=api_log,
                    )
                    current_api[0] = restarted
                    _wait_for_http(f"{API_ORIGIN}/health", restarted[0], api_log)
                    restart_ready.write_text("ready", encoding="utf-8")
                    return
            except BaseException as exception:
                coordinator_errors.append(exception)

        try:
            initial_api = current_api[0]
            assert initial_api is not None
            _wait_for_http(f"{API_ORIGIN}/health", initial_api[0], api_log)
            web_process = _start_server_process(
                [node, str(next_cli), "dev"],
                cwd=WEB_ROOT,
                environment={"NEXT_PUBLIC_API_BASE_URL": API_ORIGIN},
                log_path=web_log,
            )
            try:
                _wait_for_http(WEB_ORIGIN, web_process[0], web_log)
                coordinator = threading.Thread(
                    target=coordinate_api_restart,
                    name="gia-p16d-final-api-restart",
                )
                coordinator.start()
                try:
                    _run_playwright(
                        {
                            "GIA_P16D_FINAL_API_LOG": str(api_log),
                            "GIA_P16D_FINAL_API_ORIGIN": API_ORIGIN,
                            "GIA_P16D_FINAL_API_RESTART_REQUEST": str(restart_request),
                            "GIA_P16D_FINAL_API_RESTART_READY": str(restart_ready),
                            "GIA_P16D_FINAL_PROVIDER_CALLS": str(provider_calls),
                            "GIA_P16D_FINAL_CANCELLATION_ARM": str(cancellation_arm),
                            "GIA_P16D_FINAL_PROVIDER_BLOCKED": str(provider_blocked),
                            "GIA_P16D_FINAL_PROVIDER_CANCELLED": str(
                                provider_cancelled
                            ),
                        }
                    )
                finally:
                    coordinator_stop.set()
                    coordinator.join(timeout=SHUTDOWN_TIMEOUT_SECONDS)
                if coordinator.is_alive():
                    raise RuntimeError("Final API restart coordinator did not stop.")
                if coordinator_errors:
                    raise RuntimeError("Final API restart coordinator failed.") from (
                        coordinator_errors[0]
                    )
            finally:
                _stop_server_process(*web_process)
        except Exception:
            print("P1-6D final API log tail:", file=sys.stderr)
            print(_log_tail(api_log), file=sys.stderr)
            print("P1-6D final Web log tail:", file=sys.stderr)
            print(_log_tail(web_log), file=sys.stderr)
            raise
        finally:
            running = current_api[0]
            if running is not None:
                _stop_server_process(*running)
                current_api[0] = None
            _wait_for_port_release(WEB_PORT)
            _wait_for_port_release(API_PORT)

        required = (provider_calls, provider_blocked, provider_cancelled, restart_ready)
        if not all(path.exists() for path in required):
            raise RuntimeError("Final acceptance evidence is incomplete.")
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
        _run_final_flow(temporary_database)
    print(
        "P1-6D D2-D4 passed: Human plus exactly three AI, durable Memory/V3/V2, "
        "Browser reload, API restart, cancellation recovery, privacy/exact-once "
        "evidence, and final COMPLETED lifecycle with deterministic cleanup."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
