import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID, uuid5

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from group_interview_arena_api.db.models import (
    DiscussionEvent,
    FloorGrant,
    FloorRelease,
    SessionAction,
    SessionParticipant,
    SimulationSession,
)
from group_interview_arena_api.modules.discussion_sessions.domain import (
    PendingEvent,
    SessionStatus,
    StoredEvent,
)
from group_interview_arena_api.modules.discussion_sessions.public_events import (
    PublicEventProjectionError,
    project_public_events,
)
from group_interview_arena_api.modules.discussion_sessions.service import (
    ActionIdConflictError,
    SessionNotFoundError,
    SessionPersistenceError,
    reconcile_due_for_locked_aggregate,
)
from group_interview_arena_api.modules.floor_control.domain import (
    FLOOR_ENABLED_PHASES,
    FloorReleaseReason,
    ParticipantActorKind,
    ParticipantAvailability,
    ParticipationRole,
)
from group_interview_arena_api.modules.floor_control.lifecycle import (
    release_active_floor_for_lifecycle,
)

_UTTERANCE_ID_NAMESPACE = UUID("ca3256d4-e2a5-52d0-9742-a6e6500930f8")


class UtteranceRejectedError(Exception):
    """A syntactically valid utterance is not authorized at this checkpoint."""


@dataclass(frozen=True)
class SubmitHumanUtterance:
    session_id: UUID
    action_id: UUID
    floor_grant_id: UUID
    content: str
    received_at: datetime
    schema_version: int = 1
    command_type: str = "participant.utterance.submit"


@dataclass(frozen=True)
class HumanUtteranceCommit:
    events: tuple[StoredEvent, StoredEvent]
    utterance_id: UUID
    released_floor_grant_id: UUID
    replayed: bool


@dataclass(frozen=True)
class TranscriptItem:
    utterance_id: UUID
    sequence: int
    occurred_at: datetime
    action_id: UUID | None
    participant_id: UUID
    actor_kind: ParticipantActorKind
    floor_grant_id: UUID
    phase: SessionStatus
    content: str


@dataclass(frozen=True)
class TranscriptPage:
    items: tuple[TranscriptItem, ...]
    next_after_sequence: int | None


def validate_human_utterance_content(content: str) -> str:
    if not 1 <= len(content) <= 4000 or not content.strip() or "\x00" in content:
        raise UtteranceRejectedError
    return content


def derive_human_utterance_id(*, session_id: UUID, action_id: UUID) -> UUID:
    derived = uuid5(
        _UTTERANCE_ID_NAMESPACE,
        f"participant-utterance:{session_id}:{action_id}",
    )
    return UUID(bytes=derived.bytes, version=4)


def participant_utterance_created_event(
    *,
    utterance_id: UUID,
    participant_id: UUID,
    actor_kind: ParticipantActorKind,
    floor_grant_id: UUID,
    phase: SessionStatus,
    content: str,
) -> PendingEvent:
    return PendingEvent(
        event_version=1,
        event_type="participant.utterance.created",
        payload={
            "utterance_id": str(utterance_id),
            "participant_id": str(participant_id),
            "actor_kind": actor_kind.value,
            "floor_grant_id": str(floor_grant_id),
            "phase": phase.value,
            "content": content,
        },
    )


def human_utterance_command_digest(*, floor_grant_id: UUID, content: str) -> bytes:
    encoded = json.dumps(
        {
            "schema_version": 1,
            "type": "participant.utterance.submit",
            "payload": {
                "floor_grant_id": str(floor_grant_id),
                "content": content,
            },
        },
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).digest()


def _command_digest(command: SubmitHumanUtterance) -> bytes:
    return human_utterance_command_digest(
        floor_grant_id=command.floor_grant_id,
        content=command.content,
    )


def _stored_event(row: DiscussionEvent) -> StoredEvent:
    return StoredEvent(
        event_version=row.event_version,
        event_type=row.event_type,
        session_id=row.session_id,
        sequence=row.sequence,
        occurred_at=row.occurred_at,
        causation_action_id=row.causation_action_id,
        payload=row.payload,
    )


async def load_transcript_page(
    session: AsyncSession,
    *,
    owner_id: UUID,
    session_id: UUID,
    after_sequence: int,
    limit: int,
) -> TranscriptPage:
    if after_sequence < 0 or not 1 <= limit <= 200:
        raise ValueError("Invalid transcript cursor or limit.")

    try:
        owned_session_id = await session.scalar(
            select(SimulationSession.id).where(
                SimulationSession.id == session_id,
                SimulationSession.owner_user_id == owner_id,
            )
        )
        if owned_session_id is None:
            raise SessionNotFoundError

        rows = tuple(
            (
                await session.scalars(
                    select(DiscussionEvent)
                    .where(
                        DiscussionEvent.session_id == session_id,
                        DiscussionEvent.event_type == "participant.utterance.created",
                        DiscussionEvent.sequence > after_sequence,
                    )
                    .order_by(DiscussionEvent.sequence)
                    .limit(limit + 1)
                )
            ).all()
        )
        selected_rows = rows[:limit]
        projected = await project_public_events(
            session,
            [_stored_event(row) for row in selected_rows],
        )
    except SessionNotFoundError:
        raise
    except PublicEventProjectionError, SQLAlchemyError, ValueError:
        raise SessionPersistenceError from None

    items = tuple(
        TranscriptItem(
            utterance_id=UUID(str(event.payload["utterance_id"])),
            sequence=event.sequence,
            occurred_at=event.occurred_at,
            action_id=event.action_id,
            participant_id=UUID(str(event.payload["participant_id"])),
            actor_kind=ParticipantActorKind(str(event.payload["actor_kind"])),
            floor_grant_id=UUID(str(event.payload["floor_grant_id"])),
            phase=SessionStatus(str(event.payload["phase"])),
            content=str(event.payload["content"]),
        )
        for event in projected
    )
    return TranscriptPage(
        items=items,
        next_after_sequence=(
            items[-1].sequence if len(rows) > limit and items else None
        ),
    )


def _event_row(
    *,
    session_id: UUID,
    sequence: int,
    pending: PendingEvent,
    action_id: UUID,
    occurred_at: datetime,
) -> DiscussionEvent:
    return DiscussionEvent(
        session_id=session_id,
        sequence=sequence,
        event_version=pending.event_version,
        event_type=pending.event_type,
        causation_action_id=action_id,
        payload=pending.payload,
        occurred_at=occurred_at,
    )


async def _strict_replay_commit(
    session: AsyncSession,
    *,
    aggregate: SimulationSession,
    owner_id: UUID,
    command: SubmitHumanUtterance,
) -> HumanUtteranceCommit:
    rows = tuple(
        (
            await session.scalars(
                select(DiscussionEvent)
                .where(
                    DiscussionEvent.session_id == command.session_id,
                    DiscussionEvent.causation_action_id == command.action_id,
                )
                .order_by(DiscussionEvent.sequence)
            )
        ).all()
    )
    if len(rows) != 2:
        raise SessionPersistenceError
    utterance_row, release_event_row = rows
    if (
        utterance_row.event_version != 1
        or utterance_row.event_type != "participant.utterance.created"
        or release_event_row.event_version != 2
        or release_event_row.event_type != "floor.released"
        or release_event_row.sequence != utterance_row.sequence + 1
        or aggregate.last_sequence < release_event_row.sequence
    ):
        raise SessionPersistenceError

    try:
        utterance_id = UUID(str(utterance_row.payload["utterance_id"]))
        participant_id = UUID(str(utterance_row.payload["participant_id"]))
        floor_grant_id = UUID(str(utterance_row.payload["floor_grant_id"]))
        phase = SessionStatus(str(utterance_row.payload["phase"]))
    except KeyError, TypeError, ValueError:
        raise SessionPersistenceError from None

    expected_utterance_id = derive_human_utterance_id(
        session_id=command.session_id,
        action_id=command.action_id,
    )
    expected_utterance = participant_utterance_created_event(
        utterance_id=expected_utterance_id,
        participant_id=participant_id,
        actor_kind=ParticipantActorKind.HUMAN,
        floor_grant_id=floor_grant_id,
        phase=phase,
        content=command.content,
    )
    grant = await session.get(FloorGrant, floor_grant_id)
    participant = await session.get(SessionParticipant, participant_id)
    release = await session.get(FloorRelease, floor_grant_id)
    expected_release_payload = {
        "grant_id": str(floor_grant_id),
        "participant_id": str(participant_id),
        "phase": phase.value,
        "reason_code": FloorReleaseReason.SPEAKER_FINISHED.value,
    }
    if (
        utterance_id != expected_utterance_id
        or floor_grant_id != command.floor_grant_id
        or utterance_row.payload != expected_utterance.payload
        or release_event_row.payload != expected_release_payload
        or grant is None
        or grant.session_id != command.session_id
        or grant.participant_id != participant_id
        or grant.phase != phase.value
        or participant is None
        or participant.session_id != command.session_id
        or participant.actor_kind != ParticipantActorKind.HUMAN.value
        or participant.participation_role != ParticipationRole.CANDIDATE.value
        or participant.user_id != owner_id
        or release is None
        or release.session_id != command.session_id
        or release.causation_action_id != command.action_id
        or release.reason_code != FloorReleaseReason.SPEAKER_FINISHED.value
    ):
        raise SessionPersistenceError

    return HumanUtteranceCommit(
        events=(_stored_event(utterance_row), _stored_event(release_event_row)),
        utterance_id=utterance_id,
        released_floor_grant_id=floor_grant_id,
        replayed=True,
    )


async def submit_human_utterance(
    session: AsyncSession,
    *,
    owner_id: UUID,
    command: SubmitHumanUtterance,
) -> HumanUtteranceCommit:
    digest = _command_digest(command)
    pending_rejection = False
    committed: HumanUtteranceCommit | None = None
    try:
        async with session.begin():
            aggregate = await session.scalar(
                select(SimulationSession)
                .where(
                    SimulationSession.id == command.session_id,
                    SimulationSession.owner_user_id == owner_id,
                )
                .with_for_update()
            )
            if aggregate is None:
                pending_rejection = True
            else:
                accepted_action = await session.get(
                    SessionAction,
                    (command.session_id, command.action_id),
                )
                if accepted_action is not None:
                    if (
                        accepted_action.command_version != command.schema_version
                        or accepted_action.command_type != command.command_type
                        or accepted_action.payload_digest != digest
                    ):
                        raise ActionIdConflictError
                    return await _strict_replay_commit(
                        session,
                        aggregate=aggregate,
                        owner_id=owner_id,
                        command=command,
                    )

                system_event_rows = await reconcile_due_for_locked_aggregate(
                    session,
                    aggregate,
                    now=command.received_at,
                )
                if system_event_rows:
                    session.add_all(system_event_rows)
                    await session.flush()

                try:
                    content = validate_human_utterance_content(command.content)
                except UtteranceRejectedError:
                    pending_rejection = True
                else:
                    phase = SessionStatus(aggregate.status)
                    grant_id = command.floor_grant_id
                    grant = await session.get(FloorGrant, grant_id)
                    release = await session.get(FloorRelease, grant_id)
                    participant = (
                        await session.get(SessionParticipant, grant.participant_id)
                        if grant is not None
                        else None
                    )
                    authorized = (
                        phase in FLOOR_ENABLED_PHASES
                        and aggregate.current_floor_grant_id == grant_id
                        and grant is not None
                        and grant.session_id == command.session_id
                        and grant.phase == phase.value
                        and release is None
                        and participant is not None
                        and participant.session_id == command.session_id
                        and participant.actor_kind == ParticipantActorKind.HUMAN.value
                        and participant.participation_role
                        == ParticipationRole.CANDIDATE.value
                        and participant.availability
                        == ParticipantAvailability.AVAILABLE.value
                        and participant.user_id == owner_id
                    )
                    if not authorized:
                        pending_rejection = True
                    else:
                        assert grant is not None
                        assert participant is not None
                        utterance_id = derive_human_utterance_id(
                            session_id=command.session_id,
                            action_id=command.action_id,
                        )
                        session.add(
                            SessionAction(
                                session_id=command.session_id,
                                action_id=command.action_id,
                                command_version=command.schema_version,
                                command_type=command.command_type,
                                payload_digest=digest,
                                created_at=command.received_at,
                            )
                        )
                        await session.flush()
                        utterance_event = participant_utterance_created_event(
                            utterance_id=utterance_id,
                            participant_id=participant.id,
                            actor_kind=ParticipantActorKind.HUMAN,
                            floor_grant_id=grant.id,
                            phase=phase,
                            content=content,
                        )
                        release_event = await release_active_floor_for_lifecycle(
                            session,
                            aggregate,
                            reason=FloorReleaseReason.SPEAKER_FINISHED,
                            occurred_at=command.received_at,
                            action_id=command.action_id,
                        )
                        if release_event is None:
                            raise ValueError("Human floor release was not created.")
                        first_sequence = aggregate.last_sequence + 1
                        event_rows = (
                            _event_row(
                                session_id=command.session_id,
                                sequence=first_sequence,
                                pending=utterance_event,
                                action_id=command.action_id,
                                occurred_at=command.received_at,
                            ),
                            _event_row(
                                session_id=command.session_id,
                                sequence=first_sequence + 1,
                                pending=release_event,
                                action_id=command.action_id,
                                occurred_at=command.received_at,
                            ),
                        )
                        aggregate.last_sequence += 2
                        aggregate.updated_at = command.received_at
                        session.add_all(event_rows)
                        await session.flush()
                        committed = HumanUtteranceCommit(
                            events=(
                                _stored_event(event_rows[0]),
                                _stored_event(event_rows[1]),
                            ),
                            utterance_id=utterance_id,
                            released_floor_grant_id=grant.id,
                            replayed=False,
                        )
    except ActionIdConflictError, SessionPersistenceError:
        raise
    except SQLAlchemyError, ValueError:
        raise SessionPersistenceError from None

    if pending_rejection:
        raise UtteranceRejectedError
    if committed is None:
        raise SessionPersistenceError
    return committed
