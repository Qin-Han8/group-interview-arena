from __future__ import annotations

from enum import StrEnum
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from group_interview_arena_api.modules.ai_runtime.domain import ClosedDomainModel
from group_interview_arena_api.modules.ai_runtime.generation import GenerationProvider
from group_interview_arena_api.modules.ai_runtime.orchestration import (
    SingleAiTurnOutcome,
    SingleAiTurnResult,
    drive_single_ai_turn,
)
from group_interview_arena_api.modules.floor_control.scheduler import SchedulerPolicy

MAX_AUTOMATED_AI_TURNS_PER_DRIVE = 8


class ContinuousAiDriveOutcome(StrEnum):
    WAITING_FOR_HUMAN = "waiting_for_human"
    NO_CURRENT_WORK = "no_current_work"
    NOT_APPLICABLE = "not_applicable"
    NO_GRANT = "no_grant"
    INTERVENTION_REQUESTED = "intervention_requested"
    RECONCILIATION_REQUIRED = "reconciliation_required"
    STATE_CHANGED = "state_changed"
    BUDGET_EXHAUSTED = "budget_exhausted"


class ContinuousAiDriveResult(ClosedDomainModel):
    outcome: ContinuousAiDriveOutcome
    automated_ai_turns_advanced: int
    last_turn_result: SingleAiTurnResult | None = None


_STOP_OUTCOMES = {
    SingleAiTurnOutcome.WAITING_FOR_HUMAN: ContinuousAiDriveOutcome.WAITING_FOR_HUMAN,
    SingleAiTurnOutcome.NEXT_HUMAN_GRANTED: ContinuousAiDriveOutcome.WAITING_FOR_HUMAN,
    SingleAiTurnOutcome.NO_CURRENT_WORK: ContinuousAiDriveOutcome.NO_CURRENT_WORK,
    SingleAiTurnOutcome.NOT_APPLICABLE: ContinuousAiDriveOutcome.NOT_APPLICABLE,
    SingleAiTurnOutcome.NO_GRANT: ContinuousAiDriveOutcome.NO_GRANT,
    SingleAiTurnOutcome.INTERVENTION_REQUESTED: (
        ContinuousAiDriveOutcome.INTERVENTION_REQUESTED
    ),
    SingleAiTurnOutcome.RECONCILIATION_REQUIRED: (
        ContinuousAiDriveOutcome.RECONCILIATION_REQUIRED
    ),
    SingleAiTurnOutcome.STATE_CHANGED: ContinuousAiDriveOutcome.STATE_CHANGED,
}


def _result(
    outcome: ContinuousAiDriveOutcome,
    *,
    automated_ai_turns_advanced: int,
    last_turn_result: SingleAiTurnResult,
) -> ContinuousAiDriveResult:
    return ContinuousAiDriveResult(
        outcome=outcome,
        automated_ai_turns_advanced=automated_ai_turns_advanced,
        last_turn_result=last_turn_result,
    )


async def drive_continuous_ai(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    owner_id: UUID,
    session_id: UUID,
    provider: GenerationProvider,
    provider_identifier: str,
    model_identifier: str,
    configuration_version: str,
    scheduling_policy: SchedulerPolicy,
) -> ContinuousAiDriveResult:
    automated_ai_turns_advanced = 0
    seen_progress: set[tuple[UUID, UUID]] = set()

    while True:
        turn_result = await drive_single_ai_turn(
            session_factory,
            owner_id=owner_id,
            session_id=session_id,
            provider=provider,
            provider_identifier=provider_identifier,
            model_identifier=model_identifier,
            configuration_version=configuration_version,
            scheduling_policy=scheduling_policy,
        )

        if turn_result.release_action_id is not None:
            automated_ai_turns_advanced += 1

        if turn_result.outcome is not SingleAiTurnOutcome.NEXT_AI_GRANTED:
            return _result(
                _STOP_OUTCOMES[turn_result.outcome],
                automated_ai_turns_advanced=automated_ai_turns_advanced,
                last_turn_result=turn_result,
            )

        processed_grant_id = turn_result.processed_floor_grant_id
        next_grant_id = turn_result.next_floor_grant_id
        if (
            processed_grant_id is None
            or next_grant_id is None
            or processed_grant_id == next_grant_id
        ):
            return _result(
                ContinuousAiDriveOutcome.RECONCILIATION_REQUIRED,
                automated_ai_turns_advanced=automated_ai_turns_advanced,
                last_turn_result=turn_result,
            )

        progress = (processed_grant_id, next_grant_id)
        if progress in seen_progress:
            return _result(
                ContinuousAiDriveOutcome.RECONCILIATION_REQUIRED,
                automated_ai_turns_advanced=automated_ai_turns_advanced,
                last_turn_result=turn_result,
            )
        seen_progress.add(progress)

        if automated_ai_turns_advanced >= MAX_AUTOMATED_AI_TURNS_PER_DRIVE:
            return _result(
                ContinuousAiDriveOutcome.BUDGET_EXHAUSTED,
                automated_ai_turns_advanced=automated_ai_turns_advanced,
                last_turn_result=turn_result,
            )
