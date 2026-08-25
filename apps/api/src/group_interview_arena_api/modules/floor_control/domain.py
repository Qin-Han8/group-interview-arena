from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

from group_interview_arena_api.modules.discussion_sessions.domain import (
    PendingEvent,
    SessionStatus,
)


class ParticipantActorKind(StrEnum):
    AI = "AI"
    HUMAN = "HUMAN"
    SYSTEM = "SYSTEM"


class ParticipationRole(StrEnum):
    CANDIDATE = "CANDIDATE"
    MODERATOR = "MODERATOR"


class ParticipantAvailability(StrEnum):
    AVAILABLE = "AVAILABLE"
    UNAVAILABLE = "UNAVAILABLE"


class SpeakingOpportunityKind(StrEnum):
    PHASE_MANDATED = "PHASE_MANDATED"
    EXPLICIT_REQUEST = "EXPLICIT_REQUEST"
    NOMINATION = "NOMINATION"
    FAIRNESS = "FAIRNESS"


class FloorDecisionOutcome(StrEnum):
    GRANT = "GRANT"
    REQUEST_INTERVENTION = "REQUEST_INTERVENTION"
    NO_GRANT = "NO_GRANT"


class FloorPolicyReason(StrEnum):
    PHASE_MANDATED_TURN = "PHASE_MANDATED_TURN"
    EXPLICIT_OPPORTUNITY = "EXPLICIT_OPPORTUNITY"
    FIRST_OPPORTUNITY = "FIRST_OPPORTUNITY"
    FAIRNESS_RECOVERY = "FAIRNESS_RECOVERY"
    MONOPOLY_PREVENTION = "MONOPOLY_PREVENTION"
    PHASE_SUMMARY_OPPORTUNITY = "PHASE_SUMMARY_OPPORTUNITY"
    SILENCE_RECOVERY = "SILENCE_RECOVERY"
    DEADLINE_RECOVERY = "DEADLINE_RECOVERY"
    NO_ELIGIBLE_PARTICIPANT = "NO_ELIGIBLE_PARTICIPANT"


class FloorInterventionKind(StrEnum):
    SILENCE = "SILENCE"
    DEADLINE = "DEADLINE"
    NO_ELIGIBLE_PARTICIPANT = "NO_ELIGIBLE_PARTICIPANT"


class FloorReleaseReason(StrEnum):
    SPEAKER_FINISHED = "SPEAKER_FINISHED"
    INTERRUPTED = "INTERRUPTED"
    PHASE_CHANGED = "PHASE_CHANGED"
    SESSION_TERMINATED = "SESSION_TERMINATED"


FLOOR_ENABLED_PHASES = frozenset(
    {
        SessionStatus.OPENING_STATEMENTS,
        SessionStatus.EXPLORATION,
        SessionStatus.CONFLICT_AND_EVALUATION,
        SessionStatus.CONVERGENCE,
        SessionStatus.FINAL_SUMMARY,
    }
)


class InvalidFloorStateError(Exception):
    pass


class StaleFloorDecisionError(Exception):
    pass


class IneligibleParticipantError(Exception):
    pass


@dataclass(frozen=True)
class SafeDecisionMetadata:
    current_phase_grant_count: int
    first_opportunity_unmet: bool
    previous_owner_was_selected: bool
    consecutive_grant_count: int
    tie_break_class: str

    def __post_init__(self) -> None:
        if (
            type(self.current_phase_grant_count) is not int
            or self.current_phase_grant_count < 0
            or type(self.consecutive_grant_count) is not int
            or self.consecutive_grant_count < 0
        ):
            raise ValueError("Decision counters must be non-negative integers.")
        if self.tie_break_class not in {
            "NOT_APPLICABLE",
            "SEAT_ORDER",
            "PARTICIPANT_ID",
        }:
            raise ValueError("Decision tie-break class is unsupported.")

    def to_json(self) -> dict[str, object]:
        return {
            "current_phase_grant_count": self.current_phase_grant_count,
            "first_opportunity_unmet": self.first_opportunity_unmet,
            "previous_owner_was_selected": self.previous_owner_was_selected,
            "consecutive_grant_count": self.consecutive_grant_count,
            "tie_break_class": self.tie_break_class,
        }


@dataclass(frozen=True)
class FloorDecisionRecord:
    decision_id: UUID
    phase: SessionStatus
    expected_last_sequence: int
    outcome: FloorDecisionOutcome
    selected_participant_id: UUID | None
    opportunity_id: UUID | None
    intervention_kind: FloorInterventionKind | None
    policy_version: str
    primary_reason: FloorPolicyReason
    supporting_reasons: tuple[FloorPolicyReason, ...]
    metadata: SafeDecisionMetadata

    def __post_init__(self) -> None:
        if self.phase not in FLOOR_ENABLED_PHASES:
            raise ValueError("Floor decisions require a floor-enabled phase.")
        if (
            type(self.expected_last_sequence) is not int
            or self.expected_last_sequence < 0
        ):
            raise ValueError("Expected sequence must be a non-negative integer.")
        if not self.policy_version or len(self.policy_version) > 64:
            raise ValueError("Policy version must be between 1 and 64 characters.")
        if len(set(self.supporting_reasons)) != len(self.supporting_reasons):
            raise ValueError("Supporting policy reasons must be unique.")
        if self.primary_reason in self.supporting_reasons:
            raise ValueError("Primary policy reason must not be repeated.")
        if self.outcome is FloorDecisionOutcome.GRANT:
            if (
                self.selected_participant_id is None
                or self.intervention_kind is not None
            ):
                raise ValueError(
                    "Grant decisions require exactly one participant target."
                )
        elif self.outcome is FloorDecisionOutcome.REQUEST_INTERVENTION:
            if (
                self.selected_participant_id is not None
                or self.intervention_kind is None
            ):
                raise ValueError(
                    "Intervention decisions require an intervention kind only."
                )
        elif (
            self.selected_participant_id is not None
            or self.intervention_kind is not None
        ):
            raise ValueError("No-grant decisions cannot carry a target.")


@dataclass(frozen=True)
class GrantFloorCommand:
    session_id: UUID
    action_id: UUID
    grant_id: UUID
    decision: FloorDecisionRecord
    schema_version: int = 1
    command_type: str = "floor.grant"


@dataclass(frozen=True)
class ReleaseFloorCommand:
    session_id: UUID
    action_id: UUID
    grant_id: UUID
    expected_phase: SessionStatus
    expected_last_sequence: int
    reason: FloorReleaseReason
    schema_version: int = 1
    command_type: str = "floor.release"


@dataclass(frozen=True)
class RequestFloorInterventionCommand:
    session_id: UUID
    action_id: UUID
    intervention_id: UUID
    decision: FloorDecisionRecord
    schema_version: int = 1
    command_type: str = "floor.intervention_requested"


type FloorCommand = (
    GrantFloorCommand | ReleaseFloorCommand | RequestFloorInterventionCommand
)


def require_command_version(command: FloorCommand) -> None:
    if type(command.schema_version) is not int:
        raise ValueError("Floor command version must be an integer.")
    if command.schema_version != 1:
        raise ValueError("Unsupported floor command version.")


def require_floor_phase(status: SessionStatus) -> None:
    if status not in FLOOR_ENABLED_PHASES:
        raise InvalidFloorStateError("Session is not in a floor-enabled phase.")


def require_fresh_sequence(*, actual: int, expected: int) -> None:
    if (
        type(actual) is not int
        or type(expected) is not int
        or actual < 0
        or expected < 0
    ):
        raise ValueError("Floor sequence values must be non-negative integers.")
    if actual != expected:
        raise StaleFloorDecisionError("Floor decision is stale.")


def require_ordinary_floor_eligibility(
    *,
    actor_kind: ParticipantActorKind,
    participation_role: ParticipationRole,
    availability: ParticipantAvailability,
) -> None:
    if (
        actor_kind not in {ParticipantActorKind.AI, ParticipantActorKind.HUMAN}
        or participation_role is not ParticipationRole.CANDIDATE
        or availability is not ParticipantAvailability.AVAILABLE
    ):
        raise IneligibleParticipantError(
            "Participant is not eligible for ordinary floor."
        )


def floor_granted_event(
    *,
    grant_id: UUID,
    decision: FloorDecisionRecord,
) -> PendingEvent:
    if decision.selected_participant_id is None:
        raise ValueError("Grant event requires a selected participant.")
    return PendingEvent(
        event_version=2,
        event_type="floor.granted",
        payload={
            "grant_id": str(grant_id),
            "decision_id": str(decision.decision_id),
            "participant_id": str(decision.selected_participant_id),
            "phase": decision.phase.value,
            "opportunity_id": (
                str(decision.opportunity_id)
                if decision.opportunity_id is not None
                else None
            ),
            "reason_code": decision.primary_reason.value,
            "policy_version": decision.policy_version,
        },
    )


def floor_released_event(
    *,
    grant_id: UUID,
    participant_id: UUID,
    phase: SessionStatus,
    reason: FloorReleaseReason,
) -> PendingEvent:
    return PendingEvent(
        event_version=2,
        event_type="floor.released",
        payload={
            "grant_id": str(grant_id),
            "participant_id": str(participant_id),
            "phase": phase.value,
            "reason_code": reason.value,
        },
    )


def floor_intervention_requested_event(
    *,
    intervention_id: UUID,
    decision: FloorDecisionRecord,
) -> PendingEvent:
    if decision.intervention_kind is None:
        raise ValueError("Intervention event requires an intervention kind.")
    return PendingEvent(
        event_version=2,
        event_type="floor.intervention_requested",
        payload={
            "intervention_id": str(intervention_id),
            "decision_id": str(decision.decision_id),
            "phase": decision.phase.value,
            "intervention_kind": decision.intervention_kind.value,
            "reason_code": decision.primary_reason.value,
            "policy_version": decision.policy_version,
        },
    )
