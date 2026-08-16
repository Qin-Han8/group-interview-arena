export type SessionCreatedEvent = {
  schema_version: 1;
  type: "session.created";
  session_id: string;
  sequence: number;
  occurred_at: string;
  action_id: null;
  payload: { status: "CREATED" };
};

export type SessionStateChangedEvent = {
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

const UUID4_PATTERN =
  /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
const ERROR_CODES = new Set<RealtimeErrorCode>([
  "INVALID_SESSION_STATE",
  "ACTION_ID_CONFLICT",
  "PROTOCOL_ERROR",
  "SEQUENCE_AHEAD",
  "INTERNAL_ERROR",
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
  return (
    value.schema_version === 1 &&
    isUuid4(value.session_id) &&
    isAwareTimestamp(value.occurred_at)
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
    !Number.isSafeInteger(value.sequence) ||
    Number(value.sequence) <= 0 ||
    !isRecord(value.payload)
  ) {
    return false;
  }

  if (value.type === "session.created") {
    return (
      value.action_id === null &&
      hasExactKeys(value.payload, ["status"]) &&
      value.payload.status === "CREATED"
    );
  }

  return (
    value.type === "session.state_changed" &&
    isUuid4(value.action_id) &&
    hasExactKeys(value.payload, ["previous_status", "status"]) &&
    value.payload.previous_status === "CREATED" &&
    value.payload.status === "ABORTED_USER"
  );
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
