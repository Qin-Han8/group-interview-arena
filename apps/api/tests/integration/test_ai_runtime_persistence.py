import asyncio
from collections.abc import Callable, Coroutine
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from typing import Any, Protocol
from uuid import UUID, uuid4

import pytest
from sqlalchemy import URL, func, select
from sqlalchemy.exc import IntegrityError

from group_interview_arena_api.core.config import DatabaseSettings
from group_interview_arena_api.db import (
    AiUtterance,
    DiscussionEvent,
    LlmGenerationRequest,
    PromptVersion,
    SessionParticipant,
    SimulationSession,
    User,
)
from group_interview_arena_api.db.runtime import (
    create_database_engine,
    create_database_session_factory,
    dispose_database_engine,
)
from group_interview_arena_api.modules.ai_runtime import service as ai_runtime_service
from group_interview_arena_api.modules.ai_runtime.domain import (
    AiRuntimePersistenceError,
    FailGenerationCommand,
    GenerationContextError,
    GenerationFailureCode,
    GenerationRequestConflictError,
    GenerationRequestMetadata,
    GenerationRequestStatus,
    GenerationStateError,
    PersistUtteranceCommand,
    PromptVersionDefinition,
    PromptVersionMutationError,
    RequestGenerationCommand,
    StartGenerationCommand,
)
from group_interview_arena_api.modules.ai_runtime.orchestration import (
    _select_effective_prompt_version,  # pyright: ignore[reportPrivateUsage]
)
from group_interview_arena_api.modules.ai_runtime.seed import AI_CANDIDATE_TURN_V2
from group_interview_arena_api.modules.ai_runtime.service import (
    claim_generation_request,
    complete_generation_request,
    create_generation_request,
    fail_generation_request,
    publish_prompt_version,
    start_generation_request,
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
    GrantFloorCommand,
    SafeDecisionMetadata,
)
from group_interview_arena_api.modules.floor_control.service import apply_floor_command
from group_interview_arena_api.modules.question_personas.seed import (
    INTERNAL_VALIDATION_BUNDLE,
    seed_question_persona_foundation,
)

pytestmark = pytest.mark.integration
NOW = datetime(2026, 8, 21, 8, 0, tzinfo=UTC)
PROMPT_ID = UUID("31000000-0000-4000-8000-000000000001")
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


def _prompt(
    text: str = "Produce one concise candidate contribution.",
) -> PromptVersionDefinition:
    return PromptVersionDefinition(
        id=PROMPT_ID,
        prompt_key="AI_CANDIDATE_TURN",
        version_number=1,
        purpose_code="CANDIDATE_UTTERANCE",
        template_text=text,
        created_at=NOW,
        published_at=NOW,
    )


@asynccontextmanager
async def _runtime_context(temporary_database: TemporaryDatabaseContext):
    engine = create_database_engine(temporary_database.database_settings())
    session_factory = create_database_session_factory(engine)
    try:
        await seed_question_persona_foundation(session_factory)
        owner_id = uuid4()
        async with session_factory() as session:
            async with session.begin():
                session.add(
                    User(
                        id=owner_id,
                        username=f"ai_runtime_{owner_id.hex[:10]}",
                        password_hash="test-only-password-hash",
                    )
                )
        async with session_factory() as session:
            assert await publish_prompt_version(session, _prompt()) is True
        async with session_factory() as session:
            assert await publish_prompt_version(session, _prompt()) is False
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
                session, owner_id=owner_id, session_id=snapshot.session_id
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
            participants = list(
                (
                    await session.scalars(
                        select(SessionParticipant)
                        .where(SessionParticipant.session_id == snapshot.session_id)
                        .order_by(SessionParticipant.seat_order)
                    )
                ).all()
            )
        ai_participant = participants[1]
        grant_id = uuid4()
        grant_command = GrantFloorCommand(
            session_id=snapshot.session_id,
            action_id=uuid4(),
            grant_id=grant_id,
            decision=FloorDecisionRecord(
                decision_id=uuid4(),
                phase=SessionStatus.OPENING_STATEMENTS,
                expected_last_sequence=3,
                outcome=FloorDecisionOutcome.GRANT,
                selected_participant_id=ai_participant.id,
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
            ),
        )
        async with session_factory() as session:
            await apply_floor_command(session, owner_id=owner_id, command=grant_command)
        yield (
            session_factory,
            owner_id,
            snapshot.session_id,
            participants,
            grant_id,
        )
    finally:
        await dispose_database_engine(engine)


def _request(
    *,
    request_id: UUID,
    session_id: UUID,
    participant_id: UUID,
    grant_id: UUID,
    model_identifier: str = "discussion-model-v1",
) -> RequestGenerationCommand:
    return RequestGenerationCommand(
        request_id=request_id,
        session_id=session_id,
        participant_id=participant_id,
        floor_grant_id=grant_id,
        prompt_version_id=PROMPT_ID,
        provider_identifier="hosted-provider",
        model_identifier=model_identifier,
        request_metadata=GenerationRequestMetadata(configuration_version="V01_DEFAULT"),
        requested_at=NOW,
    )


async def _verify_ai_runtime_persistence(
    temporary_database: TemporaryDatabaseContext,
) -> None:
    async with _runtime_context(temporary_database) as context:
        session_factory, owner_id, session_id, participants, grant_id = context
        request_id = uuid4()
        request_command = _request(
            request_id=request_id,
            session_id=session_id,
            participant_id=participants[1].id,
            grant_id=grant_id,
        )
        async with session_factory() as session:
            requested = await create_generation_request(
                session, owner_id=owner_id, command=request_command
            )
        async with session_factory() as session:
            duplicate = await create_generation_request(
                session, owner_id=owner_id, command=request_command
            )
        assert requested == duplicate
        assert requested.status is GenerationRequestStatus.REQUESTED

        async with session_factory() as session:
            with pytest.raises(IntegrityError):
                async with session.begin():
                    session.add(
                        AiUtterance(
                            id=uuid4(),
                            session_id=session_id,
                            participant_id=participants[1].id,
                            floor_grant_id=grant_id,
                            generation_request_id=request_id,
                            generation_request_status="COMPLETED",
                            content="A requested generation cannot have an utterance.",
                            content_digest=b"0" * 32,
                            persisted_at=NOW,
                        )
                    )

        conflicting = request_command.model_copy(
            update={"model_identifier": "different-model"}
        )
        async with session_factory() as session:
            with pytest.raises(GenerationRequestConflictError):
                await create_generation_request(
                    session, owner_id=owner_id, command=conflicting
                )

        start_command = StartGenerationCommand(
            session_id=session_id,
            generation_request_id=request_id,
            started_at=NOW,
        )
        async with session_factory() as session:
            running = await start_generation_request(
                session, owner_id=owner_id, command=start_command
            )
        assert running.status is GenerationRequestStatus.RUNNING

        utterance_id = uuid4()
        complete_command = PersistUtteranceCommand(
            utterance_id=utterance_id,
            session_id=session_id,
            generation_request_id=request_id,
            content="I recommend validating the hard constraint before ranking options.",
            persisted_at=NOW,
        )
        async with session_factory() as session:
            completed = await complete_generation_request(
                session, owner_id=owner_id, command=complete_command
            )
        async with session_factory() as session:
            completed_duplicate = await complete_generation_request(
                session, owner_id=owner_id, command=complete_command
            )
        assert completed == completed_duplicate
        assert completed.status is GenerationRequestStatus.COMPLETED
        assert completed.utterance_id == utterance_id
        async with session_factory() as session:
            aggregate_after_completion = await session.get(
                SimulationSession, session_id
            )
            utterance_events = tuple(
                (
                    await session.scalars(
                        select(DiscussionEvent)
                        .where(
                            DiscussionEvent.session_id == session_id,
                            DiscussionEvent.event_type
                            == "participant.utterance.created",
                        )
                        .order_by(DiscussionEvent.sequence)
                    )
                ).all()
            )
        assert aggregate_after_completion is not None
        assert len(utterance_events) == 1
        public_event = utterance_events[0]
        assert public_event.sequence == aggregate_after_completion.last_sequence
        assert public_event.event_version == 1
        assert public_event.causation_action_id is None
        assert public_event.payload == {
            "utterance_id": str(utterance_id),
            "participant_id": str(participants[1].id),
            "actor_kind": "AI",
            "floor_grant_id": str(grant_id),
            "phase": "OPENING_STATEMENTS",
            "content": complete_command.content,
        }

        rollback_request_id = uuid4()
        rollback_request = _request(
            request_id=rollback_request_id,
            session_id=session_id,
            participant_id=participants[1].id,
            grant_id=grant_id,
        )
        async with session_factory() as session:
            await create_generation_request(
                session, owner_id=owner_id, command=rollback_request
            )
        async with session_factory() as session:
            await start_generation_request(
                session,
                owner_id=owner_id,
                command=StartGenerationCommand(
                    session_id=session_id,
                    generation_request_id=rollback_request_id,
                    started_at=NOW,
                ),
            )
        async with session_factory() as session:
            with pytest.raises(AiRuntimePersistenceError):
                await complete_generation_request(
                    session,
                    owner_id=owner_id,
                    command=PersistUtteranceCommand(
                        utterance_id=uuid4(),
                        session_id=session_id,
                        generation_request_id=rollback_request_id,
                        content="This second official utterance must roll back.",
                        persisted_at=NOW,
                    ),
                )
        async with session_factory() as session:
            rolled_back = await session.get(LlmGenerationRequest, rollback_request_id)
            assert rolled_back is not None and rolled_back.status == "RUNNING"
            assert rolled_back.completed_at is None
            assert (
                await session.scalar(select(func.count()).select_from(AiUtterance)) == 1
            )
            assert (
                await session.scalar(
                    select(func.count())
                    .select_from(DiscussionEvent)
                    .where(
                        DiscussionEvent.session_id == session_id,
                        DiscussionEvent.event_type == "participant.utterance.created",
                    )
                )
                == 1
            )

        fail_command = FailGenerationCommand(
            session_id=session_id,
            generation_request_id=rollback_request_id,
            failure_code=GenerationFailureCode.PARTIAL_GENERATION,
            failed_at=NOW,
        )
        async with session_factory() as session:
            failed = await fail_generation_request(
                session, owner_id=owner_id, command=fail_command
            )
        assert failed.status is GenerationRequestStatus.FAILED
        assert failed.failure_code is GenerationFailureCode.PARTIAL_GENERATION
        assert failed.utterance_id is None
        async with session_factory() as session:
            with pytest.raises(GenerationStateError):
                await complete_generation_request(
                    session,
                    owner_id=owner_id,
                    command=PersistUtteranceCommand(
                        utterance_id=uuid4(),
                        session_id=session_id,
                        generation_request_id=rollback_request_id,
                        content="A failed request cannot become an utterance.",
                        persisted_at=NOW,
                    ),
                )

        invalid_owner_request = _request(
            request_id=uuid4(),
            session_id=session_id,
            participant_id=participants[2].id,
            grant_id=grant_id,
        )
        async with session_factory() as session:
            with pytest.raises(GenerationContextError):
                await create_generation_request(
                    session, owner_id=owner_id, command=invalid_owner_request
                )

        async with session_factory() as session:
            aggregate = await session.get(SimulationSession, session_id)
            stored_prompt = await session.get(PromptVersion, PROMPT_ID)
            stored_request = await session.get(LlmGenerationRequest, request_id)
            utterance = await session.get(AiUtterance, utterance_id)
            assert aggregate is not None
            assert aggregate.status == "OPENING_STATEMENTS"
            assert aggregate.current_floor_grant_id == grant_id
            assert stored_prompt is not None and stored_request is not None
            assert utterance is not None
            assert stored_request.prompt_version_id == PROMPT_ID
            assert stored_request.provider_identifier == "hosted-provider"
            assert stored_request.model_identifier == "discussion-model-v1"
            assert stored_prompt.template_text == _prompt().template_text
            assert utterance.generation_request_id == stored_request.id
            assert participants[1].question_persona_assignment_id is not None
            serialized = repr(
                [stored_request.request_metadata, stored_request.failure_code]
            ).lower()
            for forbidden in (
                "private_stance",
                "persona_calibration",
                "hidden_ranking",
                "internal_prompt_variables",
                "provider_secret",
                "api_key",
            ):
                assert forbidden not in serialized

        async with session_factory() as session:
            with pytest.raises(PromptVersionMutationError):
                await publish_prompt_version(session, _prompt("Mutated prompt text."))


def test_ai_runtime_provenance_lifecycle_failure_and_constraints_are_durable(
    migrated_database: TemporaryDatabaseContext,
) -> None:
    run_async(lambda: _verify_ai_runtime_persistence(migrated_database))


def test_every_completed_return_path_requires_the_same_public_event_proof(
    migrated_database: TemporaryDatabaseContext,
) -> None:
    async def exercise() -> None:
        async with _runtime_context(migrated_database) as context:
            session_factory, owner_id, session_id, participants, grant_id = context
            request_id = uuid4()
            request_command = _request(
                request_id=request_id,
                session_id=session_id,
                participant_id=participants[1].id,
                grant_id=grant_id,
            )
            start_command = StartGenerationCommand(
                session_id=session_id,
                generation_request_id=request_id,
                started_at=NOW,
            )
            complete_command = PersistUtteranceCommand(
                utterance_id=uuid4(),
                session_id=session_id,
                generation_request_id=request_id,
                content="Strict completed triple proof.",
                persisted_at=NOW,
            )
            async with session_factory() as session:
                await create_generation_request(
                    session, owner_id=owner_id, command=request_command
                )
            async with session_factory() as session:
                await start_generation_request(
                    session, owner_id=owner_id, command=start_command
                )
            async with session_factory() as session:
                await complete_generation_request(
                    session, owner_id=owner_id, command=complete_command
                )
            async with session_factory() as session:
                async with session.begin():
                    event = await session.scalar(
                        select(DiscussionEvent).where(
                            DiscussionEvent.session_id == session_id,
                            DiscussionEvent.event_type
                            == "participant.utterance.created",
                        )
                    )
                    assert event is not None
                    event.payload = {**event.payload, "content": "conflicting event"}

            async with session_factory() as session:
                with pytest.raises(GenerationRequestConflictError):
                    await create_generation_request(
                        session, owner_id=owner_id, command=request_command
                    )
            async with session_factory() as session:
                async with session.begin():
                    event = await session.scalar(
                        select(DiscussionEvent).where(
                            DiscussionEvent.session_id == session_id,
                            DiscussionEvent.event_type
                            == "participant.utterance.created",
                        )
                    )
                    aggregate = await session.get(SimulationSession, session_id)
                    assert event is not None
                    assert aggregate is not None
                    event.payload = {
                        **event.payload,
                        "content": complete_command.content,
                    }
                    aggregate.last_sequence += 1
                    session.add(
                        DiscussionEvent(
                            session_id=session_id,
                            sequence=aggregate.last_sequence,
                            event_version=event.event_version,
                            event_type=event.event_type,
                            causation_action_id=None,
                            payload=event.payload,
                            occurred_at=event.occurred_at,
                        )
                    )

            async with session_factory() as session:
                with pytest.raises(GenerationRequestConflictError):
                    await claim_generation_request(
                        session, owner_id=owner_id, command=start_command
                    )
            async with session_factory() as session:
                async with session.begin():
                    events = tuple(
                        (
                            await session.scalars(
                                select(DiscussionEvent).where(
                                    DiscussionEvent.session_id == session_id,
                                    DiscussionEvent.event_type
                                    == "participant.utterance.created",
                                )
                            )
                        ).all()
                    )
                    assert len(events) == 2
                    for event in events:
                        await session.delete(event)

            async with session_factory() as session:
                with pytest.raises(GenerationRequestConflictError):
                    await create_generation_request(
                        session, owner_id=owner_id, command=request_command
                    )
            async with session_factory() as session:
                with pytest.raises(GenerationRequestConflictError):
                    await claim_generation_request(
                        session, owner_id=owner_id, command=start_command
                    )
            async with session_factory() as session:
                with pytest.raises(GenerationRequestConflictError):
                    await complete_generation_request(
                        session, owner_id=owner_id, command=complete_command
                    )

    run_async(exercise)


def test_effective_prompt_selector_uses_highest_valid_version_and_exact_retirement(
    migrated_database: TemporaryDatabaseContext,
) -> None:
    async def exercise() -> None:
        engine = create_database_engine(migrated_database.database_settings())
        session_factory = create_database_session_factory(engine)
        publication = AI_CANDIDATE_TURN_V2.published_at
        retired_key = "RETIRED_CANDIDATE_TURN"
        retired_v1 = PromptVersionDefinition(
            id=UUID("57000000-0000-4000-8000-000000000001"),
            prompt_key=retired_key,
            version_number=1,
            purpose_code="CANDIDATE_UTTERANCE",
            template_text="Retirement boundary v1.",
            created_at=publication - timedelta(hours=1),
            published_at=publication - timedelta(hours=1),
        )
        retired_v2 = PromptVersionDefinition(
            id=UUID("57000000-0000-4000-8000-000000000002"),
            prompt_key=retired_key,
            version_number=2,
            purpose_code="CANDIDATE_UTTERANCE",
            template_text="Retirement boundary v2.",
            created_at=publication,
            published_at=publication,
            retired_at=publication + timedelta(hours=1),
        )
        try:
            async with session_factory() as session:
                await publish_prompt_version(session, _prompt())
            async with session_factory() as session:
                await publish_prompt_version(session, AI_CANDIDATE_TURN_V2)
            async with session_factory() as session:
                await publish_prompt_version(session, retired_v1)
            async with session_factory() as session:
                await publish_prompt_version(session, retired_v2)

            async with session_factory() as session:
                assert retired_v2.retired_at is not None
                before_v2 = await _select_effective_prompt_version(
                    session,
                    prompt_key="AI_CANDIDATE_TURN",
                    purpose_code="CANDIDATE_UTTERANCE",
                    effective_at=publication - timedelta(microseconds=1),
                )
                at_v2 = await _select_effective_prompt_version(
                    session,
                    prompt_key="AI_CANDIDATE_TURN",
                    purpose_code="CANDIDATE_UTTERANCE",
                    effective_at=publication,
                )
                after_v2 = await _select_effective_prompt_version(
                    session,
                    prompt_key="AI_CANDIDATE_TURN",
                    purpose_code="CANDIDATE_UTTERANCE",
                    effective_at=publication + timedelta(days=1),
                )
                at_retirement = await _select_effective_prompt_version(
                    session,
                    prompt_key=retired_key,
                    purpose_code="CANDIDATE_UTTERANCE",
                    effective_at=retired_v2.retired_at,
                )
                missing = await _select_effective_prompt_version(
                    session,
                    prompt_key="MISSING_PROMPT",
                    purpose_code="CANDIDATE_UTTERANCE",
                    effective_at=publication,
                )

            assert before_v2 is not None and before_v2.id == PROMPT_ID
            assert at_v2 is not None and at_v2.id == AI_CANDIDATE_TURN_V2.id
            assert after_v2 is not None and after_v2.id == AI_CANDIDATE_TURN_V2.id
            assert at_retirement is not None and at_retirement.id == retired_v1.id
            assert missing is None
        finally:
            await dispose_database_engine(engine)

    run_async(exercise)


def test_public_event_construction_failure_rolls_back_completed_triple(
    migrated_database: TemporaryDatabaseContext,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def exercise() -> None:
        async with _runtime_context(migrated_database) as context:
            session_factory, owner_id, session_id, participants, grant_id = context
            request_id = uuid4()
            request_command = _request(
                request_id=request_id,
                session_id=session_id,
                participant_id=participants[1].id,
                grant_id=grant_id,
            )
            async with session_factory() as session:
                await create_generation_request(
                    session, owner_id=owner_id, command=request_command
                )
            async with session_factory() as session:
                await start_generation_request(
                    session,
                    owner_id=owner_id,
                    command=StartGenerationCommand(
                        session_id=session_id,
                        generation_request_id=request_id,
                        started_at=NOW,
                    ),
                )
            async with session_factory() as session:
                before = await session.get(SimulationSession, session_id)
                assert before is not None
                prior_watermark = before.last_sequence

            def event_failure(**_kwargs: object):
                raise ValueError("test-only public event construction failure")

            monkeypatch.setattr(
                ai_runtime_service,
                "participant_utterance_created_event",
                event_failure,
            )
            async with session_factory() as session:
                with pytest.raises(AiRuntimePersistenceError):
                    await complete_generation_request(
                        session,
                        owner_id=owner_id,
                        command=PersistUtteranceCommand(
                            utterance_id=uuid4(),
                            session_id=session_id,
                            generation_request_id=request_id,
                            content="Must roll back with its event.",
                            persisted_at=NOW,
                        ),
                    )
            async with session_factory() as session:
                request = await session.get(LlmGenerationRequest, request_id)
                aggregate = await session.get(SimulationSession, session_id)
                utterance_count = await session.scalar(
                    select(func.count())
                    .select_from(AiUtterance)
                    .where(AiUtterance.generation_request_id == request_id)
                )
                event_count = await session.scalar(
                    select(func.count())
                    .select_from(DiscussionEvent)
                    .where(
                        DiscussionEvent.session_id == session_id,
                        DiscussionEvent.event_type == "participant.utterance.created",
                    )
                )
            assert request is not None
            assert request.status == GenerationRequestStatus.RUNNING
            assert aggregate is not None
            assert aggregate.last_sequence == prior_watermark
            assert utterance_count == 0
            assert event_count == 0

    run_async(exercise)
