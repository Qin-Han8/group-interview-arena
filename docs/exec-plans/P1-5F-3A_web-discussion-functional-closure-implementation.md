# P1-5F-3A Web Discussion Functional Closure Implementation Plan

> For agentic workers: execute this plan task-by-task using the project phase
> runner / approved execution workflow. Every implementation task is TDD: RED
> first, then minimal GREEN, then regression verification. Do not commit or
> push unless separately authorized.

Status: `IMPLEMENTATION_PLAN_FROZEN`; `IMPLEMENTATION_COMPLETE`;
`ACTUAL_SOURCE_REVIEW_PASS`; `COMMIT_PUSH_COMPLETE`; `CI_PASS`;
`INDEPENDENT_FINAL_ACCEPTANCE_PASS`; `FINDINGS_NONE_OPEN`; F3A `DONE`

Accepted committed target: `30446af520e55977a7c7a4839e00ab1a0a94d44e`

GitHub Actions: run `32945590023`; all four required jobs `PASS`;
F3B/F4 retain historical `DONE`; current parents are `P1-5 DONE` and
`P1 DONE / CLOSED`; P1-5R and its post-closeout remediation/review are
`CLOSED`; open findings `NONE`

**Goal:** Close the V0.1 browser text-discussion functional loop on the
completed F2 backend transport: durable transcript restore, exact-floor Human
submit, one memory-only pending command, rejection recovery, safe AI
waiting/failure presentation, and deterministic browser verification.

**Architecture:** Use frozen Option B. REST owns snapshot/history reads, the
existing realtime client owns ordered WebSocket delivery and the single
pending command, `SessionSnapshot` remains authoritative for session/floor
state, a small pure transcript module owns confirmed utterance merge semantics,
and `SessionPanel` coordinates feature-local UI state. No new store,
framework, queue, backend contract or realtime channel is introduced.

**Tech stack:** Next.js 16 / React 19 / TypeScript / `openapi-fetch` / Vitest /
Testing Library / Playwright.

**Spec:**
[`P1-5F-3A_web-discussion-functional-closure.md`](P1-5F-3A_web-discussion-functional-closure.md)

## Global constraints

- The immutable Master Plan SHA-256 must remain
  `2388a9660320406cb35d5354126ad71c6849a98db7c4a356796ca951bf372f26`.
- Production implementation is Web-only.
- Do not change backend production, REST/WS semantics, schema, migrations,
  provider/runtime, scheduler or orchestration.
- Do not change dependencies, `package.json`, `pnpm-lock.yaml`, `uv.lock` or
  workspace manifests.
- Do not change CI, Docker, infrastructure or deployment configuration.
- Read `apps/web/src/lib/api/generated/schema.d.ts`; never edit it manually.
- Do not add Redux, Zustand, an app-global store, a controller framework or a
  frontend business state machine.
- Do not add a second realtime channel.
- Keep one pending command total across Start, Abort and Human submit; do not
  add a pending queue or failed-message queue.
- Do not persist draft, pending command, confirmed transcript authority or
  session authority in `localStorage` or `sessionStorage`.
- Do not expose a public generation lifecycle, provider status, retry state,
  ETA, model identity or Browser-owned AI timeout.
- Automated validation must perform no real provider/model call.
- Do not implement the F3B three-column/page redesign.
- Preserve strict historical floor-event v1 and additive floor-event v2 parser
  semantics without weakening either version.
- Preserve exact Human content: no trim, Unicode normalization, truncation or
  hidden content replacement.
- Count Human content length by Unicode code points, not UTF-16 code units.
- Bind the exact Human floor only at click-to-submit from the latest
  authoritative `snapshotRef.current`.
- Pending content is never formal transcript content.
- Transcript-only event sequences may be non-contiguous and must never trigger
  a sequence-gap reload.
- Initial and recovery authority is snapshot plus complete transcript, with
  the WebSocket cursor taken only from `snapshot.last_sequence`.
- Keep confirmed transcript visible while recovery is running or fails.
- The sole non-Web test exception is
  `apps/api/tests/integration/browser_e2e.py`, and only its test-harness /
  persistence-verification behavior may change.
- Do not replace old E2E fixed totals with new guessed totals; assert the
  frozen semantic persistence invariants instead.
- If correctness requires another production file or another non-Web test
  file, stop and report before changing scope.
- Do not stage, commit or push unless separately authorized.

## Baseline and actual-source assessment

- Repository root: current `group-interview-arena` checkout.
- Planning baseline: `main` at
  `9fd31d0b581d771258237a86b46da2e005bfcbfa`.
- The generated derivative already exposes:
  - `components["schemas"]["TranscriptResponse"]`;
  - `components["schemas"]["TranscriptUtteranceResponse"]`;
  - `GET /sessions/{session_id}/utterances` with optional
    `after_sequence` and `limit` query parameters.
- Current `client.ts` has `ApiClient`, `SessionSnapshot` and
  `getSessionSnapshot(...)`, but no transcript aliases or complete-history
  loader.
- Current realtime contract parses session/floor events and five safe error
  codes, but has no participant utterance command/event derivative and no
  `UTTERANCE_REJECTED` code.
- Current realtime client owns one `SessionStartCommand | SessionAbortCommand`
  pending value and snapshot-only recovery through `loadSnapshot/onSnapshot`.
- Current projection treats every non-session event as a floor event, so it
  needs an explicit participant-utterance branch before floor projection.
- Current `SessionPanel` restores snapshot then opens realtime; it has no
  confirmed transcript, draft, Human pending, rejected draft or recovery
  bundle state.
- The real `pnpm.cmd web:test:e2e` command invokes the existing Python harness.
  Its old fixed action/event/floor totals must become semantic persistence
  assertions under the frozen sole non-Web test exception.
- No further scope contradiction or design stop condition was found.

## Locked file structure and responsibilities

### Production files

- Modify `apps/web/src/lib/api/client.ts`
  - export generated transcript aliases;
  - load complete owner-only transcript history with bounded cursor progress.
- Modify `apps/web/src/lib/realtime/contract.ts`
  - define the Human submit command and unified utterance event derivative;
  - strictly parse utterance v1 and the safe rejection error without changing
    floor v1/v2 behavior.
- Modify `apps/web/src/lib/realtime/client.ts`
  - extend the existing one-pending union;
  - own exact Human pending identity and resend;
  - replace snapshot-only recovery with the one authoritative recovery bundle;
  - expose typed pending/rejection callbacks and one recovery trigger;
  - host the small pure Unicode draft-inspection helper next to the submission
    boundary so it is not embedded in JSX.
- Modify `apps/web/src/lib/realtime/projection.ts`
  - advance only safe snapshot timestamps/watermark for utterance events.
- Create `apps/web/src/features/sessions/discussion-transcript.ts`
  - pure confirmed-utterance conversion, immutable merge, replay dedupe,
    authoritative ordering and same-ID conflict detection only.
- Modify `apps/web/src/features/sessions/session-panel.tsx`
  - coordinate initial/recovery bundles, confirmed transcript, editable draft,
    pending/rejection presentation, exact-floor send, safe AI presentation and
    small near-bottom scrolling.

No other production file is planned.

### Test files

- Modify `apps/web/src/lib/api/client.test.ts`.
- Modify `apps/web/src/lib/realtime/contract.test.ts`.
- Modify `apps/web/src/lib/realtime/client.test.ts`.
- Modify `apps/web/src/lib/realtime/projection.test.ts`.
- Create `apps/web/src/features/sessions/discussion-transcript.test.ts`.
- Modify `apps/web/src/features/sessions/session-panel.test.tsx`.
- Modify `apps/web/e2e/session.spec.ts`.
- Modify `apps/api/tests/integration/browser_e2e.py` only for E2E harness and
  semantic persistence verification.

No other non-Web test file is planned.

### Read-only generated derivative

- Read only: `apps/web/src/lib/api/generated/schema.d.ts`.
- The implementation must pass the existing OpenAPI drift workflow without
  regenerating or editing this file.

### Minimal implementation-status documents

Only after all code gates are green, update the current status/evidence in:

- `docs/TASKS.md`;
- `docs/exec-plans/P1-5_ai-runtime-foundation.md`;
- `docs/exec-plans/P1-5F-3A_web-discussion-functional-closure.md`;
- this implementation plan.

Do not edit `PROJECT_MASTER_PLAN.md`, `DECISIONS.md`, `ROADMAP.md` or `API.md`
for behavior already frozen by F3A.

## Exact interface design

### REST transcript aliases and loader

Add to `apps/web/src/lib/api/client.ts`:

```ts
export type TranscriptUtterance =
  components["schemas"]["TranscriptUtteranceResponse"];
export type TranscriptResponse = components["schemas"]["TranscriptResponse"];

export async function loadSessionTranscript(
  client: ApiClient,
  sessionId: string,
): Promise<TranscriptUtterance[]>;
```

`loadSessionTranscript(...)` starts with `after_sequence = 0`, sends
`limit = 200` on every page, appends `data.items` unchanged, advances only to
a strictly greater non-null `next_after_sequence`, and returns only when the
cursor is null. A missing `data`, a returned `error`, an unsafe/non-integer
cursor or a non-advancing non-null cursor throws a generic internal `Error`;
the UI maps it to safe copy and never displays raw transport details. GET
requests have no `X-GIA-CSRF` header.

### Realtime command, event and error derivative

Add to `apps/web/src/lib/realtime/contract.ts`:

```ts
export type ParticipantUtteranceSubmitCommand = {
  schema_version: 1;
  type: "participant.utterance.submit";
  session_id: string;
  action_id: string;
  payload: {
    floor_grant_id: string;
    content: string;
  };
};

export type ParticipantUtteranceCreatedEvent = {
  schema_version: 1;
  type: "participant.utterance.created";
  session_id: string;
  sequence: number;
  occurred_at: string;
  action_id: string | null;
  payload: {
    utterance_id: string;
    participant_id: string;
    actor_kind: "HUMAN" | "AI";
    floor_grant_id: string;
    phase:
      | "OPENING_STATEMENTS"
      | "EXPLORATION"
      | "CONFLICT_AND_EVALUATION"
      | "CONVERGENCE"
      | "FINAL_SUMMARY";
    content: string;
  };
};
```

Extend `FormalSessionEvent` with `ParticipantUtteranceCreatedEvent`. Extend
`RealtimeErrorCode` with `"UTTERANCE_REJECTED"`. HUMAN requires UUID4
`action_id`; AI requires null `action_id`. Utterance parsing accepts schema v1
only and retains exact envelope/payload key checks, positive safe sequence,
aware timestamp, UUID4 identity, five-phase, actor and string-content checks.

### Pure confirmed-transcript model

Create in
`apps/web/src/features/sessions/discussion-transcript.ts`:

```ts
import type { TranscriptUtterance } from "@/lib/api/client";
import type { ParticipantUtteranceCreatedEvent } from "@/lib/realtime/contract";

export type ConfirmedUtterance = TranscriptUtterance;

export type TranscriptMergeResult =
  | { kind: "merged"; items: ConfirmedUtterance[] }
  | { kind: "conflict"; utterance_id: string };

export function confirmedUtteranceFromEvent(
  event: ParticipantUtteranceCreatedEvent,
): ConfirmedUtterance;

export function mergeConfirmedTranscript(
  current: readonly ConfirmedUtterance[],
  incoming: readonly ConfirmedUtterance[],
): TranscriptMergeResult;
```

Authoritative equality compares exactly `utterance_id`, `sequence`,
`occurred_at`, `action_id`, `participant_id`, `actor_kind`, `floor_grant_id`,
`phase` and `content`. Identical IDs replay-dedupe. Any same-ID field mismatch
returns conflict. Results sort by `sequence`, with `utterance_id` as a stable
tie-break only if malformed input supplies equal sequences. The function never
gap-validates transcript sequences and never mutates either caller array.

### Draft inspection, Human pending and recovery bundle

Add to `apps/web/src/lib/realtime/client.ts`:

```ts
export type HumanDraftInvalidReason =
  | "EMPTY_OR_WHITESPACE"
  | "CONTAINS_NULL"
  | "TOO_LONG";

export type HumanDraftInspection = {
  codePointCount: number;
  isSubmittable: boolean;
  invalidReason: HumanDraftInvalidReason | null;
};

export function inspectHumanDraft(content: string): HumanDraftInspection;

export type PendingHumanUtterance = {
  action_id: string;
  floor_grant_id: string;
  content: string;
};

export type RejectedHumanUtterance = PendingHumanUtterance & {
  reason: "UTTERANCE_REJECTED" | "ACTION_ID_CONFLICT";
};

export type SessionRecoveryBundle = {
  snapshot: SessionSnapshot;
  transcript: TranscriptUtterance[];
};
```

Inside this already-approved draft-inspection boundary, add two small pure,
non-exported helpers:

```ts
function isPythonStripWhitespace(character: string): boolean;
function hasPythonStripContent(content: string): boolean;
```

`isPythonStripWhitespace(...)` reads the single iterated code point and returns
true exactly for Python's current `str.strip()` whitespace set: U+0009–U+000D,
U+001C–U+0020, U+0085, U+00A0, U+1680, U+2000–U+200A, U+2028, U+2029,
U+202F, U+205F and U+3000. Use explicit code-point ranges/equality checks; do
not use JavaScript `String.trim()` or a JavaScript `\s` regular expression.
`hasPythonStripContent(...)` iterates the original string and returns true when
at least one code point is outside that exact set. It returns only a boolean and
never constructs a stripped or transformed string.

Replace the current snapshot-only options with the exact bundle callbacks:

```ts
type SessionRealtimeOptions = {
  baseUrl: string;
  snapshot: SessionSnapshot;
  loadRecoveryBundle: () => Promise<SessionRecoveryBundle>;
  onEvent: (event: FormalSessionEvent) => void;
  onRecoveryBundle: (bundle: SessionRecoveryBundle) => void;
  onPendingChange: (pending: boolean) => void;
  onHumanPendingChange: (
    pending: PendingHumanUtterance | undefined,
  ) => void;
  onRejectedHumanUtterance: (
    rejected: RejectedHumanUtterance,
  ) => void;
  onConnectionChange: (state: RealtimeConnectionState) => void;
  onError: (message: string) => void;
};
```

Extend the current returned interface without adding another client:

```ts
export type SessionRealtimeClient = {
  start: () => void;
  startSession: () => string;
  abort: () => string;
  submitHumanUtterance: (
    floorGrantId: string,
    exactContent: string,
  ) => string;
  recoverAuthoritativeState: () => void;
  stop: () => void;
};
```

The internal union is exactly:

```ts
type PendingCommand =
  | SessionStartCommand
  | SessionAbortCommand
  | ParticipantUtteranceSubmitCommand;
```

`inspectHumanDraft(...)` uses the string iterator for code-point count, calls
`hasPythonStripContent(content)` for the server-strip-equivalent non-whitespace
decision, rejects `content.includes("\u0000")`, and never returns transformed
content. U+0085 and U+001C are strip-whitespace, while U+FEFF is content; this
intentionally differs from JavaScript trimming and matches backend
`content.strip()`. `submitHumanUtterance(...)` returns the existing pending
action ID without minting or sending a different command if any pending command
already exists; normal UI gates make that defensive path unreachable to the
user.

All reconnect, full-stream gap, `SEQUENCE_AHEAD`, action conflict and explicit
component recovery calls converge on one internal recovery routine. That
routine closes the stale socket generation, loads one complete bundle, takes
the reconnect cursor only from `bundle.snapshot.last_sequence`, reconciles
Human pending from transcript `action_id`, publishes the complete bundle only
after successful load, and reconnects. Transcript maximum sequence is never a
WebSocket cursor.

## Task 1 — REST transcript loader

**Files**

- Modify: `apps/web/src/lib/api/client.test.ts`
- Modify: `apps/web/src/lib/api/client.ts`
- Read only: `apps/web/src/lib/api/generated/schema.d.ts`

**Interfaces**

- Consumes: existing `ApiClient`, generated `TranscriptResponse` and
  `TranscriptUtteranceResponse`.
- Produces: `TranscriptUtterance`, `TranscriptResponse` and
  `loadSessionTranscript(client, sessionId)` exactly as frozen above.

- [ ] **1.1 RED — add exact transcript fixtures and one-page cases.**
  Add a canonical utterance fixture containing leading/trailing spaces and a
  newline. Add separate tests for an empty one-page response and a normal
  one-page response. Assert the returned array equals `items` byte-for-byte at
  the JavaScript string level.

  ```ts
  const TRANSCRIPT_ITEM: TranscriptUtterance = {
    utterance_id: "00000000-0000-4000-8000-000000000021",
    sequence: 5,
    occurred_at: "2026-08-25T01:04:05Z",
    action_id: "00000000-0000-4000-8000-000000000022",
    participant_id: "00000000-0000-4000-8000-000000000023",
    actor_kind: "HUMAN",
    floor_grant_id: "00000000-0000-4000-8000-000000000024",
    phase: "OPENING_STATEMENTS",
    content: "  exact contribution\nsecond line  ",
  };
  ```

- [ ] **1.2 RED — add cursor and request-shape cases.**
  Mock three pages and assert calls use query pairs `(after_sequence, limit)`
  of `(0, 200)`, `(5, 200)` and `(12, 200)`, then stop on null. Inspect every
  `Request`: method `GET`, credentials `include`, no `X-GIA-CSRF` header.

- [ ] **1.3 RED — add safe-failure cases.**
  Assert rejection for missing `data`, an API `error`, a non-null cursor equal
  to the current cursor, a lower cursor, a non-safe integer cursor and a
  non-integer cursor. Assert the fetch call count stops at the first invalid
  cursor so no loop continues.

- [ ] **1.4 Run the focused RED gate.**

  ```powershell
  pnpm.cmd --filter @group-interview-arena/web exec vitest run src/lib/api/client.test.ts
  ```

  Expected RED reason: `TranscriptUtterance`, `TranscriptResponse` and
  `loadSessionTranscript` are not exported.

- [ ] **1.5 GREEN — add aliases and bounded pagination.**
  Add only the two generated aliases and the loop below; do not touch realtime
  code in this task.

  ```ts
  let afterSequence = 0;
  const transcript: TranscriptUtterance[] = [];
  for (;;) {
    const result = await client.GET("/sessions/{session_id}/utterances", {
      params: {
        path: { session_id: sessionId },
        query: { after_sequence: afterSequence, limit: 200 },
      },
    });
    // Reject missing/error data, append exact items, validate next cursor,
    // return on null, otherwise advance afterSequence.
  }
  ```

- [ ] **1.6 Run focused GREEN and API-client regression.**

  ```powershell
  pnpm.cmd --filter @group-interview-arena/web exec vitest run src/lib/api/client.test.ts
  ```

  Regression gate: every existing auth/question/session API-client test remains
  green; the generated schema has no diff.

## Task 2 — Strict participant utterance realtime contract

**Files**

- Modify: `apps/web/src/lib/realtime/contract.test.ts`
- Modify: `apps/web/src/lib/realtime/contract.ts`

**Interfaces**

- Consumes: existing exact-envelope helpers, UUID4/timestamp/sequence checks,
  five `FloorPhase` values and strict floor v1/v2 parser behavior.
- Produces: `ParticipantUtteranceSubmitCommand`,
  `ParticipantUtteranceCreatedEvent`, expanded `FormalSessionEvent`, and
  `RealtimeErrorCode` including `UTTERANCE_REJECTED`.

- [ ] **2.1 RED — add canonical Human and AI event fixtures.**
  Human uses UUID4 `action_id`; AI uses null. Assert both parse to the original
  object and preserve exact content including whitespace/newlines.

- [ ] **2.2 RED — add actor/action/version rejection matrix.**
  Reject Human/null, AI/UUID4, unknown actor, schema versions `0`, `2` and `3`,
  invalid floor phase, zero/unsafe sequence, malformed UUID4 for every identity
  field, naive/invalid timestamp and non-string content.

- [ ] **2.3 RED — add exact-key rejection matrix.**
  Independently add one extra envelope field and one extra payload field;
  remove each required payload key in table-driven cases. Every case must
  return `undefined`.

- [ ] **2.4 RED — add safe error case.**
  Assert a canonical v1 `error` envelope with code `UTTERANCE_REJECTED` parses,
  while the existing unknown-code rejection still fails closed.

- [ ] **2.5 Run the focused RED gate.**

  ```powershell
  pnpm.cmd --filter @group-interview-arena/web exec vitest run src/lib/realtime/contract.test.ts
  ```

  Expected RED reason: the utterance event is outside `FormalSessionEvent`, the
  parser rejects its type, and `UTTERANCE_REJECTED` is outside the allowlist.

- [ ] **2.6 GREEN — add only the strict derivative.**
  Define the exact types, add `UTTERANCE_REJECTED` to `ERROR_CODES`, and add an
  utterance branch in `isFormalEvent(...)` after common envelope validation and
  before the floor-event fallback. Keep `isFloorEvent(...)` unchanged.

  ```ts
  if (value.type === "participant.utterance.created") {
    // Require schema v1, exact payload keys, UUID4 fields, five-phase actor,
    // actor/action pairing and string content.
  }
  ```

- [ ] **2.7 Run focused GREEN and unchanged floor regressions.**

  ```powershell
  pnpm.cmd --filter @group-interview-arena/web exec vitest run src/lib/realtime/contract.test.ts
  ```

  Regression gate: all historical floor v1/additive v2 canonical and rejection
  cases remain green without fixture relaxation.

## Task 3 — Pure confirmed-transcript merge model

**Files**

- Create: `apps/web/src/features/sessions/discussion-transcript.test.ts`
- Create: `apps/web/src/features/sessions/discussion-transcript.ts`

**Interfaces**

- Consumes: Task 1 `TranscriptUtterance`; Task 2
  `ParticipantUtteranceCreatedEvent`.
- Produces: `ConfirmedUtterance`, `TranscriptMergeResult`,
  `confirmedUtteranceFromEvent(event)` and
  `mergeConfirmedTranscript(current, incoming)` exactly as frozen above.

- [ ] **3.1 RED — add conversion and basic immutable merge cases.**
  Assert event conversion maps `occurred_at` plus every payload/envelope field
  into the canonical REST shape. Assert empty+new, current+new and reversed
  incoming order produce ascending authoritative sequence without mutating the
  frozen input arrays/objects.

- [ ] **3.2 RED — prove non-contiguous sequences and identical replay.**
  Merge sequences `5`, `12` and `27` without conflict or recovery signal.
  Merge an identical REST item and converted WS item with the same
  `utterance_id`; assert exactly one output item.

- [ ] **3.3 RED — prove every authoritative-field conflict independently.**
  Use `it.each` to vary exactly one of `sequence`, `occurred_at`, `action_id`,
  `participant_id`, `actor_kind`, `floor_grant_id`, `phase` and `content` while
  retaining the same `utterance_id`. Each returns
  `{ kind: "conflict", utterance_id }`.

- [ ] **3.4 RED — prove deterministic incoming duplicates.**
  Identical duplicate IDs within one incoming array dedupe. Conflicting
  duplicate IDs within one incoming array return conflict. Distinct IDs with
  the same malformed sequence sort by `utterance_id` as a stable tie-break.

- [ ] **3.5 Run the focused RED gate.**

  ```powershell
  pnpm.cmd --filter @group-interview-arena/web exec vitest run src/features/sessions/discussion-transcript.test.ts
  ```

  Expected RED reason: both the module and its exported symbols are absent.

- [ ] **3.6 GREEN — implement the smallest pure map/compare/sort function.**
  Build a new map from current, process incoming without mutating inputs,
  compare all nine fields explicitly, and return a newly sorted array.

  ```ts
  const authoritativeFields = [
    "utterance_id",
    "sequence",
    "occurred_at",
    "action_id",
    "participant_id",
    "actor_kind",
    "floor_grant_id",
    "phase",
    "content",
  ] as const;
  ```

  The module imports no React, WebSocket, fetch client or mutable singleton.

- [ ] **3.7 Run focused GREEN and staged diagnostic typecheck.**

  ```powershell
  pnpm.cmd --filter @group-interview-arena/web exec vitest run src/features/sessions/discussion-transcript.test.ts
  pnpm.cmd web:typecheck
  ```

  Regression gate: pure tests prove no transcript gap rule and no caller-array
  mutation. At this staged boundary, global typecheck is diagnostic and may
  return nonzero only for both known downstream-owned consequences of Task 2:
  `apps/web/src/lib/realtime/client.ts` does not yet handle
  `UTTERANCE_REJECTED` (owned by Task 4), and
  `apps/web/src/lib/realtime/projection.ts` does not yet handle
  `participant.utterance.created` (owned by Task 5). Any other type error is a
  blocker.

## Task 4 — Realtime Human pending and authoritative recovery

**Files**

- Modify: `apps/web/src/lib/realtime/client.test.ts`
- Modify: `apps/web/src/lib/realtime/client.ts`

**Interfaces**

- Consumes: Task 1 `TranscriptUtterance`; Task 2 submit command/event/error;
  existing `SessionSnapshot`, connection state, ordered event parser and
  bounded reconnect generation guards.
- Produces: `PendingHumanUtterance`, `RejectedHumanUtterance`,
  `SessionRecoveryBundle`, updated `SessionRealtimeOptions`,
  `submitHumanUtterance(...)` and `recoverAuthoritativeState()`. Task 6 adds
  `inspectHumanDraft` and its inspection types RED-first in the same client
  file, immediately before the UI consumes them.

### Task 4A — One Human command identity

- [ ] **4A.1 RED — add submit construction tests.**
  Stub `crypto.randomUUID()` with two distinct IDs. Start/open the fake socket,
  call `submitHumanUtterance(GRANT_ID, exactContent)`, and assert one serialized
  command with schema v1, exact session/action/grant/content. Call submit again
  while pending; assert the original action ID is returned, no second send is
  added and the UUID stub was called once.

- [ ] **4A.2 RED — prove global exclusion.**
  Create pending Start and Abort cases, then call Human submit. Assert no Human
  command and no additional UUID. Create Human pending, then call Start/Abort;
  assert the same one-pending invariant remains.

- [ ] **4A.3 Run RED.**

  ```powershell
  pnpm.cmd --filter @group-interview-arena/web exec vitest run src/lib/realtime/client.test.ts
  ```

  Expected RED reason: the pending union and submit method do not include Human
  utterances.

- [ ] **4A.4 GREEN — extend the existing union and callbacks only.**
  Add the exact submit command and publish both global pending=true and the
  exact `PendingHumanUtterance`. Do not create a queue.

### Task 4B — Exact reconnect resend

- [ ] **4B.1 RED — disconnect after Human send.**
  Make recovery return a bundle whose transcript does not contain the action.
  Open the replacement socket and assert the resent JSON parses to the same
  `action_id + floor_grant_id + content`; assert UUID generation remains once.

- [ ] **4B.2 GREEN — reuse existing `sendPending(...)`.**
  Preserve the exact pending object across recovery and send that object on
  the recovered socket; do not reconstruct content or bind a new floor.

### Task 4C — Type-specialized pending confirmation

- [ ] **4C.1 RED — add formal-event confirmation matrix.**
  Assert matching Human `participant.utterance.created` clears Human pending.
  Assert a same-action `floor.released` at the next sequence does not clear it.
  Assert a duplicate utterance event at `sequence <= lastSequence` may clear
  it without invoking `onEvent` or adding a transcript itself.

- [ ] **4C.2 RED — preserve lifecycle confirmation.**
  Retain the existing Start/Abort matching-action replay tests and assert their
  pending behavior remains unchanged.

- [ ] **4C.3 GREEN — add one explicit confirmation predicate.**

  ```ts
  function confirmsPending(
    pending: PendingCommand,
    event: FormalSessionEvent,
  ): boolean {
    if (pending.type === "participant.utterance.submit") {
      return (
        event.type === "participant.utterance.created" &&
        event.action_id === pending.action_id
      );
    }
    return event.action_id === pending.action_id;
  }
  ```

  Use it in both exact-next and duplicate-event branches. Never use same-action
  floor release as Human confirmation.

### Task 4D — Recoverable rejection

- [ ] **4D.1 RED — receive matching `UTTERANCE_REJECTED`.**
  Assert Human pending clears, global pending becomes false,
  `onRejectedHumanUtterance` receives exact action/grant/content with reason
  `UTTERANCE_REJECTED`, the socket stays open, no recovery load occurs and a
  subsequent valid lifecycle command can still send.

- [ ] **4D.2 GREEN — specialize the safe error branch.**
  Copy the exact pending payload before clearing it, publish the rejected
  value, keep the socket active and do not fabricate an event/transcript item.

### Task 4E — Action conflict

- [ ] **4E.1 RED — receive matching `ACTION_ID_CONFLICT`.**
  Assert no replacement UUID, no resend, exact content preserved with reason
  `ACTION_ID_CONFLICT`, and exactly one authoritative bundle load begins.

- [ ] **4E.2 GREEN — clear/reject then call the shared recovery routine.**
  Do not reconnect through an error-specific implementation; invoke the same
  internal routine used by gap, sequence-ahead and public recovery.

### Task 4F — Replace snapshot-only recovery with one bundle

- [ ] **4F.1 RED — migrate the existing recovery tests to bundles.**
  Replace test doubles for `loadSnapshot/onSnapshot` with
  `loadRecoveryBundle/onRecoveryBundle`. Assert a successful bundle publishes
  once, takes the next WebSocket `after_sequence` only from
  `bundle.snapshot.last_sequence`, and ignores a larger transcript sequence.

- [ ] **4F.2 RED — add transcript confirmation and atomic publication.**
  A recovered transcript containing the pending Human `action_id` clears
  pending before reconnect. A rejected bundle promise or invalid session ID
  publishes neither snapshot nor transcript and keeps the previous callback
  state untouched.

- [ ] **4F.3 RED — retain bounded/stale-socket behavior.**
  Keep the five-attempt backoff, recovered-socket stability reset, one live
  socket and stale-generation message rejection tests green after option
  renaming.

- [ ] **4F.4 GREEN — implement one `recoverAndReconnect(...)` routine.**
  Replace `reloadSnapshotAndReconnect(...)`; do not layer another loader.
  Update `lastSequence` from the snapshot, reconcile pending against transcript
  action IDs, publish the bundle, then connect.

### Task 4G — Public conflict recovery trigger

- [ ] **4G.1 RED — call `recoverAuthoritativeState()`.**
  Assert it uses the same loader, reloading guard, generation invalidation,
  callback, snapshot cursor and reconnect path as sequence-gap recovery.

- [ ] **4G.2 GREEN — expose a thin method.**

  ```ts
  recoverAuthoritativeState() {
    void recoverAndReconnect(generation);
  }
  ```

  The method must not contain a second fetch/recovery implementation.

- [ ] **4.1 Run the complete Task 4 focused gate.**

  ```powershell
  pnpm.cmd --filter @group-interview-arena/web exec vitest run src/lib/realtime/client.test.ts
  ```

  Expected initial RED reasons appear per substep: missing Human method/types,
  generic same-action clearing, missing rejection callback, and snapshot-only
  recovery.

- [ ] **4.2 Run Task 4 regression gate.**

  ```powershell
  pnpm.cmd --filter @group-interview-arena/web exec vitest run src/lib/realtime/contract.test.ts src/lib/realtime/client.test.ts
  pnpm.cmd web:typecheck
  ```

  Regression gate: Start/Abort, exact-next/duplicate/gap, bounded reconnect,
  stale socket and strict floor parsing remain green. Global typecheck remains
  diagnostic at this staged boundary: the Task 4
  `UTTERANCE_REJECTED` client error must be gone, and the only allowed
  remaining type debt is both Task 5 adaptations: the explicit
  `participant.utterance.created` branch in
  `apps/web/src/lib/realtime/projection.ts`, and the migration of
  `apps/web/src/features/sessions/session-panel.tsx` from the pre-Task-4
  `loadSnapshot` / `onSnapshot` options to the authoritative recovery-bundle
  interface. A surviving Task 4 client error or any other type error is a
  blocker. Task 5 must eliminate both debts and restore a completely green
  global typecheck.

## Task 5 — Projection and SessionPanel restore integration

**Files**

- Modify: `apps/web/src/lib/realtime/projection.test.ts`
- Modify: `apps/web/src/lib/realtime/projection.ts`
- Modify: `apps/web/src/features/sessions/session-panel.test.tsx`
- Modify: `apps/web/src/features/sessions/session-panel.tsx`

**Interfaces**

- Consumes: Task 1 `loadSessionTranscript`; Task 2 utterance event; Task 3
  conversion/merge; Task 4 `SessionRecoveryBundle` and updated realtime
  options/client.
- Produces: utterance-safe `projectSessionEvent(...)`; one feature-local
  `loadAuthoritativeRecoveryBundle(sessionId)` callback; atomic application of
  snapshot plus canonical confirmed transcript; one transcript-conflict call
  to `recoverAuthoritativeState()`.

- [ ] **5.1 RED — add projection invariants.**
  Project a canonical Human utterance event into a snapshot with a current AI
  grant and latest floor event. Assert only `server_now`, `updated_at` and
  `last_sequence` advance; `status`, phase timing and the complete `floor`
  object stay deeply equal.

- [ ] **5.2 Run projection RED.**

  ```powershell
  pnpm.cmd --filter @group-interview-arena/web exec vitest run src/lib/realtime/projection.test.ts
  ```

  Expected RED reason: the current fallback treats utterance payload as a
  floor event and corrupts projection fields.

- [ ] **5.3 GREEN — add the explicit utterance branch.**

  ```ts
  if (event.type === "participant.utterance.created") {
    return {
      ...snapshot,
      server_now: event.occurred_at,
      updated_at: event.occurred_at,
      last_sequence: event.sequence,
    };
  }
  ```

- [ ] **5.4 RED — prove initial URL restore order.**
  Mock `getSessionSnapshot`, `loadSessionTranscript` and realtime creation with
  deferred promises. Assert snapshot resolves first, transcript starts only
  after it, and `createSessionRealtimeClient(...).start()` is not called until
  transcript resolves and the bundle is applied. Assert the realtime seed
  snapshot is the captured snapshot whose watermark preceded transcript load.

- [ ] **5.5 RED — prove non-destructive bundle recovery.**
  Render the existing question/floor snapshot, trigger
  `onConnectionChange("reconnecting")`, and assert those authoritative facts
  remain visible with `正在同步讨论记录…`. Reject the recovery promise and assert
  the old facts remain. Resolve a later bundle and assert the snapshot changes
  only after the transcript promise and validation succeed. Task 6 adds the
  confirmed-transcript presentation and directly proves it also remains visible.

- [ ] **5.6 RED — prove canonical bundle validation and pending path.**
  In the authoritative loader, call
  `mergeConfirmedTranscript([], transcript)` before its promise resolves; spy
  on that exact call to prove validation/dedupe precedes delivery to the
  realtime client. A same-utterance-ID conflict rejects the loader, so it
  cannot advance the recovery cursor, reconcile Human pending, publish/apply a
  bundle or open a recovered socket from the invalid snapshot watermark.
  Assert a valid recovered transcript action ID is delivered through Task 4
  reconciliation. Do not merge stale displayed history into authoritative
  replacement, which would make a corrected server item conflict forever.

- [ ] **5.7 RED — prove live merge and conflict recovery.**
  Spy on conversion/merge, deliver one utterance event, and assert projection
  plus a merge from the current confirmed state. Deliver an identical replay
  and assert the next merge receives the deduped state. Deliver the same
  `utterance_id` with changed content; assert the last merged state is retained
  and `recoverAuthoritativeState()` is called once. Do not add transcript UI in
  this task.

- [ ] **5.8 RED — split connection error from rejected content.**
  Assert a successful `connected`/recovery state clears or supersedes a stale
  realtime connection error while an existing `RejectedHumanUtterance`
  presentation remains.

- [ ] **5.9 Run SessionPanel RED.**

  ```powershell
  pnpm.cmd --filter @group-interview-arena/web exec vitest run src/features/sessions/session-panel.test.tsx
  ```

  Expected RED reason: the component has snapshot-only restore, no transcript
  state and the old realtime option names.

- [ ] **5.10 GREEN — create and reuse one feature-local bundle loader.**
  In `SessionPanel`, fetch snapshot, capture it, await
  `loadSessionTranscript(...)`, then validate/dedupe the complete transcript
  from an empty base before returning one canonical `SessionRecoveryBundle`.
  Reject an identity conflict before the realtime client can observe any part
  of that bundle. Use the same callback for URL restore and realtime recovery.
  For a newly created session, seed `{ snapshot: created, transcript: [] }`
  because no prior transcript exists.

  ```ts
  async function loadAuthoritativeRecoveryBundle(
    sessionId: string,
  ): Promise<SessionRecoveryBundle> {
    const snapshotResult = await getSessionSnapshot(apiClient, sessionId);
    if (!snapshotResult.data) throw new Error("Session snapshot unavailable");
    const transcript = await loadSessionTranscript(apiClient, sessionId);
    const canonical = mergeConfirmedTranscript([], transcript);
    if (canonical.kind === "conflict") {
      throw new Error("Authoritative transcript identity conflict");
    }
    return { snapshot: snapshotResult.data, transcript: canonical.items };
  }
  ```

- [ ] **5.11 GREEN — add one bundle application path.**
  Apply only the loader's canonical bundle by updating `snapshotRef`, React
  snapshot and confirmed transcript in the same callback. Keep the existing UI
  state until loader validation succeeds. Feed live utterance events through
  conversion/merge and invoke the realtime client recovery method on conflict.

- [ ] **5.12 Run focused GREEN and integration regressions.**

  ```powershell
  pnpm.cmd --filter @group-interview-arena/web exec vitest run src/lib/realtime/projection.test.ts src/features/sessions/discussion-transcript.test.ts src/features/sessions/session-panel.test.tsx
  pnpm.cmd web:typecheck
  ```

  Regression gate: create/start/abort, question rendering, floor projection,
  countdown and safe realtime-error tests remain green. Global typecheck must
  pass completely after Task 5, and every later task must keep it green.

## Task 6 — Composer, transcript, rejected draft and AI public-fact UX

**Files**

- Modify: `apps/web/src/lib/realtime/client.test.ts`
- Modify: `apps/web/src/features/sessions/session-panel.test.tsx`
- Modify: `apps/web/src/lib/realtime/client.ts`
- Modify: `apps/web/src/features/sessions/session-panel.tsx`

**Interfaces**

- Consumes: Task 3 confirmed transcript; Task 4 Human pending/rejection
  callbacks and submit method; Task 5 authoritative snapshot ref/recovery
  application.
- Produces: `inspectHumanDraft` and its exact inspection types; accessible
  composer/send gating; exact submit boundary; confirmed transcript rendering;
  pending/rejected presentation; public-fact AI waiting and interrupted notice;
  small near-bottom follow behavior.

### Composer and exact content

- [ ] **6.1 RED — test pure draft inspection directly.**
  Assert whitespace-only and U+0000 are invalid; 4,000 Unicode code points are
  valid; 4,001 are invalid; astral emoji counts once. Assert the inspection
  returns the original string nowhere and therefore cannot trim, normalize or
  truncate it. Add explicit server/Browser divergence cases: a draft containing
  only U+0085 is `EMPTY_OR_WHITESPACE`; a draft containing only U+001C is
  `EMPTY_OR_WHITESPACE`; and a draft containing only U+FEFF is valid content.
  Also assert U+0085 or U+001C surrounding a visible character remains valid
  without changing any code point. Expected RED reason: `inspectHumanDraft`,
  its types and the Python-strip-equivalent predicate do not yet exist; Task 4
  deliberately did not add them without these tests.

- [ ] **6.2 RED — test the six send gates.**
  For the accessible textarea and Send button assert:
  - AI floor, another participant, no floor, `PREPARATION`, `COMPLETED` and
    `ABORTED_USER`: textarea remains locally editable/readable and Send is
    disabled;
  - exact Human floor + one of five floor-enabled phases + connected + valid
    content + no pending: Send is enabled;
  - connecting/reconnecting/disconnected, invalid content or any pending
    command: Send is disabled with adjacent readable reason.
  Assert the lightweight count displays the helper's Unicode code-point count
  as `current / 4000`, including the astral-emoji case.

- [ ] **6.3 RED — test keyboard and focus behavior.**
  Enter inserts a newline. Ctrl+Enter and Cmd+Enter submit only while all send
  gates pass. Delivering a Human grant never invokes `textarea.focus()`.

- [ ] **6.4 RED — test click-time exact-floor binding.**
  Render with Human grant A, type exact whitespace/newline content, then update
  `snapshotRef.current` to Human grant B before click. Assert
  `submitHumanUtterance(B, exactContent)` is called; no trimmed/normalized value
  and no render-time grant A is sent. Repeat the submission assertion with
  U+FEFF-only content and with visible content surrounded by U+0085/U+001C;
  the exact original string must reach the realtime boundary unchanged.

- [ ] **6.5 GREEN — implement pure inspection and send derivation.**
  Derive `canSend` from the latest render state for button presentation, but
  re-run all authority/content checks against `snapshotRef.current` and the
  exact draft inside the submit handler. Clear the textarea only after the
  realtime client accepts the local submission call.

### Pending and rejected draft

- [ ] **6.6 RED — separate next draft from Human pending.**
  After submit C, assert the textarea may edit new D, Send stays disabled while
  global pending is true, and C appears only under
  `待服务器确认（尚未进入讨论记录）`. Assert C is absent from confirmed speech
  items.

- [ ] **6.7 RED — preserve rejected C without overwriting D.**
  Deliver exact rejected C after D is typed. Assert D stays in the textarea, C
  appears in a separate recovery region, and only an explicit button replaces
  D with C. For `UTTERANCE_REJECTED`, assert the frozen safe copy is exactly
  `这条发言当前无法提交，请确认发言机会后重试。`; it must disclose no stale-floor,
  scheduler, AI-owner, deadline or phase-reconciliation reason. Assert this
  rejected-draft copy remains distinct from connection/recovery status, and a
  reconnecting/connected transition neither replaces nor clears it. The action
  must have clear copy when replacing a non-empty draft.

- [ ] **6.8 GREEN — add four distinct feature-local content states.**
  Keep `draft`, Task 4 Human pending callback value, `confirmedTranscript` and
  one `rejectedDraft` state separate. Pending clearing never inserts speech;
  rejection callback never assigns `draft` automatically. Render rejected-
  draft safe copy/content in its own status region; do not reuse the connection
  error or recovery-status state for it.

### Confirmed transcript presentation

- [ ] **6.9 RED — render only confirmed utterances.**
  Assert empty copy explains that server-confirmed speech appears here. Render
  one Human item as `你` and AI items as `AI 候选人 1/2/3` from participants
  sorted by safe `seat_order`. Assert each item renders its safe phase label and
  no persona label appears.

- [ ] **6.10 RED — prove safe exact text rendering.**
  Use content containing `<strong>`, Markdown markers and newlines. Assert it
  remains text, no element injection occurs, and CSS/presentation preserves
  line breaks.

- [ ] **6.11 GREEN — add the minimum transcript section.**
  Map participant IDs only through `snapshot.floor.participants`; Human label
  is `你`, AI numbering is the AI-only safe seat order, and content renders in
  a plain-text element with preserved whitespace. Do not add Markdown/HTML
  rendering or F3B layout.

### AI public-fact presentation

- [ ] **6.12 RED — derive exact-grant AI waiting.**
  Current AI grant G with no confirmed AI item for G shows
  `AI 候选人 X 正在准备发言…`. An AI item for another grant does not remove it;
  a matching AI item for G removes it immediately before floor release.

- [ ] **6.13 RED — add one generic interrupted notice.**
  From the pre-projection current grant, receive `floor.released /
  INTERRUPTED` with no matching AI utterance. Assert one in-memory notice
  `这次 AI 发言未完成，讨论将继续。` per grant. Assert it contains no provider,
  model, runtime, retry or error taxonomy. No notice appears if the exact grant
  already has a confirmed AI utterance.

- [ ] **6.14 RED — recovery status precedence.**
  While connection is reconnecting or bundle recovery is active, assert sync
  status replaces stale AI waiting visually; confirmed transcript and rejected
  content remain visible.

- [ ] **6.15 GREEN — derive presentation from public facts only.**
  Use snapshot participant/current-grant data, confirmed transcript grant IDs
  and public release reason. Store only a small in-memory set/ref of AI grant
  IDs already announced as interrupted. Do not create a timer or generation
  state.

### Scroll and accessibility

- [ ] **6.16 RED — test small scroll behavior.**
  Mock transcript container `scrollHeight`, `scrollTop` and `clientHeight`.
  A user within the frozen near-bottom threshold follows one newly confirmed
  item; a user above that threshold is not moved. No new-message counter or
  virtual list is asserted or implemented.

- [ ] **6.17 RED — test accessible status.**
  Assert a real textarea label, an adjacent readable disabled-send reason, and
  scoped `aria-live` regions for pending, rejection and recovery. Confirmed
  transcript text is not an assertive live stream.

- [ ] **6.18 GREEN — implement the minimum existing-panel UI.**
  Add only functional sections inside `SessionPanel`, one transcript container
  ref and a pre-append near-bottom measurement. Preserve existing question,
  lifecycle, floor, countdown, start and abort behavior.

- [ ] **6.19 Run focused Task 6 GREEN.**

  ```powershell
  pnpm.cmd --filter @group-interview-arena/web exec vitest run src/lib/realtime/client.test.ts src/features/sessions/discussion-transcript.test.ts src/features/sessions/session-panel.test.tsx
  ```

  Expected initial RED reasons: missing composer/transcript sections, missing
  Human pending/rejected states, missing submit boundary and missing AI public-
  fact presentation.

- [ ] **6.20 Run complete Web unit/component regression.**

  ```powershell
  pnpm.cmd web:test
  pnpm.cmd web:typecheck
  ```

  Regression gate: all Web Vitest tests pass with existing session lifecycle,
  floor v1/v2, reconnect, question and auth behavior unchanged.

## Task 7 — Chromium vertical slice and semantic persistence verification

**Files**

- Modify first: `apps/web/e2e/session.spec.ts`
- Modify only after the Task 7 RED run:
  `apps/api/tests/integration/browser_e2e.py`, solely as the authorized test
  harness/persistence verifier
- Modify only after all code gates pass: the four implementation-status
  documents listed in the locked file structure

**Interfaces**

- Consumes: the real existing authenticated PostgreSQL/Uvicorn/Next/Chromium
  harness, Task 1 REST restore, Task 2 command/event contract, Task 4 pending
  client and Task 6 UI.
- Produces: one deterministic browser proof of exact Human submit,
  server-confirmed render/reload, storage absence and semantic durable facts;
  no backend production interface.

- [ ] **7.1 RED — extend WebSocket frame capture.**
  Capture the exact `participant.utterance.submit` sent frame and matching
  `participant.utterance.created` received frame separately from existing
  start/floor frames. Keep existing floor v2 privacy assertions.

- [ ] **7.2 RED — submit exact browser content.**
  Define an exact `HUMAN_CONTRIBUTION` fixture in the Playwright test containing
  leading/trailing whitespace and a newline. After the existing deterministic
  Human floor, fill that fixture. Click Send and assert the pending copy appears
  without a formal transcript item. Parse the sent command and assert schema
  v1, exact session ID, UUID4 action ID, captured current floor grant ID and
  exact content. Do not edit the Python verifier yet.

- [ ] **7.3 RED — wait for durable confirmation and reload.**
  Assert the matching Human event renders exactly once and clears pending.
  Reload, wait for snapshot+transcript restore, and assert the exact content is
  present once from REST before normal realtime continuation.

- [ ] **7.4 RED — preserve existing browser regressions.**
  Keep current floor v2 safe projection, duplicate command replay, API restart,
  completion/reload and private-sentinel assertions. Update sequence assertions
  to use captured semantic event order or authoritative current values rather
  than old fixed totals invalidated by Human submit.

- [ ] **7.5 RED — prove browser storage remains empty.**
  Assert neither storage contains draft, exact contribution, action ID, floor
  grant ID, pending payload, transcript authority or session authority.

- [ ] **7.6 Run the browser RED gate with the Python fixed-total verifier
  unchanged.**

  ```powershell
  git diff --exit-code -- apps/api/tests/integration/browser_e2e.py
  pnpm.cmd web:test:e2e
  ```

  The first command must pass, proving the authorized Python verifier has not
  yet been edited. Expected E2E RED reason: the Playwright Human-submit scenario
  creates legitimate new durable action/event/release facts, while the obsolete
  Python verifier still requires `2 actions`, `last_sequence = 10`, and exactly
  one grant/release.

- [ ] **7.7 GREEN — replace only the Python fixed totals with semantic
  queries.**
  Now modify `_verify_session_persistence(...)`. Define the same exact
  `HUMAN_CONTRIBUTION` fixture value used by Playwright, retain one session row
  and immutable question binding, and query/assert:
  - final status `COMPLETED`, null current floor and null phase timing;
  - event sequences equal `range(1, last_sequence + 1)` where `last_sequence`
    comes from the same durable session row;
  - exactly one `DiscussionEvent` with `event_type =
    "participant.utterance.created"`, `payload.actor_kind = "HUMAN"` and
    `payload.content = HUMAN_CONTRIBUTION`; retain its
    `causation_action_id`, sequence, exact grant, participant and phase;
  - exactly one `SessionAction` joined by that `causation_action_id`, with
    `command_type = "participant.utterance.submit"`; this join identifies the
    durable action for the tested contribution even though `session_actions`
    stores a payload digest rather than plaintext payload;
  - the Human event preserves exact content, grant, participant and phase;
  - exactly one `FloorRelease` for that grant with reason
    `SPEAKER_FINISHED` and the same causation action;
  - the matching public `floor.released` event immediately follows the Human
    utterance event;
  - zero real-provider evidence: no provider credentials are added to the
    harness and no `llm_generation_requests` row is created by this flow.

  Scope every query to the sole durable session row. Join the matching public
  `floor.released` event and `floor_releases` row by session, grant and the same
  causation action; compare the public release sequence to Human-event sequence
  plus one. Do not infer order from table insertion order.

  Keep later scheduler actions, grants, releases and lifecycle events legal.
  Do not assert a replacement fixed action count, final sequence number, grant
  count or release count. Do not change API application source,
  database models, migrations, scheduler, runtime, provider configuration, CI
  or infrastructure.

- [ ] **7.8 Run focused Chromium GREEN.**

  ```powershell
  pnpm.cmd web:test:e2e
  ```

  Regression gate: authenticated create/start, deterministic Human floor,
  exact durable submit, reload restore, existing floor v2, duplicate replay,
  API restart, terminal completion, storage absence and semantic persistence
  verification all pass with zero real provider call.

- [ ] **7.9 Update minimal implementation status only after every code gate is
  green.**
  Record exact commands/results and keep P1-5F/F3 governance status honest
  pending required review. Do not alter the frozen design decisions or mark a
  review-dependent checkpoint complete early.

## Full implementation validation gate

Run from repository root after Tasks 1–7 focused gates are green.

- [ ] **V1 — frozen dependency/manifest proof.**

  ```powershell
  pnpm.cmd install --frozen-lockfile
  git diff --exit-code -- package.json pnpm-lock.yaml pnpm-workspace.yaml apps/web/package.json apps/api/pyproject.toml apps/api/uv.lock
  ```

- [ ] **V2 — Web formatting, lint, typecheck, full Vitest and production build.**

  ```powershell
  pnpm.cmd web:format:check
  pnpm.cmd web:lint
  pnpm.cmd web:typecheck
  pnpm.cmd web:test
  pnpm.cmd web:build
  ```

- [ ] **V3 — DB-independent OpenAPI derivative drift.**
  In terminal A run:

  ```powershell
  uv run --project apps/api uvicorn group_interview_arena_api.app:app --host 127.0.0.1 --port 8000 --lifespan off
  ```

  In terminal B run, then stop terminal A:

  ```powershell
  pnpm.cmd web:api:check
  git diff --exit-code -- apps/web/src/lib/api/generated/schema.d.ts
  ```

- [ ] **V4 — real scoped Chromium regression.**

  ```powershell
  pnpm.cmd web:test:e2e
  ```

- [ ] **V5 — immutable authority and prohibited-scope proof.**

  ```powershell
  $expectedMaster = '2388a9660320406cb35d5354126ad71c6849a98db7c4a356796ca951bf372f26'
  $actualMaster = (Get-FileHash -Algorithm SHA256 -LiteralPath 'docs/PROJECT_MASTER_PLAN.md').Hash.ToLowerInvariant()
  if ($actualMaster -ne $expectedMaster) { throw 'Master Plan SHA-256 changed' }

  git diff --exit-code -- apps/api/src
  git diff --exit-code -- apps/api/alembic
  git diff --exit-code -- apps/web/src/lib/api/generated/schema.d.ts
  git diff --exit-code -- package.json pnpm-lock.yaml pnpm-workspace.yaml apps/web/package.json apps/api/pyproject.toml apps/api/uv.lock
  git diff --exit-code -- .github infra
  ```

- [ ] **V6 — exact changed-file allowlist.**
  The only allowed implementation files are the production/test/status files
  listed in this plan. This PowerShell gate fails for every other path:

  ```powershell
  $allowed = [System.Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal)
  @(
    'apps/web/src/lib/api/client.ts',
    'apps/web/src/lib/api/client.test.ts',
    'apps/web/src/lib/realtime/contract.ts',
    'apps/web/src/lib/realtime/contract.test.ts',
    'apps/web/src/lib/realtime/client.ts',
    'apps/web/src/lib/realtime/client.test.ts',
    'apps/web/src/lib/realtime/projection.ts',
    'apps/web/src/lib/realtime/projection.test.ts',
    'apps/web/src/features/sessions/discussion-transcript.ts',
    'apps/web/src/features/sessions/discussion-transcript.test.ts',
    'apps/web/src/features/sessions/session-panel.tsx',
    'apps/web/src/features/sessions/session-panel.test.tsx',
    'apps/web/e2e/session.spec.ts',
    'apps/api/tests/integration/browser_e2e.py',
    'docs/TASKS.md',
    'docs/exec-plans/P1-5_ai-runtime-foundation.md',
    'docs/exec-plans/P1-5F-3A_web-discussion-functional-closure.md',
    'docs/exec-plans/P1-5F-3A_web-discussion-functional-closure-implementation.md'
  ) | ForEach-Object { [void]$allowed.Add($_) }

  $changed = @(git status --porcelain=v1 | ForEach-Object {
    $_.Substring(3).Replace('\', '/')
  })
  $unexpected = @($changed | Where-Object { -not $allowed.Contains($_) })
  if ($unexpected.Count -gt 0) {
    throw "Unexpected F3A paths: $($unexpected -join ', ')"
  }
  ```

- [ ] **V7 — final diff and Git state.**

  ```powershell
  git diff --check
  $staged = @(git diff --cached --name-only)
  if ($staged.Count -ne 0) { throw "Unexpected staged files: $($staged -join ', ')" }
  git status --short
  ```

Do not run a real provider call at any point.

## Requirement-to-task coverage

- Complete transcript pagination, exact content and no-CSRF GET: Task 1.
- Strict Human/AI utterance v1 derivative, actor/action pairing,
  `UTTERANCE_REJECTED` and unchanged floor v1/v2: Task 2.
- Non-contiguous transcript, authoritative-field equality, REST/WS replay,
  immutable deterministic merge and conflict: Task 3.
- One pending command, exact resend, durable-only Human confirmation,
  rejection/conflict recovery, snapshot cursor and one recovery path: Task 4.
- Utterance watermark-only projection, snapshot→transcript→WS restore,
  non-destructive recovery and conflict-triggered authoritative reload: Task 5.
- Six send gates, click-time exact floor/content, Unicode code points,
  draft/pending/rejected/confirmed separation, safe transcript/AI/accessibility /
  scroll behavior: Task 6.
- Real browser submit/confirmation/reload/storage proof and semantic durable
  action/event/release/order verification: Task 7.
- Dependency, generated schema, backend production, migration, CI, provider,
  file-scope, Master Plan and Git protections: full validation gate.

## Implementation stop conditions

Stop before changing scope if any task requires:

- backend production, public F1/F2 semantic, schema or migration change;
- manual generated OpenAPI edits;
- another realtime protocol/channel;
- more than one pending command or a failed-message queue;
- Redux, Zustand, an app-global store or controller framework;
- a public generation lifecycle or Browser-owned AI timeout;
- scheduler, runtime, provider or real model work;
- Browser persistence of pending/draft/transcript/session authority;
- weakening floor v1/v2 validation;
- F3B layout work;
- a dependency, lockfile, CI or infrastructure change;
- a production file outside the frozen boundary;
- any non-Web test file other than
  `apps/api/tests/integration/browser_e2e.py`;
- an E2E assertion that can pass only by guessing new fixed totals instead of
  verifying the frozen semantic facts;
- a WebSocket cursor derived from transcript maximum sequence;
- Human pending confirmation from same-action `floor.released` without a
  matching durable utterance event or restored transcript item.

Record the exact finding and stop; do not solve it by broadening this plan.

## Plan self-review

- Spec coverage: every frozen TDD acceptance item maps to Tasks 1–7 or the full
  validation gate; no uncovered behavior was found.
- Completeness scan: every execution item names exact files, behavior, command,
  RED reason and GREEN boundary; no deferred instruction remains.
- Type consistency: `TranscriptUtterance`, `ParticipantUtteranceCreatedEvent`,
  `ConfirmedUtterance`, `SessionRecoveryBundle`, `PendingHumanUtterance`,
  `RejectedHumanUtterance`, `submitHumanUtterance(...)` and
  `recoverAuthoritativeState()` retain one spelling/signature throughout.
- Dependency direction: `lib/realtime` imports only `lib/api` and its own
  contract; it never imports `features/sessions`.
- Recovery authority: initial restore, reconnect, gap, sequence-ahead,
  action-conflict and transcript-conflict all use one snapshot+complete-
  transcript loader/callback path; the cursor is always snapshot watermark.
- Pending semantics: Human pending clears only from matching
  `participant.utterance.created` or matching restored transcript action ID;
  same-action floor release alone is explicitly negative-tested.
- Draft validation semantics: the planned pure predicate enumerates Python
  `str.strip()` whitespace, explicitly tests U+0085/U+001C/U+FEFF divergence,
  and never transforms submitted content.
- Task 7 sequencing: Playwright changes and the obsolete-verifier RED run occur
  before the sole authorized Python verifier edit; semantic verifier GREEN and
  the second E2E run follow.
- Scope: production remains Web-only; the sole Python change is the approved
  persistence verifier; no backend production, dependency, F3B, global store,
  provider or generated-schema work is planned.
- Commercial-forward safety: Option B keeps parsing, transcript merge, pending
  identity and server snapshot authority separable for the post-P2 complexity
  checkpoint without pre-building B+ or C.
- Planning stop-condition assessment: none triggered.

## Planning progress

- Authority recovery and actual-source inspection: completed.
- Generated REST derivative sufficiency: confirmed read-only.
- Exact production/test boundary: frozen.
- Seven-task TDD order and interfaces: frozen.
- Implementation: Tasks 1–7 complete；external actual-source implementation
  review `PASS` after F3A-FINAL-001 remediation；findings none open.
- Final validation: frozen install/manifests unchanged；Web
  format/lint/typecheck/build PASS；Vitest `150/150`；live OpenAPI derivative
  drift PASS；real Chromium `2/2` PASS with exact durable Human persistence
  semantics and zero provider request.
- Commit/push: `COMPLETE` at accepted target
  `30446af520e55977a7c7a4839e00ab1a0a94d44e`.
- CI: `PASS`；GitHub Actions run `32945590023` passed all four required jobs.
- Independent final acceptance: `PASS`；findings none；F3A is `DONE`；F3B/F4
  remain `NOT_STARTED`.
- Stage/commit/push authorization: none.
