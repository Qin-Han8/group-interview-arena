# P1-6 Complete Text Simulation Execution Plan

- Status: `P1-6 IN_PROGRESS`
- Current checkpoint: `P1-6A DONE / DESIGN_SCOPE_FROZEN / ACTUAL_SOURCE_REVIEW_PASS`
- Finding-only external actual-source re-review verdict: `PASS`
- Reviewed bundle: `group-interview-arena-review-20260830-044406.zip`
- Reviewed bundle SHA-256: `6137E75B1E671A561D6280901680A7445C66F5EDBB34D456142F092492473E4D`
- Findings: `P16A-REV-001 CLOSED`; `P16A-REV-002 CLOSED`; new findings `NONE`; open findings `NONE`
- Remaining checkpoints: `P1-6B NOT_STARTED`; `P1-6C NOT_STARTED`; `P1-6D NOT_STARTED`; `P1-6E NOT_STARTED`
- Parent phase: `P1 IN_PROGRESS`
- Product target: `V0.1 Internal Validation`
- Authority: [`PROJECT_MASTER_PLAN.md`](../PROJECT_MASTER_PLAN.md) > Accepted [`DECISIONS.md`](../DECISIONS.md) > [`ROADMAP.md`](../ROADMAP.md) > [`TASKS.md`](../TASKS.md) > this plan > domain docs > code
- Immutable master-plan SHA-256: `2388A9660320406CB35D5354126AD71C6849A98DB7C4A356796CA951BF372F26`

## 1. Goal and checkpoint boundary

P1-6 completes the V0.1 text-simulation boundary without reopening capabilities already accepted in P1-1～P1-5. P1-6A is a strict docs-only reconciliation and architecture/scope freeze. It establishes the actual committed capability baseline, the evidence → memory → bounded invocation context → future report layering, forward-safe seams for P2/P1-7, the exact P1-6B～P1-6E split and the minimum governance transition from P1-5 `DONE` to P1-6 `IN_PROGRESS`.

P1-6A creates no production code, test, schema, migration, API, WebSocket, Web, provider, prompt, dependency, CI or infrastructure change. It does not modify [`PROJECT_MASTER_PLAN.md`](../PROJECT_MASTER_PLAN.md), reopen P1-5 acceptance, run an independent review or authorize P1-6B implementation.

## 2. Source-grounded current baseline

The reconciliation uses committed `main` and the existing P1-5 accepted state. No P1-1～P1-4 historical plan was reopened.

| Boundary | Current committed source fact | Freeze consequence |
|---|---|---|
| Session/lifecycle authority | `SimulationSession` owns status, timing and current floor pointer; P1-3 owns transitions. | Memory, AI, Web and future voice remain consumers. |
| Floor/scheduler authority | `FloorGrant`/`FloorRelease` and the deterministic scheduler own speaker selection/release. | AI Runtime decides content only; memory never selects the next speaker. |
| Authoritative public history | Ordered `DiscussionEvent` `participant.utterance.created` facts are the durable Human/AI transcript source. | Memory derives from public facts and never replaces them. |
| AI provenance | `PromptVersion`, `LlmGenerationRequest` and `AiUtterance` preserve prompt/provider/model/configuration/request/grant relations. | Memory/evaluation versions extend alongside stable identities. |
| Authorized AI context | Runtime joins the exact Question Version and only the granted AI's Assignment/Persona/Private Stance; recent discussion comes from public events. | Shared memory contains public facts only. |
| Current bounded context | At most 6 public utterances and 4000 content code points are rendered as exact recent text. | This is a bounded raw window, not memory or a derived summary. |
| Public REST/realtime | REST owns snapshot/transcript; WS owns versioned commands/events; AI completion atomically writes `COMPLETED + AiUtterance + public event`. | P1-6B must not break the public contract. |
| Web composition | Web loads snapshot + paginated transcript, connects after the watermark and merges REST/WS by `utterance_id`/sequence. | Web cannot depend on a memory table or DB representation. |
| Recovery evidence | Existing network-free coverage proves phase completion, reload/reconnect, API restart, generation failure recovery and transcript restoration. | P1-6D composes, not reimplements, these paths. |
| Memory/report state | No structured-memory projection/version/cursor/stale/rebuild implementation or report/evidence generation exists. | Memory is P1-6B; report/evidence remains P1-7. |

Primary actual-source evidence:

- [`db/models.py`](../../apps/api/src/group_interview_arena_api/db/models.py)
- [`ai_runtime/conversation_context.py`](../../apps/api/src/group_interview_arena_api/modules/ai_runtime/conversation_context.py)
- [`ai_runtime/runtime.py`](../../apps/api/src/group_interview_arena_api/modules/ai_runtime/runtime.py)
- [`ai_runtime/service.py`](../../apps/api/src/group_interview_arena_api/modules/ai_runtime/service.py)
- [`discussion_sessions/utterances.py`](../../apps/api/src/group_interview_arena_api/modules/discussion_sessions/utterances.py)
- [`discussion_sessions/public_events.py`](../../apps/api/src/group_interview_arena_api/modules/discussion_sessions/public_events.py)
- [`discussion_sessions/progression.py`](../../apps/api/src/group_interview_arena_api/modules/discussion_sessions/progression.py)
- [`floor_control/scheduler.py`](../../apps/api/src/group_interview_arena_api/modules/floor_control/scheduler.py)
- [`session-panel.tsx`](../../apps/web/src/features/sessions/session-panel.tsx)
- [`discussion-transcript.ts`](../../apps/web/src/features/sessions/discussion-transcript.ts)
- [`session.spec.ts`](../../apps/web/e2e/session.spec.ts)

## 3. Original P1 route reconciliation

Status here describes capability coverage against the original route; it does not rewrite an earlier task's accepted governance status.

| Route item | Original owner | Current committed evidence | Status | Future owner | Notes |
|---|---|---|---|---|---|
| P1-1 契约与第一条 vertical slice | P1-1 | Session REST/WS, ordered events, action idempotency and reconnect foundation. | COMPLETE | none | Accepted evidence inherited. |
| P1-2 题目与角色系统 | P1-2 | Immutable Question Version, Persona Template, Assignment/Private Stance and exact 1 Human + 3 AI roster. | COMPLETE | none | Private data remains non-public. |
| P1-3 会话状态机 | P1-3 | Server-owned phase path, deadlines, reconciliation and `COMPLETED` closure. | COMPLETE | none | Lifecycle authority is not reassigned. |
| P1-4 发言权调度 | P1-4 | Deterministic floor decisions, grants/releases, fairness and recovery. | COMPLETE | none | Speaker authority is not reassigned. |
| P1-5 讨论记忆与 AI Provider | P1-5 | Provider/runtime/orchestration/transport/Web are complete; recent public raw context exists; structured memory was deferred. | PARTIAL | P1-6B for the carried gap | P1-5 remains governance `DONE`; it is not reopened. |
| P1-6 完整文字模拟 | P1-6 | Major transport/Web/recovery/phase capabilities were completed earlier; structured memory and one explicit full Human + 3 AI composed acceptance remain. | PARTIAL | P1-6B～P1-6E | Precompleted capabilities are validation inputs, not implementation tasks. |
| P1-7 基础报告与 V0.1 内容 | P1-7 | No report/evidence implementation is present. | GAP | P1-7 | Remains `NOT_STARTED`; not part of P1-6. |
| P1-8 P1 独立验收 | P1-8 | No full-P1 independent acceptance has run. | GAP | P1-8 | Remains `NOT_STARTED`; P1-6E is narrower. |

## 4. Detailed capability reconciliation matrix

| Capability | Original owner | Current committed evidence | Status | Future owner | Notes |
|---|---|---|---|---|---|
| Provider abstraction/runtime | P1-5 | Project-owned provider-neutral input/result boundary and runtime orchestration. | COMPLETE | none | Business/domain code does not depend on vendor SDK types. |
| Fake provider | P1-5 | Network-free deterministic/fake provider composition gates. | COMPLETE | P1-6D uses it | Do not rebuild. |
| Real provider adapter | P1-5 | Thin Zhipu HTTPX adapter with lazy server configuration and safe error normalization. | COMPLETE | later provider evolution | No routing/fallback in P1-6. |
| AI utterance generation | P1-5 | Exact grant-bound request → completion → `AiUtterance` + public event. | COMPLETE | none | At most one final utterance per request/grant. |
| Automatic AI orchestration | P1-5 | State-driven deterministic generate/release/schedule loop with restart recovery. | COMPLETE | none | P1-3/P1-4 authorities remain unchanged. |
| Structured discussion memory | P1-5 | No model, service or projection exists. | GAP | P1-6B | Carried forward without reopening P1-5. |
| Bounded context summary | P1-5 | At most 6/4000-code-point recent public raw utterances are rendered; no structured/derived summary exists. | PARTIAL | P1-6B | Preserve strict budgets; close raw-window-only dependence. |
| Public Human utterance | P1-5F | WS submit, exact Human floor authorization, atomic utterance + release, durable public event. | COMPLETE | none | Accepted v1 contract remains. |
| Public AI utterance | P1-5F | Atomic generation completion + `AiUtterance` + public event. | COMPLETE | none | Generation internals remain private. |
| REST session/transcript surface | P1-1/P1-5F | Owner-only snapshot and paginated sequence-cursor transcript. | COMPLETE | none | Memory is not added to snapshot by default. |
| Realtime delivery/recovery | P1-1/P1-5F | Versioned WS, catch-up, gap recovery, stable action identity and commit-before-send. | COMPLETE | P1-6D validates | Do not redesign. |
| Web discussion page | P1-5F | Contract-driven question/discussion/process composition and confirmed transcript UX. | COMPLETE | P1-6D validates | No P1-6 redesign. |
| Human + 3 AI composition | P1-2/P1-5 | Exact roster plus automatic Human→AI/AI→AI composition exists. | PRECOMPLETED_BY_EARLIER_PHASE | P1-6D validates all seats in one path | Not an implementation task. |
| Reload/reconnect/API restart behavior | P1-3/P1-4/P1-5R | Durable phase/transcript recovery and cancellation/re-entry coverage exists. | PRECOMPLETED_BY_EARLIER_PHASE | P1-6D composes | Reuse recovery mechanisms. |
| Full-session start → final-summary closure | P1-3/P1-5R | Chromium observes PREPARATION through FINAL_SUMMARY to COMPLETED. | PRECOMPLETED_BY_EARLIER_PHASE | P1-6D composes with memory/3 AI | No new lifecycle states. |
| Report/evidence generation | P1-7 | No implementation exists. | GAP | P1-7 | Explicitly excluded from P1-6. |

## 5. Frozen architecture principles

### 5.1 Discussion Core independence

Session, phase, floor, utterance/event and memory are project-owned core capabilities. They cannot depend on Web, a specific LLM provider or a future voice transport. P2 ASR/TTS may enter only as input/output adapters around the same authoritative session/floor/evidence boundaries; it must not require a rewrite of session, scheduler, memory or report core.

### 5.2 Evidence → Memory → Report layering

```text
authoritative raw public utterance/discussion events
  -> derived versioned structured discussion memory
  -> bounded AI invocation context / future evidence extraction
  -> future evaluation/report presentation
```

- Raw public history is the evidence authority.
- Structured memory is a derived projection, never a substitute for evidence.
- A report is a versioned presentation/evaluation result, never discussion truth.
- Private Persona/Private Stance, user-private notes, system configuration and provider credentials never enter shared memory.

### 5.3 Structured Memory conceptual contract

P1-6B must implement a rebuildable projection with, at minimum:

- stable `session_id`;
- monotonic memory `revision`/version;
- source cursor and source utterance/event provenance;
- memory schema version and derivation/algorithm version;
- generated/updated timestamp;
- stale/current determination against authoritative source sequence;
- public-only proposals, criteria, agreements, open conflicts, discarded options and current decision.

P1-6A creates no schema/table. P1-6B must choose the smallest additive persistence/domain shape with a current caller. Rebuild from authoritative public history is required in principle; deletion/recreation of historical training data is not.

The deterministic state mechanics are distinct from semantic derivation. P1-6B must make all of the following deterministic:

- source event/utterance ordering;
- source cursor advancement;
- memory revision allocation;
- stale/current detection;
- idempotent consumption/re-entry;
- provenance association;
- structural fields derivable without semantic inference.

Semantic derivation—including proposal semantic merge, agreement/conflict interpretation and concise semantic summary—may later use a project-owned semantic derivation boundary/LLM. Such derivation must be bounded, public-only, versioned, source-provenance-traceable, derivation-version-traceable and safely replayable/rebuildable as a new memory revision. A deterministic fake/test provider may provide stable test behavior; a real external LLM is not required to reproduce word-for-word or bit-for-bit identical output during rebuild. If semantic derivation is persisted, the design must retain an additive seam for sufficient provenance such as derivation, prompt, model and config versions. Authoritative raw public history remains the only evidence authority; semantic memory never substitutes for raw evidence.

### 5.4 AI remains non-authoritative

P1-3 owns phase/lifecycle. P1-4 owns floor/speaker. AI Runtime owns only allowed generated content. Provider output cannot directly own phase, floor, score, database mutation or next-speaker decisions. Memory derivation likewise cannot mutate those authorities.

### 5.5 Provider neutrality and stable identity

Business/domain consumers depend on project-owned provider-neutral contracts. Existing Question Version, Persona Assignment/Private Stance, Prompt Version and generation provenance are sufficient stable seams for additive Memory Version and later Evaluation/Report Version. P1-6 adds no provider registry, routing or fallback framework.

### 5.6 Privacy boundary

The boundaries are: public discussion context; participant-private Persona/Private Stance; user-private data/notes; and system/provider configuration/credentials. Shared memory is constructed only from allowlisted public discussion facts. Current-participant Private Stance may inform that participant's generation, but cannot be persisted into or inferred as a fact in shared memory. Cross-seat private context remains forbidden.

### 5.7 Stable API/realtime boundary

Web consumes generated REST types and versioned realtime contracts, not ORM/database shapes. Memory may change internal storage and derivation without requiring Web transcript/realtime rewrites. Any future public memory projection requires a separately frozen additive contract and real consumer; P1-6A adds none.

### 5.8 Migration safety

P1-6B persistence evolution is additive-first and uses stable session/event identities. Historical question, participant, prompt, generation and transcript facts remain readable. No destructive migration, event rewrite, table drop/recreate assumption or data backfill that fabricates evidence is allowed.

### 5.9 Forward-safe without speculative infrastructure

The boundaries should survive larger volume and replaceable implementations, while P1-6 excludes Redis, Kafka, Celery/generic workers, vector DB/embeddings/RAG, LangGraph, microservices, distributed locks, plugin frameworks, billing/payment/subscription, tenant systems, model registry/routing/fallback and Kubernetes-specific architecture. A later real trigger may reopen the appropriate Accepted ADR; absence of these systems is not a risk by itself.

Every later P1-6 design must answer: (1) if usage grows 10×, does the boundary still hold; (2) if the implementation is replaced, do consumers remain substantially unchanged; and (3) is it implementing a future system with no current need. The target is YES, YES and NO respectively.

## 6. Architecture risk matrix

| Risk ID | Current source fact | Why it matters later | Severity | P1-6 action | Deferred evolution seam |
|---|---|---|---|---|---|
| P16-R01 | No structured-memory projection, version, source cursor, stale check or rebuild path exists. | Long discussions and future reports would otherwise depend on ad hoc context and duplicate derivation. | BLOCKER | P1-6B implements the smallest versioned, traceable, rebuildable public-memory projection. | Derivation may later move behind the same projection contract. |
| P16-R02 | AI context uses only the latest 6 public utterances within 4000 code points; it is raw text, not a semantic summary. | Earlier criteria, commitments and conflicts can fall out of context. | BLOCKER | P1-6B produces bounded memory-backed invocation context with strict budgets. | Budget/model policy stays replaceable without changing evidence. |
| P16-R03 | `DiscussionEvent` is the only durable Human transcript fact; AI also has internal `AiUtterance`. | Future event compaction could destroy user-visible evidence. | IMPORTANT | Freeze no-compaction/no-deletion through P1-6. | Add an equivalent durable transcript read model before retention changes. |
| P16-R04 | Generation provenance is versioned, but memory has no schema/algorithm version or source provenance. | A changed derivation could silently reinterpret historical memory/evidence. | IMPORTANT | P1-6B stores explicit source and derivation versions/provenance; persisted semantic derivation leaves an additive seam for derivation/prompt/model/config versions. | Re-derivation writes a new revision; it never silently overwrites provenance. |
| P16-R05 | Runtime loads public transcript separately and joins only the granted participant's Private Stance. | Shared-memory work could leak private strategy across seats. | IMPORTANT | P1-6B public-only allowlist and privacy sentinels are mandatory. | Participant-local generation context stays separate. |
| P16-R06 | Web restores through project-owned snapshot/transcript/WS contracts and stable identity. | Coupling Web to memory storage would cause public contract churn. | ACCEPTABLE | Keep current contract unchanged. | A future public memory view is separately versioned. |
| P16-R07 | P1-3 lifecycle, P1-4 floor and P1-5 content authorities are separated and durable. | Voice, memory or provider evolution must not add a second authority. | ACCEPTABLE | Preserve ownership; add adapters/projections only. | P2 ASR/TTS attach around the same core. |
| P16-R08 | Tests prove recovery/closure properties but do not explicitly assert one memory-enabled run where all 3 distinct AI seats participate. | Separate green paths can miss complete-composition defects. | IMPORTANT | P1-6D adds one network-free Human + 3 distinct AI proof with recovery/failure checkpoints. | Reuse it as a future voice-adapter regression. |
| P16-R09 | Stable session ID and ordered public-event sequence support an additive memory projection without contract changes. | Destructive migration is unnecessary and endangers evidence. | ACCEPTABLE | P1-6B remains additive-first. | Later backfill/rebuild is separately governed. |
| P16-R10 | Report/evidence generation is absent and P1-7-owned. | Pulling it into P1-6 would blur facts, memory and presentation. | ACCEPTABLE | Keep report/evaluation out of P1-6. | P1-7 consumes evidence + versioned memory without becoming truth authority. |

No current Critical commercial/evolution blocker requires a new ADR or master-plan change. The two `BLOCKER` rows block P1-6 completion until P1-6B closes them; they do not block this P1-6A freeze.

## 7. Frozen P1-6B～P1-6E split

### P1-6B — Structured Discussion Memory Gap Closure

Goal: close the carried P1-5 memory gap with a public-only, versioned, traceable, stale-detectable, rebuildable structured-memory projection and bounded memory-backed invocation context.

Allowed after separate approval: minimal memory domain/persistence/application code, additive migration if required, AI context integration, targeted privacy/version/rebuild tests and directly affected docs.

Required acceptance:

- authoritative raw events remain unchanged and rebuildable;
- exact source cursor/provenance, revision, schema/algorithm version and timestamps exist;
- source ordering, cursor advancement, revision allocation, stale/current detection, idempotent consumption/re-entry, provenance association and inference-free structural fields are deterministic;
- semantic derivation is bounded, public-only, versioned, source- and derivation-version-traceable, safely replayable/rebuildable as a new memory revision and stable-testable through a deterministic fake/test provider; rebuild does not require a real external LLM to reproduce identical words or bits;
- only public facts enter shared memory; no Private Stance, prompt, credential or user-private note leaks;
- bounded AI context stays within explicit budgets and does not require the whole transcript;
- P1-3/P1-4/P1-5 and REST/WS contracts remain compatible;
- migration is additive and downgrade/upgrade/data-integrity gates pass.

Deferred: report/evaluation, public memory API/UI, voice, RAG/embeddings/vector store, background workers, multi-provider routing/fallback and speculative infrastructure.

### P1-6C — Full Text Simulation Composition

Goal: connect existing session/lifecycle, scheduler, provider-neutral AI runtime, public transport/Web composition and P1-6B memory into the complete text-simulation path.

This is integration work only. It cannot redo or rename P1-5F REST/WS/Web contracts, rebuild provider/runtime/orchestration, create a second scheduler/lifecycle authority or introduce report logic. If P1-6B is naturally consumed by the existing path, P1-6C may be a minimal caller/wiring change plus targeted regression rather than a new subsystem.

Allowed after separate approval: only the existing application composition/caller seams, directly affected tests and docs; no new public contract or infrastructure domain.

Required acceptance: current components consume the memory seam through project-owned interfaces; Human/AI public facts remain authoritative; failures preserve floor/session integrity; no precompleted capability is duplicated.

### P1-6D — Recovery + Three-AI End-to-End Validation

Goal: prove one complete network-free Human + 3 distinct AI discussion from start through `FINAL_SUMMARY`/`COMPLETED`, using P1-6B memory and existing public contracts.

The scenario must include:

- all three AI seat identities participating with private-context isolation;
- public Human/AI transcript convergence;
- reload/reconnect and API restart recovery;
- one generation failure/cancellation and continued scheduling without duplicate provider work, utterance or release;
- phase progression through final-summary closure;
- durable transcript and memory restoration/rebuild/stale checks;
- no real provider quota, secret, rendered prompt or verbatim sensitive output in evidence.

This checkpoint validates precompleted recovery/Web/transport capabilities; it does not reimplement them.

Allowed after separate approval: network-free integration/E2E fixtures, targeted acceptance assertions and directly affected docs; production behavior changes require a separately identified defect and scope review.

### P1-6E — P1-6 Independent Acceptance + Closeout

Goal: independently review committed P1-6 implementation/evidence against this plan, then close P1-6 only if findings are resolved and gates pass. It excludes P1-7 report/content and P1-8 full-P1 acceptance. P1 remains `IN_PROGRESS` after P1-6 closeout.

Allowed after separate approval: read-only committed-source review, required acceptance reruns and governance closeout after findings are resolved; no implementation mutation during the independent review.

## 8. Stop conditions for later checkpoints

Stop and request review if later work proves that:

1. a conflicting structured-memory implementation already exists;
2. P1-6B requires breaking accepted REST/realtime contracts;
3. persistence cannot evolve additively;
4. shared/public context leaks Private Stance or user-private data;
5. P1-6 must reassign P1-3 lifecycle or P1-4 floor authority;
6. a new product decision/ADR or master-plan modification is required;
7. raw authoritative evidence cannot remain available/rebuildable;
8. a Critical commercial/evolution blocker cannot be resolved inside P1-6.

## 9. P1-6A actual-source review and closeout gate

The finding-only external actual-source re-review verdict is `PASS` against reviewed bundle `group-interview-arena-review-20260830-044406.zip` / SHA-256 `6137E75B1E671A561D6280901680A7445C66F5EDBB34D456142F092492473E4D`. `P16A-REV-001 CLOSED`; `P16A-REV-002 CLOSED`; new findings `NONE`; open findings `NONE`. The current checkpoint is therefore `DONE / DESIGN_SCOPE_FROZEN / ACTUAL_SOURCE_REVIEW_PASS`. Independent review was not run for this closeout.

P1-6A closeout satisfies the following frozen gate:

- this is the only new P1-6 architecture/scope/implementation-plan document;
- only this plan, [`TASKS.md`](../TASKS.md) and [`ROADMAP.md`](../ROADMAP.md) change;
- P1-5 remains `DONE`; P1/P1-6 are `IN_PROGRESS`; P1-6A has passed external actual-source review; P1-6B～E and P1-7/P1-8 are `NOT_STARTED`;
- `PROJECT_MASTER_PLAN.md` is byte-identical to the recorded SHA-256;
- no code/schema/migration/API/Web/provider/prompt/dependency/CI/infrastructure change exists;
- `git diff --check`, document links/status checks, `git diff --stat` and `git status --short` pass;
- the default workflow is `$gia-phase-runner` → if a real diff exists, `$gia-review-bundle` → external actual-source review → finding-only remediation if needed → finding-only re-review → only then `DONE` and any separately authorized commit/push;
- `$gia-phase-runner` and `$gia-review-bundle` may run in the same Codex conversation, while `$gia-review-bundle` itself must not modify, stage or commit source;
- no independent review is required by this gate.
