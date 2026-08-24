import asyncio
from collections.abc import Callable, Coroutine
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Protocol
from uuid import UUID, uuid4

import httpx
import pytest
from pydantic import SecretStr
from sqlalchemy import URL, func, select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from group_interview_arena_api.core.config import (
    DatabaseSettings,
    ZhipuProviderSettings,
)
from group_interview_arena_api.db import (
    AiUtterance,
    DiscussionEvent,
    LlmGenerationRequest,
    PersonaPrivateStance,
    QuestionVersion,
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
from group_interview_arena_api.modules.ai_runtime.domain import (
    AiRuntimePersistenceError,
    GenerationContextError,
    GenerationFailureCode,
    GenerationRequestMetadata,
    GenerationRequestStatus,
    PromptVersionDefinition,
    RequestGenerationCommand,
)
from group_interview_arena_api.modules.ai_runtime.generation import (
    DeterministicGenerationHarness,
    DeterministicGenerationMode,
    RawGenerationSuccess,
    RuntimeGenerationInput,
)
from group_interview_arena_api.modules.ai_runtime.runtime import (
    GenerateAiUtteranceCommand,
    RuntimeGenerationOutcome,
    generate_ai_utterance,
)
from group_interview_arena_api.modules.ai_runtime.service import (
    claim_generation_request,
    create_generation_request,
    publish_prompt_version,
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
                "schema_version": 1,
                "configuration_version": "P1_5C_DETERMINISTIC",
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
            "schema_version": 1,
            "configuration_version": "ZHIPU_CHAT_DEV_V1",
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
