import asyncio
import os
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass
from logging import getLogger
from pathlib import Path
from typing import Protocol
from unittest.mock import patch
from uuid import UUID, uuid4

import pytest
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import URL, text

from group_interview_arena_api.core.config import DatabaseSettings
from group_interview_arena_api.db.models import User
from group_interview_arena_api.db.runtime import (
    create_database_engine,
    create_database_session_factory,
    dispose_database_engine,
)
from group_interview_arena_api.modules.discussion_sessions.service import (
    create_session,
)
from group_interview_arena_api.modules.question_personas.seed import (
    INTERNAL_VALIDATION_BUNDLE,
    seed_question_persona_foundation,
)

pytestmark = pytest.mark.integration

API_ROOT = Path(__file__).resolve().parents[2]
BASELINE_REVISION = "7c6ccd86b3c5"
IDENTITY_REVISION = "4fe43b42641b"
SESSION_FOUNDATION_REVISION = "f1a11d15c001"
QUESTION_PERSONA_REVISION = "f1a12b15c002"
SESSION_PHASE_TIMING_REVISION = "f1a13b15c003"
FLOOR_CONTROL_FOUNDATION_REVISION = "f1a14b15c004"
DISCUSSION_MEMORY_REVISION = "f1a16b16c006"
METADATA_TYPE_CLOSURE_REVISION = "f1a16e16c007"
REPORT_PERSISTENCE_REVISION = "f1a17b17c008"
P1_2_PRODUCT_TABLES = frozenset(
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
EXPECTED_PRODUCT_TABLES = P1_2_PRODUCT_TABLES | {
    "ai_utterances",
    "floor_decisions",
    "floor_grants",
    "floor_interventions",
    "floor_releases",
    "discussion_memory_revisions",
    "discussion_memory_states",
    "evaluation_reports",
    "evidence_items",
    "llm_generation_requests",
    "prompt_versions",
    "session_participants",
    "speaking_opportunities",
}


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


def test_database_downgrades_to_p1_2_and_reupgrades_to_head(
    temporary_database: TemporaryDatabaseContext,
) -> None:
    config = _alembic_config()
    head = ScriptDirectory.from_config(config).get_current_head()
    assert head is not None

    with _temporary_migration_environment(temporary_database):
        command.upgrade(config, "head")
        command.downgrade(config, QUESTION_PERSONA_REVISION)

        assert _migration_state(temporary_database) == MigrationState(
            revision=QUESTION_PERSONA_REVISION,
            version_table_exists=True,
            product_tables=P1_2_PRODUCT_TABLES,
        )

        command.upgrade(config, "head")
        command.current(config, check_heads=True)
        command.check(config)

        assert _migration_state(temporary_database) == MigrationState(
            revision=head,
            version_table_exists=True,
            product_tables=EXPECTED_PRODUCT_TABLES,
        )


def test_database_downgrades_to_p1_3_and_reupgrades_to_head(
    temporary_database: TemporaryDatabaseContext,
) -> None:
    config = _alembic_config()
    head = ScriptDirectory.from_config(config).get_current_head()
    assert head is not None

    with _temporary_migration_environment(temporary_database):
        command.upgrade(config, "head")
        command.downgrade(config, SESSION_PHASE_TIMING_REVISION)

        assert _migration_state(temporary_database) == MigrationState(
            revision=SESSION_PHASE_TIMING_REVISION,
            version_table_exists=True,
            product_tables=P1_2_PRODUCT_TABLES,
        )

        command.upgrade(config, "head")
        command.current(config, check_heads=True)
        command.check(config)

        assert _migration_state(temporary_database) == MigrationState(
            revision=head,
            version_table_exists=True,
            product_tables=EXPECTED_PRODUCT_TABLES,
        )


def test_database_downgrades_to_p1_4_and_reupgrades_to_head(
    temporary_database: TemporaryDatabaseContext,
) -> None:
    config = _alembic_config()
    head = ScriptDirectory.from_config(config).get_current_head()
    assert head is not None

    with _temporary_migration_environment(temporary_database):
        command.upgrade(config, "head")
        command.downgrade(config, FLOOR_CONTROL_FOUNDATION_REVISION)

        assert _migration_state(temporary_database) == MigrationState(
            revision=FLOOR_CONTROL_FOUNDATION_REVISION,
            version_table_exists=True,
            product_tables=EXPECTED_PRODUCT_TABLES
            - {
                "ai_utterances",
                "llm_generation_requests",
                "prompt_versions",
                "discussion_memory_revisions",
                "discussion_memory_states",
                "evaluation_reports",
                "evidence_items",
            },
        )

        command.upgrade(config, "head")
        command.current(config, check_heads=True)
        command.check(config)

        assert _migration_state(temporary_database) == MigrationState(
            revision=head,
            version_table_exists=True,
            product_tables=EXPECTED_PRODUCT_TABLES,
        )


def test_database_downgrades_to_p1_6_memory_and_reupgrades_to_head(
    temporary_database: TemporaryDatabaseContext,
) -> None:
    config = _alembic_config()
    head = ScriptDirectory.from_config(config).get_current_head()
    assert head == REPORT_PERSISTENCE_REVISION

    with _temporary_migration_environment(temporary_database):
        command.upgrade(config, "head")
        command.downgrade(config, DISCUSSION_MEMORY_REVISION)

        assert _migration_state(temporary_database) == MigrationState(
            revision=DISCUSSION_MEMORY_REVISION,
            version_table_exists=True,
            product_tables=EXPECTED_PRODUCT_TABLES
            - {"evaluation_reports", "evidence_items"},
        )

        command.upgrade(config, "head")
        command.current(config, check_heads=True)
        command.check(config)

        assert _migration_state(temporary_database) == MigrationState(
            revision=REPORT_PERSISTENCE_REVISION,
            version_table_exists=True,
            product_tables=EXPECTED_PRODUCT_TABLES,
        )


async def _create_backfill_source_session(
    temporary_database: TemporaryDatabaseContext,
) -> UUID:
    engine = create_database_engine(temporary_database.database_settings())
    session_factory = create_database_session_factory(engine)
    try:
        await seed_question_persona_foundation(session_factory)
        owner_id = uuid4()
        async with session_factory() as session:
            async with session.begin():
                session.add(
                    User(
                        id=owner_id,
                        username=f"backfill_{uuid4().hex[:10]}",
                        password_hash="not-used",
                    )
                )
        async with session_factory() as session:
            snapshot = await create_session(
                session,
                owner_id=owner_id,
                question_version_id=INTERNAL_VALIDATION_BUNDLE.version_id,
            )
        return snapshot.session_id
    finally:
        await dispose_database_engine(engine)


async def _load_backfilled_roster(
    temporary_database: TemporaryDatabaseContext,
    session_id: UUID,
) -> list[tuple[str, str, int]]:
    engine = create_database_engine(temporary_database.database_settings())
    try:
        async with engine.connect() as connection:
            result = await connection.execute(
                text(
                    "SELECT actor_kind, participation_role, seat_order "
                    "FROM session_participants WHERE session_id = :session_id "
                    "ORDER BY seat_order"
                ),
                {"session_id": session_id},
            )
            return [
                (str(row.actor_kind), str(row.participation_role), int(row.seat_order))
                for row in result
            ]
    finally:
        await dispose_database_engine(engine)


def test_p1_4_upgrade_backfills_bound_existing_session_roster(
    temporary_database: TemporaryDatabaseContext,
) -> None:
    config = _alembic_config()
    with _temporary_migration_environment(temporary_database):
        command.upgrade(config, "head")
        session_id = asyncio.run(
            _create_backfill_source_session(temporary_database),
            loop_factory=asyncio.SelectorEventLoop,
        )
        command.downgrade(config, SESSION_PHASE_TIMING_REVISION)
        command.upgrade(config, "head")

    roster = asyncio.run(
        _load_backfilled_roster(temporary_database, session_id),
        loop_factory=asyncio.SelectorEventLoop,
    )
    assert roster == [
        ("HUMAN", "CANDIDATE", 1),
        ("AI", "CANDIDATE", 2),
        ("AI", "CANDIDATE", 3),
        ("AI", "CANDIDATE", 4),
    ]


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
        ("simulation_sessions", "phase_started_at", "timestamptz", "YES", None),
        ("simulation_sessions", "phase_deadline_at", "timestamptz", "YES", None),
        ("simulation_sessions", "phase_duration_plan", "jsonb", "YES", None),
        ("simulation_sessions", "current_floor_grant_id", "uuid", "YES", None),
    ]
    assert constraints == {
        "ck_discussion_events_event_version_positive",
        "ck_discussion_events_sequence_positive",
        "ck_session_actions_command_version_positive",
        "ck_session_actions_payload_digest_sha256",
        "ck_simulation_sessions_last_sequence_non_negative",
        "ck_simulation_sessions_phase_duration_plan_required_keys",
        "ck_simulation_sessions_phase_timing_pair_valid",
        "ck_simulation_sessions_phase_timing_status_consistent",
        "fk_discussion_events_session_id_session_actions",
        "fk_discussion_events_session_id_simulation_sessions",
        "fk_session_actions_session_id_simulation_sessions",
        "fk_simulation_sessions_owner_user_id_users",
        "fk_simulation_sessions_question_version_id_question_versions",
        "fk_simulation_sessions_current_floor_grant",
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


async def _insert_and_load_existing_user(
    temporary_database: TemporaryDatabaseContext,
    *,
    user_id: UUID,
    insert: bool,
) -> str | None:
    engine = create_database_engine(temporary_database.database_settings())
    try:
        async with engine.begin() as connection:
            if insert:
                await connection.execute(
                    text(
                        "INSERT INTO users "
                        "(id, username, password_hash, created_at, updated_at) "
                        "VALUES (:id, 'p17b-existing-user', 'hash', now(), now())"
                    ),
                    {"id": user_id},
                )
            return await connection.scalar(
                text("SELECT username FROM users WHERE id = :id"),
                {"id": user_id},
            )
    finally:
        await dispose_database_engine(engine)


def test_report_migration_preserves_previous_head_and_existing_data(
    temporary_database: TemporaryDatabaseContext,
) -> None:
    config = _alembic_config()
    user_id = uuid4()

    with _temporary_migration_environment(temporary_database):
        command.upgrade(config, METADATA_TYPE_CLOSURE_REVISION)
        assert _migration_state(temporary_database) == MigrationState(
            revision=METADATA_TYPE_CLOSURE_REVISION,
            version_table_exists=True,
            product_tables=EXPECTED_PRODUCT_TABLES
            - {"evaluation_reports", "evidence_items"},
        )
        assert (
            asyncio.run(
                _insert_and_load_existing_user(
                    temporary_database,
                    user_id=user_id,
                    insert=True,
                ),
                loop_factory=asyncio.SelectorEventLoop,
            )
            == "p17b-existing-user"
        )

        command.upgrade(config, REPORT_PERSISTENCE_REVISION)
        assert _migration_state(temporary_database) == MigrationState(
            revision=REPORT_PERSISTENCE_REVISION,
            version_table_exists=True,
            product_tables=EXPECTED_PRODUCT_TABLES,
        )

        command.downgrade(config, METADATA_TYPE_CLOSURE_REVISION)
        assert _migration_state(temporary_database) == MigrationState(
            revision=METADATA_TYPE_CLOSURE_REVISION,
            version_table_exists=True,
            product_tables=EXPECTED_PRODUCT_TABLES
            - {"evaluation_reports", "evidence_items"},
        )
        assert (
            asyncio.run(
                _insert_and_load_existing_user(
                    temporary_database,
                    user_id=user_id,
                    insert=False,
                ),
                loop_factory=asyncio.SelectorEventLoop,
            )
            == "p17b-existing-user"
        )

        command.upgrade(config, "head")
        command.current(config, check_heads=True)
        command.check(config)
        assert _migration_state(temporary_database) == MigrationState(
            revision=REPORT_PERSISTENCE_REVISION,
            version_table_exists=True,
            product_tables=EXPECTED_PRODUCT_TABLES,
        )


async def _load_report_catalog(
    temporary_database: TemporaryDatabaseContext,
) -> tuple[
    list[tuple[str, str, str, str, int | None, int | None, int | None]],
    dict[str, tuple[str, bool, bool]],
    set[str],
]:
    engine = create_database_engine(temporary_database.database_settings())
    try:
        async with engine.connect() as connection:
            columns_result = await connection.execute(
                text(
                    "SELECT table_name, column_name, udt_name, is_nullable, "
                    "character_maximum_length, numeric_precision, numeric_scale "
                    "FROM information_schema.columns "
                    "WHERE table_schema = 'public' "
                    "AND table_name IN ('evaluation_reports', 'evidence_items') "
                    "ORDER BY table_name, ordinal_position"
                )
            )
            constraints_result = await connection.execute(
                text(
                    "SELECT conname, contype, condeferrable, condeferred "
                    "FROM pg_catalog.pg_constraint "
                    "WHERE connamespace = 'public'::regnamespace "
                    "AND contype IN ('p', 'f', 'c', 'u') "
                    "AND conrelid IN "
                    "('evaluation_reports'::regclass, 'evidence_items'::regclass) "
                    "ORDER BY conname"
                )
            )
            indexes_result = await connection.execute(
                text(
                    "SELECT indexname FROM pg_catalog.pg_indexes "
                    "WHERE schemaname = 'public' "
                    "AND tablename IN ('evaluation_reports', 'evidence_items')"
                )
            )
            columns = [
                (
                    str(row.table_name),
                    str(row.column_name),
                    str(row.udt_name),
                    str(row.is_nullable),
                    None
                    if row.character_maximum_length is None
                    else int(row.character_maximum_length),
                    None
                    if row.numeric_precision is None
                    else int(row.numeric_precision),
                    None if row.numeric_scale is None else int(row.numeric_scale),
                )
                for row in columns_result
            ]
            constraints = {
                str(row.conname): (
                    str(row.contype),
                    bool(row.condeferrable),
                    bool(row.condeferred),
                )
                for row in constraints_result
            }
            indexes = {str(name) for name in indexes_result.scalars()}
    finally:
        await dispose_database_engine(engine)
    return columns, constraints, indexes


def test_report_head_has_exact_columns_constraints_and_indexes(
    temporary_database: TemporaryDatabaseContext,
) -> None:
    config = _alembic_config()
    with _temporary_migration_environment(temporary_database):
        command.upgrade(config, "head")

    columns, constraints, indexes = asyncio.run(
        _load_report_catalog(temporary_database),
        loop_factory=asyncio.SelectorEventLoop,
    )
    assert columns == [
        ("evaluation_reports", "id", "uuid", "NO", None, None, None),
        ("evaluation_reports", "session_id", "uuid", "NO", None, None, None),
        ("evaluation_reports", "report_schema_version", "int2", "NO", None, 16, 0),
        ("evaluation_reports", "derivation_version", "varchar", "NO", 128, None, None),
        ("evaluation_reports", "source_through_sequence", "int8", "NO", None, 64, 0),
        ("evaluation_reports", "status", "varchar", "NO", 16, None, None),
        ("evaluation_reports", "overall_summary", "text", "YES", None, None, None),
        ("evaluation_reports", "priority_improvement", "text", "YES", None, None, None),
        ("evaluation_reports", "created_at", "timestamptz", "NO", None, None, None),
        ("evaluation_reports", "started_at", "timestamptz", "YES", None, None, None),
        ("evaluation_reports", "completed_at", "timestamptz", "YES", None, None, None),
        ("evaluation_reports", "failed_at", "timestamptz", "YES", None, None, None),
        ("evidence_items", "id", "uuid", "NO", None, None, None),
        ("evidence_items", "session_id", "uuid", "NO", None, None, None),
        ("evidence_items", "report_id", "uuid", "NO", None, None, None),
        ("evidence_items", "kind", "varchar", "NO", 16, None, None),
        ("evidence_items", "source_participant_id", "uuid", "NO", None, None, None),
        ("evidence_items", "source_utterance_id", "uuid", "NO", None, None, None),
        ("evidence_items", "source_event_sequence", "int8", "NO", None, 64, 0),
        ("evidence_items", "phase", "varchar", "NO", 32, None, None),
        ("evidence_items", "quote", "text", "NO", None, None, None),
        ("evidence_items", "interpretation", "text", "NO", None, None, None),
        ("evidence_items", "confidence", "numeric", "NO", None, 4, 3),
        ("evidence_items", "created_at", "timestamptz", "NO", None, None, None),
    ]
    assert constraints == {
        "ck_evaluation_reports_completed_after_started": ("c", False, False),
        "ck_evaluation_reports_derivation_version_non_empty": ("c", False, False),
        "ck_evaluation_reports_failed_after_creation": ("c", False, False),
        "ck_evaluation_reports_report_schema_version_positive": ("c", False, False),
        "ck_evaluation_reports_source_through_sequence_non_negative": (
            "c",
            False,
            False,
        ),
        "ck_evaluation_reports_started_after_creation": ("c", False, False),
        "ck_evaluation_reports_status_allowed": ("c", False, False),
        "ck_evaluation_reports_status_timing_consistent": ("c", False, False),
        "ck_evidence_items_confidence_range": ("c", False, False),
        "ck_evidence_items_interpretation_non_empty": ("c", False, False),
        "ck_evidence_items_kind_allowed": ("c", False, False),
        "ck_evidence_items_phase_allowed": ("c", False, False),
        "ck_evidence_items_quote_non_empty": ("c", False, False),
        "ck_evidence_items_source_event_sequence_positive": ("c", False, False),
        "fk_evaluation_reports_session_id_simulation_sessions": ("f", False, False),
        "fk_evidence_items_session_event": ("f", True, True),
        "fk_evidence_items_session_id_simulation_sessions": ("f", False, False),
        "fk_evidence_items_session_participant": ("f", True, True),
        "fk_evidence_items_session_report": ("f", True, True),
        "pk_evaluation_reports": ("p", False, False),
        "pk_evidence_items": ("p", False, False),
        "uq_evaluation_reports_generation_identity": ("u", False, False),
        "uq_evaluation_reports_session_id": ("u", False, False),
    }
    assert indexes == {
        "ix_evaluation_reports_session_created",
        "ix_evidence_items_report_created",
        "pk_evaluation_reports",
        "pk_evidence_items",
        "uq_evaluation_reports_generation_identity",
        "uq_evaluation_reports_session_id",
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
