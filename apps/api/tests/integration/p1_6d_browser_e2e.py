import asyncio
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import textwrap
import threading
import time
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from typing import Any, BinaryIO
from urllib.error import HTTPError, URLError
from urllib.request import urlopen
from uuid import UUID

import psycopg
from browser_e2e import (
    API_ORIGIN,
    API_PORT,
    API_RESTART_DOWNTIME_SECONDS,
    API_ROOT,
    REPOSITORY_ROOT,
    SHUTDOWN_TIMEOUT_SECONDS,
    WEB_ORIGIN,
    WEB_PORT,
    WEB_ROOT,
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
LIFECYCLE = (
    "PREPARATION",
    "OPENING_STATEMENTS",
    "EXPLORATION",
    "CONFLICT_AND_EVALUATION",
    "CONVERGENCE",
    "FINAL_SUMMARY",
    "COMPLETED",
)


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
        raise RuntimeError(f"Required P1-6D E2E port {port} is already in use.")


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


def _stop_server_process(process: subprocess.Popen[bytes], log_file: BinaryIO) -> None:
    try:
        _terminate_process_tree(process)
    finally:
        log_file.close()


@contextmanager
def _server_process(
    command: list[str],
    *,
    cwd: Path,
    environment: dict[str, str],
    log_path: Path,
) -> Generator[subprocess.Popen[bytes]]:
    process, log_file = _start_server_process(
        command, cwd=cwd, environment=environment, log_path=log_path
    )
    try:
        yield process
    finally:
        _stop_server_process(process, log_file)


def _wait_for_http(url: str, process: subprocess.Popen[bytes], log_path: Path) -> None:
    deadline = time.monotonic() + 60.0
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


def _wait_for_port_release(port: int) -> None:
    deadline = time.monotonic() + SHUTDOWN_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        if _port_is_available(port):
            return
        time.sleep(0.25)
    raise RuntimeError(f"P1-6D cleanup left port {port} in use.")


def _run_dedicated_playwright(environment_overrides: dict[str, str]) -> None:
    pnpm = shutil.which("pnpm.cmd" if os.name == "nt" else "pnpm")
    if pnpm is None:
        raise RuntimeError("pnpm is required to run the P1-6D browser scenario.")
    environment = os.environ.copy()
    environment["CI"] = "true"
    environment.update(environment_overrides)
    completed = subprocess.run(
        [pnpm, "--filter", "@group-interview-arena/web", "test:e2e:browser:p1-6d"],
        cwd=REPOSITORY_ROOT,
        env=environment,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"P1-6D Playwright scenario failed with exit code {completed.returncode}."
        )


def _provider_module_source() -> str:
    return textwrap.dedent(
        """
        import asyncio
        import json
        import os
        import time
        from pathlib import Path

        import psycopg

        from group_interview_arena_api.modules.ai_runtime import composition, continuous
        from group_interview_arena_api.modules.ai_runtime.generation import RawGenerationSuccess

        PRIVATE_SENTINELS = (
            "P16D_PRIVATE_ALPHA_DO_NOT_DISCLOSE",
            "P16D_PRIVATE_BRAVO_DO_NOT_DISCLOSE",
            "P16D_PRIVATE_CHARLIE_DO_NOT_DISCLOSE",
        )
        _blocked = asyncio.Event()
        _post_restart_gate = asyncio.Lock()

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

        class NetworkFreeP16DProvider:
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
                pre_restart_arm = Path(os.environ["GIA_P16D_PRE_RESTART_ARM"])
                restarted = Path(os.environ["GIA_P16D_RESTARTED_PROCESS"])
                if pre_restart_arm.exists() and not restarted.exists():
                    continuous.MAX_AUTOMATED_AI_TURNS_PER_DRIVE = 1
                prompt = generation_input.rendered_prompt
                sentinel_indexes = [
                    index for index, sentinel in enumerate(PRIVATE_SENTINELS)
                    if sentinel in prompt
                ]
                required_sections = (
                    "结构化公开讨论记忆（可能为空；它是派生上下文，不是原始证据）：",
                    "记忆游标之后的完整公开发言尾部（可能为空）：",
                    "当前阶段剩余秒数（未知时为 UNKNOWN）：",
                )
                if len(sentinel_indexes) != 1:
                    raise RuntimeError("Candidate prompt did not contain exactly one private stance.")
                if not all(section in prompt for section in required_sections):
                    raise RuntimeError("Candidate V3 context contract was incomplete.")
                if (
                    str(generation_input.prompt_version_id)
                    != "56000000-0000-4000-8000-000000000003"
                    or generation_input.prompt_version_number != 3
                    or generation_input.prompt_key != "AI_CANDIDATE_TURN"
                ):
                    raise RuntimeError("Candidate generation did not use accepted prompt V3.")
                database_url = _database_url()
                with psycopg.connect(database_url) as connection:
                    row = connection.execute(
                        "SELECT status, request_metadata FROM llm_generation_requests "
                        "WHERE id = %s",
                        (generation_input.generation_request_id,),
                    ).fetchone()
                if row is None or row[0] != "RUNNING":
                    raise RuntimeError(f"Candidate request was not durable RUNNING: {row!r}")
                call = {
                    "workload": "candidate",
                    "generation_request_id": str(generation_input.generation_request_id),
                    "participant_id": str(generation_input.participant_id),
                    "floor_grant_id": str(generation_input.floor_grant_id),
                    "phase": str(generation_input.phase),
                    "prompt_version_id": str(generation_input.prompt_version_id),
                    "prompt_version_number": generation_input.prompt_version_number,
                    "prompt_key": generation_input.prompt_key,
                    "private_sentinel_index": sentinel_indexes[0],
                    "request_metadata": row[1],
                }
                arm = Path(os.environ["GIA_P16D_CANCELLATION_ARM"])
                consumed = Path(os.environ["GIA_P16D_CANCELLATION_CONSUMED"])
                claimed_cancellation = False
                arm_claimed_at = None
                if restarted.exists() and arm.exists() and not consumed.exists():
                    try:
                        arm.replace(consumed)
                    except FileNotFoundError:
                        pass
                    else:
                        claimed_cancellation = True
                        arm_claimed_at = time.time()
                if claimed_cancellation:
                    try:
                        _append(call)
                        running = {
                            "generation_request_id": call["generation_request_id"],
                            "floor_grant_id": call["floor_grant_id"],
                            "arm_claimed_at": arm_claimed_at,
                            "running_at": time.time(),
                        }
                        Path(os.environ["GIA_P16D_PROVIDER_RUNNING"]).write_text(
                            json.dumps(running), encoding="utf-8"
                        )
                        await _blocked.wait()
                    except asyncio.CancelledError:
                        if not consumed.exists():
                            raise RuntimeError(
                                "P1-6D cancellation occurred before Browser intent."
                            )
                        Path(os.environ["GIA_P16D_PROVIDER_CANCELLED"]).write_text(
                            json.dumps({**running, "cancelled_at": time.time()}),
                            encoding="utf-8",
                        )
                        raise
                _append(call)
                return RawGenerationSuccess(
                    content=(
                        f"P16D_AI_PUBLIC:{generation_input.participant_id}:"
                        f"{generation_input.phase}:{generation_input.floor_grant_id}"
                    )
                )

        _provider = NetworkFreeP16DProvider()

        def _provider_factory(_settings):
            return _provider

        _original_drive_continuous_ai = composition.drive_continuous_ai

        async def _hold_at_quiescent_restart_boundary(result, session_id):
            with psycopg.connect(_database_url()) as connection:
                live_requests = connection.execute(
                    "SELECT count(id) FROM llm_generation_requests "
                    "WHERE session_id = %s AND status IN ('REQUESTED', 'RUNNING')",
                    (session_id,),
                ).fetchone()
            if live_requests is None or live_requests[0] != 0:
                raise RuntimeError(
                    "Pre-restart boundary retained a live generation request: "
                    f"{live_requests!r}"
                )
            Path(os.environ["GIA_P16D_PRE_RESTART_QUIESCENT"]).write_text(
                json.dumps({"occurred_at": time.time()}), encoding="utf-8"
            )
            restart_request = Path(os.environ["GIA_P16D_API_RESTART_REQUEST"])
            deadline = time.monotonic() + 20
            while not restart_request.exists() and time.monotonic() < deadline:
                await asyncio.sleep(0.05)
            if not restart_request.exists():
                raise RuntimeError("Browser did not request API restart after quiescence.")
            await asyncio.Event().wait()
            return result

        async def _drive_with_post_restart_arm_gate(*args, **kwargs):
            async with _post_restart_gate:
                restarted = Path(os.environ["GIA_P16D_RESTARTED_PROCESS"])
                pre_restart_arm = Path(os.environ["GIA_P16D_PRE_RESTART_ARM"])
                post_restart_success = Path(
                    os.environ["GIA_P16D_POST_RESTART_SUCCESS"]
                )
                consumed = Path(os.environ["GIA_P16D_CANCELLATION_CONSUMED"])
                if not restarted.exists():
                    if pre_restart_arm.exists():
                        return await _hold_at_quiescent_restart_boundary(
                            None, kwargs["session_id"]
                        )
                    result = await _original_drive_continuous_ai(*args, **kwargs)
                    if pre_restart_arm.exists():
                        return await _hold_at_quiescent_restart_boundary(
                            result, kwargs["session_id"]
                        )
                    return result
                if post_restart_success.exists() or consumed.exists():
                    return await _original_drive_continuous_ai(*args, **kwargs)

                restart_epoch = float(restarted.read_text(encoding="utf-8"))
                drive_deadline = time.monotonic() + 45
                while True:
                    original_budget = continuous.MAX_AUTOMATED_AI_TURNS_PER_DRIVE
                    continuous.MAX_AUTOMATED_AI_TURNS_PER_DRIVE = 1
                    try:
                        result = await _original_drive_continuous_ai(*args, **kwargs)
                    finally:
                        continuous.MAX_AUTOMATED_AI_TURNS_PER_DRIVE = original_budget
                    with psycopg.connect(_database_url()) as connection:
                        completed = connection.execute(
                            "SELECT id, floor_grant_id, "
                            "extract(epoch FROM completed_at) "
                            "FROM llm_generation_requests "
                            "WHERE session_id = %s AND status = 'COMPLETED' "
                            "AND requested_at >= to_timestamp(%s) "
                            "ORDER BY completed_at DESC, id DESC LIMIT 1",
                            (kwargs["session_id"], restart_epoch),
                        ).fetchone()
                    if completed is not None:
                        break
                    if (
                        result.outcome
                        is continuous.ContinuousAiDriveOutcome.WAITING_FOR_HUMAN
                        or time.monotonic() >= drive_deadline
                    ):
                        return result
                    await asyncio.sleep(0.1)
                post_restart_success.write_text(
                    json.dumps({
                        "generation_request_id": str(completed[0]),
                        "floor_grant_id": str(completed[1]),
                        "completed_at": float(completed[2]),
                        "observed_at": time.time(),
                    }),
                    encoding="utf-8",
                )

                arm = Path(os.environ["GIA_P16D_CANCELLATION_ARM"])
                arm_deadline = time.monotonic() + 35
                while not arm.exists() and time.monotonic() < arm_deadline:
                    await asyncio.sleep(0.05)
                if not arm.exists():
                    raise RuntimeError(
                        "Browser did not arm cancellation after durable post-restart success."
                    )
                return await _original_drive_continuous_ai(*args, **kwargs)

        composition.ZhipuGenerationProvider = _provider_factory
        composition.drive_continuous_ai = _drive_with_post_restart_arm_gate

        from group_interview_arena_api.app import app
        """
    )


def _database_connection(temporary_database: TemporaryDatabase):
    url = temporary_database.database_url
    return psycopg.connect(
        host=url.host,
        port=url.port,
        dbname=url.database,
        user=url.username,
        password=url.password,
    )


def _capture_event_prefix(
    temporary_database: TemporaryDatabase, output_path: Path
) -> None:
    with _database_connection(temporary_database) as connection:
        rows = connection.execute(
            "SELECT sequence, event_version, event_type, causation_action_id, payload "
            "FROM discussion_events ORDER BY sequence"
        ).fetchall()
    output_path.write_text(
        json.dumps(
            [
                [sequence, version, event_type, str(action_id), payload]
                for sequence, version, event_type, action_id, payload in rows
            ],
            sort_keys=True,
        ),
        encoding="utf-8",
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
    *,
    provider_calls: list[dict[str, Any]],
    post_restart_success: dict[str, Any],
    cancellation_arm: dict[str, Any],
    provider_running: dict[str, Any],
    cancellation_reload: dict[str, Any],
    cancellation: dict[str, Any],
    restart_timestamp: float,
    event_prefix: list[list[object]],
) -> None:
    with _database_connection(temporary_database) as connection:
        session_rows = connection.execute(
            "SELECT id, status, last_sequence, phase_started_at, phase_deadline_at, "
            "current_floor_grant_id FROM simulation_sessions"
        ).fetchall()
        if len(session_rows) != 1:
            raise RuntimeError(f"Expected one P1-6D session, got {session_rows!r}.")
        session_id, status, last_sequence, started_at, deadline_at, current_grant = (
            session_rows[0]
        )
        if (status, started_at, deadline_at, current_grant) != (
            "COMPLETED",
            None,
            None,
            None,
        ):
            raise RuntimeError(
                f"P1-6D final lifecycle state mismatch: {session_rows[0]!r}"
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
            raise RuntimeError(f"P1-6D authoritative roster mismatch: {participants!r}")
        ai_ids = {str(row[0]) for row in ai_rows}
        expected_private_index = {
            str(row[0]): int(str(row[3])[-1]) - 1 for row in ai_rows
        }

        events = connection.execute(
            "SELECT sequence, event_version, event_type, causation_action_id, payload "
            "FROM discussion_events WHERE session_id = %s ORDER BY sequence",
            (session_id,),
        ).fetchall()
        event_sequences = [row[0] for row in events]
        if event_sequences != list(range(1, int(last_sequence) + 1)):
            raise RuntimeError(
                "DiscussionEvent sequence is not contiguous and authoritative."
            )
        final_prefix = [
            [sequence, version, event_type, str(action_id), payload]
            for sequence, version, event_type, action_id, payload in events
        ][: len(event_prefix)]
        if final_prefix != event_prefix:
            raise RuntimeError("API restart rewrote the authoritative event prefix.")
        utterance_events = [
            row for row in events if row[2] == "participant.utterance.created"
        ]
        human_events = [
            row for row in utterance_events if row[4]["actor_kind"] == "HUMAN"
        ]
        ai_events = [row for row in utterance_events if row[4]["actor_kind"] == "AI"]
        if (
            not human_events
            or {row[4]["participant_id"] for row in ai_events} != ai_ids
        ):
            raise RuntimeError(
                "Full journey did not include active Human and all three AI seats."
            )

        memory_state = connection.execute(
            "SELECT revision, source_through_sequence, structured_state "
            "FROM discussion_memory_states WHERE session_id = %s",
            (session_id,),
        ).fetchone()
        memory_revisions = connection.execute(
            "SELECT revision, base_revision, source_from_sequence, "
            "source_through_sequence, patches, prompt_version_id, "
            "provider_identifier, model_identifier, configuration_version "
            "FROM discussion_memory_revisions WHERE session_id = %s "
            "ORDER BY revision",
            (session_id,),
        ).fetchall()
        if memory_state is None or memory_state[0] <= 0 or not memory_revisions:
            raise RuntimeError("P1-6D did not persist a durable Memory revision.")
        for index, revision in enumerate(memory_revisions, start=1):
            if revision[0] != index or revision[1] != index - 1:
                raise RuntimeError("Memory revision chain is not contiguous.")
            if any(value is None for value in revision[5:9]):
                raise RuntimeError("Semantic Memory provenance is incomplete.")
        if memory_state[0] != memory_revisions[-1][0]:
            raise RuntimeError(
                "Materialized Memory revision does not match its journal."
            )

        requests = connection.execute(
            "SELECT request.id, request.participant_id, request.floor_grant_id, "
            "request.status, request.failure_code, request.request_metadata, "
            "request.prompt_version_id, prompt.prompt_key, prompt.version_number "
            "FROM llm_generation_requests AS request "
            "JOIN prompt_versions AS prompt ON prompt.id = request.prompt_version_id "
            "WHERE request.session_id = %s ORDER BY request.requested_at, request.id",
            (session_id,),
        ).fetchall()
        request_counts = connection.execute(
            "SELECT floor_grant_id, count(id) "
            "FROM llm_generation_requests WHERE session_id = %s "
            "GROUP BY floor_grant_id ORDER BY floor_grant_id",
            (session_id,),
        ).fetchall()
        if not request_counts or any(row[1] != 1 for row in request_counts):
            raise RuntimeError(
                "Generation request count per AI floor grant was not exactly one: "
                f"{request_counts!r}"
            )
        live_requests = [row for row in requests if row[3] in {"REQUESTED", "RUNNING"}]
        if live_requests:
            raise RuntimeError(
                f"Final session retained non-terminal generation requests: {live_requests!r}"
            )
        completed = [row for row in requests if row[3] == "COMPLETED"]
        failed = [row for row in requests if row[3] == "FAILED"]
        post_restart_request = UUID(post_restart_success["generation_request_id"])
        post_restart_grant = UUID(post_restart_success["floor_grant_id"])
        if not any(
            row[0] == post_restart_request
            and row[2] == post_restart_grant
            and row[3] == "COMPLETED"
            for row in requests
        ):
            raise RuntimeError(
                "Post-restart success marker did not identify a durable completed request."
            )
        cancelled_grant = UUID(cancellation["floor_grant_id"])
        cancelled_request = UUID(cancellation["generation_request_id"])
        if [(row[0], row[2], row[4]) for row in failed] != [
            (cancelled_request, cancelled_grant, "INTERNAL_ERROR")
        ]:
            raise RuntimeError(f"Cancellation durable failure mismatch: {failed!r}")
        memory_backed = [
            row
            for row in completed
            if row[5].get("schema_version") == 2
            and row[5].get("memory_revision", 0) > 0
            and row[6] == V3_PROMPT_ID
            and row[7:9] == ("AI_CANDIDATE_TURN", 3)
        ]
        if not memory_backed:
            raise RuntimeError(
                "No completed candidate consumed Memory + V3 + Metadata V2."
            )
        utterance_sequences = {row[0] for row in utterance_events}
        for request in memory_backed:
            metadata = request[5]
            for cursor_name in (
                "memory_source_through_sequence",
                "context_source_through_sequence",
            ):
                cursor = metadata[cursor_name]
                if cursor != 0 and cursor not in utterance_sequences:
                    raise RuntimeError(
                        f"{cursor_name} did not reference public evidence."
                    )

        exact_once_rows = connection.execute(
            "SELECT request.floor_grant_id, count(DISTINCT utterance.id), "
            "count(DISTINCT event.sequence), count(DISTINCT release.grant_id), "
            "min(release.reason_code) FROM llm_generation_requests AS request "
            "LEFT JOIN ai_utterances AS utterance ON utterance.generation_request_id = request.id "
            "LEFT JOIN discussion_events AS event ON event.session_id = request.session_id "
            "AND event.event_type = 'participant.utterance.created' "
            "AND event.payload->>'floor_grant_id' = request.floor_grant_id::text "
            "LEFT JOIN floor_releases AS release ON release.session_id = request.session_id "
            "AND release.grant_id = request.floor_grant_id "
            "WHERE request.session_id = %s AND request.status = 'COMPLETED' "
            "GROUP BY request.floor_grant_id",
            (session_id,),
        ).fetchall()
        if not exact_once_rows or any(
            row[1:] != (1, 1, 1, "SPEAKER_FINISHED") for row in exact_once_rows
        ):
            raise RuntimeError(
                f"Successful AI exact-once evidence mismatch: {exact_once_rows!r}"
            )
        cancelled_counts = connection.execute(
            "SELECT count(utterance.id), count(event.sequence), count(release.grant_id), "
            "min(release.reason_code) FROM llm_generation_requests AS request "
            "LEFT JOIN ai_utterances AS utterance ON utterance.generation_request_id = request.id "
            "LEFT JOIN discussion_events AS event ON event.session_id = request.session_id "
            "AND event.event_type = 'participant.utterance.created' "
            "AND event.payload->>'floor_grant_id' = request.floor_grant_id::text "
            "LEFT JOIN floor_releases AS release ON release.session_id = request.session_id "
            "AND release.grant_id = request.floor_grant_id WHERE request.id = %s",
            (cancelled_request,),
        ).fetchone()
        if cancelled_counts != (0, 0, 1, "INTERRUPTED"):
            raise RuntimeError(
                f"Cancelled grant exact-once evidence mismatch: {cancelled_counts!r}"
            )

        lifecycle = [
            row[4]["status"] for row in events if row[2] == "session.state_changed"
        ]
        if tuple(lifecycle) != LIFECYCLE:
            raise RuntimeError(f"Durable lifecycle mismatch: {lifecycle!r}")
        _assert_no_private_sentinel([row[4] for row in events], "DiscussionEvent")
        _assert_no_private_sentinel(memory_state[2], "structured Memory")
        _assert_no_private_sentinel(
            [row[4] for row in memory_revisions], "patch journal"
        )

    candidate_calls = [row for row in provider_calls if row["workload"] == "candidate"]
    semantic_calls = [row for row in provider_calls if row["workload"] == "semantic"]
    if not candidate_calls or not semantic_calls:
        raise RuntimeError(
            "Dual semantic invoke + candidate call workload was not observed."
        )
    candidate_grants = [row["floor_grant_id"] for row in candidate_calls]
    if len(candidate_grants) != len(set(candidate_grants)):
        raise RuntimeError("A candidate floor grant was invoked more than once.")
    request_grants = {str(row[2]) for row in requests}
    if set(candidate_grants) != request_grants:
        raise RuntimeError(
            "Candidate provider calls did not map one-to-one to generation requests: "
            f"calls={candidate_grants!r}, requests={sorted(request_grants)!r}"
        )
    if candidate_grants.count(str(cancelled_grant)) != 1:
        raise RuntimeError("Cancelled eligible candidate was not invoked exactly once.")
    if {row["participant_id"] for row in candidate_calls} != ai_ids:
        raise RuntimeError("Provider did not execute calls for all three AI seats.")
    for row in candidate_calls:
        participant_id = str(row["participant_id"])
        if row["private_sentinel_index"] != expected_private_index[participant_id]:
            raise RuntimeError("Candidate received another seat's private stance.")
    if not any(
        float(row["occurred_at"]) > restart_timestamp
        and dict(row["request_metadata"]).get("memory_revision", 0) > 0
        for row in candidate_calls
    ):
        raise RuntimeError("No memory-backed candidate continued after API restart.")
    ordering = (
        restart_timestamp,
        float(post_restart_success["completed_at"]),
        float(post_restart_success["observed_at"]),
        float(cancellation_arm["occurred_at"]),
        float(provider_running["arm_claimed_at"]),
        float(provider_running["running_at"]),
        float(cancellation_reload["occurred_at"]),
        float(cancellation["cancelled_at"]),
    )
    if not (
        ordering[0]
        <= ordering[1]
        <= ordering[2]
        < ordering[3]
        < ordering[4]
        <= ordering[5]
        < ordering[6]
        < ordering[7]
    ):
        raise RuntimeError(f"Cancellation evidence ordering mismatch: {ordering!r}")
    _assert_no_private_sentinel(provider_calls, "provider evidence log")


async def _seed_p1_6d_question_async(
    temporary_database: TemporaryDatabase,
) -> None:
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


def _seed_p1_6d_question(temporary_database: TemporaryDatabase) -> None:
    asyncio.run(
        _seed_p1_6d_question_async(temporary_database),
        loop_factory=asyncio.SelectorEventLoop,
    )


def _run_browser_flow(temporary_database: TemporaryDatabase) -> None:
    _require_available_port(WEB_PORT)
    _require_available_port(API_PORT)
    node = shutil.which("node.exe" if os.name == "nt" else "node")
    if node is None:
        raise RuntimeError("Node.js is required to run the P1-6D Web server.")
    next_cli = WEB_ROOT / "node_modules" / "next" / "dist" / "bin" / "next"
    if not next_cli.is_file():
        raise RuntimeError("Next.js is not installed; run the frozen install gate.")

    database_url = temporary_database.database_settings().database_url
    with tempfile.TemporaryDirectory(prefix="gia_p16d_e2e_") as directory:
        temporary_path = Path(directory)
        api_log = temporary_path / "api.log"
        web_log = temporary_path / "web.log"
        restart_request = temporary_path / "restart-api.request"
        restart_ready = temporary_path / "restart-api.ready"
        pre_restart_arm = temporary_path / "pre-restart.arm"
        pre_restart_quiescent = temporary_path / "pre-restart-quiescent.json"
        cancellation_arm = temporary_path / "cancellation.arm"
        cancellation_consumed = temporary_path / "cancellation.consumed"
        restarted_process = temporary_path / "restarted-process.marker"
        post_restart_success = temporary_path / "post-restart-success.json"
        provider_running = temporary_path / "provider-running.json"
        provider_cancelled = temporary_path / "provider-cancelled.json"
        cancellation_reload = temporary_path / "cancellation-reload.json"
        provider_calls = temporary_path / "provider-calls.jsonl"
        event_prefix_path = temporary_path / "event-prefix.json"
        fake_app_module = temporary_path / "gia_p16d_fake_provider_app.py"
        fake_app_module.write_text(_provider_module_source(), encoding="utf-8")

        api_command = [
            sys.executable,
            "-m",
            "uvicorn",
            "gia_p16d_fake_provider_app:app",
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
            "GIA_API_ZHIPU_API_KEY": "p1-6d-network-free-placeholder",
            "GIA_API_ZHIPU_MODEL": "p1-6d-network-free-model",
            "GIA_API_SESSION_PHASE_DURATIONS": (
                '{"preparation_seconds":2,'
                '"opening_statements_seconds":30,'
                '"exploration_seconds":20,'
                '"conflict_and_evaluation_seconds":20,'
                '"convergence_seconds":20,'
                '"final_summary_seconds":20}'
            ),
            "GIA_P16D_CANCELLATION_ARM": str(cancellation_arm),
            "GIA_P16D_CANCELLATION_CONSUMED": str(cancellation_consumed),
            "GIA_P16D_API_RESTART_REQUEST": str(restart_request),
            "GIA_P16D_PRE_RESTART_ARM": str(pre_restart_arm),
            "GIA_P16D_PRE_RESTART_QUIESCENT": str(pre_restart_quiescent),
            "GIA_P16D_RESTARTED_PROCESS": str(restarted_process),
            "GIA_P16D_POST_RESTART_SUCCESS": str(post_restart_success),
            "GIA_P16D_PROVIDER_RUNNING": str(provider_running),
            "GIA_P16D_PROVIDER_CANCELLED": str(provider_cancelled),
            "GIA_P16D_PROVIDER_CALLS": str(provider_calls),
            "PYTHONPATH": os.pathsep.join(
                filter(None, (str(temporary_path), os.environ.get("PYTHONPATH")))
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
                    _capture_event_prefix(temporary_database, event_prefix_path)
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
                    restarted_process.write_text(str(time.time()), encoding="utf-8")
                    restarted = _start_server_process(
                        api_command,
                        cwd=API_ROOT,
                        environment=api_environment,
                        log_path=api_log,
                    )
                    current_api[0] = restarted
                    _wait_for_http(f"{API_ORIGIN}/health", restarted[0], api_log)
                    restart_ready.write_text(
                        json.dumps({"occurred_at": time.time()}), encoding="utf-8"
                    )
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
                    name="gia-p16d-api-restart",
                )
                coordinator.start()
                try:
                    _run_dedicated_playwright(
                        {
                            "GIA_P16D_API_ORIGIN": API_ORIGIN,
                            "GIA_P16D_API_RESTART_REQUEST": str(restart_request),
                            "GIA_P16D_API_RESTART_READY": str(restart_ready),
                            "GIA_P16D_PRE_RESTART_ARM": str(pre_restart_arm),
                            "GIA_P16D_PRE_RESTART_QUIESCENT": str(
                                pre_restart_quiescent
                            ),
                            "GIA_P16D_CANCELLATION_ARM": str(cancellation_arm),
                            "GIA_P16D_POST_RESTART_SUCCESS": str(post_restart_success),
                            "GIA_P16D_PROVIDER_RUNNING": str(provider_running),
                            "GIA_P16D_PROVIDER_CANCELLED": str(provider_cancelled),
                            "GIA_P16D_CANCELLATION_RELOAD": str(cancellation_reload),
                            "GIA_P16D_PROVIDER_CALLS": str(provider_calls),
                        }
                    )
                finally:
                    coordinator_stop.set()
                    coordinator.join(timeout=SHUTDOWN_TIMEOUT_SECONDS)
                if coordinator.is_alive():
                    raise RuntimeError("P1-6D API restart coordinator did not stop.")
                if coordinator_errors:
                    raise RuntimeError("P1-6D API restart coordinator failed.") from (
                        coordinator_errors[0]
                    )
        except Exception:
            print("P1-6D API server log tail:", file=sys.stderr)
            print(_log_tail(api_log), file=sys.stderr)
            if provider_calls.exists():
                print("P1-6D provider calls:", file=sys.stderr)
                print(provider_calls.read_text(encoding="utf-8"), file=sys.stderr)
            if api_log.exists():
                diagnostic_lines = [
                    line
                    for line in api_log.read_text(
                        encoding="utf-8", errors="replace"
                    ).splitlines()
                    if any(
                        marker in line
                        for marker in (
                            '"level":"ERROR"',
                            "Traceback",
                            "RuntimeError",
                            "INVALID_OUTPUT",
                        )
                    )
                ]
                if diagnostic_lines:
                    print("P1-6D API diagnostics:", file=sys.stderr)
                    print("\n".join(diagnostic_lines[-80:]), file=sys.stderr)
            with _database_connection(temporary_database) as diagnostic_connection:
                diagnostic_events = diagnostic_connection.execute(
                    "SELECT sequence, event_type, length(payload->>'content') "
                    "FROM discussion_events ORDER BY sequence"
                ).fetchall()
                diagnostic_requests = diagnostic_connection.execute(
                    "SELECT floor_grant_id, status, failure_code, request_metadata "
                    "FROM llm_generation_requests ORDER BY requested_at"
                ).fetchall()
                diagnostic_memory = diagnostic_connection.execute(
                    "SELECT revision, source_through_sequence "
                    "FROM discussion_memory_states"
                ).fetchall()
            print(
                f"P1-6D durable diagnostics events={diagnostic_events!r} "
                f"requests={diagnostic_requests!r} memory={diagnostic_memory!r}",
                file=sys.stderr,
            )
            print("P1-6D Web server log tail:", file=sys.stderr)
            print(_log_tail(web_log), file=sys.stderr)
            raise
        finally:
            running = current_api[0]
            if running is not None:
                _stop_server_process(*running)
                current_api[0] = None
            _wait_for_port_release(WEB_PORT)
            _wait_for_port_release(API_PORT)

        if not all(
            path.exists()
            for path in (
                provider_calls,
                provider_running,
                provider_cancelled,
                restart_ready,
                pre_restart_quiescent,
                post_restart_success,
                cancellation_consumed,
                cancellation_reload,
                event_prefix_path,
            )
        ):
            raise RuntimeError("P1-6D browser evidence files were incomplete.")
        _verify_durable_result(
            temporary_database,
            provider_calls=_read_json_lines(provider_calls),
            post_restart_success=json.loads(
                post_restart_success.read_text(encoding="utf-8")
            ),
            cancellation_arm=json.loads(
                cancellation_consumed.read_text(encoding="utf-8")
            ),
            provider_running=json.loads(provider_running.read_text(encoding="utf-8")),
            cancellation_reload=json.loads(
                cancellation_reload.read_text(encoding="utf-8")
            ),
            cancellation=json.loads(provider_cancelled.read_text(encoding="utf-8")),
            restart_timestamp=json.loads(restart_ready.read_text(encoding="utf-8"))[
                "occurred_at"
            ],
            event_prefix=json.loads(event_prefix_path.read_text(encoding="utf-8")),
        )


def main() -> int:
    database_settings = IntegrationDatabaseSettings()  # pyright: ignore[reportCallIssue]
    with temporary_database_context(
        database_settings,
        P1_6D_BROWSER_DATABASE_PREFIX,
    ) as temporary_database:
        migrate_database(temporary_database)
        _seed_p1_6d_question(temporary_database)
        _run_browser_flow(temporary_database)
    print(
        "P1-6D dedicated Browser Acceptance Scenario passed: isolated Human + three AI "
        "full lifecycle, dual semantic/candidate fake workload, durable Memory + V3 + "
        "Metadata V2 provenance, reload/API restart continuity, one eligible-candidate "
        "cancellation recovery, exact-once persistence, private-stance isolation, and "
        "complete temporary database/server cleanup."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
