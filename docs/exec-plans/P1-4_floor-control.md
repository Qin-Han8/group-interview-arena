# P1-4 Floor Control / Speaker Scheduling Execution Plan

Status: `P1 IN_PROGRESS`; `P1-4 DONE`; `P1-4A completed`; `P1-4B completed`; `P1-4C completed`; `P1-4D completed`; `P1-4E completed`; final independent verdict `PASS`; `P1-5 NOT_STARTED / awaiting explicit approval`

Target version: `V0.1 Internal Validation`

Product baseline: [`PROJECT_MASTER_PLAN.md`](../PROJECT_MASTER_PLAN.md)

Accepted decisions: [`D-003`](../DECISIONS.md#2-已确认产品决策索引), [`D-007`](../DECISIONS.md#2-已确认产品决策索引), [`D-008`](../DECISIONS.md#2-已确认产品决策索引), [`D-013`](../DECISIONS.md#2-已确认产品决策索引), [`ADR-003`](../DECISIONS.md#adr-003--fastapi-作为主要业务后端), [`ADR-005`](../DECISIONS.md#adr-005--postgresqlsqlalchemy-与-alembic-数据基线), [`ADR-006`](../DECISIONS.md#adr-006--rest-与-websocket-通信边界), [`ADR-007`](../DECISIONS.md#adr-007--api-契约生成策略), [`ADR-008`](../DECISIONS.md#adr-008--redis-延后运行), [`ADR-009`](../DECISIONS.md#adr-009--独立后台任务队列延后), [`ADR-011`](../DECISIONS.md#adr-011--轻量领域导向混合模块架构), [`ADR-012`](../DECISIONS.md#adr-012--分阶段测试与质量工具策略), [`ADR-013`](../DECISIONS.md#adr-013--配置错误与结构化日志基线), [`ADR-014`](../DECISIONS.md#adr-014--provider-neutral-ai-与自定义讨论编排), [`ADR-015`](../DECISIONS.md#adr-015--initial-identity-and-browser-session-boundary)

P1-4A baseline: committed `main` at `0fdf2c0034737044efcd986b1915fabe81f8a56c` (`P1-3D: docs: complete session state machine phase`); [`PROJECT_MASTER_PLAN.md`](../PROJECT_MASTER_PLAN.md) SHA-256 `2388A9660320406CB35D5354126AD71C6849A98DB7C4A356796CA951BF372F26`

P1-4B baseline: clean committed `main` at `100646c9d547521fb8fc67430385ebe27572f5c5` (`P1-4A: docs: freeze floor control design`), equal to `origin/main`; master-plan SHA-256 unchanged

P1-4D baseline: clean committed `main` at `5a738255d74e1c8534ae84d0eae926b52b8d2f3f` (`P1-4C: feat: add deterministic floor scheduler`), equal to `origin/main`; master-plan SHA-256 unchanged

## Goal

冻结 V0.1 floor control 的领域语言、权威边界、确定性选择规则、最小事件、解释性和持久化边界，使后续实现能够回答“当前谁拥有发言权、为什么选中该参与者、何时需要系统干预”，同时保持 P1-3 phase lifecycle、私有信息隔离和未来真人参与者兼容。

P1-4 只决定“谁应该说”，不决定“说什么”。Scheduler 是 project-owned deterministic domain logic；未来 LLM/provider 只能在已有 floor grant 之后为获准 AI 参与者生成内容，不能决定 phase transition、floor owner 或 scheduler policy。

## Context and authority

- P1-1 已提供 server-authoritative session aggregate、durable action identity、locked transaction、monotonic sequence、formal event log 和 snapshot + ordered-event recovery。
- P1-2 已提供 immutable question-version-specific Persona Assignment / Private Stance；这些数据保持 server-only，且不是 V0.1 scheduler input。
- P1-3 已实现 phase path、durable deadline 和 automatic phase transition。Floor control 必须消费 P1-3 phase truth，不能修改、延长、暂停或推进 phase。
- 总纲要求半实时受控轮次、由讨论引擎调度发言权，并要求角色行为差异；P1-4A 将可复现 floor correctness 与后续语言生成分离，不以 prompt 或模型输出代替调度器。
- P1-4A 开始时不存在 participant、floor、utterance 或 scheduler persistence/runtime；本子阶段不得用文档之外的占位实现提前创建它们。

## Five-stage decomposition

1. **P1-4A — Floor control design freeze**：`completed`。Docs-only 冻结领域模型、phase/floor authority、V0.1 deterministic policy、human compatibility、events、explainability、persistence、B～E scope 和 acceptance。
2. **P1-4B — Scheduling persistence + domain foundation**：`completed`。已建立通用 participant、speaking opportunity、current floor、decision/audit facts 的最小 persistence/domain 基础与 migration；未实现自动 speaker selection engine、Realtime/Web 或 LLM。
3. **P1-4C — Deterministic scheduler engine**：`completed`。已实现 pure deterministic candidate construction/ranking、fairness、monopoly guard、phase policy、silence/deadline intervention、transactional decision → grant/intervention 与 deterministic regressions；不生成 utterance。
4. **P1-4D — Realtime/Web floor experience**：`completed`。已在既有 ordered session channel 上实现 floor events/safe snapshot projection、Browser current-speaker/lifecycle UI 和真实 PostgreSQL Chromium recovery flow；Browser 不拥有 scheduler，且本轮明确不增加 floor inbound commands。
5. **P1-4E — Independent acceptance + closeout**：`completed`。从 committed source 独立复核 persistence、determinism、race/recovery、phase integration、human compatibility、explainability/non-disclosure、Realtime/Web 和 Deferred absence；唯一 documentation finding 修复后 full recheck final verdict `PASS`，P1-4 已为 `DONE`。

P1-4A～E 已分别获得明确批准并完成；P1-4 final independent verdict 为 `PASS`。P1-5、LLM/utterance、memory、scoring/report、Redis/queue、voice 或下一阶段实现仍须单独明确批准。

## Frozen floor ownership model

### Authority and lifecycle

- Session phase controls the discussion lifecycle. P1-3 remains the only authority for starting, advancing, completing or aborting phases.
- Floor control operates only within the authoritative current phase. It may grant or release a within-phase speaking turn, or request an intervention; it never mutates session phase or phase timing.
- `CREATED`、`PREPARATION`、`COMPLETED` 和 `ABORTED_USER` have no active floor. V0.1 floor-enabled phases are `OPENING_STATEMENTS`、`EXPLORATION`、`CONFLICT_AND_EVALUATION`、`CONVERGENCE` and `FINAL_SUMMARY`.
- A session has zero or one current floor owner. Ownership is server-authoritative and references a session participant, never a persona template, browser connection, provider invocation or free-form display name.
- A phase transition invalidates the previous phase's open opportunity/candidate calculation and requires any current floor to be released with a safe phase-change reason. The phase transition remains the cause of lifecycle change; floor cleanup cannot delay or veto it.

### Domain terms

- **Participant**：a session-scoped actor eligible for discussion participation. The model is not AI-only: actor kind is `AI`、`HUMAN` or `SYSTEM`, while participation role distinguishes `CANDIDATE` from `MODERATOR`. An AI or human candidate can own ordinary floor; a system/moderator participant can own floor only through an intervention policy.
- **Current floor owner**：the participant holding the single active speaking right for the session and phase, or null. A grant has a stable identity and phase association so release/recovery cannot apply to the wrong turn.
- **Speaking opportunity**：a normalized, session-scoped request or obligation to be considered for floor, such as a human request, nomination, phase-mandated opening/final turn or scheduler-created fairness opportunity. It expresses eligibility/intent, not speech content and not an automatic grant.
- **Candidate speaker**：an ephemeral scheduler view of one available, eligible participant plus safe policy facts derived from current phase, open opportunities and prior floor history. It is runtime calculation, not a durable identity or public event.
- **Scheduler decision**：the deterministic causal result for one evaluation: grant a candidate, request intervention, or make no grant. It records policy version, reason code and safe input/audit metadata. A decision is a cause; it is not itself the fact that the floor changed.
- **Intervention**：a scheduler-requested moderator/system action caused by silence, no eligible candidate or an approaching phase deadline. It is control-plane behavior, not generated speech. A later, separately authorized handler may grant floor to a moderator/system participant or display a non-content notice.

### Content separation

```text
authoritative phase + availability + floor history + fairness + policy
  -> deterministic scheduler decision: who should speak
  -> durable floor fact
  -> future utterance generation: what the granted AI says
```

- Scheduler never returns prompt text, stance, argument, utterance, token stream or provider request.
- Future LLM/provider output cannot retroactively justify, replace or mutate a floor decision.
- Human speech needs no LLM caller. AI speech generation may fail or be interrupted without changing who made the original floor decision; release/failure handling is a separate deterministic control operation.

## Frozen deterministic orchestration boundary

### Inputs

The scheduler receives only validated project-owned facts:

- authoritative current phase context from P1-3, including server phase deadline where timing policy needs it；
- session participant roster and current availability/eligibility；
- open speaking opportunities；
- previous durable floor grant/release history；
- fairness state deterministically derived from that history；
- closed, versioned configured policy and injected server UTC clock for silence/deadline evaluation。

Persona parameters、Private Stance、hidden question calibration、prompt text、LLM output、provider score and Browser-computed rank are not inputs to the V0.1 scheduler.

### Output

The scheduler emits one closed decision result:

- `GRANT(participant_id, opportunity_id?, reason_code, metadata)`；
- `REQUEST_INTERVENTION(intervention_kind, reason_code, metadata)`；
- `NO_GRANT(reason_code, metadata)`。

The application layer validates current aggregate preconditions and persists the resulting decision/fact atomically. The pure scheduler does not perform database, network, WebSocket, provider or clock I/O.

### Prohibitions

- LLM/model output cannot select next phase, advance state or own a timer.
- Prompt content cannot define, override or dynamically rewrite scheduler policy.
- Persona/agent personality cannot directly add priority, change fairness counters or assign floor.
- Browser cannot submit winner, rank, fairness state, reason code, deadline or current owner.
- No complex ML ranking, embeddings, semantic relevance model, multi-agent vote/negotiation or stochastic tie-break is permitted in V0.1.

## Frozen V0.1 deterministic policy

Candidate selection is a closed lexicographic policy, not a weighted model score. For the same validated input and policy version it must return the same result.

1. **Eligibility gate**：exclude unavailable participants, the wrong participation role, participants disallowed in the current phase and any participant already owning floor. Ordinary selection includes candidate-role AI and human participants; moderator/system enters only through intervention.
2. **Opportunity class**：consider phase-mandated opportunity, accepted explicit request/nomination and fairness-created opportunity according to a closed configured class order. Policy configuration may choose the order but cannot inject code or model output.
3. **First-opportunity priority**：within the applicable class, a candidate with no floor grant in the current phase precedes a candidate already granted floor.
4. **Monopoly guard**：the previous owner cannot receive a consecutive new grant while another available eligible candidate with an unmet current-phase opportunity exists. Consecutive-grant and per-phase caps are positive-integer policy values and are enforced identically for AI and humans unless a moderator intervention is active.
5. **Phase-aware order**：`OPENING_STATEMENTS` and `FINAL_SUMMARY` honor their phase-mandated eligible order; discussion phases use unmet opportunity, fewer current-phase grants, then longest time/most grants elapsed since last floor. `CONVERGENCE` may prioritize an already-open summary/decision opportunity but cannot infer content quality.
6. **Stable tie-break**：remaining ties use stable session participant slot/order, then participant UUID as the final deterministic key. Database row order, arrival race, random number and provider latency are never tie-breakers.
7. **Silence/deadline intervention**：when no ordinary grant is possible for a configured silence threshold, or remaining authoritative phase time crosses a configured intervention threshold, return an explainable intervention request. Phase expiry itself is still handled by P1-3 and always takes precedence over creating a late grant.

Minimum safe policy reason codes are `PHASE_MANDATED_TURN`、`EXPLICIT_OPPORTUNITY`、`FIRST_OPPORTUNITY`、`FAIRNESS_RECOVERY`、`MONOPOLY_PREVENTION`、`PHASE_SUMMARY_OPPORTUNITY`、`SILENCE_RECOVERY`、`DEADLINE_RECOVERY` and `NO_ELIGIBLE_PARTICIPANT`. P1-4B/C may narrow names before persistence only if this plan is first updated without changing their semantics.

Policy parameters are typed, closed and server-owned. They may configure positive durations/caps and class ordering; they cannot contain executable expressions, prompts, persona-specific overrides or hidden scoring weights.

## Frozen event boundary

The minimum new formal event vocabulary is exactly:

- `floor.granted`：fact that a specified participant acquired floor for the current phase/grant identity；
- `floor.released`：fact that the exact current grant ended, with a closed safe release reason；
- `floor.intervention_requested`：fact that the scheduler requested a typed moderator/system intervention。

Events are facts. Scheduler decision is the persisted/auditable cause referenced by the fact. Any future LLM output or utterance is later content and must use a separate, subsequently approved contract.

- A hand raise, candidate calculation, score component, timer tick and provider “thinking” state are not formal events in P1-4 unless a later real caller proves a recovery need and the plan is updated first.
- Ownership replacement is ordered release then grant under one locked transaction; event sequences remain contiguous and commit before send.
- Duplicate/stale/concurrent evaluation must not create two current owners or two grants for the same opportunity.
- P1-4 event payloads expose participant/grant/phase identity and safe reason metadata only. They never include private stance, persona parameters, prompt, generated content or internal scoring.

## Frozen explainability and audit boundary

Every grant/intervention decision must retain enough safe evidence to answer “为什么让 Agent B / this participant 发言？” without reconstructing hidden model state:

- decision identity and policy version；
- outcome kind and selected participant/opportunity where applicable；
- closed primary reason code and optional ordered supporting reason codes；
- current phase and decision timestamp；
- safe fairness facts such as current-phase grant count, whether first opportunity was unmet, previous-owner/consecutive-grant status and stable tie-break key class；
- causally linked formal event identity/sequence。

Public/Browser explanation is a purpose-built allowlist and may use user-facing reason text derived from safe reason codes. Internal audit may retain the same safe structured facts plus validated availability/opportunity references. Neither surface may contain or permit inference of:

- Private Stance, hidden information, red lines or concession conditions；
- hidden persona calibration or raw persona numeric parameters；
- scoring rubric, user score, future evaluation features or “quality” ranking；
- prompt, chain-of-thought, provider logprob/model score or generated-but-unspoken content。

Explainability is policy evidence, not a dump of all scheduler internals. No opaque weighted score is required for V0.1.

## Frozen persistence boundary

P1-4A creates no migration. P1-4B may propose the minimal relational representation needed for these durable facts:

- session-scoped participant identity, actor kind, participation role, stable slot/order and current availability lifecycle；
- speaking opportunities that must survive retry/restart or represent accepted external intent/phase obligation；
- the single current floor grant/owner with phase and grant identity；
- immutable scheduler decision/audit records with policy version and safe reason metadata；
- floor grant/release/intervention facts linked to the existing ordered `discussion_events` sequence。

Runtime-only calculations are not persisted as canonical data:

- candidate speaker objects and sorted candidate lists；
- recomputable fairness counters/ages derived from durable floor history；
- transient timers/wake-up tasks；
- rejected alternatives, raw ranking vectors or duplicated event projections。

Future scoring may consume observable durable facts such as grant/release timing, speaking opportunity response, interruption/release reason, turn distribution and phase association. It cannot treat scheduler reason as a user ability score, and P1-4 does not implement scoring or report output.

Snapshot/restart recovery must be able to reconstruct exactly one current owner and deterministic fairness inputs from durable state. If a proposed P1-4B schema cannot do that without process memory, implementation must stop and update the design before migration.

## Timing and P1-3 integration

- P1-3 phase status/deadline is read-only input to floor control. Floor control cannot update `simulation_sessions.status`、`phase_started_at`、`phase_deadline_at` or `phase_duration_plan`.
- Scheduler uses injected server UTC only to compare safe silence/intervention thresholds with the authoritative P1-3 deadline. Browser clocks and local countdown are display-only.
- A phase transition/abort/completion wins over stale floor evaluation. Under the aggregate lock, stale phase/grant preconditions cause no grant.
- At phase change, floor cleanup and any new phase-mandated opportunities may be persisted atomically with ordered facts, but scheduler cannot delay the already-due transition or add phase time.
- `PREPARATION` produces no visible floor. Future background stance preparation remains outside floor ownership and outside P1-4.

## P1-4B — Scheduling persistence + domain foundation

### Scope

- Add the minimal generalized participant/floor/opportunity/decision persistence on the current linear Alembic head; preserve historical revisions byte-for-byte.
- Add pure closed domain types/invariants for actor kind, participation role, availability, opportunity, current grant, decision outcome/reason and policy version.
- Establish exact-one-current-owner, phase/grant identity, immutable audit causation and restart reconstruction guarantees with real PostgreSQL tests.
- Integrate only the minimum session-bound roster initialization required by the existing immutable three-slot assignment and authenticated human owner; system/moderator representation must be supported without making it an ordinary candidate.
- Reuse P1-1 session aggregate locking/sequence/transaction patterns; do not create an event bus, repository/interface/factory empty layer or Redis/queue adapter.

### Acceptance

- Schema/domain supports AI, human and moderator/system participants without AI-only foreign keys or enum assumptions.
- At most one current grant exists per session; wrong-phase, wrong-grant, stale and duplicate release/grant operations fail closed or replay deterministically.
- Durable history reconstructs current floor and fairness inputs after restart; private stance/persona calibration does not enter floor tables, events, API, logs or errors.
- Migration fresh/repeat/downgrade/re-upgrade, exact catalog, rollback and concurrency tests pass on disposable PostgreSQL.
- No automatic scheduler, Browser floor UI, LLM/provider, utterance, scoring, memory, Redis/queue or voice implementation exists.

## P1-4C — Deterministic scheduler engine

### Scope

- Implement pure candidate eligibility and the exact lexicographic V0.1 policy with typed closed configuration, injected UTC and stable tie-break.
- Implement fairness reconstruction, first-opportunity priority, monopoly guard, phase-aware order and silence/deadline intervention.
- Apply decisions through the locked session aggregate with exact phase/current-grant preconditions, atomic decision + formal events, contiguous sequence and commit-before-send.
- Add deterministic table-driven/property-style regressions plus real PostgreSQL race, retry, rollback, restart and phase-boundary tests.

### Acceptance

- Identical inputs/policy return byte-equivalent outcome semantics; shuffled database/input enumeration cannot change the winner.
- No eligible participant is starved while an already-granted participant repeats; consecutive/per-phase caps and stable tie-break are proven.
- Phase transition vs grant, duplicate scheduler calls, concurrent opportunity requests and release/regrant races produce one valid durable outcome.
- Every grant/intervention has a safe auditable reason; private/persona/scoring/provider inputs are absent.
- No utterance generation, LLM/provider, semantic/ML ranking, Redis/queue or multi-agent negotiation is introduced.

### P1-4C implementation checkpoint

- Baseline: clean committed `main` at `d6a6861ebc061d95303eda25254e55a5be875863`, equal to `origin/main`; master-plan SHA-256 unchanged from P1-4A/B.
- Pure scheduler uses closed `v0.1-floor-1` typed policy, injected aware UTC and explicitly sorted durable inputs. It filters ordinary AI/human candidates by role/availability, classifies open opportunity or fairness fallback, applies first-opportunity and monopoly rules, uses phase-specific fairness order, then stable seat/UUID tie-break.
- Deadline pressure wins before a new grant；when caps leave no ordinary grant, configured silence can request intervention；an empty ordinary roster requests `NO_ELIGIBLE_PARTICIPANT`. Each outcome carries only the frozen safe reason/metadata allowlist.
- Internal `floor.schedule` evaluation runs after P1-3 overdue reconciliation and inside the existing owner-authorized session row lock. It verifies phase、sequence and current-grant preconditions, reconstructs history after locking, and atomically persists action digest、decision、grant/intervention and at most one ordered formal event. Duplicate calls replay；digest conflicts and stale/concurrent calls fail closed.
- No schema/migration、dependency/lockfile、public REST/OpenAPI、WebSocket inbound command、snapshot field or Web UI changed. P1-4D remains separately gated.

## P1-4D — Realtime/Web floor experience

### Scope

- Extend the existing versioned session channel with the three frozen formal floor event types and compatible strict Web parsing.
- Add the minimum owner-authorized client intent needed for human speaking opportunity/release/interrupt flow only after exact command vocabulary is documented; client never selects the winner.
- The explicit P1-4D approval narrowed this vertical slice to display-only server facts, so the conditional client-intent item above did not trigger and no floor inbound command was added.
- Add authoritative floor snapshot fields or a purpose-built owner-only load boundary sufficient for reload/gap/reconnect recovery.
- Render current speaker, safe pending intent and safe reason explanation in Web; keep pending action identity in memory and reuse existing bounded reconnect/gap recovery.
- Validate a complete AI/human/system-compatible floor flow with real Next/Chromium/Uvicorn/PostgreSQL infrastructure and safe cleanup.

### Acceptance

- Browser reload/reconnect recovers the same current grant, sequence and safe explanation from server truth; stale socket/browser timer cannot assign or release floor.
- Commands retain stable action identity and owner authorization; duplicate/lost-send replay has one durable outcome.
- Private stance, persona parameters, scheduler internals and future generated text do not cross API/WS/log/trace/error surfaces.
- No LLM/provider, utterance generation, scoring/report, memory, Redis/queue, voice or human audio/video enters the vertical slice.

## P1-4E — Independent acceptance + closeout

Independently review committed P1-4A～D source and rerun required governance, migration/catalog, pure deterministic policy, PostgreSQL concurrency/recovery, API/WS contract, Web quality, Chromium, privacy/non-disclosure and cleanup gates. Acceptance must explicitly verify the phase/floor authority split, single-owner invariant, human/system compatibility, explainable safe audit trail and Deferred absence.

Only an independent `PASS` may mark P1-4/P1-4E `DONE`. P1-5 or any memory/LLM/utterance/report task remains separately gated.

## Explicit deferred scope

P1-4 does not implement or prebuild:

- LLM/provider selection or adapter；
- prompt orchestration or prompt-authored scheduler rules；
- utterance/text generation or streaming；
- scoring、evidence evaluation or report；
- structured discussion memory or context compression；
- Redis、distributed scheduler、event bus or task queue；
- complex ML/semantic ranking or embedding；
- multi-agent negotiation/voting to choose the speaker；
- voice、ASR、TTS、audio interruption pipeline；
- emotion、face、camera or video detection；
- human audio/video or multi-human room runtime。

## Validation strategy

### P1-4A docs-only gates

- changed-file scope contains only the six approved docs；
- Markdown relative links resolve and anchors used by the new plan exist；
- `TASKS.md`、`ROADMAP.md`、`ARCHITECTURE.md`、`API.md`、`AGENT_BEHAVIOR.md` and this plan agree on P1/P1-4/P1-4A/P1-4B status；
- floor/phase、decision/event/content、durable/runtime and public/private boundaries are consistent；
- `git diff --check` passes；all changed Markdown files have a final newline and no trailing whitespace；
- no runtime、test、schema/migration、dependency/lockfile、CI or Accepted ADR change。

### Later implementation gates

- P1-4B: pure domain + exact PostgreSQL catalog/migration/concurrency/restart/non-disclosure gates；
- P1-4C: deterministic scheduler regressions, enumeration-order invariance, fairness/monopoly/phase/intervention and transactional race gates；
- P1-4D: API/WS derivative checks, Web lint/format/typecheck/unit/build, real PostgreSQL Chromium E2E and cleanup；
- P1-4E: independent actual-source rerun of all relevant gates from committed source。

## Decisions

- No new Accepted or Proposed ADR is required. This design specializes existing D-008/ADR-014 within the approved P1-4 task and does not change the master plan.
- V0.1 uses deterministic lexicographic scheduling rather than ML/LLM ranking.
- Participant identity is generalized for AI/human/system actors; ordinary floor and moderator intervention remain distinct roles.
- Scheduler reasons are safe policy facts; hidden persona/private stance/scoring information is excluded even from explanation metadata.

## Risks and stop conditions

- **Phase authority drift**：stop if floor implementation needs to change, pause or extend P1-3 phase timing/state.
- **AI-only schema**：stop if participant/floor persistence cannot represent human candidate and moderator/system roles without replacement migration.
- **Private leakage**：stop if fairness/explanation appears to require Private Stance, persona calibration, prompt or scoring data.
- **Non-determinism**：stop if winner depends on database enumeration, process timing, random choice or provider result.
- **Infrastructure expansion**：stop if implementation claims Redis/queue/distributed coordination is required; present the concrete trigger for approval instead.
- **Event inflation**：stop and update the plan before adding formal event types beyond the frozen three.
- **Deferred dependency**：stop before implementing LLM, utterance, memory, scoring/report, voice or multi-agent negotiation.

## Progress

- P1-4A：completed；docs-only floor-control design freeze；validation `PASS`；no blocker。
- P1-4B：completed；linear migration `f1a14b15c004`、participant/floor persistence、internal command lifecycle、durable audit、phase integration and required validation `PASS`；no blocker。
- P1-4C：completed；deterministic scheduler、locked transactional orchestration and required validation `PASS`；no blocker。
- P1-4D：completed；safe REST/WS/Web floor projection and recovery validation `PASS`；no blocker。
- P1-4E：completed；initial review `BLOCKED` on one Low documentation finding，修复后 full independent recheck final verdict `PASS`；no blocker。

### P1-4B implementation record

- Added six product tables (`session_participants`、`speaking_opportunities`、`floor_decisions`、`floor_grants`、`floor_releases`、`floor_interventions`), history indexes, a safe-metadata database check and the session-scoped nullable current-grant reference without rewriting prior revisions；bound existing sessions receive a four-seat roster backfill.
- API-created sessions now atomically materialize one human candidate and three AI candidates；schema supports future system moderators without an AI-only list or full participant runtime.
- Added closed domain types and an internal floor command service for grant、release and intervention. It reuses P1-1 owner authorization、action UUID + semantic digest replay/conflict、aggregate row lock、contiguous formal-event sequence and atomic rollback.
- Grant eligibility、single current owner、wrong-grant/stale decision rejection、terminal protection、phase-change/abort release ordering and durable immutable audit history are implemented. P1-3 remains the only status/timing authority.
- Decision metadata and the three v1 floor event payloads are strictly allowlisted and omit Private Stance、persona calibration、prompt/provider internals、hidden ranking/weights and scoring data. No public REST/WS command、snapshot field or Browser caller was added.
- Migration downgrade/re-upgrade/catalog check、domain/contract/model tests、real PostgreSQL concurrency/idempotency/rollback/cascade tests、P1-1/P1-3 regressions、OpenAPI drift and repository quality gates passed. No new ADR、dependency or lockfile change.

### P1-4D implementation record

- Additively extended the owner-only session snapshot with a safe generalized participant directory, zero-or-one current grant and latest allowlisted floor lifecycle projection. Snapshot fields omit decision metadata、policy internals、ranking/weights、Private Stance/persona、prompt/provider and scoring data.
- Reused the existing v1 floor formal events, single session WebSocket channel and discussion sequence. Strict Web parsing rejects unknown/extra fields；the existing exact-next sequence、duplicate suppression、gap reload、bounded reconnect and stale-generation guard apply unchanged.
- Added display-only current owner、granted/released/intervention lifecycle and user-facing safe reason text. Browser sends no floor command and cannot schedule、grant、release、alter phase or alter deadline.
- Real PostgreSQL tests cover live WS delivery、owner-only snapshot equivalence and reconnect catch-up；Chromium covers phase entry → scheduler grant → live event → reload → API restart/reconnect → authoritative restore → phase-change release. Existing P1-1/P1-3/P1-4B/C regressions remain green.
- No migration、dependency、lockfile、second realtime channel/protocol or Accepted ADR was added. All explicit Deferred scope remains absent.

### P1-4E independent acceptance record

- Initial independent review from clean committed `main` HEAD `170be9562c6e7dd3a833613ebf5ea4a53a354285` stopped on one Low documentation mismatch: `ARCHITECTURE.md` still named P1-4C as the most recently completed task。
- Committed HEAD `e261bc7667366dd863671c6f8a31e4466424a16a` changed only that current-state line to P1-4D；master-plan SHA-256 remained `2388A9660320406CB35D5354126AD71C6849A98DB7C4A356796CA951BF372F26`。
- Full independent recheck passed API `377` tests、real PostgreSQL migration/catalog/concurrency/recovery、Ruff/format/Pyright、Alembic head/current/check、Web `57` tests、lint/format/typecheck/build、current-source OpenAPI drift and Chromium `2` tests；development database state was preserved and temporary databases/ports were clean。
- Final findings：none。P1-4E completed，P1-4 `DONE`，P1 remains `IN_PROGRESS`，P1-5 `NOT_STARTED` / awaiting explicit approval。

Next governance-approved action: review the P1-4 docs-only closeout diff；P1-5 remains `NOT_STARTED` and requires explicit user approval.
