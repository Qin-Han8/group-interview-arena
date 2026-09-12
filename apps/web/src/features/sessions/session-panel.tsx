"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";

import {
  createSession,
  getQuestion,
  getSessionSnapshot,
  generateReport,
  loadSessionTranscript,
  listQuestions,
  type ApiClient,
  type QuestionDetail,
  type QuestionSummary,
  type SessionSnapshot,
} from "@/lib/api/client";
import {
  createSessionRealtimeClient,
  inspectHumanDraft,
  type PendingHumanUtterance,
  type RejectedHumanUtterance,
  type RealtimeConnectionState,
  type SessionRecoveryBundle,
  type SessionRealtimeClient,
} from "@/lib/realtime/client";
import { projectSessionEvent } from "@/lib/realtime/projection";

import {
  confirmedUtteranceFromEvent,
  mergeConfirmedTranscript,
  type ConfirmedUtterance,
} from "./discussion-transcript";
import DiscussionStage from "./discussion-stage";
import DiscussionWorkspace, {
  type ActiveDiscussionSurface,
} from "./discussion-workspace";
import {
  connectionLabel,
  participantLabel,
  phaseLabel,
} from "./session-presentation";
import SessionProgressPanel from "./session-progress-panel";
import TaskBriefPanel, {
  type TaskBriefQuestionState,
} from "./task-brief-panel";

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

const SPEAKING_PHASES = [
  "OPENING_STATEMENTS",
  "EXPLORATION",
  "CONFLICT_AND_EVALUATION",
  "CONVERGENCE",
  "FINAL_SUMMARY",
] as const;
const TRANSCRIPT_FOLLOW_THRESHOLD_PX = 48;
function isTranscriptNearBottom(container: HTMLDivElement) {
  return (
    container.scrollHeight - container.scrollTop - container.clientHeight <=
    TRANSCRIPT_FOLLOW_THRESHOLD_PX
  );
}

function hasAppendedConfirmedTail(
  previous: readonly ConfirmedUtterance[],
  next: readonly ConfirmedUtterance[],
) {
  if (next.length <= previous.length) return false;
  return previous.every(
    (item, index) =>
      item.sequence === next[index]?.sequence &&
      item.utterance_id === next[index]?.utterance_id,
  );
}

type BoundQuestionLoadStatus = "loading" | "available" | "unavailable";

function putSessionInUrl(sessionId: string) {
  const url = new URL(window.location.href);
  url.searchParams.set("session_id", sessionId);
  window.history.replaceState({}, "", url);
}

function isActivePhase(status: SessionSnapshot["status"]) {
  return PHASES.some((phase) => phase === status);
}

function isSpeakingPhase(status: SessionSnapshot["status"]) {
  return SPEAKING_PHASES.some((phase) => phase === status);
}

function formatCountdown(milliseconds: number) {
  if (milliseconds <= 0) return "等待服务器推进";
  const totalSeconds = Math.ceil(milliseconds / 1000);
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${minutes}:${seconds.toString().padStart(2, "0")}`;
}

export default function SessionPanel({
  apiClient,
  baseUrl,
}: SessionPanelProps) {
  const router = useRouter();
  const [snapshot, setSnapshot] = useState<SessionSnapshot>();
  const [questions, setQuestions] = useState<QuestionSummary[]>();
  const [selectedQuestionId, setSelectedQuestionId] = useState("");
  const [hasNewTranscriptBelow, setHasNewTranscriptBelow] = useState(false);
  const [question, setQuestion] = useState<QuestionDetail>();
  const [boundQuestionLoadStatus, setBoundQuestionLoadStatus] =
    useState<BoundQuestionLoadStatus>();
  const [notes, setNotes] = useState("");
  const [activeSurface, setActiveSurface] =
    useState<ActiveDiscussionSurface>("discussion");
  const [connectionSeed, setConnectionSeed] = useState<SessionSnapshot>();
  const [checkingUrl, setCheckingUrl] = useState(true);
  const [creating, setCreating] = useState(false);
  const [pendingAction, setPendingAction] = useState(false);
  const [generatingReport, setGeneratingReport] = useState(false);
  const [humanPending, setHumanPending] = useState<PendingHumanUtterance>();
  const [rejectedDraft, setRejectedDraft] = useState<RejectedHumanUtterance>();
  const [draft, setDraft] = useState("");
  const [interruptedAiGrantIds, setInterruptedAiGrantIds] = useState<string[]>(
    [],
  );
  const [confirmedTranscript, setConfirmedTranscript] = useState<
    ConfirmedUtterance[]
  >([]);
  const [connection, setConnection] =
    useState<RealtimeConnectionState>("disconnected");
  const [errorMessage, setErrorMessage] = useState<string>();
  const [clockAnchor, setClockAnchor] = useState({
    localNowMs: 0,
    serverNowMs: 0,
  });
  const [displayNowMs, setDisplayNowMs] = useState(0);
  const snapshotRef = useRef<SessionSnapshot | undefined>(undefined);
  const confirmedTranscriptRef = useRef<ConfirmedUtterance[]>([]);
  const transcriptContainerRef = useRef<HTMLDivElement | null>(null);
  const shouldFollowTranscriptRef = useRef(false);
  const interruptedAiGrantIdsRef = useRef(new Set<string>());
  const realtimeRef = useRef<SessionRealtimeClient | undefined>(undefined);
  const workspaceSessionIdRef = useRef<string | undefined>(undefined);
  const scrollTranscriptToLatest = useCallback(() => {
    const container = transcriptContainerRef.current;
    if (container) {
      if (typeof container.scrollTo === "function") {
        container.scrollTo({ top: container.scrollHeight });
      } else {
        container.scrollTop = container.scrollHeight;
      }
    }
    shouldFollowTranscriptRef.current = false;
    setHasNewTranscriptBelow(false);
  }, []);

  const handleTranscriptScroll = useCallback(() => {
    const container = transcriptContainerRef.current;
    if (container && isTranscriptNearBottom(container)) {
      setHasNewTranscriptBelow(false);
    }
  }, []);

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
      if (workspaceSessionIdRef.current !== next.id) {
        workspaceSessionIdRef.current = next.id;
        shouldFollowTranscriptRef.current = false;
        setHasNewTranscriptBelow(false);
        setNotes("");
        setActiveSurface("discussion");
        setQuestion(undefined);
        setBoundQuestionLoadStatus(
          next.question_version_id ? "loading" : undefined,
        );
      }
      snapshotRef.current = next;
      setSnapshot(next);
      updateClockFromSnapshot(next);
    },
    [updateClockFromSnapshot],
  );

  const loadAuthoritativeRecoveryBundle = useCallback(
    async (sessionId: string): Promise<SessionRecoveryBundle> => {
      const snapshotResult = await getSessionSnapshot(apiClient, sessionId);
      if (!snapshotResult.data) {
        throw new Error("Session snapshot unavailable");
      }
      const transcript = await loadSessionTranscript(apiClient, sessionId);
      const canonicalTranscript = mergeConfirmedTranscript([], transcript);
      if (canonicalTranscript.kind === "conflict") {
        throw new Error("Authoritative transcript identity conflict");
      }
      return {
        snapshot: snapshotResult.data,
        transcript: canonicalTranscript.items,
      };
    },
    [apiClient],
  );

  const applyRecoveryBundle = useCallback(
    (bundle: SessionRecoveryBundle) => {
      const previous = confirmedTranscriptRef.current;
      const isSameWorkspace =
        workspaceSessionIdRef.current === bundle.snapshot.id;
      if (
        isSameWorkspace &&
        hasAppendedConfirmedTail(previous, bundle.transcript)
      ) {
        const container = transcriptContainerRef.current;
        const shouldFollow =
          container !== null && isTranscriptNearBottom(container);
        shouldFollowTranscriptRef.current = shouldFollow;
        setHasNewTranscriptBelow(!shouldFollow);
      } else {
        shouldFollowTranscriptRef.current = false;
        setHasNewTranscriptBelow(false);
      }
      confirmedTranscriptRef.current = bundle.transcript;
      setConfirmedTranscript(bundle.transcript);
      applySnapshot(bundle.snapshot);
      setErrorMessage(undefined);
    },
    [applySnapshot],
  );

  useEffect(() => {
    confirmedTranscriptRef.current = confirmedTranscript;
    const container = transcriptContainerRef.current;
    if (!shouldFollowTranscriptRef.current || !container) {
      shouldFollowTranscriptRef.current = false;
      return;
    }
    const scrollToLatest = () => {
      if (typeof container.scrollTo === "function") {
        container.scrollTo({ top: container.scrollHeight });
      } else {
        container.scrollTop = container.scrollHeight;
      }
    };
    scrollToLatest();
    const followFrame = window.requestAnimationFrame(scrollToLatest);
    shouldFollowTranscriptRef.current = false;
    return () => window.cancelAnimationFrame(followFrame);
  }, [confirmedTranscript]);

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
        const bundle = await loadAuthoritativeRecoveryBundle(sessionId!);
        if (!active) return;
        applyRecoveryBundle(bundle);
        setConnectionSeed(bundle.snapshot);
        if (bundle.snapshot.question_version_id) {
          setBoundQuestionLoadStatus("loading");
          try {
            const questionResult = await getQuestion(
              apiClient,
              bundle.snapshot.question_version_id,
            );
            if (!active) return;
            if (questionResult.data) {
              setQuestion(questionResult.data);
              setBoundQuestionLoadStatus("available");
            } else {
              setQuestion(undefined);
              setBoundQuestionLoadStatus("unavailable");
            }
          } catch {
            if (active) {
              setQuestion(undefined);
              setBoundQuestionLoadStatus("unavailable");
            }
          }
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
  }, [apiClient, applyRecoveryBundle, loadAuthoritativeRecoveryBundle]);

  useEffect(() => {
    if (!connectionSeed) return;
    let active = true;
    const realtime = createSessionRealtimeClient({
      baseUrl,
      snapshot: connectionSeed,
      loadRecoveryBundle() {
        return loadAuthoritativeRecoveryBundle(connectionSeed.id);
      },
      onEvent(event) {
        if (!active) return;
        const current = snapshotRef.current;
        if (!current) return;
        if (event.type === "participant.utterance.created") {
          const previous = confirmedTranscriptRef.current;
          const container = transcriptContainerRef.current;
          const shouldFollow =
            container !== null && isTranscriptNearBottom(container);
          const incoming = confirmedUtteranceFromEvent(event);
          const merged = mergeConfirmedTranscript(previous, [incoming]);
          if (merged.kind === "conflict") {
            realtimeRef.current?.recoverAuthoritativeState();
            return;
          }
          if (hasAppendedConfirmedTail(previous, merged.items)) {
            shouldFollowTranscriptRef.current = shouldFollow;
            setHasNewTranscriptBelow(!shouldFollow);
          }
          confirmedTranscriptRef.current = merged.items;
          setConfirmedTranscript(merged.items);
        }
        if (
          event.type === "floor.released" &&
          event.payload.reason_code === "INTERRUPTED"
        ) {
          const grant = current.floor.current_grant;
          const participant = current.floor.participants.find(
            (item) => item.participant_id === grant?.participant_id,
          );
          const hasConfirmedUtterance = confirmedTranscriptRef.current.some(
            (item) =>
              item.actor_kind === "AI" &&
              item.floor_grant_id === event.payload.grant_id,
          );
          if (
            grant?.grant_id === event.payload.grant_id &&
            participant?.actor_kind === "AI" &&
            !hasConfirmedUtterance &&
            !interruptedAiGrantIdsRef.current.has(grant.grant_id)
          ) {
            interruptedAiGrantIdsRef.current.add(grant.grant_id);
            setInterruptedAiGrantIds([
              ...interruptedAiGrantIdsRef.current.values(),
            ]);
          }
        }
        applySnapshot(projectSessionEvent(current, event));
      },
      onRecoveryBundle(bundle) {
        if (active) applyRecoveryBundle(bundle);
      },
      onPendingChange(pending) {
        if (active) setPendingAction(pending);
      },
      onHumanPendingChange(pending) {
        if (active) setHumanPending(pending);
      },
      onRejectedHumanUtterance(rejected) {
        if (active) setRejectedDraft(rejected);
      },
      onConnectionChange(state) {
        if (!active) return;
        setConnection(state);
        if (state === "connected") setErrorMessage(undefined);
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
  }, [
    applyRecoveryBundle,
    applySnapshot,
    baseUrl,
    connectionSeed,
    loadAuthoritativeRecoveryBundle,
  ]);

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
      applyRecoveryBundle({ snapshot: result.data, transcript: [] });
      setConnectionSeed(result.data);
      const authoritativeQuestionId = result.data.question_version_id;
      if (!authoritativeQuestionId) {
        setQuestion(undefined);
        setBoundQuestionLoadStatus(undefined);
        return;
      }
      setBoundQuestionLoadStatus("loading");
      try {
        const questionResult = await getQuestion(
          apiClient,
          authoritativeQuestionId,
        );
        if (questionResult.data) {
          setQuestion(questionResult.data);
          setBoundQuestionLoadStatus("available");
        } else {
          setQuestion(undefined);
          setBoundQuestionLoadStatus("unavailable");
        }
      } catch {
        setQuestion(undefined);
        setBoundQuestionLoadStatus("unavailable");
      }
    } catch {
      setErrorMessage("无法创建会话，请稍后重试。");
    } finally {
      setCreating(false);
    }
  }

  async function openReport() {
    const current = snapshotRef.current;
    if (!current || current.status !== "COMPLETED" || generatingReport) return;
    setGeneratingReport(true);
    setErrorMessage(undefined);
    try {
      const result = await generateReport(apiClient, current.id);
      if (!result.data) {
        setErrorMessage("无法生成训练报告，请稍后重试。");
        return;
      }
      router.push(`/sessions/${current.id}/report`);
    } catch {
      setErrorMessage("无法生成训练报告，请稍后重试。");
    } finally {
      setGeneratingReport(false);
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
  const draftInspection = inspectHumanDraft(draft);
  const renderGrant = snapshot?.floor.current_grant;
  const renderGrantParticipant = snapshot?.floor.participants.find(
    (participant) => participant.participant_id === renderGrant?.participant_id,
  );
  const canSend =
    snapshot !== undefined &&
    isSpeakingPhase(snapshot.status) &&
    renderGrant !== null &&
    renderGrantParticipant?.actor_kind === "HUMAN" &&
    connection === "connected" &&
    !pendingAction &&
    draftInspection.isSubmittable;

  let sendDisabledReason = "轮到你发言";
  if (!snapshot || !isSpeakingPhase(snapshot.status)) {
    sendDisabledReason = "当前阶段可以整理思路，暂时不能发送";
  } else if (!renderGrant || renderGrantParticipant?.actor_kind !== "HUMAN") {
    sendDisabledReason = "你可以先整理观点，轮到你时再发送";
  } else if (connection !== "connected") {
    sendDisabledReason = "正在恢复讨论，暂时无法发送";
  } else if (pendingAction) {
    sendDisabledReason = "正在确认上一条发言";
  } else if (!draftInspection.isSubmittable) {
    sendDisabledReason =
      draftInspection.invalidReason === "TOO_LONG"
        ? "发言不能超过 4000 个字符。"
        : draftInspection.invalidReason === "CONTAINS_NULL"
          ? "发言包含不支持的空字符。"
          : "请输入可提交的发言内容。";
  }

  const currentAiParticipant =
    renderGrantParticipant?.actor_kind === "AI"
      ? renderGrantParticipant
      : undefined;
  const aiWaitingLabel =
    connection === "connected" &&
    renderGrant &&
    currentAiParticipant &&
    !confirmedTranscript.some(
      (item) =>
        item.actor_kind === "AI" &&
        item.floor_grant_id === renderGrant.grant_id,
    )
      ? `${participantLabel(
          snapshot?.floor.participants ?? [],
          currentAiParticipant.participant_id,
        )} 正在准备发言…`
      : undefined;

  function submitCurrentDraft() {
    const current = snapshotRef.current;
    const realtime = realtimeRef.current;
    const inspection = inspectHumanDraft(draft);
    if (
      !current ||
      !realtime ||
      !isSpeakingPhase(current.status) ||
      connection !== "connected" ||
      pendingAction ||
      !inspection.isSubmittable
    ) {
      return;
    }
    const grant = current.floor.current_grant;
    const participant = current.floor.participants.find(
      (item) => item.participant_id === grant?.participant_id,
    );
    if (!grant || participant?.actor_kind !== "HUMAN") return;
    realtime.submitHumanUtterance(grant.grant_id, draft);
    setDraft("");
  }

  if (checkingUrl) {
    return (
      <section className="mt-8 border-t border-neutral-300 pt-6">
        <p className="text-sm text-neutral-600">正在加载会话…</p>
      </section>
    );
  }

  if (!snapshot) {
    return (
      <section className="mt-8 border-t border-neutral-300 pt-6">
        <h2 className="text-lg font-medium">讨论会话</h2>
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
        {errorMessage ? (
          <p aria-live="polite" className="mt-3 text-sm text-red-700">
            {errorMessage}
          </p>
        ) : null}
      </section>
    );
  }

  let questionState: TaskBriefQuestionState;
  if (!snapshot.question_version_id) {
    questionState = { kind: "historical-missing" };
  } else if (boundQuestionLoadStatus === "unavailable") {
    questionState = { kind: "unavailable" };
  } else if (boundQuestionLoadStatus === "available" && question) {
    questionState = { kind: "available", question };
  } else {
    questionState = { kind: "loading" };
  }

  const rejectedDraftPresentation = rejectedDraft
    ? {
        content: rejectedDraft.content,
        message:
          rejectedDraft.reason === "UTTERANCE_REJECTED"
            ? "这条发言当前无法提交，请确认发言机会后重试。"
            : "这条发言需要在同步会话状态后重试。",
        restoreLabel: draft ? "用被拒发言替换当前草稿" : "恢复被拒发言到草稿",
      }
    : null;
  const actionDisabled = pendingAction || connection !== "connected";
  const showEndAction =
    snapshot.status === "CREATED" || isActivePhase(snapshot.status);

  return (
    <DiscussionWorkspace
      activeSurface={activeSurface}
      discussion={
        <DiscussionStage
          aiWaitingLabel={aiWaitingLabel ?? null}
          canSend={canSend}
          confirmedTranscript={confirmedTranscript}
          hasNewTranscriptBelow={hasNewTranscriptBelow}
          connection={connection}
          connectionLabel={connectionLabel(connection)}
          currentGrant={snapshot.floor.current_grant}
          draft={draft}
          draftInspection={draftInspection}
          errorMessage={errorMessage ?? null}
          interruptedAiNotices={interruptedAiGrantIds.map((grantId) => ({
            key: grantId,
            message: "这次 AI 发言未完成，讨论将继续。",
          }))}
          onDraftChange={setDraft}
          onReturnToLatest={scrollTranscriptToLatest}
          onTranscriptScroll={handleTranscriptScroll}
          onRestoreRejectedDraft={() => {
            if (!rejectedDraft) return;
            setDraft(rejectedDraft.content);
            setRejectedDraft(undefined);
          }}
          onSubmit={submitCurrentDraft}
          participants={snapshot.floor.participants}
          pendingContent={humanPending?.content ?? null}
          rejectedDraft={rejectedDraftPresentation}
          sendDisabledReason={sendDisabledReason}
          showComposer={
            snapshot.status !== "COMPLETED" &&
            snapshot.status !== "ABORTED_USER"
          }
          status={snapshot.status}
          transcriptContainerRef={transcriptContainerRef}
        />
      }
      header={{
        productName: "AI 群面训练场",
        sessionTitle: question?.title ?? "文字群面训练",
        phaseLabel: phaseLabel(snapshot.status),
        countdown: countdown ?? null,
        connection,
        connectionLabel: connectionLabel(connection),
        startAction: {
          visible: snapshot.status === "CREATED",
          disabled: actionDisabled,
          label: pendingAction ? "正在开始…" : "开始讨论",
          onActivate: () => {
            setErrorMessage(undefined);
            realtimeRef.current?.startSession();
          },
        },
        endAction: {
          visible: showEndAction,
          disabled: actionDisabled,
          label: pendingAction ? "正在结束…" : "结束会话",
          onActivate: () => {
            setErrorMessage(undefined);
            realtimeRef.current?.abort();
          },
        },
        reportAction: {
          visible: snapshot.status === "COMPLETED",
          disabled: generatingReport,
          label: generatingReport ? "正在生成报告…" : "生成 / 查看训练报告",
          onActivate: () => void openReport(),
        },
      }}
      onActiveSurfaceChange={setActiveSurface}
      progress={
        <SessionProgressPanel
          connection={connection}
          countdown={countdown ?? null}
          currentGrant={snapshot.floor.current_grant}
          latestFloorEvent={snapshot.floor.latest_event}
          participants={snapshot.floor.participants}
          status={snapshot.status}
        />
      }
      taskBrief={
        <TaskBriefPanel
          notes={notes}
          onNotesChange={setNotes}
          questionState={questionState}
        />
      }
    />
  );
}
