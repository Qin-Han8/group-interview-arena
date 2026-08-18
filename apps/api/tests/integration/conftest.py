import os
import re
from collections.abc import Callable, Generator, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

import psycopg
import pytest
from alembic import command
from alembic.config import Config
from psycopg import sql
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL

from group_interview_arena_api.core.config import DatabaseSettings

API_ROOT = Path(__file__).resolve().parents[2]
REPOSITORY_ROOT = API_ROOT.parents[1]
ROOT_ENV_FILE = REPOSITORY_ROOT / ".env"
TEMPORARY_DATABASE_PREFIX = "gia_p04e_"
BROWSER_DATABASE_PREFIX = "gia_p05d_"
SESSION_BROWSER_DATABASE_PREFIX = "gia_p11d_"
QUESTION_BROWSER_DATABASE_PREFIX = "gia_p12c_"
TEMPORARY_DATABASE_PATTERN = re.compile(r"^gia_p(?:0(?:4e|5d)|11d|12c)_[0-9a-f]{12}$")
SYSTEM_DATABASES = frozenset({"postgres", "template0", "template1"})


class IntegrationDatabaseSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ROOT_ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    development_database: str = Field(validation_alias="POSTGRES_DB")
    username: str = Field(validation_alias="POSTGRES_USER")
    password: SecretStr = Field(validation_alias="POSTGRES_PASSWORD")


@dataclass(frozen=True)
class TemporaryDatabase:
    database_name: str
    database_url: URL

    def database_settings(self) -> DatabaseSettings:
        database_url = self.database_url.render_as_string(hide_password=False)
        return DatabaseSettings(database_url=SecretStr(database_url))

    def __repr__(self) -> str:
        return (
            "TemporaryDatabase("
            f"database_name={self.database_name!r}, database_url=<redacted>)"
        )


def validate_temporary_database_name(
    database_name: str,
    development_database: str,
) -> None:
    if (
        database_name == development_database
        or database_name in SYSTEM_DATABASES
        or not TEMPORARY_DATABASE_PATTERN.fullmatch(database_name)
    ):
        raise ValueError("Unsafe temporary database name.")


def _database_exists(
    settings: IntegrationDatabaseSettings,
    database_name: str,
) -> bool:
    with psycopg.connect(
        host="127.0.0.1",
        port=5432,
        dbname="postgres",
        user=settings.username,
        password=settings.password.get_secret_value(),
        autocommit=True,
    ) as connection:
        result = connection.execute(
            "SELECT EXISTS(SELECT 1 FROM pg_database WHERE datname = %s)",
            (database_name,),
        ).fetchone()

    return bool(result and result[0])


def _create_database(
    settings: IntegrationDatabaseSettings,
    database_name: str,
) -> None:
    validate_temporary_database_name(database_name, settings.development_database)

    with psycopg.connect(
        host="127.0.0.1",
        port=5432,
        dbname="postgres",
        user=settings.username,
        password=settings.password.get_secret_value(),
        autocommit=True,
    ) as connection:
        connection.execute(
            sql.SQL("CREATE DATABASE {}").format(sql.Identifier(database_name))
        )


def _drop_database(
    settings: IntegrationDatabaseSettings,
    database_name: str,
) -> None:
    validate_temporary_database_name(database_name, settings.development_database)

    with psycopg.connect(
        host="127.0.0.1",
        port=5432,
        dbname="postgres",
        user=settings.username,
        password=settings.password.get_secret_value(),
        autocommit=True,
    ) as connection:
        connection.execute(
            """
            SELECT pg_terminate_backend(pid)
            FROM pg_stat_activity
            WHERE datname = %s AND pid <> pg_backend_pid()
            """,
            (database_name,),
        )
        connection.execute(
            sql.SQL("DROP DATABASE {}").format(sql.Identifier(database_name))
        )

    if _database_exists(settings, database_name):
        raise RuntimeError("Temporary database cleanup verification failed.")


@pytest.fixture
def integration_database_settings() -> IntegrationDatabaseSettings:
    return IntegrationDatabaseSettings()  # pyright: ignore[reportCallIssue]


@pytest.fixture
def protected_database_name(
    integration_database_settings: IntegrationDatabaseSettings,
) -> str:
    return integration_database_settings.development_database


@pytest.fixture
def temporary_database_name_guard() -> Callable[[str, str], None]:
    return validate_temporary_database_name


@contextmanager
def temporary_database_context(
    integration_database_settings: IntegrationDatabaseSettings,
    prefix: str,
) -> Generator[TemporaryDatabase]:
    database_name = f"{prefix}{uuid4().hex[:12]}"
    validate_temporary_database_name(
        database_name,
        integration_database_settings.development_database,
    )
    _create_database(integration_database_settings, database_name)

    try:
        database_url = URL.create(
            "postgresql+psycopg",
            username=integration_database_settings.username,
            password=integration_database_settings.password.get_secret_value(),
            host="127.0.0.1",
            port=5432,
            database=database_name,
        )
        yield TemporaryDatabase(
            database_name=database_name,
            database_url=database_url,
        )
    finally:
        _drop_database(integration_database_settings, database_name)


@pytest.fixture
def temporary_database(
    integration_database_settings: IntegrationDatabaseSettings,
) -> Iterator[TemporaryDatabase]:
    with temporary_database_context(
        integration_database_settings,
        TEMPORARY_DATABASE_PREFIX,
    ) as database:
        yield database


@pytest.fixture
def browser_temporary_database(
    integration_database_settings: IntegrationDatabaseSettings,
) -> Iterator[TemporaryDatabase]:
    with temporary_database_context(
        integration_database_settings,
        BROWSER_DATABASE_PREFIX,
    ) as database:
        yield database


def migrate_database(temporary_database: TemporaryDatabase) -> None:
    config = Config()
    config.set_main_option("script_location", str(API_ROOT / "migrations"))
    database_url = temporary_database.database_settings().database_url

    with patch.dict(
        os.environ,
        {"GIA_API_DATABASE_URL": database_url.get_secret_value()},
    ):
        command.upgrade(config, "head")


@pytest.fixture
def migrated_database(temporary_database: TemporaryDatabase) -> TemporaryDatabase:
    migrate_database(temporary_database)
    return temporary_database


@pytest.fixture
def browser_migrated_database(
    browser_temporary_database: TemporaryDatabase,
) -> TemporaryDatabase:
    migrate_database(browser_temporary_database)
    return browser_temporary_database
