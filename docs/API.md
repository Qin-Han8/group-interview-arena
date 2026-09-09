# API 与事件技术基线

- Status: P0 API Architecture Baseline + P1-1～P1-5 completed + P1-6A～P1-6D implemented and independently reviewed; P1-6E `IN_PROGRESS`
- Current phase: P1 — IN_PROGRESS
- API architecture baseline established by: P0-2 — DONE
- Target version: V0.1 Internal Validation
- Implemented REST contracts: `GET /health`, `POST /auth/register`, `POST /auth/login`, `POST /auth/logout`, `GET /auth/me`, `GET /questions`, `GET /questions/{question_version_id}`, `POST /sessions`, `GET /sessions/{session_id}`, `GET /sessions/{session_id}/utterances`, `POST /sessions/{session_id}/start`
- Implemented realtime contract: `/ws/sessions/{session_id}?after_sequence=` scoped session channel with historical v1 and current v2 formal events
- P0-5 browser CORS/CSRF/Web closure: P0-5D completed
- P1-1 contract: scoped/frozen by P1-1A; P1-1B persistence, P1-1C REST/WebSocket runtime, P1-1D Web realtime caller and P1-1E independent final review completed
- P1-2 contract: P1-2A/B/C completed; safe question reads and immutable version-bound session creation implemented
- P1-3 contract: P1-3A～D completed; independent verdict `PASS`; P1-3 `DONE`
- P1-4 contract: P1-4A～E completed; final independent verdict `PASS`; deterministic scheduler remains server-owned and safe floor snapshot/WS/Web projection is implemented
- P1-5 contract: P1-5A～P1-5R and its post-closeout remediation are `DONE`; runtime、transport、Web and recovery contracts remain accepted
- P1-6 contract: structured public Discussion Memory and bounded Working Context are internal application/persistence concerns; P1-6 adds no REST/OpenAPI/public-event/public-WS contract
- Authority: 低于 [`PROJECT_MASTER_PLAN.md`](PROJECT_MASTER_PLAN.md) 和已确认的 [`DECISIONS.md`](DECISIONS.md)

## 文档目的

本文件记录 P0-2 已批准的 REST、WebSocket、契约生成、恢复和错误语义基线，同步 P0/P1-1 与 P1-2C 已实现的 REST/browser/session 技术契约。P1-1/P1-2 scoped contracts 不等于完整 P1/P2 事件集合。

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

P1-1A 已冻结第一个 scoped v1 contract；generator package、完整 P1/P2 事件集合和大规模投递/保留仍未冻结。本文件不把总纲事件示例伪装成已经完成的完整 Schema。

## Snapshot and reconnect principle

- 服务端状态是权威来源；
- 客户端不能仅凭本地事件推断正式 session state；
- snapshot/load 使用 REST；
- WebSocket 承载 snapshot 之后的有序增量；
- client action identity 用于识别重试或重复命令；
- P1-1 scoped sequence gap、幂等和 reconnect 语义见下节；P1-1 之后的长期保留、compaction 和 compatibility 仍随真实持久化需求确定。

## P1-1 scoped REST/WS contract — P1-1C backend and P1-1D Web caller implemented

完整字段、schema、transaction 和 B～E acceptance 见 [`exec-plans/P1-1_discussion-session-foundation.md`](exec-plans/P1-1_discussion-session-foundation.md)。以下 backend contract 已由 P1-1C 实现，P1-1D 已增加最小 authenticated Web realtime caller。

### REST v1 scope

- `POST /sessions`：authenticated + existing exact Origin / `X-GIA-CSRF: 1`；无 body；原子创建 `CREATED` session 和 sequence `1` 的 `session.created` event；返回 `201 SessionSnapshotResponse`。
- `GET /sessions/{session_id}`：authenticated owner-only snapshot；missing/non-owner 均返回 `404 SESSION_NOT_FOUND`；read-only，不要求 CSRF header。
- P1-1 初始 snapshot fields 为 `id`、`status`、`created_at`、`updated_at`、`last_sequence`；后续获批的 question、phase timing 与 safe floor additive projection 分别见下文。Owner credential、Cookie/token、utterance 和 event backlog 始终不进入 response。
- FastAPI OpenAPI 继续是 REST Source of Truth；Web derivative 已由 P1-1C 重新生成并通过 drift check。

### WebSocket v1 scope

- Endpoint：`/ws/sessions/{session_id}?after_sequence=<non-negative integer>`。
- Handshake 复用现有 opaque `gia_session` Cookie、current-user service 和 owner authorization；browser Origin 必须是 existing `Settings.cors_origins` 中的单一 exact value。WebSocket 不增加 query token、JWT、custom origin env 或浏览器不可发送的 CSRF header。
- 唯一 client business command：`session.abort`，fields 为 `schema_version=1`、`type`、`session_id`、stable UUIDv4 `action_id`、empty `payload`。
- Formal events：creation 的 `session.created` 与 abort 的 `session.state_changed`；fields 为 `schema_version`、`type`、`session_id`、`sequence`、UTC `occurred_at`、nullable `action_id`、`payload`。
- Action scope 为 `(session_id, action_id)`；同 semantic action 重试重发已持久化 events，不新增 sequence；同 id 不同 semantic payload 返回 `ACTION_ID_CONFLICT`。
- Formal event sequence 来自 locked session row 上的 durable counter；一个 action 可以关联多 events，不使用 `MAX()+1` 或 memory-only idempotency。

### WS safe error scope

- Error message fields 为 `schema_version=1`、`type="error"`、session/action context、UTC `occurred_at` 和与 REST 对齐的 `error.code` / safe `error.message` / `error.request_id`。
- WS errors 不持久化、不消耗 sequence。Recoverable domain errors keep connection open；protocol error 使用 safe `PROTOCOL_ERROR` 后 close `1008`；internal failure 使用 safe `INTERNAL_ERROR` 后 close `1011` when possible。
- Error/log/span 不暴露 payload、Cookie/token、Origin、raw path/query、SQL、traceback、filesystem path、prompt/provider information 或 raw exception。

### P1-1 reconnect scope

- Browser 先 GET snapshot，再以 `after_sequence=last_sequence` 建立 WS；server 在处理 commands 前按 sequence 发送 persisted catch-up events。
- Client 只应用精确 next sequence；`<= last_sequence` 是 replay 并忽略；`> last_sequence + 1` 是 gap，必须停止应用、重新 GET authoritative snapshot、再连接。
- `after_sequence` ahead of server watermark 返回 safe `SEQUENCE_AHEAD` 并触发同一 REST reload path。
- P1-1 event history 随 session 保留；retention/compaction、large backlog pagination、multi-tab fan-out、cross-process broadcast 和 multi-worker routing Deferred。

Backend Pydantic v2 models 是 WS v1 contract authority；P1-1D 的 TypeScript discriminated union 是由 canonical fixtures/cross-layer tests 验证的 derivative。WebSocket generator package 继续 Deferred，WS contract 不进入 REST OpenAPI。

### P1-1D Web caller behavior

- Browser 从 authoritative REST snapshot 启动连接，只应用精确 next sequence；`sequence <= last_sequence` 不重复应用，但 matching `action_id` replay 可确认 pending action。
- Pending command/action identity 只在当前内存生命周期保存；reconnect 重发相同 `action_id`。Browser 不在 local/session storage 保存 Cookie/token、action queue、payload 或 authoritative session state。
- gap 立即停止增量应用、关闭旧 socket、重新获取 REST snapshot，再以新 `last_sequence` watermark 连接；stale connection generation 和 React cleanup 不能更新当前 projection。
- P1-1D caller 同时只拥有一个 live socket，自动 reconnect 有界；URL 只携带非秘密 `session_id` 以支持 reload 后重新获取 server truth。
- 真实 Next/Chromium → Uvicorn WebSocket → PostgreSQL E2E 已验证 opaque Cookie、trusted Origin、created/abort ordered events、相同 action replay、REST reload restore、单一 durable action 与完整临时资源清理。

## P1-2 safe question/session contract — P1-2C implemented

P1-2C 已按 P1-2A 冻结 contract 实现以下边界；FastAPI OpenAPI 与 generated Web derivative 已同步，既有 P1-1 WebSocket vocabulary 未改变。

### `GET /questions`

- Requires authenticated opaque Cookie；read-only，无 CSRF header。
- 返回 selectable `published_at != null && retired_at == null` Question Version summaries；不返回 draft 或 retired versions。
- Summary allowlist：`id`、`question_template_id`、`version_number`、`title`、`question_type`、`background_domain`、`difficulty`、`estimated_minutes`。
- P1-2C 不增加 filter/pagination/admin mutation；内部 validation fixture 数量很小，未来真实 list scale 出现后再扩展。

### `GET /questions/{question_version_id}`

- Requires authenticated opaque Cookie；read-only，无 CSRF header。
- Published version 可按 immutable ID 获取 safe public content，即使它之后 retired，以支持历史 session；draft/missing 返回统一 safe not-found。
- Public detail 在 summary fields 外只允许：`scenario`、`objective`、hard/soft constraints、stakeholders、options。
- Persona assignments/parameters/Private Stance、reference dimensions、hidden conflicts、acceptable outcome patterns、phase prompts、internal safety/calibration/scoring/provider data 不进入 response schema。

### Version-bound `POST /sessions`

- Create contract 已改为 closed request `{ "question_version_id": "<uuidv4>" }`；继续 requires authenticated Cookie、exact trusted Origin 和 `X-GIA-CSRF: 1`。
- Server 在 creation transaction 内验证 version exists、published、non-retired and assignment-complete；只接受 immutable version identity，不接受 template ID、title、code 或 `latest` alias。
- Success 仍为 `201 SessionSnapshotResponse`、`CREATED` 和 sequence `1` `session.created`；snapshot additive 增加 nullable `question_version_id` 以真实表示 P1-1 legacy rows，新 API-created rows 必须 non-null。
- Invalid/unselectable version 使用 safe stable error/non-disclosing not-found semantics；不返回内部 publication failure detail。
- 新版本发布或 retirement 后，existing snapshot 的 version ID 和 historical safe content 均不变。

### Minimal Web caller and non-disclosure

- Web 只使用 FastAPI OpenAPI generated client 获取 safe list/detail、提交 exact version ID、显示 public content，并继续使用 existing realtime client 投影 session state。
- Next.js 不决定 publication/selectability，不解析 private fields，也不缓存 authoritative question/session state 到 local/session storage。
- P1-2 不增加 Persona API、Private Stance API、question mutation/admin route 或 WebSocket command/event type。
- Negative contract/browser/log/trace/error tests 必须使用 attacker-controlled sentinel 证明所有 private/internal fields 都不跨 transport。

完整 scope、dependencies、caller、acceptance 和 testing 见 [`exec-plans/P1-2_question-persona-foundation.md`](exec-plans/P1-2_question-persona-foundation.md)。

## P1-3 state/timing contract — completed and independently accepted

P1-3A 冻结以下 additive contract；P1-3B 已实现 backend/domain/persistence/API/realtime-parser foundation；P1-3C 已实现 in-process deadline recovery、connected WebSocket catch-up/push、Browser start/current-phase/deadline projection 和真实 PostgreSQL Chromium complete-flow validation；P1-3D 已从 clean committed source 独立复核并给出 `PASS`。

### User command vocabulary

- Existing `session.abort` v1 remains an empty-payload client command，but P1-3 expands its legal sources to `CREATED` and every active timed phase。
- New `session.start` v1 is an empty-payload client command legal only in `CREATED`。
- Both use stable client UUIDv4 `action_id` and existing durable retry/conflict semantics。
- Browser cannot send `next_status`、phase duration、deadline、clock、transition reason or a timeout/advance command。
- `POST /sessions/{session_id}/start` is the current REST caller for user start intent；request body is exactly `{ "action_id": "<uuidv4>" }` and server-owned configuration supplies the frozen duration plan。

### System transition and event compatibility

- Deadline advance is internal and server-owned；it validates exact current status/deadline under the aggregate row lock and carries null `action_id`。
- Formal event types remain `session.created` and `session.state_changed` only；no persisted tick event。
- Stored `session.state_changed` v1 abort events remain readable。P1-3 emits `session.state_changed` event version 2 with closed `previous_status`、`status`、`trigger`、nullable `phase_started_at` and nullable `phase_deadline_at`。
- `trigger` is exactly `USER_START`、`USER_ABORT` or `PHASE_DEADLINE`。User events carry the action ID；system deadline events carry null。
- All state/timing/watermark/events commit before any WebSocket send；send failure is recovered through existing ordered catch-up。
- App startup, WS connect and the connected catch-up loop call the same server-side overdue reconciliation foundation；duplicate recovery callbacks are idempotent because P1-3B exact status/deadline preconditions and aggregate row lock remain the mutation authority。

### Authoritative snapshot projection

P1-3B additively extends `SessionSnapshotResponse` with nullable `phase_started_at` / `phase_deadline_at` and response-time `server_now`。Status expands to the exact V0.1 implemented path plus `ABORTED_USER`。The server-only frozen duration plan is never returned。

P1-3C Browser renders a local display countdown from authoritative UTC values but cannot transition at zero；snapshot or a v2 event replaces the complete local phase/timing projection。Gap、sequence-ahead、reload and reconnect continue to recover through REST snapshot + ordered formal events。

The exact state matrix、deadline arithmetic、historical version compatibility and P1-3B～D gates are in [`exec-plans/P1-3_session-state-machine.md`](exec-plans/P1-3_session-state-machine.md)。

## P1-4 floor-control contract — deterministic scheduler + safe Realtime/Web projection implemented

P1-4A froze the boundary below. P1-4B implements internal typed commands, strict server formal-event envelopes and durable records；P1-4C adds internal deterministic `floor.schedule` orchestration；P1-4D additively projects the resulting facts through the existing owner-only REST snapshot and single ordered WebSocket channel. No public floor command or Browser scheduler authority was added.

### Authority and command boundary

- P1-3 phase/status/deadline remains authoritative. Floor commands can express participant intent or release/interruption intent only；Browser cannot select the winning speaker, provide a rank/reason/fairness value, set current owner or modify phase/timing.
- The internal P1-4B command vocabulary retains stable UUIDv4 `action_id`, owner authorization, exact closed typed payloads and existing durable retry/conflict semantics. It is not a public network contract；P1-4D must document the exact client commands before exposing any.
- Scheduler evaluation and silence/deadline intervention are implemented server-owned operations. Internal `floor.schedule` carries stable action/decision/fact identity, exact phase/sequence/current-grant preconditions, injected UTC and closed policy；it is not a Browser contract and does not depend on prompt/LLM output.

### Minimum formal event vocabulary

The strict server event envelope now accepts exactly three P1-4 formal fact types at version 1:

- `floor.granted`：a participant acquired a specific grant in the authoritative current phase；
- `floor.released`：that exact current grant ended for a closed safe reason；
- `floor.intervention_requested`：the deterministic scheduler requested a typed moderator/system intervention。

An event states what happened. Its causal scheduler decision separately retains safe policy version/reason/audit metadata. A future utterance or LLM output occurs after grant and is not embedded in these floor events.

Their closed payloads expose only identities needed for future recovery/projection (`participant_id`、`grant_id`、phase、opportunity/decision reference where needed), safe reason code、policy version where causal explanation requires it, and the existing ordered event envelope. They do not expose Private Stance、persona parameters/calibration、prompt、provider score/output、candidate ranking vector、internal weights or scoring data.

Hand raises/opportunities、candidate lists、fairness calculations、timer ticks and provider thinking states are not automatically formal events. Adding any event beyond the three above requires a demonstrated recovery/client caller and a prior plan update.

### Snapshot and recovery boundary

- `SessionSnapshotResponse.floor` exposes only a safe participant directory (`participant_id`、`actor_kind`、`seat_order`), nullable current grant and latest lifecycle fact with phase/public reason/timestamp/sequence. It excludes decision metadata、policy weights/ranking、Private Stance/persona、prompt/provider and scoring fields.
- Browser projects server truth only. It cannot infer ownership from a local queue, local countdown, audio playback or generated text.
- Replacement is ordered release then grant in one locked transaction；duplicate/stale/concurrent operations must preserve zero-or-one current owner and contiguous event sequence；all durable mutation commits before send.
- Phase change/abort/completion invalidates stale floor evaluation and releases any old current grant without allowing floor cleanup to delay or alter the P1-3 transition.
- Web strictly parses the three existing v1 floor event payloads and reduces only their safe public fields. It reuses exact-next sequence application、duplicate suppression、gap/sequence-ahead REST reload、bounded reconnect and stale socket generation rejection；no second realtime channel or protocol exists.
- Web displays current owner、public granted/released/intervention status and safe reason text. It sends no grant/release/scheduler command, and LLM/utterance content remains outside this contract.

Internal grant/release/intervention/schedule commands use the existing session action/digest/aggregate-lock/sequence transaction boundary. Scheduler input is reconstructed only after locking；duplicate action IDs replay the same causal events, a changed digest conflicts, and stale sequence/phase/current grant、ineligible participant or terminal session rejects without floor mutation. Exact domain/persistence, reason metadata and P1-4D～E gates are in [`exec-plans/P1-4_floor-control.md`](exec-plans/P1-4_floor-control.md)。

## P1-5A～P1-5E-3 generation/utterance boundary — implementation remains internal

P1-5A froze the rules below。P1-5B implements internal persistence/domain commands；P1-5C adds an internal application caller and deterministic local harness；P1-5D adds a Python-internal project-owned provider Protocol and thin Zhipu HTTP adapter。None adds a REST endpoint、WebSocket command/event、OpenAPI field or Browser projection:

- `floor.granted` is the authoritative trigger/precondition for an AI Generation Request；provider “thinking” or raw output is not a formal session fact。
- Generation Request identity is separate from final Utterance identity。A future public/durable utterance must reference exact request、AI participant、grant、phase and prompt/model provenance；one logical request produces at most one final utterance。
- P1-5B durable attempt states are `REQUESTED`、`RUNNING`、`COMPLETED`、`FAILED`。Only an atomic `COMPLETED` request + final `ai_utterance` is authoritative historical content；partial/generated-but-unpersisted content is not considered heard by the group and has no public contract。
- A future contract must preserve the order `floor.granted -> generation -> persisted utterance -> floor release` without allowing the LLM/provider to emit state-transition、speaker-selection、scoring or database-mutation commands。
- P1-5D performs exactly one provider request with application retry `0` and no fallback；stable project-owned request identity records the actual provider/model/config used。Late output after phase/grant change is rejected and must not be projected。
- Timeout、unavailable、rate-limit、partial/invalid-output errors are typed internal generation outcomes, not session state changes。Public errors/events expose only safe allowlisted status/reason；provider exception body、credential、rendered prompt、other participants' Private Stance and chain-of-thought remain private。
- Through P1-5E-3，streaming chunks、request/attempt events、utterance event naming、REST transcript reads and Browser rendering had no public contract。P1-5F-1 froze the unified event and transcript read described below；P1-5F-2 now implements the backend command/event/transcript transport。Streaming、request lifecycle events、REST utterance write fallback and Browser implementation remain Deferred。

P1-5C's callable contract is Python-internal only。It assembles the exact authorized context, renders the exact Prompt Version, invokes a typed local executor outside database transactions and commits/replays the P1-5B durable result。It neither consumes nor emits transport messages, and it never auto-triggers from `floor.granted` or auto-releases floor。

P1-5D's Zhipu HTTP request is an outbound infrastructure adapter, not a product/API transport contract。It can be explicitly passed to the existing runtime callable boundary；durable `RUNNING` does not invoke it again，all automated tests inject MockTransport，and no public schema or real GLM validation call was added。

P1-5E-1 freezes only Python-internal application coordination。A durable `floor.granted` condition or a recovery caller may invoke a state-driven drive，but correctness does not rely on delivery of a new event type。The internal sequence is exact current AI grant → deterministic generation identity → confirmed terminal request/utterance truth → existing deterministic floor release → release commit → existing scheduler → committed next-floor decision。HUMAN current grants、no-grant、intervention、non-floor lifecycle、uncertain state and the 8-turn safety budget stop the internal drive。

P1-5E-2 implements the single-turn portion as the Python-internal `drive_single_ai_turn(...)` application boundary。It returns a closed provider-neutral result，drives at most one exact AI grant and one post-release scheduler checkpoint，and does not add a second AI turn、transport entry point or public event。

No P1-5E-2 public contract is added:

- no REST endpoint or OpenAPI field starts/observes the automatic drive；
- no WebSocket command/event exposes generation request、provider/model、prompt、automatic release result or budget state；
- no public utterance event name/version、streaming chunk or Browser rendering is frozen；
- no user-facing provider failure/intervention behavior is introduced；
- At the P1-5E-2 checkpoint，P1-5F remained responsible for those later concerns。P1-5F-1 now freezes the public contract docs-only；P1-5F-2 owns backend invocation/projection，P1-5F-3 owns Web composition，and P1-5F-4 owns end-to-end independent acceptance。

P1-5E-3 adds `drive_continuous_ai(...)` and `drive_configured_ai_session(...)` as Python-internal application boundaries only。The former loops the E2 result with a fixed eight-advanced-turn guard；the latter lazily composes required server-side Zhipu settings/provider provenance。Neither function is registered as a route、WebSocket command/event、startup task or Browser caller，and missing configuration is a safe internal composition error rather than a public error schema。

The internal orchestrator may return provider-neutral safe categories such as waiting-for-human、turn released/next AI or HUMAN、no-grant、intervention、reconciliation-required and budget-exhausted，but these are not transport/event schema。The historical P1-4 floor-event v1 contract remains unchanged；P1-5F additively introduces the independently versioned v2 public projection below。

The full authority, provenance and failure boundary is in [`exec-plans/P1-5_ai-runtime-foundation.md`](exec-plans/P1-5_ai-runtime-foundation.md)。

## P1-5F public text-discussion contract — F1 frozen; F2 backend implemented

P1-5F-1 was docs-only and froze the contract below。P1-5F-2 now implements its backend parser、durable publication、public projection、ordered WebSocket delivery、owner-only transcript route and mechanically generated REST artifact；handwritten Browser code remains unchanged for P1-5F-3。

### Human WS command and safe rejection

Human text submission is the v1 WS command `participant.utterance.submit` with the existing envelope fields `schema_version`、`type`、`session_id`、UUID4 `action_id` and the closed payload `{ "floor_grant_id": UUID4, "content": string }`。The client cannot send participant/phase/actor/provider/runtime identity；after locked lifecycle reconciliation the server requires the named grant to equal the authoritative current grant and verifies its authenticated `HUMAN` / `CANDIDATE` owner。This exact-floor requirement is a narrow F1 erratum restored during F2 actual-source review；delayed commands never bind implicitly to a later grant。

Accepted content is the unchanged original string with `1..4000` Unicode code points、non-empty `strip()` result and no U+0000。No normalization or automatic trim occurs。A syntactically valid command rejected by authority/content rules receives recoverable `UTTERANCE_REJECTED` / `You cannot submit an utterance right now.` and the socket stays open；malformed messages remain `PROTOCOL_ERROR`。The error never discloses AI floor、stale grant、phase/deadline advance or other internal reason。

`(session_id, action_id)` remains the command identity。Same action plus identical `floor_grant_id` and exact content replays the same two causal events；changing either floor or content returns `ACTION_ID_CONFLICT`。Human `utterance_id` is a deterministic server-owned UUID4-compatible identity derived from session/action identity and cannot be chosen by the client。

### Unified formal utterance event

`participant.utterance.created` v1 is the only Human/AI formal utterance event。Its existing envelope owns `session_id`、`sequence`、`occurred_at` and nullable `action_id`；payload is exactly：

```text
utterance_id
participant_id
actor_kind        # HUMAN | AI
floor_grant_id
phase
content
```

Human uses the original command `action_id`；AI uses `null`。Human success emits the utterance at sequence N and `floor.released / SPEAKER_FINISHED` at N+1 in the same transaction，both with the original Human action ID。

### Additive public floor-event v2 compatibility

Historical floor-event v1 is preserved exactly：`floor.granted` and `floor.intervention_requested` require a non-null UUID4 `action_id`，while `floor.released` permits UUID4 or null。Existing persisted v1 events、backend serialization and Web interpretation retain those semantics；v1 is never rewritten or redacted in place。

P1-5F transport introduces floor-event `schema_version = 2` as an additive public compatibility layer。Event names and payload meanings remain `floor.granted`、`floor.released` and `floor.intervention_requested`；only the envelope causation semantic changes。A v2 `action_id` is always present and nullable and represents only a public client action identity：an event directly caused by the Human `participant.utterance.submit` command may carry that original Human UUID4 where applicable，while internal automatic scheduler、release or intervention causation serializes `null`。The corresponding internal `SessionAction` identity remains durable and private。

P1-5F-2 must preserve historical floor-event v1 while emitting/serializing the new v2 projection where required；P1-5F-3 must parse and project both v1 and v2 without weakening either version's validation。`participant.utterance.created` remains independently frozen at `schema_version = 1`。

New P1-5F utterance/floor projections and errors never expose generation request、provider/model/configuration、Prompt Version/rendered prompt、Private Stance、raw provider data、internal generation failure code、internal automatic action identities、credential or Authorization。There are no public AI generation started/running/failed events。Historical floor-event v1 remains readable under its already-published action semantics。

### Owner-only transcript REST

`GET /sessions/{session_id}/utterances` requires authentication，not a CSRF mutation header。Missing and non-owner sessions both use `404 SESSION_NOT_FOUND`。The transcript is not embedded in `GET /sessions/{session_id}`。

Query contract：exclusive `after_sequence >= 0`；`limit` default `100`、maximum `200`；order `sequence ASC`。Response items always contain `utterance_id`、`sequence`、`occurred_at`、nullable-present `action_id`、`participant_id`、`actor_kind`、`floor_grant_id`、`phase` and `content`。`next_after_sequence` is the last returned transcript sequence when another page exists，otherwise null。Human items preserve the original action ID；AI items use null。

The cursor is the full discussion sequence，not transcript offset。Transcript rows are filtered and therefore legitimately non-contiguous；clients never run gap detection over transcript-only sequences。

### Restore, pending and complete-event ordering

Initial restore loads snapshot/watermark S，then the transcript，then connects WS with `after_sequence=S`。REST/WS duplicates merge by `utterance_id` and authoritative sequence。Identical replay is ignored；same identity with conflicting authoritative fields triggers a full session+transcript reload。Confirmed transcript is merged in place rather than deliberately cleared during reload。

Pending Human `action_id + floor_grant_id + content` is memory-only and is not a formal transcript bubble。It is confirmed by matching the WS utterance action ID or transcript item action ID after reconnect；retry reuses the same exact binding and does not use localStorage/sessionStorage。

The complete WS stream retains strict exact-next sequence/gap recovery。Every event is sent only after commit；send failure changes no business fact and catch-up recovers it。Full Browser and backend acceptance rules are in [`exec-plans/P1-5_ai-runtime-foundation.md`](exec-plans/P1-5_ai-runtime-foundation.md)。

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

P0-6D 在不改变 REST/OpenAPI/error envelope 的前提下，为现有 request middleware 增加 provider-neutral server tracing。启用时从 request headers 白名单复制并仅提取标准 W3C `traceparent`，明确不接受 `tracestate` 或 baggage，创建 `METHOD route-template` `SpanKind.SERVER` span；unmatched/404 使用固定 `METHOD <unmatched>` 且不保存 raw path。span allowlist 仅为 method、route template、status、固定 error category 与 project-owned resource `service.name`；resource 不运行 ambient detector，也不吸收 `OTEL_RESOURCE_ATTRIBUTES`/`OTEL_SERVICE_NAME`。application log 从 active valid span context 增加固定宽度 `trace_id`/`span_id`，客户端 contract 仍只暴露既有 `X-Request-ID` 与 error `request_id`，不新增 trace response header。

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

- `IN_PROGRESS`；P1-1A～E 已完成第一条文字会话 scoped contract、persistence、backend REST/WS、Web caller、browser reconnect regression 和 independent acceptance；P1-1 `DONE`；
- P1-2A safe question/session/private projection design freeze 已完成 docs-only；
- P1-2B persistence/domain/seed、P1-2C safe API/session/Web vertical slice 与 P1-2D independent acceptance 均已完成；P1-2 `DONE`。
- P1-3A～D 已完成；state/timing/command/event/snapshot、backend durable foundation 与 realtime/Web complete phase flow 已独立验收 `PASS`；P1-3 `DONE`，P1 保持 `IN_PROGRESS`。
- P1-4A～E 已完成；P1-4 `DONE`，final independent verdict `PASS`。Safe snapshot/WS/Web floor projection 已实现且无 public floor command。
- P1-5A～P1-5R and the network-free post-closeout remediation are `DONE`; their accepted runtime、public transport and recovery contracts remain unchanged.
- P1-6A～P1-6D are implemented and independently reviewed; P1-6E closeout is `IN_PROGRESS` and P1 remains `IN_PROGRESS`. Structured Memory consumes authoritative public evidence and supplies bounded Working Context internally; no Memory field or command is added to REST、OpenAPI、public events or WebSocket payloads. P1-7/P1-8 remain `NOT_STARTED`.

### P2 and later

- P2 才细化音频、ASR、TTS、打断和恢复事件；
- P4 才细化订单、支付、权益和故障返还契约；
- 不得因长期端点出现在总纲示例中而提前实现。

## TBD

- TBD：WebSocket schema generator package；
- Implemented：P1-2 safe question reads 和 version-bound session create contract；
- Implemented：P1-3B `session.start` REST/WS command parsing、generalized state event v2、phase timing snapshot 和 backend durable state-machine foundation；
- Implemented：P1-3C in-process deadline recovery、connected realtime catch-up/push、Browser authoritative phase/deadline projection 和 complete Chromium phase flow；
- Implemented：P1-4 minimum formal floor facts、deterministic schedule → fact orchestration、owner-only safe snapshot projection and display-only Realtime/Web recovery；public floor commands remain absent；
- Implemented in P1-5F-2：Human utterance WS command、unified Human/AI public utterance events、recoverable rejection、v1/v2 floor projection、owner-only transcript REST and ordered reconnect/live delivery；
- Implemented atomic AI publication：Generation Request、final AI Utterance and matching public event share the locked completion transaction and completed replay proof；
- Deferred：event retention/compaction、large replay pagination、multi-tab/cross-process delivery 和长期 compatibility policy；
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
