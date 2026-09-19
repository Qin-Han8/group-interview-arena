# P1-8-F010 Demo V2 Information Architecture / Visual Alignment Implementation Plan

> **For Codex:** REQUIRED SUB-SKILL: Use `$gia-phase-runner` to execute this plan task-by-task only after explicit user approval.

**Goal:** Recompose the real P1 frontend into the approved Demo V2 information architecture—public auth entry, normal authenticated ProductShell, Bento lobby, categorized 12-question setup, focused resizable training workspace, evidence report, and truthful settings center—without changing P1 data or behavior contracts.

**Architecture:** Keep authentication in route-level clients, keep the full authoritative `SessionSnapshot` and realtime lifecycle in `SessionPanel`, and expose only a narrow navigation projection outside the feature. Normal authenticated pages use ProductShell; real non-terminal sessions switch to a full-viewport focused presentation without remounting SessionPanel. A UI-only resizable workspace persists only versioned left/right widths in browser storage, and `/settings` consumes that same helper plus existing auth/logout. Use existing public question, session and report contracts only.

**Tech Stack:** Next.js 16, React 19, TypeScript, Tailwind CSS 4/global CSS, Vitest + Testing Library, Playwright, existing Python/PostgreSQL browser harnesses.

**Approved design:** [`docs/superpowers/specs/2026-09-15-p1-8-f010-demo-v2-alignment-design.md`](../specs/2026-09-15-p1-8-f010-demo-v2-alignment-design.md)

**Execution checkpoint (2026-09-19):** Tasks 1–9 are implemented and user-approved; Task 10 final visual matrix and real-flow verification, Final Composition Acceptance, the sole Pyright blocker repair/verification and Registration Password Policy Option B repair/re-verification all passed. F010 and P1-8 are `DONE / CLOSED`; P1-7E subsequently completed composition/independent acceptance, and P1 phase-close assessment/re-assessment passed. P1 is `DONE / CLOSED`.

---

## 1. Frozen source and scope

### 1.1 Baseline recovered for this plan

- Repository: current `group-interview-arena` repository root
- Branch: `main`
- HEAD: `305e6792ee73eda12a03e3a527f0c83a3da15321`
- Master-plan SHA-256: `2388A9660320406CB35D5354126AD71C6849A98DB7C4A356796CA951BF372F26`
- Existing dirty worktree: approved P1-8/F005–F009 source, test and governance changes plus the untracked P1-8 execution plan and F010 design specification; these changes must be preserved.

### 1.2 Actual contracts confirmed before planning

- `QuestionSummaryResponse`: `id`, `question_template_id`, `version_number`, `title`, `question_type`, `background_domain`, `difficulty`, `estimated_minutes`.
- `QuestionDetailResponse`: all Summary fields plus `scenario`, `objective`, `hard_constraints`, `soft_constraints`, `stakeholders`, `options`.
- Published catalog: exactly 12 versions, split 4 `ORDERING_SELECTION`, 4 `RESOURCE_ALLOCATION`, 4 `PLAN_DESIGN`.
- Product labels: `ORDERING_SELECTION → 排序选择型`; `RESOURCE_ALLOCATION → 资源分配型`; `PLAN_DESIGN → 方案策划型`.
- `SessionSnapshot["status"]`: `CREATED | PREPARATION | OPENING_STATEMENTS | EXPLORATION | CONFLICT_AND_EVALUATION | CONVERGENCE | FINAL_SUMMARY | COMPLETED | ABORTED_USER`.
- Report status: `REQUESTED | RUNNING | COMPLETED | FAILED`; POST generates, GET reads, route remains `/sessions/[sessionId]/report`.
- Mobile workspace tabs: `discussion | task | progress`; their state is local presentation state and does not remount the supplied regions.
- SessionPanel owns URL recovery, REST hydration, WebSocket lifecycle, floor, draft, pending/rejected Human utterances, transcript merge/follow state and F007 live-AI render provenance.

### 1.3 Hard boundaries

- Do not modify `apps/api`, OpenAPI, generated schema, database, migration, WebSocket protocol or report parser field allowlist.
- Do not add dependencies, component libraries, state libraries, Tailwind migration, CSS-in-JS, animation framework or design-token package.
- Do not add future routes other than the approved `/settings`, report history, public Memory, scores, radar, payment, device checks, growth, P2/P3 behavior or Demo Mock data. Browser persistence is limited to the approved v1 workspace-width preference; no business/session data may be stored.
- Preserve F005–F009 behavior, especially safe timing telemetry, AI-local preparing state, URL/realtime recovery, pending/rejected drafts, single-scroll ownership and privacy sentinels.
- Tasks 1–9 keep their per-task TDD order where implementation is introduced: observe the stated RED failure before minimal implementation and the GREEN rerun. Task 10 is final aggregate acceptance and does not require an artificial failing assertion.
- Visual comparison must reopen the original Demo V2 screenshots/source from `D:\Users\HP\Downloads\ai-group-interview-full-demo-standalone-v2 (2).zip`; memory and this plan's textual description are not sufficient references.
- Tasks 2–5 are already user-approved. Task 6, Task 7 and Task 8 each stop after reporting the required visual/interaction evidence. Work resumes only after explicit user visual approval for that gate.
- Stop immediately if any API/backend file becomes necessary.
- Every task ends with focused diff review and explicit no-commit/no-push confirmation; no task contains an automatic Git write.

## 2. Planned component and interface boundary

### New small presentational files

1. `apps/web/src/app/product-shell.tsx`
   - exports `ProductEntryShell` and `AuthenticatedAppShell`;
   - renders product brand, grouped navigation, top context bar, account display and content canvas;
   - receives already-derived navigation presentation and callbacks;
   - performs no auth, session, report or realtime request.
2. `apps/web/src/app/product-shell.test.tsx`
   - proves grouping, current/disabled semantics, callbacks, compact navigation and content-scroll mode.
3. `apps/web/src/features/sessions/training-entry.tsx`
   - renders the Bento lobby and categorized setup from supplied real question state;
   - owns only local presentational tab choice; no API calls or persistence.
4. `apps/web/src/features/sessions/training-entry.test.tsx`
   - proves truthful lobby content, 4/4/4 grouping fixtures, accessible selection and selected-detail states.
5. `apps/web/src/features/sessions/question-presentation.ts`
   - exports the closed public type-label map and small display helpers shared by setup and TaskBriefPanel;
   - contains no backend enum rewrite or fallback business behavior.
6. `apps/web/src/features/reports/report-page-client.test.tsx`
   - proves route-level auth bootstrap/logout and shared Shell composition around ReportView.

### Exact app-shell interface produced by Task 1

```ts
export type ProductShellNavigation = {
  activeItem: "simulation" | "report";
  simulation: {
    disabled: boolean;
    description: string | null;
    onActivate: () => void;
  };
  report: {
    disabled: boolean;
    label: string;
    description: string | null;
    onActivate: () => void;
  };
};

export type AuthenticatedAppShellProps = {
  pageTitle: string;
  username: string;
  logoutPending: boolean;
  onLogout: () => void;
  navigation: ProductShellNavigation;
  contentScrollMode: "contained" | "page";
  children: ReactNode;
};
```

`ProductEntryShell` accepts `children` plus an optional compact diagnostic slot. The future navigation entries are fixed presentational constants inside `product-shell.tsx`, always rendered as disabled buttons with “即将开放” descriptions and without routes.

### Narrow session projection produced by Task 3 and consumed by Task 5

```ts
export type SessionNavigationState =
  | {
      sessionId: null;
      status: "loading" | "lobby";
      reportAvailable: false;
    }
  | {
      sessionId: string;
      status: SessionSnapshot["status"];
      reportAvailable: boolean;
    };

export type OpenCurrentReportRequest = {
  requestId: number;
  sessionId: string;
};
```

`reportAvailable` is constructed as `snapshot.status === "COMPLETED"`; tests must reject every other value. `OpenCurrentReportRequest` carries the session ID observed by the Shell so SessionPanel can reject a stale request against `snapshotRef.current`.

### Training entry interface produced by Task 3

```ts
export type TrainingEntrySurface = "lobby" | "setup";

export type SelectedQuestionDetailState =
  | { kind: "idle" }
  | { kind: "loading"; questionId: string }
  | { kind: "available"; questionId: string; question: QuestionDetail }
  | { kind: "unavailable"; questionId: string };

export type TrainingEntryProps = {
  surface: TrainingEntrySurface;
  questions: readonly QuestionSummary[] | undefined;
  selectedQuestionId: string;
  selectedQuestion: SelectedQuestionDetailState;
  creating: boolean;
  errorMessage: string | null;
  onBeginSelection: () => void;
  onSelectQuestion: (questionId: string) => void;
  onCreateSession: () => void;
};
```

SessionPanel owns the values and all API effects. `TrainingEntry` only derives group arrays/counts and renders UI.

### Interfaces added by the 2026-09-17 amendment (Tasks 6–10 only)

The exact real focused-mode predicate is frozen from the generated `SessionStatus` union:

```ts
const FOCUSED_TRAINING_STATUSES = [
  "CREATED",
  "PREPARATION",
  "OPENING_STATEMENTS",
  "EXPLORATION",
  "CONFLICT_AND_EVALUATION",
  "CONVERGENCE",
  "FINAL_SUMMARY",
] as const satisfies readonly SessionSnapshot["status"][];
```

`COMPLETED` and `ABORTED_USER` are terminal and use normal ProductShell. The outer frame may derive only `normal | focused-training` from the existing narrow `SessionNavigationState`; the full Snapshot remains in SessionPanel. The implementation must preserve one stable SessionPanel content host so a chrome switch does not restart REST/WebSocket/recovery state.

Task 6 extends the existing shell prop contract with `presentationMode: "product" | "focused-training"`. `AuthenticatedAppShell` keeps one stable root and content slot; `product` renders sidebar/top context while `focused-training` omits them and removes canvas constraints. The existing `DiscussionWorkspace` plus `SessionHeader` are the focused-session frame. No separate shell file or duplicate session wrapper is planned because that would add a remount boundary around SessionPanel.

The only approved browser preference is:

```ts
export const TRAINING_WORKSPACE_LAYOUT_STORAGE_KEY =
  "gia.training.workspace.layout";

export type TrainingWorkspaceLayoutPreferenceV1 = {
  version: 1;
  leftWidth: number;
  rightWidth: number;
};

export const DEFAULT_TRAINING_WORKSPACE_LAYOUT = {
  leftWidth: 280,
  rightWidth: 280,
} as const;
```

The shared helper resolves storage only in the browser and exposes safe read/write/reset operations to two real consumers: `DiscussionWorkspace` and Settings. A record is accepted only when it is an object with version 1 and finite widths inside left 220–420 and right 220–380; otherwise the whole record falls back to 280/280. Storage exceptions are swallowed into the same safe fallback. The record may contain no other session or business data.

The settings route is frozen at `apps/web/src/app/settings/page.tsx` (`/settings`) because the repository uses the Next App Router. Its client lives under `apps/web/src/features/settings/`, uses the normal authenticated ProductShell, existing `getCurrentUser`/`logoutUser`, and the shared layout-preference helper. ProductShell's active-item union expands to include `"settings"`; the real Settings navigation action is route navigation, not a new global store.

---

## Task 1 — Extract the shared product Shell and visual primitives

**Purpose:** Establish the layout boundary before page recomposition so later tasks share one truthful navigation, header, canvas and responsive frame rather than repeating Demo-like classes.

**Files:**

- Create: `apps/web/src/app/product-shell.tsx`
- Create: `apps/web/src/app/product-shell.test.tsx`
- Modify: `apps/web/src/app/auth-panel.tsx`
- Modify: `apps/web/src/app/auth-panel.test.tsx`
- Modify: `apps/web/src/app/globals.css`

**Interfaces consumed:** `ReactNode`, username string, logout callback, pre-derived `ProductShellNavigation`.

**Interfaces produced:** `ProductEntryShell`, `AuthenticatedAppShell`, `ProductShellNavigation`, `AuthenticatedAppShellProps` as frozen in section 2.

### Step 1: Write RED component tests

Add `product-shell.test.tsx` first. Assert by role and semantics that:

- desktop navigation contains the exact Training/Growth/Other groups;
- only `完整模拟` and a caller-enabled `训练报告` can invoke callbacks;
- `专项训练`, `题型训练`, `成长中心`, `冲刺计划`, `场次包`, `设置` are disabled and expose “即将开放”; none is a link;
- current item exposes `aria-current="page"` and selection is not communicated only by color;
- `contentScrollMode="contained"` gives the Shell a bounded viewport and a single contained main region; `"page"` permits report-page vertical scrolling;
- compact and desktop navigation have distinct accessible labels and responsive structural markers; browser QA later proves only the intended navigation is visible at each viewport;
- children render without the Shell inspecting their data.

Update the AuthPanel mock expectation to prove authenticated AuthPanel delegates username, logout, page title and navigation callbacks to the new Shell.

### Step 2: Observe RED

Run:

```powershell
pnpm.cmd --filter @group-interview-arena/web exec vitest run src/app/product-shell.test.tsx src/app/auth-panel.test.tsx
```

Expected RED: missing `product-shell` module and/or missing grouped navigation/semantic props. Existing auth behavior tests must remain otherwise intact.

### Step 3: Implement minimally

- Move the current `EntryShell` presentation and authenticated sidebar/topbar markup from `auth-panel.tsx` into `product-shell.tsx`.
- Keep the Shell product-specific; do not build generic Button/Card primitives.
- Render a 232–240px desktop sidebar, 64–72px top context bar, centered 1200–1280px canvas and compact narrow navigation.
- Put future entries in the three approved groups as disabled buttons without `href`.
- Add only reusable CSS variables/classes needed across F010: cool-gray background, white Surface, border, shadow, radii 8/10/12, indigo focus/accent, content-width and 120–220ms transition values.
- Keep `prefers-reduced-motion` and current global focus behavior.
- Make AuthPanel supply its current authenticated content to `AuthenticatedAppShell`; do not change auth requests or SessionPanel ownership.

### Step 4: Verify GREEN

Run the same focused Vitest command. Expected GREEN: all selected tests pass; no test asserts decorative class strings except viewport/scroll structural invariants.

### Step 5: Review checkpoint

```powershell
git diff --check -- apps/web/src/app/product-shell.tsx apps/web/src/app/product-shell.test.tsx apps/web/src/app/auth-panel.tsx apps/web/src/app/auth-panel.test.tsx apps/web/src/app/globals.css
git diff -- apps/web/src/app/product-shell.tsx apps/web/src/app/product-shell.test.tsx apps/web/src/app/auth-panel.tsx apps/web/src/app/auth-panel.test.tsx apps/web/src/app/globals.css
git status --short
```

Review that the Shell has no API imports, no SessionSnapshot payload, no report payload and no route for future modules. Do not commit or push.

---

## Task 2 — Recompose the public login/register entry

**Purpose:** Make the real authentication path read as a mature 7:5 SaaS entry while preserving authentication, validation, error and loading behavior.

**Files:**

- Modify: `apps/web/src/app/auth-panel.tsx`
- Modify: `apps/web/src/app/auth-panel.test.tsx`
- Modify: `apps/web/src/app/product-shell.tsx`
- Modify: `apps/web/src/app/product-shell.test.tsx`
- Modify: `apps/web/src/app/globals.css`
- Modify: `apps/web/e2e/auth.spec.ts` for this task's real entry/Shell visual evidence; Task 10 later recaptures the final matrix

**Interfaces consumed:** existing `getCurrentUser`, `loginUser`, `registerUser`, `logoutUser`, `getSafeAuthErrorMessage`, `HealthStatus`, `ProductEntryShell`.

**Interfaces produced:** no new business interface; AuthPanel retains its current public component API.

### Step 1: Write RED tests

Extend `auth-panel.test.tsx` before markup changes to assert:

- login and register mode controls remain named buttons with `aria-pressed` or equivalent selected semantics;
- username/password labels, autocomplete, validation attributes, error live region, loading label and password clearing still work;
- entry copy contains only the three real benefits: 3 AI candidates, text discussion, evidence-based review;
- no user-facing P1/internal-validation/technical-version copy exists;
- `HealthStatus` appears only in the low-priority diagnostic slot and does not precede the authentication task heading in accessible document order;
- the entry frame exposes structural markers for desktop 7:5 and mobile single-column composition without relying on exact colors.

### Step 2: Observe RED

```powershell
pnpm.cmd --filter @group-interview-arena/web exec vitest run src/app/auth-panel.test.tsx src/app/product-shell.test.tsx
```

Expected RED: diagnostic ordering, task-card semantics and/or new structural markers are absent while real auth tests continue to execute.

### Step 3: Implement minimally

- Keep all existing auth calls, current-user bootstrap, canonical username display, password clearing, safe errors and logout behavior unchanged.
- Compose `ProductEntryShell` at approximately 7:5 on desktop; left side carries brand/value/three real benefits, right side carries the single auth card.
- Move health text to a visually and semantically secondary footer/diagnostic slot.
- Use full-width controls at 390px, allow vertical scrolling for short height and avoid fixed heights that clip validation messages.
- Retain real HTML validation and clear focus-visible styles.

### Step 4: Verify GREEN

Run the focused Task 2 command again. Expected GREEN: all auth and entry-shell unit tests pass.

### Step 5: Review checkpoint

```powershell
git diff --check -- apps/web/src/app/auth-panel.tsx apps/web/src/app/auth-panel.test.tsx apps/web/src/app/product-shell.tsx apps/web/src/app/product-shell.test.tsx apps/web/src/app/globals.css
git diff -- apps/web/src/app/auth-panel.tsx apps/web/src/app/product-shell.tsx apps/web/src/app/globals.css
git status --short
```

Review user-facing copy for engineering terminology and unsupported promises. Do not commit or push.

### Step 6: USER VISUAL APPROVAL GATE — login/register and shared Shell

Use the existing real local API/PostgreSQL browser harness and add only the screenshot attachments needed for this gate to `auth.spec.ts`:

```powershell
uv run --project apps/api python apps/api/tests/integration/browser_e2e.py
```

Capture both the unauthenticated login/register entry and the authenticated shared Shell at all three viewports:

| State               | 1440×900                    | 768×1024                    | 390×844                    |
| ------------------- | --------------------------- | --------------------------- | -------------------------- |
| Login/register      | `f010-task2-entry-1440x900` | `f010-task2-entry-768x1024` | `f010-task2-entry-390x844` |
| Authenticated Shell | `f010-task2-shell-1440x900` | `f010-task2-shell-768x1024` | `f010-task2-shell-390x844` |

Reopen the original Demo V2 screenshots/source from `D:\Users\HP\Downloads\ai-group-interview-full-demo-standalone-v2 (2).zip` and compare the corresponding same-viewport composition; memory or a textual description alone is not acceptable. Inspect and report:

- split composition;
- authenticated sidebar/header proportions;
- typography scale;
- whitespace;
- visual hierarchy;
- excessive engineering UI;
- horizontal overflow.

Correct findings only in Task 1–2 files, rerun their focused GREEN commands and recapture affected screenshots. Report the final screenshot paths/Playwright attachments plus a concise mismatch/correction ledger to the user.

**STOP — DO NOT CONTINUE WITHOUT EXPLICIT USER VISUAL APPROVAL.** Task 3 must not start until the user approves this entry/Shell gate.

---

## Task 3 — Build the Bento lobby and real categorized question setup

**Purpose:** Replace the raw select form with the primary F010 information architecture while continuing to create sessions from exact immutable public question-version IDs.

**Files:**

- Create: `apps/web/src/features/sessions/question-presentation.ts`
- Create: `apps/web/src/features/sessions/training-entry.tsx`
- Create: `apps/web/src/features/sessions/training-entry.test.tsx`
- Modify: `apps/web/src/features/sessions/session-panel.tsx`
- Modify: `apps/web/src/features/sessions/session-panel.test.tsx`
- Modify: `apps/web/src/features/sessions/task-brief-panel.tsx`
- Modify: `apps/web/src/features/sessions/discussion-workspace.test.tsx`
- Modify: `apps/web/src/app/auth-panel.tsx`
- Modify: `apps/web/src/app/auth-panel.test.tsx`
- Modify: `apps/web/e2e/auth.spec.ts` for real lobby/setup evidence
- Modify: `apps/web/e2e/session.spec.ts` only as needed to keep the existing real session flow using the new accessible question selectors; Task 10 later recaptures the final matrix

**Interfaces consumed:** `QuestionSummary`, `QuestionDetail`, `listQuestions`, `getQuestion`, `createSession`, existing `returnToLobbyRequest`.

**Interfaces produced:** `TrainingEntry`, `TrainingEntryProps`, `TrainingEntrySurface`, `SelectedQuestionDetailState`, closed question labels, the narrow `SessionNavigationState` union from section 2, and one `openSetupRequest` number prop from AuthPanel to SessionPanel.

### Step 1: Write RED tests

Create `training-entry.test.tsx` with 12 safe public fixtures split 4/4/4. Assert:

- initial lobby shows “下一场完整模拟”, the three supported facts and “开始选题”; it contains no duration before selection and none of balance/streak/history/score/progress/Mock language;
- setup renders exactly three real type controls with labels and counts `4`, and all 12 questions are accessible by switching groups;
- each question is one labelled native radio target; keyboard Space selects it, browser-native same-name radio behavior remains available, focus is visible by component contract, and selected state includes textual/icon indication in addition to color;
- card text comes only from Summary fields and never renders IDs as primary content;
- selected summary renders only an exact available QuestionDetail’s objective and hard constraints; idle/loading/unavailable are truthful local states;
- create callback receives no inferred data and is disabled only when no question is selected or creation is pending; a detail-read failure does not revoke the selected public version ID or block the existing create contract.

Extend SessionPanel tests to assert:

- real discovery continues through `listQuestions` and produces `{sessionId:null,status:"lobby",reportAvailable:false}`;
- `openSetupRequest` changes only the no-session presentation Surface and does not call an API;
- selecting a card calls existing `getQuestion` for that exact ID and ignores a stale detail response after a later selection;
- create uses the exact selected immutable version and still applies the authoritative returned Snapshot;
- terminal return clears workspace/transcript/private notes, reloads questions and returns to the lobby rather than creating a session;
- restored active, completed and aborted snapshots project their exact IDs/statuses; only completed projects `reportAvailable:true`.

Update TaskBriefPanel coverage so `ORDERING_SELECTION`, `RESOURCE_ALLOCATION` and `PLAN_DESIGN` render their frozen labels and the obsolete example-only codes are absent.

### Step 2: Observe RED

```powershell
pnpm.cmd --filter @group-interview-arena/web exec vitest run src/features/sessions/training-entry.test.tsx src/features/sessions/session-panel.test.tsx src/features/sessions/discussion-workspace.test.tsx src/app/auth-panel.test.tsx
```

Expected RED: missing TrainingEntry and closed label map, old dropdown UI, old string navigation states and absent selected-detail behavior.

### Step 3: Implement minimally

- Add the closed three-code label helper; unknown codes may display their public raw code safely but may not be remapped to a supported product category.
- Add `TrainingEntry` as a pure UI component using the exact interface in section 2.
- Keep questions and API effects in SessionPanel. Add a request-identity guard for selected-detail loading so late responses cannot overwrite the current selection.
- Keep the existing exact-version `createSession(apiClient, selectedQuestionId)` call and current post-create recovery/connection flow.
- Add local `TrainingEntrySurface`; initial discovery and terminal return enter `lobby`; `openSetupRequest` and the lobby CTA enter `setup`.
- Do not show estimated duration in the lobby. In setup use only real `estimated_minutes` from the selected public question.
- Replace DOM lookup/scroll ownership in AuthPanel with the monotonic `openSetupRequest` intent.
- Keep loading/lobby/setup vertical scrolling owned by the SessionPanel content region.

### Step 4: Verify GREEN

Run the focused Task 3 command again. Expected GREEN: question/lobby tests pass, existing creation and recovery tests remain green, and the exact 4/4/4 fixture is visible through the three groups.

### Step 5: Review checkpoint

```powershell
git diff --check -- apps/web/src/features/sessions apps/web/src/app/auth-panel.tsx apps/web/src/app/auth-panel.test.tsx
git diff -- apps/web/src/features/sessions/training-entry.tsx apps/web/src/features/sessions/question-presentation.ts apps/web/src/features/sessions/session-panel.tsx apps/web/src/features/sessions/task-brief-panel.tsx
git status --short
```

Inspect for hidden/reference/private fields, Demo codes, automatic duration claims, localStorage/sessionStorage and any API/schema edit. Do not commit or push.

### Step 6: USER VISUAL APPROVAL GATE — training lobby and categorized setup

Run the real browser harness after updating the existing browser locators for the new accessible setup:

```powershell
uv run --project apps/api python apps/api/tests/integration/browser_e2e.py
```

Capture both page states at all three viewports:

| State             | 1440×900                    | 768×1024                    | 390×844                    |
| ----------------- | --------------------------- | --------------------------- | -------------------------- |
| Training lobby    | `f010-task3-lobby-1440x900` | `f010-task3-lobby-768x1024` | `f010-task3-lobby-390x844` |
| Categorized setup | `f010-task3-setup-1440x900` | `f010-task3-setup-768x1024` | `f010-task3-setup-390x844` |

Reopen the original Demo V2 screenshots/source from `D:\Users\HP\Downloads\ai-group-interview-full-demo-standalone-v2 (2).zip` and compare the corresponding same-viewport composition; memory or a textual description alone is not acceptable. Inspect and report:

- Bento hierarchy;
- primary-task prominence;
- 8/4 setup composition;
- question-card density;
- selected-summary hierarchy;
- visual similarity to Demo V2;
- absence of Mock data.

Correct findings only in Task 1–3 files, rerun the owning focused GREEN commands and recapture affected screenshots. Report the final screenshot paths/Playwright attachments, actual 4/4/4 evidence and mismatch/correction ledger to the user.

**STOP — DO NOT CONTINUE WITHOUT EXPLICIT USER VISUAL APPROVAL.** Task 4 must not start until the user approves this lobby/setup gate.

---

## Task 4 — Recompose the discussion workspace without changing realtime behavior

**Purpose:** Make the existing authoritative simulation visibly match the Demo V2 three-region hierarchy while preserving F007/F008 correctness.

**Files:**

- Modify: `apps/web/src/features/sessions/discussion-workspace.tsx`
- Modify: `apps/web/src/features/sessions/discussion-workspace.test.tsx`
- Modify: `apps/web/src/features/sessions/discussion-stage.tsx`
- Modify: `apps/web/src/features/sessions/discussion-stage.test.tsx`
- Modify: `apps/web/src/features/sessions/task-brief-panel.tsx`
- Modify: `apps/web/src/features/sessions/session-progress-panel.tsx`
- Modify: `apps/web/src/features/sessions/session-panel.tsx`
- Modify: `apps/web/src/features/sessions/session-panel.test.tsx`
- Modify: `apps/web/src/app/globals.css`
- Modify: `apps/web/e2e/session.spec.ts` for this task's real active-discussion evidence; Task 10 later recaptures the final matrix

**Interfaces consumed:** current `DiscussionWorkspaceProps`, `DiscussionStageProps`, `TaskBriefQuestionState`, `SessionProgressPanelProps`, realtime projection and all SessionPanel state/callbacks.

**Interfaces produced:** simplified `SessionHeaderProps` without duplicate product branding; no new business state or realtime interface.

### Step 1: Write RED tests

Update component tests before layout code:

- assert desktop structural columns are support `260–300px`, center `minmax(560px, 1fr)`, support `260–300px`, with the center marked primary;
- assert discussion header no longer repeats product brand or “Interview Simulation Studio” already owned by the global Shell, while retaining session title, phase, countdown, connection and real actions;
- assert participant strip remains four compact tiles, current speaker has `aria-current`, and AI preparing appears on exactly the current AI participant;
- assert transcript remains the only long center scroller, uses confirmed public records and does not expose raw event/debug IDs;
- assert composer, pending, rejected, recovery and interrupted-AI notices remain local and reachable without a giant banner;
- retain exact mobile tab order/keyboard semantics and no-remount assertions;
- retain tablet single support-sheet behavior and ensure 768px never shows all three columns;
- assert TaskBrief contains public question/detail only and in-memory notes copy; right panel contains only approved phase/floor/connection state and no Memory placeholder.

### Step 2: Observe RED

```powershell
pnpm.cmd --filter @group-interview-arena/web exec vitest run src/features/sessions/discussion-workspace.test.tsx src/features/sessions/discussion-stage.test.tsx src/features/sessions/session-panel.test.tsx
```

Expected RED: old desktop proportions and duplicate studio identity fail the new structural assertions. All existing realtime behavior tests should still run.

### Step 3: Implement minimally

- Replace only the workspace composition and presentation classes/markup; do not touch realtime client, projection, transcript merge or API calls.
- At the desktop breakpoint use the frozen support/center/support sizing and keep center visually dominant.
- Keep the root and center `overflow-hidden`; keep the confirmed transcript list as the sole long center scroller; keep left/right support panels as their own bounded scrollers.
- Remove duplicate product identity from the session header because ProductShell owns it; retain compact phase/countdown/connection/actions.
- Refine participant tiles and confirmed utterance rows toward a meeting-record hierarchy; retain all safe content and F007 `performance.mark` behavior unchanged.
- Do not add Discussion Memory, hidden conflict, private stance, prompt/provider output or event-log rows.

### Step 4: Verify GREEN

Run the focused Task 4 command again. Expected GREEN: all selected tests pass, including existing AI render provenance, pending/rejected, scroll and tab tests.

### Step 5: Review checkpoint

```powershell
git diff --check -- apps/web/src/features/sessions/discussion-workspace.tsx apps/web/src/features/sessions/discussion-workspace.test.tsx apps/web/src/features/sessions/discussion-stage.tsx apps/web/src/features/sessions/discussion-stage.test.tsx apps/web/src/features/sessions/task-brief-panel.tsx apps/web/src/features/sessions/session-progress-panel.tsx apps/web/src/features/sessions/session-panel.tsx apps/web/src/features/sessions/session-panel.test.tsx apps/web/src/app/globals.css
git diff -- apps/web/src/features/sessions/discussion-workspace.tsx apps/web/src/features/sessions/discussion-stage.tsx apps/web/src/features/sessions/session-panel.tsx
git status --short
```

Review specifically for accidental WebSocket/state changes and nested body/workspace/transcript scrolling. Do not commit or push.

### Step 6: USER VISUAL APPROVAL GATE — active discussion workspace

Run the existing real session/recovery browser harness:

```powershell
uv run --project apps/api python apps/api/tests/integration/browser_e2e.py
```

Capture the same active real discussion state at all three viewports:

- `f010-task4-discussion-1440x900`
- `f010-task4-discussion-768x1024`
- `f010-task4-discussion-390x844`

Reopen the original Demo V2 discussion screenshot/source from `D:\Users\HP\Downloads\ai-group-interview-full-demo-standalone-v2 (2).zip` and compare the corresponding same-viewport composition; memory or a textual description alone is not acceptable. Inspect and report:

- left/center/right proportions;
- center dominance;
- participant strip;
- transcript density;
- composer position;
- phase/progress support hierarchy;
- compact participant-local AI-preparing state;
- mobile panel-switching composition.

Also retain the existing machine assertions for URL/realtime recovery, pending/rejected drafts, transcript scroll ownership and no extra REST/WebSocket work during panel switching. Correct visual findings only in Task 1–4 frontend files, rerun the owning focused GREEN commands and recapture affected screenshots. Report final paths/Playwright attachments and the mismatch/correction ledger to the user.

**STOP — DO NOT CONTINUE WITHOUT EXPLICIT USER VISUAL APPROVAL.** Task 5 must not start until the user approves this active-discussion gate.

---

## Task 5 — Connect truthful global report navigation and place reports in the shared Shell

**Purpose:** Fix the reported inaccessible global entry while retaining SessionPanel as generation authority and ReportView as report-data owner.

**Files:**

- Modify: `apps/web/src/app/auth-panel.tsx`
- Modify: `apps/web/src/app/auth-panel.test.tsx`
- Modify: `apps/web/src/app/product-shell.tsx`
- Modify: `apps/web/src/app/product-shell.test.tsx`
- Modify: `apps/web/src/features/sessions/session-panel.tsx`
- Modify: `apps/web/src/features/sessions/session-panel.test.tsx`
- Modify: `apps/web/src/app/sessions/[sessionId]/report/page.tsx`
- Modify: `apps/web/src/features/reports/report-page-client.tsx`
- Create: `apps/web/src/features/reports/report-page-client.test.tsx`
- Modify: `apps/web/src/features/reports/report-view.tsx`
- Modify: `apps/web/src/features/reports/report-view.test.tsx`
- Modify: `apps/web/e2e/report.spec.ts` for this task's real completed-report evidence; Task 10 later recaptures the final matrix

**Interfaces consumed:** narrow `SessionNavigationState`, existing `generateReport`, `getReport`, `getCurrentUser`, `logoutUser`, `parseReportView`, Next `useRouter`.

**Interfaces produced:** `OpenCurrentReportRequest`; `ReportPageClient` changes to accept `baseUrl: string | null` plus `sessionId`; ReportView remains the sole report loading/parser state owner and gains only explicit retry/back presentation callbacks if needed.

### Step 1: Write RED tests

Update AuthPanel/ProductShell tests to prove:

- loading, lobby, every active phase and `ABORTED_USER` render a disabled report entry with accurate copy;
- `COMPLETED` renders enabled “生成 / 查看本次训练报告”;
- clicking captures `{requestId, sessionId}` and passes it to SessionPanel rather than calling `generateReport` in Shell/AuthPanel;
- “完整模拟” stays on active training, opens setup in lobby, and returns terminal sessions through `returnToLobbyRequest`.

Update SessionPanel tests to prove:

- a matching completed request calls existing POST once then pushes `/sessions/{id}/report`;
- repeated same `requestId` is ignored and an in-flight second request cannot duplicate generation;
- mismatched session ID, lobby, active and `ABORTED_USER` requests are rejected by `snapshotRef.current` authority;
- safe POST failure stays on the training Surface and exposes no backend detail.

Create `report-page-client.test.tsx` and extend ReportView tests to prove:

- configured report route bootstraps current user with existing `/auth/me`, supplies username/logout to ProductShell, marks report current and routes “完整模拟” back to `/`;
- logout uses existing `logoutUser` and returns to `/`; auth/business state stays route-local and is not copied into AppShell;
- authenticated `REQUESTED`, `RUNNING`, `COMPLETED`, `FAILED`, not-found, parse/error and retry states render inside the common report content canvas;
- unauthenticated and configuration-error states use the same product visual language with a real route back to login, without pretending an authenticated username exists;
- completed layout order is overview 8, priority 4, strengths 6, improvements 6;
- only P1-7 fields render; empty evidence arrays remain honest and `content === null` never causes a blank page.

### Step 2: Observe RED

```powershell
pnpm.cmd --filter @group-interview-arena/web exec vitest run src/app/product-shell.test.tsx src/app/auth-panel.test.tsx src/features/sessions/session-panel.test.tsx src/features/reports/report-page-client.test.tsx src/features/reports/report-view.test.tsx
```

Expected RED: old string projection, permanently disabled global report entry, missing report request prop, absent route auth/Shell wrapper and old report card order.

### Step 3: Implement minimally

- Replace the old navigation strings with the narrow union and derive it only from `checkingUrl` plus the current authoritative Snapshot.
- Add `openCurrentReportRequest?: OpenCurrentReportRequest` to SessionPanel and a handled-request ref/effect parallel to the existing lobby request pattern.
- Rework `openReport` to accept the expected session ID, re-read `snapshotRef.current`, require exact ID + `COMPLETED`, and retain duplicate-generation protection before POST/navigation.
- Let AuthPanel derive ProductShell navigation presentation and emit request objects; do not import/call `generateReport` outside SessionPanel.
- In ReportPageClient, perform route-local current-user bootstrap and logout with existing endpoints. This is not a second global business store: AuthPanel is unmounted on the report route, the cookie/server remain authoritative, and ProductShell receives display props only.
- Make the server report page pass configured base URL or an explicit null configuration state; do not invent a fallback API.
- Make ReportView render report content/status bodies rather than an independent full-screen app frame; retain `parseReportView` unchanged.
- Reorder completed cards to 8/4 then 6/6 and keep provenance low priority.

### Step 4: Verify GREEN

Run the focused Task 5 command again. Expected GREEN: all selected navigation, report ownership, auth-shell and report state tests pass.

### Step 5: Review checkpoint

```powershell
git diff --check -- apps/web/src/app apps/web/src/features/sessions/session-panel.tsx apps/web/src/features/sessions/session-panel.test.tsx apps/web/src/features/reports
git diff -- apps/web/src/app/auth-panel.tsx apps/web/src/app/product-shell.tsx apps/web/src/features/sessions/session-panel.tsx apps/web/src/features/reports/report-page-client.tsx apps/web/src/features/reports/report-view.tsx
git status --short
```

Review that Shell has no report/API ownership, GET still never generates, parser allowlist is unchanged, no report history exists and non-owner/401/404 remain nondisclosing. Do not commit or push.

### Step 6: USER VISUAL APPROVAL GATE — completed report

Run the existing real P1-7D report browser harness:

```powershell
uv run --project apps/api python apps/api/tests/integration/p1_7d_report_e2e.py
```

Capture the persisted completed report at all three viewports:

- `f010-task5-report-1440x900`
- `f010-task5-report-768x1024`
- `f010-task5-report-390x844`

Reopen the original Demo V2 report screenshot/source from `D:\Users\HP\Downloads\ai-group-interview-full-demo-standalone-v2 (2).zip` and compare the corresponding same-viewport composition; memory or a textual description alone is not acceptable. Inspect and report:

- use of the same shared Shell;
- 8/4 overview/priority hierarchy;
- 6/6 strengths/improvements hierarchy;
- sparse-data and empty-evidence handling;
- absence of fake P3 scores, dimensions, radar, ranking, growth and recommendations.

Keep exact quote/provenance, refresh-safe GET and non-owner nondisclosure assertions active. Correct findings only in Task 1–5 frontend files, rerun the owning focused GREEN commands and recapture affected screenshots. Report final paths/Playwright attachments and the mismatch/correction ledger to the user.

**STOP — DO NOT CONTINUE WITHOUT EXPLICIT USER VISUAL APPROVAL.** Task 6 must not start until the user approves this completed-report gate.

---

## Task 6 — Focused Training Shell

**Purpose:** Hide normal product chrome for every real non-terminal session and give the existing discussion feature the full viewport, without moving session authority or remounting realtime state.

**Files:**

- Modify: `apps/web/src/app/auth-panel.tsx`
- Modify: `apps/web/src/app/auth-panel.test.tsx`
- Modify: `apps/web/src/app/product-shell.tsx`
- Modify: `apps/web/src/app/product-shell.test.tsx`
- Modify: `apps/web/src/features/sessions/session-panel.tsx`
- Modify: `apps/web/src/features/sessions/session-panel.test.tsx`
- Modify: `apps/web/src/features/sessions/discussion-workspace.tsx`
- Modify: `apps/web/src/features/sessions/discussion-workspace.test.tsx`
- Modify: `apps/web/src/app/globals.css`

**Interfaces consumed:** existing narrow `SessionNavigationState`, exact generated `SessionSnapshot["status"]`, current `SessionHeader`/`DiscussionWorkspace`, existing end-training action and mobile workspace tabs.

**Interfaces produced:** a presentation-only `normal | focused-training` frame mode derived from the frozen non-terminal status set; no new backend/session state.

### Step 1: Write RED tests

Add behavioral tests first that prove:

- `CREATED`, `PREPARATION`, `OPENING_STATEMENTS`, `EXPLORATION`, `CONFLICT_AND_EVALUATION`, `CONVERGENCE` and `FINAL_SUMMARY` select focused presentation;
- loading/lobby, `COMPLETED`, `ABORTED_USER`, report and settings use normal ProductShell;
- normal sidebar, top context bar and global navigation are absent from the visible focused composition;
- the compact Session Bar shows only real title, phase, countdown, connection and currently supported end action—no report/settings/growth/fake Host controls;
- switching chrome does not remount SessionPanel or create extra hydration/WebSocket work;
- completion and user abort restore normal frame behavior;
- mobile focused mode retains the existing `讨论 / 题目 / 进程` panel controls and defaults to discussion;
- AI preparing remains participant-local and no large global waiting banner returns.

Avoid exact cosmetic class assertions. Assert modes, regions, accessible names, stable content identity and request counts.

### Step 2: Observe RED

```powershell
pnpm.cmd --filter @group-interview-arena/web exec vitest run src/app/product-shell.test.tsx src/app/auth-panel.test.tsx src/features/sessions/session-panel.test.tsx src/features/sessions/discussion-workspace.test.tsx src/features/sessions/discussion-stage.test.tsx
```

Expected RED: ProductShell chrome still wraps active sessions and no exact focused-mode boundary exists.

### Step 3: Implement minimally

- Derive frame mode in AuthPanel from the existing narrow projection only; do not pass the Snapshot upward.
- Add `presentationMode: "product" | "focused-training"` to the existing `AuthenticatedAppShell`; keep one stable root/content host so showing or hiding its sidebar/top context never remounts SessionPanel.
- Let the existing DiscussionWorkspace/SessionHeader supply the focused Session Bar and three regions. Do not add a duplicate session wrapper or a second shell file.
- In focused mode remove sidebar/header layout columns, content max-width and general-product scroll assumptions; use the available viewport.
- Keep SessionPanel's URL recovery, REST, WebSocket, scheduler, transcript, floor, pending/rejected and report ownership untouched.
- Preserve current end/abort semantics. Do not make completion automatically generate a report or user abort report-eligible.

### Step 4: Verify GREEN

Run the focused Task 6 command again. Then run:

```powershell
pnpm.cmd web:typecheck
pnpm.cmd web:lint
pnpm.cmd web:format:check
git diff --check
```

Expected GREEN: mode and stability tests pass; all four Web gates exit 0.

### Step 5: Review checkpoint

```powershell
git diff -- apps/web/src/app/auth-panel.tsx apps/web/src/app/product-shell.tsx apps/web/src/features/sessions/session-panel.tsx apps/web/src/features/sessions/discussion-workspace.tsx apps/web/src/app/globals.css
git status --short
```

Confirm the exact status set, narrow projection, stable SessionPanel host, absence of report/settings shortcuts and no API/backend/schema changes. Do not commit or push.

### Step 6: USER VISUAL APPROVAL GATE — focused training

Reopen the original Demo V2 discussion screenshot/source from `D:\Users\HP\Downloads\ai-group-interview-full-demo-standalone-v2 (2).zip`; memory or text alone is not a reference. Use a real local session and capture at minimum:

- `f010-task6-focused-1440x900-active`
- `f010-task6-focused-1440x900-ai-preparing`
- `f010-task6-focused-390x844-discussion`
- additional 768×1024 and mobile task/progress tabs if needed to prove the existing switching model was preserved

Compare full-viewport use, compact Session Bar, absence of normal ProductShell chrome, center dominance, participant-local AI preparing, composer reachability, mobile tabs, whitespace and overflow. Fix every material mismatch inside Task 6 files, rerun focused GREEN and recapture before presenting evidence.

**STOP — DO NOT CONTINUE WITHOUT EXPLICIT USER VISUAL APPROVAL.** Task 7 must not start until the user approves this focused-training gate.

---

## Task 7 — Resizable Workspace and Browser Preference

**Purpose:** Add accessible user-adjustable desktop support-panel widths with safe, narrowly scoped browser persistence while preserving center dominance and the existing narrow-screen panel model.

**Files:**

- Create: `apps/web/src/lib/ui/training-workspace-layout.ts`
- Create: `apps/web/src/lib/ui/training-workspace-layout.test.ts`
- Modify: `apps/web/src/features/sessions/discussion-workspace.tsx`
- Modify: `apps/web/src/features/sessions/discussion-workspace.test.tsx`
- Modify: `apps/web/src/app/globals.css`
- Modify: `apps/web/e2e/session.spec.ts` only for real pointer/keyboard/persistence evidence at this gate

**Interfaces consumed:** focused DiscussionWorkspace from Task 6, current `min-[1200px]` desktop architecture and existing tablet/mobile support switching.

**Interfaces produced:** `TrainingWorkspaceLayoutPreferenceV1`, default/bounds constants, and safe `readTrainingWorkspaceLayout`, `writeTrainingWorkspaceLayout`, `resetTrainingWorkspaceLayout` helpers around key `gia.training.workspace.layout`.

### Step 1: Write RED tests

Write helper and component tests first. They must prove:

- no preference yields 280/280;
- valid v1 values reload and apply on a later workspace mount/new session;
- malformed JSON, non-object values, missing fields, non-finite/out-of-range widths, unsupported versions and `getItem`/`setItem`/`removeItem` failures safely use defaults and never block training;
- pointer movement adjusts only the intended side with immediate feedback and pointer capture;
- left clamps to 220–420, right to 220–380, and dynamic maxima preserve a practical 520px center plus handles/gaps/padding;
- `ArrowLeft`/`ArrowRight` adjust by 16px and Shift variants by 40px;
- both handles expose vertical separator semantics, names, min/max/current values and visible focus state;
- pointer completion and each keyboard adjustment persist `{version:1,leftWidth,rightWidth}` automatically with no Save control;
- when all minimums cannot fit, desktop columns/handles are not used and existing support-panel switching remains active;
- tablet/mobile ignore stored widths and expose no inline desktop width distortion;
- the stored value contains no user, session, question, transcript, participant, report, note or other business field.

Update existing storage/privacy assertions so they continue to reject business/session persistence while permitting only this exact UI-preference key.

### Step 2: Observe RED

```powershell
pnpm.cmd --filter @group-interview-arena/web exec vitest run src/lib/ui/training-workspace-layout.test.ts src/features/sessions/discussion-workspace.test.tsx src/features/sessions/session-panel.test.tsx
```

Expected RED: helper, separators and resize/persistence behavior do not exist.

### Step 3: Implement minimally

- Implement the helper without module-level `window` access; accept/resolve storage only in browser effects/events and catch all storage operations.
- Treat any invalid record as entirely invalid; do not partially trust it. Live pointer/keyboard input clamps at the hard bounds and current center-protection bound.
- Use native React state, CSS Grid/flex and Pointer Events. Add no dependency and no global state framework.
- Render two lightweight dividers only in the feasible desktop layout. Use pointer capture for continuous feedback and persist on pointer completion; persist each keyboard step immediately.
- Calculate effective side maxima from current workspace width so center stays at least 520px. If minimum feasibility fails, use the already-approved support-panel layout rather than squeezing.
- Read once per workspace mount. A later real session uses the persisted preference; tablet/mobile retain the record but do not apply it.

### Step 4: Verify GREEN

Run the focused Task 7 command again, then:

```powershell
pnpm.cmd web:typecheck
pnpm.cmd web:lint
pnpm.cmd web:format:check
git diff --check
```

Expected GREEN: helper and behavioral workspace tests pass; Web gates exit 0.

### Step 5: Review checkpoint

```powershell
git diff -- apps/web/src/lib/ui/training-workspace-layout.ts apps/web/src/features/sessions/discussion-workspace.tsx apps/web/src/app/globals.css apps/web/e2e/session.spec.ts
git status --short
```

Inspect the exact storage payload, exception handling, center calculation, pointer cleanup, separator ARIA and absence of session/business data. Do not commit or push.

### Step 6: USER VISUAL / INTERACTION APPROVAL GATE — resizable workspace

Using a real focused training session, capture and attach:

- `f010-task7-layout-default-1440x900`
- `f010-task7-layout-left-expanded-1440x900`
- `f010-task7-layout-right-expanded-1440x900`
- min and max clamp evidence for both dividers
- keyboard resize evidence showing 16px and Shift+40px behavior plus visible focus
- reload persistence and a second/new-session persistence capture

Also verify one insufficient-width/tablet view uses support-panel switching rather than stored inline widths. Compare the compositions against the original Demo V2 discussion source and the approved Task 6 focused evidence; fix material drift inside Task 7 files before presentation.

**STOP — DO NOT CONTINUE WITHOUT EXPLICIT USER VISUAL APPROVAL.** Task 8 must not start until the user approves this resizing/persistence gate.

---

## Task 8 — Real Settings Center

**Purpose:** Turn Settings into a real authenticated normal-ProductShell route that exposes only current account actions, truthful information and the approved workspace-layout reset.

**Files:**

- Create: `apps/web/src/app/settings/page.tsx`
- Create: `apps/web/src/features/settings/settings-page-client.tsx`
- Create: `apps/web/src/features/settings/settings-page-client.test.tsx`
- Modify: `apps/web/src/app/product-shell.tsx`
- Modify: `apps/web/src/app/product-shell.test.tsx`
- Modify: `apps/web/src/app/auth-panel.tsx`
- Modify: `apps/web/src/app/auth-panel.test.tsx`
- Modify: `apps/web/src/features/reports/report-page-client.tsx`
- Modify: `apps/web/src/features/reports/report-page-client.test.tsx`
- Modify: `apps/web/src/app/globals.css`
- Modify: `apps/web/e2e/auth.spec.ts` for the settings route flow; the current `test:e2e:browser` script explicitly selects only `auth.spec.ts` and `session.spec.ts`

**Interfaces consumed:** normal ProductShell, existing `getCurrentUser`/`logoutUser`, shared Task 7 preference helper, existing global `prefers-reduced-motion` behavior.

**Interfaces produced:** `/settings`, settings active navigation, route-local authenticated settings client and four local presentation sections; no backend API.

### Step 1: Write RED tests

Tests must prove:

- Settings is an enabled real navigation target from normal authenticated app and report Shells, and active on `/settings`;
- the route handles auth loading, authenticated username, unauthenticated/configuration-safe state and existing logout flow;
- it always uses normal ProductShell and never focused training chrome;
- desktop exposes `训练界面 / 账户与会话 / 隐私与数据 / 更多设置`; tablet/mobile use an accessible compact section switcher;
- training-interface state says default when no valid record exists and custom browser layout for a valid record;
- “恢复默认布局” removes only `gia.training.workspace.layout`, updates the current Settings UI immediately, and promises defaults only for the next workspace mount;
- storage reset failure remains safe and truthful rather than reporting success;
- reduced motion is informational and has no switch;
- username and logout are real; email, phone, avatar, subscription, password change and account deletion are absent;
- privacy copy matches source: public session/discussion data support recovery/report; panel widths stay in this browser; private notes are memory-only, not API/localStorage, and disappear on refresh;
- future sound/device, training-preference and notification rows are text-only and have no functional-looking switch/save/success controls;
- no download/delete/history purge/fake privacy action or backend settings request exists.

### Step 2: Observe RED

```powershell
pnpm.cmd --filter @group-interview-arena/web exec vitest run src/app/product-shell.test.tsx src/app/auth-panel.test.tsx src/features/reports/report-page-client.test.tsx src/features/settings/settings-page-client.test.tsx src/lib/ui/training-workspace-layout.test.ts
```

Expected RED: `/settings`, enabled navigation and real settings client do not exist.

### Step 3: Implement minimally

- Add the App Router page and pass configured API base URL or an explicit safe configuration state, following the existing report route convention.
- Build one route-local client; reuse existing auth bootstrap/logout calls and normal ProductShell. Do not create a generic settings library or global user store.
- Expand ProductShell navigation presentation with a real Settings action and `activeItem: "settings"`; keep all other unsupported modules disabled.
- Render a restrained max-width 900–1000px settings composition with local category selection and responsive section switcher.
- Read/reset the shared layout helper. Reset removes only its key, updates local display immediately, and describes next-training behavior without cross-tab/current-workspace claims.
- Render reduced-motion, privacy and future settings as honest information only.

### Step 4: Verify GREEN

Run the focused Task 8 command again, then:

```powershell
pnpm.cmd web:typecheck
pnpm.cmd web:lint
pnpm.cmd web:format:check
git diff --check
```

Expected GREEN: settings navigation/auth/content/reset tests and Web gates pass.

### Step 5: Review checkpoint

```powershell
git diff -- apps/web/src/app/settings apps/web/src/features/settings apps/web/src/app/product-shell.tsx apps/web/src/app/auth-panel.tsx apps/web/src/features/reports/report-page-client.tsx apps/web/src/lib/ui/training-workspace-layout.ts
git status --short
```

Confirm no settings API/schema/database call, no fake controls, no business-data persistence, truthful reset semantics and no active-training shortcut. Do not commit or push.

### Step 6: USER VISUAL APPROVAL GATE — settings center

Capture the authenticated real route at:

- `f010-task8-settings-1440x900`
- `f010-task8-settings-768x1024`
- `f010-task8-settings-390x844`

Include default/custom layout state and reset result in the review evidence. Compare ProductShell continuity, category hierarchy, content density, responsive section switching, typography, whitespace, focus states and absence of fake controls against the original Demo V2 source and the already-approved F010 visual system. Fix material Task 8 mismatches and rerun focused GREEN before presentation.

**STOP — DO NOT CONTINUE WITHOUT EXPLICIT USER VISUAL APPROVAL.** Task 9 must not start until the user approves this settings gate.

---

## Task 9 — Consolidate responsive, accessibility and scroll behavior

**Purpose:** Resolve cross-page behavior at the exact target viewports after all page compositions exist, without creating a separate design-system framework.

**Files:**

- Modify: `apps/web/src/app/globals.css`
- Modify: `apps/web/src/app/product-shell.tsx`
- Modify: `apps/web/src/app/product-shell.test.tsx`
- Modify: `apps/web/src/app/auth-panel.tsx`
- Modify: `apps/web/src/features/sessions/training-entry.tsx`
- Modify: `apps/web/src/features/sessions/training-entry.test.tsx`
- Modify: `apps/web/src/features/sessions/discussion-workspace.tsx`
- Modify: `apps/web/src/features/sessions/discussion-workspace.test.tsx`
- Modify: `apps/web/src/features/reports/report-view.tsx`
- Modify: `apps/web/src/features/reports/report-view.test.tsx`
- Modify: `apps/web/src/features/settings/settings-page-client.tsx`
- Modify: `apps/web/src/features/settings/settings-page-client.test.tsx`
- Modify: `apps/web/src/lib/ui/training-workspace-layout.ts`
- Modify: `apps/web/src/lib/ui/training-workspace-layout.test.ts`

**Interfaces consumed:** existing structural props and ARIA states from Tasks 1–8, focused-mode boundary, separator semantics and layout-preference helper.

**Interfaces produced:** no new business interface; shared CSS variables/classes and responsive structural markers only.

### Step 1: Write RED tests

Add/adjust structural tests to prove:

- entry, normal Shell, lobby/setup, report and settings have one explicit main scroll owner per composition;
- active discussion remains height-bounded and preserves transcript-only center scrolling;
- focused training uses the full available viewport; normal navigation does not shrink it;
- feasible desktop widths render accessible separators, and insufficient widths fall back rather than squeeze the three panels;
- stored desktop widths never affect tablet/mobile panel switching;
- settings section navigation works at desktop/tablet/mobile without horizontal page overflow;
- tabs/radios have correct labels, selected/current/disabled state and keyboard behavior;
- selected question indication includes text/icon, not only a CSS color;
- report state actions have accessible names and focus-visible behavior;
- separator focus, hover and dragging are visually distinguishable and keyboard increments remain 16/40px;
- reduced-motion hooks apply to every shared transition class;
- no test locks exact cosmetic Tailwind strings unless the string encodes a required grid/scroll breakpoint.

### Step 2: Observe RED

```powershell
pnpm.cmd --filter @group-interview-arena/web exec vitest run src/app/product-shell.test.tsx src/app/auth-panel.test.tsx src/features/sessions/training-entry.test.tsx src/features/sessions/discussion-workspace.test.tsx src/features/sessions/discussion-stage.test.tsx src/features/reports/report-view.test.tsx src/features/settings/settings-page-client.test.tsx src/lib/ui/training-workspace-layout.test.ts
```

Expected RED: one or more newly asserted cross-page scroll, mobile navigation, selection or state-action contracts are absent.

### Step 3: Implement minimally

- Consolidate the approved cool-gray/indigo/Surface/border/shadow/radius/type/spacing/motion values in `globals.css` and use them only where multiple F010 surfaces share them.
- Desktop normal mode: 232–240px sidebar, 64–72px header, 1200–1280px canvas; 12-column lobby/setup/report and 900–1000px settings content. Focused mode uses the viewport and preserves 220/520/220 feasibility.
- Tablet 768×1024: compact normal navigation; 1–2-column content; settings section switcher; focused discussion support switching, never three squeezed columns.
- Mobile 390×844: single-column entry/lobby/setup/report/settings; focused discussion tabs and composer remain reachable with no global-nav competition.
- Short 1100×360 and 125% zoom: lobby/setup own vertical scrolling; active discussion remains bounded with one center transcript scroller.
- Keep transitions 120–220ms and make reduced motion remove nonessential movement.

### Step 4: Verify GREEN

Run the focused Task 9 command again. Expected GREEN: all cross-page structural/accessibility tests pass.

### Step 5: Review checkpoint

```powershell
git diff --check -- apps/web/src/app apps/web/src/features/sessions apps/web/src/features/reports apps/web/src/features/settings apps/web/src/lib/ui
git diff -- apps/web/src/app/globals.css apps/web/src/app/product-shell.tsx apps/web/src/features/sessions/training-entry.tsx apps/web/src/features/sessions/discussion-workspace.tsx apps/web/src/features/reports/report-view.tsx apps/web/src/features/settings/settings-page-client.tsx apps/web/src/lib/ui/training-workspace-layout.ts
git status --short
```

Inspect for body + workspace + transcript triple scrolling, focused chrome leaking normal navigation, desktop widths leaking to mobile, inaccessible separators/disabled controls, settings overflow, excessive gradients/animation and ad-hoc duplicated visual values. Do not commit or push.

---

## Task 10 — Final visual matrix and real-flow regression

**Purpose:** Recapture every previously approved page family as one aggregate matrix, prove that later work has not regressed an approved Surface, and complete the real session/report/settings/layout journey. Task 10 is the final visual regression pass, not the first visual inspection.

**Files:**

- Modify: `apps/web/e2e/auth.spec.ts`
- Modify: `apps/web/e2e/session.spec.ts`
- Modify: `apps/web/e2e/report.spec.ts`
- Modify: `apps/web/e2e/auth.spec.ts` for the owning settings assertions; do not create an undiscovered standalone spec
- Update evidence section only: `docs/superpowers/plans/2026-09-15-p1-8-f010-demo-v2-alignment-implementation.md`
- Do not modify: `apps/api/tests/integration/browser_e2e.py`
- Do not modify: `apps/api/tests/integration/p1_7d_report_e2e.py`
- Do not weaken: `apps/web/e2e/p1-6d-*.spec.ts`

**Interfaces consumed:** existing real local API/PostgreSQL browser harness, Playwright `testInfo.outputPath/attach`, real catalog/session/report/settings routes and browser storage APIs.

**Interfaces produced:** final browser acceptance assertions, the original 15-screenshot regression matrix, 3 settings screenshots and required focused-layout interaction evidence; no runtime interface.

### Step 1: Consolidate final acceptance assertions without manufacturing RED

Review and, only where the final aggregate contract is not already covered, add browser acceptance assertions. Do not add or alter an assertion merely to force a failing Task 10 run. Because Tasks 1–9 retain their own RED/GREEN cycles and Tasks 2–8 have already passed the applicable user visual gates, Task 10 assertions may pass on their first run.

`auth.spec.ts` using the real local API path must prove:

- login/register at 1440×900, 768×1024 and 390×844;
- entry split/single-column structural markers and no document horizontal overflow;
- authenticated shared Shell and exact disabled future entries;
- Bento lobby contains only supported facts;
- “开始选题” exposes 3 real type groups, computed 4/4/4 counts and all 12 real questions across tabs;
- keyboard selects a radio card and selected detail comes from the real detail endpoint;
- 1100×360 and existing stable 125% Chromium zoom keep lobby/setup controls reachable.

`session.spec.ts` must preserve every existing recovery/realtime assertion and update only UI locators required by the new setup. Add:

- every real non-terminal status uses focused training and terminal statuses restore normal ProductShell without remounting SessionPanel;
- 1440×900 default-width and custom-width three-region proportion assertions with compact Session Bar and no normal global chrome;
- pointer and keyboard resizing, hard bounds, center 520px protection and visible separator focus;
- preference survives reload and a second/new session;
- malformed/unsupported localStorage falls back to 280/280 without breaking training;
- 768×1024 and 390×844 support switching without extra REST reads, WebSocket creation or remount;
- mobile/tablet are unaffected by the stored desktop preference;
- 1100×360 plus 125% zoom scroll-owner/composer reachability;
- narrow navigation projection behavior observable through truthful global controls;
- no local/session storage of session, transcript or private notes; the only allowed localStorage value is the exact v1 layout object under the frozen key.

`report.spec.ts` under the existing P1-7D real harness must prove:

- completed session enables the global Shell report entry and that entry performs POST before route navigation;
- report route uses the shared Shell, displays current owner and keeps future entries disabled;
- refresh performs persisted GET rendering and preserves exact quote/provenance;
- 1440×900, 768×1024 and 390×844 have no horizontal overflow and preserve 8/4 then 6/6 priority order;
- logout returns to entry; non-owner remains nondisclosing;
- no score/radar/ranking/growth/Mock content exists.

The settings flow in `auth.spec.ts` must prove:

- `/settings` is authenticated, uses normal ProductShell and shows current username/logout;
- desktop/tablet/mobile section navigation remains usable with no horizontal overflow;
- a real custom width preference is reported as browser-local;
- “恢复默认布局” removes only the layout key, updates Settings immediately and causes the next training workspace to use 280/280;
- reduced motion and privacy/future sections remain informational, with no unsupported account/privacy action or functional-looking fake switch.

Preserve all existing acceptance strength. Do not remove, skip, loosen or rewrite a valid assertion to make the final run pass.

### Step 2: Run the aggregate browser pass and recapture the full matrix

Run both real focused harnesses:

```powershell
uv run --project apps/api python apps/api/tests/integration/browser_e2e.py
uv run --project apps/api python apps/api/tests/integration/p1_7d_report_e2e.py
```

It is valid for both harnesses and all final acceptance assertions to pass on this first Task 10 run. Use `testInfo.outputPath()` and `testInfo.attach()` so generated screenshots stay test artifacts, not repository source. Recapture the complete original 15-screenshot matrix:

| Surface                                   | 1440×900                         | 768×1024                         | 390×844                         |
| ----------------------------------------- | -------------------------------- | -------------------------------- | ------------------------------- |
| Login/register                            | `f010-final-entry-1440x900`      | `f010-final-entry-768x1024`      | `f010-final-entry-390x844`      |
| Training lobby                            | `f010-final-lobby-1440x900`      | `f010-final-lobby-768x1024`      | `f010-final-lobby-390x844`      |
| Question setup                            | `f010-final-setup-1440x900`      | `f010-final-setup-768x1024`      | `f010-final-setup-390x844`      |
| Active focused discussion, default widths | `f010-final-discussion-1440x900` | `f010-final-discussion-768x1024` | `f010-final-discussion-390x844` |
| Completed report                          | `f010-final-report-1440x900`     | `f010-final-report-768x1024`     | `f010-final-report-390x844`     |

Recapture the additional Settings row:

| Surface  | 1440×900                       | 768×1024                       | 390×844                       |
| -------- | ------------------------------ | ------------------------------ | ----------------------------- |
| Settings | `f010-final-settings-1440x900` | `f010-final-settings-768x1024` | `f010-final-settings-390x844` |

Also attach these focused interaction states without replacing the default-width discussion row:

- `f010-final-discussion-1440x900-custom-widths`;
- reload and second/new-session persistence evidence;
- reset in Settings followed by next-session default-width evidence;
- malformed v1 and unsupported-version fallback evidence;
- 768×1024 or 390×844 evidence proving the same desktop preference does not alter support-panel composition.

For each screenshot, reopen and compare against the original Demo V2 screenshots/source from `D:\Users\HP\Downloads\ai-group-interview-full-demo-standalone-v2 (2).zip` at the same viewport; memory or a textual description alone is not acceptable. Also compare with the corresponding user-approved Task 2–8 evidence so later changes cannot silently regress an approved Surface. Record in this plan’s evidence section:

- composition mismatch;
- hierarchy mismatch;
- width/proportion mismatch;
- spacing-density mismatch;
- typography mismatch;
- unsupported fake content;
- responsive overflow;
- correction made or explicit reason no correction was needed.

### Step 3: Treat failures as acceptance findings and correct the owning task

Any browser failure or material mismatch discovered in Task 10 is an acceptance finding, not a required artificial RED phase. Correct it only in the owning Task 1–9 frontend files, then rerun that task's focused Vitest GREEN command and the affected real browser harness. If the correction affects a previously approved Surface, recapture its required viewports and include the changed evidence in the final review.

Do not weaken an assertion, manipulate a screenshot, change the reference, or lower an acceptance criterion to manufacture GREEN. If a finding cannot be corrected inside the owning Task 1–9 files without changing an approved boundary, stop and report the scope conflict.

### Step 4: Verify final GREEN and run the full F010 gates

```powershell
uv run --project apps/api python apps/api/tests/integration/browser_e2e.py
uv run --project apps/api python apps/api/tests/integration/p1_7d_report_e2e.py
```

Expected GREEN:

- browser auth/session harness passes against isolated real PostgreSQL and local API;
- P1-7D harness passes global report navigation, durable reload and non-owner isolation;
- Playwright no-skipped reporter remains green;
- all 15 original matrix screenshots, 3 Settings screenshots and supplemental focused interaction states are attached and reviewed against both the original Demo V2 source and applicable earlier user-approved evidence;
- reload/new-session persistence, Settings reset, malformed storage fallback and mobile non-application all pass through real browser flows;
- every Task 10 acceptance finding has either been corrected in its owning task files and revalidated or reported as a blocking scope conflict.

The separate report command is mandatory because the current root `web:test:e2e` browser driver does not select `e2e/report.spec.ts`.

After focused GREEN, run:

```powershell
pnpm.cmd web:test
pnpm.cmd web:lint
pnpm.cmd web:typecheck
pnpm.cmd web:format:check
pnpm.cmd web:build
pnpm.cmd web:test:e2e
uv run --project apps/api python apps/api/tests/integration/p1_7d_report_e2e.py
uv run --project apps/api pytest apps/api/tests/test_v01_question_catalog.py
git diff --check
```

Expected GREEN: every command exits 0; the catalog test still proves 12 and 4/4/4; no API/backend implementation file changed. Do not run the full PostgreSQL API suite unless a concrete cross-layer failure requires diagnosis; if an API/backend change appears necessary, stop instead of expanding scope.

### Step 5: Final focused diff and scope inspection

```powershell
git diff --name-only
git diff --stat
git diff -- apps/web/src apps/web/e2e docs/superpowers/plans/2026-09-15-p1-8-f010-demo-v2-alignment-implementation.md
git status --short
git diff --cached --name-only
```

Confirm:

- changed implementation paths are confined to `apps/web` plus the F010 plan evidence record;
- existing `apps/api` dirty files are the preserved pre-F010 changes, not F010 edits;
- generated schema and report parser allowlist are unchanged;
- no skipped/disabled existing acceptance test was introduced;
- staging is empty;
- no commit or push occurred.

---

## 3. Visual QA evidence record

Tasks 1–9 completed their approved implementation and visual gates, and Task 10 completed aggregate implementation verification on 2026-09-18. Later Final Composition Acceptance and bounded closeout repairs/re-verification passed; the user authorized formal status closeout on 2026-09-19. F010 and P1-8 are therefore `DONE / CLOSED`. This evidence was one part of the later combined P1 acceptance chain; the subsequent P1 phase-close assessment/re-assessment completed the parent-phase closeout.

| Checkpoint                             | Required evidence                                                                                                 | Approval boundary                            | Plan status     |
| -------------------------------------- | ----------------------------------------------------------------------------------------------------------------- | -------------------------------------------- | --------------- |
| Task 2 — login/register + shared Shell | Entry and authenticated Shell at 1440×900, 768×1024 and 390×844                                                   | Explicit user visual approval before Task 3  | `USER_APPROVED` |
| Task 3 — lobby + categorized setup     | Lobby and setup at 1440×900, 768×1024 and 390×844                                                                 | Explicit user visual approval before Task 4  | `USER_APPROVED` |
| Task 4 — active discussion             | Real discussion plus AI-preparing and mobile support views                                                        | Explicit user visual approval before Task 5  | `USER_APPROVED` |
| Task 5 — completed report              | Report at 1440×900, 768×1024 and 390×844                                                                          | Explicit user visual approval before Task 6  | `USER_APPROVED` |
| Task 6 — focused training              | Desktop active, desktop AI-preparing and mobile focused training                                                  | Explicit user visual approval before Task 7  | `USER_APPROVED` |
| Task 7 — resizable workspace           | Default, left/right expanded, bounds, keyboard and reload/new-session persistence                                 | Explicit user visual approval before Task 8  | `USER_APPROVED` |
| Task 8 — settings center               | Settings at 1440×900, 768×1024 and 390×844                                                                        | Explicit user visual approval before Task 9  | `USER_APPROVED` |
| Task 10 — final aggregate regression   | Original 15-screenshot matrix, 3 Settings screenshots and supplemental layout/persistence/reset/fallback evidence | Final visual matrix and real-flow acceptance | `VERIFIED`      |

Every comparison must reopen the original Demo V2 screenshots/source from `D:\Users\HP\Downloads\ai-group-interview-full-demo-standalone-v2 (2).zip`; memory and textual descriptions are supporting notes only, never the visual reference.

### Task 10 implementation-verification evidence — 2026-09-18

- Original Demo V2 was reopened from the required ZIP and copied into the external evidence bundle under `reference/`; comparison used its source and screenshots, not memory.
- Final visual review captured 33 PNGs in transient local acceptance evidence: the six page families at 1440×900, 768×1024 and 390×844; AI-preparing, custom-width, mobile task/progress, 1100×360, 125% effective zoom, reload/new-session persistence, malformed/unsupported storage fallback, Settings custom/reset state and next-session default evidence. Those local screenshots supported the completed review but are not a committed or authoritative repository dependency.
- Final Web gates: `web:test` 21 files / 274 tests passed; typecheck, lint, format and production build exited 0; `web:test:e2e` passed the real browser/recovery group 5/5 and P1-6D 2/2.
- Cross-layer gates: the final independent invocation of `browser_e2e.py` passed 5/5 against real temporary PostgreSQL; `p1_7d_report_e2e.py` passed 1/1; `test_v01_question_catalog.py` passed 4/4.
- One aggregate acceptance finding was a stale P1-6D browser entry assumption that still expected the removed heading/combobox. It was corrected to discover the real target question's `question_type`, activate the real category, keyboard-select the exact card and assert the exact `question_version_id`; all later recovery, privacy, exact-once, cancellation and completion assertions remained unchanged and passed.
- No material visual mismatch remains inside F010 scope. Non-blocking evidence-only differences are the Next.js development badge in dev-server captures and deterministic recovery-provider sentinel text in provenance/persistence captures; neither exists as a production UI field or weakens the clean six-family visual matrix.
- Task 10 changed only frontend E2E acceptance files plus these two F010 documents. No product, backend/API/schema, dependency, lockfile, migration or generated-contract file was changed by Task 10; no commit or push occurred.

## 4. Dependency order and review boundaries

1. Tasks 1–5 establish and have user approval for the normal Shell, public entry, lobby/setup, discussion composition and report flow.
2. Task 6 uses the existing narrow status projection to switch real non-terminal sessions into focused presentation, then stops for explicit user visual approval.
3. Task 7 depends on Task 6's full-viewport workspace, adds UI-only width state/persistence, then stops for explicit user visual/interaction approval.
4. Task 8 consumes Task 7's helper, makes Settings a real normal-ProductShell route and reset owner, then stops for explicit user visual approval.
5. Task 9 cannot start before Task 8 approval; it consolidates responsive, accessibility and scroll behavior across every old and new Surface.
6. Task 10 recaptures the original 15-screenshot matrix plus Settings and focused-layout evidence, verifies approved Surfaces did not regress, and runs aggregate real-flow/Web gates. It is final aggregate acceptance, not first visual inspection, and may send bounded findings back to owning Task 1–9 files.

Each task is independently reviewable at its checkpoint. No executor may bypass a Task 6–8 user visual-approval stop, collapse the work into a single CSS-only redesign, or bypass an earlier state-owner boundary.

## 5. Plan self-review

| Check                       | Result                                                                                                                                                |
| --------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------- |
| Spec coverage               | Existing F010 Surfaces plus focused mode, resizing, v1 preference, Settings, responsive/accessibility and final QA are mapped to executable tasks     |
| Placeholder scan            | No unresolved placeholders; Tasks 1–9 are truthfully `USER_APPROVED`, Task 10 and the later bounded closeout gates are complete                       |
| Type/interface consistency  | Focused mode uses the exact generated status union; Shell receives only the narrow projection; settings/layout helpers carry no Snapshot              |
| Lifecycle                   | `CREATED` through `FINAL_SUMMARY` are focused; loading/lobby, `COMPLETED`, `ABORTED_USER`, report and settings use normal ProductShell                |
| Dependency order            | Approved Tasks 1–5 → focused gate → resize/persistence gate → settings gate → consolidation → final aggregate regression                              |
| P2/P3 leakage               | None; scoring, voice, drills, growth, commercial and history features remain excluded                                                                 |
| API/backend leakage         | None planned; any required API/backend modification is a stop condition                                                                               |
| Mock-data leakage           | Unit fixtures prove presentation in isolation; final browser acceptance uses existing real local API/PostgreSQL harnesses                             |
| Privacy                     | The only new persistence is `{version:1,leftWidth,rightWidth}` under `gia.training.workspace.layout`; no session/business/private-note data is stored |
| Reset semantics             | Settings deletes only the preference and updates itself; it promises defaults for the next workspace mount, not a hidden active workspace             |
| Responsive fallback         | Desktop resizing requires 220/520/220 plus structural space; otherwise existing support-panel switching applies and stored widths are ignored         |
| Settings truthfulness       | Real username/logout/reset only; reduced motion, privacy and future items are informational; no backend API or fake controls                          |
| User visual approval        | Task 6 gates Task 7, Task 7 gates Task 8, and Task 8 gates Task 9 with the exact hard-stop wording                                                    |
| Visual QA                   | Tasks 6–8 inspect new features before Task 10; Task 10 recaptures the original 15 matrix plus Settings and focused interaction states                 |
| Task 10 role                | Final regression and real-flow acceptance only; it does not require artificial RED and is not the first visual inspection                             |
| Report ownership            | Shell emits intent; SessionPanel validates/generates/navigates; ReportPageClient authenticates route; ReportView reads/parses/renders                 |
| Existing remediation safety | F005–F009 tests and behavior remain mandatory, and existing P1-6D acceptance tests cannot be weakened                                                 |

No product decision remains unresolved inside the approved F010 boundary. Task 10 implementation verification, Final Composition Acceptance, bounded blocker/password repairs and closeout re-verification are complete. F010 and P1-8 are `DONE / CLOSED`; P1-7E composition/independent acceptance and P1 phase-close assessment/re-assessment subsequently passed, so P1 is `DONE / CLOSED`.
