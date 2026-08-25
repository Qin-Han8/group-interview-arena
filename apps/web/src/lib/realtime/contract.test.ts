import { describe, expect, it } from "vitest";

import { parseRealtimeMessage } from "./contract";

const SESSION_ID = "00000000-0000-4000-8000-000000000001";
const ACTION_ID = "00000000-0000-4000-8000-000000000002";
const REQUEST_ID = "00000000-0000-4000-8000-000000000003";
const PARTICIPANT_ID = "00000000-0000-4000-8000-000000000004";
const GRANT_ID = "00000000-0000-4000-8000-000000000005";
const DECISION_ID = "00000000-0000-4000-8000-000000000006";
const INTERVENTION_ID = "00000000-0000-4000-8000-000000000007";

describe("WebSocket derivative contract", () => {
  it.each([
    {
      schema_version: 1,
      type: "floor.granted",
      session_id: SESSION_ID,
      sequence: 4,
      occurred_at: "2026-08-20T01:04:01Z",
      action_id: ACTION_ID,
      payload: {
        grant_id: GRANT_ID,
        decision_id: DECISION_ID,
        participant_id: PARTICIPANT_ID,
        phase: "OPENING_STATEMENTS",
        opportunity_id: null,
        reason_code: "FIRST_OPPORTUNITY",
        policy_version: "v0.1-floor-1",
      },
    },
    {
      schema_version: 1,
      type: "floor.released",
      session_id: SESSION_ID,
      sequence: 5,
      occurred_at: "2026-08-20T01:04:02Z",
      action_id: null,
      payload: {
        grant_id: GRANT_ID,
        participant_id: PARTICIPANT_ID,
        phase: "OPENING_STATEMENTS",
        reason_code: "PHASE_CHANGED",
      },
    },
    {
      schema_version: 1,
      type: "floor.intervention_requested",
      session_id: SESSION_ID,
      sequence: 6,
      occurred_at: "2026-08-20T01:04:03Z",
      action_id: ACTION_ID,
      payload: {
        intervention_id: INTERVENTION_ID,
        decision_id: DECISION_ID,
        phase: "EXPLORATION",
        intervention_kind: "SILENCE",
        reason_code: "SILENCE_RECOVERY",
        policy_version: "v0.1-floor-1",
      },
    },
    {
      schema_version: 1,
      type: "session.created",
      session_id: SESSION_ID,
      sequence: 1,
      occurred_at: "2026-08-16T00:00:00Z",
      action_id: null,
      payload: { status: "CREATED" },
    },
    {
      schema_version: 1,
      type: "session.state_changed",
      session_id: SESSION_ID,
      sequence: 2,
      occurred_at: "2026-08-16T00:00:01+00:00",
      action_id: ACTION_ID,
      payload: {
        previous_status: "CREATED",
        status: "ABORTED_USER",
      },
    },
    {
      schema_version: 2,
      type: "session.state_changed",
      session_id: SESSION_ID,
      sequence: 2,
      occurred_at: "2026-08-20T01:00:00Z",
      action_id: ACTION_ID,
      payload: {
        previous_status: "CREATED",
        status: "PREPARATION",
        trigger: "USER_START",
        phase_started_at: "2026-08-20T01:00:00Z",
        phase_deadline_at: "2026-08-20T01:04:00Z",
      },
    },
    {
      schema_version: 2,
      type: "session.state_changed",
      session_id: SESSION_ID,
      sequence: 3,
      occurred_at: "2026-08-20T01:04:00Z",
      action_id: null,
      payload: {
        previous_status: "PREPARATION",
        status: "OPENING_STATEMENTS",
        trigger: "PHASE_DEADLINE",
        phase_started_at: "2026-08-20T01:04:00Z",
        phase_deadline_at: "2026-08-20T01:08:00Z",
      },
    },
    {
      schema_version: 1,
      type: "error",
      session_id: SESSION_ID,
      action_id: ACTION_ID,
      occurred_at: "2026-08-16T00:00:01Z",
      error: {
        code: "ACTION_ID_CONFLICT",
        message: "Action identity conflicts with an earlier command.",
        request_id: REQUEST_ID,
      },
    },
  ])("accepts canonical backend envelopes", (message) => {
    expect(parseRealtimeMessage(JSON.stringify(message))).toEqual(message);
  });

  it.each([
    {
      schema_version: 2,
      type: "floor.granted",
      session_id: SESSION_ID,
      sequence: 7,
      occurred_at: "2026-08-25T01:04:04Z",
      action_id: null,
      payload: {
        grant_id: GRANT_ID,
        decision_id: DECISION_ID,
        participant_id: PARTICIPANT_ID,
        phase: "OPENING_STATEMENTS",
        opportunity_id: null,
        reason_code: "FIRST_OPPORTUNITY",
        policy_version: "v0.1-floor-1",
      },
    },
    {
      schema_version: 2,
      type: "floor.released",
      session_id: SESSION_ID,
      sequence: 8,
      occurred_at: "2026-08-25T01:04:05Z",
      action_id: null,
      payload: {
        grant_id: GRANT_ID,
        participant_id: PARTICIPANT_ID,
        phase: "OPENING_STATEMENTS",
        reason_code: "PHASE_CHANGED",
      },
    },
    {
      schema_version: 2,
      type: "floor.released",
      session_id: SESSION_ID,
      sequence: 9,
      occurred_at: "2026-08-25T01:04:06Z",
      action_id: ACTION_ID,
      payload: {
        grant_id: GRANT_ID,
        participant_id: PARTICIPANT_ID,
        phase: "OPENING_STATEMENTS",
        reason_code: "SPEAKER_FINISHED",
      },
    },
    {
      schema_version: 2,
      type: "floor.intervention_requested",
      session_id: SESSION_ID,
      sequence: 10,
      occurred_at: "2026-08-25T01:04:07Z",
      action_id: null,
      payload: {
        intervention_id: INTERVENTION_ID,
        decision_id: DECISION_ID,
        phase: "EXPLORATION",
        intervention_kind: "SILENCE",
        reason_code: "SILENCE_RECOVERY",
        policy_version: "v0.1-floor-1",
      },
    },
  ])("accepts additive floor v2 envelopes", (message) => {
    expect(parseRealtimeMessage(JSON.stringify(message))).toEqual(message);
  });

  it.each([
    {
      schema_version: 1,
      type: "floor.granted",
      session_id: SESSION_ID,
      sequence: 11,
      occurred_at: "2026-08-25T01:04:08Z",
      action_id: null,
      payload: {
        grant_id: GRANT_ID,
        decision_id: DECISION_ID,
        participant_id: PARTICIPANT_ID,
        phase: "OPENING_STATEMENTS",
        opportunity_id: null,
        reason_code: "FIRST_OPPORTUNITY",
        policy_version: "v0.1-floor-1",
      },
    },
    {
      schema_version: 1,
      type: "floor.intervention_requested",
      session_id: SESSION_ID,
      sequence: 12,
      occurred_at: "2026-08-25T01:04:09Z",
      action_id: null,
      payload: {
        intervention_id: INTERVENTION_ID,
        decision_id: DECISION_ID,
        phase: "EXPLORATION",
        intervention_kind: "SILENCE",
        reason_code: "SILENCE_RECOVERY",
        policy_version: "v0.1-floor-1",
      },
    },
    {
      schema_version: 3,
      type: "floor.released",
      session_id: SESSION_ID,
      sequence: 13,
      occurred_at: "2026-08-25T01:04:10Z",
      action_id: null,
      payload: {
        grant_id: GRANT_ID,
        participant_id: PARTICIPANT_ID,
        phase: "OPENING_STATEMENTS",
        reason_code: "PHASE_CHANGED",
      },
    },
  ])("rejects invalid floor versions and v1 action nullability", (message) => {
    expect(parseRealtimeMessage(JSON.stringify(message))).toBeUndefined();
  });

  it.each([
    "{not-json",
    JSON.stringify({ schema_version: 2 }),
    JSON.stringify({
      schema_version: 1,
      type: "floor.granted",
      session_id: SESSION_ID,
      sequence: 4,
      occurred_at: "2026-08-20T01:04:01Z",
      action_id: ACTION_ID,
      payload: {
        grant_id: GRANT_ID,
        decision_id: DECISION_ID,
        participant_id: PARTICIPANT_ID,
        phase: "OPENING_STATEMENTS",
        opportunity_id: null,
        reason_code: "FIRST_OPPORTUNITY",
        policy_version: "v0.1-floor-1",
        hidden_ranking: [0.9],
      },
    }),
    JSON.stringify({
      schema_version: 1,
      type: "session.created",
      session_id: SESSION_ID,
      sequence: 1,
      occurred_at: "2026-08-16T00:00:00Z",
      action_id: null,
      payload: { status: "CREATED" },
      unexpected: true,
    }),
    JSON.stringify({
      schema_version: 1,
      type: "session.state_changed",
      session_id: SESSION_ID,
      sequence: 0,
      occurred_at: "2026-08-16T00:00:01Z",
      action_id: ACTION_ID,
      payload: { previous_status: "CREATED", status: "ABORTED_USER" },
    }),
    JSON.stringify({
      schema_version: 1,
      type: "session.created",
      session_id: SESSION_ID,
      sequence: 1,
      occurred_at: "not-a-timestamp",
      action_id: null,
      payload: { status: "CREATED" },
    }),
    JSON.stringify({
      schema_version: 1,
      type: "session.state_changed",
      session_id: SESSION_ID,
      sequence: 2,
      occurred_at: "2026-08-16T00:00:01Z",
      action_id: null,
      payload: { previous_status: "CREATED", status: "ABORTED_USER" },
    }),
    JSON.stringify({
      schema_version: 2,
      type: "session.state_changed",
      session_id: SESSION_ID,
      sequence: 2,
      occurred_at: "2026-08-20T01:00:00Z",
      action_id: ACTION_ID,
      payload: {
        previous_status: "CREATED",
        status: "PREPARATION",
        trigger: "USER_START",
        phase_started_at: "2026-08-20T01:00:00Z",
        phase_deadline_at: "2026-08-20T01:04:00Z",
        next_status: "EXPLORATION",
      },
    }),
    JSON.stringify({
      schema_version: 2,
      type: "session.state_changed",
      session_id: SESSION_ID,
      sequence: 3,
      occurred_at: "2026-08-20T01:04:00Z",
      action_id: ACTION_ID,
      payload: {
        previous_status: "PREPARATION",
        status: "OPENING_STATEMENTS",
        trigger: "PHASE_DEADLINE",
        phase_started_at: "2026-08-20T01:04:00Z",
        phase_deadline_at: "2026-08-20T01:08:00Z",
      },
    }),
    JSON.stringify({
      schema_version: 1,
      type: "error",
      session_id: SESSION_ID,
      action_id: ACTION_ID,
      occurred_at: "2026-08-16T00:00:01Z",
      error: {
        code: "SERVER_STACK_TRACE",
        message: "unsafe",
        request_id: REQUEST_ID,
      },
    }),
  ])("rejects malformed, unknown, or semantically invalid data", (raw) => {
    expect(parseRealtimeMessage(raw)).toBeUndefined();
  });
});
