# 当前任务清单

- Status: Active
- Managed scope: P0 only
- Current task: None — awaiting explicit approval for P0-2
- Allowed status values: `TODO` / `IN_PROGRESS` / `BLOCKED` / `DONE`
- Related roadmap: [`ROADMAP.md`](ROADMAP.md)

本文件只拆分当前 P0，不提前把 P1～P6 展开成大量任务。任务必须经用户明确批准后才能从 `TODO` 转为 `IN_PROGRESS`。

## P0-1 — 仓库与文档治理

- ID: `P0-1`
- 名称：仓库与文档治理
- Status: `DONE`
- 目标：建立项目 Source of Truth、长期上下文、文档层级、任务管理、决策管理和后续 Codex 执行规则。
- Dependencies：`PROJECT_MASTER_PLAN V1.0` 已存在并作为只读基线。

### In scope

- 根级 README、AGENTS 和基础仓库文本配置；
- DECISIONS、ROADMAP、TASKS 和 exec-plan 规则；
- 九份领域文档的稳定骨架；
- 总纲决策、版本边界和 TBD 的可追溯摘要；
- Git、文档同步、安全和任务交付规则；
- 文档引用、范围及状态一致性验证。

### Out of scope

- 应用脚手架；
- Next.js、React 或前端业务代码；
- FastAPI 或 Python 项目；
- PostgreSQL 业务数据库、ORM、migration；
- Redis；
- 用户登录和正式认证方案；
- LLM Provider、Prompt 或 AI Agent；
- AI 角色实现；
- 讨论状态机和发言权调度代码；
- 评分或报告代码；
- ASR、TTS 或其他语音实现；
- 支付、订单和权益实现；
- Docker、测试框架和 CI 实现。

### Acceptance criteria

- 所有获准的治理文件存在且职责明确；
- 详细治理文档足以指导后续 Codex；
- 九份领域文档只形成骨架，不伪装成完整设计；
- D-001～D-015 可追溯，未创建不存在的产品决策；
- 总纲第 37 节的 10 项问题保留为 TBD；
- 推荐技术没有被提升为 Accepted；
- 阶段、版本和 P0-x 执行拆分清楚区分；
- `PROJECT_MASTER_PLAN.md` 字节级未修改；
- 没有业务代码、应用脚手架、依赖安装、暂存、提交或推送；
- 用户完成 diff 审核后，任务方可转为 `DONE`。

### Completion note

- Governance baseline established；
- External diff review passed；
- `PROJECT_MASTER_PLAN.md` SHA-256 verified；
- No business code introduced。

## P0-2 — 技术架构决策

- ID: `P0-2`
- 名称：技术架构决策
- Status: `TODO`
- 目标：在总纲推荐方向内确认技术栈、仓库组织、模块边界和必要 ADR。
- In scope：前后端技术、包管理、通信方式、开发环境边界、部署候选方案及 ADR。
- Out of scope：创建应用、实现业务功能、数据库业务 Schema、正式认证和供应商接入。
- Dependencies：P0-1 审核完成。
- Acceptance criteria：关键技术选择有批准记录，建议与 Accepted 决策明确区分，P0-3 可据此实施。

## P0-3 — 前后端项目骨架

- ID: `P0-3`
- 名称：前后端项目骨架
- Status: `TODO`
- 目标：依据 P0-2 的 Accepted 决策建立最小 Web/API 及本地开发骨架。
- In scope：项目结构、基础配置、健康检查和经批准的本地运行方式。
- Out of scope：群面页面、AI、状态机、评分、语音、支付及完整账号产品。
- Dependencies：P0-2 完成并批准。
- Acceptance criteria：前后端骨架可按文档启动、构建和执行基础检查，无业务范围扩张。

## P0-4 — 数据库与迁移基础

- ID: `P0-4`
- 名称：数据库与迁移基础
- Status: `TODO`
- 目标：依据 P0-2 已批准的技术决策，建立 V0.1 所需的关系型数据库、数据访问层和 migration 基础。
- In scope：经批准的数据连接配置、安全占位、数据访问层、迁移工具、最小基础模型及迁移验证。
- Out of scope：一次性实现总纲所有未来业务实体或完整会话数据模型。
- Dependencies：P0-2、P0-3。
- Implementation guidance：`PROJECT_MASTER_PLAN.md` 当前推荐 PostgreSQL + SQLAlchemy 或等价方案，但在 P0-2 正式决策前不视为 `Accepted` 技术选型。
- Acceptance criteria：依据 P0-2 已批准的方案完成可重复验证的迁移基础，环境变量与密钥安全，范围符合 V0.1/P0。

## P0-5 — 最小身份边界

- ID: `P0-5`
- 名称：最小身份边界
- Status: `TODO`
- 目标：建立内部 V0.1 所需的最小身份及数据隔离边界。
- In scope：V0.1 内部环境所需的最小身份策略、数据隔离边界，以及防止不安全开发身份在生产环境误启的保护要求；具体实现由后续获批任务确定。
- Out of scope：完整公开账号体系、短信验证码、邮箱验证码、OAuth 矩阵、付费会员和企业权限系统。
- Dependencies：P0-3、P0-4，以及 V0.1 内部最小身份边界所需的技术决策；不依赖完整公开认证方案。
- Acceptance criteria：内部身份边界可验证，用户数据隔离明确，生产环境不会误启不安全的开发身份，且不提前实现 V0.5 账号产品。

完整公开认证方案继续保持 `TBD`，不构成 P0-5 的硬前置条件。

## P0-6 — CI、日志与基础可观测性

- ID: `P0-6`
- 名称：CI、日志与基础可观测性
- Status: `TODO`
- 目标：建立与当前代码规模匹配的自动检查、结构化日志和基础监控能力。
- In scope：经批准的 lint/typecheck/test/build 检查、基础日志和错误观测。
- Out of scope：完整生产监控平台、所有业务指标和过度复杂的部署流水线。
- Dependencies：P0-2、P0-3；数据库相关检查依赖 P0-4。
- Acceptance criteria：自动检查可复现，日志不泄露敏感信息，失败可定位。

## P0-7 — P0 独立验收

- ID: `P0-7`
- 名称：P0 独立验收
- Status: `TODO`
- 目标：独立确认 P0 的基础能力和治理是否足以进入 P1。
- In scope：仓库、规范、架构、骨架、数据库基础、身份边界、CI/日志和决策记录验收。
- Out of scope：提前实现 P1 文字讨论闭环。
- Dependencies：P0-1～P0-6 完成。
- Acceptance criteria：P0 所有验收项有证据，遗留风险和 TBD 已记录，并由用户明确批准进入 P1。

## 任务更新规则

- 开始任务：用户明确批准后设为 `IN_PROGRESS`。
- 完成实现：验证通过并提交 diff；若验收要求用户审核，审核前仍保持 `IN_PROGRESS`。
- 阻塞任务：只有真实外部依赖阻止继续时设为 `BLOCKED`，并写明解除条件。
- 完成任务：满足全部验收条件后设为 `DONE`。
- 范围变化：先更新决策或获得批准，再修改任务范围。
