import { describe, expect, it } from "vitest";

import type { SessionSnapshot } from "@/lib/api/client";

import {
  DISCUSSION_PHASES,
  connectionLabel,
  floorLifecycleLabel,
  floorReasonLabel,
  participantLabel,
  phaseLabel,
  sessionStatusLabel,
} from "./session-presentation";

const PARTICIPANTS: SessionSnapshot["floor"]["participants"] = [
  {
    participant_id: "00000000-0000-4000-8000-000000000001",
    actor_kind: "HUMAN",
    seat_order: 1,
  },
  {
    participant_id: "00000000-0000-4000-8000-000000000003",
    actor_kind: "AI",
    seat_order: 3,
  },
  {
    participant_id: "00000000-0000-4000-8000-000000000002",
    actor_kind: "AI",
    seat_order: 2,
  },
];

describe("session presentation helpers", () => {
  it("freezes the six authoritative phases and exact product labels", () => {
    expect(DISCUSSION_PHASES).toEqual([
      "PREPARATION",
      "OPENING_STATEMENTS",
      "EXPLORATION",
      "CONFLICT_AND_EVALUATION",
      "CONVERGENCE",
      "FINAL_SUMMARY",
    ]);
    expect(DISCUSSION_PHASES.map((phase) => phaseLabel(phase))).toEqual([
      "准备",
      "个人陈述",
      "观点探索",
      "讨论与评估",
      "收敛决策",
      "最终总结",
    ]);
    expect(phaseLabel("CREATED")).toBe("未开始");
    expect(phaseLabel("COMPLETED")).toBe("已完成");
    expect(phaseLabel("ABORTED_USER")).toBe("已结束");
  });

  it("maps lifecycle and connection state to safe display copy only", () => {
    expect(sessionStatusLabel("CREATED")).toBe("已创建");
    expect(sessionStatusLabel("PREPARATION")).toBe("进行中");
    expect(sessionStatusLabel("COMPLETED")).toBe("已完成");
    expect(sessionStatusLabel("ABORTED_USER")).toBe("已由用户结束");
    expect(connectionLabel("connected")).toBe("连接正常");
    expect(connectionLabel("connecting")).toBe("正在连接讨论…");
    expect(connectionLabel("reconnecting")).toBe("正在同步最新讨论记录…");
    expect(connectionLabel("disconnected")).toBe("讨论连接暂时不可用");
  });

  it("derives safe participant, floor lifecycle and reason labels", () => {
    expect(participantLabel(PARTICIPANTS, PARTICIPANTS[0].participant_id)).toBe(
      "你（真人参与者）",
    );
    expect(participantLabel(PARTICIPANTS, PARTICIPANTS[1].participant_id)).toBe(
      "AI 候选人 2",
    );
    expect(participantLabel(PARTICIPANTS, "missing")).toBe("会话参与者");
    expect(floorLifecycleLabel(null)).toBe("等待服务端分配发言权");
    expect(
      floorLifecycleLabel({
        type: "floor.granted",
        sequence: 2,
        occurred_at: "2026-08-27T00:00:00Z",
        participant_id: PARTICIPANTS[0].participant_id,
        phase: "OPENING_STATEMENTS",
        reason_code: "FIRST_OPPORTUNITY",
      }),
    ).toBe("发言权已授予");
    expect(floorReasonLabel("FIRST_OPPORTUNITY")).toBe(
      "优先安排尚未发言的参与者",
    );
    expect(floorReasonLabel("UNKNOWN_REASON")).toBe("正在安排讨论进程");
  });
});
