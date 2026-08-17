import asyncio
import os
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass
from logging import getLogger
from pathlib import Path
from typing import Protocol
from unittest.mock import patch

import pytest
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import URL, text

from group_interview_arena_api.core.config import DatabaseSettings
from group_interview_arena_api.db.runtime import (
    create_database_engine,
    dispose_database_engine,
)

pytestmark = pytest.mark.integration

API_ROOT = Path(__file__).resolve().parents[2]
BASELINE_REVISION = "7c6ccd86b3c5"
IDENTITY_REVISION = "4fe43b42641b"
SESSION_FOUNDATION_REVISION = "f1a11d15c001"
EXPECTED_PRODUCT_TABLES = frozenset(
    {
        "auth_sessions",
        "discussion_events",
        "persona_private_stances",
        "persona_templates",
        "question_persona_assignments",
        "question_templates",
        "question_versions",
        "session_actions",
        "simulation_sessions",
        "users",
    }
)


class TemporaryDatabaseContext(Protocol):
    database_name: str
    database_url: URL

    def database_settings(self) -> DatabaseSettings: ...


@dataclass(frozen=True)
class MigrationState:
    revision: str | None
    version_table_exists: bool
    product_tables: frozenset[str]


def _alembic_config() -> Config:
    config = Config()
    config.set_main_option("script_location", str(API_ROOT / "migrations"))
    return config


@contextmanager
def _temporary_migration_environment(
    temporary_database: TemporaryDatabaseContext,
) -> Generator[None]:
    database_url = temporary_database.database_settings().database_url

    with patch.dict(
        os.environ,
        {"GIA_API_DATABASE_URL": database_url.get_secret_value()},
    ):
        yield


async def _load_migration_state(
    temporary_database: TemporaryDatabaseContext,
) -> MigrationState:
    engine = create_database_engine(temporary_database.database_settings())

    try:
        async with engine.connect() as connection:
            version_table = await connection.scalar(
                text("SELECT to_regclass('public.alembic_version')")
            )
            revision = None
            if version_table is not None:
                revision = await connection.scalar(
                    text("SELECT version_num FROM alembic_version")
                )
            product_table_result = await connection.execute(
                text(
                    "SELECT tablename FROM pg_catalog.pg_tables "
                    "WHERE schemaname = 'public' "
                    "AND tablename <> 'alembic_version' "
                    "ORDER BY tablename"
                )
            )
    finally:
        await dispose_database_engine(engine)

    return MigrationState(
        revision=None if revision is None else str(revision),
        version_table_exists=version_table is not None,
        product_tables=frozenset(str(name) for name in product_table_result.scalars()),
    )


def _migration_state(
    temporary_database: TemporaryDatabaseContext,
) -> MigrationState:
    return asyncio.run(
        _load_migration_state(temporary_database),
        loop_factory=asyncio.SelectorEventLoop,
    )


def test_fresh_database_upgrades_repeatedly_without_schema_drift(
    temporary_database: TemporaryDatabaseContext,
) -> None:
    config = _alembic_config()
    script = ScriptDirectory.from_config(config)
    heads = script.get_heads()
    assert len(heads) == 1
    head = heads[0]

    with _temporary_migration_environment(temporary_database):
        command.upgrade(config, "head")
        command.current(config, check_heads=True)

        first_state = _migration_state(temporary_database)
        assert first_state == MigrationState(
            revision=head,
            version_table_exists=True,
            product_tables=EXPECTED_PRODUCT_TABLES,
        )

        command.upgrade(config, "head")
        command.current(config, check_heads=True)
        command.check(config)

        assert _migration_state(temporary_database) == first_state


def test_database_downgrades_to_identity_and_reupgrades_to_head(
    temporary_database: TemporaryDatabaseContext,
) -> None:
    config = _alembic_config()
    script = ScriptDirectory.from_config(config)
    heads = script.get_heads()
    assert len(heads) == 1
    head = heads[0]

    with _temporary_migration_environment(temporary_database):
        command.upgrade(config, "head")
        command.downgrade(config, IDENTITY_REVISION)

        assert _migration_state(temporary_database) == MigrationState(
            revision=IDENTITY_REVISION,
            version_table_exists=True,
            product_tables=frozenset({"auth_sessions", "users"}),
        )

        command.upgrade(config, "head")
        command.current(config, check_heads=True)
        command.check(config)

        assert _migration_state(temporary_database) == MigrationState(
            revision=head,
            version_table_exists=True,
            product_tables=EXPECTED_PRODUCT_TABLES,
        )


def test_database_downgrades_to_p1_1_and_reupgrades_to_head(
    temporary_database: TemporaryDatabaseContext,
) -> None:
    config = _alembic_config()
    head = ScriptDirectory.from_config(config).get_current_head()
    assert head is not None

    with _temporary_migration_environment(temporary_database):
        command.upgrade(config, "head")
        command.downgrade(config, SESSION_FOUNDATION_REVISION)

        assert _migration_state(temporary_database) == MigrationState(
            revision=SESSION_FOUNDATION_REVISION,
            version_table_exists=True,
            product_tables=frozenset(
                {
                    "auth_sessions",
                    "discussion_events",
                    "session_actions",
                    "simulation_sessions",
                    "users",
                }
            ),
        )

        command.upgrade(config, "head")
        command.current(config, check_heads=True)
        command.check(config)

        assert _migration_state(temporary_database) == MigrationState(
            revision=head,
            version_table_exists=True,
            product_tables=EXPECTED_PRODUCT_TABLES,
        )


def test_database_downgrades_to_baseline_and_reupgrades_to_head(
    temporary_database: TemporaryDatabaseContext,
) -> None:
    config = _alembic_config()
    script = ScriptDirectory.from_config(config)
    heads = script.get_heads()
    assert len(heads) == 1
    head = heads[0]

    with _temporary_migration_environment(temporary_database):
        command.upgrade(config, "head")
        command.downgrade(config, BASELINE_REVISION)

        assert _migration_state(temporary_database) == MigrationState(
            revision=BASELINE_REVISION,
            version_table_exists=True,
            product_tables=frozenset(),
        )

        command.upgrade(config, "head")
        command.current(config, check_heads=True)
        command.check(config)

        assert _migration_state(temporary_database) == MigrationState(
            revision=head,
            version_table_exists=True,
            product_tables=EXPECTED_PRODUCT_TABLES,
        )


async def _load_p1_1b_catalog(
    temporary_database: TemporaryDatabaseContext,
) -> tuple[list[tuple[str, str, str, str, str | None]], set[str], set[str]]:
    engine = create_database_engine(temporary_database.database_settings())

    try:
        async with engine.connect() as connection:
            columns_result = await connection.execute(
                text(
                    "SELECT table_name, column_name, udt_name, is_nullable, "
                    "column_default FROM information_schema.columns "
                    "WHERE table_schema = 'public' "
                    "AND table_name IN "
                    "('simulation_sessions', 'session_actions', 'discussion_events') "
                    "ORDER BY table_name, ordinal_position"
                )
            )
            constraints_result = await connection.execute(
                text(
                    "SELECT conname FROM pg_catalog.pg_constraint "
                    "WHERE connamespace = 'public'::regnamespace "
                    "AND contype IN ('p', 'f', 'c') "
                    "AND conrelid IN "
                    "('simulation_sessions'::regclass, 'session_actions'::regclass, "
                    "'discussion_events'::regclass)"
                )
            )
            indexes_result = await connection.execute(
                text(
                    "SELECT indexname FROM pg_catalog.pg_indexes "
                    "WHERE schemaname = 'public' "
                    "AND tablename IN "
                    "('simulation_sessions', 'session_actions', 'discussion_events')"
                )
            )
            columns = [
                (
                    str(row.table_name),
                    str(row.column_name),
                    str(row.udt_name),
                    str(row.is_nullable),
                    None if row.column_default is None else str(row.column_default),
                )
                for row in columns_result
            ]
            constraints = {str(name) for name in constraints_result.scalars()}
            indexes = {str(name) for name in indexes_result.scalars()}
    finally:
        await dispose_database_engine(engine)

    return columns, constraints, indexes


def test_head_has_exact_p1_1b_columns_constraints_and_indexes(
    temporary_database: TemporaryDatabaseContext,
) -> None:
    config = _alembic_config()
    with _temporary_migration_environment(temporary_database):
        command.upgrade(config, "head")

    columns, constraints, indexes = asyncio.run(
        _load_p1_1b_catalog(temporary_database),
        loop_factory=asyncio.SelectorEventLoop,
    )

    assert columns == [
        ("discussion_events", "session_id", "uuid", "NO", None),
        ("discussion_events", "sequence", "int8", "NO", None),
        ("discussion_events", "event_version", "int2", "NO", None),
        ("discussion_events", "event_type", "varchar", "NO", None),
        ("discussion_events", "causation_action_id", "uuid", "YES", None),
        ("discussion_events", "payload", "jsonb", "NO", None),
        ("discussion_events", "occurred_at", "timestamptz", "NO", None),
        ("session_actions", "session_id", "uuid", "NO", None),
        ("session_actions", "action_id", "uuid", "NO", None),
        ("session_actions", "command_version", "int2", "NO", None),
        ("session_actions", "command_type", "varchar", "NO", None),
        ("session_actions", "payload_digest", "bytea", "NO", None),
        ("session_actions", "created_at", "timestamptz", "NO", None),
        ("simulation_sessions", "id", "uuid", "NO", None),
        ("simulation_sessions", "owner_user_id", "uuid", "NO", None),
        ("simulation_sessions", "status", "varchar", "NO", None),
        ("simulation_sessions", "last_sequence", "int8", "NO", "0"),
        ("simulation_sessions", "created_at", "timestamptz", "NO", None),
        ("simulation_sessions", "updated_at", "timestamptz", "NO", None),
        ("simulation_sessions", "question_version_id", "uuid", "YES", None),
    ]
    assert constraints == {
        "ck_discussion_events_event_version_positive",
        "ck_discussion_events_sequence_positive",
        "ck_session_actions_command_version_positive",
        "ck_session_actions_payload_digest_sha256",
        "ck_simulation_sessions_last_sequence_non_negative",
        "fk_discussion_events_session_id_session_actions",
        "fk_discussion_events_session_id_simulation_sessions",
        "fk_session_actions_session_id_simulation_sessions",
        "fk_simulation_sessions_owner_user_id_users",
        "fk_simulation_sessions_question_version_id_question_versions",
        "pk_discussion_events",
        "pk_session_actions",
        "pk_simulation_sessions",
    }
    assert indexes == {
        "ix_discussion_events_session_causation_sequence",
        "pk_discussion_events",
        "pk_session_actions",
        "pk_simulation_sessions",
    }


def test_migration_command_preserves_existing_logger_state(
    temporary_database: TemporaryDatabaseContext,
) -> None:
    config = _alembic_config()
    assert config.config_file_name is None

    sentinel_logger = getLogger("group_interview_arena_api.migration_test_sentinel")
    initial_state = (
        sentinel_logger.disabled,
        sentinel_logger.level,
        tuple(sentinel_logger.handlers),
        sentinel_logger.propagate,
    )

    with _temporary_migration_environment(temporary_database):
        command.upgrade(config, "head")

    assert (
        sentinel_logger.disabled,
        sentinel_logger.level,
        tuple(sentinel_logger.handlers),
        sentinel_logger.propagate,
    ) == initial_state
