"""establish floor control foundation

Revision ID: f1a14b15c004
Revises: f1a13b15c003
Create Date: 2026-08-20 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "f1a14b15c004"
down_revision: str | Sequence[str] | None = "f1a13b15c003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "session_participants",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("actor_kind", sa.String(length=16), nullable=False),
        sa.Column("participation_role", sa.String(length=16), nullable=False),
        sa.Column("seat_order", sa.SmallInteger(), nullable=False),
        sa.Column("availability", sa.String(length=16), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("question_persona_assignment_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "actor_kind IN ('AI', 'HUMAN', 'SYSTEM')",
            name=op.f("ck_session_participants_actor_kind_allowed"),
        ),
        sa.CheckConstraint(
            "(actor_kind = 'AI' AND participation_role = 'CANDIDATE' "
            "AND user_id IS NULL AND question_persona_assignment_id IS NOT NULL) OR "
            "(actor_kind = 'HUMAN' AND user_id IS NOT NULL "
            "AND question_persona_assignment_id IS NULL) OR "
            "(actor_kind = 'SYSTEM' AND participation_role = 'MODERATOR' "
            "AND user_id IS NULL AND question_persona_assignment_id IS NULL)",
            name=op.f("ck_session_participants_actor_identity_consistent"),
        ),
        sa.CheckConstraint(
            "availability IN ('AVAILABLE', 'UNAVAILABLE')",
            name=op.f("ck_session_participants_availability_allowed"),
        ),
        sa.CheckConstraint(
            "participation_role IN ('CANDIDATE', 'MODERATOR')",
            name=op.f("ck_session_participants_participation_role_allowed"),
        ),
        sa.CheckConstraint(
            "seat_order > 0",
            name=op.f("ck_session_participants_seat_order_positive"),
        ),
        sa.ForeignKeyConstraint(
            ["question_persona_assignment_id"],
            ["question_persona_assignments.id"],
            name=op.f(
                "fk_session_participants_question_persona_assignment_id_question_persona_assignments"
            ),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["simulation_sessions.id"],
            name=op.f("fk_session_participants_session_id_simulation_sessions"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_session_participants_user_id_users"),
            deferrable=True,
            initially="DEFERRED",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_session_participants")),
        sa.UniqueConstraint(
            "session_id", "id", name="uq_session_participants_session_id"
        ),
        sa.UniqueConstraint(
            "session_id",
            "question_persona_assignment_id",
            name="uq_session_participants_session_assignment",
        ),
        sa.UniqueConstraint(
            "session_id",
            "seat_order",
            name="uq_session_participants_session_seat",
        ),
        sa.UniqueConstraint(
            "session_id", "user_id", name="uq_session_participants_session_user"
        ),
    )
    op.create_table(
        "speaking_opportunities",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("participant_id", sa.Uuid(), nullable=False),
        sa.Column("phase", sa.String(length=32), nullable=False),
        sa.Column("opportunity_kind", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "opportunity_kind IN "
            "('PHASE_MANDATED', 'EXPLICIT_REQUEST', 'NOMINATION', 'FAIRNESS')",
            name=op.f("ck_speaking_opportunities_opportunity_kind_allowed"),
        ),
        sa.CheckConstraint(
            "phase IN ('OPENING_STATEMENTS', 'EXPLORATION', "
            "'CONFLICT_AND_EVALUATION', 'CONVERGENCE', 'FINAL_SUMMARY')",
            name=op.f("ck_speaking_opportunities_phase_allowed"),
        ),
        sa.ForeignKeyConstraint(
            ["session_id", "participant_id"],
            ["session_participants.session_id", "session_participants.id"],
            name=op.f("fk_speaking_opportunities_session_id_session_participants"),
            deferrable=True,
            initially="DEFERRED",
        ),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["simulation_sessions.id"],
            name=op.f("fk_speaking_opportunities_session_id_simulation_sessions"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_speaking_opportunities")),
        sa.UniqueConstraint(
            "session_id", "id", name="uq_speaking_opportunities_session_id"
        ),
    )
    op.create_index(
        "ix_speaking_opportunities_session_phase_created",
        "speaking_opportunities",
        ["session_id", "phase", "created_at", "id"],
        unique=False,
    )
    op.create_table(
        "floor_decisions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("phase", sa.String(length=32), nullable=False),
        sa.Column("expected_last_sequence", sa.BigInteger(), nullable=False),
        sa.Column("outcome_kind", sa.String(length=32), nullable=False),
        sa.Column("selected_participant_id", sa.Uuid(), nullable=True),
        sa.Column("opportunity_id", sa.Uuid(), nullable=True),
        sa.Column("intervention_kind", sa.String(length=32), nullable=True),
        sa.Column("policy_version", sa.String(length=64), nullable=False),
        sa.Column("primary_reason_code", sa.String(length=64), nullable=False),
        sa.Column(
            "supporting_reason_codes",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "decision_metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "jsonb_typeof(decision_metadata) = 'object'",
            name=op.f("ck_floor_decisions_decision_metadata_object"),
        ),
        sa.CheckConstraint(
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
            name=op.f("ck_floor_decisions_decision_metadata_safe_shape"),
        ),
        sa.CheckConstraint(
            "length(policy_version) > 0",
            name=op.f("ck_floor_decisions_explanation_identifiers_non_empty"),
        ),
        sa.CheckConstraint(
            "phase IN ('OPENING_STATEMENTS', 'EXPLORATION', "
            "'CONFLICT_AND_EVALUATION', 'CONVERGENCE', 'FINAL_SUMMARY')",
            name=op.f("ck_floor_decisions_phase_allowed"),
        ),
        sa.CheckConstraint(
            "primary_reason_code IN ('PHASE_MANDATED_TURN', "
            "'EXPLICIT_OPPORTUNITY', 'FIRST_OPPORTUNITY', "
            "'FAIRNESS_RECOVERY', 'MONOPOLY_PREVENTION', "
            "'PHASE_SUMMARY_OPPORTUNITY', 'SILENCE_RECOVERY', "
            "'DEADLINE_RECOVERY', 'NO_ELIGIBLE_PARTICIPANT')",
            name=op.f("ck_floor_decisions_primary_reason_code_allowed"),
        ),
        sa.CheckConstraint(
            "expected_last_sequence >= 0",
            name=op.f("ck_floor_decisions_sequence_non_negative"),
        ),
        sa.CheckConstraint(
            "outcome_kind IN ('GRANT', 'REQUEST_INTERVENTION', 'NO_GRANT')",
            name=op.f("ck_floor_decisions_outcome_kind_allowed"),
        ),
        sa.CheckConstraint(
            "(outcome_kind = 'GRANT' AND selected_participant_id IS NOT NULL "
            "AND intervention_kind IS NULL) OR "
            "(outcome_kind = 'REQUEST_INTERVENTION' "
            "AND selected_participant_id IS NULL AND intervention_kind IS NOT NULL) OR "
            "(outcome_kind = 'NO_GRANT' AND selected_participant_id IS NULL "
            "AND intervention_kind IS NULL)",
            name=op.f("ck_floor_decisions_outcome_target_consistent"),
        ),
        sa.CheckConstraint(
            "jsonb_typeof(supporting_reason_codes) = 'array'",
            name=op.f("ck_floor_decisions_supporting_reason_codes_array"),
        ),
        sa.CheckConstraint(
            "supporting_reason_codes <@ "
            '\'["PHASE_MANDATED_TURN", "EXPLICIT_OPPORTUNITY", '
            '"FIRST_OPPORTUNITY", "FAIRNESS_RECOVERY", '
            '"MONOPOLY_PREVENTION", "PHASE_SUMMARY_OPPORTUNITY", '
            '"SILENCE_RECOVERY", "DEADLINE_RECOVERY", '
            '"NO_ELIGIBLE_PARTICIPANT"]\'::jsonb',
            name=op.f("ck_floor_decisions_supporting_reason_codes_allowed"),
        ),
        sa.ForeignKeyConstraint(
            ["session_id", "opportunity_id"],
            ["speaking_opportunities.session_id", "speaking_opportunities.id"],
            name=op.f("fk_floor_decisions_session_id_speaking_opportunities"),
            deferrable=True,
            initially="DEFERRED",
        ),
        sa.ForeignKeyConstraint(
            ["session_id", "selected_participant_id"],
            ["session_participants.session_id", "session_participants.id"],
            name=op.f("fk_floor_decisions_session_id_session_participants"),
            deferrable=True,
            initially="DEFERRED",
        ),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["simulation_sessions.id"],
            name=op.f("fk_floor_decisions_session_id_simulation_sessions"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_floor_decisions")),
        sa.UniqueConstraint("session_id", "id", name="uq_floor_decisions_session_id"),
    )
    op.create_index(
        "ix_floor_decisions_session_decided",
        "floor_decisions",
        ["session_id", "decided_at", "id"],
        unique=False,
    )
    op.create_table(
        "floor_grants",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("participant_id", sa.Uuid(), nullable=False),
        sa.Column("decision_id", sa.Uuid(), nullable=False),
        sa.Column("opportunity_id", sa.Uuid(), nullable=True),
        sa.Column("phase", sa.String(length=32), nullable=False),
        sa.Column("granted_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "phase IN ('OPENING_STATEMENTS', 'EXPLORATION', "
            "'CONFLICT_AND_EVALUATION', 'CONVERGENCE', 'FINAL_SUMMARY')",
            name=op.f("ck_floor_grants_phase_allowed"),
        ),
        sa.ForeignKeyConstraint(
            ["session_id", "decision_id"],
            ["floor_decisions.session_id", "floor_decisions.id"],
            name=op.f("fk_floor_grants_session_id_floor_decisions"),
            deferrable=True,
            initially="DEFERRED",
        ),
        sa.ForeignKeyConstraint(
            ["session_id", "opportunity_id"],
            ["speaking_opportunities.session_id", "speaking_opportunities.id"],
            name=op.f("fk_floor_grants_session_id_speaking_opportunities"),
            deferrable=True,
            initially="DEFERRED",
        ),
        sa.ForeignKeyConstraint(
            ["session_id", "participant_id"],
            ["session_participants.session_id", "session_participants.id"],
            name=op.f("fk_floor_grants_session_id_session_participants"),
            deferrable=True,
            initially="DEFERRED",
        ),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["simulation_sessions.id"],
            name=op.f("fk_floor_grants_session_id_simulation_sessions"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_floor_grants")),
        sa.UniqueConstraint("decision_id", name="uq_floor_grants_decision"),
        sa.UniqueConstraint("opportunity_id", name="uq_floor_grants_opportunity"),
        sa.UniqueConstraint("session_id", "id", name="uq_floor_grants_session_id"),
    )
    op.create_index(
        "ix_floor_grants_session_granted",
        "floor_grants",
        ["session_id", "granted_at", "id"],
        unique=False,
    )
    op.create_table(
        "floor_releases",
        sa.Column("grant_id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("causation_action_id", sa.Uuid(), nullable=True),
        sa.Column("reason_code", sa.String(length=64), nullable=False),
        sa.Column("released_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "reason_code IN ('SPEAKER_FINISHED', 'INTERRUPTED', "
            "'PHASE_CHANGED', 'SESSION_TERMINATED')",
            name=op.f("ck_floor_releases_reason_code_allowed"),
        ),
        sa.ForeignKeyConstraint(
            ["session_id", "causation_action_id"],
            ["session_actions.session_id", "session_actions.action_id"],
            name=op.f("fk_floor_releases_session_id_session_actions"),
        ),
        sa.ForeignKeyConstraint(
            ["session_id", "grant_id"],
            ["floor_grants.session_id", "floor_grants.id"],
            name=op.f("fk_floor_releases_session_id_floor_grants"),
            deferrable=True,
            initially="DEFERRED",
        ),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["simulation_sessions.id"],
            name=op.f("fk_floor_releases_session_id_simulation_sessions"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("grant_id", name=op.f("pk_floor_releases")),
    )
    op.create_index(
        "ix_floor_releases_session_causation",
        "floor_releases",
        ["session_id", "causation_action_id", "grant_id"],
        unique=False,
    )
    op.create_index(
        "ix_floor_releases_session_released",
        "floor_releases",
        ["session_id", "released_at", "grant_id"],
        unique=False,
    )
    op.create_table(
        "floor_interventions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("decision_id", sa.Uuid(), nullable=False),
        sa.Column("intervention_kind", sa.String(length=32), nullable=False),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "intervention_kind IN ('SILENCE', 'DEADLINE', 'NO_ELIGIBLE_PARTICIPANT')",
            name=op.f("ck_floor_interventions_kind_allowed"),
        ),
        sa.ForeignKeyConstraint(
            ["session_id", "decision_id"],
            ["floor_decisions.session_id", "floor_decisions.id"],
            name=op.f("fk_floor_interventions_session_id_floor_decisions"),
            deferrable=True,
            initially="DEFERRED",
        ),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["simulation_sessions.id"],
            name=op.f("fk_floor_interventions_session_id_simulation_sessions"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_floor_interventions")),
        sa.UniqueConstraint("decision_id", name="uq_floor_interventions_decision"),
    )
    op.create_index(
        "ix_floor_interventions_session_requested",
        "floor_interventions",
        ["session_id", "requested_at", "id"],
        unique=False,
    )
    op.add_column(
        "simulation_sessions",
        sa.Column("current_floor_grant_id", sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        "fk_simulation_sessions_current_floor_grant",
        "simulation_sessions",
        "floor_grants",
        ["id", "current_floor_grant_id"],
        ["session_id", "id"],
        deferrable=True,
        initially="DEFERRED",
    )
    op.execute(
        """
        INSERT INTO session_participants (
            id, session_id, actor_kind, participation_role, seat_order,
            availability, user_id, question_persona_assignment_id, created_at
        )
        SELECT
            gen_random_uuid(), id, 'HUMAN', 'CANDIDATE', 1,
            'AVAILABLE', owner_user_id, NULL, created_at
        FROM simulation_sessions
        WHERE question_version_id IS NOT NULL
        """
    )
    op.execute(
        """
        INSERT INTO session_participants (
            id, session_id, actor_kind, participation_role, seat_order,
            availability, user_id, question_persona_assignment_id, created_at
        )
        SELECT
            gen_random_uuid(), sessions.id, 'AI', 'CANDIDATE', assignments.slot + 1,
            'AVAILABLE', NULL, assignments.id, sessions.created_at
        FROM simulation_sessions AS sessions
        JOIN question_persona_assignments AS assignments
          ON assignments.question_version_id = sessions.question_version_id
        WHERE sessions.question_version_id IS NOT NULL
        """
    )
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT sessions.id
                FROM simulation_sessions AS sessions
                LEFT JOIN session_participants AS participants
                  ON participants.session_id = sessions.id
                WHERE sessions.question_version_id IS NOT NULL
                GROUP BY sessions.id
                HAVING count(participants.id) <> 4
                   OR count(*) FILTER (
                       WHERE participants.actor_kind = 'HUMAN'
                   ) <> 1
                   OR count(*) FILTER (
                       WHERE participants.actor_kind = 'AI'
                   ) <> 3
                   OR array_agg(
                       participants.seat_order ORDER BY participants.seat_order
                   ) <> ARRAY[1, 2, 3, 4]::smallint[]
            ) THEN
                RAISE EXCEPTION
                    'Cannot establish complete floor roster for bound sessions';
            END IF;
        END
        $$
        """
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(
        "fk_simulation_sessions_current_floor_grant",
        "simulation_sessions",
        type_="foreignkey",
    )
    op.drop_column("simulation_sessions", "current_floor_grant_id")
    op.drop_table("floor_interventions")
    op.drop_table("floor_releases")
    op.drop_table("floor_grants")
    op.drop_table("floor_decisions")
    op.drop_table("speaking_opportunities")
    op.drop_table("session_participants")
