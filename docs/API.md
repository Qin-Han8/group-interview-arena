# API 与事件技术基线

- Status: P0 API Architecture Baseline
- Current phase: P0
- API architecture baseline established by: P0-2 — DONE
- Target version: V0.1 Internal Validation
- Implemented contracts: `GET /health`, `POST /auth/register`, `POST /auth/login`, `POST /auth/logout`, `GET /auth/me`
- P0-5 browser CORS/CSRF/Web closure: P0-5D completed
- Detailed P1 WebSocket schema: Not started
- Authority: 低于 [`PROJECT_MASTER_PLAN.md`](PROJECT_MASTER_PLAN.md) 和已确认的 [`DECISIONS.md`](DECISIONS.md)

## 文档目的

本文件记录 P0-2 已批准的 REST、WebSocket、契约生成、恢复和错误语义基线，并同步 P0-3D/P0-3E、P0-5C 与 P0-5D 已实现的 REST/browser 技术契约。本文件不冻结完整 P1 事件集合；P0-5E final outcome 为 `PASS after findings remediation and independent recheck`，P0-5 已转为 `DONE`。

正式决策见 [`DECISIONS.md`](DECISIONS.md) `ADR-006`、`ADR-007`、`ADR-013`、`ADR-015`。

## Accepted protocol split

### REST

REST 用于：

- resource CRUD；
- question fetch；
- session create；
- session snapshot/load；
- reports；
- settings；
- future admin/orders。

总纲中的 endpoint 只是跨版本示例。P0-3 只建立获批的最小健康/基础 API；V0.1、V0.5 的业务接口必须在对应任务进入范围后才设计和实现。

### P0-3D implemented REST contract

`GET /health`

- 成功状态：`200`；
- response body：`{"status":"ok"}`；
- response header：`X-Request-ID`，值为服务端为每个请求生成的 UUIDv4；
- response model：`HealthResponse`。

当前不实现 `/ready`，因为 P0-3D 没有数据库或其他依赖型 readiness 检查。

### WebSocket

WebSocket 用于活动会话中的：

- client commands；
- state changes；
- participant events；
- timer；
- floor control；
- interruption；
- AI streamed text；
- future speech-related session events。

SSE 不作为活动 session 主协议。未来如果存在单向长任务进度等真实需求，可以单独评估，但不能因此建立第二套活动会话协议。

## WebSocket implementation timing

P1 的第一个文字讨论 vertical slice 建立 WebSocket session channel。不得先用 HTTP 完成整套文字讨论，再到 P2 重写 realtime。

P0-3 不实现 WebSocket 业务代码。P1 实施时遵守：

- server authoritative session state；
- client commands use action identity；
- session events are ordered；
- reconnect uses snapshot + sequence；
- state recovery is based on server truth。

## REST contract authority

- FastAPI OpenAPI 是 REST contract 的 Source of Truth；
- Frontend 从 OpenAPI 生成 TypeScript types/client；
- 不允许前后端手写两套同名 DTO；
- P0-3E 的 scoped implementation 使用 `openapi-typescript` 生成 TypeScript contract，并使用 `openapi-fetch` 建立 typed client；
- generator 选择不得改变 OpenAPI-as-source-of-truth 的 Accepted decision。

P0-3E 的实际流程为：FastAPI `/openapi.json` → `openapi-typescript` → `apps/web/src/lib/api/generated/schema.d.ts` → `openapi-fetch` typed client。生成文件不得手改；API 运行时使用 `web:api:generate` 更新，使用 `web:api:check` 检查漂移。

## P0-3E local CORS semantics

- CORS allowlist 由 `GIA_API_CORS_ORIGINS` 以 JSON array 显式配置；缺省为空；
- 本地示例只允许 `http://localhost:3000`，不使用 wildcard 或任意 localhost port；
- 当前 `allow_credentials=false`、允许方法仅 `GET`、不预先放宽 request headers；
- response 暴露 `X-Request-ID`；未批准 origin 不获得 `Access-Control-Allow-Origin`；
- `NEXT_PUBLIC_API_BASE_URL` 是浏览器可见的公开 base URL，不是 secret；当前 Web 从浏览器直接请求 FastAPI，不经过 Next.js proxy。

以上是 P0-3E 当时的历史行为。P0-5D 已在继续保持 explicit origin allowlist 与 wildcard rejection 的前提下，将当前 CORS contract 更新为 `allow_credentials=true`、methods 精确为 `GET`/`POST`、request headers 精确为 `Content-Type`/`X-GIA-CSRF`，并继续只 expose `X-Request-ID`。

## P0-5C implemented REST identity contract

P0-5C 已实现以下最小 contract：

- `POST /auth/register`：接收 username/password；成功时原子创建 user 与 authenticated server session，返回 `201`；canonical username conflict 返回 `409`；
- `POST /auth/login`：成功时始终生成新 opaque session并返回 `200`；unknown username 与 wrong password 使用完全相同的 generic `401`；
- `POST /auth/logout`：幂等返回 `204`，只删除当前 Cookie 对应的 exact server session，并清除 Cookie；
- `GET /auth/me`：只返回 authenticated user 的 `id` 与 `username`；未认证返回 `401`。

Password、password hash 与 raw session token 永不进入 JSON response。P0-5C 在既有 error envelope 下新增 `INVALID_USERNAME`、`INVALID_PASSWORD`、`USERNAME_UNAVAILABLE`、`INVALID_CREDENTIALS` 与 `AUTHENTICATION_REQUIRED` scoped codes；request validation 不回显输入 credential。

Cookie session 在 OpenAPI 中使用名为 `SessionCookie` 的 `apiKey`/Cookie security scheme，不引入 JWT bearer scheme。FastAPI OpenAPI 继续是 REST contract Source of Truth；P0-5C 已重新生成并验证 Web TypeScript derivative，未添加手写平行 auth DTO。

## P0-5 browser security boundary — P0-5D implemented

- Raw session token 只存在于 host-only HttpOnly Cookie；database 只保存 digest；
- local development baseline：`Secure=false`、`SameSite=Lax`、`Path=/`、省略 Domain；
- production HTTPS baseline：`Secure=true`，typed configuration 在 production + `Secure=false` 时 fail closed，其他 host-only/HttpOnly/SameSite/Path 约束不降低；
- P0-5C scoped Cookie name 为 `gia_session`；
- P0-5 implementation-scoped default 为 7-day absolute expiry，无 sliding refresh、无 refresh token。

P0-5D 已让所有 browser state-changing auth POST（`POST /auth/register`、`POST /auth/login`、`POST /auth/logout`）统一要求单一 exact `Origin` 与单一 `X-GIA-CSRF: 1`；Origin 必须存在于与 CORS 共用的 `GIA_API_CORS_ORIGINS` normalized trusted-origin set。缺失、`null`、不受信任、重复或错误值统一返回现有 error envelope 下的 `403 CSRF_REJECTED`。`GET /auth/me` 不要求 CSRF header。没有新增 `GIA_API_CSRF_TRUSTED_ORIGINS`；SameSite=Lax 继续只作为 defense-in-depth。Web 保留 raw ASCII username 并由 backend 返回 canonical lowercase username；真实 Chromium 已验证该 canonical restore、Cookie flags、reload restore、missing-header rejection、logout invalidation 与 Cookie 清除。

## Versioned WebSocket contract

WebSocket 使用独立版本化 event contract。原则至少包含：

- event type；
- schema version；
- session identity；
- ordering sequence；
- occurrence timestamp；
- client action identity，用于命令与结果关联。

时间戳使用 ISO 8601；UTC 输出使用 `Z`。事件顺序依赖 session 内 monotonic sequence，不依赖 UUID 顺序。

具体字段、JSON Schema、generator package、投递与重放细节在 P1 API design 中冻结。本文件不把总纲事件示例伪装成已经完成的正式 Schema。

## Snapshot and reconnect principle

- 服务端状态是权威来源；
- 客户端不能仅凭本地事件推断正式 session state；
- snapshot/load 使用 REST；
- WebSocket 承载 snapshot 之后的有序增量；
- client action identity 用于识别重试或重复命令；
- sequence 缺口、幂等窗口、保留期和重放范围由 P1 结合持久化设计确定。

## Unified error semantics

REST error model 至少表达：

- standard HTTP status；
- stable machine-readable error code；
- safe user-facing message；
- request correlation；
- optional safe details。

WebSocket 使用语义一致的 error event，并在实际 Schema 中增加必要的 session/action 上下文。

禁止在 API 或实时错误中暴露：

- stack trace；
- SQL；
- filesystem paths；
- secret；
- prompt；
- provider credentials。

具体 error field schema 按 P0-3/P1 实际接口逐步冻结，不以框架默认错误载荷作为未经决策的长期契约。

P0-3D 已实现的最小错误 envelope 为：

```json
{
  "error": {
    "code": "NOT_FOUND",
    "message": "Resource not found.",
    "request_id": "00000000-0000-4000-8000-000000000000"
  }
}
```

当前基础 code 仅为 `NOT_FOUND`、`VALIDATION_ERROR` 和 `INTERNAL_ERROR`。404、FastAPI request validation 与 unexpected exception 均映射为安全 envelope；unexpected exception 只产生带固定安全 category 的 `http.request.failed` application event，客户端不接收 stack trace、source path 或原始异常消息。

P0-6C application request logs 为单行 JSON。每条记录有 UTC `timestamp`、uppercase `level`、稳定 `event` 和 `logger`；请求记录按适用性包含与 `X-Request-ID`/error envelope 一致的 `request_id`、`method`、FastAPI resolved route template、固定 `route_classification`、`status_code` 与 monotonic `duration_ms`。matched request 只记录 route template；unmatched/404 omit `route` 并使用 `unmatched`，不保留 raw/hashed/truncated path。合法 HTTP response（包括 handled 4xx）记录 `http.request.completed`；真正未完成 pipeline 的异常记录 `http.request.failed`。不记录 request/response body、arbitrary headers、Cookie/Set-Cookie、Authorization、query、raw session token、credential URL 或 exception message/traceback。

## Security and authority boundaries

- FastAPI 是领域、会话状态和持久化的业务权威；
- Next.js server-side 能力不得复制领域规则、状态机、评分、Agent 编排或持久化权威；
- 服务端密钥不得进入浏览器；
- P0/V0.1 initial username/password 与 opaque Cookie session boundary 已由 `ADR-015` 批准；P0-5B 已实现 persistence/security primitives，P0-5C 已实现 backend Cookie/auth HTTP runtime，P0-5D 已实现 credentialed CORS/CSRF/Web browser closure；
- production 环境不得误启不安全的开发身份；
- structured output 和关键事件 payload 在对应实现阶段使用 Schema validation；
- prompt、角色私有信息和评分规则不得因 API 错误或日志泄露。

## Phase boundaries

### P0-3

- 最小健康/基础 API；
- Web → API connectivity；
- OpenAPI contract authority 落地；
- 基础 config、request correlation、structured logging 和 error semantics；
- 不实现 session WebSocket、Provider、数据库或业务端点。

P0-3D 已完成最小 API、OpenAPI authority、typed config、request correlation、structured logging 和 error semantics。P0-3E 已完成 CORS allowlist、generated TypeScript contract、typed client、自动化跨应用 HTTP/CORS 验证与真实浏览器手工验收。WebSocket 仍留在 P1。

### P1

- 细化文字会话 REST 端点；
- 冻结第一个版本化 WebSocket 事件契约；
- 实现 action identity、sequence、snapshot/reconnect；
- 添加 WebSocket tests 和 deterministic session regression。

### P2 and later

- P2 才细化音频、ASR、TTS、打断和恢复事件；
- P4 才细化订单、支付、权益和故障返还契约；
- 不得因长期端点出现在总纲示例中而提前实现。

## TBD

- TBD：WebSocket schema generator package；
- TBD：P1 最小 REST endpoint 和 WebSocket event 集合；
- TBD：事件投递、重放、幂等窗口和兼容策略；
- TBD：V0.1 之后的 identity expansion、verified recovery flow 与 authorization；
- TBD：音频上传和短期签名协议；
- TBD：支付 Provider 和 webhook 契约；
- TBD：公开 API 是否存在及其时间点。

## 与其他文档关系

- 正式决策：[`DECISIONS.md`](DECISIONS.md)
- 系统模块：[`ARCHITECTURE.md`](ARCHITECTURE.md)
- 会话状态：[`AGENT_BEHAVIOR.md`](AGENT_BEHAVIOR.md)
- 数据模型：[`DATABASE.md`](DATABASE.md)
- 安全要求：[`PRIVACY_AND_SAFETY.md`](PRIVACY_AND_SAFETY.md)
