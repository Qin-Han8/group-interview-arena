# AI 候选人与讨论编排骨架

- Status: P1-2/P1-3/P1-4 completed; P1-5A frozen; P1-5B persistence implemented; provider execution deferred
- Current phase: P1 — IN_PROGRESS
- Target version: V0.1 Internal Validation
- Detailed orchestrator/agent design: P1-3A～D and P1-4A～E completed; P1-5A freeze completed; P1-5B persistence commands implemented without runtime/provider execution
- Authority: 低于 [`PROJECT_MASTER_PLAN.md`](PROJECT_MASTER_PLAN.md) 和已确认的 [`DECISIONS.md`](DECISIONS.md)

## 文档目的

本文件记录已确认的 AI 候选人/私有立场基础、P1-3 已实现的讨论状态机、P1-4 floor-control、P1-5A authority freeze，以及 P1-5B provider-neutral persistence boundary。当前仍不包含 production Prompt orchestration、模型调用、自动发言生成或结构化记忆。

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

## P1-3 state-machine boundary and P1-3C realtime/Web flow

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

Formal event vocabulary remains `session.created` and `session.state_changed`。Historical abort event v1 remains readable；P1-3B emits generalized v2 payload for start、abort and phase-deadline transitions。P1-3C adds startup/connected recovery and Browser authoritative phase projection without adding a client-side state machine。Full matrix、timing arithmetic、snapshot and P1-3D gates are in [`exec-plans/P1-3_session-state-machine.md`](exec-plans/P1-3_session-state-machine.md)。This foundation does not implement P1-4 floor scheduling or AI behavior。

## P1-4A～D floor foundation, deterministic scheduler and safe Web projection

### Phase controls lifecycle; floor controls turns

- P1-3 is the sole authority for session phase/status/deadline. Floor control reads that context and assigns a turn only inside a floor-enabled phase；it never starts、advances、pauses、extends、completes or aborts the phase.
- `CREATED`、`PREPARATION` and terminal states have no active floor. V0.1 floor-enabled phases are `OPENING_STATEMENTS` through `FINAL_SUMMARY`.
- Each session has zero or one current floor owner. A phase change invalidates old opportunity/candidate calculations and releases an old grant, but floor cleanup cannot delay or veto the phase transition.

### Generalized participant and floor language

- Participant is session-scoped and supports actor kind `AI`、`HUMAN`、`SYSTEM`; role distinguishes ordinary `CANDIDATE` from `MODERATOR`. The model must not be an AI-agent-only list.
- Current floor owner is a participant holding one stable grant identity for one session phase.
- Speaking opportunity is a normalized request/obligation to be considered, not a grant and not speech content.
- Candidate speaker is an ephemeral eligible-participant view with safe policy facts；it is not persisted as canonical state.
- Scheduler decision is the deterministic cause: grant, request intervention or no grant. Intervention is a typed moderator/system control request caused by silence/no candidate/deadline pressure；it is not generated speech.

### Deterministic V0.1 scheduling

Scheduler inputs are restricted to authoritative phase context、participant availability、open opportunities、durable floor history、derived fairness state and closed configured policy/injected UTC. Persona parameters、Private Stance、hidden question calibration、prompt、provider output/model score and Browser rank are excluded.

The selection policy is closed lexicographic ordering:

1. filter by availability、role and phase eligibility；
2. apply closed opportunity-class order；
3. prefer participants without a current-phase grant；
4. prevent consecutive/per-phase monopoly while another eligible unmet opportunity exists；
5. apply phase-mandated order or discussion-phase fewest-grants/longest-wait order；
6. break remaining ties by stable participant slot, then UUID；
7. request an explainable moderator/system intervention on configured silence or deadline pressure, while P1-3 phase expiry remains authoritative。

No ML/semantic ranking, random tie-break or multi-agent negotiation is used. The same validated input and policy version must return the same result.

### Who speaks versus what is said

Scheduler only answers **who should speak**. Future LLM/provider may answer **what an already-granted AI says**. LLM output cannot choose a speaker, change state/floor, rewrite policy or serve as post-hoc decision justification. Human participant speech has no LLM dependency.

### Facts, explanation and privacy

- Minimum future formal facts are `floor.granted`、`floor.released` and `floor.intervention_requested`.
- Event is the fact；scheduler decision is the cause；future LLM output/utterance is later content.
- Each decision retains policy version、safe reason code、phase、timestamp、selected participant/opportunity and safe fairness/tie-break facts sufficient to answer why that participant received floor.
- Public explanation is allowlisted from safe reason metadata. Private Stance、red lines、hidden information、persona numeric calibration、prompt/provider internals and scoring cannot enter decision explanation、events、Browser、logs or errors.
- Durable facts include participant/availability lifecycle、accepted opportunities、single current grant、decision audit and floor history. Candidate lists、derived fairness counters、timers and rejected ranking alternatives are runtime-only.
- Future scoring may consume observable floor timing/distribution/interruption facts, but P1-4 neither scores users nor treats scheduler reason as evidence of ability.

### P1-4B/C implemented behavior boundary

- Session creation materializes a generalized roster: authenticated human owner plus three AI candidates bound to immutable Persona Assignments. Storage also supports a future `SYSTEM` / `MODERATOR`, but moderators are ineligible for ordinary candidate floor grants.
- Internal typed grant/release/intervention commands validate the frozen phase、sequence、participant role/availability、current grant and decision target before writing. They reuse durable session action identity/digest and aggregate row locking；duplicate retry replays the original result while stale or conflicting input makes no mutation.
- P1-4C reconstructs open opportunities and fairness from durable P1-4B facts, then applies the frozen closed lexicographic policy with explicit sorting and injected UTC. It never uses random、wall-clock tie-break、unordered enumeration、semantic/ML rank or process-global mutable state.
- The internal scheduler command is evaluated under the existing session aggregate row lock and shares one transaction with decision + grant/intervention mutation. Exact phase、sequence and current-grant preconditions make concurrent or stale evaluation fail closed；duplicate action identity replays the original fact.
- A safe decision record contains only closed policy/reason/phase/target/opportunity and allowlisted observable fairness/tie-break metadata. Private Stance、persona calibration、prompt/provider state、hidden ranking weights and scoring data are neither inputs nor persisted explanation.
- A phase deadline or abort remains controlled by P1-3. If a grant exists, the same locked transaction records `floor.released` before `session.state_changed`; floor cleanup never changes or blocks phase semantics.
- P1-4D exposes only participant safe identity、current grant and latest allowlisted lifecycle fact through the owner-only snapshot. The existing ordered WS channel projects the same three floor facts；Web uses exact sequence/gap/reconnect/stale-generation recovery and only displays current owner、lifecycle and safe reason.
- Browser sends no floor command and never decides grant/release/scheduler state. Public projection omits decision metadata、ranking/weights、Private Stance/persona calibration、prompt/provider and scoring data；utterance/content remains a later separately approved concern.

Full D～E scope、recovery boundary、validation and stop conditions are in [`exec-plans/P1-4_floor-control.md`](exec-plans/P1-4_floor-control.md)。P1-4D and P1-4E are completed；final independent verdict is `PASS`。

## P1-5A AI Participant and Runtime boundary

### Participant is identity; Runtime is capability

- AI Participant 是 session-scoped 群面身份，拥有 participant/seat、Persona Assignment、自己的 Private Stance 和 floor history。
- AI Runtime 是生成能力：在 exact `floor.granted` 下加载最小授权上下文、解析 Prompt Version/model configuration、调用 provider、验证输出并提交 generation result。
- Runtime 不是 participant，不拥有 seat、stance、phase、deadline、floor 或 next-speaker authority。Human Participant 不依赖 LLM Runtime。
- Persona Template 只保存稳定行为参数和展示 metadata；不得直接保存 prompt content/version、provider/model binding、API key 或其他 provider secret。
- 每次调用只能加载获准 participant 自己的 Persona behavior/Assignment/Private Stance；其他席位 Private Stance 不进入 prompt/provider/log/error。

### Who versus what

```text
floor.granted
  -> AI Runtime generation request
  -> provider-neutral LLM call
  -> validated final Utterance
  -> deterministic floor release
```

Scheduler 决定 **who speaks**；AI Runtime 决定 **what the already-granted AI says**。LLM/provider 不得选择下一位 speaker、覆盖 scheduler decision、改变 phase/deadline、修改 scoring 或绕过 domain service 写数据库。

### Prompt and model provenance

Prompt 是可追踪版本资产。Generation Request 必须固定 exact Question Version、Persona Template/Assignment/Private Stance、Prompt Version，以及实际 provider/model/effective non-secret configuration。历史 final utterance 必须从自己的 request 解释这些来源，不能依赖 mutable latest pointer。

现有 Question Version `phase_prompts` 只是题目级内部素材，不等于完整 Prompt Version。Persona Template 也不承担 prompt storage。Rendered prompt、chain-of-thought、provider raw body 和 secret 应最小化，不因审计要求默认完整保存。

### Generation Request and Utterance lifecycle

- `requested`：exact participant/grant/provenance 下的 generation intent 已建立；
- `generated`：provider-neutral output 已返回并通过 future validation，但尚未成为正式历史内容；
- `persisted`：final Utterance 已关联 request/participant/grant/phase/provenance 持久化；
- `failed`：没有 final utterance，只有 safe typed failure/audit identity。

Generation Request 与 final Utterance 是不同 identity。一个 logical request 至多产生一个 final utterance；retry 复用 logical identity 或显式 attempt child，不能重复制造正式内容。Partial output 默认不是小组已听到的事实。

### Failure/retry integrity

- Timeout、provider unavailable、rate limit、partial/invalid output 和 stale grant 使用 typed、有界、幂等处理；provider internal retry 不能绕过 application identity。
- 每次提交前重新验证 exact session/phase/participant/current grant；late result 在 grant/phase 变化后丢弃。
- Failure 不改变 phase、deadline、floor owner、scheduler decision 或 scoring。Project-owned control path 负责 exact-once-safe floor release/intervention，provider 不拥有 release policy。
- Crash/restart 后未来实现必须从 durable request/grant truth 判断 retry/fail/no-op，不能仅靠 process memory。

完整冻结与 Deferred 实现见 [`exec-plans/P1-5_ai-runtime-foundation.md`](exec-plans/P1-5_ai-runtime-foundation.md)。

### P1-5B persistence semantics

- Durable request states are `REQUESTED -> RUNNING -> COMPLETED` or `REQUESTED/RUNNING -> FAILED`。The P1-5A logical generated/persisted boundary is represented atomically at this foundation: only validated future caller output submitted through `complete_generation_request` becomes a `COMPLETED` request plus formal `ai_utterance` in one transaction；partial output is not stored as utterance。
- Request creation fixes exact participant、floor grant、Prompt Version、provider/model identifiers and a closed non-secret configuration version。The existing session and participant links recover Question Version and Persona Assignment history without copying Private Stance or prompt variables into request metadata。
- No automatic generation exists。Future provider/orchestrator code must explicitly call these commands, respect the current grant check, and use the existing floor service for release；failure alone never changes floor or session lifecycle。

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
- Confirmed and implemented through P1-4D：V0.1 deterministic lexicographic floor policy、single-owner/participant/event/explanation/persistence boundary、pure ranking、locked transactional orchestration and display-only authoritative Web recovery；
- TBD after real discussion evidence：policy parameter calibration values and conflict-loop content semantics；P1-4 does not use semantic conflict ranking；
- Implemented persistence in P1-5B：Prompt Version、Generation Request lifecycle and final AI Utterance relation；transport schema、provider attempt/fallback orchestration and runtime caller remain TBD/Deferred；
- TBD：结构化记忆和模型输出 validation 的正式 Schema；
- TBD：角色盲测样本及通过标准的执行细节。

除特别注明的总纲问题外，其余是派生 TBD，不是新的 D-xxx。

## Future work

- P1：`IN_PROGRESS`；P1-1～P1-4 `DONE`；P1-5A freeze `DONE`；P1-5B persistence implemented；LLM/provider execution、automatic runtime、transport and memory remain Deferred。
- P2：加入语音、打断、播放停止和恢复语义。
- P3：建立角色行为与评分证据之间的校准边界。
- P6/V1.0：扩展到 6～8 种角色和压力模式。

## 与其他文档关系

- 题目和私有信息来源：[`QUESTION_SYSTEM.md`](QUESTION_SYSTEM.md)
- 评分边界：[`SCORING_RUBRIC.md`](SCORING_RUBRIC.md)
- 未来服务边界：[`ARCHITECTURE.md`](ARCHITECTURE.md)
- 未来事件契约：[`API.md`](API.md)
- 隐私和 Prompt 注入：[`PRIVACY_AND_SAFETY.md`](PRIVACY_AND_SAFETY.md)
