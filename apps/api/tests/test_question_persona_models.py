from typing import cast

from sqlalchemy import (
    CheckConstraint,
    Index,
    Numeric,
    SmallInteger,
    String,
    Table,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB

from group_interview_arena_api.db import (
    PersonaPrivateStance,
    PersonaTemplate,
    QuestionPersonaAssignment,
    QuestionTemplate,
    QuestionVersion,
    SimulationSession,
)


def _constraint_names(table: Table) -> set[str]:
    return {str(constraint.name) for constraint in table.constraints}


def test_question_template_identity_is_separate_from_versions() -> None:
    template = cast(Table, QuestionTemplate.__table__)
    version = cast(Table, QuestionVersion.__table__)

    assert list(template.c.keys()) == ["id", "code", "created_at", "retired_at"]
    assert list(version.c.keys()) == [
        "id",
        "question_template_id",
        "version_number",
        "title",
        "question_type_code",
        "background_domain_code",
        "difficulty_code",
        "scenario",
        "objective",
        "estimated_minutes",
        "hard_constraints",
        "soft_constraints",
        "stakeholders",
        "options",
        "reference_dimensions",
        "hidden_conflicts",
        "acceptable_outcome_patterns",
        "phase_prompts",
        "safety_tags",
        "created_at",
        "published_at",
        "retired_at",
    ]
    assert "current_version_id" not in template.c
    assert isinstance(version.c.question_type_code.type, String)
    assert isinstance(version.c.difficulty_code.type, String)
    assert version.c.published_at.nullable is True
    assert all(
        isinstance(version.c[name].type, JSONB)
        for name in (
            "hard_constraints",
            "soft_constraints",
            "stakeholders",
            "options",
            "reference_dimensions",
            "hidden_conflicts",
            "acceptable_outcome_patterns",
            "phase_prompts",
            "safety_tags",
        )
    )
    assert "uq_question_versions_template_version" in _constraint_names(version)
    assert "ck_question_templates_retired_after_creation" in _constraint_names(template)
    assert "ck_question_versions_retirement_lifecycle" in _constraint_names(version)


def test_persona_template_uses_explicit_numeric_columns() -> None:
    table = cast(Table, PersonaTemplate.__table__)
    probability_columns = (
        "initiative",
        "interrupt_tendency",
        "stance_stability",
        "persuasion_threshold",
        "novel_idea_rate",
        "summary_tendency",
        "time_awareness",
        "detail_focus",
        "cooperation",
        "error_rate",
        "off_topic_rate",
    )

    assert "parameters" not in table.c
    for name in (*probability_columns, "support_user_bias"):
        numeric = table.c[name].type
        assert isinstance(numeric, Numeric)
        assert numeric.precision == 4
        assert numeric.scale == 3
    assert isinstance(table.c.average_turn_seconds.type, SmallInteger)
    assert "ck_persona_templates_probability_ranges" in _constraint_names(table)
    assert "ck_persona_templates_support_user_bias_range" in _constraint_names(table)
    assert "ck_persona_templates_average_turn_seconds_range" in _constraint_names(table)
    assert "ck_persona_templates_retired_after_creation" in _constraint_names(table)


def test_assignment_and_private_stance_are_question_version_specific() -> None:
    assignment = cast(Table, QuestionPersonaAssignment.__table__)
    stance = cast(Table, PersonaPrivateStance.__table__)

    assert list(assignment.c.keys()) == [
        "id",
        "question_version_id",
        "slot",
        "persona_template_id",
        "created_at",
    ]
    assert list(stance.c.keys()) == [
        "assignment_id",
        "initial_position",
        "priority_dimensions",
        "concession_conditions",
        "private_information",
        "red_lines",
        "preferred_group_role",
        "created_at",
    ]
    assert isinstance(assignment.c.question_version_id.type, Uuid)
    assert isinstance(stance.c.priority_dimensions.type, JSONB)
    assert "uq_question_persona_assignments_version_slot" in _constraint_names(
        assignment
    )
    assert "uq_question_persona_assignments_version_persona" in _constraint_names(
        assignment
    )
    assignment_fk = next(iter(stance.c.assignment_id.foreign_keys))
    assert assignment_fk.target_fullname == "question_persona_assignments.id"
    assert assignment_fk.ondelete == "CASCADE"


def test_session_version_reference_is_nullable_restrict_without_index() -> None:
    table = cast(Table, SimulationSession.__table__)
    column = table.c.question_version_id

    assert column.nullable is True
    foreign_key = next(iter(column.foreign_keys))
    assert foreign_key.target_fullname == "question_versions.id"
    assert foreign_key.ondelete == "RESTRICT"
    assert all(
        column.name not in [item.name for item in index.columns]
        for index in table.indexes
        if isinstance(index, Index)
    )
    assert sum(isinstance(item, CheckConstraint) for item in table.constraints) == 1
