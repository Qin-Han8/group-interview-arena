"""establish question and persona foundation

Revision ID: f1a12b15c002
Revises: f1a11d15c001
Create Date: 2026-08-17 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "f1a12b15c002"
down_revision: str | Sequence[str] | None = "f1a11d15c001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "question_templates",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("retired_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "retired_at IS NULL OR retired_at >= created_at",
            name=op.f("ck_question_templates_retired_after_creation"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_question_templates")),
        sa.UniqueConstraint("code", name=op.f("uq_question_templates_code")),
    )
    op.create_table(
        "persona_templates",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("display_name", sa.String(length=200), nullable=False),
        sa.Column("speech_style_code", sa.String(length=64), nullable=False),
        sa.Column("initiative", sa.Numeric(precision=4, scale=3), nullable=False),
        sa.Column(
            "interrupt_tendency", sa.Numeric(precision=4, scale=3), nullable=False
        ),
        sa.Column("average_turn_seconds", sa.SmallInteger(), nullable=False),
        sa.Column("stance_stability", sa.Numeric(precision=4, scale=3), nullable=False),
        sa.Column(
            "persuasion_threshold", sa.Numeric(precision=4, scale=3), nullable=False
        ),
        sa.Column("novel_idea_rate", sa.Numeric(precision=4, scale=3), nullable=False),
        sa.Column("summary_tendency", sa.Numeric(precision=4, scale=3), nullable=False),
        sa.Column("time_awareness", sa.Numeric(precision=4, scale=3), nullable=False),
        sa.Column("detail_focus", sa.Numeric(precision=4, scale=3), nullable=False),
        sa.Column("cooperation", sa.Numeric(precision=4, scale=3), nullable=False),
        sa.Column(
            "support_user_bias", sa.Numeric(precision=4, scale=3), nullable=False
        ),
        sa.Column("error_rate", sa.Numeric(precision=4, scale=3), nullable=False),
        sa.Column("off_topic_rate", sa.Numeric(precision=4, scale=3), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("retired_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "average_turn_seconds BETWEEN 10 AND 90",
            name=op.f("ck_persona_templates_average_turn_seconds_range"),
        ),
        sa.CheckConstraint(
            "initiative BETWEEN 0 AND 1 AND interrupt_tendency BETWEEN 0 AND 1 "
            "AND stance_stability BETWEEN 0 AND 1 AND persuasion_threshold BETWEEN 0 AND 1 "
            "AND novel_idea_rate BETWEEN 0 AND 1 AND summary_tendency BETWEEN 0 AND 1 "
            "AND time_awareness BETWEEN 0 AND 1 AND detail_focus BETWEEN 0 AND 1 "
            "AND cooperation BETWEEN 0 AND 1 AND error_rate BETWEEN 0 AND 1 "
            "AND off_topic_rate BETWEEN 0 AND 1",
            name=op.f("ck_persona_templates_probability_ranges"),
        ),
        sa.CheckConstraint(
            "support_user_bias BETWEEN -1 AND 1",
            name=op.f("ck_persona_templates_support_user_bias_range"),
        ),
        sa.CheckConstraint(
            "retired_at IS NULL OR retired_at >= created_at",
            name=op.f("ck_persona_templates_retired_after_creation"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_persona_templates")),
        sa.UniqueConstraint("code", name=op.f("uq_persona_templates_code")),
    )
    op.create_table(
        "question_versions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("question_template_id", sa.Uuid(), nullable=False),
        sa.Column("version_number", sa.SmallInteger(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("question_type_code", sa.String(length=64), nullable=False),
        sa.Column("background_domain_code", sa.String(length=64), nullable=False),
        sa.Column("difficulty_code", sa.String(length=64), nullable=False),
        sa.Column("scenario", sa.Text(), nullable=False),
        sa.Column("objective", sa.Text(), nullable=False),
        sa.Column("estimated_minutes", sa.SmallInteger(), nullable=False),
        sa.Column(
            "hard_constraints", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column(
            "soft_constraints", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column(
            "stakeholders", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column("options", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "reference_dimensions",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "hidden_conflicts", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column(
            "acceptable_outcome_patterns",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "phase_prompts", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column(
            "safety_tags", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("retired_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "estimated_minutes BETWEEN 5 AND 180",
            name=op.f("ck_question_versions_estimated_minutes_range"),
        ),
        sa.CheckConstraint(
            "jsonb_typeof(acceptable_outcome_patterns) = 'array'",
            name=op.f("ck_question_versions_acceptable_outcome_patterns_array"),
        ),
        sa.CheckConstraint(
            "jsonb_typeof(hard_constraints) = 'array'",
            name=op.f("ck_question_versions_hard_constraints_array"),
        ),
        sa.CheckConstraint(
            "jsonb_typeof(hidden_conflicts) = 'array'",
            name=op.f("ck_question_versions_hidden_conflicts_array"),
        ),
        sa.CheckConstraint(
            "jsonb_typeof(options) = 'array'",
            name=op.f("ck_question_versions_options_array"),
        ),
        sa.CheckConstraint(
            "jsonb_typeof(phase_prompts) = 'object'",
            name=op.f("ck_question_versions_phase_prompts_object"),
        ),
        sa.CheckConstraint(
            "jsonb_typeof(reference_dimensions) = 'array'",
            name=op.f("ck_question_versions_reference_dimensions_array"),
        ),
        sa.CheckConstraint(
            "jsonb_typeof(safety_tags) = 'array'",
            name=op.f("ck_question_versions_safety_tags_array"),
        ),
        sa.CheckConstraint(
            "jsonb_typeof(soft_constraints) = 'array'",
            name=op.f("ck_question_versions_soft_constraints_array"),
        ),
        sa.CheckConstraint(
            "jsonb_typeof(stakeholders) = 'array'",
            name=op.f("ck_question_versions_stakeholders_array"),
        ),
        sa.CheckConstraint(
            "published_at >= created_at",
            name=op.f("ck_question_versions_published_after_creation"),
        ),
        sa.CheckConstraint(
            "retired_at IS NULL OR "
            "(published_at IS NOT NULL AND retired_at >= published_at)",
            name=op.f("ck_question_versions_retirement_lifecycle"),
        ),
        sa.CheckConstraint(
            "version_number > 0",
            name=op.f("ck_question_versions_version_number_positive"),
        ),
        sa.ForeignKeyConstraint(
            ["question_template_id"],
            ["question_templates.id"],
            name="fk_question_versions_template_id_question_templates",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_question_versions")),
        sa.UniqueConstraint(
            "question_template_id",
            "version_number",
            name="uq_question_versions_template_version",
        ),
    )
    op.create_table(
        "question_persona_assignments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("question_version_id", sa.Uuid(), nullable=False),
        sa.Column("slot", sa.SmallInteger(), nullable=False),
        sa.Column("persona_template_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "slot > 0", name=op.f("ck_question_persona_assignments_slot_positive")
        ),
        sa.ForeignKeyConstraint(
            ["persona_template_id"],
            ["persona_templates.id"],
            name="fk_qpa_persona_template_id_persona_templates",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["question_version_id"],
            ["question_versions.id"],
            name="fk_qpa_question_version_id_question_versions",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_question_persona_assignments")),
        sa.UniqueConstraint(
            "question_version_id",
            "persona_template_id",
            name="uq_question_persona_assignments_version_persona",
        ),
        sa.UniqueConstraint(
            "question_version_id",
            "slot",
            name="uq_question_persona_assignments_version_slot",
        ),
    )
    op.create_table(
        "persona_private_stances",
        sa.Column("assignment_id", sa.Uuid(), nullable=False),
        sa.Column("initial_position", sa.Text(), nullable=False),
        sa.Column(
            "priority_dimensions",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "concession_conditions",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("private_information", sa.Text(), nullable=True),
        sa.Column("red_lines", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("preferred_group_role", sa.String(length=200), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "jsonb_typeof(concession_conditions) = 'array'",
            name=op.f("ck_persona_private_stances_concession_conditions_array"),
        ),
        sa.CheckConstraint(
            "jsonb_typeof(priority_dimensions) = 'array'",
            name=op.f("ck_persona_private_stances_priority_dimensions_array"),
        ),
        sa.CheckConstraint(
            "jsonb_typeof(red_lines) = 'array'",
            name=op.f("ck_persona_private_stances_red_lines_array"),
        ),
        sa.ForeignKeyConstraint(
            ["assignment_id"],
            ["question_persona_assignments.id"],
            name="fk_private_stances_assignment_id_assignments",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "assignment_id", name=op.f("pk_persona_private_stances")
        ),
    )
    op.add_column(
        "simulation_sessions",
        sa.Column("question_version_id", sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        op.f("fk_simulation_sessions_question_version_id_question_versions"),
        "simulation_sessions",
        "question_versions",
        ["question_version_id"],
        ["id"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(
        op.f("fk_simulation_sessions_question_version_id_question_versions"),
        "simulation_sessions",
        type_="foreignkey",
    )
    op.drop_column("simulation_sessions", "question_version_id")
    op.drop_table("persona_private_stances")
    op.drop_table("question_persona_assignments")
    op.drop_table("question_versions")
    op.drop_table("persona_templates")
    op.drop_table("question_templates")
