"use client";

import type { KeyboardEvent, ReactNode, RefObject } from "react";

import type { SessionSnapshot } from "@/lib/api/client";
import type {
  HumanDraftInspection,
  RealtimeConnectionState,
} from "@/lib/realtime/client";

import type { ConfirmedUtterance } from "./discussion-transcript";
import { participantLabel, phaseLabel } from "./session-presentation";

export type RejectedDraftPresentation = {
  content: string;
  message: string;
  restoreLabel: string;
};

export type DiscussionNotice = {
  key: string;
  message: string;
};

export type DiscussionStageProps = {
  status: SessionSnapshot["status"];
  participants: SessionSnapshot["floor"]["participants"];
  currentGrant: SessionSnapshot["floor"]["current_grant"];
  confirmedTranscript: readonly ConfirmedUtterance[];
  transcriptContainerRef: RefObject<HTMLDivElement | null>;
  hasNewTranscriptBelow: boolean;
  onTranscriptScroll: () => void;
  onReturnToLatest: () => void;
  draft: string;
  draftInspection: HumanDraftInspection;
  canSend: boolean;
  sendDisabledReason: string;
  onDraftChange: (value: string) => void;
  onSubmit: () => void;
  pendingContent: string | null;
  rejectedDraft: RejectedDraftPresentation | null;
  onRestoreRejectedDraft: () => void;
  connection: RealtimeConnectionState;
  connectionLabel: string;
  errorMessage: string | null;
  aiWaitingLabel: string | null;
  interruptedAiNotices: readonly DiscussionNotice[];
  showComposer: boolean;
};

type StageParticipant = SessionSnapshot["floor"]["participants"][number];

function safeParticipantLabel(
  participants: SessionSnapshot["floor"]["participants"],
  participant: StageParticipant,
) {
  return participant.actor_kind === "HUMAN"
    ? "你"
    : participantLabel(participants, participant.participant_id);
}

function participantStatus(
  participant: StageParticipant,
  currentGrant: SessionSnapshot["floor"]["current_grant"],
  aiWaitingLabel: string | null,
) {
  if (participant.participant_id !== currentGrant?.participant_id) {
    return "等待中";
  }
  if (participant.actor_kind === "HUMAN") return "轮到你发言";
  return aiWaitingLabel ? "正在准备发言" : "当前发言";
}

function Transcript({
  participants,
  items,
  containerRef,
  hasNewTranscriptBelow,
  onTranscriptScroll,
  onReturnToLatest,
}: {
  participants: SessionSnapshot["floor"]["participants"];
  items: readonly ConfirmedUtterance[];
  containerRef: RefObject<HTMLDivElement | null>;
  hasNewTranscriptBelow: boolean;
  onTranscriptScroll: () => void;
  onReturnToLatest: () => void;
}) {
  return (
    <section
      aria-labelledby="confirmed-transcript-heading"
      className="relative flex min-h-0 flex-1 flex-col"
      data-testid="confirmed-transcript"
    >
      <h2 className="text-sm font-semibold" id="confirmed-transcript-heading">
        讨论记录
      </h2>
      <div
        className="mt-3 min-h-0 flex-1 overflow-y-auto pr-1"
        data-testid="confirmed-transcript-list"
        onScroll={onTranscriptScroll}
        ref={containerRef}
      >
        {items.length === 0 ? (
          <p className="rounded-lg bg-neutral-50 p-4 text-sm text-neutral-600">
            服务端确认的发言会显示在这里。
          </p>
        ) : (
          <ol aria-label="已确认讨论记录" className="space-y-3">
            {items.map((item) => (
              <li
                className="border-b border-neutral-200 pb-4 last:border-b-0"
                key={item.utterance_id}
              >
                <div className="flex flex-wrap items-baseline justify-between gap-2">
                  <p className="text-sm font-semibold text-neutral-900">
                    {item.actor_kind === "HUMAN"
                      ? "你"
                      : participantLabel(participants, item.participant_id)}
                  </p>
                  <p className="text-xs text-neutral-500">
                    {phaseLabel(item.phase)}
                  </p>
                </div>
                <p
                  className="mt-2 whitespace-pre-wrap text-sm leading-6 text-neutral-800"
                  data-testid={`utterance-content-${item.utterance_id}`}
                >
                  {item.content}
                </p>
              </li>
            ))}
          </ol>
        )}
      </div>
      {hasNewTranscriptBelow ? (
        <button
          className="absolute bottom-3 left-1/2 -translate-x-1/2 rounded-full border border-neutral-300 bg-white px-3 py-1.5 text-sm font-medium text-neutral-800 shadow-sm"
          onClick={onReturnToLatest}
          type="button"
        >
          回到最新发言
        </button>
      ) : null}
    </section>
  );
}

function Composer({
  draft,
  draftInspection,
  canSend,
  sendDisabledReason,
  onDraftChange,
  onSubmit,
  pendingContent,
  rejectedDraft,
  onRestoreRejectedDraft,
}: Pick<
  DiscussionStageProps,
  | "draft"
  | "draftInspection"
  | "canSend"
  | "sendDisabledReason"
  | "onDraftChange"
  | "onSubmit"
  | "pendingContent"
  | "rejectedDraft"
  | "onRestoreRejectedDraft"
>) {
  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && (event.ctrlKey || event.metaKey) && canSend) {
      event.preventDefault();
      onSubmit();
    }
  }

  return (
    <section
      aria-labelledby="human-composer-heading"
      className="shrink-0 border-t border-neutral-200 bg-white pt-4"
      data-testid="human-composer"
    >
      <h2 className="text-sm font-semibold" id="human-composer-heading">
        你的发言
      </h2>
      <label
        className="mt-3 grid gap-1 text-sm"
        htmlFor="human-discussion-draft"
      >
        发言草稿
        <textarea
          aria-describedby="human-draft-count send-disabled-reason"
          className="min-h-24 resize-y rounded-lg border border-neutral-300 bg-white p-3 leading-6"
          id="human-discussion-draft"
          onChange={(event) => onDraftChange(event.target.value)}
          onKeyDown={handleKeyDown}
          value={draft}
        />
      </label>
      <div className="mt-2 flex items-start justify-between gap-3">
        <div>
          <p className="text-xs text-neutral-600" id="human-draft-count">
            {draftInspection.codePointCount} / 4000
          </p>
          <p
            className="mt-1 text-xs text-neutral-600"
            data-testid="send-disabled-reason"
            id="send-disabled-reason"
          >
            {sendDisabledReason}
          </p>
        </div>
        <button
          className="rounded-md border border-neutral-900 bg-neutral-900 px-4 py-2 text-sm font-medium text-white disabled:cursor-not-allowed disabled:opacity-50"
          disabled={!canSend}
          onClick={onSubmit}
          type="button"
        >
          发送发言
        </button>
      </div>

      {pendingContent ? (
        <aside
          className="mt-3 rounded-lg border border-blue-200 bg-blue-50 p-3 text-sm"
          data-testid="human-pending"
        >
          <p>待服务器确认（尚未进入讨论记录）</p>
          <p
            className="mt-1 whitespace-pre-wrap"
            data-testid="human-pending-content"
          >
            {pendingContent}
          </p>
        </aside>
      ) : null}

      {rejectedDraft ? (
        <aside
          className="mt-3 rounded-lg border border-amber-300 bg-amber-50 p-3 text-sm"
          data-testid="rejected-human-draft"
        >
          <p>{rejectedDraft.message}</p>
          <p
            className="mt-2 whitespace-pre-wrap"
            data-testid="rejected-human-content"
          >
            {rejectedDraft.content}
          </p>
          <button
            className="mt-2 rounded-md border border-amber-700 px-3 py-1 font-medium"
            onClick={onRestoreRejectedDraft}
            type="button"
          >
            {rejectedDraft.restoreLabel}
          </button>
        </aside>
      ) : null}
    </section>
  );
}

function primaryNotice({
  connection,
  connectionLabel,
  errorMessage,
  rejectedDraft,
  pendingContent,
  interruptedAiNotices,
  aiWaitingLabel,
}: Pick<
  DiscussionStageProps,
  | "connection"
  | "connectionLabel"
  | "errorMessage"
  | "rejectedDraft"
  | "pendingContent"
  | "interruptedAiNotices"
  | "aiWaitingLabel"
>): { message: string; tone: "fatal" | "information" | "recoverable" } | null {
  if (errorMessage) return { message: errorMessage, tone: "fatal" };
  if (connection !== "connected") {
    return { message: connectionLabel, tone: "information" };
  }
  if (rejectedDraft) {
    return { message: rejectedDraft.message, tone: "recoverable" };
  }
  if (pendingContent) {
    return { message: "正在确认上一条发言", tone: "information" };
  }
  if (interruptedAiNotices[0]) {
    return { message: interruptedAiNotices[0].message, tone: "information" };
  }
  if (aiWaitingLabel) {
    return { message: aiWaitingLabel, tone: "information" };
  }
  return null;
}

export default function DiscussionStage({
  status,
  participants,
  currentGrant,
  confirmedTranscript,
  transcriptContainerRef,
  draft,
  hasNewTranscriptBelow,
  onTranscriptScroll,
  onReturnToLatest,
  draftInspection,
  canSend,
  sendDisabledReason,
  onDraftChange,
  onSubmit,
  pendingContent,
  rejectedDraft,
  onRestoreRejectedDraft,
  connection,
  connectionLabel,
  errorMessage,
  aiWaitingLabel,
  interruptedAiNotices,
  showComposer,
}: DiscussionStageProps): ReactNode {
  const candidates = participants
    .filter(
      (participant) =>
        participant.actor_kind === "HUMAN" || participant.actor_kind === "AI",
    )
    .toSorted((left, right) => left.seat_order - right.seat_order);
  const notice = primaryNotice({
    connection,
    connectionLabel,
    errorMessage,
    rejectedDraft,
    pendingContent,
    interruptedAiNotices,
    aiWaitingLabel,
  });
  const terminalCopy =
    status === "COMPLETED"
      ? "讨论已完成"
      : status === "ABORTED_USER"
        ? "训练已结束"
        : null;

  return (
    <div className="flex h-full min-h-0 flex-col gap-4 p-4 sm:p-5">
      <ol
        aria-label="会话参与者"
        className="grid shrink-0 grid-cols-2 gap-2 sm:grid-cols-4"
        data-testid="participant-strip"
      >
        {candidates.map((participant) => {
          const current =
            participant.participant_id === currentGrant?.participant_id;
          return (
            <li
              className={`rounded-lg border px-3 py-2 text-sm ${
                current
                  ? "border-indigo-500 bg-indigo-50 text-indigo-950"
                  : "border-neutral-200 bg-neutral-50 text-neutral-700"
              }`}
              data-participant-state={current ? "current" : "neutral"}
              key={participant.participant_id}
            >
              <p className="font-medium">
                {safeParticipantLabel(participants, participant)}
              </p>
              <p className="mt-1 text-xs">
                {participantStatus(participant, currentGrant, aiWaitingLabel)}
              </p>
            </li>
          );
        })}
      </ol>

      {terminalCopy ? (
        <p className="shrink-0 rounded-lg bg-neutral-100 px-3 py-2 text-sm font-medium">
          {terminalCopy}
        </p>
      ) : null}

      {notice ? (
        <p
          aria-live="polite"
          className={`shrink-0 rounded-lg border px-3 py-2 text-sm ${
            notice.tone === "fatal"
              ? "border-red-300 bg-red-50 text-red-800"
              : notice.tone === "recoverable"
                ? "border-amber-300 bg-amber-50 text-amber-900"
                : "border-blue-200 bg-blue-50 text-blue-900"
          }`}
          data-testid="discussion-notice"
        >
          {notice.message}
        </p>
      ) : null}

      <Transcript
        containerRef={transcriptContainerRef}
        items={confirmedTranscript}
        hasNewTranscriptBelow={hasNewTranscriptBelow}
        onReturnToLatest={onReturnToLatest}
        onTranscriptScroll={onTranscriptScroll}
        participants={participants}
      />

      {showComposer ? (
        <Composer
          canSend={canSend}
          draft={draft}
          draftInspection={draftInspection}
          onDraftChange={onDraftChange}
          onRestoreRejectedDraft={onRestoreRejectedDraft}
          onSubmit={onSubmit}
          pendingContent={pendingContent}
          rejectedDraft={rejectedDraft}
          sendDisabledReason={sendDisabledReason}
        />
      ) : null}
    </div>
  );
}
