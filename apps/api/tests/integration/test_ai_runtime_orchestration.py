import asyncio
import json
import logging
from collections.abc import Callable, Coroutine
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Protocol, cast
from uuid import UUID, uuid4

import httpx
import pytest
from pydantic import SecretStr
from sqlalchemy import URL, func, select, text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from group_interview_arena_api.core.config import (
    DatabaseSettings,
    ZhipuProviderSettings,
)
from group_interview_arena_api.core.logging import JsonFormatter
from group_interview_arena_api.db import (
    AiUtterance,
    DiscussionEvent,
    DiscussionMemoryRevision,
    DiscussionMemoryState,
    LlmGenerationRequest,
    PersonaPrivateStance,
    QuestionVersion,
    SessionAction,
    SessionParticipant,
    SimulationSession,
    User,
)
from group_interview_arena_api.db.runtime import (
    create_database_engine,
    create_database_session_factory,
    dispose_database_engine,
)
from group_interview_arena_api.modules.ai_runtime import runtime as runtime_module
from group_interview_arena_api.modules.ai_runtime.conversation_context import (
    render_recent_discussion,
)
from group_interview_arena_api.modules.ai_runtime.domain import (
    AiRuntimePersistenceError,
    GenerationContextError,
    GenerationFailureCode,
    GenerationRequestMetadata,
    GenerationRequestMetadataV2,
    GenerationRequestStatus,
    PromptVersionDefinition,
    RequestGenerationCommand,
)
from group_interview_arena_api.modules.ai_runtime.generation import (
    DeterministicGenerationHarness,
    DeterministicGenerationMode,
    ModelInvocationInput,
    RawGenerationSuccess,
    RuntimeGenerationInput,
)
from group_interview_arena_api.modules.ai_runtime.runtime import (
    GenerateAiUtteranceCommand,
    RuntimeGenerationOutcome,
    _load_recent_public_discussion,  # pyright: ignore[reportPrivateUsage]
    generate_ai_utterance,
)
from group_interview_arena_api.modules.ai_runtime.seed import (
    AI_CANDIDATE_TURN_V2,
    AI_CANDIDATE_TURN_V3,
    DISCUSSION_MEMORY_UPDATE_V2,
)
from group_interview_arena_api.modules.ai_runtime.service import (
    claim_generation_request,
    create_generation_request,
    publish_prompt_version,
)
from group_interview_arena_api.modules.discussion_memory.application import (
    DiscussionMemoryPersistenceError,
    MemoryMaintenanceOutcome,
    MemorySemanticProvenance,
    load_discussion_memory_projection,
    load_discussion_memory_projection_at_revision,
    load_public_memory_utterances,
    maintain_discussion_memory,
    rebuild_discussion_memory,
)
from group_interview_arena_api.modules.discussion_memory.derivation import (
    DeterministicFakeMemoryDeriver,
    MemoryDerivationInput,
    MemoryDerivationResult,
    MemoryDerivationUnavailable,
)
from group_interview_arena_api.modules.discussion_memory.domain import (
    AcceptedMemoryRevision,
    DiscussionContextMode,
    DiscussionMemoryProjection,
    MemoryItemKind,
    MemoryItemStatus,
    MemoryPatch,
    MemoryPatchOperation,
    MemoryPolicy,
    StructuredDiscussionMemory,
    replay_memory_revisions,
)
from group_interview_arena_api.modules.discussion_memory.working_context import (
    DiscussionWorkingContextUnavailable,
    build_discussion_working_context,
)
from group_interview_arena_api.modules.discussion_sessions.domain import (
    PhaseDurationPlan,
    SessionCommand,
    SessionStatus,
)
from group_interview_arena_api.modules.discussion_sessions.service import (
    apply_session_command,
    create_session,
    get_session_snapshot,
    reconcile_session_deadline,
)
from group_interview_arena_api.modules.floor_control.domain import (
    FloorDecisionOutcome,
    FloorDecisionRecord,
    FloorPolicyReason,
    FloorReleaseReason,
    GrantFloorCommand,
    ParticipantActorKind,
    ReleaseFloorCommand,
    SafeDecisionMetadata,
)
from group_interview_arena_api.modules.floor_control.service import apply_floor_command
from group_interview_arena_api.modules.question_personas.seed import (
    INTERNAL_VALIDATION_BUNDLE,
    seed_question_persona_foundation,
)
from group_interview_arena_api.providers.zhipu import ZhipuGenerationProvider

pytestmark = pytest.mark.integration
NOW = datetime(2026, 8, 24, 8, 0, tzinfo=UTC)
PROMPT_ID = UUID("32000000-0000-4000-8000-000000000001")
CURRENT_STANCE_SENTINEL = "CURRENT_PRIVATE_STANCE_SENTINEL_P15C"
OTHER_STANCE_SENTINEL = "OTHER_PRIVATE_STANCE_SENTINEL_P15C"
PROVIDER_SECRET_SENTINEL = "PROVIDER_SECRET_SENTINEL_P15C"
COOKIE_SENTINEL = "COOKIE_AUTH_TOKEN_SENTINEL_P15C"
DATABASE_URL_SENTINEL = "DATABASE_URL_SENTINEL_P15C"
RAW_EXCEPTION_SENTINEL = "RAW_EXCEPTION_SENTINEL_P15C"
LATEST_PROMPT_SENTINEL = "LATEST_PROMPT_MUST_NOT_REPLACE_EXACT_VERSION_P15C"
PROMPT_TEMPLATE = """Session: $session_id
Participant: $participant_id
Grant: $floor_grant_id
Phase: $phase
Question: $question_context
Persona: $persona_context
Private stance: $private_stance
Phase instruction: $phase_instruction
"""
PLAN = PhaseDurationPlan.from_seconds(
    {
        SessionStatus.PREPARATION: 1,
        SessionStatus.OPENING_STATEMENTS: 300,
        SessionStatus.EXPLORATION: 300,
        SessionStatus.CONFLICT_AND_EVALUATION: 300,
        SessionStatus.CONVERGENCE: 300,
        SessionStatus.FINAL_SUMMARY: 300,
    }
)


class TemporaryDatabaseContext(Protocol):
    database_name: str
    database_url: URL

    def database_settings(self) -> DatabaseSettings: ...


def run_async[T](operation: Callable[[], Coroutine[Any, Any, T]]) -> T:
    return asyncio.run(operation(), loop_factory=asyncio.SelectorEventLoop)


@dataclass(frozen=True)
class RuntimeContext:
    engine: AsyncEngine
    session_factory: async_sessionmaker[AsyncSession]
    owner_id: UUID
    session_id: UUID
    participants: tuple[SessionParticipant, ...]
    grant_id: UUID


def _prompt() -> PromptVersionDefinition:
    return PromptVersionDefinition(
        id=PROMPT_ID,
        prompt_key="AI_CANDIDATE_TURN",
        version_number=1,
        purpose_code="CANDIDATE_UTTERANCE",
        template_text=PROMPT_TEMPLATE,
        created_at=NOW,
        published_at=NOW,
    )


def _decision(
    *,
    participant_id: UUID,
    expected_last_sequence: int,
) -> FloorDecisionRecord:
    return FloorDecisionRecord(
        decision_id=uuid4(),
        phase=SessionStatus.OPENING_STATEMENTS,
        expected_last_sequence=expected_last_sequence,
        outcome=FloorDecisionOutcome.GRANT,
        selected_participant_id=participant_id,
        opportunity_id=None,
        intervention_kind=None,
        policy_version="v0.1-floor-1",
        primary_reason=FloorPolicyReason.FIRST_OPPORTUNITY,
        supporting_reasons=(FloorPolicyReason.PHASE_MANDATED_TURN,),
        metadata=SafeDecisionMetadata(
            current_phase_grant_count=0,
            first_opportunity_unmet=True,
            previous_owner_was_selected=False,
            consecutive_grant_count=0,
            tie_break_class="SEAT_ORDER",
        ),
    )


@asynccontextmanager
async def _runtime_context(
    temporary_database: TemporaryDatabaseContext,
    *,
    grant_seat_index: int = 1,
):
    engine = create_database_engine(temporary_database.database_settings())
    session_factory = create_database_session_factory(engine)
    try:
        async with session_factory() as session:
            seeded = await session.get(
                QuestionVersion,
                INTERNAL_VALIDATION_BUNDLE.version_id,
            )
        if seeded is None:
            await seed_question_persona_foundation(session_factory)
        owner_id = uuid4()
        async with session_factory() as session:
            async with session.begin():
                session.add(
                    User(
                        id=owner_id,
                        username=f"ai_runtime_c_{owner_id.hex[:10]}",
                        password_hash="test-only-password-hash",
                    )
                )
        async with session_factory() as session:
            await publish_prompt_version(session, _prompt())
        async with session_factory() as session:
            snapshot = await create_session(
                session,
                owner_id=owner_id,
                question_version_id=INTERNAL_VALIDATION_BUNDLE.version_id,
            )
        async with session_factory() as session:
            await apply_session_command(
                session,
                owner_id=owner_id,
                command=SessionCommand(
                    schema_version=1,
                    command_type="session.start",
                    session_id=snapshot.session_id,
                    action_id=uuid4(),
                    payload={},
                ),
                duration_plan=PLAN,
            )
        async with session_factory() as session:
            prepared = await get_session_snapshot(
                session,
                owner_id=owner_id,
                session_id=snapshot.session_id,
            )
        assert prepared.phase_deadline_at is not None
        async with session_factory() as session:
            await reconcile_session_deadline(
                session,
                owner_id=owner_id,
                session_id=snapshot.session_id,
                now=prepared.phase_deadline_at,
            )
        async with session_factory() as session:
            participants = tuple(
                (
                    await session.scalars(
                        select(SessionParticipant)
                        .where(SessionParticipant.session_id == snapshot.session_id)
                        .order_by(SessionParticipant.seat_order)
                    )
                ).all()
            )
        assert len(participants) == 4
        assert participants[1].question_persona_assignment_id is not None
        assert participants[2].question_persona_assignment_id is not None
        async with session_factory() as session:
            async with session.begin():
                current_stance = await session.get(
                    PersonaPrivateStance,
                    participants[1].question_persona_assignment_id,
                )
                other_stance = await session.get(
                    PersonaPrivateStance,
                    participants[2].question_persona_assignment_id,
                )
                assert current_stance is not None and other_stance is not None
                current_stance.initial_position = CURRENT_STANCE_SENTINEL
                other_stance.initial_position = OTHER_STANCE_SENTINEL

        granted_participant = participants[grant_seat_index]
        grant_id = uuid4()
        async with session_factory() as session:
            await apply_floor_command(
                session,
                owner_id=owner_id,
                command=GrantFloorCommand(
                    session_id=snapshot.session_id,
                    action_id=uuid4(),
                    grant_id=grant_id,
                    decision=_decision(
                        participant_id=granted_participant.id,
                        expected_last_sequence=3,
                    ),
                ),
            )
        yield RuntimeContext(
            engine=engine,
            session_factory=session_factory,
            owner_id=owner_id,
            session_id=snapshot.session_id,
            participants=participants,
            grant_id=grant_id,
        )
    finally:
        await dispose_database_engine(engine)


def _command(
    context: RuntimeContext,
    *,
    participant_id: UUID | None = None,
    request_id: UUID | None = None,
    utterance_id: UUID | None = None,
    provider_identifier: str = "local-deterministic-executor",
    model_identifier: str = "p1-5c-harness-v1",
    configuration_version: str = "P1_5C_DETERMINISTIC",
) -> GenerateAiUtteranceCommand:
    return GenerateAiUtteranceCommand(
        generation_request_id=request_id or uuid4(),
        utterance_id=utterance_id or uuid4(),
        session_id=context.session_id,
        participant_id=participant_id or context.participants[1].id,
        floor_grant_id=context.grant_id,
        prompt_version_id=PROMPT_ID,
        provider_identifier=provider_identifier,
        model_identifier=model_identifier,
        request_metadata=GenerationRequestMetadata(
            configuration_version=configuration_version
        ),
        occurred_at=NOW,
    )


async def _append_public_utterance(
    context: RuntimeContext,
    *,
    participant: SessionParticipant,
    actor_kind: ParticipantActorKind,
    content: str,
    event_version: int = 1,
) -> int:
    async with context.session_factory() as session:
        async with session.begin():
            aggregate = await session.get(
                SimulationSession,
                context.session_id,
                with_for_update=True,
            )
            assert aggregate is not None
            aggregate.last_sequence += 1
            action_id = None
            if actor_kind is ParticipantActorKind.HUMAN:
                action_id = uuid4()
                session.add(
                    SessionAction(
                        session_id=context.session_id,
                        action_id=action_id,
                        command_version=1,
                        command_type="participant.utterance.submit",
                        payload_digest=bytes(32),
                        created_at=NOW,
                    )
                )
                await session.flush()
            session.add(
                DiscussionEvent(
                    session_id=context.session_id,
                    sequence=aggregate.last_sequence,
                    event_version=event_version,
                    event_type="participant.utterance.created",
                    causation_action_id=action_id,
                    payload={
                        "utterance_id": str(uuid4()),
                        "participant_id": str(participant.id),
                        "actor_kind": actor_kind.value,
                        "floor_grant_id": str(context.grant_id),
                        "phase": SessionStatus.OPENING_STATEMENTS.value,
                        "content": content,
                    },
                    occurred_at=NOW + timedelta(seconds=aggregate.last_sequence),
                )
            )
            return aggregate.last_sequence


async def _assert_runtime_unchanged(
    context: RuntimeContext,
    before: SimulationSession,
) -> None:
    async with context.session_factory() as session:
        after = await session.get(SimulationSession, context.session_id)
        assert after is not None
        assert after.status == before.status
        assert after.phase_started_at == before.phase_started_at
        assert after.phase_deadline_at == before.phase_deadline_at
        assert after.current_floor_grant_id == before.current_floor_grant_id
        assert after.last_sequence == before.last_sequence


def test_recent_public_discussion_loads_same_session_contiguous_suffix(
    migrated_database: TemporaryDatabaseContext,
) -> None:
    async def exercise() -> None:
        async with _runtime_context(migrated_database) as context:
            for index in range(1, 8):
                participant = (
                    context.participants[0] if index % 2 else context.participants[1]
                )
                actor_kind = (
                    ParticipantActorKind.HUMAN if index % 2 else ParticipantActorKind.AI
                )
                await _append_public_utterance(
                    context,
                    participant=participant,
                    actor_kind=actor_kind,
                    content=f"PUBLIC_{index}",
                )

            async with context.session_factory() as session:
                selected = await _load_recent_public_discussion(
                    session,
                    session_id=context.session_id,
                )

            assert tuple(item.content for item in selected) == (
                "PUBLIC_2",
                "PUBLIC_3",
                "PUBLIC_4",
                "PUBLIC_5",
                "PUBLIC_6",
                "PUBLIC_7",
            )
            assert tuple(item.actor_kind for item in selected) == (
                ParticipantActorKind.AI,
                ParticipantActorKind.HUMAN,
                ParticipantActorKind.AI,
                ParticipantActorKind.HUMAN,
                ParticipantActorKind.AI,
                ParticipantActorKind.HUMAN,
            )
            rendered = render_recent_discussion(selected)
            assert "AI 候选人 2：PUBLIC_2" in rendered
            assert "你：PUBLIC_3" in rendered
            for item in selected:
                assert str(item.participant_id) not in rendered

    run_async(exercise)


def test_v2_runtime_prompt_contains_public_context_and_current_persona_behavior_only(
    migrated_database: TemporaryDatabaseContext,
) -> None:
    async def exercise() -> None:
        pending_private_sentinel = "PENDING_REJECTED_PROVIDER_INTERNAL_R3"
        human_public = "HUMAN_PUBLIC_CONTEXT_R3"
        ai_public = "AI_PUBLIC_CONTEXT_R3"
        captured: list[RuntimeGenerationInput] = []

        async with _runtime_context(migrated_database) as context:
            await _append_public_utterance(
                context,
                participant=context.participants[0],
                actor_kind=ParticipantActorKind.HUMAN,
                content=human_public,
            )
            await _append_public_utterance(
                context,
                participant=context.participants[1],
                actor_kind=ParticipantActorKind.AI,
                content=ai_public,
            )
            async with context.session_factory() as session:
                async with session.begin():
                    aggregate = await session.get(
                        SimulationSession,
                        context.session_id,
                        with_for_update=True,
                    )
                    assert aggregate is not None
                    aggregate.last_sequence += 1
                    session.add(
                        DiscussionEvent(
                            session_id=context.session_id,
                            sequence=aggregate.last_sequence,
                            event_version=1,
                            event_type="provider.internal",
                            causation_action_id=None,
                            payload={"content": pending_private_sentinel},
                            occurred_at=NOW,
                        )
                    )
            async with context.session_factory() as session:
                await publish_prompt_version(session, AI_CANDIDATE_TURN_V2)

            async def executor(
                generation_input: RuntimeGenerationInput,
            ) -> RawGenerationSuccess:
                captured.append(generation_input)
                return RawGenerationSuccess(content="Context-aware contribution.")

            command = _command(context).model_copy(
                update={
                    "prompt_version_id": AI_CANDIDATE_TURN_V2.id,
                    "occurred_at": AI_CANDIDATE_TURN_V2.published_at
                    + timedelta(seconds=1),
                }
            )
            result = await generate_ai_utterance(
                context.session_factory,
                owner_id=context.owner_id,
                command=command,
                executor=executor,
            )

            assert result.outcome is RuntimeGenerationOutcome.COMPLETED
            assert len(captured) == 1
            rendered = captured[0].rendered_prompt
            assert rendered.index(f"你：{human_public}") < rendered.index(
                f"AI 候选人 2：{ai_public}"
            )
            assert "说话有结构，但保持口语讨论，不写成报告。" in rendered
            assert "发言时长：通常发言约 40 秒。" in rendered
            assert CURRENT_STANCE_SENTINEL in rendered
            assert OTHER_STANCE_SENTINEL not in rendered
            assert pending_private_sentinel not in rendered

    run_async(exercise)


def test_malformed_durable_public_fact_fails_closed_before_provider_input(
    migrated_database: TemporaryDatabaseContext,
) -> None:
    async def exercise() -> None:
        async with _runtime_context(migrated_database) as context:
            await _append_public_utterance(
                context,
                participant=context.participants[0],
                actor_kind=ParticipantActorKind.HUMAN,
                content="MALFORMED_VERSION_R3",
                event_version=2,
            )

            async with context.session_factory() as session:
                with pytest.raises(GenerationContextError):
                    await _load_recent_public_discussion(
                        session,
                        session_id=context.session_id,
                    )

    run_async(exercise)


async def _success_replay_and_context_isolation(
    temporary_database: TemporaryDatabaseContext,
) -> None:
    async with _runtime_context(temporary_database) as context:
        captured: list[RuntimeGenerationInput] = []
        async with context.session_factory() as session:
            await publish_prompt_version(
                session,
                PromptVersionDefinition(
                    id=uuid4(),
                    prompt_key="AI_CANDIDATE_TURN",
                    version_number=2,
                    purpose_code="CANDIDATE_UTTERANCE",
                    template_text=LATEST_PROMPT_SENTINEL,
                    created_at=NOW,
                    published_at=NOW,
                ),
            )

        async def executor(
            generation_input: RuntimeGenerationInput,
        ) -> RawGenerationSuccess:
            captured.append(generation_input)
            async with context.session_factory() as session:
                async with session.begin():
                    locked = await session.scalar(
                        select(SimulationSession)
                        .where(SimulationSession.id == context.session_id)
                        .with_for_update(nowait=True)
                    )
                    assert locked is not None
            return RawGenerationSuccess(
                content=("I recommend comparing the hard constraint before choosing.")
            )

        command = _command(context)
        result = await generate_ai_utterance(
            context.session_factory,
            owner_id=context.owner_id,
            command=command,
            executor=executor,
        )
        assert result.outcome is RuntimeGenerationOutcome.COMPLETED
        assert len(captured) == 1
        rendered = captured[0].rendered_prompt
        assert CURRENT_STANCE_SENTINEL in rendered
        assert OTHER_STANCE_SENTINEL not in rendered
        assert LATEST_PROMPT_SENTINEL not in rendered
        assert str(INTERNAL_VALIDATION_BUNDLE.version_id) in rendered
        for forbidden in (
            PROVIDER_SECRET_SENTINEL,
            COOKIE_SENTINEL,
            DATABASE_URL_SENTINEL,
        ):
            assert forbidden not in repr(captured[0])

        async def must_not_run(_: RuntimeGenerationInput) -> RawGenerationSuccess:
            raise AssertionError("completed replay must not execute generation")

        replay = await generate_ai_utterance(
            context.session_factory,
            owner_id=context.owner_id,
            command=command,
            executor=must_not_run,
        )
        assert replay.outcome is RuntimeGenerationOutcome.COMPLETED_REPLAY
        assert replay.utterance_id == command.utterance_id

        async with context.session_factory() as session:
            aggregate = await session.get(SimulationSession, context.session_id)
            assert aggregate is not None
            release_sequence = aggregate.last_sequence
        async with context.session_factory() as session:
            await apply_floor_command(
                session,
                owner_id=context.owner_id,
                command=ReleaseFloorCommand(
                    session_id=context.session_id,
                    action_id=uuid4(),
                    grant_id=context.grant_id,
                    expected_phase=SessionStatus.OPENING_STATEMENTS,
                    expected_last_sequence=release_sequence,
                    reason=FloorReleaseReason.SPEAKER_FINISHED,
                ),
            )
        stale_context_replay = await generate_ai_utterance(
            context.session_factory,
            owner_id=context.owner_id,
            command=command,
            executor=must_not_run,
        )
        assert stale_context_replay.outcome is RuntimeGenerationOutcome.COMPLETED_REPLAY
        assert stale_context_replay.utterance_id == command.utterance_id

        async with context.session_factory() as session:
            request = await session.get(
                LlmGenerationRequest,
                command.generation_request_id,
            )
            utterances = await session.scalar(
                select(func.count()).select_from(AiUtterance)
            )
            assert request is not None and request.status == "COMPLETED"
            assert request.request_metadata == {
                "schema_version": 2,
                "configuration_version": "P1_5C_DETERMINISTIC",
                "context_mode": "MEMORY_WITH_RAW_TAIL",
                "memory_revision": 0,
                "memory_source_through_sequence": 0,
                "context_source_through_sequence": 0,
                "working_context_version": "DISCUSSION_WORKING_CONTEXT_V1",
            }
            assert utterances == 1


def test_runtime_success_replay_context_isolation_and_no_long_row_lock(
    migrated_database: TemporaryDatabaseContext,
    caplog: pytest.LogCaptureFixture,
) -> None:
    run_async(lambda: _success_replay_and_context_isolation(migrated_database))
    assert CURRENT_STANCE_SENTINEL not in caplog.text
    assert OTHER_STANCE_SENTINEL not in caplog.text
    assert LATEST_PROMPT_SENTINEL not in caplog.text


def test_ai_generation_latency_log_contract_is_content_free(
    migrated_database: TemporaryDatabaseContext,
    caplog: pytest.LogCaptureFixture,
) -> None:
    sensitive_values = (
        "AI_UTTERANCE_CONTENT_SENTINEL_P18",
        "PROVIDER_REQUEST_RESPONSE_PAYLOAD_SENTINEL_P18",
        "HIDDEN_CONFLICT_SENTINEL_P18",
        "USER_DRAFT_SENTINEL_P18",
        "PRIVATE_NOTE_SENTINEL_P18",
        "AUTH_SESSION_TOKEN_SENTINEL_P18",
        CURRENT_STANCE_SENTINEL,
        OTHER_STANCE_SENTINEL,
        PROVIDER_SECRET_SENTINEL,
        COOKIE_SENTINEL,
        DATABASE_URL_SENTINEL,
    )

    async def exercise() -> GenerateAiUtteranceCommand:
        async with _runtime_context(migrated_database) as context:
            command = _command(context)

            async def executor(
                generation_input: RuntimeGenerationInput,
            ) -> RawGenerationSuccess:
                assert CURRENT_STANCE_SENTINEL in generation_input.rendered_prompt
                return RawGenerationSuccess(content=" ".join(sensitive_values[:6]))

            result = await generate_ai_utterance(
                context.session_factory,
                owner_id=context.owner_id,
                command=command,
                executor=executor,
            )
            assert result.outcome is RuntimeGenerationOutcome.COMPLETED
            return command

    caplog.set_level(logging.INFO, logger=runtime_module.__name__)
    command = run_async(exercise)
    formatter = JsonFormatter()
    payloads = [
        cast(dict[str, object], json.loads(formatter.format(record)))
        for record in caplog.records
        if record.name == runtime_module.__name__
        and record.__dict__.get("event")
        in {
            "ai.generation.started",
            "ai.provider.completed",
            "ai.utterance.committed",
        }
    ]

    assert [payload["event"] for payload in payloads] == [
        "ai.generation.started",
        "ai.provider.completed",
        "ai.utterance.committed",
    ]
    common_fields = {
        "timestamp",
        "level",
        "event",
        "logger",
        "session_id",
        "generation_request_id",
        "floor_grant_id",
        "participant_id",
    }
    assert set(payloads[0]) == common_fields
    assert set(payloads[1]) == common_fields | {"duration_ms"}
    assert set(payloads[2]) == common_fields | {"duration_ms"}
    for payload in payloads:
        assert payload["level"] == "INFO"
        assert payload["logger"] == runtime_module.__name__
        assert payload["session_id"] == str(command.session_id)
        assert payload["generation_request_id"] == str(command.generation_request_id)
        assert payload["floor_grant_id"] == str(command.floor_grant_id)
        assert payload["participant_id"] == str(command.participant_id)
    for payload in payloads[1:]:
        assert isinstance(payload["duration_ms"], float)
        assert payload["duration_ms"] >= 0

    serialized = "\n".join(json.dumps(payload) for payload in payloads)
    for sensitive in sensitive_values:
        assert sensitive not in serialized


async def _zhipu_mocked_provider_success_and_provenance(
    temporary_database: TemporaryDatabaseContext,
) -> None:
    async with _runtime_context(temporary_database) as context:
        request_count = 0

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal request_count
            request_count += 1
            assert request.headers["Authorization"] == (
                f"Bearer {PROVIDER_SECRET_SENTINEL}"
            )
            return httpx.Response(
                200,
                json={
                    "model": "glm-4.7-flashx",
                    "choices": [
                        {
                            "finish_reason": "stop",
                            "message": {
                                "role": "assistant",
                                "content": "Use the shared criteria to compare options.",
                            },
                        }
                    ],
                },
            )

        provider = ZhipuGenerationProvider(
            ZhipuProviderSettings(
                api_key=SecretStr(PROVIDER_SECRET_SENTINEL),
                model="glm-4.7-flashx",
            ),
            transport=httpx.MockTransport(handler),
        )
        command = _command(
            context,
            provider_identifier="zhipu",
            model_identifier="glm-4.7-flashx",
            configuration_version="ZHIPU_CHAT_DEV_V1",
        )

        result = await generate_ai_utterance(
            context.session_factory,
            owner_id=context.owner_id,
            command=command,
            executor=provider,
        )
        replay = await generate_ai_utterance(
            context.session_factory,
            owner_id=context.owner_id,
            command=command,
            executor=provider,
        )

        assert result.outcome is RuntimeGenerationOutcome.COMPLETED
        assert result.request_status is GenerationRequestStatus.COMPLETED
        assert result.utterance_id == command.utterance_id
        assert replay.outcome is RuntimeGenerationOutcome.COMPLETED_REPLAY
        assert request_count == 1

        async with context.session_factory() as session:
            request = await session.get(
                LlmGenerationRequest,
                command.generation_request_id,
            )
            utterance = await session.get(AiUtterance, command.utterance_id)
            utterance_count = await session.scalar(
                select(func.count()).select_from(AiUtterance)
            )
        assert request is not None
        assert request.status == "COMPLETED"
        assert request.provider_identifier == "zhipu"
        assert request.model_identifier == "glm-4.7-flashx"
        assert request.request_metadata == {
            "schema_version": 2,
            "configuration_version": "ZHIPU_CHAT_DEV_V1",
            "context_mode": "MEMORY_WITH_RAW_TAIL",
            "memory_revision": 0,
            "memory_source_through_sequence": 0,
            "context_source_through_sequence": 0,
            "working_context_version": "DISCUSSION_WORKING_CONTEXT_V1",
        }
        assert utterance is not None
        assert utterance.content == "Use the shared criteria to compare options."
        assert utterance_count == 1
        assert PROVIDER_SECRET_SENTINEL not in repr(request.request_metadata)
        assert PROVIDER_SECRET_SENTINEL not in repr(result)
        assert PROVIDER_SECRET_SENTINEL not in utterance.content


def test_zhipu_mocked_provider_uses_existing_runtime_and_durable_provenance(
    migrated_database: TemporaryDatabaseContext,
    caplog: pytest.LogCaptureFixture,
) -> None:
    run_async(lambda: _zhipu_mocked_provider_success_and_provenance(migrated_database))
    assert PROVIDER_SECRET_SENTINEL not in caplog.text


async def _failures_are_typed_and_isolated(
    temporary_database: TemporaryDatabaseContext,
) -> None:
    async with _runtime_context(temporary_database) as context:
        async with context.session_factory() as session:
            before = await session.get(SimulationSession, context.session_id)
            assert before is not None
            session.expunge(before)

        expected = {
            DeterministicGenerationMode.TIMEOUT: GenerationFailureCode.TIMEOUT,
            DeterministicGenerationMode.PROVIDER_UNAVAILABLE: (
                GenerationFailureCode.PROVIDER_UNAVAILABLE
            ),
            DeterministicGenerationMode.RATE_LIMIT: GenerationFailureCode.RATE_LIMIT,
            DeterministicGenerationMode.INVALID_OUTPUT: (
                GenerationFailureCode.INVALID_OUTPUT
            ),
            DeterministicGenerationMode.PARTIAL_GENERATION: (
                GenerationFailureCode.PARTIAL_GENERATION
            ),
            DeterministicGenerationMode.INTERNAL_FAILURE: (
                GenerationFailureCode.INTERNAL_ERROR
            ),
        }
        for mode, failure_code in expected.items():
            result = await generate_ai_utterance(
                context.session_factory,
                owner_id=context.owner_id,
                command=_command(context),
                executor=DeterministicGenerationHarness(mode),
            )
            assert result.outcome is RuntimeGenerationOutcome.FAILED
            assert result.failure_code is failure_code
            assert result.utterance_id is None

        await _assert_runtime_unchanged(context, before)
        async with context.session_factory() as session:
            assert (
                await session.scalar(select(func.count()).select_from(AiUtterance)) == 0
            )
            stored_codes = set(
                (
                    await session.scalars(
                        select(LlmGenerationRequest.failure_code).where(
                            LlmGenerationRequest.status == "FAILED"
                        )
                    )
                ).all()
            )
            assert stored_codes == {item.value for item in expected.values()}


def test_simulated_failures_are_typed_and_leave_session_floor_unchanged(
    migrated_database: TemporaryDatabaseContext,
) -> None:
    run_async(lambda: _failures_are_typed_and_isolated(migrated_database))


async def _concurrency_and_running_recovery(
    temporary_database: TemporaryDatabaseContext,
) -> None:
    async with _runtime_context(temporary_database) as context:
        entered = asyncio.Event()
        release = asyncio.Event()
        call_count = 0

        async def blocking_executor(
            generation_input: RuntimeGenerationInput,
        ) -> RawGenerationSuccess:
            nonlocal call_count
            call_count += 1
            entered.set()
            await release.wait()
            return RawGenerationSuccess(
                content=f"Only one claimant executed {generation_input.participant_id}."
            )

        command = _command(context)
        winner_task = asyncio.create_task(
            generate_ai_utterance(
                context.session_factory,
                owner_id=context.owner_id,
                command=command,
                executor=blocking_executor,
            )
        )
        await entered.wait()
        loser = await generate_ai_utterance(
            context.session_factory,
            owner_id=context.owner_id,
            command=command,
            executor=blocking_executor,
        )
        assert loser.outcome is RuntimeGenerationOutcome.RECONCILIATION_REQUIRED
        release.set()
        winner = await winner_task
        assert winner.outcome is RuntimeGenerationOutcome.COMPLETED
        assert call_count == 1

        async def must_not_run(_: RuntimeGenerationInput) -> RawGenerationSuccess:
            raise AssertionError("durable completed replay must not execute")

        replay = await generate_ai_utterance(
            context.session_factory,
            owner_id=context.owner_id,
            command=command,
            executor=must_not_run,
        )
        assert replay.outcome is RuntimeGenerationOutcome.COMPLETED_REPLAY

        running_command = _command(context)
        persistence_command = RequestGenerationCommand(
            request_id=running_command.generation_request_id,
            session_id=running_command.session_id,
            participant_id=running_command.participant_id,
            floor_grant_id=running_command.floor_grant_id,
            prompt_version_id=running_command.prompt_version_id,
            provider_identifier=running_command.provider_identifier,
            model_identifier=running_command.model_identifier,
            request_metadata=running_command.request_metadata,
            requested_at=running_command.occurred_at,
        )
        async with context.session_factory() as session:
            await create_generation_request(
                session,
                owner_id=context.owner_id,
                command=persistence_command,
            )
        async with context.session_factory() as session:
            claim = await claim_generation_request(
                session,
                owner_id=context.owner_id,
                command=running_command.start_command(),
            )
            assert claim.claimed is True
        recovery = await generate_ai_utterance(
            context.session_factory,
            owner_id=context.owner_id,
            command=running_command,
            executor=must_not_run,
        )
        assert recovery.outcome is RuntimeGenerationOutcome.RECONCILIATION_REQUIRED


def test_concurrent_exact_callers_have_one_claimant_and_running_is_fail_closed(
    migrated_database: TemporaryDatabaseContext,
) -> None:
    run_async(lambda: _concurrency_and_running_recovery(migrated_database))


async def _same_grant_different_requests_have_one_formal_winner(
    temporary_database: TemporaryDatabaseContext,
) -> None:
    async with _runtime_context(temporary_database) as context:
        both_entered = asyncio.Event()
        release = asyncio.Event()
        entered_count = 0

        async def barrier_executor(
            generation_input: RuntimeGenerationInput,
        ) -> RawGenerationSuccess:
            nonlocal entered_count
            entered_count += 1
            if entered_count == 2:
                both_entered.set()
            await release.wait()
            return RawGenerationSuccess(
                content=f"Candidate result for {generation_input.generation_request_id}."
            )

        commands = (_command(context), _command(context))
        tasks = [
            asyncio.create_task(
                generate_ai_utterance(
                    context.session_factory,
                    owner_id=context.owner_id,
                    command=command,
                    executor=barrier_executor,
                )
            )
            for command in commands
        ]
        await both_entered.wait()
        release.set()
        results = await asyncio.gather(*tasks)

        assert (
            sum(
                result.outcome is RuntimeGenerationOutcome.COMPLETED
                for result in results
            )
            == 1
        )
        assert (
            sum(
                result.outcome is RuntimeGenerationOutcome.SUPERSEDED
                for result in results
            )
            == 1
        )
        async with context.session_factory() as session:
            assert (
                await session.scalar(select(func.count()).select_from(AiUtterance)) == 1
            )
            assert (
                await session.scalar(
                    select(func.count())
                    .select_from(LlmGenerationRequest)
                    .where(LlmGenerationRequest.status == "COMPLETED")
                )
                == 1
            )


def test_different_request_race_on_same_grant_returns_safe_loser_outcome(
    migrated_database: TemporaryDatabaseContext,
) -> None:
    run_async(
        lambda: _same_grant_different_requests_have_one_formal_winner(migrated_database)
    )


async def _stale_and_privacy_paths(
    temporary_database: TemporaryDatabaseContext,
) -> None:
    async with _runtime_context(temporary_database) as context:
        wrong = await generate_ai_utterance(
            context.session_factory,
            owner_id=context.owner_id,
            command=_command(context, participant_id=context.participants[2].id),
            executor=DeterministicGenerationHarness(
                DeterministicGenerationMode.SUCCESS
            ),
        )
        assert wrong.outcome is RuntimeGenerationOutcome.CONTEXT_REJECTED

        async def releasing_executor(
            _: RuntimeGenerationInput,
        ) -> RawGenerationSuccess:
            async with context.session_factory() as session:
                await apply_floor_command(
                    session,
                    owner_id=context.owner_id,
                    command=ReleaseFloorCommand(
                        session_id=context.session_id,
                        action_id=uuid4(),
                        grant_id=context.grant_id,
                        expected_phase=SessionStatus.OPENING_STATEMENTS,
                        expected_last_sequence=4,
                        reason=FloorReleaseReason.SPEAKER_FINISHED,
                    ),
                )
            return RawGenerationSuccess(content="This late result must be discarded.")

        stale = await generate_ai_utterance(
            context.session_factory,
            owner_id=context.owner_id,
            command=_command(context),
            executor=releasing_executor,
        )
        assert stale.outcome is RuntimeGenerationOutcome.STALE_RESULT
        assert stale.failure_code is GenerationFailureCode.INTERNAL_ERROR
        async with context.session_factory() as session:
            assert (
                await session.scalar(select(func.count()).select_from(AiUtterance)) == 0
            )

    async with _runtime_context(temporary_database, grant_seat_index=0) as human:
        human_result = await generate_ai_utterance(
            human.session_factory,
            owner_id=human.owner_id,
            command=_command(human, participant_id=human.participants[0].id),
            executor=DeterministicGenerationHarness(
                DeterministicGenerationMode.SUCCESS
            ),
        )
        assert human_result.outcome is RuntimeGenerationOutcome.CONTEXT_REJECTED

    async with _runtime_context(temporary_database) as phase_context:

        async def phase_advancing_executor(
            _: RuntimeGenerationInput,
        ) -> RawGenerationSuccess:
            async with phase_context.session_factory() as session:
                snapshot = await get_session_snapshot(
                    session,
                    owner_id=phase_context.owner_id,
                    session_id=phase_context.session_id,
                )
            assert snapshot.phase_deadline_at is not None
            async with phase_context.session_factory() as session:
                await reconcile_session_deadline(
                    session,
                    owner_id=phase_context.owner_id,
                    session_id=phase_context.session_id,
                    now=snapshot.phase_deadline_at,
                )
            return RawGenerationSuccess(content="The phase changed before completion.")

        phase_result = await generate_ai_utterance(
            phase_context.session_factory,
            owner_id=phase_context.owner_id,
            command=_command(phase_context),
            executor=phase_advancing_executor,
        )
        assert phase_result.outcome is RuntimeGenerationOutcome.STALE_RESULT
        async with phase_context.session_factory() as session:
            aggregate = await session.get(SimulationSession, phase_context.session_id)
            assert aggregate is not None
            assert aggregate.status == SessionStatus.EXPLORATION.value
            assert aggregate.current_floor_grant_id is None
            assert (
                await session.scalar(select(func.count()).select_from(AiUtterance)) == 0
            )

    async with _runtime_context(temporary_database) as replaced_context:
        replacement_grant_id = uuid4()

        async def replacing_executor(
            _: RuntimeGenerationInput,
        ) -> RawGenerationSuccess:
            async with replaced_context.session_factory() as session:
                await apply_floor_command(
                    session,
                    owner_id=replaced_context.owner_id,
                    command=ReleaseFloorCommand(
                        session_id=replaced_context.session_id,
                        action_id=uuid4(),
                        grant_id=replaced_context.grant_id,
                        expected_phase=SessionStatus.OPENING_STATEMENTS,
                        expected_last_sequence=4,
                        reason=FloorReleaseReason.SPEAKER_FINISHED,
                    ),
                )
            async with replaced_context.session_factory() as session:
                await apply_floor_command(
                    session,
                    owner_id=replaced_context.owner_id,
                    command=GrantFloorCommand(
                        session_id=replaced_context.session_id,
                        action_id=uuid4(),
                        grant_id=replacement_grant_id,
                        decision=_decision(
                            participant_id=replaced_context.participants[2].id,
                            expected_last_sequence=5,
                        ),
                    ),
                )
            return RawGenerationSuccess(
                content="The old grant was replaced before completion."
            )

        replaced_result = await generate_ai_utterance(
            replaced_context.session_factory,
            owner_id=replaced_context.owner_id,
            command=_command(replaced_context),
            executor=replacing_executor,
        )
        assert replaced_result.outcome is RuntimeGenerationOutcome.STALE_RESULT
        async with replaced_context.session_factory() as session:
            aggregate = await session.get(
                SimulationSession,
                replaced_context.session_id,
            )
            assert aggregate is not None
            assert aggregate.current_floor_grant_id == replacement_grant_id
            assert (
                await session.scalar(select(func.count()).select_from(AiUtterance)) == 0
            )

    async with _runtime_context(temporary_database) as exception_context:

        async def exploding_executor(_: RuntimeGenerationInput) -> RawGenerationSuccess:
            raise RuntimeError(
                " ".join(
                    (
                        RAW_EXCEPTION_SENTINEL,
                        PROVIDER_SECRET_SENTINEL,
                        COOKIE_SENTINEL,
                        DATABASE_URL_SENTINEL,
                    )
                )
            )

        exception_result = await generate_ai_utterance(
            exception_context.session_factory,
            owner_id=exception_context.owner_id,
            command=_command(exception_context),
            executor=exploding_executor,
        )
        assert exception_result.outcome is RuntimeGenerationOutcome.FAILED
        assert exception_result.failure_code is GenerationFailureCode.INTERNAL_ERROR
        safe_result = repr(exception_result)
        for forbidden in (
            RAW_EXCEPTION_SENTINEL,
            PROVIDER_SECRET_SENTINEL,
            COOKIE_SENTINEL,
            DATABASE_URL_SENTINEL,
        ):
            assert forbidden not in safe_result
        async with exception_context.session_factory() as session:
            request = await session.get(
                LlmGenerationRequest,
                exception_result.generation_request_id,
            )
            assert request is not None
            assert request.failure_code == GenerationFailureCode.INTERNAL_ERROR.value
            assert (
                await session.scalar(select(func.count()).select_from(AiUtterance)) == 0
            )


def test_wrong_human_stale_phase_and_raw_exception_paths_fail_closed(
    migrated_database: TemporaryDatabaseContext,
    caplog: pytest.LogCaptureFixture,
) -> None:
    run_async(lambda: _stale_and_privacy_paths(migrated_database))
    logs = caplog.text
    for forbidden in (
        CURRENT_STANCE_SENTINEL,
        OTHER_STANCE_SENTINEL,
        RAW_EXCEPTION_SENTINEL,
        PROVIDER_SECRET_SENTINEL,
        COOKIE_SENTINEL,
        DATABASE_URL_SENTINEL,
        LATEST_PROMPT_SENTINEL,
    ):
        assert forbidden not in logs


async def _make_current_phase_overdue(context: RuntimeContext) -> datetime:
    overdue_at = datetime.now(UTC) - timedelta(seconds=1)
    async with context.session_factory() as session:
        async with session.begin():
            aggregate = await session.scalar(
                select(SimulationSession)
                .where(SimulationSession.id == context.session_id)
                .with_for_update()
            )
            assert aggregate is not None
            assert aggregate.status == SessionStatus.OPENING_STATEMENTS.value
            assert aggregate.current_floor_grant_id == context.grant_id
            aggregate.phase_started_at = overdue_at - timedelta(seconds=300)
            aggregate.phase_deadline_at = overdue_at
    return overdue_at


async def _assert_p1_3_reconciliation_is_authoritative(
    context: RuntimeContext,
) -> None:
    async with context.session_factory() as session:
        aggregate = await session.get(SimulationSession, context.session_id)
        events = tuple(
            (
                await session.scalars(
                    select(DiscussionEvent)
                    .where(
                        DiscussionEvent.session_id == context.session_id,
                        DiscussionEvent.sequence > 4,
                    )
                    .order_by(DiscussionEvent.sequence)
                )
            ).all()
        )
        assert aggregate is not None
        assert aggregate.status == SessionStatus.EXPLORATION.value
        assert aggregate.current_floor_grant_id is None
        assert aggregate.last_sequence == 6
        assert tuple((event.sequence, event.event_type) for event in events) == (
            (5, "floor.released"),
            (6, "session.state_changed"),
        )
        assert events[0].payload["reason_code"] == "PHASE_CHANGED"
        assert events[1].payload["trigger"] == "PHASE_DEADLINE"


async def _overdue_deadline_is_reconciled_for_generation_mutations(
    temporary_database: TemporaryDatabaseContext,
) -> None:
    async with _runtime_context(temporary_database) as create_context:
        await _make_current_phase_overdue(create_context)
        command = _command(create_context)
        with pytest.raises(GenerationContextError):
            async with create_context.session_factory() as session:
                await create_generation_request(
                    session,
                    owner_id=create_context.owner_id,
                    command=command.request_command(),
                )
        await _assert_p1_3_reconciliation_is_authoritative(create_context)
        async with create_context.session_factory() as session:
            assert (
                await session.get(
                    LlmGenerationRequest,
                    command.generation_request_id,
                )
                is None
            )

    async with _runtime_context(temporary_database) as claim_context:
        command = _command(claim_context)
        async with claim_context.session_factory() as session:
            await create_generation_request(
                session,
                owner_id=claim_context.owner_id,
                command=command.request_command(),
            )
        await _make_current_phase_overdue(claim_context)
        with pytest.raises(GenerationContextError):
            async with claim_context.session_factory() as session:
                await claim_generation_request(
                    session,
                    owner_id=claim_context.owner_id,
                    command=command.start_command(),
                )
        await _assert_p1_3_reconciliation_is_authoritative(claim_context)
        async with claim_context.session_factory() as session:
            request = await session.get(
                LlmGenerationRequest,
                command.generation_request_id,
            )
            assert request is not None
            assert request.status == "REQUESTED"

    async with _runtime_context(temporary_database) as completion_context:
        executor_called = False

        async def overdue_result_executor(
            _: RuntimeGenerationInput,
        ) -> RawGenerationSuccess:
            nonlocal executor_called
            executor_called = True
            await _make_current_phase_overdue(completion_context)
            return RawGenerationSuccess(
                content="This overdue result must not become an utterance."
            )

        command = _command(completion_context)
        result = await generate_ai_utterance(
            completion_context.session_factory,
            owner_id=completion_context.owner_id,
            command=command,
            executor=overdue_result_executor,
        )
        assert executor_called is True
        assert result.outcome is RuntimeGenerationOutcome.STALE_RESULT
        assert result.request_status is GenerationRequestStatus.FAILED
        await _assert_p1_3_reconciliation_is_authoritative(completion_context)
        async with completion_context.session_factory() as session:
            request = await session.get(
                LlmGenerationRequest,
                command.generation_request_id,
            )
            assert request is not None and request.status == "FAILED"
            assert (
                await session.scalar(select(func.count()).select_from(AiUtterance)) == 0
            )


def test_overdue_deadline_is_reconciled_before_generation_mutations(
    migrated_database: TemporaryDatabaseContext,
) -> None:
    run_async(
        lambda: _overdue_deadline_is_reconciled_for_generation_mutations(
            migrated_database
        )
    )


async def _failure_persistence_failure_preserves_running_truth(
    temporary_database: TemporaryDatabaseContext,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fail_persistence(*_: object, **__: object) -> None:
        raise AiRuntimePersistenceError("simulated failure persistence outage")

    monkeypatch.setattr(
        runtime_module,
        "fail_generation_request",
        fail_persistence,
    )

    async with _runtime_context(temporary_database) as typed_context:
        command = _command(typed_context)
        result = await generate_ai_utterance(
            typed_context.session_factory,
            owner_id=typed_context.owner_id,
            command=command,
            executor=DeterministicGenerationHarness(
                DeterministicGenerationMode.TIMEOUT
            ),
        )
        assert result.outcome is RuntimeGenerationOutcome.RECONCILIATION_REQUIRED
        assert result.request_status is not GenerationRequestStatus.FAILED
        async with typed_context.session_factory() as session:
            request = await session.get(
                LlmGenerationRequest,
                command.generation_request_id,
            )
            assert request is not None and request.status == "RUNNING"

    async with _runtime_context(temporary_database) as stale_context:

        async def releasing_executor(
            _: RuntimeGenerationInput,
        ) -> RawGenerationSuccess:
            async with stale_context.session_factory() as session:
                await apply_floor_command(
                    session,
                    owner_id=stale_context.owner_id,
                    command=ReleaseFloorCommand(
                        session_id=stale_context.session_id,
                        action_id=uuid4(),
                        grant_id=stale_context.grant_id,
                        expected_phase=SessionStatus.OPENING_STATEMENTS,
                        expected_last_sequence=4,
                        reason=FloorReleaseReason.SPEAKER_FINISHED,
                    ),
                )
            return RawGenerationSuccess(content="This result is stale.")

        command = _command(stale_context)
        result = await generate_ai_utterance(
            stale_context.session_factory,
            owner_id=stale_context.owner_id,
            command=command,
            executor=releasing_executor,
        )
        assert result.outcome is RuntimeGenerationOutcome.RECONCILIATION_REQUIRED
        assert result.request_status is not GenerationRequestStatus.FAILED
        async with stale_context.session_factory() as session:
            request = await session.get(
                LlmGenerationRequest,
                command.generation_request_id,
            )
            assert request is not None and request.status == "RUNNING"

    async with _runtime_context(temporary_database) as race_context:
        both_entered = asyncio.Event()
        release = asyncio.Event()
        entered_count = 0

        async def barrier_executor(
            generation_input: RuntimeGenerationInput,
        ) -> RawGenerationSuccess:
            nonlocal entered_count
            entered_count += 1
            if entered_count == 2:
                both_entered.set()
            await release.wait()
            return RawGenerationSuccess(
                content=f"Candidate result for {generation_input.generation_request_id}."
            )

        commands = (_command(race_context), _command(race_context))
        tasks = tuple(
            asyncio.create_task(
                generate_ai_utterance(
                    race_context.session_factory,
                    owner_id=race_context.owner_id,
                    command=command,
                    executor=barrier_executor,
                )
            )
            for command in commands
        )
        await both_entered.wait()
        release.set()
        results = await asyncio.gather(*tasks)
        assert {result.outcome for result in results} == {
            RuntimeGenerationOutcome.COMPLETED,
            RuntimeGenerationOutcome.RECONCILIATION_REQUIRED,
        }
        assert all(
            result.request_status is not GenerationRequestStatus.FAILED
            for result in results
        )
        async with race_context.session_factory() as session:
            statuses = tuple(
                (
                    await session.scalars(
                        select(LlmGenerationRequest.status).where(
                            LlmGenerationRequest.id.in_(
                                command.generation_request_id for command in commands
                            )
                        )
                    )
                ).all()
            )
            assert sorted(statuses) == ["COMPLETED", "RUNNING"]


def test_failure_persistence_failure_never_claims_durable_failed(
    migrated_database: TemporaryDatabaseContext,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_async(
        lambda: _failure_persistence_failure_preserves_running_truth(
            migrated_database,
            monkeypatch,
        )
    )


@pytest.mark.parametrize(
    "raw_tail_case",
    ("count", "codepoints", "within_limits"),
)
def test_memory_maintenance_keeps_raw_tail_within_working_context_limits(
    migrated_database: TemporaryDatabaseContext,
    raw_tail_case: str,
) -> None:
    async def exercise() -> None:
        async with _runtime_context(migrated_database) as context:
            if raw_tail_case == "count":
                contents = tuple(f"COUNT_BOUND_{index}" for index in range(7))
                compaction_expected = True
            elif raw_tail_case == "codepoints":
                contents = ("A" * 2_100, "B" * 2_100)
                compaction_expected = True
            else:
                contents = tuple(f"LAZY_BOUND_{index}" for index in range(6))
                compaction_expected = False
            policy = MemoryPolicy()
            for index, content in enumerate(contents):
                participant = context.participants[index % len(context.participants)]
                await _append_public_utterance(
                    context,
                    participant=participant,
                    actor_kind=(
                        ParticipantActorKind.HUMAN
                        if participant.seat_order == 1
                        else ParticipantActorKind.AI
                    ),
                    content=content,
                )

            async with context.session_factory() as session:
                history = await load_public_memory_utterances(
                    session,
                    session_id=context.session_id,
                )
            if compaction_expected:
                with pytest.raises(DiscussionWorkingContextUnavailable):
                    build_discussion_working_context(
                        projection=DiscussionMemoryProjection.empty(),
                        complete_public_history=history,
                        phase=SessionStatus.OPENING_STATEMENTS.value,
                        now=NOW,
                        phase_deadline_at=None,
                        policy=policy,
                    )

            class EmptyPatchDeriver:
                def derive(
                    self,
                    _value: MemoryDerivationInput,
                ) -> MemoryDerivationResult:
                    return MemoryDerivationResult(patches=())

            result = await maintain_discussion_memory(
                context.session_factory,
                session_id=context.session_id,
                deriver=EmptyPatchDeriver(),
                provenance=MemorySemanticProvenance(),
                policy=policy,
                now=NOW,
            )
            assert result.outcome is (
                MemoryMaintenanceOutcome.UPDATED
                if compaction_expected
                else MemoryMaintenanceOutcome.NOOP_BELOW_HIGH_WATERMARK
            )
            assert result.compaction_triggered is compaction_expected

            working_context = build_discussion_working_context(
                projection=result.projection,
                complete_public_history=history,
                phase=SessionStatus.OPENING_STATEMENTS.value,
                now=NOW,
                phase_deadline_at=None,
                policy=policy,
            )
            assert (
                len(working_context.recent_public_utterances)
                <= policy.recent_raw_max_utterances
            )
            assert (
                sum(
                    len(item.content)
                    for item in working_context.recent_public_utterances
                )
                <= policy.recent_raw_max_codepoints
            )

    run_async(exercise)


async def _memory_replay_rebuild_and_privacy_proof(
    temporary_database: TemporaryDatabaseContext,
) -> None:
    async with _runtime_context(temporary_database) as context:
        async with context.session_factory() as session:
            async with session.begin():
                question = await session.get(
                    QuestionVersion, INTERNAL_VALIDATION_BUNDLE.version_id
                )
                assert question is not None
                question.reference_dimensions = [{"value": "REFERENCE_SENTINEL_P16B"}]
                question.hidden_conflicts = [{"value": "HIDDEN_SENTINEL_P16B"}]
                question.acceptable_outcome_patterns = [
                    {"value": "EVALUATOR_SENTINEL_P16B"}
                ]
        for index in range(3):
            await _append_public_utterance(
                context,
                participant=context.participants[index],
                actor_kind=(
                    ParticipantActorKind.HUMAN
                    if index == 0
                    else ParticipantActorKind.AI
                ),
                content=f"PUBLIC_EVIDENCE_{index}",
            )
        async with context.session_factory() as session:
            before = tuple(
                (row.sequence, row.event_type, dict(row.payload))
                for row in (
                    await session.scalars(
                        select(DiscussionEvent)
                        .where(DiscussionEvent.session_id == context.session_id)
                        .order_by(DiscussionEvent.sequence)
                    )
                ).all()
            )

        captured: list[MemoryDerivationInput] = []

        class CapturingDeriver:
            def derive(self, value: MemoryDerivationInput) -> MemoryDerivationResult:
                captured.append(value)
                return DeterministicFakeMemoryDeriver().derive(value)

        policy = MemoryPolicy(high_watermark_utterances=3, low_watermark_utterances=1)
        first = await maintain_discussion_memory(
            context.session_factory,
            session_id=context.session_id,
            deriver=CapturingDeriver(),
            provenance=MemorySemanticProvenance(),
            policy=policy,
            now=NOW,
        )
        assert first.outcome is MemoryMaintenanceOutcome.UPDATED
        assert len(captured) == 1
        privacy_surface = captured[0].model_dump_json()
        for sentinel in (
            CURRENT_STANCE_SENTINEL,
            OTHER_STANCE_SENTINEL,
            "REFERENCE_SENTINEL_P16B",
            "HIDDEN_SENTINEL_P16B",
            "EVALUATOR_SENTINEL_P16B",
            PROVIDER_SECRET_SENTINEL,
        ):
            assert sentinel not in privacy_surface

        second = await maintain_discussion_memory(
            context.session_factory,
            session_id=context.session_id,
            deriver=CapturingDeriver(),
            provenance=MemorySemanticProvenance(),
            policy=policy,
            now=NOW,
        )
        assert second.outcome is MemoryMaintenanceOutcome.NOOP_BELOW_HIGH_WATERMARK
        assert len(captured) == 1

        async with context.session_factory() as session:
            state = await session.get(DiscussionMemoryState, context.session_id)
            revisions = tuple(
                (
                    await session.scalars(
                        select(DiscussionMemoryRevision)
                        .where(
                            DiscussionMemoryRevision.session_id == context.session_id
                        )
                        .order_by(DiscussionMemoryRevision.revision)
                    )
                ).all()
            )
        assert state is not None and len(revisions) == 1
        accepted = tuple(
            AcceptedMemoryRevision(
                revision=row.revision,
                base_revision=row.base_revision,
                source_from_sequence=row.source_from_sequence,
                source_through_sequence=row.source_through_sequence,
                schema_version=row.schema_version,
                derivation_version=row.derivation_version,
                projection_version=row.projection_version,
                patches=tuple(MemoryPatch.model_validate(item) for item in row.patches),
            )
            for row in revisions
        )
        replayed = replay_memory_revisions(
            session_id=context.session_id, revisions=accepted
        )
        assert replayed.state == StructuredDiscussionMemory.model_validate(
            state.structured_state
        )
        persisted_surface = repr((state.structured_state, revisions[0].patches))
        assert CURRENT_STANCE_SENTINEL not in persisted_surface
        assert "HIDDEN_SENTINEL_P16B" not in persisted_surface

        rebuilt = await rebuild_discussion_memory(
            context.session_factory,
            session_id=context.session_id,
            deriver=DeterministicFakeMemoryDeriver(),
            provenance=MemorySemanticProvenance(),
            derivation_version="discussion-memory-derivation/v2",
            policy=policy,
            now=NOW + timedelta(seconds=1),
        )
        assert rebuilt.outcome is MemoryMaintenanceOutcome.UPDATED
        assert rebuilt.projection.revision == 2
        assert rebuilt.projection.source_through_sequence == before[-1][0]
        assert (
            rebuilt.projection.source_through_sequence
            >= first.projection.source_through_sequence
        )
        async with context.session_factory() as session:
            after = tuple(
                (row.sequence, row.event_type, dict(row.payload))
                for row in (
                    await session.scalars(
                        select(DiscussionEvent)
                        .where(DiscussionEvent.session_id == context.session_id)
                        .order_by(DiscussionEvent.sequence)
                    )
                ).all()
            )
            chain = tuple(
                (
                    await session.scalars(
                        select(DiscussionMemoryRevision)
                        .where(
                            DiscussionMemoryRevision.session_id == context.session_id
                        )
                        .order_by(DiscussionMemoryRevision.revision)
                    )
                ).all()
            )
            rebuilt_state = await session.get(DiscussionMemoryState, context.session_id)
        assert after == before
        assert [(item.base_revision, item.revision) for item in chain] == [
            (0, 1),
            (1, 2),
        ]
        assert chain[1].derivation_version == "discussion-memory-derivation/v2"
        assert rebuilt_state is not None
        rebuilt_replay = replay_memory_revisions(
            session_id=context.session_id,
            revisions=tuple(
                AcceptedMemoryRevision(
                    revision=row.revision,
                    base_revision=row.base_revision,
                    source_from_sequence=row.source_from_sequence,
                    source_through_sequence=row.source_through_sequence,
                    schema_version=row.schema_version,
                    derivation_version=row.derivation_version,
                    projection_version=row.projection_version,
                    patches=tuple(
                        MemoryPatch.model_validate(item) for item in row.patches
                    ),
                )
                for row in chain
            ),
        )
        assert rebuilt_replay.revision == rebuilt_state.revision == 2
        assert rebuilt_replay.state == StructuredDiscussionMemory.model_validate(
            rebuilt_state.structured_state
        )


def test_memory_replay_rebuild_and_privacy_are_evidence_preserving(
    migrated_database: TemporaryDatabaseContext,
) -> None:
    run_async(lambda: _memory_replay_rebuild_and_privacy_proof(migrated_database))


async def _maintain_and_rebuild_use_frozen_v1_projection_semantics(
    temporary_database: TemporaryDatabaseContext,
) -> None:
    async with _runtime_context(temporary_database) as context:
        for index in range(3):
            await _append_public_utterance(
                context,
                participant=context.participants[1],
                actor_kind=ParticipantActorKind.AI,
                content=f"FROZEN_V1_INITIAL_{index}",
            )

        class AddProposal:
            def derive(self, value: MemoryDerivationInput) -> MemoryDerivationResult:
                return MemoryDerivationResult(
                    patches=(
                        MemoryPatch(
                            operation=MemoryPatchOperation.ADD,
                            kind=MemoryItemKind.PROPOSAL,
                            canonical_text="方案 A",
                            source_sequences=(value.utterances[0].sequence,),
                        ),
                    )
                )

        caller_policy = MemoryPolicy(
            high_watermark_utterances=3,
            low_watermark_utterances=1,
            max_terminal_items=0,
        )
        first = await maintain_discussion_memory(
            context.session_factory,
            session_id=context.session_id,
            deriver=AddProposal(),
            provenance=MemorySemanticProvenance(),
            policy=caller_policy,
            now=NOW,
        )
        assert first.outcome is MemoryMaintenanceOutcome.UPDATED
        for index in range(3):
            await _append_public_utterance(
                context,
                participant=context.participants[1],
                actor_kind=ParticipantActorKind.AI,
                content=f"FROZEN_V1_NEXT_{index}",
            )

        class SupersedeActiveProposal:
            def __init__(self, text: str) -> None:
                self.text = text

            def derive(self, value: MemoryDerivationInput) -> MemoryDerivationResult:
                target = next(
                    item
                    for item in value.previous_memory.state.proposals
                    if item.status is MemoryItemStatus.ACTIVE
                )
                return MemoryDerivationResult(
                    patches=(
                        MemoryPatch(
                            operation=MemoryPatchOperation.SUPERSEDE,
                            kind=MemoryItemKind.PROPOSAL,
                            target_memory_item_id=target.memory_item_id,
                            canonical_text=self.text,
                            source_sequences=(value.utterances[0].sequence,),
                        ),
                    )
                )

        second = await maintain_discussion_memory(
            context.session_factory,
            session_id=context.session_id,
            deriver=SupersedeActiveProposal("方案 B"),
            provenance=MemorySemanticProvenance(),
            policy=caller_policy,
            now=NOW + timedelta(seconds=1),
        )
        assert second.outcome is MemoryMaintenanceOutcome.UPDATED
        assert [item.status for item in second.projection.state.proposals] == [
            MemoryItemStatus.SUPERSEDED,
            MemoryItemStatus.ACTIVE,
        ]
        rebuilt = await rebuild_discussion_memory(
            context.session_factory,
            session_id=context.session_id,
            deriver=SupersedeActiveProposal("方案 C"),
            provenance=MemorySemanticProvenance(),
            derivation_version="discussion-memory-derivation/frozen-v1",
            policy=caller_policy,
            now=NOW + timedelta(seconds=2),
        )
        assert rebuilt.outcome is MemoryMaintenanceOutcome.UPDATED
        assert [item.status for item in rebuilt.projection.state.proposals] == [
            MemoryItemStatus.SUPERSEDED,
            MemoryItemStatus.SUPERSEDED,
            MemoryItemStatus.ACTIVE,
        ]
        async with context.session_factory() as session:
            rows = tuple(
                (
                    await session.scalars(
                        select(DiscussionMemoryRevision)
                        .where(
                            DiscussionMemoryRevision.session_id == context.session_id
                        )
                        .order_by(DiscussionMemoryRevision.revision)
                    )
                ).all()
            )
            state = await session.get(DiscussionMemoryState, context.session_id)
        assert state is not None
        replayed = replay_memory_revisions(
            session_id=context.session_id,
            revisions=_accepted_memory_revisions(rows),
        )
        assert replayed.source_through_sequence == state.source_through_sequence
        assert replayed.state == StructuredDiscussionMemory.model_validate(
            state.structured_state
        )


def test_maintain_and_rebuild_accept_v1_only_with_frozen_projection_semantics(
    migrated_database: TemporaryDatabaseContext,
) -> None:
    run_async(
        lambda: _maintain_and_rebuild_use_frozen_v1_projection_semantics(
            migrated_database
        )
    )


async def _memory_bootstrap_cas_proof(
    temporary_database: TemporaryDatabaseContext,
) -> None:
    async with _runtime_context(temporary_database) as context:
        for index in range(3):
            await _append_public_utterance(
                context,
                participant=context.participants[index],
                actor_kind=(
                    ParticipantActorKind.HUMAN
                    if index == 0
                    else ParticipantActorKind.AI
                ),
                content=f"CAS_PUBLIC_{index}",
            )
        both_read = asyncio.Event()
        release = asyncio.Event()
        entered = 0

        class BarrierDeriver:
            async def derive(
                self, value: MemoryDerivationInput
            ) -> MemoryDerivationResult:
                nonlocal entered
                entered += 1
                if entered == 2:
                    both_read.set()
                await release.wait()
                return DeterministicFakeMemoryDeriver().derive(value)

        policy = MemoryPolicy(high_watermark_utterances=3, low_watermark_utterances=1)
        calls = tuple(
            asyncio.create_task(
                maintain_discussion_memory(
                    context.session_factory,
                    session_id=context.session_id,
                    deriver=BarrierDeriver(),
                    provenance=MemorySemanticProvenance(),
                    policy=policy,
                    now=NOW,
                )
            )
            for _ in range(2)
        )
        await both_read.wait()
        release.set()
        results = await asyncio.gather(*calls)
        assert {item.outcome for item in results} == {
            MemoryMaintenanceOutcome.UPDATED,
            MemoryMaintenanceOutcome.CAS_CONFLICT,
        }
        async with context.session_factory() as session:
            state = await session.get(DiscussionMemoryState, context.session_id)
            revisions = tuple(
                (
                    await session.scalars(
                        select(DiscussionMemoryRevision).where(
                            DiscussionMemoryRevision.session_id == context.session_id
                        )
                    )
                ).all()
            )
        assert state is not None and state.revision == 1
        assert len(revisions) == 1
        assert (revisions[0].base_revision, revisions[0].revision) == (0, 1)


def test_memory_bootstrap_cas_has_one_atomic_winner(
    migrated_database: TemporaryDatabaseContext,
) -> None:
    run_async(lambda: _memory_bootstrap_cas_proof(migrated_database))


async def _non_race_integrity_failure_is_not_cas(
    temporary_database: TemporaryDatabaseContext,
    *,
    rebuild: bool,
) -> None:
    async with _runtime_context(temporary_database) as context:
        for index in range(3):
            await _append_public_utterance(
                context,
                participant=context.participants[1],
                actor_kind=ParticipantActorKind.AI,
                content=f"NON_RACE_INTEGRITY_{index}",
            )
        invalid_fk_provenance = MemorySemanticProvenance(
            prompt_version_id=uuid4(),
            provider_identifier="test-provider",
            model_identifier="test-model",
            configuration_version="TEST_CONFIG",
        )
        with pytest.raises(DiscussionMemoryPersistenceError):
            if rebuild:
                await rebuild_discussion_memory(
                    context.session_factory,
                    session_id=context.session_id,
                    deriver=DeterministicFakeMemoryDeriver(),
                    provenance=invalid_fk_provenance,
                    derivation_version="discussion-memory-derivation/integrity-test",
                    policy=MemoryPolicy(
                        high_watermark_utterances=3,
                        low_watermark_utterances=1,
                    ),
                    now=NOW,
                )
            else:
                await maintain_discussion_memory(
                    context.session_factory,
                    session_id=context.session_id,
                    deriver=DeterministicFakeMemoryDeriver(),
                    provenance=invalid_fk_provenance,
                    policy=MemoryPolicy(
                        high_watermark_utterances=3,
                        low_watermark_utterances=1,
                    ),
                    now=NOW,
                )
        async with context.session_factory() as session:
            state = await session.get(DiscussionMemoryState, context.session_id)
            revision_count = await session.scalar(
                select(func.count())
                .select_from(DiscussionMemoryRevision)
                .where(DiscussionMemoryRevision.session_id == context.session_id)
            )
        assert state is None
        assert revision_count == 0


@pytest.mark.parametrize("rebuild", [False, True], ids=["maintain", "rebuild"])
def test_non_race_integrity_failure_surfaces_as_persistence_error(
    migrated_database: TemporaryDatabaseContext,
    rebuild: bool,
) -> None:
    run_async(
        lambda: _non_race_integrity_failure_is_not_cas(
            migrated_database,
            rebuild=rebuild,
        )
    )


async def _working_context_fallback_provenance_proof(
    temporary_database: TemporaryDatabaseContext,
) -> None:
    async with _runtime_context(temporary_database) as context:
        for index in range(12):
            await _append_public_utterance(
                context,
                participant=context.participants[1],
                actor_kind=ParticipantActorKind.AI,
                content=f"BOUNDED_FALLBACK_{index}",
            )
        calls = 0

        async def provider(_input: RuntimeGenerationInput) -> RawGenerationSuccess:
            nonlocal calls
            calls += 1
            return RawGenerationSuccess(content="safe fallback response")

        command = _command(context)
        result = await generate_ai_utterance(
            context.session_factory,
            owner_id=context.owner_id,
            command=command,
            executor=provider,
        )
        assert result.outcome is RuntimeGenerationOutcome.COMPLETED
        assert calls == 1
        async with context.session_factory() as session:
            request = await session.get(
                LlmGenerationRequest, command.generation_request_id
            )
        assert request is not None
        assert request.request_metadata == {
            "schema_version": 2,
            "configuration_version": "P1_5C_DETERMINISTIC",
            "working_context_version": "DISCUSSION_WORKING_CONTEXT_V1",
            "context_mode": "SAFE_RAW_FALLBACK",
            "memory_revision": 0,
            "memory_source_through_sequence": 0,
            "context_source_through_sequence": 16,
        }


def test_derivation_failure_uses_complete_bounded_raw_fallback_with_v2_provenance(
    migrated_database: TemporaryDatabaseContext,
) -> None:
    run_async(lambda: _working_context_fallback_provenance_proof(migrated_database))


async def _unsafe_context_rejects_without_provider(
    temporary_database: TemporaryDatabaseContext,
) -> None:
    async with _runtime_context(temporary_database) as context:
        for index in range(13):
            await _append_public_utterance(
                context,
                participant=context.participants[1],
                actor_kind=ParticipantActorKind.AI,
                content=f"UNSAFE_OVERFLOW_{index}",
            )
        calls = 0

        async def provider(_input: RuntimeGenerationInput) -> RawGenerationSuccess:
            nonlocal calls
            calls += 1
            return RawGenerationSuccess(content="must not run")

        command = _command(context)
        result = await generate_ai_utterance(
            context.session_factory,
            owner_id=context.owner_id,
            command=command,
            executor=provider,
        )
        assert result.outcome is RuntimeGenerationOutcome.CONTEXT_REJECTED
        assert calls == 0
        async with context.session_factory() as session:
            assert (
                await session.get(LlmGenerationRequest, command.generation_request_id)
                is None
            )


def test_uncoverable_context_fails_safely_before_provider_or_request(
    migrated_database: TemporaryDatabaseContext,
) -> None:
    run_async(lambda: _unsafe_context_rejects_without_provider(migrated_database))


async def _stale_memory_complete_tail_continues_normally(
    temporary_database: TemporaryDatabaseContext,
) -> None:
    async with _runtime_context(temporary_database) as context:
        for index in range(3):
            await _append_public_utterance(
                context,
                participant=context.participants[index],
                actor_kind=(
                    ParticipantActorKind.HUMAN
                    if index == 0
                    else ParticipantActorKind.AI
                ),
                content=f"COMPACTED_{index}",
            )
        compacted = await maintain_discussion_memory(
            context.session_factory,
            session_id=context.session_id,
            deriver=DeterministicFakeMemoryDeriver(),
            provenance=MemorySemanticProvenance(),
            policy=MemoryPolicy(
                high_watermark_utterances=3, low_watermark_utterances=1
            ),
            now=NOW,
        )
        assert compacted.outcome is MemoryMaintenanceOutcome.UPDATED
        for index in range(2):
            await _append_public_utterance(
                context,
                participant=context.participants[1],
                actor_kind=ParticipantActorKind.AI,
                content=f"RAW_TAIL_{index}",
            )

        async def provider(_input: RuntimeGenerationInput) -> RawGenerationSuccess:
            return RawGenerationSuccess(content="memory plus complete tail")

        command = _command(context)
        result = await generate_ai_utterance(
            context.session_factory,
            owner_id=context.owner_id,
            command=command,
            executor=provider,
        )
        assert result.outcome is RuntimeGenerationOutcome.COMPLETED
        async with context.session_factory() as session:
            request = await session.get(
                LlmGenerationRequest, command.generation_request_id
            )
        assert request is not None
        assert request.request_metadata["context_mode"] == "MEMORY_WITH_RAW_TAIL"
        assert request.request_metadata["memory_revision"] == 1
        assert request.request_metadata["memory_source_through_sequence"] == 6
        assert request.request_metadata["context_source_through_sequence"] == 9


def test_stale_memory_plus_complete_raw_tail_continues_without_semantic_call(
    migrated_database: TemporaryDatabaseContext,
) -> None:
    run_async(lambda: _stale_memory_complete_tail_continues_normally(migrated_database))


async def _historical_memory_integrity_tampering_fails_closed(
    temporary_database: TemporaryDatabaseContext,
    *,
    tamper_kind: str,
) -> None:
    async with _runtime_context(temporary_database) as context:
        integrity_time = DISCUSSION_MEMORY_UPDATE_V2.published_at + timedelta(seconds=1)
        async with context.session_factory() as session:
            await publish_prompt_version(session, AI_CANDIDATE_TURN_V3)
            await publish_prompt_version(session, DISCUSSION_MEMORY_UPDATE_V2)

        for index in range(3):
            await _append_public_utterance(
                context,
                participant=context.participants[1],
                actor_kind=ParticipantActorKind.AI,
                content=f"P1_6E_REPLAY_EVIDENCE_{index}",
            )
        maintained = await maintain_discussion_memory(
            context.session_factory,
            session_id=context.session_id,
            deriver=DeterministicFakeMemoryDeriver(),
            provenance=MemorySemanticProvenance(
                prompt_version_id=DISCUSSION_MEMORY_UPDATE_V2.id,
                provider_identifier="p1-6e-memory-provider",
                model_identifier="p1-6e-memory-model",
                configuration_version="P1_6E_MEMORY",
            ),
            policy=MemoryPolicy(
                high_watermark_utterances=3,
                low_watermark_utterances=1,
            ),
            now=integrity_time,
        )
        assert maintained.outcome is MemoryMaintenanceOutcome.UPDATED

        metadata = GenerationRequestMetadataV2(
            configuration_version="P1_5C_DETERMINISTIC",
            working_context_version="DISCUSSION_WORKING_CONTEXT_V1",
            context_mode=DiscussionContextMode.MEMORY_WITH_RAW_TAIL,
            memory_revision=maintained.projection.revision,
            memory_source_through_sequence=(
                maintained.projection.source_through_sequence
            ),
            context_source_through_sequence=(
                maintained.projection.source_through_sequence
            ),
        )
        command = _command(context).model_copy(
            update={
                "prompt_version_id": AI_CANDIDATE_TURN_V3.id,
                "occurred_at": integrity_time,
            }
        )
        async with context.session_factory() as session:
            await create_generation_request(
                session,
                owner_id=context.owner_id,
                command=command.request_command(metadata),
            )

        async with context.session_factory() as session:
            async with session.begin():
                journal = await session.scalar(
                    select(DiscussionMemoryRevision).where(
                        DiscussionMemoryRevision.session_id == context.session_id,
                        DiscussionMemoryRevision.revision
                        == maintained.projection.revision,
                    )
                )
                assert journal is not None
                if tamper_kind == "digest":
                    digest = bytearray(journal.derivation_input_digest)
                    digest[0] ^= 1
                    journal.derivation_input_digest = bytes(digest)
                elif tamper_kind == "schema":
                    journal.schema_version = 2
                elif tamper_kind == "wrong_semantic_prompt":
                    journal.prompt_version_id = AI_CANDIDATE_TURN_V3.id
                elif tamper_kind == "partial_semantic_provenance":
                    await session.execute(
                        text(
                            "ALTER TABLE discussion_memory_revisions DROP CONSTRAINT "
                            "ck_discussion_memory_revisions_semantic_provenance_grou_2d56"
                        )
                    )
                    journal.provider_identifier = None
                else:
                    raise AssertionError(f"unexpected tamper kind: {tamper_kind}")

        async def snapshot_runtime_state() -> tuple[object, ...]:
            async with context.session_factory() as session:
                aggregate = await session.get(SimulationSession, context.session_id)
                request = await session.get(
                    LlmGenerationRequest,
                    command.generation_request_id,
                )
                state = await session.get(DiscussionMemoryState, context.session_id)
                journal = await session.scalar(
                    select(DiscussionMemoryRevision).where(
                        DiscussionMemoryRevision.session_id == context.session_id,
                        DiscussionMemoryRevision.revision
                        == maintained.projection.revision,
                    )
                )
                event_count = await session.scalar(
                    select(func.count())
                    .select_from(DiscussionEvent)
                    .where(DiscussionEvent.session_id == context.session_id)
                )
                utterance_count = await session.scalar(
                    select(func.count())
                    .select_from(AiUtterance)
                    .where(AiUtterance.session_id == context.session_id)
                )
                journal_count = await session.scalar(
                    select(func.count())
                    .select_from(DiscussionMemoryRevision)
                    .where(DiscussionMemoryRevision.session_id == context.session_id)
                )
            assert aggregate is not None
            assert request is not None
            assert state is not None
            assert journal is not None
            return (
                aggregate.status,
                aggregate.phase_started_at,
                aggregate.phase_deadline_at,
                aggregate.current_floor_grant_id,
                aggregate.last_sequence,
                request.status,
                request.requested_at,
                request.started_at,
                request.completed_at,
                request.failed_at,
                request.failure_code,
                json.dumps(request.request_metadata, sort_keys=True),
                state.revision,
                state.source_through_sequence,
                state.schema_version,
                state.derivation_version,
                state.projection_version,
                json.dumps(state.structured_state, sort_keys=True),
                journal.revision,
                journal.base_revision,
                journal.schema_version,
                journal.derivation_version,
                journal.projection_version,
                journal.derivation_input_digest,
                journal.prompt_version_id,
                journal.provider_identifier,
                journal.model_identifier,
                journal.configuration_version,
                journal_count,
                event_count,
                utterance_count,
            )

        before_recovery = await snapshot_runtime_state()
        direct_replay_error: DiscussionMemoryPersistenceError | None = None
        async with context.session_factory() as session:
            try:
                await load_discussion_memory_projection_at_revision(
                    session,
                    session_id=context.session_id,
                    revision=maintained.projection.revision,
                )
            except DiscussionMemoryPersistenceError as error:
                direct_replay_error = error

        provider_calls: list[RuntimeGenerationInput] = []

        async def must_not_run(
            generation_input: RuntimeGenerationInput,
        ) -> RawGenerationSuccess:
            provider_calls.append(generation_input)
            return RawGenerationSuccess(content="historical integrity was bypassed")

        result = await generate_ai_utterance(
            context.session_factory,
            owner_id=context.owner_id,
            command=command,
            executor=must_not_run,
        )
        after_recovery = await snapshot_runtime_state()

        assert direct_replay_error is not None
        assert result.outcome is RuntimeGenerationOutcome.INTERNAL_ERROR
        assert provider_calls == []
        assert after_recovery == before_recovery


@pytest.mark.parametrize(
    "tamper_kind",
    (
        "digest",
        "schema",
        "wrong_semantic_prompt",
        "partial_semantic_provenance",
    ),
)
def test_historical_memory_integrity_tampering_rejects_direct_and_recovery_use(
    migrated_database: TemporaryDatabaseContext,
    tamper_kind: str,
) -> None:
    run_async(
        lambda: _historical_memory_integrity_tampering_fails_closed(
            migrated_database,
            tamper_kind=tamper_kind,
        )
    )


async def _durable_v2_requested_memory_context_is_recovered_exactly(
    temporary_database: TemporaryDatabaseContext,
) -> None:
    async with _runtime_context(temporary_database) as context:
        async with context.session_factory() as session:
            await publish_prompt_version(session, AI_CANDIDATE_TURN_V3)
        for index in range(3):
            await _append_public_utterance(
                context,
                participant=context.participants[1],
                actor_kind=ParticipantActorKind.AI,
                content=f"RECOVERY_ORIGINAL_MEMORY_{index}",
            )
        policy = MemoryPolicy(high_watermark_utterances=3, low_watermark_utterances=1)
        original = await maintain_discussion_memory(
            context.session_factory,
            session_id=context.session_id,
            deriver=DeterministicFakeMemoryDeriver(),
            provenance=MemorySemanticProvenance(),
            policy=policy,
            now=NOW,
        )
        assert original.outcome is MemoryMaintenanceOutcome.UPDATED
        original_tail_sequence = await _append_public_utterance(
            context,
            participant=context.participants[0],
            actor_kind=ParticipantActorKind.HUMAN,
            content="RECOVERY_ORIGINAL_RAW_TAIL",
        )
        metadata = GenerationRequestMetadataV2(
            configuration_version="P1_5C_DETERMINISTIC",
            working_context_version="DISCUSSION_WORKING_CONTEXT_V1",
            context_mode=DiscussionContextMode.MEMORY_WITH_RAW_TAIL,
            memory_revision=original.projection.revision,
            memory_source_through_sequence=(
                original.projection.source_through_sequence
            ),
            context_source_through_sequence=original_tail_sequence,
        )
        command = _command(context).model_copy(
            update={
                "prompt_version_id": AI_CANDIDATE_TURN_V3.id,
                "occurred_at": AI_CANDIDATE_TURN_V3.published_at + timedelta(seconds=1),
            }
        )
        async with context.session_factory() as session:
            await create_generation_request(
                session,
                owner_id=context.owner_id,
                command=command.request_command(metadata),
            )

        for index in range(3):
            await _append_public_utterance(
                context,
                participant=context.participants[1],
                actor_kind=ParticipantActorKind.AI,
                content=f"RECOVERY_NEWER_MEMORY_{index}",
            )
        advanced = await maintain_discussion_memory(
            context.session_factory,
            session_id=context.session_id,
            deriver=DeterministicFakeMemoryDeriver(),
            provenance=MemorySemanticProvenance(),
            policy=policy,
            now=NOW + timedelta(seconds=1),
        )
        assert advanced.outcome is MemoryMaintenanceOutcome.UPDATED
        assert advanced.projection.revision > original.projection.revision

        captured: list[RuntimeGenerationInput] = []

        async def provider(
            generation_input: RuntimeGenerationInput,
        ) -> RawGenerationSuccess:
            captured.append(generation_input)
            return RawGenerationSuccess(content="exact memory recovery")

        result = await generate_ai_utterance(
            context.session_factory,
            owner_id=context.owner_id,
            command=command,
            executor=provider,
        )
        assert result.outcome is RuntimeGenerationOutcome.COMPLETED
        assert len(captured) == 1
        rendered = captured[0].rendered_prompt
        assert "RECOVERY_ORIGINAL_MEMORY_0" in rendered
        assert "RECOVERY_ORIGINAL_RAW_TAIL" in rendered
        assert "RECOVERY_NEWER_MEMORY_0" not in rendered

        async def must_not_run(
            _generation_input: RuntimeGenerationInput,
        ) -> RawGenerationSuccess:
            raise AssertionError("completed durable replay must not invoke provider")

        replay = await generate_ai_utterance(
            context.session_factory,
            owner_id=context.owner_id,
            command=command,
            executor=must_not_run,
        )
        assert replay.outcome is RuntimeGenerationOutcome.COMPLETED_REPLAY
        async with context.session_factory() as session:
            request = await session.get(
                LlmGenerationRequest, command.generation_request_id
            )
            request_count = await session.scalar(
                select(func.count())
                .select_from(LlmGenerationRequest)
                .where(LlmGenerationRequest.id == command.generation_request_id)
            )
            utterance_count = await session.scalar(
                select(func.count())
                .select_from(AiUtterance)
                .where(
                    AiUtterance.generation_request_id == command.generation_request_id
                )
            )
        assert request is not None
        assert request.request_metadata == metadata.model_dump(mode="json")
        assert request_count == 1
        assert utterance_count == 1


def test_durable_requested_v2_recovers_exact_historical_memory_and_raw_tail(
    migrated_database: TemporaryDatabaseContext,
) -> None:
    run_async(
        lambda: _durable_v2_requested_memory_context_is_recovered_exactly(
            migrated_database
        )
    )


async def _durable_v2_requested_raw_fallback_is_recovered_exactly(
    temporary_database: TemporaryDatabaseContext,
) -> None:
    async with _runtime_context(temporary_database) as context:
        async with context.session_factory() as session:
            await publish_prompt_version(session, AI_CANDIDATE_TURN_V3)
        boundary = 0
        for index in range(5):
            boundary = await _append_public_utterance(
                context,
                participant=context.participants[0],
                actor_kind=ParticipantActorKind.HUMAN,
                content=f"RECOVERY_FALLBACK_ORIGINAL_{index}",
            )
        metadata = GenerationRequestMetadataV2(
            configuration_version="P1_5C_DETERMINISTIC",
            working_context_version="DISCUSSION_WORKING_CONTEXT_V1",
            context_mode=DiscussionContextMode.SAFE_RAW_FALLBACK,
            memory_revision=0,
            memory_source_through_sequence=0,
            context_source_through_sequence=boundary,
        )
        command = _command(context).model_copy(
            update={
                "prompt_version_id": AI_CANDIDATE_TURN_V3.id,
                "occurred_at": AI_CANDIDATE_TURN_V3.published_at + timedelta(seconds=1),
            }
        )
        async with context.session_factory() as session:
            await create_generation_request(
                session,
                owner_id=context.owner_id,
                command=command.request_command(metadata),
            )
        await _append_public_utterance(
            context,
            participant=context.participants[1],
            actor_kind=ParticipantActorKind.AI,
            content="RECOVERY_FALLBACK_NEWER_MUST_BE_EXCLUDED",
        )

        captured: list[RuntimeGenerationInput] = []

        async def provider(
            generation_input: RuntimeGenerationInput,
        ) -> RawGenerationSuccess:
            captured.append(generation_input)
            return RawGenerationSuccess(content="exact raw fallback recovery")

        result = await generate_ai_utterance(
            context.session_factory,
            owner_id=context.owner_id,
            command=command,
            executor=provider,
        )
        assert result.outcome is RuntimeGenerationOutcome.COMPLETED
        assert len(captured) == 1
        rendered = captured[0].rendered_prompt
        assert "RECOVERY_FALLBACK_ORIGINAL_0" in rendered
        assert "RECOVERY_FALLBACK_ORIGINAL_4" in rendered
        assert "RECOVERY_FALLBACK_NEWER_MUST_BE_EXCLUDED" not in rendered
        async with context.session_factory() as session:
            request = await session.get(
                LlmGenerationRequest, command.generation_request_id
            )
        assert request is not None
        assert request.request_metadata == metadata.model_dump(mode="json")


def test_durable_requested_v2_recovers_exact_safe_raw_fallback_boundary(
    migrated_database: TemporaryDatabaseContext,
) -> None:
    run_async(
        lambda: _durable_v2_requested_raw_fallback_is_recovered_exactly(
            migrated_database
        )
    )


async def _mocked_semantic_model_persists_and_feeds_candidate_context(
    temporary_database: TemporaryDatabaseContext,
) -> None:
    async with _runtime_context(temporary_database) as context:
        async with context.session_factory() as session:
            await publish_prompt_version(session, AI_CANDIDATE_TURN_V3)
            await publish_prompt_version(session, DISCUSSION_MEMORY_UPDATE_V2)
        first_sequence = 0
        for index in range(12):
            sequence = await _append_public_utterance(
                context,
                participant=context.participants[index % len(context.participants)],
                actor_kind=(
                    ParticipantActorKind.HUMAN
                    if index % len(context.participants) == 0
                    else ParticipantActorKind.AI
                ),
                content=f"MOCKED_SEMANTIC_PUBLIC_{index}",
            )
            if first_sequence == 0:
                first_sequence = sequence

        class MockedSharedTransport:
            def __init__(self) -> None:
                self.semantic_inputs: list[ModelInvocationInput] = []
                self.candidate_inputs: list[RuntimeGenerationInput] = []

            async def invoke(
                self, invocation: ModelInvocationInput
            ) -> RawGenerationSuccess:
                self.semantic_inputs.append(invocation)
                return RawGenerationSuccess(
                    content=json.dumps(
                        {
                            "patches": [
                                {
                                    "operation": "ADD",
                                    "kind": "PROPOSAL",
                                    "target_memory_item_id": None,
                                    "canonical_text": "MOCKED_SEMANTIC_MEMORY",
                                    "source_sequences": [first_sequence],
                                }
                            ]
                        }
                    )
                )

            async def __call__(
                self, generation_input: RuntimeGenerationInput
            ) -> RawGenerationSuccess:
                self.candidate_inputs.append(generation_input)
                return RawGenerationSuccess(content="mocked semantic candidate")

        transport = MockedSharedTransport()
        command = _command(context).model_copy(
            update={
                "prompt_version_id": AI_CANDIDATE_TURN_V3.id,
                "occurred_at": AI_CANDIDATE_TURN_V3.published_at + timedelta(seconds=2),
            }
        )
        result = await generate_ai_utterance(
            context.session_factory,
            owner_id=context.owner_id,
            command=command,
            executor=transport,
        )
        assert result.outcome is RuntimeGenerationOutcome.COMPLETED
        assert len(transport.semantic_inputs) == 1
        semantic_prompt = transport.semantic_inputs[0].rendered_prompt
        assert '{"patches":[]}' in semantic_prompt
        assert "target_memory_item_id" in semantic_prompt
        assert "source_sequences" in semantic_prompt
        assert "MOCKED_SEMANTIC_PUBLIC_0" in semantic_prompt
        assert len(transport.candidate_inputs) == 1
        assert "MOCKED_SEMANTIC_MEMORY" in transport.candidate_inputs[0].rendered_prompt
        async with context.session_factory() as session:
            state = await session.get(DiscussionMemoryState, context.session_id)
            revision = await session.scalar(
                select(DiscussionMemoryRevision).where(
                    DiscussionMemoryRevision.session_id == context.session_id,
                    DiscussionMemoryRevision.revision == 1,
                )
            )
            request = await session.get(
                LlmGenerationRequest, command.generation_request_id
            )
        assert state is not None
        assert "MOCKED_SEMANTIC_MEMORY" in repr(state.structured_state)
        assert revision is not None
        assert revision.prompt_version_id == DISCUSSION_MEMORY_UPDATE_V2.id
        assert request is not None
        assert request.request_metadata["schema_version"] == 2
        assert request.request_metadata["context_mode"] == "MEMORY_WITH_RAW_TAIL"
        assert request.request_metadata["memory_revision"] == 1


def test_mocked_semantic_model_uses_closed_v2_contract_and_persists_provenance(
    migrated_database: TemporaryDatabaseContext,
) -> None:
    run_async(
        lambda: _mocked_semantic_model_persists_and_feeds_candidate_context(
            migrated_database
        )
    )


async def _malformed_semantic_model_output_uses_safe_raw_fallback(
    temporary_database: TemporaryDatabaseContext,
) -> None:
    async with _runtime_context(temporary_database) as context:
        async with context.session_factory() as session:
            await publish_prompt_version(session, AI_CANDIDATE_TURN_V3)
            await publish_prompt_version(session, DISCUSSION_MEMORY_UPDATE_V2)
        for index in range(12):
            await _append_public_utterance(
                context,
                participant=context.participants[1],
                actor_kind=ParticipantActorKind.AI,
                content=f"MALFORMED_SEMANTIC_PUBLIC_{index}",
            )

        class MalformedSemanticTransport:
            def __init__(self) -> None:
                self.semantic_calls = 0
                self.candidate_inputs: list[RuntimeGenerationInput] = []

            async def invoke(
                self, _invocation: ModelInvocationInput
            ) -> RawGenerationSuccess:
                self.semantic_calls += 1
                return RawGenerationSuccess(content="{not-json")

            async def __call__(
                self, generation_input: RuntimeGenerationInput
            ) -> RawGenerationSuccess:
                self.candidate_inputs.append(generation_input)
                return RawGenerationSuccess(content="safe raw fallback candidate")

        transport = MalformedSemanticTransport()
        command = _command(context).model_copy(
            update={
                "prompt_version_id": AI_CANDIDATE_TURN_V3.id,
                "occurred_at": AI_CANDIDATE_TURN_V3.published_at + timedelta(seconds=2),
            }
        )
        result = await generate_ai_utterance(
            context.session_factory,
            owner_id=context.owner_id,
            command=command,
            executor=transport,
        )
        assert result.outcome is RuntimeGenerationOutcome.COMPLETED
        assert transport.semantic_calls == 1
        assert len(transport.candidate_inputs) == 1
        assert (
            "MALFORMED_SEMANTIC_PUBLIC_0"
            in transport.candidate_inputs[0].rendered_prompt
        )
        async with context.session_factory() as session:
            state = await session.get(DiscussionMemoryState, context.session_id)
            request = await session.get(
                LlmGenerationRequest, command.generation_request_id
            )
        assert state is None
        assert request is not None
        assert request.request_metadata["context_mode"] == "SAFE_RAW_FALLBACK"
        assert request.request_metadata["memory_revision"] == 0


def test_malformed_semantic_model_output_falls_back_safely_without_persistence(
    migrated_database: TemporaryDatabaseContext,
) -> None:
    run_async(
        lambda: _malformed_semantic_model_output_uses_safe_raw_fallback(
            migrated_database
        )
    )


def _bounded_batch_result(value: MemoryDerivationInput) -> MemoryDerivationResult:
    return MemoryDerivationResult(
        patches=(
            MemoryPatch(
                operation=MemoryPatchOperation.ADD,
                kind=MemoryItemKind.PROPOSAL,
                canonical_text=f"bounded batch through {value.utterances[-1].sequence}",
                source_sequences=(
                    value.utterances[0].sequence,
                    value.utterances[-1].sequence,
                ),
            ),
        )
    )


async def _large_backlog_catches_up_in_bounded_batches(
    temporary_database: TemporaryDatabaseContext,
) -> None:
    async with _runtime_context(temporary_database) as context:
        for index in range(100):
            await _append_public_utterance(
                context,
                participant=context.participants[1],
                actor_kind=ParticipantActorKind.AI,
                content=f"LARGE_BACKLOG_{index}",
            )
        batch_sizes: list[int] = []

        class BoundedDeriver:
            def derive(self, value: MemoryDerivationInput) -> MemoryDerivationResult:
                batch_sizes.append(len(value.utterances))
                return _bounded_batch_result(value)

        result = await maintain_discussion_memory(
            context.session_factory,
            session_id=context.session_id,
            deriver=BoundedDeriver(),
            provenance=MemorySemanticProvenance(),
            policy=MemoryPolicy(),
            now=NOW,
        )
        assert result.outcome is MemoryMaintenanceOutcome.UPDATED
        assert batch_sizes == [64, 30]
        async with context.session_factory() as session:
            projection = await load_discussion_memory_projection(
                session, session_id=context.session_id
            )
            history = await load_public_memory_utterances(
                session, session_id=context.session_id
            )
            revisions = tuple(
                (
                    await session.scalars(
                        select(DiscussionMemoryRevision)
                        .where(
                            DiscussionMemoryRevision.session_id == context.session_id
                        )
                        .order_by(DiscussionMemoryRevision.revision)
                    )
                ).all()
            )
        assert [(row.base_revision, row.revision) for row in revisions] == [
            (0, 1),
            (1, 2),
        ]
        assert (
            revisions[0].source_through_sequence + 1
            == revisions[1].source_from_sequence
        )
        working_context = build_discussion_working_context(
            projection=projection,
            complete_public_history=history,
            phase=SessionStatus.OPENING_STATEMENTS.value,
            now=NOW,
            phase_deadline_at=None,
            policy=MemoryPolicy(),
        )
        assert len(working_context.recent_public_utterances) == 6
        assert working_context.context_source_through_sequence == history[-1].sequence


def test_large_backlog_catches_up_in_bounded_contiguous_batches(
    migrated_database: TemporaryDatabaseContext,
) -> None:
    run_async(lambda: _large_backlog_catches_up_in_bounded_batches(migrated_database))


async def _catch_up_derivation_failure_stops_safely(
    temporary_database: TemporaryDatabaseContext,
) -> None:
    async with _runtime_context(temporary_database) as context:
        for index in range(100):
            await _append_public_utterance(
                context,
                participant=context.participants[1],
                actor_kind=ParticipantActorKind.AI,
                content=f"FAILING_BACKLOG_{index}",
            )
        batch_sizes: list[int] = []

        class SecondBatchFails:
            def derive(self, value: MemoryDerivationInput) -> MemoryDerivationResult:
                batch_sizes.append(len(value.utterances))
                if len(batch_sizes) == 2:
                    raise MemoryDerivationUnavailable("second bounded batch failed")
                return _bounded_batch_result(value)

        with pytest.raises(MemoryDerivationUnavailable):
            await maintain_discussion_memory(
                context.session_factory,
                session_id=context.session_id,
                deriver=SecondBatchFails(),
                provenance=MemorySemanticProvenance(),
                policy=MemoryPolicy(),
                now=NOW,
            )
        assert batch_sizes == [64, 30]
        async with context.session_factory() as session:
            state = await session.get(DiscussionMemoryState, context.session_id)
            revision_count = await session.scalar(
                select(func.count())
                .select_from(DiscussionMemoryRevision)
                .where(DiscussionMemoryRevision.session_id == context.session_id)
            )
        assert state is not None and state.revision == 1
        assert revision_count == 1


def test_catch_up_derivation_failure_is_finite_and_preserves_committed_prefix(
    migrated_database: TemporaryDatabaseContext,
) -> None:
    run_async(lambda: _catch_up_derivation_failure_stops_safely(migrated_database))


def _accepted_memory_revisions(
    rows: tuple[DiscussionMemoryRevision, ...],
) -> tuple[AcceptedMemoryRevision, ...]:
    return tuple(
        AcceptedMemoryRevision(
            revision=row.revision,
            base_revision=row.base_revision,
            source_from_sequence=row.source_from_sequence,
            source_through_sequence=row.source_through_sequence,
            schema_version=row.schema_version,
            derivation_version=row.derivation_version,
            projection_version=row.projection_version,
            patches=tuple(MemoryPatch.model_validate(item) for item in row.patches),
        )
        for row in rows
    )


async def _bounded_semantic_rebuild_proof(
    temporary_database: TemporaryDatabaseContext,
) -> None:
    async with _runtime_context(temporary_database) as context:
        async with context.session_factory() as session:
            await publish_prompt_version(session, DISCUSSION_MEMORY_UPDATE_V2)
        for index in range(100):
            await _append_public_utterance(
                context,
                participant=context.participants[1],
                actor_kind=ParticipantActorKind.AI,
                content=f"REBUILD_LONG_HISTORY_{index}",
            )
        async with context.session_factory() as session:
            before = tuple(
                (
                    row.sequence,
                    row.event_version,
                    row.event_type,
                    dict(row.payload),
                )
                for row in (
                    await session.scalars(
                        select(DiscussionEvent)
                        .where(DiscussionEvent.session_id == context.session_id)
                        .order_by(DiscussionEvent.sequence)
                    )
                ).all()
            )

        batch_sizes: list[int] = []
        previous_revisions: list[int] = []

        class BoundedRebuildDeriver:
            def derive(self, value: MemoryDerivationInput) -> MemoryDerivationResult:
                batch_sizes.append(len(value.utterances))
                previous_revisions.append(value.previous_memory.revision)
                return _bounded_batch_result(value)

        provenance = MemorySemanticProvenance(
            prompt_version_id=DISCUSSION_MEMORY_UPDATE_V2.id,
            provider_identifier="mocked-semantic-provider",
            model_identifier="mocked-semantic-model",
            configuration_version="REBUILD_CONFIG_V2",
        )
        rebuilt = await rebuild_discussion_memory(
            context.session_factory,
            session_id=context.session_id,
            deriver=BoundedRebuildDeriver(),
            provenance=provenance,
            derivation_version="discussion-memory-derivation/rebuild-v2",
            policy=MemoryPolicy(),
            now=NOW,
        )
        assert rebuilt.outcome is MemoryMaintenanceOutcome.UPDATED
        assert batch_sizes == [64, 36]
        assert previous_revisions == [0, 1]

        async with context.session_factory() as session:
            after = tuple(
                (
                    row.sequence,
                    row.event_version,
                    row.event_type,
                    dict(row.payload),
                )
                for row in (
                    await session.scalars(
                        select(DiscussionEvent)
                        .where(DiscussionEvent.session_id == context.session_id)
                        .order_by(DiscussionEvent.sequence)
                    )
                ).all()
            )
            rows = tuple(
                (
                    await session.scalars(
                        select(DiscussionMemoryRevision)
                        .where(
                            DiscussionMemoryRevision.session_id == context.session_id
                        )
                        .order_by(DiscussionMemoryRevision.revision)
                    )
                ).all()
            )
            state = await session.get(DiscussionMemoryState, context.session_id)
        assert after == before
        assert [(row.base_revision, row.revision) for row in rows] == [
            (0, 1),
            (1, 2),
        ]
        assert rows[0].source_through_sequence + 1 == rows[1].source_from_sequence
        assert all(
            row.derivation_version == "discussion-memory-derivation/rebuild-v2"
            and row.prompt_version_id == DISCUSSION_MEMORY_UPDATE_V2.id
            and row.provider_identifier == "mocked-semantic-provider"
            and row.model_identifier == "mocked-semantic-model"
            and row.configuration_version == "REBUILD_CONFIG_V2"
            for row in rows
        )
        assert state is not None
        replayed = replay_memory_revisions(
            session_id=context.session_id,
            revisions=_accepted_memory_revisions(rows),
        )
        assert replayed.revision == state.revision == rebuilt.projection.revision == 2
        assert replayed.source_through_sequence == state.source_through_sequence
        assert replayed.state == StructuredDiscussionMemory.model_validate(
            state.structured_state
        )


def test_semantic_rebuild_over_100_public_utterances_is_bounded_and_replayable(
    migrated_database: TemporaryDatabaseContext,
) -> None:
    run_async(lambda: _bounded_semantic_rebuild_proof(migrated_database))


async def _bounded_semantic_rebuild_later_failure_preserves_prefix(
    temporary_database: TemporaryDatabaseContext,
) -> None:
    async with _runtime_context(temporary_database) as context:
        async with context.session_factory() as session:
            await publish_prompt_version(session, DISCUSSION_MEMORY_UPDATE_V2)
        for index in range(100):
            await _append_public_utterance(
                context,
                participant=context.participants[1],
                actor_kind=ParticipantActorKind.AI,
                content=f"REBUILD_LATER_FAILURE_{index}",
            )
        async with context.session_factory() as session:
            before = tuple(
                (
                    row.sequence,
                    row.event_type,
                    dict(row.payload),
                )
                for row in (
                    await session.scalars(
                        select(DiscussionEvent)
                        .where(DiscussionEvent.session_id == context.session_id)
                        .order_by(DiscussionEvent.sequence)
                    )
                ).all()
            )
        batch_sizes: list[int] = []

        class LaterBatchFails:
            def derive(self, value: MemoryDerivationInput) -> MemoryDerivationResult:
                batch_sizes.append(len(value.utterances))
                if len(batch_sizes) == 2:
                    raise MemoryDerivationUnavailable("later rebuild batch failed")
                return _bounded_batch_result(value)

        with pytest.raises(MemoryDerivationUnavailable):
            await rebuild_discussion_memory(
                context.session_factory,
                session_id=context.session_id,
                deriver=LaterBatchFails(),
                provenance=MemorySemanticProvenance(
                    prompt_version_id=DISCUSSION_MEMORY_UPDATE_V2.id,
                    provider_identifier="mocked-semantic-provider",
                    model_identifier="mocked-semantic-model",
                    configuration_version="REBUILD_FAILURE_CONFIG",
                ),
                derivation_version="discussion-memory-derivation/rebuild-failure",
                policy=MemoryPolicy(),
                now=NOW,
            )
        assert batch_sizes == [64, 36]
        async with context.session_factory() as session:
            after = tuple(
                (
                    row.sequence,
                    row.event_type,
                    dict(row.payload),
                )
                for row in (
                    await session.scalars(
                        select(DiscussionEvent)
                        .where(DiscussionEvent.session_id == context.session_id)
                        .order_by(DiscussionEvent.sequence)
                    )
                ).all()
            )
            rows = tuple(
                (
                    await session.scalars(
                        select(DiscussionMemoryRevision)
                        .where(
                            DiscussionMemoryRevision.session_id == context.session_id
                        )
                        .order_by(DiscussionMemoryRevision.revision)
                    )
                ).all()
            )
            state = await session.get(DiscussionMemoryState, context.session_id)
        assert after == before
        assert len(rows) == 1
        assert state is not None and state.revision == 1
        replayed = replay_memory_revisions(
            session_id=context.session_id,
            revisions=_accepted_memory_revisions(rows),
        )
        assert replayed.state == StructuredDiscussionMemory.model_validate(
            state.structured_state
        )


def test_semantic_rebuild_later_batch_failure_is_finite_and_preserves_prefix(
    migrated_database: TemporaryDatabaseContext,
) -> None:
    run_async(
        lambda: _bounded_semantic_rebuild_later_failure_preserves_prefix(
            migrated_database
        )
    )


async def _bounded_semantic_rebuild_budget_exhaustion_preserves_prefix(
    temporary_database: TemporaryDatabaseContext,
) -> None:
    async with _runtime_context(temporary_database) as context:
        for index in range(100):
            await _append_public_utterance(
                context,
                participant=context.participants[1],
                actor_kind=ParticipantActorKind.AI,
                content=f"REBUILD_BUDGET_{index}",
            )

        class BoundedBudgetDeriver:
            def derive(self, value: MemoryDerivationInput) -> MemoryDerivationResult:
                return _bounded_batch_result(value)

        with pytest.raises(
            DiscussionMemoryPersistenceError, match="rebuild step budget exhausted"
        ):
            await rebuild_discussion_memory(
                context.session_factory,
                session_id=context.session_id,
                deriver=BoundedBudgetDeriver(),
                provenance=MemorySemanticProvenance(),
                derivation_version="discussion-memory-derivation/rebuild-budget",
                policy=MemoryPolicy(max_rebuild_steps=1),
                now=NOW,
            )
        async with context.session_factory() as session:
            state = await session.get(DiscussionMemoryState, context.session_id)
            count = await session.scalar(
                select(func.count())
                .select_from(DiscussionMemoryRevision)
                .where(DiscussionMemoryRevision.session_id == context.session_id)
            )
        assert state is not None and state.revision == 1
        assert count == 1


def test_semantic_rebuild_step_budget_exhaustion_is_finite(
    migrated_database: TemporaryDatabaseContext,
) -> None:
    run_async(
        lambda: _bounded_semantic_rebuild_budget_exhaustion_preserves_prefix(
            migrated_database
        )
    )
