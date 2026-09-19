import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  createApiClient,
  getCurrentUser,
  getReport,
  logoutUser,
} from "@/lib/api/client";

import ReportPageClient from "./report-page-client";

vi.mock("@/lib/api/client", async () => {
  const actual =
    await vi.importActual<typeof import("@/lib/api/client")>(
      "@/lib/api/client",
    );
  return {
    ...actual,
    createApiClient: vi.fn(() => ({ client: "report-route" })),
    getCurrentUser: vi.fn(),
    getReport: vi.fn(),
    logoutUser: vi.fn(),
  };
});

const pushRoute = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: pushRoute }),
}));

const mockedCreateApiClient = vi.mocked(createApiClient);
const mockedGetCurrentUser = vi.mocked(getCurrentUser);
const mockedGetReport = vi.mocked(getReport);
const mockedLogoutUser = vi.mocked(logoutUser);
const sessionId = "30000000-0000-4000-8000-000000000001";
const user = {
  id: "10000000-0000-4000-8000-000000000001",
  username: "report_owner",
};

const metadata = {
  report_id: "40000000-0000-4000-8000-000000000001",
  session_id: sessionId,
  status: "COMPLETED" as const,
  report_schema_version: 1,
  derivation_version: "basic-report/v1",
  source_through_sequence: 3,
  created_at: "2026-09-12T00:00:00Z",
  completed_at: "2026-09-12T00:01:00Z",
};

const completedReport = {
  report: metadata,
  content: {
    overview: {
      session_status: "COMPLETED" as const,
      question: {
        id: "21000000-0000-4000-8000-000000000001",
        question_template_id: "20000000-0000-4000-8000-000000000001",
        version_number: 1,
        title: "资源安排",
        question_type: "RESOURCE_ALLOCATION",
        background_domain: "GENERAL",
        difficulty: "STANDARD",
        estimated_minutes: 25,
        scenario: "资源有限，需要形成共同安排。",
        objective: "形成可执行方案。",
        hard_constraints: [],
        soft_constraints: [],
        stakeholders: [],
        options: [],
      },
      participant_count: 4,
      human_utterance_count: 2,
      ai_utterance_count: 3,
      total_utterance_count: 5,
      covered_phases: ["OPENING_STATEMENTS" as const],
      summary: "共同方案逐步收敛。",
    },
    strengths: [],
    improvements: [],
    priority_improvement: "下次更早明确共同标准。",
  },
};

function response(data: unknown, status = 200) {
  return {
    data,
    response: new Response(null, { status }),
  } as Awaited<ReturnType<typeof getReport>>;
}

describe("ReportPageClient", () => {
  beforeEach(() => {
    mockedGetCurrentUser.mockResolvedValue({
      data: user,
      response: new Response(null, { status: 200 }),
    });
    mockedGetReport.mockResolvedValue(response(completedReport));
    mockedLogoutUser.mockResolvedValue({
      data: undefined,
      response: new Response(null, { status: 204 }),
    });
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  it("bootstraps route-local auth and renders the completed report inside the shared Shell", async () => {
    render(
      <ReportPageClient
        baseUrl="http://localhost:8000"
        sessionId={sessionId}
      />,
    );

    expect(screen.getByText("正在确认账户…")).toBeInTheDocument();
    expect(await screen.findByTestId("studio-shell")).toBeInTheDocument();
    expect(screen.getByTestId("current-username")).toHaveTextContent(
      "report_owner",
    );
    expect(screen.getByRole("main")).toHaveAttribute(
      "data-content-scroll-mode",
      "page",
    );
    expect(
      within(screen.getByRole("navigation", { name: "桌面主导航" })).getByRole(
        "button",
        { name: /训练报告/ },
      ),
    ).toHaveAttribute("aria-current", "page");
    expect(
      await screen.findByRole("heading", { name: "练习概览" }),
    ).toBeVisible();
    expect(mockedCreateApiClient).toHaveBeenCalledWith("http://localhost:8000");
  });

  it("routes simulation, Settings, and logout through the authenticated report Shell", async () => {
    render(
      <ReportPageClient
        baseUrl="http://localhost:8000"
        sessionId={sessionId}
      />,
    );
    const desktopNavigation = await screen.findByRole("navigation", {
      name: "桌面主导航",
    });

    fireEvent.click(
      within(desktopNavigation).getByRole("button", { name: "完整模拟" }),
    );
    expect(pushRoute).toHaveBeenCalledWith("/");

    pushRoute.mockClear();
    fireEvent.click(
      within(desktopNavigation).getByRole("button", { name: "设置" }),
    );
    expect(pushRoute).toHaveBeenCalledWith("/settings");

    pushRoute.mockClear();
    fireEvent.click(screen.getByRole("button", { name: "退出登录" }));
    await waitFor(() => expect(mockedLogoutUser).toHaveBeenCalledOnce());
    expect(pushRoute).toHaveBeenCalledWith("/");
  });

  it.each([
    ["REQUESTED", "报告已进入生成队列"],
    ["RUNNING", "报告正在生成"],
    ["FAILED", "本次报告暂时无法完成"],
  ] as const)(
    "keeps %s report state inside the shared Shell",
    async (status, copy) => {
      mockedGetReport.mockResolvedValueOnce(
        response({
          report: { ...metadata, status, completed_at: null },
          content: null,
        }),
      );

      render(
        <ReportPageClient
          baseUrl="http://localhost:8000"
          sessionId={sessionId}
        />,
      );

      expect(await screen.findByText(copy)).toBeVisible();
      expect(screen.getByTestId("studio-shell")).toBeInTheDocument();
      expect(screen.getByRole("main")).toContainElement(screen.getByText(copy));
    },
  );

  it("uses the product entry language for unauthenticated and unconfigured routes", async () => {
    mockedGetCurrentUser.mockResolvedValueOnce({
      error: {},
      response: new Response(null, { status: 401 }),
    } as Awaited<ReturnType<typeof getCurrentUser>>);
    const rendered = render(
      <ReportPageClient
        baseUrl="http://localhost:8000"
        sessionId={sessionId}
      />,
    );

    expect(
      await screen.findByRole("heading", { name: "登录后查看训练报告" }),
    ).toBeVisible();
    expect(screen.getByTestId("entry-shell")).toBeInTheDocument();
    expect(screen.queryByTestId("current-username")).toBeNull();
    expect(screen.getByRole("link", { name: "返回登录" })).toHaveAttribute(
      "href",
      "/",
    );

    rendered.rerender(
      <ReportPageClient baseUrl={null} sessionId={sessionId} />,
    );
    expect(
      await screen.findByRole("heading", { name: "报告服务暂不可用" }),
    ).toBeVisible();
    expect(screen.getByTestId("entry-shell")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "返回登录" })).toHaveAttribute(
      "href",
      "/",
    );
  });
});
