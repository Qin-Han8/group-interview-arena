import { useState, type ComponentProps } from "react";
import {
  cleanup,
  fireEvent,
  render,
  screen,
  within,
} from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { QuestionDetail, QuestionSummary } from "@/lib/api/client";

import TrainingEntry, {
  type SelectedQuestionDetailState,
} from "./training-entry";

const TYPE_FIXTURES = [
  ["ORDERING_SELECTION", "排序选择型"],
  ["RESOURCE_ALLOCATION", "资源分配型"],
  ["PLAN_DESIGN", "方案策划型"],
] as const;

const QUESTION_TITLES = [
  "候选地点优先级排序",
  "项目风险处置排序",
  "服务事项优先选择",
  "方案要素组合选择",
  "社区活动资源分配",
  "校园预算资源分配",
  "应急物资分配方案",
  "跨团队人力资源安排",
  "新员工培养方案策划",
  "城市活动落地方案",
  "课程产品设计方案",
  "公益项目执行方案",
] as const;

const QUESTIONS: QuestionSummary[] = QUESTION_TITLES.map((title, index) => ({
  id: `21000000-0000-4000-8000-${String(index + 1).padStart(12, "0")}`,
  question_template_id: `20000000-0000-4000-8000-${String(index + 1).padStart(12, "0")}`,
  version_number: index + 1,
  title,
  question_type: TYPE_FIXTURES[Math.floor(index / 4)]?.[0] ?? "PLAN_DESIGN",
  background_domain: "GENERAL",
  difficulty: index % 2 === 0 ? "STANDARD" : "ADVANCED",
  estimated_minutes: 25 + (index % 3) * 5,
}));

const SELECTED_DETAIL: QuestionDetail = {
  ...QUESTIONS[0],
  scenario: "这段场景只用于讨论工作台，不应出现在选题摘要。",
  objective: "在给定约束下形成有依据的统一排序。",
  hard_constraints: [
    { key: "COUNT", text: "必须选出前三项并说明排序依据。" },
    { key: "CONSENSUS", text: "最终需要形成小组统一结论。" },
  ],
  soft_constraints: [],
  stakeholders: [],
  options: [
    {
      key: "PRIVATE_SENTINEL",
      label: "不应进入选题摘要",
      description: "选题摘要不展示方案选项。",
    },
  ],
};

function defaultProps(
  overrides: Partial<ComponentProps<typeof TrainingEntry>> = {},
): ComponentProps<typeof TrainingEntry> {
  return {
    surface: "lobby",
    questions: QUESTIONS,
    selectedQuestionId: "",
    selectedQuestion: { kind: "idle" },
    creating: false,
    errorMessage: null,
    onBeginSelection: vi.fn(),
    onSelectQuestion: vi.fn(),
    onCreateSession: vi.fn(),
    ...overrides,
  };
}

function ControlledSetup() {
  const [questionId, setQuestionId] = useState("");
  const selectedQuestion: SelectedQuestionDetailState = questionId
    ? {
        kind: "available",
        questionId,
        question: {
          ...SELECTED_DETAIL,
          ...QUESTIONS.find((question) => question.id === questionId),
          id: questionId,
        },
      }
    : { kind: "idle" };
  return (
    <TrainingEntry
      {...defaultProps({
        surface: "setup",
        selectedQuestionId: questionId,
        selectedQuestion,
        onSelectQuestion: setQuestionId,
      })}
    />
  );
}

describe("TrainingEntry", () => {
  afterEach(() => cleanup());

  it("presents a truthful Bento lobby without mock dashboard claims", () => {
    const onBeginSelection = vi.fn();
    const { container } = render(
      <TrainingEntry {...defaultProps({ onBeginSelection })} />,
    );

    expect(screen.getByTestId("training-entry")).toHaveAttribute(
      "data-surface",
      "lobby",
    );
    expect(screen.getByTestId("training-entry")).toHaveAttribute(
      "data-scroll-owner",
      "training-entry",
    );
    expect(
      screen.getByRole("heading", { name: "下一场完整模拟" }),
    ).toBeVisible();
    expect(screen.getByText("3 位 AI 候选人")).toBeVisible();
    expect(screen.getByText("文字无领导小组讨论")).toBeVisible();
    expect(screen.getByText("基于真实发言证据的复盘")).toBeVisible();
    fireEvent.click(screen.getByRole("button", { name: "开始选题" }));
    expect(onBeginSelection).toHaveBeenCalledOnce();
    expect(container.textContent).not.toMatch(
      /分钟|余额|连续|历史|分数|得分|进度|Mock|最近训练|场次包/,
    );
  });

  it("derives three accessible type groups and their real 4/4/4 counts", () => {
    render(<TrainingEntry {...defaultProps({ surface: "setup" })} />);

    const tabs = screen.getByRole("tablist", { name: "题目类型" });
    for (const [, label] of TYPE_FIXTURES) {
      expect(
        within(tabs).getByRole("tab", { name: `${label} 4 道` }),
      ).toBeVisible();
    }
    expect(screen.getAllByRole("radio")).toHaveLength(4);
    for (const [type, label] of TYPE_FIXTURES) {
      fireEvent.click(within(tabs).getByRole("tab", { name: `${label} 4 道` }));
      const expected = QUESTIONS.filter(
        (question) => question.question_type === type,
      );
      expect(screen.getAllByRole("radio")).toHaveLength(4);
      for (const question of expected) {
        expect(
          screen.getByRole("radio", { name: question.title }),
        ).toBeVisible();
      }
    }
  });

  it("keeps native radio semantics and exposes selection beyond color", () => {
    render(<ControlledSetup />);
    const first = screen.getByRole("radio", { name: QUESTIONS[0].title });
    expect(first).toHaveAttribute("type", "radio");
    expect(first).toHaveAttribute("name", "training-question");

    first.focus();
    fireEvent.keyDown(first, { key: " ", code: "Space" });

    expect(first).toBeChecked();
    expect(first.closest("label")).toHaveAttribute("data-selected", "true");
    expect(within(first.closest("label")!).getByText("已选择")).toBeVisible();
    expect(first.closest("label")).toHaveAttribute(
      "data-focus-treatment",
      "focus-visible",
    );
  });

  it("renders only public summary fields and never promotes raw identifiers", () => {
    const privateFixture = {
      ...QUESTIONS[0],
      private_stance: "PRIVATE_STANCE_SENTINEL",
      hidden_conflict: "HIDDEN_CONFLICT_SENTINEL",
      prompt: "SYSTEM_PROMPT_SENTINEL",
    } as QuestionSummary;
    const { container } = render(
      <TrainingEntry
        {...defaultProps({ questions: [privateFixture], surface: "setup" })}
      />,
    );

    expect(screen.getByText(privateFixture.title)).toBeVisible();
    expect(screen.getByText("标准难度")).toBeVisible();
    expect(screen.getByText("通用场景")).toBeVisible();
    expect(screen.getByText("约 25 分钟")).toBeVisible();
    expect(screen.getByText("版本 1")).toBeVisible();
    expect(container.textContent).not.toContain(privateFixture.id);
    expect(container.textContent).not.toContain(
      privateFixture.question_template_id,
    );
    expect(container.textContent).not.toMatch(
      /PRIVATE_STANCE_SENTINEL|HIDDEN_CONFLICT_SENTINEL|SYSTEM_PROMPT_SENTINEL/,
    );
  });

  it("shows exact selected detail objective and hard constraints without fallback data", () => {
    const { rerender } = render(
      <TrainingEntry
        {...defaultProps({
          surface: "setup",
          selectedQuestionId: SELECTED_DETAIL.id,
          selectedQuestion: {
            kind: "available",
            questionId: SELECTED_DETAIL.id,
            question: SELECTED_DETAIL,
          },
        })}
      />,
    );

    expect(screen.getByText(SELECTED_DETAIL.objective)).toBeVisible();
    for (const constraint of SELECTED_DETAIL.hard_constraints) {
      expect(screen.getByText(constraint.text)).toBeVisible();
    }
    expect(screen.queryByText(SELECTED_DETAIL.scenario)).toBeNull();
    expect(screen.queryByText("不应进入选题摘要")).toBeNull();

    rerender(
      <TrainingEntry
        {...defaultProps({
          surface: "setup",
          selectedQuestionId: SELECTED_DETAIL.id,
          selectedQuestion: { kind: "loading", questionId: SELECTED_DETAIL.id },
        })}
      />,
    );
    expect(screen.getByText("正在加载所选题目…")).toBeVisible();

    rerender(
      <TrainingEntry
        {...defaultProps({
          surface: "setup",
          selectedQuestionId: SELECTED_DETAIL.id,
          selectedQuestion: {
            kind: "unavailable",
            questionId: SELECTED_DETAIL.id,
          },
        })}
      />,
    );
    expect(screen.getByText("所选题目详情暂时无法加载")).toBeVisible();
    expect(screen.getByRole("button", { name: "创建文字会话" })).toBeEnabled();
  });

  it("keeps creation bound to a selection and independent of detail availability", () => {
    const onCreateSession = vi.fn();
    const { rerender } = render(
      <TrainingEntry
        {...defaultProps({ surface: "setup", onCreateSession })}
      />,
    );
    expect(screen.getByRole("button", { name: "创建文字会话" })).toBeDisabled();

    rerender(
      <TrainingEntry
        {...defaultProps({
          surface: "setup",
          selectedQuestionId: QUESTIONS[0].id,
          selectedQuestion: {
            kind: "unavailable",
            questionId: QUESTIONS[0].id,
          },
          onCreateSession,
        })}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: "创建文字会话" }));
    expect(onCreateSession).toHaveBeenCalledWith();

    rerender(
      <TrainingEntry
        {...defaultProps({
          surface: "setup",
          selectedQuestionId: QUESTIONS[0].id,
          selectedQuestion: {
            kind: "loading",
            questionId: QUESTIONS[0].id,
          },
          creating: true,
          onCreateSession,
        })}
      />,
    );
    expect(screen.getByRole("button", { name: "正在创建…" })).toBeDisabled();
  });
});
