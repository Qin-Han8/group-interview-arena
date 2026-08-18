import asyncio
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

import psycopg
from conftest import (
    QUESTION_BROWSER_DATABASE_PREFIX,
    IntegrationDatabaseSettings,
    TemporaryDatabase,
    migrate_database,
    temporary_database_context,
)
from sqlalchemy import update

from group_interview_arena_api.db import PersonaPrivateStance, QuestionVersion
from group_interview_arena_api.db.runtime import (
    create_database_engine,
    create_database_session_factory,
    dispose_database_engine,
)
from group_interview_arena_api.modules.question_personas.seed import (
    INTERNAL_VALIDATION_BUNDLE,
    seed_question_persona_foundation,
)

API_ORIGIN = "http://localhost:8000"
WEB_ORIGIN = "http://localhost:3000"
API_PORT = 8000
WEB_PORT = 3000
STARTUP_TIMEOUT_SECONDS = 60.0
SHUTDOWN_TIMEOUT_SECONDS = 15.0

API_ROOT = Path(__file__).resolve().parents[2]
REPOSITORY_ROOT = API_ROOT.parents[1]
WEB_ROOT = REPOSITORY_ROOT / "apps" / "web"
PRIVATE_SENTINEL = "P1_2C_PRIVATE_SENTINEL_DO_NOT_DISCLOSE"


def _port_is_available(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            listener.bind(("127.0.0.1", port))
        except OSError:
            return False
    return True


def _require_available_port(port: int) -> None:
    if not _port_is_available(port):
        raise RuntimeError(f"Required E2E port {port} is already in use.")


def _wait_for_http(
    url: str,
    process: subprocess.Popen[bytes],
    log_path: Path,
) -> None:
    deadline = time.monotonic() + STARTUP_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(
                f"Server exited before {url} became ready.\n{_log_tail(log_path)}"
            )
        try:
            with urlopen(url, timeout=2) as response:  # noqa: S310
                if response.status == 200:
                    return
        except HTTPError, URLError, TimeoutError:
            time.sleep(0.25)
    raise RuntimeError(f"Timed out waiting for {url}.\n{_log_tail(log_path)}")


def _log_tail(log_path: Path, line_count: int = 40) -> str:
    if not log_path.exists():
        return "No server log was created."
    lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
    return "\n".join(lines[-line_count:])


def _terminate_process_tree(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is not None:
        return

    if os.name == "nt":
        subprocess.run(
            ["taskkill.exe", "/PID", str(process.pid), "/T", "/F"],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    else:
        process.terminate()

    try:
        process.wait(timeout=SHUTDOWN_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=SHUTDOWN_TIMEOUT_SECONDS)


@contextmanager
def _server_process(
    command: list[str],
    *,
    cwd: Path,
    environment: dict[str, str],
    log_path: Path,
) -> Generator[subprocess.Popen[bytes]]:
    creation_flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    process_environment = os.environ.copy()
    process_environment.update(environment)

    with log_path.open("wb") as log_file:
        process = subprocess.Popen(
            command,
            cwd=cwd,
            env=process_environment,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            creationflags=creation_flags,
        )
        try:
            yield process
        finally:
            _terminate_process_tree(process)


def _wait_for_port_release(port: int) -> None:
    deadline = time.monotonic() + SHUTDOWN_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        if _port_is_available(port):
            return
        time.sleep(0.25)
    raise RuntimeError(f"E2E server cleanup left port {port} in use.")


def _run_playwright() -> None:
    pnpm = shutil.which("pnpm.cmd" if os.name == "nt" else "pnpm")
    if pnpm is None:
        raise RuntimeError("pnpm is required to run the browser E2E suite.")

    environment = os.environ.copy()
    environment["CI"] = "true"
    completed = subprocess.run(
        [
            pnpm,
            "--filter",
            "@group-interview-arena/web",
            "test:e2e:browser",
        ],
        cwd=REPOSITORY_ROOT,
        env=environment,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"Playwright browser suite failed with exit code {completed.returncode}."
        )


def _run_browser_flow(temporary_database: TemporaryDatabase) -> None:
    _require_available_port(WEB_PORT)
    _require_available_port(API_PORT)

    node = shutil.which("node.exe" if os.name == "nt" else "node")
    if node is None:
        raise RuntimeError("Node.js is required to run the Web E2E server.")
    next_cli = WEB_ROOT / "node_modules" / "next" / "dist" / "bin" / "next"
    if not next_cli.is_file():
        raise RuntimeError(
            "Next.js is not installed; run the frozen pnpm install gate."
        )

    database_url = temporary_database.database_settings().database_url
    with tempfile.TemporaryDirectory(prefix="gia_p12c_e2e_") as temp_directory:
        temporary_path = Path(temp_directory)
        api_log = temporary_path / "api.log"
        web_log = temporary_path / "web.log"

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
                environment={
                    "GIA_API_CORS_ORIGINS": f'["{WEB_ORIGIN}"]',
                    "GIA_API_DATABASE_URL": database_url.get_secret_value(),
                    "GIA_API_ENVIRONMENT": "test",
                    "GIA_API_SESSION_COOKIE_SECURE": "false",
                    "PYTHONUNBUFFERED": "1",
                },
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
                    _run_playwright()
        except Exception:
            print("API server log tail:", file=sys.stderr)
            print(_log_tail(api_log), file=sys.stderr)
            print("Web server log tail:", file=sys.stderr)
            print(_log_tail(web_log), file=sys.stderr)
            raise
        finally:
            _wait_for_port_release(WEB_PORT)
            _wait_for_port_release(API_PORT)


def _verify_session_persistence(temporary_database: TemporaryDatabase) -> None:
    database_url = temporary_database.database_url
    with psycopg.connect(
        host=database_url.host,
        port=database_url.port,
        dbname=database_url.database,
        user=database_url.username,
        password=database_url.password,
    ) as connection:
        session_rows = connection.execute(
            "SELECT status, last_sequence, question_version_id FROM simulation_sessions"
        ).fetchall()
        action_count = connection.execute(
            "SELECT count(*) FROM session_actions"
        ).fetchone()
        event_sequences = connection.execute(
            "SELECT sequence FROM discussion_events ORDER BY sequence"
        ).fetchall()

    if session_rows != [("ABORTED_USER", 2, INTERNAL_VALIDATION_BUNDLE.version_id)]:
        raise RuntimeError("Browser E2E session state was not persisted exactly.")
    if action_count is None or action_count[0] != 1:
        raise RuntimeError("Browser E2E action idempotency row count was not one.")
    if event_sequences != [(1,), (2,)]:
        raise RuntimeError("Browser E2E formal event sequences were not [1, 2].")


async def _seed_browser_question_async(
    temporary_database: TemporaryDatabase,
) -> None:
    engine = create_database_engine(temporary_database.database_settings())
    session_factory = create_database_session_factory(engine)
    try:
        await seed_question_persona_foundation(session_factory)
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
    finally:
        await dispose_database_engine(engine)


def _seed_browser_question(temporary_database: TemporaryDatabase) -> None:
    asyncio.run(
        _seed_browser_question_async(temporary_database),
        loop_factory=asyncio.SelectorEventLoop,
    )


def main() -> int:
    database_settings = IntegrationDatabaseSettings()  # pyright: ignore[reportCallIssue]
    with temporary_database_context(
        database_settings,
        QUESTION_BROWSER_DATABASE_PREFIX,
    ) as temporary_database:
        migrate_database(temporary_database)
        _seed_browser_question(temporary_database)
        _run_browser_flow(temporary_database)
        _verify_session_persistence(temporary_database)

    print(
        "P1-2C browser E2E passed with immutable question binding, one durable "
        "action, sequences [1, 2], and private sentinel isolation; "
        "temporary database and servers were cleaned."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
