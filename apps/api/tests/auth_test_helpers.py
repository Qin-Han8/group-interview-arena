from itertools import count

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from group_interview_arena_api.identity.invitations import generate_invitations

_LABEL_SEQUENCE = count(1)


async def create_test_invitation(
    session_factory: async_sessionmaker[AsyncSession],
) -> str:
    async with session_factory() as session:
        invitations = await generate_invitations(
            session,
            count=1,
            label=f"test-{next(_LABEL_SEQUENCE)}",
        )
    return invitations[0].raw_code
