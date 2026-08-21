import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

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
} from "@/lib/realtime/client";
import type { FormalSessionEvent } from "@/lib/realtime/contract";

import SessionPanel from "./session-panel";

vi.mock("@/lib/api/client", () => ({
  createSession: vi.fn(),
  getQuestion: vi.fn(),
  getSessionSnapshot: vi.fn(),
  listQuestions: vi.fn(),
}));
vi.mock("@/lib/realtime/client", () => ({
  createSessionRealtimeClient: vi.fn(),
}));

const SESSION_ID = "00000000-0000-4000-8000-000000000010";
const ACTION_ID = "00000000-0000-4000-8000-000000000011";
const QUESTION_VERSION_ID = "21000000-0000-4000-8000-000000000001";
const QUESTION_TEMPLATE_ID = "20000000-0000-4000-8000-000000000001";
const HUMAN_PARTICIPANT_ID = "00000000-0000-4000-8000-000000000012";
const AI_PARTICIPANT_ID = "00000000-0000-4000-8000-000000000013";
const GRANT_ID = "00000000-0000-4000-8000-000000000014";
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

const mockedCreateSession = vi.mocked(createSession);
const mockedGetQuestion = vi.mocked(getQuestion);
const mockedGetSessionSnapshot = vi.mocked(getSessionSnapshot);
const mockedListQuestions = vi.mocked(listQuestions);
const mockedCreateRealtime = vi.mocked(createSessionRealtimeClient);

function installRealtimeDouble() {
  const start = vi.fn();
  const startSession = vi.fn(() => ACTION_ID);
  const abort = vi.fn(() => ACTION_ID);
  const stop = vi.fn();
  let options: Parameters<typeof createSessionRealtimeClient>[0] | undefined;
  mockedCreateRealtime.mockImplementation((candidate) => {
    options = candidate;
    return { start, startSession, abort, stop };
  });
  return {
    start,
    startSession,
    abort,
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

describe("SessionPanel", () => {
  afterEach(() => {
    cleanup();
    window.history.replaceState({}, "", "/");
    vi.clearAllMocks();
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

    expect(await screen.findByText("已创建")).toBeInTheDocument();
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
    expect(screen.getByTestId("question-version-id")).toHaveTextContent(
      QUESTION_VERSION_ID,
    );
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
    expect(await screen.findByText("已由用户结束")).toBeInTheDocument();
    expect(screen.getByTestId("session-sequence")).toHaveTextContent("2");
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
    await screen.findByText("已创建");

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

    expect(await screen.findByText("进行中")).toBeInTheDocument();
    expect(screen.getByTestId("phase-label")).toHaveTextContent("准备");
    expect(screen.getByTestId("phase-deadline")).toHaveTextContent(
      PREPARATION.phase_deadline_at!,
    );
    expect(screen.getByTestId("session-sequence")).toHaveTextContent("2");
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

    expect(await screen.findByText("已由用户结束")).toBeInTheDocument();
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
    expect(await screen.findByTestId("floor-owner")).toHaveTextContent("暂无");

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

    expect(await screen.findByTestId("floor-owner")).toHaveTextContent(
      "AI 候选人 1",
    );
    expect(screen.getByTestId("floor-lifecycle")).toHaveTextContent(
      "发言权已授予",
    );
    expect(screen.getByTestId("floor-reason")).toHaveTextContent(
      "优先安排尚未发言的参与者",
    );
    expect(screen.getByTestId("session-sequence")).toHaveTextContent("4");

    realtime.options().onSnapshot({
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
    });
    expect(await screen.findByTestId("floor-owner")).toHaveTextContent(
      "AI 候选人 1",
    );
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

    expect(await screen.findByText("情境")).toBeInTheDocument();
    expect(screen.getByText("可选方案")).toBeInTheDocument();
    expect(rendered.container.textContent).not.toContain(
      "P1_2C_PRIVATE_SENTINEL_DO_NOT_DISCLOSE",
    );
  });
});
