from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from group_interview_arena_api.db.models import (
    FloorGrant,
    FloorRelease,
    SimulationSession,
)
from group_interview_arena_api.modules.discussion_sessions.domain import (
    PendingEvent,
    SessionStatus,
)
from group_interview_arena_api.modules.floor_control.domain import (
    FloorReleaseReason,
    floor_released_event,
)


async def release_active_floor_for_lifecycle(
    session: AsyncSession,
    aggregate: SimulationSession,
    *,
    reason: FloorReleaseReason,
    occurred_at: datetime,
    action_id: UUID | None,
) -> PendingEvent | None:
    grant_id = aggregate.current_floor_grant_id
    if grant_id is None:
        return None

    grant = await session.get(FloorGrant, grant_id)
    if grant is None or grant.session_id != aggregate.id:
        raise ValueError("Current floor grant is inconsistent.")
    if await session.get(FloorRelease, grant_id) is not None:
        raise ValueError("Current floor grant has already been released.")

    session.add(
        FloorRelease(
            grant_id=grant.id,
            session_id=aggregate.id,
            causation_action_id=action_id,
            reason_code=reason.value,
            released_at=occurred_at,
        )
    )
    aggregate.current_floor_grant_id = None
    return floor_released_event(
        grant_id=grant.id,
        participant_id=grant.participant_id,
        phase=SessionStatus(grant.phase),
        reason=reason,
    )
