"use client";

import { useRef, useState, type KeyboardEvent } from "react";

import type { QuestionDetail, QuestionSummary } from "@/lib/api/client";

import {
  isSupportedQuestionType,
  QUESTION_TYPES,
  questionBackgroundLabel,
  questionDifficultyLabel,
  questionTypeLabel,
  type SupportedQuestionType,
} from "./question-presentation";

export type TrainingEntrySurface = "lobby" | "setup";

export type SelectedQuestionDetailState =
  | { kind: "idle" }
  | { kind: "loading"; questionId: string }
  | { kind: "available"; questionId: string; question: QuestionDetail }
  | { kind: "unavailable"; questionId: string };

export type TrainingEntryProps = {
  surface: TrainingEntrySurface;
  questions: readonly QuestionSummary[] | undefined;
  selectedQuestionId: string;
  selectedQuestion: SelectedQuestionDetailState;
  creating: boolean;
  errorMessage?: string | null;
  onBeginSelection: () => void;
  onSelectQuestion: (questionId: string) => void;
  onCreateSession: () => void;
};

function questionMetadata(question: QuestionSummary) {
  return [
    `${questionDifficultyLabel(question.difficulty)}难度`,
    questionBackgroundLabel(question.background_domain),
    question.estimated_minutes > 0
      ? `约 ${question.estimated_minutes} 分钟`
      : undefined,
    `版本 ${question.version_number}`,
  ].filter((value): value is string => Boolean(value));
}

function Lobby({
  onBeginSelection,
}: Pick<TrainingEntryProps, "onBeginSelection">) {
  return (
    <div className="training-lobby-grid">
      <article className="training-lobby-primary">
        <div className="training-lobby-primary-copy">
          <p className="training-entry-kicker">NEXT SIMULATION</p>
          <h2>下一场完整模拟</h2>
          <p>
            选定一道真实训练题，与 AI
            候选人完成一场有目标、有约束、有复盘的文字群面。
          </p>
          <button onClick={onBeginSelection} type="button">
            开始选题
            <span aria-hidden="true">→</span>
          </button>
        </div>
        <div aria-label="本次训练包含" className="training-lobby-facts">
          <p>
            <strong>3 位 AI 候选人</strong>
            <span>共同参与完整讨论</span>
          </p>
          <p>
            <strong>文字无领导小组讨论</strong>
            <span>专注表达与协作过程</span>
          </p>
          <p>
            <strong>基于真实发言证据的复盘</strong>
            <span>训练结束后查看</span>
          </p>
        </div>
      </article>

      <aside className="training-lobby-flow">
        <div>
          <p className="training-entry-kicker">TRAINING FLOW</p>
          <h3>一次完整的群面练习</h3>
        </div>
        <ol>
          <li>
            <span>01</span>
            <div>
              <strong>阅读题目</strong>
              <p>明确目标与硬性约束</p>
            </div>
          </li>
          <li>
            <span>02</span>
            <div>
              <strong>参与讨论</strong>
              <p>表达、质疑、协作与收敛</p>
            </div>
          </li>
          <li>
            <span>03</span>
            <div>
              <strong>证据复盘</strong>
              <p>回看真实公开发言依据</p>
            </div>
          </li>
        </ol>
      </aside>

      <article className="training-lobby-guide">
        <p className="training-entry-kicker">HOW IT WORKS</p>
        <h3>从选择开始，沿真实会话向前</h3>
        <p>题目与版本在创建会话时绑定，讨论过程不会替换为演示数据。</p>
        <div aria-hidden="true" className="training-lobby-route">
          <span>选题</span>
          <i />
          <span>讨论</span>
          <i />
          <span>复盘</span>
        </div>
      </article>
    </div>
  );
}

function SelectedQuestionSummary({
  creating,
  questions,
  selectedQuestion,
  selectedQuestionId,
  onCreateSession,
}: Pick<
  TrainingEntryProps,
  | "creating"
  | "questions"
  | "selectedQuestion"
  | "selectedQuestionId"
  | "onCreateSession"
>) {
  const summary = questions?.find((item) => item.id === selectedQuestionId);

  return (
    <aside className="training-selection-summary">
      <div>
        <p className="training-entry-kicker">YOUR SELECTION</p>
        <h3>已选题目</h3>
      </div>

      {!summary ? (
        <div className="training-selection-empty">
          <span aria-hidden="true">↖</span>
          <strong>从左侧选择一道题</strong>
          <p>选择后可在这里确认讨论目标与硬性约束。</p>
        </div>
      ) : (
        <div className="training-selection-content">
          <div>
            <span className="training-selection-type">
              {questionTypeLabel(summary.question_type)}
            </span>
            <h4>{summary.title}</h4>
            <p className="training-question-metadata">
              {questionMetadata(summary).join(" · ")}
            </p>
          </div>

          {selectedQuestion.kind === "loading" ? (
            <p aria-live="polite" className="training-selection-state">
              正在加载所选题目…
            </p>
          ) : selectedQuestion.kind === "unavailable" ? (
            <p aria-live="polite" className="training-selection-state">
              所选题目详情暂时无法加载
            </p>
          ) : selectedQuestion.kind === "available" ? (
            <div className="training-selection-detail">
              <section>
                <h5>讨论目标</h5>
                <p>{selectedQuestion.question.objective}</p>
              </section>
              {selectedQuestion.question.hard_constraints.length > 0 ? (
                <section>
                  <h5>硬性约束</h5>
                  <ul>
                    {selectedQuestion.question.hard_constraints.map(
                      (constraint) => (
                        <li key={constraint.key}>{constraint.text}</li>
                      ),
                    )}
                  </ul>
                </section>
              ) : null}
            </div>
          ) : null}
        </div>
      )}

      <div className="training-selection-action">
        <button
          disabled={creating || !selectedQuestionId}
          onClick={() => onCreateSession()}
          type="button"
        >
          {creating ? "正在创建…" : "创建文字会话"}
        </button>
        <p>会话将绑定当前所选题目版本</p>
      </div>
    </aside>
  );
}

function Setup(props: TrainingEntryProps) {
  const firstQuestionType = props.questions?.find((question) =>
    isSupportedQuestionType(question.question_type),
  )?.question_type;
  const [activeType, setActiveType] = useState<SupportedQuestionType>(() =>
    firstQuestionType && isSupportedQuestionType(firstQuestionType)
      ? firstQuestionType
      : "ORDERING_SELECTION",
  );
  const tabRefs = useRef<Array<HTMLButtonElement | null>>([]);

  const questions = props.questions?.filter(
    (question) => question.question_type === activeType,
  );

  function handleTabKeyDown(
    event: KeyboardEvent<HTMLButtonElement>,
    index: number,
  ) {
    let nextIndex: number | undefined;
    if (event.key === "ArrowRight")
      nextIndex = (index + 1) % QUESTION_TYPES.length;
    if (event.key === "ArrowLeft") {
      nextIndex = (index - 1 + QUESTION_TYPES.length) % QUESTION_TYPES.length;
    }
    if (event.key === "Home") nextIndex = 0;
    if (event.key === "End") nextIndex = QUESTION_TYPES.length - 1;
    if (nextIndex === undefined) return;
    event.preventDefault();
    const nextType = QUESTION_TYPES[nextIndex];
    if (!nextType) return;
    setActiveType(nextType);
    tabRefs.current[nextIndex]?.focus();
  }

  return (
    <div className="training-setup">
      <header className="training-setup-header">
        <div>
          <p className="training-entry-kicker">QUESTION LIBRARY</p>
          <h2>选择本次训练题目</h2>
        </div>
        <p>按题型浏览真实已发布题目，选择后确认目标与约束。</p>
      </header>

      <div className="training-setup-layout" data-layout="8-4">
        <section className="training-question-browser">
          <div
            aria-label="题目类型"
            className="training-type-tabs"
            role="tablist"
          >
            {QUESTION_TYPES.map((type, index) => {
              const count =
                props.questions?.filter(
                  (question) => question.question_type === type,
                ).length ?? 0;
              const selected = type === activeType;
              return (
                <button
                  aria-label={`${questionTypeLabel(type)} ${count} 道`}
                  aria-controls={`question-panel-${type}`}
                  aria-selected={selected}
                  id={`question-tab-${type}`}
                  key={type}
                  onClick={() => setActiveType(type)}
                  onKeyDown={(event) => handleTabKeyDown(event, index)}
                  ref={(node) => {
                    tabRefs.current[index] = node;
                  }}
                  role="tab"
                  tabIndex={selected ? 0 : -1}
                  type="button"
                >
                  <span>{questionTypeLabel(type)}</span>
                  <strong>{count} 道</strong>
                </button>
              );
            })}
          </div>

          <div
            aria-labelledby={`question-tab-${activeType}`}
            className="training-question-panel"
            id={`question-panel-${activeType}`}
            role="tabpanel"
          >
            {props.questions === undefined ? (
              <p aria-live="polite" className="training-question-state">
                正在加载训练题目…
              </p>
            ) : questions?.length ? (
              <div className="training-question-grid">
                {questions.map((question) => {
                  const selected = question.id === props.selectedQuestionId;
                  return (
                    <label
                      className="training-question-card"
                      data-focus-treatment="focus-visible"
                      data-selected={selected ? "true" : "false"}
                      key={question.id}
                    >
                      <input
                        aria-label={question.title}
                        checked={selected}
                        name="training-question"
                        onChange={() => props.onSelectQuestion(question.id)}
                        onKeyDown={(event) => {
                          if (event.key !== " " && event.key !== "Spacebar")
                            return;
                          event.preventDefault();
                          props.onSelectQuestion(question.id);
                        }}
                        type="radio"
                        value={question.id}
                      />
                      <span className="training-question-card-topline">
                        <span>
                          {questionDifficultyLabel(question.difficulty)}难度
                        </span>
                        <strong aria-hidden={!selected}>
                          {selected ? (
                            <>
                              <span aria-hidden="true">✓ </span>
                              <span>已选择</span>
                            </>
                          ) : (
                            "选择"
                          )}
                        </strong>
                      </span>
                      <span className="training-question-title">
                        {question.title}
                      </span>
                      <span className="training-question-metadata">
                        <span>
                          {questionBackgroundLabel(question.background_domain)}
                        </span>
                        <span>约 {question.estimated_minutes} 分钟</span>
                        <span>版本 {question.version_number}</span>
                      </span>
                    </label>
                  );
                })}
              </div>
            ) : (
              <p className="training-question-state">当前分类暂无可用题目。</p>
            )}
          </div>
        </section>

        <SelectedQuestionSummary {...props} />
      </div>
    </div>
  );
}

export default function TrainingEntry(props: TrainingEntryProps) {
  return (
    <section
      className="training-entry"
      data-scroll-owner="training-entry"
      data-surface={props.surface}
      data-testid="training-entry"
    >
      <div className="training-entry-inner">
        {props.surface === "lobby" ? (
          <Lobby onBeginSelection={props.onBeginSelection} />
        ) : (
          <Setup {...props} />
        )}
        {props.errorMessage ? (
          <p aria-live="polite" className="training-entry-error">
            {props.errorMessage}
          </p>
        ) : null}
      </div>
    </section>
  );
}
