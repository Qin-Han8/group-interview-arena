# 项目路线图

- Status: Active baseline
- Most recently completed development phase: P0 — `DONE`
- Current completed checkpoint: P1-7B — `DONE / ACTUAL_SOURCE_REVIEW_PASS`; P1-7A — `DONE / DESIGN_SCOPE_FROZEN / ACTUAL_SOURCE_REVIEW_PASS`; P1-7 — `IN_PROGRESS`; P1-6 — `DONE / CLOSED`; open findings — `NONE`
- P0-7 final outcome: initial `BLOCKED`; two documentation findings remediated; finding-only independent recheck `PASS`; P1 readiness `READY`
- Current phase: P1 — `IN_PROGRESS`
- Current governance checkpoint: P1-7B is `DONE / ACTUAL_SOURCE_REVIEW_PASS`; `P1-7B-F001 CLOSED`; open findings `NONE`
- Latest completed implementation review: P1-7B initial review and finding-only re-review are `PASS`; material findings/new blockers/open findings `NONE`
- Current task gate: P1-6 — `DONE / CLOSED`; P1-7 — `IN_PROGRESS`; P1-7A — `DONE / DESIGN_SCOPE_FROZEN / ACTUAL_SOURCE_REVIEW_PASS`; P1-7B — `DONE / ACTUAL_SOURCE_REVIEW_PASS`; P1-7C — `IMPLEMENTED / AWAITING_ACTUAL_SOURCE_REVIEW`; P1-7D/P1-7E/P1-8 — `NOT_STARTED`; P1 remains `IN_PROGRESS`
- P0 status: `DONE`; P0-1 through P0-7 completed
- Target product version: V0.1 — Internal Validation
- Source: [`PROJECT_MASTER_PLAN.md`](PROJECT_MASTER_PLAN.md) §30–31

## 1. 两套并行概念

本项目严格区分：

- `P0～P6`：研发推进阶段，描述按什么顺序建立能力；
- `V0.1 / V0.5 / V1.0`：产品交付版本，描述某个可验证版本包含什么。

阶段不是版本，P0-x/P1-x 也不是新增产品版本。P0 已完成不代表 V0.1 的全部业务能力已经实现；用户已明确批准进入 P1，P1 保持 `IN_PROGRESS`。P1-5A～P1-5F retain their recorded review、commit/push、CI and acceptance evidence；P1-5F-4 retains `F4-ACC-001 CLOSED` and made no real provider/model call in its accepted path。P1-5R legitimately reached `PASS / CLOSED` after R1～R3、Final Composition Acceptance and Independent Acceptance completed，and that committed closeout remains historical evidence。A later explicitly authorized post-closeout real-provider smoke exposed P1-5R-POST-001：cancellation after a generation request reached `RUNNING` could orphan the request and AI floor。The network-free remediation and its review finding both passed actual-source review，accepted commit `3b09d20a704c0fd3ff473ccb79311065b7e70408` has exact CI run `33257343273` green，and P1-5R-POST-REV-001、P1-5R-POST-001 and P1-5R are now `CLOSED` while parent P1-5 is `DONE` with open findings `NONE`。Formal R3.8 remains `NOT_EXECUTED / REQUIRES_SEPARATE_EXPLICIT_USER_AUTHORIZATION`；no further real-provider call occurred。

## 2. 开发阶段

| 阶段 | 目标摘要 | 当前状态 |
|---|---|---|
| P0 项目基础 | 仓库、规范、环境、认证、数据库基础、监控日志和决策记录 | DONE |
| P1 文字版讨论闭环 | 题目模型、角色参数、状态机、调度、记忆、文字模拟和基础报告 | IN_PROGRESS |
| P2 语音与真实交互 | 麦克风、ASR、TTS、打断恢复、延迟监控和音频生命周期 | NOT_STARTED |
| P3 评分与专项训练 | 客观指标、证据、六维评分、报告、专项训练和用户反馈 | NOT_STARTED |
| P4 商业化 | 商品、订单、权益、支付、免费限制、故障返还和运营配置 | NOT_STARTED |
| P5 公开测试 | 邀请测试、质量监控、人工校准、定价实验和内容补充 | NOT_STARTED |
| P6 V1.0 发布 | 压力模式、冲刺计划、成长中心、丰富角色和正式获客 | NOT_STARTED |

各阶段完整含义以总纲第 31 节为准。本表不替代总纲，也不把未批准的实现细节加入阶段范围。

## 3. P0 执行拆分

以下 P0-x 是为单人 + Codex 协作建立的执行拆分，不是总纲新增的产品版本，也不改变总纲 P0 的范围。

| 子任务 | 目标 | 状态 |
|---|---|---|
| P0-1 仓库与文档治理 | 建立 Source of Truth、长期上下文、任务和决策治理 | DONE |
| P0-2 技术架构决策 | 确认技术选择、模块边界和必要 ADR | DONE |
| P0-3 前后端项目骨架 | 创建最小 Web/API skeleton、工具链、健康检查、基础配置与日志、基础测试及 Web → API 连通；不包含数据库 | DONE |
| P0-4 数据库与迁移基础 | 使用 Docker Compose、PostgreSQL 18.x、SQLAlchemy 2.x 和 Alembic 建立数据与 migration 基础及数据库集成验证 | DONE |
| P0-5 最小身份边界 | 建立 V0.1 username/password、稳定 user_id 与服务端 Cookie session 身份边界，不做完整公开账号产品 | DONE |
| P0-6 CI、日志与基础可观测性 | 建立自动检查、日志和基础监控能力 | DONE — P0-6A～P0-6E completed；cross-layer closeout 与 actual-source review PASS |
| P0-7 P0 独立验收 | 独立确认 P0 是否满足进入 P1 的条件 | DONE — initial BLOCKED；2 documentation findings remediated；finding-only recheck PASS；P1 READY |

任务细节及验收条件见 [`TASKS.md`](TASKS.md)。P0-1～P0-7 均已完成，P0 整体已转为 `DONE`。P0-7 independent final acceptance initial verdict 为 `BLOCKED`，两个 documentation findings 已 remediation，finding-only independent recheck `PASS`，new blockers none，P1 readiness `READY`；其后用户已明确批准进入 P1。

P0-5 固定采用五阶段执行：P0-5A identity preflight（completed）、P0-5B identity persistence/migration/security primitives（completed）、P0-5C backend auth runtime/API（completed）、P0-5D Web/CORS/CSRF cross-layer validation（completed）、P0-5E independent final review（completed；PASS after findings remediation and independent recheck）。

P0-6 固定采用五阶段执行：P0-6A preflight/scope freeze/execution plan（completed；actual-source final review `PASS`）、P0-6B GitHub Actions CI baseline（completed；remote CI `PASS`）、P0-6C structured logging hardening（completed；actual-source review、finding remediation/re-review 与 remote CI `PASS`）、P0-6D OpenTelemetry tracing foundation（completed；actual-source review、findings remediation/re-review 与 remote CI run #6 `PASS`）、P0-6E cross-layer validation/P0-6 closeout（completed；final gates 与 7-file docs-only actual-source review `PASS`，无 blocker）。P0-7 独立 P0 final acceptance 已在其后完成，不并入 P0-6E。详细计划见 [`exec-plans/P0-6_ci-observability.md`](exec-plans/P0-6_ci-observability.md)。

P0-2 已 Accepted PostgreSQL、SQLAlchemy 2.x 和 Alembic；P0-4 实施基线为 PostgreSQL 18.x，且 Redis 不进入默认 Compose。完整决策和重新评估条件见 [`DECISIONS.md`](DECISIONS.md)。

## 4. P1 当前执行拆分

P1 已正式启动。`P1-1 — Discussion session foundation` 已建立 session create/snapshot、versioned WebSocket、durable action idempotency、monotonic event sequence 和 reconnect 基础；它不等于 P1 全部文字讨论闭环。

- `P1-1A — Preflight / scope freeze / execution plan`：completed；
- `P1-1B — Session persistence + migration foundation`：completed；
- `P1-1C — Backend REST + WebSocket vertical slice`：completed；
- `P1-1D — Web realtime caller + reconnect cross-layer validation`：completed；
- `P1-1E — Independent final review / P1-1 closeout`：completed；independent verdict `PASS`；findings none。

P1-1A 完成 docs-only plan/scope freeze；P1-1B 完成三表 ORM/migration 与真实 PostgreSQL persistence foundation；P1-1C 完成 authenticated REST create/snapshot、versioned WS v1、durable action idempotency、locked-row sequence allocation、ordered catch-up/reconnect 与安全 realtime errors/logging；P1-1D 完成最小 Web realtime caller、strict sequence/gap recovery、stable action retry 与真实 PostgreSQL Chromium cross-layer validation；P1-1E 从 committed source 独立复核 migration、transaction、auth、WS、browser、privacy 和真实 Chromium → Uvicorn → PostgreSQL 路径，verdict `PASS`、findings none。P1-1 现为 `DONE`。详细计划见 [`exec-plans/P1-1_discussion-session-foundation.md`](exec-plans/P1-1_discussion-session-foundation.md)。

`P1-2 — Question & Persona foundation` 固定为四阶段：

- `P1-2A — Design freeze`：completed；docs-only；
- `P1-2B — Persistence + Domain + Seed foundation`：completed；
- `P1-2C — API + Session integration + minimal Web vertical slice`：completed；
- `P1-2D — Independent acceptance + closeout`：completed；independent verdict `PASS`。

P1-2A 已冻结 stable Question Template、immutable published Question Version、stable-behavior Persona Template、version-specific Assignment/Private Stance、session version binding、private non-disclosure、numeric validation、retirement/deletion 和历史追溯边界，并确认 V0.1 四种基础角色。P1-2B 已实现精确五表 persistence、linear migration、strict closed domain validation、四 Persona deterministic seed 和一个明确标记的 internal-validation bundle。P1-2C 已实现 authenticated safe question reads、exact immutable version-bound session creation、authoritative snapshot 与最小 Web 选题/题面 vertical slice。P1-2D 从 clean committed source 独立复现 PostgreSQL/Chromium/full gates，verdict `PASS`、无 blocker/material finding。P1-2 现为 `DONE`；P1 保持 `IN_PROGRESS`，其后的 P1-3A 已完成。完整 scope/gates 见 [`exec-plans/P1-2_question-persona-foundation.md`](exec-plans/P1-2_question-persona-foundation.md)。Participant/utterance、调度/记忆、LLM/provider 和基础报告继续留给后续获批任务。

`P1-3 — Session state machine` 固定为四阶段：

- `P1-3A — Design freeze`：completed；docs-only；
- `P1-3B — Backend state machine + durable phase foundation`：completed；
- `P1-3C — Realtime/Web complete phase flow`：completed；
- `P1-3D — Independent acceptance + closeout`：completed；independent verdict `PASS`。

P1-3A 已冻结 V0.1 单向 path、合法 abort、server-authoritative transition matrix、server-owned immutable duration plan、durable phase start/deadline、deadline-first concurrent reconciliation、P1-1 action/sequence/transaction/commit-before-send 复用、historical v1 + current v2 formal state events，以及 Browser 只投影 state/timing/sequence 的边界。P1-3B 已实现 backend/domain/persistence/API/realtime-parser foundation、linear Alembic timing migration、server-owned closed duration plan、transactional overdue reconciliation、`session.start` 与 generalized v2 `session.state_changed` compatibility。P1-3C 已实现 in-process deadline recovery、startup durable-deadline reconciliation、connected WS catch-up/push、Browser authoritative phase/deadline projection 和真实 PostgreSQL Chromium complete-flow validation；P1-3D 从 clean committed source 独立复核全部 acceptance gates，verdict `PASS`、无 unresolved Critical/High/Medium finding，P1-3 已为 `DONE`。总纲长期 `DEVICE_CHECK`、pause/failure/partial/report states 继续 Deferred；P1-4A floor-control design freeze 与 P1-4B participant/floor persistence/domain foundation 已完成，scheduler ranking runtime、AI/LLM、utterance、memory、report/scoring、Redis/queue 和 voice 均未实现。完整 P1-3 scope/gates 见 [`exec-plans/P1-3_session-state-machine.md`](exec-plans/P1-3_session-state-machine.md)。

`P1-4 — Floor control / speaker scheduling` 固定为五阶段：

- `P1-4A — Floor control design freeze`：completed；docs-only；
- `P1-4B — Scheduling persistence + domain foundation`：completed；
- `P1-4C — Deterministic scheduler engine`：completed；
- `P1-4D — Realtime/Web floor experience`：completed；
- `P1-4E — Independent acceptance + closeout`：completed；final independent verdict `PASS`。

P1-4A 已冻结 phase lifecycle 与 within-phase floor authority 分离、single current owner、AI/human/system participant compatibility、deterministic policy、最小 floor facts 与 non-disclosure。P1-4B 已实现 generalized persistence、single-current-grant invariant、immutable audit history、idempotency/concurrency 与 lifecycle protection。P1-4C 已实现 pure deterministic scheduler、fairness/monopoly/phase-aware ordering、stable tie-break、explainable intervention 和 locked decision → fact orchestration。P1-4D 已在既有 REST snapshot + single ordered WS channel 上实现 allowlisted floor projection、strict Web parser/current-owner lifecycle UI、duplicate/gap/stale-generation recovery，以及真实 PostgreSQL Chromium reload/API-restart flow；没有 Browser scheduler authority 或新 realtime protocol。P1-4E 在唯一 documentation finding 修复后完成 full independent recheck，final verdict `PASS`。Scheduler 只决定谁说，未来 LLM/provider 只决定获准 AI 说什么。P1-4 已为 `DONE`；其后 P1-5A 已按下述边界完成。完整 P1-4 scope/gates 见 [`exec-plans/P1-4_floor-control.md`](exec-plans/P1-4_floor-control.md)。

`P1-5 — AI Runtime Foundation` is `DONE` after the P1-5R-POST-001 remediation review passed and exact accepted-commit CI completed successfully；the historical P1-5A～P1-5R closeout evidence remains unchanged。Its approved decomposition is：

- `P1-5A — AI Runtime Architecture Freeze`：completed；docs-only；
- `P1-5B — AI Runtime Persistence Foundation`：completed；provider-neutral persistence only；
- `P1-5C — Runtime Contract & Deterministic Generation Vertical Slice`：completed；deterministic local runtime only；
- `P1-5D — First Real Provider Integration`：completed；actual-source reviews and final user-run sanitized real-provider acceptance smoke `PASS`；
- `P1-5E — Automatic AI Runtime Orchestration`：completed；
- `P1-5E-1 — Automatic AI Runtime Orchestration Design Freeze`：completed；docs-only actual-source review `PASS`；findings none；
- `P1-5E-2 — Single AI Turn Orchestration Kernel`：completed；initial actual-source review `BLOCKED` on 3 findings，all remediated；remediation actual-source re-review `PASS`，findings none；
- `P1-5E-3 — Continuous AI Drive + Composition Acceptance`：completed；implementation actual-source review `PASS`，findings none；sanitized real-provider composition smoke `PASS`；
- `P1-5F — Realtime/Web Integration + Independent Acceptance`：`DONE`；
- `P1-5F-1 — Realtime/Public Contract Design Freeze`：`DONE`；docs-only contract freeze accepted after finding remediation and finding-only re-review `PASS`；
- `P1-5F-2 — Backend Text Discussion Transport`：`DONE`；initial implementation review `BLOCKED` on three findings，all remediated；finding-only external re-review `PASS`，findings none；
- `P1-5F-3 — Web Discussion Experience`：`DONE`；
  - `P1-5F-3A — Web Discussion Functional Closure`：`DONE`；
  - `P1-5F-3B — Complete Discussion Page Composition`：`DONE`；`DESIGN_FROZEN / IMPLEMENTATION_PLAN_FROZEN / IMPLEMENTATION_COMPLETE / ACTUAL_SOURCE_IMPLEMENTATION_REVIEW_PASS / COMMIT_PUSH_COMPLETE / CI_PASS / F4_COMPOSITION_ACCEPTANCE_PASS / FINDINGS_NONE_OPEN`；
- `P1-5F-4 — Composition E2E + Independent Acceptance`：`DONE`；initial acceptance `BLOCKED` on `F4-ACC-001`；finding-only remediation actual-source review `PASS`；accepted commit `af33d89baa0355ae1ee5174a2ef8cfb5e7b14554`；CI `33050532295` `SUCCESS`；independent final acceptance `PASS`；findings `NONE`；`F4-ACC-001 CLOSED`；network-free fake-provider composition only。
- `P1-5R — Local Acceptance Remediation`：`CLOSED`；the previous Independent Acceptance and closeout remain historical `PASS / CLOSED` evidence；R1/R2-A/R2-B/R3 remain `DONE`；F1/F2/visual fidelity remediation/F3 remain `CLOSED`。
- `P1-5R-POST-001 — Recover cancelled in-flight AI generation`：`CLOSED`；remediation actual-source review `PASS`；accepted commit `3b09d20a704c0fd3ff473ccb79311065b7e70408`；exact CI run `33257343273` `completed / success` with all four required jobs green；later post-closeout real-provider smoke discovery remains historical evidence；no further real-provider call。
- `P1-5R-POST-REV-001 — Real WebSocket teardown composition proof`：`CLOSED`；network-free Browser reload proves durable `RUNNING → FAILED / INTERNAL_ERROR → FAILED_REPLAY → INTERRUPTED` recovery，continued scheduling and no retry/utterance/release duplication；open findings `NONE`。

P1-5A 冻结 Scheduler 决定 who、AI Runtime 决定 what、provider 只负责 model I/O。P1-5B～P1-5F 的 historical implementation and acceptance evidence remains unchanged，including F3A/F3B/F4 `DONE` and `F4-ACC-001 CLOSED`。P1-5R R1、R2-A、R2-B and R3 remain accepted and `DONE`，with F1、F2、visual fidelity remediation and F3 `CLOSED`；Final Composition Acceptance、Independent Acceptance and the committed P1-5R/P1-5 closeout remain historical `PASS / CLOSED` evidence。The later post-closeout real-provider smoke exposed P1-5R-POST-001；the remediation and P1-5R-POST-REV-001 actual-source review passed，accepted commit `3b09d20a704c0fd3ff473ccb79311065b7e70408` and exact CI run `33257343273` are green，so P1-5R-POST-REV-001、P1-5R-POST-001 and P1-5R are `CLOSED`，parent P1-5 is `DONE`，and open findings are `NONE`。Formal R3.8 remains `NOT_EXECUTED / REQUIRES_SEPARATE_EXPLICIT_USER_AUTHORIZATION`；no further real-provider call occurred。完整边界见 [`exec-plans/P1-5_ai-runtime-foundation.md`](exec-plans/P1-5_ai-runtime-foundation.md)、[`exec-plans/P1-5R_local-acceptance-remediation.md`](exec-plans/P1-5R_local-acceptance-remediation.md) and [`exec-plans/P1-5R_local-acceptance-remediation-implementation.md`](exec-plans/P1-5R_local-acceptance-remediation-implementation.md)。

`P1-6 — Complete Text Simulation` is `DONE / CLOSED` with this frozen split:

- `P1-6A — Scope Reconciliation + Commercial-Readiness Architecture Freeze`: `DONE / DESIGN_SCOPE_FROZEN / ACTUAL_SOURCE_REVIEW_PASS`; strict docs-only; finding-only external actual-source re-review `PASS`; `P16A-REV-001 CLOSED`; `P16A-REV-002 CLOSED`; open findings `NONE`;
- `P1-6B — Structured Discussion Memory Gap Closure / Production Implementation`: `DONE / DESIGN_SCOPE_FROZEN / IMPLEMENTATION_COMPLETE / ACTUAL_SOURCE_REVIEW_PASS`; implementation finding-only re-review `PASS`; all implementation findings closed; open findings `NONE`;
- `P1-6C — Full Text Simulation Composition`: Design Freeze `DONE / DESIGN_SCOPE_FROZEN / ACTUAL_SOURCE_REVIEW_PASS`; production implementation `DONE / DESIGN_SCOPE_FROZEN / IMPLEMENTATION_COMPLETE / ACTUAL_SOURCE_REVIEW_PASS`; implementation findings `NONE`; production source changes `NONE`;
- `P1-6D — Recovery + Three-AI End-to-End Validation`: `DONE / DESIGN_SCOPE_FROZEN / IMPLEMENTATION_COMPLETE / ACTUAL_SOURCE_REVIEW_PASS`; D2-D1 through D2-D4 `PASS`; `P16D-REV-001 CLOSED`; `P16D-REV-002 CLOSED`; `P16D-D2D4-REV-001 CLOSED`; new findings `NONE`; open findings `NONE`; accepted commit `6dcce5e961d6aa7b460243dbd6407e17c2478aa2`; CI `GREEN`;
- `P1-6E — P1-6 Independent Acceptance + Closeout`: `DONE / POST_STOP_CLOSEOUT_REMEDIATION_PASS`; all findings closed; accepted remediation commit `3aa1a049728314f1fbec65367b57b8442bb49670`; exact CI run `34336016724` green.

P1-6A confirmed that provider/runtime/orchestration, public Human/AI transport, REST/WS recovery, Web composition and phase closure were inherited rather than new implementation work. Its then-remaining implementation gap was versioned, traceable, stale-detectable and rebuildable structured public discussion memory plus bounded memory-backed invocation context. Source ordering/cursor/revision/staleness/idempotency/provenance and inference-free structural fields had to be deterministic; semantic derivation could use a bounded, public-only, versioned project-owned boundary while remaining source- and derivation-version-traceable, safely rebuildable and fake-provider testable. Authoritative raw public history remained the only evidence authority, and semantic memory never replaced evidence. P1-6A created no schema/table; P1-6D later composed one explicit Human + 3 distinct AI network-free recovery path. At that P1-6A checkpoint, P1-7/P1-8 were `NOT_STARTED`; current status is recorded below. Exact P1-6 boundaries are frozen in [`exec-plans/P1-6_complete-text-simulation.md`](exec-plans/P1-6_complete-text-simulation.md).

P1-6B Design Freeze selects Evidence Ledger + Materialized Memory + Patch Journal + Lazy Semantic Compaction: the model proposes public-only typed patches, strict validation precedes a deterministic reducer, current state and immutable patch history have separate persistence responsibilities, and AI consumes bounded structured memory plus an uncompacted raw public tail. Finding-only remediation froze distinct `projection_version` replay semantics, persisted closed V2 candidate Working Context provenance and an explicit `PublicMemoryQuestionContext` allowlist with evaluator/hidden-field sentinels. The design remains session-local, optimistic-CAS safe, keeps model I/O outside transactions, preserves candidate-private isolation and existing public contracts, and defers workers/Redis/vector/graph/normalized-item infrastructure until explicit measured triggers. Finding-only external actual-source re-review verdict is `PASS` against `group-interview-arena-review-20260830-062133.zip` / SHA-256 `C10F2A9362EB6102C6C3F23D7BA66234FECC098BDE2A394D5A2738EBB97E701D`; `P16B-REV-001 CLOSED`; `P16B-REV-002 CLOSED`; `P16B-REV-003 CLOSED`; new findings `NONE`; open findings `NONE`. The separately approved production implementation is now `DONE / DESIGN_SCOPE_FROZEN / IMPLEMENTATION_COMPLETE / ACTUAL_SOURCE_REVIEW_PASS`; implementation finding-only actual-source re-review verdict is `PASS` against `group-interview-arena-review-20260830-150847.zip` / SHA-256 `0EAA4B3FEE82F4D8A82D5098CECFDA1BF04F9161B7A63E7F7779B2512D9347F6`; `P16B-IMP-001`, `P16B-IMP-002`, `P16B-IMP-003`, `P16B-IMP-004`, `P16B-IMP-005`, `P16B-IMP-006`, `P16B-IMP-007` are `CLOSED`; new findings `NONE`; open findings `NONE`. Exact boundaries remain frozen only in the existing parent plan.

P1-6C freezes existing discussion progression as the sole composition root: realtime/lifecycle triggers resume progression, P1-4 schedules and grants the floor, configured/continuous AI composition reaches the normal candidate runtime, P1-6B Memory produces bounded Working Context, candidate V3 records V2 provenance, and the accepted utterance/event/release path completes the grant. External Design Freeze actual-source review verdict is `PASS` against `group-interview-arena-review-20260830-170659.zip` / SHA-256 `D4364CA666D715EA7932B3FC525D6D154EC18F8F4AC3D3989F40C19AE683B398`; design-review findings `NONE`; new findings `NONE`; open findings `NONE`. The production implementation then added one focused network-free PostgreSQL proof through that real caller chain. It proves accepted Memory revision plus raw tail, candidate V3 and V2 provenance, safe raw fallback, unsafe-context rejection, privacy/evidence authority and re-entry idempotency; production wiring gap `NONE`, production source changes `NONE`, implementation STOP conditions `NONE`. Fresh gates are focused proof `3 passed`, affected PostgreSQL slice `87 passed`, API unit regression `521 passed`, Ruff/format/Pyright `PASS`. External actual-source implementation review verdict is `PASS` against `group-interview-arena-review-20260830-235324.zip` / SHA-256 `1E1FBE37255E294AEA76A4E4CC68E49490556C804BE77804731F78CF56EB944B`; implementation findings `NONE`; new findings `NONE`; open findings `NONE`. P1-6C Design Freeze remains `DONE / DESIGN_SCOPE_FROZEN / ACTUAL_SOURCE_REVIEW_PASS`; P1-6C production implementation is `DONE / DESIGN_SCOPE_FROZEN / IMPLEMENTATION_COMPLETE / ACTUAL_SOURCE_REVIEW_PASS`.

P1-6D freezes and completes a dedicated network-free Browser Acceptance Scenario, separate from the existing layout-heavy session spec. The dedicated harness owns isolated temporary PostgreSQL, API/Web lifecycle, restart coordination, dual semantic/candidate provider behavior, persistent cross-restart signals/logs, durable verification and cleanup; the Browser spec owns only the real product journey. The final acceptance ledger proves exactly one Human plus three authoritative AI IDs, active Human UI contribution and contributions from all three AI seats; durable Semantic Memory revision; candidate V3 plus `GenerationRequestMetadata` V2 provenance; three-seat Private Stance isolation; exact-once generation request/utterance/public event/floor release; Browser reload recovery; API restart recovery; cancellation recovery; and authoritative `FINAL_SUMMARY -> COMPLETED` lifecycle closure. D2-D1, D2-D2A, D2-D2B, D2-D3 and D2-D4 all `PASS`; accepted commit `6dcce5e961d6aa7b460243dbd6407e17c2478aa2`; CI `GREEN`. Design findings `P16D-REV-001`/`P16D-REV-002` and final integration finding `P16D-D2D4-REV-001` are `CLOSED`; new findings `NONE`; open findings `NONE`. P1-6D is `DONE / DESIGN_SCOPE_FROZEN / IMPLEMENTATION_COMPLETE / ACTUAL_SOURCE_REVIEW_PASS`; P1-6E remains `NOT_STARTED`.

P1-6E independently exercised the committed P1-6 boundary. Initial acceptance and two re-acceptances surfaced bounded defects rather than being rewritten as PASS; three repair/source-review cycles closed the original runner、Memory replay、metadata/document drift and later Web/Crash-E race findings. Re-acceptance 2 then passed the complete runtime/browser/environment matrix but returned `REPAIRABLE` on strict typing and two current-state documents. After the automatic three-repair stop, a user-authorized post-stop closeout remediation closed `P16E-RA2-001`/`P16E-RA2-002`; independent finding-only review passed, and exact accepted-remediation CI run `34336016724` is green. The repair-1 cleanup incident remains explicit: a pre-existing temporary database and Playwright marker were mistakenly deleted, were not fabricated as restored, and later validation used the user-accepted post-incident baseline plus ownership-only cleanup. P1-6E/P1-6 are `DONE / CLOSED`; P1 remains `IN_PROGRESS`; no real provider was called.

`P1-7 — Basic Evidence Report + V0.1 Content Closure` is now `IN_PROGRESS` with this frozen split:

- `P1-7A — Basic Evidence Report & V0.1 Content Architecture Freeze`: `DONE / DESIGN_SCOPE_FROZEN / ACTUAL_SOURCE_REVIEW_PASS`; strict docs-only; external review findings `NONE`;
- `P1-7B — Evidence / Report Persistence Foundation`: `DONE / ACTUAL_SOURCE_REVIEW_PASS`; `P1-7B-F001 CLOSED`; open findings `NONE`;
- `P1-7C — Evidence Extraction + Basic Report Generation`: `IMPLEMENTED / AWAITING_ACTUAL_SOURCE_REVIEW`;
- `P1-7D — Report REST/Web + V0.1 Content Closure`: `NOT_STARTED`;
- `P1-7E — Composition Acceptance + Independent Acceptance`: `NOT_STARTED`.

P1-7 freezes an independent durable/versioned report resource over project-validated authoritative public evidence after session `COMPLETED`; it adds no session report states or activity WebSocket lifecycle and does not import P3 formal six-dimension scoring. V0.1 content closure remains exactly 4 ordering + 4 resource-allocation + 4 plan-design human-reviewed questions and the existing 4 basic Persona Templates. Current committed seed source contains one resource-allocation question, so P1-7D later owns the remaining 11 questions. P1-7A creates no schema/runtime/content and required no real provider. Its external actual-source review passed against `group-interview-arena-review-20260909-234536.zip` / SHA-256 `4EA3FE5DD23775106C2602CAA2EC6DC68AC8DDA6D9895C5D74465F90390798F3`, with material findings/new blockers/open findings `NONE`. The reviewed `bc8cb40148598230bd64feeeaebb498d05137fbe` checkout is a direct parent of current GitHub `main` `f6f105ed2fcc334f6c9dd83c00d934428e1b689b` and has an identical tree/empty file diff; this is baseline equivalence, not commit-SHA equality or a claim that the bundle came from the later `main` working tree. P1-7B provides the reviewed 23-table report/evidence persistence foundation at `f1a17b17c008`; its two accepted review bundles remain recorded in the execution plan. P1-7C now implements the network-free public-source evaluation pipeline, deterministic exact-evidence validation/composition and lease/CAS/atomic generation coordinator without schema, API/Web, provider or scoring expansion; it awaits actual-source review. P1-7D/P1-7E and P1-8 remain `NOT_STARTED`. Exact boundaries are frozen in [`exec-plans/P1-7_basic-evidence-report-and-content.md`](exec-plans/P1-7_basic-evidence-report-and-content.md).

## 5. 产品版本

### V0.1 — Internal Validation

目标是验证多角色讨论和状态机，不公开收费。

明确包含：桌面 Web、文字输入输出、3 种题型、12 道人工审核题、3 名 AI 候选人、4 种基础角色、准备/陈述/讨论/总结流程、基础逐句记录、简版证据报告和最小题目配置。

明确不包含：支付、ASR/TTS、完整成长系统、压力事件和行业题包。

### V0.5 — Public MVP

目标是验证用户是否认为产品值得付费。必须加入语音输入输出、4 类题型、20～30 道精品题、新手和标准模式、六维证据评分、专项训练、账号、历史报告、场次权益、支付、隐私删除能力及基础运营后台。

### V1.0 — Stable Commercial Product

目标是形成稳定商业产品。新增压力模式、6～8 种角色、40～60 道精品题、7 天冲刺计划、成长趋势、报告音频跳转、题目 AI 变体、更完善的模型路由和成本控制、评价申诉、邀请奖励及移动端短训练优化。

## 6. 阶段与版本的关系

- P0、P1 为 V0.1 奠定项目基础和文字讨论闭环。
- P2～P5 逐步补齐公开 V0.5 所需的语音、评分训练、商业化和公开测试能力。
- P6 面向 V1.0 发布能力。

该关系用于执行导航，不表示每个版本只对应一个阶段；版本验收仍以 [`RELEASE_CHECKLIST.md`](RELEASE_CHECKLIST.md) 和总纲范围为准。

## 7. 变更规则

- 阶段状态变化时更新本文件，并同步 `TASKS.md`。
- 产品版本范围变化必须先形成正式决策。
- 不得为了实现方便把 V0.5/V1.0 能力提前塞入 P0/P1。
- 不得将 P0-x 子任务表述为总纲原文或新的产品版本。
