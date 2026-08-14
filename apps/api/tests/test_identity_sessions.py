from datetime import UTC, datetime, timedelta, timezone

import pytest

from group_interview_arena_api.identity.sessions import (
    SESSION_DURATION,
    digest_session_token,
    generate_session_token,
    session_expires_at,
)


def test_session_tokens_are_nonempty_and_distinct() -> None:
    first_token = generate_session_token()
    second_token = generate_session_token()

    assert first_token
    assert second_token
    assert first_token != second_token


def test_session_digest_is_deterministic_fixed_size_bytes() -> None:
    raw_token = "test-only-session-token"

    first_digest = digest_session_token(raw_token)
    second_digest = digest_session_token(raw_token)

    assert isinstance(first_digest, bytes)
    assert len(first_digest) == 32
    assert first_digest == second_digest
    assert first_digest != raw_token.encode()
    assert digest_session_token("different-test-token") != first_digest


def test_session_digest_rejects_empty_token() -> None:
    with pytest.raises(ValueError, match="must not be empty"):
        digest_session_token("")


def test_session_expiry_is_seven_days_from_supplied_utc_time() -> None:
    reference = datetime(2026, 8, 14, 10, 30, tzinfo=UTC)

    expiry = session_expires_at(reference)

    assert SESSION_DURATION == timedelta(days=7)
    assert expiry == reference + timedelta(days=7)
    assert expiry.tzinfo is UTC


def test_session_expiry_normalizes_aware_reference_to_utc() -> None:
    reference = datetime(2026, 8, 14, 18, 30, tzinfo=timezone(timedelta(hours=8)))

    assert session_expires_at(reference) == datetime(2026, 8, 21, 10, 30, tzinfo=UTC)


def test_session_expiry_rejects_naive_reference_time() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        session_expires_at(datetime(2026, 8, 14, 10, 30))
