from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    LargeBinary,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from group_interview_arena_api.db.base import Base


def _utc_now() -> datetime:
    return datetime.now(UTC)


class User(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    username: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utc_now,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utc_now,
        onupdate=_utc_now,
        nullable=False,
    )


class AuthSession(Base):
    __tablename__ = "auth_sessions"
    __table_args__ = (Index(None, "expires_at"),)

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    token_hash: Mapped[bytes] = mapped_column(
        LargeBinary(32),
        unique=True,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utc_now,
        nullable=False,
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )


class SimulationSession(Base):
    __tablename__ = "simulation_sessions"
    __table_args__ = (
        CheckConstraint(
            "last_sequence >= 0",
            name="last_sequence_non_negative",
        ),
        CheckConstraint(
            "(phase_started_at IS NULL AND phase_deadline_at IS NULL) OR "
            "(phase_started_at IS NOT NULL AND phase_deadline_at IS NOT NULL "
            "AND phase_deadline_at > phase_started_at)",
            name="phase_timing_pair_valid",
        ),
        CheckConstraint(
            "(status IN ('PREPARATION', 'OPENING_STATEMENTS', 'EXPLORATION', "
            "'CONFLICT_AND_EVALUATION', 'CONVERGENCE', 'FINAL_SUMMARY') "
            "AND phase_started_at IS NOT NULL "
            "AND phase_deadline_at IS NOT NULL "
            "AND phase_duration_plan IS NOT NULL) OR "
            "(status NOT IN ('PREPARATION', 'OPENING_STATEMENTS', 'EXPLORATION', "
            "'CONFLICT_AND_EVALUATION', 'CONVERGENCE', 'FINAL_SUMMARY') "
            "AND phase_started_at IS NULL "
            "AND phase_deadline_at IS NULL)",
            name="phase_timing_status_consistent",
        ),
        CheckConstraint(
            "phase_duration_plan IS NULL OR "
            "(jsonb_typeof(phase_duration_plan) = 'object' "
            "AND phase_duration_plan ?& array["
            "'PREPARATION', 'OPENING_STATEMENTS', 'EXPLORATION', "
            "'CONFLICT_AND_EVALUATION', 'CONVERGENCE', 'FINAL_SUMMARY'])",
            name="phase_duration_plan_required_keys",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    owner_user_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    last_sequence: Mapped[int] = mapped_column(
        BigInteger,
        default=0,
        server_default=text("0"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utc_now,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utc_now,
        onupdate=_utc_now,
        nullable=False,
    )
    question_version_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("question_versions.id", ondelete="RESTRICT"),
        nullable=True,
    )
    phase_started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    phase_deadline_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    phase_duration_plan: Mapped[dict[str, int] | None] = mapped_column(
        JSONB,
        nullable=True,
    )


class QuestionTemplate(Base):
    __tablename__ = "question_templates"
    __table_args__ = (
        CheckConstraint(
            "retired_at IS NULL OR retired_at >= created_at",
            name="retired_after_creation",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now, nullable=False
    )
    retired_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class QuestionVersion(Base):
    __tablename__ = "question_versions"
    __table_args__ = (
        UniqueConstraint(
            "question_template_id",
            "version_number",
            name="uq_question_versions_template_version",
        ),
        CheckConstraint("version_number > 0", name="version_number_positive"),
        CheckConstraint(
            "estimated_minutes BETWEEN 5 AND 180", name="estimated_minutes_range"
        ),
        CheckConstraint("published_at >= created_at", name="published_after_creation"),
        CheckConstraint(
            "retired_at IS NULL OR "
            "(published_at IS NOT NULL AND retired_at >= published_at)",
            name="retirement_lifecycle",
        ),
        CheckConstraint(
            "jsonb_typeof(hard_constraints) = 'array'", name="hard_constraints_array"
        ),
        CheckConstraint(
            "jsonb_typeof(soft_constraints) = 'array'", name="soft_constraints_array"
        ),
        CheckConstraint(
            "jsonb_typeof(stakeholders) = 'array'", name="stakeholders_array"
        ),
        CheckConstraint("jsonb_typeof(options) = 'array'", name="options_array"),
        CheckConstraint(
            "jsonb_typeof(reference_dimensions) = 'array'",
            name="reference_dimensions_array",
        ),
        CheckConstraint(
            "jsonb_typeof(hidden_conflicts) = 'array'", name="hidden_conflicts_array"
        ),
        CheckConstraint(
            "jsonb_typeof(acceptable_outcome_patterns) = 'array'",
            name="acceptable_outcome_patterns_array",
        ),
        CheckConstraint(
            "jsonb_typeof(phase_prompts) = 'object'", name="phase_prompts_object"
        ),
        CheckConstraint(
            "jsonb_typeof(safety_tags) = 'array'", name="safety_tags_array"
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    question_template_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey(
            "question_templates.id",
            name="fk_question_versions_template_id_question_templates",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    version_number: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    question_type_code: Mapped[str] = mapped_column(String(64), nullable=False)
    background_domain_code: Mapped[str] = mapped_column(String(64), nullable=False)
    difficulty_code: Mapped[str] = mapped_column(String(64), nullable=False)
    scenario: Mapped[str] = mapped_column(Text, nullable=False)
    objective: Mapped[str] = mapped_column(Text, nullable=False)
    estimated_minutes: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    hard_constraints: Mapped[list[dict[str, object]]] = mapped_column(
        JSONB, nullable=False
    )
    soft_constraints: Mapped[list[dict[str, object]]] = mapped_column(
        JSONB, nullable=False
    )
    stakeholders: Mapped[list[dict[str, object]]] = mapped_column(JSONB, nullable=False)
    options: Mapped[list[dict[str, object]]] = mapped_column(JSONB, nullable=False)
    reference_dimensions: Mapped[list[dict[str, object]]] = mapped_column(
        JSONB, nullable=False
    )
    hidden_conflicts: Mapped[list[dict[str, object]]] = mapped_column(
        JSONB, nullable=False
    )
    acceptable_outcome_patterns: Mapped[list[dict[str, object]]] = mapped_column(
        JSONB, nullable=False
    )
    phase_prompts: Mapped[dict[str, str]] = mapped_column(JSONB, nullable=False)
    safety_tags: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now, nullable=False
    )
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    retired_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class PersonaTemplate(Base):
    __tablename__ = "persona_templates"
    __table_args__ = (
        CheckConstraint(
            "initiative BETWEEN 0 AND 1 AND interrupt_tendency BETWEEN 0 AND 1 "
            "AND stance_stability BETWEEN 0 AND 1 AND persuasion_threshold BETWEEN 0 AND 1 "
            "AND novel_idea_rate BETWEEN 0 AND 1 AND summary_tendency BETWEEN 0 AND 1 "
            "AND time_awareness BETWEEN 0 AND 1 AND detail_focus BETWEEN 0 AND 1 "
            "AND cooperation BETWEEN 0 AND 1 AND error_rate BETWEEN 0 AND 1 "
            "AND off_topic_rate BETWEEN 0 AND 1",
            name="probability_ranges",
        ),
        CheckConstraint(
            "support_user_bias BETWEEN -1 AND 1", name="support_user_bias_range"
        ),
        CheckConstraint(
            "average_turn_seconds BETWEEN 10 AND 90", name="average_turn_seconds_range"
        ),
        CheckConstraint(
            "retired_at IS NULL OR retired_at >= created_at",
            name="retired_after_creation",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    speech_style_code: Mapped[str] = mapped_column(String(64), nullable=False)
    initiative: Mapped[Decimal] = mapped_column(Numeric(4, 3), nullable=False)
    interrupt_tendency: Mapped[Decimal] = mapped_column(Numeric(4, 3), nullable=False)
    average_turn_seconds: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    stance_stability: Mapped[Decimal] = mapped_column(Numeric(4, 3), nullable=False)
    persuasion_threshold: Mapped[Decimal] = mapped_column(Numeric(4, 3), nullable=False)
    novel_idea_rate: Mapped[Decimal] = mapped_column(Numeric(4, 3), nullable=False)
    summary_tendency: Mapped[Decimal] = mapped_column(Numeric(4, 3), nullable=False)
    time_awareness: Mapped[Decimal] = mapped_column(Numeric(4, 3), nullable=False)
    detail_focus: Mapped[Decimal] = mapped_column(Numeric(4, 3), nullable=False)
    cooperation: Mapped[Decimal] = mapped_column(Numeric(4, 3), nullable=False)
    support_user_bias: Mapped[Decimal] = mapped_column(Numeric(4, 3), nullable=False)
    error_rate: Mapped[Decimal] = mapped_column(Numeric(4, 3), nullable=False)
    off_topic_rate: Mapped[Decimal] = mapped_column(Numeric(4, 3), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now, nullable=False
    )
    retired_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class QuestionPersonaAssignment(Base):
    __tablename__ = "question_persona_assignments"
    __table_args__ = (
        UniqueConstraint(
            "question_version_id",
            "slot",
            name="uq_question_persona_assignments_version_slot",
        ),
        UniqueConstraint(
            "question_version_id",
            "persona_template_id",
            name="uq_question_persona_assignments_version_persona",
        ),
        CheckConstraint("slot > 0", name="slot_positive"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    question_version_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey(
            "question_versions.id",
            name="fk_qpa_question_version_id_question_versions",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    slot: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    persona_template_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey(
            "persona_templates.id",
            name="fk_qpa_persona_template_id_persona_templates",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now, nullable=False
    )


class PersonaPrivateStance(Base):
    __tablename__ = "persona_private_stances"
    __table_args__ = (
        CheckConstraint(
            "jsonb_typeof(priority_dimensions) = 'array'",
            name="priority_dimensions_array",
        ),
        CheckConstraint(
            "jsonb_typeof(concession_conditions) = 'array'",
            name="concession_conditions_array",
        ),
        CheckConstraint("jsonb_typeof(red_lines) = 'array'", name="red_lines_array"),
    )

    assignment_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey(
            "question_persona_assignments.id",
            name="fk_private_stances_assignment_id_assignments",
            ondelete="CASCADE",
        ),
        primary_key=True,
    )
    initial_position: Mapped[str] = mapped_column(Text, nullable=False)
    priority_dimensions: Mapped[list[dict[str, object]]] = mapped_column(
        JSONB, nullable=False
    )
    concession_conditions: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    private_information: Mapped[str | None] = mapped_column(Text, nullable=True)
    red_lines: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    preferred_group_role: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now, nullable=False
    )


class SessionAction(Base):
    __tablename__ = "session_actions"
    __table_args__ = (
        CheckConstraint(
            "command_version > 0",
            name="command_version_positive",
        ),
        CheckConstraint(
            "octet_length(payload_digest) = 32",
            name="payload_digest_sha256",
        ),
    )

    session_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("simulation_sessions.id", ondelete="CASCADE"),
        primary_key=True,
    )
    action_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    command_version: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    command_type: Mapped[str] = mapped_column(String(64), nullable=False)
    payload_digest: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utc_now,
        nullable=False,
    )


class DiscussionEvent(Base):
    __tablename__ = "discussion_events"
    __table_args__ = (
        CheckConstraint("sequence > 0", name="sequence_positive"),
        CheckConstraint(
            "event_version > 0",
            name="event_version_positive",
        ),
        ForeignKeyConstraint(
            ["session_id", "causation_action_id"],
            ["session_actions.session_id", "session_actions.action_id"],
        ),
        Index(
            "ix_discussion_events_session_causation_sequence",
            "session_id",
            "causation_action_id",
            "sequence",
        ),
    )

    session_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("simulation_sessions.id", ondelete="CASCADE"),
        primary_key=True,
    )
    sequence: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    event_version: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    causation_action_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)
    payload: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utc_now,
        nullable=False,
    )
