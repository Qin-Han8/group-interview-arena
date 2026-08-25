# P1-5F-2 Backend Text Discussion Transport — Implementation Plan

> Execution aid only. The approved design authority remains
> [`P1-5_ai-runtime-foundation.md`](P1-5_ai-runtime-foundation.md), especially
> the frozen P1-5F-1 sections. This document decomposes that design into TDD
> implementation tasks; it does not amend the contract or authorize P1-5F-3.

## Goal

Implement the backend-only P1-5F-2 vertical slice on the approved clean
baseline:

```text
authenticated Human WebSocket utterance
  -> atomic durable Human utterance + exact floor release
  -> deterministic recoverable scheduler checkpoint
  -> existing configured continuous AI drive when AI owns the floor
  -> atomic durable AI utterance + public utterance event
  -> ordered/recoverable public WebSocket projection
  -> owner-only sequence-cursor transcript REST read model
```

The finished implementation must preserve historical floor-event v1 exactly,
write new floor facts as additive v2, retain internal `SessionAction` causation,
and expose only the frozen public action semantics. It must make no real model
call in automated validation.

## Baseline and planning gate

- Repository: `Qin-Han8/group-interview-arena`
- Branch: `main`
- Required and observed `HEAD`: `a66a9416d1117e95819b0a42627a5a65cbd1940d`
- Required and observed `origin/main`: `a66a9416d1117e95819b0a42627a5a65cbd1940d`
- Observed subject: `P1-5F-1: docs: freeze realtime public discussion contract`
- Initial working tree: clean; staged count: `0`
- `docs/PROJECT_MASTER_PLAN.md` SHA-256:
  `2388a9660320406cb35d5354126ad71c6849a98db7c4a356796ca951bf372f26`
- User-authorized workflow state for this gate: P1, P1-5, and P1-5F remain
  `IN_PROGRESS`; P1-5F-1 is `DONE`; P1-5F-2 advanced from its recorded
  planning gate to `IN_PROGRESS — implementation review candidate` after
  external plan review `PASS WITH REQUIRED AMENDMENTS`; P1-5F-3 and P1-5F-4
  remain `NOT_STARTED`.
- The implementation turn was separately approved. It does not authorize
  stage, commit, push, real-provider calls, or P1-5F-3.

## Context and authoritative constraints

Read before execution:

- `AGENTS.md`
- `docs/PROJECT_MASTER_PLAN.md`
- `docs/DECISIONS.md`, especially ADR-006, ADR-007, ADR-008, ADR-009,
  ADR-011, ADR-012, ADR-013, ADR-014, and ADR-015
- `docs/TASKS.md`
- `docs/ROADMAP.md`
- The complete frozen P1-5F-1 sections in:
  - `docs/exec-plans/P1-5_ai-runtime-foundation.md`
  - `docs/API.md`
  - `docs/ARCHITECTURE.md`
  - `docs/DATABASE.md`
  - `docs/AGENT_BEHAVIOR.md`
  - `docs/PRIVACY_AND_SAFETY.md`

The implementation must keep these boundaries exact:

- Narrow F1 erratum restored during F2 actual-source review:
  `participant.utterance.submit` is a closed v1 WebSocket command whose client
  payload contains exactly `floor_grant_id: UUID4` and `content: string`.
- Authority comes only from the authenticated owner, the owned session, and
  the locked authoritative current Human candidate grant; the payload floor
  ID must equal that exact current grant and cannot bind implicitly to a later
  grant.
- Human content is 1–4000 Python/Unicode code points, must have a non-empty
  `strip()` result, must not contain U+0000, and is persisted without trimming
  or normalization.
- Content-rule and authority rejections of a syntactically valid command are
  recoverable `UTTERANCE_REJECTED` errors with the exact message
  `You cannot submit an utterance right now.`; malformed envelopes retain the
  closing `PROTOCOL_ERROR` behavior.
- `participant.utterance.created` remains v1 and has exactly the six frozen
  payload fields. Human public action is the original client action; AI public
  action is null.
- Historical floor-event v1 remains parseable and retains its existing action
  rules. New floor facts are persisted as v2; public v2 action is the Human
  submit action only for the directly caused Human release and is null for
  internal scheduling, automatic release, and intervention.
- Human utterance event N and its exact `SPEAKER_FINISHED` release N+1 commit
  in one aggregate-lock transaction. Scheduling is a later committed
  checkpoint.
- AI `COMPLETED`, `AiUtterance`, the AI public event, and sequence advancement
  commit atomically. Failures create no utterance event.
- REST transcript pagination filters the full discussion sequence; transcript
  sequences can be non-contiguous.
- All WebSocket delivery is commit-before-send and uses the same public
  projection for live delivery and reconnect.
- No schema migration, Human utterance table, orchestration table, Redis,
  queue, pub/sub, multi-worker broadcast, handwritten Web client work, or F3
  UI is included.

## Actual-source assessment and stop-condition result

No planning stop condition is present at the baseline:

1. `SimulationSession` already supplies the aggregate row lock and authoritative
   `last_sequence`; `SessionParticipant.user_id`, `FloorGrant`, and
   `FloorRelease` prove exact Human authority and release in one transaction.
2. `DiscussionEvent.causation_action_id` is nullable and references the private
   durable `SessionAction`. A server projection can resolve the causation
   command type and independently choose the public envelope action. No column
   or migration is needed.
3. `complete_generation_request(...)` already locks the session and generation
   request while committing `COMPLETED + AiUtterance`; it can append the event
   and advance the same aggregate sequence in that transaction.
4. A committed Human checkpoint can be proven from the accepted
   `participant.utterance.submit` action, its v1 utterance event, the exact
   `SPEAKER_FINISHED` release and v2 release event, the released grant and Human
   participant, plus the deterministic schedule action/decision/child facts.
   The latest applicable durable `floor.released` formal fact is selected by
   authoritative `DiscussionEvent.sequence`, never by wall-clock release time;
   current-floor and exact fact checks prevent resuming an old, AI, or lifecycle
   release.
5. The scheduler recovery code in `ai_runtime/orchestration.py` is separable
   from provider/generation authority: it accepts deterministic identities,
   invokes the existing Floor Scheduler service, and classifies durable child
   facts. Extracting that part leaves WHO with the scheduler and leaves the
   current RUNNING-generation fail-closed rule intact.
6. FastAPI owns the new REST schema. The generated TypeScript REST artifact can
   be regenerated mechanically without handwritten Web changes.

If execution disproves any statement above, stop before adding schema or
changing authority and return the exact contradiction for approval.

## Proposed architecture and exact interfaces

### 1. Durable event versus public event

Rename the in-memory `StoredEvent.action_id` field to
`StoredEvent.causation_action_id`. This is a Python symbol clarification only;
the database column and persisted values remain unchanged.

Create `discussion_sessions/public_events.py` with:

```python
class PublicEventProjectionError(RuntimeError): ...

def project_public_action_id(
    event: StoredEvent,
    *,
    causation_command_type: str | None,
) -> UUID | None: ...

def project_public_event(
    event: StoredEvent,
    *,
    causation_command_type: str | None,
) -> FormalEventEnvelope: ...

async def project_public_events(
    session: AsyncSession,
    events: Sequence[StoredEvent],
) -> list[FormalEventEnvelope]: ...
```

`project_public_events(...)` performs one batched `SessionAction` lookup for
the non-null causation IDs it needs, then applies these fail-closed rules:

- historical floor v1: preserve the durable causation in the public envelope,
  including the already-nullable v1 release;
- floor v2: expose the causation only when the matching durable action is v1
  `participant.utterance.submit`; otherwise emit null without changing the
  durable fact;
- Human utterance v1: require a matching v1
  `participant.utterance.submit` action and expose it;
- AI utterance v1: require null durable causation and expose null;
- existing session events: preserve their current public action behavior;
- missing, contradictory, unsupported-version, or payload-invalid durable
  data: raise `PublicEventProjectionError`; never guess or leak an internal ID.

Both WebSocket catch-up/live delivery and transcript projection use this
boundary. No live-only serializer remains.

### 2. Contracts

Extend `discussion_sessions/contracts.py` with:

```python
class ParticipantUtteranceSubmitPayload(_ClosedModel):
    floor_grant_id: UUID4
    content: str

class ParticipantUtteranceSubmitCommand(_ClosedModel):
    schema_version: Literal[1]
    type: Literal["participant.utterance.submit"]
    session_id: UUID4
    action_id: UUID4
    payload: ParticipantUtteranceSubmitPayload

type TranscriptActorKind = Literal["HUMAN", "AI"]
type TranscriptPhase = Literal[
    "OPENING_STATEMENTS",
    "EXPLORATION",
    "CONFLICT_AND_EVALUATION",
    "CONVERGENCE",
    "FINAL_SUMMARY",
]

class TranscriptUtteranceResponse(_ClosedModel):
    utterance_id: UUID4
    sequence: int
    occurred_at: datetime
    action_id: UUID4 | None
    participant_id: UUID4
    actor_kind: TranscriptActorKind
    floor_grant_id: UUID4
    phase: TranscriptPhase
    content: str

class TranscriptResponse(_ClosedModel):
    items: list[TranscriptUtteranceResponse]
    next_after_sequence: int | None
```

The Pydantic command checks the closed syntactic shape and string type. The
application validator owns the frozen content rules so semantically invalid
but syntactically valid content maps to recoverable `UTTERANCE_REJECTED`, not a
closing protocol error. `RealtimeSessionCommand` adds the new command.

`FormalEventEnvelope` adds `participant.utterance.created` and validates its
exact key set, UUID4 identities, floor-enabled phase, `HUMAN | AI` actor, string
content, and action semantics. Its floor validation becomes explicitly
versioned: v1 retains the current grant/intervention non-null and release
nullable rules; v2 permits a nullable public action for all three event names
without weakening payload validation.

`RealtimeErrorCode` adds `UTTERANCE_REJECTED`; the safe message is fixed at the
realtime boundary.

### 3. Human utterance application/persistence

Create `discussion_sessions/utterances.py` with focused types and functions:

```python
class UtteranceRejectedError(Exception): ...

@dataclass(frozen=True)
class SubmitHumanUtterance:
    session_id: UUID
    action_id: UUID
    floor_grant_id: UUID
    content: str
    received_at: datetime
    schema_version: int = 1
    command_type: str = "participant.utterance.submit"

@dataclass(frozen=True)
class HumanUtteranceCommit:
    events: tuple[StoredEvent, StoredEvent]
    utterance_id: UUID
    released_floor_grant_id: UUID
    replayed: bool

@dataclass(frozen=True)
class TranscriptItem:
    utterance_id: UUID
    sequence: int
    occurred_at: datetime
    action_id: UUID | None
    participant_id: UUID
    actor_kind: ParticipantActorKind
    floor_grant_id: UUID
    phase: SessionStatus
    content: str

@dataclass(frozen=True)
class TranscriptPage:
    items: tuple[TranscriptItem, ...]
    next_after_sequence: int | None

def validate_human_utterance_content(content: str) -> str: ...
def derive_human_utterance_id(*, session_id: UUID, action_id: UUID) -> UUID: ...
def participant_utterance_created_event(...) -> PendingEvent: ...

async def submit_human_utterance(
    session: AsyncSession,
    *,
    owner_id: UUID,
    command: SubmitHumanUtterance,
) -> HumanUtteranceCommit: ...

async def load_transcript_page(
    session: AsyncSession,
    *,
    owner_id: UUID,
    session_id: UUID,
    after_sequence: int,
    limit: int,
) -> TranscriptPage: ...
```

`derive_human_utterance_id(...)` uses the fixed module namespace
`ca3256d4-e2a5-52d0-9742-a6e6500930f8`, UUID5 input label
`participant-utterance:{session_id}:{action_id}`, and reconstructs the derived
bytes with `version=4`, matching the repository's deterministic UUID4-compatible
convention. A golden-value unit test freezes the namespace, label, and output
before acceptance.

`SubmitHumanUtterance.received_at` is server-owned and is not part of the
semantic digest. The digest is the canonical sorted JSON of schema version,
type, exact `floor_grant_id`, and exact unmodified content payload. Changing
either floor or content under one action identity is a conflict.

`submit_human_utterance(...)` performs one `session.begin()` transaction. It
uses the existing deferred-domain-error pattern: lifecycle reconciliation rows
are allowed to commit, an authority/content rejection is retained as a pending
safe error, and `UtteranceRejectedError` is raised only after the transaction
closes. An accepted command remains entirely within the same transaction:

1. lock the owner-scoped `SimulationSession` row;
2. if the `SessionAction` exists, compare version/type/digest and strictly
   verify the same deterministic utterance event, exact release row, exact v2
   release event and N/N+1 order; return replay or fail closed;
3. run existing deadline/lifecycle reconciliation and persist its system
   events before authority evaluation;
4. validate content without changing it;
5. require `command.floor_grant_id == aggregate.current_floor_grant_id`, then
   prove that exact named grant is current/unreleased in the exact
   floor-enabled phase and belongs to an available Human candidate with
   `participant.user_id == owner_id`;
6. insert the v1 submit `SessionAction`;
7. append v1 `participant.utterance.created` at N with the deterministic ID;
8. reuse `release_active_floor_for_lifecycle(...)` with
   `SPEAKER_FINISHED` and the same action, thereby inserting `FloorRelease` and
   clearing the current grant;
9. append v2 `floor.released` at N+1, advance `last_sequence` by two, flush,
   and commit;
10. return only after commit through the existing service-call lifecycle.

The operation stores no separate Human row. A content/authority rejection uses
`UtteranceRejectedError`; same action with a different digest uses the existing
`ActionIdConflictError`; accepted-action fact inconsistency uses
`SessionPersistenceError`.

`load_transcript_page(...)` first proves owner visibility, selects only
`participant.utterance.created` after the exclusive cursor in sequence order,
fetches `limit + 1`, projects through `project_public_events(...)`, converts to
storage-independent `TranscriptItem` values, and sets `next_after_sequence` to
the last returned sequence only when the extra row proves another page.

### 4. Additive floor v2 writes

Change the three floor event factories in `floor_control/domain.py` to create
event version 2. This affects only newly appended facts; existing v1 rows are
never rewritten. `floor_control/lifecycle.py` continues to retain the supplied
private `causation_action_id` in `FloorRelease` and receives v2 from the event
factory. The public projection decides whether that durable action is exposed.

### 5. Reusable scheduler checkpoint

Create `floor_control/progression.py` and move the authority-neutral part of
the P1-5E scheduler checkpoint into it:

```python
class SchedulerCheckpointOutcome(StrEnum):
    NEXT_AI_GRANTED = "next_ai_granted"
    NEXT_HUMAN_GRANTED = "next_human_granted"
    NO_GRANT = "no_grant"
    INTERVENTION_REQUESTED = "intervention_requested"
    RECONCILIATION_REQUIRED = "reconciliation_required"
    STATE_CHANGED = "state_changed"

@dataclass(frozen=True)
class SchedulerCheckpointIdentities:
    schedule_action_id: UUID
    decision_id: UUID
    next_floor_grant_id: UUID
    intervention_id: UUID

@dataclass(frozen=True)
class ReleasedFloorProof:
    floor_grant_id: UUID
    release_action_id: UUID
    release_command_type: str
    allowed_reasons: frozenset[FloorReleaseReason]

@dataclass(frozen=True)
class SchedulerCheckpointResult:
    outcome: SchedulerCheckpointOutcome
    processed_floor_grant_id: UUID
    identities: SchedulerCheckpointIdentities
    next_floor_grant_id: UUID | None = None
    next_participant_id: UUID | None = None
    intervention_id: UUID | None = None

async def drive_scheduler_checkpoint(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    owner_id: UUID,
    session_id: UUID,
    released_floor: ReleasedFloorProof,
    identities: SchedulerCheckpointIdentities,
    scheduling_policy: SchedulerPolicy,
) -> SchedulerCheckpointResult: ...
```

The helper owns durable scheduler-result recovery, partial-child detection,
unresolved checkpoint classification, command construction, one call to
`apply_scheduler_command(...)`, and post-call recovery. It does not own
release, participant choice, provider construction, generation, retry, or
continuous-drive policy. The proof validates the exact release row and action
type/reason before scheduling. Scheduler decision remains the only WHO
authority.

`ai_runtime/orchestration.py` keeps all generation/release semantics and the
existing `derive_automatic_turn_identities(...)`. It converts the existing
schedule/decision/grant/intervention fields into
`SchedulerCheckpointIdentities`, calls the extracted helper, and maps its
result back to `SingleAiTurnResult`; the only scheduler-checkpoint call is
`drive_scheduler_checkpoint(...)`. Existing deterministic AI labels and bytes
must not change. The current P1-5E crash-A through crash-F, concurrency,
SUPERSEDED, RUNNING, and provider-call behavior are characterization gates for
the extraction.

Rename the private resumable-AI release lookup to a tested read-only public
query:

```python
async def has_resumable_ai_work(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    owner_id: UUID,
    session_id: UUID,
) -> bool: ...
```

It reuses the existing exact AI request/utterance/failure/release proof and
does not invoke a provider.

### 6. Human post-release progression

Create `discussion_sessions/progression.py` with:

```python
class DiscussionProgressionOutcome(StrEnum):
    NO_WORK = "no_work"
    NEXT_HUMAN_GRANTED = "next_human_granted"
    AI_DRIVE_COMPLETED = "ai_drive_completed"
    NO_GRANT = "no_grant"
    INTERVENTION_REQUESTED = "intervention_requested"
    RECONCILIATION_REQUIRED = "reconciliation_required"
    STATE_CHANGED = "state_changed"

@dataclass(frozen=True)
class DiscussionProgressionResult:
    outcome: DiscussionProgressionOutcome
    released_floor_grant_id: UUID | None = None
    scheduler_result: SchedulerCheckpointResult | None = None
    ai_drive_result: ContinuousAiDriveResult | None = None

def derive_human_scheduler_identities(
    *, session_id: UUID, released_floor_grant_id: UUID
) -> SchedulerCheckpointIdentities: ...

async def resume_discussion_progression(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    owner_id: UUID,
    session_id: UUID,
) -> DiscussionProgressionResult: ...
```

Human scheduler identities use the fixed module namespace
`9b347f1a-48fc-58d1-a1d3-e71e4ee861b4` and the exact labels:

```text
human-post-release:{session_id}:{released_floor_grant_id}:schedule-action
human-post-release:{session_id}:{released_floor_grant_id}:decision
human-post-release:{session_id}:{released_floor_grant_id}:next-floor-grant
human-post-release:{session_id}:{released_floor_grant_id}:intervention
```

Each output is reconstructed as UUID4-compatible bytes and frozen by golden
tests.

Durable Human checkpoint discovery is exact:

- if a current grant exists, classify its participant; only an exact AI grant
  is eligible for configured AI drive;
- with no current grant, inspect the latest applicable durable
  `floor.released` fact ordered by `DiscussionEvent.sequence DESC`; use its
  payload grant identity to prove the matching `FloorRelease`; wall-clock
  `released_at` may be checked only for consistency and never selects the
  chronological winner;
- require `SPEAKER_FINISHED`, a Human grant owned by the authenticated user,
  release causation equal to a v1 `participant.utterance.submit` action, a
  digest matching the preserved content, exact N v1 utterance and N+1 v2
  release facts, and the deterministic Human utterance ID;
- derive the one schedule identity set and classify absent, complete, or
  inconsistent schedule action/decision/child facts;
- absent invokes `drive_scheduler_checkpoint(...)`; complete returns its
  durable result; inconsistent returns reconciliation required;
- a completed Human checkpoint is never reminted. `NEXT_HUMAN_GRANTED`, no
  grant, and intervention stop without provider construction;
- `NEXT_AI_GRANTED` calls only `drive_configured_ai_session(...)` after every
  scheduler transaction has committed;
- if no Human checkpoint exists but the current grant is AI or
  `has_resumable_ai_work(...)` proves the existing P1-5E post-release case,
  invoke the same configured drive;
- old Human releases, later completed progression, automatic AI releases,
  `PHASE_CHANGED`, and `SESSION_TERMINATED` never become Human checkpoints;
- a durable RUNNING request may be inspected by the existing drive but must
  return fail-closed without a second provider call.

No database transaction or row lock remains open across
`drive_configured_ai_session(...)` or a provider call.

### 7. AI public-event atomicity

Extend `ai_runtime/service.py` with private strict helpers that load and verify
the one `AiUtterance` and matching v1 `participant.utterance.created` event for
a completed request. On fresh completion, while the current aggregate and
request are locked:

1. retain current live-context and timestamp validation;
2. set request `COMPLETED`;
3. insert `AiUtterance`;
4. append the v1 public event using `AiUtterance.id`, request participant/grant,
   grant phase, exact content, and null `causation_action_id`;
5. increment `SimulationSession.last_sequence` once;
6. flush and commit all facts together.

One shared private service helper proves the exact consistent
`COMPLETED request + AiUtterance + participant.utterance.created v1` triple.
Every service path capable of returning a completed snapshot—at minimum
`create_generation_request(...)`, `claim_generation_request(...)`, and
`complete_generation_request(...)` replay—must use it and verify exact event
version/type/action/payload/sequence identity. Missing, duplicate, or
conflicting public facts raise `GenerationRequestConflictError` and surface as
the existing safe reconciliation/request-conflict path.
`ai_runtime/runtime.py` needs no new provider behavior: its existing catch of
that conflict remains authoritative. Failure/stale paths append no utterance
event.

### 8. Ordered WebSocket transport

Refactor `discussion_sessions/realtime.py` around one connection-local ordered
drain:

```python
async def drain_committed_events() -> None: ...
async def kick_progression_best_effort() -> None: ...
```

`drain_committed_events()` is the only formal-event sender. Under one send
lock it loads all durable events after `sent_sequence`, projects them in one DB
read through `project_public_events(...)`, closes the DB unit of work, sends in
strict sequence order, and advances the watermark only after each successful
send. Initial catch-up, command completion, and the periodic catch-up loop all
use it. Remove the separate direct-command sender.

The command loop:

1. parses the new command without accepting authority fields;
2. retains exact `PROTOCOL_ERROR` close behavior for malformed data and session
   mismatch;
3. calls `submit_human_utterance(...)` with server time for the Human command;
4. maps `UtteranceRejectedError` to recoverable `UTTERANCE_REJECTED` and
   continues;
5. retains recoverable `ACTION_ID_CONFLICT` behavior;
6. after the Human transaction returns committed, awaits
   `drain_committed_events()` so N/N+1 are sent before progression can produce
   later sequences;
7. starts a bounded best-effort progression kick guarded by one
   connection-local task/lock; progression never sends directly;
8. lets the same ordered drain deliver all later scheduler/AI events.

After initial reconnect catch-up, a best-effort kick calls
`resume_discussion_progression(...)`. Multiple connections/tasks may race, but
the deterministic durable actions and generation claims converge. Disconnect
or send failure never re-enters the mutation and never changes committed truth.
Operational logs record safe IDs/outcomes/sequences only, never `content`,
provider payloads, prompts, private stance, secrets, Authorization, or raw
errors.

The connection-local progression task catches `AiDriveCompositionError`, every
safe no-work/budget/state-changed/reconciliation terminal result, cancellation,
and unexpected exceptions. Expected stops are allowlisted metadata-only logs;
unexpected exceptions use a generic category without raw exception text. None
of these closes an otherwise healthy socket, fabricates an utterance or
`INTERRUPTED` release, chooses a speaker, retries a RUNNING request, or creates a
new public AI-runtime event/error. Reconnect may re-enter durable truth later,
and no task exception is left unobserved.

### 9. Transcript REST

Add `GET /sessions/{session_id}/utterances` to the existing session router:

```python
async def utterances(
    session_id: UUID4,
    user: CurrentUserDependency,
    session_factory: DatabaseSessionFactory,
    after_sequence: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
) -> TranscriptResponse: ...
```

It has authentication, no CSRF dependency/openapi extension, owner/missing
404 non-disclosure, safe 422/500 responses, ASC sequence ordering, and no
snapshot embedding. The response conversion consumes `TranscriptPage`, not
SQLAlchemy rows, so the public API is not permanently coupled to
`DiscussionEvent` storage.

## Exact file map

### Create during implementation

- `apps/api/src/group_interview_arena_api/modules/discussion_sessions/public_events.py`
  — one live/history public event projection and causation redaction boundary.
- `apps/api/src/group_interview_arena_api/modules/discussion_sessions/utterances.py`
  — content policy, Human atomic persistence, utterance event construction,
  replay proof, and transcript read model.
- `apps/api/src/group_interview_arena_api/modules/discussion_sessions/progression.py`
  — exact Human checkpoint discovery and configured AI-drive invocation.
- `apps/api/src/group_interview_arena_api/modules/floor_control/progression.py`
  — reusable authority-neutral scheduler checkpoint recovery/drive.
- `apps/api/tests/test_discussion_public_events.py` — pure public action and
  fail-closed projection tests.
- `apps/api/tests/integration/test_discussion_utterances.py` — Human atomicity,
  idempotency, concurrency, rollback, and transcript-storage tests.
- `apps/api/tests/integration/test_discussion_progression.py` — Human scheduler
  identity, crash/re-entry, outcome, concurrency, and E3-invocation tests.
- `apps/api/tests/integration/test_backend_text_discussion_transport.py` —
  composed network-free Human→scheduler→AI→release progression, recovery,
  ordering, and privacy regression.

### Modify during implementation

- `apps/api/src/group_interview_arena_api/modules/discussion_sessions/contracts.py`
  — command, error, strict utterance/floor envelopes, and transcript REST models.
- `apps/api/src/group_interview_arena_api/modules/discussion_sessions/domain.py`
  — rename in-memory stored private causation field only.
- `apps/api/src/group_interview_arena_api/modules/discussion_sessions/service.py`
  — carry the renamed private causation field through existing event loads.
- `apps/api/src/group_interview_arena_api/modules/discussion_sessions/realtime.py`
  — command dispatch, safe business error, ordered committed drain, and
  best-effort progression kick.
- `apps/api/src/group_interview_arena_api/modules/discussion_sessions/routes.py`
  — owner-only transcript route and storage-independent response conversion.
- `apps/api/src/group_interview_arena_api/modules/floor_control/domain.py`
  — new floor event version 2.
- `apps/api/src/group_interview_arena_api/modules/floor_control/service.py`
  — carry renamed private causation and retain internal scheduler/action facts.
- `apps/api/src/group_interview_arena_api/modules/ai_runtime/service.py`
  — atomic AI public event append and strict completed replay proof.
- `apps/api/src/group_interview_arena_api/modules/ai_runtime/orchestration.py`
  — use generic scheduler checkpoint and expose read-only resumable-AI proof.
- `apps/api/tests/test_discussion_session_contracts.py`
  — exact submit/utterance/error contracts and semantic content routing.
- `apps/api/tests/test_discussion_session_routes.py`
  — OpenAPI auth/query/response/no-CSRF transcript contract.
- `apps/api/tests/test_floor_control_contracts.py`
  — historical v1 plus additive v2 action combinations and invalid pairs.
- `apps/api/tests/test_floor_control_domain.py`
  — new floor event factories emit v2 without payload drift.
- `apps/api/tests/integration/test_discussion_session_api.py`
  — transcript HTTP pagination, isolation, errors, and non-contiguous sequence.
- `apps/api/tests/integration/test_discussion_session_websocket.py`
  — Human command, errors, ordering, projection parity, reconnect, and send loss.
- `apps/api/tests/integration/test_floor_control_foundation.py`
  — new v2 persistence assertions while durable action causation remains exact.
- `apps/api/tests/integration/test_ai_runtime_persistence.py`
  — atomic event/replay/conflict/failure/privacy persistence assertions.
- `apps/api/tests/integration/test_ai_runtime_orchestration.py`
  — runtime conflict/privacy/no-extra-provider regression.
- `apps/api/tests/integration/test_ai_runtime_automatic_orchestration.py`
  — scheduler extraction and crash-A–F behavior-preservation regression.
- `apps/api/tests/integration/test_ai_runtime_continuous_drive.py`
  — continuous AI chain, replay, concurrency, and RUNNING fail-closed regression.
- `apps/web/src/lib/api/generated/schema.d.ts`
  — mechanically regenerated FastAPI REST contract only.
- `docs/TASKS.md` and `docs/ROADMAP.md`
  — F2 execution/review evidence while P1/P1-5/P1-5F stay in progress and
  F3/F4 stay not started.
- `docs/API.md`, `docs/ARCHITECTURE.md`, `docs/DATABASE.md`,
  `docs/AGENT_BEHAVIOR.md`, and `docs/PRIVACY_AND_SAFETY.md`
  — change “frozen, not implemented” implementation-state language and record
  verified behavior without changing the approved contract.
- `docs/exec-plans/P1-5_ai-runtime-foundation.md`
  — implementation/validation/review evidence only; frozen design text remains
  unchanged.
- `docs/exec-plans/P1-5F-2_backend-text-discussion-transport.md`
  — factual progress and command evidence as tasks execute.
- `docs/RELEASE_CHECKLIST.md`
  — validation evidence for the eventual review candidate.

### Explicitly unchanged

- `docs/PROJECT_MASTER_PLAN.md`
- `docs/DECISIONS.md` unless execution discovers an actual contradiction and
  stops for approval; none is known at planning time
- `apps/api/src/group_interview_arena_api/db/models.py`
- all Alembic migration files
- `apps/api/src/group_interview_arena_api/app.py`
- `apps/api/src/group_interview_arena_api/core/errors.py`
- `apps/api/src/group_interview_arena_api/modules/floor_control/lifecycle.py`
- `apps/api/src/group_interview_arena_api/modules/floor_control/scheduler.py`
- `apps/api/src/group_interview_arena_api/modules/ai_runtime/runtime.py`
- `apps/api/src/group_interview_arena_api/modules/ai_runtime/continuous.py`
- `apps/api/src/group_interview_arena_api/modules/ai_runtime/composition.py`
- all handwritten files under `apps/web/src` other than the generated REST
  schema artifact
- dependency manifests, lockfiles, CI, Docker/infra, prompts, seeds, provider
  configuration, and Browser/Playwright tests

If execution requires changing an item in this unchanged list for correctness,
stop and re-review scope before modifying it.

## Implementation tasks and TDD order

All commands below run from `apps/api` unless a task explicitly says repository
root. Every behavior task starts with a meaningful failing test, records the
expected failure, implements only enough to pass, reruns the focused command,
then refactors while the same command remains green. Provider doubles are
network-free.

### Task 1 — Freeze executable command, event, error, and floor v1/v2 contracts

**Files:** modify `contracts.py`, `test_discussion_session_contracts.py`,
`test_floor_control_contracts.py`.

1. RED: add tests proving the closed submit envelope, rejected authority fields,
   string-only content, preserved raw whitespace, syntactically valid semantic
   content failures, exact v1 utterance payload/action rules, exact safe error,
   historical floor v1 rules, v2 nullable action rules, and rejection of every
   invalid version/action/payload combination.
2. Verify RED:

   ```powershell
   uv run pytest tests/test_discussion_session_contracts.py tests/test_floor_control_contracts.py -q
   ```

   Expected: missing command/event/error support and v2 floor rejection.
3. GREEN: add the minimal closed Pydantic models and explicitly versioned event
   validators; do not add authority fields or provider/runtime fields.
4. Verify GREEN with the same command.
5. Refactor validator helpers for exact key/type/UUID/phase checks; rerun the
   same command.

### Task 2 — Separate durable causation from public action and switch new floor facts to v2

**Files:** create `public_events.py` and `test_discussion_public_events.py`;
modify discussion `domain.py`/`service.py`, floor `domain.py`/`service.py`,
`test_floor_control_domain.py`, and focused affected tests.

1. RED: add pure projection cases for v1 preservation, Human-direct v2 action,
   automatic v2 null action, AI utterance null action, missing-action fail
   closed, and strict payload failure. Add floor factory expectations for v2.
2. Verify RED:

   ```powershell
   uv run pytest tests/test_discussion_public_events.py tests/test_floor_control_domain.py tests/test_floor_control_contracts.py -q
   ```

   Expected: module missing, stored field still ambiguous, and factories emit
   v1.
3. GREEN: rename only the in-memory `StoredEvent` field, add batched projection,
   and make all new floor factories emit v2 while preserving payloads and
   database causation.
4. Verify GREEN with the same command.
5. Refactor duplicate stored-event adapters without broad service
   restructuring; run:

   ```powershell
   uv run pytest tests/test_discussion_session_domain.py tests/test_floor_control_domain.py tests/test_discussion_public_events.py -q
   ```

### Task 3A — Establish the standing composed acceptance RED

**Files:** create
`integration/test_backend_text_discussion_transport.py` before any Human
production code.

1. RED: add the network-free composed acceptance test for Human durable
   utterance/release, scheduler progression, AI public utterance, existing AI
   release/scheduling, strict ordering, recovery, and privacy.
2. Verify RED:

   ```powershell
   uv run pytest tests/integration/test_backend_text_discussion_transport.py -q
   ```

   Expected: the Human submission/progression production boundary is absent.
   Record this missing-feature failure and keep the test red while Tasks 3–8
   add scoped components.

### Task 3 — Implement atomic Human utterance plus exact release

**Files:** create `utterances.py` and
`integration/test_discussion_utterances.py`; update supporting imports only.

1. RED: add real-PostgreSQL tests for exact owned current Human success, AI/no
   floor/wrong user rejection, stale/deadline-advanced rejection, unmodified
   accepted content, N/N+1 order, single transaction, deterministic UUID,
   exact replay, semantic conflict, concurrent duplicate convergence, and
   injected rollback leaving no action/event/release/watermark change.
2. Verify RED:

   ```powershell
   uv run pytest tests/integration/test_discussion_utterances.py -q
   ```

   Expected: application module/function missing.
3. GREEN: implement the validator, identity helper, strict replay proof, and one
   locked transaction. Reuse lifecycle reconciliation and release; do not call
   the scheduler here.
4. Verify GREEN with the same command.
5. Refactor canonical digest/event construction helpers and rerun both:

   ```powershell
   uv run pytest tests/integration/test_discussion_utterances.py tests/integration/test_discussion_session_persistence.py -q
   ```

### Task 4 — Extract the P1-5E scheduler checkpoint without behavior drift

**Files:** create `floor_control/progression.py`; modify
`ai_runtime/orchestration.py`, automatic orchestration tests, and continuous
drive tests.

1. RED: add tests against the proposed generic checkpoint interface and golden
   assertions that existing AI identity bytes and crash-E/F results stay exact.
2. Verify RED:

   ```powershell
   uv run pytest tests/integration/test_ai_runtime_automatic_orchestration.py tests/integration/test_ai_runtime_continuous_drive.py -q
   ```

   Expected: generic interface missing; all existing characterization cases
   remain green except the new interface cases.
3. GREEN: move durable recovery/classification/drive into the floor application
   helper and adapt `drive_single_ai_turn(...)` without changing generation,
   release, provider, budget, or outcome semantics.
4. Verify GREEN with the same command.
5. Refactor result mapping and expose the read-only resumable-AI proof; rerun:

   ```powershell
   uv run pytest tests/integration/test_ai_runtime_orchestration.py tests/integration/test_ai_runtime_automatic_orchestration.py tests/integration/test_ai_runtime_continuous_drive.py -q
   ```

### Task 5 — Add deterministic Human checkpoint discovery and progression

**Files:** create `discussion_sessions/progression.py` and
`integration/test_discussion_progression.py`; use the Task 4 interfaces.

1. RED: add Human release→schedule tests for deterministic/golden identities,
   crash after release, concurrent re-entry, completed checkpoint replay,
   Human→AI configured-drive invocation once, Human→Human stop, no-grant,
   intervention, old/non-latest/AI/lifecycle release exclusion, current AI
   resume, post-AI-release resume, and RUNNING no-provider-call.
2. Verify RED:

   ```powershell
   uv run pytest tests/integration/test_discussion_progression.py -q
   ```

   Expected: progression module missing.
3. GREEN: implement durable discovery, call the generic scheduler checkpoint,
   and invoke only `drive_configured_ai_session(...)` for proven AI work after
   transactions close. Monkeypatch that composition function in every test.
4. Verify GREEN with the same command and assert zero network activity.
5. Refactor query/proof helpers and run Task 4 and Task 5 suites together.

### Task 6 — Make successful AI completion append its public event atomically

**Files:** modify `ai_runtime/service.py`, AI persistence/orchestration tests,
and affected automatic/continuous-drive expectations.

1. RED: add PostgreSQL tests proving atomic `COMPLETED + AiUtterance + v1
   participant.utterance.created + sequence`, null causation, exact payload,
   completed replay proof, missing/conflicting/duplicate event fail closed,
   injected event failure rollback, stale-context absence, failure absence, and
   privacy sentinels.
2. Verify RED:

   ```powershell
   uv run pytest tests/integration/test_ai_runtime_persistence.py tests/integration/test_ai_runtime_orchestration.py -q
   ```

   Expected: event absent and replay accepts missing event.
3. GREEN: append and verify the event inside the existing locked completion
   transaction; make existing completed-request replay use the same proof.
4. Verify GREEN with the same command.
5. Refactor strict event matching and run:

   ```powershell
   uv run pytest tests/integration/test_ai_runtime_persistence.py tests/integration/test_ai_runtime_orchestration.py tests/integration/test_ai_runtime_automatic_orchestration.py tests/integration/test_ai_runtime_continuous_drive.py -q
   ```

### Task 7 — Implement the owner-only transcript read model and REST route

**Files:** extend `utterances.py`; modify `routes.py`,
`test_discussion_session_routes.py`, `integration/test_discussion_session_api.py`,
and later the generated schema.

1. RED: add tests for only utterance facts, Human/AI action mapping, ASC order,
   exclusive cursor, default 100, maximum 200, invalid query validation,
   non-contiguous sequences, next-cursor lookahead, final null cursor,
   authentication, owner/non-owner/missing 404 parity, no CSRF, exact response
   fields, and absence from the snapshot.
2. Verify RED:

   ```powershell
   uv run pytest tests/test_discussion_session_routes.py tests/integration/test_discussion_session_api.py tests/integration/test_discussion_utterances.py -q
   ```

   Expected: route and response schemas missing.
3. GREEN: implement storage-independent page types, filtered `limit + 1`
   query, public projection, and route conversion.
4. Verify GREEN with the same command.
5. Refactor response conversion without importing ORM models into contracts or
   routes; rerun the same command.

### Task 8 — Integrate Human WebSocket command and one ordered committed drain

**Files:** modify `realtime.py` and
`integration/test_discussion_session_websocket.py`.

1. RED: add tests for authenticated submit, N then N+1, preserved whitespace,
   recoverable content/authority `UTTERANCE_REJECTED`, socket remaining usable,
   recoverable action conflict, automatic floor v2 redaction with durable ID
   retained, historical v1 catch-up, live/reconnect projection equality,
   disconnect after commit, progression/catch-up race ordering, and safe logs.
2. Verify RED:

   ```powershell
   uv run pytest tests/integration/test_discussion_session_websocket.py -q
   ```

   Expected: command unsupported and current floor events still expose stored
   causation directly.
3. GREEN: add command dispatch, map business errors, replace direct sends with
   the ordered drain, and kick best-effort progression only after committed
   Human N/N+1 have drained.
4. Verify GREEN with the same command.
5. Refactor connection-local task cancellation/locking and run:

   ```powershell
   uv run pytest tests/integration/test_discussion_session_websocket.py tests/integration/test_discussion_progression.py -q
   ```

### Task 9 — Cross-path recovery, privacy, and floor regression

**Files:** create
`integration/test_backend_text_discussion_transport.py`; modify
`integration/test_floor_control_foundation.py` and the focused integration
files above; production changes only if a new failing assertion shows a scoped
defect.

1. Task 3A already established the composed vertical-slice RED before Human
   production code. Extend its assertions only when a scoped cross-path gap is
   first observed failing.
2. After Tasks 3–8, run:

   ```powershell
   uv run pytest tests/integration/test_backend_text_discussion_transport.py tests/integration/test_floor_control_foundation.py -q
   ```

3. If any assertion remains red, make
   only the smallest scoped correction at the responsible boundary.
4. Verify GREEN with the same command.
5. Refactor test fixtures only after all Task 3–8 focused suites and this
   acceptance test are green.

### Task 10 — Regenerate and verify the REST OpenAPI artifact

**Files:** mechanically modify only
`apps/web/src/lib/api/generated/schema.d.ts`.

1. Start the API from the repository root without lifespan/DB work:

   ```powershell
   uv run --project apps/api uvicorn group_interview_arena_api.app:app --host 127.0.0.1 --port 8000 --lifespan off
   ```

2. RED drift check in a second repository-root terminal:

   ```powershell
   pnpm.cmd web:api:check
   ```

   Expected: the transcript path/schema is absent from the committed generated
   artifact.
3. GREEN generation and check:

   ```powershell
   pnpm.cmd web:api:generate
   pnpm.cmd web:api:check
   ```

4. Inspect the diff and prove it contains only the new REST path/query/response
   types; make no handwritten Web edit and run no Browser E2E.
5. Stop the local API process.

### Task 11 — Update implementation state and governance evidence

**Files:** modify only the documentation files listed in the exact file map.

1. Update P1-5F-2 from planning gate to implementation evidence, preserving P1,
   P1-5, and P1-5F as `IN_PROGRESS` and P1-5F-3/F4 as `NOT_STARTED`.
2. Replace only stale “not implemented” state text; do not rewrite the approved
   frozen contract or amend ADRs.
3. Record exact tests/checks and honest results. Keep F2 `IN_PROGRESS` pending
   external actual-source review; do not mark `DONE` in the implementation turn.
4. Recheck the master-plan hash and Markdown links/final newlines.

### Task 12 — Run increasing-scope acceptance validation

Run only after all focused tasks are green.

1. Dependency/lock reproducibility from `apps/api`:

   ```powershell
   uv sync --frozen
   uv lock --check
   ```

2. Focused unit and integration suites from Tasks 1–9.
3. Full network-free API unit, integration, and combined regressions:

   ```powershell
   uv run pytest -m "not integration"
   uv run pytest -m integration
   uv run pytest
   ```

4. Static quality:

   ```powershell
   uv run ruff check .
   uv run ruff format --check .
   uv run pyright
   ```

5. Migration proof against the explicitly verified local PostgreSQL target:

   ```powershell
   uv run alembic heads
   uv run alembic current --check-heads
   uv run alembic check
   ```

   Also verify that no migration/model/schema diff exists.
6. Repeat the Task 10 OpenAPI drift check with the DB-independent API process.
7. Repository-root governance/scope checks:

   ```powershell
   Get-FileHash docs/PROJECT_MASTER_PLAN.md -Algorithm SHA256
   git diff --check
   git status --short
   git diff --name-only
   git diff -- apps/api/migrations apps/api/src/group_interview_arena_api/db/models.py docs/PROJECT_MASTER_PLAN.md docs/DECISIONS.md
   git diff -- apps/web/src ':!apps/web/src/lib/api/generated/schema.d.ts'
   git diff --cached --name-only
   ```

8. Search the actual diff for credentials, provider output, prompts/private
   stance, raw errors, utterance-log statements, temporary markers, and
   out-of-scope F3/UI/infra changes. Inspect every match; do not treat a blind
   string count as acceptance.
9. Confirm zero real Zhipu/model calls, zero Browser/Playwright runs, zero
   migration changes, staged count zero, and no commit/push.

### Task 13 — Build the actual-source review bundle and stop

Only after Task 12 passes and the implementation diff has been self-reviewed:

1. Run `$gia-review-bundle` from the repository root.
2. Record the returned ZIP path, SHA-256, included changed-file list, exclusion
   checks, and `git diff --check` result.
3. Keep P1-5F-2 `IN_PROGRESS` through implementation and finding remediation;
   mark it `DONE` only after finding-only external actual-source re-review
   passes. That later gate is now recorded as `PASS` in the closeout evidence.
4. Stop. Do not mark F2 done, start F3, stage, commit, or push.

## Requirement-to-test coverage

- Human command/authority/content/safe rejection: Tasks 1, 3, and 8.
- Unified Human/AI utterance event and privacy allowlist: Tasks 1, 2, 3, 6,
  7, 8, and 9.
- Historical floor v1 plus additive v2/public redaction: Tasks 1, 2, 8, and 9.
- Human N/N+1 atomicity/replay/conflict/concurrency/rollback: Task 3 and Task 9.
- Separate deterministic Human scheduler checkpoint and crash recovery: Tasks
  4, 5, and 9.
- Existing E3 composition, provider-free Human outcomes, and RUNNING
  fail-closed: Tasks 4, 5, 6, and 9.
- AI completion/event atomicity/replay/failure behavior: Task 6 and the P1-5E
  regressions in Tasks 4/9.
- Transcript REST/cursor/owner isolation/storage independence: Task 7 and Task
  10.
- Commit-before-send, strict ordering, reconnect and disconnect recovery: Task
  8 and Task 9.
- Logging/privacy/static leakage: every boundary task plus Task 9 and Task 12.
- No migration/dependency/CI/handwritten Web/F3 expansion: exact file map and
  Task 12 scope diff.

## Decisions fixed by this plan

- The durable column remains `DiscussionEvent.causation_action_id`; only the
  in-memory field is renamed to make its private meaning explicit.
- New floor facts use event version 2. Historical stored v1 facts are projected
  under v1 rules without rewriting.
- Public action redaction uses the durable causation action's command type; no
  public-action column is added.
- `DiscussionEvent` is the Human transcript fact; no Human utterance table is
  added.
- Human content validation is an application business rule after syntactic
  parsing so failures are recoverable.
- Human utterance identity derives from session plus client action; scheduler
  identities derive from session plus the exact released Human grant.
- Generic scheduler checkpoint code receives proof and identities; it does not
  own generation/provider logic.
- Only the existing `drive_configured_ai_session(...)` composition can start
  configured AI progression.
- One durable ordered drain owns all formal-event sends on a connection.
- Transcript responses are storage-independent application values projected
  from current durable events.

## Risks and controls

- **Public/private causation confusion:** explicit field rename, batched command
  lookup, version-specific projection, live/reconnect parity tests.
- **Sequence race:** aggregate locks allocate sequences; one send lock and one
  durable drain prevent per-connection reorder.
- **False Human checkpoint recovery:** latest-release, Human ownership, action
  digest, exact event pair, reason, current-floor, and deterministic child proof.
- **P1-5E regression:** extract only scheduler checkpoint mechanics and run all
  automatic/continuous crash and concurrency suites before Human progression.
- **Duplicate paid work:** existing request claim and RUNNING fail-closed rule
  remain unchanged; tests monkeypatch provider composition and count calls.
- **AI transcript hole:** completion and event share one transaction; every
  completed replay verifies the event.
- **Projection corruption:** mismatch fails closed instead of synthesizing or
  leaking a public event.
- **OpenAPI drift:** regenerate only from FastAPI and run `web:api:check`.
- **Scope expansion:** explicit unchanged list, master hash, migration/model/
  handwritten-Web diffs, staged count, and review-bundle inspection.

## Self-review gates before execution approval

The plan is ready for external review only when all of these are true:

- every frozen P1-5F-1 F2 rule maps to at least one task and test;
- every production behavior begins with a meaningful failing test and exact
  RED/GREEN command;
- generic checkpoint types line up across floor, AI, and Human callers;
- Human semantic digest excludes server receipt time but includes exact floor
  identity and original content exactly;
- replay proofs distinguish semantic drift from durable inconsistency;
- all DB transactions close before provider invocation and WebSocket send;
- public action projection is identical for live and reconnect;
- v1/v2 floor action combinations remain explicit and non-overlapping;
- transcript cursor uses full discussion sequence and lookahead pagination;
- generated REST schema is the only allowed Web source modification;
- no temporary marker, ambiguous optional production file, schema change, real
  provider command, Browser E2E, commit, push, or F3 step remains.

## Validation state

- Mandatory governance, frozen contract, listed source, listed tests, database
  models, app/error boundaries, generated schema, package scripts, README
  commands, and CI drift commands were inspected at the required baseline.
- Planning stop conditions: none.
- Production implementation changes: reviewed backend-only P1-5F-2 implementation;
  no schema/migration/dependency/lock/CI/handwritten-Web delta.
- Initial external actual-source review identified exactly three findings:
  restore exact Human floor binding (including candidate role), narrow the
  transcript public enums, and normalize public projection/periodic catch-up
  failures. All three are remediated; the F1 change is recorded as a narrow
  erratum only. Finding-only external re-review returned `PASS` with findings
  none against `group-interview-arena-review-20260825-150754.zip` / SHA-256
  `b9553cbe488707d5fd87598b70e48e1fabdf55a0ae6d3dab367b830267d61edd`;
  all three findings are closed and P1-5F-2 is `DONE`.
- Final validation evidence: `uv sync --frozen` and `uv lock --check` passed;
  the pre-review focused acceptance passed `145` tests; finding-remediation
  focused regression passed `77` tests and final directly affected regression
  passed `45`; unit passed `438`; integration passed `140`; full pytest passed
  `578` with two local pytest-cache warnings; projection taxonomy passed `12`
  and periodic projection/send catch-up proof passed `2`; Ruff lint and format
  checks passed; Pyright reported zero errors and warnings; Alembic reported
  the single `f1a15b15c005` head/current revision and no new upgrade
  operations; `pnpm.cmd web:api:check` passed against the regenerated REST
  contract whose transcript aliases are exactly `HUMAN | AI` and the five
  floor-enabled phases.
- Governance evidence: changed Markdown relative links and final newlines
  passed; the master-plan SHA-256 remains exact; protected schema, migration,
  model, master-plan, decisions, dependencies, lockfiles, CI, and handwritten
  Web diffs are empty; `git diff --check` passed and staged count is zero.
- Automated provider calls: zero; all provider behavior remains injected and
  network-free.
- Real provider calls: zero.
- Reviewed remediation bundle:
  `group-interview-arena-review-20260825-150754.zip`; SHA-256
  `b9553cbe488707d5fd87598b70e48e1fabdf55a0ae6d3dab367b830267d61edd`.
- Finding-only external actual-source re-review: `PASS`; findings: none.
- Closeout status: P1-5F-2 `DONE`; P1/P1-5/P1-5F remain `IN_PROGRESS`;
  P1-5F-3/P1-5F-4 remain `NOT_STARTED`.

## Progress

- Completed: baseline verification, amended TDD plan gate, Tasks 1～13,
  backend-only implementation, mechanical REST OpenAPI generation, full
  validation, governance evidence, scope/privacy review, three-finding
  remediation, finding-only external re-review, and P1-5F-2 closeout.
- In progress: none within P1-5F-2.
- Not started: P1-5F-3 and P1-5F-4.
