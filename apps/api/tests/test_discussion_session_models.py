from typing import cast

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKeyConstraint,
    Index,
    LargeBinary,
    SmallInteger,
    String,
    Table,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.schema import CreateTable

from group_interview_arena_api.db import (
    Base,
    DiscussionEvent,
    SessionAction,
    SimulationSession,
)

EXPECTED_PRODUCT_TABLES = {
    "ai_utterances",
    "auth_sessions",
    "discussion_events",
    "floor_decisions",
    "floor_grants",
    "floor_interventions",
    "floor_releases",
    "llm_generation_requests",
    "persona_private_stances",
    "persona_templates",
    "prompt_versions",
    "question_persona_assignments",
    "question_templates",
    "question_versions",
    "session_actions",
    "session_participants",
    "simulation_sessions",
    "speaking_opportunities",
    "users",
}


def _constraint_names(table: Table) -> set[str]:
    return {str(constraint.name) for constraint in table.constraints}


def test_metadata_contains_exact_product_tables() -> None:
    assert set(Base.metadata.tables) == EXPECTED_PRODUCT_TABLES


def test_simulation_sessions_has_exact_forward_safe_shape() -> None:
    table = cast(Table, SimulationSession.__table__)

    assert list(table.columns) == [
        table.c.id,
        table.c.owner_user_id,
        table.c.status,
        table.c.last_sequence,
        table.c.created_at,
        table.c.updated_at,
        table.c.question_version_id,
        table.c.phase_started_at,
        table.c.phase_deadline_at,
        table.c.phase_duration_plan,
        table.c.current_floor_grant_id,
    ]
    assert isinstance(table.c.id.type, Uuid)
    assert table.c.id.primary_key is True
    assert isinstance(table.c.owner_user_id.type, Uuid)
    assert table.c.owner_user_id.nullable is False
    owner_fk = next(iter(table.c.owner_user_id.foreign_keys))
    assert owner_fk.target_fullname == "users.id"
    assert owner_fk.ondelete == "CASCADE"
    assert isinstance(table.c.status.type, String)
    assert table.c.status.type.length == 32
    assert table.c.status.nullable is False
    assert isinstance(table.c.last_sequence.type, BigInteger)
    assert table.c.last_sequence.nullable is False
    compiled_ddl = str(CreateTable(table).compile())
    assert "last_sequence BIGINT DEFAULT 0 NOT NULL" in compiled_ddl
    assert isinstance(table.c.created_at.type, DateTime)
    assert table.c.created_at.type.timezone is True
    assert isinstance(table.c.updated_at.type, DateTime)
    assert table.c.updated_at.type.timezone is True
    assert isinstance(table.c.phase_started_at.type, DateTime)
    assert table.c.phase_started_at.type.timezone is True
    assert table.c.phase_started_at.nullable is True
    assert isinstance(table.c.phase_deadline_at.type, DateTime)
    assert table.c.phase_deadline_at.type.timezone is True
    assert table.c.phase_deadline_at.nullable is True
    assert isinstance(table.c.phase_duration_plan.type, JSONB)
    assert table.c.phase_duration_plan.nullable is True
    assert isinstance(table.c.current_floor_grant_id.type, Uuid)
    assert table.c.current_floor_grant_id.nullable is True
    assert _constraint_names(table) == {
        "ck_simulation_sessions_phase_duration_plan_required_keys",
        "ck_simulation_sessions_phase_timing_pair_valid",
        "ck_simulation_sessions_phase_timing_status_consistent",
        "ck_simulation_sessions_last_sequence_non_negative",
        "fk_simulation_sessions_owner_user_id_users",
        "fk_simulation_sessions_question_version_id_question_versions",
        "fk_simulation_sessions_current_floor_grant",
        "pk_simulation_sessions",
    }
    assert sum(isinstance(item, CheckConstraint) for item in table.constraints) == 4
    assert table.indexes == set()


def test_session_actions_has_session_scoped_action_identity() -> None:
    table = cast(Table, SessionAction.__table__)

    assert list(table.columns) == [
        table.c.session_id,
        table.c.action_id,
        table.c.command_version,
        table.c.command_type,
        table.c.payload_digest,
        table.c.created_at,
    ]
    assert [column.name for column in table.primary_key.columns] == [
        "session_id",
        "action_id",
    ]
    assert isinstance(table.c.session_id.type, Uuid)
    assert isinstance(table.c.action_id.type, Uuid)
    assert table.c.session_id.nullable is False
    assert table.c.action_id.nullable is False
    session_fk = next(iter(table.c.session_id.foreign_keys))
    assert session_fk.target_fullname == "simulation_sessions.id"
    assert session_fk.ondelete == "CASCADE"
    assert isinstance(table.c.command_version.type, SmallInteger)
    assert isinstance(table.c.command_type.type, String)
    assert table.c.command_type.type.length == 64
    assert isinstance(table.c.payload_digest.type, LargeBinary)
    assert isinstance(table.c.created_at.type, DateTime)
    assert table.c.created_at.type.timezone is True
    assert _constraint_names(table) == {
        "ck_session_actions_command_version_positive",
        "ck_session_actions_payload_digest_sha256",
        "fk_session_actions_session_id_simulation_sessions",
        "pk_session_actions",
    }
    assert sum(isinstance(item, CheckConstraint) for item in table.constraints) == 2
    assert table.indexes == set()


def test_discussion_events_supports_many_events_per_action() -> None:
    table = cast(Table, DiscussionEvent.__table__)

    assert list(table.columns) == [
        table.c.session_id,
        table.c.sequence,
        table.c.event_version,
        table.c.event_type,
        table.c.causation_action_id,
        table.c.payload,
        table.c.occurred_at,
    ]
    assert [column.name for column in table.primary_key.columns] == [
        "session_id",
        "sequence",
    ]
    assert isinstance(table.c.sequence.type, BigInteger)
    assert isinstance(table.c.event_version.type, SmallInteger)
    assert isinstance(table.c.event_type.type, String)
    assert table.c.event_type.type.length == 64
    assert table.c.causation_action_id.nullable is True
    assert isinstance(table.c.payload.type, JSONB)
    assert isinstance(table.c.occurred_at.type, DateTime)
    assert table.c.occurred_at.type.timezone is True
    assert _constraint_names(table) == {
        "ck_discussion_events_event_version_positive",
        "ck_discussion_events_sequence_positive",
        "fk_discussion_events_session_id_session_actions",
        "fk_discussion_events_session_id_simulation_sessions",
        "pk_discussion_events",
    }
    causation_fk = next(
        constraint
        for constraint in table.constraints
        if isinstance(constraint, ForeignKeyConstraint)
        and constraint.name == "fk_discussion_events_session_id_session_actions"
    )
    assert [column.name for column in causation_fk.columns] == [
        "session_id",
        "causation_action_id",
    ]
    assert [element.target_fullname for element in causation_fk.elements] == [
        "session_actions.session_id",
        "session_actions.action_id",
    ]
    assert {index.name for index in table.indexes if isinstance(index, Index)} == {
        "ix_discussion_events_session_causation_sequence"
    }
    replay_index = next(iter(table.indexes))
    assert [column.name for column in replay_index.columns] == [
        "session_id",
        "causation_action_id",
        "sequence",
    ]
    assert replay_index.unique is False
