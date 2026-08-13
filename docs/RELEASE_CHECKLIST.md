# 发布与阶段验收清单骨架

- Status: Skeleton / Baseline
- Current phase: P0
- Target version: V0.1 Internal Validation
- Detailed design: Not started
- Detailed operational checklist: Not started
- Authority: 低于 [`PROJECT_MASTER_PLAN.md`](PROJECT_MASTER_PLAN.md) 和已确认的 [`DECISIONS.md`](DECISIONS.md)

## 文档目的

本文件按 P0 exit、V0.1、V0.5 和 V1.0 分层整理总纲已经明确的范围及验收要求。复选框只是未来验收项，不表示当前已经完成。

## Confirmed by PROJECT_MASTER_PLAN

以下 P0、V0.1、V0.5 和 V1.0 清单只整理总纲第 30～32 节已经明确的范围与验收原则，不新增版本功能或质量指标。完整语义仍以总纲为准。

## 当前版本范围

P0-2 技术架构决策与 P0-3 前后端项目骨架已完成。P0-4A preflight/scope freeze 与 P0-4B PostgreSQL local infrastructure 已完成；P0-4C 等待明确批准。P0 尚未完成，V0.1 业务能力尚未实现。下方 P0 exit 与产品版本复选框仍表示完整阶段/版本验收，不能由单个子任务替代。

## Implementation guidance

- 只有实际验证并有证据的项目才能勾选。
- 不得因功能存在就跳过隐私、安全、恢复和证据质量检查。
- 版本范围变化必须先形成正式决策。
- 具体命令、负责人和发布流程在相关技术任务中补充，不在 P0-1 虚构。

### P0-3C Web foundation verification — 2026-08-12

- [x] `pnpm.cmd install`
- [x] `pnpm.cmd web:lint`
- [x] `pnpm.cmd web:typecheck`
- [x] `pnpm.cmd web:test`
- [x] `pnpm.cmd web:format:check`
- [x] `pnpm.cmd web:build`
- [x] `pnpm.cmd web:dev` 后访问 `http://localhost:3000` 返回 HTTP 200，验证后已停止服务。

这些证据只覆盖 P0-3C Web 技术骨架；不代表 API、数据库、migration、CI 或 P0 exit 已通过。

### P0-3D API foundation verification — 2026-08-13

- [x] `uv sync --frozen`
- [x] `uv lock --check`
- [x] `uv run ruff check .`
- [x] `uv run ruff format --check .`
- [x] `uv run pyright`
- [x] `uv run pytest`
- [x] package 与 FastAPI app import；
- [x] Uvicorn 下 `GET /health` 返回 `200`、精确 JSON 和 `X-Request-ID`；
- [x] Uvicorn 下 `GET /openapi.json` 返回 `200` 并包含 `/health`，验证后已停止服务。

这些证据只覆盖 P0-3D API 技术骨架；不代表 Web/API browser connectivity、CORS、数据库、migration、CI、WebSocket 或 P0 exit 已通过。

### P0-3E connectivity verification — 2026-08-13

API：

- [x] `uv sync --frozen`；
- [x] `uv lock --check`；
- [x] `uv run ruff check .`；
- [x] `uv run ruff format --check .`；
- [x] `uv run pyright`；
- [x] `uv run pytest`，17 项通过；
- [x] 真实 `GET /health` 与 `/openapi.json` 均返回 `200`；
- [x] allowed origin 获得明确 CORS allow origin 与 exposed `X-Request-ID`；
- [x] disallowed origin 未获得 `Access-Control-Allow-Origin`；
- [x] `GET` preflight 通过。

Web 与 contract：

- [x] `pnpm.cmd install --frozen-lockfile`；
- [x] `pnpm.cmd web:lint`；
- [x] `pnpm.cmd web:typecheck`；
- [x] `pnpm.cmd web:test`，8 项通过；
- [x] `pnpm.cmd web:format:check`；
- [x] `pnpm.cmd web:build`；
- [x] `pnpm.cmd web:api:generate` 生成只包含 `/health` 的契约；
- [x] `pnpm.cmd web:api:check` 无漂移；
- [x] Web `:3000` 与 API `:8000` 同时返回 HTTP `200`，验证后服务均已停止；
- [x] 用户在真实浏览器打开 `http://localhost:3000`，页面正常显示“API 状态：已连接”；
- [x] 用户在同一真实浏览器直接请求 `http://localhost:8000/health`，获得 HTTP `200` 与 `{"status":"ok"}`；
- [x] 真实浏览器请求中的 CORS 与 `X-Request-ID` 表现正常；
- [x] 浏览器 Console 未发现与本次功能相关的运行时或 CORS 错误。

P0-3E 已完成，真实浏览器手工验收为 PASS。本项未执行 Playwright、E2E 或其他浏览器自动化；这些证据不代表数据库、WebSocket、业务能力、CI、P0-3F 或 P0 exit 已通过。

### P0-3F independent final verification — 2026-08-13

- [x] 从当前 clean `main` HEAD 重新验证 Git、总纲 hash、工具链、仓库结构、lockfile、依赖范围及 Web/API 静态架构；
- [x] ADR-007 OpenAPI tooling blocker 已解决，REST Source of Truth、派生 contract 与 WebSocket Deferred 边界一致；
- [x] Web frozen install、lint、typecheck、8 项测试、format check 与 production build 通过；
- [x] API frozen sync、lock check、Ruff lint/format、Pyright、17 项 pytest、package/app import 通过；
- [x] 真实 `/health`、`/openapi.json`、allowed/disallowed CORS、preflight、OpenAPI drift 与 Web `:3000` HTTP smoke 通过，服务已清理；
- [x] 文档、scope、public env/secret 与 generated/ignored files 审计通过。

P0-3 已通过第二次独立最终验收并转为 `DONE`。P0 整体仍为 `IN_PROGRESS`；P0-4 当前为 `IN_PROGRESS`，P0-4B 已完成。本项不代表 P0-4、P0 exit 或 V0.1 业务能力已完成。

### P0-4B PostgreSQL local infrastructure verification — 2026-08-13

- [x] Docker Engine/CLI `29.6.2`、Docker Compose `v5.3.1`、`desktop-linux` context 与 Linux daemon 可用；
- [x] localhost `5432` 在启动前无 listener；
- [x] PostgreSQL 官方 release 与 Docker Official Image tag 核验为 `18.4` / `postgres:18.4-trixie`；
- [x] `docker compose --env-file .env -f infra/compose.yaml config` 通过，且只包含 `postgres`；
- [x] official image pull 成功；
- [x] container 达到 `healthy`；
- [x] `SHOW server_version` 返回 PostgreSQL `18.4`；
- [x] development database 存在且 `SELECT 1` 成功；
- [x] published port 只绑定 IPv4 loopback `127.0.0.1:5432`；
- [x] persistence 使用 Docker local named volume，挂载至 `/var/lib/postgresql`；
- [x] restart 后重新 `healthy` 且 `SELECT 1` 成功；
- [x] `.env` 保持 Git ignored，tracked 配置和文档没有真实 credential。

这些证据只覆盖已完成的 P0-4B 本地 PostgreSQL infrastructure。SQLAlchemy、Alembic、driver、migration、数据库 integration tests 与业务 Schema 尚未建立；P0-4 保持 `IN_PROGRESS`，P0-4C 等待明确批准。

## P0 exit

来源：总纲 P0 路线图及 P0 基础职责。

- [ ] 项目仓库和开发规范可供后续任务使用；
- [ ] 环境配置方式已由正式技术决策确定并验证；
- [ ] V0.1 所需的最小身份边界已验证，且生产环境不会误启不安全的开发身份；
- [ ] 已依据 P0-2 批准的技术决策验证 V0.1 所需的关系型数据库、数据访问层和 migration 基础；
- [ ] 自动检查、日志和基础监控已验证；
- [ ] 产品及技术决策记录完整可追溯；
- [ ] P0-1～P0-6 均满足各自验收条件；
- [ ] 已完成 P0-7 独立验收并获得进入 P1 的明确批准。

P0-2 已 Accepted PostgreSQL、SQLAlchemy 2.x 和 Alembic，P0-4 实施基线为 PostgreSQL 18.x，并要求真实 PostgreSQL integration/migration checks。完整公开认证方案仍不是 P0-5 的硬前置条件。

## V0.1 internal validation

目标：验证多角色讨论和状态机，不公开收费。

### 范围

- [ ] 桌面 Web；
- [ ] 文字输入输出；
- [ ] 排序选择、资源分配、方案策划 3 种题型；
- [ ] 12 道人工审核题；
- [ ] 每场 3 名 AI 候选人；
- [ ] 4 种基础角色；
- [ ] 准备、陈述、讨论和总结流程；
- [ ] 基础逐句记录；
- [ ] 简版证据报告；
- [ ] 管理端最小题目配置。

### 边界

- [ ] 未加入支付；
- [ ] 未加入 ASR/TTS；
- [ ] 未加入完整成长系统；
- [ ] 未加入压力事件；
- [ ] 未加入行业题包。

### 核心质量

- [ ] 三名 AI 的行为具有可感知且有意义的差异；
- [ ] 讨论由状态机和发言权调度控制，不陷入长期复述；
- [ ] 用户能够完成选题到简版报告的内部闭环；
- [ ] 重要评价具有可核对的发言证据；
- [ ] AI 不替用户完成答案，也不输出招聘结论。

## V0.5 public MVP

目标：验证用户是否认为产品值得付费。

### 必需能力

- [ ] 语音输入；
- [ ] AI 语音输出；
- [ ] 每场 3 名 AI 候选人；
- [ ] 4 类题型；
- [ ] 20～30 道精品题；
- [ ] 新手和标准模式；
- [ ] 六维评分；
- [ ] 时间戳证据；
- [ ] 5～8 种专项训练；
- [ ] 用户账号；
- [ ] 历史报告；
- [ ] 场次权益和支付；
- [ ] 删除数据和隐私设置；
- [ ] 基础运营后台。

### 核心流程与安全

- [ ] 讨论状态可在刷新或短断线后恢复；
- [ ] 权益不会重复扣减，系统故障场次可自动返还；
- [ ] 题目和评分规则具有版本记录；
- [ ] 用户可执行训练记录和账号删除；
- [ ] 前端无服务端密钥，用户数据隔离，对象存储默认私有；
- [ ] AI 身份明确标识；
- [ ] 报告不输出录取概率、歧视性或人格定性语言；
- [ ] 不完整会话降低置信度，用户可反馈评价准确性。

## V1.0

目标：形成稳定商业产品。

### 新增范围

- [ ] 压力模式；
- [ ] 6～8 种 AI 角色；
- [ ] 40～60 道精品题；
- [ ] 7 天冲刺计划；
- [ ] 成长趋势；
- [ ] 报告音频跳转；
- [ ] 题目 AI 变体；
- [ ] 更完善的模型路由和成本控制；
- [ ] 用户评价申诉；
- [ ] 邀请奖励；
- [ ] 移动端短训练体验优化。

### 稳定商业产品要求

- [ ] 压力模式通过复杂互动制造难度，而非单纯增加攻击性；
- [ ] 更多角色仍能通过盲测区分且不依赖固定剧本；
- [ ] 成长与冲刺围绕真实训练行为，不依赖无意义签到；
- [ ] 报告音频跳转遵守用户授权和数据保留策略；
- [ ] 成本优化没有牺牲角色差异、证据质量或可接受延迟。

## TBD

- TBD：每层检查的负责人、证据链接和签字流程；
- TBD：migration、跨应用及后续阶段的具体检查命令；
- TBD：性能、可靠性和成本阈值的正式基线；
- TBD：公开发布的合规、备案和邀请测试路径；
- TBD：版本回滚、数据迁移和事故响应流程。

这些是派生 TBD，不是总纲原始 D-xxx。

## Future work

- P0-6：补充实际自动检查和基础可观测性项目。
- P0-7：执行并记录 P0 exit 验收。
- 各版本发布任务：补充负责人、环境、命令、证据和发布/回滚步骤。

## 与其他文档关系

- 范围和路线：[`ROADMAP.md`](ROADMAP.md)
- 当前任务：[`TASKS.md`](TASKS.md)
- 产品验收：[`PRODUCT_REQUIREMENTS.md`](PRODUCT_REQUIREMENTS.md)
- 隐私与安全：[`PRIVACY_AND_SAFETY.md`](PRIVACY_AND_SAFETY.md)
- 技术与数据：[`ARCHITECTURE.md`](ARCHITECTURE.md)、[`DATABASE.md`](DATABASE.md) 和 [`API.md`](API.md)
