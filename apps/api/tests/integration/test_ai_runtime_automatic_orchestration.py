import asyncio
from collections.abc import Callable, Coroutine
from contextlib import asynccontextmanager
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from typing import Any, Protocol
from uuid import UUID, uuid4

import pytest
from sqlalchemy import URL, func, select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from group_interview_arena_api.core.config import DatabaseSettings
from group_interview_arena_api.db import (
    AiUtterance,
    FloorDecision,
    FloorGrant,
    FloorIntervention,
    FloorRelease,
    LlmGenerationRequest,
    PersonaPrivateStance,
    PromptVersion,
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
from group_interview_arena_api.modules.ai_runtime import (
    orchestration as orchestration_module,
)
from group_interview_arena_api.modules.ai_runtime.domain import (
    GenerationFailureCode,
    GenerationRequestMetadata,
    GenerationRequestStatus,
    PromptVersionDefinition,
    RequestGenerationCommand,
    StartGenerationCommand,
)
from group_interview_arena_api.modules.ai_runtime.generation import (
    RawGenerationFailure,
    RawGenerationSuccess,
    RuntimeGenerationInput,
)
from group_interview_arena_api.modules.ai_runtime.orchestration import (
    SingleAiTurnOutcome,
    SingleAiTurnResult,
    derive_automatic_turn_identities,
    drive_single_ai_turn,
    has_resumable_ai_work,
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
    SessionPersistenceError,
    apply_session_command,
    create_session,
    get_session_snapshot,
    reconcile_session_deadline,
)
from group_interview_arena_api.modules.floor_control import (
    progression as floor_progression_module,
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
PROMPT_ID = UUID("52000000-0000-4000-8000-000000000001")
CURRENT_STANCE_SENTINEL = "CURRENT_STANCE_ONLY_P1_5E_2"
OTHER_STANCE_SENTINEL = "OTHER_STANCE_FORBIDDEN_P1_5E_2"
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


def test_automatic_turn_identity_bytes_remain_frozen() -> None:
    identities = derive_automatic_turn_identities(
        session_id=UUID("10000000-0000-4000-8000-000000000001"),
        floor_grant_id=UUID("30000000-0000-4000-8000-000000000003"),
    )

    assert identities.model_dump(mode="json") == {
        "generation_request_id": "c1ba2871-1469-4c67-8b30-082fb9af6ee8",
        "utterance_id": "b5b42d93-053d-4165-92fc-eca968e2e6fb",
        "release_action_id": "5b6ffd0d-6e33-416c-a9e1-fc7551ebcbab",
        "schedule_action_id": "640c57e0-dcb2-442c-a75f-a3892603a14e",
        "decision_id": "1090ad6e-48d2-4ab7-acd0-185fbd5d2cf3",
        "next_floor_grant_id": "f6ca0e88-9f5c-4e15-9e15-9bb506306fe5",
        "intervention_id": "ed991e77-7543-4437-80c8-5a1092f0ddc4",
    }


class TemporaryDatabaseContext(Protocol):
    database_name: str
    database_url: URL

    def database_settings(self) -> DatabaseSettings: ...


def run_async[T](operation: Callable[[], Coroutine[Any, Any, T]]) -> T:
    return asyncio.run(operation(), loop_factory=asyncio.SelectorEventLoop)


@dataclass(frozen=True)
class AutomaticRuntimeContext:
    engine: AsyncEngine
    session_factory: async_sessionmaker[AsyncSession]
    owner_id: UUID
    session_id: UUID
    participants: tuple[SessionParticipant, ...]
    grant_id: UUID | None


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


def _grant_decision(
    *, participant_id: UUID, expected_last_sequence: int
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
async def _automatic_runtime_context(
    temporary_database: TemporaryDatabaseContext,
    *,
    grant_seat_index: int | None,
    with_prompt: bool = True,
    floor_enabled: bool = True,
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
                        username=f"automatic_runtime_{owner_id.hex[:10]}",
                        password_hash="test-only-password-hash",
                    )
                )
        if with_prompt:
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
        if floor_enabled:
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
                assert current_stance is not None
                assert other_stance is not None
                current_stance.initial_position = CURRENT_STANCE_SENTINEL
                other_stance.initial_position = OTHER_STANCE_SENTINEL

        grant_id = None
        if grant_seat_index is not None:
            assert floor_enabled
            grant_id = uuid4()
            async with session_factory() as session:
                await apply_floor_command(
                    session,
                    owner_id=owner_id,
                    command=GrantFloorCommand(
                        session_id=created.session_id,
                        action_id=uuid4(),
                        grant_id=grant_id,
                        decision=_grant_decision(
                            participant_id=participants[grant_seat_index].id,
                            expected_last_sequence=3,
                        ),
                    ),
                )

        yield AutomaticRuntimeContext(
            engine=engine,
            session_factory=session_factory,
            owner_id=owner_id,
            session_id=created.session_id,
            participants=participants,
            grant_id=grant_id,
        )
    finally:
        await dispose_database_engine(engine)


async def _mutation_counts(context: AutomaticRuntimeContext) -> tuple[int, ...]:
    async with context.session_factory() as session:
        counts: list[int] = []
        for model in (
            LlmGenerationRequest,
            AiUtterance,
            FloorRelease,
            SessionAction,
        ):
            count = await session.scalar(select(func.count()).select_from(model))
            counts.append(int(count or 0))
        return tuple(counts)


def test_human_floor_and_unrelated_no_current_state_are_safe_noops(
    migrated_database: TemporaryDatabaseContext,
) -> None:
    async def exercise() -> None:
        provider_calls = 0

        async def provider(_input: object) -> RawGenerationSuccess:
            nonlocal provider_calls
            provider_calls += 1
            return RawGenerationSuccess(content="must not run")

        async with _automatic_runtime_context(
            migrated_database,
            grant_seat_index=0,
        ) as human_context:
            before = await _mutation_counts(human_context)
            result = await drive_single_ai_turn(
                human_context.session_factory,
                owner_id=human_context.owner_id,
                session_id=human_context.session_id,
                provider=provider,
                provider_identifier="local-test-provider",
                model_identifier="automatic-test-model",
                configuration_version="P1_5E_2_TEST",
                scheduling_policy=V0_1_SCHEDULER_POLICY,
            )
            assert result.outcome is SingleAiTurnOutcome.WAITING_FOR_HUMAN
            assert await _mutation_counts(human_context) == before

        async with _automatic_runtime_context(
            migrated_database,
            grant_seat_index=None,
            with_prompt=False,
        ) as no_current_context:
            before = await _mutation_counts(no_current_context)
            result = await drive_single_ai_turn(
                no_current_context.session_factory,
                owner_id=no_current_context.owner_id,
                session_id=no_current_context.session_id,
                provider=provider,
                provider_identifier="local-test-provider",
                model_identifier="automatic-test-model",
                configuration_version="P1_5E_2_TEST",
                scheduling_policy=V0_1_SCHEDULER_POLICY,
            )
            assert result.outcome is SingleAiTurnOutcome.NO_CURRENT_WORK
            assert await _mutation_counts(no_current_context) == before

        async with _automatic_runtime_context(
            migrated_database,
            grant_seat_index=None,
            with_prompt=False,
            floor_enabled=False,
        ) as non_floor_context:
            before = await _mutation_counts(non_floor_context)
            result = await drive_single_ai_turn(
                non_floor_context.session_factory,
                owner_id=non_floor_context.owner_id,
                session_id=non_floor_context.session_id,
                provider=provider,
                provider_identifier="local-test-provider",
                model_identifier="automatic-test-model",
                configuration_version="P1_5E_2_TEST",
                scheduling_policy=V0_1_SCHEDULER_POLICY,
            )
            assert result.outcome is SingleAiTurnOutcome.NOT_APPLICABLE
            assert await _mutation_counts(non_floor_context) == before

        assert provider_calls == 0

    run_async(exercise)


def test_missing_exact_prompt_stops_before_provider_release_or_scheduler(
    migrated_database: TemporaryDatabaseContext,
) -> None:
    async def exercise() -> None:
        provider_calls = 0

        async def provider(_input: object) -> RawGenerationSuccess:
            nonlocal provider_calls
            provider_calls += 1
            return RawGenerationSuccess(content="must not run")

        async with _automatic_runtime_context(
            migrated_database,
            grant_seat_index=1,
            with_prompt=False,
        ) as context:
            before = await _mutation_counts(context)
            result = await drive_single_ai_turn(
                context.session_factory,
                owner_id=context.owner_id,
                session_id=context.session_id,
                provider=provider,
                provider_identifier="local-test-provider",
                model_identifier="automatic-test-model",
                configuration_version="P1_5E_2_TEST",
                scheduling_policy=V0_1_SCHEDULER_POLICY,
            )
            assert result.outcome is SingleAiTurnOutcome.RECONCILIATION_REQUIRED
            assert await _mutation_counts(context) == before

        assert provider_calls == 0

    run_async(exercise)


def test_crash_a_fresh_success_uses_grant_timestamp_before_exact_release(
    migrated_database: TemporaryDatabaseContext,
) -> None:
    async def exercise() -> None:
        provider_calls = 0

        async def provider(_input: object) -> RawGenerationSuccess:
            nonlocal provider_calls
            provider_calls += 1
            return RawGenerationSuccess(content="Deterministic automatic contribution.")

        async with _automatic_runtime_context(
            migrated_database,
            grant_seat_index=1,
        ) as context:
            assert context.grant_id is not None
            identities = derive_automatic_turn_identities(
                session_id=context.session_id,
                floor_grant_id=context.grant_id,
            )
            result = await drive_single_ai_turn(
                context.session_factory,
                owner_id=context.owner_id,
                session_id=context.session_id,
                provider=provider,
                provider_identifier="local-test-provider",
                model_identifier="automatic-test-model",
                configuration_version="P1_5E_2_TEST",
                scheduling_policy=V0_1_SCHEDULER_POLICY,
            )

            async with context.session_factory() as session:
                simulation_session = await session.get(
                    SimulationSession, context.session_id
                )
                request = await session.get(
                    LlmGenerationRequest, identities.generation_request_id
                )
                utterance = await session.get(AiUtterance, identities.utterance_id)
                release = await session.get(FloorRelease, context.grant_id)
                grant = await session.get(FloorGrant, context.grant_id)

            assert provider_calls == 1
            assert result.runtime_outcome is RuntimeGenerationOutcome.COMPLETED
            assert request is not None
            assert request.status == GenerationRequestStatus.COMPLETED
            assert grant is not None
            assert request.requested_at == grant.granted_at
            assert utterance is not None
            assert utterance.generation_request_id == identities.generation_request_id
            assert release is not None
            assert release.causation_action_id == identities.release_action_id
            assert release.reason_code == FloorReleaseReason.SPEAKER_FINISHED
            assert simulation_session is not None
            assert simulation_session.current_floor_grant_id != context.grant_id

    run_async(exercise)


def test_typed_failure_releases_interrupted_without_utterance(
    migrated_database: TemporaryDatabaseContext,
) -> None:
    async def exercise() -> None:
        provider_calls = 0

        async def provider(_input: object) -> RawGenerationFailure:
            nonlocal provider_calls
            provider_calls += 1
            return RawGenerationFailure(failure_code=GenerationFailureCode.TIMEOUT)

        async with _automatic_runtime_context(
            migrated_database,
            grant_seat_index=1,
        ) as context:
            assert context.grant_id is not None
            identities = derive_automatic_turn_identities(
                session_id=context.session_id,
                floor_grant_id=context.grant_id,
            )
            result = await drive_single_ai_turn(
                context.session_factory,
                owner_id=context.owner_id,
                session_id=context.session_id,
                provider=provider,
                provider_identifier="local-test-provider",
                model_identifier="automatic-test-model",
                configuration_version="P1_5E_2_TEST",
                scheduling_policy=V0_1_SCHEDULER_POLICY,
            )

            async with context.session_factory() as session:
                request = await session.get(
                    LlmGenerationRequest, identities.generation_request_id
                )
                utterance = await session.get(AiUtterance, identities.utterance_id)
                release = await session.get(FloorRelease, context.grant_id)

            assert provider_calls == 1
            assert result.runtime_outcome is RuntimeGenerationOutcome.FAILED
            assert result.failure_code is GenerationFailureCode.TIMEOUT
            assert request is not None
            assert request.status == GenerationRequestStatus.FAILED
            assert request.failure_code == GenerationFailureCode.TIMEOUT
            assert utterance is None
            assert release is not None
            assert release.causation_action_id == identities.release_action_id
            assert release.reason_code == FloorReleaseReason.INTERRUPTED

    run_async(exercise)


async def _complete_and_release_without_scheduling(
    context: AutomaticRuntimeContext,
) -> None:
    assert context.grant_id is not None
    identities = derive_automatic_turn_identities(
        session_id=context.session_id,
        floor_grant_id=context.grant_id,
    )
    async with context.session_factory() as session:
        grant = await session.get(FloorGrant, context.grant_id)
    assert grant is not None

    async def provider(_input: object) -> RawGenerationSuccess:
        return RawGenerationSuccess(content="Durable result before simulated crash.")

    runtime_result = await generate_ai_utterance(
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
            model_identifier="automatic-test-model",
            request_metadata=GenerationRequestMetadata(
                configuration_version="P1_5E_2_TEST"
            ),
            occurred_at=grant.granted_at,
        ),
        executor=provider,
    )
    assert runtime_result.outcome is RuntimeGenerationOutcome.COMPLETED

    async with context.session_factory() as session:
        simulation_session = await session.get(SimulationSession, context.session_id)
    assert simulation_session is not None
    async with context.session_factory() as session:
        await apply_floor_command(
            session,
            owner_id=context.owner_id,
            command=ReleaseFloorCommand(
                session_id=context.session_id,
                action_id=identities.release_action_id,
                grant_id=grant.id,
                expected_phase=SessionStatus(simulation_session.status),
                expected_last_sequence=simulation_session.last_sequence,
                reason=FloorReleaseReason.SPEAKER_FINISHED,
            ),
        )


def test_generic_scheduler_checkpoint_recovers_committed_ai_release(
    migrated_database: TemporaryDatabaseContext,
) -> None:
    async def exercise() -> None:
        async with _automatic_runtime_context(
            migrated_database,
            grant_seat_index=1,
        ) as context:
            assert context.grant_id is not None
            identities = derive_automatic_turn_identities(
                session_id=context.session_id,
                floor_grant_id=context.grant_id,
            )
            await _complete_and_release_without_scheduling(context)
            assert await has_resumable_ai_work(
                context.session_factory,
                owner_id=context.owner_id,
                session_id=context.session_id,
            )

            result = await floor_progression_module.drive_scheduler_checkpoint(
                context.session_factory,
                owner_id=context.owner_id,
                session_id=context.session_id,
                released_floor=floor_progression_module.ReleasedFloorProof(
                    floor_grant_id=context.grant_id,
                    release_action_id=identities.release_action_id,
                    release_command_type="floor.release",
                    allowed_reasons=frozenset(
                        {
                            FloorReleaseReason.SPEAKER_FINISHED,
                            FloorReleaseReason.INTERRUPTED,
                        }
                    ),
                ),
                identities=floor_progression_module.SchedulerCheckpointIdentities(
                    schedule_action_id=identities.schedule_action_id,
                    decision_id=identities.decision_id,
                    next_floor_grant_id=identities.next_floor_grant_id,
                    intervention_id=identities.intervention_id,
                ),
                scheduling_policy=V0_1_SCHEDULER_POLICY,
            )

            assert result.processed_floor_grant_id == context.grant_id
            assert result.identities.schedule_action_id == identities.schedule_action_id
            assert result.outcome.value in {
                "next_ai_granted",
                "next_human_granted",
            }

    run_async(exercise)


def test_release_commit_precedes_exactly_one_scheduler_checkpoint_and_crash_f_replays(
    migrated_database: TemporaryDatabaseContext,
) -> None:
    async def exercise() -> None:
        provider_calls = 0

        async def provider(_input: object) -> RawGenerationSuccess:
            nonlocal provider_calls
            provider_calls += 1
            return RawGenerationSuccess(content="One turn only.")

        async with _automatic_runtime_context(
            migrated_database,
            grant_seat_index=1,
        ) as context:
            assert context.grant_id is not None
            identities = derive_automatic_turn_identities(
                session_id=context.session_id,
                floor_grant_id=context.grant_id,
            )
            result = await drive_single_ai_turn(
                context.session_factory,
                owner_id=context.owner_id,
                session_id=context.session_id,
                provider=provider,
                provider_identifier="local-test-provider",
                model_identifier="automatic-test-model",
                configuration_version="P1_5E_2_TEST",
                scheduling_policy=V0_1_SCHEDULER_POLICY,
            )
            async with context.session_factory() as session:
                release_action = await session.get(
                    SessionAction,
                    (context.session_id, identities.release_action_id),
                )
                schedule_action = await session.get(
                    SessionAction,
                    (context.session_id, identities.schedule_action_id),
                )
                decision = await session.get(FloorDecision, identities.decision_id)
                next_grant = await session.get(
                    FloorGrant, identities.next_floor_grant_id
                )
                next_participant = (
                    None
                    if next_grant is None
                    else await session.get(
                        SessionParticipant, next_grant.participant_id
                    )
                )
                action_count = int(
                    await session.scalar(
                        select(func.count())
                        .select_from(SessionAction)
                        .where(SessionAction.session_id == context.session_id)
                    )
                    or 0
                )

            assert provider_calls == 1
            assert release_action is not None
            assert schedule_action is not None
            assert release_action.created_at <= schedule_action.created_at
            assert decision is not None
            assert next_grant is not None
            assert next_participant is not None
            expected_outcome = (
                SingleAiTurnOutcome.NEXT_HUMAN_GRANTED
                if next_participant.actor_kind == "HUMAN"
                else SingleAiTurnOutcome.NEXT_AI_GRANTED
            )
            assert result.outcome is expected_outcome
            assert result.next_floor_grant_id == identities.next_floor_grant_id
            assert result.next_participant_id == next_participant.id

            replay = await drive_single_ai_turn(
                context.session_factory,
                owner_id=context.owner_id,
                session_id=context.session_id,
                provider=provider,
                provider_identifier="local-test-provider",
                model_identifier="automatic-test-model",
                configuration_version="P1_5E_2_TEST",
                scheduling_policy=V0_1_SCHEDULER_POLICY,
            )
            async with context.session_factory() as session:
                replay_action_count = int(
                    await session.scalar(
                        select(func.count())
                        .select_from(SessionAction)
                        .where(SessionAction.session_id == context.session_id)
                    )
                    or 0
                )
            assert replay.outcome in {
                SingleAiTurnOutcome.WAITING_FOR_HUMAN,
                SingleAiTurnOutcome.NEXT_AI_GRANTED,
            }
            assert provider_calls == 1
            assert replay_action_count == action_count

    run_async(exercise)


def test_crash_e_committed_automatic_release_resumes_scheduler_without_provider(
    migrated_database: TemporaryDatabaseContext,
) -> None:
    async def exercise() -> None:
        provider_calls = 0

        async def provider(_input: object) -> RawGenerationSuccess:
            nonlocal provider_calls
            provider_calls += 1
            return RawGenerationSuccess(content="must not run")

        async with _automatic_runtime_context(
            migrated_database,
            grant_seat_index=1,
        ) as context:
            assert context.grant_id is not None
            identities = derive_automatic_turn_identities(
                session_id=context.session_id,
                floor_grant_id=context.grant_id,
            )
            await _complete_and_release_without_scheduling(context)
            result = await drive_single_ai_turn(
                context.session_factory,
                owner_id=context.owner_id,
                session_id=context.session_id,
                provider=provider,
                provider_identifier="local-test-provider",
                model_identifier="automatic-test-model",
                configuration_version="P1_5E_2_TEST",
                scheduling_policy=V0_1_SCHEDULER_POLICY,
            )
            async with context.session_factory() as session:
                schedule_action = await session.get(
                    SessionAction,
                    (context.session_id, identities.schedule_action_id),
                )
                decision = await session.get(FloorDecision, identities.decision_id)

            assert provider_calls == 0
            assert schedule_action is not None
            assert decision is not None
            assert result.schedule_action_id == identities.schedule_action_id

    run_async(exercise)


def test_crash_e_concurrent_scheduler_recovery_has_one_durable_winner(
    migrated_database: TemporaryDatabaseContext,
) -> None:
    async def exercise() -> None:
        provider_calls = 0

        async def provider(_input: object) -> RawGenerationSuccess:
            nonlocal provider_calls
            provider_calls += 1
            return RawGenerationSuccess(content="must not run")

        async with _automatic_runtime_context(
            migrated_database,
            grant_seat_index=1,
        ) as context:
            assert context.grant_id is not None
            identities = derive_automatic_turn_identities(
                session_id=context.session_id,
                floor_grant_id=context.grant_id,
            )
            await _complete_and_release_without_scheduling(context)

            async def drive() -> SingleAiTurnResult:
                return await drive_single_ai_turn(
                    context.session_factory,
                    owner_id=context.owner_id,
                    session_id=context.session_id,
                    provider=provider,
                    provider_identifier="local-test-provider",
                    model_identifier="automatic-test-model",
                    configuration_version="P1_5E_2_TEST",
                    scheduling_policy=V0_1_SCHEDULER_POLICY,
                )

            results = await asyncio.gather(drive(), drive())
            async with context.session_factory() as session:
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
                decision_count = int(
                    await session.scalar(
                        select(func.count())
                        .select_from(FloorDecision)
                        .where(FloorDecision.id == identities.decision_id)
                    )
                    or 0
                )
                next_grant_count = int(
                    await session.scalar(
                        select(func.count())
                        .select_from(FloorGrant)
                        .where(FloorGrant.id == identities.next_floor_grant_id)
                    )
                    or 0
                )
                intervention_count = int(
                    await session.scalar(
                        select(func.count())
                        .select_from(FloorIntervention)
                        .where(FloorIntervention.id == identities.intervention_id)
                    )
                    or 0
                )
                duplicate_schedule_actions = int(
                    await session.scalar(
                        select(func.count())
                        .select_from(SessionAction)
                        .where(
                            SessionAction.session_id == context.session_id,
                            SessionAction.command_type == "floor.schedule",
                        )
                    )
                    or 0
                )

            assert provider_calls == 0
            assert schedule_count == decision_count == 1
            assert duplicate_schedule_actions == 1
            assert next_grant_count + intervention_count <= 1
            assert all(
                result.outcome
                in {
                    SingleAiTurnOutcome.NEXT_AI_GRANTED,
                    SingleAiTurnOutcome.NEXT_HUMAN_GRANTED,
                    SingleAiTurnOutcome.NO_GRANT,
                    SingleAiTurnOutcome.INTERVENTION_REQUESTED,
                }
                for result in results
            )
            assert all(
                result.schedule_action_id == identities.schedule_action_id
                for result in results
            )

    run_async(exercise)


def test_release_persistence_uncertainty_before_durable_release_requires_reconciliation(
    migrated_database: TemporaryDatabaseContext,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def exercise() -> None:
        provider_calls = 0

        async def provider(_input: object) -> RawGenerationSuccess:
            nonlocal provider_calls
            provider_calls += 1
            return RawGenerationSuccess(
                content="Durable content before release uncertainty."
            )

        async def uncertain_release(*_args: object, **_kwargs: object) -> None:
            raise SessionPersistenceError("test uncertainty before durable release")

        async with _automatic_runtime_context(
            migrated_database,
            grant_seat_index=1,
        ) as context:
            assert context.grant_id is not None
            identities = derive_automatic_turn_identities(
                session_id=context.session_id,
                floor_grant_id=context.grant_id,
            )
            monkeypatch.setattr(
                orchestration_module,
                "apply_floor_command",
                uncertain_release,
            )

            result = await drive_single_ai_turn(
                context.session_factory,
                owner_id=context.owner_id,
                session_id=context.session_id,
                provider=provider,
                provider_identifier="local-test-provider",
                model_identifier="automatic-test-model",
                configuration_version="P1_5E_2_TEST",
                scheduling_policy=V0_1_SCHEDULER_POLICY,
            )
            async with context.session_factory() as session:
                simulation_session = await session.get(
                    SimulationSession, context.session_id
                )
                release = await session.get(FloorRelease, context.grant_id)
                schedule = await session.get(
                    SessionAction,
                    (context.session_id, identities.schedule_action_id),
                )

            assert provider_calls == 1
            assert result.outcome is SingleAiTurnOutcome.RECONCILIATION_REQUIRED
            assert result.runtime_outcome is RuntimeGenerationOutcome.COMPLETED
            assert simulation_session is not None
            assert simulation_session.current_floor_grant_id == context.grant_id
            assert release is None
            assert schedule is None

    run_async(exercise)


def test_scheduler_persistence_uncertainty_before_durable_action_requires_reconciliation(
    migrated_database: TemporaryDatabaseContext,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def exercise() -> None:
        provider_calls = 0

        async def provider(_input: object) -> RawGenerationSuccess:
            nonlocal provider_calls
            provider_calls += 1
            return RawGenerationSuccess(content="must not run")

        async def uncertain_schedule(*_args: object, **_kwargs: object) -> None:
            raise SessionPersistenceError(
                "test uncertainty before durable scheduler action"
            )

        async with _automatic_runtime_context(
            migrated_database,
            grant_seat_index=1,
        ) as context:
            assert context.grant_id is not None
            identities = derive_automatic_turn_identities(
                session_id=context.session_id,
                floor_grant_id=context.grant_id,
            )
            await _complete_and_release_without_scheduling(context)
            monkeypatch.setattr(
                floor_progression_module,
                "apply_scheduler_command",
                uncertain_schedule,
            )

            result = await drive_single_ai_turn(
                context.session_factory,
                owner_id=context.owner_id,
                session_id=context.session_id,
                provider=provider,
                provider_identifier="local-test-provider",
                model_identifier="automatic-test-model",
                configuration_version="P1_5E_2_TEST",
                scheduling_policy=V0_1_SCHEDULER_POLICY,
            )
            async with context.session_factory() as session:
                simulation_session = await session.get(
                    SimulationSession, context.session_id
                )
                release = await session.get(FloorRelease, context.grant_id)
                schedule = await session.get(
                    SessionAction,
                    (context.session_id, identities.schedule_action_id),
                )
                decision = await session.get(FloorDecision, identities.decision_id)

            assert provider_calls == 0
            assert result.outcome is SingleAiTurnOutcome.RECONCILIATION_REQUIRED
            assert simulation_session is not None
            assert simulation_session.current_floor_grant_id is None
            assert release is not None
            assert release.causation_action_id == identities.release_action_id
            assert schedule is None
            assert decision is None

    run_async(exercise)


def test_concurrent_exact_drives_have_one_provider_and_one_durable_chain(
    migrated_database: TemporaryDatabaseContext,
) -> None:
    async def exercise() -> None:
        provider_calls = 0

        async def provider(_input: object) -> RawGenerationSuccess:
            nonlocal provider_calls
            provider_calls += 1
            await asyncio.sleep(0.05)
            return RawGenerationSuccess(content="Concurrent deterministic winner.")

        async with _automatic_runtime_context(
            migrated_database,
            grant_seat_index=1,
        ) as context:
            assert context.grant_id is not None
            identities = derive_automatic_turn_identities(
                session_id=context.session_id,
                floor_grant_id=context.grant_id,
            )

            async def drive() -> SingleAiTurnResult:
                return await drive_single_ai_turn(
                    context.session_factory,
                    owner_id=context.owner_id,
                    session_id=context.session_id,
                    provider=provider,
                    provider_identifier="local-test-provider",
                    model_identifier="automatic-test-model",
                    configuration_version="P1_5E_2_TEST",
                    scheduling_policy=V0_1_SCHEDULER_POLICY,
                )

            results = await asyncio.gather(drive(), drive())
            async with context.session_factory() as session:
                request_count = int(
                    await session.scalar(
                        select(func.count())
                        .select_from(LlmGenerationRequest)
                        .where(
                            LlmGenerationRequest.id == identities.generation_request_id
                        )
                    )
                    or 0
                )
                utterance_count = int(
                    await session.scalar(
                        select(func.count())
                        .select_from(AiUtterance)
                        .where(AiUtterance.floor_grant_id == context.grant_id)
                    )
                    or 0
                )
                release_count = int(
                    await session.scalar(
                        select(func.count())
                        .select_from(FloorRelease)
                        .where(FloorRelease.grant_id == context.grant_id)
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

            assert provider_calls == 1
            assert (
                request_count == utterance_count == release_count == schedule_count == 1
            )
            assert any(
                result.outcome
                in {
                    SingleAiTurnOutcome.NEXT_AI_GRANTED,
                    SingleAiTurnOutcome.NEXT_HUMAN_GRANTED,
                    SingleAiTurnOutcome.NO_GRANT,
                    SingleAiTurnOutcome.INTERVENTION_REQUESTED,
                }
                for result in results
            )
            assert all(
                result.outcome is not SingleAiTurnOutcome.STATE_CHANGED
                for result in results
            )

    run_async(exercise)


def test_crash_c_running_request_stops_without_provider_release_or_scheduler(
    migrated_database: TemporaryDatabaseContext,
) -> None:
    async def exercise() -> None:
        provider_calls = 0

        async def provider(_input: object) -> RawGenerationSuccess:
            nonlocal provider_calls
            provider_calls += 1
            return RawGenerationSuccess(content="must not run")

        async with _automatic_runtime_context(
            migrated_database,
            grant_seat_index=1,
        ) as context:
            assert context.grant_id is not None
            identities = derive_automatic_turn_identities(
                session_id=context.session_id,
                floor_grant_id=context.grant_id,
            )
            async with context.session_factory() as session:
                grant = await session.get(FloorGrant, context.grant_id)
            assert grant is not None
            async with context.session_factory() as session:
                await create_generation_request(
                    session,
                    owner_id=context.owner_id,
                    command=RequestGenerationCommand(
                        request_id=identities.generation_request_id,
                        session_id=context.session_id,
                        participant_id=grant.participant_id,
                        floor_grant_id=grant.id,
                        prompt_version_id=PROMPT_ID,
                        provider_identifier="local-test-provider",
                        model_identifier="automatic-test-model",
                        request_metadata=GenerationRequestMetadata(
                            configuration_version="P1_5E_2_TEST"
                        ),
                        requested_at=grant.granted_at,
                    ),
                )
            async with context.session_factory() as session:
                await claim_generation_request(
                    session,
                    owner_id=context.owner_id,
                    command=StartGenerationCommand(
                        session_id=context.session_id,
                        generation_request_id=identities.generation_request_id,
                        started_at=datetime.now(UTC),
                    ),
                )

            result = await drive_single_ai_turn(
                context.session_factory,
                owner_id=context.owner_id,
                session_id=context.session_id,
                provider=provider,
                provider_identifier="local-test-provider",
                model_identifier="automatic-test-model",
                configuration_version="P1_5E_2_TEST",
                scheduling_policy=V0_1_SCHEDULER_POLICY,
            )
            async with context.session_factory() as session:
                release = await session.get(FloorRelease, context.grant_id)
                schedule = await session.get(
                    SessionAction,
                    (context.session_id, identities.schedule_action_id),
                )

            assert provider_calls == 0
            assert result.outcome is SingleAiTurnOutcome.RECONCILIATION_REQUIRED
            assert (
                result.runtime_outcome
                is RuntimeGenerationOutcome.RECONCILIATION_REQUIRED
            )
            assert release is None
            assert schedule is None

    run_async(exercise)


def test_superseded_request_proves_same_grant_winner_before_release(
    migrated_database: TemporaryDatabaseContext,
) -> None:
    async def exercise() -> None:
        automatic_provider_calls = 0

        async def winner_provider(_input: object) -> RawGenerationSuccess:
            return RawGenerationSuccess(content="Existing same-grant winner.")

        async def automatic_provider(_input: object) -> RawGenerationSuccess:
            nonlocal automatic_provider_calls
            automatic_provider_calls += 1
            return RawGenerationSuccess(content="Losing automatic request.")

        async with _automatic_runtime_context(
            migrated_database,
            grant_seat_index=1,
        ) as context:
            assert context.grant_id is not None
            identities = derive_automatic_turn_identities(
                session_id=context.session_id,
                floor_grant_id=context.grant_id,
            )
            async with context.session_factory() as session:
                grant = await session.get(FloorGrant, context.grant_id)
            assert grant is not None
            winning_request_id = uuid4()
            winning_utterance_id = uuid4()
            winner = await generate_ai_utterance(
                context.session_factory,
                owner_id=context.owner_id,
                command=GenerateAiUtteranceCommand(
                    generation_request_id=winning_request_id,
                    utterance_id=winning_utterance_id,
                    session_id=context.session_id,
                    participant_id=grant.participant_id,
                    floor_grant_id=grant.id,
                    prompt_version_id=PROMPT_ID,
                    provider_identifier="local-test-provider",
                    model_identifier="automatic-test-model",
                    request_metadata=GenerationRequestMetadata(
                        configuration_version="P1_5E_2_TEST"
                    ),
                    occurred_at=grant.granted_at,
                ),
                executor=winner_provider,
            )
            assert winner.outcome is RuntimeGenerationOutcome.COMPLETED

            result = await drive_single_ai_turn(
                context.session_factory,
                owner_id=context.owner_id,
                session_id=context.session_id,
                provider=automatic_provider,
                provider_identifier="local-test-provider",
                model_identifier="automatic-test-model",
                configuration_version="P1_5E_2_TEST",
                scheduling_policy=V0_1_SCHEDULER_POLICY,
            )
            async with context.session_factory() as session:
                release = await session.get(FloorRelease, context.grant_id)
                schedule = await session.get(
                    SessionAction,
                    (context.session_id, identities.schedule_action_id),
                )

            assert automatic_provider_calls == 1
            assert result.runtime_outcome is RuntimeGenerationOutcome.SUPERSEDED
            assert result.utterance_id == winning_utterance_id
            assert release is not None
            assert release.causation_action_id == identities.release_action_id
            assert release.reason_code == FloorReleaseReason.SPEAKER_FINISHED
            assert schedule is not None

    run_async(exercise)


def test_unrelated_release_never_triggers_automatic_scheduler(
    migrated_database: TemporaryDatabaseContext,
) -> None:
    async def exercise() -> None:
        provider_calls = 0

        async def provider(_input: object) -> RawGenerationSuccess:
            nonlocal provider_calls
            provider_calls += 1
            return RawGenerationSuccess(content="must not run")

        async with _automatic_runtime_context(
            migrated_database,
            grant_seat_index=1,
        ) as context:
            assert context.grant_id is not None
            identities = derive_automatic_turn_identities(
                session_id=context.session_id,
                floor_grant_id=context.grant_id,
            )
            async with context.session_factory() as session:
                simulation_session = await session.get(
                    SimulationSession, context.session_id
                )
            assert simulation_session is not None
            async with context.session_factory() as session:
                await apply_floor_command(
                    session,
                    owner_id=context.owner_id,
                    command=ReleaseFloorCommand(
                        session_id=context.session_id,
                        action_id=uuid4(),
                        grant_id=context.grant_id,
                        expected_phase=SessionStatus(simulation_session.status),
                        expected_last_sequence=simulation_session.last_sequence,
                        reason=FloorReleaseReason.SPEAKER_FINISHED,
                    ),
                )
            result = await drive_single_ai_turn(
                context.session_factory,
                owner_id=context.owner_id,
                session_id=context.session_id,
                provider=provider,
                provider_identifier="local-test-provider",
                model_identifier="automatic-test-model",
                configuration_version="P1_5E_2_TEST",
                scheduling_policy=V0_1_SCHEDULER_POLICY,
            )
            async with context.session_factory() as session:
                schedule = await session.get(
                    SessionAction,
                    (context.session_id, identities.schedule_action_id),
                )
            assert provider_calls == 0
            assert result.outcome is SingleAiTurnOutcome.NO_CURRENT_WORK
            assert schedule is None

    run_async(exercise)


def test_crash_b_requested_request_is_claimed_with_durable_timestamp(
    migrated_database: TemporaryDatabaseContext,
) -> None:
    async def exercise() -> None:
        provider_calls = 0

        async def provider(_input: RuntimeGenerationInput) -> RawGenerationSuccess:
            nonlocal provider_calls
            provider_calls += 1
            return RawGenerationSuccess(content="Resumed requested generation.")

        async with _automatic_runtime_context(
            migrated_database,
            grant_seat_index=1,
        ) as context:
            assert context.grant_id is not None
            identities = derive_automatic_turn_identities(
                session_id=context.session_id,
                floor_grant_id=context.grant_id,
            )
            async with context.session_factory() as session:
                grant = await session.get(FloorGrant, context.grant_id)
            assert grant is not None
            async with context.session_factory() as session:
                await create_generation_request(
                    session,
                    owner_id=context.owner_id,
                    command=RequestGenerationCommand(
                        request_id=identities.generation_request_id,
                        session_id=context.session_id,
                        participant_id=grant.participant_id,
                        floor_grant_id=grant.id,
                        prompt_version_id=PROMPT_ID,
                        provider_identifier="local-test-provider",
                        model_identifier="automatic-test-model",
                        request_metadata=GenerationRequestMetadata(
                            configuration_version="P1_5E_2_TEST"
                        ),
                        requested_at=grant.granted_at,
                    ),
                )

            result = await drive_single_ai_turn(
                context.session_factory,
                owner_id=context.owner_id,
                session_id=context.session_id,
                provider=provider,
                provider_identifier="local-test-provider",
                model_identifier="automatic-test-model",
                configuration_version="P1_5E_2_TEST",
                scheduling_policy=V0_1_SCHEDULER_POLICY,
            )
            async with context.session_factory() as session:
                request = await session.get(
                    LlmGenerationRequest, identities.generation_request_id
                )
                release = await session.get(FloorRelease, grant.id)

            assert provider_calls == 1
            assert result.runtime_outcome is RuntimeGenerationOutcome.COMPLETED
            assert request is not None
            assert request.requested_at == grant.granted_at
            assert release is not None

    run_async(exercise)


def test_crash_d_terminal_request_releases_and_schedules_without_provider(
    migrated_database: TemporaryDatabaseContext,
) -> None:
    async def exercise() -> None:
        replay_provider_calls = 0

        async def initial_provider(
            _input: RuntimeGenerationInput,
        ) -> RawGenerationSuccess:
            return RawGenerationSuccess(content="Committed before crash D.")

        async def replay_provider(
            _input: RuntimeGenerationInput,
        ) -> RawGenerationSuccess:
            nonlocal replay_provider_calls
            replay_provider_calls += 1
            return RawGenerationSuccess(content="must not run")

        async with _automatic_runtime_context(
            migrated_database,
            grant_seat_index=1,
        ) as context:
            assert context.grant_id is not None
            identities = derive_automatic_turn_identities(
                session_id=context.session_id,
                floor_grant_id=context.grant_id,
            )
            async with context.session_factory() as session:
                grant = await session.get(FloorGrant, context.grant_id)
            assert grant is not None
            initial = await generate_ai_utterance(
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
                    model_identifier="automatic-test-model",
                    request_metadata=GenerationRequestMetadata(
                        configuration_version="P1_5E_2_TEST"
                    ),
                    occurred_at=grant.granted_at,
                ),
                executor=initial_provider,
            )
            assert initial.outcome is RuntimeGenerationOutcome.COMPLETED

            result = await drive_single_ai_turn(
                context.session_factory,
                owner_id=context.owner_id,
                session_id=context.session_id,
                provider=replay_provider,
                provider_identifier="local-test-provider",
                model_identifier="automatic-test-model",
                configuration_version="P1_5E_2_TEST",
                scheduling_policy=V0_1_SCHEDULER_POLICY,
            )
            async with context.session_factory() as session:
                release = await session.get(FloorRelease, grant.id)
                schedule = await session.get(
                    SessionAction,
                    (context.session_id, identities.schedule_action_id),
                )

            assert replay_provider_calls == 0
            assert result.runtime_outcome is RuntimeGenerationOutcome.COMPLETED_REPLAY
            assert release is not None
            assert release.causation_action_id == identities.release_action_id
            assert schedule is not None

    run_async(exercise)


def test_automatic_prompt_keeps_other_participant_private_stance_out(
    migrated_database: TemporaryDatabaseContext,
) -> None:
    async def exercise() -> None:
        rendered_prompt = ""

        async def provider(
            generation_input: RuntimeGenerationInput,
        ) -> RawGenerationSuccess:
            nonlocal rendered_prompt
            rendered_prompt = generation_input.rendered_prompt
            return RawGenerationSuccess(content="Privacy-isolated contribution.")

        async with _automatic_runtime_context(
            migrated_database,
            grant_seat_index=1,
        ) as context:
            result = await drive_single_ai_turn(
                context.session_factory,
                owner_id=context.owner_id,
                session_id=context.session_id,
                provider=provider,
                provider_identifier="local-test-provider",
                model_identifier="automatic-test-model",
                configuration_version="P1_5E_2_TEST",
                scheduling_policy=V0_1_SCHEDULER_POLICY,
            )

            assert CURRENT_STANCE_SENTINEL in rendered_prompt
            assert OTHER_STANCE_SENTINEL not in rendered_prompt
            serialized_result = result.model_dump_json()
            assert CURRENT_STANCE_SENTINEL not in serialized_result
            assert OTHER_STANCE_SENTINEL not in serialized_result

    run_async(exercise)


def test_overdue_lifecycle_wins_without_automatic_release_or_scheduler(
    migrated_database: TemporaryDatabaseContext,
) -> None:
    async def exercise() -> None:
        provider_calls = 0

        async def provider(_input: RuntimeGenerationInput) -> RawGenerationSuccess:
            nonlocal provider_calls
            provider_calls += 1
            return RawGenerationSuccess(content="must not run")

        async with _automatic_runtime_context(
            migrated_database,
            grant_seat_index=1,
        ) as context:
            assert context.grant_id is not None
            identities = derive_automatic_turn_identities(
                session_id=context.session_id,
                floor_grant_id=context.grant_id,
            )
            async with context.session_factory() as session:
                async with session.begin():
                    simulation_session = await session.get(
                        SimulationSession, context.session_id
                    )
                    assert simulation_session is not None
                    overdue_at = datetime.now(UTC) - timedelta(seconds=1)
                    simulation_session.phase_started_at = overdue_at - timedelta(
                        seconds=300
                    )
                    simulation_session.phase_deadline_at = overdue_at

            result = await drive_single_ai_turn(
                context.session_factory,
                owner_id=context.owner_id,
                session_id=context.session_id,
                provider=provider,
                provider_identifier="local-test-provider",
                model_identifier="automatic-test-model",
                configuration_version="P1_5E_2_TEST",
                scheduling_policy=V0_1_SCHEDULER_POLICY,
            )
            async with context.session_factory() as session:
                release = await session.get(FloorRelease, context.grant_id)
                automatic_release = await session.get(
                    SessionAction,
                    (context.session_id, identities.release_action_id),
                )
                schedule = await session.get(
                    SessionAction,
                    (context.session_id, identities.schedule_action_id),
                )

            assert provider_calls == 0
            assert result.outcome is SingleAiTurnOutcome.STATE_CHANGED
            assert result.runtime_outcome is RuntimeGenerationOutcome.CONTEXT_REJECTED
            assert release is not None
            assert release.causation_action_id is None
            assert release.reason_code == FloorReleaseReason.PHASE_CHANGED
            assert automatic_release is None
            assert schedule is None

    run_async(exercise)


def test_invalid_prompt_rendering_with_exact_current_grant_requires_reconciliation(
    migrated_database: TemporaryDatabaseContext,
) -> None:
    async def exercise() -> None:
        provider_calls = 0

        async def provider(_input: RuntimeGenerationInput) -> RawGenerationSuccess:
            nonlocal provider_calls
            provider_calls += 1
            return RawGenerationSuccess(content="must not run")

        async with _automatic_runtime_context(
            migrated_database,
            grant_seat_index=1,
        ) as context:
            assert context.grant_id is not None
            identities = derive_automatic_turn_identities(
                session_id=context.session_id,
                floor_grant_id=context.grant_id,
            )
            async with context.session_factory() as session:
                async with session.begin():
                    prompt = await session.get(PromptVersion, PROMPT_ID)
                    assert prompt is not None
                    prompt.template_text = "Unknown variable: $not_authorized"

            result = await drive_single_ai_turn(
                context.session_factory,
                owner_id=context.owner_id,
                session_id=context.session_id,
                provider=provider,
                provider_identifier="local-test-provider",
                model_identifier="automatic-test-model",
                configuration_version="P1_5E_2_TEST",
                scheduling_policy=V0_1_SCHEDULER_POLICY,
            )
            async with context.session_factory() as session:
                simulation_session = await session.get(
                    SimulationSession, context.session_id
                )
                request = await session.get(
                    LlmGenerationRequest, identities.generation_request_id
                )
                release = await session.get(FloorRelease, context.grant_id)
                schedule = await session.get(
                    SessionAction,
                    (context.session_id, identities.schedule_action_id),
                )

            assert provider_calls == 0
            assert result.outcome is SingleAiTurnOutcome.RECONCILIATION_REQUIRED
            assert result.runtime_outcome is RuntimeGenerationOutcome.CONTEXT_REJECTED
            assert simulation_session is not None
            assert simulation_session.current_floor_grant_id == context.grant_id
            assert request is None
            assert release is None
            assert schedule is None

    run_async(exercise)


def test_automatic_no_grant_checkpoint_replays_without_provider(
    migrated_database: TemporaryDatabaseContext,
) -> None:
    async def exercise() -> None:
        provider_calls = 0

        async def provider(_input: RuntimeGenerationInput) -> RawGenerationSuccess:
            nonlocal provider_calls
            provider_calls += 1
            return RawGenerationSuccess(content="Turn before no-grant checkpoint.")

        async with _automatic_runtime_context(
            migrated_database,
            grant_seat_index=1,
        ) as context:
            assert context.grant_id is not None
            identities = derive_automatic_turn_identities(
                session_id=context.session_id,
                floor_grant_id=context.grant_id,
            )
            async with context.session_factory() as session:
                async with session.begin():
                    for participant in context.participants:
                        if participant.id == context.participants[1].id:
                            continue
                        stored = await session.get(SessionParticipant, participant.id)
                        assert stored is not None
                        stored.availability = "UNAVAILABLE"
            policy = replace(
                V0_1_SCHEDULER_POLICY,
                max_phase_grants=1,
                silence_threshold=timedelta(hours=1),
            )

            first = await drive_single_ai_turn(
                context.session_factory,
                owner_id=context.owner_id,
                session_id=context.session_id,
                provider=provider,
                provider_identifier="local-test-provider",
                model_identifier="automatic-test-model",
                configuration_version="P1_5E_2_TEST",
                scheduling_policy=policy,
            )
            replay = await drive_single_ai_turn(
                context.session_factory,
                owner_id=context.owner_id,
                session_id=context.session_id,
                provider=provider,
                provider_identifier="local-test-provider",
                model_identifier="automatic-test-model",
                configuration_version="P1_5E_2_TEST",
                scheduling_policy=policy,
            )
            async with context.session_factory() as session:
                decision = await session.get(FloorDecision, identities.decision_id)
                next_grant = await session.get(
                    FloorGrant, identities.next_floor_grant_id
                )
                intervention = await session.get(
                    FloorIntervention, identities.intervention_id
                )

            assert provider_calls == 1
            assert first.outcome is SingleAiTurnOutcome.NO_GRANT
            assert replay.outcome is SingleAiTurnOutcome.NO_GRANT
            assert decision is not None
            assert decision.outcome_kind == FloorDecisionOutcome.NO_GRANT
            assert next_grant is None
            assert intervention is None

    run_async(exercise)


def test_automatic_intervention_checkpoint_replays_without_provider(
    migrated_database: TemporaryDatabaseContext,
) -> None:
    async def exercise() -> None:
        provider_calls = 0

        async def provider(_input: RuntimeGenerationInput) -> RawGenerationSuccess:
            nonlocal provider_calls
            provider_calls += 1
            return RawGenerationSuccess(content="Turn before intervention checkpoint.")

        async with _automatic_runtime_context(
            migrated_database,
            grant_seat_index=1,
        ) as context:
            assert context.grant_id is not None
            identities = derive_automatic_turn_identities(
                session_id=context.session_id,
                floor_grant_id=context.grant_id,
            )
            policy = replace(
                V0_1_SCHEDULER_POLICY,
                deadline_intervention_threshold=timedelta(hours=1),
            )

            first = await drive_single_ai_turn(
                context.session_factory,
                owner_id=context.owner_id,
                session_id=context.session_id,
                provider=provider,
                provider_identifier="local-test-provider",
                model_identifier="automatic-test-model",
                configuration_version="P1_5E_2_TEST",
                scheduling_policy=policy,
            )
            replay = await drive_single_ai_turn(
                context.session_factory,
                owner_id=context.owner_id,
                session_id=context.session_id,
                provider=provider,
                provider_identifier="local-test-provider",
                model_identifier="automatic-test-model",
                configuration_version="P1_5E_2_TEST",
                scheduling_policy=policy,
            )
            async with context.session_factory() as session:
                decision = await session.get(FloorDecision, identities.decision_id)
                intervention = await session.get(
                    FloorIntervention, identities.intervention_id
                )

            assert provider_calls == 1
            assert first.outcome is SingleAiTurnOutcome.INTERVENTION_REQUESTED
            assert replay.outcome is SingleAiTurnOutcome.INTERVENTION_REQUESTED
            assert decision is not None
            assert decision.outcome_kind == FloorDecisionOutcome.REQUEST_INTERVENTION
            assert intervention is not None
            assert intervention.decision_id == identities.decision_id

    run_async(exercise)
