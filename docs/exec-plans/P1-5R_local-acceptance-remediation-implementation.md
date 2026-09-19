# P1-5R Local Acceptance Remediation — Detailed Implementation Plan

Status: P1 = DONE / CLOSED; P1-5 = DONE; P1-5R = CLOSED

Batch status: R1 = DONE; R2-A = DONE; R2-B = DONE; R3 = DONE; Historical Final Composition Acceptance = PASS / DONE; Historical Independent Acceptance = PASS; Previous P1-5R closeout = PASS / CLOSED; Later post-closeout real-provider smoke = EXECUTED / DEFECT_EXPOSED; Formal R3.8 = NOT_EXECUTED / REQUIRES_SEPARATE_EXPLICIT_USER_AUTHORIZATION; No further real-provider call; Remediation actual-source review = PASS; Accepted commit = 3b09d20a704c0fd3ff473ccb79311065b7e70408; Exact CI = 33257343273 completed / success

Findings: F1 = CLOSED; F2 = CLOSED; Visual fidelity remediation = CLOSED; F3 = CLOSED; P1-5R-IP-001 = CLOSED; P1-5R-POST-001 = CLOSED; P1-5R-POST-REV-001 = CLOSED; Open findings = NONE

Target version: V0.1 Internal Validation

Planning baseline: clean committed main at 043a16ba099736b5fb1d658d72632338aafad8a8, equal to origin/main

Baseline CI: GitHub Actions run 33096712024, completed / success, head SHA 043a16ba099736b5fb1d658d72632338aafad8a8

Immutable product baseline: [PROJECT_MASTER_PLAN.md](../PROJECT_MASTER_PLAN.md), SHA-256 2388a9660320406cb35d5354126ad71c6849a98db7c4a356796ca951bf372f26

Frozen specification: [P1-5R_local-acceptance-remediation.md](P1-5R_local-acceptance-remediation.md)

Unchanged historical authorities: [P1-4_floor-control.md](P1-4_floor-control.md), [P1-5_ai-runtime-foundation.md](P1-5_ai-runtime-foundation.md), [P1-5F-3A_web-discussion-functional-closure.md](P1-5F-3A_web-discussion-functional-closure.md), [P1-5F-3A_web-discussion-functional-closure-implementation.md](P1-5F-3A_web-discussion-functional-closure-implementation.md), [P1-5F-3B_complete-discussion-page-composition.md](P1-5F-3B_complete-discussion-page-composition.md), and [P1-5F-3B_complete-discussion-page-composition-implementation.md](P1-5F-3B_complete-discussion-page-composition-implementation.md).

## Outcome and execution rule

This document freezes an executable implementation plan. It implements no remediation and claims no production, test, acceptance, review, commit, push, or CI completion.

Execution is exactly:

~~~text
R1 implementation and TDD
  -> fresh R1 gates
  -> review bundle
  -> external actual-source review
  -> user commit and push
  -> exact-commit CI green
R2-A through the same sequence
R2-B through the same sequence
R3 through the same sequence
final composition acceptance
  -> committed and CI-green acceptance baseline
  -> independent acceptance
~~~

A normal failing test written before its implementation is expected TDD evidence. A governance block exists only for a frozen-contract, architecture, scope, privacy, or irreducible correctness contradiction. No later batch starts while the prior batch is uncommitted, externally unreviewed, or CI-red. No task requires a micro-commit.

## Repository assessment and narrow architecture decisions

The committed source agrees with the frozen design. The following decisions make the plan executable without changing frozen authorities.

1. The current discussion progression authority is resume_discussion_progression(...) in discussion_sessions/progression.py. It already owns Human release recovery and configured AI drive, so R1 extends this function rather than adding another loop.
2. The current floor checkpoint driver accepts only ReleasedFloorProof and reconstructs sequence/time from current state. Initial phase entry therefore requires one narrow compatibility extension in floor_control/progression.py. Scheduler policy, scheduler.py, floor_control/service.py, ScheduleFloorCommand, and apply_scheduler_command(...) remain unchanged.
3. reconcile_session_deadline(...) already returns the committed list of StoredEvent values. Realtime uses that list directly to decide whether to kick progression after draining; it performs no second status query.
4. SessionPanel remains the sole mounted Web coordinator. R2-A keeps DOM measurement, follow state, and scroll commands there. DiscussionStage only renders the supplied indication and wires supplied callbacks. Transcript merge semantics and the realtime client remain unchanged.
5. The loaded DiscussionWorkspace can supply the complete bounded ancestor chain without changing the unauthenticated/pre-session document flow or auth shell.
6. Prompt publication has an immutable application service, publish_prompt_version(...), but no production seed caller or generalized bootstrap framework. The existing production bootstrap convention is the FastAPI lifespan in app.py: it creates and stores the database session factory, performs durable deadline recovery, then starts the recovery runtime. R3 creates only the focused ai_runtime/seed.py asset/publication function and calls it from that lifespan immediately after the session factory is stored and before recover_due_sessions(...). Publication failure aborts startup before recovery/runtime work. Question/Persona seed remains independently owned and question_personas/seed.py stays unchanged except as an unchanged regression target.
7. Recent public discussion and Persona behavior are pure generation-context concerns. A focused ai_runtime/conversation_context.py keeps selection/label/translation logic out of provider code and out of public transcript authority; runtime.py owns the durable query and assembly.

## Exact batch file maps

### R1

Production files to modify:

- apps/api/src/group_interview_arena_api/modules/discussion_sessions/progression.py — resolve exact phase-entry proof, derive deterministic identities, and add the final progression branch.
- apps/api/src/group_interview_arena_api/modules/floor_control/progression.py — add the narrow initial-phase checkpoint proof/driver while preserving the release-proof driver.
- apps/api/src/group_interview_arena_api/modules/discussion_sessions/realtime.py — use committed reconciliation events for ordered drain-then-kick.

Test files to modify:

- apps/api/tests/integration/test_discussion_progression.py — phase proof, deterministic replay, branch ordering, convergence, Human/AI selection.
- apps/api/tests/integration/test_discussion_session_websocket.py — no-event no-kick and state-change send-before-kick/reconnect ordering.
- apps/api/tests/integration/browser_e2e.py — remove the direct initial-floor helper from the main evidence path while retaining it for isolated tests if still used.
- apps/web/e2e/session.spec.ts — assert natural first and cross-phase grants in the real Browser flow.

Regression-only, unchanged unless a failing assertion proves direct ownership:

- apps/api/tests/integration/test_discussion_session_deadline_recovery.py.

Explicitly unchanged: discussion_sessions/service.py, floor_control/scheduler.py, floor_control/service.py, schema/migrations, REST/OpenAPI, public events, provider code, Web production files.

### R2-A

Production files to modify:

- apps/web/src/features/sessions/discussion-workspace.tsx — bound the loaded viewport and center/support overflow owners.
- apps/web/src/features/sessions/discussion-stage.tsx — make Transcript the sole center long-scroll element and render the return-to-latest affordance.
- apps/web/src/features/sessions/session-panel.tsx — own near-bottom measurement, local new-tail state, recovery-tail policy, and scroll commands.

Test files to modify:

- apps/web/src/features/sessions/discussion-workspace.test.tsx.
- apps/web/src/features/sessions/discussion-stage.test.tsx.
- apps/web/src/features/sessions/session-panel.test.tsx.
- apps/web/e2e/session.spec.ts.
- apps/api/tests/integration/browser_e2e.py only to provide deterministic long public contributions through the existing real Browser/fake-provider path.

Explicitly unchanged: globals.css, auth-panel.tsx, discussion-transcript.ts, Web API/realtime modules, backend production, browser storage, dependencies.

### R2-B

Production files to modify:

- apps/web/src/features/sessions/discussion-workspace.tsx.
- apps/web/src/features/sessions/discussion-stage.tsx.
- apps/web/src/features/sessions/session-progress-panel.tsx.
- apps/web/src/features/sessions/task-brief-panel.tsx.
- apps/web/src/features/sessions/session-presentation.ts.

Test files to modify:

- apps/web/src/features/sessions/discussion-workspace.test.tsx.
- apps/web/src/features/sessions/discussion-stage.test.tsx.
- apps/web/src/features/sessions/session-presentation.test.ts.
- apps/web/src/features/sessions/session-panel.test.tsx only for integrated truthful-state regression.
- apps/web/e2e/session.spec.ts.

Explicitly unchanged: SessionPanel business authority, globals.css, auth-panel.tsx, API/realtime/transcript modules, backend, dependencies, and all public contracts.

### R3

Production files to create:

- apps/api/src/group_interview_arena_api/modules/ai_runtime/conversation_context.py — pure public-discussion selection/rendering and Persona behavior translation.
- apps/api/src/group_interview_arena_api/modules/ai_runtime/seed.py — immutable Prompt Version v2 definition and exact publication wrapper.

Production files to modify:

- apps/api/src/group_interview_arena_api/app.py — invoke the focused Prompt v2 publisher from the existing lifespan after session-factory initialization and before deadline recovery/runtime startup.
- apps/api/src/group_interview_arena_api/modules/ai_runtime/prompting.py — exact ten-variable contract and authorized rendered inputs.
- apps/api/src/group_interview_arena_api/modules/ai_runtime/runtime.py — durable recent-public-context load and authorized context assembly.
- apps/api/src/group_interview_arena_api/modules/ai_runtime/orchestration.py — deterministic highest-valid prompt selection for new requests while preserving existing-request pinning.

Test files to create:

- apps/api/tests/test_ai_runtime_conversation_context.py.
- apps/api/tests/test_ai_runtime_prompt_seed.py.
- apps/api/tests/integration/test_ai_runtime_prompt_bootstrap.py — production-lifespan publication, replay/no-op, conflict fail-closed, and v1 immutability against PostgreSQL.

Test files to modify:

- apps/api/tests/test_ai_runtime_prompting.py.
- apps/api/tests/test_auth_runtime.py — unit-level lifespan call-order and startup-abort contract.
- apps/api/tests/deadline_recovery_test_helpers.py — extend the existing unit-only lifespan isolation seam to stub Prompt publication; it is not publication evidence.
- apps/api/tests/integration/test_ai_runtime_persistence.py.
- apps/api/tests/integration/test_ai_runtime_orchestration.py.
- apps/api/tests/integration/test_ai_runtime_automatic_orchestration.py.
- apps/api/tests/integration/browser_e2e.py and apps/web/e2e/session.spec.ts only for final network-free cross-layer proof after the pure/integration tests are green.

Regression-only unchanged tests include apps/api/tests/test_question_persona_seed.py and provider tests.

Explicitly unchanged: question_personas/seed.py, providers/zhipu.py, DB models/migrations, provider/model/temperature/token/message-role/streaming/thinking configuration, REST/WS/Web contracts.

## Frozen interfaces

### Initial phase checkpoint

floor_control/progression.py adds these server-only contracts:

- InitialPhaseEntryProof: frozen dataclass with phase: SessionStatus, event_sequence: int, occurred_at: datetime, phase_started_at: datetime, and phase_deadline_at: datetime.
- InitialSchedulerCheckpointResult: frozen dataclass with outcome: SchedulerCheckpointOutcome, processed_phase: SessionStatus, phase_entry_sequence: int, identities: SchedulerCheckpointIdentities, and optional next_floor_grant_id, next_participant_id, intervention_id.
- drive_initial_scheduler_checkpoint(session_factory, *, owner_id, session_id, phase_entry, identities, scheduling_policy) -> InitialSchedulerCheckpointResult.

discussion_sessions/progression.py adds:

- _InitialPhaseCheckpointState with ABSENT, EXACT, and INCONSISTENT.
- _initial_phase_entry_checkpoint(session, *, owner_id, aggregate) -> tuple[_InitialPhaseCheckpointState, InitialPhaseEntryProof | None].
- derive_initial_scheduler_identities(*, session_id, phase, phase_entry_sequence) -> SchedulerCheckpointIdentities.

The fixed identity name is initial-phase:{session_id}:{phase.value}:{phase_entry_sequence}, with stable suffixes schedule-action, decision, next-floor-grant, and intervention under a new fixed UUID namespace. The existing UUIDv5-to-UUID4-compatible conversion is reused; uuid4() and connection/wall time are forbidden.

The exact proof query uses DiscussionEvent(session_id, aggregate.last_sequence) only when that row is session.state_changed v2. It requires aggregate status in FLOOR_ENABLED_PHASES, current floor null, event payload keys/values exactly compatible with the state-change contract, payload.status equal to aggregate.status, payload.phase_started_at and payload.phase_deadline_at equal to the aggregate timestamps after canonical UTC serialization, event sequence equal to aggregate.last_sequence, and an aware occurred_at. Missing proof is ABSENT; malformed/mismatched proof is INCONSISTENT. Both return reconciliation-required at the final branch without mutation.

drive_initial_scheduler_checkpoint re-reads and revalidates the same proof before applying the unchanged ScheduleFloorCommand. Its command is exactly:

~~~text
expected_phase = phase_entry.phase
expected_last_sequence = phase_entry.event_sequence
expected_current_floor_grant_id = None
evaluated_at = phase_entry.occurred_at
policy = V0_1_SCHEDULER_POLICY
action/decision/grant/intervention ids = supplied deterministic identities
~~~

It recovers the existing durable action/decision/grant/intervention by those identities, classifies Human/AI/no-grant/intervention/state-change/reconciliation with the existing SchedulerCheckpointOutcome values, and never changes scheduler policy or persistence semantics. ReleasedFloorProof and drive_scheduler_checkpoint(...) retain their existing signatures and behavior.

DiscussionProgressionResult.scheduler_result becomes SchedulerCheckpointResult | InitialSchedulerCheckpointResult | None. Existing callers only inspect outcome/children and require no public contract change.

### Realtime kick decision

realtime.py adds the pure predicate _reconciliation_changed_lifecycle(events: Sequence[StoredEvent]) -> bool. It returns true only when at least one returned event is session.state_changed v2. catchup_committed_events stores the exact list returned by reconcile_session_deadline(...), then calls drain_committed_events(), then calls kick_progression_best_effort() only when the predicate is true. Sending committed truth therefore precedes the kick. The 250ms loop never kicks when reconciliation returns an empty list or only non-state events.

### Transcript presentation state

SessionPanel remains the single owner and adds:

- hasNewTranscriptBelow: boolean React state, initialized false and reset on workspace identity change.
- isTranscriptNearBottom(container) -> boolean using the existing 48px threshold.
- scrollTranscriptToLatest() -> void, using the existing scrollTo({ top: scrollHeight }) fallback and clearing hasNewTranscriptBelow.
- handleTranscriptScroll() -> void, clearing the indicator when the reader manually returns within the threshold.
- hasAppendedConfirmedTail(previous, next) -> boolean, true only when next is a strict sequence/utterance-id-preserving extension of previous.

For a live confirmed event, SessionPanel measures before merge. Near bottom sets the existing follow flag and clears the indicator; away from bottom preserves scrollTop and sets the indicator. For an authoritative recovery bundle, an exact appended tail uses the same rule before canonical replacement. Initial restore and non-prefix authoritative replacement do not claim unread state. No value is persisted.

DiscussionStageProps adds hasNewTranscriptBelow: boolean, onTranscriptScroll: () => void, and onReturnToLatest: () => void. Transcript attaches onScroll to the confirmed-transcript-list and renders one button labelled 回到最新发言 only when the boolean is true. DiscussionStage does not inspect DOM geometry or store follow state.

The exact bounded ancestor chain is:

~~~text
loaded DiscussionWorkspace root: h-dvh max-h-dvh overflow-hidden flex-col
SessionHeader: shrink-0
mobile tab nav and tablet support controls: shrink-0
workspace body/grid: min-h-0 flex-1 overflow-hidden
Task/Progress rails: min-h-0 overflow-y-auto
Discussion surface: h-full min-h-0 overflow-hidden
DiscussionStage: h-full min-h-0 flex-col
participant strip, notices, Composer: shrink-0
Transcript wrapper: min-h-0 flex-1
confirmed-transcript-list: min-h-0 flex-1 overflow-y-auto
~~~

### Recent public discussion

conversation_context.py adds:

- PublicDiscussionUtterance: frozen dataclass containing sequence, participant_id, actor_kind, seat_order, phase, and content.
- select_recent_public_discussion(items, *, max_utterances=6, max_content_codepoints=4000) -> tuple[PublicDiscussionUtterance, ...].
- public_participant_label(item) -> str.
- render_recent_discussion(items) -> str.

Selection receives validated eligible items newest-first. It accepts complete items until six or until the first older item would exceed the remaining content budget, then stops and returns the chosen suffix chronologically. It never skips across the first non-fitting older item and never truncates. If the newest item alone exceeds 4000 code points, it returns empty. len(content) is the Python-code-point measure.

Labels are 你 for Human and AI 候选人 {seat_order} for AI. Actor kind must be HUMAN or AI and seat_order must be a positive source-owned participant seat. Invalid labels fail closed. No Persona display name, IDs, sequence, phase diagnostic, raw event JSON, or metadata is rendered. Each line is label + Chinese colon + exact content; embedded content line breaks remain exact.

runtime.py adds _load_recent_public_discussion(session, *, session_id) -> tuple[PublicDiscussionUtterance, ...]. It queries same-session DiscussionEvent rows for participant.utterance.created newest-first, requires event_version 1, projects them through the existing public-event validator, validates actor/participant/session agreement against SessionParticipant, requires phase in FLOOR_ENABLED_PHASES, then invokes the pure selector. Malformed durable public facts raise GenerationContextError and stop before provider I/O. The selected string is transient and is not written to request metadata, logs, or new tables.

### Persona behavior translation

conversation_context.py also adds:

- UnsignedBehaviorBand with LOW, MEDIUM, HIGH.
- SupportBiasBand with NEGATIVE, NEUTRAL, POSITIVE.
- unsigned_behavior_band(value: Decimal) -> UnsignedBehaviorBand.
- support_bias_band(value: Decimal) -> SupportBiasBand.
- render_persona_behavior(persona: AuthorizedPersonaContext) -> str.

Unsigned mapping is LOW for value <= 0.333, MEDIUM for 0.333 < value < 0.667, HIGH for value >= 0.667. Signed support bias is NEGATIVE below -0.333, NEUTRAL from -0.333 through 0.333 inclusive, and POSITIVE above 0.333. Inputs outside their persisted domains fail closed.

Speech style wording is fixed:

- STRUCTURED: 说话有结构，但保持口语讨论，不写成报告。
- EXPLORATORY: 愿意补充新角度，每轮只推进少量有用内容。
- SUPPORTIVE: 会承接并整合他人观点，但不会无条件赞同。
- DIRECT: 直接且礼貌地表达判断，同时给同伴留出讨论空间。

The remaining lines render in this stable order: approximate average_turn_seconds; initiative; interrupt tendency; cooperation; signed support-user bias; detail focus; summary tendency; stance stability; persuasion threshold; novel-idea rate; time awareness; error rate; off-topic rate. Each unsigned category maps to one fixed low/medium/high participation phrase. Signed NEGATIVE says 较少顺从“你”的观点，但保持建设性且不敌对; NEUTRAL says 对“你”的观点保持平衡判断; POSITIVE says 较愿意支持“你”的合理观点，但必须独立判断，禁止讨好或无条件赞同. Raw numerics and category names are not emitted. Unknown speech_style_code and illegal Decimal values raise PersonaBehaviorError before provider I/O.

### Prompt v2

prompting.py changes PROMPT_VARIABLES to exactly these ten names:

~~~text
session_id
participant_id
floor_grant_id
phase
question_context
persona_context
private_stance
phase_instruction
recent_discussion
persona_behavior
~~~

AuthorizedGenerationContext adds recent_discussion: str and persona_behavior: str. prompt_variables(...) supplies all ten. render_prompt(...) keeps its existing fail-closed closed-vocabulary behavior and byte stability.

ai_runtime/seed.py defines AI_CANDIDATE_TURN_V2 as PromptVersionDefinition with prompt_key AI_CANDIDATE_TURN, version_number 2, purpose_code CANDIDATE_UTTERANCE, id UUID("56000000-0000-4000-8000-000000000002"), created_at datetime(2026, 8, 27, 16, 0, tzinfo=UTC), published_at datetime(2026, 8, 27, 16, 0, tzinfo=UTC), retired_at None, and an immutable template containing all ten variables. In canonical serialized form, both timestamps are 2026-08-27T16:00:00Z (2026-08-28 00:00:00 Asia/Shanghai). seed_ai_runtime_prompt_versions(session_factory) publishes the v2 asset through publish_prompt_version(...) in one owned transaction and returns an exact inserted/no-op result. It never edits or retires v1. A grant before 2026-08-27T16:00:00Z keeps v1 eligible; a grant at or after that instant may select v2 as the highest valid version.

app.py is the one production-reachable caller. Its existing lifespan calls await seed_ai_runtime_prompt_versions(session_factory) immediately after assigning DATABASE_SESSION_FACTORY_STATE_KEY and before await recover_due_sessions(session_factory) and start_deadline_recovery_runtime(session_factory). It neither calls a test helper nor inserts rows directly. Exact replay returns no-op; identity/version drift raises through the immutable publication service and prevents the lifespan from yielding or starting recovery work. No migration, manual SQL, browser trigger, provider I/O, or second generalized seed framework is introduced.

The v2 template fixes these instructions: act as a group-interview candidate, not reporter/moderator/answer generator; advance one or two useful points; use conversational Chinese; no Markdown headings; no report boilerplate; do not restate the whole question; do not solve the whole task in every turn; build, challenge, supplement, ask, or compromise naturally when context exists; follow Persona behavior and approximate speaking duration; apply current phase behavior plus question phase_instruction; keep Private Stance private. Phase behavior is one closed mapping for the five FLOOR_ENABLED_PHASES exactly as frozen in the design.

### Prompt selection and replay

orchestration.py adds _select_effective_prompt_version(session, *, prompt_key, purpose_code, effective_at) -> PromptVersion | None. It filters published_at <= effective_at and retired_at is null or retired_at > effective_at, orders by version_number descending then id ascending as a defensive deterministic tie-break, and selects one. The unique prompt_key/version_number invariant makes the first order authoritative.

drive_single_ai_turn(...) invokes it only when no deterministic LlmGenerationRequest exists. effective_at is grant.granted_at. Existing requests continue to use existing_request.prompt_version_id and existing_request.requested_at exactly; publication or retirement never rebinds them. No valid prompt preserves RECONCILIATION_REQUIRED and zero provider calls.

## Batch R1 — Initial Phase Floor Scheduling

### R1.1 Exact phase-entry proof and deterministic identities

- Files: modify discussion_sessions/progression.py, floor_control/progression.py, and test_discussion_progression.py.
- Responsibility: introduce InitialPhaseEntryProof, resolve the exact current state-change event, derive four identities, and reconstruct one semantic command entirely from durable facts.
- Consumes: SimulationSession, DiscussionEvent, SessionStatus, FLOOR_ENABLED_PHASES, StoredEvent timing/payload, V0_1_SCHEDULER_POLICY.
- Produces: InitialPhaseEntryProof, SchedulerCheckpointIdentities, InitialSchedulerCheckpointResult, and drive_initial_scheduler_checkpoint(...).
- RED first: parameterize test_discussion_progression.py over every FLOOR_ENABLED_PHASES member and assert exact proof, absent event, wrong event version/type/status/timing/sequence, stable frozen UUID bytes, repeated reconstruction equality, and no uuid4/wall-clock semantic input.
- RED command, from apps/api:

~~~powershell
uv run pytest tests/integration/test_discussion_progression.py -q
~~~

- Expected RED: the initial proof types/helpers and driver do not exist; no-floor progression currently returns NO_WORK, and current checkpoint code uses current sequence plus datetime.now(UTC).
- Minimal GREEN: implement only the exact proof/identity/initial-driver contracts above; retain the release-proof path byte-for-byte except shared internal recovery extraction that preserves its behavior.
- GREEN command: uv run pytest tests/integration/test_discussion_progression.py -q from apps/api.
- Regression: uv run pytest tests/integration/test_floor_control_foundation.py tests/integration/test_ai_runtime_automatic_orchestration.py -q.
- Scope gate: git diff --exit-code -- apps/api/src/group_interview_arena_api/modules/floor_control/scheduler.py apps/api/src/group_interview_arena_api/modules/floor_control/service.py apps/api/src/group_interview_arena_api/modules/discussion_sessions/service.py apps/api/migrations.
- Review checkpoint: verify complete ScheduleFloorCommand digest equivalence on replay, no new table, no random/time identity, and fail-closed malformed proof.

### R1.2 Final initial-checkpoint progression branch

- Files: modify discussion_sessions/progression.py and test_discussion_progression.py.
- Responsibility: preserve the exact current Human -> current AI -> Human release -> resumable AI -> initial phase-entry order and map initial scheduler results into existing DiscussionProgressionOutcome values.
- Consumes: _current_floor_kind(...), _latest_human_checkpoint(...), has_resumable_ai_work(...), drive_initial_scheduler_checkpoint(...), _drive_configured(...).
- Produces: one added final branch in resume_discussion_progression(...); NEXT_AI_GRANTED reuses _drive_configured(...), NEXT_HUMAN_GRANTED maps to NEXT_HUMAN_GRANTED, and remaining outcomes map through existing names.
- RED first: natural Human selection, valid AI selection with existing deterministic fixture, repeated call convergence, one floor.schedule action, one FloorDecision, and at most one active FloorGrant.
- RED command: uv run pytest tests/integration/test_discussion_progression.py -q from apps/api.
- Expected RED: no-floor/no-recovery state returns NO_WORK and creates no scheduler action.
- Minimal GREEN: add the final branch only; do not add recursion or another progression loop.
- GREEN command: uv run pytest tests/integration/test_discussion_progression.py -q from apps/api.
- Regression: uv run pytest tests/integration/test_ai_runtime_automatic_orchestration.py tests/integration/test_ai_runtime_continuous_drive.py tests/integration/test_backend_text_discussion_transport.py -q.
- Scope gate: only the two R1.2 files may differ from the R1.1 reviewed state.
- Review checkpoint: confirm Human release wins over AI recovery, AI recovery wins over initial entry, and existing post-release outcomes are unchanged.

### R1.3 Realtime deadline drain-before-kick

- Files: modify discussion_sessions/realtime.py and test_discussion_session_websocket.py.
- Responsibility: use reconcile_session_deadline(...) returned StoredEvent values to conditionally kick after committed event projection/send.
- Consumes: list[StoredEvent], drain_committed_events(), kick_progression_best_effort().
- Produces: _reconciliation_changed_lifecycle(...) and exact reconcile -> drain -> conditional kick ordering.
- RED first: empty reconciliation causes zero progression calls; a deadline state-change is received before the resulting floor.granted; repeated catch-up/reconnect converges on one grant.
- RED command: uv run pytest tests/integration/test_discussion_session_websocket.py -q from apps/api.
- Expected RED: catch-up discards the reconciliation result and never kicks after deadline transition.
- Minimal GREEN: capture the returned list, drain first, then kick only for session.state_changed v2.
- GREEN command: uv run pytest tests/integration/test_discussion_session_websocket.py -q from apps/api.
- Regression: uv run pytest tests/integration/test_discussion_session_deadline_recovery.py tests/integration/test_discussion_progression.py -q.
- Scope gate: no public envelope, command, error, polling interval, or service signature changes.
- Review checkpoint: assert committed lifecycle event sequence is lower than resulting floor.granted and no 250ms unconditional scheduler loop exists.

### R1.4 Natural Browser composition

- Files: modify apps/api/tests/integration/browser_e2e.py and apps/web/e2e/session.spec.ts.
- Responsibility: remove _schedule_browser_floor/_schedule_browser_floor_async from the main acceptance path and observe authoritative natural grants.
- Consumes: real create/start/deadline WebSocket path, fake provider, public floor/session events.
- Produces: Browser evidence create -> start -> preparation deadline -> OPENING_STATEMENTS -> natural floor.granted -> Human/AI continuation, then one speaking deadline -> next speaking phase -> natural first floor.granted.
- RED first: update the main spec to wait for natural grants and assert no harness scheduling signal/call is used.
- RED command, from repository root: pnpm.cmd web:test:e2e.
- Expected RED: the current main harness explicitly invokes the floor helper; without it the first speaking-phase grant is absent.
- Minimal GREEN: remove only the main-path helper invocation and rely on R1 progression; retain helper definitions only if another isolated lower-level test calls them.
- GREEN command: pnpm.cmd web:test:e2e.
- Regression: pnpm.cmd web:test from repository root; from apps/api run uv run pytest tests/integration/test_discussion_progression.py tests/integration/test_discussion_session_websocket.py tests/integration/test_discussion_session_deadline_recovery.py -q.
- Scope gate: git diff --exit-code -- apps/web/src apps/web/package.json package.json pnpm-lock.yaml apps/api/src/group_interview_arena_api/providers.
- Review checkpoint: inspect the test path for zero direct floor service/scheduler calls before both natural grants.

### R1.5 Batch gate and handoff

- Files: no new implementation file; all R1 files above plus minimal current-status docs after implementation.
- Responsibility: close F1 only after evidence, then prepare review without starting R2-A.
- Consumes: all R1 GREEN results.
- Produces: R1 implementation bundle and evidence; F1 CLOSED only after required acceptance.
- RED first: run the full R1 gate while the task tests still fail; this is expected before GREEN.
- RED command: from apps/api run uv run pytest tests/integration/test_discussion_progression.py tests/integration/test_discussion_session_websocket.py tests/integration/test_discussion_session_deadline_recovery.py -q; from repository root run pnpm.cmd web:test:e2e.
- Expected RED: at least the newly written natural initial/cross-phase assertions fail before production changes.
- Minimal GREEN: no extra behavior beyond R1.1–R1.4.
- GREEN commands, from apps/api unless noted:

~~~powershell
uv run ruff check .
uv run ruff format --check .
uv run pyright
uv run pytest tests/integration/test_discussion_progression.py tests/integration/test_discussion_session_websocket.py tests/integration/test_discussion_session_deadline_recovery.py -q
uv run pytest -m "not integration"
uv run pytest -m integration
uv run pytest
~~~

From repository root:

~~~powershell
pnpm.cmd web:format:check
pnpm.cmd web:lint
pnpm.cmd web:typecheck
pnpm.cmd web:test
pnpm.cmd web:build
pnpm.cmd web:test:e2e
git diff --check
~~~

- Regression: from apps/api run uv run alembic heads, uv run alembic current, and uv run alembic check against the established local PostgreSQL environment; from root run pnpm.cmd web:api:check and git diff --exit-code -- apps/web/src/lib/api/generated/schema.d.ts; require temporary DB residue zero and ports 3000/8000 clean.
- Scope gate: exact R1 allowlist only; Master Plan hash unchanged; dependency/lock/schema/generated/provider/Web production diff empty; staged count zero.
- Review checkpoint: run the review-bundle skill in the R1 implementation turn, obtain external actual-source PASS, then user commit/push and exact CI green before R2-A.

## Batch R2-A — Transcript Viewport / Scroll Ownership

### R2-A.1 Loaded-session viewport height ownership

- Files: discussion-workspace.tsx and discussion-workspace.test.tsx.
- Responsibility: apply the exact bounded ancestor chain to loaded workspace only.
- Consumes: existing DiscussionWorkspace props and responsive bands.
- Produces: h-dvh/max-h-dvh/overflow-hidden root, shrink-0 controls, min-h-0/overflow-hidden body.
- RED first: class-contract tests for every named ancestor and unchanged mobile/tablet mount semantics.
- RED command: pnpm.cmd --filter @group-interview-arena/web test -- src/features/sessions/discussion-workspace.test.tsx.
- Expected RED: root is min-h-dvh and center owns overflow-y-auto, so bounded ownership assertions fail.
- Minimal GREEN: change only the named classes; no viewport JavaScript.
- GREEN command: pnpm.cmd --filter @group-interview-arena/web test -- src/features/sessions/discussion-workspace.test.tsx.
- Regression: pnpm.cmd web:typecheck and pnpm.cmd web:test.
- Scope gate: no auth/pre-session/API/realtime change.
- Review checkpoint: inspect DOM chain from loaded root to center surface; no generic class spreading.

### R2-A.2 Transcript sole center long-scroll owner

- Files: discussion-workspace.tsx, discussion-stage.tsx, discussion-workspace.test.tsx, discussion-stage.test.tsx.
- Responsibility: remove overflow scrolling from Discussion surface and keep it only on confirmed-transcript-list.
- Consumes: DiscussionStage flex structure.
- Produces: bounded center shell and one overflow-y-auto transcript list.
- RED first: assert center surface overflow-hidden, stage h-full/min-h-0, fixed regions shrink-0, transcript list flex-1 overflow-y-auto.
- RED command: pnpm.cmd --filter @group-interview-arena/web test -- src/features/sessions/discussion-workspace.test.tsx src/features/sessions/discussion-stage.test.tsx.
- Expected RED: Discussion surface and Transcript list currently both claim scrolling.
- Minimal GREEN: exact class changes only.
- GREEN command: pnpm.cmd --filter @group-interview-arena/web test -- src/features/sessions/discussion-workspace.test.tsx src/features/sessions/discussion-stage.test.tsx.
- Regression: pnpm.cmd web:test.
- Scope gate: discussion-transcript.ts remains unchanged.
- Review checkpoint: browser inspector shows one center vertical scrollbar under long content.

### R2-A.3 Composer stable bottom region

- Files: discussion-stage.tsx and discussion-stage.test.tsx.
- Responsibility: make Composer shrink-0 inside the bounded column; remove sticky as the primary containment mechanism.
- Consumes: existing Composer semantics and showComposer.
- Produces: stable reachable composer without new business state.
- RED first: assert shrink-0, no dependency on document scroll, and existing draft/submit/pending/rejected semantics.
- RED command: pnpm.cmd --filter @group-interview-arena/web test -- src/features/sessions/discussion-stage.test.tsx.
- Expected RED: current Composer is sticky but not explicitly shrink-0.
- Minimal GREEN: class-only containment change.
- GREEN command: pnpm.cmd --filter @group-interview-arena/web test -- src/features/sessions/discussion-stage.test.tsx.
- Regression: pnpm.cmd --filter @group-interview-arena/web test -- src/features/sessions/discussion-stage.test.tsx src/features/sessions/session-panel.test.tsx.
- Scope gate: no send eligibility/content/focus changes.
- Review checkpoint: composer bounding box stays within loaded viewport with long transcript.

### R2-A.4 Near-bottom and new-message local state

- Files: session-panel.tsx, discussion-stage.tsx, session-panel.test.tsx, discussion-stage.test.tsx.
- Responsibility: implement the single-owner interface frozen above for live events and exact recovery tails.
- Consumes: transcriptContainerRef, confirmedTranscript, recovery bundle, existing 48px threshold.
- Produces: hasNewTranscriptBelow and three DiscussionStage props/callbacks.
- RED first: near-bottom follows; away preserves scrollTop and shows indicator; click scrolls/clears; manual return clears; exact recovery tail follows the same rule; storage remains empty.
- RED command: pnpm.cmd --filter @group-interview-arena/web test -- src/features/sessions/discussion-stage.test.tsx src/features/sessions/session-panel.test.tsx.
- Expected RED: there is no indicator state/callback, and recovery unconditionally disables follow.
- Minimal GREEN: implement the frozen SessionPanel owner and presentation-only Stage wiring.
- GREEN command: pnpm.cmd --filter @group-interview-arena/web test -- src/features/sessions/discussion-stage.test.tsx src/features/sessions/session-panel.test.tsx.
- Regression: pnpm.cmd web:test.
- Scope gate: git diff --exit-code -- apps/web/src/features/sessions/discussion-transcript.ts apps/web/src/lib/realtime.
- Review checkpoint: only SessionPanel reads metrics/stores state/commands scroll; indicator is absent from storage and authoritative facts.

### R2-A.5 Long-transcript Browser regression

- Files: session.spec.ts and browser_e2e.py.
- Responsibility: use deterministic long Human/fake-AI public content through existing paths and verify 1440x900, 900x900, and 390x844 containment.
- Consumes: R1 natural flow, real Browser, fake provider, confirmed transcript UI.
- Produces: geometry evidence for bounded body, scrollHeight > clientHeight on transcript, composer inside viewport, support rails usable, history position preserved, return-to-latest behavior, no extra reads/WS/storage.
- RED first: add geometry and interaction assertions before layout changes.
- RED command: pnpm.cmd web:test:e2e.
- Expected RED: document grows or competing scroll owner pushes composer; no return button exists.
- Minimal GREEN: no extra behavior beyond R2-A.1–R2-A.4; harness changes only deterministic content length.
- GREEN command: pnpm.cmd web:test:e2e.
- Regression: pnpm.cmd web:format:check; pnpm.cmd web:lint; pnpm.cmd web:typecheck; pnpm.cmd web:test; pnpm.cmd web:build; pnpm.cmd web:test:e2e.
- Scope gate: no direct DB transcript injection, no manual initial floor, no screenshot oracle, no committed screenshots.
- Review checkpoint: inspect all three viewports and authoritative read/WS counters.

### R2-A batch gate

Run pnpm.cmd install --frozen-lockfile, web:format:check, web:lint, web:typecheck, web:test, web:build, web:api:check against the local API, and web:test:e2e. Require exact R2-A allowlist, backend/API/realtime/transcript semantics/dependencies unchanged, Master Plan hash unchanged, git diff --check, staged zero. Run review bundle, external actual-source review, then user commit/push and exact CI green. F2 closes only on accepted evidence; R2-B remains unstarted until then.

## Batch R2-B — Visual Composition / Product Fidelity

All R2-B commands run from repository root. Each task scope gate permits only its named presentation/test files, forbids fake product state, and preserves the R2-A scroll owner.

### R2-B.1 Training-session header hierarchy

- Files: discussion-workspace.tsx and discussion-workspace.test.tsx.
- Responsibility: compact truthful product/title/phase/countdown/connection/action hierarchy.
- Consumes: SessionHeaderProps only.
- Produces: the existing SessionHeader component with restrained hierarchy and no UUID/sequence/deadline/provider diagnostics.
- RED first: semantic ordering, truthful visibility, diagnostic/forbidden-copy absence.
- RED command: pnpm.cmd --filter @group-interview-arena/web test -- src/features/sessions/discussion-workspace.test.tsx.
- Expected RED: current header hierarchy lacks the frozen studio emphasis assertions.
- Minimal GREEN: typography/spacing/surface classes only.
- Regression: pnpm.cmd --filter @group-interview-arena/web test -- src/features/sessions/session-panel.test.tsx.
- GREEN command: pnpm.cmd --filter @group-interview-arena/web test -- src/features/sessions/discussion-workspace.test.tsx.
- Scope gate: only discussion-workspace.tsx and discussion-workspace.test.tsx may differ for R2-B.1; SessionHeaderProps and visible fact sources remain unchanged.
- Review checkpoint: all visible state traces to existing props.

### R2-B.2 Desktop three-column hierarchy

- Files: discussion-workspace.tsx and discussion-workspace.test.tsx.
- Responsibility: preserve >=1200 simultaneous rails and strengthen center emphasis.
- Consumes: existing three ReactNode surfaces.
- Produces: DiscussionWorkspace with center width greater than each support rail, restrained major-surface depth, and readable rails.
- RED first: exact band/visibility/priority class assertions.
- RED command: pnpm.cmd --filter @group-interview-arena/web test -- src/features/sessions/discussion-workspace.test.tsx.
- Expected RED: current geometry passes basic width but not the frozen hierarchy contract.
- Minimal GREEN: class composition only; no fourth band.
- Regression: pnpm.cmd --filter @group-interview-arena/web test -- src/features/sessions/discussion-workspace.test.tsx src/features/sessions/discussion-stage.test.tsx src/features/sessions/session-panel.test.tsx.
- GREEN command: pnpm.cmd --filter @group-interview-arena/web test -- src/features/sessions/discussion-workspace.test.tsx.
- Scope gate: only discussion-workspace.tsx and its test may differ for R2-B.2; >=1200 remains the sole desktop threshold and R2-A overflow classes remain intact.
- Review checkpoint: no overlay wins at desktop.

### R2-B.3 Participant/current-speaker states

- Files: discussion-stage.tsx, discussion-stage.test.tsx, session-presentation.ts, session-presentation.test.ts.
- Responsibility: make real current speaker clear through text plus restrained visual state.
- Consumes: snapshot participants/currentGrant and existing safe labels.
- Produces: DiscussionStage, safeParticipantLabel(...), participantStatus(...), and session-presentation helpers with Human 你, AI seat labels, 轮到你发言, and truthful AI waiting/current copy.
- RED first: all actor/current/non-current states and private-label absence.
- RED command: pnpm.cmd --filter @group-interview-arena/web test -- src/features/sessions/discussion-stage.test.tsx src/features/sessions/session-presentation.test.ts.
- Expected RED: stronger semantic state attributes/classes are absent.
- Minimal GREEN: presentation helpers/classes only.
- Regression: pnpm.cmd --filter @group-interview-arena/web test -- src/features/sessions/session-panel.test.tsx.
- GREEN command: pnpm.cmd --filter @group-interview-arena/web test -- src/features/sessions/discussion-stage.test.tsx src/features/sessions/session-presentation.test.ts.
- Scope gate: only the four named R2-B.3 source/test files may differ; participant/floor inputs remain snapshot-derived.
- Review checkpoint: no waveform/mic/duration/emotion/confidence/Persona UI.

### R2-B.4 Professional transcript rhythm

- Files: discussion-stage.tsx and discussion-stage.test.tsx.
- Responsibility: one aligned professional contribution list with clear speaker/phase rhythm.
- Consumes: confirmed plain-text utterances.
- Produces: the existing Transcript component with restrained separators/spacing/typography and exact whitespace preserved.
- RED first: aligned list, no bubbles, plain-text Markdown-like content.
- RED command: pnpm.cmd --filter @group-interview-arena/web test -- src/features/sessions/discussion-stage.test.tsx.
- Expected RED: visual rhythm contract classes are absent.
- Minimal GREEN: markup/classes without content transformation.
- Regression: pnpm.cmd --filter @group-interview-arena/web test -- src/features/sessions/discussion-stage.test.tsx src/features/sessions/session-panel.test.tsx.
- GREEN command: pnpm.cmd --filter @group-interview-arena/web test -- src/features/sessions/discussion-stage.test.tsx.
- Scope gate: only discussion-stage.tsx and its test may differ for R2-B.4; no transcript content transformation or merge change.
- Review checkpoint: no Markdown/HTML interpretation.

### R2-B.5 Stable composer treatment

- Files: discussion-stage.tsx and discussion-stage.test.tsx.
- Responsibility: visually group the existing stable action zone without changing F3A semantics.
- Consumes: existing draft inspection and callbacks.
- Produces: the existing Composer component with readable count/reason/action hierarchy.
- RED first: editable-before-floor, click-time authority, pending/rejected separation, keyboard/focus regressions plus presentation classes.
- RED command: pnpm.cmd --filter @group-interview-arena/web test -- src/features/sessions/discussion-stage.test.tsx.
- Expected RED: visual contract assertions fail while functional regressions remain green.
- Minimal GREEN: presentation-only markup/classes.
- Regression: pnpm.cmd --filter @group-interview-arena/web test -- src/features/sessions/session-panel.test.tsx.
- GREEN command: pnpm.cmd --filter @group-interview-arena/web test -- src/features/sessions/discussion-stage.test.tsx.
- Scope gate: only discussion-stage.tsx and its test may differ for R2-B.5; send eligibility, keyboard, focus, pending, and rejected-draft contracts remain unchanged.
- Review checkpoint: no autosave, 90-second, 800-character, suggestion-button claims.

### R2-B.6 Task Brief/private-note hierarchy

- Files: task-brief-panel.tsx and discussion-workspace.test.tsx.
- Responsibility: organize real question facts and memory-only notes as a readable support rail.
- Consumes: existing TaskBriefPanelProps/question states/notes callbacks.
- Produces: TaskBriefPanel with truthful card hierarchy and subdued private-note treatment.
- RED first: public allowlist, four question states, notes preservation across responsive switching, no persistence claim.
- RED command: pnpm.cmd --filter @group-interview-arena/web test -- src/features/sessions/discussion-workspace.test.tsx.
- Expected RED: new hierarchy hooks/classes are absent.
- Minimal GREEN: presentation-only structure.
- Regression: pnpm.cmd --filter @group-interview-arena/web test -- src/features/sessions/session-panel.test.tsx.
- GREEN command: pnpm.cmd --filter @group-interview-arena/web test -- src/features/sessions/discussion-workspace.test.tsx.
- Scope gate: only task-brief-panel.tsx and discussion-workspace.test.tsx may differ for R2-B.6; notes stay SessionPanel memory-only state.
- Review checkpoint: no hidden question fields or autosave text.

### R2-B.7 Six-phase Session Progress hierarchy

- Files: session-progress-panel.tsx, session-presentation.ts, session-presentation.test.ts, discussion-workspace.test.tsx.
- Responsibility: render the exact six phases and real current/completed/upcoming state without synthetic percentage.
- Consumes: DISCUSSION_PHASES, status, countdown, floor, connection.
- Produces: SessionProgressPanel plus phaseLabel(...)/sessionStatusLabel(...) presentation helpers with the exact ordered six-step hierarchy and truthful terminal/current labels.
- RED first: all six states/order, terminal states, diagnostic/fake-progress absence.
- RED command: pnpm.cmd --filter @group-interview-arena/web test -- src/features/sessions/session-presentation.test.ts src/features/sessions/discussion-workspace.test.tsx.
- Expected RED: richer hierarchy semantics are absent.
- Minimal GREEN: presentation helpers and markup only.
- Regression: pnpm.cmd --filter @group-interview-arena/web test -- src/features/sessions/session-panel.test.tsx.
- GREEN command: pnpm.cmd --filter @group-interview-arena/web test -- src/features/sessions/session-presentation.test.ts src/features/sessions/discussion-workspace.test.tsx.
- Scope gate: only the four named R2-B.7 source/test files may differ; DISCUSSION_PHASES stays the six-value authority and no synthetic progress fact is added.
- Review checkpoint: no five-phase lifecycle, score, vote, consensus, report, or percentage.

### R2-B.8 Tablet/mobile fidelity

- Files: discussion-workspace.tsx and discussion-workspace.test.tsx.
- Responsibility: retain 768–1199 one support sheet and <768 exact tabs while applying the visual system.
- Consumes: ActiveDiscussionSurface and one mounted component set.
- Produces: DiscussionWorkspace with unchanged 讨论 | 题目 | 进程 order/default/keyboard semantics and one tablet sheet.
- RED first: responsive visibility, focus, no remount/refetch/reconnect, center remains primary.
- RED command: pnpm.cmd --filter @group-interview-arena/web test -- src/features/sessions/discussion-workspace.test.tsx.
- Expected RED: new visual/bounded assertions fail; existing semantic tests establish preserved authority.
- Minimal GREEN: responsive classes only.
- Regression: pnpm.cmd web:test.
- GREEN command: pnpm.cmd --filter @group-interview-arena/web test -- src/features/sessions/discussion-workspace.test.tsx.
- Scope gate: only discussion-workspace.tsx and its test may differ for R2-B.8; no matchMedia authority, remount, refetch, or reconnect.
- Review checkpoint: no matchMedia business authority or duplicate component trees.

### R2-B.9 Representative Browser visual/layout acceptance

- Files: session.spec.ts.
- Responsibility: assert meaningful geometry/state at 1440x900, 900x900, and 390x844.
- Consumes: real Browser flow and R2-A long transcript.
- Produces: simultaneous desktop panels, center > rails, composer within viewport, transcript overflow, single tablet sheet, exact mobile tabs, focus/contrast review hooks, forbidden-text absence.
- RED first: add geometry and truthful-feature assertions before presentation changes.
- RED command: pnpm.cmd web:test:e2e.
- Expected RED: at least the strengthened composition geometry/state assertions fail.
- Minimal GREEN: only R2-B.1–R2-B.8 presentation work.
- Regression: pnpm.cmd web:test and web:build.
- GREEN command: pnpm.cmd web:test:e2e.
- Scope gate: screenshots, if locally captured, remain temporary and are not correctness inputs or tracked artifacts.
- Review checkpoint: human visual review at all three sizes; no exact-pixel comparison.

### R2-B batch gate

Run frozen-lock install, Web format/lint/typecheck/full Vitest/build, live OpenAPI drift, Chromium, R2-A containment regressions, exact R2-B allowlist, backend/API/realtime/transcript/dependency diffs empty, Master Plan hash, git diff --check, staged zero. Run review bundle, external actual-source review, then user commit/push and exact CI green. Visual fidelity remediation closes only on accepted evidence; R3 remains unstarted until then.

## Batch R3 — Conversation Quality Foundation

### R3.1 Recent public discussion selection

- Files: create conversation_context.py and test_ai_runtime_conversation_context.py.
- Responsibility: implement the pure contiguous-suffix policy.
- Consumes: validated PublicDiscussionUtterance values newest-first.
- Produces: deterministic chronological tuple and compact rendered text.
- RED first: 0–6 items, seventh excluded, exact 4000 accepted, 4001 newest yields empty, older non-fitting stops without skipping, complete Unicode code points, deterministic order, invalid actor/phase/content rejected.
- RED command: uv run pytest tests/test_ai_runtime_conversation_context.py -q from apps/api.
- Expected RED: module/types/functions do not exist.
- Minimal GREEN: pure dataclasses/functions only; no DB/provider abstraction.
- GREEN command: uv run pytest tests/test_ai_runtime_conversation_context.py -q from apps/api.
- Regression: uv run pytest tests/test_ai_runtime_prompting.py tests/test_discussion_public_events.py -q.
- Scope gate: no event/public contract/schema change.
- Review checkpoint: contiguous suffix and no truncation proven explicitly.

### R3.2 Public participant labeling

- Files: conversation_context.py and its unit test.
- Responsibility: label Human/AI only from public actor kind and seat order.
- Consumes: actor_kind and seat_order.
- Produces: 你 and AI 候选人 N prefixes.
- RED first: Human, three AI seats, invalid/system actor, non-positive seat, Persona/private sentinel absence.
- RED command: uv run pytest tests/test_ai_runtime_conversation_context.py -q from apps/api.
- Expected RED: labeling helper absent.
- Minimal GREEN: exact two-branch fail-closed helper.
- GREEN command: uv run pytest tests/test_ai_runtime_conversation_context.py -q from apps/api.
- Regression: uv run pytest tests/test_ai_runtime_conversation_context.py tests/test_ai_runtime_prompting.py -q from apps/api.
- Scope gate: no display_name/participant ID/diagnostic output.
- Review checkpoint: rendered context contains no Persona label or raw identifier.

### R3.3 Persona behavior translation

- Files: conversation_context.py and its unit test.
- Responsibility: pure exhaustive signed/unsigned mapping and stable Chinese guidance.
- Consumes: AuthorizedPersonaContext private input.
- Produces: private persona_behavior string only.
- RED first: unsigned 0, 0.331, 0.333, 0.334, 0.666, 0.667, 0.669, 1; signed -1, -0.334, -0.333, 0, 0.333, 0.334, 1; all speech styles; unknown style; illegal domains; stable line order; no raw Decimal text; no flattery/hostility wording.
- RED command: uv run pytest tests/test_ai_runtime_conversation_context.py -q from apps/api.
- Expected RED: bands/renderer absent and current prompt serializes raw Persona fields only.
- Minimal GREEN: exact enums/thresholds/phrase maps above.
- GREEN command: uv run pytest tests/test_ai_runtime_conversation_context.py -q from apps/api.
- Regression: uv run pytest tests/test_question_persona_domain.py tests/test_question_persona_seed.py -q.
- Scope gate: Persona persistence/seed values unchanged.
- Review checkpoint: every legal three-decimal persisted value maps once; support bias never uses unsigned mapping.

### R3.4 Prompt Version v2 closed contract

- Files: prompting.py, ai_runtime/seed.py, test_ai_runtime_prompting.py, test_ai_runtime_prompt_seed.py.
- Responsibility: add recent_discussion/persona_behavior and immutable v2 template without mutating v1.
- Consumes: existing eight authorized values plus two private transient rendered strings.
- Produces: exact ten-variable prompt and AI_CANDIDATE_TURN_V2 definition.
- RED first: exact PROMPT_VARIABLES set, missing/extra/unknown rejection, stable rendering, all ten v2 identifiers, required turn/phase/privacy instructions, v1 object remains unchanged.
- RED command: uv run pytest tests/test_ai_runtime_prompting.py tests/test_ai_runtime_prompt_seed.py -q.
- Expected RED: vocabulary has eight names and v2 asset is absent.
- Minimal GREEN: update closed model/variables and add the fixed immutable asset only.
- GREEN command: uv run pytest tests/test_ai_runtime_prompting.py tests/test_ai_runtime_prompt_seed.py -q from apps/api.
- Regression: uv run pytest tests/test_ai_runtime_domain.py tests/test_ai_runtime_generation.py -q.
- Scope gate: provider adapter and v1 persisted content untouched.
- Review checkpoint: no generated-output post-processing or message-role redesign.

### R3.5 Prompt publication and effective selection

- Files: app.py, ai_runtime/seed.py, orchestration.py, test_ai_runtime_prompt_seed.py, test_auth_runtime.py, deadline_recovery_test_helpers.py, test_ai_runtime_prompt_bootstrap.py, test_ai_runtime_persistence.py, test_ai_runtime_automatic_orchestration.py.
- Responsibility: publish exact v2 through the normal production lifespan, fail startup closed on publication drift, and select the highest valid version only for new deterministic requests.
- Consumes: the existing create_app(...) lifespan/session factory, publish_prompt_version(...), PromptVersion timestamps, grant.granted_at, and any existing generation request.
- Produces: AI_CANDIDATE_TURN_V2, seed_ai_runtime_prompt_versions(...), the production lifespan call, durable PromptVersion v2, and _select_effective_prompt_version(...).
- RED first — publication: in test_ai_runtime_prompt_bootstrap.py, start create_app(...) normally against a fresh migrated PostgreSQL database and require the exact literal v2 row after lifespan entry; close and restart through the same lifespan and require identical row/count/digest/timestamps with no second insert; prepublish v1 through publish_prompt_version(...), snapshot every immutable field, bootstrap, and require the snapshot unchanged; prepublish a conflicting same UUID or (prompt_key, version_number) through publish_prompt_version(...), then require normal lifespan entry to raise before recovery starts. The test calls no direct seed function.
- RED first — selection: v1-only -> v1; v1+published v2 with grant before 2026-08-27T16:00:00Z -> v1; grant at/after that instant -> v2; v2 retired at grant -> v1; existing v1 request after v2 -> persisted v1; no valid prompt -> RECONCILIATION_REQUIRED/zero provider.
- RED command: uv run pytest tests/test_ai_runtime_prompt_seed.py tests/test_auth_runtime.py tests/integration/test_ai_runtime_prompt_bootstrap.py tests/integration/test_ai_runtime_persistence.py tests/integration/test_ai_runtime_automatic_orchestration.py -q.
- Expected RED: no production caller or v2 asset exists, new turns hardcode version 1, and a fresh normally bootstrapped application database has no v2 row.
- Minimal GREEN: add the literal asset/publication wrapper, one awaited call in the existing app lifespan at the frozen position, unit-only startup stubbing/order assertions, and the ordered selector used only in the existing_request is None branch.
- GREEN command: uv run pytest tests/test_ai_runtime_prompt_seed.py tests/test_auth_runtime.py tests/integration/test_ai_runtime_prompt_bootstrap.py tests/integration/test_ai_runtime_persistence.py tests/integration/test_ai_runtime_automatic_orchestration.py -q from apps/api.
- Regression: uv run pytest tests/integration/test_ai_runtime_continuous_drive.py -q.
- Scope gate: DB model/migration/service contract and question_personas/seed.py unchanged; no v1 mutation/retirement, direct insert, manual SQL, browser-owned publication, or provider I/O.
- Review checkpoint: inspect the complete definition -> lifespan caller -> durable row -> selector -> new request -> rendered v2 chain, plus the replay branch for persisted prompt_version_id/requested_at authority.

### R3.6 Runtime context assembly

- Files: runtime.py, conversation_context.py, test_ai_runtime_conversation_context.py, test_ai_runtime_orchestration.py.
- Responsibility: load/validate same-session public utterances and compose recent_discussion/persona_behavior into AuthorizedGenerationContext.
- Consumes: DiscussionEvent, project_public_events(...), SessionParticipant, current AuthorizedPersonaContext/private stance.
- Produces: transient recent_discussion and persona_behavior in rendered prompt.
- RED first: same-session Human/AI chronological context, six/4000 bounds, malformed fact fail closed, pending/rejected/provider/log/internal/other Persona/stance sentinels absent, current stance still present.
- RED command: uv run pytest tests/integration/test_ai_runtime_orchestration.py -q.
- Expected RED: _assemble_generation_input(...) loads no discussion and no behavior text.
- Minimal GREEN: one bounded query/validation helper in runtime.py plus pure calls; no raw rows/JSON dump.
- GREEN command: uv run pytest tests/integration/test_ai_runtime_orchestration.py -q from apps/api.
- Regression: uv run pytest tests/integration/test_ai_runtime_persistence.py -q.
- Scope gate: request metadata/log/schema/public projections unchanged.
- Review checkpoint: provider input contains only the current AI private stance and public recent facts.

### R3.7 Deterministic fake-provider integration

- Files: test_ai_runtime_automatic_orchestration.py; browser_e2e.py and session.spec.ts only for the final cross-layer assertion.
- Responsibility: capture RuntimeGenerationInput.rendered_prompt while retaining the existing durable generation/utterance/release/schedule chain.
- Consumes: v2 selection, assembled context, deterministic fake provider.
- Produces: structural evidence for prior Human and AI lines/order, Persona behavior, phase instruction, report-avoidance instruction, privacy exclusions, durable request/utterance.
- RED first: add sentinel-based structural assertions, never whole-response equality.
- RED command: uv run pytest tests/integration/test_ai_runtime_automatic_orchestration.py -q, then pnpm.cmd web:test:e2e from root for cross-layer proof.
- Expected RED: captured prompt lacks recent discussion and behavior; selection remains v1.
- Minimal GREEN: no behavior beyond R3.1–R3.6.
- GREEN commands: uv run pytest tests/integration/test_ai_runtime_automatic_orchestration.py -q from apps/api; then pnpm.cmd web:test:e2e from repository root.
- Regression: uv run pytest tests/integration/test_ai_runtime_automatic_orchestration.py tests/integration/test_ai_runtime_continuous_drive.py tests/integration/test_backend_text_discussion_transport.py -q from apps/api; then pnpm.cmd web:test:e2e from repository root.
- Scope gate: network disabled; provider/model/config values unchanged.
- Review checkpoint: request and AI utterance persist through existing path; no private/internal sentinel escapes.

### R3.8 Separately authorized qualitative smoke plan

- Files: no production/test change; future sanitized operator evidence only if separately approved.
- Responsibility: define manual quality review without making it a CI/final-acceptance requirement.
- Consumes: a future committed/CI-green R3 build and explicit user approval for a real provider call.
- Produces: sanitized pass/fail checklist only; no prompt, credential, raw response, or verbatim output record.
- RED first: not applicable to automated TDD; its precondition is an explicit future authorization and all structural gates green.
- RED command: none is authorized; R3.8 is intentionally excluded from automated TDD and requires a new explicit user instruction.
- Expected RED: no automated failure is manufactured; the pre-smoke state is that no real network call has occurred and all structural gates are green.
- Minimal GREEN: review exactly five fixed scenarios—opening/no context; exploration after Human+AI; constructive conflict; convergence compromise; final summary plus paired Persona comparison.
- GREEN command/evidence: no repository command is authorized; human review checks no headings/report template/full-question repeat, reasonable spoken length, contextual response, partial-turn behavior, Persona difference, and no leakage.
- Regression: automated gates remain independently green.
- Scope gate: no key/model/output in repository or governance evidence.
- Review checkpoint: optional smoke cannot substitute for actual-source review or deterministic tests.

Post-closeout historical evidence：a later explicitly authorized real-provider local smoke was executed and exposed P1-5R-POST-001。That smoke remains defect-discovery evidence but is not the separately defined formal R3.8 checkpoint；formal R3.8 remains `NOT_EXECUTED / REQUIRES_SEPARATE_EXPLICIT_USER_AUTHORIZATION`。No further real-provider call was made。

### R3 batch gate

From apps/api run uv sync --frozen, uv lock --check, Ruff check/format, Pyright, focused R3 unit/integration tests, all non-integration tests, all integration tests, and the full suite. Run Alembic heads/current/check and migration regressions against the established PostgreSQL environment. The focused PostgreSQL gate must start a normal create_app(...) lifespan against a fresh migrated application database and assert the exact v2 UUID, key, version, purpose, template digest/text, created_at, published_at, and retired_at after supported bootstrap; it must repeat startup as an exact no-op, prove conflicting identity/version aborts startup, and prove v1 remains byte/field unchanged. The selection gate separately proves pre-publication grants choose v1, at/post-publication new requests persist/select/render v2, and existing requests retain their persisted prompt_version_id. From root run Web format/lint/typecheck/test/build and network-free Browser E2E. Require exact R3 allowlist, schema/migration/REST/WS/generated/dependency/provider/config diffs empty, Master Plan hash, privacy/static scan, git diff --check, staged zero. Run review bundle, external actual-source review, then user commit/push and exact CI green. F3 closes only on accepted evidence.

## Final Acceptance — cross-layer composition and independent acceptance

Precondition: R1, R2-A, R2-B, and R3 are each implementation-complete, external actual-source review PASS, user committed/pushed, and exact commit CI-green. The acceptance work does not reopen batch architecture.

### Final composition task

- Files: modify apps/api/tests/integration/browser_e2e.py and apps/web/e2e/session.spec.ts for the combined assertions/harness coordination; update only the minimal current-status Markdown files after evidence.
- Responsibility: one network-free fake-provider composition across all remediations.
- Consumes: committed R1–R3 authorities.
- Produces: backend/PostgreSQL proof for natural initial/cross-phase floor, reconnect/idempotency, Human->AI durable chain, v2 effective selection, bounded public context/privacy; Browser proof for natural discussion, long bounded transcript, reachable composer, preserved history browsing, return affordance, three viewports, reload/API restart, memory-only notes, no fake UI/storage authority.
- RED first: if a combined assertion is absent, add it before harness change.
- RED command: uv run pytest tests/integration/test_discussion_progression.py tests/integration/test_ai_runtime_automatic_orchestration.py -q from apps/api; then pnpm.cmd web:test:e2e from repository root.
- Expected RED: only a missing cross-layer composition proof may fail; a product behavior failure reopens the owning batch rather than being patched ad hoc.
- Minimal GREEN: test-harness composition only. A product behavior failure stops Final Acceptance and reopens the exact owning batch; Final Acceptance never patches production ad hoc.
- GREEN commands: from apps/api run uv run pytest tests/integration/test_discussion_progression.py tests/integration/test_ai_runtime_automatic_orchestration.py -q; from repository root run pnpm.cmd web:test:e2e; then run the complete API/PostgreSQL, Web quality/build, OpenAPI drift, migration, privacy, scope, hash, diff/staged gates frozen above.
- Regression: no real provider call; no manual initial-floor helper in main evidence.
- Scope gate: no new product capability or architecture.
- Review checkpoint: review bundle and external actual-source acceptance of the combined delta, then user commit/push and exact CI green.

### Independent acceptance

Only after the full remediation and final composition acceptance are committed and CI-green, invoke the independent-review skill in a separate review-only turn. It must recover authority from committed source, rerun proportional gates, verify F1/F2/Visual/F3 closure evidence, and return PASS/BLOCKED without implementation edits. P1-5R and parent P1-5 close only after PASS and findings none.

## TDD command matrix

- R1 proof/progression: test_discussion_progression.py; RED is missing initial proof/NO_WORK; GREEN is deterministic initial checkpoint.
- R1 realtime: test_discussion_session_websocket.py; RED is no deadline kick; GREEN is state event sent before conditional kick/grant.
- R1 Browser: web:test:e2e; RED is helper dependency/no natural grant; GREEN is natural first and cross-phase grants.
- R2-A viewport: workspace/stage tests plus Browser; RED is competing/unbounded scroll; GREEN is exact bounded chain and transcript-only overflow.
- R2-A follow: session-panel/stage tests; RED is missing indicator/recovery rule; GREEN is single-owner local state.
- R2-B composition: presentation component tests plus Browser; RED is missing hierarchy/geometry; GREEN is truthful presentation at three bands.
- R3 context/Persona: new pure unit test; RED is absent module/functions; GREEN is exhaustive deterministic selection/translation.
- R3 prompt/selection/runtime: prompting, persistence, orchestration integration; RED is eight variables/version-1 hardcode/no context; GREEN is immutable v2/latest-valid new request plus pinned replay.
- R3 composition: fake-provider integration/Browser; RED is absent structural context; GREEN is existing durable path with v2 private transient inputs.

## Exact batch-wide immutable gates

Every implementation batch must additionally prove:

1. PROJECT_MASTER_PLAN.md SHA-256 remains 2388a9660320406cb35d5354126ad71c6849a98db7c4a356796ca951bf372f26.
2. No unexpected path is present in git status --porcelain=v1 relative to that batch’s exact allowlist.
3. git diff --check passes and staged count is zero.
4. Dependency manifests/locks, .github, infra, migrations, and generated OpenAPI are unchanged unless the batch explicitly owns none—which all four batches do.
5. No secret/private sentinel appears in public payload/UI/log evidence; no real provider call occurs.
6. Review bundle is built in the same implementation turn and externally reviewed before commit.

## Design-to-plan coverage audit

- R1 all FLOOR_ENABLED_PHASES: R1.1 proof parameterization and R1.4 cross-phase Browser.
- R1 full deterministic command: frozen interface plus R1.1 digest/reconstruction tests.
- R1 reconnect/concurrency/ordered send-kick: R1.2/R1.3/R1.4.
- R2-A exact ancestor chain, one scroll owner, stable Composer: R2-A.1–R2-A.3.
- R2-A live/recovery/new-message/no persistence: R2-A.4/R2-A.5.
- R2-B truthful six-phase, three responsive bands, no screenshot oracle/fake capability: R2-B.1–R2-B.9.
- R3 same-session public privacy and contiguous six/4000 suffix: R3.1/R3.2/R3.6.
- R3 exhaustive unsigned/signed Persona semantics and unknown style: R3.3.
- R3 v1 immutability, exact ten variables, production-reachable v2 publication, latest-valid v2, existing-request pinning: R3.4/R3.5. The audited chain is AI_CANDIDATE_TURN_V2 literal definition -> app.py production lifespan -> seed_ai_runtime_prompt_versions(...) -> publish_prompt_version(...) -> durable PromptVersion -> _select_effective_prompt_version(...) -> new LlmGenerationRequest.prompt_version_id -> render_prompt(...) with the ten-variable v2 template; test-only/manual publication is not a link in this chain.
- R3 unchanged provider parameters and deterministic fake integration: R3.7 and immutable gates.
- Separately authorized real-provider review: R3.8 only.
- Final combined proof and independent acceptance: Final Acceptance section.

Coverage gaps: none. Source/design contradictions: none. P1-5R-IP-001: CLOSED. Open implementation findings: none.

## P1-5R-POST-001 implementation checkpoint

- Status: `CLOSED`。
- Baseline: clean committed `main` / `origin/main` `9d6270660cb7a358a62989a6a59bab2a521fa041`，which contains the legitimate prior P1-5R/P1-5 closeout after Independent Acceptance `PASS`。
- RED: a deterministic blocking fake provider proves the request is durably `RUNNING` with zero utterance before cancellation；the pre-fix task propagates `CancelledError` but leaves the request orphaned `RUNNING`。
- GREEN: `generate_ai_utterance(...)` catches cancellation across all post-claim work，uses the existing `fail_generation_request(...)` authority to terminalize `RUNNING → FAILED / INTERNAL_ERROR`，then re-raises `CancelledError`。
- Recovery: reconnect/resume observes `FAILED_REPLAY`，releases the exact AI floor as `INTERRUPTED`，runs the unchanged scheduler and processes only a newly granted AI turn；the cancelled grant has one request、zero utterances、one release and one deterministic schedule action。
- Review finding remediation: P1-5R-POST-REV-001 is `CLOSED` after remediation actual-source review `PASS`。The existing network-free Browser harness blocks the third provider call only after PostgreSQL proves its request is durably `RUNNING` with zero utterances；an actual page reload tears down the workspace WebSocket and cancels the owning progression task；normal reconnect/resume then proves `FAILED / INTERNAL_ERROR → FAILED_REPLAY`，exactly one `INTERRUPTED` release，continued scheduling，no retry for the cancelled grant and no duplicate request、utterance or release。Accepted commit `3b09d20a704c0fd3ff473ccb79311065b7e70408` has exact CI run `33257343273` `completed / success` with all four required jobs green。
- Race safety: the existing aggregate/request locks serialize completion and failure；a durable `COMPLETED` request causes cancellation cleanup to leave it unchanged，while existing `FAILED` state is terminal and the cancelled `RUNNING` row fails exactly once。
- Scope: runtime source、one existing PostgreSQL integration test file and current governance only；no schema/migration、REST/WS、scheduler、Prompt/context、provider/model/config/timeout、Web or dependency change；real-provider calls during remediation `0`。

## Stop conditions

Stop and report before changing scope if implementation requires a schema/migration, REST/OpenAPI/WS/public event change, scheduler policy/domain/service semantic change, second progression/realtime authority, browser-selected speaker, global Web store, browser business persistence, transcript merge change, provider adapter/parameter/model change, dependency, prompt v1 mutation/rebinding, RAG/memory system, or fake UI capability. Do not solve such a conflict by expanding a batch allowlist.

## Current governance hierarchy after post-acceptance remediation

~~~text
P1 = DONE / CLOSED
P1-5 = DONE
Previous P1-5 closeout = PASS / DONE at commit 9d6270660cb7a358a62989a6a59bab2a521fa041
P1-5R = CLOSED
Previous P1-5R closeout = PASS / CLOSED at commit 9d6270660cb7a358a62989a6a59bab2a521fa041
R1 = DONE
R2-A = DONE
R2-B = DONE
R3 = DONE
Historical Final Composition Acceptance = PASS / DONE
Historical Independent Acceptance = PASS
F1 = CLOSED
F2 = CLOSED
Visual fidelity remediation = CLOSED
F3 = CLOSED
Historical post-closeout real-provider smoke = EXECUTED / DEFECT_EXPOSED
Formal R3.8 = NOT_EXECUTED / REQUIRES_SEPARATE_EXPLICIT_USER_AUTHORIZATION
Further real-provider calls after defect discovery = 0
P1-5R-POST remediation actual-source review = PASS
Accepted remediation commit = 3b09d20a704c0fd3ff473ccb79311065b7e70408
Exact CI run = 33257343273 / completed / success / all four required jobs green
P1-5R-IP-001 = CLOSED
P1-5R-POST-001 = CLOSED
P1-5R-POST-REV-001 = CLOSED
Current P1-5R review finding = NONE
Open findings = NONE
~~~

Batch R1、Batch R2-A、Batch R2-B and Batch R3 remain accepted and DONE，with F1、F2、visual fidelity remediation and F3 CLOSED。Final Composition Acceptance、Independent Acceptance and the committed prior P1-5R/P1-5 closeout remain historical `PASS / CLOSED` evidence。The later post-closeout real-provider smoke exposed P1-5R-POST-001；the remediation actual-source review passed，accepted commit `3b09d20a704c0fd3ff473ccb79311065b7e70408` and exact CI run `33257343273` are green，P1-5R-POST-REV-001、P1-5R-POST-001 and P1-5R are `CLOSED`，parent P1-5 is `DONE`，and open findings are `NONE`。Formal R3.8 remains `NOT_EXECUTED / REQUIRES_SEPARATE_EXPLICIT_USER_AUTHORIZATION`；no further real-provider call occurred，and the frozen R1～R3 implementation contract is unchanged。
