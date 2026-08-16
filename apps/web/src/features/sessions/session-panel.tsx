"use client";

import { useEffect, useRef, useState } from "react";

import {
  createSession,
  getSessionSnapshot,
  type ApiClient,
  type SessionSnapshot,
} from "@/lib/api/client";
import {
  createSessionRealtimeClient,
  type RealtimeConnectionState,
  type SessionRealtimeClient,
} from "@/lib/realtime/client";
import type { FormalSessionEvent } from "@/lib/realtime/contract";

type SessionPanelProps = {
  apiClient: ApiClient;
  baseUrl: string;
};

function putSessionInUrl(sessionId: string) {
  const url = new URL(window.location.href);
  url.searchParams.set("session_id", sessionId);
  window.history.replaceState({}, "", url);
}

function projectEvent(
  snapshot: SessionSnapshot,
  event: FormalSessionEvent,
): SessionSnapshot {
  return {
    ...snapshot,
    status: event.type === "session.state_changed" ? "ABORTED_USER" : "CREATED",
    updated_at: event.occurred_at,
    last_sequence: event.sequence,
  };
}

function statusLabel(status: SessionSnapshot["status"]) {
  return status === "CREATED" ? "已创建" : "已由用户结束";
}

function connectionLabel(state: RealtimeConnectionState) {
  switch (state) {
    case "connected":
      return "实时连接已建立";
    case "connecting":
      return "正在连接实时会话…";
    case "reconnecting":
      return "正在重新加载会话…";
    default:
      return "实时连接未建立";
  }
}

export default function SessionPanel({
  apiClient,
  baseUrl,
}: SessionPanelProps) {
  const [snapshot, setSnapshot] = useState<SessionSnapshot>();
  const [connectionSeed, setConnectionSeed] = useState<SessionSnapshot>();
  const [checkingUrl, setCheckingUrl] = useState(true);
  const [creating, setCreating] = useState(false);
  const [pendingAction, setPendingAction] = useState(false);
  const [connection, setConnection] =
    useState<RealtimeConnectionState>("disconnected");
  const [errorMessage, setErrorMessage] = useState<string>();
  const realtimeRef = useRef<SessionRealtimeClient | undefined>(undefined);

  useEffect(() => {
    let active = true;
    const sessionId = new URL(window.location.href).searchParams.get(
      "session_id",
    );
    if (!sessionId) {
      queueMicrotask(() => {
        if (active) setCheckingUrl(false);
      });
      return () => {
        active = false;
      };
    }

    async function restore() {
      try {
        const result = await getSessionSnapshot(apiClient, sessionId!);
        if (!active) return;
        if (!result.data) {
          setErrorMessage("无法加载会话，请确认会话仍然可用。");
          return;
        }
        setSnapshot(result.data);
        setConnectionSeed(result.data);
      } catch {
        if (active) setErrorMessage("无法加载会话，请稍后重试。");
      } finally {
        if (active) setCheckingUrl(false);
      }
    }

    void restore();
    return () => {
      active = false;
    };
  }, [apiClient]);

  useEffect(() => {
    if (!connectionSeed) return;
    let active = true;
    const realtime = createSessionRealtimeClient({
      baseUrl,
      snapshot: connectionSeed,
      async loadSnapshot() {
        const result = await getSessionSnapshot(apiClient, connectionSeed.id);
        if (!result.data) throw new Error("Session snapshot unavailable");
        return result.data;
      },
      onEvent(event) {
        if (!active) return;
        setSnapshot((current) =>
          current ? projectEvent(current, event) : current,
        );
      },
      onSnapshot(authoritative) {
        if (active) setSnapshot(authoritative);
      },
      onPendingChange(pending) {
        if (active) setPendingAction(pending);
      },
      onConnectionChange(state) {
        if (active) setConnection(state);
      },
      onError(message) {
        if (active) setErrorMessage(message);
      },
    });
    realtimeRef.current = realtime;
    realtime.start();

    return () => {
      active = false;
      realtime.stop();
      if (realtimeRef.current === realtime) realtimeRef.current = undefined;
    };
  }, [apiClient, baseUrl, connectionSeed]);

  async function create() {
    if (creating) return;
    setCreating(true);
    setErrorMessage(undefined);
    try {
      const result = await createSession(apiClient);
      if (!result.data) {
        setErrorMessage("无法创建会话，请稍后重试。");
        return;
      }
      putSessionInUrl(result.data.id);
      setSnapshot(result.data);
      setConnectionSeed(result.data);
    } catch {
      setErrorMessage("无法创建会话，请稍后重试。");
    } finally {
      setCreating(false);
    }
  }

  if (checkingUrl) {
    return (
      <section className="mt-8 border-t border-neutral-300 pt-6">
        <p className="text-sm text-neutral-600">正在加载会话…</p>
      </section>
    );
  }

  return (
    <section className="mt-8 border-t border-neutral-300 pt-6">
      <h2 className="text-lg font-medium">讨论会话</h2>
      {!snapshot ? (
        <button
          className="mt-4 bg-neutral-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
          disabled={creating}
          onClick={() => void create()}
          type="button"
        >
          {creating ? "正在创建…" : "创建文字会话"}
        </button>
      ) : (
        <div className="mt-4 space-y-2 text-sm">
          <p>
            会话状态：<strong>{statusLabel(snapshot.status)}</strong>
          </p>
          <p className="break-all text-neutral-600" data-testid="session-id">
            会话 ID：{snapshot.id}
          </p>
          <p className="text-neutral-600">
            当前序号：
            <span data-testid="session-sequence">{snapshot.last_sequence}</span>
          </p>
          <p className="text-neutral-600">{connectionLabel(connection)}</p>
          {snapshot.status === "CREATED" ? (
            <button
              className="mt-2 border border-neutral-900 px-4 py-2 font-medium disabled:opacity-50"
              disabled={pendingAction || connection !== "connected"}
              onClick={() => {
                setErrorMessage(undefined);
                realtimeRef.current?.abort();
              }}
              type="button"
            >
              {pendingAction ? "正在结束…" : "结束会话"}
            </button>
          ) : null}
        </div>
      )}
      {errorMessage ? (
        <p aria-live="polite" className="mt-3 text-sm text-red-700">
          {errorMessage}
        </p>
      ) : null}
    </section>
  );
}
