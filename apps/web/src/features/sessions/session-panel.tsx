"use client";

import { useEffect, useRef, useState } from "react";

import {
  createSession,
  getQuestion,
  getSessionSnapshot,
  listQuestions,
  type ApiClient,
  type QuestionDetail,
  type QuestionSummary,
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

  return {
    ...snapshot,
    status: event.payload.status,
    phase_started_at:
      event.schema_version === 2 ? event.payload.phase_started_at : null,
    phase_deadline_at:
      event.schema_version === 2 ? event.payload.phase_deadline_at : null,
    updated_at: event.occurred_at,
    last_sequence: event.sequence,
  };
}

function statusLabel(status: SessionSnapshot["status"]) {
  switch (status) {
    case "CREATED":
      return "已创建";
    case "ABORTED_USER":
      return "已由用户结束";
    case "COMPLETED":
      return "已完成";
    default:
      return "进行中";
  }
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
  const [questions, setQuestions] = useState<QuestionSummary[]>();
  const [selectedQuestionId, setSelectedQuestionId] = useState("");
  const [question, setQuestion] = useState<QuestionDetail>();
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
      async function discover() {
        try {
          const result = await listQuestions(apiClient);
          if (!active) return;
          if (!result.data) {
            setErrorMessage("无法加载训练题目，请稍后重试。");
            return;
          }
          setQuestions(result.data);
          setSelectedQuestionId(result.data[0]?.id ?? "");
        } catch {
          if (active) setErrorMessage("无法加载训练题目，请稍后重试。");
        } finally {
          if (active) setCheckingUrl(false);
        }
      }

      void discover();
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
        if (result.data.question_version_id) {
          const questionResult = await getQuestion(
            apiClient,
            result.data.question_version_id,
          );
          if (!active) return;
          if (!questionResult.data) {
            setErrorMessage("无法加载会话题目，请稍后重试。");
            return;
          }
          setQuestion(questionResult.data);
        }
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
    if (creating || !selectedQuestionId) return;
    setCreating(true);
    setErrorMessage(undefined);
    try {
      const result = await createSession(apiClient, selectedQuestionId);
      if (!result.data) {
        setErrorMessage("无法创建会话，请稍后重试。");
        return;
      }
      putSessionInUrl(result.data.id);
      setSnapshot(result.data);
      setConnectionSeed(result.data);
      const authoritativeQuestionId = result.data.question_version_id;
      if (!authoritativeQuestionId) {
        setErrorMessage("会话已创建，但未绑定题目版本，请刷新后重试。");
        return;
      }
      const questionResult = await getQuestion(
        apiClient,
        authoritativeQuestionId,
      );
      if (questionResult.data) {
        setQuestion(questionResult.data);
      } else {
        setErrorMessage("会话已创建，但题目暂时无法显示，请刷新后重试。");
      }
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
        <div className="mt-4 space-y-4">
          {questions?.length ? (
            <>
              <label
                className="grid gap-1 text-sm"
                htmlFor="question-selection"
              >
                选择训练题目
                <select
                  className="border border-neutral-300 bg-white px-3 py-2"
                  id="question-selection"
                  onChange={(event) =>
                    setSelectedQuestionId(event.target.value)
                  }
                  value={selectedQuestionId}
                >
                  {questions.map((item) => (
                    <option key={item.id} value={item.id}>
                      {item.title} · {item.question_type} · {item.difficulty}
                    </option>
                  ))}
                </select>
              </label>
              <button
                className="bg-neutral-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
                disabled={creating || !selectedQuestionId}
                onClick={() => void create()}
                type="button"
              >
                {creating ? "正在创建…" : "创建文字会话"}
              </button>
            </>
          ) : questions ? (
            <p className="text-sm text-neutral-600">
              当前没有可用于新训练的题目。
            </p>
          ) : (
            <p className="text-sm text-neutral-600">正在加载训练题目…</p>
          )}
        </div>
      ) : (
        <div className="mt-4 space-y-2 text-sm">
          <p>
            会话状态：<strong>{statusLabel(snapshot.status)}</strong>
          </p>
          <p className="break-all text-neutral-600" data-testid="session-id">
            会话 ID：{snapshot.id}
          </p>
          {snapshot.question_version_id ? (
            <p
              className="break-all text-neutral-600"
              data-testid="question-version-id"
            >
              题目版本 ID：{snapshot.question_version_id}
            </p>
          ) : (
            <p className="text-neutral-600">此历史会话未绑定题目版本。</p>
          )}
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
      {question ? (
        <article className="mt-6 space-y-4 border-t border-neutral-200 pt-5 text-sm">
          <div>
            <p className="text-xs font-medium tracking-wide text-neutral-500 uppercase">
              {question.question_type} · {question.difficulty} ·{" "}
              {question.estimated_minutes} 分钟
            </p>
            <h3 className="mt-1 text-base font-semibold">{question.title}</h3>
          </div>
          <div>
            <h4 className="font-medium">情境</h4>
            <p className="mt-1 leading-6 text-neutral-700">
              {question.scenario}
            </p>
          </div>
          <div>
            <h4 className="font-medium">讨论目标</h4>
            <p className="mt-1 leading-6 text-neutral-700">
              {question.objective}
            </p>
          </div>
          <div>
            <h4 className="font-medium">硬约束</h4>
            <ul className="mt-1 list-disc space-y-1 pl-5 text-neutral-700">
              {question.hard_constraints.map((item) => (
                <li key={item.key}>{item.text}</li>
              ))}
            </ul>
          </div>
          {question.options.length ? (
            <div>
              <h4 className="font-medium">可选方案</h4>
              <ul className="mt-1 space-y-2 text-neutral-700">
                {question.options.map((item) => (
                  <li key={item.key}>
                    <strong>{item.label}</strong>：{item.description}
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
        </article>
      ) : null}
      {errorMessage ? (
        <p aria-live="polite" className="mt-3 text-sm text-red-700">
          {errorMessage}
        </p>
      ) : null}
    </section>
  );
}
