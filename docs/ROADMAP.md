# 项目路线图

- Status: Active baseline
- Most recently completed development phase: P0 — `DONE`
- Most recently completed subphase: P1-4E — `DONE`
- P0-7 final outcome: initial `BLOCKED`; two documentation findings remediated; finding-only independent recheck `PASS`; P1 readiness `READY`
- Current phase: P1 — `IN_PROGRESS`
- Most recently completed task: P1-4 — `DONE`
- Next task gate: P1-5 — `NOT_STARTED` / awaiting explicit user approval
- P0 status: `DONE`; P0-1 through P0-7 completed
- Target product version: V0.1 — Internal Validation
- Source: [`PROJECT_MASTER_PLAN.md`](PROJECT_MASTER_PLAN.md) §30–31

## 1. 两套并行概念

本项目严格区分：

- `P0～P6`：研发推进阶段，描述按什么顺序建立能力；
- `V0.1 / V0.5 / V1.0`：产品交付版本，描述某个可验证版本包含什么。

阶段不是版本，P0-x/P1-x 也不是新增产品版本。P0 已完成不代表 V0.1 的全部业务能力已经实现；用户已明确批准进入 P1，P1-1～P1-4 均已完成。P1-4E final independent verdict 为 `PASS`；P1 保持 `IN_PROGRESS`，P1-5 为 `NOT_STARTED` 并等待单独明确批准。

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

P1-4A 已冻结 phase lifecycle 与 within-phase floor authority 分离、single current owner、AI/human/system participant compatibility、deterministic policy、最小 floor facts 与 non-disclosure。P1-4B 已实现 generalized persistence、single-current-grant invariant、immutable audit history、idempotency/concurrency 与 lifecycle protection。P1-4C 已实现 pure deterministic scheduler、fairness/monopoly/phase-aware ordering、stable tie-break、explainable intervention 和 locked decision → fact orchestration。P1-4D 已在既有 REST snapshot + single ordered WS channel 上实现 allowlisted floor projection、strict Web parser/current-owner lifecycle UI、duplicate/gap/stale-generation recovery，以及真实 PostgreSQL Chromium reload/API-restart flow；没有 Browser scheduler authority 或新 realtime protocol。P1-4E 在唯一 documentation finding 修复后完成 full independent recheck，final verdict `PASS`。Scheduler 只决定谁说，未来 LLM/provider 只决定获准 AI 说什么。P1-4 已为 `DONE`；P1-5 为 `NOT_STARTED` / awaiting explicit approval。完整 scope/gates 见 [`exec-plans/P1-4_floor-control.md`](exec-plans/P1-4_floor-control.md)。

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
