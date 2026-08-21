import { describe, expect, it } from "vitest";

import type { SessionSnapshot } from "@/lib/api/client";

import type { FormalSessionEvent } from "./contract";
import { projectSessionEvent } from "./projection";

const SESSION_ID = "00000000-0000-4000-8000-000000000001";
const ACTION_ID = "00000000-0000-4000-8000-000000000002";
const PARTICIPANT_ID = "00000000-0000-4000-8000-000000000003";
const GRANT_ID = "00000000-0000-4000-8000-000000000004";

const SNAPSHOT: SessionSnapshot = {
  id: SESSION_ID,
  question_version_id: null,
  status: "OPENING_STATEMENTS",
  phase_started_at: "2026-08-20T01:00:00Z",
  phase_deadline_at: "2026-08-20T01:04:00Z",
  server_now: "2026-08-20T01:00:00Z",
  created_at: "2026-08-20T00:59:00Z",
  updated_at: "2026-08-20T01:00:00Z",
  last_sequence: 3,
  floor: {
    participants: [
      { participant_id: PARTICIPANT_ID, actor_kind: "AI", seat_order: 2 },
    ],
    current_grant: null,
    latest_event: null,
  },
};

function event(
  type: "floor.granted" | "floor.released",
  sequence: number,
): FormalSessionEvent {
  if (type === "floor.granted") {
    return {
      schema_version: 1,
      type,
      session_id: SESSION_ID,
      sequence,
      occurred_at: "2026-08-20T01:00:01Z",
      action_id: ACTION_ID,
      payload: {
        grant_id: GRANT_ID,
        decision_id: "00000000-0000-4000-8000-000000000005",
        participant_id: PARTICIPANT_ID,
        phase: "OPENING_STATEMENTS",
        opportunity_id: null,
        reason_code: "FIRST_OPPORTUNITY",
        policy_version: "v0.1-floor-1",
      },
    };
  }
  return {
    schema_version: 1,
    type,
    session_id: SESSION_ID,
    sequence,
    occurred_at: "2026-08-20T01:00:02Z",
    action_id: null,
    payload: {
      grant_id: GRANT_ID,
      participant_id: PARTICIPANT_ID,
      phase: "OPENING_STATEMENTS",
      reason_code: "PHASE_CHANGED",
    },
  };
}

describe("authoritative floor projection", () => {
  it("projects grant then release without exposing scheduler metadata", () => {
    const granted = projectSessionEvent(SNAPSHOT, event("floor.granted", 4));
    expect(granted.floor.current_grant).toMatchObject({
      grant_id: GRANT_ID,
      participant_id: PARTICIPANT_ID,
      reason_code: "FIRST_OPPORTUNITY",
    });
    expect(granted.floor.latest_event).not.toHaveProperty("decision_id");
    expect(granted.floor.latest_event).not.toHaveProperty("policy_version");

    const released = projectSessionEvent(granted, event("floor.released", 5));
    expect(released.floor.current_grant).toBeNull();
    expect(released.floor.latest_event).toMatchObject({
      type: "floor.released",
      sequence: 5,
      reason_code: "PHASE_CHANGED",
    });
    expect(released.last_sequence).toBe(5);
  });

  it("projects an intervention fact without changing the current owner", () => {
    const granted = projectSessionEvent(SNAPSHOT, event("floor.granted", 4));
    const intervention = projectSessionEvent(granted, {
      schema_version: 1,
      type: "floor.intervention_requested",
      session_id: SESSION_ID,
      sequence: 5,
      occurred_at: "2026-08-20T01:00:02Z",
      action_id: ACTION_ID,
      payload: {
        intervention_id: "00000000-0000-4000-8000-000000000006",
        decision_id: "00000000-0000-4000-8000-000000000007",
        phase: "OPENING_STATEMENTS",
        intervention_kind: "SILENCE",
        reason_code: "SILENCE_RECOVERY",
        policy_version: "v0.1-floor-1",
      },
    });

    expect(intervention.floor.current_grant).toEqual(
      granted.floor.current_grant,
    );
    expect(intervention.floor.latest_event).toMatchObject({
      type: "floor.intervention_requested",
      sequence: 5,
      intervention_kind: "SILENCE",
      reason_code: "SILENCE_RECOVERY",
    });
  });
});
