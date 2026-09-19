"use client";

import {
  useEffect,
  useRef,
  useState,
  type CSSProperties,
  type KeyboardEvent,
  type PointerEvent,
  type ReactNode,
} from "react";

import type { RealtimeConnectionState } from "@/lib/realtime/client";
import {
  DEFAULT_TRAINING_WORKSPACE_LAYOUT,
  TRAINING_WORKSPACE_LAYOUT_BOUNDS,
  readTrainingWorkspaceLayout,
  writeTrainingWorkspaceLayout,
  type TrainingWorkspaceLayout,
} from "@/lib/ui/training-workspace-layout";

export type ActiveDiscussionSurface = "discussion" | "task" | "progress";

export type SessionHeaderAction = {
  visible: boolean;
  disabled: boolean;
  label: string;
  onActivate: () => void;
};

export type SessionHeaderProps = {
  sessionTitle: string;
  phaseLabel: string;
  countdown: string | null;
  connection: RealtimeConnectionState;
  connectionLabel: string;
  startAction: SessionHeaderAction;
  endAction: SessionHeaderAction;
  reportAction: SessionHeaderAction;
};

export type DiscussionWorkspaceProps = {
  header: SessionHeaderProps;
  taskBrief: ReactNode;
  discussion: ReactNode;
  progress: ReactNode;
  activeSurface: ActiveDiscussionSurface;
  onActiveSurfaceChange: (surface: ActiveDiscussionSurface) => void;
};

const SURFACES: ReadonlyArray<{
  id: ActiveDiscussionSurface;
  label: string;
}> = [
  { id: "discussion", label: "讨论" },
  { id: "task", label: "题目" },
  { id: "progress", label: "进程" },
];

const DESKTOP_MEDIA_QUERY = "(min-width: 1200px)";
const WORKSPACE_HORIZONTAL_PADDING = 32;
const WORKSPACE_SEPARATOR_WIDTH = 16;
const WORKSPACE_COLUMN_GAP = 4;
const WORKSPACE_STRUCTURE_WIDTH =
  WORKSPACE_HORIZONTAL_PADDING +
  WORKSPACE_SEPARATOR_WIDTH * 2 +
  WORKSPACE_COLUMN_GAP * 4;
const MINIMUM_DESKTOP_WORKSPACE_WIDTH =
  WORKSPACE_STRUCTURE_WIDTH +
  TRAINING_WORKSPACE_LAYOUT_BOUNDS.left.min +
  TRAINING_WORKSPACE_LAYOUT_BOUNDS.centerMin +
  TRAINING_WORKSPACE_LAYOUT_BOUNDS.right.min;

type ResizeSide = "left" | "right";

type ActiveResize = {
  pointerId: number;
  side: ResizeSide;
  startClientX: number;
  startWidth: number;
};

function clamp(value: number, min: number, max: number) {
  return Math.min(Math.max(value, min), max);
}

function dynamicMaximum(
  side: ResizeSide,
  workspaceWidth: number,
  otherWidth: number,
) {
  const hardBounds = TRAINING_WORKSPACE_LAYOUT_BOUNDS[side];
  const centerProtectedMaximum =
    workspaceWidth -
    WORKSPACE_STRUCTURE_WIDTH -
    TRAINING_WORKSPACE_LAYOUT_BOUNDS.centerMin -
    otherWidth;
  return Math.max(
    hardBounds.min,
    Math.min(hardBounds.max, centerProtectedMaximum),
  );
}

function effectiveLayout(
  layout: TrainingWorkspaceLayout,
  workspaceWidth: number,
): TrainingWorkspaceLayout {
  const rightWidth = clamp(
    layout.rightWidth,
    TRAINING_WORKSPACE_LAYOUT_BOUNDS.right.min,
    TRAINING_WORKSPACE_LAYOUT_BOUNDS.right.max,
  );
  const leftWidth = clamp(
    layout.leftWidth,
    TRAINING_WORKSPACE_LAYOUT_BOUNDS.left.min,
    dynamicMaximum("left", workspaceWidth, rightWidth),
  );
  return { leftWidth, rightWidth };
}

function HeaderAction({ action }: { action: SessionHeaderAction }) {
  if (!action.visible) return null;

  return (
    <button
      className="shrink-0 whitespace-nowrap rounded-md border border-neutral-300 bg-white px-3 py-2 text-sm font-medium text-neutral-800 disabled:cursor-not-allowed disabled:opacity-50"
      disabled={action.disabled}
      onClick={action.onActivate}
      type="button"
    >
      {action.label}
    </button>
  );
}

function SessionHeader({
  sessionTitle,
  phaseLabel,
  countdown,
  connection,
  connectionLabel,
  startAction,
  endAction,
  reportAction,
}: SessionHeaderProps) {
  return (
    <header
      className="training-session-header shrink-0 border-b border-neutral-200 bg-white px-4 py-2.5 sm:px-5"
      data-testid="training-session-header"
    >
      <div
        className="training-session-header-title min-w-0"
        data-overflow-policy="truncate"
        data-testid="header-title-region"
      >
        <p className="text-[0.625rem] font-semibold tracking-[0.16em] text-neutral-500 uppercase">
          Live session
        </p>
        <h1 className="mt-0.5 truncate text-xl font-semibold tracking-tight text-neutral-950">
          {sessionTitle}
        </h1>
      </div>

      <div
        className="training-session-header-status flex flex-wrap items-center justify-end gap-3 text-sm"
        data-control-priority="preserve"
        data-testid="header-status-region"
      >
        <p
          className="rounded-full border border-indigo-100 bg-indigo-50 px-3 py-1.5 font-medium text-indigo-950"
          data-session-phase={phaseLabel}
          data-testid="header-phase"
        >
          {phaseLabel}
        </p>
        {countdown ? (
          <p
            className="tabular-nums text-neutral-600"
            data-testid="header-countdown"
          >
            {countdown}
          </p>
        ) : null}
        <p className="text-neutral-600" data-connection-state={connection}>
          {connectionLabel}
        </p>
        <div
          className="training-session-header-actions flex shrink-0 items-center gap-2"
          data-testid="header-actions"
        >
          <HeaderAction action={startAction} />
          <HeaderAction action={endAction} />
          <HeaderAction action={reportAction} />
        </div>
      </div>
    </header>
  );
}

export default function DiscussionWorkspace({
  header,
  taskBrief,
  discussion,
  progress,
  activeSurface,
  onActiveSurfaceChange,
}: DiscussionWorkspaceProps): ReactNode {
  const tabRefs = useRef<Array<HTMLButtonElement | null>>([]);
  const workspaceRef = useRef<HTMLDivElement | null>(null);
  const activeResizeRef = useRef<ActiveResize | undefined>(undefined);
  const preferenceLoadedRef = useRef(false);
  const [desktopViewport, setDesktopViewport] = useState(() => {
    if (typeof window === "undefined") return false;
    if (typeof window.matchMedia !== "function") {
      return window.innerWidth >= 1200;
    }
    return window.matchMedia(DESKTOP_MEDIA_QUERY).matches;
  });
  const [workspaceWidth, setWorkspaceWidth] = useState(0);
  const [layout, setLayout] = useState<TrainingWorkspaceLayout>({
    ...DEFAULT_TRAINING_WORKSPACE_LAYOUT,
  });
  const layoutRef = useRef(layout);
  const [resizingSide, setResizingSide] = useState<ResizeSide>();

  useEffect(() => {
    if (typeof window.matchMedia !== "function") return;
    const mediaQuery = window.matchMedia(DESKTOP_MEDIA_QUERY);
    const update = (event: MediaQueryListEvent) =>
      setDesktopViewport(event.matches);
    mediaQuery.addEventListener("change", update);
    return () => mediaQuery.removeEventListener("change", update);
  }, []);

  useEffect(() => {
    const workspace = workspaceRef.current;
    if (!workspace) return;

    const updateWidth = (width: number) => {
      if (Number.isFinite(width) && width >= 0) setWorkspaceWidth(width);
    };
    updateWidth(workspace.getBoundingClientRect().width);

    if (typeof ResizeObserver === "undefined") {
      const updateFromWindow = () =>
        updateWidth(workspace.getBoundingClientRect().width);
      window.addEventListener("resize", updateFromWindow);
      return () => window.removeEventListener("resize", updateFromWindow);
    }

    const observer = new ResizeObserver((entries) => {
      const entry = entries[0];
      if (entry) {
        updateWidth(
          entry.target.getBoundingClientRect().width || entry.contentRect.width,
        );
      }
    });
    observer.observe(workspace);
    return () => observer.disconnect();
  }, []);

  const desktopLayoutReady =
    desktopViewport && workspaceWidth >= MINIMUM_DESKTOP_WORKSPACE_WIDTH;

  useEffect(() => {
    if (!desktopLayoutReady || preferenceLoadedRef.current) return;
    preferenceLoadedRef.current = true;
    const preference = readTrainingWorkspaceLayout();
    layoutRef.current = preference;
    setLayout(preference);
  }, [desktopLayoutReady]);

  const appliedLayout = effectiveLayout(layout, workspaceWidth);
  const leftMaximum = dynamicMaximum(
    "left",
    workspaceWidth,
    appliedLayout.rightWidth,
  );
  const rightMaximum = dynamicMaximum(
    "right",
    workspaceWidth,
    appliedLayout.leftWidth,
  );

  function updateLayout(next: TrainingWorkspaceLayout, persist: boolean) {
    layoutRef.current = next;
    setLayout(next);
    if (persist) writeTrainingWorkspaceLayout(next);
  }

  function requestedLayout(side: ResizeSide, requestedWidth: number) {
    const current = effectiveLayout(layoutRef.current, workspaceWidth);
    if (side === "left") {
      return {
        leftWidth: clamp(
          requestedWidth,
          TRAINING_WORKSPACE_LAYOUT_BOUNDS.left.min,
          dynamicMaximum("left", workspaceWidth, current.rightWidth),
        ),
        rightWidth: current.rightWidth,
      };
    }
    return {
      leftWidth: current.leftWidth,
      rightWidth: clamp(
        requestedWidth,
        TRAINING_WORKSPACE_LAYOUT_BOUNDS.right.min,
        dynamicMaximum("right", workspaceWidth, current.leftWidth),
      ),
    };
  }

  function handleResizeStart(
    event: PointerEvent<HTMLDivElement>,
    side: ResizeSide,
  ) {
    event.preventDefault();
    const current = effectiveLayout(layoutRef.current, workspaceWidth);
    activeResizeRef.current = {
      pointerId: event.pointerId,
      side,
      startClientX: event.clientX,
      startWidth: side === "left" ? current.leftWidth : current.rightWidth,
    };
    event.currentTarget.setPointerCapture(event.pointerId);
    setResizingSide(side);
  }

  function handleResizeMove(event: PointerEvent<HTMLDivElement>) {
    const active = activeResizeRef.current;
    if (!active || active.pointerId !== event.pointerId) return;
    const horizontalDelta = event.clientX - active.startClientX;
    const requestedWidth =
      active.side === "left"
        ? active.startWidth + horizontalDelta
        : active.startWidth - horizontalDelta;
    updateLayout(requestedLayout(active.side, requestedWidth), false);
  }

  function finishResize(event: PointerEvent<HTMLDivElement>) {
    const active = activeResizeRef.current;
    if (!active || active.pointerId !== event.pointerId) return;
    activeResizeRef.current = undefined;
    setResizingSide(undefined);
    if (event.currentTarget.hasPointerCapture(event.pointerId)) {
      event.currentTarget.releasePointerCapture(event.pointerId);
    }
    writeTrainingWorkspaceLayout(layoutRef.current);
  }

  function handleSeparatorKeyDown(
    event: KeyboardEvent<HTMLDivElement>,
    side: ResizeSide,
  ) {
    if (event.key !== "ArrowLeft" && event.key !== "ArrowRight") return;
    event.preventDefault();
    const step = event.shiftKey ? 40 : 16;
    const axisDelta = event.key === "ArrowRight" ? step : -step;
    const current = effectiveLayout(layoutRef.current, workspaceWidth);
    const currentWidth =
      side === "left" ? current.leftWidth : current.rightWidth;
    const requestedWidth =
      side === "left" ? currentWidth + axisDelta : currentWidth - axisDelta;
    updateLayout(requestedLayout(side, requestedWidth), true);
  }

  function handleTabKeyDown(
    event: KeyboardEvent<HTMLButtonElement>,
    currentIndex: number,
  ) {
    let nextIndex: number | undefined;

    if (event.key === "ArrowRight") {
      nextIndex = (currentIndex + 1) % SURFACES.length;
    } else if (event.key === "ArrowLeft") {
      nextIndex = (currentIndex - 1 + SURFACES.length) % SURFACES.length;
    } else if (event.key === "Home") {
      nextIndex = 0;
    } else if (event.key === "End") {
      nextIndex = SURFACES.length - 1;
    }

    if (nextIndex === undefined) return;
    event.preventDefault();
    onActiveSurfaceChange(SURFACES[nextIndex].id);
    tabRefs.current[nextIndex]?.focus();
  }

  function toggleSupportSurface(surface: "task" | "progress") {
    onActiveSurfaceChange(activeSurface === surface ? "discussion" : surface);
  }

  return (
    <div
      className="flex h-full max-h-full w-full flex-col overflow-hidden bg-[#f3f5f9] text-slate-950"
      data-product-surface="interview-simulation-studio"
      data-scroll-owner="viewport-constrained"
      data-visual-reference="demo-v2"
    >
      <SessionHeader {...header} />

      <nav
        aria-label="讨论工作区"
        className="flex shrink-0 border-b border-neutral-200 bg-neutral-50 md:hidden"
        data-responsive-mode="mobile-tabs"
        role="tablist"
      >
        {SURFACES.map((surface, index) => {
          const selected = activeSurface === surface.id;
          return (
            <button
              aria-controls={`${surface.id}-surface`}
              aria-selected={selected}
              className="flex-1 border-b-2 border-transparent px-3 py-3 text-sm font-medium text-neutral-500 aria-selected:border-indigo-600 aria-selected:text-indigo-700"
              id={`${surface.id}-tab`}
              key={surface.id}
              onClick={() => onActiveSurfaceChange(surface.id)}
              onKeyDown={(event) => handleTabKeyDown(event, index)}
              ref={(element) => {
                tabRefs.current[index] = element;
              }}
              role="tab"
              tabIndex={selected ? 0 : -1}
              type="button"
            >
              {surface.label}
            </button>
          );
        })}
      </nav>

      <div
        className={`hidden shrink-0 items-center justify-end gap-2 border-b border-neutral-200 bg-neutral-50 px-5 py-2 md:flex ${desktopLayoutReady ? "min-[1200px]:!hidden" : ""}`}
        data-responsive-mode="tablet-support"
        data-testid="tablet-support-controls"
      >
        <button
          aria-pressed={activeSurface === "task"}
          className="rounded-md border border-neutral-300 px-3 py-1.5 text-sm aria-pressed:bg-neutral-900 aria-pressed:text-white"
          onClick={() => toggleSupportSurface("task")}
          type="button"
        >
          {activeSurface === "task" ? "关闭题目与思考" : "打开题目与思考"}
        </button>
        <button
          aria-pressed={activeSurface === "progress"}
          className="rounded-md border border-neutral-300 px-3 py-1.5 text-sm aria-pressed:bg-neutral-900 aria-pressed:text-white"
          onClick={() => toggleSupportSurface("progress")}
          type="button"
        >
          {activeSurface === "progress" ? "关闭训练进程" : "打开训练进程"}
        </button>
      </div>

      <div
        className={`relative min-h-0 flex-1 overflow-hidden p-3 sm:p-4 ${desktopLayoutReady ? "training-workspace-grid min-[1200px]:grid" : ""}`}
        data-center-min-width={TRAINING_WORKSPACE_LAYOUT_BOUNDS.centerMin}
        data-desktop-columns={`support-${appliedLayout.leftWidth} primary-min-520 support-${appliedLayout.rightWidth}`}
        data-desktop-layout="three-column"
        data-resizable-layout={desktopLayoutReady}
        data-resizing-panel={resizingSide}
        data-scroll-owner="none"
        data-support-surface={activeSurface}
        data-testid="discussion-workspace-grid"
        ref={workspaceRef}
        style={
          desktopLayoutReady
            ? ({
                "--workspace-left-width": `${appliedLayout.leftWidth}px`,
                "--workspace-right-width": `${appliedLayout.rightWidth}px`,
              } as CSSProperties)
            : undefined
        }
      >
        <aside
          aria-labelledby="task-tab"
          className={`${
            activeSurface === "task" ? "block" : "hidden"
          } studio-scroll-region min-h-0 overflow-y-auto rounded-xl border border-neutral-200 bg-white p-4 md:absolute md:inset-y-4 md:right-4 md:z-20 md:w-96 md:max-w-[calc(100%_-_2rem)] md:shadow-xl ${desktopLayoutReady ? "min-[1200px]:!static min-[1200px]:!block min-[1200px]:!w-auto min-[1200px]:!max-w-none min-[1200px]:!shadow-[0_8px_24px_rgba(15,23,42,0.04)]" : ""}`}
          data-support-mode="sheet"
          data-region-priority="support"
          data-scroll-owner="task-panel"
          id="task-surface"
          role="tabpanel"
          tabIndex={0}
        >
          {taskBrief}
        </aside>

        {desktopLayoutReady ? (
          <div
            aria-label="调整题目与思考面板宽度"
            aria-orientation="vertical"
            aria-valuemax={leftMaximum}
            aria-valuemin={TRAINING_WORKSPACE_LAYOUT_BOUNDS.left.min}
            aria-valuenow={appliedLayout.leftWidth}
            className="training-workspace-separator"
            data-dragging={resizingSide === "left"}
            data-separator-side="left"
            onKeyDown={(event) => handleSeparatorKeyDown(event, "left")}
            onLostPointerCapture={finishResize}
            onPointerCancel={finishResize}
            onPointerDown={(event) => handleResizeStart(event, "left")}
            onPointerMove={handleResizeMove}
            onPointerUp={finishResize}
            role="separator"
            tabIndex={0}
          />
        ) : null}

        <section
          aria-labelledby="discussion-tab"
          className={`${
            activeSurface === "discussion" ? "block" : "hidden"
          } studio-scroll-region h-full min-h-0 overflow-hidden rounded-xl border border-neutral-200 bg-white md:block ${desktopLayoutReady ? "min-[1200px]:shadow-[0_12px_32px_rgba(15,23,42,0.08)] min-[1200px]:ring-1 min-[1200px]:ring-neutral-200" : ""}`}
          data-region-priority="primary"
          data-region-role="live-discussion"
          data-scroll-owner="discussion-transcript"
          id="discussion-surface"
          role="tabpanel"
          tabIndex={0}
        >
          {discussion}
        </section>

        {desktopLayoutReady ? (
          <div
            aria-label="调整训练进程面板宽度"
            aria-orientation="vertical"
            aria-valuemax={rightMaximum}
            aria-valuemin={TRAINING_WORKSPACE_LAYOUT_BOUNDS.right.min}
            aria-valuenow={appliedLayout.rightWidth}
            className="training-workspace-separator"
            data-dragging={resizingSide === "right"}
            data-separator-side="right"
            onKeyDown={(event) => handleSeparatorKeyDown(event, "right")}
            onLostPointerCapture={finishResize}
            onPointerCancel={finishResize}
            onPointerDown={(event) => handleResizeStart(event, "right")}
            onPointerMove={handleResizeMove}
            onPointerUp={finishResize}
            role="separator"
            tabIndex={0}
          />
        ) : null}

        <aside
          aria-labelledby="progress-tab"
          className={`${
            activeSurface === "progress" ? "block" : "hidden"
          } studio-scroll-region min-h-0 overflow-y-auto rounded-xl border border-neutral-200 bg-white p-4 md:absolute md:inset-y-4 md:right-4 md:z-20 md:w-96 md:max-w-[calc(100%_-_2rem)] md:shadow-xl ${desktopLayoutReady ? "min-[1200px]:!static min-[1200px]:!block min-[1200px]:!w-auto min-[1200px]:!max-w-none min-[1200px]:!shadow-[0_8px_24px_rgba(15,23,42,0.04)]" : ""}`}
          data-support-mode="sheet"
          data-region-priority="support"
          data-scroll-owner="progress-panel"
          id="progress-surface"
          role="tabpanel"
          tabIndex={0}
        >
          {progress}
        </aside>
      </div>
    </div>
  );
}
