import hashlib
import re
import secrets
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from group_interview_arena_api.db.models import BetaInvitation

DEFAULT_INVITATION_LIFETIME_DAYS = 14
INVITATION_ENTROPY_BYTES = 32
_LABEL_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")


@dataclass(frozen=True)
class GeneratedInvitation:
    raw_code: str = field(repr=False)
    expires_at: datetime
    operator_label: str


def digest_invitation_code(raw_code: str) -> bytes:
    return hashlib.sha256(raw_code.encode("utf-8")).digest()


def validate_operator_label(label: str) -> str:
    normalized = label.strip()
    if not _LABEL_PATTERN.fullmatch(normalized):
        raise ValueError("Invitation label must be 1-64 safe identifier characters.")
    return normalized


async def generate_invitations(
    session: AsyncSession,
    *,
    count: int,
    expires_in_days: int = DEFAULT_INVITATION_LIFETIME_DAYS,
    label: str,
    reference_time: datetime | None = None,
) -> list[GeneratedInvitation]:
    if not 1 <= count <= 100:
        raise ValueError("Invitation count must be between 1 and 100.")
    if not 1 <= expires_in_days <= 365:
        raise ValueError("Invitation lifetime must be between 1 and 365 days.")

    operator_label = validate_operator_label(label)
    now = reference_time or datetime.now(UTC)
    expires_at = now + timedelta(days=expires_in_days)
    generated: list[GeneratedInvitation] = []
    async with session.begin():
        for _ in range(count):
            raw_code = secrets.token_urlsafe(INVITATION_ENTROPY_BYTES)
            session.add(
                BetaInvitation(
                    code_digest=digest_invitation_code(raw_code),
                    created_at=now,
                    expires_at=expires_at,
                    operator_label=operator_label,
                )
            )
            generated.append(
                GeneratedInvitation(
                    raw_code=raw_code,
                    expires_at=expires_at,
                    operator_label=operator_label,
                )
            )
    return generated
