import asyncio
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Never
from uuid import UUID

from psycopg.errors import UniqueViolation
from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from group_interview_arena_api.core.logging import log_event
from group_interview_arena_api.db.models import AuthSession, BetaInvitation, User
from group_interview_arena_api.identity.credentials import (
    hash_password,
    normalize_username,
    verify_password_and_update,
)
from group_interview_arena_api.identity.invitations import digest_invitation_code
from group_interview_arena_api.identity.sessions import (
    digest_session_token,
    generate_session_token,
    session_expires_at,
)

logger = logging.getLogger(__name__)

_USERNAME_UNIQUE_CONSTRAINT = "uq_users_username"
# Fixed non-secret Argon2id artifact for unknown-user verification work. It is
# never assigned to an account and is not generated during module import.
DUMMY_PASSWORD_HASH = (
    "$argon2id$v=19$m=65536,t=3,p=4$MJ+BSahtTahE9CvwZe4Fyg$"
    "7T6aJG5dRCLpAGPh9iHve8c46YMifmwzfiRH+Rt8d8s"
)


class InvalidUsernameError(ValueError):
    pass


class InvalidPasswordError(ValueError):
    pass


class UsernameUnavailableError(Exception):
    pass


class EnrollmentUnavailableError(Exception):
    pass


class InvalidCredentialsError(Exception):
    pass


class AuthenticationPersistenceError(Exception):
    pass


@dataclass(frozen=True)
class AuthenticationResult:
    user_id: UUID
    username: str
    raw_session_token: str = field(repr=False)


@dataclass(frozen=True)
class CurrentUser:
    user_id: UUID
    username: str


def _is_username_unique_violation(exception: IntegrityError) -> bool:
    return (
        isinstance(exception.orig, UniqueViolation)
        and exception.orig.diag.constraint_name == _USERNAME_UNIQUE_CONSTRAINT
    )


def _raise_persistence_error(operation: str) -> Never:
    del operation
    log_event(
        logger,
        logging.ERROR,
        "auth.persistence.failed",
        exception_category="persistence_error",
    )
    raise AuthenticationPersistenceError from None


async def register_user(
    session: AsyncSession,
    *,
    username: str,
    password: str,
    invite_code: str,
    reference_time: datetime | None = None,
) -> AuthenticationResult:
    try:
        canonical_username = normalize_username(username)
    except ValueError:
        raise InvalidUsernameError from None

    try:
        password_hash = await asyncio.to_thread(hash_password, password)
    except ValueError:
        raise InvalidPasswordError from None

    now = reference_time or datetime.now(UTC)
    try:
        user = User(
            username=canonical_username,
            password_hash=password_hash,
        )
        raw_token = ""
        async with session.begin():
            invitation = await session.scalar(
                select(BetaInvitation)
                .where(
                    BetaInvitation.code_digest == digest_invitation_code(invite_code)
                )
                .with_for_update()
            )
            if (
                invitation is None
                or invitation.expires_at <= now
                or invitation.consumed_at is not None
                or invitation.revoked_at is not None
            ):
                raise EnrollmentUnavailableError

            session.add(user)
            await session.flush()

            raw_token = generate_session_token()
            session.add(
                AuthSession(
                    user_id=user.id,
                    token_hash=digest_session_token(raw_token),
                    expires_at=session_expires_at(),
                )
            )
            invitation.consumed_at = now
            invitation.consumed_by_user_id = user.id
    except IntegrityError as exception:
        if _is_username_unique_violation(exception):
            raise EnrollmentUnavailableError from None
        _raise_persistence_error("register")
    except SQLAlchemyError:
        _raise_persistence_error("register")

    return AuthenticationResult(
        user_id=user.id,
        username=user.username,
        raw_session_token=raw_token,
    )


async def login_user(
    session: AsyncSession,
    *,
    username: str,
    password: str,
) -> AuthenticationResult:
    try:
        canonical_username = normalize_username(username)
    except ValueError:
        await asyncio.to_thread(
            verify_password_and_update,
            password,
            DUMMY_PASSWORD_HASH,
        )
        raise InvalidCredentialsError from None

    try:
        user = await session.scalar(
            select(User).where(User.username == canonical_username)
        )
    except SQLAlchemyError:
        _raise_persistence_error("login")
    if user is None:
        try:
            await session.rollback()
        except SQLAlchemyError:
            _raise_persistence_error("login")
        await asyncio.to_thread(
            verify_password_and_update,
            password,
            DUMMY_PASSWORD_HASH,
        )
        raise InvalidCredentialsError from None

    user_id = user.id
    stored_username = user.username
    stored_password_hash = user.password_hash
    try:
        await session.rollback()
    except SQLAlchemyError:
        _raise_persistence_error("login")

    valid, updated_hash = await asyncio.to_thread(
        verify_password_and_update,
        password,
        stored_password_hash,
    )
    if not valid:
        raise InvalidCredentialsError

    raw_token = generate_session_token()
    try:
        async with session.begin():
            if updated_hash is not None:
                await session.execute(
                    update(User)
                    .where(User.id == user_id)
                    .values(password_hash=updated_hash)
                )
            session.add(
                AuthSession(
                    user_id=user_id,
                    token_hash=digest_session_token(raw_token),
                    expires_at=session_expires_at(),
                )
            )
    except IntegrityError:
        _raise_persistence_error("login")
    except SQLAlchemyError:
        _raise_persistence_error("login")

    return AuthenticationResult(
        user_id=user_id,
        username=stored_username,
        raw_session_token=raw_token,
    )


async def get_current_user(
    session: AsyncSession,
    raw_token: str | None,
    *,
    reference_time: datetime | None = None,
) -> CurrentUser | None:
    if not raw_token:
        return None

    now = reference_time or datetime.now(UTC)
    try:
        user = await session.scalar(
            select(User)
            .join(AuthSession, AuthSession.user_id == User.id)
            .where(
                AuthSession.token_hash == digest_session_token(raw_token),
                AuthSession.expires_at > now,
            )
        )
    except SQLAlchemyError:
        _raise_persistence_error("resolve_session")
    if user is None:
        return None
    return CurrentUser(user_id=user.id, username=user.username)


async def logout_session(session: AsyncSession, raw_token: str | None) -> None:
    if not raw_token:
        return

    try:
        async with session.begin():
            await session.execute(
                delete(AuthSession).where(
                    AuthSession.token_hash == digest_session_token(raw_token)
                )
            )
    except SQLAlchemyError:
        _raise_persistence_error("logout")
