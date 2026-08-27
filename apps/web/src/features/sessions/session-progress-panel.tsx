import type { ReactNode } from "react";

import type { SessionSnapshot } from "@/lib/api/client";
import type { RealtimeConnectionState } from "@/lib/realtime/client";

import {
  DISCUSSION_PHASES,
  connectionLabel,
  floorLifecycleLabel,
  floorReasonLabel,
  participantLabel,
  phaseLabel,
} from "./session-presentation";

export type SessionProgressPanelProps = {
  status: SessionSnapshot["status"];
  countdown: string | null;
  participants: SessionSnapshot["floor"]["participants"];
  currentGrant: SessionSnapshot["floor"]["current_grant"];
  latestFloorEvent: SessionSnapshot["floor"]["latest_event"];
  connection: RealtimeConnectionState;
};

export default function SessionProgressPanel({
  status,
  countdown,
  participants,
  currentGrant,
  latestFloorEvent,
  connection,
}: SessionProgressPanelProps): ReactNode {
  const activeIndex = DISCUSSION_PHASES.findIndex((phase) => phase === status);
  const allCompleted = status === "COMPLETED";
  const floorOwner = currentGrant
    ? participantLabel(participants, currentGrant.participant_id)
    : null;
  const floorReason = currentGrant
    ? floorReasonLabel(currentGrant.reason_code)
    : latestFloorEvent
      ? floorReasonLabel(latestFloorEvent.reason_code)
      : null;

  return (
    <div className="flex min-h-0 flex-col gap-6">
      <section aria-labelledby="phase-progress-heading">
        <div className="flex items-baseline justify-between gap-3">
          <h2 className="text-sm font-semibold" id="phase-progress-heading">
            当前阶段
          </h2>
          <p className="text-sm font-medium text-neutral-900">
            {phaseLabel(status)}
          </p>
        </div>
        <p className="mt-2 text-sm tabular-nums text-neutral-600">
          {countdown ?? "等待服务端提供阶段时间"}
        </p>
        <ol aria-label="讨论阶段" className="mt-4 space-y-1.5">
          {DISCUSSION_PHASES.map((phase, index) => {
            const state =
              phase === status
                ? "current"
                : allCompleted || (activeIndex >= 0 && index < activeIndex)
                  ? "completed"
                  : "remaining";
            return (
              <li
                aria-current={state === "current" ? "step" : undefined}
                className={`rounded-md px-3 py-2 text-sm ${
                  state === "current"
                    ? "bg-neutral-900 font-medium text-white"
                    : state === "completed"
                      ? "bg-neutral-100 text-neutral-700"
                      : "text-neutral-500"
                }`}
                data-phase-state={state}
                key={phase}
              >
                {phaseLabel(phase)}
              </li>
            );
          })}
        </ol>
      </section>

      <section
        aria-labelledby="floor-progress-heading"
        className="border-t border-neutral-200 pt-5"
      >
        <h2 className="text-sm font-semibold" id="floor-progress-heading">
          发言进程
        </h2>
        <p className="mt-3 text-sm font-medium text-neutral-900">
          {floorOwner ? `当前发言：${floorOwner}` : "正在安排下一位发言者"}
        </p>
        <p className="mt-1 text-sm text-neutral-600">
          {floorLifecycleLabel(latestFloorEvent)}
        </p>
        {floorReason ? (
          <p className="mt-1 text-xs leading-5 text-neutral-500">
            {floorReason}
          </p>
        ) : null}
      </section>

      <section
        aria-labelledby="connection-progress-heading"
        className="border-t border-neutral-200 pt-5"
      >
        <h2 className="text-sm font-semibold" id="connection-progress-heading">
          讨论连接
        </h2>
        <p
          className="mt-2 text-sm text-neutral-600"
          data-connection-state={connection}
        >
          {connectionLabel(connection)}
        </p>
      </section>
    </div>
  );
}
