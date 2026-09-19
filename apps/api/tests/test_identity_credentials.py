import base64

import pytest
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher

from group_interview_arena_api.identity import credentials as credentials_module
from group_interview_arena_api.identity.credentials import (
    ARGON2_HASH_LENGTH,
    ARGON2_MEMORY_COST,
    ARGON2_PARALLELISM,
    ARGON2_SALT_LENGTH,
    ARGON2_TIME_COST,
    PASSWORD_MAX_LENGTH,
    hash_password,
    normalize_username,
    validate_password,
    validate_username,
    verify_password,
    verify_password_and_update,
)


def _decode_argon2_field(value: str) -> bytes:
    return base64.b64decode(value + "=" * (-len(value) % 4))


@pytest.mark.parametrize(
    ("input_username", "canonical_username"),
    [
        ("alice", "alice"),
        ("Alice_01", "alice_01"),
        ("z_9", "z_9"),
    ],
)
def test_username_normalization_returns_canonical_ascii_identifier(
    input_username: str,
    canonical_username: str,
) -> None:
    assert normalize_username(input_username) == canonical_username
    validate_username(canonical_username)


@pytest.mark.parametrize(
    "username",
    [
        "ab",
        "a" * 33,
        "1alice",
        "_alice",
        "alice smith",
        " alice",
        "alice ",
        "alice-smith",
        "Kevin",
        "álîce",
    ],
)
def test_username_policy_rejects_noncanonical_input(username: str) -> None:
    with pytest.raises(ValueError, match="canonical login format"):
        normalize_username(username)


def test_validate_username_requires_already_canonical_input() -> None:
    with pytest.raises(ValueError, match="canonical login format"):
        validate_username("Alice")


@pytest.mark.parametrize(
    "password",
    [
        "Abcd123!",
        "Group2026#",
        "Hello8@x",
        "Aa1!" + "a" * (PASSWORD_MAX_LENGTH - 4),
    ],
)
def test_password_policy_accepts_ascii_composition_and_length_boundaries(
    password: str,
) -> None:
    validate_password(password)


@pytest.mark.parametrize(
    "password",
    [
        "Ab1!xyz",
        "Aa1!" + "a" * (PASSWORD_MAX_LENGTH - 3),
    ],
)
def test_password_policy_rejects_outside_length_boundaries(password: str) -> None:
    with pytest.raises(ValueError, match="length"):
        validate_password(password)


@pytest.mark.parametrize(
    "password",
    [
        "abcdef1!",
        "ABCDEF1!",
        "Abcdefg!",
        "Abcdefg1",
        "Abcd123 ",
        "Abcd123。",
    ],
)
def test_password_policy_requires_each_ascii_character_class(password: str) -> None:
    with pytest.raises(ValueError, match="composition"):
        validate_password(password)


@pytest.mark.parametrize(
    "password",
    [
        "password1234567",
        "qwertyuiop12345",
        "groupinterviewarena",
        "GROUPINTERVIEWARENA",
    ],
)
def test_password_policy_rejects_full_match_blocklist(password: str) -> None:
    with pytest.raises(ValueError, match="blocked"):
        validate_password(password)


def test_password_blocklist_does_not_reject_substrings() -> None:
    validate_password("Prefix-password1234567-suffix!")


def test_password_policy_rejects_non_nfc_without_silently_changing_input() -> None:
    decomposed_password = "Cafe\u0301 password phrase"

    with pytest.raises(ValueError, match="NFC"):
        validate_password(decomposed_password)


def test_password_hash_preserves_significant_whitespace() -> None:
    password = "  Password words 1!  "
    password_hash = hash_password(password)

    assert verify_password(password, password_hash) is True
    assert verify_password(password.strip(), password_hash) is False


def test_password_hash_is_argon2id_with_explicit_application_parameters() -> None:
    password_hash = hash_password("A sufficiently long password 1!")
    fields = password_hash.split("$")
    parameters = dict(part.split("=") for part in fields[3].split(","))

    assert fields[1] == "argon2id"
    assert parameters == {
        "m": str(ARGON2_MEMORY_COST),
        "t": str(ARGON2_TIME_COST),
        "p": str(ARGON2_PARALLELISM),
    }
    assert len(_decode_argon2_field(fields[4])) == ARGON2_SALT_LENGTH
    assert len(_decode_argon2_field(fields[5])) == ARGON2_HASH_LENGTH


def test_password_hash_uses_random_salts_and_verifies_only_correct_password() -> None:
    password = "A sufficiently long password 1!"
    first_hash = hash_password(password)
    second_hash = hash_password(password)

    assert first_hash != password
    assert first_hash != second_hash
    assert verify_password(password, first_hash) is True
    assert verify_password("A different long password 2!", first_hash) is False


@pytest.mark.parametrize("password_hash", ["", "not-a-password-hash", "$unknown$v=1"])
def test_password_verification_safely_rejects_malformed_or_unknown_hashes(
    password_hash: str,
) -> None:
    assert verify_password("A sufficiently long password 1!", password_hash) is False


def test_existing_hash_remains_valid_after_enrollment_blocklist_changes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    password = "Future policy blocked password 1!"
    password_hash = hash_password(password)
    monkeypatch.setattr(
        credentials_module,
        "_BLOCKED_PASSWORDS",
        frozenset({password.casefold()}),
    )

    with pytest.raises(ValueError, match="blocked"):
        validate_password(password)

    assert verify_password(password, password_hash) is True


def test_password_verification_and_update_rehashes_old_argon2_parameters() -> None:
    password = "A sufficiently long rehash password 1!"
    old_password_hash = PasswordHash(
        (
            Argon2Hasher(
                time_cost=2,
                memory_cost=32_768,
                parallelism=2,
                hash_len=ARGON2_HASH_LENGTH,
                salt_len=ARGON2_SALT_LENGTH,
            ),
        )
    ).hash(password)

    valid, updated_hash = verify_password_and_update(password, old_password_hash)

    assert valid is True
    assert updated_hash is not None
    assert verify_password(password, updated_hash) is True
    fields = updated_hash.split("$")
    parameters = dict(part.split("=") for part in fields[3].split(","))
    assert fields[1] == "argon2id"
    assert parameters == {
        "m": str(ARGON2_MEMORY_COST),
        "t": str(ARGON2_TIME_COST),
        "p": str(ARGON2_PARALLELISM),
    }


def test_password_verification_and_update_keeps_current_hash() -> None:
    password = "A sufficiently long current password 1!"
    password_hash = hash_password(password)

    valid, updated_hash = verify_password_and_update(password, password_hash)

    assert valid is True
    assert updated_hash is None


@pytest.mark.parametrize("password_hash", ["", "not-a-password-hash", "$unknown$v=1"])
def test_password_verification_and_update_safely_rejects_invalid_hashes(
    password_hash: str,
) -> None:
    assert verify_password_and_update(
        "A sufficiently long password 1!",
        password_hash,
    ) == (False, None)
