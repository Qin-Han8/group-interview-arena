# P1-5F-3B Complete Discussion Page Composition — Design Freeze

Status: `DONE`; `DESIGN_FROZEN / IMPLEMENTATION_PLAN_FROZEN /
IMPLEMENTATION_COMPLETE / ACTUAL_SOURCE_IMPLEMENTATION_REVIEW_PASS /
COMMIT_PUSH_COMPLETE / CI_PASS / F4_COMPOSITION_ACCEPTANCE_PASS /
FINDINGS_NONE_OPEN`; document complete; self-review `PASS`

Design actual-source review: `PASS`; findings: `NONE`; reviewed bundle:
`group-interview-arena-review-20260826-190658.zip`; SHA-256:
`5867365d06fa6e0f1eb6d8f9dc5ec9dd9d806ed0ec444a909ef8266346ceba42`

Current parent status: `P1 IN_PROGRESS`;
`P1-5 IN_PROGRESS / POST_CLOSEOUT_REMEDIATION_OPEN`;
P1-5F/F3/F3A/F3B/F4 retain historical `DONE`;
`P1-5R IN_PROGRESS / DESIGN_FROZEN`; R1/R2-A/R2-B/R3 `NOT_STARTED`

Target version: `V0.1 Internal Validation`

Design-freeze baseline: clean committed `main` at
`7421532db29b8e7c64a1dcce150803803ce21126`, equal to `origin/main`

Immutable product baseline:
[`PROJECT_MASTER_PLAN.md`](../PROJECT_MASTER_PLAN.md), SHA-256
`2388a9660320406cb35d5354126ad71c6849a98db7c4a356796ca951bf372f26`

Parent execution plan:
[`P1-5_ai-runtime-foundation.md`](P1-5_ai-runtime-foundation.md)

Frozen implementation plan:
[`P1-5F-3B_complete-discussion-page-composition-implementation.md`](P1-5F-3B_complete-discussion-page-composition-implementation.md), remediated self-review `PASS`, open findings `NONE`

Implementation closeout: committed implementation baseline
`5efe1346532b95b7fabdd521015fd9f8199a457f`; actual-source implementation
review `PASS`; findings `NONE`; GitHub Actions run `33044682226` `SUCCESS`;
commit/push complete.

F4 composition acceptance: initial acceptance `BLOCKED` on `F4-ACC-001`;
finding-only remediation added network-free Human→AI Browser composition proof;
remediation actual-source review `PASS`; accepted final commit
`af33d89baa0355ae1ee5174a2ef8cfb5e7b14554`; GitHub Actions run
`33050532295` `SUCCESS`; fresh independent final acceptance `PASS`; findings
`NONE`; `F4-ACC-001 CLOSED`; no real provider/model call.

Implementation-plan finding-only remediation: initial actual-source review
`BLOCKED` on exactly `F3B-IP-001` and `F3B-IP-002`; both findings `CLOSED`;
remediated self-review `PASS`; open findings `NONE`. This evidence update does
not change the frozen product-design substance.

Preserved F3A authorities:
[`P1-5F-3A_web-discussion-functional-closure.md`](P1-5F-3A_web-discussion-functional-closure.md)
and
[`P1-5F-3A_web-discussion-functional-closure-implementation.md`](P1-5F-3A_web-discussion-functional-closure-implementation.md)

## Goal

Freeze the complete commercial-quality C-end composition of the text
discussion page without reopening P1-5F-3A realtime, transcript, pending,
rejection or recovery semantics.

The product direction is **AI 群面训练场 / Interview Simulation Studio**:
professional, immersive, reassuring, clear, controllable and commercially
credible for campus and early-career job seekers. `AI 群面训练场` remains the
canonical product name. `Interview Simulation Studio` is a design direction
and optional descriptive phrase, not a branding ADR or product rename.

This checkpoint is documentation only. It does not implement Web source or
tests and does not authorize P1-5F-3B implementation.

## Authority and design constraints

The authority order remains:

```text
PROJECT_MASTER_PLAN
  -> Accepted Decisions
  -> P1-5 / P1-5F-1 public contract
  -> completed F3A functional authority
  -> this F3B composition design
  -> later separately approved Web implementation
```

The Master Plan establishes the relevant product boundaries:

- D-002: campus and early-career job seekers are the primary users;
- D-004: complete simulation is desktop-Web-first;
- D-005: text is valid for V0.1, but the public MVP must later support voice;
- D-007: the first phase uses three AI candidates;
- sections 6 and 20: the experience is professional, restrained and focused
  on training rather than visual AI spectacle;
- sections 7 and 20: desktop uses question, discussion and process regions;
  narrow screens collapse rather than squeeze three columns;
- sections 9 and 14: the page reflects the controlled discussion lifecycle,
  phase and authoritative floor;
- sections 23 and 30–31: P2 voice is a later addition, while P1/V0.1 remains a
  valid text-discussion validation surface.

F3B must not turn the page into a sparse prototype, corporate admin dashboard,
Zoom clone, chat-bubble app, cyberpunk AI interface or fake analytics screen.
It must hide engineering complexity from the primary user interface without
deleting F3A authority or its compatibility hooks.

## Actual-source sufficiency review

The current committed source was inspected before this freeze.

### Existing public facts are sufficient

The generated REST contract and current Web source already provide:

- public Question detail: `title`, `question_type`, `background_domain`,
  `difficulty`, `estimated_minutes`, `scenario`, `objective`,
  `hard_constraints`, `soft_constraints`, `stakeholders` and `options`;
- authoritative session status with `CREATED`, six active phases,
  `COMPLETED` and `ABORTED_USER`;
- `phase_started_at`, `phase_deadline_at`, `server_now` and `last_sequence`;
- safe participant entries with `participant_id`, `actor_kind` and
  `seat_order`;
- zero-or-one current floor grant and a safe latest floor lifecycle fact;
- confirmed Human/AI transcript items with stable identity, authoritative
  sequence, phase and exact plain-text content;
- realtime connection states, one Human pending command, one rejected draft,
  generic AI waiting and generic AI interruption presentation.

These facts are sufficient for the requested composition. No backend, schema,
REST/WS contract or generated OpenAPI change is required.

### Existing frontend authority is sufficient

Current ownership is already correct:

- [`session-panel.tsx`](../../apps/web/src/features/sessions/session-panel.tsx)
  coordinates snapshot, Question load, transcript recovery, realtime,
  confirmed transcript, current floor, draft, pending, rejection, connection
  and send eligibility;
- [`client.ts`](../../apps/web/src/lib/realtime/client.ts) owns the one
  memory-only pending command and exact reconnect resend;
- [`projection.ts`](../../apps/web/src/lib/realtime/projection.ts) projects
  only public authoritative events;
- [`contract.ts`](../../apps/web/src/lib/realtime/contract.ts) remains the
  strict handwritten WS derivative;
- [`discussion-transcript.ts`](../../apps/web/src/features/sessions/discussion-transcript.ts)
  remains the pure confirmed-transcript identity/merge/order authority;
- [`client.ts`](../../apps/web/src/lib/api/client.ts) remains the typed REST
  caller and complete transcript loader.

F3B rearranges presentation around these owners. It does not move their logic
into new children or create a parallel controller.

### Current presentation limitations define the bounded implementation seam

The existing authenticated experience is nested inside an internal-validation
landing shell constrained to `max-w-3xl`. `SessionPanel` is approximately 941
lines and renders status, debug facts, lifecycle controls, transcript,
composer, notices and question detail in one long column.

Therefore a credible three-region composition later requires:

- a small authenticated app-shell adjustment;
- preservation of `SessionPanel` as coordinator;
- extraction of meaningful presentation regions under the existing sessions
  feature;
- no extraction of realtime, transcript or business authority.

This is an expected Web-only presentation delta, not a stop condition.

### Facts that must remain hidden or absent

The primary UI must not show:

- session UUID or Question Version UUID;
- discussion sequence counter or raw server deadline timestamp;
- raw action, grant, participant or utterance IDs;
- provider, model, configuration version, Prompt Version or token state;
- rendered prompt, Private Stance, Persona calibration or hidden role label;
- raw reason codes, internal error codes or provider failure taxonomy;
- fake pause, conclusion, vote, consensus, evidence, score or report data.

Existing `data-testid` hooks and non-prominent diagnostic markup may remain
where required for regression compatibility, but they cannot be primary
visual content.

## Product intent and comprehension contract

Within the first viewport, an authenticated user with a loaded session must be
able to answer:

1. What is the discussion task?
2. Which phase is active?
3. Who currently owns the floor?
4. May I submit now, and if not, why not?
5. What has already been durably said?
6. Is realtime healthy or recovering?

The page is a simulation workspace, not an engineering console. Technical
authority remains visible through calm, product-language status rather than
raw identifiers or debug rows.

## Overall composition and scroll ownership

The loaded-session experience uses one compact product header and one bounded
workspace below it.

```text
Product/session header
  -> left: Task Brief / 题目与思考
  -> center: Live Discussion / 实时讨论
  -> right: Session Progress / 训练进程
```

The desktop workspace should use the available viewport rather than creating
one long document:

- header remains compact and visible;
- workspace height is based on the remaining viewport using `dvh`-safe CSS;
- all grid/flex ancestors that contain scrollers use `min-height: 0`;
- center transcript owns the primary vertical scroll;
- left Question/notes and right progress may scroll independently when their
  content exceeds available height;
- composer remains reachable at the bottom of the center region;
- the outer page must not require scrolling through the Question before the
  user reaches the discussion composer.

No card-grid or nested-card dashboard is introduced. The three regions are
open workspace rails separated by restrained borders and spacing.

## Compact product header

The header presents only useful public state:

- canonical product name `AI 群面训练场`;
- current session context using the public Question title when available, or
  safe copy such as `文字群面训练` when it is not;
- current phase in product Chinese;
- authoritative display countdown when timing fields are available;
- realtime status;
- current valid lifecycle action.

Lifecycle actions are exact:

- `CREATED`: show the existing Start action and the existing End action;
- active phase: show only the existing End action;
- `COMPLETED` or `ABORTED_USER`: show neither Start nor End;
- no pause control exists because current source does not support pause.

The header does not show UUIDs, sequence, deadline ISO string or internal
version labels. At narrow widths, phase/countdown and connection remain
visible; secondary context may truncate with an accessible full label.

Connection copy is frozen as:

- connected: `连接正常`;
- connecting: `正在连接讨论…`;
- reconnecting/recovery: `正在同步最新讨论记录…`;
- disconnected after bounded recovery failure: a stronger but still safe
  `讨论连接暂时不可用` state with the existing safe retry/recovery behavior.

Connection status includes text and a restrained status mark; color is never
the only indicator.

## Desktop information architecture — `>= 1200px`

At viewport widths of at least 1200 CSS pixels, the workspace is one full
three-column studio:

- left — `题目与思考 / Task Brief`: approximately 22–25%;
- center — `实时讨论 / Live Discussion`: approximately 50–56%;
- right — `训练进程 / Session Progress`: approximately 22–25%.

Implementation may use constrained `minmax()` columns rather than brittle
fixed percentages, but the center must remain visually and dimensionally
primary. The intended practical ranges are:

- left and right: roughly 280–360 CSS pixels each;
- center: at least roughly 560 CSS pixels when the viewport permits;
- gutters/dividers: restrained and consistent, not dashboard-card spacing.

At exactly 1200 pixels, support rails must not force transcript or composer
controls into clipping. The layout may tighten rail padding before it reduces
the center below usable discussion width.

## Left region — Task Brief / 题目与思考

The Question region renders only safe public data already present in
`QuestionDetailResponse`:

- title;
- scenario/background;
- objective;
- hard constraints;
- options when present;
- question type and difficulty only when mapped to stable product Chinese and
  useful to the user.

`estimated_minutes` may be used only as public Question metadata, not as a
phase timer. It must never be converted into invented per-phase durations.
`background_domain`, soft constraints and stakeholders are public but are not
required in the initial F3B composition; they may be added later only when
they improve task comprehension without making the rail dense.

Safe rendering rules:

- scenario and objective are plain text with readable line height;
- each hard constraint and option is keyed by current public data and rendered
  as text, never interpreted as Markdown/HTML;
- empty hard-constraint or option collections produce no decorative empty
  card;
- no hidden conflicts, reference dimensions, acceptable outcomes, phase
  prompts, safety calibration, scoring override or private assignment data is
  requested or rendered;
- no AI answer hints, logic frameworks, facts/cases or suggested talking
  points are invented.

### Private notes scratchpad

The rail includes `我的思路 / 私人笔记` as a real editable textarea.

For P1-5F-3B the notes boundary is exact:

- one React in-memory string for the currently mounted session workspace;
- never written to localStorage or sessionStorage;
- never sent through REST or WebSocket;
- no backend API, schema or generated contract;
- no autosave, reload-persistence or cross-device claim;
- reset when the page/session workspace is replaced or reloaded;
- one visible explanation such as `仅保留在当前页面，刷新后不会保存`.

The notes state must be mounted once and shared across responsive
presentations; desktop/tablet/mobile must not instantiate separate note
authorities. This temporary P1 storage mechanism can later be replaced by a
durable notes feature without changing the three-region composition.

## Center region — Live Discussion / 实时讨论

The center is the page focal point and contains, in order:

1. participant strip;
2. low-pressure session/recovery notices when present;
3. confirmed professional transcript;
4. sticky Human composer and its pending/rejected states.

The participant strip and composer remain visible/reachable while the
transcript scrolls. The center does not become a left/right chat thread.

### Participant strip

For the current standard snapshot composition, show exactly:

- the Human user;
- three AI candidates ordered by safe `seat_order`.

Participant identity is derived only from safe public facts:

- Human label: `你` with an initial treatment such as `我`;
- AI labels: `AI 候选人 1`, `AI 候选人 2`, `AI 候选人 3`;
- each AI is explicitly identified as AI;
- avatar treatment is simple, non-photoreal and code-native, using initials or
  seat identity;
- no private Persona label such as `强势型`, `固执型` or `逻辑型` appears.

Do not synthesize a participant that is absent from the authoritative
snapshot. A malformed or historical roster is shown from safe facts with a
non-fatal availability notice rather than filled with fake candidates.
`SYSTEM` participants are not candidate cards; safe intervention presentation
belongs in the notice/progress region.

Participant status is derived only from current public authority:

- current Human grant: `轮到你发言`;
- current AI grant before matching confirmed utterance: `正在准备发言`;
- current grant card: visually emphasized with accent border/surface and
  explicit text;
- non-current participant: neutral `等待中`;
- no current floor: all candidate cards neutral, while the progress/notice
  region explains the transition from safe floor facts.

The design must not claim `正在思考`, `准备反驳`, emotion, mood, confidence,
strategy or sentiment. It must not draw fake audio waveforms. Card anatomy
reserves a bounded media/status area so P2 can later add real speaking/audio
indicators without rearranging participant identity and floor emphasis.

### Confirmed transcript

The transcript preserves every F3A invariant:

- only durable `participant.utterance.created` facts are normal discussion
  contributions;
- REST/WS merge identity remains `utterance_id`;
- order remains authoritative sequence with existing deterministic tie-break;
- transcript-only sequences remain legitimately non-contiguous;
- pending and rejected Human content never become confirmed transcript;
- recovery keeps the last confirmed transcript visible;
- same-identity field conflict uses the existing authoritative full recovery;
- exact content and original whitespace/newlines are preserved;
- content is rendered as plain text, never Markdown or HTML.

The visual form is a professional meeting record:

- one vertical contribution list, not alternating chat bubbles;
- speaker identity is aligned consistently on every row;
- phase is secondary metadata in clear Chinese;
- content has comfortable long-form line height and measure;
- latest confirmed contribution may receive subtle, non-animated emphasis;
- empty transcript copy explains that confirmed contributions will appear;
- the transcript is the primary independently scrollable region.

Auto-follow remains the existing F3A near-bottom behavior. F3B adds no
virtualization, unread-count subsystem or new-message authority.

### Sticky Human composer

The composer stays attached to the center bottom and preserves F3A exactly:

- draft is editable before the Human owns the floor;
- Enter inserts a newline;
- Ctrl+Enter/Cmd+Enter submits only when current F3A send gates pass;
- Send is enabled only for a floor-enabled phase, exact Human current grant,
  connected realtime, no pending command and valid current draft;
- click-time code re-reads and binds the exact latest Human floor grant;
- accepted content is `1..4000` Unicode code points;
- U+0000 is rejected; whitespace-only is rejected;
- content is not trimmed, normalized or truncated;
- one Human pending command exists at most;
- pending is not confirmed transcript;
- rejected exact content never silently overwrites a newer draft.

Disabled submission is explained in product language adjacent to the control:

- preparation/non-speaking phase: `当前阶段可以整理思路，暂时不能发送`;
- AI or no Human floor: `你可以先整理观点，轮到你时再发送`;
- reconnecting: `正在恢复讨论，暂时无法发送`;
- Human floor: `轮到你发言`;
- pending: `正在确认上一条发言`;
- invalid text: keep the exact 4000-code-point/null/empty guidance.

Pending is a compact, low-pressure confirmation block next to the composer,
showing its exact content and `尚未进入讨论记录`. Rejection is a separate
recoverable amber-toned block with the exact rejected content and explicit
restore/replace action. Neither is a chat bubble or fatal page error.

No autosave claim, server draft persistence, new Enter-to-send rule or
800-character limit may be introduced.

## Right region — Session Progress / 训练进程

The right rail renders only public, authoritative or safely derived state:

- current phase;
- six-phase progression;
- countdown from existing authoritative time fields;
- current floor owner;
- safe explanation of floor state where useful;
- lightweight connection/recovery state.

### Six authoritative phases

The phase mapping is exact:

- `PREPARATION` → `准备`;
- `OPENING_STATEMENTS` → `个人陈述`;
- `EXPLORATION` → `观点探索`;
- `CONFLICT_AND_EVALUATION` → `讨论与评估`;
- `CONVERGENCE` → `收敛决策`;
- `FINAL_SUMMARY` → `最终总结`.

All six phases remain visible in order. The active phase has text, position and
accent treatment; completed/remaining phases use restrained non-semantic
styling. Do not replace them with a fake five-step flow.

`CREATED`, `COMPLETED` and `ABORTED_USER` are lifecycle states around the
six-phase progression, not extra speaking phases.

### Countdown

Countdown derives only from the existing F3A calculation:

```text
server_now anchor + local elapsed display time -> phase_deadline_at difference
```

It is display-only and never advances the lifecycle. If no authoritative
deadline is available, show safe state copy rather than a fabricated time.
Do not display hard-coded per-phase minute values, even though the Master Plan
contains configurable product guidance.

### Floor and extension seams

Current floor copy uses safe participant labels only. Safe no-floor or
intervention copy may say `正在安排下一位发言者` or a mapped generic host
intervention message; raw reason codes remain hidden.

The rail reserves component/layout seams for later structured conclusion and
voting. In F3B those seams are implementation boundaries only, not visible
fake modules. Do not render consensus percentages, vote results, conclusion
content, disabled decorative controls or pretend functionality.

## Realtime and notice hierarchy

Presentation priority is:

1. fatal page/session load error;
2. reconnect/recovery status;
3. recoverable Human rejection/action conflict;
4. Human pending confirmation;
5. generic AI interruption;
6. normal AI waiting.

This priority prevents stale AI waiting from competing with recovery. It does
not delete lower-priority state; for example a rejected draft remains
recoverable while the connection synchronizes.

Connected status is subtle. Reconnecting keeps the full confirmed transcript,
Question and draft visible, adds `正在同步最新讨论记录…`, and disables Send
through existing F3A authority. It never replaces the page with a loading
screen.

AI waiting and interruption continue to use only current floor, matching
confirmed utterance and generic `INTERRUPTED` release facts. No provider,
model, HTTP status, retry, ETA or token-streaming information is shown.

Ordinary pending/rejection/recovery states use neutral, blue or amber
low-pressure presentation. Strong red treatment is reserved for fatal states
that block the whole session, not routine controlled-turn behavior.

## Responsive architecture

There are exactly three responsive bands. They reuse the same components,
props and authoritative state; there is no separate mobile session model.

### Desktop — `>= 1200px`

- full three-column studio;
- all three regions visible;
- center is primary;
- independent rail/transcript scrolling;
- composer stays at center bottom.

### Tablet — `768px–1199px`

- discussion remains the full primary surface;
- compact `题目` and `进程` access controls sit near the discussion header;
- at most one support region opens as an accessible compact side sheet or
  inline overlay over the workspace edge;
- opening a support region does not remount or refetch authority;
- composer remains visible/reachable;
- three full columns are never squeezed into this width.

The exact sheet animation is not frozen; state ownership is. One local
presentation value such as `activeSupportPanel = task | progress | null`
controls visibility only.

### Mobile — `< 768px`

Use a semantic tab interface in this exact order:

1. `讨论`;
2. `题目`;
3. `进程`.

Default tab is `讨论`. The same single Task Brief, Live Discussion and
Progress component instances are shown/hidden by presentation state; they do
not refetch, reconnect or duplicate notes/transcript authority. The discussion
tab keeps participant context, transcript and composer easy to reach. Header
content compacts without losing phase/countdown/connection comprehension.

Tabs are keyboard reachable, use semantic `tablist`/`tab`/`tabpanel`
relationships, expose selected state, support visible focus and do not rely on
color alone. Tab/collapse choice is local presentation state only and is not
stored in browser storage.

Mobile/narrow Web is supported, but it is not promised as the optimal complete
simulation experience, consistent with the Master Plan.

## Component architecture and dependency direction

F3B preserves F3A Option B.

```text
REST + one realtime client + pure transcript model
                  |
             SessionPanel
      authoritative feature coordinator
                  |
     derived props + callbacks only
                  |
      presentation-oriented components
```

### SessionPanel remains authoritative coordinator

`SessionPanel` continues to own or coordinate:

- snapshot and Question loading;
- realtime connection and recovery bundle;
- confirmed transcript merge/application;
- current floor and send eligibility;
- Human draft, pending and rejected content;
- start/end lifecycle callbacks;
- current error/notice inputs.

It also owns the small page-local notes string and responsive selection state,
or passes them from one single mounted workspace owner. These are explicitly
presentation-only and cannot influence session authority.

### Presentation component responsibilities

Exact filenames may vary during an approved implementation, but boundaries
are frozen:

- `DiscussionWorkspace` / `SimulationStudioShell`
  - composes header and three responsive regions;
  - owns no network or business transition;
  - applies the three breakpoint bands and one local active-surface state.
- `SessionHeader`
  - receives public context, phase, countdown, connection and existing
    lifecycle callbacks;
  - never calculates server authority or creates unsupported actions.
- `TaskBriefPanel`
  - renders allowlisted public Question fields;
  - receives note value/change callback or hosts the one explicitly keyed
    in-memory notes state;
  - performs no Question refetch.
- `ParticipantStrip`
  - receives safe participants and current grant;
  - derives labels/status through pure presentation helpers only;
  - never reads Persona/private/runtime data.
- `DiscussionTranscriptView`
  - renders the already-confirmed transcript and existing scroll callback/ref;
  - never merges, fetches or gap-validates transcript.
- `HumanComposer`
  - receives draft/pending/rejected values, exact callbacks, eligibility and
    product-language reason;
  - never creates its own realtime client or captures a floor outside the
    coordinator callback.
- `SessionProgressPanel`
  - receives current status/timing/countdown/floor presentation;
  - never advances phase or invents duration/conclusion/vote data.
- `ResponsiveDiscussionTabs`
  - controls local presentation visibility only;
  - never duplicates a panel instance or feature state.
- `SessionNoticeLayer`
  - applies the notice priority and appropriate live-region behavior;
  - never converts internal errors into public detail.

Small phase, participant and reason label mappings may move to one pure
feature-local presentation helper. This helper consumes existing public types
and produces display strings/variants only. It is not a store or state
machine.

Presentation children must not:

- instantiate WebSocket or API clients;
- independently fetch snapshot, Question or transcript;
- own a second authoritative transcript/floor/session copy;
- change F3A merge, recovery, pending or click-time binding behavior;
- add Redux, Zustand, Context-based global business authority or a frontend
  business state machine;
- depend on provider/config/prompt/private data.

## Lifecycle and state presentation

The design covers the complete current lifecycle without inventing behavior.

### No session / Question selection

- show a focused training-start surface rather than an empty three-column
  shell;
- retain exact immutable Question selection and create-session behavior;
- explain that the experience is a text simulation for current validation;
- no UUID, internal phase/version or fake personalization.

### `CREATED`

- load the full studio with Question and participant strip;
- phase copy is `未开始`;
- show existing Start and End actions;
- transcript uses its confirmed empty state;
- notes and draft are editable;
- Send is disabled with an explicit stage reason.

### `PREPARATION`

- emphasize Question reading and private notes without hiding discussion;
- progress highlights `准备` and authoritative countdown when present;
- participant cards remain neutral unless public floor unexpectedly says
  otherwise;
- draft remains editable; Send is disabled.

### Five speaking phases

- progress highlights the exact current phase;
- participant strip shows authoritative current floor;
- transcript remains primary;
- composer obeys unchanged F3A gates.

### Human floor

- Human participant is visibly highlighted;
- composer copy says `轮到你发言`;
- Send becomes enabled only if every other F3A gate passes;
- focus is not stolen when the floor changes.

### AI floor

- exact AI participant is highlighted;
- generic `正在准备发言` appears only until matching confirmed AI content;
- Human draft remains editable; Send remains disabled;
- no invented mental state or model lifecycle.

### No floor / intervention transition

- all candidate cards are neutral;
- center/right show safe `正在安排下一位发言者` or mapped public
  intervention copy;
- no Browser timer chooses or retries a speaker.

### Human pending

- exact pending content appears near composer as non-transcript confirmation;
- transcript does not optimistically add it;
- next draft may be edited, but a second submit stays disabled.

### Rejected Human draft

- exact rejected content remains in a separate recoverable block;
- newer draft is never overwritten;
- restore/replace is explicit;
- safe product copy does not disclose raw rejection cause.

### Reconnect / recovery

- confirmed transcript, Question, notes and draft stay visible;
- light non-blocking synchronization state takes notice priority;
- Send stays disabled through existing connection gate;
- successful recovery restores normal status without blanking history.

### AI interrupted

- show the existing one-time generic non-transcript notice;
- no fatal styling, retry control or provider detail;
- normal floor progression remains authoritative.

### `COMPLETED`

- show a calm `讨论已完成` state;
- preserve read-only transcript, Question and six-phase history;
- remove active composer submission and lifecycle actions;
- reserve a future P3 report/evidence entry seam without rendering a fake
  report button or disabled placeholder.

### `ABORTED_USER`

- show `训练已结束` and preserve confirmed history;
- no resume, report, score or conclusion behavior is invented;
- composer submission and lifecycle actions are absent.

### Missing/historical Question binding

- keep transcript, progress and floor history available;
- Task Brief shows `此历史会话没有可展示的题目内容` or equivalent safe copy;
- do not expose Question Version UUID or block the whole workspace.

### Narrow viewport

- mobile defaults to Discussion;
- task/progress remain reachable through exact tabs;
- no duplicate authority or browser persistence is introduced.

## Visual system freeze

The visual direction is professional, modern, reassuring and slightly
technological without spectacle.

### Color

- neutral near-white workspace background;
- white or very lightly tinted surfaces;
- near-black primary text and neutral secondary text;
- one controlled indigo-blue brand accent for current/interactive emphasis;
- semantic blue for recovery/info and restrained amber for recoverable
  rejection;
- strong red only for fatal blocking failure;
- no recruitment pass/fail red-green system;
- no excessive gradients, glassmorphism, glow or rainbow AI treatment.

Exact implementation tokens may use current Tailwind colors or a small set of
CSS custom properties in existing global styles. No new design-system or icon
dependency is needed.

### Typography

- keep a dependable system sans-serif stack; no external font dependency;
- compact product header with strong but not oversized brand hierarchy;
- panel headings clearly distinct from labels;
- transcript content approximately normal reading size with generous line
  height and stable long-form measure;
- controls, tabs and status text receive deliberate size/weight rather than
  browser defaults;
- engineering-style uppercase labels are not used as decorative product copy.

### Geometry and density

- restrained 8–12px family radii where framing is useful;
- thin neutral borders and very light elevation only at major shell/sticky
  boundaries;
- no card inside card inside card;
- participant cards are compact status anchors, not oversized video tiles;
- side rails are dense enough for active work but not KPI dashboards;
- spacing follows one consistent small/medium/large rhythm.

### Motion

- motion is optional and limited to panel/tabs/status transitions;
- no pulsing fake waveform or AI glow;
- respect `prefers-reduced-motion`;
- new transcript emphasis must not distract or repeatedly animate.

## Accessibility freeze

Later implementation must provide:

- semantic `header`, `main`, discussion `section` and supporting `aside`
  regions with accessible names;
- logical heading order across all responsive bands;
- keyboard-reachable Start/End, tabs, textarea, Send and recovery actions;
- visible focus rings with adequate contrast;
- programmatically associated textarea labels for draft and notes;
- semantic tab relationships and selected state;
- status text in addition to color/shape;
- appropriate, non-duplicated `aria-live` for connection recovery, pending,
  rejection and AI interruption;
- no `aria-live` on the entire transcript list;
- adequate contrast for muted text, borders and accent states;
- no focus theft on floor, phase, transcript or connection changes;
- touch targets suitable for narrow screens.

Existing F3A test hooks may remain even when debug facts become visually
hidden or moved to non-prominent diagnostic markup.

## Commercial-forward compatibility seams

F3B prepares layout and component seams but implements none of these features.

### P2 voice

- participant card has a reserved bounded speaking-status area;
- composer has a future control slot for microphone state;
- center notice/control boundary can later host real interrupt controls;
- no mic button, waveform, audio level, TTS playback or interruption command
  appears in F3B.

### P3 report and evidence

- completed-state header/workspace has a future post-session action slot;
- transcript row anatomy can later receive evidence anchors without changing
  content authority;
- no report route, score, evidence marker or analysis claim appears now.

### Later conclusion and voting

- right progress component has private extension boundaries for conclusion
  and vote props/components;
- these boundaries are absent from rendered F3B UI until durable public data
  and commands are separately approved;
- no fake conclusion, percentage, vote controls or disabled decoration.

At the post-P2 voice-loop checkpoint, the project formally re-evaluates
whether Option B should evolve to a feature-scoped B+/C architecture. F3B does
not introduce that architecture early.

## Proposed bounded future implementation file map

This map is a proposal for a later separately approved F3B implementation. It
does not authorize edits now.

### Existing app-shell files

- `apps/web/src/app/page.tsx`
  - remove the authenticated experience's prototype-width constraint and
    allow a viewport-filling studio while preserving the unauthenticated
    entry experience.
- `apps/web/src/app/auth-panel.tsx`
  - compose the authenticated product shell, preserve auth/logout behavior and
    pass only public account/session presentation needs;
  - do not move session authority into auth state.
- `apps/web/src/app/globals.css`
  - add only small global surface/type/focus tokens needed by the studio;
  - no UI framework, font package or large design-system layer.
- `apps/web/src/app/page.test.tsx` and
  `apps/web/src/app/auth-panel.test.tsx`
  - preserve unauthenticated/authenticated shell behavior and ensure internal
    validation chrome does not crowd the loaded studio.

### Existing sessions authority files

- `apps/web/src/features/sessions/session-panel.tsx`
  - remain authoritative coordinator;
  - derive presentation props and compose extracted children;
  - remove primary debug rows while preserving required hooks;
  - own one notes value and one responsive presentation selection.
- `apps/web/src/features/sessions/session-panel.test.tsx`
  - preserve every F3A semantic regression and add lifecycle/prop wiring,
    local-only notes and no-second-authority assertions.

### New sessions presentation files

- `apps/web/src/features/sessions/session-presentation.ts`
  - pure public-state-to-label/variant helpers only;
  - no React state, network, transcript merge or business transition.
- `apps/web/src/features/sessions/session-presentation.test.ts`
  - exact six-phase, participant/floor, connection and disabled-reason mapping.
- `apps/web/src/features/sessions/discussion-workspace.tsx`
  - header, responsive three-region shell, tablet support panel and mobile tab
    composition.
- `apps/web/src/features/sessions/discussion-workspace.test.tsx`
  - semantic regions/tabs, single panel instances, default Discussion tab and
    local presentation behavior.
- `apps/web/src/features/sessions/task-brief-panel.tsx`
  - allowlisted Question fields and page-local notes presentation.
- `apps/web/src/features/sessions/participant-strip.tsx`
  - Human + AI seat/status cards from safe props only.
- `apps/web/src/features/sessions/discussion-transcript-view.tsx`
  - professional confirmed-transcript rendering and existing scroll behavior.
- `apps/web/src/features/sessions/human-composer.tsx`
  - draft/pending/rejected presentation and callbacks only.
- `apps/web/src/features/sessions/session-progress-panel.tsx`
  - real six-phase timeline, countdown, floor and connection presentation.
- `apps/web/src/features/sessions/session-notice-layer.tsx`
  - notice priority and live-region rendering.

Small component-specific tests may either live beside each component or be
grouped in `discussion-workspace.test.tsx` when one test file can exercise a
meaningful composition boundary. Do not create one test file per trivial
wrapper.

### Browser composition review

- `apps/web/e2e/session-composition.spec.ts` (new) or a clearly isolated
  section of existing `apps/web/e2e/session.spec.ts`
  - deterministic visual/browser review at `1440x900`, `1024x768` and
    `390x844`;
  - verify desktop three columns, tablet discussion priority and mobile tabs;
  - capture wide and narrow screenshots for human visual review;
  - use existing deterministic/fake infrastructure and zero real provider
    calls;
  - do not claim F4 Human→AI cross-layer authority acceptance.

### Explicitly unchanged future files/domains

Unless a later actual-source review proves a contradiction and separately
approves it, F3B implementation must not modify:

- `apps/web/src/lib/realtime/client.ts` or its semantics;
- `apps/web/src/lib/realtime/contract.ts`;
- `apps/web/src/lib/realtime/projection.ts`;
- `apps/web/src/features/sessions/discussion-transcript.ts` merge semantics;
- `apps/web/src/lib/api/client.ts` or generated REST schema;
- backend production/tests, DB models/migrations or REST/WS contracts;
- dependency manifests/lockfiles, CI, provider/config/prompt or infrastructure;
- P2 voice, P3 scoring/reporting or F4 composition E2E authority.

If implementation proves a change in one of these authorities is necessary,
stop and request separate review rather than silently expanding F3B.

## Frozen executable acceptance matrix

### A. Authority preservation

- existing F3A contract, realtime client, projection and transcript unit tests
  remain semantically unchanged and passing;
- `SessionPanel` is the only feature coordinator;
- presentation children make zero API/WS client instances and zero
  authoritative refetches;
- no Redux/Zustand/global discussion store or frontend business state machine;
- draft, pending, rejected and confirmed transcript remain distinct;
- click-time exact floor binding, one pending command and recovery behavior are
  preserved.

### B. Desktop composition

- at `1440x900`, the loaded session shows one compact header and simultaneous
  left/center/right regions;
- at every viewport `>=1200`, center remains the largest region;
- transcript is independently scrollable without moving the composer out of
  reach;
- left/right overflow does not expand the whole page into the old long column;
- no primary UUID, sequence or ISO-deadline debug rows are visible.

### C. Participant presentation

- a standard current snapshot renders exactly one Human and three AI
  candidates in authoritative seat order;
- current floor is visually and textually identifiable;
- every AI identity is explicitly labeled AI;
- non-current participants are neutral;
- AI waiting uses only the exact current grant and matching confirmed
  utterance absence;
- private Persona/strategy/emotion/sentiment data never renders;
- no fake waveform or photoreal participant tile.

### D. Task Brief and notes

- title, scenario, objective, hard constraints and present options render from
  public Question data as plain text;
- absent options/constraints do not create fake content;
- hidden/private Question fields and answer hints are absent;
- notes remain usable across responsive tab/sheet switching in one mounted
  workspace;
- reload creates an empty notes field;
- localStorage/sessionStorage and network requests contain no notes text;
- UI explicitly avoids a persistence/autosave claim.

### E. Progress and timing

- all six authoritative phases appear in exact order and exact Chinese
  mapping;
- active phase is identifiable without color alone;
- countdown uses current `server_now` + elapsed display time against
  `phase_deadline_at` and never advances state;
- no fixed per-phase duration is rendered without authoritative data;
- current floor owner and safe no-floor/intervention copy use public facts;
- no consensus, vote or conclusion is rendered.

### F. Responsive behavior

- `>=1200`: full three-column studio;
- `768–1199`: Discussion remains primary and support regions use compact
  access without three-column squeeze;
- `<768`: exact `讨论 / 题目 / 进程` tabs, default `讨论`;
- tabs are keyboard accessible with correct semantics and visible focus;
- composer is reachable in Discussion mode;
- switching views causes no extra snapshot/transcript fetch or realtime
  connection and creates no duplicate notes/transcript authority.

### G. Lifecycle UX

Component/browser tests define presentation for:

- no session/Question selection;
- `CREATED`;
- `PREPARATION`;
- each of the five speaking phases;
- Human floor;
- AI floor;
- no-floor/intervention transition;
- Human pending;
- rejected Human draft with newer draft preserved;
- reconnect/recovery with transcript preserved;
- AI interruption;
- `COMPLETED`;
- `ABORTED_USER`;
- missing historical Question binding;
- narrow viewport.

No test may satisfy a missing state by inventing unsupported business behavior.

### H. Privacy and persistence

- DOM/screenshot/public copy contains no provider, model, config, prompt,
  Private Stance, Persona label, internal action/reason code or hidden score;
- primary UI contains no session/Question Version UUID or sequence counter;
- browser storage contains no F3A authority, draft, pending, transcript, notes,
  tab or support-panel state;
- confirmed transcript remains exact plain text with whitespace preserved;
- AI identities remain visibly synthetic.

### I. F3A regression and scope

- complete existing Web Vitest suite remains passing;
- current Chromium session contract remains passing and is not weakened;
- no backend, schema, migration, REST/WS, generated schema, dependency,
  lockfile, CI, provider/config or infrastructure delta;
- no real provider call;
- F4 Human→AI composition semantics remain separately unclaimed.

### J. Visual/product review

- deterministic browser screenshots are captured at representative wide and
  narrow viewports, with tablet behavior inspected separately;
- review checks hierarchy, center priority, transcript readability, composer
  reachability, non-dashboard density, focus/contrast and absence of clipping;
- review checks no chat-bubble, Zoom, cyberpunk, fake analytics or sparse
  prototype drift;
- review verifies visible copy and state claims against actual public facts;
- screenshot artifacts are review evidence only and are not committed unless
  a later implementation plan explicitly authorizes stable baselines.

## Later implementation validation gates

After separate implementation approval, risk-appropriate gates are:

- focused presentation-helper and component tests first;
- complete existing F3A Web tests;
- Prettier check, ESLint and TypeScript typecheck;
- Web production build;
- current live OpenAPI drift check without generated manual edits;
- existing Chromium session contract;
- deterministic F3B wide/tablet/narrow composition review;
- browser-storage and private-sentinel negative checks;
- exact changed-file/domain scope inspection;
- Master Plan SHA-256 and `git diff --check`;
- staged count zero before review.

F3B implementation validation does not use a real provider and does not claim
F4 complete Human→AI cross-layer acceptance.

## Stop conditions for later implementation

Stop before expanding implementation if F3B requires:

- backend, DB, migration, REST/WS or generated contract change;
- realtime-client or transcript-merge semantic change;
- another authoritative fetch/client/store path;
- Redux, Zustand or an app-global discussion authority;
- a new UI/component/icon dependency;
- browser persistence of notes, draft, pending, transcript or session truth;
- fake pause, vote, conclusion, report, score, voice or AI lifecycle facts;
- private Persona/provider/prompt/internal-action data in presentation;
- a participant or phase fact not present in public snapshot/contracts;
- modification of provider/config, CI or F4 authority;
- a fourth responsive band or duplicated mobile component authority.

If actual implementation disproves current source sufficiency, record the
exact contradiction and stop for separate scope review.

## Requirement-to-section coverage audit

All approved requirements are mapped:

- commercial C-end intent and exclusions → Product intent, Visual system;
- desktop three columns and header → Overall composition, Header, Desktop IA;
- public Question and local notes → Left region;
- Human + three AI and safe status → Participant strip;
- professional confirmed transcript → Confirmed transcript;
- sticky unchanged composer semantics → Sticky Human composer;
- real six-phase timing/progress → Right region;
- connection/recovery/AI interruption → Realtime and notice hierarchy;
- three responsive bands → Responsive architecture;
- coordinator and presentation children → Component architecture;
- full lifecycle list → Lifecycle and state presentation;
- P2/P3/later seams without fake UI → Commercial-forward compatibility;
- visual/accessibility system → Visual system, Accessibility;
- executable future proof → Acceptance matrix and validation gates;
- bounded Web-only implementation map → Proposed file map;
- explicit unchanged authorities and stop rules → File map and stop conditions.

Coverage gaps: none.

## Contradiction and design self-review

Reviewed against the Master Plan, Accepted Decisions, current roadmap/tasks,
parent P1-5 plan, both F3A plans, current `SessionPanel`, realtime
client/projection/contracts, transcript/API client, generated REST types and
relevant Web tests.

Results:

- no Master Plan or Accepted ADR change is required;
- no F3A realtime/transcript/pending/recovery semantic is reopened;
- all visible facts exist in current public REST/WS/snapshot data or are
  explicitly local presentation state;
- current source supports one Human plus three AI, six phases, authoritative
  timing, floor, transcript and connection presentation;
- private notes are local-memory-only and cannot become hidden persistence;
- no unsupported pause, voice, report, conclusion or voting behavior appears;
- desktop, tablet and mobile reuse one authority and one component set;
- proposed component boundaries reduce `SessionPanel` markup without moving
  coordinator authority or creating speculative framework layers;
- the app-shell adjustment is necessary to remove the committed `max-w-3xl`
  constraint and is still a bounded Web presentation change;
- P2/P3 extension seams are structural only and add no inactive fake controls;
- ROADMAP status synchronization changes current-state markers only;
- no implementation, dependency, schema, backend or F4 scope is authorized;
- no stop condition is triggered.

The design document is complete, self-reviewed and externally reviewed. Its
current-source TDD implementation plan is also frozen. A later separately
approved implementation turn completed all three batches and final code gates
without changing this frozen design. Actual-source implementation review,
commit/push, CI and F4 composition acceptance subsequently passed with no open
findings, so F3B is `DONE` with all frozen evidence tokens satisfied.

## Historical docs-only validation contract

The design-freeze turn required only:

- exact four-file changed scope;
- relative Markdown links and final newlines;
- status/terminology consistency;
- requirement coverage and contradiction audits;
- immutable Master Plan SHA-256;
- proof of no production/test/generated/schema/migration/dependency/CI diff;
- `git diff --check`;
- staged count zero;
- review bundle generation after self-review PASS.

No Web/API/browser/provider test suite or real provider call was required for
that historical design-freeze turn.

## Progress

- Clean baseline and authority recovery: completed.
- Actual source/types/tests sufficiency inspection: completed.
- Complete composition design: documented.
- Requirement coverage audit: `PASS`.
- Internal contradiction audit: `PASS`.
- F3B design actual-source review: `PASS`; findings: `NONE`.
- F3B implementation-plan actual-source review: initial `BLOCKED` on
  `F3B-IP-001` and `F3B-IP-002`; both findings `CLOSED` by finding-only
  remediation.
- F3B remediated implementation-plan self-review: `PASS`; open findings:
  `NONE`.
- F3B status: `DONE`; `DESIGN_FROZEN / IMPLEMENTATION_PLAN_FROZEN /
  IMPLEMENTATION_COMPLETE / ACTUAL_SOURCE_IMPLEMENTATION_REVIEW_PASS /
  COMMIT_PUSH_COMPLETE / CI_PASS / F4_COMPOSITION_ACCEPTANCE_PASS /
  FINDINGS_NONE_OPEN`.
- F3B implementation baseline: `5efe1346532b95b7fabdd521015fd9f8199a457f`;
  actual-source implementation review `PASS`; GitHub Actions run `33044682226`
  `SUCCESS`.
- Batch 3 final implementation gates: focused Vitest `48/48` and full Vitest
  `178/178`,
  typecheck, lint, format, production build, live OpenAPI drift and Chromium
  `2/2` all `PASS`; Master Plan SHA-256 unchanged; staged count `0`.
- Responsive Browser evidence uses one created session at `1440x900`,
  `900x900` and `390x844`; notes survive responsive switching, clear on reload
  and never enter browser storage; authority reads/WebSocket do not multiply.
- F4: `DONE`; initial acceptance `BLOCKED` on `F4-ACC-001`; finding-only
  remediation actual-source review `PASS`; accepted commit
  `af33d89baa0355ae1ee5174a2ef8cfb5e7b14554`; CI run `33050532295` `SUCCESS`;
  independent final acceptance `PASS`; findings `NONE`; `F4-ACC-001 CLOSED`;
  network-free fake-provider composition only; no real provider/model call.
- Stage/commit/push authorization: none.
