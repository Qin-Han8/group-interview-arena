# P0 技术架构基线

- Status: P0 Architecture Baseline + P1-1/P1-2/P1-3/P1-4 completed + P1-5A/P1-5B/P1-5C/P1-5D/P1-5E/P1-5E-1/P1-5E-2/P1-5E-3/P1-5F-1 completed + P1-5F in progress
- Current phase: P1 — IN_PROGRESS
- Architecture baseline established by: P0-2 — DONE
- P0-3 foundation status: DONE
- P0-4 database foundation status: DONE
- P0-5 identity boundary status: DONE
- Most recently completed subphase: P1-5E-3 Continuous AI Drive + Composition Acceptance
- P0 status: DONE; P0-1 through P0-7 completed
- P1 status: IN_PROGRESS; P1-1/P1-2/P1-3/P1-4 DONE; P1-5A/P1-5B/P1-5C/P1-5D/P1-5E/P1-5E-1/P1-5E-2/P1-5E-3/P1-5F-1 DONE; P1-5F IN_PROGRESS; P1-5F-2/P1-5F-3/P1-5F-4 NOT_STARTED
- Target version: V0.1 Internal Validation
- Business architecture detail: P1-1 runtime completed; P1-2 question/persona boundary implemented; P1-3 lifecycle independently accepted; P1-4 floor control implemented; P1-5A freezes authority; P1-5B persists prompt/request/final utterance; P1-5C adds deterministic internal generation orchestration; P1-5D adds the first thin real-provider adapter; P1-5E-1 freezes state-driven automatic coordination; P1-5E-2 implements its single-turn kernel; P1-5E-3 closes bounded continuous drive and lazy configured composition; P1-5F-1 freezes the public text-discussion REST/WS/Browser boundary docs-only
- Authority: 低于 [`PROJECT_MASTER_PLAN.md`](PROJECT_MASTER_PLAN.md) 和已确认的 [`DECISIONS.md`](DECISIONS.md)

## 文档目的

本文件记录 P0-2 已批准的技术架构基线、系统边界、规划目录、开发拓扑和演进约束。它不是完整业务架构；P1 以后的题目、角色、会话、编排和评分模块仍须在进入对应任务时逐步设计。

正式技术决策及其上下文以 [`DECISIONS.md`](DECISIONS.md) 中 `ADR-001`～`ADR-015` 为准。本文件只整理这些决策对实现的直接约束。

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
│   └── compose.yaml             # Implemented in P0-4B: PostgreSQL only
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

P0-3D 已实现的 API 技术基础使用 CPython `3.14.7`、uv `0.12.3`、FastAPI `0.141.1`、Pydantic `2.13.4`、pydantic-settings `2.15.0` 与 Uvicorn `0.52.1`。项目采用 packaged `src/group_interview_arena_api` layout；`api/` 当前只有 health transport，`core/` 包含 typed settings、安全错误语义、标准库 JSON logging 与 UUIDv4 `request_id`。P0-4C 已建立 `db/` persistence infrastructure，使用 SQLAlchemy `2.0.52`、psycopg/psycopg-binary `3.3.4`、`postgresql+psycopg://`、`DeclarativeBase`、async engine/session factory 与显式 dispose helper；P0-4D 已加入 Alembic `1.18.5` async migration environment 与 zero-op baseline revision。P1-1C 已因真实 session caller 创建 `modules/discussion_sessions` 与 WebSocket transport，并在 actual-source review finding F1 remediation 中加入 direct `websockets>=16.0,<17` 作为 Uvicorn WebSocket network runtime backend；未采用 `uvicorn[standard]`，因此没有引入无 caller 的 loop、HTTP parser 或 file-watcher extras。P1-5D 因首个真实 caller 创建 `providers/`，其中只有 thin Zhipu HTTP adapter；现有 `httpx>=0.28.1` 已从 dev-only 提升为单一 runtime dependency，没有 provider SDK 或第二 HTTP client。

P0-6D 为 `core/` 增加 OpenTelemetry API/SDK/OTLP HTTP exporter `1.44.0` tracing foundation；它是 cross-cutting infrastructure，不是业务 provider adapter。实现不设置 process-global provider，不采用 contrib auto-instrumentation，并保持默认 disabled。

## Local development model

```text
developer
  ├── browser
  │     -> Next.js web :3000
  │          -> REST GET /health
  │               -> FastAPI api :8000
  ├── Node.js 24 LTS + pnpm
  ├── CPython 3.14 + uv
  └── Docker Compose
        -> PostgreSQL 18.4 127.0.0.1:5432

Web 与 API 继续作为 Windows native process。Docker Compose 当前只运行 PostgreSQL，不包含 Web、API、Redis、worker 或管理 UI。

Windows API runtime 必须通过 Uvicorn custom loop factory `group_interview_arena_api.core.event_loop:create_runtime_event_loop` 使用 Psycopg-compatible `SelectorEventLoop`；P0-5D 的独立进程浏览器验证发现默认 Proactor loop 会导致真实 PostgreSQL auth request 失败。非 Windows 平台继续使用标准 asyncio loop，无新增 runtime dependency。
```

本地 browser origin 必须通过 `GIA_API_CORS_ORIGINS` 显式加入 allowlist；缺省为空，不允许跨源。该 typed normalized origin set 已批准作为 P0-5 CORS 与 CSRF exact Origin validation 共用的 browser trusted-origin Source of Truth，不新增第二套 CSRF origins 配置。`NEXT_PUBLIC_API_BASE_URL` 是公开浏览器 base URL，不是 secret。Web 直接请求 FastAPI，不建立 Next.js Route Handler proxy。

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

P0-4A/P0-4B 已完成：

- `infra/compose.yaml` 使用 `postgres:18.4-trixie`；
- service 为 `postgres`，host binding 为 `127.0.0.1:5432`；
- Docker local named volume 挂载至 PostgreSQL 18 的 `/var/lib/postgresql`；
- `pg_isready` healthcheck 使用实际 `POSTGRES_USER`/`POSTGRES_DB`；
- 真实容器已验证 PostgreSQL 18.4、开发数据库、`SELECT 1` 与 restart 后恢复。

P0-4C 已建立以下尚未接入 app runtime 的技术层：

```text
API（当前无 DB caller）
  ↓
DB infrastructure factories
  ↓
SQLAlchemy async 2.0.52
  ↓
psycopg 3.3.4
  ↓
PostgreSQL 18.4
```

`GIA_API_DATABASE_URL` 是通过 `SecretStr` 按需加载的 server-only 配置；只有 DB factory 或 Alembic command 的调用方需要提供。当前没有 global engine、FastAPI DB dependency、app DB lifecycle、启动连接、SQL echo 或 pool tuning。P0-4C 完成时 `Base.metadata.tables` 为空；P0-5B 完成后已精确注册 `users` 与 `auth_sessions`。P0-4D migration flow 为：

```text
SQLAlchemy Base.metadata
  ↓
Alembic async migration environment
  ↓
reviewed migration revisions
  ↓
PostgreSQL
```

Alembic 使用 migration-specific `AsyncEngine`、`connection.run_sync(...)` 与 `NullPool`，只接受 `postgresql+psycopg`。zero-op revision `7c6ccd86b3c5` 保留为历史 baseline；其后的 identity migration 已增加 `users`/`auth_sessions`，当前 single Alembic head 为 `4fe43b42641b`。API runtime startup 仍不自动执行 migration。P0-4E test architecture 为：

```text
pytest integration
  ↓
safe per-test gia_p04e_* PostgreSQL database
  ↓
SQLAlchemy async runtime / Alembic
  ↓
drop exact temporary database
```

Test-only sync psycopg 只管理临时 database lifecycle，application DB runtime 仍为 async。Development database 受 guard 保护，integration suite 从不对其执行 migration。P0-5B 已通过独立临时数据库验证后单独迁移 development database；Redis 继续不运行。

P0-4F 已从 clean `main` HEAD 独立复核 Git、总纲 hash、Docker/PostgreSQL runtime、Compose、secret/dependency 边界、SQLAlchemy/Alembic 架构、migration history、integration harness、unit/integration/full suites、质量门、development database 保护、临时数据库残留与范围。所有 gate 通过，P0-4 已转为 `DONE`；P0-4F 当时未建立业务 Schema、FastAPI DB caller 或 readiness，P0-5B 后的 identity schema 现状见下节。

### P0-5 identity boundary — P0-5D browser closure implemented

`ADR-015` 已批准以下长期边界：

- P0/V0.1 初始 credential 为 username/password，稳定 UUIDv4 `user_id` 与登录标识、未来 display name、phone/WeChat identity 分离；
- Password 使用 application 显式拥有并在目标环境 benchmark 的 Argon2id 参数；
- 第一方浏览器采用 PostgreSQL-backed opaque server-side session，当前不采用 JWT；
- raw session token 只进入 host-only HttpOnly Cookie，`auth_sessions` 只保存 cryptographic digest；
- browser security 使用 credentialed explicit CORS、exact Origin validation、required custom CSRF header 与 SameSite defense-in-depth；CORS/CSRF 共用 `GIA_API_CORS_ORIGINS` normalized set；
- V0.1 self-service account/password recovery Deferred；公开测试前必须重新设计 verified recovery identity/flow。

P0-5B 已建立 `users`、`auth_sessions`、identity migration 与 password/session security primitives，metadata 以 `db` package 的显式 model registration 精确包含两张 product table。P0-5C 已把现有 DB factory 接入 FastAPI lifespan/app state/request-scoped `AsyncSession`，并实现最小 register/login/logout/me、server-side session validation 与 `gia_session` Cookie issue/clear。P0-5D 已完成 shared-origin credentialed CORS/CSRF、最小 Web auth UI、raw/canonical username browser/backend closure 与真实 Chromium browser closure；P0-5E initial independent review verdict 为 `BLOCKED`，两个 findings 已完成 remediation，并通过 findings-only independent recheck；P0-5E final outcome 为 `PASS`，P0-5 已转为 `DONE`。

已实现的 DB application lifecycle 为：

```text
FastAPI lifespan
  -> AsyncEngine
  -> async_sessionmaker
  -> app state
  -> request-scoped AsyncSession
```

DatabaseSettings 只在 lifespan boundary 解析；模块 import 与 OpenAPI generation 不创建 engine 或连接数据库。禁止 import-time engine、eager global connection、startup migration、`create_all` 或 `drop_all`。Request dependency 负责 session lifecycle 和异常 rollback，但不对所有请求隐式 commit；register、login 与 logout operation boundary 显式拥有短事务，read-only current-user lookup 不 commit。

## Communication and contract boundaries

- REST：resource CRUD、question fetch、session create、session snapshot/load、reports、settings 及未来 admin/orders；
- WebSocket：active session commands、state changes、participant events、timer、floor control、interruption、AI streamed text 及未来 speech-related session events；
- SSE 不作为活动 session 主协议；
- P1 第一个文字讨论 vertical slice 即建立 WebSocket session channel，不先做完整 HTTP 讨论后再重写；
- 服务端 session state 是权威；client command 有 action identity；session event 有顺序；重连基于 server snapshot + sequence。

FastAPI OpenAPI 是 REST contract 的 Source of Truth。P0-3E 从运行中的 `/openapi.json` 使用 `openapi-typescript` 生成 `apps/web/src/lib/api/generated/schema.d.ts`，再由 `openapi-fetch` 提供 typed fetch client；生成文件受版本控制且不得手改，`api:check` 验证漂移。

WebSocket 使用独立版本化事件契约，至少表达 event type、schema version、session identity、ordering sequence、occurrence timestamp 和 action identity。P1-1A 已冻结第一条 vertical slice 的 v1 scoped contract；它不等于完整 P1/P2 事件集合，详见 [`exec-plans/P1-1_discussion-session-foundation.md`](exec-plans/P1-1_discussion-session-foundation.md)。

### P1-1 session architecture — backend and Web caller vertical slice implemented

- P1-1 aggregate root 为 `simulation_session`；FastAPI domain/service 是状态和 command outcome authority，PostgreSQL 是 session/action/event persistence authority，Browser 只是 snapshot + event projection。
- 首批 product tables `simulation_sessions`、`session_actions`、`discussion_events` 已由 P1-1B 实现；加既有 `users`、`auth_sessions` 后，actual product table set 精确为五张，Alembic single head 为 `f1a11d15c001`。
- REST scoped contract 为 authenticated `POST /sessions` 与 owner-only `GET /sessions/{session_id}`；WebSocket scoped endpoint 为 `/ws/sessions/{session_id}?after_sequence=`；三者已由 P1-1C 注册到 FastAPI。
- 创建 session 产生 `session.created`；唯一 v1 business command `session.abort` 产生 `session.state_changed`。该最小动作不依赖 future question/participant/utterance，也不创建 test-only `noop` 产品行为。
- `action_id` 在单一 session 内持久化幂等；正式 events 使用 session row lock + durable counter 分配连续 sequence，不使用 `MAX(sequence)+1`。action 到 event 为一对多 causation 边界。
- reconnect 使用 REST snapshot `last_sequence` 和后续 ordered WS events；gap 必须重新加载 snapshot，client local state 不得补写 authoritative state。
- WS Cookie authentication 复用现有 identity/session service；Origin exact validation 继续消费 `Settings.cors_origins`，不建立第二套 browser trusted-origin config。
- P1-1C 已随真实 realtime callers 增加 validated `session_id`/server-generated `connection_id`/validated `action_id`/positive sequence；payload、Cookie、Origin、raw path/query、user identity 和 exception detail 不进入 logs/spans/errors。
- P1-1D 已随真实 caller 创建最小 `lib/realtime` parser/client 与 session panel：stable pending `action_id` 只在内存保存，strict next/duplicate/gap 处理以 REST snapshot 恢复 authority，connection generation + React cleanup 阻止 stale socket/remount 覆盖新 projection 或形成双连接。
- Browser local/session storage 不保存 raw Cookie/token、action queue/payload 或 authoritative session state；URL 只保留非秘密 `session_id`，reload 必须重新读取 owner-only REST snapshot 并连接 ordered WS events。
- 真实 disposable PostgreSQL + Next/Chromium/Uvicorn E2E 已验证 create、sequence `1` catch-up、abort sequence `2`、duplicate action replay、REST reload restore、单一 durable action 与资源 cleanup。
- P1-1 不运行 Redis、queue，不创建 provider，且不扩展 WebSocket OTel propagation unless a bounded real caller needs it。

### P1-2 question/persona architecture — implemented through P1-2C

- P1-2A 冻结 `modules/question_personas` 真实业务边界；P1-2B 已创建对应 domain/persistence module，P1-2C 已增加显式 public contracts、read service/routes 与 session creation caller；没有 CMS、provider、repository/interface/factory 空壳。
- `QuestionTemplate` 只拥有 stable identity/lifecycle；immutable `QuestionVersion` 是内容、三个 Persona Assignments 和 Private Stances 的 aggregate/publication boundary。
- `PersonaTemplate` 是可跨题复用的 stable-behavior record；具体题目观点只存在于 version-specific assignment/stance，不进入 Persona Template。
- FastAPI domain/application code 是 publication、immutability、selection 和 private projection authority；ORM 只负责 persistence；Browser 只消费 purpose-built safe public question DTO。
- PostgreSQL persistence 使用 scalar columns、分别命名且 closed-schema-validated 的 structured fields 和 explicit persona numeric columns；不使用单一 arbitrary question/persona JSON blob，也不使用 question type/difficulty native DB enum。
- P1-2B 以 additive migration 新增题目/persona tables，并向 `simulation_sessions` 添加 nullable legacy-safe `question_version_id`；P1-2C 后新的 API-created session 必须绑定 selectable immutable version。
- P1-2C 已只增加 authenticated safe question reads、version-bound session creation 和最小 Web selection/render caller；未增加 question mutation/admin、persona/private API、participant/utterance、WS event vocabulary 或 AI runtime。
- Private Stance/internal calibration fields 不进入 REST OpenAPI、generated Web contract、Browser、WebSocket、logs、traces 或 errors。未来 AI caller 只在获批后由 server-side application service 按 session-bound version 为单一 assignment 加载最小 private context。
- Published content/assignment/stance 采用 append-only application invariant；retirement 只影响未来 discovery。Session foreign key 使用 restrict/no-action historical semantics，禁止 mutable latest pointer 或 retirement cascade 改写历史。
- 完整范围、schema、B～D caller/acceptance/testing 见 [`exec-plans/P1-2_question-persona-foundation.md`](exec-plans/P1-2_question-persona-foundation.md)。P1-2D independent verdict `PASS`，P1-2 `DONE`；其后的 P1-3A 已完成 docs-only design freeze。

### P1-3 session state/timing architecture — realtime/Web flow implemented

- V0.1 implemented status path 冻结为 `CREATED -> PREPARATION -> OPENING_STATEMENTS -> EXPLORATION -> CONFLICT_AND_EVALUATION -> CONVERGENCE -> FINAL_SUMMARY -> COMPLETED`；`ABORTED_USER` 可从 `CREATED` 和全部 active phases 进入。
- FastAPI/domain/PostgreSQL 是 state、timing、deadline 和 transition authority；Browser 只投影 snapshot + ordered formal events，不可指定 next state 或以 countdown 触发 transition。
- P1-3B 已向现有 session aggregate additive 增加 durable current phase start/deadline 和 server-resolved immutable duration plan；duration 是 typed server configuration，不硬编码 future mode parameters，也不接受 Browser duration。
- 所有 user transition intent 继续使用 P1-1 stable `action_id`、semantic replay/conflict、session row lock、single transaction、durable sequence 和 commit-before-send。Deadline transition 是 nullable-causation system operation；new user command 在同一 locked transaction 内先 reconcile overdue deadline，再应用 user intent。
- Recovered phase arithmetic anchored to the previous durable deadline；reload/reconnect/restart 不重置 deadline，downtime catch-up 可按顺序推进多个 overdue phases；P1-3B backend foundation 与 P1-3C startup/connected recovery 已用真实 PostgreSQL concurrency/regression/Chromium complete-flow 覆盖该语义。
- Formal vocabulary 保持最小：`session.created` v1 与 `session.state_changed`。Historical abort v1 继续可读；P1-3B start/abort/deadline transitions 使用 generalized event version 2，不静默改写旧 event。
- P1-3C app-owned in-process recovery runtime 只提供 wake-up/liveness，并在 startup、WS connect 和 connected catch-up path 调用同一 overdue reconciliation foundation；PostgreSQL deadline、row lock 和 event log 提供 correctness。Redis/queue、distributed scheduler 和 cross-process realtime fan-out 继续 Deferred。
- `DEVICE_CHECK`、pause/system failure/partial completion 和 report lifecycle states 保留总纲长期语义但不进入 P1-3 handler。完整设计、C～D scope 和 stop conditions 见 [`exec-plans/P1-3_session-state-machine.md`](exec-plans/P1-3_session-state-machine.md)。

### P1-4 floor-control architecture — deterministic scheduler implemented

- P1-3 remains the sole lifecycle/phase/timing authority. P1-4 floor control operates only inside the authoritative current phase and cannot start、advance、pause、extend or complete it.
- A session has zero or one current floor owner. Ownership references a generalized session participant, not a Persona Template/provider/browser connection；participant actor kind supports `AI`、`HUMAN`、`SYSTEM`, while role separates ordinary `CANDIDATE` from `MODERATOR` intervention.
- Speaking opportunity is durable intent/obligation when recovery requires it；candidate speaker and fairness ranking are recomputable runtime views；scheduler decision is the causal audit record；formal event is the resulting fact.
- The V0.1 scheduler is a pure deterministic lexicographic policy over phase context、availability、opportunities、floor history、derived fairness and closed server policy. It prioritizes unmet first opportunity, prevents monopoly, applies phase-aware order, uses stable slot/UUID tie-break and can request explainable silence/deadline intervention.
- Persona parameters、Private Stance、prompt、LLM/provider output、scoring and Browser ranks are not scheduler inputs. Scheduler decides who speaks；future LLM/provider may only generate what an already-granted AI says.
- Minimal future formal facts are `floor.granted`、`floor.released` and `floor.intervention_requested`, persisted/ordered through the existing session aggregate transaction and sequence boundary. Decision metadata retains safe policy reason/audit facts while excluding private stance、hidden persona calibration and internal scoring.
- P1-4B adds generalized session participants, durable opportunities, immutable decision/grant/release/intervention history and one session current-grant pointer. Session creation materializes one human plus the three immutable AI assignments; the schema supports a future `SYSTEM` moderator without creating a full participant runtime.
- Floor commands are an internal domain/service boundary in P1-4B. They reuse owner authorization, `session_actions` UUID identity + semantic digest, aggregate `FOR UPDATE` locking, contiguous `discussion_events` sequence and one transaction. Duplicate commands replay causal facts; digest conflicts, stale phase/sequence, wrong grant, ineligible actors and terminal sessions fail without mutation.
- The session row's nullable composite reference `(id, current_floor_grant_id)` may target only a grant in that same session, so the locked aggregate is the zero-or-one current owner projection. Grant/release facts remain append-only; release is a separate one-to-one fact rather than an update to historical grant data.
- P1-3 deadline/abort reconciliation may release an active grant in the same transaction before `session.state_changed`, preserving contiguous order while leaving status/timing semantics exclusively in P1-3. Floor code never writes lifecycle state.
- P1-4C implements the pure policy in `modules/floor_control/scheduler.py`. All input enumeration is explicitly sorted；first opportunity、monopoly guard、phase-aware fairness and stable seat/UUID form a closed lexicographic key, while injected UTC is used only for silence/deadline thresholds. Candidate lists/fairness counters remain runtime-only.
- Internal `floor.schedule` orchestration reconstructs participant/opportunity/history facts only after acquiring the existing session aggregate row lock, validates exact phase/sequence/current-grant preconditions, then persists action digest、safe decision and grant/intervention plus one formal event in the same transaction. Concurrent evaluation cannot create a second owner；duplicate action replays and stale evaluation fails closed.
- The three frozen formal floor facts remain on the existing single session channel and discussion sequence. P1-4D additively exposes an owner-only safe snapshot projection (generalized participant identity、current grant、latest lifecycle fact), strict Web parsing/reduction and display-only current-owner/lifecycle/reason UI. Existing exact-next sequence、duplicate suppression、gap reload、bounded reconnect and stale-generation rules recover floor state without a second channel/protocol.
- Browser has no floor command and cannot select、grant or release a speaker. Public projection is purpose-built and excludes decision metadata、hidden ranking/weights、Private Stance/persona calibration、prompt/provider and scoring data；P1-4E independent acceptance passed. Full design is in [`exec-plans/P1-4_floor-control.md`](exec-plans/P1-4_floor-control.md).

### P1-5 AI Runtime architecture — frozen authority and current implementation

P1-5A 冻结 authority boundary；P1-5B 已增加 generation request/final utterance persistence，P1-5C 已增加 deterministic internal prompt/runtime orchestration，P1-5D 已增加首个 project-owned provider Protocol 与 thin Zhipu HTTP adapter，current development model is server-configured `glm-4.7-flashx`。P1-5E-2/E3 now provide internal single-turn and bounded continuous coordination；there is still no public transport or background/startup trigger。

```text
P1-3 lifecycle authority: phase / deadline
  -> P1-4 floor authority: who speaks / floor.granted
  -> P1-5 AI Runtime: what the granted AI says
  -> provider adapter: model I/O only
  -> validated final Utterance
  -> project-owned deterministic floor release
```

- AI Runtime 只能消费 exact active AI participant + floor grant，并按 application/domain service 提交结果；它不能推进 session、修改 deadline、选择 speaker、覆盖 scheduler decision、修改 scoring 或直接绕过 domain service 写数据库。
- Business/domain code 依赖 project-owned provider-neutral request/result/error contract，不直接依赖单一 SDK。P1-5D 的 Zhipu adapter 位于外部 `providers/` boundary；hosted/enterprise/local routing、registry 和 fallback 仍未实现。
- Prompt 是 immutable/versioned asset。每个 generation request 必须固定 Question Version、获准 participant 的 Persona Template/Assignment/Private Stance、Prompt Version，以及 provider/model/effective non-secret configuration provenance；不得以 mutable `latest` 重解释历史 utterance。
- AI Participant 是 session role identity；AI Runtime 是 generation capability。Runtime 不拥有 participant seat、stance、floor 或 lifecycle，Persona Template 不保存 prompt/provider/model binding 或 secret。
- Generation Request 与 final Utterance 分离；逻辑状态为 `requested`、`generated`、`persisted`、`failed`。一个 logical request 至多产生一个 final utterance，late result 在 phase/grant stale 后必须丢弃。
- Timeout、provider unavailable、rate limit、partial/invalid generation 使用 typed、bounded、idempotent failure policy。P1-5D application retry 固定为 `0`；失败不改变 phase/deadline/floor/scoring。P1-5E-1 now freezes the future automatic release/intervention coordination policy without implementation。
- Provider/model raw response、credential、chain-of-thought 和不必要的完整 rendered prompt 不进入 public/error/log surfaces。审计保留足以解释 prompt/model/config 的最小 provenance。
- 多 provider、cost accounting、enterprise model、audit trace 和 prompt iteration 是 future commercial-readiness boundary；a DB/admin-managed server-side model source may later replace P1-5D environment configuration without changing the runtime contract，but no model table/admin API/UI/hot reload/registry/routing exists now；billing、quota、payment、multi-tenant 继续 Deferred。

完整冻结和后续 implementation gates 见 [`exec-plans/P1-5_ai-runtime-foundation.md`](exec-plans/P1-5_ai-runtime-foundation.md)。

### P1-5B implemented persistence boundary

- `modules/ai_runtime` is a provider-neutral domain/application persistence boundary, not an LLM runtime loop。It publishes immutable Prompt Versions and applies explicit request/start/complete/fail commands；there is no SDK import、provider interface/client、prompt renderer、worker or automatic caller。
- Request/start/complete use the existing owner-scoped session aggregate lock and validate exact current grant、AI participant and phase。Completion atomically stores one final utterance and a `COMPLETED` request；a database composite foreign key prevents an utterance from referencing any other request state。
- Failure is a typed terminal request record only。It writes no utterance/event, does not release or transfer floor, and cannot mutate session status/phase/deadline/scoring。The future orchestrator remains responsible for invoking this persistence boundary and then using the existing deterministic floor-release service。
- Historical provenance is recovered by immutable foreign-key paths to Question Version、Persona Assignment、Prompt Version、actual provider/model identifiers and closed non-secret configuration version。No public API/WS/Web projection is introduced。

### P1-5C implemented deterministic runtime boundary

- `modules/ai_runtime/prompting.py` uses a closed variable vocabulary and deterministic rendering over the exact Prompt Version。Context assembly reads the session-bound Question Version and only the granted AI participant's Assignment/Persona/Private Stance；other seats、secrets and mutable latest pointers are excluded。
- Immutable provider-neutral generation input/result types and a deterministic local harness exercise success plus typed timeout/unavailable/rate-limit/invalid/partial/internal outcomes without network I/O or a provider interface/SDK。
- Application orchestration uses short transactions for context/request claim and terminal persistence, while executor work runs outside every transaction and row lock。`REQUESTED` is claimed once；`RUNNING` replays as reconciliation-required no-op；terminal states replay durable truth。
- Before authoritative generation create/claim/final-completion mutation, the application holds the existing session aggregate row lock and invokes P1-3 `reconcile_due_for_locked_aggregate(...)` with server-authoritative current UTC；reconciliation and generation-context validation share the required transaction boundary。
- AI generation success/failure does not independently mutate phase、deadline、floor policy/current owner、scheduler decision、lifecycle events or discussion sequence。An overdue reconciliation may authoritatively advance phase/deadline, release the old grant, append ordered `floor.released` / `session.state_changed` events and advance sequence；those writes are P1-3 lifecycle facts, not AI Runtime decisions, and the stale generation then fails closed without an utterance。Automatic floor-triggered generation/release and all transport remain Deferred。

### P1-5D completed first-provider boundary

- `GenerationProvider` is the smallest project-owned async callable Protocol over existing provider-neutral input/result types；the deterministic harness remains compatible and no factory、registry、router、fallback hierarchy or provider-specific domain object was added。
- `ZhipuGenerationProvider` uses one `httpx.AsyncClient` request with required lazy `ZhipuProviderSettings.model` (currently `glm-4.7-flashx`)。It requires configured/input/outbound/response/durable model alignment and model-independent `ZHIPU_CHAT_DEV_V1` provenance，rejects mismatch before or after HTTP as appropriate，disables redirects/retries/streaming/thinking，applies bounded timeouts and normalizes only safe typed outcomes。
- `ZhipuProviderSettings` is a separate lazy server-only boundary with required `GIA_API_ZHIPU_API_KEY: SecretStr` and required bounded non-secret `GIA_API_ZHIPU_MODEL: str`。Ordinary API startup requires neither；changing the model requires configuration plus API restart but no Python、adapter or schema change。Both identifiers remain internal provenance，and the key、rendered prompt、request/response body、provider exception and reasoning content are not logged or persisted。
- Provider execution still uses the existing P1-5C explicit runtime callable outside database transactions。Durable `RUNNING` remains reconciliation-required/no automatic re-call；late results、overdue reconciliation、concurrent claims and at-most-one utterance retain the P1-3/P1-5C authority rules。
- Automated provider/runtime tests use injected `httpx.MockTransport` and make zero real GLM calls。Implementation and config-driven patch actual-source reviews passed。Final user-run sanitized real-provider acceptance smoke：`PASS`；`zhipu` / `glm-4.7-flashx` / `ZHIPU_CHAT_DEV_V1` returned `RawGenerationSuccess` and satisfied the intended Chinese group-interview smoke expectation，without recording credentials or raw provider data。P1-5D is `DONE`；P1-5E automatic orchestration is separately closed below。

### P1-5E automatic orchestration architecture — completed through E3

- P1-5E is an application-level、state-driven coordination layer。P1-3 remains lifecycle authority；P1-4 Floor Scheduler decides who；P1-5 AI Runtime decides what。The coordinator never directly writes current-grant/phase/deadline/floor facts or selects a participant。
- Correctness is recovered from durable session/current-grant、FloorGrant/Release、GenerationRequest/AiUtterance、SessionAction/scheduler children and ordered discussion-event state。`floor.granted` may wake the drive，but no exactly-once event listener、Redis、queue、distributed lock or in-memory mutex is authoritative。
- Exact existing calls are `generate_ai_utterance(...)`，then `apply_floor_command(...ReleaseFloorCommand...)` after confirmed terminal truth，then `apply_scheduler_command(...ScheduleFloorCommand...)` after release commit。Provider I/O remains outside all transactions/row locks。
- One exact AI grant maps to deterministic generation request、utterance、release action、next-schedule action and scheduler child UUID identities。An existing request reuses its durable timestamp/prompt/provider/model/configuration；an existing action/decision is consumed through current `SessionAction` replay/conflict semantics rather than replaced by a random identity。
- New runtime configuration resolves stable `AI_CANDIDATE_TURN` version `1` to an exact immutable Prompt Version ID；provider is `zhipu`，model comes from lazy server-side `GIA_API_ZHIPU_MODEL`，and configuration is `ZHIPU_CHAT_DEV_V1`。No DB UUID or implicit latest prompt is hardcoded。
- `COMPLETED`/replay with an exact durable utterance releases the still-current grant as `SPEAKER_FINISHED`。`FAILED`/replay releases the still-current grant as `INTERRUPTED` while retaining the typed generation failure as authoritative。`RUNNING`/reconciliation、conflict、internal or otherwise uncertain truth stops without release/scheduling/provider re-call。
- `CONTEXT_REJECTED` and `STALE_RESULT` force authoritative re-read：a no-longer-current grant or changed lifecycle is `STATE_CHANGED`，while the same exact current grant is `RECONCILIATION_REQUIRED`；neither justifies release or scheduling。`SUPERSEDED` may release only after proving the unique winning utterance for the same still-current grant；otherwise it stops/re-enters safely。
- P1-3 overdue reconciliation wins before generation/release/schedule mutation。If it releases or changes phase，the orchestrator consumes those committed facts and never overwrites lifecycle reason、deadline or sequence。
- Release commits before scheduling。For release/scheduler persistence uncertainty，an exact expected durable result is recovered，another proved authoritative change is `STATE_CHANGED`，and an unchanged applicable checkpoint without the expected durable result is `RECONCILIATION_REQUIRED`。Scheduler `GRANT` is classified by the newly durable actor kind；`NO_GRANT` and `REQUEST_INTERVENTION` stop the drive。
- Concurrent drives converge through deterministic identities、one request claimant、unique utterance/grant constraints、aggregate lock and exact sequence/current-grant preconditions。Concurrent post-release crash recovery produces exactly one deterministic scheduler action/decision and no duplicate next-speaker winner；a losing conflict reads that durable winner and never changes IDs。
- P1-5E-2 is the completed one-AI-turn kernel plus one release and one scheduler call。P1-5E-3 implements the provider-neutral continuous loop by repeatedly consuming that closed result，bounded by `MAX_AUTOMATED_AI_TURNS_PER_DRIVE = 8` and stopped by HUMAN/no-current-work/no-grant/not-applicable/intervention/state-change/reconciliation/budget boundaries。Only a proved release advances the budget；scheduler-only crash recovery does not。
- The thin composition constructs `ZhipuProviderSettings` and `ZhipuGenerationProvider` only when explicitly invoked，then passes canonical `zhipu` / configured model / `ZHIPU_CHAT_DEV_V1` provenance and the existing V0.1 scheduler policy。Missing/invalid settings fail safely before provider or drive execution；ordinary app import/startup remains independent of provider configuration。
- P1-5E-3 implementation actual-source review is `PASS` with findings none。The sanitized composition smoke proves one completed/persisted AI turn reaches a HUMAN current owner with `WAITING_FOR_HUMAN` and one advanced turn；provider/model/configuration provenance is `zhipu` / `glm-4.7-flashx` / `ZHIPU_CHAT_DEV_V1`。P1-5E is `DONE`；P1-5F implementation remains separately gated，while F1 now freezes its contract below。
- Existing schema is sufficient for orchestration correctness；no orchestration table or migration is planned。At E3 closeout API/WebSocket/Web、public utterance projection、human-side transport behavior and independent acceptance remained P1-5F concerns；F1 now freezes them docs-only and F2～F4 retain implementation/acceptance ownership。Full outcome/restart matrices are in [`exec-plans/P1-5_ai-runtime-foundation.md`](exec-plans/P1-5_ai-runtime-foundation.md)。

### P1-5F-1 realtime/public architecture — contract frozen, implementation deferred

- Public protocol split is now exact：WebSocket owns active discussion commands and the complete ordered incremental formal-event stream；REST owns session snapshot and independent transcript/history reads。Human text uses WS `participant.utterance.submit`，not REST or SSE。
- This is a public contract，not a deployment-topology promise。V0.1 may invoke progression best-effort in process，while correctness stays in PostgreSQL durable state and reentrant P1-4/P1-5E services。Future Redis/NATS/Kafka、gateway or multi-worker routing can replace delivery/invocation without changing the public contract；none is added in F1。
- Transport derives Human identity from opaque authenticated user plus the exact current `HUMAN` grant after locked lifecycle reconciliation。Browser cannot supply participant、actor、grant、phase or AI/provider/runtime identity。
- One unified `participant.utterance.created` v1 event represents formal Human and AI speech。Human action identity is public for pending/reconnect confirmation；AI utterance events use `action_id = null`。
- Historical P1-4 floor-event v1 remains unchanged：grant/intervention require a non-null UUID4 action identity and release is nullable。P1-5F adds floor-event v2 with the same names/payload meanings but a nullable envelope `action_id` meaning only public client causation；direct Human-command causation may retain that Human ID，while automatic scheduler/release/intervention projects null and keeps its durable `SessionAction` private。F2/F3 must serialize/parse both versions rather than mutate v1 semantics。
- `GET /sessions/{session_id}/utterances` is an owner-only sequence-cursor transcript projection；the session snapshot does not embed transcript。`DiscussionEvent` is current durable public transcript/event storage，not a permanent physical contract。
- The Human utterance and exact `SPEAKER_FINISHED` release are one aggregate-locked commit producing consecutive utterance/release events。The scheduler runs only after that commit in a separate deterministic checkpoint and remains the sole who-speaks authority。
- Successful AI completion atomically commits `LlmGenerationRequest.COMPLETED + AiUtterance + participant.utterance.created`。P1-5E then releases and schedules in its existing separate commits。Failure fabricates no utterance and surfaces only `floor.released / INTERRUPTED` plus safe generic Browser UX。
- Every WebSocket send follows commit。Disconnect cannot roll back、regenerate、duplicate or replace action identity；snapshot、transcript and full ordered catch-up recover durable truth。
- Browser transcript merges by `utterance_id` and orders by event sequence。Transcript-only sequences are intentionally non-contiguous，while full WS gap detection remains strict。Pending content stays memory-only and is not a transcript bubble before durable confirmation。
- Existing source is sufficient without schema or authority change：session aggregate lock、Human participant user link、FloorRelease helper、DiscussionEvent sequence and AI completion transaction cover the frozen atomic/recovery boundaries。Exact command/event/REST fields、crash matrix、privacy and F2～F4 acceptance are authoritative in [`exec-plans/P1-5_ai-runtime-foundation.md`](exec-plans/P1-5_ai-runtime-foundation.md)。

## Configuration, secrets and error boundaries

- 配置采用类型化、启动时校验的方式；
- `.env.example` 只提供安全占位符，私有环境文件不得提交；
- 服务端密钥不得进入浏览器 bundle、公开构建产物或日志；
- Zhipu key/model only load through lazy `GIA_API_ZHIPU_API_KEY` / `GIA_API_ZHIPU_MODEL` settings when the provider is explicitly constructed；neither has a default，missing/blank values fail closed，and the model is server-only non-secret configuration rather than a public/API/UI setting；
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
- P1-2：closed domain/schema validation、真实 PostgreSQL immutable-version/seed/history integration、private non-disclosure 和最小 browser vertical-slice regression；fake provider 仍等真实 provider caller；
- P1-3：pure transition/timing tests、真实 PostgreSQL concurrency/deadline/restart recovery、historical event compatibility 和 authoritative Browser phase-flow regression；不以 Browser timer test 替代 server correctness；
- P1-4：generalized participant/single-owner persistence、pure deterministic scheduling、enumeration-order invariance、fairness/monopoly/phase/intervention、真实 PostgreSQL race/restart recovery、safe explanation/non-disclosure 和 authoritative Browser floor-flow regression；
- P1-5A：docs-only links/state/scope/hash/diff checks；fake provider、runtime unit/integration 和真实 LLM tests 均未运行且未进入实现；
- P1-5C：closed prompt/context unit tests、deterministic harness cases、real PostgreSQL success/failure/replay/concurrency/stale-result integration and full backend regression；真实 LLM tests remain absent；
- P1-5D：HTTPX MockTransport exact-request/error/privacy/no-retry tests plus real PostgreSQL mocked-provider provenance/replay integration；all automated tests are network-free and the final user-run sanitized real-provider acceptance smoke is `PASS`；
- P0-5D 已因真实跨应用 auth flow 加入 `@playwright/test 1.62.1`，只运行 Chromium，并由 test-only 编排器使用迁移后的隔离 `gia_p05d_*` PostgreSQL database；
- 真实 LLM tests 必须显式执行，不进入默认 CI。

## Logging and observability

- P0-6C 已将 project-owned application logs harden 为 UTF-8 newline-delimited JSON，核心字段为 UTC `timestamp`、uppercase `level`、稳定 `event` 与 `logger`；
- 通用请求沿用既有 UUIDv4 `request_id`，并记录 method、resolved route template、固定 `matched`/`unmatched` classification、status 与 monotonic duration；404/unmatched 不记录 raw/hashed/truncated path 或 query；
- handled HTTP response（包括 4xx）使用 `http.request.completed`，只有未正常完成 pipeline 的异常路径使用 `http.request.failed` 和固定安全 exception category；现有 lifespan 发出 `app.startup.completed` / `app.shutdown.completed`；
- project logger 使用互斥 stdout（DEBUG～WARNING）/stderr（ERROR～CRITICAL）handlers，重复 `create_app()` 不叠加 handler，也不重配 process root logger；Uvicorn/server-owned logs 保持独立；
- `session_id`、`connection_id`、provider invocation id、`job_id` 只在相关能力实际出现后增加；
- 不为未来字段生成虚假 ID；
- request/response body、headers、Cookie/session、Authorization、query、raw path、credential URL、exception message/traceback 与敏感模型 payload 不进入 application logging data model；
- P0-6D 已实现默认关闭、app-owned/non-global 的 provider-neutral OpenTelemetry tracing；既有 middleware 只将白名单 `traceparent` 交给 W3C propagator，明确不接受 `tracestate`/baggage，并创建受控 `SpanKind.SERVER` span；active trace/span IDs 与 `request_id` 日志关联；
- span 只允许 method、resolved route template、status、固定 error category 与 project-owned `service.name`；resource 直接由 typed config 构造，不运行 ambient detector 或吸收任意 `OTEL_RESOURCE_ATTRIBUTES`/`OTEL_SERVICE_NAME`；不采集 query/header/body/Cookie/identity/SQL 或 exception detail；404 使用固定 `<unmatched>`；
- enabled path 使用显式 parent-based always-on sampler 与 OTLP/HTTP `BatchSpanProcessor`，不接受 ambient sampler 覆盖；会实际禁用 SDK 的 `OTEL_SDK_DISABLED` 或会注入 exporter headers/client credentials/session provider 的 ambient config 均在 provider/exporter 创建前 fail closed；startup 不探测 collector；OTLP HTTP export timeout 为 5 秒，SDK BatchSpanProcessor shutdown 使用 OTel 1.44 自身 bounded shutdown semantics，之后继续 database dispose；默认关闭不执行这些 ambient checks，也不创建 exporter 或网络 caller；
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
- OTel Logs/metrics、auto-instrumentation、Collector/backend deployment、authenticated exporter config、Sentry/SaaS、analytics；
- 具体 LLM/model、ASR、TTS 和 Embedding 实现；
- V0.1 之后的 email/phone/WeChat/OAuth identity、verified recovery flow、RBAC/authorization、支付、云平台、中国生产部署、对象存储、CDN 和 PWA production strategy。

Redis 只在多 API workers、横向扩容、跨进程 WebSocket broadcast、distributed lock、centralized rate limiting 或 durable task queue 出现时重新评估。

独立后台任务队列只在 reliable retry、delayed jobs、scheduling、independent workers 或 cross-process execution 出现时重新评估。当前能够合理完成的任务同步执行。

## Future work

- P0-5C：completed；
- P0-5D：completed；真实 browser Cookie/CORS/CSRF 闭环已通过 Chromium 验证；
- P0-5E：completed；final outcome `PASS after findings remediation and independent recheck`；
- P0：`DONE`；P0-1～P0-7 completed；P0-7 finding-only independent recheck `PASS`，P1 readiness `READY`；其后用户已明确批准进入 P1；
- P1：`IN_PROGRESS`；P1-1～P1-4 均已完成且 independent verdict `PASS`；P1-5A/P1-5B/P1-5C/P1-5D/P1-5E/P1-5E-1/P1-5E-2/P1-5E-3/P1-5F-1 已完成；P1-5F remains `IN_PROGRESS`；P1-5F-2～F4 transport/Web/E2E implementation、记忆和基础报告继续 Deferred；
- P2 以后：只在对应阶段获批后增加语音、评分训练和商业化能力。

## 与其他文档关系

- 技术决策：[`DECISIONS.md`](DECISIONS.md)
- 数据边界：[`DATABASE.md`](DATABASE.md)
- API 与事件：[`API.md`](API.md)
- 会话与编排：[`AGENT_BEHAVIOR.md`](AGENT_BEHAVIOR.md)
- 安全约束：[`PRIVACY_AND_SAFETY.md`](PRIVACY_AND_SAFETY.md)
- 当前执行顺序：[`ROADMAP.md`](ROADMAP.md) 和 [`TASKS.md`](TASKS.md)
