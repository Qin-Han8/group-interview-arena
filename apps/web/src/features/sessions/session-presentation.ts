import type { SessionSnapshot } from "@/lib/api/client";
import type { RealtimeConnectionState } from "@/lib/realtime/client";

export const DISCUSSION_PHASES = [
  "PREPARATION",
  "OPENING_STATEMENTS",
  "EXPLORATION",
  "CONFLICT_AND_EVALUATION",
  "CONVERGENCE",
  "FINAL_SUMMARY",
] as const;

export type DiscussionPhase = (typeof DISCUSSION_PHASES)[number];

export type PresentationTone =
  "neutral" | "current" | "information" | "recoverable" | "fatal";

const PHASE_LABELS: Record<SessionSnapshot["status"], string> = {
  CREATED: "未开始",
  PREPARATION: "准备",
  OPENING_STATEMENTS: "个人陈述",
  EXPLORATION: "观点探索",
  CONFLICT_AND_EVALUATION: "讨论与评估",
  CONVERGENCE: "收敛决策",
  FINAL_SUMMARY: "最终总结",
  COMPLETED: "已完成",
  ABORTED_USER: "已结束",
};

const CONNECTION_LABELS: Record<RealtimeConnectionState, string> = {
  connected: "连接正常",
  connecting: "正在连接讨论…",
  reconnecting: "正在同步最新讨论记录…",
  disconnected: "讨论连接暂时不可用",
};

const FLOOR_REASON_LABELS: Record<string, string> = {
  PHASE_MANDATED_TURN: "当前阶段要求的发言机会",
  EXPLICIT_OPPORTUNITY: "已接受的发言机会",
  FIRST_OPPORTUNITY: "优先安排尚未发言的参与者",
  FAIRNESS_RECOVERY: "恢复发言机会公平性",
  MONOPOLY_PREVENTION: "避免同一参与者连续占用发言权",
  PHASE_SUMMARY_OPPORTUNITY: "当前阶段的总结机会",
  SILENCE_RECOVERY: "讨论静默，需要主持介入",
  DEADLINE_RECOVERY: "阶段临近截止，需要主持介入",
  NO_ELIGIBLE_PARTICIPANT: "当前没有符合条件的参与者",
  SPEAKER_FINISHED: "发言已结束",
  INTERRUPTED: "发言已被中止",
  PHASE_CHANGED: "阶段已切换",
  SESSION_TERMINATED: "会话已结束",
};

export function phaseLabel(status: SessionSnapshot["status"]): string {
  return PHASE_LABELS[status];
}

export function sessionStatusLabel(status: SessionSnapshot["status"]): string {
  if (status === "CREATED") return "已创建";
  if (status === "COMPLETED") return "已完成";
  if (status === "ABORTED_USER") return "已由用户结束";
  return "进行中";
}

export function connectionLabel(state: RealtimeConnectionState): string {
  return CONNECTION_LABELS[state];
}

export function participantLabel(
  participants: SessionSnapshot["floor"]["participants"],
  participantId: string,
): string {
  const participant = participants.find(
    (candidate) => candidate.participant_id === participantId,
  );
  if (!participant) return "会话参与者";
  if (participant.actor_kind === "HUMAN") return "你（真人参与者）";
  if (participant.actor_kind === "SYSTEM") return "系统主持";

  const aiParticipants = participants
    .filter((candidate) => candidate.actor_kind === "AI")
    .sort((left, right) => left.seat_order - right.seat_order);
  const index = aiParticipants.findIndex(
    (candidate) => candidate.participant_id === participantId,
  );
  return index >= 0 ? `AI 候选人 ${index + 1}` : "AI 候选人";
}

export function floorLifecycleLabel(
  event: SessionSnapshot["floor"]["latest_event"],
): string {
  if (!event) return "等待服务端分配发言权";
  if (event.type === "floor.granted") return "发言权已授予";
  if (event.type === "floor.released") return "发言权已释放";
  return "已请求主持介入";
}

export function floorReasonLabel(reasonCode: string): string {
  return FLOOR_REASON_LABELS[reasonCode] ?? "正在安排讨论进程";
}
