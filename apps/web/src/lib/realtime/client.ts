import type { SessionSnapshot, TranscriptUtterance } from "@/lib/api/client";

import {
  parseRealtimeMessage,
  type FormalSessionEvent,
  type ParticipantUtteranceSubmitCommand,
  type RealtimeErrorCode,
  type SessionAbortCommand,
  type SessionStartCommand,
} from "./contract";

export type RealtimeConnectionState =
  "connecting" | "connected" | "reconnecting" | "disconnected";

type SessionRealtimeOptions = {
  baseUrl: string;
  snapshot: SessionSnapshot;
  loadRecoveryBundle: () => Promise<SessionRecoveryBundle>;
  onEvent: (event: FormalSessionEvent) => void;
  onRecoveryBundle: (bundle: SessionRecoveryBundle) => void;
  onPendingChange: (pending: boolean) => void;
  onHumanPendingChange: (pending: PendingHumanUtterance | undefined) => void;
  onRejectedHumanUtterance: (rejected: RejectedHumanUtterance) => void;
  onConnectionChange: (state: RealtimeConnectionState) => void;
  onError: (message: string) => void;
};

export type PendingHumanUtterance = {
  action_id: string;
  floor_grant_id: string;
  content: string;
};

export type RejectedHumanUtterance = PendingHumanUtterance & {
  reason: "ACTION_ID_CONFLICT" | "UTTERANCE_REJECTED";
};

export type SessionRecoveryBundle = {
  snapshot: SessionSnapshot;
  transcript: TranscriptUtterance[];
};

export type HumanDraftInvalidReason =
  "EMPTY_OR_WHITESPACE" | "CONTAINS_NULL" | "TOO_LONG";

export type HumanDraftInspection = {
  codePointCount: number;
  isSubmittable: boolean;
  invalidReason: HumanDraftInvalidReason | null;
};

function isPythonStripWhitespace(character: string): boolean {
  const codePoint = character.codePointAt(0);
  if (codePoint === undefined) return false;
  return (
    (codePoint >= 0x0009 && codePoint <= 0x000d) ||
    (codePoint >= 0x001c && codePoint <= 0x0020) ||
    codePoint === 0x0085 ||
    codePoint === 0x00a0 ||
    codePoint === 0x1680 ||
    (codePoint >= 0x2000 && codePoint <= 0x200a) ||
    codePoint === 0x2028 ||
    codePoint === 0x2029 ||
    codePoint === 0x202f ||
    codePoint === 0x205f ||
    codePoint === 0x3000
  );
}

function hasPythonStripContent(content: string): boolean {
  for (const character of content) {
    if (!isPythonStripWhitespace(character)) return true;
  }
  return false;
}

export function inspectHumanDraft(content: string): HumanDraftInspection {
  const codePointCount = Array.from(content).length;

  let invalidReason: HumanDraftInvalidReason | null = null;
  if (!hasPythonStripContent(content)) {
    invalidReason = "EMPTY_OR_WHITESPACE";
  } else if (content.includes("\u0000")) {
    invalidReason = "CONTAINS_NULL";
  } else if (codePointCount > 4_000) {
    invalidReason = "TOO_LONG";
  }

  return {
    codePointCount,
    isSubmittable: invalidReason === null,
    invalidReason,
  };
}

export type SessionRealtimeClient = {
  start: () => void;
  startSession: () => string;
  abort: () => string;
  submitHumanUtterance: (floorGrantId: string, exactContent: string) => string;
  recoverAuthoritativeState: () => void;
  stop: () => void;
};

type PendingCommand =
  SessionAbortCommand | SessionStartCommand | ParticipantUtteranceSubmitCommand;

const SOCKET_OPEN = 1;
const RECONNECT_DELAY_MS = 250;
const MAX_RECONNECT_ATTEMPTS = 5;
const RECOVERY_STABILITY_MS = 1_000;

const SAFE_ERROR_MESSAGES: Record<RealtimeErrorCode, string> = {
  INVALID_SESSION_STATE: "当前会话状态不接受这个操作，请重新加载会话。",
  ACTION_ID_CONFLICT: "操作标识发生冲突，请重新加载会话。",
  PROTOCOL_ERROR: "实时连接协议错误，请重新加载会话。",
  SEQUENCE_AHEAD: "会话历史需要重新加载。",
  INTERNAL_ERROR: "实时连接暂时不可用，请稍后重试。",
  UTTERANCE_REJECTED: "这条发言当前无法提交，请确认发言机会后重试。",
};

function confirmsPending(
  pending: PendingCommand,
  event: FormalSessionEvent,
): boolean {
  if (pending.type === "participant.utterance.submit") {
    return (
      event.type === "participant.utterance.created" &&
      event.action_id === pending.action_id
    );
  }
  return event.action_id === pending.action_id;
}

function humanPendingFromCommand(
  command: ParticipantUtteranceSubmitCommand,
): PendingHumanUtterance {
  return {
    action_id: command.action_id,
    floor_grant_id: command.payload.floor_grant_id,
    content: command.payload.content,
  };
}

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
    const cleared = pendingCommand;
    pendingCommand = undefined;
    if (cleared.type === "participant.utterance.submit") {
      options.onHumanPendingChange(undefined);
    }
    options.onPendingChange(false);
  }

  function rejectPendingHuman(reason: RejectedHumanUtterance["reason"]) {
    if (pendingCommand?.type !== "participant.utterance.submit") return false;
    const rejected = humanPendingFromCommand(pendingCommand);
    clearPending();
    options.onRejectedHumanUtterance({ ...rejected, reason });
    return true;
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
        const matchesPending =
          parsed.action_id !== null &&
          parsed.action_id === pendingCommand?.action_id;
        if (
          matchesPending &&
          parsed.error.code === "UTTERANCE_REJECTED" &&
          pendingCommand?.type === "participant.utterance.submit"
        ) {
          rejectPendingHuman("UTTERANCE_REJECTED");
          return;
        }

        options.onError(SAFE_ERROR_MESSAGES[parsed.error.code]);
        if (parsed.error.code === "SEQUENCE_AHEAD") {
          void recoverAndReconnect(candidateGeneration);
          return;
        }
        if (
          matchesPending &&
          parsed.error.code === "ACTION_ID_CONFLICT" &&
          pendingCommand?.type === "participant.utterance.submit"
        ) {
          rejectPendingHuman("ACTION_ID_CONFLICT");
          void recoverAndReconnect(candidateGeneration);
          return;
        }
        if (
          matchesPending &&
          pendingCommand?.type !== "participant.utterance.submit" &&
          (parsed.error.code === "INVALID_SESSION_STATE" ||
            parsed.error.code === "ACTION_ID_CONFLICT")
        ) {
          clearPending();
        }
        return;
      }

      if (parsed.sequence <= lastSequence) {
        if (pendingCommand && confirmsPending(pendingCommand, parsed)) {
          clearPending();
        }
        return;
      }

      if (parsed.sequence !== lastSequence + 1) {
        void recoverAndReconnect(candidateGeneration);
        return;
      }

      lastSequence = parsed.sequence;
      reconnectAttempts = 0;
      clearRecoveryStabilityTimer();
      options.onEvent(parsed);
      if (pendingCommand && confirmsPending(pendingCommand, parsed)) {
        clearPending();
      }
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

  async function recoverAndReconnect(expectedGeneration: number) {
    if (!active || reloading || generation !== expectedGeneration) return;
    reloading = true;
    clearRecoveryStabilityTimer();
    generation += 1;
    socket?.close();
    socket = undefined;
    options.onConnectionChange("reconnecting");

    try {
      const bundle = await options.loadRecoveryBundle();
      if (!active) return;
      if (bundle.snapshot.id !== sessionId) {
        throw new Error("Recovery bundle session mismatch");
      }
      lastSequence = bundle.snapshot.last_sequence;
      if (
        pendingCommand?.type === "participant.utterance.submit" &&
        bundle.transcript.some(
          (item) => item.action_id === pendingCommand?.action_id,
        )
      ) {
        clearPending();
      }
      options.onRecoveryBundle(bundle);
      connect();
    } catch {
      if (active) {
        options.onConnectionChange("disconnected");
        options.onError("无法重新加载会话，请稍后重试。");
        scheduleReconnect(generation);
      }
    } finally {
      reloading = false;
    }
  }

  function scheduleReconnect(expectedGeneration: number) {
    if (!active || reconnectAttempts >= MAX_RECONNECT_ATTEMPTS) return;
    const delay = RECONNECT_DELAY_MS * 2 ** reconnectAttempts;
    reconnectAttempts += 1;
    reconnectTimer = setTimeout(() => {
      reconnectTimer = undefined;
      void recoverAndReconnect(expectedGeneration);
    }, delay);
  }

  return {
    start() {
      if (active) return;
      active = true;
      connect();
    },
    startSession() {
      if (pendingCommand) return pendingCommand.action_id;
      pendingCommand = {
        schema_version: 1,
        type: "session.start",
        session_id: sessionId,
        action_id: crypto.randomUUID(),
        payload: {},
      };
      options.onPendingChange(true);
      if (socket) sendPending(socket);
      return pendingCommand.action_id;
    },
    abort() {
      if (pendingCommand) return pendingCommand.action_id;
      pendingCommand = {
        schema_version: 1,
        type: "session.abort",
        session_id: sessionId,
        action_id: crypto.randomUUID(),
        payload: {},
      };
      options.onPendingChange(true);
      if (socket) sendPending(socket);
      return pendingCommand.action_id;
    },
    submitHumanUtterance(floorGrantId, exactContent) {
      if (pendingCommand) return pendingCommand.action_id;
      pendingCommand = {
        schema_version: 1,
        type: "participant.utterance.submit",
        session_id: sessionId,
        action_id: crypto.randomUUID(),
        payload: {
          floor_grant_id: floorGrantId,
          content: exactContent,
        },
      };
      options.onPendingChange(true);
      options.onHumanPendingChange(humanPendingFromCommand(pendingCommand));
      if (socket) sendPending(socket);
      return pendingCommand.action_id;
    },
    recoverAuthoritativeState() {
      void recoverAndReconnect(generation);
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
