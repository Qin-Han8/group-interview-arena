"""add session phase timing

Revision ID: f1a13b15c003
Revises: f1a12b15c002
Create Date: 2026-08-20 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "f1a13b15c003"
down_revision: str | Sequence[str] | None = "f1a12b15c002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "simulation_sessions",
        sa.Column("phase_started_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "simulation_sessions",
        sa.Column("phase_deadline_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "simulation_sessions",
        sa.Column(
            "phase_duration_plan",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )
    op.create_check_constraint(
        op.f("ck_simulation_sessions_phase_timing_pair_valid"),
        "simulation_sessions",
        "(phase_started_at IS NULL AND phase_deadline_at IS NULL) OR "
        "(phase_started_at IS NOT NULL AND phase_deadline_at IS NOT NULL "
        "AND phase_deadline_at > phase_started_at)",
    )
    op.create_check_constraint(
        op.f("ck_simulation_sessions_phase_timing_status_consistent"),
        "simulation_sessions",
        "(status IN ('PREPARATION', 'OPENING_STATEMENTS', 'EXPLORATION', "
        "'CONFLICT_AND_EVALUATION', 'CONVERGENCE', 'FINAL_SUMMARY') "
        "AND phase_started_at IS NOT NULL "
        "AND phase_deadline_at IS NOT NULL "
        "AND phase_duration_plan IS NOT NULL) OR "
        "(status NOT IN ('PREPARATION', 'OPENING_STATEMENTS', 'EXPLORATION', "
        "'CONFLICT_AND_EVALUATION', 'CONVERGENCE', 'FINAL_SUMMARY') "
        "AND phase_started_at IS NULL "
        "AND phase_deadline_at IS NULL)",
    )
    op.create_check_constraint(
        op.f("ck_simulation_sessions_phase_duration_plan_required_keys"),
        "simulation_sessions",
        "phase_duration_plan IS NULL OR "
        "(jsonb_typeof(phase_duration_plan) = 'object' "
        "AND phase_duration_plan ?& array["
        "'PREPARATION', 'OPENING_STATEMENTS', 'EXPLORATION', "
        "'CONFLICT_AND_EVALUATION', 'CONVERGENCE', 'FINAL_SUMMARY'])",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(
        op.f("ck_simulation_sessions_phase_duration_plan_required_keys"),
        "simulation_sessions",
        type_="check",
    )
    op.drop_constraint(
        op.f("ck_simulation_sessions_phase_timing_status_consistent"),
        "simulation_sessions",
        type_="check",
    )
    op.drop_constraint(
        op.f("ck_simulation_sessions_phase_timing_pair_valid"),
        "simulation_sessions",
        type_="check",
    )
    op.drop_column("simulation_sessions", "phase_duration_plan")
    op.drop_column("simulation_sessions", "phase_deadline_at")
    op.drop_column("simulation_sessions", "phase_started_at")
