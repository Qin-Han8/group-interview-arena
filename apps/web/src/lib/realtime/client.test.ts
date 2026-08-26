import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { SessionSnapshot, TranscriptUtterance } from "@/lib/api/client";

import {
  createSessionRealtimeClient,
  inspectHumanDraft,
  type SessionRecoveryBundle,
} from "./client";

const BASE_URL = "http://localhost:8000";
const SESSION_ID = "00000000-0000-4000-8000-000000000001";
const ACTION_ID = "00000000-0000-4000-8000-000000000002";
const GRANT_ID = "00000000-0000-4000-8000-000000000003";
const PARTICIPANT_ID = "00000000-0000-4000-8000-000000000004";
const UTTERANCE_ID = "00000000-0000-4000-8000-000000000005";
const SECOND_ACTION_ID = "00000000-0000-4000-8000-000000000006";
const REQUEST_ID = "00000000-0000-4000-8000-000000000007";
const EXACT_CONTENT = "  exact contribution\nsecond line  ";

const CREATED_SNAPSHOT: SessionSnapshot = {
  id: SESSION_ID,
  question_version_id: "21000000-0000-4000-8000-000000000001",
  status: "CREATED",
  phase_started_at: null,
  phase_deadline_at: null,
  server_now: "2026-08-16T00:00:00Z",
  created_at: "2026-08-16T00:00:00Z",
  updated_at: "2026-08-16T00:00:00Z",
  last_sequence: 1,
  floor: {
    participants: [],
    current_grant: null,
    latest_event: null,
  },
};
const ABORTED_SNAPSHOT: SessionSnapshot = {
  ...CREATED_SNAPSHOT,
  status: "ABORTED_USER",
  updated_at: "2026-08-16T00:00:01Z",
  last_sequence: 2,
};

class FakeWebSocket {
  static instances: FakeWebSocket[] = [];

  readonly sent: string[] = [];
  readyState = 0;
  onopen: ((event: Event) => void) | null = null;
  onmessage: ((event: MessageEvent<string>) => void) | null = null;
  onclose: ((event: CloseEvent) => void) | null = null;
  onerror: ((event: Event) => void) | null = null;

  constructor(readonly url: string) {
    FakeWebSocket.instances.push(this);
  }

  open() {
    this.readyState = 1;
    this.onopen?.(new Event("open"));
  }

  receive(payload: object) {
    this.onmessage?.(
      new MessageEvent("message", { data: JSON.stringify(payload) }),
    );
  }

  disconnect() {
    this.readyState = 3;
    this.onclose?.(new CloseEvent("close"));
  }

  send(payload: string) {
    this.sent.push(payload);
  }

  close() {
    this.readyState = 3;
  }
}

function stateChanged(sequence: number, actionId = ACTION_ID) {
  return {
    schema_version: 1,
    type: "session.state_changed",
    session_id: SESSION_ID,
    sequence,
    occurred_at: "2026-08-16T00:00:01Z",
    action_id: actionId,
    payload: { previous_status: "CREATED", status: "ABORTED_USER" },
  };
}

function humanUtterance(sequence: number, actionId = ACTION_ID) {
  return {
    schema_version: 1,
    type: "participant.utterance.created",
    session_id: SESSION_ID,
    sequence,
    occurred_at: "2026-08-25T01:04:05Z",
    action_id: actionId,
    payload: {
      utterance_id: UTTERANCE_ID,
      participant_id: PARTICIPANT_ID,
      actor_kind: "HUMAN",
      floor_grant_id: GRANT_ID,
      phase: "OPENING_STATEMENTS",
      content: EXACT_CONTENT,
    },
  };
}

function matchingTranscript(sequence = 2): TranscriptUtterance {
  return {
    utterance_id: UTTERANCE_ID,
    sequence,
    occurred_at: "2026-08-25T01:04:05Z",
    action_id: ACTION_ID,
    participant_id: PARTICIPANT_ID,
    actor_kind: "HUMAN",
    floor_grant_id: GRANT_ID,
    phase: "OPENING_STATEMENTS",
    content: EXACT_CONTENT,
  };
}

function unmatchedTranscript(sequence = 99): TranscriptUtterance {
  return {
    ...matchingTranscript(sequence),
    utterance_id: "00000000-0000-4000-8000-000000000008",
    action_id: null,
    actor_kind: "AI",
  };
}

function floorReleased(sequence: number, actionId = ACTION_ID) {
  return {
    schema_version: 2,
    type: "floor.released",
    session_id: SESSION_ID,
    sequence,
    occurred_at: "2026-08-25T01:04:06Z",
    action_id: actionId,
    payload: {
      grant_id: GRANT_ID,
      participant_id: PARTICIPANT_ID,
      phase: "OPENING_STATEMENTS",
      reason_code: "SPEAKER_FINISHED",
    },
  };
}

function realtimeError(
  code: "ACTION_ID_CONFLICT" | "SEQUENCE_AHEAD" | "UTTERANCE_REJECTED",
  actionId: string | null = ACTION_ID,
) {
  return {
    schema_version: 1,
    type: "error",
    session_id: SESSION_ID,
    action_id: actionId,
    occurred_at: "2026-08-25T01:04:12Z",
    error: {
      code,
      message: "Safe server message is not rendered directly.",
      request_id: REQUEST_ID,
    },
  };
}

function recoveryBundle(
  snapshot: SessionSnapshot = CREATED_SNAPSHOT,
  transcript: TranscriptUtterance[] = [],
): SessionRecoveryBundle {
  return { snapshot, transcript };
}

type RealtimeOptions = Parameters<typeof createSessionRealtimeClient>[0];

function realtimeOptions(
  overrides: Partial<RealtimeOptions> = {},
): RealtimeOptions {
  return {
    baseUrl: BASE_URL,
    snapshot: CREATED_SNAPSHOT,
    loadRecoveryBundle: vi
      .fn()
      .mockResolvedValue(recoveryBundle(CREATED_SNAPSHOT)),
    onEvent: vi.fn(),
    onRecoveryBundle: vi.fn(),
    onPendingChange: vi.fn(),
    onHumanPendingChange: vi.fn(),
    onRejectedHumanUtterance: vi.fn(),
    onConnectionChange: vi.fn(),
    onError: vi.fn(),
    ...overrides,
  };
}

async function flushAsync() {
  await Promise.resolve();
  await Promise.resolve();
}

describe("session realtime client", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    FakeWebSocket.instances = [];
    vi.stubGlobal("WebSocket", FakeWebSocket);
    vi.spyOn(crypto, "randomUUID").mockReturnValue(ACTION_ID);
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  describe("Human draft inspection", () => {
    it.each([
      ["", 0],
      [" \t\r\n", 4],
      ["\u0085", 1],
      ["\u001c", 1],
    ])("matches server strip-whitespace for %j", (content, count) => {
      expect(inspectHumanDraft(content)).toEqual({
        codePointCount: count,
        isSubmittable: false,
        invalidReason: "EMPTY_OR_WHITESPACE",
      });
    });

    it("treats U+FEFF as content and preserves Python/JavaScript divergence", () => {
      expect(inspectHumanDraft("\ufeff")).toEqual({
        codePointCount: 1,
        isSubmittable: true,
        invalidReason: null,
      });
      expect(inspectHumanDraft("\u0085A\u001c")).toEqual({
        codePointCount: 3,
        isSubmittable: true,
        invalidReason: null,
      });
    });

    it("rejects nulls and counts Unicode code points rather than UTF-16 units", () => {
      expect(inspectHumanDraft("valid\u0000content")).toMatchObject({
        codePointCount: 13,
        isSubmittable: false,
        invalidReason: "CONTAINS_NULL",
      });
      expect(inspectHumanDraft("😀".repeat(4_000))).toEqual({
        codePointCount: 4_000,
        isSubmittable: true,
        invalidReason: null,
      });
      expect(inspectHumanDraft("😀".repeat(4_001))).toEqual({
        codePointCount: 4_001,
        isSubmittable: false,
        invalidReason: "TOO_LONG",
      });
    });

    it("returns inspection facts without returning transformed content", () => {
      const exact = "  e\u0301\n  ";
      const inspection = inspectHumanDraft(exact);
      expect(Object.keys(inspection).sort()).toEqual([
        "codePointCount",
        "invalidReason",
        "isSubmittable",
      ]);
      expect(Object.values(inspection)).not.toContain(exact);
    });
  });

  it("submits one exact Human command and does not mint or send a second", () => {
    vi.mocked(crypto.randomUUID)
      .mockReset()
      .mockReturnValueOnce(ACTION_ID)
      .mockReturnValueOnce(SECOND_ACTION_ID);
    const onPendingChange = vi.fn();
    const onHumanPendingChange = vi.fn();
    const client = createSessionRealtimeClient(
      realtimeOptions({ onPendingChange, onHumanPendingChange }),
    );

    client.start();
    const socket = FakeWebSocket.instances[0];
    socket?.open();

    expect(client.submitHumanUtterance(GRANT_ID, EXACT_CONTENT)).toBe(
      ACTION_ID,
    );
    expect(client.submitHumanUtterance(GRANT_ID, "different content")).toBe(
      ACTION_ID,
    );
    expect(socket?.sent).toHaveLength(1);
    expect(JSON.parse(socket?.sent[0] ?? "{}")).toEqual({
      schema_version: 1,
      type: "participant.utterance.submit",
      session_id: SESSION_ID,
      action_id: ACTION_ID,
      payload: {
        floor_grant_id: GRANT_ID,
        content: EXACT_CONTENT,
      },
    });
    expect(onPendingChange).toHaveBeenCalledExactlyOnceWith(true);
    expect(onHumanPendingChange).toHaveBeenCalledExactlyOnceWith({
      action_id: ACTION_ID,
      floor_grant_id: GRANT_ID,
      content: EXACT_CONTENT,
    });
    expect(crypto.randomUUID).toHaveBeenCalledOnce();
  });

  it.each(["startSession", "abort"] as const)(
    "does not create a Human command while %s is pending",
    (method) => {
      vi.mocked(crypto.randomUUID)
        .mockReset()
        .mockReturnValueOnce(ACTION_ID)
        .mockReturnValueOnce(SECOND_ACTION_ID);
      const onHumanPendingChange = vi.fn();
      const client = createSessionRealtimeClient(
        realtimeOptions({ onHumanPendingChange }),
      );
      client.start();
      const socket = FakeWebSocket.instances[0];
      socket?.open();

      expect(client[method]()).toBe(ACTION_ID);
      expect(client.submitHumanUtterance(GRANT_ID, EXACT_CONTENT)).toBe(
        ACTION_ID,
      );

      expect(socket?.sent).toHaveLength(1);
      expect(JSON.parse(socket?.sent[0] ?? "{}").type).toBe(
        method === "startSession" ? "session.start" : "session.abort",
      );
      expect(onHumanPendingChange).not.toHaveBeenCalled();
      expect(crypto.randomUUID).toHaveBeenCalledOnce();
    },
  );

  it("does not create lifecycle commands while a Human command is pending", () => {
    vi.mocked(crypto.randomUUID)
      .mockReset()
      .mockReturnValueOnce(ACTION_ID)
      .mockReturnValueOnce(SECOND_ACTION_ID);
    const client = createSessionRealtimeClient(realtimeOptions());
    client.start();
    const socket = FakeWebSocket.instances[0];
    socket?.open();

    expect(client.submitHumanUtterance(GRANT_ID, EXACT_CONTENT)).toBe(
      ACTION_ID,
    );
    expect(client.startSession()).toBe(ACTION_ID);
    expect(client.abort()).toBe(ACTION_ID);

    expect(socket?.sent).toHaveLength(1);
    expect(JSON.parse(socket?.sent[0] ?? "{}").type).toBe(
      "participant.utterance.submit",
    );
    expect(crypto.randomUUID).toHaveBeenCalledOnce();
  });

  it("resends the exact Human command and uses only the snapshot recovery cursor", async () => {
    const bundle = recoveryBundle({ ...ABORTED_SNAPSHOT, last_sequence: 10 }, [
      unmatchedTranscript(99),
    ]);
    const loadRecoveryBundle = vi.fn().mockResolvedValue(bundle);
    const onRecoveryBundle = vi.fn();
    const client = createSessionRealtimeClient(
      realtimeOptions({ loadRecoveryBundle, onRecoveryBundle }),
    );

    client.start();
    const firstSocket = FakeWebSocket.instances[0];
    firstSocket?.open();
    client.submitHumanUtterance(GRANT_ID, EXACT_CONTENT);
    const exactFrame = firstSocket?.sent[0];

    firstSocket?.disconnect();
    await vi.runAllTimersAsync();
    await flushAsync();

    expect(loadRecoveryBundle).toHaveBeenCalledOnce();
    expect(onRecoveryBundle).toHaveBeenCalledExactlyOnceWith(bundle);
    const recoveredSocket = FakeWebSocket.instances[1];
    expect(recoveredSocket?.url).toBe(
      `ws://localhost:8000/ws/sessions/${SESSION_ID}?after_sequence=10`,
    );
    recoveredSocket?.open();
    expect(recoveredSocket?.sent).toEqual([exactFrame]);
    expect(JSON.parse(recoveredSocket?.sent[0] ?? "{}")).toEqual(
      JSON.parse(exactFrame ?? "{}"),
    );
    expect(crypto.randomUUID).toHaveBeenCalledOnce();
  });

  it("confirms Human pending only from a matching durable utterance event", () => {
    const onEvent = vi.fn();
    const onPendingChange = vi.fn();
    const onHumanPendingChange = vi.fn();
    const client = createSessionRealtimeClient(
      realtimeOptions({ onEvent, onPendingChange, onHumanPendingChange }),
    );
    client.start();
    const socket = FakeWebSocket.instances[0];
    socket?.open();
    client.submitHumanUtterance(GRANT_ID, EXACT_CONTENT);

    socket?.receive(floorReleased(2));
    expect(onEvent).toHaveBeenCalledExactlyOnceWith(floorReleased(2));
    expect(onPendingChange).toHaveBeenCalledTimes(1);
    expect(onHumanPendingChange).toHaveBeenCalledTimes(1);

    socket?.receive(humanUtterance(3));
    expect(onEvent).toHaveBeenCalledTimes(2);
    expect(onPendingChange.mock.calls).toEqual([[true], [false]]);
    expect(onHumanPendingChange.mock.calls).toEqual([
      [
        {
          action_id: ACTION_ID,
          floor_grant_id: GRANT_ID,
          content: EXACT_CONTENT,
        },
      ],
      [undefined],
    ]);
  });

  it("allows a duplicate matching utterance replay to confirm without emitting it", () => {
    const onEvent = vi.fn();
    const onPendingChange = vi.fn();
    const client = createSessionRealtimeClient(
      realtimeOptions({ onEvent, onPendingChange }),
    );
    client.start();
    const socket = FakeWebSocket.instances[0];
    socket?.open();
    client.submitHumanUtterance(GRANT_ID, EXACT_CONTENT);

    socket?.receive(humanUtterance(1));

    expect(onEvent).not.toHaveBeenCalled();
    expect(onPendingChange.mock.calls).toEqual([[true], [false]]);
  });

  it("clears Human pending from a matching recovered transcript before reconnect", async () => {
    const bundle = recoveryBundle({ ...ABORTED_SNAPSHOT, last_sequence: 10 }, [
      matchingTranscript(99),
    ]);
    const onPendingChange = vi.fn();
    const onHumanPendingChange = vi.fn();
    const onRecoveryBundle = vi.fn();
    const client = createSessionRealtimeClient(
      realtimeOptions({
        loadRecoveryBundle: vi.fn().mockResolvedValue(bundle),
        onPendingChange,
        onHumanPendingChange,
        onRecoveryBundle,
      }),
    );
    client.start();
    const firstSocket = FakeWebSocket.instances[0];
    firstSocket?.open();
    client.submitHumanUtterance(GRANT_ID, EXACT_CONTENT);

    firstSocket?.disconnect();
    await vi.runAllTimersAsync();
    await flushAsync();

    expect(onPendingChange.mock.calls).toEqual([[true], [false]]);
    expect(onHumanPendingChange).toHaveBeenLastCalledWith(undefined);
    expect(onRecoveryBundle).toHaveBeenCalledExactlyOnceWith(bundle);
    const recoveredSocket = FakeWebSocket.instances[1];
    expect(recoveredSocket?.url).toContain("after_sequence=10");
    recoveredSocket?.open();
    expect(recoveredSocket?.sent).toEqual([]);
  });

  it("keeps UTTERANCE_REJECTED recoverable and preserves exact rejected content", () => {
    vi.mocked(crypto.randomUUID)
      .mockReset()
      .mockReturnValueOnce(ACTION_ID)
      .mockReturnValueOnce(SECOND_ACTION_ID);
    const loadRecoveryBundle = vi.fn();
    const onEvent = vi.fn();
    const onPendingChange = vi.fn();
    const onHumanPendingChange = vi.fn();
    const onRejectedHumanUtterance = vi.fn();
    const onError = vi.fn();
    const client = createSessionRealtimeClient(
      realtimeOptions({
        loadRecoveryBundle,
        onEvent,
        onPendingChange,
        onHumanPendingChange,
        onRejectedHumanUtterance,
        onError,
      }),
    );
    client.start();
    const socket = FakeWebSocket.instances[0];
    socket?.open();
    client.submitHumanUtterance(GRANT_ID, EXACT_CONTENT);

    socket?.receive(realtimeError("UTTERANCE_REJECTED"));

    expect(onPendingChange.mock.calls).toEqual([[true], [false]]);
    expect(onHumanPendingChange).toHaveBeenLastCalledWith(undefined);
    expect(onRejectedHumanUtterance).toHaveBeenCalledExactlyOnceWith({
      action_id: ACTION_ID,
      floor_grant_id: GRANT_ID,
      content: EXACT_CONTENT,
      reason: "UTTERANCE_REJECTED",
    });
    expect(onEvent).not.toHaveBeenCalled();
    expect(onError).not.toHaveBeenCalled();
    expect(loadRecoveryBundle).not.toHaveBeenCalled();
    expect(socket?.readyState).toBe(1);
    expect(FakeWebSocket.instances).toHaveLength(1);

    expect(client.startSession()).toBe(SECOND_ACTION_ID);
    expect(JSON.parse(socket?.sent[1] ?? "{}").type).toBe("session.start");
    expect(crypto.randomUUID).toHaveBeenCalledTimes(2);
  });

  it("rejects ACTION_ID_CONFLICT without replacement and enters one authoritative recovery", async () => {
    vi.mocked(crypto.randomUUID)
      .mockReset()
      .mockReturnValueOnce(ACTION_ID)
      .mockReturnValueOnce(SECOND_ACTION_ID);
    const bundle = recoveryBundle({ ...CREATED_SNAPSHOT, last_sequence: 8 });
    const loadRecoveryBundle = vi.fn().mockResolvedValue(bundle);
    const onRejectedHumanUtterance = vi.fn();
    const onRecoveryBundle = vi.fn();
    const client = createSessionRealtimeClient(
      realtimeOptions({
        loadRecoveryBundle,
        onRejectedHumanUtterance,
        onRecoveryBundle,
      }),
    );
    client.start();
    const firstSocket = FakeWebSocket.instances[0];
    firstSocket?.open();
    client.submitHumanUtterance(GRANT_ID, EXACT_CONTENT);

    firstSocket?.receive(realtimeError("ACTION_ID_CONFLICT"));
    firstSocket?.receive(realtimeError("ACTION_ID_CONFLICT"));
    await flushAsync();

    expect(onRejectedHumanUtterance).toHaveBeenCalledExactlyOnceWith({
      action_id: ACTION_ID,
      floor_grant_id: GRANT_ID,
      content: EXACT_CONTENT,
      reason: "ACTION_ID_CONFLICT",
    });
    expect(loadRecoveryBundle).toHaveBeenCalledOnce();
    expect(onRecoveryBundle).toHaveBeenCalledExactlyOnceWith(bundle);
    expect(crypto.randomUUID).toHaveBeenCalledOnce();
    const recoveredSocket = FakeWebSocket.instances[1];
    expect(recoveredSocket?.url).toContain("after_sequence=8");
    recoveredSocket?.open();
    expect(recoveredSocket?.sent).toEqual([]);
  });

  it.each([
    ["rejected loader", () => Promise.reject(new Error("API unavailable"))],
    [
      "wrong-session bundle",
      () =>
        Promise.resolve(
          recoveryBundle({
            ...CREATED_SNAPSHOT,
            id: "00000000-0000-4000-8000-000000000099",
          }),
        ),
    ],
  ])("publishes no partial bundle for a %s", async (_label, loader) => {
    const onRecoveryBundle = vi.fn();
    const client = createSessionRealtimeClient(
      realtimeOptions({
        loadRecoveryBundle: vi.fn(loader),
        onRecoveryBundle,
      }),
    );
    client.start();
    const socket = FakeWebSocket.instances[0];
    socket?.open();

    client.recoverAuthoritativeState();
    await flushAsync();

    expect(onRecoveryBundle).not.toHaveBeenCalled();
    expect(FakeWebSocket.instances).toHaveLength(1);
  });

  it("preserves Human pending and the prior cursor when canonical bundle loading rejects", async () => {
    const invalidBundle = recoveryBundle(
      { ...ABORTED_SNAPSHOT, last_sequence: 99 },
      [
        matchingTranscript(99),
        { ...matchingTranscript(99), content: "conflicting content" },
      ],
    );
    const invalidSnapshotWatermark = invalidBundle.snapshot.last_sequence;
    const validBundle = recoveryBundle(
      { ...ABORTED_SNAPSHOT, last_sequence: 2 },
      [unmatchedTranscript(98)],
    );
    const loadRecoveryBundle = vi
      .fn()
      .mockImplementationOnce(async () => {
        if (invalidBundle.transcript.length > 1) {
          throw new Error("Authoritative transcript identity conflict");
        }
        return invalidBundle;
      })
      .mockResolvedValueOnce(validBundle);
    const onPendingChange = vi.fn();
    const onHumanPendingChange = vi.fn();
    const onRecoveryBundle = vi.fn();
    const client = createSessionRealtimeClient(
      realtimeOptions({
        loadRecoveryBundle,
        onPendingChange,
        onHumanPendingChange,
        onRecoveryBundle,
      }),
    );
    client.start();
    const firstSocket = FakeWebSocket.instances[0];
    firstSocket?.open();
    client.submitHumanUtterance(GRANT_ID, EXACT_CONTENT);
    const exactFrame = firstSocket?.sent[0];

    client.recoverAuthoritativeState();
    await flushAsync();

    expect(loadRecoveryBundle).toHaveBeenCalledOnce();
    expect(onRecoveryBundle).not.toHaveBeenCalled();
    expect(onPendingChange.mock.calls).toEqual([[true]]);
    expect(onHumanPendingChange).toHaveBeenCalledExactlyOnceWith({
      action_id: ACTION_ID,
      floor_grant_id: GRANT_ID,
      content: EXACT_CONTENT,
    });
    expect(FakeWebSocket.instances).toHaveLength(1);
    expect(
      FakeWebSocket.instances.some((socket) =>
        socket.url.includes(
          `after_sequence=${invalidSnapshotWatermark.toString()}`,
        ),
      ),
    ).toBe(false);

    await vi.advanceTimersByTimeAsync(250);
    await flushAsync();

    expect(loadRecoveryBundle).toHaveBeenCalledTimes(2);
    expect(onRecoveryBundle).toHaveBeenCalledExactlyOnceWith(validBundle);
    expect(onPendingChange.mock.calls).toEqual([[true]]);
    const recoveredSocket = FakeWebSocket.instances[1];
    expect(recoveredSocket?.url).toContain("after_sequence=2");
    expect(recoveredSocket?.url).not.toContain(
      `after_sequence=${invalidSnapshotWatermark.toString()}`,
    );
    recoveredSocket?.open();
    expect(recoveredSocket?.sent).toEqual([exactFrame]);
  });

  it("uses the shared guarded recovery path for an explicit recovery trigger", async () => {
    let resolveBundle!: (bundle: SessionRecoveryBundle) => void;
    const pendingBundle = new Promise<SessionRecoveryBundle>((resolve) => {
      resolveBundle = resolve;
    });
    const bundle = recoveryBundle({ ...CREATED_SNAPSHOT, last_sequence: 7 });
    const loadRecoveryBundle = vi.fn().mockReturnValue(pendingBundle);
    const onRecoveryBundle = vi.fn();
    const client = createSessionRealtimeClient(
      realtimeOptions({ loadRecoveryBundle, onRecoveryBundle }),
    );
    client.start();
    FakeWebSocket.instances[0]?.open();

    client.recoverAuthoritativeState();
    client.recoverAuthoritativeState();
    expect(loadRecoveryBundle).toHaveBeenCalledOnce();

    resolveBundle(bundle);
    await flushAsync();

    expect(onRecoveryBundle).toHaveBeenCalledExactlyOnceWith(bundle);
    expect(FakeWebSocket.instances[1]?.url).toContain("after_sequence=7");
  });

  it("keeps one action id across reconnect and confirms lifecycle pending from duplicate replay", async () => {
    const loadRecoveryBundle = vi
      .fn()
      .mockResolvedValue(recoveryBundle(ABORTED_SNAPSHOT));
    const onEvent = vi.fn();
    const onPendingChange = vi.fn();
    const client = createSessionRealtimeClient(
      realtimeOptions({ loadRecoveryBundle, onEvent, onPendingChange }),
    );

    client.start();
    const firstSocket = FakeWebSocket.instances[0];
    expect(firstSocket?.url).toBe(
      `ws://localhost:8000/ws/sessions/${SESSION_ID}?after_sequence=1`,
    );
    firstSocket?.open();

    expect(client.abort()).toBe(ACTION_ID);
    expect(JSON.parse(firstSocket?.sent[0] ?? "{}")).toEqual({
      schema_version: 1,
      type: "session.abort",
      session_id: SESSION_ID,
      action_id: ACTION_ID,
      payload: {},
    });

    firstSocket?.disconnect();
    await vi.runAllTimersAsync();
    await flushAsync();

    expect(loadRecoveryBundle).toHaveBeenCalledOnce();
    const secondSocket = FakeWebSocket.instances[1];
    expect(secondSocket?.url).toBe(
      `ws://localhost:8000/ws/sessions/${SESSION_ID}?after_sequence=2`,
    );
    secondSocket?.open();
    expect(secondSocket?.sent).toEqual(firstSocket?.sent);

    secondSocket?.receive(stateChanged(2));
    expect(onEvent).not.toHaveBeenCalled();
    expect(onPendingChange.mock.calls).toEqual([[true], [false]]);
    expect(crypto.randomUUID).toHaveBeenCalledOnce();
  });

  it("confirms lifecycle Start pending from its matching next event", () => {
    const onPendingChange = vi.fn();
    const client = createSessionRealtimeClient(
      realtimeOptions({ onPendingChange }),
    );
    client.start();
    const socket = FakeWebSocket.instances[0];
    socket?.open();

    client.startSession();
    socket?.receive(stateChanged(2));

    expect(onPendingChange.mock.calls).toEqual([[true], [false]]);
  });

  it("sends a user start intent without selecting the next phase", () => {
    const client = createSessionRealtimeClient(realtimeOptions());

    client.start();
    const socket = FakeWebSocket.instances[0];
    socket?.open();

    expect(client.startSession()).toBe(ACTION_ID);
    expect(JSON.parse(socket?.sent[0] ?? "{}")).toEqual({
      schema_version: 1,
      type: "session.start",
      session_id: SESSION_ID,
      action_id: ACTION_ID,
      payload: {},
    });
    expect(socket?.sent[0]).not.toContain("next_status");
    expect(socket?.sent[0]).not.toContain("phase_deadline_at");
  });

  it("renews the bounded reconnect budget after a recovered socket stays healthy without events", async () => {
    const loadRecoveryBundle = vi
      .fn()
      .mockResolvedValue(recoveryBundle(CREATED_SNAPSHOT));
    const client = createSessionRealtimeClient(
      realtimeOptions({ loadRecoveryBundle }),
    );

    client.start();
    const firstSocket = FakeWebSocket.instances[0];
    firstSocket?.open();
    firstSocket?.disconnect();
    await vi.runAllTimersAsync();
    await flushAsync();

    const recoveredSocket = FakeWebSocket.instances[1];
    recoveredSocket?.open();
    await vi.runAllTimersAsync();
    recoveredSocket?.disconnect();
    await vi.runAllTimersAsync();
    await flushAsync();

    expect(loadRecoveryBundle).toHaveBeenCalledTimes(2);
    expect(FakeWebSocket.instances).toHaveLength(3);
  });

  it("keeps rapid open-close recovery failures within the reconnect limit", async () => {
    const loadRecoveryBundle = vi
      .fn()
      .mockResolvedValue(recoveryBundle(CREATED_SNAPSHOT));
    const client = createSessionRealtimeClient(
      realtimeOptions({ loadRecoveryBundle }),
    );

    client.start();
    const firstSocket = FakeWebSocket.instances[0];
    firstSocket?.open();
    firstSocket?.disconnect();
    await vi.runAllTimersAsync();
    await flushAsync();

    const unstableRecovery = FakeWebSocket.instances[1];
    unstableRecovery?.open();
    unstableRecovery?.disconnect();
    await vi.runAllTimersAsync();
    await flushAsync();

    expect(loadRecoveryBundle).toHaveBeenCalledTimes(2);
    expect(FakeWebSocket.instances).toHaveLength(3);
    expect(vi.getTimerCount()).toBe(0);
  });

  it("retries failed bundle recovery with bounded backoff and replays pending intent", async () => {
    const loadRecoveryBundle = vi
      .fn()
      .mockRejectedValueOnce(new Error("API restarting"))
      .mockRejectedValueOnce(new Error("API still restarting"))
      .mockResolvedValue(recoveryBundle(ABORTED_SNAPSHOT));
    const onRecoveryBundle = vi.fn();
    const onPendingChange = vi.fn();
    const client = createSessionRealtimeClient(
      realtimeOptions({
        loadRecoveryBundle,
        onRecoveryBundle,
        onPendingChange,
      }),
    );

    client.start();
    const firstSocket = FakeWebSocket.instances[0];
    firstSocket?.open();
    client.startSession();
    firstSocket?.disconnect();
    await vi.runAllTimersAsync();
    await flushAsync();

    expect(loadRecoveryBundle).toHaveBeenCalledTimes(3);
    expect(onRecoveryBundle).toHaveBeenCalledWith(
      recoveryBundle(ABORTED_SNAPSHOT),
    );
    const recoveredSocket = FakeWebSocket.instances[1];
    recoveredSocket?.open();
    expect(recoveredSocket?.sent).toEqual(firstSocket?.sent);
    recoveredSocket?.receive(stateChanged(2));
    expect(onPendingChange.mock.calls).toEqual([[true], [false]]);
  });

  it("stops retrying after the bounded bundle recovery budget is exhausted", async () => {
    const loadRecoveryBundle = vi
      .fn()
      .mockRejectedValue(new Error("API unavailable"));
    const client = createSessionRealtimeClient(
      realtimeOptions({ loadRecoveryBundle }),
    );

    client.start();
    const firstSocket = FakeWebSocket.instances[0];
    firstSocket?.open();
    firstSocket?.disconnect();
    await vi.runAllTimersAsync();
    await flushAsync();

    expect(loadRecoveryBundle).toHaveBeenCalledTimes(5);
    expect(FakeWebSocket.instances).toHaveLength(1);
    expect(vi.getTimerCount()).toBe(0);
  });

  it("applies only the strict next sequence, ignores duplicates, and reloads on a gap", async () => {
    const bundle = recoveryBundle({
      ...ABORTED_SNAPSHOT,
      last_sequence: 4,
    });
    const loadRecoveryBundle = vi.fn().mockResolvedValue(bundle);
    const onEvent = vi.fn();
    const onRecoveryBundle = vi.fn();
    const client = createSessionRealtimeClient(
      realtimeOptions({ loadRecoveryBundle, onEvent, onRecoveryBundle }),
    );

    client.start();
    const firstSocket = FakeWebSocket.instances[0];
    firstSocket?.open();
    firstSocket?.receive(stateChanged(2));
    firstSocket?.receive(stateChanged(2));
    firstSocket?.receive(stateChanged(4));
    await flushAsync();

    expect(onEvent).toHaveBeenCalledTimes(1);
    expect(onEvent).toHaveBeenCalledWith(stateChanged(2));
    expect(loadRecoveryBundle).toHaveBeenCalledOnce();
    expect(onRecoveryBundle).toHaveBeenCalledWith(bundle);
    expect(FakeWebSocket.instances[1]?.url).toContain("after_sequence=4");

    firstSocket?.receive(stateChanged(3));
    expect(onEvent).toHaveBeenCalledTimes(1);
  });

  it("keeps one live socket and ignores stale messages after cleanup", () => {
    const onEvent = vi.fn();
    const client = createSessionRealtimeClient(realtimeOptions({ onEvent }));

    client.start();
    client.start();
    expect(FakeWebSocket.instances).toHaveLength(1);
    const socket = FakeWebSocket.instances[0];
    socket?.open();

    client.stop();
    expect(socket?.readyState).toBe(3);
    socket?.receive(stateChanged(2));
    expect(onEvent).not.toHaveBeenCalled();
  });

  it("rejects invalid server data without applying it", () => {
    const onEvent = vi.fn();
    const onError = vi.fn();
    const client = createSessionRealtimeClient(
      realtimeOptions({ onEvent, onError }),
    );

    client.start();
    const socket = FakeWebSocket.instances[0];
    socket?.open();
    socket?.onmessage?.(
      new MessageEvent("message", { data: "attacker-controlled-invalid" }),
    );

    expect(onEvent).not.toHaveBeenCalled();
    expect(onError).toHaveBeenCalledWith(
      "实时连接返回了无法识别的数据，请重新加载会话。",
    );
  });
});
