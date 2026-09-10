from typing import cast

from sqlalchemy import (
    CheckConstraint,
    ForeignKeyConstraint,
    Index,
    Table,
    UniqueConstraint,
)

from group_interview_arena_api.db.models import EvaluationReport, EvidenceItem


def test_evaluation_report_metadata_has_generation_identity_and_lifecycle() -> None:
    table = cast(Table, EvaluationReport.__table__)

    assert set(table.columns.keys()) == {
        "id",
        "session_id",
        "report_schema_version",
        "derivation_version",
        "source_through_sequence",
        "status",
        "overall_summary",
        "priority_improvement",
        "created_at",
        "started_at",
        "completed_at",
        "failed_at",
    }
    assert str(table.c.report_schema_version.type) == "SMALLINT"
    assert str(table.c.source_through_sequence.type) == "BIGINT"
    assert str(table.c.derivation_version.type) == "VARCHAR(128)"
    assert str(table.c.status.type) == "VARCHAR(16)"
    assert table.c.overall_summary.nullable
    assert table.c.priority_improvement.nullable

    unique_constraints = {
        constraint.name: tuple(column.name for column in constraint.columns)
        for constraint in table.constraints
        if isinstance(constraint, UniqueConstraint)
    }
    assert unique_constraints == {
        "uq_evaluation_reports_session_id": ("session_id", "id"),
        "uq_evaluation_reports_generation_identity": (
            "session_id",
            "report_schema_version",
            "derivation_version",
            "source_through_sequence",
        ),
    }
    check_names = {
        constraint.name
        for constraint in table.constraints
        if isinstance(constraint, CheckConstraint)
    }
    assert check_names == {
        "ck_evaluation_reports_report_schema_version_positive",
        "ck_evaluation_reports_derivation_version_non_empty",
        "ck_evaluation_reports_source_through_sequence_non_negative",
        "ck_evaluation_reports_status_allowed",
        "ck_evaluation_reports_status_timing_consistent",
        "ck_evaluation_reports_started_after_creation",
        "ck_evaluation_reports_completed_after_started",
        "ck_evaluation_reports_failed_after_creation",
    }
    assert _index_columns(table.indexes) == {
        "ix_evaluation_reports_session_created": (
            "session_id",
            "created_at",
            "id",
        )
    }


def test_evidence_item_metadata_enforces_same_session_provenance() -> None:
    table = cast(Table, EvidenceItem.__table__)

    assert set(table.columns.keys()) == {
        "id",
        "session_id",
        "report_id",
        "kind",
        "source_participant_id",
        "source_utterance_id",
        "source_event_sequence",
        "phase",
        "quote",
        "interpretation",
        "confidence",
        "created_at",
    }
    assert str(table.c.source_event_sequence.type) == "BIGINT"
    assert str(table.c.confidence.type) == "NUMERIC(4, 3)"

    foreign_keys = {
        constraint.name: (
            tuple(column.name for column in constraint.columns),
            tuple(element.target_fullname for element in constraint.elements),
        )
        for constraint in table.constraints
        if isinstance(constraint, ForeignKeyConstraint)
    }
    assert foreign_keys == {
        "fk_evidence_items_session_id_simulation_sessions": (
            ("session_id",),
            ("simulation_sessions.id",),
        ),
        "fk_evidence_items_session_report": (
            ("session_id", "report_id"),
            ("evaluation_reports.session_id", "evaluation_reports.id"),
        ),
        "fk_evidence_items_session_participant": (
            ("session_id", "source_participant_id"),
            ("session_participants.session_id", "session_participants.id"),
        ),
        "fk_evidence_items_session_event": (
            ("session_id", "source_event_sequence"),
            ("discussion_events.session_id", "discussion_events.sequence"),
        ),
    }
    check_names = {
        constraint.name
        for constraint in table.constraints
        if isinstance(constraint, CheckConstraint)
    }
    assert check_names == {
        "ck_evidence_items_kind_allowed",
        "ck_evidence_items_source_event_sequence_positive",
        "ck_evidence_items_phase_allowed",
        "ck_evidence_items_quote_non_empty",
        "ck_evidence_items_interpretation_non_empty",
        "ck_evidence_items_confidence_range",
    }
    assert _index_columns(table.indexes) == {
        "ix_evidence_items_report_created": ("report_id", "created_at", "id")
    }


def _index_columns(indexes: set[Index]) -> dict[str | None, tuple[str, ...]]:
    return {
        index.name: tuple(column.name for column in index.columns) for index in indexes
    }
