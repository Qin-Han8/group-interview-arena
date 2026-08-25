import asyncio
from collections.abc import Callable, Coroutine
from datetime import UTC, datetime, timedelta
from typing import Any, Protocol
from uuid import UUID, uuid4

import pytest
from sqlalchemy import URL, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from group_interview_arena_api.core.config import DatabaseSettings
from group_interview_arena_api.db import (
    DiscussionEvent,
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
from group_interview_arena_api.modules.ai_runtime.continuous import drive_continuous_ai
from group_interview_arena_api.modules.ai_runtime.domain import PromptVersionDefinition
from group_interview_arena_api.modules.ai_runtime.generation import (
    RawGenerationSuccess,
    RuntimeGenerationInput,
)
from group_interview_arena_api.modules.ai_runtime.service import publish_prompt_version
from group_interview_arena_api.modules.discussion_sessions import (
    progression,
    utterances,
)
from group_interview_arena_api.modules.discussion_sessions.domain import (
    PhaseDurationPlan,
    SessionCommand,
    SessionStatus,
)
from group_interview_arena_api.modules.discussion_sessions.public_events import (
    project_public_events,
)
from group_interview_arena_api.modules.discussion_sessions.service import (
    apply_session_command,
    create_session,
    get_session_snapshot,
    load_reconnect_events,
    reconcile_session_deadline,
)
from group_interview_arena_api.modules.floor_control.domain import (
    FloorDecisionOutcome,
    FloorDecisionRecord,
    FloorPolicyReason,
    GrantFloorCommand,
    ParticipantAvailability,
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

NOW = datetime(2026, 8, 25, 2, 0, tzinfo=UTC)
PROMPT_ID = UUID("54000000-0000-4000-8000-000000000001")
CURRENT_STANCE_SENTINEL = "CURRENT_STANCE_ONLY_P1_5F_2"
OTHER_STANCE_SENTINEL = "OTHER_STANCE_FORBIDDEN_P1_5F_2"
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


def _human_grant_decision(
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


def test_composed_human_scheduler_ai_transport_is_ordered_recoverable_and_private(
    migrated_database: TemporaryDatabaseContext,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def exercise() -> None:
        engine = create_database_engine(migrated_database.database_settings())
        session_factory: async_sessionmaker[AsyncSession] = (
            create_database_session_factory(engine)
        )
        provider_calls = 0
        rendered_prompt = ""
        try:
            await seed_question_persona_foundation(session_factory)
            owner_id = uuid4()
            async with session_factory() as session:
                async with session.begin():
                    session.add(
                        User(
                            id=owner_id,
                            username=f"text_transport_{owner_id.hex[:10]}",
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
                active = await get_session_snapshot(
                    session,
                    owner_id=owner_id,
                    session_id=created.session_id,
                )
                participants = tuple(
                    (
                        await session.scalars(
                            select(SessionParticipant)
                            .where(SessionParticipant.session_id == created.session_id)
                            .order_by(SessionParticipant.seat_order)
                        )
                    ).all()
                )
            assert active.phase_deadline_at is not None
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
                    for participant in participants[2:]:
                        stored = await session.get(SessionParticipant, participant.id)
                        assert stored is not None
                        stored.availability = ParticipantAvailability.UNAVAILABLE

            human_grant_id = uuid4()
            async with session_factory() as session:
                simulation_session = await session.get(
                    SimulationSession, created.session_id
                )
            assert simulation_session is not None
            async with session_factory() as session:
                await apply_floor_command(
                    session,
                    owner_id=owner_id,
                    command=GrantFloorCommand(
                        session_id=created.session_id,
                        action_id=uuid4(),
                        grant_id=human_grant_id,
                        decision=_human_grant_decision(
                            participant_id=participants[0].id,
                            expected_last_sequence=simulation_session.last_sequence,
                        ),
                    ),
                )

            human_action_id = uuid4()
            async with session_factory() as session:
                human_commit = await utterances.submit_human_utterance(
                    session,
                    owner_id=owner_id,
                    command=utterances.SubmitHumanUtterance(
                        session_id=created.session_id,
                        action_id=human_action_id,
                        floor_grant_id=human_grant_id,
                        content="  Human contribution stays exact.  ",
                        received_at=active.phase_deadline_at - timedelta(seconds=1),
                    ),
                )
            assert [event.event_type for event in human_commit.events] == [
                "participant.utterance.created",
                "floor.released",
            ]
            assert (
                human_commit.events[1].sequence == human_commit.events[0].sequence + 1
            )

            async def provider(
                generation_input: RuntimeGenerationInput,
            ) -> RawGenerationSuccess:
                nonlocal provider_calls, rendered_prompt
                provider_calls += 1
                rendered_prompt = generation_input.rendered_prompt
                return RawGenerationSuccess(content="AI public contribution.")

            async def drive_test_ai(
                factory: async_sessionmaker[AsyncSession],
                *,
                owner_id: UUID,
                session_id: UUID,
            ):
                return await drive_continuous_ai(
                    factory,
                    owner_id=owner_id,
                    session_id=session_id,
                    provider=provider,
                    provider_identifier="local-test-provider",
                    model_identifier="text-transport-test-model",
                    configuration_version="P1_5F_2_TEST",
                    scheduling_policy=V0_1_SCHEDULER_POLICY,
                )

            monkeypatch.setattr(
                progression,
                "drive_configured_ai_session",
                drive_test_ai,
            )
            first_progression = await progression.resume_discussion_progression(
                session_factory,
                owner_id=owner_id,
                session_id=created.session_id,
            )
            assert first_progression.outcome.value == "ai_drive_completed", (
                first_progression
            )

            async with session_factory() as session:
                stored_events = await load_reconnect_events(
                    session,
                    owner_id=owner_id,
                    session_id=created.session_id,
                    after_sequence=0,
                )
                public_events = await project_public_events(session, stored_events)
                watermark = await session.get(SimulationSession, created.session_id)
            assert watermark is not None
            serialized = "".join(event.model_dump_json() for event in public_events)
            utterance_events = [
                event
                for event in public_events
                if event.type == "participant.utterance.created"
            ]
            assert [event.payload["actor_kind"] for event in utterance_events] == [
                "HUMAN",
                "AI",
            ]
            assert [event.action_id for event in utterance_events] == [
                human_action_id,
                None,
            ]
            assert all(
                event.action_id is None
                for event in public_events
                if event.type in {"floor.granted", "floor.released"}
                and event.sequence > human_commit.events[1].sequence
            )
            assert [event.sequence for event in public_events] == sorted(
                event.sequence for event in public_events
            )
            assert CURRENT_STANCE_SENTINEL in rendered_prompt
            assert OTHER_STANCE_SENTINEL not in rendered_prompt
            assert CURRENT_STANCE_SENTINEL not in serialized
            assert OTHER_STANCE_SENTINEL not in serialized

            prior_watermark = watermark.last_sequence
            replay = await progression.resume_discussion_progression(
                session_factory,
                owner_id=owner_id,
                session_id=created.session_id,
            )
            async with session_factory() as session:
                recovered = await session.get(SimulationSession, created.session_id)
                durable_events = tuple(
                    (
                        await session.scalars(
                            select(DiscussionEvent)
                            .where(DiscussionEvent.session_id == created.session_id)
                            .order_by(DiscussionEvent.sequence)
                        )
                    ).all()
                )
            assert recovered is not None
            assert replay.outcome.value in {"no_work", "next_human_granted"}
            assert provider_calls == 1
            assert recovered.last_sequence == prior_watermark
            assert len({event.sequence for event in durable_events}) == len(
                durable_events
            )
        finally:
            await dispose_database_engine(engine)

    run_async(exercise)
