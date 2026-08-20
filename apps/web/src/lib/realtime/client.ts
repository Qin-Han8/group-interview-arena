import type { SessionSnapshot } from "@/lib/api/client";

import {
  parseRealtimeMessage,
  type FormalSessionEvent,
  type RealtimeErrorCode,
  type SessionAbortCommand,
  type SessionStartCommand,
} from "./contract";

export type RealtimeConnectionState =
  "connecting" | "connected" | "reconnecting" | "disconnected";

type SessionRealtimeOptions = {
  baseUrl: string;
  snapshot: SessionSnapshot;
  loadSnapshot: () => Promise<SessionSnapshot>;
  onEvent: (event: FormalSessionEvent) => void;
  onSnapshot: (snapshot: SessionSnapshot) => void;
  onPendingChange: (pending: boolean) => void;
  onConnectionChange: (state: RealtimeConnectionState) => void;
  onError: (message: string) => void;
};

export type SessionRealtimeClient = {
  start: () => void;
  startSession: () => string;
  abort: () => string;
  stop: () => void;
};

type PendingCommand = SessionAbortCommand | SessionStartCommand;

const SOCKET_OPEN = 1;
const RECONNECT_DELAY_MS = 250;
const MAX_RECONNECT_ATTEMPTS = 1;
const RECOVERY_STABILITY_MS = 1_000;

const SAFE_ERROR_MESSAGES: Record<RealtimeErrorCode, string> = {
  INVALID_SESSION_STATE: "当前会话状态不接受这个操作，请重新加载会话。",
  ACTION_ID_CONFLICT: "操作标识发生冲突，请重新加载会话。",
  PROTOCOL_ERROR: "实时连接协议错误，请重新加载会话。",
  SEQUENCE_AHEAD: "会话历史需要重新加载。",
  INTERNAL_ERROR: "实时连接暂时不可用，请稍后重试。",
};

function websocketUrl(
  baseUrl: string,
  sessionId: string,
  afterSequence: number,
) {
  const url = new URL(baseUrl);
  url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
  url.pathname = `/ws/sessions/${encodeURIComponent(sessionId)}`;
  url.search = new URLSearchParams({
    after_sequence: String(afterSequence),
  }).toString();
  url.hash = "";
  return url.toString();
}

export function createSessionRealtimeClient(
  options: SessionRealtimeOptions,
): SessionRealtimeClient {
  const sessionId = options.snapshot.id;
  let active = false;
  let generation = 0;
  let socket: WebSocket | undefined;
  let lastSequence = options.snapshot.last_sequence;
  let pendingCommand: PendingCommand | undefined;
  let reconnectAttempts = 0;
  let reconnectTimer: ReturnType<typeof setTimeout> | undefined;
  let recoveryStabilityTimer: ReturnType<typeof setTimeout> | undefined;
  let reloading = false;

  function isCurrent(candidate: WebSocket, candidateGeneration: number) {
    return active && socket === candidate && generation === candidateGeneration;
  }

  function clearPending() {
    if (!pendingCommand) return;
    pendingCommand = undefined;
    options.onPendingChange(false);
  }

  function sendPending(candidate: WebSocket) {
    if (candidate.readyState === SOCKET_OPEN && pendingCommand) {
      candidate.send(JSON.stringify(pendingCommand));
    }
  }

  function clearRecoveryStabilityTimer() {
    if (recoveryStabilityTimer) clearTimeout(recoveryStabilityTimer);
    recoveryStabilityTimer = undefined;
  }

  function markRecoveredConnectionHealthy(
    candidate: WebSocket,
    candidateGeneration: number,
  ) {
    if (reconnectAttempts === 0) return;
    clearRecoveryStabilityTimer();
    recoveryStabilityTimer = setTimeout(() => {
      recoveryStabilityTimer = undefined;
      if (isCurrent(candidate, candidateGeneration)) reconnectAttempts = 0;
    }, RECOVERY_STABILITY_MS);
  }

  function connect() {
    if (!active) return;
    generation += 1;
    const candidateGeneration = generation;
    const candidate = new WebSocket(
      websocketUrl(options.baseUrl, sessionId, lastSequence),
    );
    socket = candidate;
    options.onConnectionChange("connecting");

    candidate.onopen = () => {
      if (!isCurrent(candidate, candidateGeneration)) {
        candidate.close();
        return;
      }
      options.onConnectionChange("connected");
      sendPending(candidate);
      markRecoveredConnectionHealthy(candidate, candidateGeneration);
    };

    candidate.onmessage = (message) => {
      if (!isCurrent(candidate, candidateGeneration)) return;
      if (typeof message.data !== "string") {
        options.onError("实时连接返回了无法识别的数据，请重新加载会话。");
        candidate.close();
        return;
      }

      const parsed = parseRealtimeMessage(message.data);
      if (!parsed || parsed.session_id !== sessionId) {
        options.onError("实时连接返回了无法识别的数据，请重新加载会话。");
        candidate.close();
        return;
      }

      if (parsed.type === "error") {
        options.onError(SAFE_ERROR_MESSAGES[parsed.error.code]);
        if (parsed.error.code === "SEQUENCE_AHEAD") {
          void reloadSnapshotAndReconnect(candidateGeneration);
          return;
        }
        if (
          parsed.action_id === pendingCommand?.action_id &&
          (parsed.error.code === "INVALID_SESSION_STATE" ||
            parsed.error.code === "ACTION_ID_CONFLICT")
        ) {
          clearPending();
        }
        return;
      }

      if (parsed.sequence <= lastSequence) {
        if (parsed.action_id === pendingCommand?.action_id) clearPending();
        return;
      }

      if (parsed.sequence !== lastSequence + 1) {
        void reloadSnapshotAndReconnect(candidateGeneration);
        return;
      }

      lastSequence = parsed.sequence;
      reconnectAttempts = 0;
      clearRecoveryStabilityTimer();
      options.onEvent(parsed);
      if (parsed.action_id === pendingCommand?.action_id) clearPending();
    };

    candidate.onerror = () => {
      if (isCurrent(candidate, candidateGeneration)) {
        options.onError("实时连接暂时不可用，请稍后重试。");
      }
    };

    candidate.onclose = () => {
      if (!isCurrent(candidate, candidateGeneration)) return;
      clearRecoveryStabilityTimer();
      options.onConnectionChange("disconnected");
      scheduleReconnect(candidateGeneration);
    };
  }

  async function reloadSnapshotAndReconnect(expectedGeneration: number) {
    if (!active || reloading || generation !== expectedGeneration) return;
    reloading = true;
    clearRecoveryStabilityTimer();
    generation += 1;
    socket?.close();
    socket = undefined;
    options.onConnectionChange("reconnecting");

    try {
      const snapshot = await options.loadSnapshot();
      if (!active || snapshot.id !== sessionId) return;
      lastSequence = snapshot.last_sequence;
      options.onSnapshot(snapshot);
      connect();
    } catch {
      if (active) {
        options.onConnectionChange("disconnected");
        options.onError("无法重新加载会话，请稍后重试。");
      }
    } finally {
      reloading = false;
    }
  }

  function scheduleReconnect(expectedGeneration: number) {
    if (!active || reconnectAttempts >= MAX_RECONNECT_ATTEMPTS) return;
    reconnectAttempts += 1;
    reconnectTimer = setTimeout(() => {
      reconnectTimer = undefined;
      void reloadSnapshotAndReconnect(expectedGeneration);
    }, RECONNECT_DELAY_MS);
  }

  return {
    start() {
      if (active) return;
      active = true;
      connect();
    },
    startSession() {
      if (!pendingCommand) {
        pendingCommand = {
          schema_version: 1,
          type: "session.start",
          session_id: sessionId,
          action_id: crypto.randomUUID(),
          payload: {},
        };
        options.onPendingChange(true);
      }
      if (socket) sendPending(socket);
      return pendingCommand.action_id;
    },
    abort() {
      if (!pendingCommand) {
        pendingCommand = {
          schema_version: 1,
          type: "session.abort",
          session_id: sessionId,
          action_id: crypto.randomUUID(),
          payload: {},
        };
        options.onPendingChange(true);
      }
      if (socket) sendPending(socket);
      return pendingCommand.action_id;
    },
    stop() {
      if (!active) return;
      active = false;
      generation += 1;
      if (reconnectTimer) clearTimeout(reconnectTimer);
      reconnectTimer = undefined;
      clearRecoveryStabilityTimer();
      socket?.close();
      socket = undefined;
      options.onConnectionChange("disconnected");
    },
  };
}
