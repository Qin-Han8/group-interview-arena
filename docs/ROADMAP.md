# 项目路线图

- Status: Active baseline
- Current development phase: P0 — 项目基础
- Current task: P0-6 — `IN_PROGRESS`
- Most recently completed substep: P0-6A actual-source final review `PASS`; four review findings closed
- Current substep: P0-6B — awaiting explicit user approval / not started
- P0-6 status: `IN_PROGRESS`; P0-6A completed；P0-6B awaiting explicit user approval / not started；P0-6C～P0-6E not started
- Target product version: V0.1 — Internal Validation
- Source: [`PROJECT_MASTER_PLAN.md`](PROJECT_MASTER_PLAN.md) §30–31

## 1. 两套并行概念

本项目严格区分：

- `P0～P6`：研发推进阶段，描述按什么顺序建立能力；
- `V0.1 / V0.5 / V1.0`：产品交付版本，描述某个可验证版本包含什么。

阶段不是版本，P0-x 也不是新增产品版本。当前处于 P0，不代表当前需要实现 V0.1 的全部业务能力。

## 2. 开发阶段

| 阶段 | 目标摘要 | 当前状态 |
|---|---|---|
| P0 项目基础 | 仓库、规范、环境、认证、数据库基础、监控日志和决策记录 | IN_PROGRESS |
| P1 文字版讨论闭环 | 题目模型、角色参数、状态机、调度、记忆、文字模拟和基础报告 | NOT_STARTED |
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
| P0-6 CI、日志与基础可观测性 | 建立自动检查、日志和基础监控能力 | IN_PROGRESS — P0-6A completed；P0-6B awaiting approval / not started；C～E not started |
| P0-7 P0 独立验收 | 独立确认 P0 是否满足进入 P1 的条件 | NOT_STARTED |

任务细节及验收条件见 [`TASKS.md`](TASKS.md)。P0-1～P0-5 均已完成并转为 `DONE`。P0 整体仍为 `IN_PROGRESS`；P0-6A completed，actual-source final review `PASS`，four review findings closed；P0-6B awaiting explicit user approval / not started；P0-6C～P0-6E not started，P0-7 not started。

P0-5 固定采用五阶段执行：P0-5A identity preflight（completed）、P0-5B identity persistence/migration/security primitives（completed）、P0-5C backend auth runtime/API（completed）、P0-5D Web/CORS/CSRF cross-layer validation（completed）、P0-5E independent final review（completed；PASS after findings remediation and independent recheck）。

P0-6 固定采用五阶段执行：P0-6A preflight/scope freeze/execution plan（completed；actual-source final review `PASS`）、P0-6B GitHub Actions CI baseline（awaiting explicit user approval / not started）、P0-6C structured logging hardening（not started）、P0-6D OpenTelemetry tracing foundation（not started）、P0-6E cross-layer validation/P0-6 closeout（not started）。P0-7 仍为独立 P0 final acceptance，不并入 P0-6E。详细计划见 [`exec-plans/P0-6_ci-observability.md`](exec-plans/P0-6_ci-observability.md)。

P0-2 已 Accepted PostgreSQL、SQLAlchemy 2.x 和 Alembic；P0-4 实施基线为 PostgreSQL 18.x，且 Redis 不进入默认 Compose。完整决策和重新评估条件见 [`DECISIONS.md`](DECISIONS.md)。

## 4. 产品版本

### V0.1 — Internal Validation

目标是验证多角色讨论和状态机，不公开收费。

明确包含：桌面 Web、文字输入输出、3 种题型、12 道人工审核题、3 名 AI 候选人、4 种基础角色、准备/陈述/讨论/总结流程、基础逐句记录、简版证据报告和最小题目配置。

明确不包含：支付、ASR/TTS、完整成长系统、压力事件和行业题包。

### V0.5 — Public MVP

目标是验证用户是否认为产品值得付费。必须加入语音输入输出、4 类题型、20～30 道精品题、新手和标准模式、六维证据评分、专项训练、账号、历史报告、场次权益、支付、隐私删除能力及基础运营后台。

### V1.0 — Stable Commercial Product

目标是形成稳定商业产品。新增压力模式、6～8 种角色、40～60 道精品题、7 天冲刺计划、成长趋势、报告音频跳转、题目 AI 变体、更完善的模型路由和成本控制、评价申诉、邀请奖励及移动端短训练优化。

## 5. 阶段与版本的关系

- P0、P1 为 V0.1 奠定项目基础和文字讨论闭环。
- P2～P5 逐步补齐公开 V0.5 所需的语音、评分训练、商业化和公开测试能力。
- P6 面向 V1.0 发布能力。

该关系用于执行导航，不表示每个版本只对应一个阶段；版本验收仍以 [`RELEASE_CHECKLIST.md`](RELEASE_CHECKLIST.md) 和总纲范围为准。

## 6. 变更规则

- 阶段状态变化时更新本文件，并同步 `TASKS.md`。
- 产品版本范围变化必须先形成正式决策。
- 不得为了实现方便把 V0.5/V1.0 能力提前塞入 P0/P1。
- 不得将 P0-x 子任务表述为总纲原文或新的产品版本。
