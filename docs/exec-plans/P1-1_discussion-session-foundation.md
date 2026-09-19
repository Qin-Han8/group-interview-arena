# P1-1 Discussion Session Foundation Execution Plan

Status: `P1 DONE / CLOSED`; `P1-1 DONE`; `P1-1A` through `P1-1E completed`; independent final verdict `PASS`. The original later-task approval boundary remains historical; current phase status is tracked in `TASKS.md`.

Target version: `V0.1 Internal Validation`

Product baseline: [`PROJECT_MASTER_PLAN.md`](../PROJECT_MASTER_PLAN.md)

Accepted architecture: [`ADR-003`](../DECISIONS.md#adr-003--fastapi-作为主要业务后端), [`ADR-005`](../DECISIONS.md#adr-005--postgresqlsqlalchemy-与-alembic-数据基线), [`ADR-006`](../DECISIONS.md#adr-006--rest-与-websocket-通信边界), [`ADR-007`](../DECISIONS.md#adr-007--api-契约生成策略), [`ADR-008`](../DECISIONS.md#adr-008--redis-延后运行), [`ADR-009`](../DECISIONS.md#adr-009--独立后台任务队列延后), [`ADR-011`](../DECISIONS.md#adr-011--轻量领域导向混合模块架构), [`ADR-012`](../DECISIONS.md#adr-012--分阶段测试与质量工具策略), [`ADR-013`](../DECISIONS.md#adr-013--配置错误与结构化日志基线), [`ADR-014`](../DECISIONS.md#adr-014--provider-neutral-ai-与自定义讨论编排), [`ADR-015`](../DECISIONS.md#adr-015--initial-identity-and-browser-session-boundary)

P1-1A baseline: `main` at `118aa6d298bd80a5868da2457484c1609ab77d3f`; `PROJECT_MASTER_PLAN.md` SHA-256 `2388A9660320406CB35D5354126AD71C6849A98DB7C4A356796CA951BF372F26`

## Goal

建立第一条不需要在 P2 推倒重写的 authenticated text-session foundation：用户可创建最小 simulation session、通过 REST 获取 authoritative snapshot、通过 WebSocket 发送带稳定 `action_id` 的命令并接收带 session 内 monotonic `sequence` 的正式事件；重复命令不重复改变业务状态，断线后使用 REST snapshot watermark 加后续有序事件恢复。

P1-1 只证明 session、persistence、transport、authentication/authorization、idempotency、ordering 和 reconnect 边界。它不实现题目系统、参与者、逐句发言、讨论编排、AI 角色、LLM、评分或报告。

## Current baseline

- P0-7 final acceptance 已在当前 `main` 完成；initial findings 已修复，finding-only independent recheck 为 `PASS`，P1 readiness 为 `READY`。
- FastAPI 是 domain/session/persistence authority；Next.js 不持有正式 session state。
- FastAPI lifespan 已拥有 `AsyncEngine` 和 `async_sessionmaker`；HTTP 请求使用 request-scoped `AsyncSession`，operation boundary 显式拥有 transaction。
- PostgreSQL 18.x、SQLAlchemy 2.x、psycopg 3 和 Alembic 已建立；当前 single head 为 session foundation revision `f1a11d15c001`。
- 当前 product tables 精确为 `users`、`auth_sessions`、`simulation_sessions`、`session_actions`、`discussion_events`；API startup 不执行 migration，也不调用 `create_all()`/`drop_all()`。
- identity 已提供 stable UUIDv4 `user_id`、PostgreSQL-backed opaque `gia_session` Cookie 和 current-user lookup；raw token 只在 HttpOnly Cookie 中，数据库只保存 digest。
- `Settings.cors_origins` / `GIA_API_CORS_ORIGINS` 是 CORS、CSRF 与 browser WebSocket Origin validation 必须共用的 trusted-origin Source of Truth。
- REST OpenAPI 已由 FastAPI 生成并通过 `openapi-typescript`/`openapi-fetch` 消费；WebSocket contract 必须独立版本化。
- structured logs 已使用安全 allowlist 字段和 `request_id`；HTTP tracing 只记录 route template 和固定安全属性。
- Web 已有 authenticated identity/session caller、generated REST client、minimal realtime client、Vitest/Testing Library 和真实 PostgreSQL + Chromium E2E harness。

## Five-stage decomposition

1. **P1-1A — Preflight / scope freeze / execution plan**：`completed`。只冻结本计划和同步 current-state 文档；不修改 runtime、tests、migration、schema、dependencies、lockfiles 或 CI。
2. **P1-1B — Session persistence + migration foundation**：`completed`。已实现三张最小 product tables、ORM metadata 和线性 Alembic revision；只验证 schema/migration，不实现 REST、WebSocket 或 Web UI。
3. **P1-1C — Backend REST + WebSocket vertical slice**：`completed`。已实现 authenticated create/snapshot、WS v1 contract、持久化 command handling、idempotency、sequence、catch-up 和安全错误；Web caller 随后的 P1-1D 才创建。
4. **P1-1D — Web realtime caller + reconnect cross-layer validation**：`completed`。已因真实 caller 创建最小 `lib/realtime` 与 browser session UI，并以 PostgreSQL-backed Chromium 回归验证 reconnect/idempotency/ordered projection。
5. **P1-1E — Independent final review / P1-1 closeout**：`completed`。已从 committed/approved source state 独立复核完整 P1-1，不增加新业务能力；verdict `PASS`、findings none，P1-1 已转为 `DONE`。

每个子阶段都需要用户单独明确批准。P1-1D 完成后不得自动进入 P1-1E。

## Frozen scope and ownership

### Domain authority

- `simulation_session` 是本阶段唯一业务 aggregate root。
- FastAPI domain/service code 负责状态转换和 command outcome；transport 只解析/序列化，ORM 只负责 persistence。
- PostgreSQL 保存 authoritative session state、accepted action identity 和正式 event log。
- Browser state 是 snapshot 与事件的 projection；不得由 local storage、React state 或 WebSocket connection state反向覆盖服务端。
- P1-1 使用自定义、确定性代码；没有 LLM caller，因此不创建 `LLMProvider`、provider adapter 或 fake provider 空壳。

### Minimal domain objects

- `SessionSnapshot`：`session_id`、`status`、`created_at`、`updated_at`、`last_sequence`。
- `SessionCommand`：validated v1 command，包含 `type`、`session_id`、`action_id` 和 command payload。
- `PendingEvent`：domain operation 产生的零到多条未分配 sequence 的正式事件。
- `StoredEvent`：已持久化的 `event_type`、`event_version`、`session_id`、`sequence`、`occurred_at`、nullable causation `action_id` 和 payload。
- `SessionStatus` 当前只使用总纲已有的 `CREATED` 与异常状态 `ABORTED_USER`。数据库使用可演进的 `VARCHAR`，不使用 PostgreSQL native enum，也不建立只允许当前两个值的封闭 check constraint；application enum 是当前写入权威。

### Minimal current behavior

- `POST /sessions` 原子创建 `CREATED` session，并创建 sequence `1` 的 `session.created` formal event。
- WebSocket v1 唯一 business command 为 `session.abort`，payload 必须是空 object。
- 合法 `session.abort` 将 `CREATED` 转为 `ABORTED_USER`，并创建 `session.state_changed` event，payload 精确为 `{"previous_status":"CREATED","status":"ABORTED_USER"}`。
- 已处于 `ABORTED_USER` 的 session 接收新的 `action_id` 时返回 `INVALID_SESSION_STATE`，不保存 action、不增加 sequence、不产生 event。
- 相同 accepted `action_id` 重试时重发该 action 已持久化的全部 events，保持原 sequence/occurred_at，不重复改变 state。

`session.abort` 是真实、长期合理且不依赖 question/participant/utterance 的最小业务动作；不创建 `ping`、`noop`、临时标题或其他只为测试基础设施而存在的产品行为。

## Frozen PostgreSQL schema

P1-1B 只新增 `simulation_sessions`、`session_actions`、`discussion_events`。完成后 product table set 应精确为这三张表加既有 `users`、`auth_sessions`。

### `simulation_sessions`

- `id UUID PRIMARY KEY`，application 生成 UUIDv4。
- `owner_user_id UUID NOT NULL`，foreign key → `users.id`，`ON DELETE CASCADE`。
- `status VARCHAR(32) NOT NULL`，当前 application values 为 `CREATED`、`ABORTED_USER`。
- `last_sequence BIGINT NOT NULL DEFAULT 0`，check `last_sequence >= 0`；它既是 snapshot watermark，也是正式 event sequence allocator 的持久化计数器。
- `created_at TIMESTAMPTZ NOT NULL`。
- `updated_at TIMESTAMPTZ NOT NULL`。
- 当前查询以 session primary key 加 owner predicate 授权；不为尚不存在的 session list/query 建 owner-only index。

### `session_actions`

- `session_id UUID NOT NULL`，foreign key → `simulation_sessions.id`，`ON DELETE CASCADE`。
- `action_id UUID NOT NULL`。
- `command_version SMALLINT NOT NULL`，generic check `command_version > 0`。
- `command_type VARCHAR(64) NOT NULL`。
- `payload_digest BYTEA NOT NULL`，check `octet_length(payload_digest) = 32`。
- `created_at TIMESTAMPTZ NOT NULL`。
- composite primary key `(session_id, action_id)`；`action_id` 的正式作用域是单一 session，不要求全局唯一。
- 不保存 raw Cookie、user credential 或重复 command content。digest 是服务端对 validated semantic command `{schema_version,type,payload}` 的 compact sorted-key UTF-8 JSON 计算 SHA-256；`session_id`/`action_id` 不进入 digest。

### `discussion_events`

- `session_id UUID NOT NULL`，foreign key → `simulation_sessions.id`，`ON DELETE CASCADE`。
- `sequence BIGINT NOT NULL`，check `sequence > 0`。
- `event_version SMALLINT NOT NULL`，generic check `event_version > 0`。
- `event_type VARCHAR(64) NOT NULL`。
- `causation_action_id UUID NULL`。
- `payload JSONB NOT NULL`。
- `occurred_at TIMESTAMPTZ NOT NULL`。
- composite primary key `(session_id, sequence)`。
- composite foreign key `(session_id, causation_action_id)` → `session_actions(session_id, action_id)`；creation/system events may use nullable causation。
- index `(session_id, causation_action_id, sequence)` supports durable duplicate-action replay。
- `causation_action_id` 不唯一；一个 command 可以产生多条 ordered events，schema 和 service 都不得假定一 action 只产生一 event。

### Sequence allocation and transaction boundary

- 禁止 `MAX(sequence) + 1`、in-memory counter、UUID ordering 或 process-local lock 生成 formal sequence。
- 每个 accepted command 使用短 PostgreSQL transaction，先 `SELECT simulation_sessions ... FOR UPDATE` 锁定 aggregate row。
- 在同一锁/transaction 内检查 `(session_id, action_id)`、验证 state、产生 `PendingEvent[]`、插入 action、将 `last_sequence` 从 `N` 原子推进到 `N + event_count`，并把 events 分配为连续 `N+1 ... N+event_count`。
- action、state change、watermark 和全部 events 同一 transaction commit；任一失败全部 rollback。
- duplicate 在取得同一 session row lock 后读取既有 action。digest/type/version 相同则返回其全部 stored events；不同则返回 `ACTION_ID_CONFLICT`，不产生 mutation。
- network send 只发生在 commit 后。send 失败不能 rollback 已提交的业务结果；客户端通过 retry/reconnect 取回相同 events。
- WebSocket connection 不长期持有 `AsyncSession` 或数据库 transaction；authentication、catch-up 和每条 command 各使用短 session/transaction。

## Evolution boundary for later P1/P2 entities

- P1-1 不创建 `question_versions`、`session_participants` 或 `utterances`，也不在 session/event JSON 中伪造这些 normalized records。
- P1-2 建立真正 question version caller 时，以 additive migration 增加 `question_versions` 和 `simulation_sessions.question_version_id`。P1-1 的 foundation sessions 可保持 nullable legacy rows；从 P1-2 起由 application invariant 要求新的 runnable session 关联版本。不得预存不存在的 question UUID。
- participant 出现时使用独立 `session_participants` 一对多表；真人 participant 可关联既有 `user_id`，AI participant 关联届时真实存在的 persona/config version。不得在 `simulation_sessions` 增加 `participant_1/2/3` columns。
- utterance 出现时使用独立 `utterances` 表并关联 session/participant；transcript、phase/timing/interruption 等属于 utterance。`discussion_events.payload` 只引用 `utterance_id` 和必要安全 metadata，不作为 transcript 的唯一正式存储。
- `discussion_events` 是 ordered domain/transport event log，不替代 question、participant、utterance 或未来 report 的 canonical tables。
- P2 音频字段和 ASR/TTS lifecycle 只在 P2 真实 caller 出现时添加；P1-1 schema 不包含 audio URL、ASR confidence、TTS state 或 provider identifiers。

## Frozen REST contract

FastAPI OpenAPI 继续是 REST Source of Truth，Web generated derivative 必须同步并通过 drift check。

### `POST /sessions`

- Requires authenticated opaque Cookie session。
- Requires the existing exact Origin + `X-GIA-CSRF: 1` browser guard because it changes state。
- Request body：none。
- Success：`201` with `SessionSnapshotResponse`。
- Creation transaction inserts the session and `session.created` event, so response `last_sequence` is `1`。

### `GET /sessions/{session_id}`

- Requires authenticated opaque Cookie session。
- Success：`200` with `SessionSnapshotResponse`。
- Missing session and session owned by another user both return `404 SESSION_NOT_FOUND`，避免 existence disclosure。
- No CSRF header，because it is read-only。

### `SessionSnapshotResponse`

```json
{
  "id": "00000000-0000-4000-8000-000000000000",
  "status": "CREATED",
  "created_at": "2026-08-16T00:00:00Z",
  "updated_at": "2026-08-16T00:00:00Z",
  "last_sequence": 1
}
```

Owner identity、Cookie/token、question、participants、utterances 和 event backlog 不进入 snapshot。REST timestamps 使用 ISO 8601 UTC `Z`。

## Frozen WebSocket v1 contract

### Endpoint and handshake

- Endpoint：`/ws/sessions/{session_id}?after_sequence=<non-negative integer>`。
- Browser automatically supplies the existing host-only `gia_session` Cookie；browser WebSocket API 不支持自定义 CSRF header，因此 WS CSRF defense 是 exact trusted `Origin` validation。
- Origin parsing must reject missing、`null`、untrusted or duplicate Origin headers and consume the same normalized `Settings.cors_origins` used by CORS/CSRF；不得增加第二个 env/config key。
- Before accept，server resolves the existing opaque session and verifies `owner_user_id`。Missing/expired auth is unauthorized；missing/non-owned session uses non-disclosing not-found semantics。
- Unauthorized/untrusted connections are denied before `accept()` and never receive formal session events。Browser UI may only show a generic safe connection failure。
- Server generates a UUIDv4 `connection_id` after successful authorization；it is diagnostic only，not persisted session state。

### Client command envelope

```json
{
  "schema_version": 1,
  "type": "session.abort",
  "session_id": "00000000-0000-4000-8000-000000000000",
  "action_id": "00000000-0000-4000-8000-000000000001",
  "payload": {}
}
```

- `session_id` must match the authorized path session。
- `action_id` is client-generated UUIDv4 and remains stable across network retry/reconnect until a terminal accepted/error result is known。
- Unknown fields are rejected；unsupported version/type and malformed JSON are protocol errors。

### Formal server event envelope

```json
{
  "schema_version": 1,
  "type": "session.state_changed",
  "session_id": "00000000-0000-4000-8000-000000000000",
  "sequence": 2,
  "occurred_at": "2026-08-16T00:00:01Z",
  "action_id": "00000000-0000-4000-8000-000000000001",
  "payload": {
    "previous_status": "CREATED",
    "status": "ABORTED_USER"
  }
}
```

- `action_id` is nullable for `session.created` and other future system events。
- Formal events are persisted before send and always carry sequence；client-local connection notices are not formal events and must not consume sequence。

### Safe WS error envelope

```json
{
  "schema_version": 1,
  "type": "error",
  "session_id": "00000000-0000-4000-8000-000000000000",
  "action_id": "00000000-0000-4000-8000-000000000001",
  "occurred_at": "2026-08-16T00:00:02Z",
  "error": {
    "code": "INVALID_SESSION_STATE",
    "message": "Session command could not be applied.",
    "request_id": "00000000-0000-4000-8000-000000000002"
  }
}
```

- WS errors align with REST `code`/safe `message`/`request_id` semantics and add session/action context。
- Error messages do not expose SQL、traceback、filesystem path、Cookie/token、payload、Origin value or raw exception。
- WS errors are not formal domain events：they are not persisted and carry no `sequence`。
- Recoverable domain errors (`INVALID_SESSION_STATE`, `ACTION_ID_CONFLICT`) keep the connection open；malformed/unsupported protocol sends `PROTOCOL_ERROR` then closes with `1008`；unexpected internal failure sends safe `INTERNAL_ERROR` when possible then closes with `1011`。

### Contract authority without a new generator dependency

- Backend Pydantic v2 WebSocket models are the v1 contract authority。
- Web TypeScript discriminated unions are derivative and appear only with the P1-1D caller。
- Shared canonical valid/invalid JSON fixtures and cross-layer serialization tests must prove the derivative matches backend behavior。
- WebSocket schema generator package remains Deferred；do not force WS schemas into REST OpenAPI and do not add a dependency only for this two-command/event contract。

## Snapshot, reconnect and gap behavior

1. Browser loads `GET /sessions/{id}` and sets local `last_sequence` to snapshot `last_sequence`。
2. Browser connects WS with `after_sequence=last_sequence`。
3. Server validates `after_sequence <= authoritative last_sequence` and sends persisted events with greater sequence in ascending order before processing commands。
4. An event with `sequence == local last_sequence + 1` is applied；`sequence <= local last_sequence` is an idempotent replay and ignored。
5. `sequence > local last_sequence + 1` is a gap。Client must stop applying incrementals、close the socket、reload authoritative REST snapshot、then reconnect with the new watermark。
6. `after_sequence` ahead of server watermark produces safe `SEQUENCE_AHEAD` and forces the same REST reload path。
7. P1-1 retains all of its tiny event history with the session and has no replay-retention window。Compaction、retention、large backlog pagination and archived replay remain Deferred until a real load/caller exists。

P1-1 only promises delivery to the originating connection plus reconnect catch-up from PostgreSQL。Multi-tab fan-out、cross-process broadcast、multi-worker routing and proactive AI events are not implemented。Those are the accepted Redis re-evaluation triggers；they do not justify Redis in P1-1。

## Authentication, authorization and browser security

- REST and WS reuse the exact current-user/session lookup from identity service；no JWT、query token、local-storage token or parallel auth middleware。
- REST state changes reuse the existing CSRF guard and `SessionCookie` OpenAPI security scheme。
- WS authorizes both identity and session ownership before accepting；a valid login alone is insufficient to read another user's session。
- The raw WebSocket path/query、Cookie、Origin and auth failure details are never application log fields。
- Session UUID is safe only after strict UUID parsing and authorization; connection UUID is server-generated。Neither substitutes for `user_id`, and `user_id` is not added to routine realtime logs/spans。

## Logging and tracing safety boundary

- P1-1C adds real log callers for `session_id` and `connection_id` and extends the existing allowlist/log helper only for validated UUID strings。
- Permitted realtime log correlation：`request_id`、`session_id`、`connection_id`、validated `action_id`、formal `sequence`、fixed event name、fixed error category and bounded duration/status fields。
- Forbidden：command/event payload text、raw path/query、Origin、headers、Cookie/token/digest、username/user_id、SQL、exception message/traceback and future prompt/provider content。
- Existing HTTP session routes continue to use route-template tracing; path `session_id` is not placed in HTTP span route attributes。
- P1-1 does not require a new long-lived WebSocket OTel span or new propagation mechanism。If P1-1C adds bounded WS command spans while implementing correlation, they may extract only existing `traceparent` at handshake and may add only validated `session_id`/server-generated `connection_id`/fixed command type/status/error category；no arbitrary carrier or payload collection。
- Negative sentinel tests must prove realtime errors、logs and any newly added spans exclude sensitive/attacker-controlled values。

## Exact implementation plan

### P1-1B — Session persistence + migration foundation

**Expected files**

- Modify `apps/api/src/group_interview_arena_api/db/models.py` and `apps/api/src/group_interview_arena_api/db/__init__.py` to register exactly the three scoped ORM models。
- Create `apps/api/migrations/versions/f1a11d15c001_establish_discussion_session_foundation.py` with `down_revision = "4fe43b42641b"`。
- Create `apps/api/tests/test_discussion_session_models.py`；modify `apps/api/tests/test_database.py` and `apps/api/tests/test_migrations.py` for exact metadata/schema/history assertions。
- Modify `apps/api/tests/integration/test_migrations.py` for fresh/repeat/check/downgrade-to-identity/re-upgrade and exact PostgreSQL catalog assertions。

**Steps**

- [x] Write failing metadata/model tests for exact five-table product metadata, columns, generic checks, FKs and indexes。
- [x] Implement the three ORM models without native enum, relationship graph or future entities。
- [x] Write migration-history and revision-shape tests that preserve both existing revisions byte-for-byte and require a linear single head。
- [x] Create/review the migration; downgrade removes only the three P1-1 tables in dependency-safe order and returns to the identity head。
- [x] Run isolated real PostgreSQL fresh upgrade、repeat upgrade、`current --check-heads`、`alembic check`、downgrade to identity、re-upgrade and exact schema/index/constraint checks。
- [x] After all disposable-database gates pass, verify the development DB exact name、current identity head、expected two-table schema and row counts; run approved `upgrade head` once, verify repeat upgrade is a no-op, and never downgrade development。

**Acceptance**

- Migration graph single head and existing revisions unchanged。
- Exact product table set and schema match this plan；no question/participant/utterance/provider/payment/voice tables or columns。
- Development DB is either truthfully reported as not migrated because a safety precondition failed, or is at the new single head after the approved exact-name/read-only/schema preflight；no automatic startup migration or development downgrade。
- Unit、integration、Ruff、format、Pyright、frozen lock and `git diff --check` pass。
- No REST/WS/UI code and no dependency/lockfile/CI changes。

### P1-1C — Backend REST + WebSocket vertical slice

**Expected files**

- Create `apps/api/src/group_interview_arena_api/modules/__init__.py` and `modules/discussion_sessions/{__init__.py,domain.py,contracts.py,service.py,routes.py,realtime.py}`；create no unrelated module directories。
- Modify `apps/api/src/group_interview_arena_api/app.py` to register the REST/WS routes and `core/errors.py` for stable scoped codes。
- Create `apps/api/src/group_interview_arena_api/identity/dependencies.py` and minimally modify `identity/routes.py` only if needed to share the existing current-user resolution；modify `db/dependencies.py` only if a short-lived session-factory accessor is required。Do not change credential/Cookie semantics。
- Modify `apps/api/src/group_interview_arena_api/core/logging.py` only for real session/connection correlation fields and negative safety coverage。
- Add unit and PostgreSQL integration tests for REST、WS、transactions、concurrency、authorization、idempotency、ordering and reconnect。
- Regenerate `apps/web/src/lib/api/generated/schema.d.ts` from FastAPI OpenAPI; do not create `lib/realtime` yet。
- Create focused tests `apps/api/tests/test_discussion_session_domain.py`、`test_discussion_session_contracts.py`、`test_discussion_session_routes.py` and integration tests `tests/integration/test_discussion_sessions.py`、`test_discussion_session_api.py`、`test_discussion_session_websocket.py`；extend existing logging/migration tests only for their owned boundaries。

**Steps**

- [x] Write failing pure-domain tests for `CREATED -> ABORTED_USER`, invalid state, and a list-valued event outcome。
- [x] Implement deterministic domain types/transition without I/O or framework coupling。
- [x] Write failing real PostgreSQL service tests for creation event sequence `1`, concurrent identical action, concurrent distinct actions, digest conflict, rollback and multi-event contiguous reservation capability。
- [x] Implement the row-lock/transaction command service; network send remains outside the service transaction。
- [x] Write failing REST tests for auth、shared CSRF、owner-only create/snapshot、safe 401/404 and OpenAPI models。
- [x] Implement `POST /sessions` and `GET /sessions/{id}` and update the generated REST derivative。
- [x] Write failing WS contract/handshake tests for Cookie auth、exact shared Origin、ownership、version/type/schema validation and safe errors。
- [x] Implement WS v1 accept/catch-up/receive/commit/send loop with a fresh short DB session per operation。
- [x] Write and pass duplicate retry、lost-send reconnect、ordered catch-up、replay ignore、ahead watermark and sequence-gap regression tests。
- [x] Add safe realtime logging fields and sentinel negative tests; do not expand trace collection without the bounded allowlist above。

**Acceptance**

- REST/WS contracts and semantics match this plan exactly。
- Two concurrent copies of the same action produce one accepted action, one state transition and one event sequence; duplicate response reuses the stored event。
- No duplicate `(session_id, sequence)` and no gap among committed formal events；no `MAX()+1` or memory-only idempotency。
- Non-owner cannot infer or connect to another user's session。
- API unit/integration/full suites、Ruff、format、Pyright、migration checks、OpenAPI drift and `git diff --check` pass。
- No Web UI/realtime caller, provider, Redis, queue, LLM or CI changes。The actual-source review blocker exception below permits only the direct WebSocket network-runtime dependency and its lockfile update。

P1-1C completion evidence: API unit `201`、PostgreSQL integration `38`、API full `239`、Ruff、format、Pyright、Alembic heads/current/check、Web lint/format/typecheck/Vitest `16`/build 与 REST OpenAPI drift 均通过；schema/migration、CI 与 Web `lib/realtime` 未修改。P1-1D 保持 not started。

P1-1C actual-source review finding F1 identified a real network-runtime blocker: the project declared bare Uvicorn but neither `websockets` nor `wsproto`, so Starlette `TestClient` coverage could not prove a real Uvicorn WebSocket Upgrade。The approved finding-only exception adds direct `websockets>=16.0,<17` plus the frozen lock update and validates the existing REST/WS flow against a real Uvicorn process and disposable PostgreSQL database。This does not change the frozen contract or architecture scope and does not add Uvicorn `standard` extras。

### P1-1D — Web realtime caller + reconnect cross-layer validation

**Expected files**

- Create `apps/web/src/lib/realtime/contract.ts`、`contract.test.ts`、`client.ts` and `client.test.ts` only now, with the v1 derivative contract and a real caller。
- Create `apps/web/src/features/sessions/session-panel.tsx` and `session-panel.test.tsx`；modify `apps/web/src/app/auth-panel.tsx` only to mount the feature for an authenticated user，and modify `apps/web/src/lib/api/client.ts`/tests for generated create/snapshot calls。
- Create `apps/web/e2e/session.spec.ts` and extend `apps/api/tests/integration/browser_e2e.py` plus its safe temporary-database guard only for authenticated create/snapshot/WS/action/reload/reconnect evidence；use a disposable PostgreSQL database matching `^gia_p11d_[0-9a-f]{12}$` with exact cleanup rather than reusing a development database。

**Steps**

- [x] Write failing TypeScript contract fixtures/type-guard tests against backend canonical v1 examples。
- [x] Implement minimal realtime parsing and reject unknown/malformed server messages without applying them。
- [x] Write failing client state tests for stable `action_id` retry、duplicate event ignore、strict next-sequence apply、gap-triggered snapshot reload and reconnect cleanup。
- [x] Implement the smallest connection state machine with one live socket, bounded reconnect attempt behavior and authoritative REST reload on gap。
- [x] Write component tests for create、connect、abort、safe connection error and server-authoritative reload states。
- [x] Add the minimal authenticated browser caller; do not add question/participant/utterance/AI/report UI。
- [x] Extend Chromium E2E to verify Cookie-authenticated WS、created watermark、abort event、duplicate action no duplicate DB effect、reload snapshot restore and server/database/process cleanup。

**Acceptance**

- `lib/realtime` has a real caller and no provider/transport abstraction beyond v1 needs。
- Browser never persists raw Cookie/action payload/session authority in local/session storage。
- Web unit/component tests、lint、format、typecheck、production build、REST OpenAPI drift and real PostgreSQL Chromium E2E pass with zero skips。
- API regression/integration and migration gates remain green；no dependency/lockfile/CI changes unless a separately approved blocker proves unavoidable。

P1-1D completion evidence: Web Vitest `37`、lint、format、typecheck、production build 与 REST OpenAPI drift 通过；API non-integration `201`、PostgreSQL integration `39`、full `240`、Ruff、format、Pyright 与 Alembic heads/current/check 通过。真实 Next/Chromium → Uvicorn WS → disposable `gia_p11d_*` PostgreSQL E2E 为 `2 passed` / zero skips，验证 opaque Cookie + trusted Origin、sequence `1` catch-up、stable `action_id` abort/replay、sequence `2`、REST reload restore、单一 durable action、events `[1, 2]` 及 DB/process/port cleanup。Actual-source review F1 reconnect-budget remediation 以 deterministic regression 证明健康恢复后新的独立断线仍可有界重连，持续失败仍有上限。No dependency/lockfile、CI、backend contract、schema 或 migration change；P1-1E subsequently completed with independent verdict `PASS`。

### P1-1E — Independent final review / closeout

**Expected files**

- No feature files by default。Only finding remediation and truthful status/docs updates may change source after findings are reported and explicitly scoped。

**Steps**

- [x] Independently recover committed Git/Source of Truth baseline and review actual P1-1 diff rather than prior PASS prose。
- [x] Re-run migration history/schema/concurrency/idempotency/authz/Origin/error/privacy/reconnect and cleanup evidence。
- [x] Re-run full API/Web/PostgreSQL/Chromium quality gates required by the final changed boundary。
- [x] Confirm no Redis、queue、LangGraph、LLM/vendor、question CMS、participant/utterance、voice、score、payment or speculative directory scope creep。
- [x] Record findings; independent verdict `PASS` with findings none; mark P1-1 `DONE`。

**Acceptance**

- Independent verdict `PASS` with no unresolved launch blocker or material-rework finding。
- P1-1B～D evidence is reproducible, temporary databases/listeners/artifacts are cleaned, docs match actual source。
- Only then update P1-1 to `DONE`; P1 remains `IN_PROGRESS` for its next separately approved task。

## Validation commands for implementation phases

Use actual project commands at execution time; do not claim unrun gates。Current expected command families are:

```powershell
Set-Location apps/api
uv sync --frozen
uv lock --check
uv run ruff check .
uv run ruff format --check .
uv run pyright
uv run pytest -m "not integration"
uv run pytest -m integration
uv run pytest
uv run alembic heads
uv run alembic check

Set-Location ../..
pnpm.cmd install --frozen-lockfile
pnpm.cmd web:lint
pnpm.cmd web:format:check
pnpm.cmd web:typecheck
pnpm.cmd web:test
pnpm.cmd web:build
pnpm.cmd web:api:check
pnpm.cmd web:test:e2e

git diff --check
git status --short
```

Database commands require the existing protected disposable PostgreSQL harness。Do not point integration tests at the development database and do not run API startup migration。

Git staging、commit and push remain separate user-authorized actions in every implementation subphase；the phase runner must stop after diff/evidence unless the user explicitly authorizes them。

## Explicit deferrals

- Question templates/versions、12-question content set、CMS/admin and question publishing workflow。
- Session participants、AI personas、utterances、text discussion loop、state machine beyond the scoped abort transition、floor scheduling and structured memory。
- LLM Provider/vendor/model、real or fake provider implementation、LangGraph and model invocations。
- Reports、evidence extraction、objective metrics and six-dimension scoring。
- Voice、microphone、audio、ASR、TTS and interruption playback。
- Redis、multi-worker/cross-process broadcast、distributed lock/rate limit and task queue/worker。
- Event retention/compaction、large replay pagination、multi-tab fan-out and offline support。
- Payment、entitlement、growth、industry packs、account expansion/recovery/RBAC and production deployment。
- WebSocket schema generator package；the P1-1 v1 contract uses existing Pydantic plus tested TypeScript derivative。

## Decisions and open items

- No new Proposed Decision is required。All frozen choices are scoped implementation details derived from accepted ADRs and the master plan。
- No P1-1B blocker is known at P1-1A closeout。
- The existing `DECISIONS.md` open/deferred entries for provider、Redis、task queue、identity expansion and WebSocket generator remain Deferred and do not block P1-1。
- Future question/participant/utterance schema details are intentionally not decided by P1-1; their additive boundaries are fixed above without inventing their product schemas。

## Risks and stop conditions

- **BLOCKER — baseline or user changes**：if P1-1B starts from a dirty/changed baseline that overlaps planned files, stop and report; never reset/restore/clean/stash user work。
- **BLOCKER — migration safety**：non-linear head、changed historical revision、development DB ambiguity or inability to isolate a disposable PostgreSQL database stops migration work。
- **HIGH — duplicate side effects**：any memory-only idempotency, action/event partial commit or digest ambiguity blocks P1-1。
- **HIGH — sequence race**：any `MAX()+1`、unlocked read-modify-write or network-before-commit design blocks P1-1。
- **HIGH — authorization/Origin drift**：second trusted-origin config、query token、accepted unauthorized socket or existence disclosure blocks P1-1。
- **HIGH — client authority**：applying a sequence gap or restoring local state without REST snapshot blocks P1-1。
- **MEDIUM — event schema overreach**：using event JSON as canonical question/participant/utterance storage creates future rework and must be corrected before closeout。
- **MEDIUM — telemetry leakage**：payload、Cookie、raw path/query、Origin or exception details in logs/spans/errors blocks closeout。
- **SCOPE STOP**：a required new dependency、Redis、queue、provider、future table or higher-level product decision must be reported and separately approved before implementation。

## Progress

- [x] P1 formally approved by the user。
- [x] P1-1A Git/source-of-truth/actual-source preflight completed。
- [x] P1-1 scope、schema、REST/WS contract、idempotency、sequence、reconnect、security and B～E acceptance frozen。
- [x] P1-1A docs/static validation completed；no runtime implementation started。
- [x] P1-1B persistence/migration implementation and risk-matched validation completed；no REST/WS/UI implementation started。
- [x] P1-1C backend REST/WebSocket vertical slice completed；actual-source review F1 runtime dependency blocker remediated with direct `websockets` and real Uvicorn network evidence；P1/P1-1 remain `IN_PROGRESS`。
- [x] P1-1D Web realtime caller + reconnect cross-layer validation completed；actual-source review F1 reconnect-budget finding remediated with deterministic independent-disconnect and bounded-failure regressions；P1/P1-1 remained `IN_PROGRESS` pending P1-1E。
- [x] P1-1E independently reviewed clean committed `main` at `252ca9524c459ce19d11190ae17059d55c5bd0c1`；verdict `PASS`、findings none；API `201`/`39`/`240`、Web Vitest `37`、Chromium `2 passed` zero skips、static/build/OpenAPI/Alembic gates and cleanup all passed。
- [x] P1-1 `DONE`；P1 remains `IN_PROGRESS`；P1-2 not started / awaiting explicit user approval。
