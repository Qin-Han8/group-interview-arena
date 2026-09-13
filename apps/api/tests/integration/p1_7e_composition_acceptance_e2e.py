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
    P1_7E_BROWSER_DATABASE_PREFIX,
    IntegrationDatabaseSettings,
    TemporaryDatabase,
    migrate_database,
    temporary_database_context,
)
from p1_6d_happy_path_e2e import (
    PRIVATE_SENTINELS,
    _seed_question,  # pyright: ignore[reportPrivateUsage]
)

EXPECTED_LIFECYCLE = [
    "PREPARATION",
    "OPENING_STATEMENTS",
    "EXPLORATION",
    "CONFLICT_AND_EVALUATION",
    "CONVERGENCE",
    "FINAL_SUMMARY",
    "COMPLETED",
]
FORBIDDEN_PUBLIC_TOKENS = (
    *PRIVATE_SENTINELS,
    "private_information",
    "red_lines",
    "concession_conditions",
    "behavior_parameters",
    "hidden_conflicts",
    "acceptable_outcome_patterns",
    "reference_dimensions",
    "chain-of-thought",
    "user_private_notes",
)
FORBIDDEN_SCORING_TOKENS = (
    "overall_score",
    "six_dimension",
    "percentile",
    "ranking",
    "outperformed",
    "hiring_probability",
    "job_fit",
    "personality_type",
    "雷达图",
    "录取概率",
)


def _provider_module_source() -> str:
    sentinels = repr(PRIVATE_SENTINELS)
    return textwrap.dedent(
        f"""
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
            with Path(os.environ["GIA_P17E_PROVIDER_CALLS"]).open(
                "a", encoding="utf-8"
            ) as stream:
                stream.write(json.dumps(row, sort_keys=True) + "\\n")

        class NetworkFreeP17EProvider:
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
                    "provider_impl": "P1_7E_NETWORK_FREE",
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
                        "canonical_text": "P1-7E public deterministic memory",
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
                metadata = row[1]
                _append({{
                    "provider_impl": "P1_7E_NETWORK_FREE",
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
                    "request_metadata_schema_version": metadata.get("schema_version"),
                    "request_metadata_memory_revision": metadata.get("memory_revision"),
                }})
                prefix = (
                    f"P17E_AI_PUBLIC:{{generation_input.participant_id}}:"
                    f"{{generation_input.phase}}:{{generation_input.floor_grant_id}}:"
                )
                return RawGenerationSuccess(
                    content=prefix
                    + "比较约束、风险与可执行性，并提出面向小组收敛的公开方案。"
                )

        _provider = NetworkFreeP17EProvider()

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


def _assert_absent(value: object, tokens: tuple[str, ...], label: str) -> None:
    serialized = json.dumps(value, sort_keys=True, default=str, ensure_ascii=False)
    for token in tokens:
        if token.lower() in serialized.lower():
            raise RuntimeError(f"Forbidden token {token!r} appeared in {label}.")


def _required_count(row: tuple[Any, ...] | None) -> int:
    if row is None or not isinstance(row[0], int):
        raise RuntimeError("Required PostgreSQL count query returned no integer.")
    return row[0]


def _pre_report_probe(
    temporary_database: TemporaryDatabase,
    request_path: Path,
    result_path: Path,
) -> bool:
    if not request_path.exists() or result_path.exists():
        return False
    request = json.loads(request_path.read_text(encoding="utf-8"))
    session_id = request["session_id"]
    with _database_connection(temporary_database) as connection:
        report_count = _required_count(
            connection.execute(
                "SELECT count(*) FROM evaluation_reports WHERE session_id = %s",
                (session_id,),
            ).fetchone()
        )
        evidence_count = _required_count(
            connection.execute(
                "SELECT count(*) FROM evidence_items WHERE session_id = %s",
                (session_id,),
            ).fetchone()
        )
    result_path.write_text(
        json.dumps(
            {"report_count": report_count, "evidence_count": evidence_count},
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    return True


def _verify_durable_result(
    temporary_database: TemporaryDatabase,
    *,
    browser_evidence: dict[str, Any],
    provider_calls: list[dict[str, Any]],
    api_log: str,
    web_log: str,
) -> dict[str, Any]:
    session_id = browser_evidence["session_id"]
    report_view = browser_evidence["report"]
    report_metadata = report_view["report"]
    report_content = report_view["content"]
    if report_content is None:
        raise RuntimeError("P1-7E Browser received no completed report content.")

    with _database_connection(temporary_database) as connection:
        session_rows = connection.execute(
            "SELECT id, status, last_sequence, current_floor_grant_id, "
            "phase_started_at, phase_deadline_at FROM simulation_sessions"
        ).fetchall()
        if len(session_rows) != 1:
            raise RuntimeError(f"Expected one composed session: {session_rows!r}.")
        session_row = session_rows[0]
        if str(session_row[0]) != session_id or session_row[1] != "COMPLETED":
            raise RuntimeError(f"Composed session did not complete: {session_row!r}.")
        if any(value is not None for value in session_row[3:]):
            raise RuntimeError(
                f"Terminal phase/floor state was not cleared: {session_row!r}."
            )
        last_sequence = int(session_row[2])
        if last_sequence != browser_evidence["completion_last_sequence"]:
            raise RuntimeError("Completion watermark changed before report generation.")

        participants = connection.execute(
            "SELECT id, actor_kind FROM session_participants "
            "WHERE session_id = %s ORDER BY seat_order, id",
            (session_id,),
        ).fetchall()
        human_ids = {str(row[0]) for row in participants if row[1] == "HUMAN"}
        ai_ids = {str(row[0]) for row in participants if row[1] == "AI"}
        if len(participants) != 4 or len(human_ids) != 1 or len(ai_ids) != 3:
            raise RuntimeError(f"Authoritative roster mismatch: {participants!r}.")

        events = connection.execute(
            "SELECT sequence, event_type, payload FROM discussion_events "
            "WHERE session_id = %s ORDER BY sequence",
            (session_id,),
        ).fetchall()
        if [row[0] for row in events] != list(range(1, last_sequence + 1)):
            raise RuntimeError("DiscussionEvent sequence is not contiguous.")
        lifecycle = [
            row[2].get("status") for row in events if row[1] == "session.state_changed"
        ]
        if lifecycle != EXPECTED_LIFECYCLE:
            raise RuntimeError(f"Lifecycle mismatch: {lifecycle!r}.")
        utterance_events = {
            int(row[0]): row[2]
            for row in events
            if row[1] == "participant.utterance.created"
        }
        spoken_ai_ids = {
            str(payload.get("participant_id"))
            for payload in utterance_events.values()
            if payload.get("actor_kind") == "AI"
        }
        if not ai_ids.issubset(spoken_ai_ids):
            raise RuntimeError("Not all three AI participants spoke durably.")
        if not any(
            payload.get("actor_kind") == "HUMAN"
            and isinstance(payload.get("content"), str)
            and payload["content"].strip()
            for payload in utterance_events.values()
        ):
            raise RuntimeError("No real non-empty Human utterance was persisted.")

        reports = connection.execute(
            "SELECT id, session_id, status, report_schema_version, "
            "derivation_version, source_through_sequence, completed_at, "
            "overall_summary, priority_improvement FROM evaluation_reports "
            "WHERE session_id = %s",
            (session_id,),
        ).fetchall()
        if len(reports) != 1:
            raise RuntimeError(f"Expected exactly one durable report: {reports!r}.")
        report = reports[0]
        if (
            str(report[0]) != report_metadata["report_id"]
            or str(report[1]) != session_id
            or report[2] != "COMPLETED"
            or report[3] != 1
            or report[4] != "basic-report/v1"
            or int(report[5]) != last_sequence
            or report[6] is None
            or report[7] != report_content["overview"]["summary"]
            or report[8] != report_content["priority_improvement"]
        ):
            raise RuntimeError(f"Durable report metadata/content mismatch: {report!r}.")

        evidence_rows = connection.execute(
            "SELECT evidence.kind, evidence.source_participant_id, "
            "evidence.source_utterance_id, evidence.source_event_sequence, "
            "evidence.phase, evidence.quote, evidence.interpretation, "
            "evidence.confidence, participant.actor_kind, event.event_type, "
            "event.payload "
            "FROM evidence_items AS evidence "
            "JOIN session_participants AS participant "
            "ON participant.session_id = evidence.session_id "
            "AND participant.id = evidence.source_participant_id "
            "JOIN discussion_events AS event "
            "ON event.session_id = evidence.session_id "
            "AND event.sequence = evidence.source_event_sequence "
            "WHERE evidence.session_id = %s AND evidence.report_id = %s "
            "ORDER BY evidence.source_event_sequence, evidence.id",
            (session_id, report[0]),
        ).fetchall()
        public_cards = report_content["strengths"] + report_content["improvements"]
        if not evidence_rows or len(evidence_rows) != len(public_cards):
            raise RuntimeError(
                "Evidence did not persist or public cardinality diverged."
            )
        for row, card in zip(evidence_rows, public_cards, strict=True):
            payload = row[10]
            if (
                row[8] != "HUMAN"
                or row[9] != "participant.utterance.created"
                or payload.get("actor_kind") != "HUMAN"
                or str(payload.get("utterance_id")) != str(row[2])
                or str(payload.get("participant_id")) != str(row[1])
                or payload.get("phase") != row[4]
                or int(row[3]) > int(report[5])
                or row[5] not in payload.get("content", "")
            ):
                raise RuntimeError(f"Evidence provenance mismatch: {row!r}.")
            expected_card = {
                "kind": row[0],
                "source_participant_id": str(row[1]),
                "source_utterance_id": str(row[2]),
                "source_event_sequence": int(row[3]),
                "phase": row[4],
                "quote": row[5],
                "interpretation": row[6],
                "confidence": str(row[7]),
            }
            comparable_card = {**card, "confidence": str(card["confidence"])}
            if comparable_card != expected_card:
                raise RuntimeError(
                    f"Displayed evidence differs from persistence: {card!r}."
                )

        report_count = _required_count(
            connection.execute(
                "SELECT count(*) FROM evaluation_reports WHERE session_id = %s",
                (session_id,),
            ).fetchone()
        )
        evidence_count = _required_count(
            connection.execute(
                "SELECT count(*) FROM evidence_items WHERE session_id = %s",
                (session_id,),
            ).fetchone()
        )

    if browser_evidence["pre_report_probe"] != {
        "report_count": 0,
        "evidence_count": 0,
    }:
        raise RuntimeError("Pre-generation GET mutated report persistence.")
    for key in ("repeated_get", "after_restart"):
        if browser_evidence[key] != {"status": 200, "body": report_view}:
            raise RuntimeError(f"{key} did not return identical durable state.")
    if browser_evidence["repeated_post"] != {
        "status": 200,
        "body": report_metadata,
    }:
        raise RuntimeError("Repeated POST was not idempotent.")
    if browser_evidence["owner_isolation_status"] != 404:
        raise RuntimeError("Second owner received existence-sensitive report access.")

    candidate_calls = [row for row in provider_calls if row["workload"] == "candidate"]
    semantic_calls = [row for row in provider_calls if row["workload"] == "semantic"]
    candidate_ai_ids = {row["participant_id"] for row in candidate_calls}
    if not semantic_calls or not ai_ids.issubset(candidate_ai_ids):
        raise RuntimeError("Network-free provider did not compose all AI workloads.")
    if any(row.get("provider_impl") != "P1_7E_NETWORK_FREE" for row in provider_calls):
        raise RuntimeError("A non-P1-7E provider appeared in provider evidence.")
    if {row["private_sentinel_index"] for row in candidate_calls} != {0, 1, 2}:
        raise RuntimeError("Candidate-private stance isolation was not exercised.")

    public_evidence = {
        "browser": browser_evidence,
        "provider_calls": provider_calls,
        "api_log": api_log,
        "web_log": web_log,
    }
    _assert_absent(public_evidence, FORBIDDEN_PUBLIC_TOKENS, "public evidence/logs")
    _assert_absent(browser_evidence, FORBIDDEN_SCORING_TOKENS, "report/browser state")
    if "p1-7e-network-free-placeholder" in api_log:
        raise RuntimeError("Provider API key placeholder leaked into application logs.")

    return {
        "session_id": session_id,
        "participant_count": len(participants),
        "human_count": len(human_ids),
        "ai_count": len(ai_ids),
        "lifecycle": lifecycle,
        "completion_last_sequence": last_sequence,
        "report_id": str(report[0]),
        "report_schema_version": report[3],
        "derivation_version": report[4],
        "source_through_sequence": report[5],
        "report_count": report_count,
        "evidence_count": evidence_count,
        "provider_candidate_participants": len(candidate_ai_ids),
        "semantic_provider_calls": len(semantic_calls),
        "owner_isolation_status": browser_evidence["owner_isolation_status"],
    }


def _run_playwright(environment: dict[str, str]) -> None:
    pnpm = shutil.which("pnpm.cmd" if os.name == "nt" else "pnpm")
    if pnpm is None:
        raise RuntimeError("pnpm is required for P1-7E composition acceptance.")
    process_environment = os.environ.copy()
    process_environment["CI"] = "true"
    process_environment.update(environment)
    completed = subprocess.run(
        [
            pnpm,
            "exec",
            "playwright",
            "test",
            "e2e/p1-7e-composition-acceptance.spec.ts",
        ],
        cwd=WEB_ROOT,
        env=process_environment,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"P1-7E Playwright failed with exit code {completed.returncode}."
        )


def _run_composed_flow(temporary_database: TemporaryDatabase) -> dict[str, Any]:
    _require_available_port(WEB_PORT)
    _require_available_port(API_PORT)
    node = shutil.which("node.exe" if os.name == "nt" else "node")
    if node is None:
        raise RuntimeError("Node.js is required for P1-7E composition acceptance.")
    next_cli = WEB_ROOT / "node_modules" / "next" / "dist" / "bin" / "next"
    if not next_cli.is_file():
        raise RuntimeError("Next.js is not installed; run the frozen install gate.")

    database_url = temporary_database.database_settings().database_url
    with tempfile.TemporaryDirectory(prefix="gia_p17e_composition_") as directory:
        temporary_path = Path(directory)
        api_log = temporary_path / "api.log"
        web_log = temporary_path / "web.log"
        restart_request = temporary_path / "restart-api.request"
        restart_ready = temporary_path / "restart-api.ready"
        probe_request = temporary_path / "pre-report-probe.request.json"
        probe_result = temporary_path / "pre-report-probe.result.json"
        provider_calls = temporary_path / "provider-calls.jsonl"
        browser_evidence = temporary_path / "browser-evidence.json"
        fake_app = temporary_path / "gia_p17e_provider_app.py"
        fake_app.write_text(_provider_module_source(), encoding="utf-8")

        api_environment = {
            "GIA_API_CORS_ORIGINS": f'["{WEB_ORIGIN}"]',
            "GIA_API_DATABASE_URL": database_url.get_secret_value(),
            "GIA_API_ENVIRONMENT": "test",
            "GIA_API_SESSION_COOKIE_SECURE": "false",
            "GIA_API_ZHIPU_API_KEY": "p1-7e-network-free-placeholder",
            "GIA_API_ZHIPU_MODEL": "p1-7e-network-free-model",
            "GIA_API_SESSION_PHASE_DURATIONS": (
                '{"preparation_seconds":1,'
                '"opening_statements_seconds":1,'
                '"exploration_seconds":30,'
                '"conflict_and_evaluation_seconds":1,'
                '"convergence_seconds":1,'
                '"final_summary_seconds":1}'
            ),
            "GIA_P17E_PROVIDER_CALLS": str(provider_calls),
            "PYTHONPATH": os.pathsep.join(
                filter(None, (str(temporary_path), os.environ.get("PYTHONPATH")))
            ),
            "PYTHONUNBUFFERED": "1",
        }
        api_command = [
            sys.executable,
            "-m",
            "uvicorn",
            "gia_p17e_provider_app:app",
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

        def coordinate_read_probe_and_restart() -> None:
            try:
                restart_complete = False
                while not coordinator_stop.is_set():
                    _pre_report_probe(
                        temporary_database,
                        probe_request,
                        probe_result,
                    )
                    if restart_request.exists() and not restart_complete:
                        running = current_api[0]
                        if running is None:
                            raise RuntimeError("P1-7E restart lacked a running API.")
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
                        restart_complete = True
                    coordinator_stop.wait(0.05)
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
                    target=coordinate_read_probe_and_restart,
                    name="gia-p17e-probe-restart",
                )
                coordinator.start()
                try:
                    _run_playwright(
                        {
                            "GIA_P17E_API_ORIGIN": API_ORIGIN,
                            "GIA_P17E_API_RESTART_REQUEST": str(restart_request),
                            "GIA_P17E_API_RESTART_READY": str(restart_ready),
                            "GIA_P17E_PRE_REPORT_PROBE_REQUEST": str(probe_request),
                            "GIA_P17E_PRE_REPORT_PROBE_RESULT": str(probe_result),
                            "GIA_P17E_BROWSER_EVIDENCE": str(browser_evidence),
                            "GIA_P17E_PROVIDER_CALLS": str(provider_calls),
                        }
                    )
                finally:
                    coordinator_stop.set()
                    coordinator.join(timeout=SHUTDOWN_TIMEOUT_SECONDS)
                if coordinator.is_alive():
                    raise RuntimeError("P1-7E probe/restart coordinator did not stop.")
                if coordinator_errors:
                    raise RuntimeError("P1-7E probe/restart coordinator failed.") from (
                        coordinator_errors[0]
                    )
            finally:
                _stop_server_process(*web_process)
        except Exception:
            print("P1-7E API log tail:", file=sys.stderr)
            print(_log_tail(api_log), file=sys.stderr)
            print("P1-7E Web log tail:", file=sys.stderr)
            print(_log_tail(web_log), file=sys.stderr)
            raise
        finally:
            running = current_api[0]
            if running is not None:
                _stop_server_process(*running)
                current_api[0] = None
            _wait_for_port_release(WEB_PORT)
            _wait_for_port_release(API_PORT)

        required = (
            browser_evidence,
            provider_calls,
            probe_result,
            restart_ready,
        )
        if not all(path.exists() for path in required):
            raise RuntimeError("P1-7E acceptance evidence is incomplete.")
        return _verify_durable_result(
            temporary_database,
            browser_evidence=json.loads(browser_evidence.read_text(encoding="utf-8")),
            provider_calls=_read_json_lines(provider_calls),
            api_log=api_log.read_text(encoding="utf-8"),
            web_log=web_log.read_text(encoding="utf-8"),
        )


def _temporary_database_count(settings: IntegrationDatabaseSettings) -> int:
    with psycopg.connect(
        host="127.0.0.1",
        port=5432,
        dbname="postgres",
        user=settings.username,
        password=settings.password.get_secret_value(),
        autocommit=True,
    ) as connection:
        return _required_count(
            connection.execute(
                "SELECT count(*) FROM pg_database WHERE datname LIKE %s",
                (f"{P1_7E_BROWSER_DATABASE_PREFIX}%",),
            ).fetchone()
        )


def main() -> int:
    database_settings = IntegrationDatabaseSettings()  # pyright: ignore[reportCallIssue]
    result: dict[str, Any]
    with temporary_database_context(
        database_settings,
        P1_7E_BROWSER_DATABASE_PREFIX,
    ) as temporary_database:
        migrate_database(temporary_database)
        _seed_question(temporary_database)
        result = _run_composed_flow(temporary_database)
    residual_databases = _temporary_database_count(database_settings)
    if residual_databases != 0:
        raise RuntimeError(f"P1-7E residual temporary databases: {residual_databases}.")
    _require_available_port(WEB_PORT)
    _require_available_port(API_PORT)
    result["residual_temporary_databases"] = residual_databases
    result["port_3000_listener"] = 0
    result["port_8000_listener"] = 0
    print("P1-7E composition acceptance PASS")
    print(json.dumps(result, indent=2, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
