import hashlib
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from group_interview_arena_api.modules.discussion_sessions.domain import (
    SessionStatus,
)
from group_interview_arena_api.modules.floor_control.domain import (
    FLOOR_ENABLED_PHASES,
    FloorDecisionOutcome,
    FloorDecisionRecord,
    FloorInterventionKind,
    FloorPolicyReason,
    ParticipantActorKind,
    ParticipantAvailability,
    ParticipationRole,
    SafeDecisionMetadata,
    SpeakingOpportunityKind,
)


@dataclass(frozen=True)
class SchedulerPolicy:
    version: str
    opportunity_order: tuple[SpeakingOpportunityKind, ...]
    max_consecutive_grants: int
    max_phase_grants: int
    silence_threshold: timedelta
    deadline_intervention_threshold: timedelta

    def __post_init__(self) -> None:
        if not self.version or len(self.version) > 64:
            raise ValueError("Policy version must be between 1 and 64 characters.")
        if len(self.opportunity_order) != len(SpeakingOpportunityKind) or set(
            self.opportunity_order
        ) != set(SpeakingOpportunityKind):
            raise ValueError("Policy must order every opportunity kind exactly once.")
        for value in (self.max_consecutive_grants, self.max_phase_grants):
            if type(value) is not int or value <= 0:
                raise ValueError("Scheduler caps must be positive integers.")
        for value in (
            self.silence_threshold,
            self.deadline_intervention_threshold,
        ):
            if value <= timedelta(0):
                raise ValueError("Scheduler thresholds must be positive durations.")


V0_1_SCHEDULER_POLICY_V1 = SchedulerPolicy(
    version="v0.1-floor-1",
    opportunity_order=(
        SpeakingOpportunityKind.PHASE_MANDATED,
        SpeakingOpportunityKind.EXPLICIT_REQUEST,
        SpeakingOpportunityKind.NOMINATION,
        SpeakingOpportunityKind.FAIRNESS,
    ),
    max_consecutive_grants=2,
    max_phase_grants=3,
    silence_threshold=timedelta(seconds=20),
    deadline_intervention_threshold=timedelta(seconds=15),
)

V0_1_SCHEDULER_POLICY_V2 = SchedulerPolicy(
    version="v0.1-floor-2",
    opportunity_order=V0_1_SCHEDULER_POLICY_V1.opportunity_order,
    max_consecutive_grants=V0_1_SCHEDULER_POLICY_V1.max_consecutive_grants,
    max_phase_grants=V0_1_SCHEDULER_POLICY_V1.max_phase_grants,
    silence_threshold=V0_1_SCHEDULER_POLICY_V1.silence_threshold,
    deadline_intervention_threshold=(
        V0_1_SCHEDULER_POLICY_V1.deadline_intervention_threshold
    ),
)

# Existing callers use this name for the current policy. Historical decisions keep
# their own immutable policy version and are never rewritten to this alias.
V0_1_SCHEDULER_POLICY = V0_1_SCHEDULER_POLICY_V2


def scheduler_policy_for_version(version: str) -> SchedulerPolicy | None:
    if version == V0_1_SCHEDULER_POLICY_V1.version:
        return V0_1_SCHEDULER_POLICY_V1
    if version == V0_1_SCHEDULER_POLICY_V2.version:
        return V0_1_SCHEDULER_POLICY_V2
    return None


@dataclass(frozen=True)
class SchedulerParticipant:
    participant_id: UUID
    actor_kind: ParticipantActorKind
    participation_role: ParticipationRole
    availability: ParticipantAvailability
    seat_order: int

    def __post_init__(self) -> None:
        if type(self.seat_order) is not int or self.seat_order <= 0:
            raise ValueError("Participant seat order must be a positive integer.")


@dataclass(frozen=True)
class SchedulerOpportunity:
    opportunity_id: UUID
    participant_id: UUID
    kind: SpeakingOpportunityKind
    created_at: datetime

    def __post_init__(self) -> None:
        _require_utc(self.created_at)


@dataclass(frozen=True)
class SchedulerGrantHistory:
    grant_id: UUID
    participant_id: UUID
    phase: SessionStatus
    granted_at: datetime
    released_at: datetime | None

    def __post_init__(self) -> None:
        if self.phase not in FLOOR_ENABLED_PHASES:
            raise ValueError("Grant history requires a floor-enabled phase.")
        _require_utc(self.granted_at)
        if self.released_at is not None:
            _require_utc(self.released_at)
            if self.released_at < self.granted_at:
                raise ValueError("Floor release cannot precede its grant.")


@dataclass(frozen=True)
class SchedulerInput:
    session_id: UUID
    decision_id: UUID
    phase: SessionStatus
    expected_last_sequence: int
    now: datetime
    phase_started_at: datetime
    phase_deadline_at: datetime
    participants: tuple[SchedulerParticipant, ...]
    opportunities: tuple[SchedulerOpportunity, ...]
    grant_history: tuple[SchedulerGrantHistory, ...]

    def __post_init__(self) -> None:
        if self.phase not in FLOOR_ENABLED_PHASES:
            raise ValueError("Scheduler input requires a floor-enabled phase.")
        if (
            type(self.expected_last_sequence) is not int
            or self.expected_last_sequence < 0
        ):
            raise ValueError("Expected sequence must be a non-negative integer.")
        for value in (self.now, self.phase_started_at, self.phase_deadline_at):
            _require_utc(value)
        if self.phase_deadline_at <= self.phase_started_at:
            raise ValueError("Phase deadline must follow phase start.")
        participant_ids = [item.participant_id for item in self.participants]
        if len(participant_ids) != len(set(participant_ids)):
            raise ValueError("Scheduler participants must be unique.")
        opportunity_ids = [item.opportunity_id for item in self.opportunities]
        if len(opportunity_ids) != len(set(opportunity_ids)):
            raise ValueError("Scheduler opportunities must be unique.")
        participant_id_set = set(participant_ids)
        if any(
            item.participant_id not in participant_id_set for item in self.opportunities
        ):
            raise ValueError("Scheduler opportunity participant is unknown.")
        if any(
            item.participant_id not in participant_id_set for item in self.grant_history
        ):
            raise ValueError("Scheduler grant participant is unknown.")


@dataclass(frozen=True)
class ScheduleFloorCommand:
    session_id: UUID
    action_id: UUID
    decision_id: UUID
    grant_id: UUID
    intervention_id: UUID
    expected_phase: SessionStatus
    expected_last_sequence: int
    expected_current_floor_grant_id: UUID | None
    evaluated_at: datetime
    policy: SchedulerPolicy
    schema_version: int = 1
    command_type: str = "floor.schedule"

    def __post_init__(self) -> None:
        if self.expected_phase not in FLOOR_ENABLED_PHASES:
            raise ValueError("Schedule command requires a floor-enabled phase.")
        if (
            type(self.expected_last_sequence) is not int
            or self.expected_last_sequence < 0
        ):
            raise ValueError("Expected sequence must be a non-negative integer.")
        _require_utc(self.evaluated_at)
        if type(self.schema_version) is not int or self.schema_version != 1:
            raise ValueError("Unsupported schedule command version.")
        if self.command_type != "floor.schedule":
            raise ValueError("Unsupported schedule command type.")


@dataclass(frozen=True)
class _Candidate:
    participant: SchedulerParticipant
    opportunity: SchedulerOpportunity | None
    opportunity_kind: SpeakingOpportunityKind
    phase_grant_count: int
    last_granted_at: datetime | None
    consecutive_grant_count: int
    is_previous_owner: bool


def _require_utc(value: datetime) -> None:
    if value.tzinfo is None or value.utcoffset() != timedelta(0):
        raise ValueError("Scheduler timestamps must use aware UTC values.")


def _intervention_decision(
    scheduler_input: SchedulerInput,
    policy: SchedulerPolicy,
    *,
    kind: FloorInterventionKind,
    reason: FloorPolicyReason,
) -> FloorDecisionRecord:
    return FloorDecisionRecord(
        decision_id=scheduler_input.decision_id,
        phase=scheduler_input.phase,
        expected_last_sequence=scheduler_input.expected_last_sequence,
        outcome=FloorDecisionOutcome.REQUEST_INTERVENTION,
        selected_participant_id=None,
        opportunity_id=None,
        intervention_kind=kind,
        policy_version=policy.version,
        primary_reason=reason,
        supporting_reasons=(),
        metadata=SafeDecisionMetadata(
            current_phase_grant_count=0,
            first_opportunity_unmet=False,
            previous_owner_was_selected=False,
            consecutive_grant_count=0,
            tie_break_class="NOT_APPLICABLE",
        ),
    )


def _no_grant_decision(
    scheduler_input: SchedulerInput,
    policy: SchedulerPolicy,
    *,
    reason: FloorPolicyReason = FloorPolicyReason.NO_ELIGIBLE_PARTICIPANT,
) -> FloorDecisionRecord:
    return FloorDecisionRecord(
        decision_id=scheduler_input.decision_id,
        phase=scheduler_input.phase,
        expected_last_sequence=scheduler_input.expected_last_sequence,
        outcome=FloorDecisionOutcome.NO_GRANT,
        selected_participant_id=None,
        opportunity_id=None,
        intervention_kind=None,
        policy_version=policy.version,
        primary_reason=reason,
        supporting_reasons=(),
        metadata=SafeDecisionMetadata(
            current_phase_grant_count=0,
            first_opportunity_unmet=False,
            previous_owner_was_selected=False,
            consecutive_grant_count=0,
            tie_break_class="NOT_APPLICABLE",
        ),
    )


def _ordinary_participant(participant: SchedulerParticipant) -> bool:
    return (
        participant.actor_kind in {ParticipantActorKind.AI, ParticipantActorKind.HUMAN}
        and participant.participation_role is ParticipationRole.CANDIDATE
        and participant.availability is ParticipantAvailability.AVAILABLE
    )


def _phase_history(
    scheduler_input: SchedulerInput,
) -> list[SchedulerGrantHistory]:
    return sorted(
        (
            item
            for item in scheduler_input.grant_history
            if item.phase is scheduler_input.phase
        ),
        key=lambda item: (item.granted_at, item.grant_id.int),
    )


def _consecutive_counts(
    history: list[SchedulerGrantHistory],
) -> tuple[UUID | None, dict[UUID, int]]:
    if not history:
        return None, {}
    previous_owner = history[-1].participant_id
    count = 0
    for item in reversed(history):
        if item.participant_id != previous_owner:
            break
        count += 1
    return previous_owner, {previous_owner: count}


def _best_opportunities(
    scheduler_input: SchedulerInput,
    policy: SchedulerPolicy,
) -> dict[UUID, SchedulerOpportunity]:
    class_rank = {kind: index for index, kind in enumerate(policy.opportunity_order)}
    ordered = sorted(
        scheduler_input.opportunities,
        key=lambda item: (
            class_rank[item.kind],
            item.created_at,
            item.opportunity_id.int,
        ),
    )
    selected: dict[UUID, SchedulerOpportunity] = {}
    for opportunity in ordered:
        selected.setdefault(opportunity.participant_id, opportunity)
    return selected


def _phase_order_key(candidate: _Candidate, phase: SessionStatus) -> tuple[object, ...]:
    if phase in {SessionStatus.OPENING_STATEMENTS, SessionStatus.FINAL_SUMMARY}:
        return ()
    oldest = candidate.last_granted_at or datetime.min.replace(tzinfo=UTC)
    return (candidate.phase_grant_count, oldest)


def _opportunity_reason(
    phase: SessionStatus,
    kind: SpeakingOpportunityKind,
) -> FloorPolicyReason:
    if kind is SpeakingOpportunityKind.PHASE_MANDATED:
        if phase in {SessionStatus.CONVERGENCE, SessionStatus.FINAL_SUMMARY}:
            return FloorPolicyReason.PHASE_SUMMARY_OPPORTUNITY
        return FloorPolicyReason.PHASE_MANDATED_TURN
    if kind in {
        SpeakingOpportunityKind.EXPLICIT_REQUEST,
        SpeakingOpportunityKind.NOMINATION,
    }:
        return FloorPolicyReason.EXPLICIT_OPPORTUNITY
    return FloorPolicyReason.FAIRNESS_RECOVERY


def _tie_break_class(
    candidates: list[_Candidate],
    selected: _Candidate,
    prefix_key: Callable[[_Candidate], tuple[object, ...]],
    policy: SchedulerPolicy,
) -> str:
    tied = [item for item in candidates if prefix_key(item) == prefix_key(selected)]
    if len(tied) <= 1:
        return "NOT_APPLICABLE"
    if policy.version == V0_1_SCHEDULER_POLICY_V1.version:
        lowest_seat = min(item.participant.seat_order for item in tied)
        if sum(item.participant.seat_order == lowest_seat for item in tied) == 1:
            return "SEAT_ORDER"
    return "PARTICIPANT_ID"


def _stable_tie_break_value(
    scheduler_input: SchedulerInput,
    participant_id: UUID,
) -> int:
    payload = (
        f"{scheduler_input.session_id}:{scheduler_input.phase.value}:{participant_id}"
    ).encode("ascii")
    return int.from_bytes(hashlib.sha256(payload).digest(), "big")


def decide_floor(
    scheduler_input: SchedulerInput,
    policy: SchedulerPolicy,
) -> FloorDecisionRecord:
    if scheduler_policy_for_version(policy.version) is None:
        raise ValueError("Unsupported scheduler policy version.")
    if scheduler_input.now >= scheduler_input.phase_deadline_at:
        if policy.version == V0_1_SCHEDULER_POLICY_V1.version:
            return _intervention_decision(
                scheduler_input,
                policy,
                kind=FloorInterventionKind.DEADLINE,
                reason=FloorPolicyReason.DEADLINE_RECOVERY,
            )
        return _no_grant_decision(
            scheduler_input,
            policy,
            reason=FloorPolicyReason.DEADLINE_RECOVERY,
        )
    if (
        scheduler_input.phase_deadline_at - scheduler_input.now
        <= policy.deadline_intervention_threshold
    ):
        if policy.version == V0_1_SCHEDULER_POLICY_V1.version:
            return _intervention_decision(
                scheduler_input,
                policy,
                kind=FloorInterventionKind.DEADLINE,
                reason=FloorPolicyReason.DEADLINE_RECOVERY,
            )
        return _no_grant_decision(
            scheduler_input,
            policy,
            reason=FloorPolicyReason.DEADLINE_RECOVERY,
        )

    ordinary = sorted(
        (item for item in scheduler_input.participants if _ordinary_participant(item)),
        key=lambda item: (item.seat_order, item.participant_id.int),
    )
    if not ordinary:
        return _intervention_decision(
            scheduler_input,
            policy,
            kind=FloorInterventionKind.NO_ELIGIBLE_PARTICIPANT,
            reason=FloorPolicyReason.NO_ELIGIBLE_PARTICIPANT,
        )

    history = _phase_history(scheduler_input)
    previous_owner, consecutive_counts = _consecutive_counts(history)
    best_opportunities = _best_opportunities(scheduler_input, policy)
    grant_count: dict[UUID, int] = {}
    last_granted: dict[UUID, datetime] = {}
    for grant in history:
        grant_count[grant.participant_id] = grant_count.get(grant.participant_id, 0) + 1
        last_granted[grant.participant_id] = grant.granted_at

    candidates: list[_Candidate] = []
    previous_excluded_by_consecutive_cap = False
    for participant in ordinary:
        phase_count = grant_count.get(participant.participant_id, 0)
        consecutive_count = consecutive_counts.get(participant.participant_id, 0)
        if (
            participant.participant_id == previous_owner
            and consecutive_count >= policy.max_consecutive_grants
        ):
            previous_excluded_by_consecutive_cap = True
        if (
            phase_count >= policy.max_phase_grants
            or consecutive_count >= policy.max_consecutive_grants
        ):
            continue
        opportunity = best_opportunities.get(participant.participant_id)
        candidates.append(
            _Candidate(
                participant=participant,
                opportunity=opportunity,
                opportunity_kind=(
                    opportunity.kind
                    if opportunity is not None
                    else SpeakingOpportunityKind.FAIRNESS
                ),
                phase_grant_count=phase_count,
                last_granted_at=last_granted.get(participant.participant_id),
                consecutive_grant_count=consecutive_count,
                is_previous_owner=participant.participant_id == previous_owner,
            )
        )

    if not candidates:
        latest_activity = max(
            [
                scheduler_input.phase_started_at,
                *(item.granted_at for item in history),
                *(item.released_at for item in history if item.released_at is not None),
            ]
        )
        if scheduler_input.now - latest_activity >= policy.silence_threshold:
            return _intervention_decision(
                scheduler_input,
                policy,
                kind=FloorInterventionKind.SILENCE,
                reason=FloorPolicyReason.SILENCE_RECOVERY,
            )
        return _no_grant_decision(scheduler_input, policy)

    has_unmet_alternative = any(
        item.phase_grant_count == 0 and not item.is_previous_owner
        for item in candidates
    )
    monopoly_guard_applied = has_unmet_alternative and (
        previous_excluded_by_consecutive_cap
        or any(item.is_previous_owner for item in candidates)
    )
    if monopoly_guard_applied:
        candidates = [item for item in candidates if not item.is_previous_owner]

    class_rank = {kind: index for index, kind in enumerate(policy.opportunity_order)}

    def prefix(candidate: _Candidate) -> tuple[object, ...]:
        shared = (
            class_rank[candidate.opportunity_kind],
            candidate.phase_grant_count != 0,
            *_phase_order_key(candidate, scheduler_input.phase),
        )
        if policy.version == V0_1_SCHEDULER_POLICY_V1.version:
            return shared
        return (
            *shared,
            0 if candidate.participant.actor_kind is ParticipantActorKind.HUMAN else 1,
        )

    def full_key(candidate: _Candidate) -> tuple[object, ...]:
        if policy.version == V0_1_SCHEDULER_POLICY_V1.version:
            return (
                *prefix(candidate),
                candidate.participant.seat_order,
                candidate.participant.participant_id.int,
            )
        return (
            *prefix(candidate),
            _stable_tie_break_value(
                scheduler_input,
                candidate.participant.participant_id,
            ),
            candidate.participant.participant_id.int,
        )

    ordered = sorted(candidates, key=full_key)
    selected = ordered[0]
    tie_break_class = _tie_break_class(ordered, selected, prefix, policy)
    opportunity_reason = _opportunity_reason(
        scheduler_input.phase,
        selected.opportunity_kind,
    )
    if monopoly_guard_applied:
        primary_reason = FloorPolicyReason.MONOPOLY_PREVENTION
    elif selected.phase_grant_count == 0:
        primary_reason = FloorPolicyReason.FIRST_OPPORTUNITY
    else:
        primary_reason = opportunity_reason

    supporting: list[FloorPolicyReason] = []
    for reason in (
        opportunity_reason,
        FloorPolicyReason.FIRST_OPPORTUNITY
        if selected.phase_grant_count == 0
        else None,
        FloorPolicyReason.MONOPOLY_PREVENTION if monopoly_guard_applied else None,
    ):
        if reason is not None and reason != primary_reason and reason not in supporting:
            supporting.append(reason)

    return FloorDecisionRecord(
        decision_id=scheduler_input.decision_id,
        phase=scheduler_input.phase,
        expected_last_sequence=scheduler_input.expected_last_sequence,
        outcome=FloorDecisionOutcome.GRANT,
        selected_participant_id=selected.participant.participant_id,
        opportunity_id=(
            selected.opportunity.opportunity_id
            if selected.opportunity is not None
            else None
        ),
        intervention_kind=None,
        policy_version=policy.version,
        primary_reason=primary_reason,
        supporting_reasons=tuple(supporting),
        metadata=SafeDecisionMetadata(
            current_phase_grant_count=selected.phase_grant_count,
            first_opportunity_unmet=selected.phase_grant_count == 0,
            previous_owner_was_selected=selected.is_previous_owner,
            consecutive_grant_count=selected.consecutive_grant_count,
            tie_break_class=tie_break_class,
        ),
    )
