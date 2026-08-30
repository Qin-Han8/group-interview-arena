from __future__ import annotations

import json
from datetime import datetime
from typing import Self

from pydantic import Field, model_validator

from group_interview_arena_api.modules.discussion_memory.derivation import (
    PublicMemoryUtterance,
)
from group_interview_arena_api.modules.discussion_memory.domain import (
    DiscussionContextMode,
    DiscussionMemoryProjection,
    MemoryDomainModel,
    MemoryItem,
    MemoryItemStatus,
    MemoryPolicy,
)

DISCUSSION_WORKING_CONTEXT_V1 = "DISCUSSION_WORKING_CONTEXT_V1"


class DiscussionWorkingContextUnavailable(RuntimeError):
    pass


class DiscussionWorkingContext(MemoryDomainModel):
    working_context_version: str = DISCUSSION_WORKING_CONTEXT_V1
    context_mode: DiscussionContextMode
    memory_revision: int = Field(ge=0)
    memory_source_through_sequence: int = Field(ge=0)
    context_source_through_sequence: int = Field(ge=0)
    active_proposals: tuple[MemoryItem, ...]
    active_evaluation_criteria: tuple[MemoryItem, ...]
    active_agreements: tuple[MemoryItem, ...]
    active_conflicts: tuple[MemoryItem, ...]
    current_decision: MemoryItem | None
    recent_public_utterances: tuple[PublicMemoryUtterance, ...]
    phase: str = Field(min_length=1, max_length=64)
    remaining_time_seconds: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def validate_boundaries(self) -> Self:
        if self.context_source_through_sequence < self.memory_source_through_sequence:
            raise ValueError("context cursor cannot precede memory cursor")
        return self


def select_compaction_episode(
    utterances: tuple[PublicMemoryUtterance, ...],
    *,
    policy: MemoryPolicy,
    force_toward_working_context: bool = False,
) -> tuple[PublicMemoryUtterance, ...]:
    codepoints = sum(len(item.content) for item in utterances)
    if (
        not force_toward_working_context
        and len(utterances) < policy.high_watermark_utterances
        and codepoints < policy.high_watermark_codepoints
    ):
        return ()
    target_utterances = min(
        policy.low_watermark_utterances, policy.recent_raw_max_utterances
    )
    target_codepoints = min(
        policy.low_watermark_codepoints, policy.recent_raw_max_codepoints
    )
    remaining_count = len(utterances)
    remaining_codepoints = codepoints
    selected: list[PublicMemoryUtterance] = []
    for item in utterances:
        if (
            remaining_count <= target_utterances
            and remaining_codepoints <= target_codepoints
        ):
            break
        if len(selected) >= policy.max_derivation_utterances:
            break
        selected.append(item)
        remaining_count -= 1
        remaining_codepoints -= len(item.content)
    return tuple(selected)


def _fits(
    items: tuple[PublicMemoryUtterance, ...], *, utterances: int, codepoints: int
) -> bool:
    return (
        len(items) <= utterances
        and sum(len(item.content) for item in items) <= codepoints
    )


def build_discussion_working_context(
    *,
    projection: DiscussionMemoryProjection,
    complete_public_history: tuple[PublicMemoryUtterance, ...],
    phase: str,
    now: datetime,
    phase_deadline_at: datetime | None,
    policy: MemoryPolicy,
    compaction_failed: bool = False,
) -> DiscussionWorkingContext:
    if any(item.sequence <= 0 for item in complete_public_history):
        raise DiscussionWorkingContextUnavailable("invalid public evidence")
    sequences = tuple(item.sequence for item in complete_public_history)
    if tuple(sorted(set(sequences))) != sequences:
        raise DiscussionWorkingContextUnavailable("public evidence is not ordered")
    tail = tuple(
        item
        for item in complete_public_history
        if item.sequence > projection.source_through_sequence
    )
    state_size = len(projection.state.model_dump_json())
    if compaction_failed:
        if not _fits(
            complete_public_history,
            utterances=policy.safe_raw_fallback_max_utterances,
            codepoints=policy.safe_raw_fallback_max_codepoints,
        ):
            raise DiscussionWorkingContextUnavailable(
                "complete raw fallback exceeds budget"
            )
        context_mode = DiscussionContextMode.SAFE_RAW_FALLBACK
        visible = complete_public_history
        represented = DiscussionMemoryProjection.empty()
    else:
        if state_size > policy.working_context_memory_codepoints or not _fits(
            tail,
            utterances=policy.recent_raw_max_utterances,
            codepoints=policy.recent_raw_max_codepoints,
        ):
            raise DiscussionWorkingContextUnavailable(
                "memory plus complete raw tail exceeds budget"
            )
        context_mode = DiscussionContextMode.MEMORY_WITH_RAW_TAIL
        visible = tail
        represented = projection

    def active(items: tuple[MemoryItem, ...]) -> tuple[MemoryItem, ...]:
        return tuple(item for item in items if item.status is MemoryItemStatus.ACTIVE)

    remaining = None
    if phase_deadline_at is not None:
        remaining = max(0, int((phase_deadline_at - now).total_seconds()))
    return DiscussionWorkingContext(
        context_mode=context_mode,
        memory_revision=represented.revision,
        memory_source_through_sequence=represented.source_through_sequence,
        context_source_through_sequence=(
            visible[-1].sequence if visible else represented.source_through_sequence
        ),
        active_proposals=active(represented.state.proposals),
        active_evaluation_criteria=active(represented.state.evaluation_criteria),
        active_agreements=active(represented.state.agreements),
        active_conflicts=active(represented.state.open_conflicts),
        current_decision=represented.state.current_decision,
        recent_public_utterances=visible,
        phase=phase,
        remaining_time_seconds=remaining,
    )


def render_structured_discussion_memory(context: DiscussionWorkingContext) -> str:
    payload = {
        "proposals": [
            item.model_dump(mode="json") for item in context.active_proposals
        ],
        "evaluation_criteria": [
            item.model_dump(mode="json") for item in context.active_evaluation_criteria
        ],
        "agreements": [
            item.model_dump(mode="json") for item in context.active_agreements
        ],
        "open_conflicts": [
            item.model_dump(mode="json") for item in context.active_conflicts
        ],
        "current_decision": None
        if context.current_decision is None
        else context.current_decision.model_dump(mode="json"),
    }
    return json.dumps(
        payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    )


def render_working_context_recent_discussion(context: DiscussionWorkingContext) -> str:
    lines: list[str] = []
    for item in context.recent_public_utterances:
        label = "你" if item.actor_kind == "HUMAN" else f"AI 候选人 {item.seat_order}"
        lines.append(f"{label}：{item.content}")
    return "\n".join(lines)
