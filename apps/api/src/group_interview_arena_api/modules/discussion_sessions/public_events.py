from collections.abc import Sequence
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy import select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from group_interview_arena_api.db.models import SessionAction
from group_interview_arena_api.modules.discussion_sessions.contracts import (
    FormalEventEnvelope,
)
from group_interview_arena_api.modules.discussion_sessions.domain import StoredEvent

_FLOOR_EVENT_TYPES = frozenset(
    {"floor.granted", "floor.released", "floor.intervention_requested"}
)
_UTTERANCE_EVENT_TYPE = "participant.utterance.created"
_HUMAN_UTTERANCE_COMMAND = "participant.utterance.submit"


class PublicEventProjectionError(RuntimeError):
    """Raised when durable causation cannot be projected without leaking it."""


def project_public_action_id(
    event: StoredEvent,
    *,
    causation_command_type: str | None,
) -> UUID | None:
    durable_action_id = event.causation_action_id

    if event.event_type in _FLOOR_EVENT_TYPES:
        if event.event_version == 1:
            return durable_action_id
        if event.event_version != 2:
            raise PublicEventProjectionError("Unsupported public floor event version.")
        if durable_action_id is None:
            return None
        if causation_command_type is None:
            raise PublicEventProjectionError(
                "Floor v2 causation requires a durable command fact."
            )
        if causation_command_type == _HUMAN_UTTERANCE_COMMAND:
            return durable_action_id
        return None

    if event.event_type == _UTTERANCE_EVENT_TYPE:
        actor_kind = event.payload.get("actor_kind")
        if actor_kind == "HUMAN":
            if (
                durable_action_id is None
                or causation_command_type != _HUMAN_UTTERANCE_COMMAND
            ):
                raise PublicEventProjectionError(
                    "Human utterance causation must be its submit command."
                )
            return durable_action_id
        if actor_kind == "AI":
            if durable_action_id is not None or causation_command_type is not None:
                raise PublicEventProjectionError(
                    "AI utterances must not carry public or durable action identity."
                )
            return None
        raise PublicEventProjectionError("Unsupported utterance actor kind.")

    return durable_action_id


def project_public_event(
    event: StoredEvent,
    *,
    causation_command_type: str | None,
) -> FormalEventEnvelope:
    try:
        return FormalEventEnvelope.model_validate(
            {
                "schema_version": event.event_version,
                "type": event.event_type,
                "session_id": event.session_id,
                "sequence": event.sequence,
                "occurred_at": event.occurred_at,
                "action_id": project_public_action_id(
                    event,
                    causation_command_type=causation_command_type,
                ),
                "payload": event.payload,
            }
        )
    except PublicEventProjectionError:
        raise
    except ValidationError, ValueError, TypeError, KeyError:
        raise PublicEventProjectionError(
            "Durable event cannot be projected safely."
        ) from None


async def project_public_events(
    session: AsyncSession,
    events: Sequence[StoredEvent],
) -> list[FormalEventEnvelope]:
    causation_keys = {
        (event.session_id, event.causation_action_id)
        for event in events
        if event.causation_action_id is not None
        and (
            (event.event_type in _FLOOR_EVENT_TYPES and event.event_version == 2)
            or event.event_type == _UTTERANCE_EVENT_TYPE
        )
    }
    command_types: dict[tuple[UUID, UUID], str] = {}
    if causation_keys:
        rows = (
            await session.execute(
                select(
                    SessionAction.session_id,
                    SessionAction.action_id,
                    SessionAction.command_type,
                ).where(
                    tuple_(SessionAction.session_id, SessionAction.action_id).in_(
                        causation_keys
                    )
                )
            )
        ).all()
        command_types = {
            (session_id, action_id): command_type
            for session_id, action_id, command_type in rows
        }

    projected: list[FormalEventEnvelope] = []
    for event in events:
        command_type = None
        if event.causation_action_id is not None:
            command_type = command_types.get(
                (event.session_id, event.causation_action_id)
            )
        projected.append(
            project_public_event(
                event,
                causation_command_type=command_type,
            )
        )
    return projected
