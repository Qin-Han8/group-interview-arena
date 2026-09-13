# 当前任务清单

- Status: P1 in progress; P1-1 through P1-6 completed; P1-6 is `DONE / CLOSED`; P1-7 is `DONE / CLOSED`; P1-7A is `DONE / DESIGN_SCOPE_FROZEN / ACTUAL_SOURCE_REVIEW_PASS`; P1-7B, P1-7C and P1-7D are `DONE / ACTUAL_SOURCE_REVIEW_PASS`; P1-7E is `DONE / INDEPENDENT_ACCEPTANCE_PASS`; P1-8 is `NOT_STARTED`; P1-7D-F001～F005 are `CLOSED`; open findings `NONE`
- Managed scope: P1-7E/P1-7 docs-only governance closeout after external independent acceptance `PASS`; no production behavior, real provider, scoring, commercial behavior or P1-8 work
- Current acceptance checkpoint: P1-7E — `DONE / INDEPENDENT_ACCEPTANCE_PASS`; P1-7 — `DONE / CLOSED`; P1-8 remains `NOT_STARTED`
- P0-7 final outcome: initial verdict `BLOCKED` with two documentation findings; remediation completed; finding-only independent recheck `PASS`; new blockers none; P1 readiness `READY`
- Current phase: P1 — `IN_PROGRESS`
- Current governance checkpoint: P1-7E external independent acceptance is `PASS`; P1-7E is `DONE / INDEPENDENT_ACCEPTANCE_PASS`; P1-7 is `DONE / CLOSED`; content is `4/4/4 IMPLEMENTED / HUMAN_CONTENT_REVIEW_PASS`; open findings are `NONE`
- Latest completed acceptance: P1-7E is `DONE / INDEPENDENT_ACCEPTANCE_PASS`; P1-7 is `DONE / CLOSED`; open findings/new blockers are `NONE`
- Current task gate: P1-6 — `DONE / CLOSED`; P1-7 — `DONE / CLOSED`; P1-7A — `DONE / DESIGN_SCOPE_FROZEN / ACTUAL_SOURCE_REVIEW_PASS`; P1-7B/P1-7C/P1-7D — `DONE / ACTUAL_SOURCE_REVIEW_PASS`; P1-7D-F001～F005 — `CLOSED`; P1-7E — `DONE / INDEPENDENT_ACCEPTANCE_PASS`; P1-8 — `NOT_STARTED`; P1 remains `IN_PROGRESS`
- P0 status: `DONE`; P0-1 through P0-7 completed
- Allowed status values: `TODO` / `IN_PROGRESS` / `BLOCKED` / `DONE`
- Related roadmap: [`ROADMAP.md`](ROADMAP.md)

用户已明确批准正式进入 P1；P1 本身保持 `IN_PROGRESS`。P1-5A～P1-5F 的历史实现、review、commit/push、CI 和 acceptance 证据不变，P1-5F-4 的 `F4-ACC-001` 仍为 `CLOSED`，且 F4 accepted path 未调用 real provider/model。P1-5R later legitimately completed R1～R3、Final Composition Acceptance and Independent Acceptance，and the committed `PASS / CLOSED` closeout remains historical evidence。A later explicitly authorized post-closeout real-provider smoke exposed P1-5R-POST-001：provider-await cancellation could leave a generation request and AI floor durably stuck。The network-free remediation and review finding passed actual-source review，accepted commit `3b09d20a704c0fd3ff473ccb79311065b7e70408` has exact CI run `33257343273` green，P1-5R-POST-REV-001、P1-5R-POST-001 and P1-5R are `CLOSED`，parent P1-5 is `DONE`，and open findings are `NONE`。Formal R3.8 remains `NOT_EXECUTED / REQUIRES_SEPARATE_EXPLICIT_USER_AUTHORIZATION`；no further real-provider call occurred。

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
- Status: `DONE`
- Approval state：P1-4A～E completed；P1-4E independent acceptance final verdict `PASS`。
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
- `P1-4E — Independent acceptance + closeout`：completed；final independent verdict `PASS`。

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

### P1-4E completion note

- Initial independent review from clean committed `main` HEAD `170be9562c6e7dd3a833613ebf5ea4a53a354285` found one Low current-state documentation mismatch and correctly stopped without closeout；no runtime、test、schema、migration、dependency or CI repair was made during review。
- The finding was fixed in committed HEAD `e261bc7667366dd863671c6f8a31e4466424a16a` by changing only `ARCHITECTURE.md` from stale P1-4C wording to P1-4D；the finding-only check confirmed the documents agree。
- Full independent recheck reran governance、API `377 passed`、real PostgreSQL migration/catalog/concurrency/recovery、Ruff/format/Pyright、Alembic head/current/check、Web `57 passed`、lint/format/typecheck/build、current-source OpenAPI drift and Chromium `2 passed`；temporary databases and test ports were clean, and development database state was preserved。
- Final independent verdict `PASS` with findings `none`；P1-4E completed，P1-4 `DONE`，P1 remains `IN_PROGRESS`，and P1-5 is `NOT_STARTED` / awaiting explicit approval。

## P1-5 — AI Runtime Foundation

- ID: `P1-5`
- 名称：AI Runtime Foundation
- Status: `DONE`
- Approval state：P1-5A～P1-5F and the accepted P1-5R closeout retain historical `DONE / PASS / CLOSED` evidence；R1/R2-A/R2-B/R3 remain `DONE`；F1/F2/visual fidelity remediation/F3 remain `CLOSED`；Final Composition Acceptance and Independent Acceptance remain historical `PASS`；P1-5R-POST-REV-001 and P1-5R-POST-001 are `CLOSED` after remediation actual-source review `PASS` and exact accepted-commit CI green；open findings `NONE`。
- 目标：在既有 immutable question/persona、server-authoritative session lifecycle 与 deterministic floor control 之上，建立 provider-neutral、可追踪、可重试且不破坏 session integrity 的 AI utterance generation boundary。
- Historical completed closeout scope：P1-5R Final Composition Acceptance through the authorized network-free test harness，Independent Acceptance against the committed CI-green baseline，and exact governance-only closeout synchronization。
- Completed remediation scope：terminalize a claimed `RUNNING` generation as `FAILED / INTERNAL_ERROR` when its owning task is cancelled，then reuse existing `FAILED_REPLAY → INTERRUPTED → scheduler` recovery without retry or duplicates。
- Out of scope for this remediation：schema/migration、REST/OpenAPI/WS、scheduler policy、Prompt v2/recent context、Zhipu provider/model/config/timeout、Web production、dependencies and any further real-provider call。
- Dependencies：P1-1/P1-2/P1-3/P1-4 `DONE`；Accepted `D-003`、`D-007`、`D-008`、`D-013`、`ADR-006`、`ADR-007`、`ADR-009`、`ADR-011`～`ADR-014`。
- P1-5D acceptance result：the frozen Zhipu/configured-model/model-independent-configuration/request/timeouts are exact；provider/domain separation、safe error mapping、secret non-disclosure、one-request/no-retry behavior and existing P1-5C lifecycle/provenance invariants passed network-free tests and full PostgreSQL regression；HTTPX remains the single runtime dependency；no schema/API/WS/Web or automatic implementation was added；both actual-source reviews and the sanitized user smoke passed，so P1-5D is `DONE`。P1-5E-1 has separately passed its docs-only actual-source review with findings none and is `DONE`。

### Substep progress

- `P1-5A — AI Runtime Architecture Freeze`：completed；docs-only；
- `P1-5B — AI Runtime Persistence Foundation`：completed；three-table persistence + domain transaction foundation；no provider caller；
- `P1-5C — Runtime Contract & Deterministic Generation Vertical Slice`：completed；closed prompt/context、typed deterministic harness、short-transaction orchestration and durable replay/concurrency/stale-result behavior；
- `P1-5D — First Real Provider Integration`：`DONE`；implementation/config-driven patch actual-source reviews and final user-run sanitized real-provider acceptance smoke `PASS`；
- `P1-5E — Automatic AI Runtime Orchestration`：`DONE`；
- `P1-5E-1 — Automatic AI Runtime Orchestration Design Freeze`：`DONE`；docs-only actual-source review `PASS`；findings none；
- `P1-5E-2 — Single AI Turn Orchestration Kernel`：`DONE`；initial actual-source review `BLOCKED` on 3 findings；all 3 findings remediated；remediation actual-source re-review `PASS`，findings none；
- `P1-5E-3 — Continuous AI Drive + Composition Acceptance`：`DONE`；implementation actual-source review `PASS`，findings none；sanitized real-provider composition smoke `PASS`；
- `P1-5F — Realtime/Web Integration + Independent Acceptance`：`DONE`；
- `P1-5F-1 — Realtime/Public Contract Design Freeze`：`DONE`；docs-only contract accepted after finding remediation and finding-only external re-review `PASS`；
- `P1-5F-2 — Backend Text Discussion Transport`：`DONE`；initial implementation actual-source review `BLOCKED` on three findings，all remediated；finding-only external re-review `PASS`，findings none；reviewed remediation bundle SHA-256 `b9553cbe488707d5fd87598b70e48e1fabdf55a0ae6d3dab367b830267d61edd`；
- `P1-5F-3 — Web Discussion Experience`：`DONE`；
  - `P1-5F-3A — Web Discussion Functional Closure`：`DONE`；`DESIGN_FROZEN / IMPLEMENTATION_COMPLETE / ACTUAL_SOURCE_REVIEW_PASS / COMMIT_PUSH_COMPLETE / CI_PASS / INDEPENDENT_FINAL_ACCEPTANCE_PASS / FINDINGS_NONE_OPEN`；
  - `P1-5F-3B — Complete Discussion Page Composition`：`DONE` with `DESIGN_FROZEN / IMPLEMENTATION_PLAN_FROZEN / IMPLEMENTATION_COMPLETE / ACTUAL_SOURCE_IMPLEMENTATION_REVIEW_PASS / COMMIT_PUSH_COMPLETE / CI_PASS / F4_COMPOSITION_ACCEPTANCE_PASS / FINDINGS_NONE_OPEN`；committed implementation baseline `5efe1346532b95b7fabdd521015fd9f8199a457f`；GitHub Actions run `33044682226` `SUCCESS`；
- `P1-5F-4 — Composition E2E + Independent Acceptance`：`DONE`；accepted commit `af33d89baa0355ae1ee5174a2ef8cfb5e7b14554`；GitHub Actions run `33050532295` `SUCCESS`；independent final acceptance `PASS`；findings `NONE`；`F4-ACC-001 CLOSED`；network-free fake-provider composition only；no real provider/model call。
- `P1-5R — Local Acceptance Remediation`：`CLOSED`；R1/R2-A/R2-B/R3 and F1/F2/Visual fidelity remediation/F3 retain their accepted `DONE / CLOSED` states；previous Independent Acceptance and closeout remain historical `PASS / CLOSED` evidence。
- `P1-5R-POST-001 — Recover cancelled in-flight AI generation`：`CLOSED`；remediation actual-source review `PASS`；accepted commit `3b09d20a704c0fd3ff473ccb79311065b7e70408`；exact CI run `33257343273` `completed / success` with all four required jobs green；later post-closeout real-provider smoke discovery remains historical evidence；no further real-provider call。
- `P1-5R-POST-REV-001 — Real WebSocket teardown composition proof`：`CLOSED`；the existing network-free Browser harness proves durable `RUNNING`，actual reload/WebSocket teardown cancellation，normal reconnect/resume，exactly one `INTERRUPTED` release，continued scheduling and no retry、utterance or release duplicate for the cancelled grant；open findings `NONE`。
- P1-5F-2 and P1-5F-3A remain historical `DONE` with their previously recorded evidence。F3B implementation review、commit/push、CI and F4 composition acceptance passed with no findings open，so F3B and parent P1-5F-3 remain historical `DONE`。F4 initially `BLOCKED` on `F4-ACC-001`；finding-only remediation added network-free Human→AI Browser composition proof，its actual-source review passed，the accepted remediation commit and CI passed，and fresh independent final acceptance returned `PASS` with findings `NONE`；`F4-ACC-001` remains `CLOSED`。P1-5R Final Composition Acceptance、Independent Acceptance and the prior P1-5R/P1-5 closeout remain historical `PASS / CLOSED` evidence。The later post-closeout smoke exposed P1-5R-POST-001；its remediation review and exact accepted-commit CI passed，so P1-5R and parent P1-5 are closed/done with open findings `NONE`；P1 remains `IN_PROGRESS`。Formal R3.8 remains `NOT_EXECUTED / REQUIRES_SEPARATE_EXPLICIT_USER_AUTHORIZATION`。

### P1-5F-3A design-freeze checkpoint

- Baseline is clean committed `main` / `origin/main` `9fd31d0` with P1-5F-2 backend transport and realtime replay remediation complete；Master Plan SHA-256 remains `2388a9660320406cb35d5354126ad71c6849a98db7c4a356796ca951bf372f26`。
- Approved Option B keeps protocol parsing independent from React，puts the maximum-one memory-only pending command in the realtime client，keeps session/phase/floor truth in the authoritative snapshot，adds one pure framework-independent confirmed-transcript merge module，and leaves `SessionPanel` to coordinate draft/recovery presentation without a frontend business state machine。
- Draft、Pending Human submit、Confirmed transcript and one RejectedDraft are distinct。Textarea remains editable；Send requires a floor-enabled phase、exact Human current grant、connected socket、no pending command and valid exact content。Click time re-reads and binds the authoritative grant，generates one UUID4 action and never trims/normalizes/truncates content。
- Initial/recovery order is authoritative snapshot + watermark → complete transcript pagination → confirmed render → WS from the snapshot watermark。Transcript merge dedupes by `utterance_id`、orders by authoritative sequence and treats same-identity field drift as a full-reload conflict；transcript-only sequences are never gap-validated and confirmed history is not intentionally cleared during recovery。
- AI waiting/interruption UI derives only from the safe current floor、matching confirmed AI utterance and generic `INTERRUPTED` release。No provider/model/generation lifecycle、retry、ETA or Browser AI timeout is introduced。
- F3A implemented functional transcript/composer/pending/rejected/recovery UI in the existing panel and one deterministic Human Chromium vertical slice；final code gates are GREEN，including Vitest `150/150`、live OpenAPI drift and Chromium `2/2` with exact durable Human persistence semantics and zero provider request。External actual-source implementation review、commit/push、GitHub Actions run `32945590023` and independent final acceptance are all `PASS`/complete with no findings open，so F3A remains `DONE` at accepted commit `30446af520e55977a7c7a4839e00ab1a0a94d44e`。F3B and F4 later completed under separate approvals and are recorded in the current P1-5 status above。

### P1-5F-3B design-freeze checkpoint

- Baseline is clean committed `main` / `origin/main` `7421532db29b8e7c64a1dcce150803803ce21126` with unchanged Master Plan SHA-256 `2388a9660320406cb35d5354126ad71c6849a98db7c4a356796ca951bf372f26`；
- F3B freezes a commercial C-end `AI 群面训练场 / Interview Simulation Studio` composition：desktop three-region Task Brief / Live Discussion / Session Progress，discussion-first tablet support access and narrow `讨论 / 题目 / 进程` tabs；
- `SessionPanel` remains the authority coordinator；presentation children receive props/callbacks only，and F3A realtime、confirmed transcript、pending、rejected、recovery、Unicode and exact-floor semantics remain unchanged；
- Public Question fields、safe participant/floor facts、six authoritative phases、server timing and current connection facts are sufficient；notes are one page-local React string with no browser/backend persistence；
- P2 voice、P3 report/evidence and later conclusion/vote have layout seams only；no fake control/data is rendered and Option B is not prematurely replaced；
- Implemented F3B scope remained bounded to the existing Web app shell plus focused presentation components/tests under `features/sessions`；backend、contracts、generated schema、realtime/transcript authorities、dependencies、CI、provider/config and F4 authority remain unchanged；
- Full composition、lifecycle matrix、accessibility/visual system、future file map、executable acceptance and stop conditions are frozen in [`exec-plans/P1-5F-3B_complete-discussion-page-composition.md`](exec-plans/P1-5F-3B_complete-discussion-page-composition.md)；
- Exact current-source component interfaces、three integration batches、TDD commands、full gates and changed-file allowlist are frozen in [`exec-plans/P1-5F-3B_complete-discussion-page-composition-implementation.md`](exec-plans/P1-5F-3B_complete-discussion-page-composition-implementation.md)；
- F3B design actual-source review is `PASS` with findings `NONE` against `group-interview-arena-review-20260826-190658.zip` / SHA-256 `5867365d06fa6e0f1eb6d8f9dc5ec9dd9d806ed0ec444a909ef8266346ceba42`；implementation-plan findings `F3B-IP-001/F3B-IP-002` are `CLOSED`。Batch 3 captured valid terminal and wide-layout RED, applied minimal presentation fixes, and finished focused Vitest `48/48`、full Vitest `178/178`、typecheck、lint、format、build、live OpenAPI drift and Chromium `2/2` with one session across `1440x900`/`900x900`/`390x844`。F3B actual-source implementation review later returned `PASS` with findings `NONE`；implementation was committed at `5efe1346532b95b7fabdd521015fd9f8199a457f` and GitHub Actions run `33044682226` succeeded。F4 then supplied the required network-free composition acceptance，so F3B is `DONE` with all evidence tokens satisfied。

### P1-5F-4 final acceptance closeout

- Initial F4 acceptance was `BLOCKED` on `F4-ACC-001` because the Browser proof stopped at the durable Human path and did not prove scheduler-driven public AI composition。
- Finding-only remediation added one deterministic network-free provider boundary while preserving the real scheduler、continuous drive、generation-request and AI-utterance persistence、public event、WebSocket、Browser transcript and reload/API-restart recovery path；it made no real provider/model call。
- Remediation actual-source review: `PASS`；`F4-ACC-001 CLOSED`；open findings `NONE`。
- Accepted final commit: `af33d89baa0355ae1ee5174a2ef8cfb5e7b14554`；GitHub Actions run `33050532295` `SUCCESS`；fresh independent final acceptance `PASS` with findings `NONE`。
- Resulting hierarchy: `P1 IN_PROGRESS`; `P1-5 DONE`; `P1-5F DONE`; `P1-5F-3 DONE`; `P1-5F-3A DONE`; `P1-5F-3B DONE`; `P1-5F-4 DONE`。

### P1-5R design-freeze checkpoint

- Baseline is clean committed `main` / `origin/main` `91671fe1afc19a9dcc4341184c23500852f96780`；baseline CI run `33054731104` is `completed / success` for that exact head；Master Plan SHA-256 remains `2388a9660320406cb35d5354126ad71c6849a98db7c4a356796ca951bf372f26`。
- Real local acceptance reopened only parent P1-5 for four bounded findings：F1 progression correctness、F2 long-session viewport/follow UX、visual-fidelity remediation and F3 AI conversation quality。Historical P1-5A～P1-5F completion evidence is unchanged。
- Frozen remediation batches are R1 deterministic phase-entry progression recovery；R2-A bounded viewport/transcript ownership and new-message return affordance；R2-B faithful Interview Simulation Studio responsive composition；R3 prompt v2、bounded recent public context and pure Persona translation。
- Exact design contracts are frozen in [`exec-plans/P1-5R_local-acceptance-remediation.md`](exec-plans/P1-5R_local-acceptance-remediation.md)，and the executable batch/file/interface/TDD/gate plan is frozen in [`exec-plans/P1-5R_local-acceptance-remediation-implementation.md`](exec-plans/P1-5R_local-acceptance-remediation-implementation.md)。Batch R1、Batch R2-A、Batch R2-B and Batch R3 remain accepted and `DONE`；F1、F2、visual fidelity remediation and F3 remain `CLOSED`；Final Composition Acceptance、Independent Acceptance and the committed P1-5R/P1-5 closeout remain historical `PASS / CLOSED` evidence。The later post-closeout real-provider smoke exposed P1-5R-POST-001；its remediation actual-source review passed，accepted commit `3b09d20a704c0fd3ff473ccb79311065b7e70408` and exact CI run `33257343273` are green，P1-5R-POST-REV-001、P1-5R-POST-001 and P1-5R are `CLOSED`，parent P1-5 is `DONE`，and open findings are `NONE`。Formal R3.8 remains `NOT_EXECUTED / REQUIRES_SEPARATE_EXPLICIT_USER_AUTHORIZATION`；no further real-provider call occurred and the frozen contracts are unchanged。

### P1-5F-1 implementation checkpoint

- Baseline is clean committed `main` / `origin/main` `fa4e8b0123d55044c9c621068311db06524b93c6` with P1-5E `DONE` and unchanged master-plan SHA-256 `2388a9660320406cb35d5354126ad71c6849a98db7c4a356796ca951bf372f26`；
- Frozen protocol：Human text commands use `participant.utterance.submit` over WebSocket；REST remains authoritative for snapshot/history；`participant.utterance.created` v1 is the only formal Human/AI utterance event；`GET /sessions/{session_id}/utterances` is owner-only sequence-cursor transcript；
- Frozen floor compatibility：historical P1-4 floor-event v1 semantics stay unchanged；additive floor-event v2 keeps the same names/payload meanings but makes nullable `action_id` public-client causation only，with automatic scheduler/release/intervention projected as null and internal `SessionAction` private。F2/F3 must preserve and parse v1 alongside v2；
- Frozen authority/atomicity：server derives the exact Human participant/current grant；Human utterance+exact release are one transaction and scheduling is separate；AI `COMPLETED + AiUtterance + public event` are one transaction；all WS delivery is commit-before-send；
- Frozen recovery：same Human action replays exact content/identity；post-Human schedule identity is deterministic from session/released grant；existing P1-5E drives any resulting AI grant；crash/restart and disconnect recover from durable state without a second provider call or duplicate mutation；
- Frozen Browser/privacy：pending text is not formal transcript；REST/WS merge uses `utterance_id` plus authoritative sequence；transcript-only sequences need not be contiguous；AI loading derives only from current floor；new v2 projections exclude internal automatic action IDs，and provider/runtime/prompt/private/failure details plus utterance content in ordinary logs remain excluded；
- Actual-source stop-condition assessment found existing `DiscussionEvent`、Human participant/user identity、aggregate lock、FloorRelease、generation completion transaction and deterministic action/scheduler facts sufficient with no schema or P1-5E authority change；
- Full contract、F2～F4 acceptance and docs-only validation are in [`exec-plans/P1-5_ai-runtime-foundation.md`](exec-plans/P1-5_ai-runtime-foundation.md)。The initial actual-source review was blocked by one floor-event v1 `action_id` compatibility finding；the remediation preserved historical v1 and froze additive v2。Finding-only re-review is `PASS` with findings none against `group-interview-arena-review-20260825-110115.zip` / SHA-256 `6603b1f0377aa449d3a209e475fb3afbb74f9f83c9be38f84df97918eeb1ac0c`，so P1-5F-1 is `DONE`。At that F1 checkpoint there was no commit/push and F2 had not started；the current separately approved F2 status is recorded above。
- F2 external actual-source finding remediation restored the narrow F1 exact-floor command binding (`floor_grant_id + content`)，tightened transcript OpenAPI to exact Human/AI and five floor phases，and normalized projection/background catch-up failure handling。No unrelated F1 design was reopened；finding-only re-review is `PASS` with findings none against `group-interview-arena-review-20260825-150754.zip` / SHA-256 `b9553cbe488707d5fd87598b70e48e1fabdf55a0ae6d3dab367b830267d61edd`，so F2 is `DONE`。

### P1-5E-1 completion note

- Baseline is clean committed `main` / `origin/main` `a416d955920ec407c011c32602ac720a6d8080fd` with P1-5D `DONE` and unchanged master-plan SHA-256 `2388A9660320406CB35D5354126AD71C6849A98DB7C4A356796CA951BF372F26`；
- Freeze P1-5E as an application-level、state-driven coordinator：P1-3 owns lifecycle，P1-4 Floor Scheduler decides who，P1-5 AI Runtime decides what；durable state rather than exactly-once event delivery provides correctness；
- Existing exact authorities are `generate_ai_utterance(...)`、`apply_floor_command(...ReleaseFloorCommand...)` and `apply_scheduler_command(...ScheduleFloorCommand...)`；the orchestrator never directly writes floor/session facts or chooses a participant；
- One exact AI grant deterministically maps to generation request、utterance、release action、next-schedule action and scheduler child identities。Existing request timestamps/provenance and `SessionAction` digest semantics are replayed rather than replaced；
- Exact prompt selection is stable `AI_CANDIDATE_TURN` version `1` resolved to immutable `PromptVersion.id`；current development invocation is `zhipu` / server-configured model / `ZHIPU_CHAT_DEV_V1`；no hardcoded DB UUID or implicit latest；
- Confirmed completed utterance releases the exact current AI grant as `SPEAKER_FINISHED`；confirmed failed request releases it as `INTERRUPTED` while preserving typed `failure_code`；uncertain、conflict、internal、`RUNNING` or stale truth stops/re-reads without unsafe progression；
- Commit order is terminal generation → exact release → re-read → scheduler → re-read。P1-3 reconciliation facts always win；provider I/O remains outside transactions；
- Two concurrent drives converge through deterministic identities、one request claimant、unique utterance/grant constraints、aggregate lock、sequence/current-grant preconditions and deterministic scheduler children；no distributed lock or in-memory authority；
- P1-5E-2 is one AI turn + one release + one scheduler call；P1-5E-3 loops consecutive AI turns with `MAX_AUTOMATED_AI_TURNS_PER_DRIVE = 8` and stops at human/no-grant/intervention/lifecycle/reconciliation/budget boundaries；
- Existing nineteen-table schema plus deterministic `SessionAction`/floor/request/utterance facts is sufficient；no orchestration table/migration is planned。Full matrices and deferrals are in [`exec-plans/P1-5_ai-runtime-foundation.md`](exec-plans/P1-5_ai-runtime-foundation.md)。
- Actual-source review：`PASS`；findings：none；reviewed bundle SHA-256：`dae10e722244b1b6e73a5a360f6064c948bfaf5aa138c0d4b89b1f9961f35055`。At that checkpoint P1-5E-1 was `DONE`、P1-5E remained `IN_PROGRESS`、P1-5E-2 was separately approved and `IN_PROGRESS`，and P1-5E-3/P1-5F remained `NOT_STARTED`。

### P1-5E-2 implementation checkpoint

- Baseline is clean committed `main` / `origin/main` `754ea265a29da3b7829115d2ac29902a43550dfc` with unchanged master-plan SHA-256 `2388A9660320406CB35D5354126AD71C6849A98DB7C4A356796CA951BF372F26`；
- New application coordinator `ai_runtime/orchestration.py` reuses only `generate_ai_utterance(...)`、`apply_floor_command(...)` and `apply_scheduler_command(...)` for authoritative mutations；
- Stable per-grant identities、`FloorGrant.granted_at` request identity、exact `AI_CANDIDATE_TURN` v1 resolution、terminal outcome proof、exact release and deterministic scheduler recovery are implemented without a second AI-turn loop；
- Initial actual-source review verdict was `BLOCKED` on authoritative post-`CONTEXT_REJECTED`/`STALE_RESULT` classification、release/scheduler persistence uncertainty classification and missing concurrent post-release crash-E coverage。The remediation now re-reads exact durable authority，recovers only proved expected results，returns `STATE_CHANGED` only for proved grant/lifecycle change，and otherwise returns `RECONCILIATION_REQUIRED` without provider or mutation retry；
- Network-free tests cover HUMAN/non-floor/no-current/missing/invalid prompt、success/failure/SUPERSEDED、NO_GRANT/intervention replay、concurrency、crash A～F、release/scheduler persistence uncertainty、unrelated release、privacy isolation and P1-3 lifecycle precedence；new focused tests are `22 passed`，relevant regression is `98 passed`，full backend/PostgreSQL is `491 passed` with 1 existing Starlette deprecation warning；
- Remediation actual-source re-review：`PASS`；findings：none；reviewed bundle SHA-256：`69b5f23c131bff409d4455854e6b0526863aebe9b5a314894895d8e62d600795`；
- Final verified gates remain `22` focused tests、`98` relevant regressions and `491` full backend/PostgreSQL tests；real-provider calls remain zero；
- No schema/migration/dependency/lock/config/provider/runtime/service/API/WS/Web implementation change。At the P1-5E-2 closeout checkpoint，P1-5E-2 was `DONE`、P1-5E remained `IN_PROGRESS` and P1-5E-3/P1-5F remained `NOT_STARTED`；the current status is superseded by the P1-5E-3 final closeout below。

### P1-5E-3 final closeout

- Baseline is clean committed `main` / `origin/main` `de6ffdc5f98b2ec4549037f7fa3f96eeb83c7d31` with unchanged master-plan SHA-256 `2388A9660320406CB35D5354126AD71C6849A98DB7C4A356796CA951BF372F26`；
- New provider-neutral `drive_continuous_ai(...)` repeatedly consumes the frozen single-turn result and stops at HUMAN、no current work/grant、non-applicable lifecycle、intervention、state change、reconciliation or an exact `8` advanced-turn budget。Only a proved automatic release consumes budget；scheduler-only crash-E recovery does not；
- New lazy `drive_configured_ai_session(...)` constructs required Zhipu settings only when explicitly invoked and passes canonical `zhipu` / configured model / `ZHIPU_CHAT_DEV_V1` provenance plus the existing V0.1 scheduler policy。Missing configuration fails with a safe generic error before provider/drive execution；
- Real PostgreSQL tests prove consecutive AI → AI → HUMAN progression、terminal failure followed by a distinct AI、post-release crash-E recovery、concurrent convergence without duplicate provider/request/utterance/release and cancellation/re-entry with durable `RUNNING` reconciliation；
- Network-free gates are `47 passed` focused E3/E2、`253 passed` relevant runtime/floor/lifecycle and `516 passed` full backend/PostgreSQL with one existing Starlette deprecation warning；real-provider calls are zero；
- External implementation actual-source review：`PASS`；findings：none；reviewed implementation bundle SHA-256：`a2b453846f1ad1e94fa17b74ca507efe462c176d67471cae87278893bb907dd0`；
- User-run sanitized real-provider composition smoke：`PASS`；`continuous_outcome = WAITING_FOR_HUMAN`、`automated_ai_turns_advanced = 1`、`generation_request_count = 1`、`provider_identifier = zhipu`、`model_identifier = glm-4.7-flashx`、`configuration_version = ZHIPU_CHAT_DEV_V1`、generation request `COMPLETED`、formal `AiUtterance` persisted、AI `FloorRelease = SPEAKER_FINISHED`、resulting current floor actor `HUMAN`；pytest smoke `1 passed in 5.56s`；
- No credential、Authorization header、raw provider response、rendered prompt、Private Stance or verbatim model output was recorded。The temporary manual smoke test file was removed and is not part of project source/review scope；
- No E2 kernel、schema/migration、dependency/lock/config、runtime/service、API/WS/Web implementation change。At the P1-5E-3 closeout checkpoint，P1-5E/P1-5E-3 became `DONE` and P1-5F remained `NOT_STARTED`；the current F1 status is recorded above。

### P1-5D design and implementation checkpoint note

- Baseline is clean committed `main` / `origin/main` `371d5a57ffb952a7ccb664170819e07b606b5688` with P1-5C committed and unchanged master-plan SHA-256 `2388A9660320406CB35D5354126AD71C6849A98DB7C4A356796CA951BF372F26`；
- First real-provider path is `zhipu` / required server-configured model (current development selection `glm-4.7-flashx`) / model-independent `ZHIPU_CHAT_DEV_V1`, non-streaming BigModel chat completions over a thin `httpx.AsyncClient` adapter；thinking disabled、`stream=false`、`max_tokens=512`、`temperature=0.7` and automatic application retry `0`；
- Formal abstraction is one project-owned provider protocol retaining the existing async callable input/result shape；no SDK、registry、factory hierarchy、routing、fallback or multi-provider framework；
- API key is lazy server-only `SecretStr` configuration and cannot enter generation input/result、database、metadata、logs、traces、errors、tests or review artifacts；model is required lazy server-only non-secret `GIA_API_ZHIPU_MODEL` configuration and remains internal provenance；raw provider bodies/exceptions are normalized to existing safe typed failure codes；
- Existing P1-5B provider/model/configuration-version fields remain sufficient, so no schema/migration was required or added；the existing `httpx 0.28.1` constraint is now promoted from dev-only to the single runtime declaration；
- The minimal `GenerationProvider` Protocol and `ZhipuGenerationProvider` implement the frozen one-request non-streaming path without an SDK、registry、routing、fallback or automatic retry；lazy provider settings keep ordinary API startup independent of `GIA_API_ZHIPU_API_KEY` / `GIA_API_ZHIPU_MODEL`。Changing the model requires configuration plus API restart but no Python、adapter or schema change；future DB/admin configuration remains deferred；
- User-supplied manual access evidence selected FlashX for current development：`glm-4.7-flash` repeatedly encountered rate-limit/availability failures，while the same credential/endpoint returned HTTP `200` for `glm-4.7-flashx`。This does not claim permanent Flash unavailability or permanent Zhipu/FlashX production policy；
- All automated tests use HTTPX mocked/injected transport and remain network-free；config/provider focused results are `55 passed` / `47 passed`，provider/config/generation targeted is `111 passed`，PostgreSQL orchestration is `8 passed`，and fresh full backend/PostgreSQL is `469 passed` with 1 existing Starlette deprecation warning。Codex made zero real GLM calls；
- Final user-run sanitized real-provider acceptance smoke：`PASS`；provider `zhipu`、model `glm-4.7-flashx` and configuration version `ZHIPU_CHAT_DEV_V1` returned `RawGenerationSuccess`，and output satisfied the intended Chinese group-interview smoke expectation。No credential、raw provider response、sensitive header、verbatim output or diagnostic payload is recorded。P1-5D and all P1-5E substeps are `DONE`；P1-5F was still `NOT_STARTED` at that checkpoint and has since entered the separately approved F1 freeze above。

### P1-5C completion note

- Implemented exact immutable Prompt Version rendering with a closed variable vocabulary and minimum authorized context from the session-bound Question Version plus only the granted AI participant's Assignment/Persona/Private Stance；
- Implemented immutable provider-neutral runtime input/result validation and a deterministic local harness for success、timeout、unavailable、rate-limit、invalid output、partial generation and internal failure；
- Implemented short-transaction application orchestration：durable request identity/claim/replay、executor outside transaction/row-lock scope、atomic final utterance completion and fail-closed stale/concurrent recovery；before authoritative create/claim/final-completion mutation, the locked path reuses P1-3 `reconcile_due_for_locked_aggregate(...)` with server-authoritative current UTC；
- AI generation outcome/failure does not independently mutate lifecycle or floor authority；when overdue reconciliation advances phase/deadline, releases the old grant, appends ordered floor/session events or advances sequence, those are P1-3 lifecycle facts and no stale utterance is persisted；
- Real PostgreSQL and full backend regression pass (`406 passed`, 1 existing Starlette deprecation warning)；Ruff、format、strict Pyright、frozen dependencies、Alembic head/current/check and governance/scope gates pass；
- No real provider、provider abstraction、schema/migration、dependency/lockfile、API/WS/Web、automatic floor trigger/release or later-stage capability was added。

### P1-5A completion note

- 从 clean committed `main` HEAD `5397cd2b25f36c6a9fbd666b759261091c36a8c0` 恢复总纲、Accepted Decisions、P1-4 actual source、相关领域文档和现有 tests/config；HEAD 与 `origin/main` 一致；总纲 SHA-256 baseline 为 `2388A9660320406CB35D5354126AD71C6849A98DB7C4A356796CA951BF372F26`；
- 冻结 `floor.granted -> AI Runtime -> LLM Provider -> final Utterance -> deterministic Floor release`，明确 P1-3 lifecycle、P1-4 floor 和 future AI Runtime content authority 分离；
- 冻结业务代码 provider-neutral、SDK object 不穿透 domain、hosted/enterprise/local evolution，以及 provider failure 不影响 session integrity；
- 冻结 Prompt 为版本资产，历史 utterance 必须关联 exact Question Version、Persona/Assignment、Prompt Version、provider/model 和 effective non-secret configuration provenance；
- 冻结 AI Participant 是 session role identity、Runtime 是 generation capability；Persona Template 不保存 prompt/provider secret；
- 冻结 Generation Request 与 final Utterance 分离及 `requested/generated/persisted/failed` 逻辑生命周期；timeout/unavailable/rate-limit/partial generation 使用有界、幂等、stale-grant-safe 处理，失败不改变 phase/deadline/floor/scoring 且不重复产生 utterance；
- 多 provider、成本统计、企业模型、审计和 prompt iteration 保留 safely evolvable；billing/quota/payment/multi-tenant 及全部 LLM/provider/runtime/schema/API/test implementation 继续 Deferred；
- 完整冻结、后续 implementation gates 和 stop conditions 见 [`exec-plans/P1-5_ai-runtime-foundation.md`](exec-plans/P1-5_ai-runtime-foundation.md)。

### P1-5B completion note

- Linear revision `f1a15b15c005` additively creates `prompt_versions`、`llm_generation_requests` and `ai_utterances`；current schema is nineteen product tables with one Alembic head and no native enum。
- Prompt publication is immutable insert-or-exact replay；request identity uses a semantic SHA-256 digest；durable request lifecycle is `REQUESTED / RUNNING / COMPLETED / FAILED` with closed non-secret configuration metadata and safe typed failure codes。
- Final utterance is separate and at most one per request/floor grant；a completed-status composite foreign key blocks formal utterances for unsuccessful requests。Completion is atomic；constraint failure rolls the request transition back。
- Create/start/complete reuse owner-scoped session aggregate locking and exact floor/session/AI participant validation。Failure records no utterance/event and leaves phase、deadline、floor pointer and scheduler facts unchanged。
- No provider SDK/client/interface、LLM call、prompt execution、streaming、API/WS/Web、dependency/lockfile、CI、queue/worker or other deferred capability was added。
- Required gates PASS：Ruff、format、Pyright、`385 passed` full API/PostgreSQL suite、migration downgrade/re-upgrade/single-head/catalog/drift、master-plan hash and diff/scope checks。

## P1-6 — Complete Text Simulation

- ID: `P1-6`
- 名称：完整文字模拟
- Status: `DONE / CLOSED`
- Approval state: P1-6A～P1-6D retain their recorded review-pass states; P1-6E is `DONE / POST_STOP_CLOSEOUT_REMEDIATION_PASS`; all P1-6 findings are closed.
- Dependencies: P1-5 `DONE`; P1-5R/P1-5R-POST tracks `CLOSED` with their historical open findings `NONE`; P1-6A `P16A-REV-001` and `P16A-REV-002` are `CLOSED`; P1-6B `P16B-REV-001`, `P16B-REV-002` and `P16B-REV-003` are `CLOSED`; P1-6D `P16D-REV-001`, `P16D-REV-002` and `P16D-D2D4-REV-001` are `CLOSED`; open findings `NONE`.
- Goal: close the structured discussion-memory gap and compose/validate existing lifecycle, floor, AI runtime, public transport and Web capabilities as one complete Human + 3 AI text simulation.
- Out of scope: P1-7 report/V0.1 content; P1-8 full-P1 acceptance; voice/ASR/TTS; billing/payment; provider routing/fallback; Redis/queue/RAG/microservices and deferred infrastructure.
- Source plan: [`exec-plans/P1-6_complete-text-simulation.md`](exec-plans/P1-6_complete-text-simulation.md)

### Substep progress

- `P1-6A — Scope Reconciliation + Commercial-Readiness Architecture Freeze`: `DONE / DESIGN_SCOPE_FROZEN / ACTUAL_SOURCE_REVIEW_PASS`; docs-only; finding-only external actual-source re-review `PASS`; open findings `NONE`;
- `P1-6B — Structured Discussion Memory Gap Closure / Production Implementation`: `DONE / DESIGN_SCOPE_FROZEN / IMPLEMENTATION_COMPLETE / ACTUAL_SOURCE_REVIEW_PASS`; implementation finding-only re-review `PASS`; four frozen batches only; `P16B-IMP-001`, `P16B-IMP-002`, `P16B-IMP-003`, `P16B-IMP-004`, `P16B-IMP-005`, `P16B-IMP-006`, `P16B-IMP-007` closed; new findings `NONE`; open findings `NONE`;
- `P1-6C — Full Text Simulation Composition`: Design Freeze `DONE / DESIGN_SCOPE_FROZEN / ACTUAL_SOURCE_REVIEW_PASS`; production implementation `DONE / DESIGN_SCOPE_FROZEN / IMPLEMENTATION_COMPLETE / ACTUAL_SOURCE_REVIEW_PASS`; implementation findings `NONE`; production source changes `NONE`;
- `P1-6D — Recovery + Three-AI End-to-End Validation`: `DONE / DESIGN_SCOPE_FROZEN / IMPLEMENTATION_COMPLETE / ACTUAL_SOURCE_REVIEW_PASS`; D2-D1 through D2-D4 `PASS`; `P16D-REV-001 CLOSED`; `P16D-REV-002 CLOSED`; `P16D-D2D4-REV-001 CLOSED`; new findings `NONE`; open findings `NONE`; accepted commit `6dcce5e961d6aa7b460243dbd6407e17c2478aa2`; CI `GREEN`;
- `P1-6E — P1-6 Independent Acceptance + Closeout`: `DONE / POST_STOP_CLOSEOUT_REMEDIATION_PASS`; full re-acceptance 2 was `REPAIRABLE` on two Medium findings, and the user-authorized post-stop remediation plus independent finding-only review closed both without a third full re-acceptance; exact accepted-remediation CI is green.

### P1-6A finding-only review closeout note

- Search-first actual-source inspection confirms no structured-memory model/service/projection, memory revision/source cursor, stale detection or rebuild implementation; current AI context is only a bounded recent-public-transcript window (maximum 6 utterances / 4000 content code points).
- Existing P1-3 lifecycle, P1-4 floor/scheduler, P1-5 provider-neutral runtime/orchestration, Human/AI public utterance, REST/WS recovery and Web composition remain accepted and are not reopened.
- Frozen memory is a public-only derived projection over authoritative raw utterance/discussion events. Source event/utterance ordering, source cursor advancement, revision allocation, stale/current detection, idempotent consumption/re-entry, provenance association and inference-free structural fields must be deterministic. Proposal semantic merge, agreement/conflict interpretation and concise semantic summary may use a project-owned semantic derivation boundary/LLM, but derivation must be bounded, public-only, versioned, source-provenance-traceable, derivation-version-traceable and safely replayable/rebuildable as a new memory revision; a deterministic fake/test provider supports stable tests, while a real external LLM is not required to be word-for-word or bit-for-bit deterministic on rebuild.
- Authoritative raw public history remains the only evidence authority; semantic memory never replaces raw evidence. If semantic derivation is persisted, the design must leave an additive seam for derivation/prompt/model/config version provenance. P1-6A creates no schema/table.
- P1-6B owns structured memory + bounded memory-backed context; P1-6C owns minimal composition; P1-6D owns one complete network-free Human + 3 distinct AI recovery path through final-summary closure; P1-6E owns P1-6-only independent acceptance.
- Finding-only external actual-source re-review verdict is `PASS` against reviewed bundle `group-interview-arena-review-20260830-044406.zip` / SHA-256 `6137E75B1E671A561D6280901680A7445C66F5EDBB34D456142F092492473E4D`; `P16A-REV-001 CLOSED`; `P16A-REV-002 CLOSED`; new findings `NONE`; open findings `NONE`. P1-6A is therefore `DONE / DESIGN_SCOPE_FROZEN / ACTUAL_SOURCE_REVIEW_PASS`. No independent review was run. At that closeout checkpoint, P1-6B～P1-6E and P1-7/P1-8 were `NOT_STARTED`; the current P1-6B Design Freeze status is recorded below.

### P1-6B Design Freeze finding-only review closeout note

- Approved architecture: authoritative public `DiscussionEvent` ledger → public-only semantic patch proposal → strict provenance/policy validation → deterministic reducer → one current materialized state plus append-only patch journal → bounded memory + raw tail `DiscussionWorkingContext`.
- Actual-source calibration confirms additive PostgreSQL/Alembic evolution from head `f1a15b15c005`, safe public utterance projection, a separate candidate-only Private Stance boundary and reusable immutable `PromptVersion`. Current candidate-specific provider input makes a minimal shared model-transport refinement justified for the second real caller during implementation; no registry/router/fallback is authorized.
- Finding-only remediation adds distinct immutable `projection_version` to both Memory persistence responsibilities and binds replay-affecting reducer/state-policy semantics to it; exact replay resolves historical projection semantics rather than the latest policy.
- Memory-backed candidate generation freezes additive closed `GenerationRequestMetadata` V2 provenance for Working Context version/mode, exact memory revision/cursor and visible raw-tail boundary while preserving historical V1 rows; Batch 3 and acceptance cover normal and safe-fallback modes.
- `MemoryDerivationInput` now accepts only explicit `PublicMemoryQuestionContext`, equal to or narrower than the existing public candidate subset; ORM/generic dumps plus hidden/evaluator/reference-answer question fields are forbidden and covered by privacy sentinels.
- Initial external actual-source review verdict was `BLOCKED` against `group-interview-arena-review-20260830-060509.zip` / SHA-256 `C0C7A7A589B1795DD917C11CF13B36FBCE245DFFD36CD20D5C96BAD80AC6EF26` on exactly `P16B-REV-001`, `P16B-REV-002`, `P16B-REV-003`. After finding-only remediation, the finding-only external actual-source re-review verdict is `PASS` against `group-interview-arena-review-20260830-062133.zip` / SHA-256 `C10F2A9362EB6102C6C3F23D7BA66234FECC098BDE2A394D5A2738EBB97E701D`; `P16B-REV-001 CLOSED`; `P16B-REV-002 CLOSED`; `P16B-REV-003 CLOSED`; new findings `NONE`; open findings `NONE`. P1-6B is `DONE / DESIGN_SCOPE_FROZEN / ACTUAL_SOURCE_REVIEW_PASS`. Design-time STOP conditions remain `NONE`; no tables/code were created, no independent review was run and production implementation still requires separate approval.

### P1-6C Design Freeze note

- Baseline `3b9d4cf9a33f3d20a0b43a9f04d0483316728fa5` actual-source calibration confirms the existing production root is `resume_discussion_progression -> configured AI composition -> continuous drive -> candidate runtime -> P1-6B Memory/Working Context -> candidate V3 -> existing utterance/event/release path`; no production wiring gap or STOP condition was found.
- P1-6C owns composition proof only. P1-3 retains lifecycle, P1-4 floor/scheduling, P1-5/P1-6B candidate content, P1-6B Memory and existing REST/WS/Web presentation. Future implementation defaults to production changes `NONE`; only a focused RED test may justify the smallest existing caller-seam correction.
- Future proof is a focused network-free backend integration through the real progression caller with one deterministic dual-workload provider fixture. It covers accepted Memory revision/V3/V2 provenance/evidence/privacy/idempotency, `SAFE_RAW_FALLBACK` and unsafe-context rejection without duplicating P1-6D's full Human + 3 AI browser/recovery scope.
- External actual-source review verdict is `PASS` against `group-interview-arena-review-20260830-170659.zip` / SHA-256 `D4364CA666D715EA7932B3FC525D6D154EC18F8F4AC3D3989F40C19AE683B398`; design-review findings `NONE`; new findings `NONE`; open findings `NONE`.
- Design Freeze status is `DONE / DESIGN_SCOPE_FROZEN / ACTUAL_SOURCE_REVIEW_PASS`; production implementation is `DONE / DESIGN_SCOPE_FROZEN / IMPLEMENTATION_COMPLETE / ACTUAL_SOURCE_REVIEW_PASS`. The focused PostgreSQL proof drives the real progression/configured/continuous/runtime path with one network-free semantic/candidate provider and covers Memory + V3 + V2 provenance, safe raw fallback, unsafe rejection, privacy/evidence authority and re-entry idempotency. Production wiring gap `NONE`; production source changes `NONE`; implementation STOP conditions `NONE`; focused proof `3 passed`; affected PostgreSQL slice `87 passed`; API unit regression `521 passed`; Ruff/format/Pyright `PASS`. External actual-source implementation review verdict is `PASS` against `group-interview-arena-review-20260830-235324.zip` / SHA-256 `1E1FBE37255E294AEA76A4E4CC68E49490556C804BE77804731F78CF56EB944B`; implementation findings `NONE`; new findings `NONE`; open findings `NONE`.

### P1-6D Design Freeze note

- P1-6D is a dedicated network-free Browser Acceptance Scenario, separate from the existing layout-heavy session spec. Its harness owns isolated PostgreSQL/API/Web/restart/provider/log/verifier/cleanup mechanics; its Browser spec owns only the real product journey.
- It must prove exactly one Human + three authoritative AI participants, public contributions from all three AI IDs, legitimate phase-aware Human submissions, dual semantic/candidate workloads, durable Memory revision, candidate V3 + metadata V2 provenance, three-seat private-sentinel isolation, reload/reconnect, API restart, next-eligible-candidate cancellation, exact-once recovery and the full accepted lifecycle through `COMPLETED`.
- The existing P1-3/P1-4/P1-5/P1-6B/P1-6C authorities and public REST/WS/Web contracts remain unchanged. Production wiring gap `NONE`; production changes default to `NONE`; no new coordinator, scheduler, lifecycle engine, provider router, schema or dependency is authorized.
- Frozen runner topology: `web:test:e2e` first invokes the legacy harness with an explicit selector for the complete existing legacy suite (`auth.spec.ts` + `session.spec.ts`, or a source-compatible explicit selector), waits for complete cleanup, then invokes the dedicated P1-6D harness with an explicit selector for only `p1-6d-full-session.spec.ts` and waits for its cleanup. `workers = 1`; no harness overlap or new parallelism architecture.
- Future proof requires the dedicated `gia_p16d_` temporary-database prefix allowlist and CI cleanup recognition. Minimal test-only changes to existing `browser_e2e.py` and/or Web runner scripts are allowed solely for explicit selector isolation; no new CI job.
- P1-6D owns the normal Memory-enabled journey and one intentional eligible-candidate cancellation/recovery. P1-6C retains `SAFE_RAW_FALLBACK` and unsafe-context rejection as inherited focused backend regressions; rerun them only if a relevant runtime/Memory seam changes, and do not add a second P1-6D fallback/unsafe scenario merely for phase ownership.
- Initial external review was `BLOCKED` on exactly `P16D-REV-001` and `P16D-REV-002` against `group-interview-arena-review-20260831-004302.zip` / SHA-256 `7CE39C1EB4DE8314DCE7DB1CDE9809EB386E0E0CADDED8620D11B47FDB1791D0`. Finding-only external actual-source re-review is `PASS` against `group-interview-arena-review-20260831-005931.zip` / SHA-256 `502D21B84410EDD606C806C188FFFF1FAF6C8E8ACE3F08381B86E9FA13E29A66`; `P16D-REV-001 CLOSED`; `P16D-REV-002 CLOSED`; new findings `NONE`; open findings `NONE`.
- Design Freeze status: `DONE / DESIGN_SCOPE_FROZEN / ACTUAL_SOURCE_REVIEW_PASS`; production implementation status: `DONE / DESIGN_SCOPE_FROZEN / IMPLEMENTATION_COMPLETE / ACTUAL_SOURCE_REVIEW_PASS`. `P16D-REV-001 CLOSED`; `P16D-REV-002 CLOSED`; `P16D-D2D4-REV-001 CLOSED`; new findings `NONE`; open findings `NONE`; P1-6E remains `NOT_STARTED`.

### P1-6D production implementation final closeout

- Final acceptance ledger: exactly one Human plus exactly three authoritative AI participants, active Human UI contribution and public contributions from all three AI seats; durable Semantic Memory revision; candidate `AI_CANDIDATE_TURN` V3 plus `GenerationRequestMetadata` V2 consumption/provenance; three-seat private-sentinel isolation; exact-once generation request, utterance, public event and floor release; Browser reload recovery; API restart recovery against the same durable database; deterministic cancellation recovery without duplicate side effects; and authoritative `FINAL_SUMMARY -> COMPLETED` lifecycle closure.
- D2-D1 happy path, D2-D2A Browser reload, D2-D2B API restart, D2-D3 cancellation recovery and D2-D4 final integration all `PASS`; accepted commit `6dcce5e961d6aa7b460243dbd6407e17c2478aa2`; CI `GREEN`.
- D2-D4 finding-only remediation moved the Human continuation action outside polling and retained an observation-only durable completion predicate. Actual-source review verdict is `PASS`; `P16D-D2D4-REV-001 CLOSED`; new findings `NONE`; open findings `NONE`.
- P1-6D is `DONE / DESIGN_SCOPE_FROZEN / IMPLEMENTATION_COMPLETE / ACTUAL_SOURCE_REVIEW_PASS`. This closeout changes governance documents only, adds no feature or acceptance, changes no production/test/CI behavior, does not enter P1-6E and does not run independent review.

### P1-6E independent acceptance and post-stop closeout

- Initial independent acceptance at `df144f7605d435970a82871bd6f424dbd60722ee` returned `REPAIRABLE` on `P16E-001`～`P16E-004`. Repair/source-review cycles closed those findings and `P16E-SR1-001`; source review 2 passed before clean commit `2e91b623393c7ec3ef0b1b575a10f33eb175ee17`.
- The first committed re-acceptance found the pre-existing Web realtime-effect and Crash-E returned-state races. Repair 3 and source review 3 closed `P16E-RA-001`/`P16E-RA-002` in clean commit `822b024156396e079f51df7489c3ac166c3bc566`.
- Re-acceptance 2 proved the full required API/Web、real PostgreSQL/migration、Memory/private-stance/recovery and serial Chromium gates, including legacy `2 passed / 0 skipped` plus P1-6D final `2 passed / 0 skipped`, but returned `REPAIRABLE` on strict-Pyright finding `P16E-RA2-001` and API/privacy current-state finding `P16E-RA2-002`.
- After the three-repair stop condition, the user explicitly authorized one post-stop closeout remediation rather than `repair 4`. It changed only the typed Crash-E regression and `API.md`/`PRIVACY_AND_SAFETY.md`; independent finding-only review `PASS` closed both findings with no production/schema/workflow/dependency drift or new blocker. Accepted remediation commit `3aa1a049728314f1fbec65367b57b8442bb49670` has exact CI run `34336016724` green across all four jobs.
- During repair 1 cleanup, one acceptance-preexisting temporary database `gia_p04e_dcaf6d0303de` and the acceptance-preexisting Playwright `.last-run.json` marker were mistakenly deleted and could not be restored identically. The user accepted a new post-incident baseline; no later evidence claims restoration, and all later cleanup was ownership-only. Development-database identity/revision/table count/size/deterministic dump remained identical across the later independent validation.
- At the P1-6E closeout checkpoint, P1-6E and parent P1-6 became `DONE / CLOSED`, P1 remained `IN_PROGRESS`, and P1-7/P1-8 were `NOT_STARTED`; no real provider was called in P1-6E. Current P1-7 status is recorded below.

## P1-7 — Basic Evidence Report + V0.1 Content Closure

- ID: `P1-7`
- Status: `DONE / CLOSED`
- Goal: generate a durable V0.1 basic training report from validated authoritative public discussion evidence after `SimulationSession.COMPLETED`, and close the exact 3-type/12-human-reviewed-question V0.1 content target without importing P3 formal scoring.
- Source plan: [`exec-plans/P1-7_basic-evidence-report-and-content.md`](exec-plans/P1-7_basic-evidence-report-and-content.md)
- Current source: exactly 4 Persona seeds and 12 published V0.1 Question Versions at 4 `ORDERING_SELECTION` / 4 `RESOURCE_ALLOCATION` / 4 `PLAN_DESIGN`; report persistence/generation and the owner-only POST command plus independent GET/Web surface have passed external actual-source review.
- Out of scope: six-dimension scores/overall score/radar/ranking/hiring or fit claims/personality labels; session report lifecycle states; aborted/partial/failed-session reports; voice/audio timestamps; real-provider requirement; P3 drills; V0.5 content; Redis/queue/deferred infrastructure.

### P1-7 substep progress

- `P1-7A — Basic Evidence Report & V0.1 Content Architecture Freeze`: `DONE / DESIGN_SCOPE_FROZEN / ACTUAL_SOURCE_REVIEW_PASS`; strict docs-only; external actual-source review verdict `PASS`; material findings/new blockers/open findings `NONE`;
- `P1-7B — Evidence / Report Persistence Foundation`: `DONE / ACTUAL_SOURCE_REVIEW_PASS`; `P1-7B-F001 CLOSED`; open findings `NONE`;
- `P1-7C — Evidence Extraction + Basic Report Generation`: `DONE / ACTUAL_SOURCE_REVIEW_PASS`;
- `P1-7D — Report REST/Web + V0.1 Content Closure`: `DONE / ACTUAL_SOURCE_REVIEW_PASS`; `P1-7D-F001～F005 CLOSED`; content `4/4/4 IMPLEMENTED / HUMAN_CONTENT_REVIEW_PASS`; material content findings `NONE OPEN`;
- `P1-7E — Composition Acceptance + Independent Acceptance`: `DONE / INDEPENDENT_ACCEPTANCE_PASS`.

P1-7A review closeout uses `group-interview-arena-review-20260909-234536.zip` / SHA-256 `4EA3FE5DD23775106C2602CAA2EC6DC68AC8DDA6D9895C5D74465F90390798F3`. The reviewed checkout `bc8cb40148598230bd64feeeaebb498d05137fbe` is a direct parent of current GitHub `main` `f6f105ed2fcc334f6c9dd83c00d934428e1b689b`; their tree identities are equal and their file-content diff is empty. This is review baseline equivalence, not commit-SHA equality and not a claim that the bundle was generated from the later `main` working tree. No real provider was called and no P1-7B implementation occurred.

### P1-7A frozen boundary

- Architecture is Independent Report Resource + Evidence Records. `COMPLETED` remains the session lifecycle endpoint; report generation status is report-owned; GET reads a durable report and never regenerates it; no report activity WebSocket lifecycle is added.
- Raw public utterance/`DiscussionEvent` history is evidence authority. P1-6 Memory is bounded public-only auxiliary context and is never transcript, evidence or report truth.
- V0.1 report contains completion/question/deterministic participation/covered-phase overview, concise summary, at most 3 evidence-backed strengths, at most 3 evidence-backed improvement opportunities, exactly 1 next-session priority and evidence cards with participant/phase/utterance/sequence/quote/interpretation/confidence. Text V0.1 does not invent audio timestamps.
- Semantic evaluation proposes behavior/interpretation/priority/confidence; project-owned code owns eligibility, source ordering/watermark, source lookup, exact-quote and session/participant/phase/Human-source validation, completeness, versioning/provenance and idempotent re-entry. Invalid evidence is rejected, not repaired approximately.
- Evaluator input is explicit public Question/session/participant/transcript/Memory context only. Private Stance, persona calibration, hidden conflicts/acceptable outcomes/reference-answer fields, prompts, credentials, raw provider I/O/reasoning and private notes are forbidden.
- P1-7A freezes conceptual `EvaluationReport`/`EvidenceItem` responsibilities only and creates no schema/migration. P3 may later add dimension/metric/rubric/scoring versions additively.
- Eligibility is exactly `SimulationSession.status == COMPLETED`; aborted/partial/service-failure reports remain Deferred.
- Content target is 4 ordering + 4 resource-allocation + 4 plan-design = 12 human-reviewed immutable Question Versions. P1-7D implements the exact 4/4/4 catalog and external human content review is `PASS`; automated validation remains separate supporting evidence rather than a substitute for that review.
- The master-plan “score versus level + evidence” question remains TBD. P1-7 outputs no formal score, radar, percentile, ranking, hiring probability, job fit or personality type.
- P1-7E independently accepted one network-free select → session → 1 Human + 3 AI → all text phases → `COMPLETED` → report → Web/evidence resolution → Browser reload → API restart/durable recovery path. P1-7E is `DONE / INDEPENDENT_ACCEPTANCE_PASS`; P1-7 is `DONE / CLOSED`; open findings are `NONE`; P1-8 remains separate and `NOT_STARTED`.

### P1-7B implementation checkpoint

- Additive revision `f1a17b17c008` extends the linear schema from 21 to 23 product tables with `evaluation_reports` and `evidence_items`; historical migrations remain unchanged and downgrade returns exactly to `f1a16e16c007`.
- Report generation identity is unique on session, report schema version, derivation version and frozen `SimulationSession.last_sequence`; report-owned lifecycle is closed to `REQUESTED/RUNNING/COMPLETED/FAILED` with database timing/content consistency.
- Evidence provenance uses same-session composite foreign keys to report, participant and authoritative `DiscussionEvent(session_id, sequence)`; Human `source_utterance_id` remains a stable UUID because the actual source has no generic Human utterance table.
- `get_or_create_eligible_report` accepts only owner-scoped `COMPLETED` sessions, freezes the watermark under a PostgreSQL share lock and resolves concurrent re-entry through the named database unique constraint. It performs no evaluator/provider call and creates no Evidence rows.
- Fresh unit, PostgreSQL migration/catalog/downgrade/re-upgrade, constraint, idempotency and two-caller concurrency gates pass. External actual-source review final verdict is `PASS`; `P1-7B-F001` is `CLOSED`; material findings/new blockers/open findings are `NONE`. Accepted bundles are `gia-p1-7b-report-persistence-review-20260910-113955.zip` / SHA-256 `9FB2E9CF3E2BD3E865295F11C15764670E216BC0FED4CD9E1CD59DDE5F12AD9E` and `gia-p1-7b-f001-finding-only-review-20260910-120420.zip` / SHA-256 `CCA43286017D97133755285F8D5EFC6EFAF15F38DDD54D3DD07327C936AFE4B0`.

### P1-7C implementation checkpoint

- `ReportSourceCollector` projects only the exact public Question allowlist, ordered public roster and authoritative `participant.utterance.created` events through the report's frozen watermark. It excludes Memory, hidden/reference Question fields and Persona private/calibration data, and preserves source content exactly.
- `ReportEvaluator` returns a closed evaluator-neutral proposal. `EvidenceValidator` resolves every proposed citation exactly to Human public source identity/sequence/phase/quote, and `ReportComposer` assigns trusted evidence kind and rejects the whole generation if any proposed item is invalid. `DeterministicReportEvaluator` is network-free.
- `ReportGenerationCoordinator` uses the durable generation identity and `started_at` claim token with an explicit positive lease. Short transactions own claim/failure/finalization CAS; no DB scope is held during evaluation. Completion plus every Evidence row commits atomically, stale claimants persist nothing, FAILED retries reuse the same report, and COMPLETED re-entry does not evaluate again.
- P1-7C changes no schema, migration, session lifecycle, public API, Web surface or dependency. It adds no P3 score/dimension/ranking behavior and makes no real-provider call. External actual-source review passed; P1-7C is `DONE / ACTUAL_SOURCE_REVIEW_PASS`.

### P1-7D implementation checkpoint

- `POST /sessions/{session_id}/report` is the minimal owner-only product command over `ReportGenerationCoordinator.generate`; the server owns schema version `1`, derivation `basic-report/v1`, deterministic evaluator selection and lease. Existing CSRF, completed-session eligibility, non-disclosing ownership, claim/CAS, retry/idempotency and atomic finalization remain authoritative. The response is safe metadata only.
- `GET /sessions/{session_id}/report` is owner-only and read-only. It selects the current durable report by `created_at DESC, id DESC`, never falls back from a newer non-completed report, and never invokes evaluator/coordinator/provider or creates report/evidence rows.
- The closed public envelope exposes safe metadata for every durable lifecycle state; content is `null` unless `COMPLETED`. Completed projection reuses the trusted frozen-watermark public source, renders deterministic factual counts and 0..3 evidence cards per kind ordered by source event sequence then evidence identity, and preserves quote/provenance exactly without P3 scoring.
- The completed SessionPanel exposes `生成 / 查看训练报告`, invokes the POST command and navigates to the reloadable `/sessions/{sessionId}/report` route. The report page handles loading, authentication/not-found, all four report statuses, empty evidence sections and the five-part completed report surface.
- The immutable seed catalog contains exactly 12 candidate versions at 4/4/4 with the existing four Persona Templates and three explicit question-specific private AI stances per added question. Museum, rural-clinic and heatwave prompts now carry the missing decision-grade public facts. See [`V01_CONTENT_REVIEW_MANIFEST.md`](V01_CONTENT_REVIEW_MANIFEST.md). Content is `4/4/4 IMPLEMENTED / HUMAN_CONTENT_REVIEW_PASS`.
- P1-7D adds no schema/migration/dependency/WebSocket, score/rank, commercial behavior or P1-7E implementation. External actual-source review passed; P1-7D-F001～F005 are closed; P1-7D is `DONE / ACTUAL_SOURCE_REVIEW_PASS`.

#### P1-7D finding-only remediation matrix

| Finding | Remediation | Review state |
| --- | --- | --- |
| P1-7D-F001 | Added the real owner-only POST product command over the accepted coordinator with server-owned V0.1 identity and safe metadata. | `CLOSED` |
| P1-7D-F002 | Added the completed-session CTA, typed POST client and stable report-route navigation with safe errors. | `CLOSED` |
| P1-7D-F003 | Added comparable museum facts, three-town rural demand facts and heatwave unit economics. | `CLOSED` |
| P1-7D-F004 | Replaced generic stance text with three explicit differentiated stances for each of the 11 added questions. | `CLOSED` |
| P1-7D-F005 | Synchronized P1-7D API/data/agent/architecture/question/task/plan/manifest governance facts. | `CLOSED` |

### P1-7E independent acceptance and P1-7 closeout

- Status: P1-7E `DONE / INDEPENDENT_ACCEPTANCE_PASS`; P1-7 `DONE / CLOSED`; external independent acceptance `PASS`; open findings `NONE`.
- The dedicated network-free acceptance created a real Web session from the retained internal-validation Question Version, proved exactly 1 Human + 3 distinct AI, traversed every text phase to `COMPLETED`, and froze completion watermark `48` without direct Session/Event/Report/Evidence mutation.
- The completed-session Web CTA issued the real POST through `ReportGenerationCoordinator`, producing exactly 1 durable schema-1 / `basic-report/v1` report and 1 authoritative Human evidence item at watermark `48`. Read-only PostgreSQL proof resolved its participant, utterance, phase, event sequence and exact unnormalized quote to the authoritative `participant.utterance.created` event.
- Pre-generation GET left report/evidence counts at zero; repeated GET, repeated POST, report-page reload and API restart preserved the same durable identity/content/counts; a second authenticated user received nondisclosing 404. Private/scoring leakage scans passed and only the P1-7E network-free candidate provider was exercised.
- Fresh dedicated P1-7E, API unit/PostgreSQL integration, API/Web quality, production build, repository Chromium, OpenAPI drift, Alembic/head/table and cleanup gates passed before external independent acceptance. Production source, schema/migrations, dependencies/lockfiles and CI/infrastructure remained unchanged; no scoring and no real-provider call occurred. External independent acceptance returned `PASS`; P1-8 remains `NOT_STARTED`.

## P1-8 — Independent P1 Acceptance

- ID: `P1-8`
- Status: `NOT_STARTED`
- Boundary: future independent acceptance of complete P1; not the same as P1-6E.

## 任务更新规则

- 开始任务：用户明确批准后设为 `IN_PROGRESS`。
- 完成实现：验证通过并提交 diff；若验收要求用户审核，审核前仍保持 `IN_PROGRESS`。
- 阻塞任务：只有真实外部依赖阻止继续时设为 `BLOCKED`，并写明解除条件。
- 完成任务：满足全部验收条件后设为 `DONE`。
- 范围变化：先更新决策或获得批准，再修改任务范围。
