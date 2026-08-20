import asyncio
from contextlib import suppress
from datetime import UTC, datetime
from typing import Protocol, runtime_checkable
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from group_interview_arena_api.db.models import SimulationSession
from group_interview_arena_api.modules.discussion_sessions.domain import ACTIVE_PHASES
from group_interview_arena_api.modules.discussion_sessions.service import (
    reconcile_session_deadline,
)

RECOVERY_POLL_SECONDS = 0.25
MAX_DEADLINE_SLEEP_SECONDS = 30.0


@runtime_checkable
class DeadlineRecoveryRuntime(Protocol):
    async def stop(self) -> None: ...


def _utc_now() -> datetime:
    return datetime.now(UTC)


async def recover_due_sessions(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    now: datetime | None = None,
) -> int:
    effective_now = _utc_now() if now is None else now
    async with session_factory() as session:
        rows = list(
            (
                await session.execute(
                    select(SimulationSession.id, SimulationSession.owner_user_id)
                    .where(SimulationSession.status.in_(ACTIVE_PHASES))
                    .where(SimulationSession.phase_deadline_at <= effective_now)
                    .order_by(SimulationSession.phase_deadline_at)
                )
            ).all()
        )

    changed = 0
    for session_id, owner_id in rows:
        assert isinstance(session_id, UUID)
        assert isinstance(owner_id, UUID)
        async with session_factory() as session:
            events = await reconcile_session_deadline(
                session,
                owner_id=owner_id,
                session_id=session_id,
                now=effective_now,
            )
            changed += len(events)
    return changed


async def next_active_deadline(
    session_factory: async_sessionmaker[AsyncSession],
) -> datetime | None:
    async with session_factory() as session:
        return await session.scalar(
            select(func.min(SimulationSession.phase_deadline_at))
            .where(SimulationSession.status.in_(ACTIVE_PHASES))
            .where(SimulationSession.phase_deadline_at.is_not(None))
        )


def _sleep_seconds_until(deadline: datetime | None, now: datetime) -> float:
    if deadline is None:
        return MAX_DEADLINE_SLEEP_SECONDS
    remaining = (deadline.astimezone(UTC) - now.astimezone(UTC)).total_seconds()
    if remaining <= 0:
        return RECOVERY_POLL_SECONDS
    return min(max(remaining, RECOVERY_POLL_SECONDS), MAX_DEADLINE_SLEEP_SECONDS)


async def deadline_recovery_loop(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    while True:
        now = _utc_now()
        await recover_due_sessions(session_factory, now=now)
        deadline = await next_active_deadline(session_factory)
        await asyncio.sleep(_sleep_seconds_until(deadline, _utc_now()))


class _TaskDeadlineRecoveryRuntime:
    def __init__(self, task: asyncio.Task[None]) -> None:
        self._task = task

    async def stop(self) -> None:
        self._task.cancel()
        with suppress(asyncio.CancelledError):
            await self._task


def start_deadline_recovery_runtime(
    session_factory: async_sessionmaker[AsyncSession],
) -> DeadlineRecoveryRuntime:
    return _TaskDeadlineRecoveryRuntime(
        asyncio.create_task(deadline_recovery_loop(session_factory))
    )
