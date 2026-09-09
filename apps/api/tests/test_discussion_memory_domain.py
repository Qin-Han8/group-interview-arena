from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from group_interview_arena_api.modules.discussion_memory import domain as domain_module
from group_interview_arena_api.modules.discussion_memory.domain import (
    MEMORY_DERIVATION_V1,
    MEMORY_PROJECTION_V1,
    MEMORY_SCHEMA_V1,
    AcceptedMemoryRevision,
    DiscussionMemoryProjection,
    MemoryItem,
    MemoryItemKind,
    MemoryItemStatus,
    MemoryPatch,
    MemoryPatchOperation,
    MemoryPolicy,
    UnknownProjectionVersionError,
    apply_memory_revision,
    replay_memory_revisions,
)

SESSION_ID = uuid4()


def _patch(
    operation: MemoryPatchOperation,
    *,
    target: UUID | None = None,
    text: str | None = None,
    sources: tuple[int, ...] = (3,),
) -> MemoryPatch:
    return MemoryPatch(
        operation=operation,
        kind=MemoryItemKind.PROPOSAL,
        target_memory_item_id=target,
        canonical_text=text,
        source_sequences=sources,
    )


def _apply(
    base: DiscussionMemoryProjection,
    patches: tuple[MemoryPatch, ...],
    revision: int,
    source_from: int,
    source_through: int,
) -> DiscussionMemoryProjection:
    return apply_memory_revision(
        session_id=SESSION_ID,
        base=base,
        patches=patches,
        revision=revision,
        source_from_sequence=source_from,
        source_through_sequence=source_through,
        schema_version=MEMORY_SCHEMA_V1,
        derivation_version=MEMORY_DERIVATION_V1,
        projection_version=MEMORY_PROJECTION_V1,
        policy=MemoryPolicy(),
    )


def test_empty_projection_has_all_frozen_categories() -> None:
    projection = DiscussionMemoryProjection.empty()
    assert (projection.revision, projection.source_through_sequence) == (0, 0)
    assert projection.state.proposals == ()
    assert projection.state.evaluation_criteria == ()
    assert projection.state.agreements == ()
    assert projection.state.open_conflicts == ()
    assert projection.state.discarded_options == ()
    assert projection.state.current_decision is None


def test_reducer_allocates_stable_ids_and_applies_typed_transitions() -> None:
    add = _patch(MemoryPatchOperation.ADD, text="方案 A", sources=(3, 5))
    first = _apply(DiscussionMemoryProjection.empty(), (add,), 1, 3, 5)
    assert first == _apply(DiscussionMemoryProjection.empty(), (add,), 1, 3, 5)
    original = first.state.proposals[0]
    assert original.memory_item_id.version == 5
    assert original.source_sequences == (3, 5)
    updated = _apply(
        first,
        (
            _patch(
                MemoryPatchOperation.UPDATE,
                target=original.memory_item_id,
                text="方案 A+",
                sources=(7,),
            ),
        ),
        2,
        7,
        7,
    )
    assert updated.state.proposals[0].source_sequences == (3, 5, 7)
    superseded = _apply(
        updated,
        (
            _patch(
                MemoryPatchOperation.SUPERSEDE,
                target=original.memory_item_id,
                text="方案 B",
                sources=(9,),
            ),
        ),
        3,
        9,
        9,
    )
    old, replacement = superseded.state.proposals
    assert old.status is MemoryItemStatus.SUPERSEDED
    assert old.superseded_by_id == replacement.memory_item_id
    discarded = _apply(
        superseded,
        (
            _patch(
                MemoryPatchOperation.DISCARD,
                target=replacement.memory_item_id,
                sources=(11,),
            ),
        ),
        4,
        11,
        11,
    )
    assert discarded.state.proposals[-1].status is MemoryItemStatus.DISCARDED


def test_patch_contract_and_provenance_are_closed_and_bounded() -> None:
    invalid_patches: tuple[dict[str, Any], ...] = (
        {"operation": MemoryPatchOperation.ADD, "text": None},
        {"operation": MemoryPatchOperation.UPDATE, "text": "x"},
        {"operation": MemoryPatchOperation.ADD, "text": "x", "sources": ()},
        {"operation": MemoryPatchOperation.ADD, "text": "x", "sources": (2, 2)},
        {"operation": MemoryPatchOperation.ADD, "text": "x", "sources": (3, 2)},
    )
    for kwargs in invalid_patches:
        with pytest.raises(ValidationError):
            _patch(**kwargs)
    with pytest.raises(ValueError, match="source window"):
        _apply(
            DiscussionMemoryProjection.empty(),
            (_patch(MemoryPatchOperation.ADD, text="x", sources=(2,)),),
            1,
            3,
            3,
        )
    with pytest.raises(ValidationError):
        MemoryPolicy(high_watermark_utterances=4, low_watermark_utterances=4)


def test_exact_replay_dispatches_historical_projection_version() -> None:
    accepted = AcceptedMemoryRevision(
        revision=1,
        base_revision=0,
        source_from_sequence=3,
        source_through_sequence=5,
        schema_version=MEMORY_SCHEMA_V1,
        derivation_version=MEMORY_DERIVATION_V1,
        projection_version=MEMORY_PROJECTION_V1,
        patches=(_patch(MemoryPatchOperation.ADD, text="方案 A", sources=(3, 5)),),
    )
    assert replay_memory_revisions(
        session_id=SESSION_ID, revisions=(accepted,)
    ) == _apply(DiscussionMemoryProjection.empty(), accepted.patches, 1, 3, 5)
    unknown = accepted.model_copy(
        update={"projection_version": "memory-projection/unknown"}
    )
    with pytest.raises(UnknownProjectionVersionError):
        replay_memory_revisions(session_id=SESSION_ID, revisions=(unknown,))
    unsupported_schema = accepted.model_copy(update={"schema_version": 2})
    with pytest.raises(ValueError, match="schema"):
        replay_memory_revisions(
            session_id=SESSION_ID,
            revisions=(unsupported_schema,),
        )


def test_v1_replay_uses_frozen_projection_policy_not_current_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    accepted = AcceptedMemoryRevision(
        revision=1,
        base_revision=0,
        source_from_sequence=1,
        source_through_sequence=2,
        schema_version=MEMORY_SCHEMA_V1,
        derivation_version=MEMORY_DERIVATION_V1,
        projection_version=MEMORY_PROJECTION_V1,
        patches=(
            _patch(MemoryPatchOperation.ADD, text="方案 A", sources=(1,)),
            _patch(MemoryPatchOperation.ADD, text="方案 B", sources=(2,)),
        ),
    )
    expected = replay_memory_revisions(session_id=SESSION_ID, revisions=(accepted,))
    monkeypatch.setattr(
        domain_module,
        "DEFAULT_MEMORY_POLICY",
        MemoryPolicy(max_active_items_per_kind=1),
    )
    assert (
        replay_memory_revisions(session_id=SESSION_ID, revisions=(accepted,))
        == expected
    )


def test_live_v1_reduction_uses_same_frozen_semantics_as_exact_replay(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    caller_policy = MemoryPolicy(max_terminal_items=0)
    first_patches = (_patch(MemoryPatchOperation.ADD, text="方案 A", sources=(1,)),)
    first = apply_memory_revision(
        session_id=SESSION_ID,
        base=DiscussionMemoryProjection.empty(),
        patches=first_patches,
        revision=1,
        source_from_sequence=1,
        source_through_sequence=1,
        schema_version=MEMORY_SCHEMA_V1,
        derivation_version=MEMORY_DERIVATION_V1,
        projection_version=MEMORY_PROJECTION_V1,
        policy=caller_policy,
    )
    second_patches = (
        _patch(
            MemoryPatchOperation.SUPERSEDE,
            target=first.state.proposals[0].memory_item_id,
            text="方案 B",
            sources=(2,),
        ),
    )
    live = apply_memory_revision(
        session_id=SESSION_ID,
        base=first,
        patches=second_patches,
        revision=2,
        source_from_sequence=2,
        source_through_sequence=2,
        schema_version=MEMORY_SCHEMA_V1,
        derivation_version=MEMORY_DERIVATION_V1,
        projection_version=MEMORY_PROJECTION_V1,
        policy=caller_policy,
    )
    accepted = (
        AcceptedMemoryRevision(
            revision=1,
            base_revision=0,
            source_from_sequence=1,
            source_through_sequence=1,
            schema_version=MEMORY_SCHEMA_V1,
            derivation_version=MEMORY_DERIVATION_V1,
            projection_version=MEMORY_PROJECTION_V1,
            patches=first_patches,
        ),
        AcceptedMemoryRevision(
            revision=2,
            base_revision=1,
            source_from_sequence=2,
            source_through_sequence=2,
            schema_version=MEMORY_SCHEMA_V1,
            derivation_version=MEMORY_DERIVATION_V1,
            projection_version=MEMORY_PROJECTION_V1,
            patches=second_patches,
        ),
    )
    replayed = replay_memory_revisions(session_id=SESSION_ID, revisions=accepted)
    assert live.state == replayed.state
    assert live.source_through_sequence == replayed.source_through_sequence
    assert [item.status for item in live.state.proposals] == [
        MemoryItemStatus.SUPERSEDED,
        MemoryItemStatus.ACTIVE,
    ]
    monkeypatch.setattr(
        domain_module,
        "DEFAULT_MEMORY_POLICY",
        MemoryPolicy(max_terminal_items=0),
    )
    assert replay_memory_revisions(session_id=SESSION_ID, revisions=accepted) == live


@pytest.mark.parametrize(
    "operation, text",
    (
        (MemoryPatchOperation.UPDATE, "方案 A 更新"),
        (MemoryPatchOperation.DISCARD, None),
    ),
)
def test_transition_rejects_final_merged_provenance_beyond_v1_projection_policy(
    operation: MemoryPatchOperation,
    text: str | None,
) -> None:
    caller_policy = MemoryPolicy(max_source_refs_per_item=32)
    frozen_v1_sequences = tuple(range(1, 17))
    first = apply_memory_revision(
        session_id=SESSION_ID,
        base=DiscussionMemoryProjection.empty(),
        patches=(
            _patch(
                MemoryPatchOperation.ADD,
                text="方案 A",
                sources=frozen_v1_sequences,
            ),
        ),
        revision=1,
        source_from_sequence=1,
        source_through_sequence=16,
        schema_version=MEMORY_SCHEMA_V1,
        derivation_version=MEMORY_DERIVATION_V1,
        projection_version=MEMORY_PROJECTION_V1,
        policy=caller_policy,
    )
    target = first.state.proposals[0]
    with pytest.raises(ValueError, match="source reference bound"):
        apply_memory_revision(
            session_id=SESSION_ID,
            base=first,
            patches=(
                _patch(
                    operation, target=target.memory_item_id, text=text, sources=(17,)
                ),
            ),
            revision=2,
            source_from_sequence=17,
            source_through_sequence=17,
            schema_version=MEMORY_SCHEMA_V1,
            derivation_version=MEMORY_DERIVATION_V1,
            projection_version=MEMORY_PROJECTION_V1,
            policy=caller_policy,
        )


def test_valid_merged_provenance_is_ordered_unique_and_fully_validated() -> None:
    policy = MemoryPolicy(max_source_refs_per_item=3)
    first = apply_memory_revision(
        session_id=SESSION_ID,
        base=DiscussionMemoryProjection.empty(),
        patches=(_patch(MemoryPatchOperation.ADD, text="方案 A", sources=(1, 3)),),
        revision=1,
        source_from_sequence=1,
        source_through_sequence=3,
        schema_version=MEMORY_SCHEMA_V1,
        derivation_version=MEMORY_DERIVATION_V1,
        projection_version=MEMORY_PROJECTION_V1,
        policy=policy,
    )
    target = first.state.proposals[0]
    updated = apply_memory_revision(
        session_id=SESSION_ID,
        base=first,
        patches=(
            _patch(
                MemoryPatchOperation.UPDATE,
                target=target.memory_item_id,
                text="方案 A 更新",
                sources=(2, 3),
            ),
        ),
        revision=2,
        source_from_sequence=2,
        source_through_sequence=3,
        schema_version=MEMORY_SCHEMA_V1,
        derivation_version=MEMORY_DERIVATION_V1,
        projection_version=MEMORY_PROJECTION_V1,
        policy=policy,
    )
    item = updated.state.proposals[0]
    assert item.source_sequences == (1, 2, 3)
    assert MemoryItem.model_validate(item.model_dump()) == item
