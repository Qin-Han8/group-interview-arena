from __future__ import annotations

from uuid import UUID

from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from group_interview_arena_api.core.config import ZhipuProviderSettings
from group_interview_arena_api.modules.ai_runtime.continuous import (
    ContinuousAiDriveResult,
    drive_continuous_ai,
)
from group_interview_arena_api.modules.floor_control.scheduler import (
    V0_1_SCHEDULER_POLICY,
)
from group_interview_arena_api.providers.zhipu import (
    ZHIPU_CONFIGURATION_VERSION,
    ZHIPU_PROVIDER_IDENTIFIER,
    ZhipuGenerationProvider,
)


class AiDriveCompositionError(RuntimeError):
    """Safe configuration boundary for the concrete provider composition."""


async def drive_configured_ai_session(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    owner_id: UUID,
    session_id: UUID,
) -> ContinuousAiDriveResult:
    try:
        settings = ZhipuProviderSettings()  # pyright: ignore[reportCallIssue]
    except ValidationError:
        raise AiDriveCompositionError(
            "AI runtime provider configuration is unavailable."
        ) from None

    provider = ZhipuGenerationProvider(settings)
    return await drive_continuous_ai(
        session_factory,
        owner_id=owner_id,
        session_id=session_id,
        provider=provider,
        provider_identifier=ZHIPU_PROVIDER_IDENTIFIER,
        model_identifier=settings.model,
        configuration_version=ZHIPU_CONFIGURATION_VERSION,
        scheduling_policy=V0_1_SCHEDULER_POLICY,
    )
