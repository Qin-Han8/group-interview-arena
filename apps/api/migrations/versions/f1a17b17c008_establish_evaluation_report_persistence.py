"""establish evaluation report persistence

Revision ID: f1a17b17c008
Revises: f1a16e16c007
Create Date: 2026-09-10 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "f1a17b17c008"
down_revision: str | Sequence[str] | None = "f1a16e16c007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "evaluation_reports",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("report_schema_version", sa.SmallInteger(), nullable=False),
        sa.Column("derivation_version", sa.String(length=128), nullable=False),
        sa.Column("source_through_sequence", sa.BigInteger(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("overall_summary", sa.Text(), nullable=True),
        sa.Column("priority_improvement", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "report_schema_version > 0",
            name=op.f("ck_evaluation_reports_report_schema_version_positive"),
        ),
        sa.CheckConstraint(
            "length(btrim(derivation_version)) > 0",
            name=op.f("ck_evaluation_reports_derivation_version_non_empty"),
        ),
        sa.CheckConstraint(
            "source_through_sequence >= 0",
            name=op.f("ck_evaluation_reports_source_through_sequence_non_negative"),
        ),
        sa.CheckConstraint(
            "status IN ('REQUESTED', 'RUNNING', 'COMPLETED', 'FAILED')",
            name=op.f("ck_evaluation_reports_status_allowed"),
        ),
        sa.CheckConstraint(
            "(status = 'REQUESTED' AND started_at IS NULL "
            "AND completed_at IS NULL AND failed_at IS NULL) OR "
            "(status = 'RUNNING' AND started_at IS NOT NULL "
            "AND completed_at IS NULL AND failed_at IS NULL) OR "
            "(status = 'COMPLETED' AND started_at IS NOT NULL "
            "AND completed_at IS NOT NULL AND failed_at IS NULL "
            "AND overall_summary IS NOT NULL "
            "AND length(btrim(overall_summary)) > 0 "
            "AND priority_improvement IS NOT NULL "
            "AND length(btrim(priority_improvement)) > 0) OR "
            "(status = 'FAILED' AND completed_at IS NULL "
            "AND failed_at IS NOT NULL)",
            name=op.f("ck_evaluation_reports_status_timing_consistent"),
        ),
        sa.CheckConstraint(
            "started_at IS NULL OR started_at >= created_at",
            name=op.f("ck_evaluation_reports_started_after_creation"),
        ),
        sa.CheckConstraint(
            "completed_at IS NULL OR completed_at >= started_at",
            name=op.f("ck_evaluation_reports_completed_after_started"),
        ),
        sa.CheckConstraint(
            "failed_at IS NULL OR failed_at >= created_at",
            name=op.f("ck_evaluation_reports_failed_after_creation"),
        ),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["simulation_sessions.id"],
            name=op.f("fk_evaluation_reports_session_id_simulation_sessions"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_evaluation_reports")),
        sa.UniqueConstraint(
            "session_id",
            "id",
            name="uq_evaluation_reports_session_id",
        ),
        sa.UniqueConstraint(
            "session_id",
            "report_schema_version",
            "derivation_version",
            "source_through_sequence",
            name="uq_evaluation_reports_generation_identity",
        ),
    )
    op.create_index(
        "ix_evaluation_reports_session_created",
        "evaluation_reports",
        ["session_id", "created_at", "id"],
        unique=False,
    )
    op.create_table(
        "evidence_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("report_id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("source_participant_id", sa.Uuid(), nullable=False),
        sa.Column("source_utterance_id", sa.Uuid(), nullable=False),
        sa.Column("source_event_sequence", sa.BigInteger(), nullable=False),
        sa.Column("phase", sa.String(length=32), nullable=False),
        sa.Column("quote", sa.Text(), nullable=False),
        sa.Column("interpretation", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Numeric(precision=4, scale=3), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "kind IN ('STRENGTH', 'IMPROVEMENT')",
            name=op.f("ck_evidence_items_kind_allowed"),
        ),
        sa.CheckConstraint(
            "source_event_sequence > 0",
            name=op.f("ck_evidence_items_source_event_sequence_positive"),
        ),
        sa.CheckConstraint(
            "phase IN ('OPENING_STATEMENTS', 'EXPLORATION', "
            "'CONFLICT_AND_EVALUATION', 'CONVERGENCE', 'FINAL_SUMMARY')",
            name=op.f("ck_evidence_items_phase_allowed"),
        ),
        sa.CheckConstraint(
            "length(btrim(quote)) > 0",
            name=op.f("ck_evidence_items_quote_non_empty"),
        ),
        sa.CheckConstraint(
            "length(btrim(interpretation)) > 0",
            name=op.f("ck_evidence_items_interpretation_non_empty"),
        ),
        sa.CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name=op.f("ck_evidence_items_confidence_range"),
        ),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["simulation_sessions.id"],
            name=op.f("fk_evidence_items_session_id_simulation_sessions"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["session_id", "report_id"],
            ["evaluation_reports.session_id", "evaluation_reports.id"],
            name="fk_evidence_items_session_report",
            ondelete="CASCADE",
            deferrable=True,
            initially="DEFERRED",
        ),
        sa.ForeignKeyConstraint(
            ["session_id", "source_participant_id"],
            ["session_participants.session_id", "session_participants.id"],
            name="fk_evidence_items_session_participant",
            deferrable=True,
            initially="DEFERRED",
        ),
        sa.ForeignKeyConstraint(
            ["session_id", "source_event_sequence"],
            ["discussion_events.session_id", "discussion_events.sequence"],
            name="fk_evidence_items_session_event",
            deferrable=True,
            initially="DEFERRED",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_evidence_items")),
    )
    op.create_index(
        "ix_evidence_items_report_created",
        "evidence_items",
        ["report_id", "created_at", "id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_evidence_items_report_created",
        table_name="evidence_items",
    )
    op.drop_table("evidence_items")
    op.drop_index(
        "ix_evaluation_reports_session_created",
        table_name="evaluation_reports",
    )
    op.drop_table("evaluation_reports")
