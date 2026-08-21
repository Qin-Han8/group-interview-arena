import type { SessionSnapshot } from "@/lib/api/client";

import type { FormalSessionEvent } from "./contract";

export function projectSessionEvent(
  snapshot: SessionSnapshot,
  event: FormalSessionEvent,
): SessionSnapshot {
  if (event.type === "session.created") {
    return {
      ...snapshot,
      status: "CREATED",
      phase_started_at: null,
      phase_deadline_at: null,
      updated_at: event.occurred_at,
      last_sequence: event.sequence,
    };
  }

  if (event.type === "session.state_changed") {
    return {
      ...snapshot,
      status: event.payload.status,
      phase_started_at:
        event.schema_version === 2 ? event.payload.phase_started_at : null,
      phase_deadline_at:
        event.schema_version === 2 ? event.payload.phase_deadline_at : null,
      server_now: event.occurred_at,
      updated_at: event.occurred_at,
      last_sequence: event.sequence,
    };
  }

  const latestEvent = {
    type: event.type,
    sequence: event.sequence,
    occurred_at: event.occurred_at,
    phase: event.payload.phase,
    reason_code: event.payload.reason_code,
    grant_id:
      event.type === "floor.granted" || event.type === "floor.released"
        ? event.payload.grant_id
        : null,
    participant_id:
      event.type === "floor.granted" || event.type === "floor.released"
        ? event.payload.participant_id
        : null,
    intervention_id:
      event.type === "floor.intervention_requested"
        ? event.payload.intervention_id
        : null,
    intervention_kind:
      event.type === "floor.intervention_requested"
        ? event.payload.intervention_kind
        : null,
  } as SessionSnapshot["floor"]["latest_event"];

  return {
    ...snapshot,
    server_now: event.occurred_at,
    updated_at: event.occurred_at,
    last_sequence: event.sequence,
    floor: {
      ...snapshot.floor,
      current_grant:
        event.type === "floor.granted"
          ? {
              grant_id: event.payload.grant_id,
              participant_id: event.payload.participant_id,
              phase: event.payload.phase,
              reason_code: event.payload.reason_code,
              granted_at: event.occurred_at,
            }
          : event.type === "floor.released"
            ? null
            : snapshot.floor.current_grant,
      latest_event: latestEvent,
    },
  };
}
