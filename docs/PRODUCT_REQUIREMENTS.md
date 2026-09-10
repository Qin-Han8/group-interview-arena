# 产品需求文档骨架

- Status: Baseline + P1-3 session-flow + P1-7A basic evidence report/content design freeze
- Current phase: P1 — IN_PROGRESS
- Target version: V0.1 Internal Validation
- Detailed design: P1-3A session state/timing flow and P1-7A basic evidence report/V0.1 content boundaries frozen; broader PRD remains incremental
- Authority: 低于 [`PROJECT_MASTER_PLAN.md`](PROJECT_MASTER_PLAN.md) 和已确认的 [`DECISIONS.md`](DECISIONS.md)

## 文档目的

本文件用于在具体产品任务获批后承载详细 PRD，包括用户故事、流程、交互、边界和验收标准。当前只整理总纲确认的产品基线，不表示详细需求已经完成。

## Confirmed by PROJECT_MASTER_PLAN

- 产品是动态群面能力训练平台，不是题库、答案生成器或普通聊天机器人。
- 首要用户是校招及初入职场求职者。
- 用户与 3 名 AI 候选人完成受控讨论；角色需要体现真实行为差异。
- 完整模拟以桌面 Web 为主；首期不开发原生 App。
- 公开 MVP 必须支持语音；内部 V0.1 可以先用文字验证。
- 评分面向可观察行为，重要评价必须有证据且只用于训练。
- 报告应突出最大优势、最大问题和下一步训练。
- 产品不提供录取概率、岗位适配结论或正式面试实时提词。
- 首期不采集视频，不做表情、微表情或眼神评分。

## 当前版本范围

V0.1 的目标是验证多角色讨论和状态机，不公开收费。

包含：

- 桌面 Web；
- 文字输入输出；
- 3 种题型、12 道人工审核题；
- 每场 3 名 AI 候选人、共 4 种基础角色模板；
- 准备、陈述、讨论、总结流程；
- 基础逐句记录；
- 简版证据报告；
- 管理端最小题目配置。

不包含：

- 支付；
- ASR/TTS；
- 完整成长系统；
- 压力事件；
- 行业题包。

当前 P1-1～P1-6 已完成，P1-6 `DONE / CLOSED`。P1-7 现为 `IN_PROGRESS`；P1-7A 为 `DONE / DESIGN_SCOPE_FROZEN / ACTUAL_SOURCE_REVIEW_PASS`；P1-7B 为 `DONE / ACTUAL_SOURCE_REVIEW_PASS`，`P1-7B-F001 CLOSED`，open findings `NONE`；P1-7C～E/P1-8 尚未开始。

## P1-3A confirmed session-flow boundary

- V0.1 text flow uses `CREATED -> PREPARATION -> OPENING_STATEMENTS -> EXPLORATION -> CONFLICT_AND_EVALUATION -> CONVERGENCE -> FINAL_SUMMARY -> COMPLETED`；device check remains a later voice concern。
- User can start a created session or abort a created/active session；the user cannot skip、reverse or choose a destination phase。
- Active phase duration is configurable by the server and frozen per session；reload、reconnect or server restart does not reset the authoritative deadline。
- Browser displays server-authoritative phase/timing/sequence and a display-only countdown；it does not own the state machine。
- Long-term pause、service-failure、partial-completion and report lifecycle states remain Deferred；P1-3 does not invent placeholder user flows for them。
- P1-4 floor scheduling、AI/participant/utterance、memory、report/scoring and voice remain separate future work。

## P1-7A confirmed basic-report and content boundary

- Formal V0.1 report eligibility is exactly an authoritative `SimulationSession.status == COMPLETED`. `COMPLETED` stays the discussion lifecycle endpoint; report status belongs to an independent durable resource.
- User flow after completion is stable report generation/read → report Web experience. A report is not generated on each GET and does not receive a new activity WebSocket lifecycle.
- The report presents completion/question/deterministic participation/covered-phase facts, a concise summary, up to 3 evidence-backed strengths, up to 3 evidence-backed improvement opportunities, exactly 1 next-session priority and verifiable evidence cards.
- Evidence cards expose source participant, authoritative phase, source utterance identity, source event sequence, exact quote, interpretation and confidence. Text V0.1 does not claim audio timestamps.
- The report evaluates observable behavior using public discussion facts. It does not show six 0–100 scores, an overall score, radar, percentile/rank, hiring probability, job fit or personality type; the score-versus-level TBD remains open.
- V0.1 content closure is exactly 4 ordering-selection, 4 resource-allocation and 4 plan-design human-reviewed immutable Question Versions, plus the existing 4 basic Persona Templates. Current committed seed is 0/1/0 questions, so P1-7D later owns 11 additional reviewed questions; P1-7A authors none.
- P1-7B owns persistence, P1-7C owns validated extraction/generation, P1-7D owns REST/Web/content closure and P1-7E owns P1-7 composition/independent acceptance. P1-8 remains separate full-P1 acceptance.

## Implementation guidance

- 需求应按“完整动态训练闭环”组织，而不是按页面数量组织。
- 每项功能必须说明其所属阶段、目标版本、非目标和验收证据。
- 新手模式可给非内容型阶段提示，但不能生成用户下一句或刷分话术。
- 完整模拟与移动端短训练应分别定义体验承诺。
- 建议一次只向用户强调最重要的三项反馈，避免报告堆叠。

以上是总纲指导原则，不等于具体页面和交互已经冻结。

## TBD

### 总纲第 37 节原始待验证问题

1. TBD：首次免费体验是 5 分钟还是完整新手场；
2. TBD：首期付费价格；
3. TBD：公开 MVP 的中文 ASR、TTS 和 LLM 供应商；
4. TBD：原始音频是否默认完全不保存；
5. TBD：标准模式的 AI 发言人数和总时长；
6. TBD：是否允许用户上传自定义题目；
7. TBD：报告展示分数还是等级加证据；
8. TBD：何时加入真人多人房；
9. TBD：国内正式公开运营还是先做小范围邀请测试；
10. TBD：人工评分校准支持从何处获得。

### 派生 TBD

- TBD：V0.1 四种基础角色具体组合；
- TBD：V0.1 各流程的详细交互和异常流程；
- TBD：最小题目管理端的具体功能边界。

派生 TBD 不是总纲原始 D-xxx 决策。

## Future work

- P1：P1-1～P1-6 are complete；P1-7A has frozen the basic evidence report and V0.1 content architecture；P1-7B persistence awaits external review；P1-7C～E/P1-8 remain pending.
- P2：细化语音交互、打断、降级和音频生命周期。
- P3：细化报告和专项训练体验。
- P4：细化商品、权益、支付和故障补偿。
- P5/P6：依据测试结果细化公开发布和 V1.0 能力。

## 与其他文档关系

- 产品最高层定义：[`PROJECT_MASTER_PLAN.md`](PROJECT_MASTER_PLAN.md)
- 正式决策：[`DECISIONS.md`](DECISIONS.md)
- 当前版本与阶段：[`ROADMAP.md`](ROADMAP.md)
- 当前获批任务：[`TASKS.md`](TASKS.md)
- 角色、评分、隐私等细节分别由对应领域文档承载。
