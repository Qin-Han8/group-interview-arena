# 当前任务清单

- Status: P1 in progress; P1-1 discussion session foundation approved
- Managed scope: P1-1 only; P1-1A completed; P1-1B～E require separate explicit approval
- Most recently completed task: P1-1A — `DONE`
- P0-7 final outcome: initial verdict `BLOCKED` with two documentation findings; remediation completed; finding-only independent recheck `PASS`; new blockers none; P1 readiness `READY`
- Current phase: P1 — `IN_PROGRESS`
- Current task: P1-1 — `IN_PROGRESS`
- Next subphase gate: P1-1B — `TODO` / not started / awaiting explicit user approval
- P0 status: `DONE`; P0-1 through P0-7 completed
- Allowed status values: `TODO` / `IN_PROGRESS` / `BLOCKED` / `DONE`
- Related roadmap: [`ROADMAP.md`](ROADMAP.md)

用户已明确批准正式进入 P1。本文件当前只展开获准的 P1-1 discussion session foundation，不提前展开 P1 的题目、角色、完整状态机、调度、记忆或报告任务，也不提前展开 P2～P6。

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
- Status: `DONE`
- 目标：在总纲推荐方向内确认技术栈、仓库组织、模块边界和必要 ADR。
- In scope：前后端技术、运行时与包管理、REST/WebSocket 边界、本地开发方式、数据技术基线、模块边界、测试/日志/Provider 原则及正式 ADR。
- Out of scope：创建应用、实现业务功能、数据库业务 Schema、正式认证和供应商接入。
- Dependencies：P0-1 审核完成。
- Acceptance criteria：关键技术选择有批准记录，建议与 Accepted 决策明确区分，P0-3 可据此实施，并完成最终 diff 审核。

### Completion note

- 14 architecture ADRs accepted；
- External diff review passed；
- Runtime/toolchain baseline established；
- P0-3/P0-4 boundary established；
- No application code introduced。

## P0-3 — 前后端项目骨架

- ID: `P0-3`
- 名称：前后端项目骨架
- Status: `DONE`
- 目标：依据 P0-2 的 Accepted 决策建立最小 Web/API 及本地开发骨架。
- In scope：`apps/web` 与 `apps/api` skeleton、Node.js 24 LTS/pnpm、CPython 3.14/uv、健康检查、Web → API connectivity、基础配置、structured logging baseline、backend unit/API tests、frontend unit/component smoke tests 及 lint/type/build。
- Out of scope：PostgreSQL、Docker Compose、SQLAlchemy、Alembic、Redis、WebSocket 业务通道、Provider 实现、群面页面、AI、状态机、评分、语音、支付及完整账号产品。
- Dependencies：P0-2 完成并批准。
- Acceptance criteria：前后端骨架可按文档启动、构建和执行获批的基础检查，Web 可验证访问 API 健康端点，无数据库或业务范围扩张。

### Substep progress

- `P0-3A — Environment preflight`：completed；
- `P0-3B — Environment normalization verification`：completed；
- `P0-3C — Root workspace + Web skeleton`：completed；
- `P0-3D — API skeleton`：completed；
- `P0-3E — Connectivity + quality gates + docs`：completed；
- `P0-3F — Independent final review`：completed。

### P0-3C completion note

- 已建立仅包含 `apps/web` 的根 pnpm workspace 和唯一根 `pnpm-lock.yaml`；
- 已建立 Next.js `16.3.0` App Router、TypeScript strict、Tailwind CSS 最小 Web 骨架；
- 已建立并实际通过 Web lint、typecheck、Vitest/Testing Library 测试、Prettier check、production build 与本地 HTTP 200 smoke；
- 未创建 API、数据库、业务模块或任何 P0-3D 及后续能力；
- P0-3 整体保持 `IN_PROGRESS`。

### P0-3D completion note

- 已建立 CPython 3.14、uv、FastAPI、Pydantic v2 的 packaged `src` layout API skeleton 与唯一 `uv.lock`；
- 已实现 `create_app()`、`GET /health`、typed settings、UUIDv4 `request_id`、标准库 JSON structured logging 和统一安全 error envelope；
- 已实际通过 frozen sync、lock check、Ruff lint/format、Pyright strict、9 项 pytest、package/app import、health 与 OpenAPI smoke；
- 未修改 `apps/web`，未建立 CORS、Web → API connectivity、数据库、WebSocket、Provider 或业务 endpoint；
- P0-3 整体保持 `IN_PROGRESS`；P0-3D 完成当时，P0-3E 尚待明确批准。

### P0-3E completion note

- 已实现显式 typed CORS allowlist，默认不允许 browser cross-origin，并保留现有 request_id、结构化日志和安全错误语义；
- 已从运行中的 FastAPI `/openapi.json` 使用 `openapi-typescript` 生成受版本控制的 TypeScript contract，并由 `openapi-fetch` 建立 `/health` typed client；
- 已实现 Web public base URL 校验与一次性 `HealthStatus` 连通状态，未建立 Next.js proxy、轮询或业务 UI；
- 已通过 API/Web 全部质量检查、contract drift check、真实 CORS headers 与双服务 HTTP 200 smoke；
- 用户已在真实浏览器确认首页显示“API 状态：已连接”、直接访问 `/health` 返回 `200` 与精确 JSON、CORS 和 `X-Request-ID` 正常，且 Console 无相关运行时或 CORS 错误；该手工验收为 PASS，未执行 Playwright、E2E 或其他浏览器自动化；
- P0-3E 完成当时，P0-3 整体仍为 `IN_PROGRESS`，P0-3F 等待明确批准，不得自动进入。

### P0-3F completion note

- 第二次独立最终验收已从 clean HEAD 重新执行完整 Git、治理、工具链、结构、依赖、Web/API 质量门、真实 HTTP/CORS/OpenAPI smoke、契约漂移、范围、安全与生成物检查；
- ADR-007 的 OpenAPI tooling 治理 blocker 已确认解决，FastAPI OpenAPI 仍是 REST contract 的 Source of Truth，WebSocket schema tooling 仍 Deferred 到 P1；
- Web 8 项测试与 API 17 项测试通过，双服务验证后端口已清理，最终实现基线保持 clean；
- P0-3 已完成并转为 `DONE`；P0 整体仍为 `IN_PROGRESS`，P0-4 保持 `TODO` 并等待明确批准。

## P0-4 — 数据库与迁移基础

- ID: `P0-4`
- 名称：数据库与迁移基础
- Status: `DONE`
- Approval state：P0-4A/P0-4B/P0-4C/P0-4D/P0-4E/P0-4F completed。
- 目标：依据 P0-2 已批准的技术决策，建立 V0.1 所需的 PostgreSQL 数据库、数据访问层和 migration 基础。
- In scope：Docker Compose、PostgreSQL 18.x、安全连接配置、SQLAlchemy 2.x、Alembic、最小基础模型、PostgreSQL integration tests 及 migration checks。
- Out of scope：一次性实现总纲所有未来业务实体或完整会话数据模型。
- Dependencies：P0-2、P0-3。
- Implementation guidance：使用明确的 PostgreSQL 18.x 镜像版本，不得使用 `postgres:latest`；不使用 SQLite 替代正式开发/集成路径；Redis 不进入默认 Compose。
- Acceptance criteria：依据 P0-2 已批准的 PostgreSQL 18.x、SQLAlchemy 2.x 和 Alembic 方案完成可重复验证的迁移基础，真实 PostgreSQL integration/migration checks 通过，环境变量与密钥安全，范围符合 V0.1/P0。

### Substep progress

- `P0-4A — Database implementation preflight and scope freeze`：completed；
- `P0-4B — Docker Compose + PostgreSQL local infrastructure`：completed；
- `P0-4C — SQLAlchemy async foundation + typed DB config`：completed；
- `P0-4D — Alembic migration foundation + zero-op baseline revision`：completed；
- `P0-4E — PostgreSQL integration tests + migration validation + docs`：completed；
- `P0-4F — Independent final review`：completed。

### P0-4B completion note

- 已建立 `infra/compose.yaml`，唯一 service 为 `postgres`，使用 `postgres:18.4-trixie`；
- PostgreSQL 18 named volume 挂载至 `/var/lib/postgresql`，host binding 为 `127.0.0.1:5432`；
- Compose config、official image pull、container health、PostgreSQL `18.4`、开发数据库、`SELECT 1`、named volume 与 restart smoke 均通过；
- `.env` 保持 Git ignored，Compose 和文档未提交真实 credential；
- 未创建 SQLAlchemy、Alembic、driver、migration、业务 Schema、Redis 或应用 container；
- P0-4 保持 `IN_PROGRESS`；P0-4C 已采用 scoped `psycopg[binary]` 3.3.x async driver baseline 并完成最终审核。

### P0-4C implementation note

- 已加入 SQLAlchemy `2.0.52` 与 psycopg/psycopg-binary `3.3.4`，使用 `postgresql+psycopg://`、`create_async_engine()` 与 `async_sessionmaker()`；
- 已建立 lazy、server-only `GIA_API_DATABASE_URL`/`SecretStr` 配置，现有 app startup 与 `GET /health` 不要求数据库 URL；
- 已建立 `DeclarativeBase`、稳定 naming convention、async engine/session factory 与显式 dispose helper；没有 global engine 或 app lifecycle 接入；
- 31 项 API 测试通过，其中 14 项为新增 DB foundation unit tests；这些测试不连接 PostgreSQL，不是 integration tests；
- 当前 metadata table count 为 0；未加入 Alembic、migration、业务 ORM model、FastAPI DB dependency 或业务 Schema；
- P0-4C、P0-4D、P0-4E 与 P0-4F 均已完成。

### P0-4D implementation note

- Alembic `1.18.5` 仅加入 development dependency group，已建立 async migration environment；
- P0-4D 验收时唯一 head `7c6ccd86b3c5` 是不含业务 DDL 的 zero-op baseline，`Base.metadata.tables` 为 `0`；P0-5B 已在不修改 baseline 的前提下追加 identity head；
- 使用隔离的随机 `gia_p04d_*` PostgreSQL database 完成 upgrade、重复 upgrade、drift check、downgrade base 与 re-upgrade smoke；临时数据库已删除，开发数据库未迁移且 `SELECT 1` 通过；
- 新增 4 项 migration static/unit tests，总计 35 项 API tests 通过；本轮 smoke 不等同于 P0-4E reusable integration test suite；
- 未增加业务 table/model、FastAPI DB dependency、app migration startup 或 `create_all`/`drop_all`；当前 P0-4E 完成状态见下方 completion note。

### P0-4E completion note

- 已建立 `tests/integration/` reusable harness，以 test-only typed settings 安全读取根 `.env`，为每个数据库测试创建唯一 `gia_p04e_*` PostgreSQL database 并精确清理；
- protected database guard 覆盖 development database、system databases 与无安全前缀名称，admin DDL 使用 `psycopg.sql.Identifier`；
- 真实验证 AsyncEngine、AsyncSession、PostgreSQL major 18、commit 与 rollback；test-only probe table 不属于 product schema；
- P0-4E 验收时 programmatic Alembic tests 覆盖 fresh → zero-op head、repeat upgrade、drift check、downgrade base、re-upgrade 与 final check，当时 business table count 为 `0`；
- unit suite 35 项、integration suite 11 项（skipped 0）、full suite 46 项全部通过；P0-4E 验收时 development database 未迁移，`SELECT 1` 通过且无 `alembic_version`；P0-5B 后的当前状态见下方 completion note；临时数据库残留为 0；
- 未新增 dependency，`uv.lock` 与 baseline revision 均未改变；本段只记录 P0-4E 证据，P0-4F 的独立验收结果见下方 completion note。

### P0-4F completion note

- 从 clean `main` HEAD `622170f9f1cae0d6ad7492d4134564001b030713` 独立复核 P0-4，不沿用此前子步骤 PASS 作为替代证据；
- 总纲 SHA-256、Git history、Docker/PostgreSQL/Compose runtime、loopback binding、named volume、secret/dependency 边界、SQLAlchemy/Alembic 静态架构、单一 zero-op revision 与 integration harness safety 全部通过；
- unit suite 35 项、integration suite 11 项（skipped 0）、full suite 46 项通过；frozen sync、lock check、Ruff、format、Pyright 与 Alembic heads 通过；
- P0-4F 验收时 development database 保持未迁移、无 `alembic_version`、public table count 为 `0` 且 `SELECT 1` 通过；P0-5B 后已安全迁移至 identity head；`gia_p04e_%` 残留为 `0`；
- 未修改被审计实现、测试、依赖、Compose 或 migration；P0-4 已转为 `DONE`，P0-5 等待明确批准。

## P0-5 — 最小身份边界

- ID: `P0-5`
- 名称：最小身份边界
- Status: `DONE`
- Approval state：P0-5A/P0-5B/P0-5C/P0-5D completed；P0-5E independent review completed；initial verdict `BLOCKED` with two findings；findings remediation completed；findings-only independent recheck `PASS`；final P0-5E outcome `PASS`。
- 目标：建立内部 V0.1 的 username/password identity、稳定 UUIDv4 `user_id`、PostgreSQL-backed opaque Cookie session 与 authenticated current-user boundary。
- In scope：Argon2id password security、`users`/`auth_sessions` persistence、第一批真实 identity migration、FastAPI DB lifecycle、register/login/logout/me、host-only HttpOnly Cookie、credentialed explicit CORS、Origin/custom-header CSRF、最小 Web auth round trip 与分层安全测试。
- Out of scope：email/phone/SMS/WeChat/OAuth、JWT/refresh token、MFA、V0.1 self-service recovery、profile/account center、RBAC/permissions、payment、Redis session、训练业务 persistence 及其他 P1+ 能力。
- Dependencies：P0-3、P0-4、Accepted `ADR-015`；每个实施子步骤仍需用户明确批准。
- Acceptance criteria：五阶段全部完成并经 P0-5E 独立验收后，P1 可依赖稳定 `user_id`、authenticated current user、request-scoped `AsyncSession`、identity migration、secure Cookie session 及真实浏览器 register/login/logout/me 闭环；不得把 Deferred 能力描述为已实现。

### Substep progress

- `P0-5A — Identity preflight / security & scope freeze`：completed；
- `P0-5B — Identity persistence + migration + security primitives`：completed；
- `P0-5C — Backend auth runtime + FastAPI DB lifecycle + API`：completed；
- `P0-5D — Web auth round trip + CORS/CSRF + cross-layer validation`：completed；
- `P0-5E — Independent final review`：completed；PASS after findings remediation and independent recheck。

### P0-5A completion note

- 用户已批准 `ADR-015`：P0/V0.1 使用 username/password、Argon2id、稳定 UUIDv4 `user_id` 与 PostgreSQL-backed opaque server-side session；当前不采用 JWT；
- raw session token 只允许存在于 HttpOnly Cookie，数据库只持久化 cryptographic digest；
- CORS 与 CSRF exact Origin validation 必须共用现有 typed browser trusted-origin Source of Truth；
- P0-5B 需显式配置并 benchmark Argon2 参数，实施 small application-owned offline full-password blocklist；
- V0.1 self-service recovery Deferred，公开测试前必须设计 verified recovery identity/flow；
- 本子步骤只完成治理、架构、范围与 execution plan，不包含 identity/auth 代码、依赖、migration、schema、endpoint 或 Web 实现。

详细 scoped baseline、迁移门禁和各子步骤 exit criteria 见 [`exec-plans/P0-5_identity-boundary.md`](exec-plans/P0-5_identity-boundary.md)。

### P0-5B completion note

- 唯一新增 direct runtime dependency 为 `pwdlib[argon2]>=0.3.0,<0.4`，解析 `pwdlib 0.3.1` 与 `argon2-cffi 25.1.0`，已在 CPython 3.14.7 验证；
- 已实现先校验 raw ASCII 的 canonical username、15–128 code-point password policy、small offline full-match blocklist、显式参数 Argon2id hash/verify/verify-and-update，以及 opaque token generation、32-byte SHA-256 digest 与 7-day absolute expiry primitives；
- 已建立 `users`、`auth_sessions` ORM models，`Base.metadata` 精确包含两张 product table；session primitive 与 integration persistence 验证 32-byte SHA-256 digest，无 Deferred field、relationship 或额外 product table；
- 已新增 identity revision `4fe43b42641b`，线性承接 immutable baseline `7c6ccd86b3c5`，fresh PostgreSQL migration/downgrade/re-upgrade/check 与 exact schema tests 全部通过；
- development database 已在 exact-name/read-only/schema preflight 后首次迁移至 identity head，重复 upgrade 为 no-op，未 downgrade、未写入测试 user/session；
- FastAPI DB lifecycle、auth routes 与 Cookie runtime 在 P0-5B closeout 时尚未开始，现已由 P0-5C 实现；credentialed CORS/CSRF 与 Web auth 当时也尚未开始，现已由 P0-5D 完成。

### P0-5C implementation note

- FastAPI lifespan 在 runtime boundary 按需解析 `DatabaseSettings`，创建 AsyncEngine/sessionmaker、写入 app state 并在 shutdown dispose；module import 与 OpenAPI generation 不需要 DB URL 或 PostgreSQL；
- request dependency 为每个请求创建独立 `AsyncSession`，只负责 lifecycle/rollback/close；register、login 与 logout 显式拥有 transaction；
- 已实现 `POST /auth/register`（201）、`POST /auth/login`（200）、`POST /auth/logout`（idempotent 204）与 `GET /auth/me`（200/401），公开 identity 仅含 `id`、`username`；
- `gia_session` 为 host-only HttpOnly、SameSite=Lax、Path=/、7-day Max-Age Cookie；local `Secure=false`，production 要求 typed `GIA_API_SESSION_COOKIE_SECURE=true` 并在不安全配置下 fail closed；数据库只持久化 SHA-256 digest，raw token 不进入普通 result repr；
- unknown user 与 wrong password 共用 generic 401，unknown path 执行固定非 secret Argon2id dummy verification；successful register/login 始终创建 fresh token，login rehash 与新 session 原子提交；
- unit 102、integration 18（skipped 0）、full 120 项通过；真实 auth integration 使用 Alembic head 上的隔离 `gia_p04e_*` PostgreSQL database；无新 dependency、lockfile、migration 或 schema change；
- FastAPI OpenAPI 与 Web generated derivative 已同步，`/auth/me` 使用 Cookie security scheme，无 Bearer/JWT；
- P0-5C 当时明确保持 `allow_credentials=false`，没有 CSRF、Web auth UI 或真实 browser auth acceptance；这些必要 browser security gates 现已由 P0-5D 完成。

### P0-5D implementation note

- Credentialed CORS 精确复用 `GIA_API_CORS_ORIGINS`，只允许 `GET`/`POST`、`Content-Type`/`X-GIA-CSRF`，并继续只暴露 `X-Request-ID`；无 wildcard 或第二套 trusted-origin 配置；
- `POST /auth/register`、`POST /auth/login`、`POST /auth/logout` 统一要求单一 exact trusted `Origin` 与单一 `X-GIA-CSRF: 1`，缺失、`null`、不受信任、重复或错误 header 均使用现有安全 error envelope 返回 `403 CSRF_REJECTED`；`GET /auth/me` 保持豁免；
- Web 正式 `openapi-fetch` client 统一使用 `credentials: "include"`，仅 unsafe auth POST 自动发送 CSRF marker；最小 UI 覆盖 loading、unauthenticated register/login、authenticated username、initial `/auth/me` restore 与 logout；
- Web 不对 raw ASCII username 做 lowercase mutation；backend canonical lowercase username 在 register response、authenticated UI 与 reload restore 中保持一致；
- 新增唯一获批 Web direct dev dependency `@playwright/test 1.62.1`，只运行 Chromium；隔离编排器创建并迁移精确 `gia_p05d_*` PostgreSQL database，启动 API/Web，运行浏览器测试后在成功/失败路径停止服务并精确删除临时库；
- 真实 Chromium 已验证 register、HttpOnly/host-only/SameSite=Lax/Path=/ Cookie、`document.cookie` 不可见、reload restore、browser storage 无 auth secret、missing-CSRF `403`、logout、后续 `/auth/me` `401` 与 Cookie 清除；selected 1、skipped 0、passed 1；
- Windows Uvicorn runtime 现通过 custom loop factory 显式使用 Psycopg-compatible `SelectorEventLoop`；未新增 API dependency，development DB 保持 head `4fe43b42641b` 且 `users`/`auth_sessions` 均为 0；P0-5D actual-source final review 已通过并转为 completed；P0-5E initial independent review verdict 为 `BLOCKED`，两个 findings 已完成 remediation，并通过 findings-only independent recheck；P0-5E final outcome 为 `PASS`，P0-5 已转为 `DONE`。

## P0-6 — CI、日志与基础可观测性

- ID: `P0-6`
- 名称：CI、日志与基础可观测性
- Status: `DONE`
- Approval state：P0-6A completed，actual-source final review `PASS`，four review findings closed；P0-6B implementation、local parity、actual-source review、findings remediation 与 remote CI 均 `PASS`，已 completed；P0-6C implementation、API quality gates、actual-source review、finding remediation/re-review 与 remote CI 均 `PASS`，已 completed；P0-6D implementation、local gates、actual-source review、findings remediation/re-review 与 remote CI 均 `PASS`，已 completed；P0-6E cross-layer validation 与 P0-6 closeout `PASS`，已 completed。
- 目标：建立与当前代码规模匹配的自动检查、结构化日志和基础监控能力。
- In scope：GitHub Actions CI、现有 API/Web/PostgreSQL/Chromium quality gates automation、structured logging hardening、request/trace correlation、provider-neutral basic OpenTelemetry tracing、documentation 与 observability safety tests。
- Out of scope：deployment/CD、production hosting/secrets、alerting/on-call、dashboard、vendor observability backend/SDK、OpenTelemetry Collector deployment、OTel Logs pipeline、无真实 caller 的 metrics、product/AI/payment analytics 与 P0-7 final acceptance。
- Dependencies：P0-2、P0-3、P0-4、P0-5；每个实施子步骤仍需用户明确批准。
- Acceptance criteria：P0-6A～P0-6E 全部完成并通过实际源码审核；CI 可复现现有 quality gates；日志与 traces 可关联且不泄露敏感信息；tracing 默认关闭且无外部 backend 仍可运行/测试；P0-7 保持独立验收。

### Substep progress

- `P0-6A — Preflight / scope freeze / execution plan`：completed；actual-source final review `PASS`，four review findings closed；
- `P0-6B — GitHub Actions CI baseline`：completed；implementation、local parity、actual-source review、findings remediation 与 remote GitHub Actions run #1 均 `PASS`；
- `P0-6C — Structured logging hardening`：completed；implementation、API quality gates、actual-source review、finding remediation/re-review 与 remote CI 均 `PASS`；
- `P0-6D — OpenTelemetry tracing foundation`：completed；implementation、local API/full/Chromium gates、actual-source review、findings remediation/re-review 与 remote CI 均 `PASS`；
- `P0-6E — Cross-layer validation / P0-6 closeout`：completed；final API/Web/PostgreSQL/Chromium/CI、security/privacy、cleanup gates 与 7-file docs-only actual-source review 均 `PASS`。

详细 baseline、CI/logging/tracing 边界、dependency gate 与各子步骤 exit criteria 见 [`exec-plans/P0-6_ci-observability.md`](exec-plans/P0-6_ci-observability.md)。

### P0-6B implementation note

- 新增单一 `.github/workflows/ci.yml`，在 pull request 与 push-to-main 上以 read-only permissions 和 duplicate-run cancellation 执行 API quality、PostgreSQL integration/migration、Web quality/OpenAPI drift、Chromium E2E 四个 required jobs；
- 所有 external actions 使用 P0-6B live official preflight 核对的 full 40-character release commit SHA；无 cache action、write permission、production secret、deployment/CD 或 `continue-on-error`；
- API unit 132、PostgreSQL integration 18、Web Vitest 16、Chromium E2E 1 均通过，skipped 0；Alembic disposable database、DB-independent OpenAPI 与 cleanup gates 通过；
- application dependency、lockfile、runtime、schema、migration history、API contract 与 P0-6C/D observability runtime 均未修改；
- Remote CI verification completed / `PASS`：reviewed commit `513491af128849f93c3ae601a906bd88fd8860f4` 经 push-to-main 触发 GitHub Actions run #1，API quality、PostgreSQL integration and migration、Web quality and OpenAPI drift、Chromium E2E 四个 required jobs 均 completed / success；P0-6B completed。

### P0-6C implementation note

- project-owned logs 使用 stdlib newline-delimited JSON，冻结 `timestamp`/`level`/`event`/`logger` 核心字段、互斥 stdout/stderr、resolved route template 与 fixed unmatched classification；
- `http.request.completed`、`http.request.failed`、`app.startup.completed`、`app.shutdown.completed` 已有真实 caller；handled 4xx 不误分为 failed，未预建 `telemetry.export.failed`；
- request_id 与 `X-Request-ID`/error envelope 保持一致；exception 只记录固定安全 category，不记录 message/traceback；sentinel negative tests 证明 body/header/query/Cookie/session/credential/path/exception 数据不进入 application logs；
- initial targeted 53、API unit 139、PostgreSQL integration 18、API full 157、Ruff、format、Pyright 与 Alembic single-head checks 通过；actual-source review 发现的 `JsonFormatter` missing/malformed event fail-safe finding 已用固定 `logging.record.invalid` fallback 和安全 regression 修复，remediation source re-review `PASS`；
- Remote CI verification completed / `PASS`：reviewed commit `2d3d235d08aefb6b536ad6217a99c167fe879eb3` 经 push-to-main 触发 GitHub Actions CI run #4，四个 required jobs 均 completed / success；dependency/lockfile、schema/migration、API/OpenAPI contract、Web/CI workflow 与 P0-6D 均未改变；P0-6C completed。

### P0-6D implementation note

- 加入最小 OpenTelemetry API/SDK 与 OTLP HTTP exporter direct dependencies；2026-08-16 live official preflight 确认 1.44.0、Python 3.14 支持和实际 public APIs，lock graph 无 contrib instrumentation、metrics/logs pipeline 或 vendor SDK；
- tracing 默认关闭且不创建 provider/exporter；启用时由每个 FastAPI app lifespan 显式拥有 provider 与 OTLP HTTP `BatchSpanProcessor`，不设置 process-global provider；OTLP HTTP export timeout 为 5 秒，SDK BatchSpanProcessor shutdown 使用 OTel 1.44 自身 bounded shutdown semantics；collector 不可达不阻断 startup/request；
- 既有 request middleware 创建受控 `SpanKind.SERVER` spans，只接受 W3C `traceparent`；span 仅含 method、resolved route template、status、固定 error category 和 `service.name`，404 使用固定 `<unmatched>`，不记录 baggage、query/header/body/Cookie/identity/SQL/exception detail；
- project JSON logs 只从 active valid span context 增加固定宽度 `trace_id`/`span_id`，继续与既有 `request_id` 关联；exporter flush/shutdown failure 只产生安全 `telemetry.export.failed` category；
- targeted 56、API unit 165、PostgreSQL integration 18、API full 183、Ruff、format、Pyright、Alembic single-head/drift 与 Chromium 1 均通过；默认关闭、config fail-closed、sentinel leakage、provider isolation、database dispose 和 processor thread cleanup 均有回归；
- actual-source review 的 tracestate/Resource 与 ambient SDK/exporter config findings 均已 remediation 并通过 source re-review；reviewed commit `96581dd7c3f972dbe5d90592ee34d9973bd3dd41` 经 push-to-main 触发 GitHub Actions CI run #6，四个 required jobs 均 completed / success；P0-6D completed。该子步骤 closeout 时 P0-6、P0 均继续 `IN_PROGRESS`，P0-6E awaiting explicit user approval / not started，P0-7 not started。

### P0-6E closeout note

- frozen API sync/lock、unit 177、integration 18、full 195、Ruff、format 与 Pyright gates 均通过；Alembic single head、current head 与 schema drift checks 通过；
- Web frozen install、lint、format、typecheck、Vitest 16、production build、DB-independent OpenAPI drift 与真实 Chromium E2E 1 selected / 0 skipped 均通过；
- CI workflow 仍为四个 required jobs、read-only permissions、full-SHA action pins 和 duplicate-run cancellation，无 deployment/CD/write-secret scope creep；
- 既有 logging/tracing tests 覆盖 request/trace correlation、default-disabled tracing、project-owned provider/resource/sampler、traceparent-only propagation、ambient config fail-closed 与 sensitive sentinel negative boundaries；
- temporary database、3000/8000 listeners、Playwright artifacts 与 unexpected untracked artifacts residual 均为 0；本步骤未修改 runtime、workflow、dependencies、lockfiles、schema、migration、master plan 或 decisions；
- P0-6A～P0-6E completed，P0-6 转为 `DONE`；P0 整体保持 `IN_PROGRESS`，P0-7 保持 `TODO` / not started。
- P0-6E 7-file docs-only actual-source review `PASS`，无 blocker。

## P0-7 — P0 独立验收

- ID: `P0-7`
- 名称：P0 独立验收
- Status: `DONE`
- Approval state：independent final acceptance initial verdict `BLOCKED`；两个 documentation current-state findings 已 remediation；finding-only independent recheck `PASS`；new blockers none；P1 readiness `READY`。
- 目标：独立确认 P0 的基础能力和治理是否足以进入 P1。
- In scope：仓库、规范、架构、骨架、数据库基础、身份边界、CI/日志和决策记录验收。
- Out of scope：提前实现 P1 文字讨论闭环。
- Dependencies：P0-1～P0-6 完成。
- Acceptance criteria：P0 所有验收项有证据，遗留风险和 TBD 已记录，并通过独立最终验收；进入 P1 仍需单独获得用户明确批准。

### P0-7 closeout note

- initial independent verdict 为 `BLOCKED`：`ARCHITECTURE.md` 的 Alembic current head 描述错误，`DATABASE.md` 的 P0-5D browser-boundary status 过期；
- 两个 findings 均已完成 docs-only remediation；finding-only independent recheck `PASS`，new blockers none；
- P0-1～P0-7 completed，P0 转为 `DONE`；P1 readiness `READY`。该 P0-7 closeout 当时 P1 尚未获批；其后用户已明确批准进入 P1。

## P1-1 — Discussion session foundation

- ID: `P1-1`
- 名称：Discussion session foundation
- Status: `IN_PROGRESS`
- Approval state：用户已明确批准进入 P1 并执行 P1-1A；P1-1A completed；P1-1B～E not started / awaiting separate explicit approval。
- 目标：建立 authenticated session create/snapshot、versioned WebSocket、durable action idempotency、session monotonic sequence 和 snapshot + ordered-events reconnect 的第一条文字会话 vertical slice。
- In scope：最小 session/action/event persistence、REST create/snapshot、WS v1 command/event/error contract、opaque Cookie authentication/owner authorization、shared trusted-origin Origin validation、transaction/concurrency、deterministic regression、最小 Web caller 和最终独立验收。
- Out of scope：question CMS/schema、participant、utterance、完整讨论状态机/调度/记忆、LLM/provider、六维评分/报告、voice/ASR/TTS、Redis、task queue、payment/entitlement/growth/industry pack。
- Dependencies：P0 `DONE`；Accepted `ADR-003`、`ADR-005`～`ADR-015` 中相关边界；每个实施子步骤仍需用户明确批准。
- Acceptance criteria：P1-1A～E 全部完成并经 P1-1E 独立验收后，第一条 session vertical slice 可在真实 PostgreSQL 与 browser 中证明 server authority、owner isolation、durable idempotency、race-free ordered events 和 reconnect；不得把 Deferred 能力描述为已实现。

### Substep progress

- `P1-1A — Preflight / scope freeze / execution plan`：completed；docs-only；未修改 runtime/tests/migration/schema/dependency/CI；
- `P1-1B — Session persistence + migration foundation`：`TODO`；not started；
- `P1-1C — Backend REST + WebSocket vertical slice`：`TODO`；not started；
- `P1-1D — Web realtime caller + reconnect cross-layer validation`：`TODO`；not started；
- `P1-1E — Independent final review / P1-1 closeout`：`TODO`；not started。

### P1-1A completion note

- 从 clean `main` HEAD `118aa6d298bd80a5868da2457484c1609ab77d3f` 恢复 Source of Truth 和 actual API/DB/identity/Web/tests；P0-7 final closeout 已在当前 main；
- 冻结三张首批真实 caller tables：`simulation_sessions`、`session_actions`、`discussion_events`；question version、participant、utterance 保持 additive future boundary；
- 冻结 `POST /sessions`、`GET /sessions/{session_id}`、`/ws/sessions/{session_id}?after_sequence=`，以及 `session.abort`、`session.created`、`session.state_changed` 和 non-formal safe WS error；
- `action_id` 作用域为 `(session_id, action_id)` 并持久化；sequence 由锁定 session row 后的 durable counter 区间分配，不使用 `MAX()+1`，一个 action 可关联多 event；
- reconnect 使用 REST snapshot `last_sequence` + ordered WS catch-up；gap 触发重新获取 snapshot，client 不成为 state authority；
- CORS/CSRF/WS Origin 共用既有 `Settings.cors_origins`，WS 复用 opaque Cookie identity 和 owner authorization；无第二套配置、JWT、Redis 或 queue；
- 无 Proposed Decision 或 blocker。完整 scoped schema、contract、B～E acceptance 和风险见 [`exec-plans/P1-1_discussion-session-foundation.md`](exec-plans/P1-1_discussion-session-foundation.md)。

## 任务更新规则

- 开始任务：用户明确批准后设为 `IN_PROGRESS`。
- 完成实现：验证通过并提交 diff；若验收要求用户审核，审核前仍保持 `IN_PROGRESS`。
- 阻塞任务：只有真实外部依赖阻止继续时设为 `BLOCKED`，并写明解除条件。
- 完成任务：满足全部验收条件后设为 `DONE`。
- 范围变化：先更新决策或获得批准，再修改任务范围。
