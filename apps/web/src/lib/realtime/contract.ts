export type SessionCreatedEvent = {
  schema_version: 1;
  type: "session.created";
  session_id: string;
  sequence: number;
  occurred_at: string;
  action_id: null;
  payload: { status: "CREATED" };
};

type SessionStatus =
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

export type FormalSessionEvent = SessionCreatedEvent | SessionStateChangedEvent;

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

  if (value.type !== "session.state_changed") return false;

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
