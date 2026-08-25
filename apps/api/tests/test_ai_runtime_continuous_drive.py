import asyncio
from collections.abc import Sequence
from typing import Any, cast
from uuid import UUID, uuid4

import pytest

from group_interview_arena_api.modules.ai_runtime.continuous import (
    MAX_AUTOMATED_AI_TURNS_PER_DRIVE,
    ContinuousAiDriveOutcome,
    ContinuousAiDriveResult,
    drive_continuous_ai,
)
from group_interview_arena_api.modules.ai_runtime.domain import GenerationFailureCode
from group_interview_arena_api.modules.ai_runtime.generation import RawGenerationSuccess
from group_interview_arena_api.modules.ai_runtime.orchestration import (
    SingleAiTurnOutcome,
    SingleAiTurnResult,
)
from group_interview_arena_api.modules.ai_runtime.runtime import (
    RuntimeGenerationOutcome,
)
from group_interview_arena_api.modules.floor_control.scheduler import (
    V0_1_SCHEDULER_POLICY,
)


async def _provider(_input: object) -> RawGenerationSuccess:
    return RawGenerationSuccess(content="network-free")


def _result(
    outcome: SingleAiTurnOutcome,
    *,
    processed: UUID | None = None,
    next_grant: UUID | None = None,
    advanced: bool = False,
    runtime_outcome: RuntimeGenerationOutcome | None = None,
    failure_code: GenerationFailureCode | None = None,
) -> SingleAiTurnResult:
    return SingleAiTurnResult(
        outcome=outcome,
        processed_floor_grant_id=processed,
        next_floor_grant_id=next_grant,
        release_action_id=uuid4() if advanced else None,
        runtime_outcome=runtime_outcome,
        failure_code=failure_code,
    )


async def _drive_with_results(
    monkeypatch: pytest.MonkeyPatch,
    results: Sequence[SingleAiTurnResult],
) -> tuple[ContinuousAiDriveResult, int]:
    from group_interview_arena_api.modules.ai_runtime import continuous

    calls = 0

    async def fake_single_turn(*_args: object, **_kwargs: object) -> SingleAiTurnResult:
        nonlocal calls
        result = results[calls]
        calls += 1
        return result

    monkeypatch.setattr(continuous, "drive_single_ai_turn", fake_single_turn)
    continuous_result = await drive_continuous_ai(
        cast(Any, object()),
        owner_id=uuid4(),
        session_id=uuid4(),
        provider=_provider,
        provider_identifier="test-provider",
        model_identifier="test-model",
        configuration_version="TEST_V1",
        scheduling_policy=V0_1_SCHEDULER_POLICY,
    )
    return continuous_result, calls


def test_next_ai_continues_until_next_human_and_counts_advanced_turns(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def exercise() -> None:
        first = uuid4()
        second = uuid4()
        human = uuid4()
        result, calls = await _drive_with_results(
            monkeypatch,
            (
                _result(
                    SingleAiTurnOutcome.NEXT_AI_GRANTED,
                    processed=first,
                    next_grant=second,
                    advanced=True,
                ),
                _result(
                    SingleAiTurnOutcome.NEXT_HUMAN_GRANTED,
                    processed=second,
                    next_grant=human,
                    advanced=True,
                ),
            ),
        )

        assert result.outcome is ContinuousAiDriveOutcome.WAITING_FOR_HUMAN
        assert result.automated_ai_turns_advanced == 2
        assert result.last_turn_result is not None
        assert result.last_turn_result.processed_floor_grant_id == second
        assert calls == 2

    asyncio.run(exercise())


@pytest.mark.parametrize(
    ("single_outcome", "continuous_outcome"),
    (
        (
            SingleAiTurnOutcome.WAITING_FOR_HUMAN,
            ContinuousAiDriveOutcome.WAITING_FOR_HUMAN,
        ),
        (
            SingleAiTurnOutcome.NEXT_HUMAN_GRANTED,
            ContinuousAiDriveOutcome.WAITING_FOR_HUMAN,
        ),
        (
            SingleAiTurnOutcome.NO_CURRENT_WORK,
            ContinuousAiDriveOutcome.NO_CURRENT_WORK,
        ),
        (
            SingleAiTurnOutcome.NOT_APPLICABLE,
            ContinuousAiDriveOutcome.NOT_APPLICABLE,
        ),
        (SingleAiTurnOutcome.NO_GRANT, ContinuousAiDriveOutcome.NO_GRANT),
        (
            SingleAiTurnOutcome.INTERVENTION_REQUESTED,
            ContinuousAiDriveOutcome.INTERVENTION_REQUESTED,
        ),
        (
            SingleAiTurnOutcome.RECONCILIATION_REQUIRED,
            ContinuousAiDriveOutcome.RECONCILIATION_REQUIRED,
        ),
        (
            SingleAiTurnOutcome.STATE_CHANGED,
            ContinuousAiDriveOutcome.STATE_CHANGED,
        ),
    ),
)
def test_frozen_boundaries_stop_after_one_kernel_call(
    monkeypatch: pytest.MonkeyPatch,
    single_outcome: SingleAiTurnOutcome,
    continuous_outcome: ContinuousAiDriveOutcome,
) -> None:
    async def exercise() -> None:
        result, calls = await _drive_with_results(
            monkeypatch,
            (_result(single_outcome),),
        )

        assert result.outcome is continuous_outcome
        assert result.automated_ai_turns_advanced == 0
        assert calls == 1

    asyncio.run(exercise())


def test_confirmed_failed_turn_continues_to_distinct_next_ai_without_retry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def exercise() -> None:
        failed_grant = uuid4()
        next_ai_grant = uuid4()
        result, calls = await _drive_with_results(
            monkeypatch,
            (
                _result(
                    SingleAiTurnOutcome.NEXT_AI_GRANTED,
                    processed=failed_grant,
                    next_grant=next_ai_grant,
                    advanced=True,
                    runtime_outcome=RuntimeGenerationOutcome.FAILED,
                    failure_code=GenerationFailureCode.TIMEOUT,
                ),
                _result(
                    SingleAiTurnOutcome.WAITING_FOR_HUMAN,
                    processed=next_ai_grant,
                ),
            ),
        )

        assert result.outcome is ContinuousAiDriveOutcome.WAITING_FOR_HUMAN
        assert result.automated_ai_turns_advanced == 1
        assert calls == 2

    asyncio.run(exercise())


def test_exact_budget_stops_before_ninth_kernel_invocation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def exercise() -> None:
        grants = [uuid4() for _ in range(MAX_AUTOMATED_AI_TURNS_PER_DRIVE + 1)]
        results = tuple(
            _result(
                SingleAiTurnOutcome.NEXT_AI_GRANTED,
                processed=grants[index],
                next_grant=grants[index + 1],
                advanced=True,
            )
            for index in range(MAX_AUTOMATED_AI_TURNS_PER_DRIVE)
        )
        result, calls = await _drive_with_results(monkeypatch, results)

        assert result.outcome is ContinuousAiDriveOutcome.BUDGET_EXHAUSTED
        assert result.automated_ai_turns_advanced == 8
        assert result.last_turn_result is results[-1]
        assert calls == 8

    asyncio.run(exercise())


def test_scheduler_only_crash_e_recovery_does_not_consume_budget(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def exercise() -> None:
        released = uuid4()
        next_ai = uuid4()
        human = uuid4()
        result, calls = await _drive_with_results(
            monkeypatch,
            (
                _result(
                    SingleAiTurnOutcome.NEXT_AI_GRANTED,
                    processed=released,
                    next_grant=next_ai,
                    advanced=False,
                ),
                _result(
                    SingleAiTurnOutcome.NEXT_HUMAN_GRANTED,
                    processed=next_ai,
                    next_grant=human,
                    advanced=True,
                ),
            ),
        )

        assert result.outcome is ContinuousAiDriveOutcome.WAITING_FOR_HUMAN
        assert result.automated_ai_turns_advanced == 1
        assert calls == 2

    asyncio.run(exercise())


@pytest.mark.parametrize("invalid_kind", ("missing", "same"))
def test_inconsistent_next_ai_fails_closed_without_busy_loop(
    monkeypatch: pytest.MonkeyPatch,
    invalid_kind: str,
) -> None:
    async def exercise() -> None:
        processed = uuid4()
        result, calls = await _drive_with_results(
            monkeypatch,
            (
                _result(
                    SingleAiTurnOutcome.NEXT_AI_GRANTED,
                    processed=processed,
                    next_grant=None if invalid_kind == "missing" else processed,
                    advanced=True,
                ),
            ),
        )

        assert result.outcome is ContinuousAiDriveOutcome.RECONCILIATION_REQUIRED
        assert result.automated_ai_turns_advanced == 1
        assert calls == 1

    asyncio.run(exercise())


def test_repeated_progress_checkpoint_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def exercise() -> None:
        processed = uuid4()
        next_grant = uuid4()
        repeated = _result(
            SingleAiTurnOutcome.NEXT_AI_GRANTED,
            processed=processed,
            next_grant=next_grant,
        )
        result, calls = await _drive_with_results(
            monkeypatch,
            (repeated, repeated),
        )

        assert result.outcome is ContinuousAiDriveOutcome.RECONCILIATION_REQUIRED
        assert result.automated_ai_turns_advanced == 0
        assert calls == 2

    asyncio.run(exercise())


def test_cancellation_propagates(monkeypatch: pytest.MonkeyPatch) -> None:
    async def exercise() -> None:
        from group_interview_arena_api.modules.ai_runtime import continuous

        async def cancelled(*_args: object, **_kwargs: object) -> SingleAiTurnResult:
            raise asyncio.CancelledError

        monkeypatch.setattr(continuous, "drive_single_ai_turn", cancelled)
        with pytest.raises(asyncio.CancelledError):
            await drive_continuous_ai(
                cast(Any, object()),
                owner_id=uuid4(),
                session_id=uuid4(),
                provider=_provider,
                provider_identifier="test-provider",
                model_identifier="test-model",
                configuration_version="TEST_V1",
                scheduling_policy=V0_1_SCHEDULER_POLICY,
            )

    asyncio.run(exercise())
