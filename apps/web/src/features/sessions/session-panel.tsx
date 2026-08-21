"use client";

import { useCallback, useEffect, useRef, useState } from "react";

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
import { projectSessionEvent } from "@/lib/realtime/projection";

type SessionPanelProps = {
  apiClient: ApiClient;
  baseUrl: string;
};

const PHASES = [
  "PREPARATION",
  "OPENING_STATEMENTS",
  "EXPLORATION",
  "CONFLICT_AND_EVALUATION",
  "CONVERGENCE",
  "FINAL_SUMMARY",
] as const;

const PHASE_LABELS: Record<SessionSnapshot["status"], string> = {
  CREATED: "未开始",
  PREPARATION: "准备",
  OPENING_STATEMENTS: "个人陈述",
  EXPLORATION: "观点探索",
  CONFLICT_AND_EVALUATION: "冲突评估",
  CONVERGENCE: "收敛决策",
  FINAL_SUMMARY: "最终总结",
  COMPLETED: "已完成",
  ABORTED_USER: "已结束",
};

function putSessionInUrl(sessionId: string) {
  const url = new URL(window.location.href);
  url.searchParams.set("session_id", sessionId);
  window.history.replaceState({}, "", url);
}

function isActivePhase(status: SessionSnapshot["status"]) {
  return PHASES.some((phase) => phase === status);
}

function participantLabel(
  participant: SessionSnapshot["floor"]["participants"][number] | undefined,
) {
  if (!participant) return "会话参与者";
  if (participant.actor_kind === "HUMAN") return "你（真人参与者）";
  if (participant.actor_kind === "SYSTEM") return "系统主持";
  return `AI 候选人 ${Math.max(1, participant.seat_order - 1)}`;
}

const FLOOR_REASON_LABELS: Record<string, string> = {
  PHASE_MANDATED_TURN: "当前阶段要求的发言机会",
  EXPLICIT_OPPORTUNITY: "已接受的发言机会",
  FIRST_OPPORTUNITY: "优先安排尚未发言的参与者",
  FAIRNESS_RECOVERY: "恢复发言机会公平性",
  MONOPOLY_PREVENTION: "避免同一参与者连续占用发言权",
  PHASE_SUMMARY_OPPORTUNITY: "当前阶段的总结机会",
  SILENCE_RECOVERY: "讨论静默，需要主持介入",
  DEADLINE_RECOVERY: "阶段临近截止，需要主持介入",
  NO_ELIGIBLE_PARTICIPANT: "当前没有符合条件的参与者",
  SPEAKER_FINISHED: "发言已结束",
  INTERRUPTED: "发言已被中止",
  PHASE_CHANGED: "阶段已切换",
  SESSION_TERMINATED: "会话已结束",
};

function lifecycleLabel(event: SessionSnapshot["floor"]["latest_event"]) {
  if (!event) return "等待服务端分配发言权";
  if (event.type === "floor.granted") return "发言权已授予";
  if (event.type === "floor.released") return "发言权已释放";
  return "已请求主持介入";
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

function formatCountdown(milliseconds: number) {
  if (milliseconds <= 0) return "等待服务器推进";
  const totalSeconds = Math.ceil(milliseconds / 1000);
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${minutes}:${seconds.toString().padStart(2, "0")}`;
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
  const [clockAnchor, setClockAnchor] = useState({
    localNowMs: 0,
    serverNowMs: 0,
  });
  const [displayNowMs, setDisplayNowMs] = useState(0);
  const snapshotRef = useRef<SessionSnapshot | undefined>(undefined);
  const realtimeRef = useRef<SessionRealtimeClient | undefined>(undefined);

  const updateClockFromSnapshot = useCallback((next: SessionSnapshot) => {
    if (!next.server_now) return;
    const localNowMs = Date.now();
    setClockAnchor({
      localNowMs,
      serverNowMs: Date.parse(next.server_now),
    });
    setDisplayNowMs(localNowMs);
  }, []);

  const applySnapshot = useCallback(
    (next: SessionSnapshot) => {
      snapshotRef.current = next;
      setSnapshot(next);
      updateClockFromSnapshot(next);
    },
    [updateClockFromSnapshot],
  );

  useEffect(() => {
    if (!snapshot?.phase_deadline_at || !isActivePhase(snapshot.status)) return;
    const interval = window.setInterval(() => {
      setDisplayNowMs(Date.now());
    }, 1_000);
    return () => window.clearInterval(interval);
  }, [snapshot?.phase_deadline_at, snapshot?.status]);

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
        applySnapshot(result.data);
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
  }, [apiClient, applySnapshot]);

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
        const current = snapshotRef.current;
        if (current) applySnapshot(projectSessionEvent(current, event));
      },
      onSnapshot(authoritative) {
        if (active) applySnapshot(authoritative);
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
  }, [apiClient, applySnapshot, baseUrl, connectionSeed]);

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
      applySnapshot(result.data);
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

  const estimatedServerNowMs =
    clockAnchor.serverNowMs === 0
      ? undefined
      : clockAnchor.serverNowMs + (displayNowMs - clockAnchor.localNowMs);
  const phaseDeadlineMs = snapshot?.phase_deadline_at
    ? Date.parse(snapshot.phase_deadline_at)
    : undefined;
  const countdown =
    phaseDeadlineMs === undefined || estimatedServerNowMs === undefined
      ? undefined
      : formatCountdown(phaseDeadlineMs - estimatedServerNowMs);

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
          <div className="mt-4 space-y-3 border-t border-neutral-200 pt-4">
            <div>
              <p className="font-medium" data-testid="phase-label">
                当前阶段：{PHASE_LABELS[snapshot.status]}
              </p>
              {countdown ? (
                <p className="text-neutral-600" data-testid="phase-countdown">
                  剩余时间：{countdown}
                </p>
              ) : (
                <p className="text-neutral-600">等待开始后显示阶段时间。</p>
              )}
              {snapshot.phase_deadline_at ? (
                <p
                  className="break-all text-neutral-600"
                  data-testid="phase-deadline"
                >
                  服务端截止：{snapshot.phase_deadline_at}
                </p>
              ) : null}
            </div>
            <ol className="grid gap-1 text-neutral-600">
              {PHASES.map((phase) => (
                <li
                  className={
                    snapshot.status === phase
                      ? "font-medium text-neutral-950"
                      : undefined
                  }
                  key={phase}
                >
                  {PHASE_LABELS[phase]}
                </li>
              ))}
            </ol>
          </div>
          <div
            className="mt-4 space-y-1 border-t border-neutral-200 pt-4"
            data-testid="floor-status"
          >
            <p className="font-medium">发言权</p>
            <p data-testid="floor-owner">
              当前发言者：
              <strong>
                {snapshot.floor.current_grant
                  ? participantLabel(
                      snapshot.floor.participants.find(
                        (participant) =>
                          participant.participant_id ===
                          snapshot.floor.current_grant?.participant_id,
                      ),
                    )
                  : "暂无"}
              </strong>
            </p>
            <p className="text-neutral-600" data-testid="floor-lifecycle">
              {lifecycleLabel(snapshot.floor.latest_event)}
            </p>
            {snapshot.floor.latest_event ? (
              <p className="text-neutral-600" data-testid="floor-reason">
                原因：
                {FLOOR_REASON_LABELS[snapshot.floor.latest_event.reason_code] ??
                  "服务端发言权规则"}
              </p>
            ) : null}
          </div>
          {snapshot.status === "CREATED" ? (
            <div className="mt-3 flex flex-wrap gap-2">
              <button
                className="border border-neutral-900 bg-neutral-900 px-4 py-2 font-medium text-white disabled:opacity-50"
                disabled={pendingAction || connection !== "connected"}
                onClick={() => {
                  setErrorMessage(undefined);
                  realtimeRef.current?.startSession();
                }}
                type="button"
              >
                {pendingAction ? "正在开始…" : "开始讨论"}
              </button>
              <button
                className="border border-neutral-900 px-4 py-2 font-medium disabled:opacity-50"
                disabled={pendingAction || connection !== "connected"}
                onClick={() => {
                  setErrorMessage(undefined);
                  realtimeRef.current?.abort();
                }}
                type="button"
              >
                {pendingAction ? "正在结束…" : "结束会话"}
              </button>
            </div>
          ) : isActivePhase(snapshot.status) ? (
            <button
              className="mt-3 border border-neutral-900 px-4 py-2 font-medium disabled:opacity-50"
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
