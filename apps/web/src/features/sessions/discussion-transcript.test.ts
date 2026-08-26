import { describe, expect, it } from "vitest";

import type { TranscriptUtterance } from "@/lib/api/client";
import type { ParticipantUtteranceCreatedEvent } from "@/lib/realtime/contract";

import {
  confirmedUtteranceFromEvent,
  mergeConfirmedTranscript,
} from "./discussion-transcript";

const UTTERANCE: TranscriptUtterance = {
  utterance_id: "00000000-0000-4000-8000-000000000021",
  sequence: 5,
  occurred_at: "2026-08-25T01:04:05Z",
  action_id: "00000000-0000-4000-8000-000000000022",
  participant_id: "00000000-0000-4000-8000-000000000023",
  actor_kind: "HUMAN",
  floor_grant_id: "00000000-0000-4000-8000-000000000024",
  phase: "OPENING_STATEMENTS",
  content: "  exact contribution\nsecond line  ",
};

const EVENT: ParticipantUtteranceCreatedEvent = {
  schema_version: 1,
  type: "participant.utterance.created",
  session_id: "00000000-0000-4000-8000-000000000020",
  sequence: UTTERANCE.sequence,
  occurred_at: UTTERANCE.occurred_at,
  action_id: UTTERANCE.action_id,
  payload: {
    utterance_id: UTTERANCE.utterance_id,
    participant_id: UTTERANCE.participant_id,
    actor_kind: UTTERANCE.actor_kind,
    floor_grant_id: UTTERANCE.floor_grant_id,
    phase: UTTERANCE.phase,
    content: UTTERANCE.content,
  },
};

function utterance(
  sequence: number,
  suffix: string,
  overrides: Partial<TranscriptUtterance> = {},
): TranscriptUtterance {
  return {
    ...UTTERANCE,
    utterance_id: `00000000-0000-4000-8000-0000000000${suffix}`,
    sequence,
    ...overrides,
  };
}

describe("confirmed discussion transcript", () => {
  it("converts a formal utterance event to the complete REST transcript shape", () => {
    expect(confirmedUtteranceFromEvent(EVENT)).toEqual(UTTERANCE);
  });

  it("immutably merges new items in authoritative sequence order", () => {
    const atFive = Object.freeze({ ...utterance(5, "21") });
    const atTwelve = Object.freeze({ ...utterance(12, "25") });
    const current = Object.freeze([atTwelve]);
    const incoming = Object.freeze([atFive]);

    expect(mergeConfirmedTranscript([], [atFive])).toEqual({
      kind: "merged",
      items: [atFive],
    });
    expect(mergeConfirmedTranscript(current, incoming)).toEqual({
      kind: "merged",
      items: [atFive, atTwelve],
    });
    expect(mergeConfirmedTranscript([], [atTwelve, atFive])).toEqual({
      kind: "merged",
      items: [atFive, atTwelve],
    });
    expect(current).toEqual([atTwelve]);
    expect(incoming).toEqual([atFive]);
  });

  it("accepts non-contiguous transcript sequences without a gap signal", () => {
    const atFive = utterance(5, "21");
    const atTwelve = utterance(12, "25");
    const atTwentySeven = utterance(27, "26");

    expect(
      mergeConfirmedTranscript([atFive], [atTwentySeven, atTwelve]),
    ).toEqual({
      kind: "merged",
      items: [atFive, atTwelve, atTwentySeven],
    });
  });

  it("dedupes an identical REST item and converted WebSocket replay", () => {
    expect(
      mergeConfirmedTranscript(
        [UTTERANCE],
        [confirmedUtteranceFromEvent(EVENT)],
      ),
    ).toEqual({ kind: "merged", items: [UTTERANCE] });
  });

  it.each([
    ["sequence", 12],
    ["occurred_at", "2026-08-25T01:04:06Z"],
    ["action_id", null],
    ["participant_id", "00000000-0000-4000-8000-000000000031"],
    ["actor_kind", "AI"],
    ["floor_grant_id", "00000000-0000-4000-8000-000000000032"],
    ["phase", "EXPLORATION"],
    ["content", "different content"],
  ] as const)(
    "reports a same-ID conflict when %s differs",
    (field, changedValue) => {
      const conflicting = { ...UTTERANCE, [field]: changedValue };

      expect(mergeConfirmedTranscript([UTTERANCE], [conflicting])).toEqual({
        kind: "conflict",
        utterance_id: UTTERANCE.utterance_id,
      });
    },
  );

  it("dedupes identical duplicate IDs within one incoming array", () => {
    expect(
      mergeConfirmedTranscript([], [{ ...UTTERANCE }, { ...UTTERANCE }]),
    ).toEqual({ kind: "merged", items: [UTTERANCE] });
  });

  it("reports conflicting duplicate IDs within one incoming array", () => {
    expect(
      mergeConfirmedTranscript(
        [],
        [UTTERANCE, { ...UTTERANCE, content: "conflicting replay" }],
      ),
    ).toEqual({
      kind: "conflict",
      utterance_id: UTTERANCE.utterance_id,
    });
  });

  it("uses utterance ID as the deterministic tie-break for equal sequences", () => {
    const laterId = utterance(12, "29");
    const earlierId = utterance(12, "28");

    expect(mergeConfirmedTranscript([], [laterId, earlierId])).toEqual({
      kind: "merged",
      items: [earlierId, laterId],
    });
  });
});
