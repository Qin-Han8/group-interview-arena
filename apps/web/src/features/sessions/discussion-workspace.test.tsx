import { useEffect, useState } from "react";
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { QuestionDetail, SessionSnapshot } from "@/lib/api/client";

import DiscussionWorkspace, {
  type ActiveDiscussionSurface,
  type SessionHeaderProps,
} from "./discussion-workspace";
import SessionProgressPanel from "./session-progress-panel";
import TaskBriefPanel from "./task-brief-panel";

let workspaceViewportWidth = 1440;

class WorkspaceResizeObserver {
  readonly callback: ResizeObserverCallback;

  constructor(callback: ResizeObserverCallback) {
    this.callback = callback;
  }

  disconnect() {}

  observe(target: Element) {
    this.callback(
      [
        {
          contentRect: { width: workspaceViewportWidth },
          target,
        } as ResizeObserverEntry,
      ],
      this,
    );
  }

  unobserve() {}
}

class WorkspacePointerEvent extends MouseEvent {
  readonly pointerId: number;

  constructor(type: string, init: PointerEventInit = {}) {
    super(type, init);
    this.pointerId = init.pointerId ?? 0;
  }
}

function configureWorkspaceViewport(width: number) {
  workspaceViewportWidth = width;
  Object.defineProperty(window, "innerWidth", {
    configurable: true,
    value: width,
  });
  Object.defineProperty(window, "matchMedia", {
    configurable: true,
    value: vi.fn((query: string) => ({
      addEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
      matches: query === "(min-width: 1200px)" && width >= 1200,
      media: query,
      onchange: null,
      removeEventListener: vi.fn(),
    })),
  });
  vi.stubGlobal("ResizeObserver", WorkspaceResizeObserver);
  vi.stubGlobal("PointerEvent", WorkspacePointerEvent);
}

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
  reportAction: {
    visible: false,
    disabled: false,
    label: "生成 / 查看训练报告",
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

beforeEach(() => {
  window.localStorage.clear();
  configureWorkspaceViewport(1440);
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

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

function WorkspaceHarness({
  header = HEADER,
  onMount,
}: {
  header?: SessionHeaderProps;
  onMount?: (name: string) => void;
}) {
  const [activeSurface, setActiveSurface] =
    useState<ActiveDiscussionSurface>("discussion");

  return (
    <DiscussionWorkspace
      activeSurface={activeSurface}
      discussion={<MountProbe name="讨论" onMount={onMount} />}
      header={header}
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
      "h-full",
      "max-h-full",
      "overflow-hidden",
      "flex-col",
    );
    expect(root).toHaveAttribute("data-scroll-owner", "viewport-constrained");
    expect(screen.getByRole("banner")).toHaveClass("shrink-0");
    expect(screen.getByRole("tablist", { name: "讨论工作区" })).toHaveClass(
      "shrink-0",
    );
    expect(
      screen.getByRole("button", { name: "打开题目与思考" }).parentElement,
    ).toHaveClass("shrink-0");

    const grid = screen.getByTestId("discussion-workspace-grid");
    expect(grid).toHaveClass("min-h-0", "flex-1", "overflow-hidden");
    expect(grid).toHaveAttribute("data-scroll-owner", "none");
    expect(screen.getByRole("tabpanel", { name: "题目" })).toHaveClass(
      "min-h-0",
      "overflow-y-auto",
    );
    expect(screen.getByRole("tabpanel", { name: "题目" })).toHaveAttribute(
      "data-scroll-owner",
      "task-panel",
    );
    expect(screen.getByRole("tabpanel", { name: "进程" })).toHaveClass(
      "min-h-0",
      "overflow-y-auto",
    );
    expect(screen.getByRole("tabpanel", { name: "进程" })).toHaveAttribute(
      "data-scroll-owner",
      "progress-panel",
    );
    expect(screen.getByRole("tabpanel", { name: "讨论" })).toHaveClass(
      "h-full",
      "min-h-0",
      "overflow-hidden",
    );
    expect(screen.getByRole("tabpanel", { name: "讨论" })).toHaveAttribute(
      "data-scroll-owner",
      "discussion-transcript",
    );
  });

  it("presents a compact truthful training-session header hierarchy", () => {
    render(<WorkspaceHarness />);

    const header = screen.getByRole("banner");
    expect(header).toHaveAttribute("data-testid", "training-session-header");
    expect(within(header).queryByText("AI 群面训练场")).not.toBeInTheDocument();
    expect(
      within(header).queryByText("Interview Simulation Studio"),
    ).not.toBeInTheDocument();
    expect(
      within(header).getByRole("heading", {
        level: 1,
        name: HEADER.sessionTitle,
      }),
    ).toHaveClass("text-xl", "font-semibold");
    expect(within(header).getByTestId("header-phase")).toHaveAttribute(
      "data-session-phase",
      HEADER.phaseLabel,
    );
    expect(within(header).getByTestId("header-countdown")).toHaveTextContent(
      HEADER.countdown!,
    );
    expect(within(header).getByText(HEADER.connectionLabel)).toHaveAttribute(
      "data-connection-state",
      HEADER.connection,
    );
    expect(within(header).getByTestId("header-actions")).toHaveTextContent(
      "结束会话",
    );
    expect(within(header).getByTestId("header-title-region")).toHaveAttribute(
      "data-overflow-policy",
      "truncate",
    );
    expect(within(header).getByTestId("header-status-region")).toHaveAttribute(
      "data-control-priority",
      "preserve",
    );
  });

  it("keeps status, countdown and actions structurally protected beside a long title", () => {
    const longTitle =
      "这是一个需要在非常有限资源下完成跨部门协作并说明多项硬约束取舍的超长训练题目标题";
    render(
      <WorkspaceHarness header={{ ...HEADER, sessionTitle: longTitle }} />,
    );

    const header = screen.getByTestId("training-session-header");
    expect(header).toHaveClass("training-session-header");
    expect(
      within(header).getByRole("heading", { name: longTitle }),
    ).toHaveClass("truncate");
    expect(within(header).getByTestId("header-status-region")).toContainElement(
      within(header).getByTestId("header-countdown"),
    );
    expect(within(header).getByTestId("header-actions")).toHaveClass(
      "training-session-header-actions",
    );
  });
  it("renders one desktop three-region studio with Discussion as visual priority", () => {
    render(<WorkspaceHarness />);

    const grid = screen.getByTestId("discussion-workspace-grid");
    expect(grid).toHaveAttribute("data-desktop-layout", "three-column");
    expect(grid).toHaveAttribute(
      "data-desktop-columns",
      "support-280 primary-min-520 support-280",
    );
    expect(screen.getByRole("tabpanel", { name: "题目" })).toHaveClass(
      "min-[1200px]:!block",
    );
    expect(screen.getByRole("tabpanel", { name: "题目" })).toHaveAttribute(
      "data-region-priority",
      "support",
    );
    expect(screen.getByRole("tabpanel", { name: "讨论" })).toHaveAttribute(
      "data-region-priority",
      "primary",
    );
    expect(screen.getByRole("tabpanel", { name: "讨论" })).toHaveAttribute(
      "data-region-role",
      "live-discussion",
    );
    expect(screen.getByRole("tabpanel", { name: "进程" })).toHaveClass(
      "min-[1200px]:!block",
    );
    expect(screen.getByRole("tabpanel", { name: "进程" })).toHaveAttribute(
      "data-region-priority",
      "support",
    );
  });

  it("starts desktop training at 280 / 280 with two accessible separators", async () => {
    render(<WorkspaceHarness />);

    const separators = await screen.findAllByRole("separator");
    expect(separators).toHaveLength(2);
    const left = screen.getByRole("separator", {
      name: "调整题目与思考面板宽度",
    });
    const right = screen.getByRole("separator", {
      name: "调整训练进程面板宽度",
    });
    expect(left).toHaveAttribute("aria-orientation", "vertical");
    expect(left).toHaveAttribute("aria-valuemin", "220");
    expect(left).toHaveAttribute("aria-valuemax", "420");
    expect(left).toHaveAttribute("aria-valuenow", "280");
    expect(right).toHaveAttribute("aria-valuemin", "220");
    expect(right).toHaveAttribute("aria-valuemax", "380");
    expect(right).toHaveAttribute("aria-valuenow", "280");
    expect(left).toHaveAttribute("tabindex", "0");
    expect(right).toHaveAttribute("tabindex", "0");
    expect(left).toHaveClass("training-workspace-separator");
    expect(screen.queryByRole("button", { name: /保存/ })).toBeNull();

    const grid = screen.getByTestId("discussion-workspace-grid");
    expect(grid.style.getPropertyValue("--workspace-left-width")).toBe("280px");
    expect(grid.style.getPropertyValue("--workspace-right-width")).toBe(
      "280px",
    );
    expect(Object.entries(window.localStorage)).toEqual([]);
  });

  it("resizes only the left panel with pointer capture and persists on completion", async () => {
    render(<WorkspaceHarness />);
    const left = await screen.findByRole("separator", {
      name: "调整题目与思考面板宽度",
    });
    const setPointerCapture = vi.fn();
    const releasePointerCapture = vi.fn();
    Object.assign(left, {
      hasPointerCapture: () => true,
      releasePointerCapture,
      setPointerCapture,
    });

    fireEvent.pointerDown(left, { clientX: 500, pointerId: 7 });
    fireEvent.pointerMove(left, { clientX: 580, pointerId: 7 });

    const grid = screen.getByTestId("discussion-workspace-grid");
    expect(grid.style.getPropertyValue("--workspace-left-width")).toBe("360px");
    expect(grid.style.getPropertyValue("--workspace-right-width")).toBe(
      "280px",
    );
    expect(grid).toHaveAttribute("data-resizing-panel", "left");
    expect(setPointerCapture).toHaveBeenCalledWith(7);
    expect(window.localStorage.length).toBe(0);

    fireEvent.pointerUp(left, { clientX: 580, pointerId: 7 });
    expect(releasePointerCapture).toHaveBeenCalledWith(7);
    expect(grid).not.toHaveAttribute("data-resizing-panel");
    expect(window.localStorage.getItem("gia.training.workspace.layout")).toBe(
      '{"version":1,"leftWidth":360,"rightWidth":280}',
    );
  });

  it("resizes only the right panel and clamps both panels to hard bounds", async () => {
    render(<WorkspaceHarness />);
    const grid = screen.getByTestId("discussion-workspace-grid");
    const left = await screen.findByRole("separator", {
      name: "调整题目与思考面板宽度",
    });
    const right = screen.getByRole("separator", {
      name: "调整训练进程面板宽度",
    });
    Object.assign(left, {
      hasPointerCapture: () => false,
      setPointerCapture: vi.fn(),
    });
    Object.assign(right, {
      hasPointerCapture: () => false,
      setPointerCapture: vi.fn(),
    });

    fireEvent.pointerDown(right, { clientX: 1000, pointerId: 1 });
    fireEvent.pointerMove(right, { clientX: 900, pointerId: 1 });
    fireEvent.pointerUp(right, { clientX: 900, pointerId: 1 });
    expect(grid.style.getPropertyValue("--workspace-left-width")).toBe("280px");
    expect(grid.style.getPropertyValue("--workspace-right-width")).toBe(
      "380px",
    );

    fireEvent.pointerDown(right, { clientX: 1000, pointerId: 2 });
    fireEvent.pointerMove(right, { clientX: 2000, pointerId: 2 });
    fireEvent.pointerUp(right, { clientX: 2000, pointerId: 2 });
    expect(grid.style.getPropertyValue("--workspace-right-width")).toBe(
      "220px",
    );

    fireEvent.pointerDown(left, { clientX: 500, pointerId: 3 });
    fireEvent.pointerMove(left, { clientX: 1000, pointerId: 3 });
    fireEvent.pointerUp(left, { clientX: 1000, pointerId: 3 });
    expect(grid.style.getPropertyValue("--workspace-left-width")).toBe("420px");

    fireEvent.pointerDown(left, { clientX: 500, pointerId: 4 });
    fireEvent.pointerMove(left, { clientX: 0, pointerId: 4 });
    fireEvent.pointerUp(left, { clientX: 0, pointerId: 4 });
    expect(grid.style.getPropertyValue("--workspace-left-width")).toBe("220px");
  });

  it("dynamically clamps an aggressive side resize to preserve a 520px center", async () => {
    configureWorkspaceViewport(1200);
    render(<WorkspaceHarness />);
    const left = await screen.findByRole("separator", {
      name: "调整题目与思考面板宽度",
    });
    Object.assign(left, {
      hasPointerCapture: () => false,
      setPointerCapture: vi.fn(),
    });

    expect(left).toHaveAttribute("aria-valuemax", "320");
    fireEvent.pointerDown(left, { clientX: 300, pointerId: 1 });
    fireEvent.pointerMove(left, { clientX: 1300, pointerId: 1 });
    fireEvent.pointerUp(left, { clientX: 1300, pointerId: 1 });

    expect(left).toHaveAttribute("aria-valuenow", "320");
    expect(screen.getByTestId("discussion-workspace-grid")).toHaveAttribute(
      "data-center-min-width",
      "520",
    );
  });

  it("supports 16px and Shift+40px screen-axis keyboard resizing and persists each step", async () => {
    render(<WorkspaceHarness />);
    const left = await screen.findByRole("separator", {
      name: "调整题目与思考面板宽度",
    });
    const right = screen.getByRole("separator", {
      name: "调整训练进程面板宽度",
    });

    fireEvent.keyDown(left, { key: "ArrowRight" });
    expect(left).toHaveAttribute("aria-valuenow", "296");
    expect(window.localStorage.getItem("gia.training.workspace.layout")).toBe(
      '{"version":1,"leftWidth":296,"rightWidth":280}',
    );
    fireEvent.keyDown(left, { key: "ArrowLeft", shiftKey: true });
    expect(left).toHaveAttribute("aria-valuenow", "256");

    fireEvent.keyDown(right, { key: "ArrowLeft" });
    expect(right).toHaveAttribute("aria-valuenow", "296");
    fireEvent.keyDown(right, { key: "ArrowRight", shiftKey: true });
    expect(right).toHaveAttribute("aria-valuenow", "256");
    expect(window.localStorage.getItem("gia.training.workspace.layout")).toBe(
      '{"version":1,"leftWidth":256,"rightWidth":256}',
    );
  });

  it("keeps current-page resizing functional when browser storage rejects writes", async () => {
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new DOMException("full", "QuotaExceededError");
    });
    render(<WorkspaceHarness />);
    const left = await screen.findByRole("separator", {
      name: "调整题目与思考面板宽度",
    });

    fireEvent.keyDown(left, { key: "ArrowRight" });

    expect(left).toHaveAttribute("aria-valuenow", "296");
    expect(screen.getByTestId("discussion-workspace-grid")).toHaveStyle({
      "--workspace-left-width": "296px",
    });
  });

  it("restores a valid preference on reload and a later workspace mount", async () => {
    window.localStorage.setItem(
      "gia.training.workspace.layout",
      '{"version":1,"leftWidth":352,"rightWidth":336}',
    );
    const first = render(<WorkspaceHarness />);

    await waitFor(() =>
      expect(
        screen
          .getByTestId("discussion-workspace-grid")
          .style.getPropertyValue("--workspace-left-width"),
      ).toBe("352px"),
    );
    first.unmount();
    render(<WorkspaceHarness />);
    const grid = await screen.findByTestId("discussion-workspace-grid");
    await waitFor(() =>
      expect(grid.style.getPropertyValue("--workspace-right-width")).toBe(
        "336px",
      ),
    );
  });

  it("keeps stored desktop widths dormant and renders no separators on tablet/mobile", () => {
    configureWorkspaceViewport(768);
    window.localStorage.setItem(
      "gia.training.workspace.layout",
      '{"version":1,"leftWidth":420,"rightWidth":380}',
    );
    render(<WorkspaceHarness />);

    const grid = screen.getByTestId("discussion-workspace-grid");
    expect(screen.queryByRole("separator")).toBeNull();
    expect(grid.style.getPropertyValue("--workspace-left-width")).toBe("");
    expect(grid.style.getPropertyValue("--workspace-right-width")).toBe("");
    expect(screen.getByTestId("tablet-support-controls")).toBeVisible();
    expect(window.localStorage.getItem("gia.training.workspace.layout")).toBe(
      '{"version":1,"leftWidth":420,"rightWidth":380}',
    );
  });

  it("uses one collapsible tablet support sheet while Discussion stays primary", () => {
    render(<WorkspaceHarness />);

    const grid = screen.getByTestId("discussion-workspace-grid");
    const taskPanel = screen.getByRole("tabpanel", { name: "题目" });
    const progressPanel = screen.getByRole("tabpanel", { name: "进程" });

    expect(grid).toHaveClass("relative", "min-[1200px]:grid");
    const tabletControls = screen.getByTestId("tablet-support-controls");
    expect(tabletControls).toHaveAttribute(
      "data-responsive-mode",
      "tablet-support",
    );
    expect(tabletControls).toHaveClass("bg-neutral-50");
    expect(tabletControls).toHaveClass("min-[1200px]:!hidden");
    expect(taskPanel).toHaveAttribute("data-support-mode", "sheet");
    expect(progressPanel).toHaveAttribute("data-support-mode", "sheet");
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
    const mobileTabs = screen.getByRole("tablist", {
      name: "讨论工作区",
    });
    expect(mobileTabs).toHaveAttribute("data-responsive-mode", "mobile-tabs");
    expect(mobileTabs).toHaveClass("bg-neutral-50");
    expect(tabs.map((tab) => tab.textContent)).toEqual([
      "讨论",
      "题目",
      "进程",
    ]);
    expect(tabs[0]).toHaveAttribute("aria-selected", "true");
    expect(tabs[0]).toHaveAttribute("tabindex", "0");
    expect(tabs[0]).toHaveClass(
      "aria-selected:border-indigo-600",
      "aria-selected:text-indigo-700",
    );
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

    expect(screen.getByTestId("task-brief-panel")).toHaveAttribute(
      "data-information-hierarchy",
      "task-brief",
    );
    expect(screen.getByTestId("task-brief-content")).toHaveAttribute(
      "data-content-priority",
      "primary",
    );
    expect(screen.getByText("CASE BRIEF")).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "题目与思考" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: QUESTION.title })).toHaveClass(
      "text-xl",
      "font-semibold",
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
      screen.getByText("资源分配型 · 标准 · 约 25 分钟"),
    ).toBeInTheDocument();
    expect(screen.queryByText("不进入初始任务面板")).not.toBeInTheDocument();
    expect(screen.queryByText("不渲染的利益相关方")).not.toBeInTheDocument();
    expect(screen.queryByText(QUESTION.id)).not.toBeInTheDocument();
    expect(
      screen.queryByText(/AI 提示|参考答案|建议发言/),
    ).not.toBeInTheDocument();
  });

  it.each([
    ["ORDERING_SELECTION", "排序选择型"],
    ["RESOURCE_ALLOCATION", "资源分配型"],
    ["PLAN_DESIGN", "方案策划型"],
  ])("presents %s with the frozen product label", (questionType, label) => {
    const { container } = render(
      <TaskBriefPanel
        notes=""
        onNotesChange={vi.fn()}
        questionState={{
          kind: "available",
          question: { ...QUESTION, question_type: questionType },
        }}
      />,
    );

    expect(screen.getByText(new RegExp(`^${label} ·`))).toBeVisible();
    expect(container.textContent).not.toMatch(/PRIORITIZATION|OPEN_DISCUSSION/);
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
    expect(
      screen.getByRole("region", { name: "我的思路 / 私人笔记" }),
    ).toHaveAttribute("data-private-notes", "memory-only");
    expect(
      screen.getByRole("region", { name: "我的思路 / 私人笔记" }),
    ).toHaveAttribute("data-private-notes", "memory-only");
    expect(notes).toHaveClass(
      "focus-visible:ring-2",
      "focus-visible:ring-indigo-500",
    );
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

    expect(screen.getByTestId("session-progress-panel")).toHaveAttribute(
      "data-progress-model",
      "six-phase",
    );
    expect(screen.getByText("SESSION STATE")).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "训练进程" }),
    ).toBeInTheDocument();
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
    const phases = within(phaseList).getAllByRole("listitem");
    expect(phases.map((item) => item.dataset.phaseState)).toEqual([
      "completed",
      "completed",
      "completed",
      "current",
      "upcoming",
      "upcoming",
    ]);
    expect(phases.map((item) => item.dataset.phaseNumber)).toEqual([
      "1",
      "2",
      "3",
      "4",
      "5",
      "6",
    ]);
    expect(
      within(phaseList).getByText("讨论与评估").closest("li"),
    ).toHaveAttribute("aria-current", "step");
    expect(screen.getByText("等待服务端提供阶段时间")).toBeInTheDocument();
    expect(screen.getByText("当前发言：AI 候选人 1")).toBeInTheDocument();
    expect(screen.getByText("连接正常")).toBeInTheDocument();
    expect(
      screen.queryByText(/Discussion Memory|讨论结构|投票|结论|报告|共识率/i),
    ).not.toBeInTheDocument();
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
