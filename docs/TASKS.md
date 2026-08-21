# 当前任务清单

- Status: P1 in progress; P1-1, P1-2, and P1-3 completed; P1-4 in progress
- Managed scope: P1-4A/P1-4B/P1-4C/P1-4D completed; P1-4E remains unstarted and requires explicit approval
- Most recently completed subphase: P1-4D — `DONE`
- P0-7 final outcome: initial verdict `BLOCKED` with two documentation findings; remediation completed; finding-only independent recheck `PASS`; new blockers none; P1 readiness `READY`
- Current phase: P1 — `IN_PROGRESS`
- Most recently completed task: P1-4D — `DONE`; P1-4 — `IN_PROGRESS`
- Next task gate: P1-4E — `TODO` / not started / awaiting explicit user approval
- P0 status: `DONE`; P0-1 through P0-7 completed
- Allowed status values: `TODO` / `IN_PROGRESS` / `BLOCKED` / `DONE`
- Related roadmap: [`ROADMAP.md`](ROADMAP.md)

用户已明确批准正式进入 P1、P1-2A～D、P1-3、P1-4 和 P1-4B～D；P1-2 与 P1-3 均已在 independent verdict `PASS` 后完成。P1/P1-4 保持 `IN_PROGRESS`；P1-4A～D 已完成，P1-4E 未开始并等待单独明确批准，不得提前开始 independent closeout、LLM/utterance、记忆、报告、语音、Redis/queue 或 P2～P6。

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
- Status: `DONE`
- Approval state：用户已明确批准进入 P1；P1-1A～E completed；P1-1 independent final verdict `PASS`。
- 目标：建立 authenticated session create/snapshot、versioned WebSocket、durable action idempotency、session monotonic sequence 和 snapshot + ordered-events reconnect 的第一条文字会话 vertical slice。
- In scope：最小 session/action/event persistence、REST create/snapshot、WS v1 command/event/error contract、opaque Cookie authentication/owner authorization、shared trusted-origin Origin validation、transaction/concurrency、deterministic regression、最小 Web caller 和最终独立验收。
- Out of scope：question CMS/schema、participant、utterance、完整讨论状态机/调度/记忆、LLM/provider、六维评分/报告、voice/ASR/TTS、Redis、task queue、payment/entitlement/growth/industry pack。
- Dependencies：P0 `DONE`；Accepted `ADR-003`、`ADR-005`～`ADR-015` 中相关边界；P1-2 及后续任务仍需用户明确批准。
- Acceptance criteria：P1-1A～E 全部完成并经 P1-1E 独立验收后，第一条 session vertical slice 可在真实 PostgreSQL 与 browser 中证明 server authority、owner isolation、durable idempotency、race-free ordered events 和 reconnect；不得把 Deferred 能力描述为已实现。

### Substep progress

- `P1-1A — Preflight / scope freeze / execution plan`：completed；docs-only；未修改 runtime/tests/migration/schema/dependency/CI；
- `P1-1B — Session persistence + migration foundation`：completed；
- `P1-1C — Backend REST + WebSocket vertical slice`：completed；
- `P1-1D — Web realtime caller + reconnect cross-layer validation`：completed；
- `P1-1E — Independent final review / P1-1 closeout`：completed；independent verdict `PASS`；findings none。

### P1-1A completion note

- 从 clean `main` HEAD `118aa6d298bd80a5868da2457484c1609ab77d3f` 恢复 Source of Truth 和 actual API/DB/identity/Web/tests；P0-7 final closeout 已在当前 main；
- 冻结三张首批真实 caller tables：`simulation_sessions`、`session_actions`、`discussion_events`；question version、participant、utterance 保持 additive future boundary；
- 冻结 `POST /sessions`、`GET /sessions/{session_id}`、`/ws/sessions/{session_id}?after_sequence=`，以及 `session.abort`、`session.created`、`session.state_changed` 和 non-formal safe WS error；
- `action_id` 作用域为 `(session_id, action_id)` 并持久化；sequence 由锁定 session row 后的 durable counter 区间分配，不使用 `MAX()+1`，一个 action 可关联多 event；
- reconnect 使用 REST snapshot `last_sequence` + ordered WS catch-up；gap 触发重新获取 snapshot，client 不成为 state authority；
- CORS/CSRF/WS Origin 共用既有 `Settings.cors_origins`，WS 复用 opaque Cookie identity 和 owner authorization；无第二套配置、JWT、Redis 或 queue；
- 无 Proposed Decision 或 blocker。完整 scoped schema、contract、B～E acceptance 和风险见 [`exec-plans/P1-1_discussion-session-foundation.md`](exec-plans/P1-1_discussion-session-foundation.md)。

### P1-1B completion note

- 新增 `simulation_sessions`、`session_actions`、`discussion_events` 三张精确 scoped tables 及 ORM metadata；状态为可演进 `VARCHAR`，没有 PostgreSQL native enum、question/participant/utterance 或其他 speculative schema；
- revision `f1a11d15c001` 线性承接 immutable identity head `4fe43b42641b`，保持 single head；fresh/repeat/check、downgrade-to-identity/re-upgrade 和 exact PostgreSQL catalog assertions 通过；
- `(session_id, action_id)` composite primary key、`(session_id, sequence)` composite primary key、nullable composite causation foreign key 与 replay index 建立 durable idempotency、ordered events 和一 action 多 events 的 persistence boundary；
- 真实 PostgreSQL regression 证明 session row `FOR UPDATE` + durable `last_sequence` 可串行化并发 sequence allocation，transaction rollback 不留下 action/event/watermark partial state；command/domain service 已在其后的 P1-1C 实现；
- development database 经 exact-name、identity-head、two-table schema 与 row-count read-only preflight 后只向前迁移至 `f1a11d15c001`；repeat upgrade 为 no-op，未 downgrade development；
- P1 / P1-1 保持 `IN_PROGRESS`；P1-1C 当时尚未开始，其后已完成；P1-1D～E 继续要求 separate explicit approval。

### P1-1C completion note

- 实现 authenticated `POST /sessions` 与 owner-only `GET /sessions/{session_id}`；创建 transaction 原子写入 `CREATED` session 与 sequence `1` 的 `session.created`，snapshot 精确返回五个冻结字段，missing/non-owner 共用 `404 SESSION_NOT_FOUND`；FastAPI OpenAPI 与 Web generated derivative 已同步；
- 新增轻量 `modules/discussion_sessions` domain/contracts/service/routes/realtime 边界；纯 domain 确定性实现 `CREATED -> ABORTED_USER`，唯一 v1 command `session.abort` 产生 `session.state_changed`，未创建 repository/interface/factory/provider/event bus；
- command service 在短 transaction 内以 owner predicate 锁定 session row，先检查 durable `(session_id, action_id)`，再推进 state/`last_sequence` 并写入一到多条 contiguous events；duplicate 重放原 stored events，semantic conflict 与 invalid state 均不产生 mutation；没有 `MAX(sequence)+1`、process-local lock 或 network-before-commit；
- `/ws/sessions/{session_id}?after_sequence=` 复用 opaque `gia_session` current-user lookup 和 `Settings.cors_origins` exact Origin Source of Truth，在 accept 前验证 auth/owner；实现 ordered PostgreSQL catch-up、ahead reload error、durable duplicate/lost-send reconnect、recoverable domain errors、protocol `1008` 与 internal `1011`；只向 originating connection 投递；
- realtime logs 只增加 validated UUIDv4 `session_id`/`connection_id`/`action_id` 与 positive sequence；negative tests 证明 payload、Cookie/token、Origin、raw path/query 和 exception sentinel 不进入 safe errors/application logs；未增加 WebSocket tracing propagation；
- API unit `201`、PostgreSQL integration `38`、API full `239`、Ruff、format、Pyright、Alembic single-head/current/drift、Web lint/format/typecheck/Vitest `16`/build 与 OpenAPI drift 均通过；没有 schema/migration、CI 或 Web `lib/realtime` 修改；
- actual-source review finding F1 发现 bare Uvicorn 缺少真实 WebSocket protocol backend；获批 finding-only exception 以 direct `websockets>=16.0,<17` 和 frozen lock update 修复，并用 disposable PostgreSQL + 真实 Uvicorn 进程验证 Upgrade、catch-up 与 `session.abort`；未引入 `uvicorn[standard]` extras，也未改变 REST/WS/domain contract；
- P1-1C closeout 时 P1 / P1-1 保持 `IN_PROGRESS`、P1-1D～E 未开始；其后的 P1-1D 只在本轮单独批准后实施。

### P1-1D completion note

- 新增有真实 authenticated caller 的 `lib/realtime` v1 derivative parser/client 与最小 session panel；Browser 只投影 REST snapshot + ordered WS events，不在 local/session storage 保存 Cookie/token、action queue、payload 或 authoritative state；
- pending `session.abort` 在内存中保留稳定 UUIDv4 `action_id` 并在 reconnect 后重发；matching duplicate replay 可确认 pending action 但不重复应用 mutation，client 仅应用精确 next sequence；
- sequence gap 会停止应用 incrementals、重新加载 authoritative REST snapshot 并以新 watermark 重连；connection generation 与 React cleanup 阻止 stale socket/remount 覆盖新 state 或产生双连接；
- disposable `gia_p11d_*` PostgreSQL + 真实 Next/Chromium/Uvicorn E2E 以 opaque Cookie 和 trusted Origin 验证 create、sequence `1` catch-up、abort sequence `2`、相同 action replay、REST reload restore；数据库精确为一个 action 与 events `[1, 2]`，2 个 Chromium tests zero skips，进程、端口和临时库清理完成；
- actual-source review finding F1 的 reconnect budget 已改为有界的连续恢复失败预算；健康连接稳定后会重置预算，独立的后续断线可再次有界重连，rapid open-close 失败仍不会形成无限循环；deterministic regressions 已覆盖成功恢复但无 formal event 后的第二次断线与持续失败上限；
- API non-integration `201`、PostgreSQL integration `39`、API full `240`、Web Vitest `37`、Ruff、format、Pyright、Web lint/format/typecheck/build、Alembic heads/current/check 与 REST OpenAPI drift 均通过；无 dependency/lockfile、CI、backend contract、schema 或 migration 变化；
- P1 / P1-1 保持 `IN_PROGRESS`；P1-1E 未开始，不自动进入独立 final review。

### P1-1E completion note

- 从 clean committed `main` HEAD `252ca9524c459ce19d11190ae17059d55c5bd0c1` 独立恢复 Source of Truth，并重新审计 P1-1A～D actual-source diff；不依赖此前 PASS 或 GitHub CI 结论；
- 三表 migration/schema、locked-row sequence allocation、durable idempotency/rollback、REST auth/CSRF/owner nondisclosure、WS Origin/auth/commit-before-send/catch-up、安全 errors/logging、browser stable action/replay/gap/reconnect/stale-socket 边界均独立复核通过；未发现 blocker 或 material finding；
- `uv sync --frozen`、`uv lock --check`、Ruff、format、Pyright、API non-integration `201`、PostgreSQL integration `39`、API full `240`、Web lint/format/typecheck、Vitest `37`、production build、OpenAPI drift、Alembic single-head/current/drift 全部通过；
- disposable `gia_p11d_*` PostgreSQL + 真实 Next/Chromium/Uvicorn E2E 为 `2 passed` / zero skips，并复证一个 durable action、events `[1, 2]`、REST reload restore；测试后临时数据库残留为 `0`、端口 `3000`/`8000` clean、生成测试产物已清理；
- development PostgreSQL 在独立验收前后均为 revision `f1a11d15c001`、精确五张 product tables、各表 `0` rows；P1-1 转为 `DONE`，P1 保持 `IN_PROGRESS`，P1-2 未开始并等待用户明确批准。

## P1-2 — Question & Persona foundation

- ID: `P1-2`
- 名称：Question & Persona foundation
- Status: `DONE`
- Approval state：用户已明确批准 P1-2A～D；四个子步骤 completed；independent final verdict `PASS`。
- 目标：建立 stable Question Template identity、immutable published Question Version、stable-behavior Persona Template，以及 question-version-specific Persona Assignment / Private Stance，并让后续 session 绑定不可变版本且不泄露私有立场。
- In scope：P1-2A design freeze；后续经单独批准的 P1-2B persistence/domain/seed、P1-2C safe API/session/Web vertical slice、P1-2D independent acceptance。
- Out of scope：完整 CMS/RBAC/审批流、AI 自动出题、12 道正式内容生产、LLM/provider、participant/utterance、完整状态机/调度/记忆、scoring/report、Redis/queue/voice 和行业题包插件。
- Dependencies：P1-1 `DONE`；Accepted `D-007`、`D-012`～`D-014`、`ADR-003`、`ADR-005`～`ADR-007`、`ADR-011`～`ADR-015`；每个实施子步骤仍需用户明确批准。
- Acceptance criteria：P1-2A～D 全部完成并经独立验收后，published question bundle append-only、历史 session 精确绑定原 version、Persona Template 不绑定题目观点、Private Stance 保持 server-only、类型/难度可演进、结构化内容和 numeric parameters 有明确 validation boundary，且 retirement/deletion 不破坏历史追溯。

### Substep progress

- `P1-2A — Design freeze`：completed；docs-only；未修改 runtime/tests/schema/migrations/dependencies/lockfiles/CI；
- `P1-2B — Persistence + Domain + Seed foundation`：completed；
- `P1-2C — API + Session integration + minimal Web vertical slice`：completed；
- `P1-2D — Independent acceptance + closeout`：completed；independent verdict `PASS`。

### P1-2A completion note

- 从 clean committed `main` HEAD `895a1d432150af198373f43dedd5a97af23f1ea9` 恢复总纲、Accepted Decisions、P1-1 actual source 和题目/角色/数据库/API 文档；总纲 SHA-256 保持 `2388A9660320406CB35D5354126AD71C6849A98DB7C4A356796CA951BF372F26`；
- 冻结 Question Template stable identity 与 immutable Question Version 边界；session 后续只绑定 version UUID，不绑定 template/latest/current pointer；
- 冻结 Persona Template 只承载稳定行为、Assignment/Private Stance 属于具体 question version，V0.1 四种基础模板为逻辑分析者、创意发散者、温和协调者、强势控场者；
- 冻结 question type/difficulty 可演进 code、closed structured content、numeric parameter validation、private non-disclosure、retirement/restrict deletion 和历史 session traceability；
- P1-2A domain boundary 由 execution plan 与对应领域文档冻结；不新增 Accepted 或 Proposed ADR；未经单独批准新增的 Accepted ADR 记录已在 governance finding remediation 中删除；
- 完整 B～D scope、dependency、expected caller、acceptance、testing strategy 和 stop conditions 见 [`exec-plans/P1-2_question-persona-foundation.md`](exec-plans/P1-2_question-persona-foundation.md)；
- 该 note 记录 P1-2A 当时的交付边界；P1-2B 后续已获明确批准并完成，当前等待 P1-2C 单独批准。

### P1-2B completion note

- 新增五张精确 question/persona tables、nullable `simulation_sessions.question_version_id` 与线性 Alembic head `f1a12b15c002`；历史 revisions 未改写；
- strict closed domain validation 将 template identity、immutable version、stable Persona behavior 和 version-specific assignment/private stance 分离；type/difficulty/background 使用 validated string registry，无 PostgreSQL native enum 或 catch-all content/parameter blob；
- application writer 对 published bundle 只允许 insert 或 exact-match no-op；同版本 drift 拒绝，新 version 追加不覆盖旧 version；retirement 和 session `ON DELETE RESTRICT` 保留历史追溯；
- deterministic seed 精确建立四种 V0.1 Persona Template 和一个明确标记、不计入 12 道正式题的 internal-validation bundle；重复执行 no-op，stable-code drift 在单一事务内失败；
- exact metadata/catalog、numeric/structured checks、private one-to-one、seed、immutability、retirement、single-head、fresh/repeat/downgrade/re-upgrade 和 P1-1 regression gates 通过；未新增 HTTP/WS/Web/dependency/lockfile/CI；
- P1-2C 与 P1-2D 后续均已完成；P1-2 independent final verdict `PASS`，当前状态为 `DONE`。

### P1-2C completion note

- 从 clean committed `main` HEAD `cc05b6be938cec845f45e8142123b2185e85c5cb` 开始，确认与 `origin/main` 一致且 P1-2A/B 已提交完成；总纲 SHA-256 保持 `2388A9660320406CB35D5354126AD71C6849A98DB7C4A356796CA951BF372F26`；
- 新增 authenticated `GET /questions` 与 `GET /questions/{question_version_id}` safe public projection；draft/missing 使用 non-disclosing not-found，retired published version 仍可按 immutable ID 供历史 session 解析；
- `POST /sessions` 只接受 closed `{question_version_id}`，在同一事务内验证 published、non-retired、template/persona availability 与完整三席 assignment/private stance 后保存 exact FK；snapshot additive 返回 nullable `question_version_id` 以兼容 P1-1 legacy row；
- ordinary OpenAPI/REST/WebSocket/browser/log surfaces 只使用显式 public allowlist；negative sentinel 覆盖 Private Stance、persona calibration 与内部题目 calibration 不泄露；未创建内部 endpoint 或 speculative AI abstraction；
- 最小 Web caller 通过 generated contract 完成题目选择、session 创建、safe content 展示与 reload 后按 authoritative snapshot 恢复同一 version；existing owner/CSRF/CORS、action idempotency、sequence、reconnect/gap 语义保持通过；
- API 281 tests、Web 42 tests、Ruff/format/Pyright/lint/typecheck/build、OpenAPI drift、Alembic、真实 PostgreSQL integration 与 2 项真实 Chromium E2E 均通过，zero skips；开发库经 exact-name/empty-row preflight 后只向前迁移到 `f1a12b15c002`，未 downgrade、未 seed；
- 正式 12 题、LLM/provider、participant/utterance、state machine/scheduler/memory、AI persona runtime、scoring/report、CMS/RBAC/approval、Redis/queue/voice 继续 Deferred；该 P1-2C checkpoint 未自动开始 P1-2D，后续独立验收结果见下方 P1-2D completion note。

### P1-2D completion note

- 从 clean committed `main` HEAD `5752f078e9343c64b5d234936252a66130ad7538` 独立复核 P1-2A～C actual source；HEAD 与 `origin/main` 一致，总纲 SHA-256 保持 `2388A9660320406CB35D5354126AD71C6849A98DB7C4A356796CA951BF372F26`；
- 独立重跑 API 228 项 non-integration、53 项 PostgreSQL integration、281 项 full suite，Web 42 项 tests、lint/format/typecheck/build、OpenAPI drift、Alembic head/drift 与 2 项真实 Chromium E2E；required skips 为 0；
- 复核 exact schema、published bundle insert-or-exact-match、deterministic seed/drift failure、retirement/history、Private Stance isolation、exact session version FK、auth/CSRF/ownership/WS/idempotency/reconnect regression 与 Deferred absence；无 blocker 或 material finding；
- development PostgreSQL 验收前后均为 `f1a12b15c002` 且保持 18 rows，不用于 destructive fixture；disposable databases、ports `3000`/`8000` 与 E2E processes 均清理完成；
- independent verdict `PASS`；P1-2D completed，P1-2 `DONE`，P1 保持 `IN_PROGRESS`；在该 closeout checkpoint，P1-3 尚未开始，其后已获批并完成 P1-3A。

## P1-3 — Session state machine

- ID: `P1-3`
- 名称：Session state machine
- Status: `DONE`
- Approval state：用户已明确批准并完成 P1-3A～D；P1-3D independent verdict `PASS`。
- 目标：建立 V0.1 server-authoritative 单向 session phase state machine、durable timing/deadline、deterministic concurrent transition、ordered formal events 和 restart/reconnect recovery。
- In scope：P1-3A design freeze；后续分别获批的 P1-3B backend state machine + durable phase foundation、P1-3C realtime/Web complete phase flow、P1-3D independent acceptance + closeout。
- Out of scope：P1-4 floor scheduling、AI speaker selection、participant/utterance runtime、LLM/provider、memory、report/scoring、Redis/queue、voice/device check 和完整 pause/system-failure engine。
- Dependencies：P1-1/P1-2 `DONE`；Accepted `D-003`、`D-008`、`ADR-003`、`ADR-005`～`ADR-015` 中相关边界；每个实施子步骤仍需用户明确批准。
- Acceptance criteria：P1-3A～D 全部完成并经独立验收后，状态只能沿冻结路径或合法 abort 推进；并发/duplicate/stale/timeout races 只有一个 durable result；server UTC deadline 在 reload/reconnect/restart 后不重置不漂移；Browser 只投影 authoritative state/timing/sequence。

### Substep progress

- `P1-3A — Design freeze`：completed；docs-only；未修改 runtime/tests/schema/migrations/dependencies/lockfiles/CI；
- `P1-3B — Backend state machine + durable phase foundation`：completed；
- `P1-3C — Realtime/Web complete phase flow`：completed；
- `P1-3D — Independent acceptance + closeout`：completed；independent verdict `PASS`。

### P1-3A completion note

- 从 clean committed `main` HEAD `b775106` 恢复总纲、Accepted Decisions、P1-1/P1-2 actual source 和 session/API/database/Web 文档；总纲 SHA-256 保持 `2388A9660320406CB35D5354126AD71C6849A98DB7C4A356796CA951BF372F26`；
- 冻结 V0.1 implemented path：`CREATED -> PREPARATION -> OPENING_STATEMENTS -> EXPLORATION -> CONFLICT_AND_EVALUATION -> CONVERGENCE -> FINAL_SUMMARY -> COMPLETED`，并保留合法 `ABORTED_USER`；
- 冻结 exact transition matrix：无跳阶段、倒退、active reopening 或 Browser-specified next state；abort 来源为 `CREATED` 和全部 timed active phases；`COMPLETED` / `ABORTED_USER` 在 P1-3 为 terminal；
- 冻结 server-owned duration plan、durable `phase_started_at` / `phase_deadline_at`、server UTC deadline arithmetic、overdue multi-phase catch-up 和 restart/reconnect no-drift semantics；
- 冻结 `session.start` / `session.abort` user intent 与 internal deadline transition 分离；用户 command 复用 durable action identity，所有 transition 复用 row lock、single transaction、monotonic sequence 和 commit-before-send；
- 冻结 formal vocabulary 为 `session.created` v1 + generalized `session.state_changed` v2，同时保留 historical v1 replay；snapshot additively 投影 current state/timing/`server_now`/sequence，Browser 不拥有状态机；
- `DEVICE_CHECK`、pause/system failure/partial completion 和 report states 保留总纲长期语义但 Deferred；无 Proposed Decision 或 blocker；
- 完整 B～D scope、acceptance、validation 和 stop conditions 见 [`exec-plans/P1-3_session-state-machine.md`](exec-plans/P1-3_session-state-machine.md)。

### P1-3B completion note

- 从 clean committed `main` HEAD `5fc7cdd6b4e12500b202475a8b7bd5ab4452c725` 开始，确认与 `origin/main` 一致，P1-3A 已提交完成且 P1-3B 获用户明确批准；
- 新增线性 Alembic revision `f1a13b15c003`，向 `simulation_sessions` additive 增加 `phase_started_at`、`phase_deadline_at`、`phase_duration_plan`，并保持十张 product tables、历史 revisions 未改写；
- 实现 exact P1-3A frozen status path、terminal behavior、pure deterministic domain transitions、server-owned closed duration plan、`session.start`、active-phase `session.abort`、overdue/deadline reconciliation foundation 和 locked transaction orchestration；
- `session.state_changed` 保留 historical v1 abort event parsing/replay；P1-3B start/abort/deadline transitions 使用 generalized v2 payload，REST snapshot additively 返回 authoritative timing 和 `server_now`，duration plan 不暴露给 Browser；
- duplicate action replay、stale start、terminal-state rejection、timeout vs user command precedence、multi-event sequence continuity、rollback atomicity、migration roundtrip、REST/WS/Web realtime parser compatibility、P1-1/P1-2 regressions 和真实 PostgreSQL concurrency gates 均通过；
- P1-3C 的 in-process deadline recovery loop、connected realtime phase catch-up/push、complete Web countdown/phase projection、restart/reload deadline preservation 和真实 Chromium complete-flow validation 已完成；P1-4 scheduling、participant/utterance、LLM/provider、memory、report/scoring、Redis/queue、voice/pause/failure/device-check/report lifecycle 继续 Deferred，未开始。

### P1-3C completion note

- 从 clean committed `main` HEAD `87afef4fc6b1926a3bef52116841e420a0f8b0ad` 开始，确认与 `origin/main` 一致，P1-3A/B 已提交完成且 P1-3C 获用户明确批准；
- 实现 app-owned in-process deadline recovery runtime：startup 从 durable `phase_deadline_at` 扫描并 reconcile overdue sessions，运行期 bounded async loop 按最近 active deadline wake-up，shutdown cancellable/awaited；未引入 Redis、queue、APScheduler、distributed scheduler 或未来 scheduler abstraction；
- WS connect 和 connected catch-up path 调用同一 deadline reconciliation foundation，deadline/user command race 继续复用 P1-3B aggregate row lock、single transaction、durable sequence/action replay 和 commit-before-send；
- Web 新增 `session.start` intent caller、authoritative phase/status/timing projection、phase timeline、server-deadline countdown display、reload/reconnect snapshot recovery；Browser 不提交 next state、duration 或 deadline，也不以 local countdown 推进状态；
- Backend targeted recovery/WS/session regression、API full suite、Alembic head/check、Web lint/type/test/build 和真实 Chromium E2E 均通过；其后 P1-3D 从 committed source 独立复现全部 acceptance gates 并完成 closeout。

### P1-3D completion note

- 从 clean committed `main` HEAD `529e58bf58268277473cbddf4f6d036466ee3411` 开始，确认与 `origin/main` 一致；总纲 SHA-256 保持 `2388A9660320406CB35D5354126AD71C6849A98DB7C4A356796CA951BF372F26`；
- 独立确认 F1 bounded Web restart recovery 和 F2 strict positive-integer duration validation 已进入 committed source；snapshot failure 继续 bounded backoff recovery，bool/float/string/zero/negative 在 config/domain boundary 均被拒绝；
- 独立复核 frozen transition matrix、durable deadline arithmetic、startup/WS unified reconciliation、aggregate lock/action idempotency/race precedence、v1/v2 realtime compatibility、Browser authority boundary 和全部 Deferred absence；无 unresolved Critical/High/Medium finding；
- API non-integration `260 passed`、真实 PostgreSQL integration `60 passed`、Web `50 passed`、Chromium `2 passed`；Ruff、format、Pyright、Web lint/typecheck/build、OpenAPI drift、Alembic head/current/check 和 cleanup gates 均通过；
- Independent verdict `PASS`；P1-3D completed，P1-3 `DONE`，P1 保持 `IN_PROGRESS`；P1-4 `TODO` / not started / awaiting explicit user approval。

## P1-4 — Floor control / speaker scheduling

- ID: `P1-4`
- 名称：Floor control / speaker scheduling
- Status: `IN_PROGRESS`
- Approval state：用户已明确批准 P1-4/P1-4B/P1-4C/P1-4D；P1-4A～D completed；P1-4E not started / awaiting explicit approval。
- 目标：建立 phase 内 server-authoritative、deterministic、可解释、可恢复且兼容 AI/human/system participant 的单一发言权调度边界；只决定谁说，不生成说什么。
- In scope：P1-4A docs-only design freeze；后续分别获批的 P1-4B scheduling persistence + domain foundation、P1-4C deterministic scheduler engine、P1-4D realtime/Web floor experience、P1-4E independent acceptance + closeout。
- Out of scope：LLM/provider、prompt orchestration、utterance generation、scoring/report、memory、Redis/queue、complex ML ranking、multi-agent negotiation、voice/ASR/TTS、emotion detection、human audio/video。
- Dependencies：P1-1/P1-2/P1-3 `DONE`；Accepted `D-003`、`D-007`、`D-008`、`D-013`、`ADR-003`、`ADR-005`～`ADR-015` 中相关边界；P1-4B～E 每个实施子步骤仍需用户明确批准。
- Acceptance criteria：P1-4A～E 全部完成并经 P1-4E 独立验收后，phase/floor authority 无漂移、每场最多一个 current floor owner、相同输入/policy 产生相同选择、fairness/monopoly/phase/intervention 可验证、AI/human/system 共享 participant model、decision/audit 可解释且不泄露 private stance/persona calibration/scoring，reload/reconnect/restart 从 durable truth 恢复。

### Substep progress

- `P1-4A — Floor control design freeze`：completed；docs-only；未修改 runtime/tests/schema/migrations/dependencies/lockfiles/CI；
- `P1-4B — Scheduling persistence + domain foundation`：completed；
- `P1-4C — Deterministic scheduler engine`：completed；
- `P1-4D — Realtime/Web floor experience`：completed；
- `P1-4E — Independent acceptance + closeout`：not started / awaiting explicit approval。

### P1-4A completion note

- 从 clean committed `main` HEAD `0fdf2c0034737044efcd986b1915fabe81f8a56c` 恢复总纲、Accepted Decisions、P1-1/P1-2/P1-3 actual-source baseline 和 session/API/architecture/agent docs；总纲 SHA-256 保持 `2388A9660320406CB35D5354126AD71C6849A98DB7C4A356796CA951BF372F26`；
- 冻结 P1-3 phase 控制 lifecycle、P1-4 floor 只控制 within-phase turns：floor 不推进、暂停、延长或修改 session phase/deadline，phase change 使旧 floor/candidate calculation 失效；
- 冻结 generalized participant（AI/HUMAN/SYSTEM actor + CANDIDATE/MODERATOR role）、single current owner、speaking opportunity、ephemeral candidate speaker、causal scheduler decision 和 intervention 领域边界；
- 冻结 V0.1 deterministic lexicographic policy：eligibility、opportunity class、未获 floor 优先、monopoly guard、phase-aware order、stable slot/UUID tie-break，以及 silence/deadline explainable intervention；不使用 LLM/ML/persona/private stance 决定 speaker；
- 冻结最小 formal facts 为 `floor.granted`、`floor.released`、`floor.intervention_requested`；event 是事实、decision 是原因、未来 LLM output 是后续内容；
- 冻结 durable participant/opportunity/current grant/decision audit/floor history 与 runtime candidate/fairness/timer calculation 的分界，并允许未来评分只消费可观察 floor facts，不把 scheduler reason 当作能力评分；
- 冻结 safe policy reason/decision metadata/audit trail，明确禁止泄露 Private Stance、hidden persona calibration、prompt、provider score 或 internal scoring；
- P1-4A 完成时无新增 Accepted/Proposed ADR、无 blocker；其后 P1-4B 已获单独批准并按下述 completion note 完成。完整 B～E scope、acceptance、validation 和 stop conditions 见 [`exec-plans/P1-4_floor-control.md`](exec-plans/P1-4_floor-control.md)。

### P1-4B completion note

- 从 clean committed `main` HEAD `100646c9d547521fb8fc67430385ebe27572f5c5` 开始，确认与 `origin/main` 一致且 P1-4B 已获明确批准；总纲 SHA-256 保持 `2388A9660320406CB35D5354126AD71C6849A98DB7C4A356796CA951BF372F26`；
- 在线性 revision `f1a14b15c004` 新增 generalized `session_participants`、durable `speaking_opportunities`、immutable `floor_decisions` / `floor_grants` / `floor_releases` / `floor_interventions`，回填既有 bound sessions 的四席 roster，并以 session-scoped deferred composite foreign key 将 `simulation_sessions.current_floor_grant_id` 限制为零或一个 current grant；
- API-created session 事务内建立 owner human candidate 与三个 AI candidates；schema 同时支持 `SYSTEM` moderator，但不创建 participant runtime、provider 或发言内容；
- floor command foundation 复用 owner authorization、aggregate row lock、`session_actions` semantic digest/idempotency、contiguous `discussion_events` sequence 和 commit-before-send boundary，实现 eligibility、grant/release、intervention、stale rejection、terminal protection 与 duplicate replay；
- phase deadline/abort 在既有 P1-3 aggregate transaction 内先记录安全的 `floor.released`，再记录 `session.state_changed`；floor 从不写 phase/status/deadline，且 cleanup 不延迟或否决 lifecycle transition；
- safe decision metadata 采用 closed allowlist，只保存 policy version/reason、phase、target/opportunity 和非私密 fairness/tie-break facts；Private Stance、persona calibration、prompt、provider/ranking weight 与 future scoring data 不进入 floor records/events/API；
- pure/domain/model/contract、真实 PostgreSQL concurrency/idempotency/rollback/cascade、migration downgrade/re-upgrade、P1-1/P1-3 regression、event sequence 与 OpenAPI drift gates 通过；无新增 ADR/dependency/lockfile/REST/Web UI。P1-4 保持 `IN_PROGRESS`；其后 P1-4C 已获单独批准并按下述 completion note 完成。

### P1-4C completion note

- 从 clean committed `main` HEAD `d6a6861ebc061d95303eda25254e55a5be875863` 开始，确认与 `origin/main` 一致且 P1-4C 已获明确批准；总纲 SHA-256 保持 `2388A9660320406CB35D5354126AD71C6849A98DB7C4A356796CA951BF372F26`；
- 新增 project-owned pure deterministic scheduler：只消费 authoritative phase/timing、generalized participant availability、open opportunity、durable grant/release history、derived fairness、closed typed policy 与 injected UTC；不消费 Persona、Private Stance、prompt、provider/model output、semantic score 或 Browser rank；
- 实现 closed lexicographic eligibility/opportunity class/first-opportunity/monopoly/phase-aware ordering，并以 stable seat order + UUID 完成最终 tie-break；consecutive/per-phase caps、silence/deadline/no-eligible intervention 均产生稳定 safe reason metadata；
- 内部 `floor.schedule` command 复用 owner authorization、session action digest/idempotent replay、aggregate `FOR UPDATE` lock、P1-3 overdue reconciliation 与 contiguous event sequence，在同一事务内重建公平输入并原子持久化 decision + grant/intervention；phase/current-grant/sequence stale 均 fail closed；
- deterministic enumeration-order、fairness/monopoly/phase/intervention unit regressions与真实 PostgreSQL duplicate/digest-conflict/concurrent-schedule/release-regrant/restart/phase-boundary/rollback/event-sequence gates 通过；无 migration、dependency、lockfile、public REST/OpenAPI、WebSocket inbound command 或 Web UI 变更；
- P1-4 保持 `IN_PROGRESS`；P1-4D 已完成，P1-4E 未开始并等待单独明确批准。LLM/provider、utterance、memory、scoring/report、Redis/queue、ML/semantic ranking、human audio/video 等继续 Deferred。

### P1-4D completion note

- `SessionSnapshotResponse` additively exposes an owner-authorized safe floor projection: generalized participant identity (`participant_id`、actor kind、seat order), zero-or-one current grant and the latest allowlisted lifecycle fact；decision metadata、ranking/weights、Private Stance/persona、prompt/provider 和 scoring fields remain server-only。
- The existing single versioned session WebSocket channel now has strict Web parsing/projection for `floor.granted`、`floor.released` and `floor.intervention_requested`; it reuses the discussion event sequence、duplicate suppression、gap reload、bounded reconnect and stale-generation guard without adding a second channel/protocol or Browser floor commands。
- Web renders current owner、public lifecycle status and safe reason text only. Browser cannot schedule、grant、release or mutate phase/deadline；P1-3 remains lifecycle authority and the server scheduler remains floor authority。
- Backend contract/privacy tests、real PostgreSQL snapshot/live/catch-up regressions、Web lint/typecheck/Vitest/build/OpenAPI derivative and real Chromium grant → live event → reload → API restart/reconnect → phase release flow passed；no migration、dependency、lockfile or Accepted ADR was added。

## 任务更新规则

- 开始任务：用户明确批准后设为 `IN_PROGRESS`。
- 完成实现：验证通过并提交 diff；若验收要求用户审核，审核前仍保持 `IN_PROGRESS`。
- 阻塞任务：只有真实外部依赖阻止继续时设为 `BLOCKED`，并写明解除条件。
- 完成任务：满足全部验收条件后设为 `DONE`。
- 范围变化：先更新决策或获得批准，再修改任务范围。
