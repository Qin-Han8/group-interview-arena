# AI 候选人与讨论编排骨架

- Status: P1-2 completed; P1-3 state-machine design frozen; orchestrator/AI runtime deferred
- Current phase: P1 — IN_PROGRESS
- Target version: V0.1 Internal Validation
- Detailed orchestrator/agent design: P1-3A state/timing boundary completed docs-only; P1-3B awaiting explicit approval
- Authority: 低于 [`PROJECT_MASTER_PLAN.md`](PROJECT_MASTER_PLAN.md) 和已确认的 [`DECISIONS.md`](DECISIONS.md)

## 文档目的

本文件记录已确认的 AI 候选人/私有立场基础和 P1-3A 已冻结的讨论状态机边界；发言权调度、结构化记忆和 AI runtime 仍待后续任务。当前不包含 production Prompt、模型选择、可执行算法或代码。

## Confirmed by PROJECT_MASTER_PLAN

### 基础角色库

总纲定义了八种基础角色方向：

- 强势控场者：主动定框架和推动决策，但可被证据说服且不应永远正确；
- 逻辑分析者：重视标准、证据和概念清晰度；
- 创意发散者：提出新方案，但需要他人帮助筛选和收敛；
- 细节纠缠者：可能拖慢进度，也可能发现关键风险；
- 温和协调者：整合观点、降低冲突和邀请参与；
- 沉默跟随者：发言欲望低，用于观察用户是否促进团队参与；
- 固执反对者：需要高质量论证才让步，不能退化成无理由抬杠；
- 摇摆决策者：能看到多方优点，可被清晰标准和总结说服。

### 参数化角色原则

角色差异不能只依赖文风。参数需要影响发言主动性、打断倾向、平均发言长度、立场稳定性、说服阈值、新观点倾向、总结倾向、时间意识、细节关注、合作度、错误率和跑题率等行为概率。

参数只控制概率和策略；具体发言仍受题目、讨论阶段、私有信息和上下文约束。

### 私有立场

同一人格模板在不同题目中必须获得不同立场。私有信息可以包含初始偏好、关注指标、可接受让步、独有信息、不可接受底线及对小组角色的偏好。

角色不得读取其他角色私有信息，不得知道评分规则，不得主动帮助用户刷高分。改变立场必须存在可解释原因。

### 状态机与阶段目标

总纲级主流程为：

```text
CREATED
  -> DEVICE_CHECK
  -> PREPARATION
  -> OPENING_STATEMENTS
  -> EXPLORATION
  -> CONFLICT_AND_EVALUATION
  -> CONVERGENCE
  -> FINAL_SUMMARY
  -> COMPLETED
  -> REPORT_GENERATING
  -> REPORTED
```

异常状态包括 `PAUSED_NETWORK`、`PAUSED_SYSTEM`、`ABORTED_USER`、`FAILED_SERVICE` 和 `COMPLETED_PARTIAL`。

阶段目标：

- PREPARATION：用户阅读，角色在后台形成初始立场，不产生可见讨论；
- OPENING_STATEMENTS：限时陈述并收集初始差异；
- EXPLORATION：产生方案、标准和信息；
- CONFLICT_AND_EVALUATION：比较核心分歧并防止无限循环；
- CONVERGENCE：减少新方案，提高时间提醒、总结、投票和折中权重；
- FINAL_SUMMARY：完成总结后不重新开启大规模讨论。

### 发言权计算原则

调度考虑发言意愿、与上一观点的相关性、角色主动性、阶段适配、独有信息、被点名、沉默补偿，以及最近发言、超时和重复惩罚。用户发言具有较高优先级，但参与质量仍进入报告评估。

### 三层记忆

1. 原始逐句记录：用于回放和报告；
2. 结构化讨论记忆：观点、标准、共识、分歧、淘汰选项、当前结论和剩余时间；
3. 短上下文摘要：供单次模型调用使用。

不得每轮把全部原始文本传给所有模型。

## 当前版本范围

- V0.1 每场固定 3 名 AI 候选人；
- V0.1 四种基础 Persona Template 已确认为：逻辑分析者、创意发散者、温和协调者、强势控场者；
- 使用文字输入输出验证准备、陈述、讨论和总结闭环；
- 目标是验证角色差异、状态机、调度和记忆，而不是语音或视觉拟真。

## P1-2A frozen persona boundary

### Persona Template is stable behavior, not a stance

Persona Template 只拥有跨题稳定的行为参数和展示 metadata：initiative、interrupt tendency、average turn seconds、stance stability、persuasion threshold、novel idea rate、summary tendency、time awareness、detail focus、cooperation、support-user bias、error rate、off-topic rate 和 speech style。

它不得拥有具体题目的答案、初始偏好、支持的 option、隐藏事实、让步条件或底线。同一 Persona Template 在不同 Question Version 中可以获得完全不同的 Private Stance；强势控场者不能永久绑定某一种观点。

P1-2B numeric write boundary 使用 strict finite Decimal/integer validation：概率 `[0,1]`、support-user bias `[-1,1]`、average turn seconds `[10,90]`，且 Decimal 最多三位小数；bool、NaN、infinity、越界和过精度值在 domain write boundary 拒绝。PostgreSQL 以 `NUMERIC(4,3)` 加 range checks 保存 canonical values；直接 SQL 的过精度输入按 PostgreSQL 语义 canonicalize，不另造 trigger/custom type。参数使用显式 columns，不保存为 generic JSON parameter blob。

Seeded/assigned V0.1 templates 的行为参数不原地改写。需要重新校准时创建 successor template identity；retirement 只阻止未来 assignment，不能删除历史 version 引用。

### Version-specific Assignment and Private Stance

QuestionPersonaAssignment 属于一个 immutable Question Version，并引用一个 Persona Template。V0.1 发布校验要求三个不同 Persona、连续 slots `1..3`，但数据库不把“3”做成永久封闭 constraint。

Private Stance 是 assignment 的 required one-to-one child，显式表达：

- initial position；
- weighted priority dimensions；
- concession conditions；
- optional private information；
- red lines；
- optional preferred group role。

Assignment 和 Private Stance 与发布后的 Question Version 一起不可覆盖修改。修订 stance 必须发布新 Question Version，不能修改历史 session 使用的版本。

### Private isolation and future AI caller

- Private Stance、Persona parameters、assignments、reference dimensions、hidden conflicts、acceptable outcome patterns 和 phase prompts 不进入普通 REST/OpenAPI/Browser/WebSocket/session snapshot/log/trace/error。
- P1-2B 只建立 server-side domain/persistence types，不创建 public schema、provider、prompt runtime 或 unused AI interface。
- P1-2C session create 只验证 version assignment completeness，并返回 safe `question_version_id`/public question projection；participant 尚未存在，因此不向 Browser 下发 Persona Template label/parameters。
- 未来获批 orchestrator/AI caller 只能按 session-bound `question_version_id` + its own assignment 加载单一 Persona behavior 和本席 Private Stance；不得把其他席位 stance 注入候选人上下文，也不得交给 browser/provider logs。
- 以上只是 future caller contract。LLMProvider 必须等真实 LLM caller 获批出现后再建立。

### V0.1 seed identities

- `LOGIC_ANALYST` — 逻辑分析者；
- `CREATIVE_DIVERGER` — 创意发散者；
- `GENTLE_COORDINATOR` — 温和协调者；
- `ASSERTIVE_FACILITATOR` — 强势控场者。

P1-2B seed 已为每个 code 显式提供完整参数；重复执行 exact-match no-op，已有 code drift 在单一事务内 fail，不静默 overwrite。Persona Template 不含题目观点；internal-validation bundle 的三席 Private Stance 只保存在 assignment-specific server-side persistence 中。

## P1-1 foundation boundary — backend and Web caller implemented

P1-1A 冻结、P1-1B～D 已实现讨论会话的 persistence/backend transport 与最小 Web caller foundation；仍不实现本文件的角色行为、发言权调度、结构化记忆或完整状态机：

- 最小 session 从 `CREATED` 开始；唯一 scoped WS business command `session.abort` 只验证总纲已有异常状态 `ABORTED_USER`、durable idempotency 和 ordered event path；
- 创建 formal event 为 `session.created`；abort formal event 为 `session.state_changed`；该集合不是未来完整 discussion event vocabulary；
- FastAPI/domain service 是 session state authority，Browser 只消费 REST snapshot `last_sequence` 和后续 ordered events；
- P1-1 不创建 question、participant、utterance、AI persona、orchestrator、memory 或 LLM/provider；不会用 event JSON 假装这些 canonical objects；
- `session.abort` 不要求 question/participant/utterance，因此可在不提前决定其 Schema 的前提下建立真实 vertical slice；
- P1-1B persistence/migration foundation、P1-1C deterministic domain command service/REST/WebSocket 与 P1-1D authoritative Web projection/reconnect caller 已完成；`session.abort` 之外的状态机、讨论行为、角色与 AI 仍未实现。完整计划见 [`exec-plans/P1-1_discussion-session-foundation.md`](exec-plans/P1-1_discussion-session-foundation.md)。

## P1-3A frozen state-machine boundary

V0.1 current implemented path is frozen as:

```text
CREATED
  -> PREPARATION
  -> OPENING_STATEMENTS
  -> EXPLORATION
  -> CONFLICT_AND_EVALUATION
  -> CONVERGENCE
  -> FINAL_SUMMARY
  -> COMPLETED
```

`session.start` 是唯一开始 intent；phase deadline 是唯一自动前进 trigger；Browser 没有 `advance`/`finish`/`set_state` 或 next-state input。`session.abort` 可从 `CREATED` 和任一 active timed phase 进入 `ABORTED_USER`。禁止跳阶段、倒退和从 `COMPLETED` / `ABORTED_USER` 返回 active discussion。

`DEVICE_CHECK`、`PAUSED_NETWORK`、`PAUSED_SYSTEM`、`FAILED_SERVICE`、`COMPLETED_PARTIAL`、`REPORT_GENERATING`、`REPORTED` 保留总纲长期语义但在 P1-3 Deferred。未来 report lifecycle 只能从 discussion completion 单向扩展，不能 reopen discussion。

每个 session 在 start 时由 server-owned typed configuration 冻结六个 active phases 的 duration plan；current `phase_started_at` / `phase_deadline_at` 持久化并使用 server UTC。Recovered phase start anchored to the previous deadline，so reload、reconnect、restart 或 callback delay 不增加额外时间。Browser countdown only displays the deadline and never owns expiry。

Concurrent user/system transitions share the P1-1 aggregate row lock、durable action replay、monotonic sequence、single transaction and commit-before-send boundary。System timeout uses exact expected status/deadline and null action causation；before a user command is applied, overdue phases are reconciled in order。This makes duplicate timers、stale starts and timeout/abort races resolve to one ordered durable outcome。

Formal event vocabulary remains `session.created` and `session.state_changed`。Historical abort event v1 remains readable；P1-3 state/timing transitions use generalized v2 payload。Full matrix、timing arithmetic、snapshot and P1-3B～D gates are in [`exec-plans/P1-3_session-state-machine.md`](exec-plans/P1-3_session-state-machine.md)。This design does not implement P1-4 floor scheduling or AI behavior。

## Implementation guidance

- 大模型负责自然语言和受约束的局部语义决策；项目代码负责状态、时间、发言权、私有信息隔离、记忆和恢复。
- 关键模型输出未来应采用结构化 Schema 验证，但具体 Schema 尚未决定。
- 角色决策与发言生成建议分离，以提高可控性和成本可观测性。
- 发言默认保持简短、回应上下文并避免重复；具体阈值需要后续验证。

## TBD

- TBD：标准模式 AI 发言人数和总时长（总纲第 37 节）；
- TBD：具体 LLM 供应商（总纲第 37 节）；
- TBD：P1-2B initial numeric seed 经过真实讨论后的校准方法和 blind-test threshold；
- Confirmed for P1-3：V0.1 状态转换条件、abort 来源、deadline concurrency/recovery 语义；
- TBD：P1-4 调度公式和冲突循环阈值；
- TBD：结构化记忆和模型输出的正式 Schema；
- TBD：角色盲测样本及通过标准的执行细节。

除特别注明的总纲问题外，其余是派生 TBD，不是新的 D-xxx。

## Future work

- P1：`IN_PROGRESS`；P1-1 session foundation 与 P1-2 question/persona foundation 均为 `DONE`；P1-3A state/timing design freeze 已完成 docs-only，P1-3 `IN_PROGRESS`，P1-3B not started / awaiting explicit approval；state-machine runtime、P1-4 调度、记忆和 AI runtime 仍未开始并需后续批准。
- P2：加入语音、打断、播放停止和恢复语义。
- P3：建立角色行为与评分证据之间的校准边界。
- P6/V1.0：扩展到 6～8 种角色和压力模式。

## 与其他文档关系

- 题目和私有信息来源：[`QUESTION_SYSTEM.md`](QUESTION_SYSTEM.md)
- 评分边界：[`SCORING_RUBRIC.md`](SCORING_RUBRIC.md)
- 未来服务边界：[`ARCHITECTURE.md`](ARCHITECTURE.md)
- 未来事件契约：[`API.md`](API.md)
- 隐私和 Prompt 注入：[`PRIVACY_AND_SAFETY.md`](PRIVACY_AND_SAFETY.md)
