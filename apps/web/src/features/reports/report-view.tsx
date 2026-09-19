"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

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
    <article className="rounded-2xl border border-slate-200/90 bg-slate-50/70 p-4 sm:p-5">
      <p className="text-xs font-semibold tracking-[0.08em] text-slate-500 uppercase">
        {phaseLabels[item.phase]} · 发言事件 #{item.source_event_sequence}
      </p>
      <blockquote
        className="report-wrap-anywhere mt-3 whitespace-pre-wrap border-l-2 border-indigo-500 pl-4 text-[0.95rem] leading-7 text-slate-950"
        data-wrap-policy="anywhere"
      >
        {item.quote}
      </blockquote>
      <p className="report-wrap-anywhere mt-3 text-sm leading-6 text-slate-600">
        {item.interpretation}
      </p>
      <details className="mt-3 border-t border-slate-200 pt-3 text-xs text-slate-500">
        <summary className="cursor-pointer font-medium text-slate-600">
          查看证据来源
        </summary>
        <div className="mt-2 space-y-1 break-all">
          <p>来源参与者 {item.source_participant_id}</p>
          <p>来源发言 {item.source_utterance_id}</p>
          <p>证据置信度 {item.confidence}</p>
        </div>
      </details>
    </article>
  );
}

function ReportStateSurface({
  eyebrow,
  heading,
  message,
  onRetry,
}: {
  eyebrow: string;
  heading: string;
  message: string;
  onRetry?: () => void;
}) {
  return (
    <section
      className="grid min-h-[24rem] place-items-center px-4 py-10"
      data-testid="report-state-surface"
    >
      <div className="w-full max-w-xl rounded-2xl border border-slate-200 bg-white p-6 shadow-[0_16px_50px_rgba(15,23,42,0.06)] sm:p-8">
        <p className="text-xs font-semibold tracking-[0.14em] text-indigo-600 uppercase">
          {eyebrow}
        </p>
        <h2 className="mt-3 text-2xl font-semibold tracking-tight text-slate-950">
          {heading}
        </h2>
        <p className="mt-3 leading-7 text-slate-600">{message}</p>
        <div className="mt-6 flex flex-wrap gap-3">
          {onRetry ? (
            <button
              className="rounded-xl bg-slate-950 px-4 py-2.5 text-sm font-semibold text-white"
              onClick={onRetry}
              type="button"
            >
              重新读取
            </button>
          ) : null}
          <Link
            className="rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm font-semibold text-slate-700"
            href="/"
          >
            返回训练大厅
          </Link>
        </div>
      </div>
    </section>
  );
}

export default function ReportView({
  apiClient,
  embedded = false,
  sessionId,
}: {
  apiClient: ApiClient;
  embedded?: boolean;
  sessionId: string;
}) {
  const [state, setState] = useState<State>({ kind: "loading", sessionId });
  const [reloadRequest, setReloadRequest] = useState(0);

  useEffect(() => {
    let active = true;
    void getReport(apiClient, sessionId)
      .then((result) => {
        if (!active) return;
        if (result.response.status === 401) {
          setState({ kind: "unauthenticated", sessionId });
          return;
        }
        if (result.response.status === 404) {
          setState({ kind: "not-found", sessionId });
          return;
        }
        if (!result.data) {
          setState({ kind: "error", sessionId });
          return;
        }
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
  }, [apiClient, reloadRequest, sessionId]);

  const retry = () => {
    setState({ kind: "loading", sessionId });
    setReloadRequest((request) => request + 1);
  };

  if (state.sessionId !== sessionId || state.kind === "loading") {
    return (
      <ReportStateSurface
        eyebrow="Training report"
        heading="正在读取训练报告…"
        message="正在同步这次训练的真实报告状态。"
      />
    );
  }
  if (state.kind === "unauthenticated") {
    return (
      <ReportStateSurface
        eyebrow="Authentication required"
        heading="请先登录后查看训练报告"
        message="当前账户状态无法读取这份报告。"
      />
    );
  }
  if (state.kind === "not-found") {
    return (
      <ReportStateSurface
        eyebrow="Report unavailable"
        heading="未找到可查看的训练报告"
        message="这次训练可能尚未完成，或报告尚未生成。"
        onRetry={retry}
      />
    );
  }
  if (state.kind === "error") {
    return (
      <ReportStateSurface
        eyebrow="Report unavailable"
        heading="报告暂时无法读取，请稍后重试。"
        message="页面没有展示服务端内部错误信息。"
        onRetry={retry}
      />
    );
  }

  const { report, content } = state.report;
  if (report.status === "REQUESTED") {
    return (
      <ReportStateSurface
        eyebrow="Report requested"
        heading="报告已进入生成队列"
        message="报告完成后，重新读取即可查看本次证据化复盘。"
        onRetry={retry}
      />
    );
  }
  if (report.status === "RUNNING") {
    return (
      <ReportStateSurface
        eyebrow="Report running"
        heading="报告正在生成"
        message="系统正在整理本次公开讨论证据，请稍后重新读取。"
        onRetry={retry}
      />
    );
  }
  if (report.status === "FAILED") {
    return (
      <ReportStateSurface
        eyebrow="Report failed"
        heading="本次报告暂时无法完成"
        message="可以稍后重新读取，或返回训练大厅。"
        onRetry={retry}
      />
    );
  }
  if (!content) return null;

  const allEvidence = [...content.strengths, ...content.improvements];
  return (
    <section className="px-4 py-5 text-slate-950 sm:px-6 sm:py-7 lg:px-8">
      <div
        className="mx-auto grid max-w-[78rem] gap-4 lg:grid-cols-12 lg:gap-5"
        data-testid="report-bento"
        data-visual-reference="demo-v2"
      >
        <header className="pb-2 lg:col-span-12">
          <p className="text-xs font-semibold tracking-[0.14em] text-indigo-600 uppercase">
            Evidence-based review
          </p>
          {!embedded ? (
            <h1 className="mt-2 text-3xl font-semibold tracking-tight">
              训练报告
            </h1>
          ) : (
            <h2 className="mt-2 text-3xl font-semibold tracking-tight">
              本次训练复盘
            </h2>
          )}
          <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">
            仅基于本次公开讨论记录形成，所有判断都可回到真实发言证据。
          </p>
        </header>

        <section
          className="rounded-2xl border border-slate-200 bg-white p-5 shadow-[0_16px_44px_rgba(15,23,42,0.05)] sm:p-6 lg:col-span-8"
          data-report-span="8"
          data-testid="report-overview"
        >
          <p className="text-xs font-semibold tracking-[0.12em] text-slate-500 uppercase">
            Practice overview
          </p>
          <h2 className="mt-2 text-xl font-semibold">练习概览</h2>
          <div className="mt-5 border-t border-slate-200 pt-5">
            <h3 className="text-xl font-semibold tracking-tight sm:text-2xl">
              {content.overview.question.title}
            </h3>
            <p className="mt-2 text-sm leading-6 text-slate-600">
              {content.overview.question.objective}
            </p>
            <p className="mt-5 text-base leading-7 text-slate-800">
              {content.overview.summary}
            </p>
            <dl className="mt-5 grid grid-cols-2 gap-3 border-t border-slate-100 pt-5 sm:grid-cols-4">
              {[
                ["参与者", content.overview.participant_count],
                ["你的发言", content.overview.human_utterance_count],
                ["AI 发言", content.overview.ai_utterance_count],
                ["全部发言", content.overview.total_utterance_count],
              ].map(([label, value]) => (
                <div key={label}>
                  <dt className="text-xs text-slate-500">{label}</dt>
                  <dd className="mt-1 text-lg font-semibold text-slate-900">
                    {value}
                  </dd>
                </div>
              ))}
            </dl>
            <p className="mt-5 text-sm leading-6 text-slate-500">
              覆盖阶段：
              {content.overview.covered_phases
                .map((phase) => phaseLabels[phase])
                .join("、") || "暂无公开发言阶段"}
            </p>
          </div>
        </section>

        <section
          className="flex flex-col rounded-2xl border border-indigo-200 bg-indigo-50 p-5 shadow-[0_16px_44px_rgba(79,70,229,0.08)] sm:p-6 lg:col-span-4"
          data-report-span="4"
          data-testid="report-priority"
        >
          <p className="text-xs font-semibold tracking-[0.12em] text-indigo-600 uppercase">
            Next focus
          </p>
          <h2 className="mt-2 text-xl font-semibold text-indigo-950">
            下次训练重点
          </h2>
          <p
            className="report-wrap-anywhere mt-6 text-lg font-semibold leading-7 text-indigo-950 sm:text-xl sm:leading-8 xl:text-2xl"
            data-testid="report-priority-copy"
            data-wrap-policy="anywhere"
          >
            {content.priority_improvement}
          </p>
          <p className="mt-auto pt-8 text-sm leading-6 text-indigo-800/75">
            来自本次报告中优先级最高的真实改进项。
          </p>
        </section>

        <section
          className="rounded-2xl border border-slate-200 bg-white p-5 shadow-[0_14px_40px_rgba(15,23,42,0.04)] sm:p-6 lg:col-span-6"
          data-report-span="6"
          data-testid="report-strengths"
        >
          <p className="text-xs font-semibold tracking-[0.12em] text-emerald-700 uppercase">
            Strengths
          </p>
          <h2 className="mt-2 text-xl font-semibold">表现亮点</h2>
          <div className="mt-5 grid gap-4">
            {content.strengths.length ? (
              content.strengths.map((item) => (
                <Evidence
                  key={`${item.source_event_sequence}-${item.source_utterance_id}`}
                  item={item}
                />
              ))
            ) : (
              <p className="rounded-xl bg-slate-50 px-4 py-5 text-sm leading-6 text-slate-600">
                暂无可展示的亮点证据
              </p>
            )}
          </div>
        </section>

        <section
          className="rounded-2xl border border-slate-200 bg-white p-5 shadow-[0_14px_40px_rgba(15,23,42,0.04)] sm:p-6 lg:col-span-6"
          data-report-span="6"
          data-testid="report-improvements"
        >
          <p className="text-xs font-semibold tracking-[0.12em] text-amber-700 uppercase">
            Improvements
          </p>
          <h2 className="mt-2 text-xl font-semibold">改进机会</h2>
          <div className="mt-5 grid gap-4">
            {content.improvements.length ? (
              content.improvements.map((item) => (
                <Evidence
                  key={`${item.source_event_sequence}-${item.source_utterance_id}`}
                  item={item}
                />
              ))
            ) : (
              <p className="rounded-xl bg-slate-50 px-4 py-5 text-sm leading-6 text-slate-600">
                暂无可展示的改进证据
              </p>
            )}
          </div>
        </section>

        <section className="rounded-2xl border border-slate-200 bg-white px-5 py-4 sm:px-6 lg:col-span-12">
          <h2 className="sr-only">证据来源</h2>
          <details className="text-sm text-slate-500">
            <summary className="cursor-pointer font-semibold text-slate-700">
              证据来源
            </summary>
            <div className="mt-3 grid gap-2 border-t border-slate-100 pt-3 sm:grid-cols-2">
              <p>共 {allEvidence.length} 条证据；展示顺序不表示优劣。</p>
              <p>
                报告版本 {report.report_schema_version} · 推导版本{" "}
                {report.derivation_version}
              </p>
              <p>证据覆盖至事件 #{report.source_through_sequence}</p>
              <p>报告完成于 {report.completed_at}</p>
            </div>
          </details>
        </section>
      </div>
    </section>
  );
}
