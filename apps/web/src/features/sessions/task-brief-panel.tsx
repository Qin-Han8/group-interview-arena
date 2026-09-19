"use client";

import type { ReactNode } from "react";

import type { QuestionDetail } from "@/lib/api/client";

import { questionTypeLabel } from "./question-presentation";

export type TaskBriefQuestionState =
  | { kind: "available"; question: QuestionDetail }
  | { kind: "loading" }
  | { kind: "historical-missing" }
  | { kind: "unavailable" };

export type TaskBriefPanelProps = {
  questionState: TaskBriefQuestionState;
  notes: string;
  onNotesChange: (value: string) => void;
};

const DIFFICULTY_LABELS: Record<string, string> = {
  BASIC: "基础",
  STANDARD: "标准",
  ADVANCED: "进阶",
};

function QuestionContent({ question }: { question: QuestionDetail }) {
  const metadata = [
    questionTypeLabel(question.question_type),
    DIFFICULTY_LABELS[question.difficulty],
    question.estimated_minutes > 0
      ? `约 ${question.estimated_minutes} 分钟`
      : undefined,
  ].filter((value): value is string => Boolean(value));

  return (
    <article
      className="space-y-5"
      data-content-priority="primary"
      data-testid="task-brief-content"
    >
      <div>
        <h2 className="text-xl font-semibold tracking-tight">
          {question.title}
        </h2>
        {metadata.length > 0 ? (
          <p className="mt-2 text-xs text-neutral-500">
            {metadata.join(" · ")}
          </p>
        ) : null}
      </div>

      <section aria-labelledby="task-scenario-heading">
        <h3
          className="text-xs font-semibold tracking-[0.12em] text-neutral-500 uppercase"
          id="task-scenario-heading"
        >
          讨论情境
        </h3>
        <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-neutral-800">
          {question.scenario}
        </p>
      </section>

      <section aria-labelledby="task-objective-heading">
        <h3
          className="text-xs font-semibold tracking-[0.12em] text-neutral-500 uppercase"
          id="task-objective-heading"
        >
          讨论目标
        </h3>
        <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-neutral-800">
          {question.objective}
        </p>
      </section>

      {question.hard_constraints.length > 0 ? (
        <section aria-labelledby="task-constraints-heading">
          <h3 className="text-sm font-semibold" id="task-constraints-heading">
            硬性约束
          </h3>
          <ul className="mt-2 space-y-2 text-sm leading-6 text-neutral-700">
            {question.hard_constraints.map((constraint) => (
              <li
                className="border-l-2 border-amber-500 pl-3"
                key={constraint.key}
              >
                {constraint.text}
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      {question.options.length > 0 ? (
        <section aria-labelledby="task-options-heading">
          <h3 className="text-sm font-semibold" id="task-options-heading">
            可选方案
          </h3>
          <ul className="mt-2 space-y-2 text-sm leading-6 text-neutral-700">
            {question.options.map((option) => (
              <li className="rounded-lg bg-neutral-100 p-3" key={option.key}>
                <p className="font-medium text-neutral-900">{option.label}</p>
                <p>{option.description}</p>
              </li>
            ))}
          </ul>
        </section>
      ) : null}
    </article>
  );
}

function QuestionState({
  state,
}: {
  state: TaskBriefQuestionState;
}): ReactNode {
  if (state.kind === "available") {
    return <QuestionContent question={state.question} />;
  }

  const copy =
    state.kind === "loading"
      ? "正在加载题目内容…"
      : state.kind === "historical-missing"
        ? "此历史会话没有可展示的题目内容"
        : "题目内容暂时无法加载，讨论记录仍可继续查看";

  return (
    <p className="rounded-lg bg-neutral-100 p-4 text-sm leading-6 text-neutral-600">
      {copy}
    </p>
  );
}

export default function TaskBriefPanel({
  questionState,
  notes,
  onNotesChange,
}: TaskBriefPanelProps): ReactNode {
  return (
    <div
      className="flex min-h-0 flex-col gap-4"
      data-information-hierarchy="task-brief"
      data-testid="task-brief-panel"
    >
      <div className="shrink-0 border-b border-neutral-200 pb-3">
        <p className="text-[0.625rem] font-semibold tracking-[0.16em] text-neutral-500 uppercase">
          CASE BRIEF
        </p>
        <h2 className="mt-0.5 text-base font-semibold text-neutral-950">
          题目与思考
        </h2>
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto">
        <QuestionState state={questionState} />
      </div>

      <section
        aria-labelledby="private-notes-heading"
        className="rounded-lg border border-neutral-200 bg-neutral-50 p-3"
        data-private-notes="memory-only"
      >
        <h2 className="text-sm font-semibold" id="private-notes-heading">
          我的思路 / 私人笔记
        </h2>
        <label className="mt-3 block" htmlFor="private-session-notes">
          <span className="sr-only">我的思路 / 私人笔记</span>
          <textarea
            className="min-h-28 w-full resize-y rounded-lg border border-neutral-300 bg-white px-3 py-2 text-sm leading-6 outline-none focus-visible:border-indigo-500 focus-visible:ring-2 focus-visible:ring-indigo-500"
            id="private-session-notes"
            onChange={(event) => onNotesChange(event.target.value)}
            value={notes}
          />
        </label>
        <p className="mt-2 text-xs leading-5 text-neutral-500">
          仅保留在当前页面，刷新后不会保存
        </p>
      </section>
    </div>
  );
}
