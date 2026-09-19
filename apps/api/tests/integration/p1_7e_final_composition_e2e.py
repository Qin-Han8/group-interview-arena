import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
from pathlib import Path
from typing import BinaryIO

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
from p1_6d_final_acceptance_e2e import (
    _assert_private_absent,  # pyright: ignore[reportPrivateUsage]
    _database_connection,  # pyright: ignore[reportPrivateUsage]
    _provider_module_source,  # pyright: ignore[reportPrivateUsage]
    _read_json_lines,  # pyright: ignore[reportPrivateUsage]
    _verify_durable_result,  # pyright: ignore[reportPrivateUsage]
)
from p1_6d_happy_path_e2e import (
    _seed_question,  # pyright: ignore[reportPrivateUsage]
)


def _verify_report_result(temporary_database: TemporaryDatabase) -> None:
    with _database_connection(temporary_database) as connection:
        reports = connection.execute(
            "SELECT report.id, report.session_id, report.status, "
            "report.report_schema_version, report.derivation_version, "
            "report.source_through_sequence, report.overall_summary, "
            "report.priority_improvement, report.completed_at, "
            "simulation.last_sequence, simulation.status, simulation.owner_user_id "
            "FROM evaluation_reports AS report "
            "JOIN simulation_sessions AS simulation "
            "ON simulation.id = report.session_id"
        ).fetchall()
        if len(reports) != 1:
            raise RuntimeError(f"Expected one durable report, got {reports!r}.")
        report = reports[0]
        if (
            report[2] != "COMPLETED"
            or report[3] != 1
            or report[4] != "basic-report/v1"
            or report[5] != report[9]
            or report[8] is None
            or report[10] != "COMPLETED"
        ):
            raise RuntimeError(f"Final report identity mismatch: {report!r}.")

        users = connection.execute(
            "SELECT id, username FROM users ORDER BY username"
        ).fetchall()
        if len(users) != 2:
            raise RuntimeError(f"Expected owner and isolation user, got {users!r}.")
        owner = next((row for row in users if row[0] == report[11]), None)
        if owner is None or not owner[1].lower().startswith("p16d_final_"):
            raise RuntimeError(f"Report ownership mismatch: {users!r}.")
        if not any(row[1].lower().startswith("p17e_other_") for row in users):
            raise RuntimeError(f"Isolation user was not durable: {users!r}.")

        evidence = connection.execute(
            "SELECT item.kind, item.source_participant_id, "
            "item.source_utterance_id, item.source_event_sequence, item.phase, "
            "item.quote, item.interpretation, item.confidence, "
            "participant.actor_kind, event.payload "
            "FROM evidence_items AS item "
            "JOIN session_participants AS participant "
            "ON participant.session_id = item.session_id "
            "AND participant.id = item.source_participant_id "
            "JOIN discussion_events AS event "
            "ON event.session_id = item.session_id "
            "AND event.sequence = item.source_event_sequence "
            "WHERE item.report_id = %s ORDER BY item.source_event_sequence",
            (report[0],),
        ).fetchall()
        if len(evidence) != 1:
            raise RuntimeError(
                f"Deterministic P1 report must contain one Human evidence row: {evidence!r}."
            )
        item = evidence[0]
        payload = item[9]
        if (
            item[0] != "STRENGTH"
            or item[8] != "HUMAN"
            or str(item[1]) != str(payload.get("participant_id"))
            or str(item[2]) != str(payload.get("utterance_id"))
            or item[3] > report[5]
            or item[4] != payload.get("phase")
            or item[5] != payload.get("content")
        ):
            raise RuntimeError(f"Evidence did not resolve to Human source: {item!r}.")

        duplicates = connection.execute(
            "SELECT session_id, report_schema_version, derivation_version, "
            "source_through_sequence, count(*) FROM evaluation_reports "
            "GROUP BY session_id, report_schema_version, derivation_version, "
            "source_through_sequence HAVING count(*) > 1"
        ).fetchall()
        if duplicates:
            raise RuntimeError(f"Duplicate report generation identity: {duplicates!r}.")

    _assert_private_absent(reports, "durable report rows")
    _assert_private_absent(evidence, "durable report evidence")


def _run_playwright(environment: dict[str, str]) -> None:
    pnpm = shutil.which("pnpm.cmd" if os.name == "nt" else "pnpm")
    if pnpm is None:
        raise RuntimeError("pnpm is required for P1-7E final composition acceptance.")
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
            "P1-7E final composition Playwright failed with exit code "
            f"{completed.returncode}."
        )


def _run_final_composition(temporary_database: TemporaryDatabase) -> None:
    _require_available_port(WEB_PORT)
    _require_available_port(API_PORT)
    node = shutil.which("node.exe" if os.name == "nt" else "node")
    if node is None:
        raise RuntimeError("Node.js is required for P1-7E final composition.")
    next_cli = WEB_ROOT / "node_modules" / "next" / "dist" / "bin" / "next"
    if not next_cli.is_file():
        raise RuntimeError("Next.js is not installed; run the frozen install gate.")

    database_url = temporary_database.database_settings().database_url
    with tempfile.TemporaryDirectory(prefix="gia_p17e_final_") as directory:
        temporary_path = Path(directory)
        api_log = temporary_path / "api.log"
        web_log = temporary_path / "web.log"
        restart_request = temporary_path / "restart-api.request"
        restart_ready = temporary_path / "restart-api.ready"
        report_restart_request = temporary_path / "restart-report-api.request"
        report_restart_ready = temporary_path / "restart-report-api.ready"
        provider_calls = temporary_path / "provider-calls.jsonl"
        cancellation_arm = temporary_path / "cancellation.arm"
        provider_blocked = temporary_path / "provider-blocked.json"
        provider_cancelled = temporary_path / "provider-cancelled.json"
        fake_app = temporary_path / "gia_p17e_final_provider_app.py"
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
            "GIA_P16D_FINAL_PROVIDER_CALLS": str(provider_calls),
            "GIA_P16D_FINAL_CANCELLATION_ARM": str(cancellation_arm),
            "GIA_P16D_FINAL_CANCELLATION_CLAIMED": str(
                temporary_path / "cancellation.claimed"
            ),
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
            "gia_p17e_final_provider_app:app",
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

        def coordinate_api_restarts() -> None:
            try:
                for request, ready in (
                    (restart_request, restart_ready),
                    (report_restart_request, report_restart_ready),
                ):
                    while not coordinator_stop.is_set() and not request.exists():
                        coordinator_stop.wait(0.05)
                    if coordinator_stop.is_set():
                        return
                    running = current_api[0]
                    if running is None:
                        raise RuntimeError("API restart lacked a running process.")
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
                    ready.write_text("ready", encoding="utf-8")
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
                    target=coordinate_api_restarts,
                    name="gia-p17e-api-restarts",
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
                            "GIA_P17E_FINAL_COMPOSITION": "1",
                            "GIA_P17E_REPORT_API_RESTART_REQUEST": str(
                                report_restart_request
                            ),
                            "GIA_P17E_REPORT_API_RESTART_READY": str(
                                report_restart_ready
                            ),
                        }
                    )
                finally:
                    coordinator_stop.set()
                    coordinator.join(timeout=SHUTDOWN_TIMEOUT_SECONDS)
                if coordinator.is_alive():
                    raise RuntimeError("P1-7E API restart coordinator did not stop.")
                if coordinator_errors:
                    raise RuntimeError("P1-7E API restart coordinator failed.") from (
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
            provider_calls,
            provider_blocked,
            provider_cancelled,
            restart_ready,
            report_restart_ready,
        )
        if not all(path.exists() for path in required):
            raise RuntimeError("P1-7E final composition evidence is incomplete.")
        provider_evidence = _read_json_lines(provider_calls)
        _verify_durable_result(
            temporary_database,
            blocked=json.loads(provider_blocked.read_text(encoding="utf-8")),
            cancelled=json.loads(provider_cancelled.read_text(encoding="utf-8")),
            provider_calls=provider_evidence,
        )
        _verify_report_result(temporary_database)
        _assert_private_absent(api_log.read_text(encoding="utf-8"), "P1-7E API logs")
        _assert_private_absent(web_log.read_text(encoding="utf-8"), "P1-7E Web logs")


def main() -> int:
    database_settings = IntegrationDatabaseSettings()  # pyright: ignore[reportCallIssue]
    with temporary_database_context(
        database_settings,
        P1_6D_BROWSER_DATABASE_PREFIX,
    ) as temporary_database:
        migrate_database(temporary_database)
        _seed_question(temporary_database)
        _run_final_composition(temporary_database)
    print(
        "P1-7E passed: one real Browser session reached COMPLETED, generated one "
        "evidence-grounded owner-only report, and recovered the identical report "
        "after Browser reload plus a second API restart without network provider use."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
