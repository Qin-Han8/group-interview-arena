import hashlib
import secrets
from datetime import UTC, datetime, timedelta

SESSION_DURATION = timedelta(days=7)


def generate_session_token() -> str:
    """Generate a high-entropy opaque token for browser-only storage."""
    return secrets.token_urlsafe(32)


def digest_session_token(raw_token: str) -> bytes:
    """Create the fixed-size lookup digest that may be persisted."""
    if not raw_token:
        raise ValueError("Session token must not be empty.")
    return hashlib.sha256(raw_token.encode("utf-8")).digest()


def session_expires_at(reference_time: datetime | None = None) -> datetime:
    """Calculate the fixed absolute expiry from an aware UTC instant."""
    reference = reference_time or datetime.now(UTC)
    if reference.tzinfo is None or reference.utcoffset() is None:
        raise ValueError("Session expiry requires a timezone-aware reference time.")
    return reference.astimezone(UTC) + SESSION_DURATION
