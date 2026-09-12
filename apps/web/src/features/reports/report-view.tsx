"use client";

import { useEffect, useState } from "react";

import { getReport, type ApiClient } from "@/lib/api/client";

import {
  parseReportView,
  type EvidenceCard,
  type ReportView as ReportData,
} from "./report-contract";

type State =
  | { kind: "loading"; sessionId: string }
  | { kind: "unauthenticated"; sessionId: string }
  | { kind: "not-found"; sessionId: string }
  | { kind: "error"; sessionId: string }
  | { kind: "ready"; sessionId: string; report: ReportData };

const phaseLabels: Record<string, string> = {
  OPENING_STATEMENTS: "开场陈述",
  EXPLORATION: "方案探索",
  CONFLICT_AND_EVALUATION: "分歧评估",
  CONVERGENCE: "收敛决策",
  FINAL_SUMMARY: "最终总结",
};

function Evidence({ item }: { item: EvidenceCard }) {
  return (
    <article className="rounded-2xl border border-neutral-200 bg-white p-5 shadow-sm">
      <p className="mb-2 text-sm font-medium text-neutral-500">
        {phaseLabels[item.phase]} · 发言事件 #{item.source_event_sequence}
      </p>
      <blockquote className="whitespace-pre-wrap border-l-2 border-emerald-600 pl-4 text-lg text-neutral-900">
        {item.quote}
      </blockquote>
      <p className="mt-3 text-neutral-700">{item.interpretation}</p>
      <details className="mt-3 text-xs text-neutral-500">
        <summary>查看证据来源</summary>
        <p>参与者 {item.source_participant_id}</p>
        <p>发言 {item.source_utterance_id}</p>
        <p>置信度 {item.confidence}</p>
      </details>
    </article>
  );
}

export default function ReportView({
  apiClient,
  sessionId,
}: {
  apiClient: ApiClient;
  sessionId: string;
}) {
  const [state, setState] = useState<State>({ kind: "loading", sessionId });
  useEffect(() => {
    let active = true;
    void getReport(apiClient, sessionId)
      .then((result) => {
        if (!active) return;
        if (result.response.status === 401)
          return setState({ kind: "unauthenticated", sessionId });
        if (result.response.status === 404)
          return setState({ kind: "not-found", sessionId });
        if (!result.data) return setState({ kind: "error", sessionId });
        try {
          setState({
            kind: "ready",
            sessionId,
            report: parseReportView(result.data),
          });
        } catch {
          setState({ kind: "error", sessionId });
        }
      })
      .catch(() => {
        if (active) setState({ kind: "error", sessionId });
      });
    return () => {
      active = false;
    };
  }, [apiClient, sessionId]);

  if (state.sessionId !== sessionId || state.kind === "loading")
    return (
      <main className="grid min-h-dvh place-items-center bg-[#f7f7f5]">
        <p>正在读取训练报告…</p>
      </main>
    );
  if (state.kind === "unauthenticated")
    return (
      <main className="grid min-h-dvh place-items-center bg-[#f7f7f5]">
        <p>请先登录后查看训练报告</p>
      </main>
    );
  if (state.kind === "not-found")
    return (
      <main className="grid min-h-dvh place-items-center bg-[#f7f7f5]">
        <p>未找到可查看的训练报告</p>
      </main>
    );
  if (state.kind === "error")
    return (
      <main className="grid min-h-dvh place-items-center bg-[#f7f7f5]">
        <p>报告暂时无法读取，请稍后重试。</p>
      </main>
    );
  const { report, content } = state.report;
  if (report.status === "REQUESTED")
    return (
      <main className="grid min-h-dvh place-items-center bg-[#f7f7f5]">
        <div>
          <h1 className="text-2xl font-semibold">报告已进入生成队列</h1>
          <p className="mt-2 text-neutral-600">完成后刷新此页面即可查看。</p>
        </div>
      </main>
    );
  if (report.status === "RUNNING")
    return (
      <main className="grid min-h-dvh place-items-center bg-[#f7f7f5]">
        <div>
          <h1 className="text-2xl font-semibold">报告正在生成</h1>
          <p className="mt-2 text-neutral-600">请稍后再回来查看。</p>
        </div>
      </main>
    );
  if (report.status === "FAILED")
    return (
      <main className="grid min-h-dvh place-items-center bg-[#f7f7f5]">
        <div>
          <h1 className="text-2xl font-semibold">本次报告暂时无法完成</h1>
          <p className="mt-2 text-neutral-600">请稍后重试或联系维护人员。</p>
        </div>
      </main>
    );
  if (!content) return null;
  const allEvidence = [...content.strengths, ...content.improvements];
  return (
    <main className="min-h-dvh bg-[#f7f7f5] px-5 py-10 text-neutral-950">
      <div className="mx-auto max-w-5xl space-y-10">
        <header>
          <p className="text-sm font-medium text-emerald-700">AI 群面训练场</p>
          <h1 className="mt-2 text-4xl font-semibold tracking-tight">
            训练报告
          </h1>
          <p className="mt-3 text-neutral-600">
            基于本次公开讨论记录形成的证据化复盘
          </p>
        </header>
        <section>
          <h2 className="text-2xl font-semibold">练习概览</h2>
          <div className="mt-4 rounded-2xl bg-neutral-900 p-6 text-white">
            <h3 className="text-xl font-medium">
              {content.overview.question.title}
            </h3>
            <p className="mt-2 text-neutral-300">
              {content.overview.question.objective}
            </p>
            <p className="mt-5">{content.overview.summary}</p>
            <p className="mt-4 text-sm text-neutral-300">
              {content.overview.participant_count} 位参与者 · 你发言{" "}
              {content.overview.human_utterance_count} 次 · AI 发言{" "}
              {content.overview.ai_utterance_count} 次 · 共{" "}
              {content.overview.total_utterance_count} 次
            </p>
            <p className="mt-2 text-sm text-neutral-300">
              覆盖阶段：
              {content.overview.covered_phases
                .map((phase) => phaseLabels[phase])
                .join("、") || "暂无"}
            </p>
          </div>
        </section>
        <section>
          <h2 className="text-2xl font-semibold">表现亮点</h2>
          <div className="mt-4 grid gap-4">
            {content.strengths.length ? (
              content.strengths.map((item) => (
                <Evidence
                  key={`${item.source_event_sequence}-${item.source_utterance_id}`}
                  item={item}
                />
              ))
            ) : (
              <p className="text-neutral-600">暂无可展示的亮点证据</p>
            )}
          </div>
        </section>
        <section>
          <h2 className="text-2xl font-semibold">改进机会</h2>
          <div className="mt-4 grid gap-4">
            {content.improvements.length ? (
              content.improvements.map((item) => (
                <Evidence
                  key={`${item.source_event_sequence}-${item.source_utterance_id}`}
                  item={item}
                />
              ))
            ) : (
              <p className="text-neutral-600">暂无可展示的改进证据</p>
            )}
          </div>
        </section>
        <section>
          <h2 className="text-2xl font-semibold">下次训练重点</h2>
          <p className="mt-4 rounded-2xl bg-emerald-700 p-6 text-xl text-white">
            {content.priority_improvement}
          </p>
        </section>
        <section>
          <h2 className="text-2xl font-semibold">证据来源</h2>
          <p className="mt-3 text-neutral-600">
            以下 {allEvidence.length}{" "}
            条卡片均保留原始发言、讨论阶段和事件序号；展示顺序按事件序号确定，不表示优劣。
          </p>
        </section>
      </div>
    </main>
  );
}
