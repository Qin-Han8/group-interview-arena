from __future__ import annotations

from enum import StrEnum
from typing import Self
from uuid import UUID, uuid5

from pydantic import BaseModel, ConfigDict, Field, model_validator

MEMORY_SCHEMA_V1 = 1
MEMORY_DERIVATION_V1 = "discussion-memory-derivation/v1"
MEMORY_PROJECTION_V1 = "discussion-memory-projection/v1"
MEMORY_UUID_NAMESPACE = UUID("c3192e9d-02cd-5e47-b9fa-b46fbdc492da")


class MemoryDomainModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class MemoryItemKind(StrEnum):
    PROPOSAL = "PROPOSAL"
    EVALUATION_CRITERION = "EVALUATION_CRITERION"
    AGREEMENT = "AGREEMENT"
    OPEN_CONFLICT = "OPEN_CONFLICT"
    DISCARDED_OPTION = "DISCARDED_OPTION"
    CURRENT_DECISION = "CURRENT_DECISION"


class MemoryItemStatus(StrEnum):
    ACTIVE = "ACTIVE"
    SUPERSEDED = "SUPERSEDED"
    DISCARDED = "DISCARDED"


class MemoryPatchOperation(StrEnum):
    ADD = "ADD"
    UPDATE = "UPDATE"
    SUPERSEDE = "SUPERSEDE"
    DISCARD = "DISCARD"


class DiscussionContextMode(StrEnum):
    MEMORY_WITH_RAW_TAIL = "MEMORY_WITH_RAW_TAIL"
    SAFE_RAW_FALLBACK = "SAFE_RAW_FALLBACK"


class MemoryItem(MemoryDomainModel):
    memory_item_id: UUID
    kind: MemoryItemKind
    canonical_text: str = Field(min_length=1, max_length=2_000)
    status: MemoryItemStatus
    source_sequences: tuple[int, ...] = Field(min_length=1, max_length=32)
    introduced_at_sequence: int = Field(gt=0)
    updated_at_sequence: int = Field(gt=0)
    superseded_by_id: UUID | None = None

    @model_validator(mode="after")
    def validate_item(self) -> Self:
        _validate_sequences(self.source_sequences)
        if self.introduced_at_sequence != self.source_sequences[0]:
            raise ValueError("introduced_at_sequence must equal first source sequence")
        if self.updated_at_sequence != self.source_sequences[-1]:
            raise ValueError("updated_at_sequence must equal last source sequence")
        if (self.status is MemoryItemStatus.SUPERSEDED) != (
            self.superseded_by_id is not None
        ):
            raise ValueError("superseded_by_id is required only for SUPERSEDED items")
        return self


class StructuredDiscussionMemory(MemoryDomainModel):
    proposals: tuple[MemoryItem, ...] = ()
    evaluation_criteria: tuple[MemoryItem, ...] = ()
    agreements: tuple[MemoryItem, ...] = ()
    open_conflicts: tuple[MemoryItem, ...] = ()
    discarded_options: tuple[MemoryItem, ...] = ()
    current_decision: MemoryItem | None = None

    @model_validator(mode="after")
    def validate_kinds(self) -> Self:
        expected = (
            (self.proposals, MemoryItemKind.PROPOSAL),
            (self.evaluation_criteria, MemoryItemKind.EVALUATION_CRITERION),
            (self.agreements, MemoryItemKind.AGREEMENT),
            (self.open_conflicts, MemoryItemKind.OPEN_CONFLICT),
            (self.discarded_options, MemoryItemKind.DISCARDED_OPTION),
        )
        for items, kind in expected:
            if any(item.kind is not kind for item in items):
                raise ValueError(f"{kind} item stored in wrong category")
        if (
            self.current_decision is not None
            and self.current_decision.kind is not MemoryItemKind.CURRENT_DECISION
        ):
            raise ValueError("current_decision item has wrong kind")
        identifiers = [item.memory_item_id for items, _ in expected for item in items]
        if self.current_decision is not None:
            identifiers.append(self.current_decision.memory_item_id)
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("memory item identifiers must be unique")
        return self


class DiscussionMemoryProjection(MemoryDomainModel):
    revision: int = Field(ge=0)
    source_through_sequence: int = Field(ge=0)
    schema_version: int = Field(gt=0)
    derivation_version: str = Field(min_length=1, max_length=128)
    projection_version: str = Field(min_length=1, max_length=128)
    state: StructuredDiscussionMemory

    @classmethod
    def empty(cls) -> Self:
        return cls(
            revision=0,
            source_through_sequence=0,
            schema_version=MEMORY_SCHEMA_V1,
            derivation_version=MEMORY_DERIVATION_V1,
            projection_version=MEMORY_PROJECTION_V1,
            state=StructuredDiscussionMemory(),
        )


class MemoryPatch(MemoryDomainModel):
    operation: MemoryPatchOperation
    kind: MemoryItemKind
    target_memory_item_id: UUID | None = None
    canonical_text: str | None = Field(default=None, min_length=1, max_length=2_000)
    source_sequences: tuple[int, ...] = Field(min_length=1, max_length=32)

    @model_validator(mode="after")
    def validate_shape(self) -> Self:
        _validate_sequences(self.source_sequences)
        if self.operation is MemoryPatchOperation.ADD:
            if self.target_memory_item_id is not None or self.canonical_text is None:
                raise ValueError("ADD requires text and forbids a target")
        elif self.operation in {
            MemoryPatchOperation.UPDATE,
            MemoryPatchOperation.SUPERSEDE,
        }:
            if self.target_memory_item_id is None or self.canonical_text is None:
                raise ValueError(f"{self.operation} requires target and text")
        elif self.target_memory_item_id is None or self.canonical_text is not None:
            raise ValueError("DISCARD requires target and forbids text")
        return self


class MemoryPolicy(MemoryDomainModel):
    max_active_items_per_kind: int = Field(default=12, ge=1, le=64)
    max_terminal_items: int = Field(default=24, ge=0, le=128)
    max_patch_operations: int = Field(default=24, ge=1, le=128)
    max_canonical_text_codepoints: int = Field(default=1_000, ge=64, le=2_000)
    max_source_refs_per_item: int = Field(default=16, ge=1, le=32)
    max_serialized_state_bytes: int = Field(default=32_768, ge=4_096, le=131_072)
    max_derivation_utterances: int = Field(default=64, ge=1, le=64)
    max_catch_up_steps: int = Field(default=4, ge=1, le=16)
    max_rebuild_steps: int = Field(default=16, ge=1, le=64)
    high_watermark_utterances: int = Field(default=12, ge=2, le=64)
    low_watermark_utterances: int = Field(default=6, ge=1, le=32)
    high_watermark_codepoints: int = Field(default=8_000, ge=1_000, le=64_000)
    low_watermark_codepoints: int = Field(default=4_000, ge=500, le=32_000)
    recent_raw_max_utterances: int = Field(default=6, ge=1, le=24)
    recent_raw_max_codepoints: int = Field(default=4_000, ge=500, le=16_000)
    working_context_memory_codepoints: int = Field(default=6_000, ge=500, le=32_000)
    safe_raw_fallback_max_utterances: int = Field(default=12, ge=1, le=64)
    safe_raw_fallback_max_codepoints: int = Field(default=8_000, ge=500, le=64_000)

    @model_validator(mode="after")
    def validate_watermarks(self) -> Self:
        if self.low_watermark_utterances >= self.high_watermark_utterances:
            raise ValueError("utterance low watermark must be below high watermark")
        if self.low_watermark_codepoints >= self.high_watermark_codepoints:
            raise ValueError("codepoint low watermark must be below high watermark")
        return self


MEMORY_PROJECTION_V1_POLICY = MemoryPolicy(
    max_active_items_per_kind=12,
    max_terminal_items=24,
    max_patch_operations=24,
    max_canonical_text_codepoints=1_000,
    max_source_refs_per_item=16,
    max_serialized_state_bytes=32_768,
    max_derivation_utterances=64,
    max_catch_up_steps=4,
    max_rebuild_steps=16,
    high_watermark_utterances=12,
    low_watermark_utterances=6,
    high_watermark_codepoints=8_000,
    low_watermark_codepoints=4_000,
    recent_raw_max_utterances=6,
    recent_raw_max_codepoints=4_000,
    working_context_memory_codepoints=6_000,
    safe_raw_fallback_max_utterances=12,
    safe_raw_fallback_max_codepoints=8_000,
)
DEFAULT_MEMORY_POLICY = MemoryPolicy()


class AcceptedMemoryRevision(MemoryDomainModel):
    revision: int = Field(gt=0)
    base_revision: int = Field(ge=0)
    source_from_sequence: int = Field(gt=0)
    source_through_sequence: int = Field(gt=0)
    schema_version: int = Field(gt=0)
    derivation_version: str = Field(min_length=1, max_length=128)
    projection_version: str = Field(min_length=1, max_length=128)
    patches: tuple[MemoryPatch, ...]

    @model_validator(mode="after")
    def validate_revision(self) -> Self:
        if self.revision != self.base_revision + 1:
            raise ValueError("revision must advance exactly once")
        if self.source_through_sequence < self.source_from_sequence:
            raise ValueError("invalid source range")
        return self


class UnknownProjectionVersionError(ValueError):
    pass


class UnknownMemorySchemaVersionError(ValueError):
    pass


def _validate_sequences(sequences: tuple[int, ...]) -> None:
    if not sequences or sequences[0] <= 0 or tuple(sorted(set(sequences))) != sequences:
        raise ValueError(
            "source sequences must be positive, strictly ordered, and unique"
        )


def _items_by_kind(
    state: StructuredDiscussionMemory,
) -> dict[MemoryItemKind, list[MemoryItem]]:
    return {
        MemoryItemKind.PROPOSAL: list(state.proposals),
        MemoryItemKind.EVALUATION_CRITERION: list(state.evaluation_criteria),
        MemoryItemKind.AGREEMENT: list(state.agreements),
        MemoryItemKind.OPEN_CONFLICT: list(state.open_conflicts),
        MemoryItemKind.DISCARDED_OPTION: list(state.discarded_options),
        MemoryItemKind.CURRENT_DECISION: []
        if state.current_decision is None
        else [state.current_decision],
    }


def _new_id(
    session_id: UUID, revision: int, ordinal: int, kind: MemoryItemKind
) -> UUID:
    return uuid5(
        MEMORY_UUID_NAMESPACE, f"{session_id}:{revision}:{ordinal}:{kind.value}"
    )


def _validated_item_transition(
    item: MemoryItem, *, update: dict[str, object]
) -> MemoryItem:
    payload = item.model_dump(mode="python")
    payload.update(update)
    return MemoryItem.model_validate(payload)


def _projection_policy(projection_version: str) -> MemoryPolicy:
    if projection_version == MEMORY_PROJECTION_V1:
        return MEMORY_PROJECTION_V1_POLICY
    raise UnknownProjectionVersionError(projection_version)


def apply_memory_revision(
    *,
    session_id: UUID,
    base: DiscussionMemoryProjection,
    patches: tuple[MemoryPatch, ...],
    revision: int,
    source_from_sequence: int,
    source_through_sequence: int,
    schema_version: int,
    derivation_version: str,
    projection_version: str,
    policy: MemoryPolicy = DEFAULT_MEMORY_POLICY,
) -> DiscussionMemoryProjection:
    if schema_version != MEMORY_SCHEMA_V1:
        raise UnknownMemorySchemaVersionError(
            f"unsupported memory schema version: {schema_version}"
        )
    policy = _projection_policy(projection_version)
    if revision != base.revision + 1:
        raise ValueError("revision must advance exactly once")
    if source_through_sequence < source_from_sequence:
        raise ValueError("invalid source window")
    if len(patches) > policy.max_patch_operations:
        raise ValueError("patch operation bound exceeded")
    by_kind = _items_by_kind(base.state)
    for ordinal, patch in enumerate(patches):
        if (
            patch.source_sequences[0] < source_from_sequence
            or patch.source_sequences[-1] > source_through_sequence
        ):
            raise ValueError("patch provenance is outside source window")
        if len(patch.source_sequences) > policy.max_source_refs_per_item:
            raise ValueError("source reference bound exceeded")
        if (
            patch.canonical_text is not None
            and len(patch.canonical_text) > policy.max_canonical_text_codepoints
        ):
            raise ValueError("canonical text bound exceeded")
        items = by_kind[patch.kind]
        target_index = next(
            (
                i
                for i, item in enumerate(items)
                if item.memory_item_id == patch.target_memory_item_id
            ),
            None,
        )
        target: MemoryItem | None = None
        if patch.operation is not MemoryPatchOperation.ADD:
            if target_index is None:
                raise ValueError("patch target does not exist in the declared kind")
            target = items[target_index]
            if target.status is not MemoryItemStatus.ACTIVE:
                raise ValueError("patch target is not active")
        if patch.operation is MemoryPatchOperation.ADD:
            assert patch.canonical_text is not None
            new_item = MemoryItem(
                memory_item_id=_new_id(session_id, revision, ordinal, patch.kind),
                kind=patch.kind,
                canonical_text=patch.canonical_text,
                status=MemoryItemStatus.ACTIVE,
                source_sequences=patch.source_sequences,
                introduced_at_sequence=patch.source_sequences[0],
                updated_at_sequence=patch.source_sequences[-1],
            )
            if patch.kind is MemoryItemKind.CURRENT_DECISION:
                for index, current in enumerate(items):
                    if current.status is MemoryItemStatus.ACTIVE:
                        items[index] = _validated_item_transition(
                            current,
                            update={
                                "status": MemoryItemStatus.SUPERSEDED,
                                "superseded_by_id": new_item.memory_item_id,
                            },
                        )
            items.append(new_item)
        elif patch.operation is MemoryPatchOperation.UPDATE:
            assert target is not None and target_index is not None
            sequences = tuple(
                sorted(set((*target.source_sequences, *patch.source_sequences)))
            )
            if len(sequences) > policy.max_source_refs_per_item:
                raise ValueError("source reference bound exceeded")
            items[target_index] = _validated_item_transition(
                target,
                update={
                    "canonical_text": patch.canonical_text,
                    "source_sequences": sequences,
                    "updated_at_sequence": sequences[-1],
                },
            )
        elif patch.operation is MemoryPatchOperation.SUPERSEDE:
            assert target is not None and target_index is not None
            assert patch.canonical_text is not None
            replacement = MemoryItem(
                memory_item_id=_new_id(session_id, revision, ordinal, patch.kind),
                kind=patch.kind,
                canonical_text=patch.canonical_text,
                status=MemoryItemStatus.ACTIVE,
                source_sequences=patch.source_sequences,
                introduced_at_sequence=patch.source_sequences[0],
                updated_at_sequence=patch.source_sequences[-1],
            )
            items[target_index] = _validated_item_transition(
                target,
                update={
                    "status": MemoryItemStatus.SUPERSEDED,
                    "superseded_by_id": replacement.memory_item_id,
                },
            )
            items.append(replacement)
        else:
            assert target is not None and target_index is not None
            sequences = tuple(
                sorted(set((*target.source_sequences, *patch.source_sequences)))
            )
            if len(sequences) > policy.max_source_refs_per_item:
                raise ValueError("source reference bound exceeded")
            items[target_index] = _validated_item_transition(
                target,
                update={
                    "status": MemoryItemStatus.DISCARDED,
                    "source_sequences": sequences,
                    "updated_at_sequence": sequences[-1],
                },
            )
    for kind, items in by_kind.items():
        active = [item for item in items if item.status is MemoryItemStatus.ACTIVE]
        if len(active) > (
            1
            if kind is MemoryItemKind.CURRENT_DECISION
            else policy.max_active_items_per_kind
        ):
            raise ValueError("active memory item bound exceeded")
        terminal_indexes = [
            i
            for i, item in enumerate(items)
            if item.status is not MemoryItemStatus.ACTIVE
        ]
        for index in reversed(
            terminal_indexes[: -policy.max_terminal_items]
            if policy.max_terminal_items
            else terminal_indexes
        ):
            del items[index]
    state = StructuredDiscussionMemory(
        proposals=tuple(by_kind[MemoryItemKind.PROPOSAL]),
        evaluation_criteria=tuple(by_kind[MemoryItemKind.EVALUATION_CRITERION]),
        agreements=tuple(by_kind[MemoryItemKind.AGREEMENT]),
        open_conflicts=tuple(by_kind[MemoryItemKind.OPEN_CONFLICT]),
        discarded_options=tuple(by_kind[MemoryItemKind.DISCARDED_OPTION]),
        current_decision=next(
            (
                item
                for item in reversed(by_kind[MemoryItemKind.CURRENT_DECISION])
                if item.status is MemoryItemStatus.ACTIVE
            ),
            None,
        ),
    )
    if len(state.model_dump_json().encode()) > policy.max_serialized_state_bytes:
        raise ValueError("serialized memory state bound exceeded")
    return DiscussionMemoryProjection(
        revision=revision,
        source_through_sequence=max(
            base.source_through_sequence, source_through_sequence
        ),
        schema_version=schema_version,
        derivation_version=derivation_version,
        projection_version=projection_version,
        state=state,
    )


def replay_memory_revisions(
    *, session_id: UUID, revisions: tuple[AcceptedMemoryRevision, ...]
) -> DiscussionMemoryProjection:
    projection = DiscussionMemoryProjection.empty()
    for item in revisions:
        if item.base_revision != projection.revision:
            raise ValueError("revision journal is not contiguous")
        projection = apply_memory_revision(
            session_id=session_id,
            base=projection,
            patches=item.patches,
            revision=item.revision,
            source_from_sequence=item.source_from_sequence,
            source_through_sequence=item.source_through_sequence,
            schema_version=item.schema_version,
            derivation_version=item.derivation_version,
            projection_version=item.projection_version,
            policy=_projection_policy(item.projection_version),
        )
    return projection
