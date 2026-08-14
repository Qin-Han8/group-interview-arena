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
EXPECTED_PRODUCT_TABLES = frozenset({"auth_sessions", "users"})


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
