# P1-5 AI Runtime Foundation Execution Plan

Status: `P1 IN_PROGRESS`; `P1-5 IN_PROGRESS / POST_CLOSEOUT_REMEDIATION_OPEN`; P1-5A～P1-5F retain historical `DONE`; `P1-5F-3 DONE`; `P1-5F-3A DONE`; `P1-5F-3B DONE` with its recorded evidence；`P1-5F-4 DONE`; `P1-5R IN_PROGRESS / DESIGN_FROZEN`; R1/R2-A/R2-B/R3 `NOT_STARTED`; implementation plan `NOT_STARTED`

Target version: `V0.1 Internal Validation`

Product baseline: [`PROJECT_MASTER_PLAN.md`](../PROJECT_MASTER_PLAN.md)

Accepted decisions: [`D-003`](../DECISIONS.md#2-已确认产品决策索引), [`D-007`](../DECISIONS.md#2-已确认产品决策索引), [`D-008`](../DECISIONS.md#2-已确认产品决策索引), [`D-013`](../DECISIONS.md#2-已确认产品决策索引), [`ADR-006`](../DECISIONS.md#adr-006--rest-与-websocket-通信边界), [`ADR-007`](../DECISIONS.md#adr-007--api-契约生成策略), [`ADR-009`](../DECISIONS.md#adr-009--独立后台任务队列延后), [`ADR-011`](../DECISIONS.md#adr-011--轻量领域导向混合模块架构), [`ADR-012`](../DECISIONS.md#adr-012--分阶段测试与质量工具策略), [`ADR-013`](../DECISIONS.md#adr-013--配置错误与结构化日志基线), [`ADR-014`](../DECISIONS.md#adr-014--provider-neutral-ai-与自定义讨论编排)

P1-5A baseline: clean committed `main` at `5397cd2b25f36c6a9fbd666b759261091c36a8c0`, equal to `origin/main`; [`PROJECT_MASTER_PLAN.md`](../PROJECT_MASTER_PLAN.md) SHA-256 `2388A9660320406CB35D5354126AD71C6849A98DB7C4A356796CA951BF372F26`

P1-5D design-freeze baseline: clean committed `main` at `371d5a57ffb952a7ccb664170819e07b606b5688`, equal to `origin/main`; P1-5C is committed；[`PROJECT_MASTER_PLAN.md`](../PROJECT_MASTER_PLAN.md) SHA-256 remains `2388A9660320406CB35D5354126AD71C6849A98DB7C4A356796CA951BF372F26`

P1-5E-1 design-freeze baseline: clean committed `main` at `a416d955920ec407c011c32602ac720a6d8080fd`, equal to `origin/main`; P1-5D is committed and `DONE`；P1-5E was `NOT_STARTED` before this approved checkpoint；[`PROJECT_MASTER_PLAN.md`](../PROJECT_MASTER_PLAN.md) SHA-256 remains `2388A9660320406CB35D5354126AD71C6849A98DB7C4A356796CA951BF372F26`

P1-5E-3 implementation baseline: clean committed `main` at `de6ffdc5f98b2ec4549037f7fa3f96eeb83c7d31`, equal to `origin/main`; P1-5E-1/P1-5E-2 are committed and `DONE`；[`PROJECT_MASTER_PLAN.md`](../PROJECT_MASTER_PLAN.md) SHA-256 remains `2388A9660320406CB35D5354126AD71C6849A98DB7C4A356796CA951BF372F26`

P1-5F-1 design-freeze baseline: clean committed `main` at `fa4e8b0123d55044c9c621068311db06524b93c6`, equal to `origin/main`; P1-5E is committed and `DONE`；P1-5F was `NOT_STARTED` before this approved checkpoint；[`PROJECT_MASTER_PLAN.md`](../PROJECT_MASTER_PLAN.md) SHA-256 remains `2388a9660320406cb35d5354126ad71c6849a98db7c4a356796ca951bf372f26`

P1-5F-3B design-freeze baseline: clean committed `main` at `7421532db29b8e7c64a1dcce150803803ce21126`, equal to `origin/main`; P1-5F-3A is committed and `DONE`；[`PROJECT_MASTER_PLAN.md`](../PROJECT_MASTER_PLAN.md) SHA-256 remains `2388a9660320406cb35d5354126ad71c6849a98db7c4a356796ca951bf372f26`

P1-5F-3B design actual-source review: `PASS`; findings `NONE`; reviewed bundle `group-interview-arena-review-20260826-190658.zip`; SHA-256 `5867365d06fa6e0f1eb6d8f9dc5ec9dd9d806ed0ec444a909ef8266346ceba42`; implementation later completed under separate approval

P1-5F-3B implementation-planning baseline: clean committed `main` at `ab089974e21a2d01ae2865beb15864c50883ee24`, equal to `origin/main`; GitHub Actions run `32968355532` completed `SUCCESS` for that exact head；the initial implementation-plan actual-source review was `BLOCKED` by exactly `F3B-IP-001/F3B-IP-002`；finding-only remediation marks both `CLOSED`；remediated implementation-plan self-review `PASS`；open findings `NONE`

P1-5F-3B implementation closeout: committed implementation baseline `5efe1346532b95b7fabdd521015fd9f8199a457f`; actual-source implementation review `PASS`; findings `NONE`; GitHub Actions run `33044682226` `SUCCESS`; commit/push complete; later F4 network-free composition acceptance `PASS`; F3B is `DONE`

P1-5F-4 final closeout: initial acceptance `BLOCKED` on `F4-ACC-001`; finding-only remediation added network-free Human→AI Browser composition proof while preserving the real scheduler/runtime/persistence/public-event/WS/recovery path; remediation actual-source review `PASS`; `F4-ACC-001 CLOSED`; accepted final commit `af33d89baa0355ae1ee5174a2ef8cfb5e7b14554`; GitHub Actions run `33050532295` `SUCCESS`; fresh independent final acceptance `PASS`; findings `NONE`; no real provider/model call

P1-5R design-freeze baseline: clean committed `main` at `91671fe1afc19a9dcc4341184c23500852f96780`, equal to `origin/main`; GitHub Actions run `33054731104` `completed / success` for that exact head；[`PROJECT_MASTER_PLAN.md`](../PROJECT_MASTER_PLAN.md) SHA-256 remains `2388a9660320406cb35d5354126ad71c6849a98db7c4a356796ca951bf372f26`

P1-5F-3B Batch 3 baseline: clean committed `main` at `ee2701e9e66baec16c6095e706770f5490f3df67`, equal to `origin/main`; GitHub Actions run `33035085603` completed `SUCCESS`；implementation and final local gates subsequently completed。The later actual-source implementation review passed with findings `NONE`; accepted implementation baseline `5efe1346532b95b7fabdd521015fd9f8199a457f` and GitHub Actions run `33044682226` `SUCCESS`; F4 composition acceptance passed; F3B is `DONE`

## Goal

冻结 AI Runtime Foundation 的架构边界，使未来实现能够在既有 `floor.granted` 之后为获准 AI participant 生成可追踪、可重试且不破坏 session integrity 的 utterance，同时保持 P1-3 lifecycle authority、P1-4 floor authority、题目/Persona 私有信息隔离和 provider neutrality。

P1-5A 是 docs-only architecture freeze。它不实现 LLM、provider adapter、prompt runtime、utterance persistence、API/Realtime contract、schema、migration、dependency、test 或 CI。

P1-5B 是 separately approved persistence foundation。它只实现 immutable Prompt Version、provider-neutral Generation Request lifecycle、successful final AI Utterance relation and locked transactional domain services；不接入真实 provider、不自动生成、不增加 API/Realtime/Web。

P1-5C 是 separately approved deterministic runtime vertical slice。它在不调用真实 LLM、不增加 schema/API/Realtime/Web/dependency 的前提下，实现 exact Prompt Version rendering、single-participant authorized context assembly、typed immutable generation input/result、deterministic local harness 和 application orchestration，并复用 P1-5B lifecycle 原子提交唯一 final AI Utterance。

后续拆分固定为：

- `P1-5A — AI Runtime Architecture Freeze`：`DONE`；
- `P1-5B — AI Runtime Persistence Foundation`：`DONE`；
- `P1-5C — Runtime Contract & Deterministic Generation Vertical Slice`：`DONE`；
- `P1-5D — First Real Provider Integration`：`DONE`；implementation and config-driven model patch actual-source reviews `PASS`，final user-run sanitized real-provider acceptance smoke `PASS`；
- `P1-5E — Automatic AI Runtime Orchestration`：`DONE`；
  - `P1-5E-1 — Automatic AI Runtime Orchestration Design Freeze`：`DONE`；docs-only actual-source review `PASS`；findings none；
  - `P1-5E-2 — Single AI Turn Orchestration Kernel`：`DONE`；initial actual-source review `BLOCKED` on 3 findings；all remediated；remediation actual-source re-review `PASS`，findings none；
  - `P1-5E-3 — Continuous AI Drive + Composition Acceptance`：`DONE`；implementation actual-source review `PASS`，findings none；sanitized real-provider composition smoke `PASS`；
- `P1-5F — Realtime/Web Integration + Independent Acceptance`：`DONE`；
- `P1-5F-1 — Realtime/Public Contract Design Freeze`：`DONE`；docs-only；finding-only external re-review `PASS` with findings none；
  - `P1-5F-2 — Backend Text Discussion Transport`：`DONE`；initial implementation actual-source review `BLOCKED` on three findings；all remediated；finding-only external re-review `PASS`，findings none；
  - `P1-5F-3 — Web Discussion Experience`：`DONE`；
    - `P1-5F-3A — Web Discussion Functional Closure`：`DONE` with `DESIGN_FROZEN / IMPLEMENTATION_COMPLETE / ACTUAL_SOURCE_REVIEW_PASS / COMMIT_PUSH_COMPLETE / CI_PASS / INDEPENDENT_FINAL_ACCEPTANCE_PASS / FINDINGS_NONE_OPEN`；
    - `P1-5F-3B — Complete Discussion Page Composition`：`DONE` with `DESIGN_FROZEN / IMPLEMENTATION_PLAN_FROZEN / IMPLEMENTATION_COMPLETE / ACTUAL_SOURCE_IMPLEMENTATION_REVIEW_PASS / COMMIT_PUSH_COMPLETE / CI_PASS / F4_COMPOSITION_ACCEPTANCE_PASS / FINDINGS_NONE_OPEN`；accepted implementation baseline `5efe1346532b95b7fabdd521015fd9f8199a457f`；CI `33044682226` `SUCCESS`；
  - `P1-5F-4 — Composition E2E + Independent Acceptance`：`DONE`；initial acceptance `BLOCKED` on `F4-ACC-001`；remediation actual-source review `PASS`；accepted commit `af33d89baa0355ae1ee5174a2ef8cfb5e7b14554`；CI `33050532295` `SUCCESS`；independent final acceptance `PASS`；findings `NONE`；`F4-ACC-001 CLOSED`；network-free fake-provider path only。

P1-5D design freeze、implementation and config-driven model patch were separately approved；both actual-source reviews and its final user-run sanitized real-provider acceptance smoke passed，so P1-5D is `DONE`。P1-5E-1、P1-5E-2 and P1-5E-3 are also `DONE` after their required reviews，closing P1-5E as `DONE`。P1-5F-1/P1-5F-2/P1-5F-3A remain historical `DONE` with their recorded evidence。F3B implementation review、commit/push、CI and F4 composition acceptance passed with no findings open；F4 later closed `F4-ACC-001` after review、accepted commit/CI and independent acceptance。Those historical statuses remain unchanged。Later local acceptance opened P1-5R only，so parent P1-5 is currently `IN_PROGRESS / POST_CLOSEOUT_REMEDIATION_OPEN` while P1 remains `IN_PROGRESS`。

## Context and authority

- P1-2 已提供 immutable Question Version、stable-behavior Persona Template、version-specific Assignment / Private Stance。Persona Template 不保存 prompt 或 provider secret。
- P1-3 是 session phase/status/deadline 的唯一 authority。
- P1-4 是 within-phase speaker/floor 的唯一 authority，且已持久化 `floor.granted` / `floor.released` facts。
- `ADR-014` 要求 provider-neutral AI、自定义确定性编排和真实 caller 出现后才创建 provider abstraction。
- 总纲要求历史报告和模型调用可追溯，但不得保存不必要的完整敏感输入。

## Frozen authority boundary

### Floor Scheduler decides who; AI Runtime decides what

- Floor Scheduler 只决定 **WHO speaks**，并产生 authoritative `floor.granted` fact。
- AI Runtime 只为当前 grant 指向的 AI participant 决定 **WHAT to say**。
- AI Runtime 不拥有 session state transition、phase、deadline、timer、floor grant/release policy 或 next-speaker authority。
- LLM/provider output 不能选择下一位 speaker、修改 scheduler decision、改变 scoring、直接写数据库，或绕过 domain/application service。
- Human participant speech 不依赖 AI Runtime；SYSTEM/moderator content 需要未来单独获批的 caller，不因本冻结自动进入范围。

冻结调用链：

```text
floor.granted
  -> AI Runtime generation request
  -> LLM Provider
  -> generated candidate output
  -> persisted final Utterance
  -> deterministic Floor release
```

`floor.granted` 是生成前置条件，不是 prompt；Utterance 是内容事实，不是 floor grant；Floor release 是 project-owned control operation，不由 provider 自行决定。

### Runtime write boundary

- AI Runtime 通过获批的 application/domain service 读取最小上下文并提交 generation result。
- Provider adapter 只执行外部模型 I/O，返回 validated provider-neutral result/error；SDK object、provider response object 和 credential 不穿透 domain layer。
- 未来 persistence mutation 必须复用 session aggregate lock、current grant identity、phase/grant stale checks、single transaction、ordered event 和 commit-before-send 原则。
- Provider failure 不能写 session phase/deadline、替换 current floor owner或制造第二个 utterance。

## Frozen provider abstraction

- 业务代码只依赖 project-owned provider-independent request/result/error contract，不直接 import 或暴露 OpenAI SDK、Anthropic SDK 或单一模型 API types。
- Provider capability 目标支持 hosted provider、enterprise provider 和 local model；这只是 portability boundary，不代表本轮实现 routing/fallback。
- Provider selection、model name 和 effective configuration 是 server-owned invocation input；credential 只存在于 server-side secret configuration。
- Provider failure 被归一化为 typed timeout、unavailable、rate-limit、partial/invalid-output 等结果；provider exception/message/body 不成为 public error 或 domain state。
- Provider failure 不影响 session integrity。是否重试、何时放弃以及如何 release floor 由 project-owned runtime policy 决定。
- 按 `ADR-014`，具体 interface、adapter、factory 和 `providers/` 目录等到首个获批真实 LLM caller 时才创建；P1-5A 不预建空 abstraction。

## Frozen prompt/version traceability boundary

Prompt 是可追踪、不可静默覆盖的版本资产，不是 Persona Template 字段、散落业务字符串或 provider-specific request body。

每次 generation request 必须解析并固定以下 effective inputs：

```text
Question Version
+ Persona Template/Version identity
+ Question-version-specific Assignment / Private Stance identity
+ Prompt Version
+ Model configuration snapshot/version
= explainable generation provenance
```

- Prompt Version 代表实际模板/指令资产版本；修改 prompt 必须产生新 version identity，历史 invocation 不重绑定到 latest。
- Model configuration 至少可解释 provider、model identifier、受控 generation parameters 和适用的 configuration version/snapshot；secret 不进入 provenance。
- 历史 final utterance 必须可追溯到其 generation request，并回答使用了什么 prompt version、provider/model 和 effective non-secret configuration。
- 允许 privacy-safe hash/reference 证明输入资产，不要求保存不必要的完整 rendered prompt、chain-of-thought、provider raw body 或 credential。
- Question Version 内现有 `phase_prompts` 是题目级内部编排素材，不等于完整 Prompt Version，也不能替代 invocation provenance。

## Frozen participant/runtime distinction

- **AI Participant** 是 session-scoped 群面角色身份：participant、seat、Persona Assignment、Private Stance 和 floor history。
- **AI Runtime** 是生成能力：组装最小授权上下文、解析 Prompt Version/model configuration、调用 provider、验证输出并提交 generation result。
- 一个 Participant 可以跨多次 grant 发起多次 generation request；Runtime 本身不是 participant，不拥有 seat、stance、floor 或 session lifecycle。
- Persona Template 只保存稳定行为参数与展示 metadata；不得直接保存 rendered prompt、Prompt Version content、provider/model binding、API key 或其他 provider secret。
- Runtime 每次只能读取获准 participant 自己的 Persona behavior 与 Private Stance；不得把其他席位 Private Stance 注入调用或日志。

## Frozen utterance lifecycle

AI 输出不是普通 message，也不是 provider response 的直接镜像。逻辑生命周期为：

```text
requested -> generated -> persisted
     |           |
     +----------> failed
```

- `requested`：在 exact active floor grant 下创建 generation intent/identity，并固定 provenance 与幂等边界。
- `generated`：provider-neutral output 已返回并通过结构/安全/长度等 future validation，但尚未成为 durable user-visible utterance。
- `persisted`：final utterance 已由 application service 原子持久化并关联 exact request、participant、grant、phase 和 provenance；只有此状态可作为正式历史内容。
- `failed`：request 在没有 final utterance 的情况下终止，保留 safe typed reason 和审计 identity；它不是 session failure state。

Generation Request 与 final Utterance 必须分离：一个 request 至多产生一个 final utterance；retry 复用同一 logical request/idempotency boundary 或建立显式 attempt child，不能生成多个正式 utterances。`generated` 的 partial/raw candidate 在未持久化前不是小组已听到的事实。

P1-5A 只冻结 lifecycle/invariants。P1-5B 现将 generation attempt 的 durable states 具体化为 `REQUESTED / RUNNING / COMPLETED / FAILED`：`RUNNING` 表示 caller 已开始 attempt；`COMPLETED` 只与同一 transaction 中唯一 formal utterance 一起成立。Conceptual `generated -> persisted` 不作为可崩溃分离的数据库状态，避免 raw/partial output 在正式 utterance 前成为 durable group fact。At the P1-5B checkpoint event vocabulary、streaming chunks and Browser projection were Deferred；F1 now freezes the formal event docs-only while streaming and implementation remain Deferred。

## P1-5B implemented persistence foundation

- `prompt_versions` stores immutable UUID/version identity、stable key/purpose、template text + SHA-256 digest and creation/publication/retirement metadata。Publication is insert-or-exact-replay；Persona Template schema remains unchanged。
- `llm_generation_requests` records exact session、AI participant、floor grant、Prompt Version、actual provider/model identifiers、closed non-secret configuration version、semantic digest、lifecycle timing and safe typed failure code。One row is one attempt；same request ID exact replay is idempotent and semantic drift is a conflict。
- `ai_utterances` stores only final displayable content。It has at-most-one relations to generation request and floor grant；a composite deferred foreign key includes request status `COMPLETED`, preventing a formal utterance without a matching successful generation context。
- Create/start/complete/fail mutations reuse the owner-scoped `simulation_sessions` row lock and short transaction discipline。Create/start/complete validate current session phase、exact grant and eligible AI participant；complete updates request and inserts utterance atomically。Failure writes only terminal request metadata and never mutates phase/deadline/current floor/events。
- Provenance is recoverable through immutable links: session → Question Version；participant → Persona Assignment/Template/Private Stance；request → Prompt Version + provider/model + configuration version；utterance → successful request。No private stance content、persona calibration、hidden ranking、internal prompt variables、provider secret/raw error is copied into request or utterance storage。

## P1-5C approved runtime slice

### Goals and current callers

- Current caller is a deterministic local runtime harness used to prove runtime correctness；it performs no network or model SDK I/O。
- Runtime resolves the exact session-bound Question Version、exact current AI floor grant、that participant's exact Assignment/Persona Template/Private Stance and exact request-bound Prompt Version。
- A single project-owned prompt boundary renders a closed allowlisted variable vocabulary with deterministic standard-library substitution；unknown/invalid/missing variables fail closed and rendered private prompts are neither persisted nor logged。
- The executor receives only a typed immutable provider-neutral input, not ORM objects、credentials、headers、database configuration、other participants' Private Stance or scoring/scheduler internals。
- Application orchestration creates/replays and claims the P1-5B request in short transactions, executes outside every database transaction, and atomically persists at most one final utterance。Before authoritative generation create/claim/final-completion mutation, it holds the session aggregate row lock and reuses P1-3 `reconcile_due_for_locked_aggregate(...)` with server-authoritative current UTC；reconciliation and generation-context validation share the required lock/transaction boundary。

### Allowed implementation scope

- `apps/api/src/group_interview_arena_api/modules/ai_runtime/`：pure prompt/rendering contract、typed deterministic generation harness、runtime orchestrator and the minimum persistence-service claim result required by the real deterministic caller；
- `apps/api/tests/`：targeted domain/harness tests and real PostgreSQL lifecycle/concurrency/privacy regressions；
- this execution plan plus `TASKS.md`、`ROADMAP.md`、`ARCHITECTURE.md`、`DATABASE.md`、`API.md`、`AGENT_BEHAVIOR.md` and `QUESTION_SYSTEM.md` current-state synchronization。

### Explicit deferrals and stop gates

- No schema/migration unless actual-source correctness proves an additive need；such a need must be reported for approval before implementation。
- No provider SDK、production adapter、factory、routing、fallback、registry or `providers/` directory。
- A minimum callable/async callable type may exist only because the deterministic runtime harness is a current real caller；it has no provider-specific semantics and P1-5D must recalibrate the formal provider abstraction when a real model caller exists。
- No API、WebSocket、Web、streaming/chunks、automatic floor-triggered generation、floor release/reassignment、memory/RAG/vector store、scoring/report、voice、Redis、queue/worker、billing/quota or CI workflow change。
- P1-3 remains phase/deadline authority and P1-4 remains floor/speaker authority；AI generation success/failure does not independently mutate either boundary。Before authoritative generation mutation, P1-5C must nevertheless reuse P1-3 overdue reconciliation under the aggregate lock；any resulting lifecycle/floor/event-sequence changes remain P1-3 facts rather than AI Runtime decisions。

### Crash/restart and concurrency policy

- `REQUESTED` may be durably claimed exactly once for execution；exact replay remains idempotent。
- A caller that observes an already `RUNNING` request does not assume whether an earlier execution is live or lost and does not auto-retry；it returns a safe deterministic reconciliation-required no-op。
- This fail-closed policy is sufficient for the local deterministic P1-5C harness and must be reevaluated in P1-5D before real provider retry/recovery semantics are approved。
- `COMPLETED` replays the durable utterance；`FAILED` replays the safe typed failure；neither state invokes the executor again。
- Concurrent exact callers have at most one executor claimant and at most one final utterance；stale phase/released or replaced grant results fail closed without an utterance or AI-owned floor/session mutation。A due phase discovered during locked pre-mutation validation may first persist authoritative P1-3 reconciliation facts, after which generation still fails closed。

### P1-5C acceptance gates

- Prompt renderer tests cover stable bytes、escaping、closed vocabulary、unknown/invalid/missing variables and immutable exact Prompt Version use。
- Authorized-context tests prove exact session-bound Question Version and only the granted participant's Persona/Private Stance are assembled。
- Deterministic harness tests cover success、timeout、unavailable、rate-limit、invalid output、partial generation and internal failure with stable provider-neutral results。
- Real PostgreSQL tests cover success lifecycle、exact replay、concurrent invocation、completed replay、RUNNING recovery no-op、stale grant、changed phase、released/replaced grant、wrong participant/human participant and failed-generation isolation。
- Privacy sentinels prove current private stance is available only to the generation context while other-participant stance、provider secret、Cookie/auth token、database URL and raw exception text do not enter generation input where forbidden、safe results、durable metadata/failure state or ordinary structured logs。
- Full API/PostgreSQL regression、Ruff、format、strict Pyright、frozen lock、Alembic single-head/current/drift/migration suite、temporary database cleanup、master-plan hash、scope and `git diff --check` pass。

## P1-5D design freeze — First Real Provider Integration

The completed design-freeze checkpoint established the first real-provider boundary without code or a GLM call。The separately approved implementation checkpoint now realizes that design through one explicit internal Zhipu provider while preserving every existing P1-3/P1-4/P1-5C lifecycle invariant。Codex still makes zero real GLM calls。

### Provider, endpoint and versioned development configuration

- First provider identity is exactly `provider_identifier = "zhipu"`；actual `model_identifier` comes from required lazy server-side `GIA_API_ZHIPU_MODEL` configuration。The current development selection is `glm-4.7-flashx`。
- The only approved transport is non-streaming `POST https://open.bigmodel.cn/api/paas/v4/chat/completions` with `Authorization: Bearer <server-only-api-key>` and JSON content。The endpoint and Bearer form were checked against the live official [Chat Completions reference](https://docs.bigmodel.cn/api-reference/%E6%A8%A1%E5%9E%8B-api/%E5%AF%B9%E8%AF%9D%E8%A1%A5%E5%85%A8) on 2026-08-24；the user's successful pre-implementation real API smoke is accepted evidence and will not be repeated by Codex。
- The code-owned non-secret invocation configuration version is exactly `ZHIPU_CHAT_DEV_V1`：`thinking = {"type": "disabled"}`、`stream = false`、`max_tokens = 512`、`temperature = 0.7` and application-level automatic retry `0`。Configuration version is independent of model identity；a model-only switch keeps `ZHIPU_CHAT_DEV_V1`，while a future parameter/timeout/retry-policy change requires a new version。This is development configuration, not permanent provider/model/product policy；the thinking field follows the live official [Thinking reference](https://docs.bigmodel.cn/cn/guide/capabilities/thinking)。
- The outbound message list is exactly one `user` message whose content is the already rendered P1-5C Prompt Version。The adapter adds no hidden system prompt、tool、response format、session metadata or provider-specific prompt suffix。
- Transport timeouts are explicit and bounded for this development configuration：connect `5s`、read `60s`、write `10s`、pool `5s`。Redirect following and client/application retries remain disabled。Changing these values requires a new configuration version or a documented transport-policy revision；it must not silently reinterpret historical generation provenance。

### Minimal project-owned provider boundary

The frozen call path is:

```text
P1-5C Runtime
  -> project-owned GenerationProvider contract
  -> Zhipu HTTP adapter
  -> BigModel chat completions endpoint
  -> normalized RawGenerationSuccess / RawGenerationFailure
  -> existing P1-5C completion/failure lifecycle
```

- P1-5D implements one minimal `GenerationProvider` `Protocol` retaining the current async `__call__(RuntimeGenerationInput) -> RawGenerationResult` shape。The existing executor alias now points to that Protocol，so deterministic and real callers remain compatible without lifecycle rewrites。
- Business/runtime code continues to depend only on project-owned `RuntimeGenerationInput`、`RawGenerationSuccess`、`RawGenerationFailure` and typed failure codes。HTTPX request/response/exception/client objects never cross the adapter boundary。
- The only adapter is `providers/zhipu.py`。No registry、factory hierarchy、multi-provider interface family、routing、fallback or SDK wrapper is created。
- The adapter uses `httpx.AsyncClient` and owns explicit client close/context-manager semantics。Tests may inject `httpx.MockTransport` / `AsyncBaseTransport`；production code does not accept arbitrary provider response objects as domain input。
- `zai-sdk` / `zhipuai` is not added。The existing `httpx>=0.28.1` constraint is promoted from dev-only to the single runtime dependency declaration and `uv.lock` is refreshed；no second HTTP client is added。

### Server-only secret and configuration boundary

- Implementation adds lazy `ZhipuProviderSettings` with environment prefix `GIA_API_ZHIPU_`、required `api_key: SecretStr` and required bounded `model: str`。The exact variables are `GIA_API_ZHIPU_API_KEY` and server-only non-secret `GIA_API_ZHIPU_MODEL`；ordinary API startup remains independent of these settings until an explicit provider caller loads them，and missing/blank values fail closed。
- The API key may exist only in server-side settings and the outbound Authorization header。It must not enter database rows、`RuntimeGenerationInput`、raw/validated generation result、request metadata、error messages、structured logs、trace spans、test fixtures or review bundles。
- `.env.example` may contain only a non-secret placeholder；no committed `.env`、example、test or documentation contains a real key。
- Provider/model/configuration mismatch is rejected before HTTP I/O：the adapter accepts only `zhipu`、the exact `ZhipuProviderSettings.model` value and `ZHIPU_CHAT_DEV_V1`。The same configured model is sent outbound and required in the successful provider response，keeping selected/outbound/confirmed/durable model provenance aligned without a model-specific branch。
- Changing the P1-5D Zhipu model requires only `GIA_API_ZHIPU_MODEL` configuration change plus API restart；it requires no Python、adapter or schema change。A future DB/admin-managed source may replace the environment source without changing the provider-neutral runtime contract，but no table、admin API/UI、hot reload、registry or routing is implemented now。

### Response acceptance and safe error normalization

- A successful HTTP response is accepted only when JSON reports the exact configured model、the selected choice has `finish_reason = "stop"`、`choices[0].message.role = "assistant"`, and content is a non-empty textual value accepted by the existing P1-5C `UtteranceText` validation。No reasoning content、tool call or provider metadata becomes utterance content。
- `finish_reason = "length"` or any other non-`stop` string is `PARTIAL_GENERATION` and no partial text is persisted。Missing/non-string finish reason、malformed JSON/shape、empty/non-string content or an unusable successful response is `INVALID_OUTPUT`；existing P1-5C validation also rejects whitespace-only or otherwise invalid utterance text before persistence。
- `httpx.TimeoutException` (including connect/read timeout) maps to `TIMEOUT`；HTTP `429` maps to `RATE_LIMIT`；network/transport failures and HTTP `5xx` map to `PROVIDER_UNAVAILABLE`；other safe unexpected adapter/HTTP failures map to `INTERNAL_ERROR`。
- Raw response bodies、raw exception text、request headers and credential-bearing request objects are never returned、persisted or logged。Only the existing allowlisted typed failure code reaches durable/runtime state。

### Provenance and schema assessment

- Every current development real-provider command must durably use `provider_identifier = "zhipu"`、`model_identifier = ZhipuProviderSettings.model` (currently `glm-4.7-flashx`) and `request_metadata.configuration_version = "ZHIPU_CHAT_DEV_V1"`。
- Actual source confirms the existing P1-5B `llm_generation_requests.provider_identifier`、`model_identifier` and closed `request_metadata.configuration_version` fields are sufficient。No schema/migration is authorized or required for P1-5D as designed。
- Rendered private prompt、raw provider request/response、reasoning content and API key remain transient and are not persistence requirements。
- If implementation discovers that exact actual provider/model/configuration provenance cannot be represented without a schema change, stop and report the additive need；do not create or edit a migration in P1-5D without new approval。

### Runtime, concurrency, restart and retry policy

- Provider execution remains outside every database transaction and row lock。Authoritative create/claim/final mutation reuses the existing aggregate-lock semantics, P1-3 `reconcile_due_for_locked_aggregate(...)`, exact phase/current-grant validation and atomic completion/failure persistence。
- A late/stale result never creates an utterance；one formal utterance remains the maximum per request and floor grant；AI outcome does not acquire lifecycle/floor/scheduler authority。
- Existing durable `RUNNING` remains fail-closed and returns reconciliation-required/no-op。It never automatically calls GLM again after restart or uncertain completion, preventing duplicate generation and duplicate cost。
- Application-level automatic retry is exactly `0`。Timeout、429、unavailable、partial、invalid and internal adapter outcomes produce one typed failed attempt；no fallback、routing or implicit provider retry is allowed。

### Exact P1-5D implementation files

The approved implementation changes are:

- modify `apps/api/src/group_interview_arena_api/modules/ai_runtime/generation.py` — formal minimal `GenerationProvider` protocol while preserving provider-neutral input/result/error types and the deterministic harness；
- keep `apps/api/src/group_interview_arena_api/modules/ai_runtime/runtime.py` unchanged — actual source already consumes the structurally compatible async callable outside lifecycle transactions；
- modify `apps/api/src/group_interview_arena_api/core/config.py` — lazy server-only `ZhipuProviderSettings`；
- add `apps/api/src/group_interview_arena_api/providers/__init__.py` and `apps/api/src/group_interview_arena_api/providers/zhipu.py` — the first real HTTP adapter and no framework around it；
- modify `apps/api/pyproject.toml` and `apps/api/uv.lock` — promote existing `httpx>=0.28.1` from dev-only to runtime dependency；
- modify `.env.example` — safe `GIA_API_ZHIPU_API_KEY=<server-only-zhipu-api-key>` placeholder and server-only non-secret `GIA_API_ZHIPU_MODEL=glm-4.7-flashx` selection。

No change is made to domain persistence services、ORM models、migration history、REST/OpenAPI、WebSocket、Web or CI。

### Implemented network-free automated test files

- add `apps/api/tests/test_zhipu_provider.py` — exact URL/header/body/model/config shape；thinking disabled；stream false；success、timeout、429、5xx/network、malformed JSON/shape、empty content、length truncation and raw body/exception/API-key secrecy through `httpx.MockTransport`；
- modify `apps/api/tests/test_config.py` — lazy required server-only key、`SecretStr` representation and environment isolation；
- modify `apps/api/tests/test_ai_runtime_generation.py` — deterministic harness compatibility with the formal provider protocol and absence of credential fields；
- modify `apps/api/tests/integration/test_ai_runtime_orchestration.py` — one mocked-transport provider-through-runtime success/failure proof while retaining all stale/deadline/concurrency/idempotency regressions；
- rerun the complete existing P1-5C targeted and full API/PostgreSQL suites。No automated test contacts the real GLM endpoint。

### Manual verification and implementation acceptance

- Manual access evidence supplied by the user：the original `glm-4.7-flash` verification repeatedly encountered provider rate-limit/availability failures，while the same valid credential and endpoint returned HTTP `200` for `glm-4.7-flashx`。This is the reason FlashX is the current development selection；it does not establish permanent unavailability or permanent production provider/model policy。Codex does not repeat either call。
- Final user-run sanitized real-provider acceptance smoke：`PASS`；`provider_identifier = "zhipu"`、server-configured `model_identifier = "glm-4.7-flashx"` from `GIA_API_ZHIPU_MODEL` and `configuration_version = "ZHIPU_CHAT_DEV_V1"`。`ZhipuGenerationProvider` returned `RawGenerationSuccess`，and output satisfied the intended Chinese group-interview smoke expectation。No credential、raw provider response、sensitive header、verbatim output or diagnostic payload is recorded。
- Implementation actual-source review and config-driven model patch actual-source review both returned `PASS`。All automated/network-free implementation gates and the final user-run sanitized real-provider acceptance smoke are satisfied；P1-5D is `DONE`。

### Explicit P1-5D stop gates and out of scope

- Stop on any required schema/migration、provider SDK、second HTTP client、credential-bearing persisted/logged/public state、automatic retry/fallback/routing、or lifecycle/floor authority drift。
- Do not implement automatic `floor.granted -> generation`、automatic floor release/reassignment、streaming、API/WS/Web、memory/RAG、scoring/report、voice、Redis/queue/worker、billing/quota or any P1-5E/F capability。
- Do not implement a model table、admin model API/UI、runtime hot reload、registry、routing、fallback、A/B/cost/per-plan/per-question selection；these remain future commercial evolution。
- The implementation checkpoint did not edit schema/migrations、runtime lifecycle control、API/WS/Web or CI and Codex did not contact BigModel。Final closeout is documentation-only and does not authorize P1-5E。

### P1-5D design-freeze acceptance

- The only working-tree changes are this execution plan、`TASKS.md` and `ROADMAP.md`；source、tests、schema/migrations、dependencies/lockfiles、configuration、API/WS/Web and CI remain unchanged。
- All Markdown relative links resolve、changed files retain final newlines、`git diff --check` passes and the master-plan hash remains unchanged from the recorded baseline。
- HEAD and `origin/main` remain at the recorded baseline；staged changes、commits and pushes remain zero。
- No provider endpoint was contacted and no secret/quota was used in the design freeze。At that checkpoint P1-5D remained open for implementation review and final user-run acceptance evidence；both later gates are now closed as recorded in the current acceptance section。

## P1-5E-1 design freeze — Automatic AI Runtime Orchestration

P1-5E is an application-level、state-driven coordination layer over existing authorities。A future minimal implementation candidate is `modules/ai_runtime/orchestration.py`，but P1-5E-1 creates no Python file、test、fixture、schema or migration。

The frozen authority chain is:

```text
durable current floor grant
  -> identify exact current participant
  -> HUMAN: stop and wait for human-side transport/action
  -> AI: resolve exact immutable runtime configuration
  -> create/replay one deterministic generation identity
  -> generate_ai_utterance(...)
  -> persist one final AI utterance or one typed terminal failure
  -> release the exact AI grant through Floor Control
  -> invoke Floor Scheduler
  -> inspect the newly durable current state
  -> continue only while the current owner is an eligible AI candidate
```

Floor Scheduler decides **WHO**；AI Runtime decides **WHAT**；the Automatic Orchestrator only coordinates these existing authorities。It is not a new domain authority and cannot directly update `simulation_sessions.current_floor_grant_id`、insert floor facts、choose a participant、change phase/deadline、bypass AI Runtime utterance persistence or own API/WebSocket/Web behavior。

### Exact existing application authorities

- Exact AI content entry point：`generate_ai_utterance(...)` in `modules/ai_runtime/runtime.py`。It owns request create/claim/replay、provider-neutral execution outside transactions and terminal request/utterance persistence。
- Exact floor-release entry point：`apply_floor_command(..., ReleaseFloorCommand(...))` in `modules/floor_control/service.py`。It owns `session_actions` replay/conflict、aggregate locking、exact phase/sequence/current-grant validation、`floor_releases` and ordered `floor.released`。
- Exact next-speaker entry point：`apply_scheduler_command(..., ScheduleFloorCommand(...))` in `modules/floor_control/service.py`。It owns locked scheduler input reconstruction、P1-3 reconciliation、phase/sequence/current-grant preconditions、`FloorDecision` and the resulting grant/intervention/no-grant fact。
- Exact lifecycle reconciliation entry point remains `reconcile_due_for_locked_aggregate(...)` in `modules/discussion_sessions/service.py`。The existing generation、release and scheduler services invoke this authority under the session aggregate lock where applicable；the orchestrator consumes the committed result and never overwrites it。

### State-driven invocation and authoritative re-entry

`floor.granted` is a durable trigger condition，not an exactly-once in-memory delivery requirement。Correctness must survive duplicate invocation、concurrent invocation、process restart and crashes between committed steps。Redis、event bus、queue、distributed lock and in-memory mutex are not correctness dependencies。

Every entry/re-entry first reads owner-scoped authoritative state：`simulation_sessions.status/current_floor_grant_id/last_sequence`、the exact `FloorGrant`/`FloorRelease`、participant actor/role/availability、durable `LlmGenerationRequest`、durable `AiUtterance`、`SessionAction` plus deterministic scheduler child facts and ordered `discussion_events`。The event sequence orders control facts；the utterance's exact request/grant links prove content completion。No public utterance event or transport projection is introduced here。

If the session is not in a floor-enabled phase，the drive stops as not applicable。If the current grant belongs to an eligible HUMAN candidate，the drive stops successfully and does not generate、release、schedule over or fabricate content for that participant。If no current grant exists，recovery may schedule only when it can prove that the latest unfinished automatic step is the deterministic next-schedule action for an exact AI grant already released by this orchestration chain；a P1-3 lifecycle release、human release or unrelated empty-floor state is not enough。

### Deterministic identities and replay payloads

One exact AI `floor_grant_id` maps to one logical automated turn。Project-owned deterministic UUIDs are derived from stable inputs under one fixed project namespace:

- `generation_request_id = deterministic(session_id, floor_grant_id, "ai-generation-request")`；
- `utterance_id = deterministic(session_id, floor_grant_id, "ai-utterance")`；
- `release_action_id = deterministic(session_id, floor_grant_id, "ai-floor-release")`；
- `next_schedule_action_id = deterministic(session_id, floor_grant_id, "ai-next-schedule")`；
- the scheduler `decision_id`、possible `grant_id` and possible `intervention_id` are deterministic children of that exact next-schedule action。

P1-5E-2 may use a fixed project UUID namespace plus standard-library UUIDv5 or an equivalent deterministic standard-library mechanism；the exact constant/helper name is an implementation detail，while the mappings above are frozen。A caller never mints a random replacement identity to escape a conflict、`RUNNING` state or stale precondition。

Existing digests include semantic payload fields beyond UUID identity，so replay must also preserve those fields:

- A new generation request chooses one server-authoritative `occurred_at`。If the deterministic request already exists，re-entry reconstructs the command from its exact durable `requested_at`、Prompt Version、provider/model and configuration version；it does not substitute current time/current latest configuration and therefore avoids `REQUEST_CONFLICT` or provenance drift。
- The release command uses the exact grant、phase、pre-release sequence and reason。An accepted deterministic release action replays through existing `SessionAction` digest semantics；its single causal release event also proves the committed pre-release sequence。
- The scheduler command uses the deterministic action/child IDs、post-release phase/sequence/current-grant preconditions、closed policy and one evaluated UTC。If the deterministic `SessionAction`/`FloorDecision` already exists，re-entry consumes that durable decision and child fact rather than minting another action。An exact reconstructed payload may use native replay；a concurrent same-ID/different-evaluation digest conflict means another caller won and requires a durable re-read，not a new ID。

This preserves current `SessionAction` semantics：same identity + same digest replays original causal events；same identity + different digest conflicts without mutation。Deterministic child IDs、the aggregate lock、current-grant pointer and scheduler preconditions prevent two formal next-floor winners。

### Invocation configuration resolution

For a new deterministic request，the server-owned V0.1 configuration is:

- `provider_identifier = "zhipu"`；
- `model_identifier = GIA_API_ZHIPU_MODEL` from lazy server-only settings；
- `configuration_version = "ZHIPU_CHAT_DEV_V1"`；
- `prompt_key = "AI_CANDIDATE_TURN"`；
- `prompt_version_number = 1`。

Committed runtime fixtures consistently use `AI_CANDIDATE_TURN` version `1` with purpose `CANDIDATE_UTTERANCE`，so this freeze does not invent a second prompt identity。The orchestrator resolves that exact stable key/version to one immutable published `PromptVersion.id` before request creation；it never hardcodes a database UUID and never selects implicit latest。If the exact key/version is absent、ambiguous、not yet published or retired for a new request，the drive stops safely before provider I/O。

For an existing deterministic request，its durable Prompt Version/provider/model/configuration/requested timestamp are authoritative。The injected `GenerationProvider` and current composition must exactly satisfy that provenance；a restart after a server model/config change cannot reinterpret or replace the request。If the exact stored configuration cannot be supplied，automatic progression stops for reconciliation/configuration recovery without a second request or provider call。

### Runtime outcome matrix

No new `RuntimeGenerationOutcome` is added in P1-5E-1。The orchestrator applies the following exact policy after re-reading durable state:

- `COMPLETED` / `COMPLETED_REPLAY`：require the exact request to be `COMPLETED` and one durable `AiUtterance` to match the request/grant。If that exact grant is still current，release it with `SPEAKER_FINISHED`；if lifecycle or another valid action already released/replaced it，do not mutate the stale grant and continue only from the new authoritative state。
- `FAILED` / `FAILED_REPLAY`：require the exact request to be durably `FAILED`。If that exact grant is still current，release it with `INTERRUPTED` and preserve the request's typed `failure_code` as the failure truth。Here `INTERRUPTED` means the granted AI turn ended without a formal utterance after a confirmed terminal runtime failure；it does not erase or replace the typed generation failure。No migration adds `AI_GENERATION_FAILED` in V0.1。
- `RECONCILIATION_REQUIRED`：stop。This includes durable `RUNNING` and any state where provider contact may already have occurred。Do not call provider again、release、schedule or synthesize `FAILED`。
- `REQUEST_CONFLICT` / `INTERNAL_ERROR`：stop with a reconciliation-required orchestration result。Do not release、schedule、retry provider or mint another identity。
- `CONTEXT_REJECTED`：re-read the session/grant/lifecycle facts。If P1-3 or another authority already changed state，follow that durable state；if the same grant remains current but context is still rejected，stop。Never release solely because context was rejected。
- `STALE_RESULT`：the old generation result is not authority for the current floor。Re-read lifecycle/current grant；never release or schedule from the stale grant。A new authoritative eligible AI grant may be handled only as a new exact state-driven turn；otherwise stop at the current human/non-floor/reconciliation boundary。
- `SUPERSEDED`：current source semantics mean another durable formal utterance won the unique floor-grant slot。First verify the exact winning `AiUtterance` and current state without another provider call。If the same grant is still current，treat the verified winning utterance as content completion and release with `SPEAKER_FINISHED`；if the grant is no longer current，make no stale mutation。If the winner cannot be proved，stop for reconciliation。

### Release and next-schedule ordering

The required commit order is strict:

1. generation reaches confirmed durable terminal truth；
2. revalidate exact current grant、phase and sequence；
3. release through `apply_floor_command`；
4. release transaction commits；
5. re-read authoritative session、release and sequence；
6. schedule through `apply_scheduler_command`；
7. scheduler transaction commits；
8. inspect deterministic `FloorDecision` and newly durable current grant；
9. continue only if that current grant belongs to an eligible AI candidate。

Provider I/O、release and scheduler execution are never wrapped in one database transaction。Provider I/O remains outside every transaction/row lock，and every next step consumes a committed prior step。

If scheduler outcome is `GRANT`，the durable current grant decides whether the caller stops for HUMAN or may continue for AI。If outcome is `NO_GRANT`，the deterministic decision is durable and the drive stops without mutating phase/current grant。If outcome is `REQUEST_INTERVENTION`，the existing scheduler authority persists `FloorIntervention` plus `floor.intervention_requested` and the drive stops；the AI orchestrator does not decide moderator/UI behavior。

### P1-3 reconciliation interaction

P1-3 lifecycle truth wins at every boundary。Generation create/claim/completion already reconciles overdue state under the session lock。Floor release also reconciles before applying its exact phase/sequence command；if reconciliation released the grant or changed phase，the automatic release becomes stale and must not overwrite the P1-3 facts。Scheduler likewise reconciles and validates exact phase/sequence/current-grant preconditions before deciding。

After any reconciliation-caused `floor.released` / `session.state_changed` facts，the orchestrator commits/returns to authoritative re-entry。It may continue only if the resulting phase is floor-enabled and the resulting exact current state independently permits it；it never rewrites lifecycle reason、phase、deadline or sequence facts。

### Concurrency and idempotency

Two concurrent drive invocations may observe the same AI grant。Both derive the same generation/request/utterance/release/schedule identities。Existing request digest + claim semantics allow one logical request and one executor claimant；an observed `RUNNING` is fail-closed。The unique `AiUtterance` request/grant constraints allow one formal content winner。

After terminal truth，the deterministic release action plus session aggregate lock/current-grant/sequence guards make exact release replay safe。After release，the deterministic schedule action/children plus expected phase/sequence/current-null-grant preconditions allow only one scheduling decision and at most one new current grant。A losing caller re-reads the durable winner；it never escapes by changing IDs。No distributed lock or authoritative in-memory mutex is introduced。

### Crash/restart matrix

- A — crash before request creation：re-entry derives the same request/utterance IDs and safely creates the request once。
- B — crash after `REQUESTED` but before `RUNNING`：re-entry loads the durable request payload/timestamp and may claim it under existing semantics；no new identity is created。
- C — crash while `RUNNING` or after provider may have been contacted：re-entry returns reconciliation required and never automatically contacts the provider again。
- D — crash after `COMPLETED` utterance but before release：re-entry replays durable completion and releases the exact still-current grant without provider I/O。
- E — crash after release but before scheduling：re-entry proves the deterministic automatic release and absent next-schedule action，then runs that exact deterministic scheduling step without provider I/O。
- F — crash after scheduler commit/grant：re-entry reads the deterministic decision and new current grant；it stops for HUMAN，drives the new exact AI grant when eligible，or stops on no-grant/intervention/non-floor state。

### Structured orchestration results and continuous-drive boundary

P1-5E-2/3 may implement provider-neutral structured result categories for：waiting for human、single AI turn completed/released、single AI turn failed/released、next AI granted、next human granted、no grant、intervention requested、not applicable lifecycle state、reconciliation required and drive budget exhausted。These are internal application results，not new `RuntimeGenerationOutcome` values、public events or telemetry schema。

`P1-5E-2 — Single AI Turn Orchestration Kernel` now implements `drive_single_ai_turn(...)` with `owner_id + session_id + orchestration configuration + injected GenerationProvider`，inspects one authoritative current grant，drives at most that one AI grant through generation、safe terminal release and one scheduler invocation，then returns the structured result/new current state。Its network-free PostgreSQL tests cover crash A～F、fresh and post-release same-session concurrency、typed failure、release/scheduler persistence uncertainty、SUPERSEDED winner proof、prompt/privacy isolation and lifecycle precedence；Codex makes no real-provider call。

`P1-5E-3 — Continuous AI Drive + Composition Acceptance` repeatedly invokes the single-turn kernel across consecutive AI grants and composes the existing Zhipu provider only from lazy server settings。The kernel remains provider-neutral and automated tests remain network-free。The separately user-run sanitized real-provider composition smoke is `PASS` with only the allowlisted facts recorded below。

Continuous drive stops when the current grant belongs to HUMAN、scheduler returns `NO_GRANT`、scheduler requests intervention、session leaves a floor-enabled phase、lifecycle reconciliation changes/terminates applicability、durable truth is uncertain or the per-invocation safety budget is exhausted。The frozen application guard is `MAX_AUTOMATED_AI_TURNS_PER_DRIVE = 8`。Exhaustion does not release/mutate the current grant、fail a request or change phase；it returns safe `drive budget exhausted / resume allowed` and a later invocation resumes from durable state。This is not a user-facing product limit。

### Schema conclusion and explicit deferrals

Actual-source analysis confirms no orchestration table or migration is required for the frozen invariants。Existing `simulation_sessions`、`session_actions`、`discussion_events`、`floor_decisions`、`floor_grants`、`floor_releases`、`llm_generation_requests`、`ai_utterances` and `prompt_versions` already provide current-state authority、deterministic action replay/conflict、single-owner sequence guards、request lifecycle and unique utterance/grant truth。Scheduler interventions use the existing `floor_interventions` table。

This conclusion is limited to automatic orchestration correctness。P1-5E-1 did not add a public utterance event、human utterance transport、REST/WebSocket/Web projection、streaming/chunks、telemetry、Redis、queue/worker、retry/fallback/routing、model registry/admin configuration、RAG/memory、scoring/report、billing/quota、voice or schema。At that checkpoint P1-5F owned later transport/public behavior and nothing was pre-decided there；the separately approved F1 section below now freezes those contracts docs-only。

### P1-5E-1 acceptance

- Only approved documentation is changed；no Python/source/test/fixture/schema/migration/dependency/lock/config/API/WS/Web/CI artifact changes。
- Current-state/status、outcome、crash/restart、concurrency/action replay、privacy and schema conclusions agree across this plan and synchronized domain/governance docs。
- Markdown relative links、final newlines、secret/static leakage、master-plan hash、scope and `git diff --check` pass。
- Provider calls、staged changes、commit and push remained zero at the P1-5E-1 closeout checkpoint。P1-5E-1 actual-source review is `PASS` with findings none；reviewed bundle SHA-256 is `dae10e722244b1b6e73a5a360f6064c948bfaf5aa138c0d4b89b1f9961f35055`；at that checkpoint P1-5E-1 was `DONE` and P1-5E-2/P1-5E-3/P1-5F were `NOT_STARTED`。

## Frozen failure and retry boundary

适用 failure classes：timeout、provider unavailable、rate limit、partial generation、invalid/unsafe output 和 caller cancellation/stale grant。

共同原则：

- 重试必须有界、按 typed class 决定，并保持同一 logical generation identity；provider 自带 retry 不能绕过 application idempotency。
- 每次 attempt 在提交结果前重新验证 exact session、phase、participant 和 current grant；phase/grant 已变化时丢弃 late result，不持久化 utterance。
- timeout/unavailable/rate-limit 可按未来获批 policy 重试或降级；provider fallback 仍必须记录实际 provider/model/config provenance。
- partial generation 默认不是 final utterance。除非未来明确冻结 partial-commit contract，否则 partial output 必须丢弃或作为非公开诊断最小化处理。
- AI generation failure itself does not independently change phase、extend/shorten deadline、transfer floor、modify scheduler decision or trigger scoring。
- Before authoritative generation mutation, P1-5C reuses P1-3 `reconcile_due_for_locked_aggregate(...)` under the same aggregate lock with server-authoritative current UTC。That reconciliation may advance phase/deadline, release the old grant, append ordered `floor.released` / `session.state_changed` events and advance discussion sequence；these are P1-3 lifecycle facts, not effects decided by the AI generation outcome。
- failure resolution 必须通过 deterministic control path release exact grant 或请求已有 floor intervention；不能让 floor 永久悬挂，也不能重复 release。
- crash/restart 后必须能从 durable request/grant truth 判断 retry、fail 或 no-op，不能仅靠 process memory 猜测是否已产生 utterance。

## Commercial-readiness boundary

未来架构应可演进支持：

- multiple providers and provider routing；
- token/latency/cost accounting；
- enterprise model endpoints；
- DB/admin-managed server-side model configuration replacing the current environment source without changing the runtime provenance contract；
- audit trace from utterance to prompt/model/config；
- prompt iteration and version comparison。

P1-5A 不提前实现 billing、quota、payment、multi-tenant、enterprise account provisioning、provider marketplace 或成本结算。成本统计是 invocation observability/provenance 能力，不是商业计费系统。

## Explicit deferred scope

Implemented in P1-5C current state:

- closed deterministic exact Prompt Version rendering；
- authorized context assembly for the exact session-bound Question Version and only the granted AI participant's Assignment/Persona/Private Stance；
- deterministic internal runtime/application caller with a network-free local executor harness。

Implemented in P1-5D current checkpoint:

- one non-streaming Zhipu path using the minimal project-owned provider protocol and thin HTTPX adapter，with current configured model `glm-4.7-flashx`；
- lazy server-only Zhipu credential/model loading from `GIA_API_ZHIPU_API_KEY` / `GIA_API_ZHIPU_MODEL` and promotion of existing HTTPX to runtime dependency；
- exact `provider_identifier` / configured `model_identifier` / model-independent `ZHIPU_CHAT_DEV_V1` provenance，with model changes requiring configuration plus API restart rather than Python、adapter or schema changes；
- network-free mocked-transport provider tests plus final user-run sanitized real-provider acceptance smoke `PASS`。

Still Deferred after the P1-5E-1 docs-only freeze:

- provider SDK、multi-provider registry/routing/fallback and automatic retry；
- production prompt orchestration beyond the closed P1-5C renderer and internal prompt-variable persistence；
- additional provider-attempt/fallback hierarchy beyond the current one-request/one-attempt identity；
- P1-5E-3 implements only bounded in-process continuous automatic orchestration and configured composition；P1-5F-1 now freezes transport/API/WebSocket/Web semantics docs-only，while all implementation、startup/background invocation and streaming remain deferred to P1-5F-2～F4 or later approved work；
- memory、RAG、embedding/vector store；
- scoring、evidence extraction、report generation；
- voice、ASR、TTS、audio interruption；
- emotion、face、camera or video detection；
- Redis、task queue、distributed worker；
- billing、quota、payment and multi-tenant。

## Later implementation gates

P1-5D implementation and config-driven patch followed the frozen section above without scope expansion；both actual-source reviews and the final user-run sanitized real-provider acceptance smoke passed，and P1-5D is `DONE`。P1-5E-1/E2/E3 and P1-5F-1/F2/F3A/F3B/F4 retain historical `DONE` and all recorded acceptance evidence；`F4-ACC-001` remains `CLOSED`。The parent historically closed after F4，then local acceptance opened P1-5R；therefore P1-5 is currently `IN_PROGRESS / POST_CLOSEOUT_REMEDIATION_OPEN` and P1 remains `IN_PROGRESS`。Any later implementation/transport subphase must preserve:

- any additive schema need and historical deletion/retention semantics；
- provider-neutral request/result/error contract with a real caller；
- Prompt Version rendering authority；
- generation/attempt idempotency, concurrency and restart recovery；
- formal event/API/WS/public projection vocabulary；
- fake-provider deterministic tests and privacy sentinel tests；
- whether a bounded synchronous/in-process caller is sufficient before any queue is reconsidered。

## P1-5A validation

- changed-file scope contains documentation only；
- Markdown relative links resolve；
- `TASKS.md`、`ROADMAP.md`、`ARCHITECTURE.md`、`API.md`、`DATABASE.md`、`AGENT_BEHAVIOR.md`、`QUESTION_SYSTEM.md` and this plan agree on P1-5A status and Deferred implementation；
- scheduler/runtime、participant/runtime、request/utterance、provider/domain and public/private boundaries are consistent；
- `git diff --check` passes and changed Markdown files have final newlines；
- master-plan SHA-256 and Git object hash remain unchanged；
- no runtime、tests、schema/migration、dependency/lockfile、CI、API implementation or review bundle change。

## P1-5B validation gates

- Ruff lint、Ruff format check and strict Pyright；
- domain/model tests for immutable prompt identity、closed metadata、`VARCHAR` lifecycle and completed-generation utterance constraint；
- real PostgreSQL integration for exact replay/conflict、request lifecycle、ownership/stale-context checks、failed generation isolation、at-most-one utterance and constraint-triggered transaction rollback；
- fresh/repeat migration、single head、downgrade to P1-4、re-upgrade、exact table catalog and `alembic check`；
- full API test regression, master-plan hash, changed-file scope and `git diff --check`；
- no provider SDK/dependency/lockfile/API/WS/Web/CI changes。

## P1-5C validation result

- Closed Prompt Version rendering、typed immutable runtime contract and deterministic local success/failure harness are implemented without network I/O；
- authorized-context assembly resolves the exact session-bound Question Version、current AI grant、that participant's Assignment/Persona/Private Stance and exact Prompt Version, with no cross-seat private context；
- short database transactions surround an executor call that runs outside all transaction/row-lock scopes；P1-5B request claim、terminal replay and atomic completion remain the durable truth；
- real PostgreSQL tests cover success、safe failures、completed/RUNNING replay、concurrent exact/different request identities、stale phase/released/replaced grants and overdue phase reconciliation before executor/result mutation；AI generation outcome/failure does not independently mutate lifecycle/floor authority, while any authoritative phase/deadline/floor/event-sequence change remains a P1-3 reconciliation fact and no stale utterance is persisted；
- final full backend regression is `406 passed` with 1 existing Starlette deprecation warning；Ruff、format、strict Pyright、frozen dependency checks、Alembic head/current/check and governance/scope checks pass；
- no schema/migration、dependency/lockfile、provider SDK/abstraction、API/WS/Web、automatic floor trigger/release、queue/worker、memory/RAG or scoring/report implementation was added。

## P1-5D implementation checkpoint validation result

- Original implementation TDD preserved its two meaningful collection RED gates。The config-driven model patch then produced a focused meaningful RED of `9 failed`：settings had no required model validation and the hardcoded adapter could not switch `glm-4.7-flashx` / `glm-4.7` from configuration。Current focused GREEN results are config `55 passed` and provider `47 passed`。
- Network-free provider/config/generation targeted tests are `111 passed`；real PostgreSQL AI runtime orchestration is `8 passed`。Coverage includes two code-free configured model selections、outbound/response/durable exact model alignment、model-independent configuration version、pre-I/O mismatch、safe error/secret boundaries and existing lifecycle/replay behavior。
- Fresh full backend/PostgreSQL regression is `469 passed` with 1 existing Starlette deprecation warning。No test constructs an unmocked Zhipu provider；Codex made zero real GLM calls and used no provider secret/quota。
- Ruff lint、Ruff format check (`109 files`)、strict Pyright、`uv sync --frozen` and `uv lock --check` pass。HTTPX has one runtime declaration，with no provider SDK or second HTTP client。
- Alembic single head/current/check remains `f1a15b15c005` with no new upgrade operations；migration/schema source is unchanged and temporary PostgreSQL database residual is `0`。
- Markdown relative links、final newlines for all current changed/untracked files、master-plan hash、exact scope、secret/static boundary and `git diff --check` pass。Implementation and config-driven patch actual-source reviews are `PASS`；the sanitized user smoke is `PASS`；staged/commit/push remain zero and P1-5D is `DONE`。

## P1-5E-2 actual-source review and final closeout

- Initial actual-source review verdict was `BLOCKED` with three findings only。All three findings were remediated；remediation actual-source re-review verdict is `PASS` with findings none。Reviewed bundle SHA-256 is `69b5f23c131bff409d4455854e6b0526863aebe9b5a314894895d8e62d600795`。
- `CONTEXT_REJECTED`/`STALE_RESULT` now re-read exact session/current-grant truth：proved current-grant/lifecycle change returns `STATE_CHANGED`；the same exact current grant returns `RECONCILIATION_REQUIRED` without release、scheduler or provider retry。Invalid prompt rendering and overdue lifecycle regressions prove both branches。
- Release/scheduler `SessionPersistenceError` now re-reads authority：an exact expected durable result is recovered，another proved authoritative change returns `STATE_CHANGED`，and an otherwise still-applicable checkpoint without the expected durable result returns `RECONCILIATION_REQUIRED`。No success/failure is synthesized and provider execution is never retried。
- Real PostgreSQL crash-E concurrency prepares one exact automatic release with no schedule fact，then runs two callers：provider calls remain zero，one deterministic `SessionAction` and `FloorDecision` win，at most one next grant/intervention exists and both callers recover the same action identity without duplicate next speaker。
- Remediation-focused automatic orchestration is `22 passed`；relevant runtime/floor/lifecycle regression is `98 passed`；fresh full backend/PostgreSQL is `491 passed` with one existing Starlette deprecation warning。Ruff、format (`112 files`)、strict Pyright、frozen dependency/lock and Alembic head/current/check pass。
- No schema/migration、dependency/lock、configuration、provider、`runtime.py`、`service.py`、API/WS/Web or continuous-drive implementation change；real-provider calls are zero。At the P1-5E-2 closeout checkpoint，P1-5E-2 was `DONE`、P1-5E remained `IN_PROGRESS` and P1-5E-3/P1-5F remained `NOT_STARTED`；the current status is superseded by the P1-5E-3 final closeout below。

## P1-5E-3 actual-source review, composition smoke and final closeout

- Meaningful TDD RED gates were missing `continuous` composition surface and missing canonical public Zhipu provenance constants。The GREEN implementation adds one provider-neutral continuous module、one thin lazy composition module and only promotes the two existing adapter constants；the E2 kernel remains unchanged。
- `drive_continuous_ai(...)` calls E2 until a frozen stop boundary or exact budget。A proved release action advances the count；post-release scheduler recovery does not；eight advances return `BUDGET_EXHAUSTED` before a ninth kernel/provider call。Distinct next-grant and repeated-progress guards prevent a busy loop or fabricated progress。
- PostgreSQL tests use real services/state transitions to prove AI → AI → HUMAN consecutive drive、terminal provider failure followed by a distinct AI、post-release crash-E scheduler recovery、concurrent convergence with one call/request/utterance/release per exact grant and cancellation propagation with durable `RUNNING` fail-closed re-entry。
- `drive_configured_ai_session(...)` lazily loads required server-only Zhipu settings，constructs the existing provider and passes canonical `zhipu` / configured model / `ZHIPU_CHAT_DEV_V1` plus the existing V0.1 scheduler policy。Missing settings produce only a generic safe composition error；ordinary imports/startup require no provider environment。
- Network-free results are `47 passed` focused E3/E2、`253 passed` relevant runtime/floor/lifecycle and `516 passed` full backend/PostgreSQL with one existing Starlette deprecation warning。Ruff formatting/lint and strict Pyright pass；real-provider calls are zero。
- External implementation actual-source review verdict is `PASS` with findings none；reviewed implementation bundle SHA-256 is `a2b453846f1ad1e94fa17b74ca507efe462c176d67471cae87278893bb907dd0`。
- User-run sanitized real-provider composition smoke is `PASS`：`continuous_outcome = WAITING_FOR_HUMAN`、`automated_ai_turns_advanced = 1`、`generation_request_count = 1`、`provider_identifier = zhipu`、`model_identifier = glm-4.7-flashx`、`configuration_version = ZHIPU_CHAT_DEV_V1`、generation request `COMPLETED`、formal `AiUtterance` persisted、AI `FloorRelease = SPEAKER_FINISHED` and resulting current floor actor `HUMAN`；pytest smoke is `1 passed in 5.56s`。
- No credential、Authorization header、raw provider response、rendered prompt、Private Stance or verbatim model output was recorded。The temporary manual smoke test file was removed and is excluded from project/review scope。
- No schema/migration、dependency/lock/config、E2 orchestration、runtime/service、API/WS/Web implementation change。At the P1-5E-3 closeout checkpoint，P1-5E/P1-5E-3 became `DONE` and P1-5F remained `NOT_STARTED`；the current P1-5F-1 status is superseded by the design-freeze section below。

## P1-5F-1 design freeze — Realtime/Public Contract

P1-5F-1 is the separately approved docs-only architectural freeze for exposing the completed P1-5E automatic AI orchestration through a public text-discussion contract。It created no backend、Web、WebSocket、REST、schema、migration、test、generated contract、dependency、configuration or infrastructure implementation in that design-freeze turn。Its later F2/F3/F4 descendants retain historical `DONE` and their evidence。The current hierarchy additionally has `P1-5 IN_PROGRESS / POST_CLOSEOUT_REMEDIATION_OPEN` and `P1-5R IN_PROGRESS / DESIGN_FROZEN`；R1/R2-A/R2-B/R3 are `NOT_STARTED`。F4 acceptance used the network-free fake-provider path and made no real provider/model call。

### Public protocol and deployment boundary

- WebSocket is the client-facing realtime protocol for active discussion commands and ordered incremental session events。REST remains authoritative for resource、snapshot and history reads。
- WebSocket does not promise a permanent deployment topology。Future Redis/NATS/Kafka、realtime gateway or multi-worker routing may replace internal delivery without changing this public REST/WS contract。
- Human text utterance submission uses WebSocket，not REST。P1-5F-1 adds no SSE、REST command fallback、Redis、queue、worker or realtime gateway。
- The approved command is `participant.utterance.submit` with `schema_version = 1` and the existing command envelope：

```text
schema_version = 1
type = "participant.utterance.submit"
session_id
action_id
payload:
  floor_grant_id
  content
```

- Narrow F1 contract erratum discovered during P1-5F-2 actual-source review：the client must provide the exact public `floor_grant_id` it is answering；the client still must not provide `participant_id`、`actor_kind`、`phase` or any AI/provider/runtime identity。The server derives participant identity and phase from the authenticated user and locked durable state，and must never silently bind a delayed command to whichever Human grant is current on arrival。

### Human authorization, reconciliation and text validation

A syntactically valid Human utterance is accepted only when one locked aggregate operation proves all of the following after lifecycle/deadline reconciliation：

- the session belongs to the current authenticated owner；
- the session remains in a floor-enabled active phase；
- `payload.floor_grant_id == aggregate.current_floor_grant_id`；
- that exact named floor grant is current and unreleased；
- the grant participant belongs to the session and the grant phase remains exact；
- the participant has `actor_kind = HUMAN`、`participation_role = CANDIDATE` and belongs to the authenticated user；
- the exact authoritative phase/current grant did not advance during reconciliation。

A late command after authoritative phase/grant advancement is rejected and never becomes an utterance in the old turn。A syntactically valid command rejected by current authority or content rules uses the recoverable WS business error `UTTERANCE_REJECTED` with the exact safe message `You cannot submit an utterance right now.`；the socket remains open。The error does not reveal whether rejection came from an AI floor、stale grant、phase transition、deadline reconciliation、content rule or another internal state reason。Malformed envelopes remain `PROTOCOL_ERROR`。Existing safe concepts remain `ACTION_ID_CONFLICT`、`SEQUENCE_AHEAD` and `INTERNAL_ERROR`。

V0.1 Human `content` is frozen as：

- `1..4000` Unicode code points；
- `content.strip()` must not be empty；
- U+0000 is rejected；
- no Unicode normalization；
- accepted content is not automatically trimmed；
- the accepted original content is persisted exactly。

The 4000-code-point bound is a V0.1 safety/abuse limit，not a permanent commercial product limit。

### Unified formal utterance event、versioned floor compatibility and public allowlist

Human and AI formal public utterances use one event only：`participant.utterance.created`，`schema_version = 1`。There is no `human.utterance.created`、`ai.utterance.created`、`message.created`、`ai.generation.started` or `ai.generation.failed` event。

The existing formal envelope owns `session_id`、`sequence`、`occurred_at` and nullable `action_id`。The payload is exactly：

```text
utterance_id
participant_id
actor_kind        # HUMAN | AI
floor_grant_id
phase
content
```

Envelope fields are not duplicated in the payload。A Human utterance event carries the original `participant.utterance.submit` `action_id`；an AI utterance event carries `action_id = null`。

Historical P1-4 floor-event `schema_version = 1` semantics remain unchanged：`floor.granted` and `floor.intervention_requested` require a non-null UUID4 `action_id`，while `floor.released` permits UUID4 or null。Existing persisted v1 facts、backend serialization and Web parsing keep those exact semantics；v1 events are not rewritten、redacted in place or reinterpreted as the new meaning。

P1-5F freezes additive public floor-event `schema_version = 2`。Event names and payload meanings remain `floor.granted`、`floor.released` and `floor.intervention_requested`。The v2 envelope keeps `action_id` always present and nullable，but the field represents only a public client action identity：an event directly caused by the Human `participant.utterance.submit` command may expose that original Human action ID where applicable；internal automatic scheduler、release or intervention causation must serialize `action_id = null`。Internal `SessionAction` causation remains durable/private for idempotency and replay。

Floor-event v2 is an additive public compatibility layer under ADR-007's independently versioned WS contract，not a change to historical v1。P1-5F-2 preserves historical v1 serialization/replay while producing v2 for new P1-5F public floor projections；P1-5F-3A implementation must parse/project both versions and enforce each version's exact action semantics。`participant.utterance.created` remains independently frozen at `schema_version = 1`。

New P1-5F utterance/floor REST/WS projections and errors never expose `generation_request_id`、provider/model identifiers、configuration version、Prompt Version identity/content、rendered prompt、Private Stance、provider raw response、generation internal failure taxonomy、internal automatic orchestration release/schedule/intervention action IDs、secrets or Authorization headers。Historical floor-event v1 remains readable with its already-published action semantics。

### Authoritative transcript REST contract

The independent authoritative transcript read endpoint is：

```text
GET /sessions/{session_id}/utterances
```

The whole transcript is not added to `GET /sessions/{session_id}`。The endpoint requires authentication but no CSRF mutation header。Missing and non-owner sessions both follow existing `SESSION_NOT_FOUND` / `404` non-disclosure semantics。

Pagination uses `after_sequence >= 0` as an exclusive cursor，`limit = 100` by default and `limit <= 200`，ordered by full discussion `sequence ASC`。Offset/page-number pagination is not used。The response is：

```json
{
  "items": [
    {
      "utterance_id": "...",
      "sequence": 18,
      "occurred_at": "...",
      "action_id": "... or null",
      "participant_id": "...",
      "actor_kind": "HUMAN | AI",
      "floor_grant_id": "...",
      "phase": "...",
      "content": "..."
    }
  ],
  "next_after_sequence": 18
}
```

`next_after_sequence` is the last returned transcript sequence when another page exists，otherwise `null`。`action_id` is always present and nullable：Human items use the original client action ID；AI items use `null`。This lets reconnect prove whether a pending Human command already became durable。

### Current transcript persistence and future retention safety

- `DiscussionEvent` is the current durable ordered public transcript/event persistence implementation。The public transcript read is a purpose-built projection over its `participant.utterance.created` facts。
- Human utterance does not require a `human_utterances` table。Existing `AiUtterance` remains the internal AI provenance/content fact；its ID is the AI public `utterance_id`。
- Public clients depend only on the REST/WS contracts，not on `DiscussionEvent` as a permanent physical-storage promise。
- If event retention、compaction or a replacement read model is introduced later，an equivalent durable transcript projection must exist before deleting the only user-visible transcript copy。Compaction must never accidentally destroy historical transcript。
- P1-5F does not redesign `AiUtterance` into a generic table and does not add a Human utterance table。

### Human identity, idempotency and atomic release

The existing `(session_id, action_id)` identity remains the Human command idempotency boundary。Same action ID plus the same `floor_grant_id` and exactly the same content is exact replay：no second utterance、release、scheduling or AI drive。Same action ID plus a different floor grant or different content is `ACTION_ID_CONFLICT`。

Human `utterance_id` is server-owned and deterministic from the accepted session/Human command identity。Replay returns the same ID；the client cannot choose it。P1-5F-2 may finalize the namespace/helper，but the result must follow the existing project convention of deterministic bytes with UUID4-compatible public identity。

The accepted Human utterance and release of that exact Human floor grant are one locked aggregate transaction：

```text
lifecycle/deadline reconciliation
  -> validate exact HUMAN current grant
  -> persist SessionAction(participant.utterance.submit)
  -> persist participant.utterance.created   sequence N
  -> persist FloorRelease(SPEAKER_FINISHED)
  -> clear current_floor_grant_id
  -> persist floor.released                  sequence N+1
  -> commit
```

The `participant.utterance.created` v1 event and causal `floor.released` v2 event both carry the original Human action ID。The system never exposes a durable intermediate state in which the Human utterance exists but that exact successful Human grant remains authoritative/current because release was omitted。Successful public order is always `N participant.utterance.created` then `N+1 floor.released / SPEAKER_FINISHED`。

### Separate scheduler checkpoint and P1-5E composition

The Human transaction never chooses the next speaker。After Human+release commit，P1-4's deterministic Floor Scheduler runs as a separate locked transaction and produces `floor.granted`、intervention or no grant。Human progression uses deterministic scheduler/action/child identities tied to the exact session and released Human grant，so crash/re-entry converges on the same logical checkpoint without minting a new schedule identity。

No orchestration table is planned。If P1-5F-2 proves that existing durable release/action/scheduler facts cannot recover this checkpoint，implementation must stop for separate schema review。

If the post-Human scheduler grants an AI participant，transport calls the existing configured P1-5E composition path `drive_configured_ai_session(...)`。Transport does not duplicate AI Runtime、Generation Request lifecycle、Floor Scheduler、release logic、continuous drive loop or provider selection。P1-5E remains application-level、state-driven and reentrant。

### AI public-event atomicity

For successful AI generation，these three facts must commit atomically in the existing locked generation-completion transaction：

```text
LlmGenerationRequest -> COMPLETED
AiUtterance
participant.utterance.created
```

The event uses the same `AiUtterance.id` as public `utterance_id`，increments the authoritative discussion sequence and has `action_id = null`。This prevents a crash after `AiUtterance` commit from permanently omitting the public transcript fact。After that commit，existing P1-5E progression continues in separate commits：release `SPEAKER_FINISHED`，then scheduler。AI terminal failure creates no fabricated utterance event；existing typed generation failure remains internal while the authoritative public control flow is `floor.released / INTERRUPTED` then scheduler。

### Commit-before-send and progression invocation

All WebSocket delivery happens after the authoritative database transaction commits：always `DB commit -> WS/catch-up delivery`，never `WS send -> DB commit`。Disconnect/send failure after commit does not roll back、regenerate、duplicate the utterance or mint a replacement action identity；reconnect/catch-up recovers durable truth。The socket is delivery，not truth。

V0.1 transport may use bounded best-effort in-process invocation after the Human commit to resume progression，but correctness cannot depend on the task surviving。Progression remains state-driven、reentrant、concurrency-safe、restart-safe and may be re-entered by reconnect/resume。P1-5F-1 adds no Redis、Celery、Kafka、NATS、distributed worker or dedicated realtime gateway。

### Crash and restart matrix

- A — crash before Human transaction commit：no utterance fact；the original action can safely retry。
- B — Human utterance+release committed，crash before scheduler：the Human utterance remains；the deterministic same scheduler checkpoint resumes。
- C — scheduler committed an AI grant，crash before provider：the durable current AI grant drives existing P1-5E。
- D — provider may have been contacted and request is `RUNNING`：preserve existing P1-5E fail-closed behavior；never automatically issue a second paid call。
- E — AI utterance+public event committed，crash before AI release：existing P1-5E resumes the exact release without regeneration。
- F — AI release committed，crash before next scheduler：existing P1-5E crash-E scheduler recovery applies。
- G — any business commit succeeded but WS send failed：reconnect/catch-up only；no repeated business mutation。

### Browser AI UX and Human pending rules

No public AI Runtime lifecycle event、provider status or ETA/countdown is introduced。The Browser derives processing only from authoritative current floor：when the current grant actor is AI，it may show `AI 候选人正在组织发言…`。Success is observed through the formal utterance then normal floor progression。Terminal failure has no utterance；`floor.released / INTERRUPTED` is authoritative and the Browser may show a non-transcript、non-durable generic notice such as `该 AI 候选人本轮未能完成发言，讨论已继续。`。It never shows HTTP status、`RATE_LIMIT`、provider/model/configuration or raw exception。

Local、non-authoritative draft preparation in the textarea may remain editable before the authenticated Human owns the current floor；editability does not grant permission to submit。Authoritative `participant.utterance.submit` permission is enabled only when authoritative state proves an active floor-enabled session whose current grant belongs to that Human and the other frozen F3A send gates pass。AI floor、another participant、no current floor and terminal session disable submission，not local draft preparation。Client submission disablement is UX only；the backend always revalidates the command、including its exact floor binding。

After submit，the Browser may keep an in-memory pending state but must not render pending text as a formal transcript bubble before a durable `participant.utterance.created` fact arrives。Pending is confirmed by matching WS event `action_id` or，after reconnect，matching transcript item `action_id`。Pending `action_id + floor_grant_id + content` is never stored in localStorage/sessionStorage。Disconnect does not justify a new action ID；retry reuses the original action and floor binding。

### Browser restore and transcript convergence

Initial load/reload is frozen conceptually as：

```text
GET /sessions/{id}
  -> authoritative snapshot and watermark S
GET /sessions/{id}/utterances
  -> durable transcript
connect WS with after_sequence=S
  -> S-after ordered incremental session events
```

REST/WS races converge by stable identity。`utterance_id` is transcript primary identity and `sequence` is authoritative order：a new ID inserts；an identical replay is ignored；the same ID with conflicting authoritative fields is an integrity mismatch that stops local inference and reloads both authoritative session and transcript。Transcript sequence is filtered from the full `DiscussionEvent` stream and is not contiguous；for example `18, 21, 25` is valid。Transcript-only items never use sequence-gap detection；gap detection remains a property of the complete WS formal event stream。

Authoritative reload merges by identity and does not deliberately clear already confirmed transcript first，avoiding an unnecessary empty/flicker cycle。

### Logging, privacy and public redaction

Utterance content is not duplicated into ordinary logs、WS error logs、traces or telemetry merely because it is a legitimate transcript fact。Safe operational metadata may include `session_id`、`participant_id`、`utterance_id`、`action_id`、`sequence`、`actor_kind`、a safe outcome category and latency。Logs/telemetry never contain utterance content、prompt、Private Stance、provider raw response、credential、Authorization or raw provider exception body。

Purpose-built floor-event v2 serialization strips internal automatic scheduler/release/intervention action IDs while preserving them in internal durable facts when required for replay。Historical floor-event v1 remains unchanged and dual-readable；generation request/provider/model/configuration/prompt/failure internals remain excluded from new transcript、formal events、errors and Browser state。

### P1-5F subphases and later acceptance

- `P1-5F-1 — Realtime/Public Contract Design Freeze`：this docs-only checkpoint。
- `P1-5F-2 — Backend Text Discussion Transport`：Human WS command；durable unified public utterance event；historical floor-event v1 preservation plus additive v2 serialization；atomic Human utterance+release；transcript REST；AI completion event projection；post-Human scheduler plus existing E3 composition invocation；backend recovery/idempotency/privacy tests。Web UI remains out of scope。
- `P1-5F-3 — Web Discussion Experience` is split into:
  - `P1-5F-3A — Web Discussion Functional Closure`：existing session-panel/realtime integration；strict dual parsing/projection of historical floor-event v1 and additive v2；pure confirmed-transcript merge；Human input/pending/rejected recovery；public-fact-derived AI waiting/interruption；non-destructive reload/reconnect/gap recovery；no major visual redesign。The frozen design is [`P1-5F-3A_web-discussion-functional-closure.md`](P1-5F-3A_web-discussion-functional-closure.md)。
  - `P1-5F-3B — Complete Discussion Page Composition`：later complete desktop question/discussion/process-status page composition and layout；no change to F3A protocol/transcript semantics。
- `P1-5F-4 — Composition E2E + Independent Acceptance`：PostgreSQL+backend+WS+Browser/Chromium end-to-end with fake/mock network-free provider；independent acceptance；an optional final user-run sanitized one-call real-provider Browser smoke only when explicitly instructed。

P1-5F-2 acceptance must prove exact Human-floor authorization、Human event+release atomicity、exact replay/conflict、AI completion+public-event atomicity、transcript pagination/owner isolation、deterministic post-Human scheduling、reuse of E3、crash recovery、disconnect/send-failure recovery、historical floor-event v1 preservation、new v2 serialization/action semantics、privacy/public-projection sentinels and network-free provider tests。

P1-5F-3A implementation acceptance must prove exact floor-event v1/v2 dual parsing and projection；Human-floor input enablement；AI/other/no-floor disablement while the textarea remains editable；pending is not formal transcript；WS and REST reconnect confirmation；pure REST/WS duplicate merge without transcript gap validation；non-destructive sequence-gap reload；`UTTERANCE_REJECTED` and `ACTION_ID_CONFLICT` recovery；generic AI `INTERRUPTED` UX；exact Unicode/code-point and click-time floor binding。F3B separately owns complete page composition without reopening these semantics。

P1-5F-4 end-to-end path is：

```text
Browser
  -> Human WS command
  -> durable Human utterance
  -> release
  -> scheduler
  -> AI grant
  -> configured composition
  -> durable AI utterance/public event
  -> release
  -> scheduler
  -> Browser receives transcript
  -> reload
  -> transcript remains complete
```

Automated CI/E2E never uses real provider quota。A potential final user-run real-provider Browser smoke requires explicit instruction，approximately one Human turn and one real generation，and records only sanitized proof that the AI formal event became visible、floor progressed and reload restored transcript。Credential、rendered prompt、Private Stance、raw response and verbatim provider output never become governance evidence。

### Actual-source sufficiency and stop-condition assessment

P1-5F-1 actual-source inspection found no approved stop condition：

- `DiscussionEvent` already has session-scoped ordered sequence、nullable action causation、JSON payload and owner-session deletion semantics，so the unified public utterance fact and sequence-cursor transcript do not contradict current event semantics。
- `SessionParticipant.user_id`、the session aggregate row lock、`FloorGrant`/`FloorRelease` and reusable lifecycle release helper are sufficient for exact Human authorization and one Human utterance+release transaction without a Human table。
- `complete_generation_request(...)` already locks the session aggregate and atomically commits `COMPLETED + AiUtterance`，so P1-5F-2 can add the corresponding `DiscussionEvent` and sequence allocation to that same transaction without changing P1-5E authority。
- Existing deterministic UUID4-compatible derivation、`SessionAction` digest semantics and scheduler child facts are sufficient to define a Human post-release checkpoint from stable session/grant identity；P1-5F-2 must freeze the exact label/helper and test it before implementation acceptance。
- Actual committed source confirms the historical floor-event v1 constraints：backend and Web require non-null UUID4 `action_id` for `floor.granted` and `floor.intervention_requested`，while `floor.released` is nullable。Therefore F2/F3 must add the independently versioned v2 projection and dual-version parsing rather than alter v1；this is an expected transport compatibility delta under ADR-007，not a schema、authority or ADR contradiction。

If later actual-source implementation disproves any of those facts，requires a new durable schema fact、cannot make AI completion/event atomic、cannot recover the Human scheduler checkpoint、contradicts sequence semantics or changes P1-5E authority，the affected implementation stops for separate review。A discovered need is not permission to implement schema or architecture changes in P1-5F-1。

### P1-5F-1 validation and closeout state

- Exact scope is documentation only：`TASKS.md`、`ROADMAP.md`、`ARCHITECTURE.md`、`API.md`、`DATABASE.md`、`AGENT_BEHAVIOR.md`、`PRIVACY_AND_SAFETY.md` and this execution plan。
- No source、test、OpenAPI generated schema、package/dependency/lock、DB model/migration、provider/runtime/orchestration/floor/lifecycle、REST/WS/Web、CI、Docker/infra、prompt/seed or provider configuration change is authorized。
- Validation is limited to baseline/changed-file scope、Markdown relative links、final newlines、terminology/status、secret/static leakage、master-plan hash、`git diff --check` and staged count。No backend/Web/provider test、browser smoke or real-model call runs。
- The initial external actual-source review was `BLOCKED` by one floor-event v1 `action_id` compatibility finding。Remediation preserved historical v1 semantics and froze additive floor-event v2 without changing source、schema or ADR authority。
- The finding-only external re-review verdict is `PASS` with findings none。Reviewed bundle：`group-interview-arena-review-20260825-110115.zip`；SHA-256：`6603b1f0377aa449d3a209e475fb3afbb74f9f83c9be38f84df97918eeb1ac0c`。
- A narrow F1 command erratum was later discovered during P1-5F-2 actual-source review：the previously approved exact-floor binding is restored by requiring `floor_grant_id` in the v1 submit payload and matching it to the locked authoritative current grant。This does not reopen the unrelated F1 design or alter the independently versioned public-event contract。
- At the P1-5F-1 closeout checkpoint，P1-5F-2～F4 were `NOT_STARTED` and no commit or push was authorized。After separately approved later turns，P1-5F-1/P1-5F-2/P1-5F-3A/F3B/F4 became historical `DONE` with the recorded evidence，and parent P1-5 historically closed。Later local acceptance opened P1-5R only；the current parent state is therefore `P1-5 IN_PROGRESS / POST_CLOSEOUT_REMEDIATION_OPEN` while all F descendants remain historical `DONE`。


## P1-5R post-closeout remediation design freeze

P1-5R is the approved docs-only freeze for four findings found by real local acceptance after the historical P1-5 closeout。It does not invalidate prior completion evidence and creates no implementation plan or remediation implementation。

- R1 freezes deterministic phase-entry progression recovery and connected deadline catch-up ordering without a new scheduler authority or background loop。
- R2-A freezes loaded-session viewport ownership、transcript-local scrolling and a presentation-only new-message return affordance；R2-B preserves the F3B Interview Simulation Studio composition across `1440x900`、`900x900` and `390x844`。
- R3 freezes Prompt Version v2 selection、bounded recent public transcript context、pure Persona-to-behavior translation and three-layer network-free acceptance；real-provider checks remain separately approval-gated。
- Current state is `P1-5R IN_PROGRESS / DESIGN_FROZEN`; R1/R2-A/R2-B/R3 `NOT_STARTED`; F1/F2/Visual fidelity remediation/F3 `OPEN`; implementation plan `NOT_STARTED`。
- Frozen exact design、source-grounded feasibility、privacy exclusions、acceptance and stop conditions are in [`P1-5R_local-acceptance-remediation.md`](P1-5R_local-acceptance-remediation.md)。Future implementation order is R1 → R2-A → R2-B → R3 → final composition acceptance / independent acceptance。
## Decisions

- The user-approved config-driven model-selection specialization is recorded as a 2026-08-24 amendment to existing `ADR-014`；no separate new ADR or master-plan change is required。
- Floor Scheduler owns who; AI Runtime owns what; provider owns only model I/O.
- Prompt/model provenance is required for every historical AI utterance while raw sensitive prompt/provider data remains minimized.
- Generation Request and final Utterance are distinct identities/lifecycles.
- Provider failure is contained inside the generation boundary and cannot corrupt session/floor integrity.
- The current development provider/model is Zhipu `glm-4.7-flashx` through a thin HTTPX adapter，selected by lazy server-side configuration。The earlier `glm-4.7-flash` manual access attempt's rate-limit/availability result is not a permanent unavailability claim；neither Zhipu nor FlashX is permanent production policy。
- `provider_identifier`、actual configured `model_identifier` and model-independent invocation `configuration_version` are distinct durable provenance dimensions。A model-only change keeps `ZHIPU_CHAT_DEV_V1`；parameter-policy changes require a later version。
- Existing P1-5B provenance schema is sufficient；HTTPX is now promoted from dev-only to the single runtime dependency declaration for the implemented caller。
- P1-5E automatic orchestration is application-level and state-driven；durable current state/actions provide correctness while P1-3/P1-4/P1-5 authorities remain unchanged。
- One AI grant owns deterministic generation、utterance、release and next-schedule identities；existing `SessionAction` replay/conflict and scheduler children provide restart/concurrency convergence without an orchestration table。
- Confirmed success releases `SPEAKER_FINISHED`；confirmed terminal failure releases `INTERRUPTED` while preserving typed generation failure；uncertain/stale truth never drives stale release or scheduling。
- Release and scheduler are separate committed operations，and continuous drive has the fixed per-invocation guard `MAX_AUTOMATED_AI_TURNS_PER_DRIVE = 8`。
- Public Human text commands use WebSocket；REST owns snapshots/history；one unified `participant.utterance.created` event and owner-only sequence-cursor transcript represent Human and AI formal speech。
- Human utterance and exact-grant release are one transaction；next-speaker scheduling is a separate deterministic checkpoint；AI completion、`AiUtterance` and its public event are one transaction。
- `participant.utterance.created` remains v1；historical floor-event v1 remains unchanged；additive floor-event v2 exposes the original Human action ID only for applicable direct client causation and maps internal automatic scheduler/release/intervention action IDs to null。F2/F3 preserve and parse both floor versions；provider/runtime/prompt/failure internals remain private。
- `DiscussionEvent` is the current durable transcript implementation，but future compaction cannot remove the only transcript copy without an equivalent durable projection。

## Risks and stop conditions

- **Authority drift**：stop if runtime design needs to independently mutate phase/deadline, choose speaker or override floor decisions；reusing the existing locked P1-3 overdue reconciliation path is required lifecycle validation, not AI Runtime authority.
- **Duplicate content**：stop if retry/restart cannot prove at-most-one final utterance per logical request.
- **Untraceable output**：stop if an utterance cannot identify prompt/model/config provenance without mutable latest pointers.
- **Private leakage**：stop if rendered prompt, other participants' stance, secrets or raw provider bodies enter public/log/error surfaces.
- **Premature infrastructure**：stop before adding provider SDK、queue、Redis、RAG、billing or speculative schema without a separately approved real caller.
- **Provider contract drift**：stop if outbound provider/model/config differs from durable provenance or if an HTTPX/provider object crosses into domain/runtime results.
- **Credential leakage**：stop if the API key、Authorization header、raw response body or exception text can reach persistence、logs、traces、tests、errors or review artifacts.
- **Duplicate paid work**：stop if restart/RUNNING handling or hidden client retry can issue an untracked second real call.
- **Action replay drift**：stop if deterministic release/schedule identity cannot reconstruct or consume the original semantic payload without minting a replacement action。
- **Unsafe progression**：stop if an uncertain/stale generation or lifecycle result would require release/scheduling before exact durable revalidation。
- **Schema contradiction**：stop if P1-5E-2 actual-source implementation proves existing action/floor/request/utterance facts cannot recover a crash boundary without a new durable fact；request separate approval before migration。
- **Transcript loss**：stop before event retention/compaction can delete the only durable user-visible transcript without an equivalent projection。
- **Public causation/version drift**：stop if a new floor-event v2 projection exposes an internal automatic scheduler/release/intervention action identity，if F2/F3 break historical v1 compatibility，or if generation request/provider/model/configuration/prompt/private/failure internals reach a new REST/WS event、error or Browser projection。
- **Atomicity drift**：stop if Human utterance+release or AI completion+AiUtterance+public event cannot be committed in their frozen atomic boundaries using the locked aggregate。

## Progress

- P1-5A：completed；docs-only AI Runtime Architecture Freeze；validation required before delivery；no blocker。
- P1-5B：completed；provider-neutral persistence foundation；all required gates PASS；no provider/runtime caller。
- P1-5C：completed；deterministic runtime contract/vertical slice and PostgreSQL orchestration gates PASS；no real provider or transport。
- P1-5D：`DONE`；design freeze、implementation、findings remediation、config-driven model patch、both actual-source reviews and final user-run sanitized real-provider acceptance smoke completed without a Codex real-model call or sensitive-data recording。
- P1-5E：`DONE`；P1-5E-1 design freeze、P1-5E-2 single-turn kernel and P1-5E-3 bounded continuous drive/configured composition are `DONE` after required reviews and the sanitized composition smoke。
- P1-5F：historical `DONE`；
- P1-5F-1：`DONE`；docs-only public REST/WS/Browser contract freeze accepted after finding remediation and finding-only external re-review `PASS`；
  - P1-5F-2：`DONE`；initial implementation review `BLOCKED` on three findings，all remediated；finding-only external re-review `PASS`，findings none；reviewed remediation bundle `group-interview-arena-review-20260825-150754.zip` / SHA-256 `b9553cbe488707d5fd87598b70e48e1fabdf55a0ae6d3dab367b830267d61edd`；
  - P1-5F-3A：`DONE` with `DESIGN_FROZEN / IMPLEMENTATION_COMPLETE / ACTUAL_SOURCE_REVIEW_PASS / COMMIT_PUSH_COMPLETE / CI_PASS / INDEPENDENT_FINAL_ACCEPTANCE_PASS / FINDINGS_NONE_OPEN`；accepted target `30446af520e55977a7c7a4839e00ab1a0a94d44e`；GitHub Actions run `32945590023` all four jobs `PASS`；
  - P1-5F-3：`DONE`；P1-5F-3A and P1-5F-3B are both `DONE`；
  - P1-5F-3B：`DONE` with `DESIGN_FROZEN / IMPLEMENTATION_PLAN_FROZEN / IMPLEMENTATION_COMPLETE / ACTUAL_SOURCE_IMPLEMENTATION_REVIEW_PASS / COMMIT_PUSH_COMPLETE / CI_PASS / F4_COMPOSITION_ACCEPTANCE_PASS / FINDINGS_NONE_OPEN`；accepted implementation baseline `5efe1346532b95b7fabdd521015fd9f8199a457f`；GitHub Actions run `33044682226` `SUCCESS`；
  - P1-5F-4：`DONE`；initial acceptance `BLOCKED` on `F4-ACC-001`；finding-only remediation actual-source review `PASS`；accepted commit `af33d89baa0355ae1ee5174a2ef8cfb5e7b14554`；GitHub Actions run `33050532295` `SUCCESS`；independent final acceptance `PASS`；findings `NONE`；`F4-ACC-001 CLOSED`；no real provider/model call。
- P1-5R：`IN_PROGRESS / DESIGN_FROZEN`；R1/R2-A/R2-B/R3 `NOT_STARTED`；implementation plan `NOT_STARTED`。
- P1-5：`IN_PROGRESS / POST_CLOSEOUT_REMEDIATION_OPEN`；historical P1-5A～P1-5F statuses remain `DONE`；P1 remains `IN_PROGRESS`。
