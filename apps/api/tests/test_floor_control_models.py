from typing import cast

from sqlalchemy import ForeignKeyConstraint, Table

from group_interview_arena_api.db import (
    FloorDecision,
    FloorGrant,
    FloorIntervention,
    FloorRelease,
    SessionParticipant,
    SimulationSession,
    SpeakingOpportunity,
)


def _constraint_names(table: Table) -> set[str]:
    return {str(item.name) for item in table.constraints}


def _index_names(table: Table) -> set[str]:
    return {str(item.name) for item in table.indexes}


def test_session_current_floor_is_a_deferred_same_session_grant_reference() -> None:
    table = cast(Table, SimulationSession.__table__)
    constraint = next(
        item
        for item in table.constraints
        if isinstance(item, ForeignKeyConstraint)
        and item.name == "fk_simulation_sessions_current_floor_grant"
    )

    assert table.c.current_floor_grant_id.nullable is True
    assert [column.name for column in constraint.columns] == [
        "id",
        "current_floor_grant_id",
    ]
    assert [item.target_fullname for item in constraint.elements] == [
        "floor_grants.session_id",
        "floor_grants.id",
    ]
    assert constraint.deferrable is True
    assert constraint.initially == "DEFERRED"


def test_participant_model_supports_ai_human_and_system_without_private_fields() -> (
    None
):
    table = cast(Table, SessionParticipant.__table__)
    assert [column.name for column in table.columns] == [
        "id",
        "session_id",
        "actor_kind",
        "participation_role",
        "seat_order",
        "availability",
        "user_id",
        "question_persona_assignment_id",
        "created_at",
    ]
    assert {
        "ck_session_participants_actor_kind_allowed",
        "ck_session_participants_actor_identity_consistent",
        "ck_session_participants_availability_allowed",
        "ck_session_participants_participation_role_allowed",
        "ck_session_participants_seat_order_positive",
    } <= _constraint_names(table)
    forbidden = {"private_stance", "persona_parameters", "policy_weights", "score"}
    assert forbidden.isdisjoint(table.columns.keys())


def test_floor_history_uses_immutable_fact_rows_and_separate_active_pointer() -> None:
    grant = cast(Table, FloorGrant.__table__)
    release = cast(Table, FloorRelease.__table__)
    decision = cast(Table, FloorDecision.__table__)
    intervention = cast(Table, FloorIntervention.__table__)
    opportunity = cast(Table, SpeakingOpportunity.__table__)

    assert "updated_at" not in grant.c
    assert "released_at" not in grant.c
    assert [column.name for column in release.primary_key.columns] == ["grant_id"]
    assert "updated_at" not in release.c
    assert "updated_at" not in decision.c
    assert "updated_at" not in intervention.c
    assert "updated_at" not in opportunity.c
    assert "uq_floor_grants_decision" in _constraint_names(grant)
    assert "uq_floor_grants_opportunity" in _constraint_names(grant)
    assert "uq_floor_interventions_decision" in _constraint_names(intervention)
    assert _index_names(grant) == {"ix_floor_grants_session_granted"}
    assert _index_names(release) == {
        "ix_floor_releases_session_causation",
        "ix_floor_releases_session_released",
    }
    assert _index_names(decision) == {"ix_floor_decisions_session_decided"}
    assert _index_names(intervention) == {"ix_floor_interventions_session_requested"}
    assert _index_names(opportunity) == {
        "ix_speaking_opportunities_session_phase_created"
    }


def test_decision_audit_schema_has_closed_safe_metadata_boundary() -> None:
    table = cast(Table, FloorDecision.__table__)
    assert [column.name for column in table.columns] == [
        "id",
        "session_id",
        "phase",
        "expected_last_sequence",
        "outcome_kind",
        "selected_participant_id",
        "opportunity_id",
        "intervention_kind",
        "policy_version",
        "primary_reason_code",
        "supporting_reason_codes",
        "decision_metadata",
        "decided_at",
    ]
    forbidden = {
        "private_stance",
        "persona_calibration",
        "ranking_vector",
        "policy_weights",
        "score",
        "prompt",
    }
    assert forbidden.isdisjoint(table.columns.keys())
    assert "ck_floor_decisions_decision_metadata_safe_shape" in _constraint_names(table)
