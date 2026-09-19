from datetime import UTC, datetime

import pytest
from pydantic import SecretStr, ValidationError
from starlette.requests import Request

from group_interview_arena_api.core.config import Environment, Settings
from group_interview_arena_api.identity.client_source import (
    CLIENT_SOURCE_HEADER,
    InvalidClientSourceError,
    resolve_client_source,
)
from group_interview_arena_api.identity.invitations import (
    GeneratedInvitation,
    digest_invitation_code,
)
from group_interview_arena_api.identity.rate_limits import (
    ACCOUNT_SHARD_COUNT,
    LOGIN_ACCOUNT_BLOCK,
    LOGIN_ACCOUNT_WINDOW,
    LOGIN_WINDOW,
    REGISTER_WINDOW,
    account_shard,
)


def _request(*headers: tuple[bytes, bytes], client_host: str = "127.0.0.1") -> Request:
    return Request(
        {
            "type": "http",
            "method": "POST",
            "scheme": "http",
            "path": "/auth/login",
            "raw_path": b"/auth/login",
            "query_string": b"",
            "headers": list(headers),
            "client": (client_host, 12345),
            "server": ("testserver", 80),
        }
    )


def test_trusted_client_source_requires_one_canonical_ip_header() -> None:
    settings = Settings(
        environment=Environment.TEST,
        auth_trusted_caddy_mode=True,
    )
    trusted = _request((CLIENT_SOURCE_HEADER.lower().encode(), b"2001:0db8::1"))

    assert resolve_client_source(trusted, settings) == "2001:db8::1"

    for request in (
        _request(),
        _request((b"x-gia-client-ip", b"not-an-ip")),
        _request((b"x-gia-client-ip", b"127.0.0.1, 10.0.0.1")),
        _request(
            (b"x-gia-client-ip", b"127.0.0.1"),
            (b"x-gia-client-ip", b"10.0.0.1"),
        ),
    ):
        with pytest.raises(InvalidClientSourceError):
            resolve_client_source(request, settings)


def test_local_client_source_uses_socket_peer_and_canonicalizes_it() -> None:
    request = _request(
        (b"x-gia-client-ip", b"198.51.100.9"),
        client_host="127.000.000.001",
    )
    with pytest.raises(InvalidClientSourceError):
        resolve_client_source(request, Settings(environment=Environment.TEST))

    assert (
        resolve_client_source(
            _request(client_host="127.0.0.1"),
            Settings(environment=Environment.TEST),
        )
        == "127.0.0.1"
    )


def test_invitation_digest_and_repr_never_retain_plaintext_representation() -> None:
    raw_code = "unit-only-raw-invitation-secret"
    generated = GeneratedInvitation(
        raw_code=raw_code,
        expires_at=datetime(2026, 10, 3, tzinfo=UTC),
        operator_label="unit-test",
    )

    assert len(digest_invitation_code(raw_code)) == 32
    assert raw_code.encode() != digest_invitation_code(raw_code)
    assert raw_code not in repr(generated)


def test_account_identifiers_map_to_exact_bounded_shard_space() -> None:
    key = b"unit-only-rate-limit-key-32-bytes"
    shards = {account_shard(f"user_{index}", key) for index in range(20_000)}

    assert ACCOUNT_SHARD_COUNT == 16_384
    assert all(0 <= shard < ACCOUNT_SHARD_COUNT for shard in shards)
    assert account_shard("Example_User", key) == account_shard("example_user", key)
    assert account_shard("not valid", key) == account_shard("also invalid", key)


def test_production_auth_requires_trusted_mode_and_strong_hmac_key() -> None:
    with pytest.raises(ValidationError, match="trusted Caddy"):
        Settings(
            environment=Environment.PRODUCTION,
            session_cookie_secure=True,
        )
    with pytest.raises(ValidationError, match="HMAC key"):
        Settings(
            environment=Environment.PRODUCTION,
            session_cookie_secure=True,
            auth_trusted_caddy_mode=True,
        )
    with pytest.raises(ValidationError, match="at least 32 bytes"):
        Settings(
            environment=Environment.PRODUCTION,
            session_cookie_secure=True,
            auth_trusted_caddy_mode=True,
            auth_rate_limit_hmac_key=SecretStr("too-short"),
        )

    settings = Settings(
        environment=Environment.PRODUCTION,
        session_cookie_secure=True,
        auth_trusted_caddy_mode=True,
        auth_rate_limit_hmac_key=SecretStr("x" * 32),
    )
    assert settings.auth_trusted_caddy_mode is True


def test_closed_beta_rate_limit_defaults_match_accepted_thresholds() -> None:
    settings = Settings(environment=Environment.TEST)

    assert settings.auth_register_global_limit == 200
    assert settings.auth_register_source_limit == 20
    assert settings.auth_register_invite_limit == 5
    assert settings.auth_login_global_limit == 1_200
    assert settings.auth_login_source_limit == 60
    assert settings.auth_login_account_shard_limit == 10
    assert REGISTER_WINDOW.total_seconds() == 60 * 60
    assert LOGIN_WINDOW.total_seconds() == 10 * 60
    assert LOGIN_ACCOUNT_WINDOW.total_seconds() == 15 * 60
    assert LOGIN_ACCOUNT_BLOCK.total_seconds() == 15 * 60
