import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ApiClient } from "@/lib/api/client";
import { getReport } from "@/lib/api/client";

import ReportView from "./report-view";

vi.mock("@/lib/api/client", async () => {
  const actual =
    await vi.importActual<typeof import("@/lib/api/client")>(
      "@/lib/api/client",
    );
  return { ...actual, getReport: vi.fn() };
});

const mockedGetReport = vi.mocked(getReport);
const client = { test: true } as unknown as ApiClient;
const sessionId = "30000000-0000-4000-8000-000000000001";

const metadata = {
  report_id: "40000000-0000-4000-8000-000000000001",
  session_id: sessionId,
  status: "COMPLETED" as const,
  report_schema_version: 1,
  derivation_version: "deterministic-v1",
  source_through_sequence: 3,
  created_at: "2026-09-12T00:00:00Z",
  completed_at: "2026-09-12T00:01:00Z",
};

const question = {
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
  hard_constraints: [{ key: "BUDGET", text: "预算不超限" }],
  soft_constraints: [],
  stakeholders: [],
  options: [],
};

function response(data: unknown, status = 200) {
  return Promise.resolve({
    data,
    response: new Response(null, { status }),
  } as Awaited<ReturnType<typeof getReport>>);
}

describe("ReportView", () => {
  beforeEach(() => mockedGetReport.mockReset());
  afterEach(cleanup);

  it("shows loading and each durable non-completed state without fake progress", async () => {
    let resolve!: (value: Awaited<ReturnType<typeof getReport>>) => void;
    mockedGetReport.mockReturnValueOnce(
      new Promise((done) => (resolve = done)),
    );
    const rendered = render(
      <ReportView apiClient={client} sessionId={sessionId} />,
    );
    expect(screen.getByText("正在读取训练报告…")).toBeInTheDocument();
    resolve(
      await response({
        report: { ...metadata, status: "REQUESTED", completed_at: null },
        content: null,
      }),
    );
    expect(await screen.findByText("报告已进入生成队列")).toBeInTheDocument();
    expect(rendered.container.textContent).not.toContain("%");

    for (const [status, copy] of [
      ["RUNNING", "报告正在生成"],
      ["FAILED", "本次报告暂时无法完成"],
    ] as const) {
      mockedGetReport.mockResolvedValueOnce(
        await response({
          report: { ...metadata, status, completed_at: null },
          content: null,
        }),
      );
      rendered.rerender(
        <ReportView apiClient={client} sessionId={`${sessionId}-${status}`} />,
      );
      expect(await screen.findByText(copy)).toBeInTheDocument();
    }
  });

  it("renders the five-part completed surface, exact quotes, and provenance", async () => {
    mockedGetReport.mockResolvedValueOnce(
      await response({
        report: metadata,
        content: {
          overview: {
            session_status: "COMPLETED",
            question,
            participant_count: 4,
            human_utterance_count: 2,
            ai_utterance_count: 3,
            total_utterance_count: 5,
            covered_phases: ["OPENING_STATEMENTS", "CONVERGENCE"],
            summary: "共同方案逐步收敛。",
          },
          strengths: [
            {
              kind: "STRENGTH",
              source_participant_id: "31000000-0000-4000-8000-000000000001",
              source_utterance_id: "32000000-0000-4000-8000-000000000001",
              source_event_sequence: 2,
              phase: "OPENING_STATEMENTS",
              quote: "  exact source\n",
              interpretation: "提出了明确约束。",
              confidence: "0.900",
            },
          ],
          improvements: [],
          priority_improvement: "下次更早明确共同标准。",
        },
      }),
    );
    const rendered = render(
      <ReportView apiClient={client} sessionId={sessionId} />,
    );

    expect(
      await screen.findByRole("heading", { name: "训练报告" }),
    ).toBeInTheDocument();
    for (const heading of [
      "练习概览",
      "表现亮点",
      "改进机会",
      "下次训练重点",
      "证据来源",
    ]) {
      expect(
        screen.getByRole("heading", { name: heading }),
      ).toBeInTheDocument();
    }
    const quote = rendered.container.querySelector("blockquote");
    expect(quote).toHaveTextContent("exact source");
    expect(quote?.textContent).toBe("  exact source\n");
    expect(quote).toHaveClass("whitespace-pre-wrap");
    expect(screen.getByText(/发言事件 #2/)).toBeInTheDocument();
    expect(screen.getByText("暂无可展示的改进证据")).toBeInTheDocument();
    expect(rendered.container.textContent).not.toMatch(
      /得分|排名|百分位|score|rank/i,
    );
  });

  it("shows nondisclosing unauthenticated and not-found states", async () => {
    mockedGetReport.mockResolvedValueOnce({
      error: {},
      response: new Response(null, { status: 401 }),
    } as Awaited<ReturnType<typeof getReport>>);
    const rendered = render(
      <ReportView apiClient={client} sessionId={sessionId} />,
    );
    expect(
      await screen.findByText("请先登录后查看训练报告"),
    ).toBeInTheDocument();

    mockedGetReport.mockResolvedValueOnce({
      error: {},
      response: new Response(null, { status: 404 }),
    } as Awaited<ReturnType<typeof getReport>>);
    rendered.rerender(
      <ReportView apiClient={client} sessionId={`${sessionId}-next`} />,
    );
    expect(
      await screen.findByText("未找到可查看的训练报告"),
    ).toBeInTheDocument();
  });
});
