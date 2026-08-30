from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from group_interview_arena_api.modules.discussion_memory.derivation import (
    MemoryDerivationInput,
    PublicMemoryUtterance,
)
from group_interview_arena_api.modules.discussion_memory.domain import (
    DiscussionMemoryProjection,
    MemoryPolicy,
)
from group_interview_arena_api.modules.discussion_memory.working_context import (
    DiscussionContextMode,
    DiscussionWorkingContextUnavailable,
    build_discussion_working_context,
    select_compaction_episode,
)


def _utterances(
    count: int, *, content: str = "public"
) -> tuple[PublicMemoryUtterance, ...]:
    session_id = uuid4()
    return tuple(
        PublicMemoryUtterance(
            session_id=session_id,
            sequence=index * 2 + 1,
            participant_id=uuid4(),
            seat_order=index + 1,
            actor_kind="HUMAN" if index == 0 else "AI",
            phase="EXPLORATION",
            content=f"{content}-{index}",
        )
        for index in range(count)
    )


def test_hysteresis_calls_nothing_below_high_and_compacts_oldest_toward_low() -> None:
    policy = MemoryPolicy(high_watermark_utterances=6, low_watermark_utterances=3)
    assert select_compaction_episode(_utterances(5), policy=policy) == ()
    selected = select_compaction_episode(_utterances(6), policy=policy)
    assert tuple(item.sequence for item in selected) == (1, 3, 5)


def test_large_backlog_selects_one_closed_bounded_derivation_episode() -> None:
    backlog = _utterances(100)
    selected = select_compaction_episode(backlog, policy=MemoryPolicy())
    assert len(selected) == 64
    assert selected == backlog[:64]
    assert (
        MemoryDerivationInput(
            session_id=selected[0].session_id,
            previous_memory=DiscussionMemoryProjection.empty(),
            utterances=selected,
        ).utterances
        == selected
    )


def test_memory_plus_complete_raw_tail_has_exact_provenance_and_dynamic_time() -> None:
    tail = _utterances(2)
    now = datetime(2026, 8, 30, tzinfo=UTC)
    context = build_discussion_working_context(
        projection=DiscussionMemoryProjection.empty(),
        complete_public_history=tail,
        phase="EXPLORATION",
        now=now,
        phase_deadline_at=now + timedelta(seconds=91),
        policy=MemoryPolicy(),
    )
    assert context.context_mode is DiscussionContextMode.MEMORY_WITH_RAW_TAIL
    assert context.memory_revision == 0
    assert context.memory_source_through_sequence == 0
    assert context.context_source_through_sequence == tail[-1].sequence
    assert context.remaining_time_seconds == 91
    assert context.recent_public_utterances == tail


def test_failed_compaction_uses_complete_raw_fallback_or_rejects_without_truncation() -> (
    None
):
    history = _utterances(6, content="x")
    policy = MemoryPolicy(
        safe_raw_fallback_max_utterances=6,
        safe_raw_fallback_max_codepoints=4000,
        recent_raw_max_utterances=2,
    )
    fallback = build_discussion_working_context(
        projection=DiscussionMemoryProjection.empty(),
        complete_public_history=history,
        phase="EXPLORATION",
        now=datetime.now(UTC),
        phase_deadline_at=None,
        policy=policy,
        compaction_failed=True,
    )
    assert fallback.context_mode is DiscussionContextMode.SAFE_RAW_FALLBACK
    assert fallback.recent_public_utterances == history
    with pytest.raises(DiscussionWorkingContextUnavailable):
        build_discussion_working_context(
            projection=DiscussionMemoryProjection.empty(),
            complete_public_history=_utterances(7, content="x"),
            phase="EXPLORATION",
            now=datetime.now(UTC),
            phase_deadline_at=None,
            policy=policy,
            compaction_failed=True,
        )
