"use client";

import { useRef, type KeyboardEvent, type ReactNode } from "react";

import type { RealtimeConnectionState } from "@/lib/realtime/client";

export type ActiveDiscussionSurface = "discussion" | "task" | "progress";

export type SessionHeaderAction = {
  visible: boolean;
  disabled: boolean;
  label: string;
  onActivate: () => void;
};

export type SessionHeaderProps = {
  productName: "AI 群面训练场";
  sessionTitle: string;
  phaseLabel: string;
  countdown: string | null;
  connection: RealtimeConnectionState;
  connectionLabel: string;
  startAction: SessionHeaderAction;
  endAction: SessionHeaderAction;
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

function HeaderAction({ action }: { action: SessionHeaderAction }) {
  if (!action.visible) return null;

  return (
    <button
      className="rounded-md border border-neutral-300 bg-white px-3 py-2 text-sm font-medium text-neutral-800 disabled:cursor-not-allowed disabled:opacity-50"
      disabled={action.disabled}
      onClick={action.onActivate}
      type="button"
    >
      {action.label}
    </button>
  );
}

function SessionHeader({
  productName,
  sessionTitle,
  phaseLabel,
  countdown,
  connection,
  connectionLabel,
  startAction,
  endAction,
}: SessionHeaderProps) {
  return (
    <header className="flex shrink-0 flex-wrap items-center justify-between gap-4 border-b border-neutral-200 bg-white px-4 py-3 sm:px-6">
      <div className="min-w-0">
        <p className="text-xs font-medium tracking-[0.12em] text-neutral-500 uppercase">
          {productName}
        </p>
        <h1 className="mt-1 truncate text-lg font-semibold tracking-tight">
          {sessionTitle}
        </h1>
      </div>

      <div className="flex flex-wrap items-center justify-end gap-3 text-sm">
        <p className="rounded-full bg-neutral-100 px-3 py-1.5 font-medium">
          {phaseLabel}
        </p>
        {countdown ? (
          <p className="tabular-nums text-neutral-600">{countdown}</p>
        ) : null}
        <p className="text-neutral-600" data-connection-state={connection}>
          {connectionLabel}
        </p>
        <HeaderAction action={startAction} />
        <HeaderAction action={endAction} />
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
    <div className="flex h-dvh max-h-dvh w-full flex-col overflow-hidden bg-neutral-100 text-neutral-950">
      <SessionHeader {...header} />

      <nav
        aria-label="讨论工作区"
        className="flex shrink-0 border-b border-neutral-200 bg-white md:hidden"
        role="tablist"
      >
        {SURFACES.map((surface, index) => {
          const selected = activeSurface === surface.id;
          return (
            <button
              aria-controls={`${surface.id}-surface`}
              aria-selected={selected}
              className="flex-1 border-b-2 border-transparent px-3 py-3 text-sm font-medium text-neutral-500 aria-selected:border-neutral-900 aria-selected:text-neutral-950"
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

      <div className="hidden shrink-0 items-center justify-end gap-2 border-b border-neutral-200 bg-white px-5 py-2 md:flex min-[1200px]:hidden">
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
        className="relative min-h-0 flex-1 overflow-hidden p-4 min-[1200px]:grid min-[1200px]:grid-cols-[minmax(15rem,1fr)_minmax(32rem,2.2fr)_minmax(15rem,1fr)] min-[1200px]:gap-4"
        data-support-surface={activeSurface}
        data-testid="discussion-workspace-grid"
      >
        <aside
          aria-labelledby="task-tab"
          className={`${
            activeSurface === "task" ? "block" : "hidden"
          } studio-scroll-region min-h-0 overflow-y-auto rounded-xl border border-neutral-200 bg-white p-4 md:absolute md:inset-y-4 md:right-4 md:z-20 md:w-96 md:max-w-[calc(100%_-_2rem)] md:shadow-xl min-[1200px]:!static min-[1200px]:!block min-[1200px]:!w-auto min-[1200px]:!max-w-none min-[1200px]:!shadow-none`}
          id="task-surface"
          role="tabpanel"
          tabIndex={0}
        >
          {taskBrief}
        </aside>

        <section
          aria-labelledby="discussion-tab"
          className={`${
            activeSurface === "discussion" ? "block" : "hidden"
          } studio-scroll-region h-full min-h-0 overflow-hidden rounded-xl border border-neutral-200 bg-white md:block`}
          data-region-priority="primary"
          id="discussion-surface"
          role="tabpanel"
          tabIndex={0}
        >
          {discussion}
        </section>

        <aside
          aria-labelledby="progress-tab"
          className={`${
            activeSurface === "progress" ? "block" : "hidden"
          } studio-scroll-region min-h-0 overflow-y-auto rounded-xl border border-neutral-200 bg-white p-4 md:absolute md:inset-y-4 md:right-4 md:z-20 md:w-96 md:max-w-[calc(100%_-_2rem)] md:shadow-xl min-[1200px]:!static min-[1200px]:!block min-[1200px]:!w-auto min-[1200px]:!max-w-none min-[1200px]:!shadow-none`}
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
