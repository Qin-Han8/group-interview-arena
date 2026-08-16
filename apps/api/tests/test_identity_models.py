from typing import cast

from sqlalchemy import (
    DateTime,
    Index,
    LargeBinary,
    String,
    Table,
    Text,
    UniqueConstraint,
    Uuid,
)

from group_interview_arena_api.db import AuthSession, Base, User


def test_identity_metadata_contains_identity_tables() -> None:
    assert {"auth_sessions", "users"} <= set(Base.metadata.tables)


def test_users_model_has_exact_columns_and_constraints() -> None:
    table = cast(Table, User.__table__)

    assert list(table.columns) == [
        table.c.id,
        table.c.username,
        table.c.password_hash,
        table.c.created_at,
        table.c.updated_at,
    ]
    assert isinstance(table.c.id.type, Uuid)
    assert table.c.id.primary_key is True
    assert table.c.id.nullable is False
    assert isinstance(table.c.username.type, String)
    assert table.c.username.type.length == 32
    assert table.c.username.nullable is False
    assert isinstance(table.c.password_hash.type, Text)
    assert table.c.password_hash.nullable is False
    assert isinstance(table.c.created_at.type, DateTime)
    assert table.c.created_at.type.timezone is True
    assert table.c.created_at.nullable is False
    assert isinstance(table.c.updated_at.type, DateTime)
    assert table.c.updated_at.type.timezone is True
    assert table.c.updated_at.nullable is False
    assert {constraint.name for constraint in table.constraints} == {
        "pk_users",
        "uq_users_username",
    }
    assert sum(isinstance(item, UniqueConstraint) for item in table.constraints) == 1


def test_auth_sessions_model_has_exact_columns_constraints_and_index() -> None:
    table = cast(Table, AuthSession.__table__)

    assert list(table.columns) == [
        table.c.id,
        table.c.user_id,
        table.c.token_hash,
        table.c.created_at,
        table.c.expires_at,
    ]
    assert isinstance(table.c.id.type, Uuid)
    assert table.c.id.primary_key is True
    assert table.c.id.nullable is False
    assert isinstance(table.c.user_id.type, Uuid)
    assert table.c.user_id.nullable is False
    assert next(iter(table.c.user_id.foreign_keys)).ondelete == "CASCADE"
    assert isinstance(table.c.token_hash.type, LargeBinary)
    assert table.c.token_hash.type.length == 32
    assert table.c.token_hash.nullable is False
    assert isinstance(table.c.created_at.type, DateTime)
    assert table.c.created_at.type.timezone is True
    assert isinstance(table.c.expires_at.type, DateTime)
    assert table.c.expires_at.type.timezone is True
    assert {constraint.name for constraint in table.constraints} == {
        "fk_auth_sessions_user_id_users",
        "pk_auth_sessions",
        "uq_auth_sessions_token_hash",
    }
    assert {index.name for index in table.indexes if isinstance(index, Index)} == {
        "ix_auth_sessions_expires_at"
    }
