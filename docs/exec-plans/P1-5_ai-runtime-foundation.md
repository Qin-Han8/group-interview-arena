# P1-5 AI Runtime Foundation Execution Plan

Status: `P1 IN_PROGRESS`; `P1-5 IN_PROGRESS`; `P1-5A completed`; `P1-5B completed`; `P1-5C completed`; `P1-5D/P1-5E/P1-5F NOT_STARTED`

Target version: `V0.1 Internal Validation`

Product baseline: [`PROJECT_MASTER_PLAN.md`](../PROJECT_MASTER_PLAN.md)

Accepted decisions: [`D-003`](../DECISIONS.md#2-已确认产品决策索引), [`D-007`](../DECISIONS.md#2-已确认产品决策索引), [`D-008`](../DECISIONS.md#2-已确认产品决策索引), [`D-013`](../DECISIONS.md#2-已确认产品决策索引), [`ADR-006`](../DECISIONS.md#adr-006--rest-与-websocket-通信边界), [`ADR-007`](../DECISIONS.md#adr-007--api-契约生成策略), [`ADR-009`](../DECISIONS.md#adr-009--独立后台任务队列延后), [`ADR-011`](../DECISIONS.md#adr-011--轻量领域导向混合模块架构), [`ADR-012`](../DECISIONS.md#adr-012--分阶段测试与质量工具策略), [`ADR-013`](../DECISIONS.md#adr-013--配置错误与结构化日志基线), [`ADR-014`](../DECISIONS.md#adr-014--provider-neutral-ai-与自定义讨论编排)

P1-5A baseline: clean committed `main` at `5397cd2b25f36c6a9fbd666b759261091c36a8c0`, equal to `origin/main`; [`PROJECT_MASTER_PLAN.md`](../PROJECT_MASTER_PLAN.md) SHA-256 `2388A9660320406CB35D5354126AD71C6849A98DB7C4A356796CA951BF372F26`

## Goal

冻结 AI Runtime Foundation 的架构边界，使未来实现能够在既有 `floor.granted` 之后为获准 AI participant 生成可追踪、可重试且不破坏 session integrity 的 utterance，同时保持 P1-3 lifecycle authority、P1-4 floor authority、题目/Persona 私有信息隔离和 provider neutrality。

P1-5A 是 docs-only architecture freeze。它不实现 LLM、provider adapter、prompt runtime、utterance persistence、API/Realtime contract、schema、migration、dependency、test 或 CI。

P1-5B 是 separately approved persistence foundation。它只实现 immutable Prompt Version、provider-neutral Generation Request lifecycle、successful final AI Utterance relation and locked transactional domain services；不接入真实 provider、不自动生成、不增加 API/Realtime/Web。

P1-5C 是 separately approved deterministic runtime vertical slice。它在不调用真实 LLM、不增加 schema/API/Realtime/Web/dependency 的前提下，实现 exact Prompt Version rendering、single-participant authorized context assembly、typed immutable generation input/result、deterministic local harness 和 application orchestration，并复用 P1-5B lifecycle 原子提交唯一 final AI Utterance。

后续拆分固定为：

- `P1-5A — AI Runtime Architecture Freeze`：`DONE`；
- `P1-5B — AI Runtime Persistence Foundation`：`DONE`；
- `P1-5C — Runtime Contract & Deterministic Generation Vertical Slice`：`DONE`；
- `P1-5D — First Real Provider Integration`：`NOT_STARTED`；
- `P1-5E — Automatic AI Runtime Orchestration`：`NOT_STARTED`；
- `P1-5F — Realtime/Web Integration + Independent Acceptance`：`NOT_STARTED`。

P1-5D～F 不是本轮授权范围，仍需新的 explicit user approval。

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

P1-5A 只冻结 lifecycle/invariants。P1-5B 现将 generation attempt 的 durable states 具体化为 `REQUESTED / RUNNING / COMPLETED / FAILED`：`RUNNING` 表示 caller 已开始 attempt；`COMPLETED` 只与同一 transaction 中唯一 formal utterance 一起成立。Conceptual `generated -> persisted` 不作为可崩溃分离的数据库状态，避免 raw/partial output 在正式 utterance 前成为 durable group fact。Event vocabulary、streaming chunks 和 Browser projection 继续 Deferred。

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
- audit trace from utterance to prompt/model/config；
- prompt iteration and version comparison。

P1-5A 不提前实现 billing、quota、payment、multi-tenant、enterprise account provisioning、provider marketplace 或成本结算。成本统计是 invocation observability/provenance 能力，不是商业计费系统。

## Explicit deferred scope

Implemented in P1-5C current state:

- closed deterministic exact Prompt Version rendering；
- authorized context assembly for the exact session-bound Question Version and only the granted AI participant's Assignment/Persona/Private Stance；
- deterministic internal runtime/application caller with a network-free local executor harness。

Still Deferred:

- real-provider prompt/model execution、LLM implementation and real model calls；
- provider SDK/interface/adapter/factory/routing/fallback implementation；
- production prompt orchestration beyond the closed P1-5C renderer and internal prompt-variable persistence；
- additional provider-attempt/fallback hierarchy beyond the current one-request/one-attempt identity；
- automatic floor-triggered generation、transport/API/WebSocket/Web and streaming；
- memory、RAG、embedding/vector store；
- scoring、evidence extraction、report generation；
- voice、ASR、TTS、audio interruption；
- emotion、face、camera or video detection；
- Redis、task queue、distributed worker；
- billing、quota、payment and multi-tenant。

## Later implementation gates

Any P1-5D or later provider/automatic/transport subphase requires separate explicit approval and an updated decomposition before code changes. At minimum it must define:

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

## Decisions

- No new Accepted or Proposed ADR is required. P1-5A specializes total-plan §22 and existing `ADR-014` within the explicitly approved task without selecting a provider or changing product direction.
- Floor Scheduler owns who; AI Runtime owns what; provider owns only model I/O.
- Prompt/model provenance is required for every historical AI utterance while raw sensitive prompt/provider data remains minimized.
- Generation Request and final Utterance are distinct identities/lifecycles.
- Provider failure is contained inside the generation boundary and cannot corrupt session/floor integrity.

## Risks and stop conditions

- **Authority drift**：stop if runtime design needs to independently mutate phase/deadline, choose speaker or override floor decisions；reusing the existing locked P1-3 overdue reconciliation path is required lifecycle validation, not AI Runtime authority.
- **Duplicate content**：stop if retry/restart cannot prove at-most-one final utterance per logical request.
- **Untraceable output**：stop if an utterance cannot identify prompt/model/config provenance without mutable latest pointers.
- **Private leakage**：stop if rendered prompt, other participants' stance, secrets or raw provider bodies enter public/log/error surfaces.
- **Premature infrastructure**：stop before adding provider SDK、queue、Redis、RAG、billing or speculative schema without a separately approved real caller.

## Progress

- P1-5A：completed；docs-only AI Runtime Architecture Freeze；validation required before delivery；no blocker。
- P1-5B：completed；provider-neutral persistence foundation；all required gates PASS；no provider/runtime caller。
- P1-5C：completed；deterministic runtime contract/vertical slice and PostgreSQL orchestration gates PASS；no real provider or transport。
- P1-5D/P1-5E/P1-5F：not started；require separate explicit approval。
