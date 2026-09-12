import { describe, expect, it } from "vitest";

import { parseReportView } from "./report-contract";

const completed = {
  report: {
    report_id: "40000000-0000-4000-8000-000000000001",
    session_id: "30000000-0000-4000-8000-000000000001",
    status: "COMPLETED",
    report_schema_version: 1,
    derivation_version: "deterministic-v1",
    source_through_sequence: 3,
    created_at: "2026-09-12T00:00:00Z",
    completed_at: "2026-09-12T00:01:00Z",
  },
  content: {
    overview: {
      session_status: "COMPLETED",
      question: {
        id: "21000000-0000-4000-8000-000000000001",
        question_template_id: "20000000-0000-4000-8000-000000000001",
        version_number: 1,
        title: "资源安排",
        question_type: "RESOURCE_ALLOCATION",
        background_domain: "GENERAL",
        difficulty: "STANDARD",
        estimated_minutes: 25,
        scenario: "场景",
        objective: "目标",
        hard_constraints: [{ key: "BUDGET", text: "预算不超限" }],
        soft_constraints: [],
        stakeholders: [{ key: "USERS", name: "用户", description: "受影响者" }],
        options: [{ key: "A", label: "方案 A", description: "说明" }],
      },
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
} as const;

describe("parseReportView", () => {
  it("preserves exact quote and the closed public provenance surface", () => {
    const parsed = parseReportView(completed);
    expect(parsed.content?.strengths[0]?.quote).toBe("  exact source\n");
    expect(parsed.content?.strengths[0]?.source_event_sequence).toBe(2);
  });

  it("rejects extras, private lifecycle fields, and inconsistent lifecycle content", () => {
    expect(() => parseReportView({ ...completed, score: 95 })).toThrow();
    expect(() =>
      parseReportView({
        ...completed,
        report: { ...completed.report, started_at: "private" },
      }),
    ).toThrow();
    expect(() =>
      parseReportView({
        ...completed,
        report: { ...completed.report, status: "RUNNING", completed_at: null },
      }),
    ).toThrow();
  });

  it("accepts only null content for non-completed lifecycle states", () => {
    for (const status of ["REQUESTED", "RUNNING", "FAILED"] as const) {
      const parsed = parseReportView({
        report: { ...completed.report, status, completed_at: null },
        content: null,
      });
      expect(parsed.report.status).toBe(status);
      expect(parsed.content).toBeNull();
    }
  });
});
