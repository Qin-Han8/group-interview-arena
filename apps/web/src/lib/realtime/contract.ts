export type SessionCreatedEvent = {
  schema_version: 1;
  type: "session.created";
  session_id: string;
  sequence: number;
  occurred_at: string;
  action_id: null;
  payload: { status: "CREATED" };
};

export type SessionStatus =
  | "CREATED"
  | "PREPARATION"
  | "OPENING_STATEMENTS"
  | "EXPLORATION"
  | "CONFLICT_AND_EVALUATION"
  | "CONVERGENCE"
  | "FINAL_SUMMARY"
  | "COMPLETED"
  | "ABORTED_USER";

export type SessionStateChangedV1Event = {
  schema_version: 1;
  type: "session.state_changed";
  session_id: string;
  sequence: number;
  occurred_at: string;
  action_id: string;
  payload: {
    previous_status: "CREATED";
    status: "ABORTED_USER";
  };
};

export type SessionStateChangedV2Event = {
  schema_version: 2;
  type: "session.state_changed";
  session_id: string;
  sequence: number;
  occurred_at: string;
  action_id: string | null;
  payload: {
    previous_status: SessionStatus;
    status: SessionStatus;
    trigger: "USER_START" | "USER_ABORT" | "PHASE_DEADLINE";
    phase_started_at: string | null;
    phase_deadline_at: string | null;
  };
};

export type SessionStateChangedEvent =
  SessionStateChangedV1Event | SessionStateChangedV2Event;

type FloorPhase = Exclude<
  SessionStatus,
  "CREATED" | "PREPARATION" | "COMPLETED" | "ABORTED_USER"
>;

export type FloorPolicyReason =
  | "PHASE_MANDATED_TURN"
  | "EXPLICIT_OPPORTUNITY"
  | "FIRST_OPPORTUNITY"
  | "FAIRNESS_RECOVERY"
  | "MONOPOLY_PREVENTION"
  | "PHASE_SUMMARY_OPPORTUNITY"
  | "SILENCE_RECOVERY"
  | "DEADLINE_RECOVERY"
  | "NO_ELIGIBLE_PARTICIPANT";

export type FloorReleaseReason =
  "SPEAKER_FINISHED" | "INTERRUPTED" | "PHASE_CHANGED" | "SESSION_TERMINATED";

export type FloorGrantedV1Event = {
  schema_version: 1;
  type: "floor.granted";
  session_id: string;
  sequence: number;
  occurred_at: string;
  action_id: string;
  payload: {
    grant_id: string;
    decision_id: string;
    participant_id: string;
    phase: FloorPhase;
    opportunity_id: string | null;
    reason_code: FloorPolicyReason;
    policy_version: string;
  };
};

export type FloorGrantedV2Event = Omit<
  FloorGrantedV1Event,
  "schema_version" | "action_id"
> & {
  schema_version: 2;
  action_id: string | null;
};

export type FloorGrantedEvent = FloorGrantedV1Event | FloorGrantedV2Event;

export type FloorReleasedV1Event = {
  schema_version: 1;
  type: "floor.released";
  session_id: string;
  sequence: number;
  occurred_at: string;
  action_id: string | null;
  payload: {
    grant_id: string;
    participant_id: string;
    phase: FloorPhase;
    reason_code: FloorReleaseReason;
  };
};

export type FloorReleasedV2Event = Omit<
  FloorReleasedV1Event,
  "schema_version" | "action_id"
> & {
  schema_version: 2;
  action_id: string | null;
};

export type FloorReleasedEvent = FloorReleasedV1Event | FloorReleasedV2Event;

export type FloorInterventionRequestedV1Event = {
  schema_version: 1;
  type: "floor.intervention_requested";
  session_id: string;
  sequence: number;
  occurred_at: string;
  action_id: string;
  payload: {
    intervention_id: string;
    decision_id: string;
    phase: FloorPhase;
    intervention_kind: "SILENCE" | "DEADLINE" | "NO_ELIGIBLE_PARTICIPANT";
    reason_code: FloorPolicyReason;
    policy_version: string;
  };
};

export type FloorInterventionRequestedV2Event = Omit<
  FloorInterventionRequestedV1Event,
  "schema_version" | "action_id"
> & {
  schema_version: 2;
  action_id: string | null;
};

export type FloorInterventionRequestedEvent =
  FloorInterventionRequestedV1Event | FloorInterventionRequestedV2Event;

export type FloorEvent =
  FloorGrantedEvent | FloorReleasedEvent | FloorInterventionRequestedEvent;

export type FormalSessionEvent =
  SessionCreatedEvent | SessionStateChangedEvent | FloorEvent;

export type RealtimeErrorCode =
  | "INVALID_SESSION_STATE"
  | "ACTION_ID_CONFLICT"
  | "PROTOCOL_ERROR"
  | "SEQUENCE_AHEAD"
  | "INTERNAL_ERROR";

export type RealtimeErrorEvent = {
  schema_version: 1;
  type: "error";
  session_id: string;
  action_id: string | null;
  occurred_at: string;
  error: {
    code: RealtimeErrorCode;
    message: string;
    request_id: string;
  };
};

export type RealtimeMessage = FormalSessionEvent | RealtimeErrorEvent;

export type SessionAbortCommand = {
  schema_version: 1;
  type: "session.abort";
  session_id: string;
  action_id: string;
  payload: Record<string, never>;
};

export type SessionStartCommand = {
  schema_version: 1;
  type: "session.start";
  session_id: string;
  action_id: string;
  payload: Record<string, never>;
};

const UUID4_PATTERN =
  /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
const ERROR_CODES = new Set<RealtimeErrorCode>([
  "INVALID_SESSION_STATE",
  "ACTION_ID_CONFLICT",
  "PROTOCOL_ERROR",
  "SEQUENCE_AHEAD",
  "INTERNAL_ERROR",
]);
const SESSION_STATUSES = new Set<SessionStatus>([
  "CREATED",
  "PREPARATION",
  "OPENING_STATEMENTS",
  "EXPLORATION",
  "CONFLICT_AND_EVALUATION",
  "CONVERGENCE",
  "FINAL_SUMMARY",
  "COMPLETED",
  "ABORTED_USER",
]);
const ACTIVE_STATUSES = new Set<SessionStatus>([
  "PREPARATION",
  "OPENING_STATEMENTS",
  "EXPLORATION",
  "CONFLICT_AND_EVALUATION",
  "CONVERGENCE",
  "FINAL_SUMMARY",
]);
const FLOOR_PHASES = new Set<FloorPhase>([
  "OPENING_STATEMENTS",
  "EXPLORATION",
  "CONFLICT_AND_EVALUATION",
  "CONVERGENCE",
  "FINAL_SUMMARY",
]);
const FLOOR_POLICY_REASONS = new Set<FloorPolicyReason>([
  "PHASE_MANDATED_TURN",
  "EXPLICIT_OPPORTUNITY",
  "FIRST_OPPORTUNITY",
  "FAIRNESS_RECOVERY",
  "MONOPOLY_PREVENTION",
  "PHASE_SUMMARY_OPPORTUNITY",
  "SILENCE_RECOVERY",
  "DEADLINE_RECOVERY",
  "NO_ELIGIBLE_PARTICIPANT",
]);
const FLOOR_RELEASE_REASONS = new Set<FloorReleaseReason>([
  "SPEAKER_FINISHED",
  "INTERRUPTED",
  "PHASE_CHANGED",
  "SESSION_TERMINATED",
]);

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function hasExactKeys(value: Record<string, unknown>, keys: string[]) {
  const actual = Object.keys(value).sort();
  return (
    actual.length === keys.length &&
    actual.every((key, index) => key === [...keys].sort()[index])
  );
}

function isUuid4(value: unknown): value is string {
  return typeof value === "string" && UUID4_PATTERN.test(value);
}

function isAwareTimestamp(value: unknown): value is string {
  return (
    typeof value === "string" &&
    /(?:Z|[+-]\d{2}:\d{2})$/.test(value) &&
    !Number.isNaN(Date.parse(value))
  );
}

function hasEnvelopeIdentity(value: Record<string, unknown>) {
  return isUuid4(value.session_id) && isAwareTimestamp(value.occurred_at);
}

function isSessionStatus(value: unknown): value is SessionStatus {
  return (
    typeof value === "string" && SESSION_STATUSES.has(value as SessionStatus)
  );
}

function isV2StateChangedPayload(
  value: Record<string, unknown>,
): value is SessionStateChangedV2Event["payload"] {
  if (
    !hasExactKeys(value, [
      "previous_status",
      "status",
      "trigger",
      "phase_started_at",
      "phase_deadline_at",
    ]) ||
    !isSessionStatus(value.previous_status) ||
    !isSessionStatus(value.status) ||
    value.previous_status === value.status ||
    !["USER_START", "USER_ABORT", "PHASE_DEADLINE"].includes(
      String(value.trigger),
    )
  ) {
    return false;
  }

  if (ACTIVE_STATUSES.has(value.status)) {
    return (
      isAwareTimestamp(value.phase_started_at) &&
      isAwareTimestamp(value.phase_deadline_at)
    );
  }

  return value.phase_started_at === null && value.phase_deadline_at === null;
}

function isFloorPhase(value: unknown): value is FloorPhase {
  return typeof value === "string" && FLOOR_PHASES.has(value as FloorPhase);
}

function isFloorPolicyReason(value: unknown): value is FloorPolicyReason {
  return (
    typeof value === "string" &&
    FLOOR_POLICY_REASONS.has(value as FloorPolicyReason)
  );
}

function isFloorEvent(value: Record<string, unknown>): value is FloorEvent {
  if (
    (value.schema_version !== 1 && value.schema_version !== 2) ||
    !isRecord(value.payload) ||
    !isFloorPhase(value.payload.phase)
  ) {
    return false;
  }
  const payload = value.payload;

  if (value.type === "floor.granted") {
    return (
      (value.schema_version === 1
        ? isUuid4(value.action_id)
        : value.action_id === null || isUuid4(value.action_id)) &&
      hasExactKeys(payload, [
        "grant_id",
        "decision_id",
        "participant_id",
        "phase",
        "opportunity_id",
        "reason_code",
        "policy_version",
      ]) &&
      isUuid4(payload.grant_id) &&
      isUuid4(payload.decision_id) &&
      isUuid4(payload.participant_id) &&
      (payload.opportunity_id === null || isUuid4(payload.opportunity_id)) &&
      isFloorPolicyReason(payload.reason_code) &&
      typeof payload.policy_version === "string" &&
      payload.policy_version.length > 0 &&
      payload.policy_version.length <= 64
    );
  }

  if (value.type === "floor.released") {
    return (
      (value.action_id === null || isUuid4(value.action_id)) &&
      hasExactKeys(payload, [
        "grant_id",
        "participant_id",
        "phase",
        "reason_code",
      ]) &&
      isUuid4(payload.grant_id) &&
      isUuid4(payload.participant_id) &&
      typeof payload.reason_code === "string" &&
      FLOOR_RELEASE_REASONS.has(payload.reason_code as FloorReleaseReason)
    );
  }

  if (value.type !== "floor.intervention_requested") return false;
  return (
    (value.schema_version === 1
      ? isUuid4(value.action_id)
      : value.action_id === null || isUuid4(value.action_id)) &&
    hasExactKeys(payload, [
      "intervention_id",
      "decision_id",
      "phase",
      "intervention_kind",
      "reason_code",
      "policy_version",
    ]) &&
    isUuid4(payload.intervention_id) &&
    isUuid4(payload.decision_id) &&
    ["SILENCE", "DEADLINE", "NO_ELIGIBLE_PARTICIPANT"].includes(
      String(payload.intervention_kind),
    ) &&
    isFloorPolicyReason(payload.reason_code) &&
    typeof payload.policy_version === "string" &&
    payload.policy_version.length > 0 &&
    payload.policy_version.length <= 64
  );
}

function isFormalEvent(
  value: Record<string, unknown>,
): value is FormalSessionEvent {
  if (
    !hasExactKeys(value, [
      "schema_version",
      "type",
      "session_id",
      "sequence",
      "occurred_at",
      "action_id",
      "payload",
    ]) ||
    !hasEnvelopeIdentity(value) ||
    (value.schema_version !== 1 && value.schema_version !== 2) ||
    !Number.isSafeInteger(value.sequence) ||
    Number(value.sequence) <= 0 ||
    !isRecord(value.payload)
  ) {
    return false;
  }

  if (value.type === "session.created") {
    return (
      value.schema_version === 1 &&
      value.action_id === null &&
      hasExactKeys(value.payload, ["status"]) &&
      value.payload.status === "CREATED"
    );
  }

  if (value.type !== "session.state_changed") return isFloorEvent(value);

  if (value.schema_version === 1) {
    return (
      isUuid4(value.action_id) &&
      hasExactKeys(value.payload, ["previous_status", "status"]) &&
      value.payload.previous_status === "CREATED" &&
      value.payload.status === "ABORTED_USER"
    );
  }

  if (!isV2StateChangedPayload(value.payload)) return false;
  if (value.payload.trigger === "PHASE_DEADLINE")
    return value.action_id === null;
  return isUuid4(value.action_id);
}

function isErrorEvent(
  value: Record<string, unknown>,
): value is RealtimeErrorEvent {
  if (
    !hasExactKeys(value, [
      "schema_version",
      "type",
      "session_id",
      "action_id",
      "occurred_at",
      "error",
    ]) ||
    !hasEnvelopeIdentity(value) ||
    value.schema_version !== 1 ||
    value.type !== "error" ||
    (value.action_id !== null && !isUuid4(value.action_id)) ||
    !isRecord(value.error) ||
    !hasExactKeys(value.error, ["code", "message", "request_id"])
  ) {
    return false;
  }

  return (
    typeof value.error.code === "string" &&
    ERROR_CODES.has(value.error.code as RealtimeErrorCode) &&
    typeof value.error.message === "string" &&
    isUuid4(value.error.request_id)
  );
}

export function parseRealtimeMessage(raw: string): RealtimeMessage | undefined {
  let value: unknown;
  try {
    value = JSON.parse(raw);
  } catch {
    return undefined;
  }

  if (!isRecord(value)) return undefined;
  if (isFormalEvent(value) || isErrorEvent(value)) return value;
  return undefined;
}
