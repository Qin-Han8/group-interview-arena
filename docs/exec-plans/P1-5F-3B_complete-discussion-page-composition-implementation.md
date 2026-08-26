# P1-5F-3B Complete Discussion Page Composition — Implementation Plan

Status: `DESIGN_FROZEN / IMPLEMENTATION_PLAN_FROZEN / IMPLEMENTATION_NOT_STARTED`

Parent status: `P1 IN_PROGRESS`; `P1-5 IN_PROGRESS`; `P1-5F IN_PROGRESS`;
`P1-5F-3 IN_PROGRESS`; `P1-5F-3A DONE`; `P1-5F-4 NOT_STARTED`

Target version: `V0.1 Internal Validation`

Planning baseline: clean committed `main` at
`ab089974e21a2d01ae2865beb15864c50883ee24`, equal to `origin/main`

Baseline CI: GitHub Actions run `32968355532`, workflow `CI`, exact head
`ab089974e21a2d01ae2865beb15864c50883ee24`, completed `SUCCESS`

Immutable product baseline:
[`PROJECT_MASTER_PLAN.md`](../PROJECT_MASTER_PLAN.md), SHA-256
`2388a9660320406cb35d5354126ad71c6849a98db7c4a356796ca951bf372f26`

Frozen design authority:
[`P1-5F-3B_complete-discussion-page-composition.md`](P1-5F-3B_complete-discussion-page-composition.md), design actual-source review `PASS`, findings `NONE`

Implementation-plan review record: the initial external actual-source review
was `BLOCKED` by exactly `F3B-IP-001` and `F3B-IP-002`. This finding-only
remediation closes both findings without changing frozen product-design
substance or authorizing implementation. The remediated implementation-plan
self-review is `PASS`; open findings are `NONE`.

Preserved F3A authorities:
[`P1-5F-3A_web-discussion-functional-closure.md`](P1-5F-3A_web-discussion-functional-closure.md)
and
[`P1-5F-3A_web-discussion-functional-closure-implementation.md`](P1-5F-3A_web-discussion-functional-closure-implementation.md)

Parent plan:
[`P1-5_ai-runtime-foundation.md`](P1-5_ai-runtime-foundation.md)

## Goal

Freeze an executable, test-first implementation sequence for the already
approved F3B discussion-page composition. The implementation later replaces
the current prototype-width, long-column presentation with the frozen
desktop/tablet/mobile studio while preserving all F3A authority and behavior.

This checkpoint creates planning and status documents only. It does not
modify or authorize production code, tests, generated contracts, backend,
dependencies, CI or F4.

## Authority and invariant boundary

The dependency direction remains exact:

```text
generated REST types + realtime client + projection + transcript model
                              |
                         SessionPanel
                  authoritative coordinator
                              |
             derived presentation props + callbacks
                              |
     workspace / task / discussion / progress presentation
```

`SessionPanel` remains the only owner or coordinator of:

- Question discovery/detail and session snapshot loading;
- complete transcript loading, merge, conflict recovery and near-bottom
  follow decisions;
- the one realtime client and its recovery bundle;
- authoritative status, phase timing, floor and connection inputs;
- Human draft, one pending command, one rejected draft and exact submit gate;
- click-time re-read of the current Human floor grant;
- start/end callbacks, safe error input and AI waiting/interruption facts.

New state remains strictly presentation-local and is limited to:

- `notes: string`, one in-memory value keyed to the mounted session workspace;
- `activeSurface: "discussion" | "task" | "progress"`, one responsive
  visibility value;
- `boundQuestionLoadStatus: "loading" | "available" | "unavailable" |
  undefined`, the smallest UI-only discriminator needed to distinguish a bound
  Question fetch in progress, a successful bound Question fetch and a bound
  Question fetch that returned no data or failed. `undefined` means there is no
  active bound-Question fetch state, including a historical session with no
  binding.

These values enter neither REST, WebSocket, browser storage nor a global store.
`boundQuestionLoadStatus` is not Question identity, Question content, session
truth or retry authority; the existing snapshot binding and `question` value
remain authoritative inputs.

## Explicit non-goals and unchanged authorities

Implementation must not change:

- [`client.ts`](../../apps/web/src/lib/realtime/client.ts), including pending,
  resend, recovery and Unicode semantics;
- [`contract.ts`](../../apps/web/src/lib/realtime/contract.ts);
- [`projection.ts`](../../apps/web/src/lib/realtime/projection.ts);
- [`discussion-transcript.ts`](../../apps/web/src/features/sessions/discussion-transcript.ts);
- [`client.ts`](../../apps/web/src/lib/api/client.ts);
- [`schema.d.ts`](../../apps/web/src/lib/api/generated/schema.d.ts);
- backend production/tests, schema, migration or database authority;
- package manifests, lockfiles, CI, Docker, provider/config or prompt assets;
- voice, scoring, reports, voting, conclusion or F4 Human-to-AI acceptance.

No Redux, Zustand, Context-based business authority, component library, icon
package, external font or new dependency is introduced. Current Tailwind and
tooling remain sufficient.

## Actual-source assessment and planning decisions

The committed source establishes these implementation facts:

1. [`page.tsx`](../../apps/web/src/app/page.tsx) owns the current
   `max-w-3xl` outer constraint and unconditional internal-validation chrome.
2. [`auth-panel.tsx`](../../apps/web/src/app/auth-panel.tsx) is the earliest
   component that knows whether the user is authenticated. It must therefore
   select the narrow entry shell versus the full authenticated studio shell;
   it must not acquire session authority.
3. [`session-panel.tsx`](../../apps/web/src/features/sessions/session-panel.tsx)
   already owns every authoritative F3A state and callback. The composition
   work is extraction and prop wiring, not state relocation.
4. The generated Question, snapshot, floor participant/grant/lifecycle and
   transcript types contain all facts needed by the frozen design. No public
   contract change is justified.
5. The current `SessionPanel` tests have reusable authoritative fixtures for
   one Human plus three AI participants, all send gates, transcript identity,
   recovery and lifecycle events.
6. The current Browser harness runs all Playwright specs against one temporary
   database and its final verifier requires exactly one persisted session.
   Adding a second independent composition flow would break the harness for a
   test-data reason. Responsive composition coverage therefore extends the
   existing [`session.spec.ts`](../../apps/web/e2e/session.spec.ts) flow and
   creates no second spec or session.
7. Current F3A tests read session ID, Question Version ID, sequence and deadline
   from rendered diagnostic rows. F3B removes those raw engineering facts from
   the rendered product DOM, including the accessibility tree. Coordinator and
   Browser tests instead obtain identity and exact progression from the
   existing create response, REST snapshots, captured WS commands/events and
   mocked coordinator inputs. No `sr-only`, `aria-hidden`, test-only diagnostic
   markup, debug mode or runtime configuration is introduced.

No source contradiction or stop condition was found.

## Exact implementation file boundary

### Existing production files to modify

- `apps/web/src/app/page.tsx`
  - remove the unconditional prototype-width shell;
  - render one neutral full-width page root and delegate auth-specific shell
    choice to `AuthPanel`.
- `apps/web/src/app/auth-panel.tsx`
  - preserve all current auth/API behavior;
  - render existing entry/health/auth content in a constrained entry shell for
    loading and unauthenticated states;
  - render account/logout controls plus `SessionPanel` in the full
    authenticated shell.
- `apps/web/src/app/globals.css`
  - add only studio surface, focus, `dvh`, `min-height: 0` and reduced-motion
    primitives that cannot be expressed clearly at one component call site.
- `apps/web/src/features/sessions/session-panel.tsx`
  - remain authoritative coordinator;
  - add only the presentation-local notes, active-surface and bound-Question
    load-status values;
  - derive exact presentation props and compose extracted children;
  - retain current refs, effects, fetches, realtime creation and callbacks.

### New production files

- `apps/web/src/features/sessions/session-presentation.ts`
  - pure status, phase, connection, participant, floor and safe reason label
    mappings;
  - no React state, timers, network, transcript merge or transition logic.
- `apps/web/src/features/sessions/discussion-workspace.tsx`
  - compact header, three stable region slots, desktop grid, tablet support
    overlay and mobile tabs;
  - internal `SessionHeader` and responsive controls have no second caller and
    remain in this file;
  - no business state or network.
- `apps/web/src/features/sessions/task-brief-panel.tsx`
  - allowlisted Question rendering and the one controlled notes textarea;
  - no Question fetch and no storage.
- `apps/web/src/features/sessions/session-progress-panel.tsx`
  - exact six-phase rail, lifecycle/countdown/floor/connection presentation;
  - no state advancement, fixed duration, conclusion or vote module.
- `apps/web/src/features/sessions/discussion-stage.tsx`
  - center-region participant strip, confirmed transcript, Human composer and
    prioritized notices;
  - internal leaf components remain colocated because they share this single
    composition caller and their props are tested through one coherent stage;
  - no API/WS client, transcript merge or send-authority calculation.

This five-file component set is the smallest sensible extraction. Workspace,
Task Brief, Progress and Discussion Stage are independently meaningful and
testable. Header/tabs and participant/transcript/composer/notice leaves are
not split into one-file wrappers without another caller or independent
authority.

### Existing test files to modify

- `apps/web/src/app/page.test.tsx`;
- `apps/web/src/app/auth-panel.test.tsx`;
- `apps/web/src/features/sessions/session-panel.test.tsx`;
- `apps/web/e2e/session.spec.ts`.

### New test files

- `apps/web/src/features/sessions/session-presentation.test.ts`;
- `apps/web/src/features/sessions/discussion-workspace.test.tsx`;
- `apps/web/src/features/sessions/discussion-stage.test.tsx`.

`discussion-workspace.test.tsx` also exercises `TaskBriefPanel` and
`SessionProgressPanel` at their composition boundary. Separate trivial test
files for those panels are not created.

### Implementation-status documents

Only after all later implementation gates are green, status/evidence may be
updated in:

- `docs/TASKS.md`;
- `docs/exec-plans/P1-5_ai-runtime-foundation.md`;
- `docs/exec-plans/P1-5F-3B_complete-discussion-page-composition.md`;
- this implementation plan.

`docs/ROADMAP.md` needs no implementation-planning change and remains out of
scope unless an independently proven current-state contradiction appears.

## Exact presentation interfaces

The signatures below are frozen. Equivalent inline `type` versus `interface`
syntax is not a semantic change, but names, fields and ownership are exact.

### Pure presentation helpers

`session-presentation.ts` exports:

```ts
import type { SessionSnapshot } from "@/lib/api/client";
import type { RealtimeConnectionState } from "@/lib/realtime/client";

export const DISCUSSION_PHASES = [
  "PREPARATION",
  "OPENING_STATEMENTS",
  "EXPLORATION",
  "CONFLICT_AND_EVALUATION",
  "CONVERGENCE",
  "FINAL_SUMMARY",
] as const;

export type DiscussionPhase = (typeof DISCUSSION_PHASES)[number];

export type PresentationTone =
  | "neutral"
  | "current"
  | "information"
  | "recoverable"
  | "fatal";

export function phaseLabel(status: SessionSnapshot["status"]): string;
export function sessionStatusLabel(
  status: SessionSnapshot["status"],
): string;
export function connectionLabel(state: RealtimeConnectionState): string;
export function participantLabel(
  participants: SessionSnapshot["floor"]["participants"],
  participantId: string,
): string;
export function floorLifecycleLabel(
  event: SessionSnapshot["floor"]["latest_event"],
): string;
export function floorReasonLabel(reasonCode: string): string;
```

Mappings include all nine session statuses and the exact six frozen Chinese
phase labels. Helpers return display strings only; they do not decide whether
a command is legal or whether a phase advances.

### Workspace and header

`discussion-workspace.tsx` exports:

```ts
import type { ReactNode } from "react";
import type { RealtimeConnectionState } from "@/lib/realtime/client";

export type ActiveDiscussionSurface = "discussion" | "task" | "progress";

export type SessionHeaderAction = {
  visible: boolean;
  disabled: boolean;
  label: string;
  onActivate: () => void;
};

export type SessionHeaderProps = {
  productName: "AI 群面训练场";
  sessionTitle: string;
  phaseLabel: string;
  countdown: string | null;
  connection: RealtimeConnectionState;
  connectionLabel: string;
  startAction: SessionHeaderAction;
  endAction: SessionHeaderAction;
};

export type DiscussionWorkspaceProps = {
  header: SessionHeaderProps;
  taskBrief: ReactNode;
  discussion: ReactNode;
  progress: ReactNode;
  activeSurface: ActiveDiscussionSurface;
  onActiveSurfaceChange: (surface: ActiveDiscussionSurface) => void;
};

export default function DiscussionWorkspace(
  props: DiscussionWorkspaceProps,
): ReactNode;
```

The three region nodes are mounted once. CSS and the one `activeSurface`
value control visibility; tab/sheet switching does not recreate state,
refetch or reconnect. Desktop ignores `activeSurface` and shows all regions.
Tablet always shows Discussion and uses Task/Progress controls for at most one
support overlay. Mobile exposes semantic tabs in exact order `讨论 / 题目 /
进程`, defaulting to Discussion.

### Task Brief

`task-brief-panel.tsx` exports:

```ts
import type { QuestionDetail } from "@/lib/api/client";

export type TaskBriefQuestionState =
  | { kind: "available"; question: QuestionDetail }
  | { kind: "loading" }
  | { kind: "historical-missing" }
  | { kind: "unavailable" };

export type TaskBriefPanelProps = {
  questionState: TaskBriefQuestionState;
  notes: string;
  onNotesChange: (value: string) => void;
};

export default function TaskBriefPanel(
  props: TaskBriefPanelProps,
): React.ReactNode;
```

Only title, scenario, objective, non-empty hard constraints, present options
and useful mapped public metadata render. Notes are a controlled textarea with
copy stating that refresh does not save them. Soft constraints and
stakeholders remain unrendered in this implementation because actual content
density does not justify them. Raw IDs and private fields never enter props.
The four Question states have exact, non-overlapping meanings:

- `available`: the bound Question detail loaded and is passed as `question`;
- `loading`: a non-null authoritative binding is currently being loaded;
- `historical-missing`: the authoritative session has no Question Version
  binding;
- `unavailable`: the authoritative binding is non-null, but the existing
  `getQuestion(...)` call failed or returned no data. It renders the frozen safe
  copy `题目内容暂时无法加载，讨论记录仍可继续查看`.

`historical-missing` never represents a failed bound fetch, and `unavailable`
never erases or rewrites the session binding. No retry control or new API
behavior is part of Task Brief.

### Session Progress

`session-progress-panel.tsx` exports:

```ts
import type { SessionSnapshot } from "@/lib/api/client";
import type { RealtimeConnectionState } from "@/lib/realtime/client";

export type SessionProgressPanelProps = {
  status: SessionSnapshot["status"];
  countdown: string | null;
  participants: SessionSnapshot["floor"]["participants"];
  currentGrant: SessionSnapshot["floor"]["current_grant"];
  latestFloorEvent: SessionSnapshot["floor"]["latest_event"];
  connection: RealtimeConnectionState;
};

export default function SessionProgressPanel(
  props: SessionProgressPanelProps,
): React.ReactNode;
```

The panel renders all six phases in order, active/completed/remaining visual
states, display-only countdown, safe floor owner/lifecycle text and lightweight
connection state. It does not receive phase deadlines or callbacks that could
advance state.

### Discussion Stage

`discussion-stage.tsx` exports:

```ts
import type { RefObject } from "react";
import type { SessionSnapshot } from "@/lib/api/client";
import type {
  HumanDraftInspection,
  RealtimeConnectionState,
} from "@/lib/realtime/client";
import type { ConfirmedUtterance } from "./discussion-transcript";

export type RejectedDraftPresentation = {
  content: string;
  message: string;
  restoreLabel: string;
};

export type DiscussionNotice = {
  key: string;
  message: string;
};

export type DiscussionStageProps = {
  status: SessionSnapshot["status"];
  participants: SessionSnapshot["floor"]["participants"];
  currentGrant: SessionSnapshot["floor"]["current_grant"];
  confirmedTranscript: readonly ConfirmedUtterance[];
  transcriptContainerRef: RefObject<HTMLDivElement | null>;
  draft: string;
  draftInspection: HumanDraftInspection;
  canSend: boolean;
  sendDisabledReason: string;
  onDraftChange: (value: string) => void;
  onSubmit: () => void;
  pendingContent: string | null;
  rejectedDraft: RejectedDraftPresentation | null;
  onRestoreRejectedDraft: () => void;
  connection: RealtimeConnectionState;
  connectionLabel: string;
  errorMessage: string | null;
  aiWaitingLabel: string | null;
  interruptedAiNotices: readonly DiscussionNotice[];
  showComposer: boolean;
};

export default function DiscussionStage(
  props: DiscussionStageProps,
): React.ReactNode;
```

The stage receives exact values and callbacks only. It never imports the API
client, realtime constructor or projection. Pending/rejected presentation
omits action/grant IDs. `onSubmit` remains the coordinator callback that
re-reads `snapshotRef.current`; no child captures a floor grant. The transcript
ref remains coordinator-owned so the existing near-bottom decision is
unchanged.

### SessionPanel integration

`SessionPanel` adds:

```ts
type BoundQuestionLoadStatus = "loading" | "available" | "unavailable";

const [notes, setNotes] = useState("");
const [activeSurface, setActiveSurface] =
  useState<ActiveDiscussionSurface>("discussion");
const [boundQuestionLoadStatus, setBoundQuestionLoadStatus] =
  useState<BoundQuestionLoadStatus>();
const workspaceSessionIdRef = useRef<string | undefined>(undefined);
```

When `applySnapshot(...)` observes a different session ID, and only then, it
sets the workspace ID, clears notes and returns `activeSurface` to Discussion.
Recovery bundles for the same session never clear notes, draft or selection.
Initial mount and full page reload naturally begin with empty notes.

The existing bound-Question load sites set `boundQuestionLoadStatus` to
`loading` immediately before the existing `getQuestion(...)` call, to
`available` only when that call returns data, and to `unavailable` when it
returns no data or throws. A different/new workspace clears the prior
`question` and prior load status before deriving its own historical-missing or
loading state; a later successful load therefore replaces stale unavailable
copy with the available Question. A null snapshot binding derives
`historical-missing` without calling `getQuestion(...)`. These transitions add
no retry, fetch path, API/schema behavior or session/Question authority.

Task Brief state derivation is exact: loaded `question` plus `available` maps to
`available`; a non-null binding plus `loading` maps to `loading`; a null binding
maps to `historical-missing`; and a non-null binding plus `unavailable` maps to
`unavailable`. The stable unavailable state does not depend on generic
`errorMessage`, so a realtime connection update cannot clear it accidentally.

`SessionPanel` keeps the current `canSend` calculation and
`submitCurrentDraft()` body. It passes:

- `onSubmit={submitCurrentDraft}`;
- `onDraftChange={setDraft}`;
- lifecycle callbacks that call only the existing realtime client methods;
- safe presentational projections of pending, rejected and interrupted facts;
- `showComposer` false only for `COMPLETED` and `ABORTED_USER`.

Raw session UUID, Question Version UUID, sequence, server deadline and similar
engineering diagnostics are removed from rendered markup rather than moved to
`sr-only`. Genuine product elements such as phase, floor, transcript, composer
and connection presentation may retain stable `data-testid` hooks. Tests that
need raw authority use non-DOM create/REST/WS or mock evidence as frozen below;
no raw diagnostic compatibility surface is exposed visually or to assistive
technology.

## TDD execution protocol

Each batch follows this order:

1. add or update the named tests;
2. run the exact RED command and confirm the stated product-facing failure;
3. implement the smallest production delta that satisfies that batch;
4. run the focused GREEN command;
5. run the batch regression gate;
6. inspect changed files before entering the next batch.

A failure caused by missing dependencies, broken environment or unrelated
baseline regression is not an acceptable RED result. A successful gate may be
reused by the final validation only when no file in that gate's dependency
surface changes afterward.

## Batch 1 — Workspace shell and responsive composition contracts

### Exact files

Tests first:

- modify `apps/web/src/app/page.test.tsx`;
- modify `apps/web/src/app/auth-panel.test.tsx`;
- create `apps/web/src/features/sessions/session-presentation.test.ts`;
- create `apps/web/src/features/sessions/discussion-workspace.test.tsx`.

Then production:

- modify `apps/web/src/app/page.tsx`;
- modify `apps/web/src/app/auth-panel.tsx`;
- modify `apps/web/src/app/globals.css`;
- create `apps/web/src/features/sessions/session-presentation.ts`;
- create `apps/web/src/features/sessions/discussion-workspace.tsx`;
- create `apps/web/src/features/sessions/task-brief-panel.tsx`;
- create `apps/web/src/features/sessions/session-progress-panel.tsx`.

### Tests written first

Freeze tests for:

- loading/unauthenticated states retaining current product, health and auth
  entry content inside a constrained entry shell;
- authenticated state removing internal-validation chrome from the studio and
  preserving current username/logout/`SessionPanel` behavior;
- exact phase and connection labels, including `讨论与评估` and frozen safe
  connection copy;
- desktop three stable semantic regions with center priority;
- tablet Discussion primary plus mutually exclusive Task/Progress support;
- mobile exact tab order, selected state, keyboard semantics and default
  Discussion surface;
- one mounted instance per supplied region while switching visibility;
- Task Brief allowlist, empty-collection behavior, plain-text rendering,
  controlled memory-only note copy and all four exact Question presentations:
  available detail, bound loading, historical missing binding, and bound load
  failure with `题目内容暂时无法加载，讨论记录仍可继续查看`;
- six exact phases, safe current-floor labeling, no fabricated countdown,
  conclusion or vote content.

### RED command and expected failure

```powershell
pnpm.cmd --filter @group-interview-arena/web test -- src/app/page.test.tsx src/app/auth-panel.test.tsx src/features/sessions/session-presentation.test.ts src/features/sessions/discussion-workspace.test.tsx
```

Expected RED: new presentation modules do not exist; the committed page keeps
the authenticated experience inside `max-w-3xl`; auth state does not select a
full studio shell; semantic regions/tabs, exact product labels and the distinct
safe unavailable-Question presentation are absent.

### Minimal GREEN implementation

- move existing entry chrome into the loading/unauthenticated branch owned by
  `AuthPanel`, without changing authentication requests or error mapping;
- make `page.tsx` a neutral full-width root;
- implement the pure mappings and complete reusable workspace shell;
- implement Task Brief's four-state discriminated presentation and Progress as
  controlled presentation components;
- add only the minimal global CSS primitives described by the file boundary;
- continue rendering the existing `SessionPanel` in the authenticated shell;
  Batch 2 supplies its complete workspace children.

### Focused GREEN command

Run the RED command unchanged. Expected result: all named tests pass.

### Batch regression gate

```powershell
pnpm.cmd --filter @group-interview-arena/web test -- src/app/page.test.tsx src/app/auth-panel.test.tsx src/features/sessions/session-panel.test.tsx src/features/sessions/session-presentation.test.ts src/features/sessions/discussion-workspace.test.tsx
```

This proves the app-shell change does not break current F3A coordinator tests.

### Consumes and produces

Consumes: frozen layout, public generated types, current auth boundary and
Tailwind baseline.

Produces for Batch 2: complete app shell, pure label helpers,
`DiscussionWorkspaceProps`, `TaskBriefPanelProps` and
`SessionProgressPanelProps`, including the exact four-member
`TaskBriefQuestionState`. It produces no new session or Question authority.

## Batch 2 — Discussion presentation extraction and F3A integration

### Exact files

Tests first:

- create `apps/web/src/features/sessions/discussion-stage.test.tsx`;
- modify `apps/web/src/features/sessions/session-panel.test.tsx`.

Then production:

- create `apps/web/src/features/sessions/discussion-stage.tsx`;
- modify `apps/web/src/features/sessions/session-panel.tsx`.

### Tests written first

Freeze focused stage tests for:

- one Human and three explicitly labeled AI candidates in safe seat order;
- current Human, current AI waiting and neutral participant states derived
  only from supplied public props;
- professional one-column confirmed transcript with exact whitespace/plain
  text and no `aria-live` on the list;
- sticky composer with Enter newline, Ctrl/Cmd+Enter callback, exact count,
  `canSend` and supplied disabled reason;
- pending content outside transcript, rejected content with explicit restore,
  and newer draft preservation delegated through callbacks;
- notice priority: safe error/recovery, rejection, pending, AI interruption,
  then AI waiting;
- terminal `showComposer=false` behavior without fake report controls.

Extend coordinator tests to prove:

- the existing snapshot/transcript/realtime setup count remains one;
- `SessionPanel` passes derived props without presentation children fetching;
- exact click-time Human grant and content still reach
  `submitHumanUtterance(...)`;
- draft, pending, rejected and confirmed content remain distinct;
- near-bottom scroll ref and conflict recovery behavior remain unchanged;
- notes and active surface survive same-session recovery but reset only when a
  different workspace session is applied;
- a non-null binding whose existing `getQuestion(...)` returns no data or
  throws produces stable `unavailable` Task Brief copy even after realtime
  reports `connected` and clears the generic error channel;
- a historical null binding produces `historical-missing`, never
  `unavailable`, and makes no Question-detail call;
- a later successful bound load for a fresh/new workspace transitions through
  `loading` to `available`, renders the new Question and does not retain the
  previous unavailable copy;
- switching responsive surfaces causes zero additional Question/snapshot/
  transcript calls and zero additional realtime client creation.

Existing coordinator tests that currently query raw session ID, Question
Version ID, sequence or server deadline rows are rewritten in this batch.
State projection is asserted through genuine product output and the existing
mocked snapshot/realtime callbacks; exact raw values stay in test fixtures and
mock evidence rather than rendered markup.

### RED command and expected failure

```powershell
pnpm.cmd --filter @group-interview-arena/web test -- src/features/sessions/discussion-stage.test.tsx src/features/sessions/session-panel.test.tsx
```

Expected RED: `DiscussionStage` is absent; `SessionPanel` still emits the long
single-column markup, owns no notes/surface/bound-Question load-status state,
cannot preserve unavailable Question copy independently from generic realtime
errors, still exposes raw diagnostic rows and does not compose the Batch 1
workspace contracts.

### Minimal GREEN implementation

- move participant, transcript, composer and notice markup into the stage
  without moving refs, effects, merge, gates or client creation;
- add the three presentation-local values and exact session-key/load-status
  resets;
- wrap only the already-existing bound `getQuestion(...)` calls with
  loading/available/unavailable UI transitions; do not add a fetch, retry,
  endpoint, schema behavior or Question/session authority;
- derive Task Brief, Stage, Progress and Header props from existing state;
- render the three region nodes once through `DiscussionWorkspace`;
- keep `submitCurrentDraft()` and lifecycle callbacks in `SessionPanel`;
- remove raw diagnostic rows from rendered markup and migrate their tests to
  existing mock/create/REST/WS evidence; retain `data-testid` only on genuine
  product elements;
- delete superseded long-column presentation only after equivalent tests are
  green; do not duplicate the old and new UI.

### Focused GREEN command

Run the RED command unchanged. Expected result: all named tests pass.

### Batch regression gate

```powershell
pnpm.cmd web:test
```

Expected result: the complete Web Vitest suite passes, including unchanged
contract, realtime client, projection and transcript semantics.

### Consumes and produces

Consumes: Batch 1 presentation contracts and the existing F3A coordinator
state/callback surface.

Produces for Batch 3: one complete authoritative studio composition with
extracted presentation, one notes value, one active-surface value, one UI-only
bound-Question load-status value and all F3A unit semantics preserved. It
produces no retry behavior or diagnostic UI.

## Batch 3 — Lifecycle polish, responsive browser and final acceptance

### Exact files

Tests first and then minimal production polish in the same named surfaces:

- modify `apps/web/src/features/sessions/session-presentation.test.ts`;
- modify `apps/web/src/features/sessions/discussion-workspace.test.tsx`;
- modify `apps/web/src/features/sessions/discussion-stage.test.tsx`;
- modify `apps/web/src/features/sessions/session-panel.test.tsx`;
- modify `apps/web/e2e/session.spec.ts`;
- modify, only where a failing test requires presentation correction:
  - `apps/web/src/features/sessions/session-presentation.ts`;
  - `apps/web/src/features/sessions/discussion-workspace.tsx`;
  - `apps/web/src/features/sessions/task-brief-panel.tsx`;
  - `apps/web/src/features/sessions/session-progress-panel.tsx`;
  - `apps/web/src/features/sessions/discussion-stage.tsx`;
  - `apps/web/src/features/sessions/session-panel.tsx`;
  - `apps/web/src/app/globals.css`.

No new production or browser-test file is added in this batch.

### Tests written first

Component/coordinator coverage is exact for:

- no session/Question selection;
- `CREATED` with Start/End and disabled send;
- `PREPARATION` with notes emphasis and authoritative countdown;
- each of the five speaking phases;
- Human floor, AI floor and no-floor/intervention transition;
- Human pending, rejected draft, reconnect/recovery and AI interruption;
- `COMPLETED` and `ABORTED_USER` with no composer submission or lifecycle
  action;
- available Question, bound loading, historical missing binding, bound
  Question load failure and a successful later/new-workspace Question load;
- all six phase labels/order, notice priority and safe no-floor copy;
- no private/provider/model/prompt/persona/score/vote/conclusion strings;
- focus stability, visible focus styles, labels, semantic regions and tabs;
- no duplicate live regions and no transcript-wide live region;
- no raw session UUID, Question Version UUID, sequence, server deadline or
  equivalent engineering diagnostic in visual text, accessible text/name or
  an `sr-only`/test-only compatibility container. Genuine product test IDs
  remain allowed.

The existing Playwright flow is extended without creating another session and
is migrated away from raw diagnostic DOM rows:

1. parse the existing `POST /sessions` response and prove its authoritative
   session ID, Question Version binding and initial `last_sequence`; keep the
   existing create request/body and `session_id` URL-binding assertions;
2. `1440x900`: assert compact header plus simultaneous Task/Discussion/
   Progress regions, center greater than either rail, independent transcript
   overflow and reachable composer;
3. `1024x768`: assert Discussion remains primary, Task/Progress support
   controls exist, and only one support region opens;
4. `390x844`: assert exact tabs, default Discussion, keyboard-accessible
   switching and reachable composer;
5. enter a unique note, switch surfaces and viewports, assert the same value,
   assert browser storage remains empty, reload, and assert the note is empty;
6. return to `1440x900` and continue the complete existing F3A start, Human
   floor, exact submit and durable confirmation path. Prove sequence progression
   from the create response plus already captured floor/Human-created/
   Human-release WS events, and prove Human causation by matching command/event
   `action_id`, exact floor grant, participant and content as before;
7. after completion, read the existing authoritative REST snapshot before the
   duplicate-replay check, derive `finalSequence` from `last_sequence`, prove it
   advances beyond the Human release, and use it for `after_sequence`;
8. after API recovery and page reload, prove persistence through the existing
   REST session snapshot, exact confirmed transcript content, completed/floor
   product UI and Question content. No raw ID, sequence or deadline selector is
   used, and the durable action/event/storage assertions retain their current
   semantic strength.

The Browser test also asserts that the raw session UUID, Question Version UUID,
sequence and ISO deadline are absent from rendered and accessibility-facing
product content. It does not require them to be hidden in DOM. No separate
debug mode, runtime config, API route or Python harness change is allowed.

The test attaches deterministic wide/tablet/mobile screenshots through
Playwright's per-test output for human review. Screenshots are evidence only,
not pixel-diff assertions and not committed baselines.

### RED commands and expected failure

Component RED:

```powershell
pnpm.cmd --filter @group-interview-arena/web test -- src/features/sessions/session-presentation.test.ts src/features/sessions/discussion-workspace.test.tsx src/features/sessions/discussion-stage.test.tsx src/features/sessions/session-panel.test.tsx
```

Expected RED: at least the newly frozen lifecycle, terminal, four-state
Question, raw-diagnostic absence, privacy, focus or notice assertions fail
until polish is complete.

Browser RED, after component GREEN and before browser-specific corrections:

```powershell
pnpm.cmd web:test:e2e
```

Expected RED: the new semantic viewport assertions expose any incorrect
desktop proportions, tablet support visibility, mobile tabs, notes reset or
raw diagnostic exposure. The selector migration initially fails until create,
REST and WS evidence replaces raw DOM reads. The old durable F3A identity,
sequence progression, Human causation and persistence semantics must remain
green; weakening any of them is a blocker, not an acceptable RED.

### Minimal GREEN implementation

- correct only the presentation component or prop derivation named by a
  failing acceptance test;
- use current Tailwind/CSS, semantic HTML and stable test IDs;
- preserve all coordinator callbacks and realtime/transcript source;
- update existing Browser raw-diagnostic selectors to the already available
  create response, REST snapshots and captured WS frames without weakening
  durable identity/action/event/sequence/storage assertions;
- delete raw diagnostic markup instead of moving it to `sr-only` or adding a
  debug/config surface; retain test IDs only on genuine product elements;
- keep one browser session/spec and leave the Python harness untouched.

### Focused GREEN commands

Run both RED commands unchanged. Expected result: component tests and real
Chromium suite pass.

### Batch regression gate

```powershell
pnpm.cmd web:test
pnpm.cmd web:test:e2e
```

The Chromium command is not rerun in the final aggregate gate unless a
browser-relevant file changes afterward.

### Consumes and produces

Consumes: the complete Batch 2 composition and existing deterministic browser
harness.

Produces: frozen F3B presentation behavior across lifecycle and three viewport
bands, transient notes/privacy proof, accessibility evidence, visual review
artifacts and unchanged F3A durable Human semantics. It does not produce or
claim F4 Human-to-AI composition acceptance.

## Final implementation validation gate

Run from repository root after all three batches are green.

### Web quality

```powershell
pnpm.cmd install --frozen-lockfile
pnpm.cmd web:format:check
pnpm.cmd web:lint
pnpm.cmd web:typecheck
pnpm.cmd web:test
pnpm.cmd web:build
```

### Live generated REST drift

With the existing API application running locally on port 8000, run:

```powershell
pnpm.cmd web:api:check
git diff --exit-code -- apps/web/src/lib/api/generated/schema.d.ts
```

Stop the local API afterward. No provider call is made.

### Chromium

If no browser-relevant file changed after the Batch 3 green Chromium run, use
that result. Otherwise rerun exactly:

```powershell
pnpm.cmd web:test:e2e
```

### Immutable/prohibited-domain proof

```powershell
$expectedMaster = '2388a9660320406cb35d5354126ad71c6849a98db7c4a356796ca951bf372f26'
$actualMaster = (Get-FileHash -Algorithm SHA256 -LiteralPath 'docs/PROJECT_MASTER_PLAN.md').Hash.ToLowerInvariant()
if ($actualMaster -ne $expectedMaster) { throw 'Master Plan SHA-256 changed' }

git diff --exit-code -- apps/api
git diff --exit-code -- apps/web/src/lib/api/client.ts
git diff --exit-code -- apps/web/src/lib/api/generated/schema.d.ts
git diff --exit-code -- apps/web/src/lib/realtime
git diff --exit-code -- apps/web/src/features/sessions/discussion-transcript.ts
git diff --exit-code -- package.json pnpm-lock.yaml pnpm-workspace.yaml apps/web/package.json apps/api/pyproject.toml apps/api/uv.lock
git diff --exit-code -- .github infra
```

### Exact changed-file allowlist

```powershell
$allowed = [System.Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal)
@(
  'apps/web/src/app/page.tsx',
  'apps/web/src/app/page.test.tsx',
  'apps/web/src/app/auth-panel.tsx',
  'apps/web/src/app/auth-panel.test.tsx',
  'apps/web/src/app/globals.css',
  'apps/web/src/features/sessions/session-panel.tsx',
  'apps/web/src/features/sessions/session-panel.test.tsx',
  'apps/web/src/features/sessions/session-presentation.ts',
  'apps/web/src/features/sessions/session-presentation.test.ts',
  'apps/web/src/features/sessions/discussion-workspace.tsx',
  'apps/web/src/features/sessions/discussion-workspace.test.tsx',
  'apps/web/src/features/sessions/task-brief-panel.tsx',
  'apps/web/src/features/sessions/session-progress-panel.tsx',
  'apps/web/src/features/sessions/discussion-stage.tsx',
  'apps/web/src/features/sessions/discussion-stage.test.tsx',
  'apps/web/e2e/session.spec.ts',
  'docs/TASKS.md',
  'docs/exec-plans/P1-5_ai-runtime-foundation.md',
  'docs/exec-plans/P1-5F-3B_complete-discussion-page-composition.md',
  'docs/exec-plans/P1-5F-3B_complete-discussion-page-composition-implementation.md'
) | ForEach-Object { [void]$allowed.Add($_) }

$changed = @(git status --porcelain=v1 | ForEach-Object {
  $_.Substring(3).Replace('\', '/')
})
$unexpected = @($changed | Where-Object { -not $allowed.Contains($_) })
if ($unexpected.Count -gt 0) {
  throw "Unexpected F3B paths: $($unexpected -join ', ')"
}
```

Both finding remediations fit the existing allowlist: Question presentation
state is implemented and tested in the already-listed Task Brief/SessionPanel
surfaces, while raw-diagnostic selector migration stays in the already-listed
SessionPanel tests and existing `session.spec.ts`. No new source/test/config
path is authorized.

### Final diff and Git state

```powershell
git diff --check
$staged = @(git diff --cached --name-only)
if ($staged.Count -ne 0) {
  throw "Unexpected staged files: $($staged -join ', ')"
}
git status --short
```

No automatic `git add`, commit or push command is part of implementation.

## Requirement-to-batch coverage

- Authenticated shell expansion and preserved entry/auth boundary: Batch 1.
- Desktop/tablet/mobile ownership, header, tabs and support panel: Batch 1.
- Task Brief, memory-only notes and six-phase Progress: Batch 1, integrated in
  Batch 2 and browser-verified in Batch 3.
- Four distinct Task Brief states, stable safe bound-load failure copy, and a
  successful later/new-workspace load: Batch 1 component contract plus Batch 2
  coordinator transitions and Batch 3 lifecycle coverage.
- Participant strip, confirmed transcript, sticky composer and notices:
  Batch 2.
- SessionPanel-only authority and no second client/fetch/store: Batch 2 tests
  plus final prohibited-domain proof.
- All current lifecycle states, missing Question and terminal behavior:
  Batch 3.
- Accessibility, privacy/storage and deterministic responsive evidence:
  Batch 3.
- Raw engineering facts absent from both visual and assistive product content,
  with identity/sequence/causation/persistence derived from non-DOM authority:
  Batch 2 test migration plus Batch 3 Browser flow.
- F3A regression, exact Human floor/content, recovery and durable Chromium
  path: Batch 2 regression plus Batch 3 existing browser flow.
- No backend/generated/dependency/provider/F4 expansion: every batch boundary
  and final scope gates.

Coverage gaps: none.

## Implementation stop conditions

Stop and report the exact contradiction before changing scope if any batch
requires:

- backend, DB, migration, REST/WS or generated contract change;
- realtime client, projection, contract or transcript semantic change;
- another API/WS client, authoritative fetch path or state store;
- a dependency, lockfile, CI, Docker or provider/config change;
- browser storage for notes, draft, pending, transcript or session truth;
- a Question retry control, additional Question fetch, API/schema change or
  authority beyond the existing snapshot binding and detail load;
- duplicate mobile/desktop component authority;
- a fourth responsive band;
- fake pause, voice, conclusion, vote, report, score or AI lifecycle facts;
- private Persona, prompt, provider, model or internal action data in UI;
- raw session/Question UUID, sequence, server deadline or equivalent
  engineering diagnostics in visual or accessibility-facing product content;
- `sr-only`, `aria-hidden` or test-only diagnostic compatibility markup, a
  debug mode or new runtime configuration for raw test evidence;
- modification of the Python E2E harness to accommodate extra F3B test data;
- weakening the existing F3A Browser durable assertions;
- treating screenshot pixel equality as the primary correctness oracle;
- beginning F4 complete Human-to-AI composition acceptance.

Do not solve a stop condition by silently expanding the allowlist.

## Implementation-plan self-review

1. Frozen-design coverage: every design acceptance group A–J maps to a batch
   and final gate; the two narrow review clarifications add truthful Question
   failure and accessibility-safe diagnostic handling without redesign;
   coverage gaps are none.
2. Completeness: every batch names exact files, tests, RED command/failure,
   minimal GREEN step, focused GREEN, regression and handoff contract; no
   stub or unresolved instruction remains.
3. Type/interface consistency: `ActiveDiscussionSurface`,
   `SessionHeaderAction`, `SessionHeaderProps`, `DiscussionWorkspaceProps`,
   `TaskBriefQuestionState`, `BoundQuestionLoadStatus`, `TaskBriefPanelProps`,
   `SessionProgressPanelProps`, `RejectedDraftPresentation`,
   `DiscussionNotice` and `DiscussionStageProps` have one exact spelling and
   ownership throughout.
4. Architecture: `SessionPanel` remains the only coordinator; presentation
   modules receive public values/callbacks and import no client constructor,
   projection or store.
5. Data claims: every visible fact comes from current generated REST/F3A
   public state or explicit page-local presentation state; historical missing
   and bound-load unavailable are distinct; raw diagnostic authority comes
   from non-DOM create/REST/WS/mock evidence; no unsupported conclusion, vote,
   score, voice or model lifecycle appears.
6. Independent testability: Batch 1 components are complete and testable
   before integration; Batch 2 composes them without a duplicate controller;
   Batch 3 closes lifecycle/browser behavior on a green integrated surface.
7. Handoffs: each batch's produced interfaces and state are documented; later
   batches rely on no hidden behavior.
8. Gate sufficiency: focused tests cover all four Question presentations,
   failure stability, later success and diagnostic absence; full Vitest runs
   after integration/polish; Chromium retains session identity, sequence
   progression, Human causation and persistence via authoritative non-DOM
   evidence; final lint/type/build/OpenAPI/scope checks add distinct evidence
   without planned redundant execution.

Hidden architecture expansion: none. `F3B-IP-001`: `CLOSED`.
`F3B-IP-002`: `CLOSED`. Open findings: `NONE`. Planning stop conditions
triggered: none.

## Planning progress

- Baseline and exact CI evidence: verified.
- Authority and actual-source inspection: completed.
- Frozen-design requirement mapping: completed.
- Exact component/file boundary: frozen.
- Three integration batches and TDD commands: frozen.
- Interface consistency review: `PASS`.
- Finding-only remediation: `F3B-IP-001 CLOSED`; `F3B-IP-002 CLOSED`.
- Remediated implementation-plan self-review: `PASS`.
- F3B state: `DESIGN_FROZEN / IMPLEMENTATION_PLAN_FROZEN /
  IMPLEMENTATION_NOT_STARTED`.
- Open findings: `NONE`.
- F4: `NOT_STARTED`.
- Stage/commit/push authorization: none.
