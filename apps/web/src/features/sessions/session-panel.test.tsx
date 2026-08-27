import {
  act,
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  createSession,
  getQuestion,
  getSessionSnapshot,
  loadSessionTranscript,
  listQuestions,
  type ApiClient,
  type QuestionDetail,
  type QuestionSummary,
  type SessionSnapshot,
  type TranscriptUtterance,
} from "@/lib/api/client";
import {
  createSessionRealtimeClient,
  type RejectedHumanUtterance,
  type RealtimeConnectionState,
} from "@/lib/realtime/client";
import type { FormalSessionEvent } from "@/lib/realtime/contract";

import * as transcriptModel from "./discussion-transcript";
import SessionPanel from "./session-panel";

vi.mock("@/lib/api/client", () => ({
  createSession: vi.fn(),
  getQuestion: vi.fn(),
  getSessionSnapshot: vi.fn(),
  loadSessionTranscript: vi.fn(),
  listQuestions: vi.fn(),
}));
vi.mock("@/lib/realtime/client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/realtime/client")>();
  return {
    ...actual,
    createSessionRealtimeClient: vi.fn(),
  };
});

const SESSION_ID = "00000000-0000-4000-8000-000000000010";
const ACTION_ID = "00000000-0000-4000-8000-000000000011";
const QUESTION_VERSION_ID = "21000000-0000-4000-8000-000000000001";
const QUESTION_TEMPLATE_ID = "20000000-0000-4000-8000-000000000001";
const HUMAN_PARTICIPANT_ID = "00000000-0000-4000-8000-000000000012";
const AI_PARTICIPANT_ID = "00000000-0000-4000-8000-000000000013";
const AI_PARTICIPANT_2_ID = "00000000-0000-4000-8000-000000000018";
const AI_PARTICIPANT_3_ID = "00000000-0000-4000-8000-000000000019";
const GRANT_ID = "00000000-0000-4000-8000-000000000014";
const SECOND_GRANT_ID = "00000000-0000-4000-8000-000000000020";
const DECISION_ID = "00000000-0000-4000-8000-000000000015";
const QUESTION_SUMMARY: QuestionSummary = {
  id: QUESTION_VERSION_ID,
  question_template_id: QUESTION_TEMPLATE_ID,
  version_number: 1,
  title: "内部验证：社区活动资源安排",
  question_type: "RESOURCE_ALLOCATION",
  background_domain: "GENERAL",
  difficulty: "STANDARD",
  estimated_minutes: 25,
};
const QUESTION_DETAIL: QuestionDetail = {
  ...QUESTION_SUMMARY,
  scenario: "团队需要在有限资源下安排三类社区活动。",
  objective: "形成满足硬约束、说明取舍且可执行的资源安排。",
  hard_constraints: [{ key: "BUDGET", text: "总资源不得超过 100 个单位。" }],
  soft_constraints: [],
  stakeholders: [
    { key: "RESIDENTS", name: "社区居民", description: "活动服务对象。" },
  ],
  options: [{ key: "A", label: "基础服务", description: "保障最大覆盖面。" }],
};
const CREATED: SessionSnapshot = {
  id: SESSION_ID,
  question_version_id: QUESTION_VERSION_ID,
  status: "CREATED",
  phase_started_at: null,
  phase_deadline_at: null,
  server_now: "2026-08-16T00:00:00Z",
  created_at: "2026-08-16T00:00:00Z",
  updated_at: "2026-08-16T00:00:00Z",
  last_sequence: 1,
  floor: {
    participants: [
      {
        participant_id: HUMAN_PARTICIPANT_ID,
        actor_kind: "HUMAN",
        seat_order: 1,
      },
      {
        participant_id: AI_PARTICIPANT_ID,
        actor_kind: "AI",
        seat_order: 2,
      },
    ],
    current_grant: null,
    latest_event: null,
  },
};
const ABORTED: SessionSnapshot = {
  ...CREATED,
  status: "ABORTED_USER",
  updated_at: "2026-08-16T00:00:01Z",
  last_sequence: 2,
};
const PREPARATION: SessionSnapshot = {
  ...CREATED,
  status: "PREPARATION",
  phase_started_at: "2026-08-16T00:00:01Z",
  phase_deadline_at: "2026-08-16T00:04:01Z",
  server_now: "2026-08-16T00:00:01Z",
  updated_at: "2026-08-16T00:00:01Z",
  last_sequence: 2,
};
const API_CLIENT = { unit: true } as unknown as ApiClient;
const HUMAN_TRANSCRIPT: TranscriptUtterance = {
  utterance_id: "00000000-0000-4000-8000-000000000016",
  sequence: 5,
  occurred_at: "2026-08-16T00:01:20Z",
  action_id: ACTION_ID,
  participant_id: HUMAN_PARTICIPANT_ID,
  actor_kind: "HUMAN",
  floor_grant_id: GRANT_ID,
  phase: "OPENING_STATEMENTS",
  content: "  exact Human contribution\nsecond line  ",
};

function utteranceEvent(
  item: TranscriptUtterance = HUMAN_TRANSCRIPT,
): FormalSessionEvent {
  return {
    schema_version: 1,
    type: "participant.utterance.created",
    session_id: SESSION_ID,
    sequence: item.sequence,
    occurred_at: item.occurred_at,
    action_id: item.action_id,
    payload: {
      utterance_id: item.utterance_id,
      participant_id: item.participant_id,
      actor_kind: item.actor_kind,
      floor_grant_id: item.floor_grant_id,
      phase: item.phase,
      content: item.content,
    },
  };
}

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((resolvePromise, rejectPromise) => {
    resolve = resolvePromise;
    reject = rejectPromise;
  });
  return { promise, resolve, reject };
}

const mockedCreateSession = vi.mocked(createSession);
const mockedGetQuestion = vi.mocked(getQuestion);
const mockedGetSessionSnapshot = vi.mocked(getSessionSnapshot);
const mockedLoadSessionTranscript = vi.mocked(loadSessionTranscript);
const mockedListQuestions = vi.mocked(listQuestions);
const mockedCreateRealtime = vi.mocked(createSessionRealtimeClient);

function installRealtimeDouble() {
  const start = vi.fn();
  const startSession = vi.fn(() => ACTION_ID);
  const abort = vi.fn(() => ACTION_ID);
  const submitHumanUtterance = vi.fn(() => ACTION_ID);
  const recoverAuthoritativeState = vi.fn();
  const stop = vi.fn();
  let options: Parameters<typeof createSessionRealtimeClient>[0] | undefined;
  mockedCreateRealtime.mockImplementation((candidate) => {
    options = candidate;
    return {
      start,
      startSession,
      abort,
      submitHumanUtterance,
      recoverAuthoritativeState,
      stop,
    };
  });
  return {
    start,
    startSession,
    abort,
    submitHumanUtterance,
    recoverAuthoritativeState,
    stop,
    options: () => {
      if (!options) throw new Error("Realtime client was not created");
      return options;
    },
  };
}

function installQuestionDiscovery(
  questions: QuestionSummary[] = [QUESTION_SUMMARY],
) {
  mockedListQuestions.mockResolvedValue({
    data: questions,
    response: new Response(null, { status: 200 }),
  });
  mockedGetQuestion.mockResolvedValue({
    data: QUESTION_DETAIL,
    response: new Response(null, { status: 200 }),
  });
}

function discussionSnapshot(
  participantId: string | null = HUMAN_PARTICIPANT_ID,
  grantId = GRANT_ID,
  status: SessionSnapshot["status"] = "OPENING_STATEMENTS",
): SessionSnapshot {
  return {
    ...CREATED,
    status,
    phase_started_at: isActiveTestPhase(status) ? "2026-08-16T00:01:00Z" : null,
    phase_deadline_at: isActiveTestPhase(status)
      ? "2026-08-16T00:05:00Z"
      : null,
    last_sequence: 4,
    floor: {
      participants: [
        ...CREATED.floor.participants,
        {
          participant_id: AI_PARTICIPANT_2_ID,
          actor_kind: "AI",
          seat_order: 3,
        },
        {
          participant_id: AI_PARTICIPANT_3_ID,
          actor_kind: "AI",
          seat_order: 4,
        },
      ],
      current_grant: participantId
        ? {
            grant_id: grantId,
            participant_id: participantId,
            phase: "OPENING_STATEMENTS",
            reason_code: "FIRST_OPPORTUNITY",
            granted_at: "2026-08-16T00:01:10Z",
          }
        : null,
      latest_event: null,
    },
  };
}

function isActiveTestPhase(status: SessionSnapshot["status"]) {
  return [
    "PREPARATION",
    "OPENING_STATEMENTS",
    "EXPLORATION",
    "CONFLICT_AND_EVALUATION",
    "CONVERGENCE",
    "FINAL_SUMMARY",
  ].includes(status);
}

async function renderRestoredSession(
  snapshot: SessionSnapshot,
  transcript: TranscriptUtterance[] = [],
) {
  window.history.replaceState({}, "", `/?session_id=${SESSION_ID}`);
  mockedGetSessionSnapshot.mockResolvedValue({
    data: snapshot,
    response: new Response(null, { status: 200 }),
  });
  mockedLoadSessionTranscript.mockResolvedValue(transcript);
  mockedGetQuestion.mockResolvedValue({
    data: QUESTION_DETAIL,
    response: new Response(null, { status: 200 }),
  });
  const realtime = installRealtimeDouble();
  const rendered = render(
    <SessionPanel apiClient={API_CLIENT} baseUrl="http://localhost:8000" />,
  );
  await waitFor(() => expect(realtime.start).toHaveBeenCalledOnce());
  return { realtime, rendered };
}

describe("SessionPanel", () => {
  beforeEach(() => {
    mockedLoadSessionTranscript.mockResolvedValue([]);
  });

  afterEach(() => {
    cleanup();
    window.history.replaceState({}, "", "/");
    vi.clearAllMocks();
  });

  it("restores snapshot then complete transcript before opening realtime", async () => {
    window.history.replaceState({}, "", `/?session_id=${SESSION_ID}`);
    const snapshotLoad = deferred<{
      data: SessionSnapshot;
      response: Response;
    }>();
    const transcriptLoad = deferred<TranscriptUtterance[]>();
    mockedGetSessionSnapshot.mockReturnValue(snapshotLoad.promise);
    mockedLoadSessionTranscript.mockReturnValue(transcriptLoad.promise);
    mockedGetQuestion.mockResolvedValue({
      data: QUESTION_DETAIL,
      response: new Response(null, { status: 200 }),
    });
    const realtime = installRealtimeDouble();

    render(
      <SessionPanel apiClient={API_CLIENT} baseUrl="http://localhost:8000" />,
    );

    await waitFor(() =>
      expect(mockedGetSessionSnapshot).toHaveBeenCalledWith(
        API_CLIENT,
        SESSION_ID,
      ),
    );
    expect(mockedLoadSessionTranscript).not.toHaveBeenCalled();
    expect(mockedCreateRealtime).not.toHaveBeenCalled();

    snapshotLoad.resolve({
      data: CREATED,
      response: new Response(null, { status: 200 }),
    });
    await waitFor(() =>
      expect(mockedLoadSessionTranscript).toHaveBeenCalledWith(
        API_CLIENT,
        SESSION_ID,
      ),
    );
    expect(mockedCreateRealtime).not.toHaveBeenCalled();

    transcriptLoad.resolve([HUMAN_TRANSCRIPT]);
    expect((await screen.findAllByText("未开始")).length).toBeGreaterThan(0);
    await waitFor(() => expect(realtime.start).toHaveBeenCalledOnce());
    expect(realtime.options().snapshot).toBe(CREATED);
  });

  it("keeps authoritative facts during failed recovery and applies only a complete later bundle", async () => {
    const opening: SessionSnapshot = {
      ...CREATED,
      status: "OPENING_STATEMENTS",
      last_sequence: 4,
      floor: {
        ...CREATED.floor,
        current_grant: {
          grant_id: GRANT_ID,
          participant_id: AI_PARTICIPANT_ID,
          phase: "OPENING_STATEMENTS",
          reason_code: "FIRST_OPPORTUNITY",
          granted_at: "2026-08-16T00:01:10Z",
        },
      },
    };
    window.history.replaceState({}, "", `/?session_id=${SESSION_ID}`);
    mockedGetSessionSnapshot.mockResolvedValue({
      data: opening,
      response: new Response(null, { status: 200 }),
    });
    mockedLoadSessionTranscript.mockResolvedValue([HUMAN_TRANSCRIPT]);
    mockedGetQuestion.mockResolvedValue({
      data: QUESTION_DETAIL,
      response: new Response(null, { status: 200 }),
    });
    const realtime = installRealtimeDouble();

    render(
      <SessionPanel apiClient={API_CLIENT} baseUrl="http://localhost:8000" />,
    );
    expect(
      await screen.findByText("当前发言：AI 候选人 1"),
    ).toBeInTheDocument();
    await waitFor(() => expect(realtime.start).toHaveBeenCalledOnce());

    act(() => {
      realtime.options().onError("旧连接错误");
      realtime.options().onRejectedHumanUtterance({
        action_id: ACTION_ID,
        floor_grant_id: GRANT_ID,
        content: HUMAN_TRANSCRIPT.content,
        reason: "UTTERANCE_REJECTED",
      } satisfies RejectedHumanUtterance);
      realtime.options().onConnectionChange("reconnecting");
    });
    expect(
      (await screen.findAllByText("正在同步最新讨论记录…")).length,
    ).toBeGreaterThan(0);
    expect(screen.getByText("当前发言：AI 候选人 1")).toBeInTheDocument();
    expect(screen.getByTestId("rejected-human-content").textContent).toBe(
      HUMAN_TRANSCRIPT.content,
    );

    mockedGetSessionSnapshot.mockRejectedValueOnce(
      new Error("recovery failed"),
    );
    await expect(realtime.options().loadRecoveryBundle()).rejects.toThrow();
    expect(screen.getByText("当前发言：AI 候选人 1")).toBeInTheDocument();

    mockedGetSessionSnapshot.mockResolvedValueOnce({
      data: ABORTED,
      response: new Response(null, { status: 200 }),
    });
    mockedLoadSessionTranscript.mockResolvedValueOnce([HUMAN_TRANSCRIPT]);
    const recovered = await realtime.options().loadRecoveryBundle();
    act(() => {
      realtime.options().onRecoveryBundle(recovered);
      realtime.options().onConnectionChange("connected");
    });

    expect((await screen.findAllByText("已结束")).length).toBeGreaterThan(0);
    expect(screen.queryByText("旧连接错误")).not.toBeInTheDocument();
    expect(screen.getByText("训练已结束")).toBeInTheDocument();
    expect(screen.queryByTestId("rejected-human-content")).toBeNull();
  });

  it("rejects conflicting transcript identities before an authoritative bundle resolves", async () => {
    const mergeSpy = vi.spyOn(transcriptModel, "mergeConfirmedTranscript");
    const { realtime } = await renderRestoredSession(CREATED, [
      HUMAN_TRANSCRIPT,
    ]);
    expect(realtime.options().snapshot).toBe(CREATED);
    expect(
      screen.getByTestId(`utterance-content-${HUMAN_TRANSCRIPT.utterance_id}`)
        .textContent,
    ).toBe(HUMAN_TRANSCRIPT.content);

    const conflictingTranscript = [
      HUMAN_TRANSCRIPT,
      { ...HUMAN_TRANSCRIPT, content: "conflicting authoritative content" },
    ];
    mockedGetSessionSnapshot.mockResolvedValueOnce({
      data: { ...ABORTED, last_sequence: 99 },
      response: new Response(null, { status: 200 }),
    });
    mockedLoadSessionTranscript.mockResolvedValueOnce(conflictingTranscript);

    await expect(realtime.options().loadRecoveryBundle()).rejects.toThrow(
      "Authoritative transcript identity conflict",
    );

    expect(mergeSpy).toHaveBeenLastCalledWith([], conflictingTranscript);
    expect(realtime.options().snapshot).toBe(CREATED);
    expect(
      screen.getByRole("button", { name: "开始讨论" }),
    ).toBeInTheDocument();
    expect(
      screen.getByTestId(`utterance-content-${HUMAN_TRANSCRIPT.utterance_id}`)
        .textContent,
    ).toBe(HUMAN_TRANSCRIPT.content);
  });

  it("validates every authoritative bundle from an empty transcript base", async () => {
    window.history.replaceState({}, "", `/?session_id=${SESSION_ID}`);
    mockedGetSessionSnapshot.mockResolvedValue({
      data: CREATED,
      response: new Response(null, { status: 200 }),
    });
    mockedLoadSessionTranscript.mockResolvedValue([HUMAN_TRANSCRIPT]);
    mockedGetQuestion.mockResolvedValue({
      data: QUESTION_DETAIL,
      response: new Response(null, { status: 200 }),
    });
    const mergeSpy = vi.spyOn(transcriptModel, "mergeConfirmedTranscript");
    const realtime = installRealtimeDouble();

    render(
      <SessionPanel apiClient={API_CLIENT} baseUrl="http://localhost:8000" />,
    );
    await waitFor(() => expect(realtime.start).toHaveBeenCalledOnce());
    expect(mergeSpy).toHaveBeenCalledWith([], [HUMAN_TRANSCRIPT]);

    const duplicateTranscript = [HUMAN_TRANSCRIPT, HUMAN_TRANSCRIPT];
    mockedGetSessionSnapshot.mockResolvedValueOnce({
      data: ABORTED,
      response: new Response(null, { status: 200 }),
    });
    mockedLoadSessionTranscript.mockResolvedValueOnce(duplicateTranscript);
    const correctedBundle = await realtime.options().loadRecoveryBundle();

    expect(correctedBundle).toEqual({
      snapshot: ABORTED,
      transcript: [HUMAN_TRANSCRIPT],
    });
    expect(mergeSpy).toHaveBeenLastCalledWith([], duplicateTranscript);

    act(() => realtime.options().onRecoveryBundle(correctedBundle));

    expect((await screen.findAllByText("已结束")).length).toBeGreaterThan(0);
  });

  it("merges live utterances and requests recovery on identity conflict", async () => {
    const opening: SessionSnapshot = {
      ...CREATED,
      status: "OPENING_STATEMENTS",
      last_sequence: HUMAN_TRANSCRIPT.sequence,
    };
    const aiItem: TranscriptUtterance = {
      ...HUMAN_TRANSCRIPT,
      utterance_id: "00000000-0000-4000-8000-000000000017",
      sequence: 6,
      action_id: null,
      participant_id: AI_PARTICIPANT_ID,
      actor_kind: "AI",
      content: "AI confirmed contribution",
    };
    window.history.replaceState({}, "", `/?session_id=${SESSION_ID}`);
    mockedGetSessionSnapshot.mockResolvedValue({
      data: opening,
      response: new Response(null, { status: 200 }),
    });
    mockedLoadSessionTranscript.mockResolvedValue([HUMAN_TRANSCRIPT]);
    mockedGetQuestion.mockResolvedValue({
      data: QUESTION_DETAIL,
      response: new Response(null, { status: 200 }),
    });
    const mergeSpy = vi.spyOn(transcriptModel, "mergeConfirmedTranscript");
    const realtime = installRealtimeDouble();

    render(
      <SessionPanel apiClient={API_CLIENT} baseUrl="http://localhost:8000" />,
    );
    await waitFor(() => expect(realtime.start).toHaveBeenCalledOnce());

    act(() => realtime.options().onEvent(utteranceEvent(aiItem)));
    expect(
      await screen.findByTestId(`utterance-content-${aiItem.utterance_id}`),
    ).toHaveTextContent(aiItem.content);
    expect(mergeSpy).toHaveBeenLastCalledWith([HUMAN_TRANSCRIPT], [aiItem]);

    act(() => realtime.options().onEvent(utteranceEvent(aiItem)));
    expect(mergeSpy).toHaveBeenLastCalledWith(
      [HUMAN_TRANSCRIPT, aiItem],
      [aiItem],
    );

    act(() =>
      realtime
        .options()
        .onEvent(utteranceEvent({ ...aiItem, content: "conflicting content" })),
    );
    expect(realtime.recoverAuthoritativeState).toHaveBeenCalledOnce();
    expect(
      screen.getByTestId(`utterance-content-${aiItem.utterance_id}`),
    ).toHaveTextContent(aiItem.content);
  });

  it("keeps the textarea editable while enforcing all six send gates", async () => {
    const human = discussionSnapshot(HUMAN_PARTICIPANT_ID);
    const { realtime } = await renderRestoredSession(human);
    const textarea = screen.getByLabelText("发言草稿");
    const send = screen.getByRole("button", { name: "发送发言" });

    act(() => realtime.options().onConnectionChange("connected"));
    fireEvent.change(textarea, { target: { value: "valid contribution" } });
    expect(textarea).toBeEnabled();
    expect(send).toBeEnabled();
    expect(screen.getByText("18 / 4000")).toBeInTheDocument();

    for (const blocked of [
      discussionSnapshot(AI_PARTICIPANT_ID),
      discussionSnapshot(null),
      discussionSnapshot(HUMAN_PARTICIPANT_ID, GRANT_ID, "PREPARATION"),
    ]) {
      act(() =>
        realtime.options().onRecoveryBundle({
          snapshot: blocked,
          transcript: [],
        }),
      );
      expect(textarea).toBeEnabled();
      expect(send).toBeDisabled();
      expect(
        screen.getByTestId("send-disabled-reason"),
      ).not.toBeEmptyDOMElement();
    }

    for (const terminal of ["COMPLETED", "ABORTED_USER"] as const) {
      act(() =>
        realtime.options().onRecoveryBundle({
          snapshot: discussionSnapshot(
            HUMAN_PARTICIPANT_ID,
            GRANT_ID,
            terminal,
          ),
          transcript: [],
        }),
      );
      expect(screen.queryByLabelText("发言草稿")).not.toBeInTheDocument();
    }

    act(() =>
      realtime.options().onRecoveryBundle({ snapshot: human, transcript: [] }),
    );
    const restoredTextarea = screen.getByLabelText("发言草稿");
    const restoredSend = screen.getByRole("button", { name: "发送发言" });
    for (const state of [
      "connecting",
      "reconnecting",
      "disconnected",
    ] satisfies RealtimeConnectionState[]) {
      act(() => realtime.options().onConnectionChange(state));
      expect(restoredSend).toBeDisabled();
    }

    act(() => realtime.options().onConnectionChange("connected"));
    fireEvent.change(restoredTextarea, { target: { value: "\u0085" } });
    expect(restoredSend).toBeDisabled();
    fireEvent.change(restoredTextarea, { target: { value: "😀" } });
    expect(screen.getByText("1 / 4000")).toBeInTheDocument();
    expect(restoredSend).toBeEnabled();
    act(() => realtime.options().onPendingChange(true));
    expect(restoredSend).toBeDisabled();
  });

  it("submits keyboard and click actions against the latest exact Human floor", async () => {
    const grantB = "00000000-0000-4000-8000-000000000021";
    const humanA = discussionSnapshot(HUMAN_PARTICIPANT_ID, GRANT_ID);
    const humanB = discussionSnapshot(HUMAN_PARTICIPANT_ID, grantB);
    const { realtime } = await renderRestoredSession(humanA);
    act(() => realtime.options().onConnectionChange("connected"));
    const textarea = screen.getByLabelText("发言草稿");
    const focus = vi.spyOn(textarea, "focus");
    const exact = "  exact contribution\nsecond line  ";
    fireEvent.change(textarea, { target: { value: exact } });

    expect(fireEvent.keyDown(textarea, { key: "Enter" })).toBe(true);
    expect(realtime.submitHumanUtterance).not.toHaveBeenCalled();
    act(() =>
      realtime.options().onRecoveryBundle({ snapshot: humanB, transcript: [] }),
    );
    expect(focus).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "发送发言" }));
    expect(realtime.submitHumanUtterance).toHaveBeenLastCalledWith(
      grantB,
      exact,
    );

    fireEvent.change(textarea, { target: { value: "\ufeff" } });
    fireEvent.keyDown(textarea, { key: "Enter", ctrlKey: true });
    expect(realtime.submitHumanUtterance).toHaveBeenLastCalledWith(
      grantB,
      "\ufeff",
    );

    const surrounded = "\u0085visible\u001c";
    fireEvent.change(textarea, { target: { value: surrounded } });
    fireEvent.keyDown(textarea, { key: "Enter", metaKey: true });
    expect(realtime.submitHumanUtterance).toHaveBeenLastCalledWith(
      grantB,
      surrounded,
    );
  });

  it("keeps draft, Human pending, rejected content, and transcript distinct", async () => {
    const human = discussionSnapshot(HUMAN_PARTICIPANT_ID);
    const { realtime } = await renderRestoredSession(human);
    act(() => realtime.options().onConnectionChange("connected"));
    const textarea = screen.getByLabelText("发言草稿");
    const pendingContent = "pending C";
    fireEvent.change(textarea, { target: { value: pendingContent } });
    fireEvent.click(screen.getByRole("button", { name: "发送发言" }));
    act(() => {
      realtime.options().onPendingChange(true);
      realtime.options().onHumanPendingChange({
        action_id: ACTION_ID,
        floor_grant_id: GRANT_ID,
        content: pendingContent,
      });
    });

    expect(textarea).toHaveValue("");
    fireEvent.change(textarea, { target: { value: "newer draft D" } });
    expect(textarea).toHaveValue("newer draft D");
    expect(screen.getByTestId("human-pending-content").textContent).toBe(
      pendingContent,
    );
    expect(screen.getByRole("button", { name: "发送发言" })).toBeDisabled();
    expect(
      within(screen.getByTestId("confirmed-transcript")).queryByText(
        pendingContent,
      ),
    ).not.toBeInTheDocument();

    act(() => {
      realtime.options().onHumanPendingChange(undefined);
      realtime.options().onPendingChange(false);
      realtime.options().onRejectedHumanUtterance({
        action_id: ACTION_ID,
        floor_grant_id: GRANT_ID,
        content: pendingContent,
        reason: "UTTERANCE_REJECTED",
      });
    });
    expect(textarea).toHaveValue("newer draft D");
    expect(
      within(screen.getByTestId("rejected-human-draft")).getByText(
        "这条发言当前无法提交，请确认发言机会后重试。",
      ),
    ).toBeInTheDocument();
    expect(screen.getByTestId("rejected-human-content").textContent).toBe(
      pendingContent,
    );

    act(() => realtime.options().onConnectionChange("reconnecting"));
    expect(screen.getAllByText("正在同步最新讨论记录…").length).toBeGreaterThan(
      0,
    );
    expect(screen.getByTestId("rejected-human-content")).toBeInTheDocument();
    act(() => realtime.options().onConnectionChange("connected"));
    expect(screen.getByTestId("rejected-human-content")).toBeInTheDocument();

    fireEvent.click(
      screen.getByRole("button", { name: "用被拒发言替换当前草稿" }),
    );
    expect(textarea).toHaveValue(pendingContent);
  });

  it("renders only safe confirmed transcript facts with deterministic speaker labels", async () => {
    const snapshot = discussionSnapshot(null);
    const items: TranscriptUtterance[] = [
      {
        ...HUMAN_TRANSCRIPT,
        content: "<strong>plain</strong>\n**markdown stays text**",
      },
      {
        ...HUMAN_TRANSCRIPT,
        utterance_id: "00000000-0000-4000-8000-000000000022",
        sequence: 6,
        action_id: null,
        participant_id: AI_PARTICIPANT_ID,
        actor_kind: "AI",
        content: "AI one",
      },
      {
        ...HUMAN_TRANSCRIPT,
        utterance_id: "00000000-0000-4000-8000-000000000023",
        sequence: 7,
        action_id: null,
        participant_id: AI_PARTICIPANT_2_ID,
        actor_kind: "AI",
        content: "AI two",
      },
      {
        ...HUMAN_TRANSCRIPT,
        utterance_id: "00000000-0000-4000-8000-000000000024",
        sequence: 8,
        action_id: null,
        participant_id: AI_PARTICIPANT_3_ID,
        actor_kind: "AI",
        content: "AI three",
      },
    ];

    await renderRestoredSession(snapshot, items);
    const transcript = screen.getByTestId("confirmed-transcript");
    expect(within(transcript).getByText("你")).toBeInTheDocument();
    expect(within(transcript).getByText("AI 候选人 1")).toBeInTheDocument();
    expect(within(transcript).getByText("AI 候选人 2")).toBeInTheDocument();
    expect(within(transcript).getByText("AI 候选人 3")).toBeInTheDocument();
    expect(within(transcript).getAllByText("个人陈述")).toHaveLength(4);
    const exact = within(transcript).getByTestId(
      `utterance-content-${HUMAN_TRANSCRIPT.utterance_id}`,
    );
    expect(exact.textContent).toBe(items[0]?.content);
    expect(exact).toHaveClass("whitespace-pre-wrap");
    expect(
      within(transcript).queryByText("强势控场者"),
    ).not.toBeInTheDocument();
    expect(exact.querySelector("strong")).toBeNull();
    expect(transcript).not.toHaveAttribute("aria-live", "assertive");
  });

  it("derives AI waiting and one interrupted notice from public grant facts", async () => {
    const aiFloor = discussionSnapshot(AI_PARTICIPANT_ID);
    const { realtime, rendered } = await renderRestoredSession(aiFloor);
    act(() => realtime.options().onConnectionChange("connected"));
    expect(screen.getByText("AI 候选人 1 正在准备发言…")).toBeInTheDocument();

    const otherGrant: TranscriptUtterance = {
      ...HUMAN_TRANSCRIPT,
      utterance_id: "00000000-0000-4000-8000-000000000025",
      sequence: 5,
      action_id: null,
      participant_id: AI_PARTICIPANT_ID,
      actor_kind: "AI",
      floor_grant_id: SECOND_GRANT_ID,
      content: "other grant",
    };
    act(() => realtime.options().onEvent(utteranceEvent(otherGrant)));
    expect(screen.getByText("AI 候选人 1 正在准备发言…")).toBeInTheDocument();

    const matching = {
      ...otherGrant,
      utterance_id: "00000000-0000-4000-8000-000000000026",
      sequence: 6,
      floor_grant_id: GRANT_ID,
    };
    act(() => realtime.options().onEvent(utteranceEvent(matching)));
    expect(
      screen.queryByText("AI 候选人 1 正在准备发言…"),
    ).not.toBeInTheDocument();

    act(() =>
      realtime.options().onRecoveryBundle({
        snapshot: { ...aiFloor, last_sequence: 6 },
        transcript: [],
      }),
    );
    act(() =>
      realtime.options().onEvent({
        schema_version: 2,
        type: "floor.released",
        session_id: SESSION_ID,
        sequence: 7,
        occurred_at: "2026-08-16T00:02:00Z",
        action_id: null,
        payload: {
          grant_id: GRANT_ID,
          participant_id: AI_PARTICIPANT_ID,
          phase: "OPENING_STATEMENTS",
          reason_code: "INTERRUPTED",
        },
      }),
    );
    expect(
      screen.getAllByText("这次 AI 发言未完成，讨论将继续。"),
    ).toHaveLength(1);
    expect(rendered.container.textContent).not.toMatch(
      /provider|model|runtime|retry/i,
    );
  });

  it("follows new confirmed speech only when the reader is near the bottom", async () => {
    const snapshot = discussionSnapshot(null);
    const { realtime } = await renderRestoredSession(snapshot, [
      HUMAN_TRANSCRIPT,
    ]);
    const transcript = screen.getByTestId("confirmed-transcript-list");
    const scrollTo = vi.fn();
    Object.defineProperties(transcript, {
      scrollHeight: { configurable: true, value: 100 },
      scrollTop: { configurable: true, value: 75, writable: true },
      clientHeight: { configurable: true, value: 20 },
      scrollTo: { configurable: true, value: scrollTo },
    });
    const nearItem: TranscriptUtterance = {
      ...HUMAN_TRANSCRIPT,
      utterance_id: "00000000-0000-4000-8000-000000000027",
      sequence: 6,
      action_id: null,
      participant_id: AI_PARTICIPANT_ID,
      actor_kind: "AI",
    };

    act(() => realtime.options().onEvent(utteranceEvent(nearItem)));
    expect(scrollTo).toHaveBeenCalledWith({ top: 100 });

    scrollTo.mockClear();
    transcript.scrollTop = 0;
    act(() =>
      realtime.options().onEvent(
        utteranceEvent({
          ...nearItem,
          utterance_id: "00000000-0000-4000-8000-000000000028",
          sequence: 7,
        }),
      ),
    );
    expect(scrollTo).not.toHaveBeenCalled();
  });

  it("creates, connects, and aborts a minimal session", async () => {
    installQuestionDiscovery();
    mockedCreateSession.mockResolvedValue({
      data: CREATED,
      response: new Response(null, { status: 201 }),
    });
    const realtime = installRealtimeDouble();

    render(
      <SessionPanel apiClient={API_CLIENT} baseUrl="http://localhost:8000" />,
    );
    await screen.findByRole("button", { name: "创建文字会话" });
    fireEvent.click(screen.getByRole("button", { name: "创建文字会话" }));

    expect((await screen.findAllByText("未开始")).length).toBeGreaterThan(0);
    expect(mockedCreateSession).toHaveBeenCalledWith(
      API_CLIENT,
      QUESTION_VERSION_ID,
    );
    expect(mockedGetQuestion).toHaveBeenCalledWith(
      API_CLIENT,
      QUESTION_VERSION_ID,
    );
    expect(
      await screen.findByText(QUESTION_DETAIL.scenario),
    ).toBeInTheDocument();
    expect(screen.queryByTestId("question-version-id")).toBeNull();
    expect(new URL(window.location.href).searchParams.get("session_id")).toBe(
      SESSION_ID,
    );
    expect(realtime.start).toHaveBeenCalledOnce();

    realtime
      .options()
      .onConnectionChange("connected" satisfies RealtimeConnectionState);
    expect(
      await screen.findByRole("button", { name: "开始讨论" }),
    ).toBeEnabled();
    fireEvent.click(await screen.findByRole("button", { name: "结束会话" }));
    expect(realtime.abort).toHaveBeenCalledOnce();

    realtime.options().onEvent({
      schema_version: 1,
      type: "session.state_changed",
      session_id: SESSION_ID,
      sequence: 2,
      occurred_at: "2026-08-16T00:00:01Z",
      action_id: ACTION_ID,
      payload: { previous_status: "CREATED", status: "ABORTED_USER" },
    } satisfies FormalSessionEvent);
    expect((await screen.findAllByText("已结束")).length).toBeGreaterThan(0);
  });

  it("starts a session and projects authoritative phase timing from v2 events", async () => {
    installQuestionDiscovery();
    mockedCreateSession.mockResolvedValue({
      data: CREATED,
      response: new Response(null, { status: 201 }),
    });
    const realtime = installRealtimeDouble();

    render(
      <SessionPanel apiClient={API_CLIENT} baseUrl="http://localhost:8000" />,
    );
    fireEvent.click(
      await screen.findByRole("button", { name: "创建文字会话" }),
    );
    await screen.findAllByText("未开始");

    realtime
      .options()
      .onConnectionChange("connected" satisfies RealtimeConnectionState);
    await waitFor(() =>
      expect(screen.getByRole("button", { name: "开始讨论" })).toBeEnabled(),
    );
    fireEvent.click(screen.getByRole("button", { name: "开始讨论" }));
    expect(realtime.startSession).toHaveBeenCalledOnce();

    realtime.options().onEvent({
      schema_version: 2,
      type: "session.state_changed",
      session_id: SESSION_ID,
      sequence: 2,
      occurred_at: PREPARATION.updated_at,
      action_id: ACTION_ID,
      payload: {
        previous_status: "CREATED",
        status: "PREPARATION",
        trigger: "USER_START",
        phase_started_at: PREPARATION.phase_started_at,
        phase_deadline_at: PREPARATION.phase_deadline_at,
      },
    } satisfies FormalSessionEvent);

    expect((await screen.findAllByText("准备")).length).toBeGreaterThan(0);
    expect(screen.queryByTestId("phase-deadline")).toBeNull();
    expect(screen.getByRole("button", { name: "结束会话" })).toBeEnabled();
  });

  it("reloads the authoritative REST snapshot from the session URL", async () => {
    window.history.replaceState({}, "", `/?session_id=${SESSION_ID}`);
    mockedGetSessionSnapshot.mockResolvedValue({
      data: ABORTED,
      response: new Response(null, { status: 200 }),
    });
    mockedGetQuestion.mockResolvedValue({
      data: QUESTION_DETAIL,
      response: new Response(null, { status: 200 }),
    });
    const realtime = installRealtimeDouble();

    render(
      <SessionPanel apiClient={API_CLIENT} baseUrl="http://localhost:8000" />,
    );

    expect((await screen.findAllByText("已结束")).length).toBeGreaterThan(0);
    expect(mockedGetSessionSnapshot).toHaveBeenCalledWith(
      API_CLIENT,
      SESSION_ID,
    );
    expect(mockedCreateRealtime).toHaveBeenCalledWith(
      expect.objectContaining({ snapshot: ABORTED }),
    );
    expect(realtime.start).toHaveBeenCalledOnce();
    expect(mockedGetQuestion).toHaveBeenCalledWith(
      API_CLIENT,
      QUESTION_VERSION_ID,
    );
    expect(screen.getByText(QUESTION_DETAIL.objective)).toBeInTheDocument();
  });

  it("projects a floor grant and restores the same safe owner from snapshot", async () => {
    const opening: SessionSnapshot = {
      ...CREATED,
      status: "OPENING_STATEMENTS",
      phase_started_at: "2026-08-16T00:01:00Z",
      phase_deadline_at: "2026-08-16T00:05:00Z",
      last_sequence: 3,
    };
    window.history.replaceState({}, "", `/?session_id=${SESSION_ID}`);
    mockedGetSessionSnapshot.mockResolvedValue({
      data: opening,
      response: new Response(null, { status: 200 }),
    });
    mockedGetQuestion.mockResolvedValue({
      data: QUESTION_DETAIL,
      response: new Response(null, { status: 200 }),
    });
    const realtime = installRealtimeDouble();

    render(
      <SessionPanel apiClient={API_CLIENT} baseUrl="http://localhost:8000" />,
    );
    expect(await screen.findByText("正在安排下一位发言者")).toBeInTheDocument();

    realtime.options().onEvent({
      schema_version: 1,
      type: "floor.granted",
      session_id: SESSION_ID,
      sequence: 4,
      occurred_at: "2026-08-16T00:01:10Z",
      action_id: ACTION_ID,
      payload: {
        grant_id: GRANT_ID,
        decision_id: DECISION_ID,
        participant_id: AI_PARTICIPANT_ID,
        phase: "OPENING_STATEMENTS",
        opportunity_id: null,
        reason_code: "FIRST_OPPORTUNITY",
        policy_version: "v0.1-floor-1",
      },
    } satisfies FormalSessionEvent);

    expect(
      await screen.findByText("当前发言：AI 候选人 1"),
    ).toBeInTheDocument();
    expect(screen.getByText("发言权已授予")).toBeInTheDocument();
    expect(screen.getByText("优先安排尚未发言的参与者")).toBeInTheDocument();

    realtime.options().onRecoveryBundle({
      snapshot: {
        ...opening,
        last_sequence: 4,
        floor: {
          ...opening.floor,
          current_grant: {
            grant_id: GRANT_ID,
            participant_id: AI_PARTICIPANT_ID,
            phase: "OPENING_STATEMENTS",
            reason_code: "FIRST_OPPORTUNITY",
            granted_at: "2026-08-16T00:01:10Z",
          },
          latest_event: {
            type: "floor.granted",
            sequence: 4,
            occurred_at: "2026-08-16T00:01:10Z",
            phase: "OPENING_STATEMENTS",
            reason_code: "FIRST_OPPORTUNITY",
            grant_id: GRANT_ID,
            participant_id: AI_PARTICIPANT_ID,
            intervention_id: null,
            intervention_kind: null,
          },
        },
      },
      transcript: [],
    });
    expect(
      await screen.findByText("当前发言：AI 候选人 1"),
    ).toBeInTheDocument();
  });

  it("shows safe realtime errors and closes the connection on unmount", async () => {
    installQuestionDiscovery();
    mockedCreateSession.mockResolvedValue({
      data: CREATED,
      response: new Response(null, { status: 201 }),
    });
    const realtime = installRealtimeDouble();
    const rendered = render(
      <SessionPanel apiClient={API_CLIENT} baseUrl="http://localhost:8000" />,
    );
    await screen.findByRole("button", { name: "创建文字会话" });
    fireEvent.click(screen.getByRole("button", { name: "创建文字会话" }));
    await waitFor(() => expect(realtime.start).toHaveBeenCalledOnce());

    realtime.options().onError("实时连接暂时不可用，请稍后重试。");
    expect(
      await screen.findByText("实时连接暂时不可用，请稍后重试。"),
    ).toBeInTheDocument();

    rendered.unmount();
    expect(realtime.stop).toHaveBeenCalledOnce();
  });

  it("shows an explicit empty state when no selectable questions exist", async () => {
    installQuestionDiscovery([]);
    render(
      <SessionPanel apiClient={API_CLIENT} baseUrl="http://localhost:8000" />,
    );

    expect(
      await screen.findByText("当前没有可用于新训练的题目。"),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "创建文字会话" }),
    ).not.toBeInTheDocument();
  });

  it("uses the exact explicitly selected immutable version", async () => {
    const second = {
      ...QUESTION_SUMMARY,
      id: "21000000-0000-4000-8000-000000000002",
      version_number: 2,
      title: "第二版本",
    };
    installQuestionDiscovery([QUESTION_SUMMARY, second]);
    mockedCreateSession.mockResolvedValue({
      data: { ...CREATED, question_version_id: second.id },
      response: new Response(null, { status: 201 }),
    });
    installRealtimeDouble();
    render(
      <SessionPanel apiClient={API_CLIENT} baseUrl="http://localhost:8000" />,
    );

    fireEvent.change(await screen.findByLabelText("选择训练题目"), {
      target: { value: second.id },
    });
    fireEvent.click(screen.getByRole("button", { name: "创建文字会话" }));

    await waitFor(() =>
      expect(mockedCreateSession).toHaveBeenCalledWith(API_CLIENT, second.id),
    );
  });

  it("shows a safe error when question discovery fails", async () => {
    mockedListQuestions.mockRejectedValue(
      new Error("private failure sentinel"),
    );
    render(
      <SessionPanel apiClient={API_CLIENT} baseUrl="http://localhost:8000" />,
    );

    expect(
      await screen.findByText("无法加载训练题目，请稍后重试。"),
    ).toBeInTheDocument();
    expect(document.body.textContent).not.toContain("private failure sentinel");
  });

  it("renders only safe public question content", async () => {
    installQuestionDiscovery();
    mockedCreateSession.mockResolvedValue({
      data: CREATED,
      response: new Response(null, { status: 201 }),
    });
    installRealtimeDouble();
    const rendered = render(
      <SessionPanel apiClient={API_CLIENT} baseUrl="http://localhost:8000" />,
    );
    fireEvent.click(
      await screen.findByRole("button", { name: "创建文字会话" }),
    );

    expect(await screen.findByText("讨论情境")).toBeInTheDocument();
    expect(screen.getByText("可选方案")).toBeInTheDocument();
    expect(rendered.container.textContent).not.toContain(
      "P1_2C_PRIVATE_SENTINEL_DO_NOT_DISCLOSE",
    );
  });

  it("composes one workspace and preserves presentation state across same-session recovery", async () => {
    const snapshot = discussionSnapshot(HUMAN_PARTICIPANT_ID);
    const { realtime, rendered } = await renderRestoredSession(snapshot);
    act(() => realtime.options().onConnectionChange("connected"));

    const notes = await screen.findByRole("textbox", {
      name: "我的思路 / 私人笔记",
    });
    const draft = screen.getByLabelText("发言草稿");
    fireEvent.change(notes, { target: { value: "same-session notes" } });
    fireEvent.change(draft, { target: { value: "same-session draft" } });
    fireEvent.click(screen.getByRole("tab", { name: "题目" }));
    expect(screen.getByRole("tab", { name: "题目" })).toHaveAttribute(
      "aria-selected",
      "true",
    );

    const authorityCounts = {
      question: mockedGetQuestion.mock.calls.length,
      realtime: mockedCreateRealtime.mock.calls.length,
      snapshot: mockedGetSessionSnapshot.mock.calls.length,
      transcript: mockedLoadSessionTranscript.mock.calls.length,
    };
    fireEvent.click(screen.getByRole("tab", { name: "进程" }));
    fireEvent.click(screen.getByRole("tab", { name: "讨论" }));
    fireEvent.click(screen.getByRole("tab", { name: "题目" }));
    expect({
      question: mockedGetQuestion.mock.calls.length,
      realtime: mockedCreateRealtime.mock.calls.length,
      snapshot: mockedGetSessionSnapshot.mock.calls.length,
      transcript: mockedLoadSessionTranscript.mock.calls.length,
    }).toEqual(authorityCounts);

    act(() => {
      realtime.options().onHumanPendingChange({
        action_id: ACTION_ID,
        floor_grant_id: GRANT_ID,
        content: "pending remains",
      });
      realtime.options().onRejectedHumanUtterance({
        action_id: ACTION_ID,
        floor_grant_id: GRANT_ID,
        content: "rejected remains",
        reason: "ACTION_ID_CONFLICT",
      });
      realtime.options().onRecoveryBundle({ snapshot, transcript: [] });
    });

    expect(notes).toHaveValue("same-session notes");
    expect(draft).toHaveValue("same-session draft");
    expect(screen.getByRole("tab", { name: "题目" })).toHaveAttribute(
      "aria-selected",
      "true",
    );
    expect(screen.getByTestId("human-pending-content")).toHaveTextContent(
      "pending remains",
    );
    expect(screen.getByTestId("rejected-human-content")).toHaveTextContent(
      "rejected remains",
    );

    const replacement = {
      ...snapshot,
      id: "00000000-0000-4000-8000-000000000099",
      question_version_id: "21000000-0000-4000-8000-000000000099",
    };
    act(() =>
      realtime
        .options()
        .onRecoveryBundle({ snapshot: replacement, transcript: [] }),
    );
    expect(notes).toHaveValue("");
    expect(screen.getByRole("tab", { name: "讨论" })).toHaveAttribute(
      "aria-selected",
      "true",
    );
    expect(screen.getByText("正在加载题目内容…")).toBeInTheDocument();
    expect(rendered.container.textContent).not.toContain(QUESTION_DETAIL.title);
  });

  it("keeps bound Question load failure stable after the generic error clears", async () => {
    window.history.replaceState({}, "", `/?session_id=${SESSION_ID}`);
    mockedGetSessionSnapshot.mockResolvedValue({
      data: CREATED,
      response: new Response(null, { status: 200 }),
    });
    mockedLoadSessionTranscript.mockResolvedValue([]);
    mockedGetQuestion.mockResolvedValue({
      error: {
        error: {
          code: "INTERNAL_ERROR",
          message: "Question unavailable",
          request_id: "00000000-0000-4000-8000-000000000097",
        },
      },
      response: new Response(null, { status: 503 }),
    });
    const realtime = installRealtimeDouble();

    render(
      <SessionPanel apiClient={API_CLIENT} baseUrl="http://localhost:8000" />,
    );
    expect(
      await screen.findByText("题目内容暂时无法加载，讨论记录仍可继续查看"),
    ).toBeInTheDocument();
    expect(mockedGetQuestion).toHaveBeenCalledTimes(1);

    act(() => {
      realtime.options().onError("temporary generic error");
      realtime.options().onConnectionChange("connected");
    });
    expect(screen.queryByText("temporary generic error")).toBeNull();
    expect(
      screen.getByText("题目内容暂时无法加载，讨论记录仍可继续查看"),
    ).toBeInTheDocument();
  });

  it("derives historical missing binding without a Question detail call", async () => {
    await renderRestoredSession({ ...CREATED, question_version_id: null });

    expect(
      await screen.findByText("此历史会话没有可展示的题目内容"),
    ).toBeInTheDocument();
    expect(mockedGetQuestion).not.toHaveBeenCalled();
    expect(
      screen.queryByText("题目内容暂时无法加载，讨论记录仍可继续查看"),
    ).toBeNull();
  });

  it("replaces stale unavailable Question state after a later workspace load succeeds", async () => {
    const nextSessionId = "00000000-0000-4000-8000-000000000098";
    const nextQuestionId = "21000000-0000-4000-8000-000000000098";
    const nextQuestion = {
      ...QUESTION_DETAIL,
      id: nextQuestionId,
      title: "新的工作区题目",
    };
    const nextQuestionLoad = deferred<{
      data: QuestionDetail;
      response: Response;
    }>();
    mockedGetSessionSnapshot
      .mockResolvedValueOnce({
        data: CREATED,
        response: new Response(null, { status: 200 }),
      })
      .mockResolvedValueOnce({
        data: {
          ...CREATED,
          id: nextSessionId,
          question_version_id: nextQuestionId,
        },
        response: new Response(null, { status: 200 }),
      });
    mockedLoadSessionTranscript.mockResolvedValue([]);
    mockedGetQuestion
      .mockResolvedValueOnce({
        error: {
          error: {
            code: "INTERNAL_ERROR",
            message: "Question unavailable",
            request_id: "00000000-0000-4000-8000-000000000099",
          },
        },
        response: new Response(null, { status: 503 }),
      })
      .mockReturnValueOnce(nextQuestionLoad.promise);
    const realtime = installRealtimeDouble();
    window.history.replaceState({}, "", `/?session_id=${SESSION_ID}`);

    const rendered = render(
      <SessionPanel apiClient={API_CLIENT} baseUrl="http://localhost:8000" />,
    );
    expect(
      await screen.findByText("题目内容暂时无法加载，讨论记录仍可继续查看"),
    ).toBeInTheDocument();

    window.history.replaceState({}, "", `/?session_id=${nextSessionId}`);
    const nextApiClient = { unit: "next" } as unknown as ApiClient;
    rendered.rerender(
      <SessionPanel
        apiClient={nextApiClient}
        baseUrl="http://localhost:8000"
      />,
    );
    await waitFor(() =>
      expect(mockedGetQuestion).toHaveBeenLastCalledWith(
        nextApiClient,
        nextQuestionId,
      ),
    );
    expect(screen.getByText("正在加载题目内容…")).toBeInTheDocument();

    nextQuestionLoad.resolve({
      data: nextQuestion,
      response: new Response(null, { status: 200 }),
    });
    expect(
      (await screen.findAllByText(nextQuestion.title)).length,
    ).toBeGreaterThan(0);
    expect(
      screen.queryByText("题目内容暂时无法加载，讨论记录仍可继续查看"),
    ).toBeNull();
    expect(realtime.stop).toHaveBeenCalled();
  });

  it("removes raw engineering diagnostics from rendered product content", async () => {
    const { rendered } = await renderRestoredSession(PREPARATION);

    for (const testId of [
      "session-id",
      "question-version-id",
      "session-sequence",
      "phase-deadline",
    ]) {
      expect(screen.queryByTestId(testId)).toBeNull();
    }
    expect(rendered.container.textContent).not.toContain(SESSION_ID);
    expect(rendered.container.textContent).not.toContain(QUESTION_VERSION_ID);
    expect(rendered.container.textContent).not.toContain(
      PREPARATION.phase_deadline_at,
    );
    expect(rendered.container.textContent).not.toContain(GRANT_ID);
  });
});
