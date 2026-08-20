# P1-3 Session State-Machine Execution Plan

Status: `P1 IN_PROGRESS`; `P1-3 IN_PROGRESS`; `P1-3A completed`; `P1-3B completed`; `P1-3C not started / awaiting explicit approval`

Target version: `V0.1 Internal Validation`

Product baseline: [`PROJECT_MASTER_PLAN.md`](../PROJECT_MASTER_PLAN.md)

Accepted decisions: [`D-003`](../DECISIONS.md#2-已确认产品决策索引), [`D-008`](../DECISIONS.md#2-已确认产品决策索引), [`ADR-003`](../DECISIONS.md#adr-003--fastapi-作为主要业务后端), [`ADR-005`](../DECISIONS.md#adr-005--postgresqlsqlalchemy-与-alembic-数据基线), [`ADR-006`](../DECISIONS.md#adr-006--rest-与-websocket-通信边界), [`ADR-007`](../DECISIONS.md#adr-007--api-契约生成策略), [`ADR-008`](../DECISIONS.md#adr-008--redis-延后运行), [`ADR-009`](../DECISIONS.md#adr-009--独立后台任务队列延后), [`ADR-011`](../DECISIONS.md#adr-011--轻量领域导向混合模块架构), [`ADR-012`](../DECISIONS.md#adr-012--分阶段测试与质量工具策略), [`ADR-013`](../DECISIONS.md#adr-013--配置错误与结构化日志基线), [`ADR-014`](../DECISIONS.md#adr-014--provider-neutral-ai-与自定义讨论编排), [`ADR-015`](../DECISIONS.md#adr-015--initial-identity-and-browser-session-boundary)

P1-3A baseline: committed `main` at `b775106` (`P1-2D: docs: complete question and persona foundation`); [`PROJECT_MASTER_PLAN.md`](../PROJECT_MASTER_PLAN.md) SHA-256 `2388A9660320406CB35D5354126AD71C6849A98DB7C4A356796CA951BF372F26`

## Goal

建立 V0.1 文字讨论可依赖的 server-authoritative session state machine：状态只能沿冻结的单向路径推进，用户 intent 与内部 deadline transition 分离；每次推进继续使用 P1-1 的 durable action、aggregate row lock、monotonic sequence、single-transaction mutation 和 commit-before-send 语义；当前 phase timing 使用 server UTC clock 和 durable deadline，刷新、断线或进程重启后不重置、不漂移。

P1-3 只建立 session phase/state/timing/recovery 和 Browser authoritative projection。它不实现发言权、AI speaker selection、participant/utterance、LLM/provider、memory、report/scoring、voice/device check、完整 pause/failure engine、Redis 或 queue。

## Current baseline and actual-source findings

- P1-1/P1-2 independent verdicts 均为 `PASS`；当前 Alembic single head 是 `f1a12b15c002`，product tables 精确为十张。
- `simulation_sessions` 已拥有 UUIDv4 identity、owner、immutable `question_version_id`、`status VARCHAR(32)`、durable `last_sequence` 和 timestamps；当前没有 phase timing/plan columns。
- 当前 application `SessionStatus` 精确为 `CREATED` / `ABORTED_USER`；唯一 browser business command 是 `session.abort`，且只允许 `CREATED -> ABORTED_USER`。
- `apply_session_command()` 已用 owner-scoped `SELECT ... FOR UPDATE`、durable `(session_id, action_id)`、semantic digest、single transaction、contiguous event allocation 和 commit-before-send 建立正确并发基础。
- `discussion_events` 已允许 nullable causation action；system event 可使用 `action_id = null`。一个 action 可关联多 events。
- `session.created` 与旧 `session.state_changed` 是 event version `1`；当前 Web derivative 对 v1 abort payload 使用 exact shape validation。P1-3 不得静默改变已持久化 v1 event 的解释。
- Browser 已实现 REST snapshot + ordered WS events projection、duplicate ignore、gap reload、stable pending action retry 和 bounded reconnect；它目前只认识 `CREATED` / `ABORTED_USER`，没有 phase timing。
- 当前 WS 只向 originating connection send；multi-tab fan-out、cross-process broadcast 和 multi-worker routing 已明确 Deferred。P1-3 不以 phase timer 为理由引入 Redis。

## Four-stage decomposition

1. **P1-3A — Design freeze**：`completed`。Docs-only 冻结状态、transition、timing、command/event、snapshot、B～D scope 和 acceptance；不修改 runtime、tests、schema/migration、dependency/lockfile 或 CI。
2. **P1-3B — Backend state machine + durable phase foundation**：`completed`。实现 pure domain matrix、additive timing persistence、server-owned duration-plan resolution、locked transactional transitions、due reconciliation、REST/WS backend contracts和 PostgreSQL regressions；不实现 Browser complete phase UI 或 P1-4 调度。
3. **P1-3C — Realtime/Web complete phase flow**：`not started / awaiting explicit approval`。实现 in-process deadline wake-up/recovery、connected WS catch-up/push、Browser start/current-phase/deadline projection 和真实 PostgreSQL Chromium complete-flow validation；不引入 Redis/queue。
4. **P1-3D — Independent acceptance + closeout**：`not started / awaiting explicit approval`。从 committed source 独立复核 matrix、并发、timing、restart/reconnect、contract/browser 和 Deferred absence；PASS 后才把 P1-3 标记 `DONE`。

P1-3C、P1-3D 均需单独明确批准。P1-3B 完成后不得自动开始 P1-3C。

## Frozen V0.1 state model

### Implemented path

```text
CREATED
  -> PREPARATION
  -> OPENING_STATEMENTS
  -> EXPLORATION
  -> CONFLICT_AND_EVALUATION
  -> CONVERGENCE
  -> FINAL_SUMMARY
  -> COMPLETED
```

`ABORTED_USER` 是 P1-1 已存在并由 P1-3 保留的异常 terminal state。

状态与 phase 在 P1-3 使用同一个 authoritative `simulation_sessions.status` code；不建立会漂移的第二个 `current_phase` 字段。`CREATED` 是未开始状态；六个中间状态是 timed active phases；`COMPLETED` / `ABORTED_USER` 是 P1-3 terminal states。

`COMPLETED` 是“讨论已完成”的 terminal boundary：P1-3 后任何用户或 phase command 都不能回到 active discussion。长期 `REPORT_GENERATING -> REPORTED` 可在未来获批后作为单向 report lifecycle 扩展，但不得 reopen discussion。

### Deferred master-plan states

以下状态仍属于总纲长期导航，但 P1-3 不实现、不写入、不加入当前 transition handler：

- `DEVICE_CHECK`：P2 voice/device scope；V0.1 text path 从 `CREATED` 直接进入 `PREPARATION`。
- `PAUSED_NETWORK`、`PAUSED_SYSTEM`：需要完整 pause/resume timing policy 后单独设计。
- `FAILED_SERVICE`、`COMPLETED_PARTIAL`：需要 service-failure/incomplete-session policy 和后续报告语义。
- `REPORT_GENERATING`、`REPORTED`：报告/评分阶段；不得在 P1-3 用假任务或假报告状态占位。

Deferred 状态不是当前合法输入；收到这些 code 必须 fail closed，而不是自动映射到相近状态。

## Frozen transition matrix

| From | To | Trigger | P1-3 rule |
|---|---|---|---|
| `CREATED` | `PREPARATION` | user `session.start` | only legal start transition |
| `PREPARATION` | `OPENING_STATEMENTS` | server phase deadline | automatic, sequential only |
| `OPENING_STATEMENTS` | `EXPLORATION` | server phase deadline | automatic, sequential only |
| `EXPLORATION` | `CONFLICT_AND_EVALUATION` | server phase deadline | automatic, sequential only |
| `CONFLICT_AND_EVALUATION` | `CONVERGENCE` | server phase deadline | automatic, sequential only |
| `CONVERGENCE` | `FINAL_SUMMARY` | server phase deadline | automatic, sequential only |
| `FINAL_SUMMARY` | `COMPLETED` | server phase deadline | automatic completion |
| `CREATED` or any timed active phase | `ABORTED_USER` | user `session.abort` | legal user abort source |

All other transitions are invalid in P1-3:

- no skip, backward transition or client-selected destination；
- no transition out of `ABORTED_USER`；
- no active-discussion transition out of `COMPLETED`；
- no direct user `advance` / `finish` / `set_state` command；
- no browser field that names `next_status` or supplies phase timestamps/durations；
- no transition into a Deferred state。

## Frozen concurrency and stale-command semantics

- Every mutation locks the owner-scoped `simulation_sessions` aggregate row and re-reads status/timing under that lock。
- Concurrent copies of the same accepted `action_id` replay the same stored events；they do not re-run the transition。
- Concurrent different `session.start` actions can commit only one `CREATED -> PREPARATION` transition；the loser observes the new phase and receives `INVALID_SESSION_STATE` without persisted action/event/watermark change。
- A stale new action cannot advance a second time because user commands never select or advance the current phase. `session.start` is legal only in `CREATED`；system advance includes exact expected status + exact persisted deadline preconditions。
- A timeout invocation is an idempotent system operation, not a browser action. Under the row lock it advances only when current status and deadline still match its expected values and server UTC has reached the deadline；otherwise it is a no-op。
- Before applying a user command, the same transaction reconciles every phase whose persisted deadline is already due. Therefore deadline precedence is based on durable deadline + server UTC evaluation, not on which in-process callback happened to wake first。
- If an abort is evaluated before the current deadline, abort wins. If evaluated at/after it, due phase transitions are recorded first and abort is then evaluated against the resulting state；if catch-up already reached `COMPLETED`, abort is rejected. The committed ordered events are the deterministic result。
- All reconciled system events, accepted user action, final state/timing, `last_sequence` and causal events commit atomically. Errors roll back the whole operation。

## Frozen phase timing model

### Durable fields

P1-3B adds these minimal fields to `simulation_sessions`:

- `phase_started_at TIMESTAMPTZ NULL`：effective start of the current timed phase；
- `phase_deadline_at TIMESTAMPTZ NULL`：authoritative deadline of the current timed phase；
- `phase_duration_plan JSONB NULL`：server-resolved, closed map of positive integer seconds for exactly the six implemented timed phases。

`CREATED` legacy/current rows may have all three null。On accepted `session.start`, the server resolves the configured V0.1 duration profile and atomically freezes the full six-phase plan with the first phase timing。The plan is immutable after start；later deploy/config changes do not alter an in-flight session。

The JSONB field is purpose-specific, closed and domain validated；it is not a generic metadata escape hatch and is not exposed to the Browser。If actual P1-3B source proves an equivalently minimal normalized representation is materially safer, implementation may use it only after updating this plan truthfully before code；it may not omit durable plan immutability。

### Clock and arithmetic

- All authoritative comparisons and persisted timestamps use an aware server UTC clock injected at the domain/application boundary for deterministic tests；never use browser timers as authority。
- `session.start` uses server UTC `now` as `PREPARATION.phase_started_at` and computes its deadline from the frozen plan。
- Normal on-time automatic transition uses the previous persisted deadline as the next phase's effective `phase_started_at`，not callback execution time；next deadline is `effective start + frozen duration`。
- If the process was unavailable through multiple deadlines, recovery advances all overdue phases in order in one locked transaction. This preserves the original schedule and may reach `COMPLETED` immediately；it must not grant extra phase time because of downtime。
- Formal event `occurred_at` is the actual server processing time；`phase_started_at`/`phase_deadline_at` in the event payload are the effective authoritative schedule. They may differ during catch-up and must not be conflated。
- `COMPLETED` and `ABORTED_USER` clear current `phase_started_at` / `phase_deadline_at` to null。Prior phase timing remains reconstructable from persisted formal events。
- Reload/reconnect reads the same persisted status/timing/sequence. A Browser display countdown may tick locally between authoritative messages, but expiry never mutates state locally and every snapshot/event reconciliation replaces the display with server truth。

### In-process timer boundary

- Queue/Redis is not required for P1-3 correctness. PostgreSQL state/deadline/row lock/formal events are authoritative；an in-process timer only provides wake-up/liveness。
- P1-3C may use app-owned async timer/recovery tasks because they have a real caller. Tasks must be bounded, cancellable during app shutdown and must not own authoritative state in memory。
- Startup recovery scans/schedules nonterminal rows with durable deadlines；WS connect and every state-changing command also reconcile overdue phases, so a missed callback cannot reset or permanently strand timing。
- Multiple callbacks/processes are safe because the database precondition and row lock permit one committed transition only。Multi-worker realtime fan-out remains Deferred；a client that misses send recovers through ordered catch-up。

## Frozen command boundary

### Browser/user intent

P1-3 command vocabulary is exactly:

- existing `session.abort` v1：empty payload；legal from `CREATED` and every timed active phase；
- new `session.start` v1：empty payload；legal only from `CREATED`。

Both commands require client-generated stable UUIDv4 `action_id` and reuse P1-1 semantic digest、durable `(session_id, action_id)`、duplicate replay and conflict behavior。Browser cannot send `next_status`、duration、clock、deadline、transition reason or internal timeout command。

### Internal/system transition

`phase deadline elapsed` is an internal application operation with exact expected status/deadline preconditions. It has no client action and its formal events use `action_id = null`。Its exactly-once effect comes from the locked persisted aggregate precondition；it does not create a fake browser action or depend on a process-local idempotency key。

The distinction is deliberate：`action_id` identifies retryable user intent；nullable causation already represents system events。All transitions still reuse P1-1 ordered sequence、single transaction and commit-before-send semantics。

## Frozen formal event vocabulary

P1-3 adds no speculative event type. The minimal formal vocabulary remains:

- `session.created` event version `1`；
- `session.state_changed` for every accepted state transition。

Historical `session.state_changed` version `1` (`CREATED -> ABORTED_USER` with the old exact payload) remains readable/replayable。P1-3 emits generalized `session.state_changed` event version `2` with a closed payload:

```json
{
  "previous_status": "PREPARATION",
  "status": "OPENING_STATEMENTS",
  "trigger": "PHASE_DEADLINE",
  "phase_started_at": "2026-08-20T02:04:00Z",
  "phase_deadline_at": "2026-08-20T02:08:00Z"
}
```

`trigger` is exactly `USER_START`、`USER_ABORT` or `PHASE_DEADLINE`。Terminal events carry null phase timestamps。User-triggered events carry the accepted action ID；deadline events carry null。No `timer.tick`/`timer.updated` event is persisted or consumes sequence；Browser derives display countdown from the authoritative deadline。

Backend Pydantic models remain WS contract authority。Web derivative must support stored v1 events and new v2 events with exact closed validation；event version is not silently rewritten in PostgreSQL。

## Frozen authoritative phase snapshot

`GET /sessions/{session_id}` remains the authoritative load boundary and additively projects:

```json
{
  "id": "00000000-0000-4000-8000-000000000000",
  "question_version_id": "00000000-0000-4000-8000-000000000001",
  "status": "EXPLORATION",
  "phase_started_at": "2026-08-20T02:08:00Z",
  "phase_deadline_at": "2026-08-20T02:13:00Z",
  "server_now": "2026-08-20T02:10:00Z",
  "created_at": "2026-08-20T02:00:00Z",
  "updated_at": "2026-08-20T02:08:00Z",
  "last_sequence": 4
}
```

- `server_now` is response-time server UTC, not persisted state；it lets the Browser estimate display clock skew。
- `phase_started_at` / `phase_deadline_at` are nullable for `CREATED` and terminal states。
- The full duration plan is server-only and not returned。
- Browser projects only status、current timing and `last_sequence` from snapshot/v2 events。It cannot write them, infer a transition from countdown zero or synthesize a formal event。
- On gap/ahead/reload/reconnect, snapshot replaces the entire local phase/timing projection before ordered catch-up resumes。

## P1-3B — Backend state machine + durable phase foundation

### Scope

- Expand the pure session domain to the exact current state set and matrix above；keep status storage as evolvable `VARCHAR`。
- Add the three timing/plan fields through one linear additive migration on `f1a12b15c002`；preserve all historical revisions byte-for-byte。
- Add typed server-owned V0.1 duration configuration/resolver and freeze the closed plan at start；do not add public mode selection or Browser durations。
- Generalize the transactional service for `session.start`、existing abort and internal due reconciliation while retaining P1-1 idempotency/ordering/rollback/commit-before-send。
- Extend REST snapshot and backend WS contract for status/timing/v2 events；retain historical v1 replay compatibility。
- Add pure-domain, contract, real PostgreSQL migration/concurrency/recovery/security regressions。

### Acceptance

- Exact matrix is closed in application code；skip/backward/reopen/client-next-state paths are absent。
- Same-action replay、different-action races、stale start、concurrent timeouts and abort-vs-timeout rules match this plan with one committed result and gap-free sequences。
- Frozen duration plan and current timestamps survive transaction/session/process boundaries；restart catch-up uses prior deadlines without drift。
- Snapshot and event schemas expose no private question/persona data or full timing plan。
- Fresh/repeat/check、downgrade-to-P1-2/re-upgrade、exact catalog and current P1-1/P1-2 regressions pass in disposable PostgreSQL。
- No participant/utterance、scheduler/floor、provider/memory/report、voice、Redis/queue、dependency/lockfile/CI/Web implementation unless a separately approved real blocker is proven。

## P1-3C — Realtime/Web complete phase flow

### Scope

- Add the smallest app-owned in-process deadline wake-up/recovery behavior with clean lifespan shutdown；PostgreSQL remains authority。
- Make an authorized connected session receive committed v2 state events and recover missed transitions through existing catch-up；never send before commit。
- Add Browser `session.start` intent, phase labels, authoritative start/deadline/sequence projection and display-only countdown corrected from `server_now`/event time。
- Extend strict TypeScript derivative for v1 historical + v2 current events, duplicate/gap/stale-socket behavior and stable action retry。
- Add real disposable PostgreSQL + Next/Chromium/Uvicorn tests covering complete timed flow, reload, disconnect/reconnect and API restart recovery with accelerated test-only server timing config。

### Acceptance

- Browser never selects next state, never treats countdown as authority and never persists timing/action/session authority in browser storage。
- A full `CREATED -> ... -> COMPLETED` run is observed in order with stable deadlines and contiguous formal sequences；no duplicate transition under concurrent timers/connections。
- Reload/reconnect and server restart preserve the same effective phase schedule；missed sends are recovered from committed events。
- Abort, duplicate replay, stale start, timeout race, gap reload, owner/Origin/CSRF and private-sentinel regressions pass。
- Timer tasks/processes/listeners/disposable databases/artifacts clean up on success and failure；no Redis/queue or P1-4+ capability appears。

## P1-3D — Independent acceptance + closeout

### Scope and acceptance

- Read-only independent review from committed P1-3B/C source by default；only separately approved finding remediation may change implementation。
- Reproduce migration/schema, matrix, action/event transaction, concurrency, deadline arithmetic, startup/reconnect recovery, Web projection, security/privacy and cleanup evidence。
- Confirm all Deferred states/capabilities remain absent and documentation matches actual source。
- Independent verdict must be `PASS` with no unresolved correctness、security/privacy、migration/API compatibility or material-rework finding before P1-3 becomes `DONE`。

## Validation strategy for implementation phases

Use actual project commands at execution time and preserve machine evidence。Expected families:

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

P1-3A is docs-only, so its gate is document consistency、reference/status checks、master-plan hash、changed-file scope、`git diff --check` and Git state；it does not run runtime suites or `gia-review-bundle`。

P1-3B implemented the backend-only foundation and ran risk-matched backend/Web/API-contract/PostgreSQL gates；P1-3C remains responsible for the in-process scheduler/recovery loop and complete Browser phase flow.

## Explicit deferrals

- P1-4 floor scheduling、speaker scoring/selection、nomination、vote and interruption behavior。
- AI candidates、participant/utterance runtime、transcripts and text generation loop。
- LLM/provider/model、prompt、model invocation、fake provider and LangGraph。
- Structured memory、summary compression and discussion semantic decisions。
- Report/scoring/evidence/objective metrics/drills and report lifecycle implementation。
- Redis、queue/worker、distributed scheduler、cross-process broadcast and multi-worker fan-out。
- Voice、microphone、`DEVICE_CHECK`、ASR/TTS/audio and playback interruption。
- Full `PAUSED_NETWORK` / `PAUSED_SYSTEM` / `FAILED_SERVICE` / `COMPLETED_PARTIAL` engine。
- Payment/entitlement/growth/industry packs、CMS expansion and public identity expansion。

## Decisions and blockers

- No new Accepted or Proposed ADR is required。The frozen model is a scoped implementation design derived from the master plan and Accepted ADRs；it does not change product direction or infrastructure strategy。
- Exact product duration values and future mode-specific profiles remain configuration/content calibration, not state-machine constants。P1-3B must expose a typed server-owned configuration boundary and tests, but P1-3A does not invent long-term beginner/standard/stress values。
- No blocker was found at P1-3A closeout。

## Risks and stop conditions

- **BLOCKER — authority/baseline conflict**：higher-authority conflict, overlapping unknown user changes or changed migration baseline stops implementation；never reset/restore/clean/stash。
- **HIGH — dual authority**：Browser-computed expiry, process-memory-only phase or local state overwrite blocks P1-3。
- **HIGH — timing drift**：resetting deadline on reload/reconnect/restart or using callback execution time as recovered phase start blocks P1-3。
- **HIGH — race/partial commit**：unlocked transition、duplicate phase event、event-before-commit、state/timing/event partial transaction or action replay drift blocks P1-3。
- **HIGH — contract history**：silently reinterpreting/replacing stored event v1 or rejecting historical catch-up blocks P1-3。
- **MEDIUM — duration scope**：hard-coding future product modes into transition rules or accepting Browser duration input must be corrected。
- **SCOPE STOP**：P1-4 scheduling、provider/LLM、participant/utterance、memory/report、voice/pause engine、Redis/queue or new dependency requires separate approval。

## Progress

- [x] User explicitly approved P1-3 and P1-3A docs-only design freeze。
- [x] Committed `main`、clean working tree、P1-1/P1-2 actual source and immutable master-plan hash verified。
- [x] V0.1 path、terminal/Deferred states and exact legal transition matrix frozen。
- [x] Durable timing plan/current deadline、server UTC arithmetic、restart/reconnect and in-process-timer correctness boundary frozen。
- [x] User/system command split、action/sequence/transaction semantics、v1 history + v2 event vocabulary and authoritative snapshot frozen。
- [x] P1-3B～D scope、acceptance、validation、risks and explicit deferrals frozen。
- [x] No Proposed Decision or blocker found；P1-3A completed docs-only。
- [x] P1-3B backend state machine + durable phase foundation completed。
- [ ] P1-3C not started / awaiting explicit approval。
- [ ] P1-3D not started / awaiting explicit approval。
