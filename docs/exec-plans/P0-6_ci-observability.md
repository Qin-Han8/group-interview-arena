# P0-6 CI、日志与基础可观测性执行计划

## Status

- Parent task：`P0-6 — DONE`
- Completed substeps：`P0-6A — completed；actual-source final review PASS；four review findings closed`；`P0-6B — completed；implementation/local parity/actual-source review/remote CI PASS`；`P0-6C — completed；implementation/API quality gates/actual-source review/finding remediation/re-review/remote CI PASS`；`P0-6D — completed；implementation/local gates/actual-source review/findings remediation/re-review/remote CI PASS`；`P0-6E — completed；cross-layer validation/P0-6 closeout/actual-source review PASS`
- Current gate：none；P0-6 closed
- P0-7：独立任务，`NOT_STARTED`
- Scope owner：[`TASKS.md`](../TASKS.md)
- Product baseline：[`PROJECT_MASTER_PLAN.md`](../PROJECT_MASTER_PLAN.md)
- Last updated：2026-08-16

本计划冻结 P0-6 的执行边界与风险门禁。P0-6A 已完成且只产生文档。P0-6B workflow implementation、local parity、actual-source review、findings remediation 与 remote GitHub Actions verification 均已完成并 `PASS`。P0-6C implementation、API quality gates、actual-source review、finding remediation/re-review 与 remote GitHub Actions verification 均已完成并 `PASS`。P0-6D implementation、local gates、actual-source review、findings remediation/re-review 与 remote GitHub Actions verification 均已完成并 `PASS`。P0-6E cross-layer validation、security/privacy acceptance、cleanup 与 P0-6 closeout 均已完成并 `PASS`；P0-7 保持 `NOT_STARTED`。

## Goal

在不扩大 P0/V0.1 产品范围的前提下完成四项可验证结果：

1. 用 GitHub Actions 自动执行仓库现有 API、PostgreSQL、Web 与 Chromium 质量门禁；
2. 在既有 `request_id`、error envelope 与 stdlib logging 基础上冻结并实现安全的一行 JSON 日志契约；
3. 建立 provider-neutral、默认关闭、无外部 backend 也可启动和测试的最小 OpenTelemetry tracing foundation；
4. 在 P0-6E 完成跨层回归与 P0-6 closeout，但不提前执行 P0-7 的独立 P0 final acceptance。

## Current baseline

### Repository gate at P0-6A start

- Repository：`E:\group-interview-arena`
- Branch：`main`
- Working tree：clean
- Staged files：`0`
- HEAD：`e6f293a`（`P0-5: close identity boundary after final review`）
- P0-5：`DONE`，P0-5A～P0-5E 均已完成；P0-5E 最终结果 `PASS`
- P0-6 runtime implementation：尚未开始
- `.github/`：当前不存在
- `docs/PROJECT_MASTER_PLAN.md` SHA-256：`2388A9660320406CB35D5354126AD71C6849A98DB7C4A356796CA951BF372F26`

### Existing capabilities to preserve

- API 已通过 UUIDv4 `request_id` middleware、`ContextVar`、`X-Request-ID`、安全 error envelope 和 request/error structured logging 建立关联基础；P0-6C 是 hardening，不重新实现第二套 request context。
- 现有日志字段包括 timestamp、level、logger、message，以及 request_id、method、path、status_code、duration_ms 等 request fields；未处理异常通过现有 handler 返回稳定 envelope。
- FastAPI `lifespan` 已拥有 async SQLAlchemy engine/sessionmaker 的创建与 dispose；P0-6D 的 provider flush/shutdown 必须接入同一生命周期，不增加旁路生命周期。
- `Settings`/`DatabaseSettings` 已形成 server-only typed config boundary，数据库 URL 使用 `SecretStr`；可观测性配置必须进入这一边界，且不得暴露给 Web。
- PostgreSQL integration harness 已能创建、迁移并清理受保护前缀的隔离数据库；Compose 与测试基线使用 PostgreSQL `18.4`，当前精确镜像为 `postgres:18.4-trixie`。
- API 当前质量工具为 uv `0.12.x`、CPython `3.14`、pytest、Ruff、Pyright 与 Alembic；Web 为 Node `24.x`、pnpm `11.21.0`、ESLint、Prettier、TypeScript、Vitest、Next production build 与 OpenAPI drift check。
- 现有正式 OpenAPI generation path 不要求 database URL，也不运行 FastAPI lifespan；P0-6B 必须保持这一 DB-independent contract。
- P0-5D 已建立 Chromium-only Playwright E2E、隔离 `gia_p05d_*` database、API/Web 编排与 Windows `SelectorEventLoop` runtime。CI 必须复用其安全模型，不能连接 development database。

## Dependencies and governing decisions

- Task dependencies：P0-2、P0-3、P0-4、P0-5 均为 `DONE`；P0-6B～P0-6E 必须按顺序获得用户批准。
- `ADR-004`：Node 24/pnpm 与 CPython 3.14/uv runtime and lockfile policy；
- `ADR-005`：PostgreSQL 18.x、SQLAlchemy 2.x、Alembic 与 real integration tests；
- `ADR-007`：FastAPI OpenAPI 是 REST contract Source of Truth；
- `ADR-010`：应用原生运行、基础服务使用 Compose；CI 可用等价 PostgreSQL service container；
- `ADR-012`：分阶段 pytest/Ruff/Pyright、Vitest/ESLint/TypeScript/Prettier/Playwright quality strategy；
- `ADR-013`：typed config、safe error envelope、structured logging、request_id 与 P0-6 OTel trigger；
- `ADR-015`：identity/session/Cookie/CORS/CSRF safety boundary，决定 Chromium CI gate 的安全验收范围。

本计划不改变上述 Accepted ADR，也不需要新增 durable architecture decision。CI job 划分、JSON event schema 与受控 server-span implementation 属于 P0-6 已授权范围内的可逆实现选择；若后续必须放宽隐私边界或引入 production observability architecture，先提出 Proposed Decision。

## Plan decisions

- 固定采用 P0-6A～P0-6E 五阶段结构，不增加机械子阶段；
- Chromium E2E 进入 CI gate；
- local/prod 共用一行 JSON logging schema；
- tracing 默认关闭，启用时采用 provider-neutral OTel API/SDK + optional OTLP/HTTP；
- P0-6D 使用现有 request middleware 创建安全 server spans，不采用当前 beta FastAPI/ASGI auto-instrumentation；
- OTel Logs、metrics、SQLAlchemy instrumentation 与所有 external backend 保持 Deferred；
- P0-6E 只 close out P0-6，P0-7 继续独立执行。

## Five-stage decomposition

### P0-6A — Preflight / scope freeze / execution plan

- 完成 baseline blocking gate、mandatory context recovery 与官方资料核对；
- 冻结 CI、logging、tracing、configuration、dependency 与 test boundaries；
- 创建本计划并最小同步 TASKS/ROADMAP；
- 只运行文档级验证并生成 actual-source review bundle；
- actual-source final review `PASS`，四个 execution-plan design findings 均已关闭，P0-6A completed。

### P0-6B — GitHub Actions CI baseline

- 新建唯一基础 CI workflow；
- 自动化 API static/unit、real PostgreSQL integration/migration、Web quality/OpenAPI drift 与 Chromium E2E；
- 先以正确性和清晰失败边界为目标，不加入 CD、发布或仓库自动化扩展。

#### P0-6B implementation checkpoint

- `.github/workflows/ci.yml` 已实现 pull request 与 push-to-main triggers、`contents: read`、per-workflow/ref concurrency cancellation、四个 fail-closed jobs 与合理 timeouts；
- live official preflight 后 authoritative pins 为 checkout v7.0.1 `3d3c42e5aac5ba805825da76410c181273ba90b1`、setup-python v7.0.0 `5fda3b95a4ea91299a34e894583c3862153e4b97`、setup-node v7.0.0 `820762786026740c76f36085b0efc47a31fe5020`、setup-uv v10.0.1 `20cfd1bf945f4377ade1205e4dbc17946fc9a30d`、pnpm/setup v2.0.2 `84cb39b217b10273981911c288cd62326dc7c6d2`；
- API quality job 不使用 PostgreSQL；PostgreSQL integration/migration 与 Chromium E2E jobs 使用 `postgres:18.4-trixie`、CI-only dummy credentials 和 disposable databases；Web/OpenAPI job 不使用 PostgreSQL，并通过 actual app + `--lifespan off` 复用正式 HTTP generator；
- local parity：frozen sync/lock、API unit 132、integration 18、Ruff、format、Pyright、disposable Alembic CLI、Web lint/format/typecheck/Vitest 16/build/OpenAPI drift、Chromium 1 均通过，skipped 0；
- cleanup：temporary database、`:3000`、`:8000`、Playwright test-results/report/screenshot/video/trace residual 均为 0；
- dependency/lockfile/runtime/schema/migration/API contract 均未改变；P0-6C/D 未开始；
- actual-source review `PASS`；两个 findings（pnpm v11 successor action 与 temporary database exact-prefix residual diagnostics）完成 remediation 并通过 re-review；
- Remote CI verification completed / `PASS`：reviewed commit `513491af128849f93c3ae601a906bd88fd8860f4` 经 push-to-main 触发 GitHub Actions run #1，API quality、PostgreSQL integration and migration、Web quality and OpenAPI drift、Chromium E2E 四个 required jobs 均 completed / success；P0-6B completed。

### P0-6C — Structured logging hardening

- 在现有 request_id/logging foundation 上增加稳定 event schema、低基数字段、exception category 与安全测试；
- 保持 API error envelope 与用户可见错误边界不变；
- 输出仍为 stdlib structured application logs，不引入 vendor SDK 或日志 backend。

#### P0-6C implementation checkpoint

- project-owned logger 输出单行 UTF-8 JSON，核心字段、互斥 stdout/stderr、idempotent handlers 与 root/Uvicorn boundary 均按冻结 contract 实现；
- request middleware 复用既有 UUIDv4 request context，matched route 仅记录 resolved template，unmatched/404 omit route 并使用 fixed classification；handled responses 与真正 pipeline failures 使用不同 event 且每个请求只记录一个终态 event；
- lifespan 的真实 database lifecycle caller 产生 startup/shutdown events；unexpected exception 与 auth persistence failure 只记录安全固定 category，无 exception message/traceback；
- targeted 53、API unit 139、PostgreSQL integration 18、API full 157、Ruff、format、Pyright 与 Alembic single-head checks 均通过；sensitive sentinel、query/raw/derived path negative tests 通过；
- dependency/lockfile、schema/migration、API/OpenAPI contract、Web、CI workflow 与 OpenTelemetry 均未改变；
- actual-source review 发现的 `JsonFormatter` missing/malformed event fail-safe finding 已用固定 `logging.record.invalid` fallback 和安全 regression 修复，remediation source re-review `PASS`；
- reviewed commit `2d3d235d08aefb6b536ad6217a99c167fe879eb3` 经 push-to-main 触发 GitHub Actions CI run #4；API quality、PostgreSQL integration and migration、Web quality and OpenAPI drift、Chromium E2E 四个 required jobs 均 completed / success；P0-6C completed。

### P0-6D — OpenTelemetry tracing foundation

- 引入最小 OTel API/SDK 与可选 OTLP/HTTP trace exporter；
- 在现有请求 middleware 中创建受控 server span，支持 W3C trace context 与日志 correlation；
- 默认关闭、不探测 collector、不要求外部 backend；
- 不采用 OTel Logs pipeline，不引入 metrics backend。

#### P0-6D implementation checkpoint

- 2026-08-16 live official preflight 确认 OTel API/SDK/OTLP HTTP exporter `1.44.0` 为 current stable core release，支持 CPython 3.14；实际核对 `TracerProvider`、`SpanKind.SERVER`、`record_exception=False`、`set_status_on_exception=False`、W3C propagator、`BatchSpanProcessor`、`OTLPSpanExporter`、`Resource`、`force_flush`/`shutdown` 与 `InMemorySpanExporter` public APIs；
- direct dependencies 为 `opentelemetry-api>=1.44.0,<2`、`opentelemetry-sdk>=1.44.0,<2`、`opentelemetry-exporter-otlp-proto-http>=1.44.0,<2`，lock resolution 为 1.44.0；标准 OTLP HTTP transitive graph 包含 proto/common、semantic conventions、protobuf、googleapis common protos 与 requests HTTP stack，无 contrib instrumentation、distro、gRPC、metrics/log exporter 或 vendor SDK；
- `Settings` 已实现默认 disabled、service name 与 fail-closed OTLP endpoint 校验；endpoint 仅允许 scheme/host/port/path，拒绝 userinfo/query/fragment，配置不进入 Web/OpenAPI；
- 每个 FastAPI app lifespan 显式拥有 non-global provider/tracer；disabled path 不创建 provider/exporter/worker/network，enabled path 使用 OTLP HTTP + `BatchSpanProcessor`，startup 不探测 collector；OTLP HTTP export timeout 为 5 秒，SDK BatchSpanProcessor shutdown 使用 OTel 1.44 自身 bounded shutdown semantics，并先于 database dispose；
- 既有 middleware 仅把白名单 `traceparent` 交给 W3C propagator，不接受 `tracestate`/baggage，并创建受控 `SpanKind.SERVER` span；matched name 为 `METHOD route-template`，unmatched 为固定 `METHOD <unmatched>`；attributes 仅含 method、route template、status、固定 error category，resource 直接由 project typed config 构造唯一 `service.name`，不运行 ambient detector；4xx/404 保持 unset status，5xx 标记 error，禁用 exception recording；
- project JSON formatter 从 active valid span context 自动增加固定宽度 lowercase `trace_id`/`span_id`，caller-supplied 同名字段无效；无 active span 时省略，lookup failure 继续输出安全单行 JSON；
- OTel SDK 1.44.0 的 `BatchSpanProcessor` 没有简洁可靠的 public async export-failure callback，因此不建立 wrapper hierarchy 或依赖 private internals；异步 export result 保留 SDK handling，项目只在真实可控的 flush timeout/error、provider shutdown error caller 记录安全 `telemetry.export.failed` category；
- initial targeted 56、API unit 165、PostgreSQL integration 18、API full 183、Ruff、format、Pyright、Alembic single-head/drift 与 Chromium 1 均通过；sensitive sentinel、export failure availability、provider isolation、database dispose 与 processor-thread cleanup 均有回归；
- actual-source review 的两个 data-boundary findings 已修复并通过 re-review：`traceparent` allowlist carrier 防止 arbitrary `tracestate` 进入 child context，public `Resource(attributes=...)` 防止 `OTEL_RESOURCE_ATTRIBUTES`/`OTEL_SERVICE_NAME` 与 detector metadata 绕过 project allowlist；remediation targeted tracing/logging/config 58 项通过；
- 后续 actual-source review 的两个 ambient-config findings 已修复并通过 re-review：enabled path 对会实际禁用 SDK 的 `OTEL_SDK_DISABLED` fail closed，并用 public `ParentBased(ALWAYS_ON)` 固定默认语义；OTLP HTTP exporter 的 ambient headers、client key/certificate 与 trace credential-provider side channel 在构造 provider/exporter 前做 presence-only fail-closed validation，不读取 credential value；disabled path 保持无 exporter 且不受这些变量影响；
- application behavior、REST/OpenAPI/error envelope、database schema/migrations、Web、CI workflow 与 JavaScript dependencies 未改变；reviewed commit `96581dd7c3f972dbe5d90592ee34d9973bd3dd41` 经 push-to-main 触发 GitHub Actions CI run #6，API quality、PostgreSQL integration and migration、Web quality and OpenAPI drift、Chromium E2E 四个 required jobs 均 completed / success；P0-6D completed。

### P0-6E — Cross-layer validation / P0-6 closeout

- 运行风险匹配的 API/Web/PostgreSQL/Chromium/CI configuration final acceptance；
- 复核日志和 span 的敏感数据负面测试、默认关闭行为与 shutdown；
- 同步 P0-6 文档状态并完成 P0-6 actual-source closeout；
- 不执行 P0-7 的独立 P0 acceptance，也不以 P0-6E 替代 P0-7。

## CI boundary

### Workflow boundary

P0-6B 冻结为一个 `.github/workflows/ci.yml`，使用 Linux hosted runner `ubuntu-24.04`，最小权限 `contents: read`：

- trigger：`pull_request`；
- trigger：`push`，仅 `main`；
- concurrency group：`${{ github.workflow }}-${{ github.event.pull_request.number || github.ref }}`；
- `cancel-in-progress: true`，取消同一 workflow/PR 或 branch 的过期运行，不跨 workflow 相互取消；
- 不使用 production secret，不对 pull request 提供部署凭据。

### P0-6A candidate action pin snapshot

以下是 2026-08-15 P0-6A research snapshot，只用于记录候选 pin，不是 P0-6B authoritative selection。实施时优先用完整 commit SHA 固定供应链输入，并在注释中记录对应 release：

- `actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1`（v7.0.1）；
- `actions/setup-node@820762786026740c76f36085b0efc47a31fe5020`（v7.0.0）；
- `actions/setup-python@a309ff8b426b58ec0e2a45f0f869d46889d02405`（v6.2.0）；
- `pnpm/action-setup@0ebf47130e4866e96fce0953f49152a61190b271`（v6.0.9）；
- `astral-sh/setup-uv@c771a70e6277c0a99b617c7a806ffedaca235ff9`（v9.0.0）。

P0-6B implementation preflight 必须实时查询官方文档/release，核对候选 release/SHA 未撤回且仍满足当前 runner/runtime；该次 recheck 的结果才是 authoritative pin selection。版本变化只更新 workflow 供应链选择，不改变本计划产品边界，也不因 P0-6A review 期间的 release churn 反复改写 snapshot。

### Jobs and gates

#### 1. API quality

- CPython `3.14`；uv 按 `apps/api/pyproject.toml` 的 `required-version` 安装；
- `uv sync --frozen`；
- `uv lock --check`；
- `pytest -m "not integration"`；
- `ruff check .`；
- `ruff format --check .`；
- `pyright`。

该 job 不需要 PostgreSQL，不构造占位 database URL，不启动 API。

#### 2. PostgreSQL integration and migration

- GitHub service container 使用与本地基线精确一致的 `postgres:18.4-trixie`；
- Linux runner job 使用 loopback published port、ephemeral non-production credentials 与 `pg_isready` health check；
- `uv sync --frozen` 后在 disposable CI database 上运行 Alembic upgrade/head/current/check；
- 运行 `pytest -m integration`，继续由现有 harness 创建和清理精确前缀的 per-test databases；
- CI database 名称必须显式标识为 disposable CI，且不得等于 development database；
- 失败后仍需执行精确 residue/status diagnostics，不执行 broad database deletion。

#### 3. Web quality and OpenAPI drift

- Node `24.x`、pnpm `11.21.0`；
- `pnpm install --frozen-lockfile`；
- `pnpm web:lint`；
- `pnpm web:format:check`；
- `pnpm web:typecheck`；
- `pnpm web:test`；
- `pnpm web:build`；
- `pnpm web:api:check`。

OpenAPI drift check 继续以 FastAPI OpenAPI document 为 Source of Truth，并保持 DB/lifespan-independent。P0-6B implementation preflight 根据当前正式 generator 选择 direct application OpenAPI generation、lifespan-disabled temporary API，或现有等价安全方式；不得仅为 OpenAPI generation 给该 job 增加 PostgreSQL service、migration 或 DB-backed API lifecycle，也不得改变 OpenAPI Source of Truth。真实 PostgreSQL coverage 完整保留在 PostgreSQL integration/migration job 与 Chromium E2E job。

#### 4. Chromium E2E

P0-5D browser E2E 必须成为 CI gate，因为它是当前唯一覆盖 Cookie、CORS/CSRF、reload restore 与 logout 的真实浏览器跨层证据：

- 使用 `postgres:18.4-trixie` service 和 CI-only admin settings；
- `pnpm exec playwright install --with-deps chromium`，只安装/运行 Chromium；
- 运行现有 `pnpm web:test:e2e` 隔离编排器；
- 测试数据库继续使用精确 `gia_p05d_*` safety prefix，绝不使用 development database；
- 保持 one worker，不引入 Firefox/WebKit、视频、trace-on-every-run 或并行数据库共享；
- 成功与失败路径均验证 API/Web process 与临时数据库 cleanup。

### Cache decision

- 允许使用 setup-node 的 pnpm store cache 与 setup-uv 的 uv download cache，cache key 必须包含对应 lockfile；
- 不缓存 `node_modules`、`.venv`、数据库目录或 Playwright runtime state；首版不缓存 Chromium browser binary；
- frozen install、lock check 和测试必须在空 cache 上同样正确，cache miss/eviction 不得改变结果；
- 不引入单独 `actions/cache` 编排。若内置 cache 增加复杂度或权限风险，P0-6B 可先省略 cache，不得为了性能阻塞 CI baseline。

### Explicit CI non-goals

不设计 deployment、CD、release publishing、Docker registry publishing、production secrets、branch auto-merge、Dependabot/Renovate、artifact release、preview environment 或生产数据库操作。

## Logging contract

### Output and readability strategy

- 所有环境使用同一套 newline-delimited JSON schema；不维护 local text/prod JSON 两套 formatter。
- `DEBUG`/`INFO`/`WARNING` 输出 stdout，`ERROR`/`CRITICAL` 输出 stderr；两个 handler 必须用互斥 filter 避免重复。
- local human readability 通过终端/编辑器 JSON pretty view 或外部 pipe 获得，不改变应用 schema，也不为此增加项目 dependency。
- Uvicorn/FastAPI/SQLAlchemy logger 必须避免重复 handler；应用不打开 SQLAlchemy `echo`。

### Stable fields

每条记录都包含：

- `timestamp`：UTC RFC 3339，带 `Z`；
- `level`：uppercase severity；
- `event`：稳定的 lower snake/dot event name，例如 `http.request.completed`；
- `logger`：logger name。

HTTP request completion/error 记录按可用性增加：

- `request_id`：沿用现有 UUIDv4 request ID；
- `method`；
- `route`：仅 matched request 使用 FastAPI resolved route template，避免 path parameter 高基数；
- `route_classification`：固定枚举 `matched` / `unmatched`；unmatched/404 时 `route` omitted/null，绝不记录 raw path，也不通过 hash、truncation 或其他派生形式保留 path；
- `status_code`；
- `duration_ms`：非负 numeric milliseconds，固定精度；
- `exception_category`：仅安全、稳定的异常类别，不含 exception message；
- `trace_id` / `span_id`：仅在 active valid span 中输出 lowercase fixed-width hexadecimal IDs，不生成伪值。

`message` 可作为简短人类描述保留，但自动检索与测试以 `event` 为契约；不得把任意 exception、request 或 provider payload 填入 message。

### Event minimum

P0-6C 至少冻结并测试：

- `http.request.completed`；
- `http.request.failed`；
- `app.startup.completed`；
- `app.shutdown.completed`。

P0-6C 不预建 `telemetry.export.failed` 或其他未来空 event。该事件只在 P0-6D 的 exporter caller 实际存在时实现和测试；其他业务事件同样在真实 caller 出现后再增加。

### Exception policy

- 普通 structured log 只记录 `exception_category`，不序列化 exception message、traceback、locals、SQL 或 filesystem path；
- error envelope 继续只返回稳定 code/message/request_id，绝不返回日志或 tracing 细节；
- `KeyboardInterrupt`/`SystemExit` 等 process-control exceptions 不转成 HTTP 500；
- exporter failure 不影响 request response，也不递归触发无限 logging/export loop。

## Security and privacy logging rules

日志和 trace span 均默认禁止记录：

- request/response body；
- password、password hash、Cookie、Set-Cookie；
- raw session token、token digest、Authorization；
- database password、full database URL；
- arbitrary headers、query names/values；
- username、user_id 或其他 identity field（当前无故障定位 caller）；
- SQL text/parameters；
- model prompt、model response、candidate memory、评分规则或其他敏感模型 payload。

P0-6C/P0-6D 测试必须向 body/header/query/Cookie/exception/DB URL 注入 sentinel secret，并断言 stdout、stderr、exported spans 与 error response 均不包含 sentinel。不得只测试 happy-path field presence。

## OpenTelemetry boundary

### Signal decision

- `TRACING`：NOW；OpenTelemetry Python 当前 traces signal 为 stable。
- OTel `Logs` pipeline：DEFER；当前官方 Python status 仍为 development，应用继续使用 stdlib structured logs，只读取 active span IDs 做 correlation。
- `Metrics`：DEFER；虽然 SDK signal 已 stable，但 P0/V0.1 当前没有明确 consumer、SLO、dashboard 或 operations caller，不为名义完整性创建无消费方指标。

### Instrumentation decision

P0-6D 不直接采用 `opentelemetry-instrumentation-fastapi` 或 `opentelemetry-instrumentation-asgi`：

- contrib instrumentation 当前仍以 beta 版本发布；
- FastAPI instrumentor 内部已使用 ASGI instrumentation，因此无理由同时增加两项 direct dependency；
- 当前 ASGI request attribute collection 会处理 query string，而本项目禁止 arbitrary query values 进入遥测；
- P0 当前只有单个 FastAPI service，既有 request middleware 已拥有 method/route/status/duration/error lifecycle，受控手工 server span 的范围更小且可安全测试。

P0-6D 在既有 middleware 内使用 OTel API 创建 `SpanKind.SERVER` span：

- 从入站 headers 只复制 `traceparent` 构造最小 carrier，再通过标准 W3C Trace Context propagator 提取父上下文；不读取、接受或记录任意 `tracestate`/baggage；
- span name 最终使用 `METHOD route-template`，404 fallback 使用固定低基数名称；
- attributes 只允许 method、normalized route、status code、server address/service resource 等安全 low-cardinality values；不添加 query、header、body、Cookie、identity 或 SQL；
- 发生异常时只设置 error status 与安全 `exception_category`，不调用会附加 message/stack 的默认 exception recording；
- request completion log 从 active span context 读取 trace_id/span_id。

如果 P0-6D 开始时官方 FastAPI instrumentation 已提供经验证的 public configuration，可完全禁止 query/header/body 等敏感属性且版本不再 beta，可以提出小范围调整；未经证据不得静默改用自动 instrumentation。

### Provider and exporter

- provider-neutral：应用代码依赖 OTel API/SDK，不依赖 vendor resource、propagator 或 SDK；
- resource 通过 public `Resource(attributes=...)` 直接设置唯一 `service.name=group-interview-arena-api`（可由 typed config 覆盖），不调用 ambient resource detectors，不吸收 `OTEL_RESOURCE_ATTRIBUTES`/`OTEL_SERVICE_NAME`；
- production path 使用 OTLP over HTTP/protobuf `BatchSpanProcessor`，不使用 gRPC 双栈；
- default disabled 时不创建/export provider，不发网络请求；
- enabled 时配置校验要求 endpoint，并拒绝与 project enable authority 冲突的 active ambient SDK disablement 及 unsupported exporter authentication side channel；sampler 通过 public API 显式固定为 parent-based always-on，不接受 ambient sampler 覆盖；startup 不探测 collector；collector 不可达只产生受控 telemetry diagnostic，不阻断 startup/request；
- lifespan shutdown 先执行 5 秒 OTLP HTTP export/force-flush boundary，再调用采用 OTel 1.44 自身 bounded shutdown semantics 的 SDK BatchSpanProcessor shutdown；无论 export 成功与否都继续 dispose database engine；
- tests 注入 SDK in-memory exporter，不需要 collector/backend，也不写全局永久 provider 状态；每个 app instance 显式拥有并清理 provider。

### SQLAlchemy instrumentation

P0-6D 明确 DEFER `opentelemetry-instrumentation-sqlalchemy`：当前数据库调用只覆盖 identity boundary，自动 DB spans 的额外价值不足以抵消 SQL statement/database attributes 与 beta contrib dependency 的隐私、基数和生命周期风险。触发重新评估的条件是 P1 出现多步 discussion persistence、真实 DB latency diagnosis caller，并能通过无 SQL text/parameter 的安全测试。不得开启 sqlcommenter、statement parameter capture 或 SQLAlchemy echo。

## Configuration proposal

只在 API 现有 typed `Settings` boundary 增加三项：

- `otel_tracing_enabled: bool = False` → `GIA_API_OTEL_TRACING_ENABLED`；
- `otel_service_name: str = "group-interview-arena-api"` → `GIA_API_OTEL_SERVICE_NAME`；
- `otel_otlp_http_endpoint: AnyHttpUrl | None = None` → `GIA_API_OTEL_OTLP_HTTP_ENDPOINT`。

Validation rules：

- enabled 为 `true` 时 endpoint 必填；
- disabled 为默认安全状态，允许预置 endpoint 但不连接；
- service name 必须 trim 后非空并有合理长度上限；
- endpoint typed validation 只允许 scheme、host、port 与 path（例如 `/v1/traces`），并对 username/password userinfo、query、fragment fail closed；enabled/disabled 两种状态都执行同一结构校验；
- endpoint 的 repr/logging 同样不得输出 credential；P0-6 不增加 exporter auth header/token config；
- enabled path 对 OTel 1.44.0 会读取的 exporter headers、client key/certificate 与 trace credential-provider ambient variables 做 presence-only fail-closed validation，不读取或记录值；disabled path 不建立 exporter，因此不执行该 auth validation；
- sampler 通过 public API 固定为与 OTel 默认 intended semantics 等价的 parent-based always-on，不读取 ambient sampler 配置，也不增加 sampler、batch queue、resource attributes、metrics、logs 等未来 project config；
- 不把任何 observability config 加入 `NEXT_PUBLIC_*`、Web runtime config、OpenAPI 或 client bundle。

若未来生产 OTLP endpoint 需要 authentication header，必须在 deployment/operations 阶段通过 server-side secret boundary 单独设计；不得把 token 拼入 endpoint URL。

## NOW / DEFER scope freeze

### NOW in P0-6

- GitHub Actions CI；
- 现有 quality gates automation；
- structured logging hardening；
- request_id/trace correlation；
- provider-neutral basic OTel tracing；
- CI/logging/tracing documentation；
- observability safety and lifecycle tests。

### DEFER

- deployment/CD、production hosting、release publishing；
- alerting/on-call、dashboards、production log retention implementation；
- Grafana、Loki、ELK、Sentry、Datadog、CloudWatch-specific integration；
- Prometheus backend/server、OpenTelemetry Collector deployment、distributed tracing backend；
- Jaeger/Zipkin backend、vendor observability SDK；
- Redis、queue；
- product/user behavior analytics、AI telemetry、payment observability；
- OTel Logs pipeline、metrics signal、SQLAlchemy instrumentation。

## Dependency proposal

P0-6A dependency changes：`0`。不得修改 `pyproject.toml`、`uv.lock`、`package.json` 或 `pnpm-lock.yaml`。

2026-08-15 官方 release/PyPI preflight 仅作为候选证据，不是提前批准的 lock decision：

- `opentelemetry-api 1.44.0`；
- `opentelemetry-sdk 1.44.0`；
- `opentelemetry-exporter-otlp-proto-http 1.44.0`；
- `opentelemetry-instrumentation-fastapi 0.65b0` 已评估但按上述隐私/稳定性理由不进入 P0-6D direct dependency；
- `opentelemetry-instrumentation-asgi` 与 `opentelemetry-instrumentation-sqlalchemy` 不进入 P0-6D direct dependency。

P0-6D 修改 dependency 前必须重新：

1. 查询官方 current stable/core 与 contrib releases；
2. 验证每个候选的 CPython 3.14 classifier、requires-python 与实际 import；
3. 用 uv dry-run/tree 检查完整 dependency graph、core/contrib version pairing 与冲突；
4. 核对实际 TracerProvider、SpanProcessor、OTLPSpanExporter、propagator、force_flush/shutdown APIs；
5. 只加入应用直接 import/use 的最小 direct dependencies，再 frozen sync、lock check 和审查 lock diff。

上述 gate 已于 2026-08-16 完成。`uv pip install --dry-run --python .venv`、`uv tree`、CPython 3.14.7 import/signature checks、`uv sync --frozen` 与 `uv lock --check` 均通过；authoritative resolved direct versions 为 1.44.0。P0-6A 的 2026-08-15 candidate snapshot 继续保留为历史记录，不替代本次 live preflight。

## Risk-based test strategy

### P0-6A

- `git diff --check`；
- changed-file review；
- master-plan SHA-256 recheck；
- staged count `0`；
- 不运行 API/Web/PostgreSQL/Alembic/Chromium，因为没有 runtime/code change。

### P0-6B

- workflow YAML/action input review，full SHA/version/permissions/concurrency/service health review；
- 针对每个 job 在本地或等价环境运行现有命令，避免每次小 patch 重跑 Chromium；
- reviewed commit 通过已配置 trigger 完成一次 authoritative GitHub Actions run，四个 job 全部通过；
- OpenAPI drift generator 在无 database URL、无 PostgreSQL service、无 lifespan 的条件下通过；PostgreSQL integration/migration 与 Chromium E2E jobs 的真实数据库覆盖保持不变；
- 失败路径检查 process/database cleanup，确认 development DB 未使用；
- cache cold-run correctness 不依赖 cache hit。

### P0-6C

- logging unit tests：schema、event、stdout/stderr split、level、timestamp、matched route template、unmatched fixed classification、numeric duration、exception category、trace IDs absent/present；
- API integration：request_id 与 error envelope 保持一致，404/validation/handled/unhandled paths；
- unmatched/404 sentinel path 测试断言 raw path 及其 hash/truncated derivative 均未出现在日志，`route` omitted/null 且 classification 固定；
- sentinel leakage negative tests；
- targeted tests 通过后运行 API full gates，不运行无关 Chromium。

### P0-6D

- config validation/default-disabled tests；
- OTLP endpoint config tests：接受 scheme/host/port/path，拒绝 username/password userinfo、query、fragment；
- W3C parent context extraction、server span/status/route、request_id/trace correlation；
- 合法 `traceparent` 与敏感 `tracestate` 同时存在时仍继承 parent IDs，但 child `trace_state` 为空；ambient OTel resource env 不进入 exported resource；
- enabled + active `OTEL_SDK_DISABLED=true` 在构造 provider/exporter 前 fail closed；ambient `OTEL_TRACES_SAMPLER=always_off` 不改变 project-owned root sampling；
- enabled 时逐项拒绝 OTel 1.44.0 OTLP HTTP exporter 的 ambient headers、client key/certificate 与 trace credential-provider variables，错误不包含变量值且不创建 provider/exporter worker；disabled 时同组变量不导致失败；
- invalid trace context 不导致 request failure；
- in-memory exporter tests，无 external backend；
- unreachable OTLP endpoint 不阻断 startup/request；OTLP HTTP export timeout 为 5 秒，SDK BatchSpanProcessor shutdown 使用 OTel 1.44 自身 bounded shutdown semantics；
- 在项目真实可控的 flush/shutdown failure caller 实现并测试 `telemetry.export.failed`，只含安全 event/category 与 active correlation fields，不含 endpoint、credential、response body 或 exception message；BatchSpanProcessor 异步 export result 因无可靠 public callback 保留 SDK handling，不以 private API 或大型 wrapper 伪造捕获；
- sentinel query/header/body/Cookie/exception/DB URL 不进入 span/log/response；
- targeted tests 通过后运行 API integration/full gates。

### P0-6E

- API frozen sync、lock check、Ruff、format、Pyright、unit/full tests；
- real PostgreSQL migration/integration tests与 residue checks；
- Web frozen install、lint、format、typecheck、Vitest、production build、OpenAPI drift；
- Chromium-only cross-layer E2E；
- CI workflow permissions/action pins/concurrency/service/cold-cache acceptance；
- docs/status/hash/git diff acceptance。

P0-7 之后从 committed repository state 单独进行 independent P0 acceptance，不复用 P0-6E 结论替代独立检查。

## Exit criteria

### P0-6B exit

- PR 与 push-to-main triggers、read-only permissions、concurrency cancellation 已实现；
- API quality、PostgreSQL integration/migration、Web quality/OpenAPI drift、Chromium E2E 均为 required CI gates；
- OpenAPI drift 使用 DB/lifespan-independent generation path；Web quality job 不为此增加 PostgreSQL service，真实 PostgreSQL coverage 仍由 integration/migration 与 Chromium E2E jobs 承担；
- PostgreSQL 精确镜像、disposable DB 和 cleanup 可验证，未触碰 development DB；
- 所有 action 固定到已核对的 full SHA，frozen install/lock checks 生效；
- 无 deployment/CD/production secret 或未批准 automation。
- Exit evidence：commit `513491af128849f93c3ae601a906bd88fd8860f4` 的 push-to-main GitHub Actions run #1 conclusion `success`，四个 required jobs 均 completed / success。

### P0-6C exit

- JSON schema/event contract、matched route template/unmatched fixed classification、stdout/stderr split、request_id 与 safe exception category 已实现；
- existing error envelope 与 request_id behavior 无回归；
- sensitive sentinel negative tests 覆盖禁止字段与 attacker-controlled unmatched path 并通过；
- unmatched/404 不记录 raw/hashed/truncated path；无 vendor logger/backend、request body/header/query capture；
- P0-6C 未预建 `telemetry.export.failed`，该 event 归 P0-6D exporter caller 所有。

### P0-6D exit

- default-disabled provider-neutral tracing、typed config、traceparent-only W3C propagation 与 project-owned `service.name` 已实现；`tracestate`/baggage 和 ambient OTel resource attributes 均被隔离；OTLP endpoint 接受 scheme/host/port/path，并对 userinfo/query/fragment fail closed；enabled path 对 active ambient SDK disablement 与 unsupported exporter auth side channel fail closed，sampler 固定为 parent-based always-on；
- active trace_id/span_id 可与既有 request_id 日志关联；
- OTLP/HTTP exporter 不做 startup availability dependency，in-memory tests 不需要 backend；
- 项目可控 flush/shutdown caller 的 `telemetry.export.failed` 已实现并通过无 endpoint/credential/body/exception-message leakage tests；BatchSpanProcessor async exporter failure 的 public callback limitation 已记录；
- 5 秒 OTLP HTTP export/force-flush boundary、OTel 1.44 SDK BatchSpanProcessor bounded shutdown semantics 与 database dispose 均验证；
- 不含 OTel Logs、metrics、SQLAlchemy/FastAPI/ASGI auto-instrumentation 或 external backend；
- dependency/API/Python 3.14 review 与 lock diff 有证据。

### P0-6E exit

- P0-6B/C/D 的全部风险门禁通过；
- final API/Web/PostgreSQL/Chromium/CI configuration acceptance 有实际证据；
- docs、scope、security/privacy、default-safe behavior 与 residual risks 同步；
- P0-6A～P0-6D implementation reviews 与 P0-6E final cross-layer gates 均已完成；P0-6E 7-file docs-only actual-source review `PASS` 且无 blocker；P0-6 转为 `DONE`，P0-7 仍为 `NOT_STARTED`。
- Exit evidence：API unit 177 / integration 18 / full 195、Ruff、format、Pyright、Alembic single-head/current/drift、Web lint/format/typecheck/Vitest 16/build/DB-independent OpenAPI drift、Chromium 1 selected / 0 skipped、四-job CI scope audit与 residual cleanup 均 `PASS`。

### P0-6 overall exit

- 五个子步骤全部完成并通过各自 review；
- CI 自动复现已有 quality gates，失败可定位且不依赖 cache；
- structured logs 与 traces 可通过 request_id/trace_id/span_id 关联，且不泄露敏感数据；
- tracing 默认关闭、无 backend 可运行、collector unavailable 不影响应用可用性；
- NOW/DEFER 边界未扩大，无 production operations stack；
- master plan 未修改，没有未经批准的 Accepted ADR；
- Git staged count 为 0，用户明确接受 P0-6 closeout 后再进入独立 P0-7。

## Risks and open questions

- OTel core signal stable，但 contrib instrumentations 仍为 beta；实现已通过受控 manual server spans 避免把 beta auto-instrumentation 与 query capture 带入 P0，2026-08-16 official API/version recheck 已通过。
- OTel global provider 通常只能设置一次，容易污染 pytest process；实现使用 app-owned/non-global provider/exporter，并已验证重复 app teardown 与 processor thread cleanup。
- resolved route template 只在 routing 后可用；logging/tracing middleware 必须在 response/exception path 上统一 finalize，404 只使用 fixed unmatched classification 并 omit/null route，不保留任何 raw/derived path。
- OTLP/HTTP 无 auth 配置只适用于受控 endpoint；生产 authenticated exporter 属于后续 deployment/operations decision，当前不得把 credential 放入 URL。
- Chromium CI 会增加运行时间，但其 Cookie/CSRF 安全覆盖不可由 unit test 替代，因此保留为 gate；首版通过 one worker、Chromium-only 控制成本。
- GitHub action pins、hosted runner image 与 OTel releases 会变化；B/D 开始时重新核对，不把 2026-08-15 的查询结果当作永久最新值。
- P0-6D actual-source review 与 findings re-review 已通过，无 remaining blocker；P0-6E final validation 与 7-file docs-only actual-source review 均已通过，未发现新的 correctness/security/privacy blocker。

## Official references reviewed

- GitHub Actions：[workflow concurrency](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/control-workflow-concurrency)、[PostgreSQL service containers](https://docs.github.com/en/actions/tutorials/use-containerized-services/create-postgresql-service-containers)
- P0-6A action snapshot：[checkout v7.0.1](https://github.com/actions/checkout/releases/tag/v7.0.1)、[setup-node v7.0.0](https://github.com/actions/setup-node/releases/tag/v7.0.0)、[setup-python v6.2.0](https://github.com/actions/setup-python/releases/tag/v6.2.0)、[pnpm/action-setup v6.0.9](https://github.com/pnpm/action-setup/releases/tag/v6.0.9)、[setup-uv v9.0.0](https://github.com/astral-sh/setup-uv/releases/tag/v9.0.0)
- P0-6B live action preflight：[checkout v7.0.1](https://github.com/actions/checkout/releases/tag/v7.0.1)、[setup-node v7.0.0](https://github.com/actions/setup-node/releases/tag/v7.0.0)、[setup-python v7.0.0](https://github.com/actions/setup-python/releases/tag/v7.0.0)、[pnpm/setup v2.0.2](https://github.com/pnpm/setup/releases/tag/v2.0.2)、[setup-uv v10.0.1](https://github.com/astral-sh/setup-uv/releases/tag/v10.0.1)
- OpenTelemetry Python：[signal status](https://opentelemetry.io/docs/languages/python/)、[instrumentation](https://opentelemetry.io/docs/languages/python/instrumentation/)、[propagation](https://opentelemetry.io/docs/languages/python/propagation/)、[resources](https://opentelemetry.io/docs/concepts/resources/)、[OTLP exporters](https://opentelemetry.io/docs/languages/python/exporters/)
- P0-6D live dependency/API preflight：[OpenTelemetry Python releases](https://github.com/open-telemetry/opentelemetry-python/releases)、[API 1.44.0](https://pypi.org/project/opentelemetry-api/)、[SDK 1.44.0](https://pypi.org/project/opentelemetry-sdk/)、[OTLP HTTP exporter 1.44.0](https://pypi.org/project/opentelemetry-exporter-otlp-proto-http/)、[trace SDK API](https://opentelemetry-python.readthedocs.io/en/latest/sdk/trace.html)、[trace API](https://opentelemetry-python.readthedocs.io/en/stable/api/trace.html)
- OpenTelemetry contrib：[FastAPI instrumentation](https://opentelemetry-python-contrib.readthedocs.io/en/latest/instrumentation/fastapi/fastapi.html)、[ASGI request attribute source](https://opentelemetry-python-contrib.readthedocs.io/en/latest/_modules/opentelemetry/instrumentation/asgi.html)

## Progress

- Completed：P0-6A baseline gate、scope freeze、execution plan 与 actual-source final review `PASS`；P0-6B workflow implementation、live action preflight、local parity、cleanup validation、actual-source review、findings remediation 与 remote GitHub Actions run #1 `PASS`；P0-6C structured JSON logging implementation、security regression coverage、actual-source review、`JsonFormatter` safe fallback remediation/re-review 与 remote GitHub Actions run #4 `PASS`；P0-6D OpenTelemetry 1.44 tracing foundation、local gates、actual-source review、tracestate/Resource 与 ambient SDK/exporter config remediation/re-review、remote GitHub Actions run #6 `PASS`；P0-6E final API/Web/PostgreSQL/Chromium/CI、security/privacy、cleanup、closeout gates 与 7-file docs-only actual-source review `PASS`；P0-6 `DONE`；
- Current gate：none；
- Not started：P0-7；
- Next：等待用户后续明确批准独立 P0-7；不得自行进入 P0-7。
