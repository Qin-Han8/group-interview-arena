import hashlib
import hmac
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from group_interview_arena_api.core.config import Settings
from group_interview_arena_api.db.models import AuthRateLimitBucket, BetaInvitation
from group_interview_arena_api.identity.credentials import normalize_username
from group_interview_arena_api.identity.invitations import digest_invitation_code

REGISTER_WINDOW = timedelta(hours=1)
LOGIN_WINDOW = timedelta(minutes=10)
LOGIN_ACCOUNT_WINDOW = timedelta(minutes=15)
LOGIN_ACCOUNT_BLOCK = timedelta(minutes=15)
ACCOUNT_SHARD_COUNT = 16_384
RATE_LIMIT_RETRY_AFTER_SECONDS = 900


class RateLimitScope(StrEnum):
    REGISTER_GLOBAL = "REGISTER_GLOBAL"
    REGISTER_SOURCE = "REGISTER_SOURCE"
    REGISTER_INVITE = "REGISTER_INVITE"
    LOGIN_GLOBAL = "LOGIN_GLOBAL"
    LOGIN_SOURCE = "LOGIN_SOURCE"
    LOGIN_ACCOUNT_SHARD = "LOGIN_ACCOUNT_SHARD"


class AuthRateLimitedError(Exception):
    pass


class AuthRateLimitPersistenceError(Exception):
    pass


@dataclass(frozen=True)
class _RateRule:
    scope: RateLimitScope
    key_digest: bytes
    limit: int
    window: timedelta
    block_duration: timedelta | None = None


def _hmac_digest(key: bytes, purpose: str, value: str) -> bytes:
    material = f"{purpose}\0{value}".encode()
    return hmac.new(key, material, hashlib.sha256).digest()


def _settings_key(settings: Settings) -> bytes | None:
    secret = settings.auth_rate_limit_hmac_key
    if secret is None:
        return None
    return secret.get_secret_value().encode("utf-8")


def account_shard(username: str, key: bytes) -> int:
    try:
        canonical = normalize_username(username)
    except ValueError:
        canonical = "<invalid>"
    digest = _hmac_digest(key, "account-shard-source", canonical)
    return int.from_bytes(digest[:2]) & (ACCOUNT_SHARD_COUNT - 1)


async def _apply_rule(
    session: AsyncSession,
    rule: _RateRule,
    now: datetime,
) -> bool:
    await session.execute(
        insert(AuthRateLimitBucket)
        .values(
            scope=rule.scope.value,
            key_digest=rule.key_digest,
            window_started_at=now,
            attempt_count=0,
            blocked_until=None,
            updated_at=now,
        )
        .on_conflict_do_nothing(
            index_elements=[
                AuthRateLimitBucket.scope,
                AuthRateLimitBucket.key_digest,
            ]
        )
    )
    bucket = await session.scalar(
        select(AuthRateLimitBucket)
        .where(
            AuthRateLimitBucket.scope == rule.scope.value,
            AuthRateLimitBucket.key_digest == rule.key_digest,
        )
        .with_for_update()
    )
    if bucket is None:
        raise AuthRateLimitPersistenceError

    if bucket.blocked_until is not None and bucket.blocked_until > now:
        bucket.attempt_count += 1
        bucket.updated_at = now
        return False

    if now >= bucket.window_started_at + rule.window:
        bucket.window_started_at = now
        bucket.attempt_count = 0
        bucket.blocked_until = None

    bucket.attempt_count += 1
    bucket.updated_at = now
    if bucket.attempt_count <= rule.limit:
        return True

    bucket.blocked_until = now + (rule.block_duration or rule.window)
    return False


async def _enforce(
    session_factory: async_sessionmaker[AsyncSession],
    rules: list[_RateRule],
    *,
    now: datetime,
) -> None:
    allowed = True
    try:
        async with session_factory() as session:
            async with session.begin():
                for rule in rules:
                    if not await _apply_rule(session, rule, now):
                        allowed = False
                        break
    except AuthRateLimitPersistenceError:
        raise
    except SQLAlchemyError:
        raise AuthRateLimitPersistenceError from None
    if not allowed:
        raise AuthRateLimitedError


async def enforce_register_rate_limits(
    session_factory: async_sessionmaker[AsyncSession],
    settings: Settings,
    *,
    client_source: str,
    invite_code: str,
    reference_time: datetime | None = None,
) -> None:
    key = _settings_key(settings)
    if key is None:
        return
    now = reference_time or datetime.now(UTC)
    await _enforce(
        session_factory,
        [
            _RateRule(
                RateLimitScope.REGISTER_GLOBAL,
                _hmac_digest(key, "register-global", "global"),
                settings.auth_register_global_limit,
                REGISTER_WINDOW,
            ),
            _RateRule(
                RateLimitScope.REGISTER_SOURCE,
                _hmac_digest(key, "register-source", client_source),
                settings.auth_register_source_limit,
                REGISTER_WINDOW,
            ),
        ],
        now=now,
    )

    invite_digest = digest_invitation_code(invite_code)
    try:
        async with session_factory() as lookup_session:
            invitation_exists = (
                await lookup_session.scalar(
                    select(BetaInvitation.id).where(
                        BetaInvitation.code_digest == invite_digest
                    )
                )
                is not None
            )
    except SQLAlchemyError:
        raise AuthRateLimitPersistenceError from None
    if not invitation_exists:
        return
    await _enforce(
        session_factory,
        [
            _RateRule(
                RateLimitScope.REGISTER_INVITE,
                _hmac_digest(key, "register-invite", invite_digest.hex()),
                settings.auth_register_invite_limit,
                REGISTER_WINDOW,
            )
        ],
        now=now,
    )


async def enforce_login_rate_limits(
    session_factory: async_sessionmaker[AsyncSession],
    settings: Settings,
    *,
    client_source: str,
    username: str,
    reference_time: datetime | None = None,
) -> None:
    key = _settings_key(settings)
    if key is None:
        return
    now = reference_time or datetime.now(UTC)
    shard = account_shard(username, key)
    await _enforce(
        session_factory,
        [
            _RateRule(
                RateLimitScope.LOGIN_GLOBAL,
                _hmac_digest(key, "login-global", "global"),
                settings.auth_login_global_limit,
                LOGIN_WINDOW,
            ),
            _RateRule(
                RateLimitScope.LOGIN_SOURCE,
                _hmac_digest(key, "login-source", client_source),
                settings.auth_login_source_limit,
                LOGIN_WINDOW,
            ),
            _RateRule(
                RateLimitScope.LOGIN_ACCOUNT_SHARD,
                _hmac_digest(key, "login-account-shard", str(shard)),
                settings.auth_login_account_shard_limit,
                LOGIN_ACCOUNT_WINDOW,
                LOGIN_ACCOUNT_BLOCK,
            ),
        ],
        now=now,
    )
