import asyncio
from collections import Counter
from collections.abc import Callable, Coroutine
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import UUID, uuid4

import pytest
from sqlalchemy import URL, func, select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from group_interview_arena_api.core.config import DatabaseSettings
from group_interview_arena_api.db import (
    AiUtterance,
    FloorGrant,
    FloorRelease,
    LlmGenerationRequest,
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
from group_interview_arena_api.modules.ai_runtime.continuous import (
    ContinuousAiDriveOutcome,
    drive_continuous_ai,
)
from group_interview_arena_api.modules.ai_runtime.domain import (
    GenerationFailureCode,
    GenerationRequestMetadata,
    GenerationRequestStatus,
    PersistUtteranceCommand,
    PromptVersionDefinition,
)
from group_interview_arena_api.modules.ai_runtime.generation import (
    GenerationProvider,
    RawGenerationFailure,
    RawGenerationSuccess,
    RuntimeGenerationInput,
)
from group_interview_arena_api.modules.ai_runtime.orchestration import (
    SingleAiTurnOutcome,
    derive_automatic_turn_identities,
    drive_single_ai_turn,
)
from group_interview_arena_api.modules.ai_runtime.runtime import (
    GenerateAiUtteranceCommand,
    RuntimeGenerationOutcome,
    generate_ai_utterance,
)
from group_interview_arena_api.modules.ai_runtime.service import (
    complete_generation_request,
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
    ParticipantActorKind,
    ParticipantAvailability,
    ReleaseFloorCommand,
    SafeDecisionMetadata,
)
from group_interview_arena_api.modules.floor_control.scheduler import (
    V0_1_SCHEDULER_POLICY,
)
from group_interview_arena_api.modules.floor_control.service import apply_floor_command
from group_interview_arena_api.modules.question_personas.seed import (
    INTERNAL_VALIDATION_BUNDLE,
    seed_question_persona_foundation,
)

pytestmark = pytest.mark.integration
NOW = datetime(2026, 8, 24, 8, 0, tzinfo=UTC)
PROMPT_ID = UUID("53000000-0000-4000-8000-000000000001")
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
class ContinuousRuntimeContext:
    engine: AsyncEngine
    session_factory: async_sessionmaker[AsyncSession]
    owner_id: UUID
    session_id: UUID
    participants: tuple[SessionParticipant, ...]
    initial_ai_grant_id: UUID


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


async def _grant(
    context: ContinuousRuntimeContext,
    *,
    participant_id: UUID,
) -> UUID:
    async with context.session_factory() as session:
        simulation_session = await session.get(SimulationSession, context.session_id)
        phase_grant_count = int(
            await session.scalar(
                select(func.count())
                .select_from(FloorGrant)
                .where(
                    FloorGrant.session_id == context.session_id,
                    FloorGrant.phase == SessionStatus.OPENING_STATEMENTS,
                )
            )
            or 0
        )
    assert simulation_session is not None
    grant_id = uuid4()
    async with context.session_factory() as session:
        await apply_floor_command(
            session,
            owner_id=context.owner_id,
            command=GrantFloorCommand(
                session_id=context.session_id,
                action_id=uuid4(),
                grant_id=grant_id,
                decision=FloorDecisionRecord(
                    decision_id=uuid4(),
                    phase=SessionStatus.OPENING_STATEMENTS,
                    expected_last_sequence=simulation_session.last_sequence,
                    outcome=FloorDecisionOutcome.GRANT,
                    selected_participant_id=participant_id,
                    opportunity_id=None,
                    intervention_kind=None,
                    policy_version="v0.1-floor-1",
                    primary_reason=FloorPolicyReason.FIRST_OPPORTUNITY,
                    supporting_reasons=(FloorPolicyReason.PHASE_MANDATED_TURN,),
                    metadata=SafeDecisionMetadata(
                        current_phase_grant_count=phase_grant_count,
                        first_opportunity_unmet=True,
                        previous_owner_was_selected=False,
                        consecutive_grant_count=0,
                        tie_break_class="SEAT_ORDER",
                    ),
                ),
            ),
        )
    return grant_id


async def _release(
    context: ContinuousRuntimeContext,
    *,
    grant_id: UUID,
    action_id: UUID,
) -> None:
    async with context.session_factory() as session:
        simulation_session = await session.get(SimulationSession, context.session_id)
    assert simulation_session is not None
    async with context.session_factory() as session:
        await apply_floor_command(
            session,
            owner_id=context.owner_id,
            command=ReleaseFloorCommand(
                session_id=context.session_id,
                action_id=action_id,
                grant_id=grant_id,
                expected_phase=SessionStatus(simulation_session.status),
                expected_last_sequence=simulation_session.last_sequence,
                reason=FloorReleaseReason.SPEAKER_FINISHED,
            ),
        )


@asynccontextmanager
async def _continuous_runtime_context(
    temporary_database: TemporaryDatabaseContext,
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
                        username=f"continuous_runtime_{owner_id.hex[:10]}",
                        password_hash="test-only-password-hash",
                    )
                )
        async with session_factory() as session:
            await publish_prompt_version(session, _prompt())
        async with session_factory() as session:
            created = await create_session(
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
                    session_id=created.session_id,
                    action_id=uuid4(),
                    payload={},
                ),
                duration_plan=PLAN,
            )
        async with session_factory() as session:
            prepared = await get_session_snapshot(
                session,
                owner_id=owner_id,
                session_id=created.session_id,
            )
        assert prepared.phase_deadline_at is not None
        async with session_factory() as session:
            await reconcile_session_deadline(
                session,
                owner_id=owner_id,
                session_id=created.session_id,
                now=prepared.phase_deadline_at,
            )
        async with session_factory() as session:
            participants = tuple(
                (
                    await session.scalars(
                        select(SessionParticipant)
                        .where(SessionParticipant.session_id == created.session_id)
                        .order_by(SessionParticipant.seat_order)
                    )
                ).all()
            )
            third_ai = await session.get(SessionParticipant, participants[3].id)
            assert third_ai is not None
            third_ai.availability = ParticipantAvailability.UNAVAILABLE
            await session.commit()

        provisional = ContinuousRuntimeContext(
            engine=engine,
            session_factory=session_factory,
            owner_id=owner_id,
            session_id=created.session_id,
            participants=participants,
            initial_ai_grant_id=uuid4(),
        )
        human_grant_id = await _grant(provisional, participant_id=participants[0].id)
        await _release(provisional, grant_id=human_grant_id, action_id=uuid4())
        initial_ai_grant_id = await _grant(
            provisional,
            participant_id=participants[1].id,
        )
        yield ContinuousRuntimeContext(
            engine=engine,
            session_factory=session_factory,
            owner_id=owner_id,
            session_id=created.session_id,
            participants=participants,
            initial_ai_grant_id=initial_ai_grant_id,
        )
    finally:
        await dispose_database_engine(engine)


async def _drive(
    context: ContinuousRuntimeContext,
    provider: GenerationProvider,
):
    return await drive_continuous_ai(
        context.session_factory,
        owner_id=context.owner_id,
        session_id=context.session_id,
        provider=provider,
        provider_identifier="local-test-provider",
        model_identifier="continuous-test-model",
        configuration_version="P1_5E_3_TEST",
        scheduling_policy=V0_1_SCHEDULER_POLICY,
    )


async def _complete_and_release_without_scheduling(
    context: ContinuousRuntimeContext,
) -> None:
    identities = derive_automatic_turn_identities(
        session_id=context.session_id,
        floor_grant_id=context.initial_ai_grant_id,
    )
    async with context.session_factory() as session:
        grant = await session.get(FloorGrant, context.initial_ai_grant_id)
    assert grant is not None

    async def setup_provider(_input: RuntimeGenerationInput) -> RawGenerationSuccess:
        return RawGenerationSuccess(content="Durable result before crash E.")

    result = await generate_ai_utterance(
        context.session_factory,
        owner_id=context.owner_id,
        command=GenerateAiUtteranceCommand(
            generation_request_id=identities.generation_request_id,
            utterance_id=identities.utterance_id,
            session_id=context.session_id,
            participant_id=grant.participant_id,
            floor_grant_id=grant.id,
            prompt_version_id=PROMPT_ID,
            provider_identifier="local-test-provider",
            model_identifier="continuous-test-model",
            request_metadata=GenerationRequestMetadata(
                configuration_version="P1_5E_3_TEST"
            ),
            occurred_at=grant.granted_at,
        ),
        executor=setup_provider,
    )
    assert result.outcome is RuntimeGenerationOutcome.COMPLETED
    await _release(
        context,
        grant_id=grant.id,
        action_id=identities.release_action_id,
    )


def test_consecutive_ai_chain_reaches_human_and_replays_without_generation(
    migrated_database: TemporaryDatabaseContext,
) -> None:
    async def exercise() -> None:
        provider_calls: list[UUID] = []

        async def provider(
            generation_input: RuntimeGenerationInput,
        ) -> RawGenerationSuccess:
            provider_calls.append(generation_input.floor_grant_id)
            return RawGenerationSuccess(content=f"AI response {len(provider_calls)}")

        async with _continuous_runtime_context(migrated_database) as context:
            result = await _drive(context, provider)
            async with context.session_factory() as session:
                requests = tuple(
                    (
                        await session.scalars(
                            select(LlmGenerationRequest).where(
                                LlmGenerationRequest.session_id == context.session_id
                            )
                        )
                    ).all()
                )
                utterances = tuple(
                    (
                        await session.scalars(
                            select(AiUtterance).where(
                                AiUtterance.session_id == context.session_id
                            )
                        )
                    ).all()
                )
                releases = tuple(
                    (
                        await session.scalars(
                            select(FloorRelease).where(
                                FloorRelease.grant_id.in_(
                                    request.floor_grant_id for request in requests
                                )
                            )
                        )
                    ).all()
                )
                simulation_session = await session.get(
                    SimulationSession, context.session_id
                )
                assert simulation_session is not None
                current_grant = await session.get(
                    FloorGrant, simulation_session.current_floor_grant_id
                )
                assert current_grant is not None
                current_participant = await session.get(
                    SessionParticipant, current_grant.participant_id
                )

            assert result.outcome is ContinuousAiDriveOutcome.WAITING_FOR_HUMAN
            assert result.automated_ai_turns_advanced == 2
            assert len(provider_calls) == len(set(provider_calls)) == 2
            assert len(requests) == len(utterances) == len(releases) == 2
            assert all(
                request.status == GenerationRequestStatus.COMPLETED
                for request in requests
            )
            assert current_participant is not None
            assert current_participant.actor_kind == ParticipantActorKind.HUMAN

            replay = await _drive(context, provider)
            assert replay.outcome is ContinuousAiDriveOutcome.WAITING_FOR_HUMAN
            assert replay.automated_ai_turns_advanced == 0
            assert len(provider_calls) == 2

    run_async(exercise)


def test_confirmed_failure_releases_once_then_continues_to_new_ai_grant(
    migrated_database: TemporaryDatabaseContext,
) -> None:
    async def exercise() -> None:
        calls = 0

        async def provider(
            _generation_input: RuntimeGenerationInput,
        ) -> RawGenerationFailure | RawGenerationSuccess:
            nonlocal calls
            calls += 1
            if calls == 1:
                return RawGenerationFailure(failure_code=GenerationFailureCode.TIMEOUT)
            return RawGenerationSuccess(content="Independent next AI turn.")

        async with _continuous_runtime_context(migrated_database) as context:
            result = await _drive(context, provider)
            async with context.session_factory() as session:
                requests = tuple(
                    (
                        await session.scalars(
                            select(LlmGenerationRequest)
                            .where(
                                LlmGenerationRequest.session_id == context.session_id
                            )
                            .order_by(LlmGenerationRequest.requested_at)
                        )
                    ).all()
                )
                utterance_count = int(
                    await session.scalar(
                        select(func.count())
                        .select_from(AiUtterance)
                        .where(AiUtterance.session_id == context.session_id)
                    )
                    or 0
                )
                first_release = await session.get(
                    FloorRelease, requests[0].floor_grant_id
                )

            assert result.outcome is ContinuousAiDriveOutcome.WAITING_FOR_HUMAN
            assert result.automated_ai_turns_advanced == 2
            assert calls == 2
            assert len(requests) == 2
            assert requests[0].status == GenerationRequestStatus.FAILED
            assert requests[0].failure_code == GenerationFailureCode.TIMEOUT
            assert requests[1].status == GenerationRequestStatus.COMPLETED
            assert requests[0].floor_grant_id != requests[1].floor_grant_id
            assert utterance_count == 1
            assert first_release is not None
            assert first_release.reason_code == FloorReleaseReason.INTERRUPTED

    run_async(exercise)


def test_post_release_restart_schedules_then_processes_only_new_ai_turn(
    migrated_database: TemporaryDatabaseContext,
) -> None:
    async def exercise() -> None:
        provider_calls: list[UUID] = []

        async def provider(
            generation_input: RuntimeGenerationInput,
        ) -> RawGenerationSuccess:
            provider_calls.append(generation_input.floor_grant_id)
            return RawGenerationSuccess(content="New AI after crash-E recovery.")

        async with _continuous_runtime_context(migrated_database) as context:
            initial_identities = derive_automatic_turn_identities(
                session_id=context.session_id,
                floor_grant_id=context.initial_ai_grant_id,
            )
            await _complete_and_release_without_scheduling(context)
            result = await _drive(context, provider)
            async with context.session_factory() as session:
                initial_schedule_count = int(
                    await session.scalar(
                        select(func.count())
                        .select_from(SessionAction)
                        .where(
                            SessionAction.session_id == context.session_id,
                            SessionAction.action_id
                            == initial_identities.schedule_action_id,
                        )
                    )
                    or 0
                )
                initial_release_count = int(
                    await session.scalar(
                        select(func.count())
                        .select_from(FloorRelease)
                        .where(FloorRelease.grant_id == context.initial_ai_grant_id)
                    )
                    or 0
                )

            assert result.outcome is ContinuousAiDriveOutcome.WAITING_FOR_HUMAN
            assert result.automated_ai_turns_advanced == 1
            assert len(provider_calls) == 1
            assert provider_calls[0] != context.initial_ai_grant_id
            assert initial_schedule_count == initial_release_count == 1

    run_async(exercise)


def test_concurrent_continuous_drives_preserve_one_winner_per_grant(
    migrated_database: TemporaryDatabaseContext,
) -> None:
    async def exercise() -> None:
        provider_calls: Counter[UUID] = Counter()

        async def provider(
            generation_input: RuntimeGenerationInput,
        ) -> RawGenerationSuccess:
            provider_calls[generation_input.floor_grant_id] += 1
            await asyncio.sleep(0.05)
            return RawGenerationSuccess(content="Concurrent continuous winner.")

        async with _continuous_runtime_context(migrated_database) as context:
            results = await asyncio.gather(
                _drive(context, provider),
                _drive(context, provider),
            )
            async with context.session_factory() as session:
                duplicate_requests = tuple(
                    (
                        await session.execute(
                            select(
                                LlmGenerationRequest.floor_grant_id,
                                func.count(LlmGenerationRequest.id),
                            )
                            .where(
                                LlmGenerationRequest.session_id == context.session_id
                            )
                            .group_by(LlmGenerationRequest.floor_grant_id)
                            .having(func.count(LlmGenerationRequest.id) > 1)
                        )
                    ).all()
                )
                duplicate_utterances = tuple(
                    (
                        await session.execute(
                            select(
                                AiUtterance.floor_grant_id, func.count(AiUtterance.id)
                            )
                            .where(AiUtterance.session_id == context.session_id)
                            .group_by(AiUtterance.floor_grant_id)
                            .having(func.count(AiUtterance.id) > 1)
                        )
                    ).all()
                )
                duplicate_releases = tuple(
                    (
                        await session.execute(
                            select(
                                FloorRelease.grant_id, func.count(FloorRelease.grant_id)
                            )
                            .where(FloorRelease.session_id == context.session_id)
                            .group_by(FloorRelease.grant_id)
                            .having(func.count(FloorRelease.grant_id) > 1)
                        )
                    ).all()
                )

            assert provider_calls
            assert all(count == 1 for count in provider_calls.values())
            assert (
                duplicate_requests == duplicate_utterances == duplicate_releases == ()
            )
            assert any(
                result.outcome is ContinuousAiDriveOutcome.WAITING_FOR_HUMAN
                for result in results
            )
            assert all(
                result.outcome
                in {
                    ContinuousAiDriveOutcome.WAITING_FOR_HUMAN,
                    ContinuousAiDriveOutcome.RECONCILIATION_REQUIRED,
                }
                for result in results
            )

    run_async(exercise)


def test_cancellation_terminalizes_running_request_and_reentry_continues(
    migrated_database: TemporaryDatabaseContext,
) -> None:
    async def exercise() -> None:
        started = asyncio.Event()

        async def blocking_provider(
            _generation_input: RuntimeGenerationInput,
        ) -> RawGenerationSuccess:
            started.set()
            await asyncio.Event().wait()
            return RawGenerationSuccess(content="unreachable")

        async with _continuous_runtime_context(migrated_database) as context:
            identities = derive_automatic_turn_identities(
                session_id=context.session_id,
                floor_grant_id=context.initial_ai_grant_id,
            )
            task = asyncio.create_task(_drive(context, blocking_provider))
            await started.wait()
            async with context.session_factory() as session:
                running_request = await session.get(
                    LlmGenerationRequest, identities.generation_request_id
                )
                running_utterance_count = int(
                    await session.scalar(
                        select(func.count())
                        .select_from(AiUtterance)
                        .where(
                            AiUtterance.floor_grant_id == context.initial_ai_grant_id
                        )
                    )
                    or 0
                )
            assert running_request is not None
            assert running_request.status == GenerationRequestStatus.RUNNING
            assert running_utterance_count == 0

            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task

            async with context.session_factory() as session:
                cancelled_request = await session.get(
                    LlmGenerationRequest, identities.generation_request_id
                )
                cancelled_utterance_count = int(
                    await session.scalar(
                        select(func.count())
                        .select_from(AiUtterance)
                        .where(
                            AiUtterance.floor_grant_id == context.initial_ai_grant_id
                        )
                    )
                    or 0
                )
            assert cancelled_request is not None
            assert cancelled_request.status == GenerationRequestStatus.FAILED
            assert (
                cancelled_request.failure_code == GenerationFailureCode.INTERNAL_ERROR
            )
            assert cancelled_utterance_count == 0

            failed_replay_provider_calls = 0

            async def failed_replay_provider(
                _generation_input: RuntimeGenerationInput,
            ) -> RawGenerationSuccess:
                nonlocal failed_replay_provider_calls
                failed_replay_provider_calls += 1
                return RawGenerationSuccess(content="must not run")

            replay = await drive_single_ai_turn(
                context.session_factory,
                owner_id=context.owner_id,
                session_id=context.session_id,
                provider=failed_replay_provider,
                provider_identifier="local-test-provider",
                model_identifier="continuous-test-model",
                configuration_version="P1_5E_3_TEST",
                scheduling_policy=V0_1_SCHEDULER_POLICY,
            )
            assert replay.outcome is SingleAiTurnOutcome.NEXT_AI_GRANTED
            assert replay.runtime_outcome is RuntimeGenerationOutcome.FAILED_REPLAY
            assert replay.failure_code is GenerationFailureCode.INTERNAL_ERROR
            assert failed_replay_provider_calls == 0

            continuation_provider_calls: list[UUID] = []

            async def continuation_provider(
                generation_input: RuntimeGenerationInput,
            ) -> RawGenerationSuccess:
                continuation_provider_calls.append(generation_input.floor_grant_id)
                return RawGenerationSuccess(content="Independent next AI turn.")

            continuation = await _drive(context, continuation_provider)
            async with context.session_factory() as session:
                request_after_reentry = await session.get(
                    LlmGenerationRequest, identities.generation_request_id
                )
                release = await session.get(FloorRelease, context.initial_ai_grant_id)
                initial_request_count = int(
                    await session.scalar(
                        select(func.count())
                        .select_from(LlmGenerationRequest)
                        .where(
                            LlmGenerationRequest.floor_grant_id
                            == context.initial_ai_grant_id
                        )
                    )
                    or 0
                )
                initial_utterance_count = int(
                    await session.scalar(
                        select(func.count())
                        .select_from(AiUtterance)
                        .where(
                            AiUtterance.floor_grant_id == context.initial_ai_grant_id
                        )
                    )
                    or 0
                )
                initial_release_count = int(
                    await session.scalar(
                        select(func.count())
                        .select_from(FloorRelease)
                        .where(FloorRelease.grant_id == context.initial_ai_grant_id)
                    )
                    or 0
                )
                schedule_count = int(
                    await session.scalar(
                        select(func.count())
                        .select_from(SessionAction)
                        .where(
                            SessionAction.session_id == context.session_id,
                            SessionAction.action_id == identities.schedule_action_id,
                        )
                    )
                    or 0
                )

            assert continuation.outcome is ContinuousAiDriveOutcome.WAITING_FOR_HUMAN
            assert continuation.automated_ai_turns_advanced == 1
            assert len(continuation_provider_calls) == 1
            assert continuation_provider_calls[0] != context.initial_ai_grant_id
            assert request_after_reentry is not None
            assert request_after_reentry.status == GenerationRequestStatus.FAILED
            assert (
                request_after_reentry.failure_code
                == GenerationFailureCode.INTERNAL_ERROR
            )
            assert release is not None
            assert release.reason_code == FloorReleaseReason.INTERRUPTED
            assert initial_request_count == initial_release_count == schedule_count == 1
            assert initial_utterance_count == 0

    run_async(exercise)


def test_durable_completion_is_not_overwritten_by_cancellation_cleanup(
    migrated_database: TemporaryDatabaseContext,
) -> None:
    async def exercise() -> None:
        started = asyncio.Event()

        async def blocking_provider(
            _generation_input: RuntimeGenerationInput,
        ) -> RawGenerationSuccess:
            started.set()
            await asyncio.Event().wait()
            return RawGenerationSuccess(content="unreachable")

        async with _continuous_runtime_context(migrated_database) as context:
            identities = derive_automatic_turn_identities(
                session_id=context.session_id,
                floor_grant_id=context.initial_ai_grant_id,
            )
            task = asyncio.create_task(_drive(context, blocking_provider))
            await started.wait()

            async with context.session_factory() as session:
                completed = await complete_generation_request(
                    session,
                    owner_id=context.owner_id,
                    command=PersistUtteranceCommand(
                        utterance_id=identities.utterance_id,
                        session_id=context.session_id,
                        generation_request_id=identities.generation_request_id,
                        content="Concurrent durable completion wins.",
                        persisted_at=datetime.now(UTC),
                    ),
                )
            assert completed.status is GenerationRequestStatus.COMPLETED

            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task

            async with context.session_factory() as session:
                request = await session.get(
                    LlmGenerationRequest, identities.generation_request_id
                )
                utterance_count = int(
                    await session.scalar(
                        select(func.count())
                        .select_from(AiUtterance)
                        .where(
                            AiUtterance.floor_grant_id == context.initial_ai_grant_id
                        )
                    )
                    or 0
                )

            assert request is not None
            assert request.status == GenerationRequestStatus.COMPLETED
            assert request.failure_code is None
            assert utterance_count == 1

    run_async(exercise)
