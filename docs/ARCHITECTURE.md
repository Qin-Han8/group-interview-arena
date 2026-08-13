# P0 技术架构基线

- Status: P0 Architecture Baseline
- Current phase: P0
- Architecture baseline established by: P0-2 — DONE
- P0-3 foundation status: DONE
- Next task: P0-4 awaiting explicit approval
- Target version: V0.1 Internal Validation
- Business architecture detail: Incremental from P1
- Authority: 低于 [`PROJECT_MASTER_PLAN.md`](PROJECT_MASTER_PLAN.md) 和已确认的 [`DECISIONS.md`](DECISIONS.md)

## 文档目的

本文件记录 P0-2 已批准的技术架构基线、系统边界、规划目录、开发拓扑和演进约束。它不是完整业务架构；P1 以后的题目、角色、会话、编排和评分模块仍须在进入对应任务时逐步设计。

正式技术决策及其上下文以 [`DECISIONS.md`](DECISIONS.md) 中 `ADR-001`～`ADR-014` 为准。本文件只整理这些决策对实现的直接约束。

## Accepted architecture baseline

### Repository and application boundaries

- 使用 simple monorepo；
- Web 应用位于 `apps/web`，P0-3C 已建立最小技术骨架；
- API 应用位于 `apps/api`，P0-3D 已建立最小技术骨架；
- 当前不使用 multi-repo、Nx 或 Turborepo；
- 根 pnpm workspace 当前只包含 `apps/web`。

重新评估 monorepo 工具的触发器：出现多个独立 JS package/application、CI 构建依赖明显复杂，或普通 workspace scripts 已无法合理维护。

### Current and planned repository layout

下列结构明确区分已实现与规划项：

```text
group-interview-arena/
├── apps/
│   ├── web/                     # Implemented in P0-3C: Next.js skeleton
│   └── api/                     # Implemented in P0-3D: FastAPI skeleton
├── infra/
│   └── compose.yaml             # Planned for P0-4; not created
├── docs/
├── package.json                 # Implemented: JS workspace and Web delegates
├── pnpm-workspace.yaml          # Implemented: apps/web only
└── pnpm-lock.yaml               # Implemented: sole JS lockfile
```

不提前创建 `packages/`、worker、Redis adapter、未来业务 module 或没有调用方的 infrastructure 目录。

### Runtime and toolchain policy

- JavaScript runtime：Node.js 24 LTS；P0-3 选用当时最新兼容的 24.x，不以当前机器的 Node 26 Current 作为项目基线；
- JavaScript package manager：pnpm；`packageManager` 记录实际精确版本，只提交 `pnpm-lock.yaml`；
- Python runtime：CPython 3.14；`.python-version` 和 `pyproject.toml` 在 P0-3 表达 3.14 policy；
- Python environment/package manager：uv；`apps/api/uv.lock` 是已提交边界内的 Python lockfile；
- 只有项目必需依赖明确不兼容 Python 3.14 时，才能提出降至 3.13 的 Proposed ADR；
- Windows PowerShell 是正式支持的本地开发环境，不要求 WSL。

### Frontend boundary

- Next.js App Router、React、TypeScript strict、Tailwind CSS；
- `app` 负责 routing/layout；
- `features` 只存放已经进入当前范围的真实用户能力；
- `components` 只存放真正共享的 UI；
- `lib/api` 存放 API transport 和生成契约；
- `lib/realtime` 仅在 P1 真正建立实时通道时创建；
- UI primitives/component library 保持 Deferred。

Next.js Server Actions/Route Handlers 可以处理 Web 专属能力，但不得复制 domain logic、session state machine、scoring、agent orchestration 或 persistence authority。FastAPI 始终是主要业务后端。

P0-3C 已实现的 Web 技术基础为：Next.js `16.3.0`、React `19.2.8`、TypeScript `5.9.3` strict、Tailwind CSS `4.3.3` 和 App Router。根 workspace 使用 pnpm `11.21.0`；前端质量栈使用 ESLint `9.39.5`、Prettier `3.9.6`、Vitest `4.1.10`、Testing Library React `16.3.2`、jest-dom `7.0.1` 与 jsdom `30.0.1`。P0-3E 加入 `openapi-typescript 7.13.0` 与 `openapi-fetch 0.17.0`，只服务于当前真实 `/health` caller。当前首页只证明技术骨架，不是群面业务 UI。

### Backend boundary

- FastAPI；
- Pydantic v2；
- 在外部 I/O 边界适当使用 Python async I/O；
- 纯领域规则不因 FastAPI 是 async 就被强制写成 async；
- API schema、ORM model 和领域对象保持分离。

后端采用 lightweight domain-oriented hybrid，规划职责为：

```text
api/          transport adapters
core/         configuration, errors, logging and cross-cutting infrastructure
db/           persistence infrastructure, created when P0-4 needs it
modules/      real business domains, created only when their phase begins
providers/    provider adapters that have actual callers
```

禁止 full DDD ceremony、repository/service/controller 多层空壳、global giant `services.py`，以及提前创建未来全部 module。

P0-3D 已实现的 API 技术基础使用 CPython `3.14.7`、uv `0.12.3`、FastAPI `0.141.1`、Pydantic `2.13.4`、pydantic-settings `2.15.0` 与 Uvicorn `0.52.1`。项目采用 packaged `src/group_interview_arena_api` layout；`api/` 当前只有 health transport，`core/` 只包含 typed settings、安全错误语义、标准库 JSON logging 与 UUIDv4 `request_id`。数据库、业务 `modules/`、`providers/` 与 WebSocket 目录均未创建。

## Local development model

```text
developer
  ├── browser
  │     -> Next.js web :3000
  │          -> REST GET /health
  │               -> FastAPI api :8000
  ├── Node.js 24 LTS + pnpm
  └── CPython 3.14 + uv

PostgreSQL 18.x via Docker Compose remains planned for P0-4.
```

本地 browser origin 必须通过 `GIA_API_CORS_ORIGINS` 显式加入 allowlist；缺省为空，不允许跨源。`NEXT_PUBLIC_API_BASE_URL` 是公开浏览器 base URL，不是 secret。Web 直接请求 FastAPI，不建立 Next.js Route Handler proxy。

### P0-3 — completed

已建立并通过独立最终验收：

- Web skeleton；
- API skeleton；
- approved toolchain；
- health endpoints；
- Web → API connectivity；
- basic configuration；
- structured logging baseline；
- backend unit/API tests；
- frontend unit/component smoke tests；
- 当前阶段需要的 lint、typecheck 和 build。

P0-3 不需要数据库容器，不创建 Redis、task queue、WebSocket 业务代码或 Provider 实现。

### P0-4

加入：

- Docker Compose；
- PostgreSQL 18.x，禁止 `postgres:latest`；
- SQLAlchemy 2.x；
- Alembic；
- PostgreSQL integration tests 和 migration tests。

Redis 继续不运行。

## Communication and contract boundaries

- REST：resource CRUD、question fetch、session create、session snapshot/load、reports、settings 及未来 admin/orders；
- WebSocket：active session commands、state changes、participant events、timer、floor control、interruption、AI streamed text 及未来 speech-related session events；
- SSE 不作为活动 session 主协议；
- P1 第一个文字讨论 vertical slice 即建立 WebSocket session channel，不先做完整 HTTP 讨论后再重写；
- 服务端 session state 是权威；client command 有 action identity；session event 有顺序；重连基于 server snapshot + sequence。

FastAPI OpenAPI 是 REST contract 的 Source of Truth。P0-3E 从运行中的 `/openapi.json` 使用 `openapi-typescript` 生成 `apps/web/src/lib/api/generated/schema.d.ts`，再由 `openapi-fetch` 提供 typed fetch client；生成文件受版本控制且不得手改，`api:check` 验证漂移。

WebSocket 使用独立版本化事件契约，至少表达 event type、schema version、session identity、ordering sequence、occurrence timestamp 和 action identity。完整 P1 事件 Schema 由 P1 API design 冻结，不在 P0-2 假装已经完成。

## Configuration, secrets and error boundaries

- 配置采用类型化、启动时校验的方式；
- `.env.example` 只提供安全占位符，私有环境文件不得提交；
- 服务端密钥不得进入浏览器 bundle、公开构建产物或日志；
- 生产环境不得接受不安全开发身份默认值；
- REST 使用标准 HTTP status、稳定 machine-readable error code、安全 message、request correlation 和可选安全 details；
- WebSocket error event 与 REST error semantics 对齐；
- 不向用户暴露 stack trace、SQL、filesystem path、secret、prompt 或 provider credential。

## Testing and quality layers

按阶段安装当前验收真正需要的工具：

- Python quality：Ruff lint、Ruff format、Pyright；不同时启用 mypy；
- Backend tests：pytest，只有异步测试需要时使用 pytest-asyncio；
- Frontend quality：ESLint、TypeScript `tsc`、Prettier；
- Frontend tests：Vitest、Testing Library；
- P0-4：真实 PostgreSQL integration/migration tests，不使用 SQLite 代替；
- P1：WebSocket tests、fake provider tests、deterministic session/orchestrator regression；
- 有真实跨应用用户流后再加入 Playwright；
- 真实 LLM tests 必须显式执行，不进入默认 CI。

## Logging and observability

- 从 P0-3 应用骨架开始使用 structured logging；
- 通用请求使用 `request_id`；
- `session_id`、`connection_id`、provider invocation id、`job_id` 只在相关能力实际出现后增加；
- 不为未来字段生成虚假 ID；
- 敏感 prompt、secret 和不必要的完整输入默认不写日志；
- OpenTelemetry 延后到 P0-6；
- Sentry 或其他 SaaS exporter 保持 Deferred。

## Provider neutrality and orchestration

- 业务领域不得直接绑定厂商 SDK；
- LLM Provider、ASR Provider、TTS Provider、可选 Embedding Provider 是按需建立的概念边界；
- LLMProvider 在 P1 首次真正调用 LLM 时建立；
- ASRProvider/TTSProvider 在 P2 首次接入时建立；
- Embedding Provider 只有实际需求时建立；
- Provider SDK object 不得穿透 domain layer；
- structured output 必须经过 Schema validation；
- V0.1 不使用 LangGraph；核心 discussion orchestrator 是自定义、确定性、可测试的状态机。

不得为尚未使用的 Provider、Redis 或 task queue 创建空 interface、adapter、factory、worker 或目录。

## Deferred infrastructure and decisions

- Redis runtime、implementation 和产品；
- 独立 task queue 及其具体产品；
- UI primitives/component library；
- WebSocket schema generator；
- OpenTelemetry exporter、Sentry/SaaS、analytics；
- 具体 LLM/model、ASR、TTS 和 Embedding 实现；
- 正式认证、支付、云平台、中国生产部署、对象存储、CDN 和 PWA production strategy。

Redis 只在多 API workers、横向扩容、跨进程 WebSocket broadcast、distributed lock、centralized rate limiting 或 durable task queue 出现时重新评估。

独立后台任务队列只在 reliable retry、delayed jobs、scheduling、independent workers 或 cross-process execution 出现时重新评估。当前能够合理完成的任务同步执行。

## Future work

- P0-4：创建 PostgreSQL 数据与 migration 基础；
- P0-5：落实内部 V0.1 最小身份边界；
- P0-6：建立 CI 和基础可观测性；
- P1：逐步设计题目、角色、会话、状态机、调度、记忆和基础报告，并建立第一个 WebSocket vertical slice；
- P2 以后：只在对应阶段获批后增加语音、评分训练和商业化能力。

## 与其他文档关系

- 技术决策：[`DECISIONS.md`](DECISIONS.md)
- 数据边界：[`DATABASE.md`](DATABASE.md)
- API 与事件：[`API.md`](API.md)
- 会话与编排：[`AGENT_BEHAVIOR.md`](AGENT_BEHAVIOR.md)
- 安全约束：[`PRIVACY_AND_SAFETY.md`](PRIVACY_AND_SAFETY.md)
- 当前执行顺序：[`ROADMAP.md`](ROADMAP.md) 和 [`TASKS.md`](TASKS.md)
