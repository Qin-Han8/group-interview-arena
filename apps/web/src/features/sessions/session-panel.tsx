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
import DiscussionStage, {
  type LiveAiRenderCandidate,
} from "./discussion-stage";
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
import TrainingEntry, {
  type SelectedQuestionDetailState,
  type TrainingEntrySurface,
} from "./training-entry";

type SessionPanelProps = {
  apiClient: ApiClient;
  baseUrl: string;
  onNavigationStateChange?: (state: SessionNavigationState) => void;
  openCurrentReportRequest?: OpenCurrentReportRequest;
  openSetupRequest?: number;
  returnToLobbyRequest?: number;
};

export type OpenCurrentReportRequest = {
  requestId: number;
  sessionId: string;
};

export type SessionNavigationState =
  | { sessionId: null; status: "loading" | "lobby"; reportAvailable: false }
  | {
      sessionId: string;
      status: SessionSnapshot["status"];
      reportAvailable: boolean;
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

function removeSessionFromUrl() {
  const url = new URL(window.location.href);
  url.searchParams.delete("session_id");
  window.history.replaceState({}, "", url);
}

function isTerminalStatus(status: SessionSnapshot["status"]) {
  return status === "COMPLETED" || status === "ABORTED_USER";
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
  onNavigationStateChange,
  openCurrentReportRequest,
  openSetupRequest = 0,
  returnToLobbyRequest = 0,
}: SessionPanelProps) {
  const router = useRouter();
  const [snapshot, setSnapshot] = useState<SessionSnapshot>();
  const [questions, setQuestions] = useState<QuestionSummary[]>();
  const [trainingEntrySurface, setTrainingEntrySurface] =
    useState<TrainingEntrySurface>("lobby");
  const [selectedQuestionId, setSelectedQuestionId] = useState("");
  const [selectedQuestion, setSelectedQuestion] =
    useState<SelectedQuestionDetailState>({ kind: "idle" });
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
  const [liveAiRenderCandidate, setLiveAiRenderCandidate] =
    useState<LiveAiRenderCandidate | null>(null);
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
  const selectedQuestionRequestRef = useRef(0);
  const handledOpenSetupRequestRef = useRef(openSetupRequest);
  const handledReturnToLobbyRequestRef = useRef(returnToLobbyRequest);
  const handledOpenCurrentReportRequestRef = useRef(
    openCurrentReportRequest?.requestId ?? 0,
  );
  const reportGenerationInFlightRef = useRef(false);
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

  const handleLiveAiRenderMarked = useCallback((utteranceId: string) => {
    setLiveAiRenderCandidate((candidate) =>
      candidate?.utteranceId === utteranceId ? null : candidate,
    );
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
      setLiveAiRenderCandidate(null);
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
            setQuestions([]);
            setErrorMessage("无法加载训练题目，请稍后重试。");
            return;
          }
          setQuestions(result.data);
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
    const navigationState: SessionNavigationState = checkingUrl
      ? { sessionId: null, status: "loading", reportAvailable: false }
      : !snapshot
        ? { sessionId: null, status: "lobby", reportAvailable: false }
        : {
            sessionId: snapshot.id,
            status: snapshot.status,
            reportAvailable: snapshot.status === "COMPLETED",
          };
    onNavigationStateChange?.(navigationState);
  }, [checkingUrl, onNavigationStateChange, snapshot]);

  useEffect(() => {
    if (openSetupRequest === handledOpenSetupRequestRef.current) return;
    handledOpenSetupRequestRef.current = openSetupRequest;
    if (!snapshotRef.current) setTrainingEntrySurface("setup");
  }, [openSetupRequest]);

  useEffect(() => {
    if (returnToLobbyRequest === handledReturnToLobbyRequestRef.current) return;
    handledReturnToLobbyRequestRef.current = returnToLobbyRequest;
    const current = snapshotRef.current;
    if (!current || !isTerminalStatus(current.status)) return;

    let active = true;
    removeSessionFromUrl();
    workspaceSessionIdRef.current = undefined;
    snapshotRef.current = undefined;
    confirmedTranscriptRef.current = [];
    shouldFollowTranscriptRef.current = false;
    interruptedAiGrantIdsRef.current.clear();
    selectedQuestionRequestRef.current += 1;
    setConnectionSeed(undefined);
    setSnapshot(undefined);
    setQuestions(undefined);
    setTrainingEntrySurface("lobby");
    setSelectedQuestionId("");
    setSelectedQuestion({ kind: "idle" });
    setHasNewTranscriptBelow(false);
    setQuestion(undefined);
    setBoundQuestionLoadStatus(undefined);
    setNotes("");
    setActiveSurface("discussion");
    setCreating(false);
    setPendingAction(false);
    setGeneratingReport(false);
    setHumanPending(undefined);
    setRejectedDraft(undefined);
    setDraft("");
    setInterruptedAiGrantIds([]);
    setLiveAiRenderCandidate(null);
    setConfirmedTranscript([]);
    setConnection("disconnected");
    setErrorMessage(undefined);
    setClockAnchor({ localNowMs: 0, serverNowMs: 0 });
    setDisplayNowMs(0);

    async function discover() {
      try {
        const result = await listQuestions(apiClient);
        if (!active) return;
        if (!result.data) {
          setQuestions([]);
          setErrorMessage("无法加载训练题目，请稍后重试。");
          return;
        }
        setQuestions(result.data);
      } catch {
        if (active) {
          setQuestions([]);
          setErrorMessage("无法加载训练题目，请稍后重试。");
        }
      }
    }

    void discover();
    return () => {
      active = false;
    };
  }, [apiClient, returnToLobbyRequest]);

  async function selectQuestion(questionId: string) {
    const requestId = selectedQuestionRequestRef.current + 1;
    selectedQuestionRequestRef.current = requestId;
    setSelectedQuestionId(questionId);
    setSelectedQuestion({ kind: "loading", questionId });
    setErrorMessage(undefined);
    try {
      const result = await getQuestion(apiClient, questionId);
      if (selectedQuestionRequestRef.current !== requestId) return;
      if (result.data?.id === questionId) {
        setSelectedQuestion({
          kind: "available",
          questionId,
          question: result.data,
        });
      } else {
        setSelectedQuestion({ kind: "unavailable", questionId });
      }
    } catch {
      if (selectedQuestionRequestRef.current === requestId) {
        setSelectedQuestion({ kind: "unavailable", questionId });
      }
    }
  }

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
          if (
            incoming.actor_kind === "AI" &&
            !previous.some(
              (item) => item.utterance_id === incoming.utterance_id,
            )
          ) {
            setLiveAiRenderCandidate({
              utteranceId: incoming.utterance_id,
              sequence: incoming.sequence,
              participantId: incoming.participant_id,
            });
          }
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
      selectedQuestionRequestRef.current += 1;
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

  const openReport = useCallback(
    async (expectedSessionId: string) => {
      const current = snapshotRef.current;
      if (
        !current ||
        current.id !== expectedSessionId ||
        current.status !== "COMPLETED" ||
        reportGenerationInFlightRef.current
      ) {
        return;
      }
      reportGenerationInFlightRef.current = true;
      setGeneratingReport(true);
      setErrorMessage(undefined);
      try {
        const result = await generateReport(apiClient, expectedSessionId);
        if (!result.data) {
          setErrorMessage("无法生成训练报告，请稍后重试。");
          return;
        }
        const latest = snapshotRef.current;
        if (latest?.id === expectedSessionId && latest.status === "COMPLETED") {
          router.push(`/sessions/${expectedSessionId}/report`);
        }
      } catch {
        setErrorMessage("无法生成训练报告，请稍后重试。");
      } finally {
        reportGenerationInFlightRef.current = false;
        setGeneratingReport(false);
      }
    },
    [apiClient, router],
  );

  useEffect(() => {
    if (
      !openCurrentReportRequest ||
      openCurrentReportRequest.requestId ===
        handledOpenCurrentReportRequestRef.current
    ) {
      return;
    }
    handledOpenCurrentReportRequestRef.current =
      openCurrentReportRequest.requestId;
    void openReport(openCurrentReportRequest.sessionId);
  }, [openCurrentReportRequest, openReport]);

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
      <section
        className="h-full overflow-y-auto overscroll-contain p-6"
        data-testid="training-lobby-loading-scroll"
      >
        <p className="text-sm text-neutral-600">正在加载会话…</p>
      </section>
    );
  }

  if (!snapshot) {
    return (
      <TrainingEntry
        creating={creating}
        errorMessage={errorMessage}
        onBeginSelection={() => setTrainingEntrySurface("setup")}
        onCreateSession={() => void create()}
        onSelectQuestion={(questionId) => void selectQuestion(questionId)}
        questions={questions}
        selectedQuestion={selectedQuestion}
        selectedQuestionId={selectedQuestionId}
        surface={trainingEntrySurface}
      />
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
          liveAiRenderCandidate={liveAiRenderCandidate}
          onLiveAiRenderMarked={handleLiveAiRenderMarked}
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
          onActivate: () => void openReport(snapshot.id),
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
