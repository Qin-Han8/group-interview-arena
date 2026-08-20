import asyncio
import re
from collections.abc import Callable, Generator
from contextlib import contextmanager
from typing import Never, Protocol, cast
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from httpx import Cookies, Headers, Response
from sqlalchemy import URL
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
from group_interview_arena_api.db.runtime import (
    create_database_engine,
    create_database_session_factory,
    dispose_database_engine,
)
from group_interview_arena_api.identity.cookies import SESSION_COOKIE_NAME
from group_interview_arena_api.modules.discussion_sessions import realtime
from group_interview_arena_api.modules.discussion_sessions.domain import StoredEvent
from group_interview_arena_api.modules.discussion_sessions.service import (
    ActionIdConflictError,
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

            websocket.send_json(command)
            duplicate = websocket.receive_json()
            assert duplicate == accepted

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

            websocket.send_json(command)
            assert websocket.receive_json() == accepted

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
        real_formal_event = realtime._formal_event  # pyright: ignore[reportPrivateUsage]

        def fail_after_commit(_event: StoredEvent) -> Never:
            raise RuntimeError("lost-send-exception-sentinel")

        monkeypatch.setattr(realtime, "_formal_event", fail_after_commit)
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

        monkeypatch.setattr(realtime, "_formal_event", real_formal_event)

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
            websocket.send_json(_abort_command(session_id, action_id))
            assert websocket.receive_json() == recovered


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
