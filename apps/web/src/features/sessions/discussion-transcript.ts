import type { TranscriptUtterance } from "@/lib/api/client";
import type { ParticipantUtteranceCreatedEvent } from "@/lib/realtime/contract";

export type ConfirmedUtterance = TranscriptUtterance;

export type TranscriptMergeResult =
  | { kind: "merged"; items: ConfirmedUtterance[] }
  | { kind: "conflict"; utterance_id: string };

const AUTHORITATIVE_FIELDS = [
  "utterance_id",
  "sequence",
  "occurred_at",
  "action_id",
  "participant_id",
  "actor_kind",
  "floor_grant_id",
  "phase",
  "content",
] as const;

export function confirmedUtteranceFromEvent(
  event: ParticipantUtteranceCreatedEvent,
): ConfirmedUtterance {
  return {
    utterance_id: event.payload.utterance_id,
    sequence: event.sequence,
    occurred_at: event.occurred_at,
    action_id: event.action_id,
    participant_id: event.payload.participant_id,
    actor_kind: event.payload.actor_kind,
    floor_grant_id: event.payload.floor_grant_id,
    phase: event.payload.phase,
    content: event.payload.content,
  };
}

function isIdenticalUtterance(
  left: ConfirmedUtterance,
  right: ConfirmedUtterance,
) {
  return AUTHORITATIVE_FIELDS.every((field) => left[field] === right[field]);
}

export function mergeConfirmedTranscript(
  current: readonly ConfirmedUtterance[],
  incoming: readonly ConfirmedUtterance[],
): TranscriptMergeResult {
  const byId = new Map<string, ConfirmedUtterance>();

  for (const item of [...current, ...incoming]) {
    const existing = byId.get(item.utterance_id);
    if (existing && !isIdenticalUtterance(existing, item)) {
      return { kind: "conflict", utterance_id: item.utterance_id };
    }
    if (!existing) byId.set(item.utterance_id, item);
  }

  const items = [...byId.values()].sort((left, right) => {
    if (left.sequence !== right.sequence) return left.sequence - right.sequence;
    if (left.utterance_id < right.utterance_id) return -1;
    if (left.utterance_id > right.utterance_id) return 1;
    return 0;
  });
  return { kind: "merged", items };
}
