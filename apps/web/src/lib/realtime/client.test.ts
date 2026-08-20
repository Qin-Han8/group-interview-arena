import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { SessionSnapshot } from "@/lib/api/client";

import { createSessionRealtimeClient } from "./client";

const BASE_URL = "http://localhost:8000";
const SESSION_ID = "00000000-0000-4000-8000-000000000001";
const ACTION_ID = "00000000-0000-4000-8000-000000000002";

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

  it("keeps one action id across reconnect and confirms pending from duplicate replay", async () => {
    const loadSnapshot = vi.fn().mockResolvedValue(ABORTED_SNAPSHOT);
    const onEvent = vi.fn();
    const onPendingChange = vi.fn();
    const client = createSessionRealtimeClient({
      baseUrl: BASE_URL,
      snapshot: CREATED_SNAPSHOT,
      loadSnapshot,
      onEvent,
      onSnapshot: vi.fn(),
      onPendingChange,
      onConnectionChange: vi.fn(),
      onError: vi.fn(),
    });

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

    expect(loadSnapshot).toHaveBeenCalledOnce();
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

  it("sends a user start intent without selecting the next phase", () => {
    const client = createSessionRealtimeClient({
      baseUrl: BASE_URL,
      snapshot: CREATED_SNAPSHOT,
      loadSnapshot: vi.fn().mockResolvedValue(CREATED_SNAPSHOT),
      onEvent: vi.fn(),
      onSnapshot: vi.fn(),
      onPendingChange: vi.fn(),
      onConnectionChange: vi.fn(),
      onError: vi.fn(),
    });

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
    const loadSnapshot = vi.fn().mockResolvedValue(CREATED_SNAPSHOT);
    const client = createSessionRealtimeClient({
      baseUrl: BASE_URL,
      snapshot: CREATED_SNAPSHOT,
      loadSnapshot,
      onEvent: vi.fn(),
      onSnapshot: vi.fn(),
      onPendingChange: vi.fn(),
      onConnectionChange: vi.fn(),
      onError: vi.fn(),
    });

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

    expect(loadSnapshot).toHaveBeenCalledTimes(2);
    expect(FakeWebSocket.instances).toHaveLength(3);
  });

  it("keeps rapid open-close recovery failures within the reconnect limit", async () => {
    const loadSnapshot = vi.fn().mockResolvedValue(CREATED_SNAPSHOT);
    const client = createSessionRealtimeClient({
      baseUrl: BASE_URL,
      snapshot: CREATED_SNAPSHOT,
      loadSnapshot,
      onEvent: vi.fn(),
      onSnapshot: vi.fn(),
      onPendingChange: vi.fn(),
      onConnectionChange: vi.fn(),
      onError: vi.fn(),
    });

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

    expect(loadSnapshot).toHaveBeenCalledOnce();
    expect(FakeWebSocket.instances).toHaveLength(2);
    expect(vi.getTimerCount()).toBe(0);
  });

  it("applies only the strict next sequence, ignores duplicates, and reloads on a gap", async () => {
    const loadSnapshot = vi.fn().mockResolvedValue({
      ...ABORTED_SNAPSHOT,
      last_sequence: 4,
    });
    const onEvent = vi.fn();
    const onSnapshot = vi.fn();
    const client = createSessionRealtimeClient({
      baseUrl: BASE_URL,
      snapshot: CREATED_SNAPSHOT,
      loadSnapshot,
      onEvent,
      onSnapshot,
      onPendingChange: vi.fn(),
      onConnectionChange: vi.fn(),
      onError: vi.fn(),
    });

    client.start();
    const firstSocket = FakeWebSocket.instances[0];
    firstSocket?.open();
    firstSocket?.receive(stateChanged(2));
    firstSocket?.receive(stateChanged(2));
    firstSocket?.receive(stateChanged(4));
    await flushAsync();

    expect(onEvent).toHaveBeenCalledTimes(1);
    expect(onEvent).toHaveBeenCalledWith(stateChanged(2));
    expect(loadSnapshot).toHaveBeenCalledOnce();
    expect(onSnapshot).toHaveBeenCalledWith({
      ...ABORTED_SNAPSHOT,
      last_sequence: 4,
    });
    expect(FakeWebSocket.instances[1]?.url).toContain("after_sequence=4");

    firstSocket?.receive(stateChanged(3));
    expect(onEvent).toHaveBeenCalledTimes(1);
  });

  it("keeps one live socket and ignores stale messages after cleanup", () => {
    const onEvent = vi.fn();
    const client = createSessionRealtimeClient({
      baseUrl: BASE_URL,
      snapshot: CREATED_SNAPSHOT,
      loadSnapshot: vi.fn().mockResolvedValue(CREATED_SNAPSHOT),
      onEvent,
      onSnapshot: vi.fn(),
      onPendingChange: vi.fn(),
      onConnectionChange: vi.fn(),
      onError: vi.fn(),
    });

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
    const client = createSessionRealtimeClient({
      baseUrl: BASE_URL,
      snapshot: CREATED_SNAPSHOT,
      loadSnapshot: vi.fn().mockResolvedValue(CREATED_SNAPSHOT),
      onEvent,
      onSnapshot: vi.fn(),
      onPendingChange: vi.fn(),
      onConnectionChange: vi.fn(),
      onError,
    });

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
