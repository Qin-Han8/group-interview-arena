import asyncio
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
from collections.abc import Generator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import BinaryIO
from urllib.error import HTTPError, URLError
from urllib.request import urlopen
from uuid import UUID

import psycopg
from conftest import (
    QUESTION_BROWSER_DATABASE_PREFIX,
    IntegrationDatabaseSettings,
    TemporaryDatabase,
    migrate_database,
    temporary_database_context,
)
from sqlalchemy import update

from group_interview_arena_api.db import (
    PersonaPrivateStance,
    QuestionVersion,
)
from group_interview_arena_api.db.runtime import (
    create_database_engine,
    create_database_session_factory,
    dispose_database_engine,
)
from group_interview_arena_api.modules.ai_runtime.domain import PromptVersionDefinition
from group_interview_arena_api.modules.ai_runtime.service import publish_prompt_version
from group_interview_arena_api.modules.question_personas.seed import (
    INTERNAL_VALIDATION_BUNDLE,
    seed_question_persona_foundation,
)

WEB_ORIGIN = "http://localhost:3000"
API_PORT = int(os.environ.get("GIA_E2E_API_PORT", "8000"))
API_ORIGIN = f"http://localhost:{API_PORT}"
WEB_PORT = 3000
STARTUP_TIMEOUT_SECONDS = 60.0
SHUTDOWN_TIMEOUT_SECONDS = 15.0
API_RESTART_DOWNTIME_SECONDS = 2.25

API_ROOT = Path(__file__).resolve().parents[2]
REPOSITORY_ROOT = API_ROOT.parents[1]
WEB_ROOT = REPOSITORY_ROOT / "apps" / "web"
PRIVATE_SENTINEL = "P1_2C_PRIVATE_SENTINEL_DO_NOT_DISCLOSE"
HUMAN_CONTRIBUTION = "\n".join(
    (
        "  Human evidence: preserve this exact contribution.",
        *(
            f"Public evidence line {index:02d}: resource allocation trade-offs "
            "stay concrete, attributable, and reviewable."
            for index in range(1, 25)
        ),
        "Second line stays exact.  ",
    )
)
AI_CONTRIBUTION = (
    "R3_PROMPT_CONTEXT_VERIFIED: deterministic network-free AI contribution."
)
R3_PHASE_INSTRUCTION = "R3_QUESTION_PHASE_INSTRUCTION"
PROMPT_VERSION_ID = UUID("55000000-0000-4000-8000-000000000001")
PROMPT_TEMPLATE = """Session: $session_id
Participant: $participant_id
Grant: $floor_grant_id
Phase: $phase
Question: $question_context
Persona: $persona_context
Private stance: $private_stance
Phase instruction: $phase_instruction
"""


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
    process, log_file = _start_server_process(
        command,
        cwd=cwd,
        environment=environment,
        log_path=log_path,
    )
    try:
        yield process
    finally:
        _stop_server_process(process, log_file)


def _start_server_process(
    command: list[str],
    *,
    cwd: Path,
    environment: dict[str, str],
    log_path: Path,
) -> tuple[subprocess.Popen[bytes], BinaryIO]:
    creation_flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    process_environment = os.environ.copy()
    process_environment.update(environment)

    log_file = log_path.open("ab")
    try:
        process = subprocess.Popen(
            command,
            cwd=cwd,
            env=process_environment,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            creationflags=creation_flags,
        )
    except Exception:
        log_file.close()
        raise
    return process, log_file


def _stop_server_process(
    process: subprocess.Popen[bytes],
    log_file: BinaryIO,
) -> None:
    try:
        _terminate_process_tree(process)
    finally:
        log_file.close()


def _wait_for_port_release(port: int) -> None:
    deadline = time.monotonic() + SHUTDOWN_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        if _port_is_available(port):
            return
        time.sleep(0.25)
    raise RuntimeError(f"E2E server cleanup left port {port} in use.")


def _run_playwright(*, environment_overrides: dict[str, str]) -> None:
    pnpm = shutil.which("pnpm.cmd" if os.name == "nt" else "pnpm")
    if pnpm is None:
        raise RuntimeError("pnpm is required to run the browser E2E suite.")

    environment = os.environ.copy()
    environment["CI"] = "true"
    environment.update(environment_overrides)
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


def _run_browser_flow(temporary_database: TemporaryDatabase) -> UUID:
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
        restart_request = temporary_path / "restart-api.request"
        restart_ready = temporary_path / "restart-api.ready"
        provider_blocked = temporary_path / "provider-blocked.json"
        provider_cancelled = temporary_path / "provider-cancelled.json"
        provider_calls = temporary_path / "provider-calls.jsonl"
        fake_app_module = temporary_path / "gia_e2e_fake_provider_app.py"
        fake_app_module.write_text(
            "import asyncio\n"
            "import json\n"
            "import os\n"
            "from pathlib import Path\n"
            "\n"
            "import psycopg\n"
            "\n"
            "from group_interview_arena_api.modules.ai_runtime import composition\n"
            "from group_interview_arena_api.modules.ai_runtime.generation "
            "import RawGenerationSuccess\n"
            "\n"
            "\n"
            "_provider_call_count = 0\n"
            "_blocked_provider = asyncio.Event()\n"
            "\n"
            "\n"
            "async def _network_free_provider(generation_input):\n"
            "    global _provider_call_count\n"
            "    _provider_call_count += 1\n"
            "    floor_grant_id = str(generation_input.floor_grant_id)\n"
            "    with Path(os.environ['GIA_E2E_PROVIDER_CALLS']).open(\n"
            "        'a', encoding='utf-8'\n"
            "    ) as call_log:\n"
            "        call_log.write(json.dumps({\n"
            "            'call': _provider_call_count,\n"
            "            'floor_grant_id': floor_grant_id,\n"
            "        }) + '\\n')\n"
            "    rendered_prompt = generation_input.rendered_prompt\n"
            "    checks = {\n"
            "        'v3_id': str(generation_input.prompt_version_id) == "
            "'56000000-0000-4000-8000-000000000003',\n"
            "        'v3_number': generation_input.prompt_version_number == 3,\n"
            "        'prompt_key': generation_input.prompt_key == "
            "'AI_CANDIDATE_TURN',\n"
            "        'phase': generation_input.phase == "
            "'OPENING_STATEMENTS',\n"
            "        'human_context': os.environ['GIA_E2E_HUMAN_CONTENT'] "
            "in rendered_prompt,\n"
            "        'human_label': '你：' in rendered_prompt,\n"
            "        'persona_section': "
            "'当前候选人的自然语言行为约束：' in rendered_prompt,\n"
            "        'persona_duration': '发言时长：通常发言约 ' "
            "in rendered_prompt,\n"
            "        'phase_guidance': "
            "'OPENING_STATEMENTS：清楚表达初始立场' in rendered_prompt,\n"
            "        'question_phase_instruction': "
            "os.environ['GIA_E2E_PHASE_INSTRUCTION'] in rendered_prompt,\n"
            "        'structured_memory_section': "
            "'结构化公开讨论记忆（可能为空；它是派生上下文，不是原始证据）：' "
            "in rendered_prompt,\n"
            "        'raw_tail_section': "
            "'记忆游标之后的完整公开发言尾部（可能为空）：' "
            "in rendered_prompt,\n"
            "        'remaining_time_section': "
            "'当前阶段剩余秒数（未知时为 UNKNOWN）：' in rendered_prompt,\n"
            "        'candidate_boundary': '不是报告撰写者' "
            "in rendered_prompt,\n"
            "        'turn_style': '不要使用 Markdown 标题' "
            "in rendered_prompt,\n"
            "    }\n"
            "    if _provider_call_count > 1:\n"
            "        human_context = os.environ['GIA_E2E_HUMAN_CONTENT']\n"
            "        prior_ai_context = os.environ['GIA_E2E_AI_CONTENT']\n"
            "        checks.update({\n"
            "            'prior_ai_context': prior_ai_context "
            "in rendered_prompt,\n"
            "            'prior_ai_label': 'AI 候选人 ' in rendered_prompt,\n"
            "            'public_context_order': rendered_prompt.index("
            "human_context) < rendered_prompt.index(prior_ai_context) "
            "if prior_ai_context in rendered_prompt else False,\n"
            "        })\n"
            "    failed = [name for name, passed in checks.items() if not passed]\n"
            "    if failed:\n"
            "        return RawGenerationSuccess(\n"
            "            content='R3_PROMPT_CONTEXT_FAILED:' + ','.join(failed)\n"
            "        )\n"
            "    if _provider_call_count == 3:\n"
            "        database_url = os.environ['GIA_API_DATABASE_URL'].replace(\n"
            "            'postgresql+psycopg://', 'postgresql://', 1\n"
            "        )\n"
            "        with psycopg.connect(database_url) as connection:\n"
            "            durable_rows = connection.execute(\n"
            '                "SELECT request.status, request.failure_code, "\n'
            '                "count(utterance.id) FROM llm_generation_requests "\n'
            '                "AS request LEFT JOIN ai_utterances AS utterance "\n'
            '                "ON utterance.generation_request_id = request.id "\n'
            '                "WHERE request.floor_grant_id = %s "\n'
            '                "GROUP BY request.id",\n'
            "                (generation_input.floor_grant_id,),\n"
            "            ).fetchall()\n"
            "        if durable_rows != [('RUNNING', None, 0)]:\n"
            "            raise RuntimeError(\n"
            "                f'Blocked provider durable state mismatch: {durable_rows!r}'\n"
            "            )\n"
            "        Path(os.environ['GIA_E2E_PROVIDER_BLOCKED']).write_text(\n"
            "            json.dumps({\n"
            "                'floor_grant_id': floor_grant_id,\n"
            "                'request_status': 'RUNNING',\n"
            "            }),\n"
            "            encoding='utf-8',\n"
            "        )\n"
            "        try:\n"
            "            await _blocked_provider.wait()\n"
            "        except asyncio.CancelledError:\n"
            "            Path(os.environ['GIA_E2E_PROVIDER_CANCELLED']).write_text(\n"
            "                json.dumps({'floor_grant_id': floor_grant_id}),\n"
            "                encoding='utf-8',\n"
            "            )\n"
            "            raise\n"
            "    return RawGenerationSuccess(\n"
            "        content=os.environ['GIA_E2E_AI_CONTENT']\n"
            "    )\n"
            "\n"
            "\n"
            "def _network_free_provider_factory(_settings):\n"
            "    return _network_free_provider\n"
            "\n"
            "\n"
            "composition.ZhipuGenerationProvider = "
            "_network_free_provider_factory\n"
            "\n"
            "from group_interview_arena_api.app import app\n",
            encoding="utf-8",
        )

        api_command = [
            sys.executable,
            "-m",
            "uvicorn",
            "gia_e2e_fake_provider_app:app",
            "--host",
            "localhost",
            "--port",
            str(API_PORT),
            "--loop",
            "group_interview_arena_api.core.event_loop:create_runtime_event_loop",
        ]
        api_environment = {
            "GIA_API_CORS_ORIGINS": f'["{WEB_ORIGIN}"]',
            "GIA_API_DATABASE_URL": database_url.get_secret_value(),
            "GIA_API_ENVIRONMENT": "test",
            "GIA_API_SESSION_COOKIE_SECURE": "false",
            "GIA_API_ZHIPU_API_KEY": "network-free-e2e-placeholder",
            "GIA_API_ZHIPU_MODEL": "network-free-e2e-model",
            "GIA_API_SESSION_PHASE_DURATIONS": (
                '{"preparation_seconds":2,'
                '"opening_statements_seconds":20,'
                '"exploration_seconds":20,'
                '"conflict_and_evaluation_seconds":20,'
                '"convergence_seconds":20,'
                '"final_summary_seconds":20}'
            ),
            "GIA_E2E_AI_CONTENT": AI_CONTRIBUTION,
            "GIA_E2E_HUMAN_CONTENT": HUMAN_CONTRIBUTION,
            "GIA_E2E_PHASE_INSTRUCTION": R3_PHASE_INSTRUCTION,
            "GIA_E2E_PROVIDER_BLOCKED": str(provider_blocked),
            "GIA_E2E_PROVIDER_CANCELLED": str(provider_cancelled),
            "GIA_E2E_PROVIDER_CALLS": str(provider_calls),
            "PYTHONPATH": os.pathsep.join(
                filter(
                    None,
                    (str(temporary_path), os.environ.get("PYTHONPATH")),
                )
            ),
            "PYTHONUNBUFFERED": "1",
        }
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
                        time.sleep(0.05)
                        continue

                    running = current_api[0]
                    if running is None:
                        raise RuntimeError(
                            "API restart requested without a running API."
                        )
                    _stop_server_process(*running)
                    current_api[0] = None
                    _wait_for_port_release(API_PORT)
                    time.sleep(API_RESTART_DOWNTIME_SECONDS)
                    if coordinator_stop.is_set():
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

            with _server_process(
                [node, str(next_cli), "dev"],
                cwd=WEB_ROOT,
                environment={"NEXT_PUBLIC_API_BASE_URL": API_ORIGIN},
                log_path=web_log,
            ) as web_process:
                _wait_for_http(WEB_ORIGIN, web_process, web_log)
                coordinator = threading.Thread(
                    target=coordinate_api_restart,
                    name="gia-e2e-api-restart",
                )
                coordinator.start()
                try:
                    _run_playwright(
                        environment_overrides={
                            "GIA_E2E_API_ORIGIN": API_ORIGIN,
                            "GIA_E2E_API_RESTART_REQUEST": str(restart_request),
                            "GIA_E2E_API_RESTART_READY": str(restart_ready),
                            "GIA_E2E_AI_CONTENT": AI_CONTRIBUTION,
                            "GIA_E2E_PROVIDER_BLOCKED": str(provider_blocked),
                            "GIA_E2E_PROVIDER_CANCELLED": str(provider_cancelled),
                        }
                    )
                finally:
                    coordinator_stop.set()
                    coordinator.join(timeout=SHUTDOWN_TIMEOUT_SECONDS)
                if coordinator.is_alive():
                    raise RuntimeError("API restart coordinator did not stop.")
                if coordinator_errors:
                    raise RuntimeError("API restart coordinator failed.") from (
                        coordinator_errors[0]
                    )
                blocked_state = json.loads(provider_blocked.read_text(encoding="utf-8"))
                cancelled_state = json.loads(
                    provider_cancelled.read_text(encoding="utf-8")
                )
                provider_call_rows = [
                    json.loads(line)
                    for line in provider_calls.read_text(encoding="utf-8").splitlines()
                ]
                cancelled_grant_id = UUID(cancelled_state["floor_grant_id"])
                if blocked_state["floor_grant_id"] != str(cancelled_grant_id):
                    raise RuntimeError(
                        "Browser E2E blocked/cancelled provider grant did not match."
                    )
                if (
                    sum(
                        row["floor_grant_id"] == str(cancelled_grant_id)
                        for row in provider_call_rows
                    )
                    != 1
                ):
                    raise RuntimeError(
                        "Browser E2E retried the cancelled provider floor grant."
                    )
        except Exception:
            print("API server log tail:", file=sys.stderr)
            print(_log_tail(api_log), file=sys.stderr)
            print("Web server log tail:", file=sys.stderr)
            print(_log_tail(web_log), file=sys.stderr)
            raise
        finally:
            running = current_api[0]
            if running is not None:
                _stop_server_process(*running)
                current_api[0] = None
            _wait_for_port_release(WEB_PORT)
            _wait_for_port_release(API_PORT)
        return cancelled_grant_id


def _verify_session_persistence(
    temporary_database: TemporaryDatabase,
    cancelled_grant_id: UUID,
) -> None:
    database_url = temporary_database.database_url
    with psycopg.connect(
        host=database_url.host,
        port=database_url.port,
        dbname=database_url.database,
        user=database_url.username,
        password=database_url.password,
    ) as connection:
        session_rows = connection.execute(
            "SELECT id, status, last_sequence, question_version_id, "
            "phase_started_at, phase_deadline_at, current_floor_grant_id "
            "FROM simulation_sessions"
        ).fetchall()
        if len(session_rows) != 1:
            raise RuntimeError("Browser E2E did not persist exactly one session.")

        (
            session_id,
            status,
            last_sequence,
            question_version_id,
            phase_started_at,
            phase_deadline_at,
            current_floor_grant_id,
        ) = session_rows[0]
        event_sequences = connection.execute(
            "SELECT sequence FROM discussion_events "
            "WHERE session_id = %s ORDER BY sequence",
            (session_id,),
        ).fetchall()
        human_event_rows = connection.execute(
            "SELECT event.causation_action_id, event.sequence, "
            "event.payload->>'floor_grant_id', "
            "event.payload->>'participant_id', event.payload->>'phase', "
            "event.payload->>'content', action.command_type "
            "FROM discussion_events AS event "
            "JOIN session_actions AS action "
            "ON action.session_id = event.session_id "
            "AND action.action_id = event.causation_action_id "
            "WHERE event.session_id = %s "
            "AND event.event_type = 'participant.utterance.created' "
            "AND event.payload->>'actor_kind' = 'HUMAN' "
            "AND event.payload->>'content' = %s",
            (session_id, HUMAN_CONTRIBUTION),
        ).fetchall()
        human_submit_action_rows = connection.execute(
            "SELECT action_id FROM session_actions "
            "WHERE session_id = %s "
            "AND command_type = 'participant.utterance.submit'",
            (session_id,),
        ).fetchall()
        provider_request_count = connection.execute(
            "SELECT count(*) FROM llm_generation_requests WHERE session_id = %s",
            (session_id,),
        ).fetchone()
        ai_event_rows = connection.execute(
            "SELECT event.sequence, event.payload->>'utterance_id', "
            "event.payload->>'participant_id', event.payload->>'floor_grant_id', "
            "event.payload->>'phase', event.payload->>'content', "
            "utterance.content, request.status "
            "FROM discussion_events AS event "
            "JOIN ai_utterances AS utterance "
            "ON utterance.session_id = event.session_id "
            "AND utterance.id::text = event.payload->>'utterance_id' "
            "JOIN llm_generation_requests AS request "
            "ON request.session_id = utterance.session_id "
            "AND request.id = utterance.generation_request_id "
            "WHERE event.session_id = %s "
            "AND event.event_type = 'participant.utterance.created' "
            "AND event.payload->>'actor_kind' = 'AI' "
            "AND event.payload->>'content' = %s "
            "ORDER BY event.sequence",
            (session_id, AI_CONTRIBUTION),
        ).fetchall()
        cancelled_request_rows = connection.execute(
            "SELECT status, failure_code FROM llm_generation_requests "
            "WHERE session_id = %s AND floor_grant_id = %s",
            (session_id, cancelled_grant_id),
        ).fetchall()
        cancelled_utterance_count = connection.execute(
            "SELECT count(*) FROM ai_utterances "
            "WHERE session_id = %s AND floor_grant_id = %s",
            (session_id, cancelled_grant_id),
        ).fetchone()
        cancelled_release_rows = connection.execute(
            "SELECT reason_code FROM floor_releases "
            "WHERE session_id = %s AND grant_id = %s",
            (session_id, cancelled_grant_id),
        ).fetchall()
        cancelled_public_release_rows = connection.execute(
            "SELECT payload->>'reason_code' FROM discussion_events "
            "WHERE session_id = %s AND event_type = 'floor.released' "
            "AND payload->>'grant_id' = %s",
            (session_id, str(cancelled_grant_id)),
        ).fetchall()

        if human_event_rows:
            (
                human_action_id,
                human_event_sequence,
                human_grant_id_text,
                human_participant_id_text,
                human_phase,
                human_content,
                human_command_type,
            ) = human_event_rows[0]
            human_grant_id = UUID(human_grant_id_text)
            human_participant_id = UUID(human_participant_id_text)
            grant_rows = connection.execute(
                "SELECT participant_id, phase FROM floor_grants "
                "WHERE session_id = %s AND id = %s",
                (session_id, human_grant_id),
            ).fetchall()
            participant_rows = connection.execute(
                "SELECT actor_kind FROM session_participants "
                "WHERE session_id = %s AND id = %s",
                (session_id, human_participant_id),
            ).fetchall()
            release_rows = connection.execute(
                "SELECT reason_code FROM floor_releases "
                "WHERE session_id = %s AND grant_id = %s "
                "AND causation_action_id = %s",
                (session_id, human_grant_id, human_action_id),
            ).fetchall()
            public_release_rows = connection.execute(
                "SELECT sequence, payload->>'reason_code', payload->>'grant_id' "
                "FROM discussion_events WHERE session_id = %s "
                "AND event_type = 'floor.released' "
                "AND causation_action_id = %s "
                "AND payload->>'grant_id' = %s",
                (session_id, human_action_id, str(human_grant_id)),
            ).fetchall()
        else:
            human_action_id = None
            human_event_sequence = None
            human_grant_id_text = None
            human_participant_id_text = None
            human_phase = None
            human_content = None
            human_command_type = None
            grant_rows = []
            participant_rows = []
            release_rows = []
            public_release_rows = []

    if (
        status != "COMPLETED"
        or question_version_id != INTERNAL_VALIDATION_BUNDLE.version_id
        or phase_started_at is not None
        or phase_deadline_at is not None
        or current_floor_grant_id is not None
    ):
        raise RuntimeError("Browser E2E terminal session state was not persisted.")
    if event_sequences != [(sequence,) for sequence in range(1, last_sequence + 1)]:
        raise RuntimeError("Browser E2E formal event sequences were not contiguous.")
    if len(human_event_rows) != 1:
        raise RuntimeError(
            "Browser E2E Human utterance was not persisted exactly once."
        )
    if (
        human_action_id is None
        or human_event_sequence is None
        or human_command_type != "participant.utterance.submit"
        or human_phase != "OPENING_STATEMENTS"
        or human_content != HUMAN_CONTRIBUTION
    ):
        raise RuntimeError("Browser E2E Human submit action/event did not match.")
    if human_submit_action_rows != [(human_action_id,)]:
        raise RuntimeError(
            "Browser E2E did not persist exactly one matching Human submit action."
        )
    if grant_rows != [(UUID(human_participant_id_text), human_phase)]:
        raise RuntimeError("Browser E2E Human utterance floor binding did not match.")
    if participant_rows != [("HUMAN",)]:
        raise RuntimeError("Browser E2E Human participant binding did not match.")
    if release_rows != [("SPEAKER_FINISHED",)]:
        raise RuntimeError("Browser E2E Human floor release did not match.")
    if public_release_rows != [
        (human_event_sequence + 1, "SPEAKER_FINISHED", human_grant_id_text)
    ]:
        raise RuntimeError("Browser E2E Human public release order did not match.")
    if provider_request_count is None or provider_request_count[0] < 1:
        raise RuntimeError("Browser E2E did not persist an AI generation request.")
    if not ai_event_rows:
        raise RuntimeError(
            "Browser E2E did not persist the fake-provider AI public utterance."
        )
    for (
        _ai_sequence,
        ai_utterance_id,
        ai_participant_id,
        ai_floor_grant_id,
        ai_phase,
        ai_event_content,
        ai_utterance_content,
        ai_request_status,
    ) in ai_event_rows:
        if (
            ai_utterance_id is None
            or ai_participant_id is None
            or ai_floor_grant_id is None
            or ai_phase is None
            or ai_event_content != AI_CONTRIBUTION
            or ai_utterance_content != AI_CONTRIBUTION
            or ai_request_status != "COMPLETED"
        ):
            raise RuntimeError(
                "Browser E2E fake-provider AI persistence evidence did not match."
            )
    if cancelled_request_rows != [("FAILED", "INTERNAL_ERROR")]:
        raise RuntimeError(
            "Browser E2E cancelled generation request was not FAILED/INTERNAL_ERROR."
        )
    if cancelled_utterance_count != (0,):
        raise RuntimeError(
            "Browser E2E cancelled generation unexpectedly persisted an utterance."
        )
    if cancelled_release_rows != [("INTERRUPTED",)]:
        raise RuntimeError(
            "Browser E2E cancelled AI floor was not released once as INTERRUPTED."
        )
    if cancelled_public_release_rows != [("INTERRUPTED",)]:
        raise RuntimeError(
            "Browser E2E cancelled AI floor public release was not exactly once."
        )


async def _seed_browser_question_async(
    temporary_database: TemporaryDatabase,
) -> None:
    engine = create_database_engine(temporary_database.database_settings())
    session_factory = create_database_session_factory(engine)
    try:
        await seed_question_persona_foundation(session_factory)
        async with session_factory() as session:
            await publish_prompt_version(
                session,
                PromptVersionDefinition(
                    id=PROMPT_VERSION_ID,
                    prompt_key="AI_CANDIDATE_TURN",
                    version_number=1,
                    purpose_code="CANDIDATE_UTTERANCE",
                    template_text=PROMPT_TEMPLATE,
                    created_at=datetime(2026, 8, 26, tzinfo=UTC),
                    published_at=datetime(2026, 8, 26, tzinfo=UTC),
                ),
            )
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
                        phase_prompts={
                            "PREPARATION": PRIVATE_SENTINEL,
                            "OPENING_STATEMENTS": R3_PHASE_INSTRUCTION,
                        },
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
        cancelled_grant_id = _run_browser_flow(temporary_database)
        _verify_session_persistence(temporary_database, cancelled_grant_id)

    print(
        "P1-5F-4 browser E2E passed with exact durable Human submit/restore, "
        "real scheduler/runtime composition through the network-free fake provider, "
        "durable public AI transcript recovery, contiguous event history, matching "
        "speaker-finished release, reload-driven cancelled-provider FAILED_REPLAY and "
        "exact INTERRUPTED release, immutable question binding, reload/API-restart "
        "recovery and private isolation; temporary database and servers were cleaned."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
