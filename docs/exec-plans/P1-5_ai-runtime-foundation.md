# P1-5 AI Runtime Foundation Execution Plan

Status: `P1 IN_PROGRESS`; `P1-5 IN_PROGRESS`; `P1-5A completed`; later P1-5 implementation subphases `NOT_STARTED / awaiting explicit approval`

Target version: `V0.1 Internal Validation`

Product baseline: [`PROJECT_MASTER_PLAN.md`](../PROJECT_MASTER_PLAN.md)

Accepted decisions: [`D-003`](../DECISIONS.md#2-已确认产品决策索引), [`D-007`](../DECISIONS.md#2-已确认产品决策索引), [`D-008`](../DECISIONS.md#2-已确认产品决策索引), [`D-013`](../DECISIONS.md#2-已确认产品决策索引), [`ADR-006`](../DECISIONS.md#adr-006--rest-与-websocket-通信边界), [`ADR-007`](../DECISIONS.md#adr-007--api-契约生成策略), [`ADR-009`](../DECISIONS.md#adr-009--独立后台任务队列延后), [`ADR-011`](../DECISIONS.md#adr-011--轻量领域导向混合模块架构), [`ADR-012`](../DECISIONS.md#adr-012--分阶段测试与质量工具策略), [`ADR-013`](../DECISIONS.md#adr-013--配置错误与结构化日志基线), [`ADR-014`](../DECISIONS.md#adr-014--provider-neutral-ai-与自定义讨论编排)

P1-5A baseline: clean committed `main` at `5397cd2b25f36c6a9fbd666b759261091c36a8c0`, equal to `origin/main`; [`PROJECT_MASTER_PLAN.md`](../PROJECT_MASTER_PLAN.md) SHA-256 `2388A9660320406CB35D5354126AD71C6849A98DB7C4A356796CA951BF372F26`

## Goal

冻结 AI Runtime Foundation 的架构边界，使未来实现能够在既有 `floor.granted` 之后为获准 AI participant 生成可追踪、可重试且不破坏 session integrity 的 utterance，同时保持 P1-3 lifecycle authority、P1-4 floor authority、题目/Persona 私有信息隔离和 provider neutrality。

P1-5A 是 docs-only architecture freeze。它不实现 LLM、provider adapter、prompt runtime、utterance persistence、API/Realtime contract、schema、migration、dependency、test 或 CI。

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

具体表名、columns、event vocabulary、streaming chunks 和 Browser projection Deferred 到后续获批实施设计；P1-5A 只冻结 lifecycle/invariants。

## Frozen failure and retry boundary

适用 failure classes：timeout、provider unavailable、rate limit、partial generation、invalid/unsafe output 和 caller cancellation/stale grant。

共同原则：

- 重试必须有界、按 typed class 决定，并保持同一 logical generation identity；provider 自带 retry 不能绕过 application idempotency。
- 每次 attempt 在提交结果前重新验证 exact session、phase、participant 和 current grant；phase/grant 已变化时丢弃 late result，不持久化 utterance。
- timeout/unavailable/rate-limit 可按未来获批 policy 重试或降级；provider fallback 仍必须记录实际 provider/model/config provenance。
- partial generation 默认不是 final utterance。除非未来明确冻结 partial-commit contract，否则 partial output 必须丢弃或作为非公开诊断最小化处理。
- failure 不改变 phase、不延长/缩短 deadline、不转移 floor、不修改 scheduler decision、不触发 scoring。
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

- LLM implementation and real model calls；
- provider SDK/interface/adapter/factory/routing/fallback implementation；
- prompt orchestration engine、prompt storage/schema/rendering；
- generation request / attempt / utterance schema and migration；
- runtime/API/WebSocket/Web implementation and streaming；
- memory、RAG、embedding/vector store；
- scoring、evidence extraction、report generation；
- voice、ASR、TTS、audio interruption；
- emotion、face、camera or video detection；
- Redis、task queue、distributed worker；
- billing、quota、payment and multi-tenant。

## Later implementation gates

Any later P1-5 implementation subphase requires separate explicit approval and an updated decomposition before code changes. At minimum it must define:

- exact schema/migration and historical deletion semantics；
- provider-neutral request/result/error contract with a real caller；
- Prompt Version storage and rendering authority；
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

## Decisions

- No new Accepted or Proposed ADR is required. P1-5A specializes total-plan §22 and existing `ADR-014` within the explicitly approved task without selecting a provider or changing product direction.
- Floor Scheduler owns who; AI Runtime owns what; provider owns only model I/O.
- Prompt/model provenance is required for every historical AI utterance while raw sensitive prompt/provider data remains minimized.
- Generation Request and final Utterance are distinct identities/lifecycles.
- Provider failure is contained inside the generation boundary and cannot corrupt session/floor integrity.

## Risks and stop conditions

- **Authority drift**：stop if runtime design needs to mutate phase/deadline, choose speaker or override floor decisions.
- **Duplicate content**：stop if retry/restart cannot prove at-most-one final utterance per logical request.
- **Untraceable output**：stop if an utterance cannot identify prompt/model/config provenance without mutable latest pointers.
- **Private leakage**：stop if rendered prompt, other participants' stance, secrets or raw provider bodies enter public/log/error surfaces.
- **Premature infrastructure**：stop before adding provider SDK、queue、Redis、RAG、billing or speculative schema without a separately approved real caller.

## Progress

- P1-5A：completed；docs-only AI Runtime Architecture Freeze；validation required before delivery；no blocker。
- Later P1-5 implementation：not started；requires separate explicit approval。

