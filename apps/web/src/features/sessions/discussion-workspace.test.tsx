import { useEffect, useState } from "react";
import {
  cleanup,
  fireEvent,
  render,
  screen,
  within,
} from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { QuestionDetail, SessionSnapshot } from "@/lib/api/client";

import DiscussionWorkspace, {
  type ActiveDiscussionSurface,
  type SessionHeaderProps,
} from "./discussion-workspace";
import SessionProgressPanel from "./session-progress-panel";
import TaskBriefPanel from "./task-brief-panel";

const QUESTION: QuestionDetail = {
  id: "21000000-0000-4000-8000-000000000001",
  question_template_id: "20000000-0000-4000-8000-000000000001",
  version_number: 1,
  title: "社区活动资源安排",
  question_type: "RESOURCE_ALLOCATION",
  background_domain: "GENERAL",
  difficulty: "STANDARD",
  estimated_minutes: 25,
  scenario: "<strong>有限资源下安排三类社区活动</strong>",
  objective: "形成满足硬约束、说明取舍且可执行的安排。",
  hard_constraints: [{ key: "BUDGET", text: "总资源不得超过 100 个单位。" }],
  soft_constraints: [{ key: "PRIVATE", text: "不进入初始任务面板" }],
  stakeholders: [
    { key: "RESIDENTS", name: "不渲染的利益相关方", description: "暂缓字段" },
  ],
  options: [{ key: "A", label: "基础服务", description: "保障最大覆盖面。" }],
};

const PARTICIPANTS: SessionSnapshot["floor"]["participants"] = [
  {
    participant_id: "00000000-0000-4000-8000-000000000001",
    actor_kind: "HUMAN",
    seat_order: 1,
  },
  {
    participant_id: "00000000-0000-4000-8000-000000000002",
    actor_kind: "AI",
    seat_order: 2,
  },
];

const HEADER: SessionHeaderProps = {
  productName: "AI 群面训练场",
  sessionTitle: "社区活动资源安排",
  phaseLabel: "讨论与评估",
  countdown: "3:20",
  connection: "connected",
  connectionLabel: "连接正常",
  startAction: {
    visible: false,
    disabled: false,
    label: "开始讨论",
    onActivate: vi.fn(),
  },
  endAction: {
    visible: true,
    disabled: false,
    label: "结束会话",
    onActivate: vi.fn(),
  },
};

const SURFACE_EXPECTATIONS = [
  {
    label: "讨论",
    panelId: "discussion-surface",
    tabId: "discussion-tab",
  },
  { label: "题目", panelId: "task-surface", tabId: "task-tab" },
  { label: "进程", panelId: "progress-surface", tabId: "progress-tab" },
] as const;

afterEach(() => cleanup());

function MountProbe({
  name,
  onMount,
}: {
  name: string;
  onMount?: (name: string) => void;
}) {
  useEffect(() => {
    onMount?.(name);
  }, [name, onMount]);
  return <p>{name} 内容</p>;
}

function WorkspaceHarness({ onMount }: { onMount?: (name: string) => void }) {
  const [activeSurface, setActiveSurface] =
    useState<ActiveDiscussionSurface>("discussion");

  return (
    <DiscussionWorkspace
      activeSurface={activeSurface}
      discussion={<MountProbe name="讨论" onMount={onMount} />}
      header={HEADER}
      onActiveSurfaceChange={setActiveSurface}
      progress={<MountProbe name="进程" onMount={onMount} />}
      taskBrief={<MountProbe name="题目" onMount={onMount} />}
    />
  );
}

describe("DiscussionWorkspace", () => {
  it("bounds only the loaded workspace and gives each region explicit height ownership", () => {
    const { container } = render(<WorkspaceHarness />);

    const root = container.firstElementChild;
    expect(root).toHaveClass(
      "flex",
      "h-dvh",
      "max-h-dvh",
      "overflow-hidden",
      "flex-col",
    );
    expect(screen.getByRole("banner")).toHaveClass("shrink-0");
    expect(screen.getByRole("tablist", { name: "讨论工作区" })).toHaveClass(
      "shrink-0",
    );
    expect(
      screen.getByRole("button", { name: "打开题目与思考" }).parentElement,
    ).toHaveClass("shrink-0");

    const grid = screen.getByTestId("discussion-workspace-grid");
    expect(grid).toHaveClass("min-h-0", "flex-1", "overflow-hidden");
    expect(screen.getByRole("tabpanel", { name: "题目" })).toHaveClass(
      "min-h-0",
      "overflow-y-auto",
    );
    expect(screen.getByRole("tabpanel", { name: "进程" })).toHaveClass(
      "min-h-0",
      "overflow-y-auto",
    );
    expect(screen.getByRole("tabpanel", { name: "讨论" })).toHaveClass(
      "h-full",
      "min-h-0",
      "overflow-hidden",
    );
  });

  it("renders one desktop three-region studio with Discussion as visual priority", () => {
    render(<WorkspaceHarness />);

    const grid = screen.getByTestId("discussion-workspace-grid");
    expect(grid).toHaveClass(
      "min-[1200px]:grid-cols-[minmax(15rem,1fr)_minmax(32rem,2.2fr)_minmax(15rem,1fr)]",
    );
    expect(screen.getByRole("tabpanel", { name: "题目" })).toHaveClass(
      "min-[1200px]:!block",
    );
    expect(screen.getByRole("tabpanel", { name: "讨论" })).toHaveAttribute(
      "data-region-priority",
      "primary",
    );
    expect(screen.getByRole("tabpanel", { name: "进程" })).toHaveClass(
      "min-[1200px]:!block",
    );
  });

  it("uses one collapsible tablet support sheet while Discussion stays primary", () => {
    render(<WorkspaceHarness />);

    const grid = screen.getByTestId("discussion-workspace-grid");
    const taskPanel = screen.getByRole("tabpanel", { name: "题目" });
    const progressPanel = screen.getByRole("tabpanel", { name: "进程" });

    expect(grid).toHaveClass("relative", "min-[1200px]:grid");
    expect(grid).not.toHaveClass("grid");
    expect(taskPanel).toHaveClass(
      "md:absolute",
      "md:inset-y-4",
      "md:right-4",
      "md:z-20",
      "min-[1200px]:!static",
    );
    expect(progressPanel).toHaveClass(
      "md:absolute",
      "md:inset-y-4",
      "md:right-4",
      "md:z-20",
      "min-[1200px]:!static",
    );
    expect(grid).toHaveAttribute("data-support-surface", "discussion");

    fireEvent.click(screen.getByRole("button", { name: "打开题目与思考" }));
    expect(grid).toHaveAttribute("data-support-surface", "task");
    expect(taskPanel).toHaveClass("block");
    expect(progressPanel).toHaveClass("hidden");
    expect(screen.getByRole("tabpanel", { name: "讨论" })).toHaveClass(
      "md:block",
    );

    fireEvent.click(screen.getByRole("button", { name: "关闭题目与思考" }));
    expect(grid).toHaveAttribute("data-support-surface", "discussion");

    fireEvent.click(screen.getByRole("button", { name: "打开训练进程" }));
    expect(grid).toHaveAttribute("data-support-surface", "progress");
    expect(taskPanel).toHaveClass("hidden");
    expect(progressPanel).toHaveClass("block");
  });

  it("implements the exact mobile tab order, selection and keyboard semantics", () => {
    render(<WorkspaceHarness />);

    const tabs = screen.getAllByRole("tab");
    expect(tabs.map((tab) => tab.textContent)).toEqual([
      "讨论",
      "题目",
      "进程",
    ]);
    expect(tabs[0]).toHaveAttribute("aria-selected", "true");
    expect(tabs[0]).toHaveAttribute("tabindex", "0");
    expect(tabs[1]).toHaveAttribute("tabindex", "-1");

    for (const [index, surface] of SURFACE_EXPECTATIONS.entries()) {
      const panel = screen.getByRole("tabpanel", { name: surface.label });
      expect(tabs[index]).toHaveAttribute("aria-controls", surface.panelId);
      expect(panel).toHaveAttribute("id", surface.panelId);
      expect(panel).toHaveAttribute("aria-labelledby", surface.tabId);
      expect(panel).toHaveAttribute("tabindex", "0");
      expect(panel).toHaveClass(index === 0 ? "block" : "hidden");
    }

    fireEvent.keyDown(tabs[0], { key: "ArrowRight" });
    const taskTab = screen.getByRole("tab", { name: "题目" });
    expect(taskTab).toHaveAttribute("aria-selected", "true");
    expect(taskTab).toHaveFocus();
    expect(screen.getByRole("tabpanel", { name: "讨论" })).toHaveClass(
      "hidden",
    );
    expect(screen.getByRole("tabpanel", { name: "题目" })).toHaveClass("block");
    fireEvent.keyDown(taskTab, { key: "End" });
    const progressTab = screen.getByRole("tab", { name: "进程" });
    expect(progressTab).toHaveAttribute("aria-selected", "true");
    expect(progressTab).toHaveFocus();
  });

  it("switches responsive visibility without remounting supplied regions", () => {
    const onMount = vi.fn();
    render(<WorkspaceHarness onMount={onMount} />);

    fireEvent.click(screen.getByRole("tab", { name: "题目" }));
    fireEvent.click(screen.getByRole("tab", { name: "进程" }));
    fireEvent.click(screen.getByRole("tab", { name: "讨论" }));

    expect(onMount.mock.calls).toEqual([["题目"], ["讨论"], ["进程"]]);
  });
});

describe("TaskBriefPanel", () => {
  it("renders only the frozen public allowlist as plain text", () => {
    render(
      <TaskBriefPanel
        notes=""
        onNotesChange={vi.fn()}
        questionState={{ kind: "available", question: QUESTION }}
      />,
    );

    expect(
      screen.getByRole("heading", { name: QUESTION.title }),
    ).toBeInTheDocument();
    expect(screen.getByText(QUESTION.scenario)).toBeInTheDocument();
    expect(document.querySelector("strong")).not.toBeInTheDocument();
    expect(screen.getByText(QUESTION.objective)).toBeInTheDocument();
    expect(screen.getByText("总资源不得超过 100 个单位。")).toBeInTheDocument();
    expect(screen.getByText("基础服务")).toBeInTheDocument();
    expect(
      screen.getByText("资源分配 · 标准 · 约 25 分钟"),
    ).toBeInTheDocument();
    expect(screen.queryByText("不进入初始任务面板")).not.toBeInTheDocument();
    expect(screen.queryByText("不渲染的利益相关方")).not.toBeInTheDocument();
    expect(screen.queryByText(QUESTION.id)).not.toBeInTheDocument();
    expect(
      screen.queryByText(/AI 提示|参考答案|建议发言/),
    ).not.toBeInTheDocument();
  });

  it("keeps notes controlled and makes the no-storage boundary visible", () => {
    const onNotesChange = vi.fn();
    render(
      <TaskBriefPanel
        notes="只在当前页面的思路"
        onNotesChange={onNotesChange}
        questionState={{ kind: "available", question: QUESTION }}
      />,
    );

    const notes = screen.getByRole("textbox", { name: "我的思路 / 私人笔记" });
    expect(notes).toHaveValue("只在当前页面的思路");
    fireEvent.change(notes, { target: { value: "更新后的思路" } });
    expect(onNotesChange).toHaveBeenCalledWith("更新后的思路");
    expect(
      screen.getByText("仅保留在当前页面，刷新后不会保存"),
    ).toBeInTheDocument();
  });

  it.each([
    ["loading", "正在加载题目内容…"],
    ["historical-missing", "此历史会话没有可展示的题目内容"],
    ["unavailable", "题目内容暂时无法加载，讨论记录仍可继续查看"],
  ] as const)("renders the %s Question state", (kind, copy) => {
    render(
      <TaskBriefPanel
        notes=""
        onNotesChange={vi.fn()}
        questionState={{ kind }}
      />,
    );

    expect(screen.getByText(copy)).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /重试/ }),
    ).not.toBeInTheDocument();
  });

  it("omits decorative empty constraint and option groups", () => {
    render(
      <TaskBriefPanel
        notes=""
        onNotesChange={vi.fn()}
        questionState={{
          kind: "available",
          question: { ...QUESTION, hard_constraints: [], options: [] },
        }}
      />,
    );

    expect(
      screen.queryByRole("heading", { name: "硬性约束" }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("heading", { name: "可选方案" }),
    ).not.toBeInTheDocument();
  });
});

describe("SessionProgressPanel", () => {
  it("renders six authoritative phases, safe floor state and no fake modules", () => {
    render(
      <SessionProgressPanel
        connection="connected"
        countdown={null}
        currentGrant={{
          grant_id: "00000000-0000-4000-8000-000000000010",
          participant_id: PARTICIPANTS[1].participant_id,
          phase: "CONFLICT_AND_EVALUATION",
          reason_code: "FIRST_OPPORTUNITY",
          granted_at: "2026-08-27T00:00:00Z",
        }}
        latestFloorEvent={null}
        participants={PARTICIPANTS}
        status="CONFLICT_AND_EVALUATION"
      />,
    );

    const phaseList = screen.getByRole("list", { name: "讨论阶段" });
    expect(
      within(phaseList)
        .getAllByRole("listitem")
        .map((item) => item.textContent),
    ).toEqual([
      "准备",
      "个人陈述",
      "观点探索",
      "讨论与评估",
      "收敛决策",
      "最终总结",
    ]);
    expect(
      within(phaseList).getByText("讨论与评估").closest("li"),
    ).toHaveAttribute("aria-current", "step");
    expect(screen.getByText("等待服务端提供阶段时间")).toBeInTheDocument();
    expect(screen.getByText("当前发言：AI 候选人 1")).toBeInTheDocument();
    expect(screen.getByText("连接正常")).toBeInTheDocument();
    expect(screen.queryByText(/投票|结论|报告|共识率/)).not.toBeInTheDocument();
    expect(screen.queryByText(/每阶段|分钟\/阶段/)).not.toBeInTheDocument();
  });

  it.each([
    ["COMPLETED", "讨论已完成"],
    ["ABORTED_USER", "训练已结束"],
  ] as const)(
    "renders truthful terminal floor copy for %s without implying another speaker",
    (status, expectedCopy) => {
      render(
        <SessionProgressPanel
          connection="connected"
          countdown={null}
          currentGrant={null}
          latestFloorEvent={null}
          participants={PARTICIPANTS}
          status={status}
        />,
      );

      expect(
        screen.queryByText("正在安排下一位发言者", { exact: true }),
      ).not.toBeInTheDocument();
      expect(
        screen.queryByText("等待服务端分配发言权", { exact: true }),
      ).not.toBeInTheDocument();
      expect(
        screen.getByText(expectedCopy, { exact: true }),
      ).toBeInTheDocument();
    },
  );
});
