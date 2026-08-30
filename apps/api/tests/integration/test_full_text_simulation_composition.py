import asyncio
import json
from collections.abc import Callable, Coroutine
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Protocol
from uuid import UUID, uuid4

import pytest
from sqlalchemy import URL, select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from group_interview_arena_api.core.config import DatabaseSettings
from group_interview_arena_api.db import (
    AiUtterance,
    DiscussionEvent,
    DiscussionMemoryRevision,
    DiscussionMemoryState,
    FloorGrant,
    FloorRelease,
    LlmGenerationRequest,
    PersonaPrivateStance,
    SessionParticipant,
    SimulationSession,
    User,
)
from group_interview_arena_api.db.runtime import (
    create_database_engine,
    create_database_session_factory,
    dispose_database_engine,
)
from group_interview_arena_api.modules.ai_runtime import composition
from group_interview_arena_api.modules.ai_runtime.continuous import (
    ContinuousAiDriveOutcome,
)
from group_interview_arena_api.modules.ai_runtime.domain import (
    GenerationFailureCode,
    GenerationRequestStatus,
)
from group_interview_arena_api.modules.ai_runtime.generation import (
    ModelInvocationInput,
    ModelOutputExpectation,
    RawGenerationFailure,
    RawGenerationResult,
    RawGenerationSuccess,
    RuntimeGenerationInput,
)
from group_interview_arena_api.modules.ai_runtime.runtime import (
    RuntimeGenerationOutcome,
)
from group_interview_arena_api.modules.ai_runtime.seed import (
    AI_CANDIDATE_TURN_V3,
    DISCUSSION_MEMORY_UPDATE_V2,
    seed_ai_runtime_prompt_versions,
)
from group_interview_arena_api.modules.discussion_sessions import progression
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
from group_interview_arena_api.modules.discussion_sessions.utterances import (
    SubmitHumanUtterance,
    submit_human_utterance,
)
from group_interview_arena_api.modules.floor_control.domain import (
    FloorDecisionOutcome,
    FloorDecisionRecord,
    FloorPolicyReason,
    FloorReleaseReason,
    GrantFloorCommand,
    ParticipantActorKind,
    ParticipantAvailability,
    SafeDecisionMetadata,
)
from group_interview_arena_api.modules.floor_control.service import apply_floor_command
from group_interview_arena_api.modules.question_personas.seed import (
    INTERNAL_VALIDATION_BUNDLE,
    seed_question_persona_foundation,
)
from group_interview_arena_api.providers.zhipu import (
    ZHIPU_CONFIGURATION_VERSION,
    ZHIPU_PROVIDER_IDENTIFIER,
)

pytestmark = pytest.mark.integration

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
MODEL_IDENTIFIER = "p1-6c-network-free"
CANDIDATE_CONTENT = "P1-6C deterministic candidate contribution."
MEMORY_SENTINEL = "P1_6C_PUBLIC_MEMORY_SENTINEL"
OTHER_PRIVATE_SENTINEL = "P1_6C_OTHER_AI_PRIVATE_STANCE_MUST_NOT_LEAK"


class TemporaryDatabaseContext(Protocol):
    database_name: str
    database_url: URL

    def database_settings(self) -> DatabaseSettings: ...


def run_async[T](operation: Callable[[], Coroutine[Any, Any, T]]) -> T:
    return asyncio.run(operation(), loop_factory=asyncio.SelectorEventLoop)


@dataclass(frozen=True)
class CompositionContext:
    engine: AsyncEngine
    session_factory: async_sessionmaker[AsyncSession]
    owner_id: UUID
    session_id: UUID
    participants: tuple[SessionParticipant, ...]
    human_grant_id: UUID
    public_sequences: tuple[int, ...]
    phase: SessionStatus
    phase_started_at: datetime
    phase_deadline_at: datetime | None


class NetworkFreeCompositionProvider:
    def __init__(self, *, source_sequence: int, fail_semantic: bool = False) -> None:
        self._source_sequence = source_sequence
        self._fail_semantic = fail_semantic
        self.semantic_inputs: list[ModelInvocationInput] = []
        self.candidate_inputs: list[RuntimeGenerationInput] = []

    async def invoke(self, invocation: ModelInvocationInput) -> RawGenerationResult:
        self.semantic_inputs.append(invocation)
        if self._fail_semantic:
            return RawGenerationFailure(
                failure_code=GenerationFailureCode.PROVIDER_UNAVAILABLE
            )
        return RawGenerationSuccess(
            content=json.dumps(
                {
                    "patches": [
                        {
                            "operation": "ADD",
                            "kind": "PROPOSAL",
                            "target_memory_item_id": None,
                            "canonical_text": MEMORY_SENTINEL,
                            "source_sequences": [self._source_sequence],
                        }
                    ]
                }
            )
        )

    async def __call__(
        self, generation_input: RuntimeGenerationInput
    ) -> RawGenerationResult:
        self.candidate_inputs.append(generation_input)
        return RawGenerationSuccess(content=CANDIDATE_CONTENT)


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


async def _append_public_evidence(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    session_id: UUID,
    participant: SessionParticipant,
    floor_grant_id: UUID,
    actor_kind: ParticipantActorKind,
    content: str,
) -> int:
    async with session_factory() as session:
        async with session.begin():
            aggregate = await session.get(
                SimulationSession, session_id, with_for_update=True
            )
            assert aggregate is not None
            assert aggregate.phase_started_at is not None
            aggregate.last_sequence += 1
            sequence = aggregate.last_sequence
            session.add(
                DiscussionEvent(
                    session_id=session_id,
                    sequence=sequence,
                    event_version=1,
                    event_type="participant.utterance.created",
                    causation_action_id=None,
                    payload={
                        "utterance_id": str(uuid4()),
                        "participant_id": str(participant.id),
                        "actor_kind": actor_kind.value,
                        "floor_grant_id": str(floor_grant_id),
                        "phase": SessionStatus.OPENING_STATEMENTS.value,
                        "content": content,
                    },
                    occurred_at=aggregate.phase_started_at
                    + timedelta(seconds=sequence),
                )
            )
            return sequence


@asynccontextmanager
async def _composition_context(
    temporary_database: TemporaryDatabaseContext,
    *,
    public_utterance_count: int,
):
    engine = create_database_engine(temporary_database.database_settings())
    session_factory = create_database_session_factory(engine)
    try:
        await seed_question_persona_foundation(session_factory)
        await seed_ai_runtime_prompt_versions(session_factory)
        owner_id = uuid4()
        async with session_factory() as session:
            async with session.begin():
                session.add(
                    User(
                        id=owner_id,
                        username=f"p16c_composition_{owner_id.hex[:10]}",
                        password_hash="test-only-password-hash",
                    )
                )
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
        assert len(participants) == 4
        assert participants[2].question_persona_assignment_id is not None
        async with session_factory() as session:
            async with session.begin():
                other_stance = await session.get(
                    PersonaPrivateStance,
                    participants[2].question_persona_assignment_id,
                )
                assert other_stance is not None
                other_stance.initial_position = OTHER_PRIVATE_SENTINEL
                for participant in participants[2:]:
                    stored = await session.get(SessionParticipant, participant.id)
                    assert stored is not None
                    stored.availability = ParticipantAvailability.UNAVAILABLE

        async with session_factory() as session:
            aggregate = await session.get(SimulationSession, created.session_id)
        assert aggregate is not None
        assert aggregate.status == SessionStatus.OPENING_STATEMENTS
        human_grant_id = uuid4()
        async with session_factory() as session:
            await apply_floor_command(
                session,
                owner_id=owner_id,
                command=GrantFloorCommand(
                    session_id=created.session_id,
                    action_id=uuid4(),
                    grant_id=human_grant_id,
                    decision=_grant_decision(
                        participant_id=participants[0].id,
                        expected_last_sequence=aggregate.last_sequence,
                    ),
                ),
            )

        for index in range(public_utterance_count - 1):
            participant = participants[(index % 3) + 1]
            await _append_public_evidence(
                session_factory,
                session_id=created.session_id,
                participant=participant,
                floor_grant_id=human_grant_id,
                actor_kind=ParticipantActorKind.AI,
                content=f"P1_6C_PUBLIC_EVIDENCE_{index}",
            )

        async with session_factory() as session:
            active = await get_session_snapshot(
                session,
                owner_id=owner_id,
                session_id=created.session_id,
            )
        assert active.phase_deadline_at is not None
        async with session_factory() as session:
            await submit_human_utterance(
                session,
                owner_id=owner_id,
                command=SubmitHumanUtterance(
                    session_id=created.session_id,
                    action_id=uuid4(),
                    floor_grant_id=human_grant_id,
                    content="P1_6C_HUMAN_RELEASE_EVIDENCE",
                    received_at=active.phase_deadline_at - timedelta(seconds=1),
                ),
            )
        async with session_factory() as session:
            public_sequences = tuple(
                (
                    await session.scalars(
                        select(DiscussionEvent.sequence)
                        .where(
                            DiscussionEvent.session_id == created.session_id,
                            DiscussionEvent.event_type
                            == "participant.utterance.created",
                        )
                        .order_by(DiscussionEvent.sequence)
                    )
                ).all()
            )
            before = await session.get(SimulationSession, created.session_id)
        assert before is not None
        assert before.phase_started_at is not None
        assert len(public_sequences) == public_utterance_count
        yield CompositionContext(
            engine=engine,
            session_factory=session_factory,
            owner_id=owner_id,
            session_id=created.session_id,
            participants=participants,
            human_grant_id=human_grant_id,
            public_sequences=public_sequences,
            phase=SessionStatus(before.status),
            phase_started_at=before.phase_started_at,
            phase_deadline_at=before.phase_deadline_at,
        )
    finally:
        await dispose_database_engine(engine)


def _install_provider(
    monkeypatch: pytest.MonkeyPatch,
    provider: NetworkFreeCompositionProvider,
) -> list[object]:
    monkeypatch.setenv("GIA_API_ZHIPU_API_KEY", "p1-6c-network-free-secret")
    monkeypatch.setenv("GIA_API_ZHIPU_MODEL", MODEL_IDENTIFIER)
    constructed_with: list[object] = []

    def provider_factory(settings: object) -> NetworkFreeCompositionProvider:
        constructed_with.append(settings)
        return provider

    monkeypatch.setattr(composition, "ZhipuGenerationProvider", provider_factory)
    return constructed_with


async def _participant_events(
    context: CompositionContext,
) -> tuple[DiscussionEvent, ...]:
    async with context.session_factory() as session:
        return tuple(
            (
                await session.scalars(
                    select(DiscussionEvent)
                    .where(
                        DiscussionEvent.session_id == context.session_id,
                        DiscussionEvent.event_type == "participant.utterance.created",
                    )
                    .order_by(DiscussionEvent.sequence)
                )
            ).all()
        )


async def _happy_memory_and_reentry_proof(
    temporary_database: TemporaryDatabaseContext,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async with _composition_context(
        temporary_database,
        public_utterance_count=12,
    ) as context:
        provider = NetworkFreeCompositionProvider(
            source_sequence=context.public_sequences[0]
        )
        compacted_through = context.public_sequences[-7]
        constructed_with = _install_provider(monkeypatch, provider)

        first = await progression.resume_discussion_progression(
            context.session_factory,
            owner_id=context.owner_id,
            session_id=context.session_id,
        )

        assert (
            first.outcome is progression.DiscussionProgressionOutcome.AI_DRIVE_COMPLETED
        )
        assert first.ai_drive_result is not None
        assert (
            first.ai_drive_result.outcome is ContinuousAiDriveOutcome.WAITING_FOR_HUMAN
        )
        assert first.ai_drive_result.automated_ai_turns_advanced == 1
        turn = first.ai_drive_result.last_turn_result
        assert turn is not None
        assert turn.runtime_outcome is RuntimeGenerationOutcome.COMPLETED
        assert turn.generation_request_id is not None
        assert turn.utterance_id is not None
        assert turn.release_action_id is not None
        assert turn.processed_floor_grant_id is not None
        assert len(constructed_with) == 1
        assert len(provider.semantic_inputs) == 1
        assert len(provider.candidate_inputs) == 1

        semantic_input = provider.semantic_inputs[0]
        assert semantic_input.output_expectation is ModelOutputExpectation.JSON_OBJECT
        assert semantic_input.provider_identifier == ZHIPU_PROVIDER_IDENTIFIER
        assert semantic_input.model_identifier == MODEL_IDENTIFIER
        assert semantic_input.configuration_version == ZHIPU_CONFIGURATION_VERSION
        assert OTHER_PRIVATE_SENTINEL not in semantic_input.rendered_prompt

        candidate_input = provider.candidate_inputs[0]
        assert candidate_input.prompt_version_id == AI_CANDIDATE_TURN_V3.id
        assert candidate_input.prompt_version_number == 3
        assert candidate_input.prompt_key == "AI_CANDIDATE_TURN"
        assert MEMORY_SENTINEL in candidate_input.rendered_prompt
        assert "P1_6C_HUMAN_RELEASE_EVIDENCE" in candidate_input.rendered_prompt
        assert OTHER_PRIVATE_SENTINEL not in candidate_input.rendered_prompt
        assert "结构化公开讨论记忆" in candidate_input.rendered_prompt
        assert "记忆游标之后的完整公开发言尾部" in candidate_input.rendered_prompt
        assert "当前阶段剩余秒数" in candidate_input.rendered_prompt

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
            request = await session.get(
                LlmGenerationRequest, turn.generation_request_id
            )
            utterance = await session.get(AiUtterance, turn.utterance_id)
            release = await session.get(FloorRelease, turn.processed_floor_grant_id)
            aggregate = await session.get(SimulationSession, context.session_id)

        assert state is not None
        assert state.revision == 1
        assert state.source_through_sequence == compacted_through
        state_surface = repr(state.structured_state)
        assert MEMORY_SENTINEL in state_surface
        assert OTHER_PRIVATE_SENTINEL not in state_surface
        assert len(revisions) == 1
        revision = revisions[0]
        assert revision.base_revision == 0
        assert revision.revision == 1
        assert revision.source_from_sequence == context.public_sequences[0]
        assert revision.source_through_sequence == compacted_through
        assert revision.prompt_version_id == DISCUSSION_MEMORY_UPDATE_V2.id
        assert revision.provider_identifier == ZHIPU_PROVIDER_IDENTIFIER
        assert revision.model_identifier == MODEL_IDENTIFIER
        assert revision.configuration_version == ZHIPU_CONFIGURATION_VERSION
        revision_surface = repr(revision.patches)
        assert MEMORY_SENTINEL in revision_surface
        assert OTHER_PRIVATE_SENTINEL not in revision_surface

        assert request is not None
        assert request.status == GenerationRequestStatus.COMPLETED
        assert request.prompt_version_id == AI_CANDIDATE_TURN_V3.id
        assert request.request_metadata == {
            "schema_version": 2,
            "configuration_version": ZHIPU_CONFIGURATION_VERSION,
            "working_context_version": "DISCUSSION_WORKING_CONTEXT_V1",
            "context_mode": "MEMORY_WITH_RAW_TAIL",
            "memory_revision": 1,
            "memory_source_through_sequence": compacted_through,
            "context_source_through_sequence": context.public_sequences[-1],
        }
        assert utterance is not None
        assert utterance.content == CANDIDATE_CONTENT
        assert release is not None
        assert release.reason_code == FloorReleaseReason.SPEAKER_FINISHED
        assert release.causation_action_id == turn.release_action_id
        assert aggregate is not None
        assert SessionStatus(aggregate.status) is context.phase
        assert aggregate.phase_started_at == context.phase_started_at
        assert aggregate.phase_deadline_at == context.phase_deadline_at

        events_after_first = await _participant_events(context)
        generated_events = tuple(
            event
            for event in events_after_first
            if event.payload.get("utterance_id") == str(turn.utterance_id)
        )
        assert len(generated_events) == 1
        assert generated_events[0].payload["content"] == CANDIDATE_CONTENT

        second = await progression.resume_discussion_progression(
            context.session_factory,
            owner_id=context.owner_id,
            session_id=context.session_id,
        )
        assert second.outcome is progression.DiscussionProgressionOutcome.NO_WORK
        assert len(provider.semantic_inputs) == 1
        assert len(provider.candidate_inputs) == 1
        async with context.session_factory() as session:
            revision_rows = (
                await session.scalars(
                    select(DiscussionMemoryRevision).where(
                        DiscussionMemoryRevision.session_id == context.session_id
                    )
                )
            ).all()
            utterance_rows = (
                await session.scalars(
                    select(AiUtterance).where(
                        AiUtterance.session_id == context.session_id
                    )
                )
            ).all()
            release_rows = (
                await session.scalars(
                    select(FloorRelease).where(
                        FloorRelease.session_id == context.session_id,
                        FloorRelease.grant_id == turn.processed_floor_grant_id,
                    )
                )
            ).all()
        assert len(revision_rows) == 1
        assert len(utterance_rows) == 1
        assert len(release_rows) == 1
        replayed_generated_events = tuple(
            event
            for event in await _participant_events(context)
            if event.payload.get("utterance_id") == str(turn.utterance_id)
        )
        assert len(replayed_generated_events) == 1


def test_real_progression_composes_memory_v3_persistence_and_reentry(
    migrated_database: TemporaryDatabaseContext,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_async(lambda: _happy_memory_and_reentry_proof(migrated_database, monkeypatch))


async def _safe_raw_fallback_proof(
    temporary_database: TemporaryDatabaseContext,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async with _composition_context(
        temporary_database,
        public_utterance_count=12,
    ) as context:
        provider = NetworkFreeCompositionProvider(
            source_sequence=context.public_sequences[0],
            fail_semantic=True,
        )
        _install_provider(monkeypatch, provider)

        result = await progression.resume_discussion_progression(
            context.session_factory,
            owner_id=context.owner_id,
            session_id=context.session_id,
        )

        assert (
            result.outcome
            is progression.DiscussionProgressionOutcome.AI_DRIVE_COMPLETED
        )
        assert result.ai_drive_result is not None
        assert (
            result.ai_drive_result.outcome is ContinuousAiDriveOutcome.WAITING_FOR_HUMAN
        )
        assert result.ai_drive_result.automated_ai_turns_advanced == 1
        turn = result.ai_drive_result.last_turn_result
        assert turn is not None
        assert turn.runtime_outcome is RuntimeGenerationOutcome.COMPLETED
        assert turn.generation_request_id is not None
        assert turn.utterance_id is not None
        assert turn.processed_floor_grant_id is not None
        assert len(provider.semantic_inputs) == 1
        assert len(provider.candidate_inputs) == 1
        assert OTHER_PRIVATE_SENTINEL not in provider.semantic_inputs[0].rendered_prompt

        candidate_input = provider.candidate_inputs[0]
        assert candidate_input.prompt_version_id == AI_CANDIDATE_TURN_V3.id
        assert candidate_input.prompt_version_number == 3
        assert "P1_6C_PUBLIC_EVIDENCE_0" in candidate_input.rendered_prompt
        assert "P1_6C_HUMAN_RELEASE_EVIDENCE" in candidate_input.rendered_prompt
        assert OTHER_PRIVATE_SENTINEL not in candidate_input.rendered_prompt
        assert "结构化公开讨论记忆" in candidate_input.rendered_prompt
        assert "记忆游标之后的完整公开发言尾部" in candidate_input.rendered_prompt
        assert "当前阶段剩余秒数" in candidate_input.rendered_prompt

        async with context.session_factory() as session:
            state = await session.get(DiscussionMemoryState, context.session_id)
            revisions = (
                await session.scalars(
                    select(DiscussionMemoryRevision).where(
                        DiscussionMemoryRevision.session_id == context.session_id
                    )
                )
            ).all()
            request = await session.get(
                LlmGenerationRequest, turn.generation_request_id
            )
            utterance = await session.get(AiUtterance, turn.utterance_id)
            release = await session.get(FloorRelease, turn.processed_floor_grant_id)

        assert state is None
        assert revisions == []
        assert request is not None
        assert request.status == GenerationRequestStatus.COMPLETED
        assert request.prompt_version_id == AI_CANDIDATE_TURN_V3.id
        assert request.request_metadata == {
            "schema_version": 2,
            "configuration_version": ZHIPU_CONFIGURATION_VERSION,
            "working_context_version": "DISCUSSION_WORKING_CONTEXT_V1",
            "context_mode": "SAFE_RAW_FALLBACK",
            "memory_revision": 0,
            "memory_source_through_sequence": 0,
            "context_source_through_sequence": context.public_sequences[-1],
        }
        assert utterance is not None
        assert utterance.content == CANDIDATE_CONTENT
        assert release is not None
        assert release.reason_code == FloorReleaseReason.SPEAKER_FINISHED


def test_real_progression_composes_safe_raw_fallback_with_v2_provenance(
    migrated_database: TemporaryDatabaseContext,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_async(lambda: _safe_raw_fallback_proof(migrated_database, monkeypatch))


async def _unsafe_context_proof(
    temporary_database: TemporaryDatabaseContext,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async with _composition_context(
        temporary_database,
        public_utterance_count=13,
    ) as context:
        provider = NetworkFreeCompositionProvider(
            source_sequence=context.public_sequences[0],
            fail_semantic=True,
        )
        _install_provider(monkeypatch, provider)

        result = await progression.resume_discussion_progression(
            context.session_factory,
            owner_id=context.owner_id,
            session_id=context.session_id,
        )

        assert (
            result.outcome
            is progression.DiscussionProgressionOutcome.AI_DRIVE_COMPLETED
        )
        assert result.ai_drive_result is not None
        assert (
            result.ai_drive_result.outcome
            is ContinuousAiDriveOutcome.RECONCILIATION_REQUIRED
        )
        assert result.ai_drive_result.automated_ai_turns_advanced == 0
        turn = result.ai_drive_result.last_turn_result
        assert turn is not None
        assert turn.runtime_outcome is RuntimeGenerationOutcome.CONTEXT_REJECTED
        assert turn.processed_floor_grant_id is not None
        assert turn.generation_request_id is not None
        assert len(provider.semantic_inputs) == 1
        assert provider.candidate_inputs == []
        assert OTHER_PRIVATE_SENTINEL not in provider.semantic_inputs[0].rendered_prompt

        async with context.session_factory() as session:
            request = await session.get(
                LlmGenerationRequest, turn.generation_request_id
            )
            state = await session.get(DiscussionMemoryState, context.session_id)
            revisions = (
                await session.scalars(
                    select(DiscussionMemoryRevision).where(
                        DiscussionMemoryRevision.session_id == context.session_id
                    )
                )
            ).all()
            utterances = (
                await session.scalars(
                    select(AiUtterance).where(
                        AiUtterance.session_id == context.session_id
                    )
                )
            ).all()
            release = await session.get(FloorRelease, turn.processed_floor_grant_id)
            grant = await session.get(FloorGrant, turn.processed_floor_grant_id)
            aggregate = await session.get(SimulationSession, context.session_id)

        assert request is None
        assert state is None
        assert revisions == []
        assert utterances == []
        assert release is None
        assert grant is not None
        assert grant.participant_id == context.participants[1].id
        assert aggregate is not None
        assert aggregate.current_floor_grant_id == turn.processed_floor_grant_id
        assert SessionStatus(aggregate.status) is context.phase
        assert aggregate.phase_started_at == context.phase_started_at
        assert aggregate.phase_deadline_at == context.phase_deadline_at
        events = await _participant_events(context)
        assert len(events) == 13
        assert all(
            event.payload.get("content") != CANDIDATE_CONTENT for event in events
        )


def test_real_progression_rejects_uncoverable_context_before_candidate_provider(
    migrated_database: TemporaryDatabaseContext,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_async(lambda: _unsafe_context_proof(migrated_database, monkeypatch))
