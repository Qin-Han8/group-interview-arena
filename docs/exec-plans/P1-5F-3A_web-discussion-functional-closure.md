# P1-5F-3A Web Discussion Functional Closure — Design Freeze

Status: `DESIGN_FROZEN`; `IMPLEMENTATION_COMPLETE`;
`ACTUAL_SOURCE_REVIEW_PASS`; `COMMIT_PUSH_COMPLETE`; `CI_PASS`;
`INDEPENDENT_FINAL_ACCEPTANCE_PASS`; `FINDINGS_NONE_OPEN`; F3A `DONE`

Accepted committed target: `30446af520e55977a7c7a4839e00ab1a0a94d44e`

GitHub Actions: run `32945590023`; all four required jobs `PASS`

Current parent status: `P1 IN_PROGRESS`;
`P1-5 IN_PROGRESS / POST_CLOSEOUT_REMEDIATION_OPEN`;
P1-5F/F3/F3A/F3B/F4 retain historical `DONE`;
`P1-5R IN_PROGRESS / DESIGN_FROZEN`; R1/R2-A/R2-B/R3 `NOT_STARTED`

Target version: `V0.1 Internal Validation`

Design-freeze baseline: clean committed `main` at
`9fd31d0` (`9fd31d0 P1-5F-2: fix: restore realtime command replay delivery`),
equal to `origin/main`

Immutable product baseline:
[`PROJECT_MASTER_PLAN.md`](../PROJECT_MASTER_PLAN.md), SHA-256
`2388a9660320406cb35d5354126ad71c6849a98db7c4a356796ca951bf372f26`

Parent contract:
[`P1-5_ai-runtime-foundation.md`](P1-5_ai-runtime-foundation.md), especially
the frozen P1-5F-1 contract

Implemented backend transport:
[`P1-5F-2_backend-text-discussion-transport.md`](P1-5F-2_backend-text-discussion-transport.md)

## Goal

Freeze the Web architecture, behavior, recovery semantics, file boundary and
TDD acceptance matrix required to close the functional text-discussion
experience on top of the completed P1-5F-2 backend transport.

P1-5F-3A later implementation must let an authenticated user restore and read
the confirmed discussion transcript, prepare text at any time, submit only
against the exact authoritative Human floor, distinguish draft/pending/
rejected/confirmed content, recover without losing confirmed history, and show
only public floor-derived AI waiting/failure information.

This checkpoint is documentation only. It does not implement or modify Web
runtime, tests, generated OpenAPI, backend transport, schema, migrations,
dependencies, lockfiles, CI, provider/runtime, scheduler or orchestration.

## Context and authority

- The Master Plan requires a desktop-Web text discussion for V0.1, a
  server-authoritative controlled-turn simulation, recoverable sessions and a
  visible basic utterance history. It does not authorize a free-chat client or
  Browser-owned scheduler.
- `ADR-006` assigns resource/snapshot/history reads to REST and active-session
  commands/ordered events to WebSocket. No second realtime channel is needed.
- `ADR-007` makes FastAPI OpenAPI authoritative for REST. The handwritten
  realtime TypeScript contract remains a strict derivative of the independently
  versioned backend WebSocket contract.
- `ADR-011` requires feature-local Web structure and forbids speculative
  framework layers. `ADR-008` and `ADR-009` keep Redis and a task queue
  deferred.
- P1-5F-1 freezes the Human command, unified utterance event, transcript REST,
  floor v1/v2 compatibility, memory-only pending identity and snapshot-first
  recovery contract.
- P1-5F-2 implements that backend contract and the generated REST derivative.
  F3A consumes it without changing its semantics.

Authority order for this plan remains:

```text
PROJECT_MASTER_PLAN
  -> Accepted Decisions
  -> P1-5/P1-5F-1 frozen contract
  -> P1-5F-2 implemented backend transport
  -> this Web design
  -> later Web implementation
```

## Approved phase structure

`P1-5F-3 — Web Discussion Experience` is split as follows:

- `P1-5F-3A — Web Discussion Functional Closure`
  - this checkpoint: `DESIGN_FROZEN`;
  - Web implementation: `IMPLEMENTATION_NOT_STARTED`;
  - closes discussion behavior in the existing `SessionPanel` without a full
    visual/page-layout redesign.
- `P1-5F-3B — Complete Discussion Page Composition`
  - `NOT_STARTED`;
  - later composes the complete desktop question/discussion/process-status
    page and owns the full three-region layout.
- `P1-5F-4 — Composition E2E + Independent Acceptance`
  - `NOT_STARTED`;
  - later owns complete cross-layer composition acceptance and independent
    review.

F3A may add the minimum functional sections to the current panel. It must not
pre-implement F3B layout work. F3B must be able to rearrange the resulting UI
without redesigning protocol, pending-command or transcript semantics.

## Scope

Later, separately approved F3A implementation includes only:

- a typed owner-only transcript REST caller with complete bounded pagination;
- strict handwritten Web parsing for the already-implemented Human command
  result and unified Human/AI utterance event;
- a small pure TypeScript confirmed-transcript merge model;
- one memory-only pending command owned by the realtime client;
- exact-floor Human submission and recoverable rejected-content handling;
- confirmed transcript, composer, send availability, pending/rejection,
  derived AI waiting/interruption and recovery status in the existing
  `SessionPanel`;
- targeted unit/component tests and one deterministic Chromium Human-submit /
  server-confirmation / reload-restore vertical slice, including semantic
  persistence verification in the existing repository E2E harness;
- minimal current-state documentation after implementation.

## Explicit non-goals

F3A does not include:

- backend production source, REST/WS semantics or a second realtime
  protocol/channel; the sole non-Web test-file exception is the existing
  `apps/api/tests/integration/browser_e2e.py` harness, and only for F3A
  persistence verification;
- ORM models, schema, migration, generated OpenAPI manual edits or a Human
  utterance table;
- dependencies, lockfiles, CI, Docker/infra or deployment topology;
- scheduler, AI runtime, provider, prompt, model configuration or real model
  calls;
- streaming tokens, generation lifecycle events, provider status, retry
  status, ETA or Browser-owned AI timeout;
- REST utterance write fallback, multi-pending queue, failed-message queue or
  offline creation of a new Human submit;
- localStorage/sessionStorage persistence of draft, pending command,
  transcript authority or session authority;
- Redux, Zustand, an app-global discussion store, a frontend business state
  machine, controller/service framework or speculative provider abstraction;
- F3B page composition, three-column redesign, avatar/animation/polish system,
  virtualized history or a “new messages” subsystem;
- Markdown/HTML rich text, edit/delete/reaction behavior, voice, ASR or TTS;
- memory/RAG, scoring/report, billing/quota/payment or P2–P6 capabilities.

## Approved frontend architecture — Option B

Option B is the frozen architecture:

```text
FastAPI REST snapshot + transcript       ordered WebSocket stream
                 |                                  |
                 +---------- SessionPanel ----------+
                              |       |
                  pure transcript     realtime client
                  merge/model         pending identity/retry
```

Responsibilities are exact:

- `lib/realtime/contract.ts` parses protocol envelopes independently of
  React. It performs strict shape/version/action validation and no UI work.
- `lib/realtime/client.ts` owns the maximum-one memory-only pending command,
  exact resend identity and connection/recovery sequencing. It does not own
  session/phase/floor truth.
- the authoritative `SessionSnapshot` continues to own current session,
  phase, participants and floor state.
- `features/sessions/discussion-transcript.ts` is a small, framework-independent
  pure TypeScript module that owns confirmed utterance merge/dedupe/order/
  identity-conflict detection only.
- `SessionPanel` coordinates REST loading, local editable draft, recovery
  presentation, transcript rendering and the public-state-derived UI. It does
  not implement a duplicate backend lifecycle/floor state machine.

Option B is not a temporary demo architecture. It is an acceptable commercial
architecture while discussion state remains feature-local. User volume alone
does not justify migration.

The first formal `B / B+ / C` reassessment occurs only after the P2 speech loop
is complete and only from demonstrated frontend state complexity. If change is
then justified, prefer a feature-scoped discussion store/controller, not an
app-global store.

Migration-friendly constraints are frozen now:

- protocol parsing stays independent of React;
- transcript merge stays pure and framework-independent;
- pending command identity stays in the realtime client;
- server snapshot stays authoritative;
- no duplicated client business state machine is introduced.

## Four content states

The Web must keep these concepts distinct:

### A. Draft

- current local textarea text;
- always editable while a discussion session is loaded, including before the
  Human owns the floor and while another command is pending;
- non-authoritative, not persisted and not bound to a floor while typing.

### B. Pending Human submit

- exact `action_id + floor_grant_id + content` captured at click time;
- owned and retried by the realtime client in memory only;
- maximum one pending client command across lifecycle and utterance commands;
- not a transcript item and not a formal speech bubble;
- reconnect resends the same exact action/floor/content;
- never written to localStorage/sessionStorage.

### C. Confirmed transcript

- durable server-confirmed `participant.utterance.created` facts only;
- sourced from transcript REST and the ordered formal WS stream;
- the only content rendered as normal discussion speech.

### D. RejectedDraft

- only the most recently explicitly rejected Human submission content;
- exact content, memory-only, not transcript, not a queue and not persisted;
- displayed separately from any newer draft;
- restored or used to replace the current draft only through an explicit user
  action.

No state silently moves content from B or D into C. Only a durable server fact
creates C.

## Human content and validation contract

The Browser mirrors, but never replaces, the F1/F2 server authority:

```json
{
  "floor_grant_id": "UUID4",
  "content": "exact string"
}
```

Rules are exact:

- length is `1..4000` Unicode code points;
- `strip()`-equivalent validation must find at least one non-whitespace code
  point;
- U+0000 is forbidden;
- no Unicode normalization;
- no trim before send;
- no automatic truncation;
- accepted input persists exactly.

JavaScript must count Unicode code points, not UTF-16 code units. An astral
emoji counts as one. A pure helper using the language string iterator, such as
`Array.from(content).length`, is acceptable; `.length` is not.

The UI shows a lightweight `current / 4000` count. Enter inserts a newline.
Ctrl+Enter or Cmd+Enter submits only when submission is currently allowed.
Receiving a Human floor does not steal focus.

The later implementation may keep the small pure draft inspection helper next
to the realtime submission boundary and cover it directly in existing tests.
It must not put reusable/non-trivial Unicode validation into React effects or
JSX event branches. If a new production module beyond the frozen file boundary
is genuinely necessary, implementation stops and explains the need first.

## Send availability and exact-floor binding

The textarea remains editable. Send is enabled only when all are true:

1. the authoritative session is in one of the five floor-enabled active
   phases: `OPENING_STATEMENTS`, `EXPLORATION`,
   `CONFLICT_AND_EVALUATION`, `CONVERGENCE`, `FINAL_SUMMARY`;
2. `snapshot.floor.current_grant` exists;
3. its participant is the safe directory entry with `actor_kind = HUMAN`;
4. realtime connection state is exactly `connected`;
5. no lifecycle or utterance command is pending;
6. the exact current draft passes the Browser mirror validation.

At submit time the handler must re-read the latest authoritative snapshot from
the current ref, not a render-time captured grant. It then:

1. verifies the current grant still belongs to the Human;
2. captures the exact current `floor_grant_id`;
3. captures the exact current content;
4. asks the realtime client to generate exactly one UUID4 `action_id`;
5. sends `participant.utterance.submit` v1 with the exact binding.

The draft is never bound while typing. The Browser does not create a new Human
submit while disconnected or reconnecting.

## Realtime derivative contract

The strict handwritten derivative must add the already-implemented backend
contract without weakening existing validation.

Client command v1:

```text
schema_version = 1
type = participant.utterance.submit
session_id = UUID4
action_id = UUID4
payload exactly:
  floor_grant_id = UUID4
  content = string
```

Formal event v1:

```text
schema_version = 1
type = participant.utterance.created
session_id = UUID4
sequence = positive safe integer
occurred_at = aware timestamp
action_id = UUID4 for HUMAN, null for AI
payload exactly:
  utterance_id = UUID4
  participant_id = UUID4
  actor_kind = HUMAN | AI
  floor_grant_id = UUID4
  phase = one of the five floor-enabled phases
  content = string
```

The parser rejects unsupported schema versions, extra fields, invalid actor /
action combinations and invalid UUID/phase/content types. Historical floor v1
and additive floor v2 remain version-discriminated and strict; v1 nullability
must not be relaxed. `UTTERANCE_REJECTED` is added to the safe error-code
allowlist.

No generation request, provider/model/configuration, prompt, Private Stance,
internal action or failure taxonomy may enter the derivative.

## Realtime client pending and recovery boundary

The existing client remains one feature-local connection owner. Its internal
pending union expands to include `ParticipantUtteranceSubmitCommand`; it does
not gain a command queue.

The later interface must provide the equivalent of:

- one `submitHumanUtterance(floorGrantId, exactContent)` operation that mints
  at most one UUID4 when no command is pending;
- a boolean/global pending callback so lifecycle and Send controls share the
  single-command exclusion;
- a Human-pending callback exposing the exact memory-only pending payload for
  the local status presentation;
- a rejected-submission callback that carries the exact content into the
  single `RejectedDraft` slot;
- an authoritative recovery callback/load result containing both snapshot and
  complete transcript;
- a callable recovery trigger for transcript identity conflicts.

Exact exported symbol names may follow existing project naming, but these
ownership boundaries may not move into React or an app-global store.

After valid send:

- the realtime client owns the exact pending command;
- the textarea may clear immediately;
- the user may start editing the next draft;
- a second submit remains disabled until the pending command is confirmed or
  rejected;
- a lightweight local status may show
  `待服务器确认（尚未进入讨论记录）` plus the exact pending content;
- the pending status has no sequence and is never rendered as a formal
  transcript item.

Pending confirmation has two equal authoritative paths:

1. matching WS `participant.utterance.created.action_id`;
2. matching REST transcript item `action_id` after reconnect/recovery.

Both clear the same pending identity. A duplicate WS replay may confirm the
pending command but does not add a second transcript item.

## Rejection and action-conflict recovery

`UTTERANCE_REJECTED` is recoverable and keeps the socket open. For a matching
pending Human action the client must:

- clear that pending command;
- create no transcript item;
- retain the exact content in the one `RejectedDraft` slot;
- show safe copy such as
  `这条发言当前无法提交，请确认发言机会后重试。`;
- disclose no stale-floor, scheduler, AI-owner, deadline or phase-reconciliation
  reason.

If content `C` is rejected after the user has started a newer draft `D`, the
Web never overwrites `D`. It displays `C` separately and offers an explicit
restore/replace action. Replacing a non-empty draft must be clearly initiated
by the user; there is no automatic merge.

For matching `ACTION_ID_CONFLICT`:

- never mint a replacement action and silently retry;
- stop retrying the conflicted command;
- preserve its exact content in the same one-item recovery presentation so it
  is not lost;
- show only a safe generic state-integrity/reload message;
- trigger authoritative snapshot + transcript recovery;
- create no transcript item unless durable REST/WS truth later proves it.

This is not a general failed-message queue.

## Initial restore and transcript pagination

Initial load and browser reload use the exact order:

```text
1. GET authoritative session snapshot
2. capture snapshot watermark S = last_sequence
3. GET complete authoritative transcript
4. publish confirmed transcript to the UI
5. connect WS with after_sequence = S
```

The Web must not intentionally open the socket before transcript restore and
race the initial REST load.

Transcript REST pagination is:

- `GET /sessions/{session_id}/utterances`;
- exclusive full-discussion `after_sequence` cursor;
- server default limit `100`, maximum `200`;
- fetch successive pages until `next_after_sequence = null`;
- no infinite-scroll or history virtualization in F3A.

The API wrapper should request `limit = 200` for the finite F3A full-history
load and must fail safely if a non-null next cursor does not advance, avoiding
an accidental infinite request loop. It does not add a CSRF header to the GET.

Transcript sequences are legitimately non-contiguous because they are a
filtered view of the full discussion sequence. Transcript loading and merging
must never perform transcript-only sequence-gap validation.

## Pure confirmed-transcript model

Create:

`apps/web/src/features/sessions/discussion-transcript.ts`

The module is pure and framework-independent:

- no React;
- no WebSocket;
- no fetch/network;
- no global mutable state.

It owns only confirmed utterance merge, dedupe by `utterance_id`, authoritative
sequence ordering and same-identity conflict detection.

Authoritative fields are exactly:

- `utterance_id`;
- `sequence`;
- `occurred_at`;
- `action_id`;
- `participant_id`;
- `actor_kind`;
- `floor_grant_id`;
- `phase`;
- `content`.

Merge rules:

1. unseen `utterance_id` → add and order by `sequence`;
2. same `utterance_id` and every authoritative field identical → replay,
   ignore;
3. same `utterance_id` and any authoritative field differs → conflict and
   request a full authoritative session + transcript recovery.

The model never uses last-write-wins, “WS always beats REST” or transcript
sequence-gap detection. It never stores pending/rejected items.

## Non-destructive reload and conflict recovery

Reconnect, a full-WS gap, `SEQUENCE_AHEAD` and transcript identity conflict all
use one authoritative recovery path:

1. keep the currently confirmed transcript rendered;
2. show a non-destructive `正在同步讨论记录…`-style status;
3. load authoritative snapshot, capture its watermark, and load the complete
   transcript;
4. reconcile pending from transcript action IDs;
5. apply the newly loaded snapshot/transcript only after both loads and pure
   merge validation succeed;
6. reconnect the WS from the captured snapshot watermark.

The implementation does not intentionally set transcript to `[]` during
recovery. A failed recovery leaves the last confirmed transcript visible and
offers safe retry through the existing bounded connection behavior.

When recovery succeeds, stale connection-error banners must be cleared or
superseded by the healthy connection state. Connection/recovery status is
separate from rejected-content copy so one does not erase the other.

The complete WS stream keeps the existing exact-next, duplicate and gap
behavior. Only transcript-only data skips gap checks.

## Session projection integration

`participant.utterance.created` consumes one full-stream sequence but does not
change session status, timing or floor ownership. `projectSessionEvent(...)`
must handle it explicitly by advancing the safe snapshot watermark/timestamps
without treating its payload as a floor event.

`SessionPanel` separately feeds the same event into the pure transcript merge.
Floor release/grant events continue to update only the authoritative floor
projection. The Browser never infers that an utterance itself releases a floor
or chooses the next speaker.

## AI waiting and interruption UX

No public generation lifecycle exists. The Web must not invent model thinking,
generation started, token streaming, provider busy, retry state, ETA,
provider/model name or failure taxonomy.

AI waiting is derived only when:

```text
current authoritative floor participant actor_kind = AI
AND
no confirmed AI utterance exists for that exact floor_grant_id
```

Then the UI may show `AI 候选人 X 正在准备发言…`, using only the safe
participant directory/seat mapping. The notice disappears immediately when a
matching confirmed AI utterance arrives, even before the later floor-release
event.

If an AI grant ends with `floor.released / INTERRUPTED` and no confirmed AI
utterance exists for that exact grant, `SessionPanel` may show once per
in-memory grant a generic local notice:

`这次 AI 发言未完成，讨论将继续。`

It exposes no provider/runtime details. The Browser never selects the next
speaker, retries the AI or starts its own generation timeout. While the
connection is reconnecting/synchronizing, recovery status takes precedence
over stale AI-waiting presentation.

## Minimum F3A UI and accessibility

F3A adds functional sections to the existing `SessionPanel` only:

- confirmed discussion transcript;
- Human textarea/composer;
- readable send availability reason/status;
- pending local status with exact content;
- rejected-draft recovery presentation;
- derived AI waiting state;
- safe generic one-time AI interrupted notice;
- reconnect/synchronizing status.

Each confirmed transcript item shows:

- speaker label;
- lightweight phase label;
- exact plain-text content with line breaks preserved.

Speaker labels use only the safe participant directory:

- Human: `你`;
- AI candidates: `AI 候选人 1 / 2 / 3`, ordered by safe seat mapping.

Backend Persona labels such as `强势控场者`, `固执反对者` or
`逻辑分析者` never appear. Utterance content is rendered as text, not
Markdown or HTML. The empty state explains that server-confirmed speech will
appear there.

Accessibility requirements:

- the textarea has a real accessible label;
- disabled Send always has an adjacent readable reason/status;
- important pending/rejection/recovery changes use appropriate `aria-live`
  regions without announcing every transcript token or causing excessive
  chatter;
- receiving a floor does not force focus.

Scroll behavior remains small:

- if the user is already near the transcript bottom, a newly confirmed item
  may auto-follow;
- if the user intentionally scrolled upward, do not force them to the bottom;
- no virtual list, “N new messages” subsystem or complex scroll state machine.

## Expected implementation file boundary

Later F3A implementation is expected to primarily touch:

- `apps/web/src/lib/api/client.ts`;
- `apps/web/src/lib/api/client.test.ts` for transcript pagination behavior;
- `apps/web/src/lib/realtime/contract.ts`;
- `apps/web/src/lib/realtime/contract.test.ts`;
- `apps/web/src/lib/realtime/client.ts`;
- `apps/web/src/lib/realtime/client.test.ts`;
- `apps/web/src/lib/realtime/projection.ts`;
- `apps/web/src/lib/realtime/projection.test.ts`;
- `apps/web/src/features/sessions/discussion-transcript.ts` (new);
- `apps/web/src/features/sessions/discussion-transcript.test.ts` (new);
- `apps/web/src/features/sessions/session-panel.tsx`;
- `apps/web/src/features/sessions/session-panel.test.tsx`;
- `apps/web/e2e/session.spec.ts`;
- `apps/api/tests/integration/browser_e2e.py` (existing test harness and
  persistence verifier only; the sole authorized non-Web test file);
- minimal current-state/docs files after implementation.

The generated REST schema is already present from F2 and must not be manually
edited. This list is not authorization to implement. If implementation proves
another production file is genuinely required, stop and explain why before
broadening scope. Additional focused tests in an existing corresponding test
file are allowed when they exercise the frozen production boundary. No other
non-Web test file is authorized. The `browser_e2e.py` exception does not
authorize backend production, contract, schema, migration, provider/runtime,
CI or infrastructure changes.

F3A must not simply dump protocol, merge, Unicode validation and recovery
logic into `SessionPanel`. Pure merge belongs in the new transcript module;
pending identity belongs in the realtime client; protocol validation belongs
in the contract module; network pagination belongs in the API client.

## Later implementation order and TDD gates

Every behavior task starts with a meaningful failing test after separate
implementation approval.

### Task 1 — REST transcript loader and strict derivative contract

- Add failing API-client tests for exclusive cursor pagination through all
  pages, maximum-200 requests, null termination and non-advancing-cursor safe
  failure.
- Add failing contract tests for Human and AI utterance events,
  actor/action nullability, unsupported version, extra fields and
  `UTTERANCE_REJECTED`.
- Implement only the typed transcript loader and strict handwritten parser.
- Rerun existing floor v1/v2 regression tests unchanged.

### Task 2 — Pure confirmed-transcript merge

- Add failing pure tests for non-contiguous sequences, REST+WS identical replay,
  ordering and each authoritative-field conflict.
- Implement the smallest immutable merge/model module.
- Prove the module has no React/network/global-state dependency.

### Task 3 — Realtime pending identity and rejection recovery

- Add failing client tests for one action generation, exact click-time floor
  and content, same reconnect resend, no second action mint, WS/REST
  confirmation, recoverable rejection and action-conflict no-retry.
- Extend the existing one-pending union and authoritative recovery callback;
  do not add a queue.
- Preserve lifecycle start/abort and bounded reconnect regressions.

### Task 4 — Snapshot/transcript projection and non-destructive recovery

- Add failing projection/component tests proving utterance events advance the
  full-stream watermark without changing floor, complete restore precedes WS,
  confirmed transcript stays visible during recovery, and identity conflict
  requests full recovery.
- Implement snapshot → transcript → WS initial ordering and the shared
  recovery bundle path.
- Clear stale connection error presentation after successful recovery.

### Task 5 — Composer, pending and rejected-draft UX

- Add failing component tests for editable textarea, six send gates, exact
  whitespace, code-point boundary, keyboard behavior, next-draft editing,
  pending-not-transcript and explicit rejected-content restore/replace.
- Implement only the existing-panel functional sections and pure click-time
  submission boundary.
- Do not implement F3B layout.

### Task 6 — AI waiting/interruption and transcript presentation

- Add failing tests for safe speaker labels, plain text/line breaks, empty
  transcript copy, exact-grant AI waiting removal, generic one-time
  `INTERRUPTED` notice and reconnect-status precedence.
- Implement only public-fact-derived presentation and the small near-bottom
  auto-follow behavior.

### Task 7 — Deterministic Chromium Human vertical slice

- Extend the existing authenticated PostgreSQL/Uvicorn/Next/Chromium flow with
  a deterministic Human floor, exact submit command, server-confirmed render,
  REST reload restore and browser-storage absence proof.
- Update only the existing `browser_e2e.py` persistence verifier to replace
  its pre-F3A fixed totals (`2` actions, `last_sequence = 10`, one grant and
  one release) with semantic assertions. It must prove:
  - the final session is `COMPLETED` with no current floor;
  - `DiscussionEvent` sequence is contiguous from `1` through the durable
    `SimulationSession.last_sequence`;
  - exactly one durable `participant.utterance.submit` `SessionAction` exists
    for the tested contribution;
  - exactly one matching Human `participant.utterance.created` event exists;
  - its exact content, floor grant, participant and phase are preserved;
  - the matching `SPEAKER_FINISHED` release exists, has the Human submit action
    as causation, and immediately follows the utterance event;
  - later legitimate scheduler/floor events may exist and do not invalidate
    the verifier.
- Preserve existing floor v2, duplicate replay and API-restart regressions.
- Use no real provider/model call and add no provider credential/configuration
  to the harness. AI rendering/waiting may use deterministic fixtures;
  complete Human→AI composition remains F4 acceptance.

No task stages, commits or pushes unless separately authorized.

## Frozen TDD acceptance matrix

### Contract

- parse canonical Human utterance created;
- parse canonical AI utterance created;
- require non-null Human `action_id`;
- require null AI `action_id`;
- reject wrong actor/action combinations;
- reject unsupported utterance schema;
- reject extra envelope or payload fields;
- preserve strict historical floor v1 and additive floor v2 regressions.

### Transcript

- accept non-contiguous transcript sequences;
- dedupe identical REST + WS replay;
- sort by authoritative sequence;
- report a conflict when the same `utterance_id` differs in any authoritative
  field.

### Realtime client

- submit generates one UUID4 action;
- command uses exact click-time floor grant and exact content;
- reconnect resends the same action/floor/content;
- no second action is minted;
- matching WS durable event clears pending;
- matching restored REST transcript clears pending;
- `UTTERANCE_REJECTED` is recoverable and the socket remains usable;
- rejected exact content is available to recovery UX;
- `ACTION_ID_CONFLICT` never silently retries with a new identity.

### UI

- AI floor: textarea editable, Send disabled;
- Human floor + connected: Send enabled when content is valid;
- reconnecting: draft preserved, Send disabled;
- pending content is not transcript;
- pending allows editing the next draft but not submitting it;
- exact whitespace/content is preserved;
- astral emoji/code-point 4000 boundary is correct;
- rejected `C` never silently overwrites newer draft `D`;
- confirmed Human utterance appears once;
- confirmed AI utterance appears once;
- matching AI utterance removes AI waiting;
- AI interrupted notice is generic only;
- reconnect keeps confirmed transcript visible;
- transcript identity conflict triggers authoritative reload;
- terminal, preparation, no-floor and non-Human floor disable submit.

### Chromium vertical slice

- authenticated browser;
- create and start session;
- obtain Human floor;
- enter exact text;
- submit `participant.utterance.submit`;
- durable Human utterance renders only after server confirmation;
- reload restores the exact utterance from REST transcript;
- browser storage contains no pending action/content/authoritative session
  data;
- final durable session is `COMPLETED` with null current floor;
- persisted event sequence is contiguous from `1` through authoritative
  `last_sequence`;
- exactly one durable Human submit action and exactly one matching Human
  utterance event preserve the tested action, content, grant, participant and
  phase;
- its matching `SPEAKER_FINISHED` release has the same causation, follows the
  utterance event immediately, and later legitimate scheduler/floor facts do
  not cause a fixed-total failure;
- existing floor v2, duplicate replay and restart regressions remain passing.

No real model/provider call is required for F3A automated validation. Complete
real Human→AI composition belongs to later F4 controlled acceptance.

## Later implementation validation gates

After focused TDD gates pass, the separately approved implementation must run:

- frozen dependency/lock checks without changing manifests;
- Web Prettier check, ESLint, TypeScript typecheck and complete Vitest suite;
- Web production build;
- FastAPI OpenAPI derivative drift check without regenerating a manual delta;
- the scoped deterministic Chromium vertical slice and existing session
  regressions;
- `git diff --check`;
- Master Plan SHA-256 verification;
- explicit no-diff checks for backend production, every non-Web test except
  the exact `apps/api/tests/integration/browser_e2e.py` verifier exception,
  generated OpenAPI, schema/migrations, dependencies/lockfiles, CI,
  provider/runtime and infra; the allowed harness diff must be persistence
  verification only;
- staged count zero and an honest Git status.

## Stop conditions for later implementation

Stop before implementation or scope expansion if the frozen behavior requires:

- backend, public F1/F2 semantic, schema or migration change;
- another realtime protocol/channel;
- a multi-pending or failed-message queue;
- Redux, Zustand or an app-global store;
- a public AI generation lifecycle or Browser-owned AI timeout;
- scheduler, runtime or provider changes;
- Browser persistence of pending/draft;
- weakening floor v1/v2 validation;
- F3B layout work;
- an unapproved new dependency;
- a production file outside the frozen boundary that is necessary for
  correctness;
- any non-Web test file other than the exact existing
  `apps/api/tests/integration/browser_e2e.py` harness.

## Decisions frozen by this plan

- Option B is the current commercial-capable feature-local architecture.
- The first B/B+/C checkpoint is after the P2 speech loop and is complexity-
  driven, not volume-driven.
- Draft, pending, confirmed transcript and RejectedDraft are separate states.
- Exact floor binding happens only at submit time from the latest authoritative
  grant.
- The realtime client owns one memory-only pending command and exact resend.
- Confirmed transcript merge is pure, identity-based and never gap-validates a
  transcript-only sequence.
- Initial and recovery load are snapshot → complete transcript → WS.
- Recovery preserves confirmed history on screen.
- AI waiting/failure UX derives only from public floor and confirmed utterance
  facts.
- F3A closes functional behavior; F3B owns complete page composition; F4 owns
  composition E2E and independent acceptance.

No new Accepted ADR is required. This design specializes existing accepted
REST/WS, feature-based frontend and server-authority decisions without changing
the Master Plan.

## Risks and controls

- **Duplicate frontend authority:** snapshot/floor truth stays server-owned;
  Browser helpers only derive presentation and send eligibility.
- **Lost or overwritten text:** pending and RejectedDraft preserve exact
  content; restore/replace is explicit and never overwrites a newer draft.
- **Duplicate formal speech:** only durable utterance facts enter transcript;
  identity replay dedupes and pending is never a speech bubble.
- **Unicode corruption:** code-point counting uses the string iterator; the
  Browser never trims, normalizes or truncates accepted content.
- **Reconnect flicker/data loss:** confirmed transcript remains rendered until
  a complete authoritative recovery bundle is safely applied.
- **False gap:** gap checks remain on the complete WS stream only, never the
  filtered transcript.
- **Provider leakage:** AI UI uses public floor/utterance/release facts only.
- **F3B contamination:** F3A adds functional sections without a page-layout
  redesign or visual system.
- **State-framework overreach:** no global store/controller is introduced
  before demonstrated complexity and the post-P2 checkpoint.
- **Brittle E2E totals:** the persistence verifier asserts the Human action,
  utterance, release, ordering, terminal state and contiguous authoritative
  sequence semantically; it does not reject legitimate later scheduler/floor
  facts because an obsolete fixed count changed.

## Design self-review

Reviewed against the Master Plan, parent P1-5 plan, frozen P1-5F-1 contract,
implemented P1-5F-2 plan, `docs/API.md`, actual current Web source and the
corresponding unit/E2E tests.

Results:

- no duplicated frontend session/floor authority;
- no command queue or app-global store;
- no hidden provider/generation state;
- no transcript-only gap detection;
- no content trim, normalization or truncation;
- exact-floor binding occurs at click-to-submit;
- pending never becomes formal transcript;
- rejection cannot silently lose or overwrite newer user text;
- restore retains confirmed history and avoids intentional blank flicker;
- F3B complete composition remains separate;
- post-P2 B/B+/C checkpoint is explicit;
- no speculative commercial framework or deferred infrastructure is added;
- the sole non-Web `browser_e2e.py` test-harness exception is persistence-only
  and does not expand backend production or public-contract scope;
- no contradiction with F1/F2 semantics was found;
- no stop condition was triggered.

## Design-freeze validation

This docs-only checkpoint requires only:

- changed-file scope inspection;
- Markdown relative-link/final-newline checks;
- Master Plan SHA-256 verification;
- proof of no runtime/test/generated/schema/migration/dependency/CI diff;
- `git diff --check`;
- staged/untracked status inspection.

No Web/API/provider/browser test is required for a documentation-only design
freeze.

## Progress

- Design recovery and actual-source inspection: completed.
- Option B architecture and functional behavior: `DESIGN_FROZEN`.
- E2E harness/persistence-verifier boundary amendment: `DESIGN_FROZEN`.
- F3A Web implementation: `IMPLEMENTATION_COMPLETE`；external actual-source
  implementation review `PASS` after F3A-FINAL-001 remediation；findings none
  open；Tasks 1–7 and final code gates GREEN.
- Commit/push: `COMPLETE` at accepted target
  `30446af520e55977a7c7a4839e00ab1a0a94d44e`.
- CI: `PASS`；GitHub Actions run `32945590023` passed all four required jobs.
- Independent final acceptance: `PASS`；findings none；F3A is `DONE`.
- F3B complete discussion page composition: historical `DONE`.
- F4 composition E2E + independent acceptance: historical `DONE`.
- New decisions or unresolved F3A design questions: none.
- Stage/commit/push authorization: none.
