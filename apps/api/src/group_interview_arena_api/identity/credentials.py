import re
import unicodedata

from pwdlib import PasswordHash
from pwdlib.exceptions import UnknownHashError
from pwdlib.hashers.argon2 import Argon2Hasher

USERNAME_MIN_LENGTH = 3
USERNAME_MAX_LENGTH = 32
PASSWORD_MIN_LENGTH = 15
PASSWORD_MAX_LENGTH = 128

ARGON2_TIME_COST = 3
ARGON2_MEMORY_COST = 65_536
ARGON2_PARALLELISM = 4
ARGON2_HASH_LENGTH = 32
ARGON2_SALT_LENGTH = 16

_USERNAME_PATTERN = re.compile(r"^[a-z][a-z0-9_]{2,31}$")
_BLOCKED_PASSWORDS = frozenset(
    {
        "groupinterviewarena",
        "password1234567",
        "qwertyuiop12345",
    }
)
_PASSWORD_HASH = PasswordHash(
    (
        Argon2Hasher(
            time_cost=ARGON2_TIME_COST,
            memory_cost=ARGON2_MEMORY_COST,
            parallelism=ARGON2_PARALLELISM,
            hash_len=ARGON2_HASH_LENGTH,
            salt_len=ARGON2_SALT_LENGTH,
        ),
    )
)


def validate_username(username: str) -> None:
    """Validate a canonical username without changing it."""
    if not _USERNAME_PATTERN.fullmatch(username):
        raise ValueError("Username does not match the canonical login format.")


def normalize_username(username: str) -> str:
    """Lowercase and validate the approved ASCII login identifier."""
    if not username.isascii():
        raise ValueError("Username does not match the canonical login format.")
    normalized = username.lower()
    validate_username(normalized)
    return normalized


def validate_password(password: str) -> None:
    """Validate the scoped password policy without changing the hash input."""
    if not unicodedata.is_normalized("NFC", password):
        raise ValueError("Password must already use NFC normalization.")
    if not PASSWORD_MIN_LENGTH <= len(password) <= PASSWORD_MAX_LENGTH:
        raise ValueError("Password length is outside the allowed range.")
    if password.casefold() in _BLOCKED_PASSWORDS:
        raise ValueError("Password is blocked by the application policy.")


def hash_password(password: str) -> str:
    """Validate and hash a password with application-owned Argon2id settings."""
    validate_password(password)
    return _PASSWORD_HASH.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password, safely rejecting malformed or unknown hashes."""
    try:
        return _PASSWORD_HASH.verify(password, password_hash)
    except TypeError, ValueError, UnknownHashError:
        return False


def verify_password_and_update(
    password: str,
    password_hash: str,
) -> tuple[bool, str | None]:
    """Verify a stored credential and rehash it when parameters are outdated."""
    try:
        return _PASSWORD_HASH.verify_and_update(password, password_hash)
    except TypeError, ValueError, UnknownHashError:
        return False, None
