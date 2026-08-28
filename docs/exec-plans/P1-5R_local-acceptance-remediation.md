# P1-5R Local Acceptance Remediation — Design Freeze

Status: `P1 IN_PROGRESS`; `P1-5 IN_PROGRESS / POST_CLOSEOUT_REMEDIATION_OPEN`; `P1-5R IN_PROGRESS / DESIGN_FROZEN / IMPLEMENTATION_PLAN_FROZEN`; `R1 NOT_STARTED / READY_FOR_IMPLEMENTATION`; `R2-A NOT_STARTED / BLOCKED_BY_R1`; `R2-B NOT_STARTED / BLOCKED_BY_R2-A`; `R3 NOT_STARTED / BLOCKED_BY_R2-B`

Target version: `V0.1 Internal Validation`

Design-freeze baseline: clean committed `main` at `91671fe1afc19a9dcc4341184c23500852f96780`, equal to `origin/main`

Baseline CI: GitHub Actions run `33054731104`, `completed / success`, head SHA `91671fe1afc19a9dcc4341184c23500852f96780`

Immutable product baseline: [`PROJECT_MASTER_PLAN.md`](../PROJECT_MASTER_PLAN.md), SHA-256 `2388a9660320406cb35d5354126ad71c6849a98db7c4a356796ca951bf372f26`

Governance: [`DECISIONS.md`](../DECISIONS.md), [`TASKS.md`](../TASKS.md), [`ROADMAP.md`](../ROADMAP.md)

Historical parent plan: [`P1-5_ai-runtime-foundation.md`](P1-5_ai-runtime-foundation.md)

Historical composition intent: [`P1-5F-3B_complete-discussion-page-composition.md`](P1-5F-3B_complete-discussion-page-composition.md)

## Purpose and reopen semantics

P1-5 previously reached `DONE` at the committed baseline above after F3B/F4 implementation, CI and independent acceptance. Later real local-browser acceptance exposed correctness, long-session UX, visual-fidelity and AI-conversation-quality findings that were not falsified by the earlier evidence.

This document creates one post-closeout remediation checkpoint. It does not rewrite P1-5 history:

- `P1-5A` through `P1-5F` retain their historical `DONE` checkpoints and evidence;
- `P1-5F`, `P1-5F-3`, `P1-5F-3A`, `P1-5F-3B` and `P1-5F-4` remain `DONE`;
- parent `P1-5` is currently reopened to `IN_PROGRESS` only because `P1-5R` is unresolved;
- `P1-5R` is `IN_PROGRESS / DESIGN_FROZEN` after this docs-only checkpoint;
- no remediation implementation is claimed.

The open findings are:

- `F1 OPEN` — floor-enabled phases can enter without an initial scheduler checkpoint;
- `F2 OPEN` — transcript growth can expand the document and push the composer/progress out of the useful viewport;
- `Visual fidelity remediation OPEN` — the committed page is functional but remains materially below the frozen simulation-studio composition intent;
- `F3 OPEN` — AI turns are report-like and lack recent public discussion context plus natural-language behavioral Persona guidance.

## Scope and non-goals

This checkpoint freezes design only. It changes documentation and does not implement R1, R2-A, R2-B or R3.

No production source, tests, migration, schema, REST/OpenAPI contract, WebSocket event contract, generated artifact, dependency/lockfile, provider adapter, provider parameter, CI, realtime protocol or frontend production file changes are authorized here.

The remediation remains narrow. It adds no Redis, queue, worker, voice, scoring, report, RAG/memory system, CMS, multi-worker broadcast rewrite, global frontend store, second realtime authority, new provider abstraction, browser persistence of business authority, fake consensus/vote or unrelated refactor.

The frozen future implementation order is:

```text
R1
  -> R2-A
  -> R2-B
  -> R3
  -> final composition acceptance
  -> independent acceptance
```

Each future batch uses TDD and actual-source review before commit. Final independent acceptance occurs only against a committed, CI-green remediation baseline. The detailed executable plan is frozen separately in [`P1-5R_local-acceptance-remediation-implementation.md`](P1-5R_local-acceptance-remediation-implementation.md).

## Accepted source observations

The committed source was inspected before freezing this design.

### R1 observations

- [`resume_discussion_progression(...)`](../../apps/api/src/group_interview_arena_api/modules/discussion_sessions/progression.py) stops with `NO_WORK` when a floor-enabled phase has no current floor, no exact Human release checkpoint and no resumable AI work.
- Existing Human post-release progression derives deterministic identities from the released grant and calls the single existing scheduler through `drive_scheduler_checkpoint(...)`.
- The realtime catch-up loop reconciles deadlines and drains committed lifecycle events, but does not kick discussion progression after a reconciliation-created phase transition.
- Initial WebSocket connection/reconnect already drains committed truth and best-effort kicks progression.
- `floor.schedule` replay is semantic: its digest includes child identities, expected phase, expected sequence, expected current grant, `evaluated_at` and the full closed scheduler policy. Stable UUIDs alone are insufficient.
- `session.state_changed` v2 events durably record the status entered, phase timing and ordered session sequence. They can identify the exact entry into the current floor-enabled phase without a new table.

### R2 observations

- Existing confirmed-transcript logic already measures near-bottom state before applying a live utterance and follows the new tail only when the user was near the bottom.
- No presentation state or control currently communicates `有新发言` / `回到底部` while the user browses history.
- The loaded authenticated shell and the nested discussion workspace both use minimum viewport height. The discussion surface itself owns overflow, but the complete ancestor height chain is not bounded, so transcript growth can still expand the document rather than one reliable transcript viewport.
- Existing responsive component/state authority is sufficient; no refetch, remount, second realtime client or global store is required.

### R3 observations

- `AuthorizedGenerationContext` currently contains exact Question, Persona JSON, the current AI's Private Stance and question-specific phase instruction, but no recent public transcript.
- Persona behavior is supplied mostly as structured fields rather than deterministic natural-language behavior guidance.
- New automatic turns currently resolve exact `AI_CANDIDATE_TURN` version `1` at the grant time.
- Existing generation requests correctly reuse their persisted `prompt_version_id`, provider/model/configuration and request timestamp.
- The durable `participant.utterance.created` v1 event is already the allowlisted public Human/AI transcript fact and is sufficient for bounded same-session recent context.

These observations reveal no requirement for a DB migration, public API/realtime change, new provider abstraction or global frontend state.

## R1 — Initial Phase Floor Scheduling

Status: `NOT_STARTED`

Severity: correctness blocker.

### Authority and progression order

P1-3 remains the only lifecycle/phase/deadline authority. P1-4 remains the only speaker scheduler and floor authority. P1-5 AI Runtime still decides only what an already-granted AI says.

The progression order is frozen as:

```text
floor-enabled phase
  -> current floor exists?
       HUMAN -> wait for Human
       AI    -> drive existing configured AI runtime
  -> exact Human release checkpoint exists?
       yes   -> existing Human scheduler checkpoint
  -> resumable AI work exists?
       yes   -> existing AI recovery path
  -> exact initial phase-entry checkpoint
       -> existing Floor Scheduler
       -> floor.granted / no-grant / intervention
```

The final initial phase-entry branch applies to every phase in the source-owned `FLOOR_ENABLED_PHASES` set. The current set is:

- `OPENING_STATEMENTS`;
- `EXPLORATION`;
- `CONFLICT_AND_EVALUATION`;
- `CONVERGENCE`;
- `FINAL_SUMMARY`.

No second scheduler, client-selected speaker, public scheduling endpoint or browser timer is introduced. `V0_1_SCHEDULER_POLICY`, `ScheduleFloorCommand`, `apply_scheduler_command(...)` and current scheduler decision semantics remain unchanged.

### Durable phase-entry proof

An initial checkpoint is eligible only when authoritative state proves all of the following:

- the owner-scoped session is currently in a source-defined floor-enabled phase;
- `current_floor_grant_id` is null;
- no exact pending Human post-release checkpoint applies;
- no resumable AI work applies;
- one durable `session.state_changed` v2 event for the same session entered the current status;
- that event's payload status and phase timing agree with the current aggregate;
- its ordered sequence is the latest authoritative entry into that current phase.

The durable phase-entry identity is:

```text
session_id
+ current phase
+ phase-entry session.state_changed sequence
```

The database identity `(session_id, sequence)` plus the closed event payload is the proof. Wall-clock `now`, WebSocket connection identity and process memory are not identity inputs. Missing, ambiguous or inconsistent proof returns reconciliation-required and performs no scheduling mutation.

### Deterministic identities and semantic replay

One exact phase-entry identity deterministically derives:

- `schedule_action_id`;
- `decision_id`;
- `next_floor_grant_id`;
- `intervention_id`.

Derivation uses one fixed project namespace and stable labels containing the session, phase and phase-entry sequence. It follows the existing UUIDv5-to-UUID4-compatible project convention; no random replacement ID may escape a replay conflict.

The complete `ScheduleFloorCommand` semantics are reconstructed only from durable facts:

- `expected_phase` = the entered phase from the exact phase-entry event;
- `expected_last_sequence` = the exact phase-entry event sequence;
- `expected_current_floor_grant_id` = `null`;
- `evaluated_at` = the committed `occurred_at` of that exact phase-entry event;
- `policy` = unchanged `V0_1_SCHEDULER_POLICY`;
- child identities = the deterministic values above.

This freezes `evaluated_at` rather than substituting a later wall-clock value. Repeated progression kicks therefore reconstruct the same schedule digest. If the deterministic `SessionAction` and `FloorDecision` already exist, progression consumes the durable decision/child fact. Same action with different semantics remains `ACTION_ID_CONFLICT` and is handled by authoritative re-read, never by minting a new identity.

Existing concurrency protection remains sufficient:

- owner-scoped aggregate row lock;
- lifecycle reconciliation under that lock;
- exact phase/sequence/current-floor preconditions;
- durable `SessionAction` digest replay/conflict;
- deterministic decision/grant/intervention children;
- current-floor and uniqueness constraints;
- existing scheduler transaction boundaries.

No scheduler policy or schema change is frozen.

### Realtime phase-transition caller

For a connected WebSocket, the deadline catch-up order is frozen as:

```text
reconcile authoritative deadline
  -> reconciliation committed lifecycle/state-change events?
       no  -> drain normally; do not kick a scheduler loop
       yes -> drain/project/send those committed events
            -> best-effort kick existing discussion progression
```

The committed lifecycle event becomes visible before the progression kick. Only an authoritative reconciliation result containing lifecycle/state-change events creates this catch-up kick. The existing 250ms delivery loop must not become an unconditional scheduler invocation loop.

Initial connection/reconnect may continue to drain and kick progression. Duplicate connection, reconnect or catch-up kicks are harmless because the phase-entry checkpoint has deterministic identity and complete semantic replay.

The separate deadline recovery runtime remains lifecycle recovery, not a new scheduler architecture. A later connection/reconnect safely resumes progression from durable state.

### R1 acceptance contract

Future R1 implementation must prove:

1. Natural first speaking phase: create session, `session.start`, use no manual/test scheduling helper, naturally enter the first floor-enabled phase and naturally emit `floor.granted`.
2. Cross-phase: deadline reconciliation advances from speaking phase A to speaking phase B and B naturally obtains its first `floor.granted`; at least two speaking phases are crossed, with broader source-enum coverage preferred where practical.
3. Repeated progression: multiple kicks for the same phase entry converge on one scheduler action/decision and at most one active floor.
4. Reconnect: reconnect before or after the initial grant creates no duplicate initial floor.
5. Existing semantics: Human/AI post-release scheduling, idempotency, continuous AI drive, recovery and interventions remain unchanged.
6. Browser composition: the main user-path E2E no longer grants the first floor through a helper. Test-only direct grants may remain only in isolated lower-level tests that are not evidence for natural composition.

## R2-A — Transcript Viewport / Scroll Ownership

Status: `NOT_STARTED`

Scope: Web-only presentation remediation. REST, WebSocket, backend events, DB, transcript persistence/identity/merge, session/floor semantics and browser persistence rules remain unchanged.

### Viewport-bounded ownership

The loaded training studio is bounded to the dynamic viewport. Unauthenticated entry and pre-session selection may retain ordinary document flow; the active loaded-session workspace must use the following ownership:

```text
loaded studio root
  -> h-dvh / max-h-dvh equivalent
  -> overflow hidden

product/account header + mobile nav/support controls
  -> shrink-0

workspace body/grid
  -> remaining flex/grid height
  -> min-height: 0
  -> overflow constrained

Task and Progress support rails
  -> min-height: 0
  -> independent overflow-y auto where needed

center Discussion surface
  -> h-full
  -> min-height: 0
  -> overflow hidden

DiscussionStage
  -> flex column
  -> h-full
  -> min-height: 0

participant strip + notices
  -> shrink-0

confirmed Transcript list
  -> flex: 1
  -> min-height: 0
  -> overflow-y: auto

Composer
  -> shrink-0
  -> consistently visible/reachable
```

The whole Discussion surface is not the transcript scroll owner. The transcript list is. No virtualization, windowing or paging is introduced in V0.1.

### Near-bottom and new-message behavior

The existing near-bottom threshold and follow behavior remain the basis:

- when the user is near the transcript bottom and a new confirmed utterance is merged, follow the newest transcript automatically;
- when the user has deliberately scrolled upward, preserve their scroll position and do not steal scroll;
- when a newly confirmed tail is added while the user is away from the bottom, show one subtle presentation-only `有新发言` / `回到底部` indication;
- clicking the indication scrolls the transcript to the newest confirmed item, clears the indication and resumes near-bottom following;
- manually returning within the existing near-bottom threshold clears the indication and restores natural follow for subsequent utterances.

The indication is local mounted-workspace presentation state only. It is neither an unread business fact nor a realtime authority. It does not enter localStorage, sessionStorage, backend state, transcript facts, logs or public contracts.

Authoritative recovery does not remount or blank the confirmed transcript. If recovery adds a new confirmed tail to the mounted canonical transcript, the same near-bottom rule applies; restored history is not a second transcript authority.

### R2-A acceptance contract

Large deterministic transcript content must prove:

- page/document height does not grow indefinitely with transcript length;
- the transcript list itself scrolls;
- composer remains visible/reachable;
- desktop Task/Progress rails remain useful;
- near-bottom arrival follows the new tail;
- upward history browsing is not stolen;
- the new-message indication appears only when appropriate;
- clicking or manually returning to bottom clears it and restores follow;
- desktop, tablet and mobile behavior remains correct;
- no transcript remount, extra snapshot/transcript fetch or WebSocket reconnect is introduced.

## R2-B — Visual Composition / Product Fidelity

Status: `NOT_STARTED`

This is a fidelity remediation of the accepted `AI 群面训练场 / Interview Simulation Studio` direction, not screenshot pixel matching and not a new product design system.

Core feeling:

> 让求职者感觉自己正在参加一场真实、可掌控、能学习的群面训练。

The page must feel like an active interview simulation rather than an internal validation console, sparse prototype, admin dashboard, Zoom clone or chat application.

### Desktop composition

At `>= 1200px`, preserve the simultaneous three-column architecture:

- left: Task Brief plus private scratch notes;
- center: Live Discussion with participant strip, professional transcript and stable composer;
- right: Session Progress;
- center Discussion remains the clear visual and dimensional focal point.

Hierarchy uses spacing, typography, panel grouping, restrained borders, subtle major-surface shadow, neutral surfaces, restrained indigo/blue accent and restrained semantic state colors.

No gradients, glass, neon, cyberpunk styling, chat bubbles, fake video tiles or KPI-dashboard cards are introduced.

### Header

The compact header communicates only real state:

- canonical product identity;
- public Question/session title;
- current authoritative phase;
- authoritative countdown when available;
- connection/recovery status;
- existing Start/End action only when authoritative;
- existing authenticated account/logout access may remain subdued without competing with the session state.

It does not expose session UUID, Question Version UUID, sequence, server deadline ISO value, provider/model/prompt data or engineering diagnostics.

### Participants

Render actual snapshot participants only:

- Human label is `你`;
- AI candidates use the existing safe public seat labels;
- the exact current speaker is unmistakable through text plus restrained visual emphasis;
- Human floor explicitly says `轮到你发言`;
- AI waiting copy remains the existing safe public-fact-derived state only.

No private Persona label, fake waveform, fake speaking duration, fake microphone state, emotion, confidence or strategy is rendered. The future voice seam may remain structurally extensible without displaying a fake feature.

### Transcript

The transcript remains a professional meeting/discussion record:

- one aligned vertical contribution list, never alternating bubbles;
- durable confirmed records only;
- speaker and phase metadata remain clear;
- exact plain text, whitespace and line breaks are preserved;
- AI Markdown-like syntax is still rendered as plain text, not interpreted as Markdown or HTML.

R3 improves generated content. R2-B does not rewrite stored utterances or strip model output.

### Composer

The composer remains a stable bottom action zone and preserves all F3A semantics:

- draft editable before Human floor;
- exact current send eligibility and click-time grant binding;
- pending outside confirmed transcript;
- rejected draft recovery without overwriting a newer draft;
- Enter inserts newline;
- Ctrl/Cmd+Enter submits only when eligible;
- no autofocus on floor arrival;
- exact `1..4000` code-point backend contract remains the only current limit.

No autosave claim, 90-second requirement, unsupported 800-character limit, points card, logic framework, facts/cases or fake tips are added.

### Progress

Continue using the real six-phase lifecycle in exact order:

- `PREPARATION`;
- `OPENING_STATEMENTS`;
- `EXPLORATION`;
- `CONFLICT_AND_EVALUATION`;
- `CONVERGENCE`;
- `FINAL_SUMMARY`.

Progress may show current phase, authoritative countdown, current floor, connection and real lifecycle progression. It adds no atmosphere score, progress percentage, fake timing, consensus, vote, report or scoring.

### Responsive composition

The three frozen bands remain:

- `>=1200px`: real simultaneous three-column studio;
- `768px–1199px`: Discussion-first with at most one Task/Progress support sheet, never a squeezed three-column layout;
- `<768px`: tabs exactly `讨论 | 题目 | 进程`, default `讨论`.

Responsive presentation reuses one mounted authority and one component set. Switching support views does not remount/refetch/reconnect or duplicate notes/transcript state. Viewport JavaScript or `matchMedia` does not become business authority.

### R2-B acceptance contract

Meaningful browser layout inspection at `1440x900`, `900x900` and `390x844` must verify:

- center Discussion is visually primary on desktop;
- all three desktop columns fit and remain usable;
- current participant/floor states are immediately clear;
- composer remains visible/reachable;
- transcript owns long-session scrolling;
- Task and Progress have readable hierarchy without dashboard density;
- tablet support sheet and mobile tabs remain correct;
- no fake/unsupported UI was added;
- focus, contrast and keyboard behavior remain accessible.

Temporary screenshots may support human review but are not committed correctness artifacts or pixel oracles.

## R3 — Conversation Quality Foundation

Status: `NOT_STARTED`

R3 first changes prompt/context quality. It does not initially change provider abstraction, provider/model, temperature, max tokens, streaming, thinking configuration or automatic retry.

R3 is one implementation scope with five design concerns:

- R3-A — turn style;
- R3-B — authorized recent discussion context;
- R3-C — Persona behavioral translation;
- R3-D — Prompt Version v2 and phase behavior;
- R3-E — qualitative acceptance.

### R3-A turn style

Prompt v2 teaches the candidate that:

- it is a group-interview candidate, not a report writer, answer generator or moderator;
- one turn normally advances one or two useful points;
- it does not repeat the full question;
- default expression is conversational spoken Chinese;
- Markdown headings and report boilerplate such as `总结如下`、`第一第二第三` and `当前状态分析` are avoided;
- it does not solve the complete task independently every turn;
- it may naturally agree, challenge, supplement, ask, compromise or build on another public contribution;
- it may naturally hand the discussion back to peers;
- approximate turn length is influenced by `persona.average_turn_seconds`.

Post-generation Markdown stripping is not the primary solution. Stored content remains exact plain text; source behavior is improved through the authorized prompt/context.

### R3-B bounded recent public discussion

The only source is durable `participant.utterance.created` version `1` events for the same owner-scoped session. Eligible rows must validate the existing public allowlist:

- actor kind is `HUMAN` or `AI`;
- participant belongs to the same session and agrees with the event actor kind;
- phase is a source-defined floor-enabled phase;
- content is a valid complete string;
- ordering comes from durable discussion sequence.

Pending Human draft, rejected draft, another AI's Private Stance, Persona calibration, logs, provider metadata, prompt diagnostics and system internals are forbidden.

Selection is deterministic:

1. inspect eligible confirmed utterances newest-first;
2. select at most six complete utterances;
3. keep total selected utterance **content** at no more than 4000 Python code points;
4. stop before the first older utterance that would exceed the remaining budget;
5. never truncate an individual utterance merely to fit;
6. render the selected suffix back in chronological sequence order.

This keeps one contiguous recent conversational window. If the newest complete utterance alone exceeds the budget, recent discussion is empty rather than truncated. Current Human content bounds and AI generation limits make that an exceptional safe fallback.

Rendering is compact plain text using the existing safe participant-label semantics:

```text
你：...
AI 候选人 1：...
AI 候选人 2：...
```

Content and line breaks remain exact after the label prefix. Raw event JSON, database rows, IDs, sequence values, action IDs and private/public transport metadata are not rendered to the model. Recent content remains transient generation input and is not duplicated into ordinary logs, request metadata or a new persistence table.

### R3-C Persona behavioral translation

Existing authorized Persona data and provenance remain unchanged. A pure deterministic composition function translates the current AI's fields into concise natural-language guidance without exposing raw numbers to public output.

Current speech-style codes map semantically as:

- `STRUCTURED`: orderly reasoning expressed as spoken discussion, not a report;
- `EXPLORATORY`: willing to add new angles while limiting each turn to a small useful advance;
- `SUPPORTIVE`: acknowledges and integrates others without unconditional agreement;
- `DIRECT`: states judgments directly and politely without suppressing peers.

Unknown speech-style codes fail closed rather than silently inventing behavior.

`average_turn_seconds` renders as the exact approximate speaking duration. Every ordinary unsigned `Probability` Persona field uses exhaustive, non-overlapping Decimal bands across its full persisted `0..1` domain:

- `LOW`: `value <= 0.333`;
- `MEDIUM`: `0.333 < value < 0.667`;
- `HIGH`: `value >= 0.667`.

`support_user_bias` retains its distinct signed `-1..1` meaning and is never passed through the unsigned bands:

- `NEGATIVE`: `value < -0.333` — less inclined to support the Human, without automatic hostility;
- `NEUTRAL`: `-0.333 <= value <= 0.333` — balanced toward the Human;
- `POSITIVE`: `value > 0.333` — more inclined to support the Human, without unconditional agreement or flattery.

Thus every legal persisted value maps to exactly one deterministic behavioral category with no gap or overlap. Exact Chinese behavior phrasing may be frozen during implementation planning, but signed and unsigned semantics cannot be conflated. Raw numeric values remain private implementation input and never enter public UI/output; only concise natural-language behavior guidance enters the private generation context. Stable composition order is unchanged. Guidance covers:

- exact approximate speaking duration from `average_turn_seconds`;
- initiative and interruption tendency;
- cooperation and support-user bias without automatic flattery;
- detail focus and summary tendency;
- stance stability and persuasion threshold;
- novel-idea rate and time awareness;
- bounded error/off-topic tendencies without instructing unsafe or intentionally absurd behavior.

The resulting guidance describes how to participate, not hidden scores. It may say, for example, `说话偏有结构，但不要写报告；通常约40秒；会主动提出判断；关注细节；合作性中等，会礼貌表达不同意见。`

The AI's own authorized Private Stance remains available through the existing boundary. Other participants' Persona parameters or Private Stance never enter its translation.

### R3-D Prompt Version v2 and phase behavior

Published Prompt Version v1 is immutable and must not be edited, overwritten or retired merely to force migration.

R3 introduces a new immutable asset:

```text
prompt_key: AI_CANDIDATE_TURN
version_number: 2
purpose_code: CANDIDATE_UTTERANCE
```

The exact Prompt v2 closed variable vocabulary is:

```text
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
```

No other variable is accepted. `recent_discussion` and `persona_behavior` are transient rendered strings from the pure boundaries above. Existing Question/Persona/Private Stance provenance remains unchanged.

For a **new** deterministic generation request, prompt selection is:

```text
prompt_key = AI_CANDIDATE_TURN
purpose_code = CANDIDATE_UTTERANCE
published_at <= authoritative floor grant time
retired_at is null or retired_at > authoritative floor grant time
order by version_number descending
select one
```

The existing unique `(prompt_key, version_number)` constraint makes the highest valid version deterministic. Prompt v2 affects only grants at or after its publication time. If no valid version exists, progression stops safely before provider I/O.

For an **existing** generation request or replay, the persisted `prompt_version_id`, request timestamp, provider/model and configuration remain authoritative. Restart, replay, new publication or retirement does not silently rebind that request to v2.

Phase guidance remains lightweight and combines the generic behavior below with the existing question-specific `phase_instruction`:

- `OPENING_STATEMENTS`: state an initial position clearly; response to others is optional when context is sparse;
- `EXPLORATION`: add angles and build on earlier contributions;
- `CONFLICT_AND_EVALUATION`: compare, challenge, test assumptions and disagree constructively;
- `CONVERGENCE`: identify tradeoffs, compromise and move toward a shared solution;
- `FINAL_SUMMARY`: concisely synthesize current consensus and remaining disagreement.

There are not five separate prompt systems. One Prompt v2 uses a closed phase-behavior mapping plus the current question-specific instruction.

### R3-E acceptance contract

Future validation has three layers.

1. Structural/pure tests:
   - recent-event allowlist, newest-backward selection, chronological rendering, six-item and 4000-code-point budgets;
   - pending/rejected/private/internal exclusion;
   - deterministic Persona behavioral translation and unknown-code failure;
   - exact v2 closed-variable contract;
   - v1 immutability, effective latest-valid v2 selection and existing-request pinning.
2. Deterministic fake-provider integration:
   - capture the rendered generation input;
   - prove expected prior Human/AI lines, Persona behavior and correct phase guidance are present;
   - prove pending/private/internal sentinels are absent;
   - prove existing request/utterance/floor release/scheduler/runtime persistence paths remain unchanged.
3. Limited real-provider qualitative smoke:
   - only after explicit user approval at execution time;
   - no brittle exact-string CI oracle;
   - no credential, rendered prompt, Private Stance, raw response or verbatim output in governance evidence.

Prepare five fixed qualitative scenarios:

1. opening statement with no recent context;
2. exploration after one Human and one AI contribution;
3. conflict/evaluation requiring a constructive challenge to a prior assumption;
4. convergence requiring tradeoff and compromise rather than a new standalone plan;
5. final summary plus a paired Persona comparison using the same public discussion.

Human review checks:

- no Markdown heading/report template;
- no full-question repetition;
- reasonable spoken-turn length;
- visible response/building on recent discussion when context exists;
- not every turn is a complete standalone solution;
- perceptible behavioral difference between Personas;
- no private/internal leakage.

## Global acceptance and stop conditions

The design is blocked and must return for approval if future implementation requires:

- a schema/migration or public REST/WebSocket contract change;
- a second scheduler, second realtime authority or browser-selected speaker;
- a new frontend global store or business authority in browser storage;
- Redis, queue, worker or multi-worker broadcast architecture;
- provider/model/temperature/max-token/streaming/thinking changes as part of the initial R3 batch;
- a new provider abstraction, CMS, memory/RAG system, scoring/report, voice or fake UI capability;
- transcript/private data entering logs, telemetry, public projections or another participant's prompt;
- mutation of Prompt v1 or rebinding of an existing generation request;
- implementation outside the separately approved future batch.

## Frozen status after this checkpoint

```text
P1 = IN_PROGRESS

P1-5 = IN_PROGRESS
reason = POST_CLOSEOUT_REMEDIATION_OPEN

P1-5A ... P1-5F = historical DONE
P1-5F = DONE
P1-5F-3 = DONE
P1-5F-3A = DONE
P1-5F-3B = DONE
P1-5F-4 = DONE

P1-5R = IN_PROGRESS / DESIGN_FROZEN / IMPLEMENTATION_PLAN_FROZEN
R1 = NOT_STARTED / READY_FOR_IMPLEMENTATION
R2-A = NOT_STARTED / BLOCKED_BY_R1
R2-B = NOT_STARTED / BLOCKED_BY_R2-A
R3 = NOT_STARTED / BLOCKED_BY_R2-B
Final acceptance = NOT_STARTED / BLOCKED_BY_R3

F1 = OPEN
F2 = OPEN
Visual fidelity remediation = OPEN
F3 = OPEN

Implementation plan = FROZEN
Open implementation findings = NONE

P1-5R-DES-001 = CLOSED
Open design findings = NONE
```

No remediation is implemented. The next separately approved action is Batch R1 implementation under the frozen detailed plan.
