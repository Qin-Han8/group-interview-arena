import { createRef } from "react";
import {
  cleanup,
  fireEvent,
  render,
  screen,
  within,
} from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { SessionSnapshot } from "@/lib/api/client";

import DiscussionStage, { type DiscussionStageProps } from "./discussion-stage";

const HUMAN_ID = "00000000-0000-4000-8000-000000000001";
const AI_ONE_ID = "00000000-0000-4000-8000-000000000002";
const AI_TWO_ID = "00000000-0000-4000-8000-000000000003";
const AI_THREE_ID = "00000000-0000-4000-8000-000000000004";
const GRANT_ID = "00000000-0000-4000-8000-000000000010";

const PARTICIPANTS: SessionSnapshot["floor"]["participants"] = [
  { participant_id: AI_THREE_ID, actor_kind: "AI", seat_order: 4 },
  { participant_id: HUMAN_ID, actor_kind: "HUMAN", seat_order: 1 },
  { participant_id: AI_ONE_ID, actor_kind: "AI", seat_order: 2 },
  { participant_id: AI_TWO_ID, actor_kind: "AI", seat_order: 3 },
  {
    participant_id: "00000000-0000-4000-8000-000000000005",
    actor_kind: "SYSTEM",
    seat_order: 5,
  },
];

const HUMAN_GRANT: NonNullable<SessionSnapshot["floor"]["current_grant"]> = {
  grant_id: GRANT_ID,
  participant_id: HUMAN_ID,
  phase: "OPENING_STATEMENTS",
  reason_code: "FIRST_OPPORTUNITY",
  granted_at: "2026-08-27T00:00:00Z",
};

const CONFIRMED: DiscussionStageProps["confirmedTranscript"] = [
  {
    utterance_id: "00000000-0000-4000-8000-000000000020",
    sequence: 5,
    occurred_at: "2026-08-27T00:01:00Z",
    action_id: "00000000-0000-4000-8000-000000000021",
    participant_id: HUMAN_ID,
    actor_kind: "HUMAN",
    floor_grant_id: GRANT_ID,
    phase: "OPENING_STATEMENTS",
    content: "  <strong>exact Human text</strong>\n**markdown stays text**  ",
  },
  {
    utterance_id: "00000000-0000-4000-8000-000000000022",
    sequence: 6,
    occurred_at: "2026-08-27T00:01:10Z",
    action_id: null,
    participant_id: AI_ONE_ID,
    actor_kind: "AI",
    floor_grant_id: "00000000-0000-4000-8000-000000000023",
    phase: "OPENING_STATEMENTS",
    content: "AI confirmed contribution",
  },
];

function stageProps(
  overrides: Partial<DiscussionStageProps> = {},
): DiscussionStageProps {
  return {
    status: "OPENING_STATEMENTS",
    participants: PARTICIPANTS,
    currentGrant: HUMAN_GRANT,
    confirmedTranscript: CONFIRMED,
    transcriptContainerRef: createRef<HTMLDivElement>(),
    draft: "😀 current draft",
    draftInspection: {
      codePointCount: 15,
      isSubmittable: true,
      invalidReason: null,
    },
    canSend: true,
    sendDisabledReason: "轮到你发言",
    onDraftChange: vi.fn(),
    onSubmit: vi.fn(),
    pendingContent: null,
    rejectedDraft: null,
    onRestoreRejectedDraft: vi.fn(),
    connection: "connected",
    connectionLabel: "连接正常",
    errorMessage: null,
    aiWaitingLabel: null,
    interruptedAiNotices: [],
    showComposer: true,
    ...overrides,
  };
}

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("DiscussionStage", () => {
  it("renders the authoritative Human and AI roster in safe seat order", () => {
    const { container, rerender } = render(
      <DiscussionStage {...stageProps()} />,
    );
    const strip = screen.getByRole("list", { name: "会话参与者" });
    expect(
      within(strip)
        .getAllByRole("listitem")
        .map((item) => item.textContent),
    ).toEqual([
      "你轮到你发言",
      "AI 候选人 1等待中",
      "AI 候选人 2等待中",
      "AI 候选人 3等待中",
    ]);
    expect(within(strip).getByText("你").closest("li")).toHaveAttribute(
      "data-participant-state",
      "current",
    );

    rerender(
      <DiscussionStage
        {...stageProps({
          currentGrant: { ...HUMAN_GRANT, participant_id: AI_TWO_ID },
          aiWaitingLabel: "AI 候选人 2 正在准备发言…",
        })}
      />,
    );
    expect(
      within(strip).getByText("AI 候选人 2").closest("li"),
    ).toHaveAttribute("data-participant-state", "current");
    expect(
      within(strip).getByText("AI 候选人 2").closest("li"),
    ).toHaveTextContent("正在准备发言");
    expect(container.textContent).not.toMatch(
      /强势型|固执型|逻辑型|persona|strategy|emotion|provider|model/i,
    );
    expect(container.textContent).not.toContain("系统主持");
  });

  it("renders one plain-text confirmed transcript without pending or rejected content", () => {
    render(
      <DiscussionStage
        {...stageProps({
          pendingContent: "pending must stay outside",
          rejectedDraft: {
            content: "rejected must stay outside",
            message: "这条发言当前无法提交，请确认发言机会后重试。",
            restoreLabel: "用被拒发言替换当前草稿",
          },
        })}
      />,
    );

    const transcript = screen.getByTestId("confirmed-transcript");
    const list = screen.getByTestId("confirmed-transcript-list");
    expect(list).not.toHaveAttribute("aria-live");
    expect(within(list).getAllByRole("listitem")).toHaveLength(2);
    const exact = within(list).getByTestId(
      `utterance-content-${CONFIRMED[0].utterance_id}`,
    );
    expect(exact.textContent).toBe(CONFIRMED[0].content);
    expect(exact).toHaveClass("whitespace-pre-wrap");
    expect(exact.querySelector("strong")).toBeNull();
    expect(
      within(transcript).queryByText("pending must stay outside"),
    ).toBeNull();
    expect(
      within(transcript).queryByText("rejected must stay outside"),
    ).toBeNull();
  });

  it("keeps composer input delegated and obeys supplied submit authority", () => {
    const onDraftChange = vi.fn();
    const onSubmit = vi.fn();
    const { rerender } = render(
      <DiscussionStage
        {...stageProps({
          canSend: false,
          onDraftChange,
          onSubmit,
          sendDisabledReason: "你可以先整理观点，轮到你时再发送",
        })}
      />,
    );

    const textarea = screen.getByLabelText("发言草稿");
    expect(textarea).toBeEnabled();
    expect(screen.getByText("15 / 4000")).toBeInTheDocument();
    expect(
      screen.getByText("你可以先整理观点，轮到你时再发送"),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "发送发言" })).toBeDisabled();
    fireEvent.change(textarea, { target: { value: "new draft" } });
    expect(onDraftChange).toHaveBeenCalledWith("new draft");
    expect(fireEvent.keyDown(textarea, { key: "Enter" })).toBe(true);
    fireEvent.keyDown(textarea, { key: "Enter", ctrlKey: true });
    expect(onSubmit).not.toHaveBeenCalled();

    rerender(
      <DiscussionStage
        {...stageProps({ canSend: true, onDraftChange, onSubmit })}
      />,
    );
    fireEvent.keyDown(screen.getByLabelText("发言草稿"), {
      key: "Enter",
      metaKey: true,
    });
    expect(onSubmit).toHaveBeenCalledOnce();
    expect(screen.getByTestId("human-composer")).toHaveClass(
      "sticky",
      "bottom-0",
    );
  });

  it("keeps pending and rejected content separate and delegates explicit restore", () => {
    const onRestoreRejectedDraft = vi.fn();
    render(
      <DiscussionStage
        {...stageProps({
          draft: "newer draft remains",
          pendingContent: "pending exact content",
          rejectedDraft: {
            content: "rejected exact content",
            message: "这条发言需要在同步会话状态后重试。",
            restoreLabel: "用被拒发言替换当前草稿",
          },
          onRestoreRejectedDraft,
        })}
      />,
    );

    expect(screen.getByTestId("human-pending-content").textContent).toBe(
      "pending exact content",
    );
    expect(screen.getByTestId("rejected-human-content").textContent).toBe(
      "rejected exact content",
    );
    expect(screen.getByLabelText("发言草稿")).toHaveValue(
      "newer draft remains",
    );
    fireEvent.click(
      screen.getByRole("button", { name: "用被拒发言替换当前草稿" }),
    );
    expect(onRestoreRejectedDraft).toHaveBeenCalledOnce();
    expect(screen.getByLabelText("发言草稿")).toHaveValue(
      "newer draft remains",
    );
  });

  it("renders exactly the highest-priority notice", () => {
    const fatal = "会话暂时无法加载，请稍后重试。";
    const rejected = {
      content: "rejected",
      message: "这条发言需要在同步会话状态后重试。",
      restoreLabel: "恢复被拒发言到草稿",
    };
    const interrupted = [
      { key: GRANT_ID, message: "这次 AI 发言未完成，讨论将继续。" },
    ];
    const { rerender } = render(
      <DiscussionStage
        {...stageProps({
          errorMessage: fatal,
          connection: "reconnecting",
          connectionLabel: "正在同步最新讨论记录…",
          rejectedDraft: rejected,
          pendingContent: "pending",
          interruptedAiNotices: interrupted,
          aiWaitingLabel: "AI 候选人 1 正在准备发言…",
        })}
      />,
    );
    const notice = () => screen.getByTestId("discussion-notice");
    expect(notice()).toHaveTextContent(fatal);

    rerender(
      <DiscussionStage
        {...stageProps({
          connection: "reconnecting",
          connectionLabel: "正在同步最新讨论记录…",
          rejectedDraft: rejected,
          pendingContent: "pending",
          interruptedAiNotices: interrupted,
          aiWaitingLabel: "AI 候选人 1 正在准备发言…",
        })}
      />,
    );
    expect(notice()).toHaveTextContent("正在同步最新讨论记录…");

    rerender(
      <DiscussionStage
        {...stageProps({
          rejectedDraft: rejected,
          pendingContent: "pending",
          interruptedAiNotices: interrupted,
          aiWaitingLabel: "AI 候选人 1 正在准备发言…",
        })}
      />,
    );
    expect(notice()).toHaveTextContent(rejected.message);

    rerender(
      <DiscussionStage
        {...stageProps({
          pendingContent: "pending",
          interruptedAiNotices: interrupted,
          aiWaitingLabel: "AI 候选人 1 正在准备发言…",
        })}
      />,
    );
    expect(notice()).toHaveTextContent("正在确认上一条发言");

    rerender(
      <DiscussionStage
        {...stageProps({
          interruptedAiNotices: interrupted,
          aiWaitingLabel: "AI 候选人 1 正在准备发言…",
        })}
      />,
    );
    expect(notice()).toHaveTextContent(interrupted[0].message);

    rerender(
      <DiscussionStage
        {...stageProps({ aiWaitingLabel: "AI 候选人 1 正在准备发言…" })}
      />,
    );
    expect(notice()).toHaveTextContent("AI 候选人 1 正在准备发言…");
  });

  it("keeps confirmed history but removes terminal submission and fake modules", () => {
    const { container } = render(
      <DiscussionStage
        {...stageProps({ status: "COMPLETED", showComposer: false })}
      />,
    );
    expect(screen.getByTestId("confirmed-transcript")).toBeInTheDocument();
    expect(screen.queryByLabelText("发言草稿")).toBeNull();
    expect(screen.queryByRole("button", { name: "发送发言" })).toBeNull();
    expect(container.textContent).not.toMatch(/报告|投票|结论|共识率|评分/);
  });
});
