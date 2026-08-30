from __future__ import annotations

import hashlib
import inspect
import json
from collections.abc import Awaitable
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Literal, Protocol, Self, cast
from uuid import UUID, uuid4

from pydantic import Field, model_validator
from sqlalchemy import select, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from group_interview_arena_api.db.models import (
    DiscussionEvent,
    DiscussionMemoryRevision,
    DiscussionMemoryState,
    QuestionVersion,
    SessionParticipant,
    SimulationSession,
)
from group_interview_arena_api.modules.discussion_memory.derivation import (
    MemoryDerivationInput,
    MemoryDerivationResult,
    PublicMemoryQuestionContext,
    PublicMemoryUtterance,
    project_public_memory_question_context,
    validate_memory_derivation_result,
)
from group_interview_arena_api.modules.discussion_memory.domain import (
    DEFAULT_MEMORY_POLICY,
    MEMORY_DERIVATION_V1,
    MEMORY_PROJECTION_V1,
    MEMORY_SCHEMA_V1,
    AcceptedMemoryRevision,
    DiscussionMemoryProjection,
    MemoryDomainModel,
    MemoryPatch,
    MemoryPolicy,
    StructuredDiscussionMemory,
    apply_memory_revision,
    replay_memory_revisions,
)
from group_interview_arena_api.modules.discussion_memory.working_context import (
    select_compaction_episode,
)
from group_interview_arena_api.modules.discussion_sessions.domain import StoredEvent
from group_interview_arena_api.modules.discussion_sessions.public_events import (
    PublicEventProjectionError,
    project_public_events,
)


class DiscussionMemoryPersistenceError(RuntimeError):
    pass


class MemoryMaintenanceOutcome(StrEnum):
    NOOP_BELOW_HIGH_WATERMARK = "NOOP_BELOW_HIGH_WATERMARK"
    UPDATED = "UPDATED"
    CAS_CONFLICT = "CAS_CONFLICT"


class MemorySemanticProvenance(MemoryDomainModel):
    prompt_version_id: UUID | None = None
    provider_identifier: str | None = Field(default=None, min_length=1, max_length=128)
    model_identifier: str | None = Field(default=None, min_length=1, max_length=128)
    configuration_version: str | None = Field(
        default=None, min_length=1, max_length=128
    )

    @model_validator(mode="after")
    def validate_group(self) -> Self:
        values = (
            self.prompt_version_id,
            self.provider_identifier,
            self.model_identifier,
            self.configuration_version,
        )
        if any(value is None for value in values) and any(
            value is not None for value in values
        ):
            raise ValueError("semantic model provenance is all-or-none")
        return self


class MemoryDeriverLike(Protocol):
    def derive(
        self, derivation_input: MemoryDerivationInput, /
    ) -> MemoryDerivationResult | Awaitable[MemoryDerivationResult]: ...


class MemoryMaintenanceResult(MemoryDomainModel):
    outcome: MemoryMaintenanceOutcome
    projection: DiscussionMemoryProjection
    compaction_triggered: bool
    patch_operation_count: int = Field(ge=0)


async def load_public_memory_utterances(
    session: AsyncSession, *, session_id: UUID
) -> tuple[PublicMemoryUtterance, ...]:
    rows = tuple(
        (
            await session.scalars(
                select(DiscussionEvent)
                .where(
                    DiscussionEvent.session_id == session_id,
                    DiscussionEvent.event_type == "participant.utterance.created",
                )
                .order_by(DiscussionEvent.sequence.asc())
            )
        ).all()
    )
    stored = tuple(
        StoredEvent(
            event_version=row.event_version,
            event_type=row.event_type,
            session_id=row.session_id,
            sequence=row.sequence,
            occurred_at=row.occurred_at,
            causation_action_id=row.causation_action_id,
            payload=row.payload,
        )
        for row in rows
    )
    try:
        projected = await project_public_events(session, stored)
        participant_ids = {
            UUID(str(event.payload["participant_id"])) for event in projected
        }
        participants = {
            item.id: item
            for item in (
                await session.scalars(
                    select(SessionParticipant).where(
                        SessionParticipant.session_id == session_id,
                        SessionParticipant.id.in_(participant_ids),
                    )
                )
            ).all()
        }
        items: list[PublicMemoryUtterance] = []
        for event in projected:
            participant_id = UUID(str(event.payload["participant_id"]))
            participant = participants.get(participant_id)
            content = event.payload["content"]
            actor_kind = str(event.payload["actor_kind"])
            phase = str(event.payload["phase"])
            if (
                event.type != "participant.utterance.created"
                or event.schema_version != 1
                or event.session_id != session_id
                or participant is None
                or actor_kind not in {"HUMAN", "AI"}
                or participant.actor_kind != actor_kind
                or not isinstance(content, str)
                or not phase
            ):
                raise ValueError("invalid public utterance projection")
            items.append(
                PublicMemoryUtterance(
                    session_id=session_id,
                    sequence=event.sequence,
                    participant_id=participant_id,
                    seat_order=participant.seat_order,
                    actor_kind=cast(Literal["HUMAN", "AI"], actor_kind),
                    phase=phase,
                    content=content,
                )
            )
        return tuple(items)
    except (PublicEventProjectionError, KeyError, TypeError, ValueError) as error:
        raise DiscussionMemoryPersistenceError(
            "public memory evidence projection failed"
        ) from error


def _projection(record: DiscussionMemoryState | None) -> DiscussionMemoryProjection:
    if record is None:
        return DiscussionMemoryProjection.empty()
    return DiscussionMemoryProjection(
        revision=record.revision,
        source_through_sequence=record.source_through_sequence,
        schema_version=record.schema_version,
        derivation_version=record.derivation_version,
        projection_version=record.projection_version,
        state=StructuredDiscussionMemory.model_validate(record.structured_state),
    )


async def load_discussion_memory_projection(
    session: AsyncSession, *, session_id: UUID
) -> DiscussionMemoryProjection:
    return _projection(await session.get(DiscussionMemoryState, session_id))


async def load_discussion_memory_projection_at_revision(
    session: AsyncSession, *, session_id: UUID, revision: int
) -> DiscussionMemoryProjection:
    if revision < 0:
        raise DiscussionMemoryPersistenceError(
            "historical memory revision cannot be negative"
        )
    if revision == 0:
        return DiscussionMemoryProjection.empty()
    rows = tuple(
        (
            await session.scalars(
                select(DiscussionMemoryRevision)
                .where(
                    DiscussionMemoryRevision.session_id == session_id,
                    DiscussionMemoryRevision.revision <= revision,
                )
                .order_by(DiscussionMemoryRevision.revision)
            )
        ).all()
    )
    if len(rows) != revision or rows[-1].revision != revision:
        raise DiscussionMemoryPersistenceError(
            "historical memory revision is unavailable"
        )
    try:
        accepted = tuple(
            AcceptedMemoryRevision(
                revision=row.revision,
                base_revision=row.base_revision,
                source_from_sequence=row.source_from_sequence,
                source_through_sequence=row.source_through_sequence,
                schema_version=row.schema_version,
                derivation_version=row.derivation_version,
                projection_version=row.projection_version,
                patches=tuple(
                    MemoryPatch.model_validate(patch) for patch in row.patches
                ),
            )
            for row in rows
        )
        return replay_memory_revisions(session_id=session_id, revisions=accepted)
    except ValueError as error:
        raise DiscussionMemoryPersistenceError(
            "historical memory journal replay failed"
        ) from error


async def _load_proven_cas_winner(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    session_id: UUID,
    base_projection: DiscussionMemoryProjection,
    proposed_projection: DiscussionMemoryProjection,
) -> DiscussionMemoryProjection | None:
    try:
        async with session_factory() as session:
            winner = await load_discussion_memory_projection(
                session, session_id=session_id
            )
    except SQLAlchemyError as error:
        raise DiscussionMemoryPersistenceError(
            "memory CAS winner verification failed"
        ) from error
    if (
        winner.revision > base_projection.revision
        and winner.source_through_sequence
        >= proposed_projection.source_through_sequence
    ):
        return winner
    return None


def _digest(value: MemoryDerivationInput) -> bytes:
    encoded = json.dumps(
        value.model_dump(mode="json"),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode()
    return hashlib.sha256(encoded).digest()


async def _maintain_discussion_memory_step(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    session_id: UUID,
    deriver: MemoryDeriverLike,
    provenance: MemorySemanticProvenance,
    policy: MemoryPolicy = DEFAULT_MEMORY_POLICY,
    now: datetime | None = None,
    force_compaction: bool = False,
) -> MemoryMaintenanceResult:
    timestamp = (now or datetime.now(UTC)).astimezone(UTC)
    try:
        async with session_factory() as read_session:
            projection = await load_discussion_memory_projection(
                read_session, session_id=session_id
            )
            history = await load_public_memory_utterances(
                read_session, session_id=session_id
            )
            question = await read_session.scalar(
                select(QuestionVersion)
                .join(
                    SimulationSession,
                    SimulationSession.question_version_id == QuestionVersion.id,
                )
                .where(SimulationSession.id == session_id)
            )
    except SQLAlchemyError as error:
        raise DiscussionMemoryPersistenceError(
            "memory read transaction failed"
        ) from error
    if question is None:
        raise DiscussionMemoryPersistenceError("memory question context is unavailable")
    tail = tuple(
        item for item in history if item.sequence > projection.source_through_sequence
    )
    episode = select_compaction_episode(
        tail,
        policy=policy,
        force_toward_working_context=force_compaction,
    )
    if not episode:
        return MemoryMaintenanceResult(
            outcome=MemoryMaintenanceOutcome.NOOP_BELOW_HIGH_WATERMARK,
            projection=projection,
            compaction_triggered=False,
            patch_operation_count=0,
        )
    derivation_input = MemoryDerivationInput(
        session_id=session_id,
        previous_memory=projection,
        utterances=episode,
        question_context=project_public_memory_question_context(question),
    )
    proposed = deriver.derive(derivation_input)
    result = await proposed if inspect.isawaitable(proposed) else proposed
    validated = validate_memory_derivation_result(
        derivation_input, result, policy=policy
    )
    next_projection = apply_memory_revision(
        session_id=session_id,
        base=projection,
        patches=validated.patches,
        revision=projection.revision + 1,
        source_from_sequence=episode[0].sequence,
        source_through_sequence=episode[-1].sequence,
        schema_version=MEMORY_SCHEMA_V1,
        derivation_version=MEMORY_DERIVATION_V1,
        projection_version=MEMORY_PROJECTION_V1,
        policy=policy,
    )
    revision_record = DiscussionMemoryRevision(
        id=uuid4(),
        session_id=session_id,
        revision=next_projection.revision,
        base_revision=projection.revision,
        source_from_sequence=episode[0].sequence,
        source_through_sequence=episode[-1].sequence,
        patches=[patch.model_dump(mode="json") for patch in validated.patches],
        schema_version=next_projection.schema_version,
        derivation_version=next_projection.derivation_version,
        projection_version=next_projection.projection_version,
        derivation_input_digest=_digest(derivation_input),
        prompt_version_id=provenance.prompt_version_id,
        provider_identifier=provenance.provider_identifier,
        model_identifier=provenance.model_identifier,
        configuration_version=provenance.configuration_version,
        created_at=timestamp,
    )
    try:
        async with session_factory() as write_session:
            async with write_session.begin():
                write_session.add(revision_record)
                values = dict(
                    revision=next_projection.revision,
                    source_through_sequence=next_projection.source_through_sequence,
                    schema_version=next_projection.schema_version,
                    derivation_version=next_projection.derivation_version,
                    projection_version=next_projection.projection_version,
                    structured_state=next_projection.state.model_dump(mode="json"),
                    updated_at=timestamp,
                )
                if projection.revision == 0:
                    write_session.add(
                        DiscussionMemoryState(session_id=session_id, **values)
                    )
                else:
                    changed = await write_session.execute(
                        update(DiscussionMemoryState)
                        .where(
                            DiscussionMemoryState.session_id == session_id,
                            DiscussionMemoryState.revision == projection.revision,
                            DiscussionMemoryState.source_through_sequence
                            == projection.source_through_sequence,
                        )
                        .values(**values)
                    )
                    if cast(CursorResult[Any], changed).rowcount != 1:
                        raise _CasConflict
    except (_CasConflict, IntegrityError) as error:
        winner = await _load_proven_cas_winner(
            session_factory,
            session_id=session_id,
            base_projection=projection,
            proposed_projection=next_projection,
        )
        if winner is None:
            raise DiscussionMemoryPersistenceError(
                "memory write transaction failed without a proven CAS winner"
            ) from error
        return MemoryMaintenanceResult(
            outcome=MemoryMaintenanceOutcome.CAS_CONFLICT,
            projection=winner,
            compaction_triggered=True,
            patch_operation_count=len(validated.patches),
        )
    except SQLAlchemyError as error:
        raise DiscussionMemoryPersistenceError(
            "memory write transaction failed"
        ) from error
    return MemoryMaintenanceResult(
        outcome=MemoryMaintenanceOutcome.UPDATED,
        projection=next_projection,
        compaction_triggered=True,
        patch_operation_count=len(validated.patches),
    )


async def _bounded_catch_up_is_pending(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    session_id: UUID,
    policy: MemoryPolicy,
) -> bool:
    try:
        async with session_factory() as session:
            projection = await load_discussion_memory_projection(
                session, session_id=session_id
            )
            history = await load_public_memory_utterances(
                session, session_id=session_id
            )
    except SQLAlchemyError as error:
        raise DiscussionMemoryPersistenceError(
            "memory catch-up verification failed"
        ) from error
    tail = tuple(
        item for item in history if item.sequence > projection.source_through_sequence
    )
    return bool(
        select_compaction_episode(
            tail,
            policy=policy,
            force_toward_working_context=True,
        )
    )


async def maintain_discussion_memory(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    session_id: UUID,
    deriver: MemoryDeriverLike,
    provenance: MemorySemanticProvenance,
    policy: MemoryPolicy = DEFAULT_MEMORY_POLICY,
    now: datetime | None = None,
) -> MemoryMaintenanceResult:
    updated: MemoryMaintenanceResult | None = None
    patch_operation_count = 0
    for _step in range(policy.max_catch_up_steps):
        result = await _maintain_discussion_memory_step(
            session_factory,
            session_id=session_id,
            deriver=deriver,
            provenance=provenance,
            policy=policy,
            now=now,
            force_compaction=updated is not None,
        )
        if result.outcome is MemoryMaintenanceOutcome.CAS_CONFLICT:
            return result.model_copy(
                update={
                    "patch_operation_count": (
                        patch_operation_count + result.patch_operation_count
                    )
                }
            )
        if result.outcome is MemoryMaintenanceOutcome.NOOP_BELOW_HIGH_WATERMARK:
            if updated is None:
                return result
            return updated.model_copy(
                update={"patch_operation_count": patch_operation_count}
            )
        updated = result
        patch_operation_count += result.patch_operation_count
    if await _bounded_catch_up_is_pending(
        session_factory, session_id=session_id, policy=policy
    ):
        raise DiscussionMemoryPersistenceError("memory catch-up budget exhausted")
    assert updated is not None
    return updated.model_copy(update={"patch_operation_count": patch_operation_count})


async def _rebuild_discussion_memory_batch(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    session_id: UUID,
    projection: DiscussionMemoryProjection,
    episode: tuple[PublicMemoryUtterance, ...],
    question_context: PublicMemoryQuestionContext,
    deriver: MemoryDeriverLike,
    provenance: MemorySemanticProvenance,
    derivation_version: str,
    policy: MemoryPolicy,
    timestamp: datetime,
) -> MemoryMaintenanceResult:
    derivation_input = MemoryDerivationInput(
        session_id=session_id,
        previous_memory=projection,
        utterances=episode,
        question_context=question_context,
    )
    proposed = deriver.derive(derivation_input)
    result = await proposed if inspect.isawaitable(proposed) else proposed
    validated = validate_memory_derivation_result(
        derivation_input, result, policy=policy
    )
    next_projection = apply_memory_revision(
        session_id=session_id,
        base=projection,
        patches=validated.patches,
        revision=projection.revision + 1,
        source_from_sequence=episode[0].sequence,
        source_through_sequence=episode[-1].sequence,
        schema_version=MEMORY_SCHEMA_V1,
        derivation_version=derivation_version,
        projection_version=MEMORY_PROJECTION_V1,
        policy=policy,
    )
    revision_record = DiscussionMemoryRevision(
        id=uuid4(),
        session_id=session_id,
        revision=next_projection.revision,
        base_revision=projection.revision,
        source_from_sequence=episode[0].sequence,
        source_through_sequence=episode[-1].sequence,
        patches=[patch.model_dump(mode="json") for patch in validated.patches],
        schema_version=next_projection.schema_version,
        derivation_version=derivation_version,
        projection_version=next_projection.projection_version,
        derivation_input_digest=_digest(derivation_input),
        prompt_version_id=provenance.prompt_version_id,
        provider_identifier=provenance.provider_identifier,
        model_identifier=provenance.model_identifier,
        configuration_version=provenance.configuration_version,
        created_at=timestamp,
    )
    values = dict(
        revision=next_projection.revision,
        source_through_sequence=next_projection.source_through_sequence,
        schema_version=next_projection.schema_version,
        derivation_version=derivation_version,
        projection_version=next_projection.projection_version,
        structured_state=next_projection.state.model_dump(mode="json"),
        updated_at=timestamp,
    )
    try:
        async with session_factory() as write_session:
            async with write_session.begin():
                write_session.add(revision_record)
                if projection.revision == 0:
                    write_session.add(
                        DiscussionMemoryState(session_id=session_id, **values)
                    )
                else:
                    changed = await write_session.execute(
                        update(DiscussionMemoryState)
                        .where(
                            DiscussionMemoryState.session_id == session_id,
                            DiscussionMemoryState.revision == projection.revision,
                            DiscussionMemoryState.source_through_sequence
                            == projection.source_through_sequence,
                        )
                        .values(**values)
                    )
                    if cast(CursorResult[Any], changed).rowcount != 1:
                        raise _CasConflict
    except (_CasConflict, IntegrityError) as error:
        winner = await _load_proven_cas_winner(
            session_factory,
            session_id=session_id,
            base_projection=projection,
            proposed_projection=next_projection,
        )
        if winner is None:
            raise DiscussionMemoryPersistenceError(
                "memory rebuild write failed without a proven CAS winner"
            ) from error
        return MemoryMaintenanceResult(
            outcome=MemoryMaintenanceOutcome.CAS_CONFLICT,
            projection=winner,
            compaction_triggered=True,
            patch_operation_count=len(validated.patches),
        )
    except SQLAlchemyError as error:
        raise DiscussionMemoryPersistenceError("memory rebuild write failed") from error
    return MemoryMaintenanceResult(
        outcome=MemoryMaintenanceOutcome.UPDATED,
        projection=next_projection,
        compaction_triggered=True,
        patch_operation_count=len(validated.patches),
    )


async def rebuild_discussion_memory(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    session_id: UUID,
    deriver: MemoryDeriverLike,
    provenance: MemorySemanticProvenance,
    derivation_version: str,
    policy: MemoryPolicy = DEFAULT_MEMORY_POLICY,
    now: datetime | None = None,
) -> MemoryMaintenanceResult:
    """Append bounded semantic reinterpretation revisions without rewriting evidence."""
    timestamp = (now or datetime.now(UTC)).astimezone(UTC)
    try:
        async with session_factory() as read_session:
            projection = await load_discussion_memory_projection(
                read_session, session_id=session_id
            )
            history = await load_public_memory_utterances(
                read_session, session_id=session_id
            )
            question = await read_session.scalar(
                select(QuestionVersion)
                .join(
                    SimulationSession,
                    SimulationSession.question_version_id == QuestionVersion.id,
                )
                .where(SimulationSession.id == session_id)
            )
    except SQLAlchemyError as error:
        raise DiscussionMemoryPersistenceError("memory rebuild read failed") from error
    if question is None or not history:
        raise DiscussionMemoryPersistenceError("memory rebuild evidence is unavailable")

    question_context = project_public_memory_question_context(question)
    offset = 0
    patch_operation_count = 0
    latest: MemoryMaintenanceResult | None = None
    for _step in range(policy.max_rebuild_steps):
        episode = history[offset : offset + policy.max_derivation_utterances]
        if not episode:
            break
        result = await _rebuild_discussion_memory_batch(
            session_factory,
            session_id=session_id,
            projection=projection,
            episode=episode,
            question_context=question_context,
            deriver=deriver,
            provenance=provenance,
            derivation_version=derivation_version,
            policy=policy,
            timestamp=timestamp,
        )
        patch_operation_count += result.patch_operation_count
        if result.outcome is MemoryMaintenanceOutcome.CAS_CONFLICT:
            return result.model_copy(
                update={"patch_operation_count": patch_operation_count}
            )
        latest = result
        projection = result.projection
        offset += len(episode)
        if offset == len(history):
            return result.model_copy(
                update={"patch_operation_count": patch_operation_count}
            )
    if offset < len(history):
        raise DiscussionMemoryPersistenceError("memory rebuild step budget exhausted")
    assert latest is not None
    return latest.model_copy(update={"patch_operation_count": patch_operation_count})


class _CasConflict(Exception):
    pass
