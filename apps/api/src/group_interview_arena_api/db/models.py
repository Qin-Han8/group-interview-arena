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


class BetaInvitation(Base):
    __tablename__ = "beta_invitations"
    __table_args__ = (
        CheckConstraint(
            "octet_length(code_digest) = 32",
            name="code_digest_sha256",
        ),
        CheckConstraint(
            "expires_at > created_at",
            name="expires_after_creation",
        ),
        CheckConstraint(
            "(consumed_at IS NULL) = (consumed_by_user_id IS NULL)",
            name="consumption_pair_consistent",
        ),
        CheckConstraint(
            "NOT (consumed_at IS NOT NULL AND revoked_at IS NOT NULL)",
            name="single_terminal_state",
        ),
        CheckConstraint(
            "consumed_at IS NULL OR consumed_at >= created_at",
            name="consumed_after_creation",
        ),
        CheckConstraint(
            "revoked_at IS NULL OR revoked_at >= created_at",
            name="revoked_after_creation",
        ),
        CheckConstraint(
            "length(btrim(operator_label)) BETWEEN 1 AND 64",
            name="operator_label_non_empty",
        ),
        Index(None, "expires_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    code_digest: Mapped[bytes] = mapped_column(
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
    consumed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    consumed_by_user_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    operator_label: Mapped[str] = mapped_column(String(64), nullable=False)


class AuthRateLimitBucket(Base):
    __tablename__ = "auth_rate_limit_buckets"
    __table_args__ = (
        CheckConstraint(
            "scope IN ('REGISTER_GLOBAL', 'REGISTER_SOURCE', "
            "'REGISTER_INVITE', 'LOGIN_GLOBAL', 'LOGIN_SOURCE', "
            "'LOGIN_ACCOUNT_SHARD')",
            name="scope_allowed",
        ),
        CheckConstraint(
            "octet_length(key_digest) = 32",
            name="key_digest_hmac_sha256",
        ),
        CheckConstraint("attempt_count >= 0", name="attempt_count_non_negative"),
        CheckConstraint(
            "updated_at >= window_started_at",
            name="updated_after_window_start",
        ),
        CheckConstraint(
            "blocked_until IS NULL OR blocked_until >= window_started_at",
            name="blocked_after_window_start",
        ),
        Index(None, "updated_at"),
    )

    scope: Mapped[str] = mapped_column(String(32), primary_key=True)
    key_digest: Mapped[bytes] = mapped_column(LargeBinary(32), primary_key=True)
    window_started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    attempt_count: Mapped[int] = mapped_column(BigInteger, nullable=False)
    blocked_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
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
        ForeignKeyConstraint(
            ["id", "current_floor_grant_id"],
            ["floor_grants.session_id", "floor_grants.id"],
            name="fk_simulation_sessions_current_floor_grant",
            deferrable=True,
            initially="DEFERRED",
            use_alter=True,
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
    current_floor_grant_id: Mapped[UUID | None] = mapped_column(
        Uuid,
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


class SessionParticipant(Base):
    __tablename__ = "session_participants"
    __table_args__ = (
        UniqueConstraint("session_id", "id", name="uq_session_participants_session_id"),
        UniqueConstraint(
            "session_id", "seat_order", name="uq_session_participants_session_seat"
        ),
        UniqueConstraint(
            "session_id", "user_id", name="uq_session_participants_session_user"
        ),
        UniqueConstraint(
            "session_id",
            "question_persona_assignment_id",
            name="uq_session_participants_session_assignment",
        ),
        CheckConstraint("seat_order > 0", name="seat_order_positive"),
        CheckConstraint(
            "actor_kind IN ('AI', 'HUMAN', 'SYSTEM')", name="actor_kind_allowed"
        ),
        CheckConstraint(
            "participation_role IN ('CANDIDATE', 'MODERATOR')",
            name="participation_role_allowed",
        ),
        CheckConstraint(
            "availability IN ('AVAILABLE', 'UNAVAILABLE')",
            name="availability_allowed",
        ),
        CheckConstraint(
            "(actor_kind = 'AI' AND participation_role = 'CANDIDATE' "
            "AND user_id IS NULL AND question_persona_assignment_id IS NOT NULL) OR "
            "(actor_kind = 'HUMAN' AND user_id IS NOT NULL "
            "AND question_persona_assignment_id IS NULL) OR "
            "(actor_kind = 'SYSTEM' AND participation_role = 'MODERATOR' "
            "AND user_id IS NULL AND question_persona_assignment_id IS NULL)",
            name="actor_identity_consistent",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    session_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("simulation_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    actor_kind: Mapped[str] = mapped_column(String(16), nullable=False)
    participation_role: Mapped[str] = mapped_column(String(16), nullable=False)
    seat_order: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    availability: Mapped[str] = mapped_column(String(16), nullable=False)
    user_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("users.id", deferrable=True, initially="DEFERRED"),
        nullable=True,
    )
    question_persona_assignment_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("question_persona_assignments.id", ondelete="RESTRICT"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now, nullable=False
    )


class SpeakingOpportunity(Base):
    __tablename__ = "speaking_opportunities"
    __table_args__ = (
        Index(
            "ix_speaking_opportunities_session_phase_created",
            "session_id",
            "phase",
            "created_at",
            "id",
        ),
        UniqueConstraint(
            "session_id", "id", name="uq_speaking_opportunities_session_id"
        ),
        ForeignKeyConstraint(
            ["session_id", "participant_id"],
            ["session_participants.session_id", "session_participants.id"],
            deferrable=True,
            initially="DEFERRED",
        ),
        CheckConstraint(
            "opportunity_kind IN "
            "('PHASE_MANDATED', 'EXPLICIT_REQUEST', 'NOMINATION', 'FAIRNESS')",
            name="opportunity_kind_allowed",
        ),
        CheckConstraint(
            "phase IN ('OPENING_STATEMENTS', 'EXPLORATION', "
            "'CONFLICT_AND_EVALUATION', 'CONVERGENCE', 'FINAL_SUMMARY')",
            name="phase_allowed",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    session_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("simulation_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    participant_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    phase: Mapped[str] = mapped_column(String(32), nullable=False)
    opportunity_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now, nullable=False
    )


class FloorDecision(Base):
    __tablename__ = "floor_decisions"
    __table_args__ = (
        Index(
            "ix_floor_decisions_session_decided",
            "session_id",
            "decided_at",
            "id",
        ),
        UniqueConstraint("session_id", "id", name="uq_floor_decisions_session_id"),
        ForeignKeyConstraint(
            ["session_id", "selected_participant_id"],
            ["session_participants.session_id", "session_participants.id"],
            deferrable=True,
            initially="DEFERRED",
        ),
        ForeignKeyConstraint(
            ["session_id", "opportunity_id"],
            ["speaking_opportunities.session_id", "speaking_opportunities.id"],
            deferrable=True,
            initially="DEFERRED",
        ),
        CheckConstraint(
            "outcome_kind IN ('GRANT', 'REQUEST_INTERVENTION', 'NO_GRANT')",
            name="outcome_kind_allowed",
        ),
        CheckConstraint("expected_last_sequence >= 0", name="sequence_non_negative"),
        CheckConstraint(
            "length(policy_version) > 0",
            name="explanation_identifiers_non_empty",
        ),
        CheckConstraint(
            "phase IN ('OPENING_STATEMENTS', 'EXPLORATION', "
            "'CONFLICT_AND_EVALUATION', 'CONVERGENCE', 'FINAL_SUMMARY')",
            name="phase_allowed",
        ),
        CheckConstraint(
            "primary_reason_code IN ('PHASE_MANDATED_TURN', "
            "'EXPLICIT_OPPORTUNITY', 'FIRST_OPPORTUNITY', "
            "'FAIRNESS_RECOVERY', 'MONOPOLY_PREVENTION', "
            "'PHASE_SUMMARY_OPPORTUNITY', 'SILENCE_RECOVERY', "
            "'DEADLINE_RECOVERY', 'NO_ELIGIBLE_PARTICIPANT')",
            name="primary_reason_code_allowed",
        ),
        CheckConstraint(
            "jsonb_typeof(supporting_reason_codes) = 'array'",
            name="supporting_reason_codes_array",
        ),
        CheckConstraint(
            "supporting_reason_codes <@ "
            '\'["PHASE_MANDATED_TURN", "EXPLICIT_OPPORTUNITY", '
            '"FIRST_OPPORTUNITY", "FAIRNESS_RECOVERY", '
            '"MONOPOLY_PREVENTION", "PHASE_SUMMARY_OPPORTUNITY", '
            '"SILENCE_RECOVERY", "DEADLINE_RECOVERY", '
            '"NO_ELIGIBLE_PARTICIPANT"]\'::jsonb',
            name="supporting_reason_codes_allowed",
        ),
        CheckConstraint(
            "jsonb_typeof(decision_metadata) = 'object'",
            name="decision_metadata_object",
        ),
        CheckConstraint(
            "decision_metadata ?& ARRAY["
            "'current_phase_grant_count', 'first_opportunity_unmet', "
            "'previous_owner_was_selected', 'consecutive_grant_count', "
            "'tie_break_class'] AND "
            "decision_metadata - ARRAY["
            "'current_phase_grant_count', 'first_opportunity_unmet', "
            "'previous_owner_was_selected', 'consecutive_grant_count', "
            "'tie_break_class'] = '{}'::jsonb AND "
            "jsonb_typeof(decision_metadata->'current_phase_grant_count') "
            "= 'number' AND "
            "(decision_metadata->>'current_phase_grant_count') "
            "~ '^(0|[1-9][0-9]*)$' AND "
            "jsonb_typeof(decision_metadata->'first_opportunity_unmet') "
            "= 'boolean' AND "
            "jsonb_typeof(decision_metadata->'previous_owner_was_selected') "
            "= 'boolean' AND "
            "jsonb_typeof(decision_metadata->'consecutive_grant_count') "
            "= 'number' AND "
            "(decision_metadata->>'consecutive_grant_count') "
            "~ '^(0|[1-9][0-9]*)$' AND "
            "decision_metadata->>'tie_break_class' IN "
            "('NOT_APPLICABLE', 'SEAT_ORDER', 'PARTICIPANT_ID')",
            name="decision_metadata_safe_shape",
        ),
        CheckConstraint(
            "(outcome_kind = 'GRANT' AND selected_participant_id IS NOT NULL "
            "AND intervention_kind IS NULL) OR "
            "(outcome_kind = 'REQUEST_INTERVENTION' "
            "AND selected_participant_id IS NULL AND intervention_kind IS NOT NULL) OR "
            "(outcome_kind = 'NO_GRANT' AND selected_participant_id IS NULL "
            "AND intervention_kind IS NULL)",
            name="outcome_target_consistent",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    session_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("simulation_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    phase: Mapped[str] = mapped_column(String(32), nullable=False)
    expected_last_sequence: Mapped[int] = mapped_column(BigInteger, nullable=False)
    outcome_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    selected_participant_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)
    opportunity_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)
    intervention_kind: Mapped[str | None] = mapped_column(String(32), nullable=True)
    policy_version: Mapped[str] = mapped_column(String(64), nullable=False)
    primary_reason_code: Mapped[str] = mapped_column(String(64), nullable=False)
    supporting_reason_codes: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    decision_metadata: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    decided_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now, nullable=False
    )


class FloorGrant(Base):
    __tablename__ = "floor_grants"
    __table_args__ = (
        Index(
            "ix_floor_grants_session_granted",
            "session_id",
            "granted_at",
            "id",
        ),
        UniqueConstraint("session_id", "id", name="uq_floor_grants_session_id"),
        UniqueConstraint("decision_id", name="uq_floor_grants_decision"),
        UniqueConstraint("opportunity_id", name="uq_floor_grants_opportunity"),
        ForeignKeyConstraint(
            ["session_id", "participant_id"],
            ["session_participants.session_id", "session_participants.id"],
            deferrable=True,
            initially="DEFERRED",
        ),
        CheckConstraint(
            "phase IN ('OPENING_STATEMENTS', 'EXPLORATION', "
            "'CONFLICT_AND_EVALUATION', 'CONVERGENCE', 'FINAL_SUMMARY')",
            name="phase_allowed",
        ),
        ForeignKeyConstraint(
            ["session_id", "decision_id"],
            ["floor_decisions.session_id", "floor_decisions.id"],
            deferrable=True,
            initially="DEFERRED",
        ),
        ForeignKeyConstraint(
            ["session_id", "opportunity_id"],
            ["speaking_opportunities.session_id", "speaking_opportunities.id"],
            deferrable=True,
            initially="DEFERRED",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    session_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("simulation_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    participant_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    decision_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    opportunity_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)
    phase: Mapped[str] = mapped_column(String(32), nullable=False)
    granted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now, nullable=False
    )


class FloorRelease(Base):
    __tablename__ = "floor_releases"
    __table_args__ = (
        Index(
            "ix_floor_releases_session_released",
            "session_id",
            "released_at",
            "grant_id",
        ),
        Index(
            "ix_floor_releases_session_causation",
            "session_id",
            "causation_action_id",
            "grant_id",
        ),
        ForeignKeyConstraint(
            ["session_id", "grant_id"],
            ["floor_grants.session_id", "floor_grants.id"],
            deferrable=True,
            initially="DEFERRED",
        ),
        ForeignKeyConstraint(
            ["session_id", "causation_action_id"],
            ["session_actions.session_id", "session_actions.action_id"],
        ),
        CheckConstraint(
            "reason_code IN ('SPEAKER_FINISHED', 'INTERRUPTED', "
            "'PHASE_CHANGED', 'SESSION_TERMINATED')",
            name="reason_code_allowed",
        ),
    )

    grant_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    session_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("simulation_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    causation_action_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)
    reason_code: Mapped[str] = mapped_column(String(64), nullable=False)
    released_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now, nullable=False
    )


class PromptVersion(Base):
    __tablename__ = "prompt_versions"
    __table_args__ = (
        UniqueConstraint(
            "prompt_key", "version_number", name="uq_prompt_versions_key_version"
        ),
        CheckConstraint("length(prompt_key) > 0", name="prompt_key_non_empty"),
        CheckConstraint("version_number > 0", name="version_number_positive"),
        CheckConstraint("length(purpose_code) > 0", name="purpose_code_non_empty"),
        CheckConstraint("length(template_text) > 0", name="template_text_non_empty"),
        CheckConstraint(
            "octet_length(content_digest) = 32", name="content_digest_sha256"
        ),
        CheckConstraint(
            "published_at >= created_at", name="publication_after_creation"
        ),
        CheckConstraint(
            "retired_at IS NULL OR retired_at >= published_at",
            name="retirement_after_publication",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    prompt_key: Mapped[str] = mapped_column(String(64), nullable=False)
    version_number: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    purpose_code: Mapped[str] = mapped_column(String(64), nullable=False)
    template_text: Mapped[str] = mapped_column(Text, nullable=False)
    content_digest: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    published_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    retired_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class LlmGenerationRequest(Base):
    __tablename__ = "llm_generation_requests"
    __table_args__ = (
        UniqueConstraint(
            "session_id", "id", name="uq_llm_generation_requests_session_id"
        ),
        UniqueConstraint(
            "session_id",
            "id",
            "participant_id",
            "floor_grant_id",
            "status",
            name="uq_llm_generation_requests_utterance_context",
        ),
        ForeignKeyConstraint(
            ["session_id", "participant_id"],
            ["session_participants.session_id", "session_participants.id"],
            deferrable=True,
            initially="DEFERRED",
        ),
        ForeignKeyConstraint(
            ["session_id", "floor_grant_id"],
            ["floor_grants.session_id", "floor_grants.id"],
            deferrable=True,
            initially="DEFERRED",
        ),
        CheckConstraint(
            "status IN ('REQUESTED', 'RUNNING', 'COMPLETED', 'FAILED')",
            name="status_allowed",
        ),
        CheckConstraint(
            "length(provider_identifier) > 0 AND length(model_identifier) > 0",
            name="provider_model_identifiers_non_empty",
        ),
        CheckConstraint(
            "octet_length(request_digest) = 32", name="request_digest_sha256"
        ),
        CheckConstraint(
            "jsonb_typeof(request_metadata) = 'object' AND (("
            "request_metadata ?& ARRAY['schema_version', 'configuration_version'] AND "
            "request_metadata - ARRAY['schema_version', 'configuration_version'] = '{}'::jsonb AND "
            "jsonb_typeof(request_metadata->'schema_version') = 'number' AND "
            "request_metadata->>'schema_version' = '1' AND "
            "jsonb_typeof(request_metadata->'configuration_version') = 'string' AND "
            "length(request_metadata->>'configuration_version') > 0) OR ("
            "request_metadata ?& ARRAY['schema_version', 'configuration_version', "
            "'working_context_version', 'context_mode', 'memory_revision', "
            "'memory_source_through_sequence', 'context_source_through_sequence'] AND "
            "request_metadata - ARRAY['schema_version', 'configuration_version', "
            "'working_context_version', 'context_mode', 'memory_revision', "
            "'memory_source_through_sequence', 'context_source_through_sequence'] = '{}'::jsonb AND "
            "jsonb_typeof(request_metadata->'schema_version') = 'number' AND "
            "request_metadata->>'schema_version' = '2' AND "
            "jsonb_typeof(request_metadata->'configuration_version') = 'string' AND "
            "length(request_metadata->>'configuration_version') > 0 AND "
            "jsonb_typeof(request_metadata->'working_context_version') = 'string' AND "
            "length(request_metadata->>'working_context_version') > 0 AND "
            "jsonb_typeof(request_metadata->'context_mode') = 'string' AND "
            "request_metadata->>'context_mode' IN ('MEMORY_WITH_RAW_TAIL', 'SAFE_RAW_FALLBACK') AND "
            "jsonb_typeof(request_metadata->'memory_revision') = 'number' AND "
            "request_metadata->>'memory_revision' ~ '^(0|[1-9][0-9]*)$' AND "
            "jsonb_typeof(request_metadata->'memory_source_through_sequence') = 'number' AND "
            "request_metadata->>'memory_source_through_sequence' ~ '^(0|[1-9][0-9]*)$' AND "
            "jsonb_typeof(request_metadata->'context_source_through_sequence') = 'number' AND "
            "request_metadata->>'context_source_through_sequence' ~ '^(0|[1-9][0-9]*)$' AND "
            "CASE WHEN "
            "jsonb_typeof(request_metadata->'memory_source_through_sequence') = 'number' AND "
            "request_metadata->>'memory_source_through_sequence' ~ '^(0|[1-9][0-9]*)$' AND "
            "jsonb_typeof(request_metadata->'context_source_through_sequence') = 'number' AND "
            "request_metadata->>'context_source_through_sequence' ~ '^(0|[1-9][0-9]*)$' "
            "THEN (request_metadata->>'context_source_through_sequence')::bigint >= "
            "(request_metadata->>'memory_source_through_sequence')::bigint ELSE FALSE END))",
            name="request_metadata_safe_shape",
        ),
        CheckConstraint(
            "(status = 'REQUESTED' AND started_at IS NULL "
            "AND completed_at IS NULL AND failed_at IS NULL "
            "AND failure_code IS NULL) OR "
            "(status = 'RUNNING' AND started_at IS NOT NULL "
            "AND completed_at IS NULL AND failed_at IS NULL "
            "AND failure_code IS NULL) OR "
            "(status = 'COMPLETED' AND started_at IS NOT NULL "
            "AND completed_at IS NOT NULL AND failed_at IS NULL "
            "AND failure_code IS NULL) OR "
            "(status = 'FAILED' AND completed_at IS NULL "
            "AND failed_at IS NOT NULL AND failure_code IS NOT NULL)",
            name="status_timing_consistent",
        ),
        CheckConstraint(
            "started_at IS NULL OR started_at >= requested_at",
            name="started_after_requested",
        ),
        CheckConstraint(
            "completed_at IS NULL OR completed_at >= started_at",
            name="completed_after_started",
        ),
        CheckConstraint(
            "failed_at IS NULL OR failed_at >= requested_at",
            name="failed_after_requested",
        ),
        CheckConstraint(
            "failure_code IS NULL OR failure_code IN "
            "('TIMEOUT', 'PROVIDER_UNAVAILABLE', 'RATE_LIMIT', "
            "'PARTIAL_GENERATION', 'INVALID_OUTPUT', 'INTERNAL_ERROR')",
            name="failure_code_allowed",
        ),
        Index(
            "ix_llm_generation_requests_session_requested",
            "session_id",
            "requested_at",
            "id",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    session_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("simulation_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    participant_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    floor_grant_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    prompt_version_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("prompt_versions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    provider_identifier: Mapped[str] = mapped_column(String(128), nullable=False)
    model_identifier: Mapped[str] = mapped_column(String(128), nullable=False)
    request_metadata: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    request_digest: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    failed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    failure_code: Mapped[str | None] = mapped_column(String(32), nullable=True)


class AiUtterance(Base):
    __tablename__ = "ai_utterances"
    __table_args__ = (
        UniqueConstraint(
            "generation_request_id", name="uq_ai_utterances_generation_request"
        ),
        UniqueConstraint(
            "session_id", "floor_grant_id", name="uq_ai_utterances_floor_grant"
        ),
        ForeignKeyConstraint(
            ["session_id", "participant_id"],
            ["session_participants.session_id", "session_participants.id"],
            deferrable=True,
            initially="DEFERRED",
        ),
        ForeignKeyConstraint(
            ["session_id", "floor_grant_id"],
            ["floor_grants.session_id", "floor_grants.id"],
            deferrable=True,
            initially="DEFERRED",
        ),
        ForeignKeyConstraint(
            [
                "session_id",
                "generation_request_id",
                "participant_id",
                "floor_grant_id",
                "generation_request_status",
            ],
            [
                "llm_generation_requests.session_id",
                "llm_generation_requests.id",
                "llm_generation_requests.participant_id",
                "llm_generation_requests.floor_grant_id",
                "llm_generation_requests.status",
            ],
            deferrable=True,
            initially="DEFERRED",
        ),
        CheckConstraint(
            "generation_request_status = 'COMPLETED'",
            name="successful_generation_required",
        ),
        CheckConstraint("length(content) > 0", name="content_non_empty"),
        CheckConstraint(
            "octet_length(content_digest) = 32", name="content_digest_sha256"
        ),
        Index(
            "ix_ai_utterances_session_persisted",
            "session_id",
            "persisted_at",
            "id",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    session_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("simulation_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    participant_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    floor_grant_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    generation_request_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    generation_request_status: Mapped[str] = mapped_column(String(16), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_digest: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    persisted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


class FloorIntervention(Base):
    __tablename__ = "floor_interventions"
    __table_args__ = (
        Index(
            "ix_floor_interventions_session_requested",
            "session_id",
            "requested_at",
            "id",
        ),
        UniqueConstraint("decision_id", name="uq_floor_interventions_decision"),
        ForeignKeyConstraint(
            ["session_id", "decision_id"],
            ["floor_decisions.session_id", "floor_decisions.id"],
            deferrable=True,
            initially="DEFERRED",
        ),
        CheckConstraint(
            "intervention_kind IN ('SILENCE', 'DEADLINE', 'NO_ELIGIBLE_PARTICIPANT')",
            name="kind_allowed",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    session_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("simulation_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    decision_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    intervention_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    requested_at: Mapped[datetime] = mapped_column(
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


class EvaluationReport(Base):
    __tablename__ = "evaluation_reports"
    __table_args__ = (
        UniqueConstraint("session_id", "id", name="uq_evaluation_reports_session_id"),
        UniqueConstraint(
            "session_id",
            "report_schema_version",
            "derivation_version",
            "source_through_sequence",
            name="uq_evaluation_reports_generation_identity",
        ),
        CheckConstraint(
            "report_schema_version > 0",
            name="report_schema_version_positive",
        ),
        CheckConstraint(
            "length(btrim(derivation_version)) > 0",
            name="derivation_version_non_empty",
        ),
        CheckConstraint(
            "source_through_sequence >= 0",
            name="source_through_sequence_non_negative",
        ),
        CheckConstraint(
            "status IN ('REQUESTED', 'RUNNING', 'COMPLETED', 'FAILED')",
            name="status_allowed",
        ),
        CheckConstraint(
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
            name="status_timing_consistent",
        ),
        CheckConstraint(
            "started_at IS NULL OR started_at >= created_at",
            name="started_after_creation",
        ),
        CheckConstraint(
            "completed_at IS NULL OR completed_at >= started_at",
            name="completed_after_started",
        ),
        CheckConstraint(
            "failed_at IS NULL OR failed_at >= created_at",
            name="failed_after_creation",
        ),
        Index(
            "ix_evaluation_reports_session_created",
            "session_id",
            "created_at",
            "id",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    session_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("simulation_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    report_schema_version: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
    )
    derivation_version: Mapped[str] = mapped_column(String(128), nullable=False)
    source_through_sequence: Mapped[int] = mapped_column(BigInteger, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    overall_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    priority_improvement: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utc_now,
        nullable=False,
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    failed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class EvidenceItem(Base):
    __tablename__ = "evidence_items"
    __table_args__ = (
        ForeignKeyConstraint(
            ["session_id", "report_id"],
            ["evaluation_reports.session_id", "evaluation_reports.id"],
            name="fk_evidence_items_session_report",
            ondelete="CASCADE",
            deferrable=True,
            initially="DEFERRED",
        ),
        ForeignKeyConstraint(
            ["session_id", "source_participant_id"],
            ["session_participants.session_id", "session_participants.id"],
            name="fk_evidence_items_session_participant",
            deferrable=True,
            initially="DEFERRED",
        ),
        ForeignKeyConstraint(
            ["session_id", "source_event_sequence"],
            ["discussion_events.session_id", "discussion_events.sequence"],
            name="fk_evidence_items_session_event",
            deferrable=True,
            initially="DEFERRED",
        ),
        CheckConstraint(
            "kind IN ('STRENGTH', 'IMPROVEMENT')",
            name="kind_allowed",
        ),
        CheckConstraint(
            "source_event_sequence > 0",
            name="source_event_sequence_positive",
        ),
        CheckConstraint(
            "phase IN ('OPENING_STATEMENTS', 'EXPLORATION', "
            "'CONFLICT_AND_EVALUATION', 'CONVERGENCE', 'FINAL_SUMMARY')",
            name="phase_allowed",
        ),
        CheckConstraint("length(btrim(quote)) > 0", name="quote_non_empty"),
        CheckConstraint(
            "length(btrim(interpretation)) > 0",
            name="interpretation_non_empty",
        ),
        CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="confidence_range",
        ),
        Index(
            "ix_evidence_items_report_created",
            "report_id",
            "created_at",
            "id",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    session_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("simulation_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    report_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    source_participant_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    source_utterance_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    source_event_sequence: Mapped[int] = mapped_column(BigInteger, nullable=False)
    phase: Mapped[str] = mapped_column(String(32), nullable=False)
    quote: Mapped[str] = mapped_column(Text, nullable=False)
    interpretation: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[Decimal] = mapped_column(Numeric(4, 3), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utc_now,
        nullable=False,
    )


class DiscussionMemoryState(Base):
    __tablename__ = "discussion_memory_states"
    __table_args__ = (
        CheckConstraint("revision >= 0", name="revision_non_negative"),
        CheckConstraint(
            "source_through_sequence >= 0", name="source_through_sequence_non_negative"
        ),
        CheckConstraint("schema_version > 0", name="schema_version_positive"),
        CheckConstraint(
            "length(derivation_version) > 0 AND length(projection_version) > 0",
            name="version_identifiers_non_empty",
        ),
        CheckConstraint(
            "jsonb_typeof(structured_state) = 'object'",
            name="structured_state_object",
        ),
    )

    session_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("simulation_sessions.id", ondelete="CASCADE"),
        primary_key=True,
    )
    revision: Mapped[int] = mapped_column(BigInteger, nullable=False)
    source_through_sequence: Mapped[int] = mapped_column(BigInteger, nullable=False)
    schema_version: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    derivation_version: Mapped[str] = mapped_column(String(128), nullable=False)
    projection_version: Mapped[str] = mapped_column(String(128), nullable=False)
    structured_state: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


class DiscussionMemoryRevision(Base):
    __tablename__ = "discussion_memory_revisions"
    __table_args__ = (
        UniqueConstraint(
            "session_id",
            "revision",
            name="uq_discussion_memory_revisions_session_revision",
        ),
        CheckConstraint("revision > 0", name="revision_positive"),
        CheckConstraint("base_revision >= 0", name="base_revision_non_negative"),
        CheckConstraint("revision = base_revision + 1", name="revision_advances_once"),
        CheckConstraint(
            "source_from_sequence > 0 AND source_through_sequence >= source_from_sequence",
            name="source_range_valid",
        ),
        CheckConstraint("jsonb_typeof(patches) = 'array'", name="patches_array"),
        CheckConstraint("schema_version > 0", name="schema_version_positive"),
        CheckConstraint(
            "length(derivation_version) > 0 AND length(projection_version) > 0",
            name="version_identifiers_non_empty",
        ),
        CheckConstraint(
            "octet_length(derivation_input_digest) = 32",
            name="derivation_input_digest_sha256",
        ),
        CheckConstraint(
            "(prompt_version_id IS NULL AND provider_identifier IS NULL AND model_identifier IS NULL "
            "AND configuration_version IS NULL) OR "
            "(prompt_version_id IS NOT NULL AND provider_identifier IS NOT NULL AND model_identifier IS NOT NULL "
            "AND configuration_version IS NOT NULL AND length(provider_identifier) > 0 "
            "AND length(model_identifier) > 0 AND length(configuration_version) > 0)",
            name="semantic_provenance_group_complete",
        ),
        Index(
            "ix_discussion_memory_revisions_session_source",
            "session_id",
            "source_through_sequence",
            "revision",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    session_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("simulation_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    revision: Mapped[int] = mapped_column(BigInteger, nullable=False)
    base_revision: Mapped[int] = mapped_column(BigInteger, nullable=False)
    source_from_sequence: Mapped[int] = mapped_column(BigInteger, nullable=False)
    source_through_sequence: Mapped[int] = mapped_column(BigInteger, nullable=False)
    patches: Mapped[list[dict[str, object]]] = mapped_column(JSONB, nullable=False)
    schema_version: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    derivation_version: Mapped[str] = mapped_column(String(128), nullable=False)
    projection_version: Mapped[str] = mapped_column(String(128), nullable=False)
    derivation_input_digest: Mapped[bytes] = mapped_column(
        LargeBinary(32), nullable=False
    )
    prompt_version_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("prompt_versions.id", ondelete="RESTRICT"),
        nullable=True,
    )
    provider_identifier: Mapped[str | None] = mapped_column(String(128), nullable=True)
    model_identifier: Mapped[str | None] = mapped_column(String(128), nullable=True)
    configuration_version: Mapped[str | None] = mapped_column(
        String(128), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
