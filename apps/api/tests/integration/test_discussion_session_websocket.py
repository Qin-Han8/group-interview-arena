import asyncio
import re
from collections.abc import Callable, Generator
from contextlib import contextmanager
from typing import Never, Protocol, cast
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from httpx import Cookies, Headers, Response
from sqlalchemy import URL, select
from starlette.testclient import (
    TestClient,
    WebSocketDenialResponse,
    WebSocketTestSession,
)
from starlette.websockets import WebSocketDisconnect

from group_interview_arena_api.app import create_app
from group_interview_arena_api.core.config import (
    DatabaseSettings,
    Environment,
    SessionPhaseDurations,
    Settings,
)
from group_interview_arena_api.db.models import SimulationSession
from group_interview_arena_api.db.runtime import (
    create_database_engine,
    create_database_session_factory,
    dispose_database_engine,
)
from group_interview_arena_api.identity.cookies import SESSION_COOKIE_NAME
from group_interview_arena_api.modules.discussion_sessions import realtime
from group_interview_arena_api.modules.discussion_sessions.domain import (
    SessionStatus,
    StoredEvent,
)
from group_interview_arena_api.modules.discussion_sessions.public_events import (
    PublicEventProjectionError,
)
from group_interview_arena_api.modules.discussion_sessions.service import (
    ActionIdConflictError,
)
from group_interview_arena_api.modules.floor_control.scheduler import (
    V0_1_SCHEDULER_POLICY,
    ScheduleFloorCommand,
)
from group_interview_arena_api.modules.floor_control.service import (
    apply_scheduler_command,
)
from group_interview_arena_api.modules.question_personas.seed import (
    INTERNAL_VALIDATION_BUNDLE,
    seed_question_persona_foundation,
)

pytestmark = pytest.mark.integration

TRUSTED_ORIGIN = "http://localhost:3000"
UNTRUSTED_ORIGIN = "https://attacker.invalid"
VALID_PASSWORD = "websocket integration password"
AUTH_HEADERS = {"Origin": TRUSTED_ORIGIN, "X-GIA-CSRF": "1"}
DeniedConnection = (WebSocketDenialResponse, WebSocketDisconnect)


class TemporaryDatabaseContext(Protocol):
    database_name: str
    database_url: URL

    def database_settings(self) -> DatabaseSettings: ...


class SyncTestClient(Protocol):
    cookies: Cookies

    def post(
        self,
        url: str,
        *,
        headers: dict[str, str],
        json: dict[str, str] | None = None,
    ) -> Response: ...

    def get(self, url: str) -> Response: ...

    def websocket_connect(
        self,
        url: str,
        *,
        headers: dict[str, str] | Headers,
    ) -> WebSocketTestSession: ...


def _application(
    temporary_database: TemporaryDatabaseContext,
    *,
    settings: Settings | None = None,
) -> FastAPI:
    async def seed() -> None:
        engine = create_database_engine(temporary_database.database_settings())
        try:
            await seed_question_persona_foundation(
                create_database_session_factory(engine)
            )
        finally:
            await dispose_database_engine(engine)

    asyncio.run(seed(), loop_factory=asyncio.SelectorEventLoop)
    return create_app(
        settings
        or Settings(
            environment=Environment.TEST,
            cors_origins=(TRUSTED_ORIGIN,),
        ),
        temporary_database.database_settings(),
    )


@contextmanager
def _client(application: FastAPI) -> Generator[SyncTestClient]:
    with TestClient(
        application,
        backend_options={"loop_factory": asyncio.SelectorEventLoop},
    ) as raw_client:
        yield raw_client  # pyright: ignore[reportUnknownVariableType]


def _register(client: SyncTestClient, username: str) -> str:
    response = client.post(
        "/auth/register",
        headers=AUTH_HEADERS,
        json={"username": username, "password": VALID_PASSWORD},
    )
    assert response.status_code == 201
    token = client.cookies.get(SESSION_COOKIE_NAME)
    assert token is not None
    return token


def _create_session(client: SyncTestClient) -> dict[str, object]:
    response = client.post(
        "/sessions",
        headers=AUTH_HEADERS,
        json={"question_version_id": str(INTERNAL_VALIDATION_BUNDLE.version_id)},
    )
    assert response.status_code == 201
    return response.json()  # pyright: ignore[reportAny]


def _set_token(client: SyncTestClient, token: str | None) -> None:
    client.cookies.clear()
    if token is not None:
        client.cookies.set(SESSION_COOKIE_NAME, token)


def _ws_path(session_id: str, after_sequence: int = 1) -> str:
    return f"/ws/sessions/{session_id}?after_sequence={after_sequence}"


def _abort_command(session_id: str, action_id: UUID) -> dict[str, object]:
    return {
        "schema_version": 1,
        "type": "session.abort",
        "session_id": session_id,
        "action_id": str(action_id),
        "payload": {},
    }


def _start_command(session_id: str, action_id: UUID) -> dict[str, object]:
    return {
        "schema_version": 1,
        "type": "session.start",
        "session_id": session_id,
        "action_id": str(action_id),
        "payload": {},
    }


def _utterance_command(
    session_id: str,
    action_id: UUID,
    floor_grant_id: UUID | str,
    content: str,
) -> dict[str, object]:
    return {
        "schema_version": 1,
        "type": "participant.utterance.submit",
        "session_id": session_id,
        "action_id": str(action_id),
        "payload": {
            "floor_grant_id": str(floor_grant_id),
            "content": content,
        },
    }


async def _schedule_floor(
    temporary_database: TemporaryDatabaseContext,
    session_id: UUID,
) -> list[StoredEvent]:
    engine = create_database_engine(temporary_database.database_settings())
    try:
        session_factory = create_database_session_factory(engine)
        async with session_factory() as session:
            aggregate = await session.scalar(
                select(SimulationSession).where(SimulationSession.id == session_id)
            )
            assert aggregate is not None
            owner_id = aggregate.owner_user_id
            command = ScheduleFloorCommand(
                session_id=session_id,
                action_id=uuid4(),
                decision_id=uuid4(),
                grant_id=uuid4(),
                intervention_id=uuid4(),
                expected_phase=SessionStatus(aggregate.status),
                expected_last_sequence=aggregate.last_sequence,
                expected_current_floor_grant_id=aggregate.current_floor_grant_id,
                evaluated_at=aggregate.updated_at,
                policy=V0_1_SCHEDULER_POLICY,
            )
        async with session_factory() as session:
            return await apply_scheduler_command(
                session,
                owner_id=owner_id,
                command=command,
            )
    finally:
        await dispose_database_engine(engine)


def _assert_error(
    payload: dict[str, object],
    *,
    code: str,
    session_id: str,
) -> None:
    assert payload["schema_version"] == 1
    assert payload["type"] == "error"
    assert payload["session_id"] == session_id
    assert "sequence" not in payload
    assert re.fullmatch(
        r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z",
        str(payload["occurred_at"]),
    )
    error = payload["error"]
    assert isinstance(error, dict)
    error = cast(dict[str, object], error)
    assert error["code"] == code
    assert UUID(str(error["request_id"])).version == 4


def test_websocket_denies_invalid_origin_auth_and_non_owner_before_accept(
    migrated_database: TemporaryDatabaseContext,
    capsys: pytest.CaptureFixture[str],
) -> None:
    application = _application(migrated_database)
    with _client(application) as client:
        owner_token = _register(client, "ws_owner")
        snapshot = _create_session(client)
        session_id = str(snapshot["id"])

        _set_token(client, None)
        with pytest.raises(DeniedConnection):
            with client.websocket_connect(
                _ws_path(session_id),
                headers={"Origin": TRUSTED_ORIGIN},
            ):
                pass

        _set_token(client, owner_token)
        invalid_origin_headers: list[dict[str, str] | Headers] = [
            {},
            {"Origin": "null"},
            {"Origin": UNTRUSTED_ORIGIN},
            Headers([("Origin", TRUSTED_ORIGIN), ("Origin", TRUSTED_ORIGIN)]),
        ]
        for headers in invalid_origin_headers:
            with pytest.raises(DeniedConnection):
                with client.websocket_connect(
                    _ws_path(session_id),
                    headers=headers,
                ):
                    pass

        _set_token(client, None)
        non_owner_token = _register(client, "ws_non_owner")
        _set_token(client, non_owner_token)
        with pytest.raises(DeniedConnection):
            with client.websocket_connect(
                _ws_path(session_id),
                headers={"Origin": TRUSTED_ORIGIN},
            ):
                pass

        _set_token(client, owner_token)
        for path in (
            f"/ws/sessions/{session_id}",
            _ws_path(session_id, after_sequence=-1),
        ):
            with pytest.raises(DeniedConnection):
                with client.websocket_connect(
                    path,
                    headers={"Origin": TRUSTED_ORIGIN},
                ):
                    pass
        with client.websocket_connect(
            _ws_path(session_id),
            headers={"Origin": TRUSTED_ORIGIN},
        ):
            pass

    captured = capsys.readouterr()
    combined = captured.out + captured.err
    assert owner_token not in combined
    assert UNTRUSTED_ORIGIN not in combined


def test_websocket_abort_duplicate_invalid_state_and_ordered_catchup(
    migrated_database: TemporaryDatabaseContext,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    application = _application(migrated_database)
    with _client(application) as client:
        _register(client, "ws_command_owner")
        snapshot = _create_session(client)
        session_id = str(snapshot["id"])
        action_id = uuid4()
        command = _abort_command(session_id, action_id)

        with client.websocket_connect(
            _ws_path(session_id, after_sequence=0),
            headers={"Origin": TRUSTED_ORIGIN},
        ) as websocket:
            created = websocket.receive_json()
            assert created == {
                "schema_version": 1,
                "type": "session.created",
                "session_id": session_id,
                "sequence": 1,
                "occurred_at": snapshot["created_at"],
                "action_id": None,
                "payload": {"status": "CREATED"},
            }

            websocket.send_json(command)
            accepted = websocket.receive_json()
            assert accepted["schema_version"] == 2
            assert accepted["type"] == "session.state_changed"
            assert accepted["sequence"] == 2
            assert accepted["action_id"] == str(action_id)
            assert accepted["payload"] == {
                "previous_status": "CREATED",
                "status": "ABORTED_USER",
                "trigger": "USER_ABORT",
                "phase_started_at": None,
                "phase_deadline_at": None,
            }

            real_apply = realtime.apply_session_command

            async def conflict(
                *_args: object,
                **_kwargs: object,
            ) -> list[StoredEvent]:
                raise ActionIdConflictError

            monkeypatch.setattr(realtime, "apply_session_command", conflict)
            websocket.send_json(_abort_command(session_id, uuid4()))
            conflict_error = websocket.receive_json()
            _assert_error(
                conflict_error,
                code="ACTION_ID_CONFLICT",
                session_id=session_id,
            )
            monkeypatch.setattr(realtime, "apply_session_command", real_apply)

            websocket.send_json(_abort_command(session_id, uuid4()))
            invalid_state = websocket.receive_json()
            _assert_error(
                invalid_state,
                code="INVALID_SESSION_STATE",
                session_id=session_id,
            )

        with client.websocket_connect(
            _ws_path(session_id, after_sequence=0),
            headers={"Origin": TRUSTED_ORIGIN},
        ) as websocket:
            catchup = [websocket.receive_json(), websocket.receive_json()]
            assert [event["sequence"] for event in catchup] == [1, 2]


ProtocolPayloadFactory = Callable[[str], str | dict[str, object]]
PROTOCOL_PAYLOAD_FACTORIES: tuple[ProtocolPayloadFactory, ...] = (
    lambda _session_id: "{not-json",
    lambda session_id: {
        **_abort_command(session_id, uuid4()),
        "schema_version": 2,
    },
    lambda session_id: {
        **_abort_command(session_id, uuid4()),
        "type": "session.pause",
    },
    lambda session_id: {
        **_abort_command(session_id, uuid4()),
        "payload": {"secret": "payload-sentinel"},
    },
    lambda session_id: {
        **_abort_command(session_id, uuid4()),
        "unexpected": True,
    },
    lambda session_id: {
        "schema_version": 1,
        "type": "participant.utterance.submit",
        "session_id": session_id,
        "action_id": str(uuid4()),
        "payload": {"content": "missing exact floor binding"},
    },
    lambda session_id: {
        "schema_version": 1,
        "type": "participant.utterance.submit",
        "session_id": session_id,
        "action_id": str(uuid4()),
        "payload": {
            "floor_grant_id": str(uuid4()),
            "content": "authority must stay server-owned",
            "participant_id": str(uuid4()),
        },
    },
    lambda _session_id: _abort_command(str(uuid4()), uuid4()),
)


@pytest.mark.parametrize(
    "payload_factory",
    PROTOCOL_PAYLOAD_FACTORIES,
)
def test_websocket_protocol_error_is_safe_and_closes_1008(
    migrated_database: TemporaryDatabaseContext,
    payload_factory: ProtocolPayloadFactory,
    capsys: pytest.CaptureFixture[str],
) -> None:
    application = _application(migrated_database)
    with _client(application) as client:
        _register(client, f"ws_protocol_{uuid4().hex[:8]}")
        snapshot = _create_session(client)
        session_id = str(snapshot["id"])

        with client.websocket_connect(
            _ws_path(session_id),
            headers={"Origin": TRUSTED_ORIGIN},
        ) as websocket:
            payload = payload_factory(session_id)
            if isinstance(payload, str):
                websocket.send_text(payload)
            else:
                websocket.send_json(payload)
            error = websocket.receive_json()
            _assert_error(error, code="PROTOCOL_ERROR", session_id=session_id)
            assert "payload-sentinel" not in str(error)
            with pytest.raises(WebSocketDisconnect) as disconnect:
                websocket.receive_json()
            assert disconnect.value.code == 1008

        unchanged = client.get(f"/sessions/{session_id}")
        assert unchanged.status_code == 200
        assert unchanged.json()["status"] == "CREATED"
        assert unchanged.json()["last_sequence"] == 1

    captured = capsys.readouterr()
    assert "payload-sentinel" not in captured.out + captured.err


def test_websocket_ahead_watermark_and_lost_send_reconnect_are_durable(
    migrated_database: TemporaryDatabaseContext,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    application = _application(migrated_database)
    with _client(application) as client:
        _register(client, "ws_reconnect_owner")
        snapshot = _create_session(client)
        session_id = str(snapshot["id"])

        with client.websocket_connect(
            _ws_path(session_id, after_sequence=2),
            headers={"Origin": TRUSTED_ORIGIN},
        ) as websocket:
            ahead = websocket.receive_json()
            _assert_error(ahead, code="SEQUENCE_AHEAD", session_id=session_id)
            with pytest.raises(WebSocketDisconnect) as disconnect:
                websocket.receive_json()
            assert disconnect.value.code == 1008

        action_id = uuid4()
        real_projection = getattr(realtime, "project_public_events", None)

        async def fail_after_commit(*_args: object, **_kwargs: object) -> Never:
            raise RuntimeError("lost-send-exception-sentinel")

        monkeypatch.setattr(
            realtime,
            "project_public_events",
            fail_after_commit,
            raising=False,
        )
        with client.websocket_connect(
            _ws_path(session_id),
            headers={"Origin": TRUSTED_ORIGIN},
        ) as websocket:
            websocket.send_json(_abort_command(session_id, action_id))
            internal = websocket.receive_json()
            _assert_error(internal, code="INTERNAL_ERROR", session_id=session_id)
            assert internal["action_id"] == str(action_id)
            assert "lost-send-exception-sentinel" not in str(internal)
            with pytest.raises(WebSocketDisconnect) as disconnect:
                websocket.receive_json()
            assert disconnect.value.code == 1011

        if real_projection is not None:
            monkeypatch.setattr(realtime, "project_public_events", real_projection)

        restored = client.get(f"/sessions/{session_id}")
        assert restored.status_code == 200
        assert restored.json()["status"] == "ABORTED_USER"
        assert restored.json()["last_sequence"] == 2

        with client.websocket_connect(
            _ws_path(session_id),
            headers={"Origin": TRUSTED_ORIGIN},
        ) as websocket:
            recovered = websocket.receive_json()
            assert recovered["sequence"] == 2
            assert recovered["action_id"] == str(action_id)


@pytest.mark.parametrize("failure_kind", ["projection", "send"])
def test_periodic_catchup_failure_closes_safely_without_raw_error(
    migrated_database: TemporaryDatabaseContext,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    failure_kind: str,
) -> None:
    application = _application(
        migrated_database,
        settings=Settings(
            environment=Environment.TEST,
            cors_origins=(TRUSTED_ORIGIN,),
            session_phase_durations=SessionPhaseDurations(
                preparation_seconds=1,
                opening_statements_seconds=30,
                exploration_seconds=30,
                conflict_and_evaluation_seconds=30,
                convergence_seconds=30,
                final_summary_seconds=30,
            ),
        ),
    )
    original_send = vars(realtime)["_send_formal_event"]
    send_attempts = 0

    async def fail_once(*args: object, **kwargs: object) -> None:
        nonlocal send_attempts
        send_attempts += 1
        if send_attempts == 1:
            raise RuntimeError("periodic-send-private-sentinel")
        await original_send(*args, **kwargs)  # pyright: ignore[reportArgumentType]

    async def fail_projection(*_args: object, **_kwargs: object) -> Never:
        raise PublicEventProjectionError("periodic-projection-private-sentinel")

    with _client(application) as client:
        _register(client, "ws_periodic_send_failure_owner")
        snapshot = _create_session(client)
        session_id = str(snapshot["id"])

        with client.websocket_connect(
            _ws_path(session_id),
            headers={"Origin": TRUSTED_ORIGIN},
        ) as websocket:
            websocket.send_json(_start_command(session_id, uuid4()))
            assert websocket.receive_json()["sequence"] == 2
            assert websocket.receive_json()["sequence"] == 3
            if failure_kind == "projection":
                monkeypatch.setattr(
                    realtime,
                    "project_public_events",
                    fail_projection,
                )
            else:
                monkeypatch.setattr(realtime, "_send_formal_event", fail_once)
            asyncio.run(
                _schedule_floor(migrated_database, UUID(session_id)),
                loop_factory=asyncio.SelectorEventLoop,
            )

            error = websocket.receive_json()
            _assert_error(error, code="INTERNAL_ERROR", session_id=session_id)
            assert error["action_id"] is None
            with pytest.raises(WebSocketDisconnect) as disconnect:
                websocket.receive_json()
            assert disconnect.value.code == 1011

        durable = client.get(f"/sessions/{session_id}")
        assert durable.status_code == 200
        assert durable.json()["status"] == "OPENING_STATEMENTS"
        assert durable.json()["last_sequence"] == 4
        assert durable.json()["floor"]["current_grant"] is not None

    captured = capsys.readouterr()
    combined = captured.out + captured.err
    assert "periodic-send-private-sentinel" not in combined
    assert "periodic-projection-private-sentinel" not in combined
    assert "Task exception was never retrieved" not in combined


def test_websocket_delivers_committed_phase_deadline_event(
    migrated_database: TemporaryDatabaseContext,
) -> None:
    application = _application(
        migrated_database,
        settings=Settings(
            environment=Environment.TEST,
            cors_origins=(TRUSTED_ORIGIN,),
            session_phase_durations=SessionPhaseDurations(
                preparation_seconds=1,
                opening_statements_seconds=30,
                exploration_seconds=30,
                conflict_and_evaluation_seconds=30,
                convergence_seconds=30,
                final_summary_seconds=30,
            ),
        ),
    )
    with _client(application) as client:
        _register(client, "ws_phase_owner")
        snapshot = _create_session(client)
        session_id = str(snapshot["id"])
        action_id = uuid4()

        with client.websocket_connect(
            _ws_path(session_id),
            headers={"Origin": TRUSTED_ORIGIN},
        ) as websocket:
            websocket.send_json(_start_command(session_id, action_id))
            started = websocket.receive_json()
            assert started["schema_version"] == 2
            assert started["sequence"] == 2
            assert started["action_id"] == str(action_id)
            assert started["payload"]["trigger"] == "USER_START"
            assert started["payload"]["status"] == "PREPARATION"
            assert started["payload"]["phase_started_at"] is not None
            assert started["payload"]["phase_deadline_at"] is not None

            advanced = websocket.receive_json()
            assert advanced["schema_version"] == 2
            assert advanced["type"] == "session.state_changed"
            assert advanced["sequence"] == 3
            assert advanced["action_id"] is None
            assert advanced["payload"]["trigger"] == "PHASE_DEADLINE"
            assert advanced["payload"]["previous_status"] == "PREPARATION"
            assert advanced["payload"]["status"] == "OPENING_STATEMENTS"
            assert (
                advanced["payload"]["phase_started_at"]
                == started["payload"]["phase_deadline_at"]
            )

        restored = client.get(f"/sessions/{session_id}")
        assert restored.status_code == 200
        assert restored.json()["status"] == "OPENING_STATEMENTS"
        assert restored.json()["last_sequence"] == 3


def test_websocket_projects_floor_grant_and_recovers_it_from_snapshot_and_catchup(
    migrated_database: TemporaryDatabaseContext,
) -> None:
    application = _application(
        migrated_database,
        settings=Settings(
            environment=Environment.TEST,
            cors_origins=(TRUSTED_ORIGIN,),
            session_phase_durations=SessionPhaseDurations(
                preparation_seconds=1,
                opening_statements_seconds=30,
                exploration_seconds=30,
                conflict_and_evaluation_seconds=30,
                convergence_seconds=30,
                final_summary_seconds=30,
            ),
        ),
    )
    with _client(application) as client:
        _register(client, "ws_floor_owner")
        created = _create_session(client)
        session_id = str(created["id"])

        with client.websocket_connect(
            _ws_path(session_id),
            headers={"Origin": TRUSTED_ORIGIN},
        ) as websocket:
            websocket.send_json(_start_command(session_id, uuid4()))
            assert websocket.receive_json()["sequence"] == 2
            phase_event = websocket.receive_json()
            assert phase_event["sequence"] == 3
            assert phase_event["payload"]["status"] == "OPENING_STATEMENTS"

            scheduled = asyncio.run(
                _schedule_floor(migrated_database, UUID(session_id)),
                loop_factory=asyncio.SelectorEventLoop,
            )
            assert [(event.sequence, event.event_type) for event in scheduled] == [
                (4, "floor.granted")
            ]
            assert scheduled[0].causation_action_id is not None
            granted = websocket.receive_json()
            assert granted["schema_version"] == 2
            assert granted["type"] == "floor.granted"
            assert granted["sequence"] == 4
            assert granted["action_id"] is None
            assert set(granted["payload"]) == {
                "grant_id",
                "decision_id",
                "participant_id",
                "phase",
                "opportunity_id",
                "reason_code",
                "policy_version",
            }
            assert granted["payload"]["phase"] == "OPENING_STATEMENTS"
            assert granted["payload"]["reason_code"] == "FIRST_OPPORTUNITY"

        snapshot_response = client.get(f"/sessions/{session_id}")
        assert snapshot_response.status_code == 200
        snapshot = snapshot_response.json()
        assert snapshot["last_sequence"] == 4
        assert snapshot["floor"]["current_grant"] == {
            "grant_id": granted["payload"]["grant_id"],
            "participant_id": granted["payload"]["participant_id"],
            "phase": "OPENING_STATEMENTS",
            "reason_code": "FIRST_OPPORTUNITY",
            "granted_at": granted["occurred_at"],
        }
        assert snapshot["floor"]["latest_event"] == {
            "type": "floor.granted",
            "sequence": 4,
            "occurred_at": granted["occurred_at"],
            "phase": "OPENING_STATEMENTS",
            "reason_code": "FIRST_OPPORTUNITY",
            "grant_id": granted["payload"]["grant_id"],
            "participant_id": granted["payload"]["participant_id"],
            "intervention_id": None,
            "intervention_kind": None,
        }
        assert len(snapshot["floor"]["participants"]) == 4

        with client.websocket_connect(
            _ws_path(session_id, after_sequence=3),
            headers={"Origin": TRUSTED_ORIGIN},
        ) as websocket:
            assert websocket.receive_json() == granted

        public_surfaces = (str(granted) + str(snapshot)).lower()
        for forbidden in (
            "private_stance",
            "persona_calibration",
            "policy_weights",
            "hidden_ranking",
            "decision_metadata",
            "score",
            "prompt",
            "provider",
        ):
            assert forbidden not in public_surfaces


def test_websocket_human_submit_is_ordered_recoverable_and_preserves_content(
    migrated_database: TemporaryDatabaseContext,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    async def progression_failure(*_args: object, **_kwargs: object) -> Never:
        raise RuntimeError("progression-private-sentinel")

    monkeypatch.setattr(
        realtime,
        "resume_discussion_progression",
        progression_failure,
        raising=False,
    )
    application = _application(
        migrated_database,
        settings=Settings(
            environment=Environment.TEST,
            cors_origins=(TRUSTED_ORIGIN,),
            session_phase_durations=SessionPhaseDurations(
                preparation_seconds=1,
                opening_statements_seconds=30,
                exploration_seconds=30,
                conflict_and_evaluation_seconds=30,
                convergence_seconds=30,
                final_summary_seconds=30,
            ),
        ),
    )
    with _client(application) as client:
        _register(client, "ws_human_utterance_owner")
        created = _create_session(client)
        session_id = str(created["id"])
        content = "  preserve me exactly  "
        action_id = uuid4()

        with client.websocket_connect(
            _ws_path(session_id),
            headers={"Origin": TRUSTED_ORIGIN},
        ) as websocket:
            websocket.send_json(_start_command(session_id, uuid4()))
            assert websocket.receive_json()["sequence"] == 2
            phase_event = websocket.receive_json()
            assert phase_event["sequence"] == 3
            assert phase_event["payload"]["status"] == "OPENING_STATEMENTS"

            scheduled = asyncio.run(
                _schedule_floor(migrated_database, UUID(session_id)),
                loop_factory=asyncio.SelectorEventLoop,
            )
            human_grant = websocket.receive_json()
            assert human_grant["sequence"] == 4
            assert human_grant["payload"]["participant_id"] == str(
                scheduled[0].payload["participant_id"]
            )

            websocket.send_json(
                _utterance_command(
                    session_id,
                    uuid4(),
                    human_grant["payload"]["grant_id"],
                    "   ",
                )
            )
            rejected = websocket.receive_json()
            _assert_error(
                rejected,
                code="UTTERANCE_REJECTED",
                session_id=session_id,
            )
            assert rejected["error"]["message"] == (
                "You cannot submit an utterance right now."
            )

            websocket.send_json(
                _utterance_command(
                    session_id,
                    action_id,
                    human_grant["payload"]["grant_id"],
                    content,
                )
            )
            utterance = websocket.receive_json()
            released = websocket.receive_json()
            assert [utterance["sequence"], released["sequence"]] == [5, 6]
            assert utterance == {
                "schema_version": 1,
                "type": "participant.utterance.created",
                "session_id": session_id,
                "sequence": 5,
                "occurred_at": utterance["occurred_at"],
                "action_id": str(action_id),
                "payload": {
                    "utterance_id": utterance["payload"]["utterance_id"],
                    "participant_id": human_grant["payload"]["participant_id"],
                    "actor_kind": "HUMAN",
                    "floor_grant_id": human_grant["payload"]["grant_id"],
                    "phase": "OPENING_STATEMENTS",
                    "content": content,
                },
            }
            assert released["schema_version"] == 2
            assert released["type"] == "floor.released"
            assert released["action_id"] == str(action_id)

            websocket.send_json(
                _utterance_command(
                    session_id,
                    action_id,
                    human_grant["payload"]["grant_id"],
                    "different content",
                )
            )
            conflict = websocket.receive_json()
            _assert_error(
                conflict,
                code="ACTION_ID_CONFLICT",
                session_id=session_id,
            )

            websocket.send_json(
                _utterance_command(
                    session_id,
                    uuid4(),
                    human_grant["payload"]["grant_id"],
                    "still open",
                )
            )
            no_floor = websocket.receive_json()
            _assert_error(
                no_floor,
                code="UTTERANCE_REJECTED",
                session_id=session_id,
            )

        transcript = client.get(f"/sessions/{session_id}/utterances")
        assert transcript.status_code == 200
        assert transcript.json()["items"][0]["content"] == content
        assert transcript.json()["items"][0]["action_id"] == str(action_id)

    captured = capsys.readouterr()
    combined = captured.out + captured.err
    assert "progression-private-sentinel" not in combined
    assert "Task exception was never retrieved" not in combined
