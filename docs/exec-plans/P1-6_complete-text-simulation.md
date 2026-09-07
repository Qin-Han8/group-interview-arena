# P1-6 Complete Text Simulation Execution Plan

- Status: `P1-6 IN_PROGRESS`
- Previous checkpoint: `P1-6D D2-D4 final integration PASS`
- Current checkpoint: `P1-6D DONE / DESIGN_SCOPE_FROZEN / IMPLEMENTATION_COMPLETE / ACTUAL_SOURCE_REVIEW_PASS`
- P1-6D initial external actual-source review verdict: `BLOCKED`
- P1-6D initial reviewed bundle: `group-interview-arena-review-20260831-004302.zip`
- P1-6D initial reviewed bundle SHA-256: `7CE39C1EB4DE8314DCE7DB1CDE9809EB386E0E0CADDED8620D11B47FDB1791D0`
- P1-6D finding-only external actual-source re-review verdict: `PASS`
- P1-6D finding-only reviewed bundle: `group-interview-arena-review-20260831-005931.zip`
- P1-6D finding-only reviewed bundle SHA-256: `502D21B84410EDD606C806C188FFFF1FAF6C8E8ACE3F08381B86E9FA13E29A66`
- P1-6D findings: `P16D-REV-001 CLOSED`; `P16D-REV-002 CLOSED`; `P16D-D2D4-REV-001 CLOSED`; new findings `NONE`; open findings `NONE`
- P1-6D production implementation: `DONE / DESIGN_SCOPE_FROZEN / IMPLEMENTATION_COMPLETE / ACTUAL_SOURCE_REVIEW_PASS`
- P1-6D final acceptance: D2-D1/D2-D2A/D2-D2B/D2-D3/D2-D4 `PASS`; accepted commit `6dcce5e961d6aa7b460243dbd6407e17c2478aa2`; CI `GREEN`
- P1-6C production implementation: `DONE / DESIGN_SCOPE_FROZEN / IMPLEMENTATION_COMPLETE / ACTUAL_SOURCE_REVIEW_PASS`
- P1-6C Design Freeze external actual-source review verdict: `PASS`
- P1-6C Design Freeze reviewed bundle: `group-interview-arena-review-20260830-170659.zip`
- P1-6C Design Freeze reviewed bundle SHA-256: `D4364CA666D715EA7932B3FC525D6D154EC18F8F4AC3D3989F40C19AE683B398`
- P1-6C design-review findings: `NONE`; new findings `NONE`; open findings `NONE`
- P1-6C production implementation external actual-source review verdict: `PASS`
- P1-6C production implementation reviewed bundle: `group-interview-arena-review-20260830-235324.zip`
- P1-6C production implementation reviewed bundle SHA-256: `1E1FBE37255E294AEA76A4E4CC68E49490556C804BE77804731F78CF56EB944B`
- P1-6C implementation findings: `NONE`; new findings `NONE`; open findings `NONE`; production wiring gap `NONE`; production source changes `NONE`
- P1-6A finding-only external actual-source re-review verdict: `PASS`
- P1-6A reviewed bundle: `group-interview-arena-review-20260830-044406.zip`
- P1-6A reviewed bundle SHA-256: `6137E75B1E671A561D6280901680A7445C66F5EDBB34D456142F092492473E4D`
- P1-6A findings: `P16A-REV-001 CLOSED`; `P16A-REV-002 CLOSED`; new findings `NONE`; open findings `NONE`
- P1-6B finding-only external actual-source re-review verdict: `PASS`
- P1-6B finding-only re-review bundle: `group-interview-arena-review-20260830-062133.zip`
- P1-6B finding-only re-review bundle SHA-256: `C10F2A9362EB6102C6C3F23D7BA66234FECC098BDE2A394D5A2738EBB97E701D`
- P1-6B findings: `P16B-REV-001 CLOSED`; `P16B-REV-002 CLOSED`; `P16B-REV-003 CLOSED`; new findings `NONE`; open findings `NONE`
- P1-6B implementation external actual-source review verdict: `PASS`
- P1-6B implementation reviewed bundle: `group-interview-arena-review-20260830-150847.zip`
- P1-6B implementation reviewed bundle SHA-256: `0EAA4B3FEE82F4D8A82D5098CECFDA1BF04F9161B7A63E7F7779B2512D9347F6`
- P1-6B implementation findings: `P16B-IMP-001 CLOSED`; `P16B-IMP-002 CLOSED`; `P16B-IMP-003 CLOSED`; `P16B-IMP-004 CLOSED`; `P16B-IMP-005 CLOSED`; `P16B-IMP-006 CLOSED`; `P16B-IMP-007 CLOSED`; new findings `NONE`; open findings `NONE`
- P1-6D design-time production wiring gap: `NONE`; design-time STOP conditions: `NONE`; production source changes: `NONE`
- Remaining checkpoint: `P1-6E NOT_STARTED`
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
- at the P1-6A closeout checkpoint, P1-5 remained `DONE`, P1/P1-6 remained `IN_PROGRESS`, P1-6A had passed external actual-source review, and P1-6B～E plus P1-7/P1-8 were `NOT_STARTED`;
- `PROJECT_MASTER_PLAN.md` is byte-identical to the recorded SHA-256;
- no code/schema/migration/API/Web/provider/prompt/dependency/CI/infrastructure change exists;
- `git diff --check`, document links/status checks, `git diff --stat` and `git status --short` pass;
- the default workflow is `$gia-phase-runner` → if a real diff exists, `$gia-review-bundle` → external actual-source review → finding-only remediation if needed → finding-only re-review → only then `DONE` and any separately authorized commit/push;
- `$gia-phase-runner` and `$gia-review-bundle` may run in the same Codex conversation, while `$gia-review-bundle` itself must not modify, stage or commit source;
- no independent review is required by this gate.

## 10. P1-6B Design Freeze

### 10.1 Checkpoint and actual-source calibration

P1-6B Design Freeze is `DONE / DESIGN_SCOPE_FROZEN / ACTUAL_SOURCE_REVIEW_PASS`. The finding-only external actual-source re-review verdict is `PASS` against `group-interview-arena-review-20260830-062133.zip` / SHA-256 `C10F2A9362EB6102C6C3F23D7BA66234FECC098BDE2A394D5A2738EBB97E701D`; `P16B-REV-001 CLOSED`; `P16B-REV-002 CLOSED`; `P16B-REV-003 CLOSED`; new findings `NONE`; open findings `NONE`. The separately approved production implementation is now `DONE / DESIGN_SCOPE_FROZEN / IMPLEMENTATION_COMPLETE / ACTUAL_SOURCE_REVIEW_PASS`; implementation finding-only actual-source re-review verdict is `PASS` against `group-interview-arena-review-20260830-150847.zip` / SHA-256 `0EAA4B3FEE82F4D8A82D5098CECFDA1BF04F9161B7A63E7F7779B2512D9347F6`; `P16B-IMP-001`, `P16B-IMP-002`, `P16B-IMP-003`, `P16B-IMP-004`, `P16B-IMP-005`, `P16B-IMP-006`, `P16B-IMP-007` are `CLOSED`; new findings `NONE`; open findings `NONE`. At that P1-6B closeout checkpoint, P1-6C～P1-6E were `NOT_STARTED`. No independent review was run.

The approved architecture is **Evidence Ledger + Materialized Memory + Patch Journal + Lazy Semantic Compaction**. Current source calibrates it as follows:

| Seam | Actual-source fact | Frozen consequence |
|---|---|---|
| Migration | The linear Alembic head is `f1a15b15c005`; current migrations use explicit PostgreSQL constraints, UUID identities, JSONB and downgrade paths. | P1-6B implementation may add one migration after this head and exactly two memory persistence responsibilities; no destructive rewrite or fabricated backfill. |
| Evidence | `DiscussionEvent` is keyed by `(session_id, sequence)`; `participant.utterance.created` v1 stores participant, actor kind, floor grant, phase and content. | Real ordered public utterance events are the only semantic evidence input and remain unchanged. |
| Public projection | `project_public_events` validates version/actor/action exposure before transcript/runtime consumption. | Memory input reuses the safe public projection semantics rather than reading private runtime state or trusting raw model claims. |
| Cursor | Session sequence also contains non-utterance events. | `source_through_sequence` is a `DiscussionEvent.sequence` cursor through the last covered eligible public utterance; current/stale means whether a later eligible public utterance exists, not whether `SimulationSession.last_sequence` changed for unrelated floor/lifecycle events. |
| Current AI context | Runtime loads public utterances newest-first and retains at most 6 utterances / 4000 content code points. | P1-6B replaces raw-window-only dependence with memory plus an uncovered raw tail while preserving explicit budgets. |
| Privacy | `AuthorizedGenerationContext` joins only the current AI participant's `PersonaPrivateStance`; public discussion is loaded separately. | `MemoryDerivationInput` is a separate public-only type and never reuses candidate-authorized private context. |
| Question context | `QuestionVersion` contains candidate-visible fields alongside evaluator/hidden/reference fields; existing `AuthorizedQuestionContext` already demonstrates an explicit public subset. | Memory uses a dedicated `PublicMemoryQuestionContext` allowlist equal to or narrower than that public subset; it never accepts an ORM row or generic dump. |
| Prompt versioning | `PromptVersion` already provides immutable `prompt_key`, `version_number`, `purpose_code`, content digest and publish/retire chronology. | Reuse this table for a new semantic-memory prompt; never create `MemoryPromptVersion` or mutate published candidate V2. |
| Generation context provenance | `GenerationRequestMetadata` V1 and its DB constraint allow exactly `schema_version` plus `configuration_version`; `request_digest` proves input integrity but does not expose reconstructable memory/raw-tail boundaries. | Preserve readable V1 rows and add a closed V2 metadata shape for memory-backed candidate context provenance in the existing generation request persistence. |
| Provider transport | `GenerationProvider`/`ZhipuGenerationProvider` currently accept candidate-specific `RuntimeGenerationInput`, although vendor transport uses only rendered prompt and provider/model/config plus fixed invocation options. | The second real workload justifies a minimal project-owned model-invocation transport refinement during implementation so candidate and memory callers do not duplicate vendor HTTP; candidate generation lifecycle/persistence remains unchanged. |
| Public surface | Memory has no current REST/WS/Web consumer and existing transcript/recovery contracts already expose authoritative facts. | P1-6B adds no public Memory REST API, WebSocket event or Web UI. |

No approved architecture deviation is required. The provider transport calibration is the explicitly allowed minimal refinement with two real callers; it is not a provider registry, router, fallback framework or generic agent runtime.

### 10.2 Architecture flow and authority boundaries

```text
authoritative public DiscussionEvent ledger
  -> ordered public episode batch
  -> public-only MemoryDerivationInput
  -> MemoryDeriver proposes typed MemoryPatch[] only
  -> strict parser + provenance/policy validation
  -> project-owned deterministic reducer
  -> current discussion_memory_states + append-only discussion_memory_revisions
  -> current structured memory + uncompacted recent public tail
  -> bounded DiscussionWorkingContext
  -> candidate-local prompt composition / future Report / future Scoring
```

The new project-owned module boundary is `discussion_memory`, separate from `ai_runtime`:

```text
discussion events / public evidence
  -> discussion_memory
  -> DiscussionWorkingContext
  -> ai_runtime
```

`discussion_memory` cannot depend on Persona, `PersonaPrivateStance`, candidate prompt rendering or candidate generation lifecycle. It owns typed memory, patches, validation, deterministic reduction, persistence projection, lazy maintenance and public working-context construction. It does not own session lifecycle, phase transition, floor, next speaker, scoring, public transcript truth or provider selection. P1-7 Report, P3 scoring/evaluation, P2 voice adapters and a future moderator may consume the same public structured-memory seam without becoming memory authorities.

### 10.3 Evidence authority and persistence responsibilities

`DiscussionEvent` / authoritative public utterance history remains the only evidence authority. Memory is a derived projection: it cannot rewrite/delete source events, fabricate evidence during rebuild or become historical truth. Every accepted semantic item provenance reference must resolve to a real allowlisted public utterance sequence in the same session and visible derivation range.

P1-6B implementation freezes exactly two persistence responsibilities:

1. `discussion_memory_states` — at most one hot-path current row per session:
   - `session_id` as primary key and cascading FK to `simulation_sessions`;
   - non-negative `revision` and `source_through_sequence`;
   - positive `schema_version`, non-empty `derivation_version` and non-empty immutable project-owned `projection_version`;
   - closed, validated `structured_state` JSONB;
   - timezone-aware `updated_at`.
2. `discussion_memory_revisions` — immutable append-only accepted patch journal:
   - UUID `id`, `session_id`, positive `revision`, non-negative `base_revision`;
   - `source_from_sequence` and `source_through_sequence` with a valid ordered range;
   - closed `patches` JSONB, positive `schema_version`, non-empty `derivation_version` and non-empty immutable project-owned `projection_version`;
   - SHA-256 `derivation_input_digest` and timezone-aware `created_at`;
   - nullable `prompt_version_id` FK plus nullable `provider_identifier`, `model_identifier` and `configuration_version` as one all-or-none semantic-model provenance group. Non-model deterministic derivation leaves that group null; no generic model registry is introduced;
   - unique `(session_id, revision)` and session-local revision/source indexes.

An absent current row is logically empty revision 0/cursor 0. The first successful writer atomically inserts revision 1 plus the current row; uniqueness makes concurrent bootstrap losers stale. Every later successful write atomically appends revision `R+1` and CAS-updates the current row from `R` to `R+1`. A journal row never stores a full structured-state snapshot. Current state is the fast read, the patch journal is exact memory history, and `DiscussionEvent` is ultimate evidence.

The three version responsibilities are separate: `schema_version` identifies structured-memory/patch data shape; `derivation_version` identifies semantic interpretation/derivation algorithm; `projection_version` identifies deterministic reducer semantics plus deterministic materialized-state policy semantics required for exact replay. A deterministic reducer/state-policy change receives a new immutable `projection_version`. Policy parameters that affect materialized replay output are bound to or resolvable by that version. No generic plugin/version registry and no reducer/policy table is created.

### 10.4 Typed semantic state and stable item identity

The closed structured state contains:

- `proposals`;
- `evaluation_criteria`;
- `agreements`;
- `open_conflicts`;
- `discarded_options`;
- optional `current_decision`.

Each semantic `MemoryItem` has project-owned `memory_item_id`, closed `kind`, bounded `canonical_text`, minimal `status` (`ACTIVE`, `SUPERSEDED`, `DISCARDED`), validated `source_sequences`, `introduced_at_sequence`, `updated_at_sequence` and optional `superseded_by_id`. Dynamic phase, remaining time, current floor and next speaker never become durable semantic-memory truth.

The deriver cannot assign durable IDs. For `ADD` or replacement content, the reducer allocates a deterministic UUID from session identity, target revision, patch ordinal and item kind. `UPDATE`, `SUPERSEDE` and `DISCARD` must target an existing compatible item ID. The materialized JSONB stays bounded: policy may deterministically evict the oldest terminal items before active items when size limits require it, while the journal preserves their history. No entity/edge/node, normalized memory-item, vector or graph table is created.

### 10.5 MemoryPatch, derivation and deterministic reducer

The project-owned contracts are:

```text
MemoryDerivationInput
MemoryPatch
MemoryDerivationResult
MemoryDeriver Protocol
```

`MemoryDerivationInput` allowlists only session identity, previous public structured memory, the ordered new public utterance episode batch and an optional project-owned `PublicMemoryQuestionContext`. That question type is equal to or narrower than existing `AuthorizedQuestionContext` and contains only explicitly selected candidate-visible facts needed by derivation: question version identity, title, scenario, objective, public hard/soft constraints, public stakeholders and public options. It never accepts ORM `QuestionVersion`, generic `QuestionVersion.model_dump()`, `reference_dimensions`, `hidden_conflicts`, `acceptable_outcome_patterns`, private/evaluator/reference-answer metadata or system-only question configuration. Phase-specific public guidance, if genuinely needed, must be a deliberately projected public field; the entire `phase_prompts` map is not exposed by default.

The input also forbids `PersonaPrivateStance`, `private_information`, `red_lines`, `concession_conditions`, participant-private strategy, user-private notes, credentials and candidate rendered prompts. Question-field allowlisting is explicit rather than inferred from whatever fields happen to exist on `QuestionVersion`.

`MemoryDeriver` returns proposed closed operations only: `ADD`, `UPDATE`, `SUPERSEDE`, `DISCARD`. It cannot choose revision numbers, invent durable IDs/source sequences, write ORM state or alter session/floor/scoring authority. Provider text passes through a project-owned strict parser into the closed patch schema before any mutation.

For every claimed `source_sequences` reference, application validation proves that the sequence exists, belongs to the same session, is an allowlisted public utterance, lies inside the derivation-visible source range and does not cross a private/system boundary. Speaker identity is derived from the projected source record. Any invalid or hallucinated provenance rejects the whole derivation result; it is never silently repaired or persisted.

Only the deterministic reducer mutates memory:

```text
previous validated structured state
  + validated ordered MemoryPatch[]
  + target source range / target revision / MemoryPolicy
  = next validated structured state
```

Source ordering/range coverage, cursor advancement, revision allocation, operation ordering, item identity/status transitions, provenance association, idempotent re-entry, journal replay, stale/current detection and state-size enforcement are deterministic. The same accepted journal plus its recorded `schema_version` and historical `projection_version` reproduce the same current state; `derivation_version` explains semantic interpretation but does not substitute for deterministic projection identity.

### 10.6 Exact replay versus semantic rebuild

Exact replay applies accepted patch journal revisions in `(session_id, revision)` order and resolves the historical deterministic reducer/materialized-state policy semantics recorded by each revision's `projection_version`. It must reproduce the same structured state and cursor and must never silently apply the latest reducer/policy behavior to older revisions. Missing/unknown projection semantics or a digest/schema/provenance mismatch fails replay rather than guessing. No generic version registry is required: implementation owns the finite supported projection-version dispatch in project code.

Semantic rebuild re-reads immutable authoritative public history under a new derivation/prompt/model/config version and produces a newly validated patch set. A real LLM need not reproduce identical text or bits. Rebuild appends a new revision that transforms the current projection, retains old journal history and records new provenance; it never overwrites prior derivation records or source events. P1-6B leaves this additive seam without building branches, forks or a generic version-control system.

### 10.7 Lazy semantic compaction and bounded MemoryPolicy

The hot path uses:

```text
current materialized memory + uncompacted recent public utterance tail
```

When that combination provides complete coverage inside `DiscussionWorkingContext` budgets, maintenance performs no semantic model call. When the uncovered raw tail reaches a configurable high watermark, `MaintainDiscussionMemory(session_id)` selects the oldest eligible ordered episode batch and compacts enough data that a successful commit returns the tail to or below a lower target watermark. High/low hysteresis prevents per-utterance calls and threshold oscillation. Numeric production values are configuration, not schema.

`MemoryPolicy` explicitly bounds max active items per semantic kind, canonical-text length, provenance references per item, patch operations per derivation, serialized structured-state size, retained terminal items, Working Context memory budget, recent raw-tail budget and high/low episode/codepoint watermarks. Parameters that affect deterministic materialized-state output—including size enforcement and terminal-item eviction—are bound to/resolvable by `projection_version`. High/low compaction trigger thresholds need not be duplicated per revision unless implementation proves they affect exact journal replay output. Tests freeze boundary behavior; the Design Freeze does not guess final commercial numbers.

### 10.8 DiscussionWorkingContext and prompt compatibility

`DiscussionWorkingContext` is a public structured application type containing memory revision/cursor, active proposals, criteria, agreements, conflicts, current decision, ordered recent public utterances, authoritative dynamic phase and computed remaining time. Semantic fields come from memory, the tail comes from evidence, and dynamic fields come from `SimulationSession`. It is not an opaque summary string.

Every memory-backed candidate request persists a closed `GenerationRequestMetadata` V2 in the existing `LlmGenerationRequest.request_metadata` column. V2 records at least: `schema_version`, `configuration_version`, `working_context_version`, closed `context_mode`, `memory_revision`, `memory_source_through_sequence` and `context_source_through_sequence`. `memory_revision = 0` represents consumed logical empty memory; `memory_source_through_sequence` is that memory revision's represented public cursor; `context_source_through_sequence` is the highest public utterance sequence actually visible after adding the raw tail. `context_mode` distinguishes at least `MEMORY_WITH_RAW_TAIL` from `SAFE_RAW_FALLBACK`. `working_context_version` identifies project-owned assembly/render semantics independently from provider configuration.

Historical V1 metadata rows with only `schema_version = 1` and `configuration_version` remain readable and are never rewritten. The V2 DB/domain constraint is additive/compatible and closed by schema version; it does not create a provenance service/table. `request_digest` remains integrity evidence but is not a substitute for PromptVersion + provider/model/config + exact memory revision/cursor + raw-tail boundary + Working Context version/mode provenance.

Candidate-local composition continues to add only the current AI participant's authorized Persona/Private Stance after public Working Context construction. Candidate prompt rendering converts the structured context to text. Published `AI_CANDIDATE_TURN` V2 remains immutable and historically traceable. Implementation publishes a new immutable V3 using closed variables equivalent to `discussion_memory`, `recent_discussion` and `time_remaining_seconds` alongside the existing phase/private candidate variables; it never updates V2 in place.

Semantic derivation reuses `PromptVersion` with `prompt_key = DISCUSSION_MEMORY_UPDATE` and `purpose_code = DISCUSSION_MEMORY_DERIVATION` (or source-compatible equivalent uppercase codes), plus its own public-only renderer/parser. It does not create `MemoryPromptVersion` or reuse `AuthorizedGenerationContext`.

### 10.9 Minimal model/provider transport seam and output portability

Because current `RuntimeGenerationInput` includes generation request, participant, floor and phase fields while Zhipu transport only needs rendered prompt, provider/model/config and invocation options, the second real memory caller would otherwise duplicate vendor HTTP or fake candidate identities. P1-6B implementation may therefore extract the smallest project-owned model-invocation transport input/result containing rendered prompt, provider/model/config identity, temperature, output budget and output expectation. Candidate generation and memory derivation adapt their domain inputs/results at this boundary; existing `LlmGenerationRequest`, `AiUtterance`, orchestration outcomes and candidate provider-neutral behavior remain candidate-owned and compatible.

The memory domain never depends on Zhipu JSON mode. Baseline flow is model text → strict project-owned parser → closed typed schema → provenance/policy validation → patches. An adapter may later use constrained output without changing the domain contract. No registry, routing, fallback, marketplace, generic agent runtime or distributed model service is allowed.

### 10.10 Concurrency, transaction and session locality

The design is multi-process safe without Redis or a distributed lock:

```text
short read transaction: read state revision R + eligible public batch
COMMIT
external semantic derivation and strict validation
short write transaction:
  verify current revision/cursor still equal the base
  append immutable revision R+1
  insert/update materialized state R+1
COMMIT
```

The write uses optimistic CAS through a conditional session-local insert/update plus uniqueness constraints. A loser discards the stale semantic result, re-reads current state and does not overwrite or blindly retry provider work. Journal append and materialized-state update succeed or roll back together. No model call occurs inside a database transaction. All normal reads/writes are `WHERE session_id = ?`; there is no global lock or cross-session aggregation on the hot path.

### 10.11 Failure and fallback semantics

- Case A: memory is stale but memory plus uncovered raw tail still gives complete bounded coverage — generate normally and do not call the semantic model merely to become current.
- Case B: compaction is required and derivation fails, but complete public context still fits the safe raw fallback budget — use bounded raw fallback and emit safe observability.
- Case C: derivation fails and complete necessary context no longer fits — never silently truncate earlier discussion. Raise project-owned `DiscussionWorkingContextUnavailable`; the AI-runtime caller maps it to its existing safe `CONTEXT_REJECTED` path before provider invocation, preserving session/floor/orchestration authority.

If the model succeeds and the process crashes before save, public evidence remains intact and later maintenance may derive again. P1-6B creates no durable Memory job/worker/queue. `MaintainDiscussionMemory(session_id)` is an application seam whose caller may be replaced later without changing the memory domain.

### 10.12 Privacy and observability

Privacy tests use sentinels for Private Stance, private information, red lines, concession conditions, candidate rendered prompts, user-private notes and credentials across derivation input, journal/state JSON, logs and Working Context. No shared-memory path may contain or infer them as public facts.

Existing structured logging/observability may add safe fields: `memory_revision`, `source_gap`, `raw_tail_size`, `memory_state_size`, `compaction_triggered`, `derivation_input_size`, `derivation_output_size`, `derivation_latency`, `patch_operation_count`, `derivation_failure`, `cas_conflict` and `fallback_used`. It must not log Private Stance, credentials, unnecessary verbatim user content or full sensitive prompts. No telemetry vendor/infrastructure is added.

### 10.13 Scale, replaceability and explicit upgrade triggers

The domain/interface passes the frozen tests: 10× sessions remain session-local with bounded state and short transactions; inline derivation can later move to a worker; JSONB current state can later gain normalized/vector/graph secondary projections; PostgreSQL tables can later partition/shard; and provider transport can change without consumer/domain rewrites. No future infrastructure is implemented now.

Re-evaluate only on observed triggers:

- worker/queue: model I/O is a measured online bottleneck, API waits saturate, or duplicate derivation cost is material;
- pgvector/retrieval: active structured memory cannot bounded-fit or real cross-session semantic retrieval appears;
- normalized memory-item table: Report/P3/operations require material cross-session SQL querying;
- graph store: substantial cross-session/person/question temporal multi-hop queries become a real product need;
- partition/sharding: table size/query/latency metrics justify it.

### 10.14 Frozen implementation batches

These are internal batches of one future P1-6B implementation checkpoint, not new governance stages:

1. Memory domain + additive persistence — typed state/patches/reducer, materialized state, patch journal and migration.
2. Semantic derivation boundary — public-only input, `MemoryDeriver`, semantic PromptVersion, strict parser/provenance validator and only the justified minimal provider-transport refinement.
3. Lazy maintenance + Working Context — `MemoryPolicy`, hysteresis compaction, CAS, Working Context builder, additive closed `GenerationRequestMetadata` V2 persistence, immutable candidate prompt V3 and AI runtime caller integration with normal/fallback context provenance.
4. Correctness/recovery proof — PostgreSQL migration, projection-versioned exact replay, semantic rebuild, concurrency/CAS, Persona/question evaluator privacy sentinels, hallucinated provenance rejection, bounded state/context, normal/fallback provenance, fallback and AI-context integration.

### 10.15 Implementation acceptance matrix

| Area | Required implementation acceptance |
|---|---|
| Evidence | Raw `DiscussionEvent` facts remain byte/sequence authoritative; no rewrite, deletion or fabricated backfill. |
| Persistence | One current row/session plus append-only patch revisions record `schema_version`, `derivation_version` and `projection_version`; additive upgrade/downgrade, constraints, indexes and atomic state+journal write pass PostgreSQL tests. |
| State | Closed typed semantic kinds/items/statuses, deterministic IDs/transitions and projection-version-bound bounded/eviction policy pass unit/property-style boundaries. |
| Derivation | Public-only input uses explicit `PublicMemoryQuestionContext`; ORM/generic dumps and hidden/evaluator/reference question fields are rejected; closed parser, deterministic fake deriver and invalid-output rejection pass without real provider calls. |
| Provenance | Wrong session/type/range/missing/hallucinated/private references reject the whole result; participant identity comes from source. |
| Replay/rebuild | Accepted journal exact replay resolves every historical `projection_version` and reproduces state without latest-policy drift; unknown versions fail; semantic re-derivation records a new revision/provenance without changing source or old journal. |
| Lazy compaction | No call below high watermark when full context fits; oldest eligible batch compacts toward low watermark; re-entry is idempotent. |
| Working Context | Memory + full eligible raw tail + authoritative dynamic phase/time fit explicit budgets; no opaque summary-only dependency. |
| Generation context provenance | Historical metadata V1 remains readable; every memory-backed candidate request persists closed V2 Prompt/provider/model/config plus working-context version/mode, exact memory revision/cursor and visible raw-tail upper sequence for both `MEMORY_WITH_RAW_TAIL` and `SAFE_RAW_FALLBACK`. |
| Prompt compatibility | Candidate V2 remains immutable; new candidate V3 and semantic-memory prompt are separately versioned and historically resolvable. |
| Provider | Candidate and memory callers share only minimal transport; domain stays vendor-neutral; no registry/router/fallback or duplicate vendor HTTP. |
| Concurrency | Bootstrap and steady-state CAS admit one winner; stale result cannot append/update; state+journal are transactionally consistent. |
| Transactions | No external model call occurs inside a transaction; read and write transactions remain short and session-local. |
| Failure | Cases A/B/C are proved; Case C reaches safe `CONTEXT_REJECTED` without provider call, silent truncation or authority mutation. |
| Privacy | Private/candidate/user/system sentinels and question-level evaluator/hidden/reference-answer sentinels never enter derivation input, state, journal, Working Context or logs. |
| Compatibility | P1-3 lifecycle, P1-4 floor, P1-5 generation/orchestration and existing REST/WS/Web contracts remain compatible. |
| Observability | Safe memory/compaction/CAS/fallback fields exist without sensitive payload logging or new telemetry infrastructure. |
| Scale/YAGNI | Session-local bounded path passes; no Redis, queue, worker, vector, graph, normalized item table or speculative service is added. |

### 10.16 Explicit non-goals, STOP conditions and review gate

P1-6B Design Freeze and implementation exclude public Memory REST/WS/Web, Report/scoring, cross-session user memory, RAG/embeddings/pgvector, graph/Graphiti, Redis, queue/worker, microservice, multi-tenant system, billing, provider routing/fallback, voice and P1-7/P1-8 work.

Stop before implementation or scope expansion if actual source later proves that: (1) the two-table shape cannot migrate additively; (2) public evidence cannot replay safely; (3) a public REST/WS change is required; (4) shared memory cannot isolate Private Stance; (5) optimistic CAS is unsafe in the current transaction model; (6) `PromptVersion` cannot support the semantic prompt without a new product decision; (7) transport refinement breaks accepted P1-5 contracts; (8) the master plan must change; (9) a new Accepted ADR/product decision is required; or (10) a 10× domain blocker cannot be addressed by replaceable infrastructure.

Design-time STOP-condition result: `NONE`. The initial external actual-source review verdict was `BLOCKED` on exactly `P16B-REV-001`, `P16B-REV-002` and `P16B-REV-003` against `group-interview-arena-review-20260830-060509.zip` / SHA-256 `C0C7A7A589B1795DD917C11CF13B36FBCE245DFFD36CD20D5C96BAD80AC6EF26`. Finding-only remediation froze projection identity, persisted candidate Working Context provenance and explicit public question allowlisting. The finding-only external actual-source re-review verdict is `PASS` against `group-interview-arena-review-20260830-062133.zip` / SHA-256 `C10F2A9362EB6102C6C3F23D7BA66234FECC098BDE2A394D5A2738EBB97E701D`; `P16B-REV-001 CLOSED`; `P16B-REV-002 CLOSED`; `P16B-REV-003 CLOSED`; new findings `NONE`; open findings `NONE`. The approved production implementation is now `DONE / DESIGN_SCOPE_FROZEN / IMPLEMENTATION_COMPLETE / ACTUAL_SOURCE_REVIEW_PASS`. Implementation finding-only actual-source re-review verdict is `PASS` against `group-interview-arena-review-20260830-150847.zip` / SHA-256 `0EAA4B3FEE82F4D8A82D5098CECFDA1BF04F9161B7A63E7F7779B2512D9347F6`; `P16B-IMP-001`, `P16B-IMP-002`, `P16B-IMP-003`, `P16B-IMP-004`, `P16B-IMP-005`, `P16B-IMP-006`, `P16B-IMP-007` are `CLOSED`; new findings `NONE`; open findings `NONE`. P1-6C Design Freeze is `DONE / DESIGN_SCOPE_FROZEN / ACTUAL_SOURCE_REVIEW_PASS`; P1-6C production implementation is `DONE / DESIGN_SCOPE_FROZEN / IMPLEMENTATION_COMPLETE / ACTUAL_SOURCE_REVIEW_PASS`; implementation findings `NONE`. At the P1-6B closeout checkpoint, P1-6D/P1-6E plus P1-7/P1-8 were `NOT_STARTED`; current status is governed by the plan header and later checkpoint sections.

## 11. P1-6C Design Freeze

P1-6C is an integration/composition checkpoint only. At committed baseline `3b9d4cf9a33f3d20a0b43a9f04d0483316728fa5`, P1-6B and its post-commit CI are green. Scoped actual-source calibration found no production wiring gap and no STOP condition. The preferred implementation outcome was therefore `production changes = 0`, with focused tests proving the existing composition. The Design Freeze is `DONE / DESIGN_SCOPE_FROZEN / ACTUAL_SOURCE_REVIEW_PASS`; production implementation is `DONE / DESIGN_SCOPE_FROZEN / IMPLEMENTATION_COMPLETE / ACTUAL_SOURCE_REVIEW_PASS`.

### 11.1 Actual-source composition map and approved root

The approved composition root is the existing discussion progression:

```text
Web / WS command or lifecycle reconciliation
  -> resume_discussion_progression()
  -> existing P1-4 scheduler
  -> AI floor grant
  -> drive_configured_ai_session()
  -> drive_continuous_ai()
  -> generate_ai_utterance()
  -> P1-6B lazy memory maintenance
  -> DiscussionWorkingContext
  -> AI_CANDIDATE_TURN V3
  -> provider
  -> AiUtterance + authoritative public DiscussionEvent
  -> existing floor release / scheduler continuation
```

Current source confirms that `discussion_sessions/progression.py` delegates configured AI work rather than owning generation or Memory; `ai_runtime/composition.py`, `continuous.py` and `orchestration.py` reuse the accepted provider/runtime/floor path and already support AI-to-AI continuation; `ai_runtime/runtime.py` naturally maintains P1-6B Memory while assembling the candidate V3 Working Context and persists exact `GenerationRequestMetadata` V2 context provenance; `discussion_sessions/realtime.py` already resumes progression after connect/reconciliation and Human contribution. P1-6C must not invoke Memory separately from this path.

### 11.2 Authority boundaries

| Authority | Frozen owner |
|---|---|
| Session lifecycle and phase transitions | P1-3 |
| Speaker, floor and scheduling | P1-4 |
| AI candidate content | P1-5/P1-6B AI Runtime |
| Structured public discussion memory | P1-6B |
| Composition trigger | Existing discussion progression/realtime seams |
| Presentation | Existing REST/WS/Web contracts |

P1-6C owns none of these authorities. It adds no `TextSimulationCoordinator`, `SimulationOrchestrator`, second scheduler/lifecycle engine, Memory-driven speaker selection or Web-driven Memory orchestration. The rule is **composition, not orchestration reinvention**.

### 11.3 Production-change-only-if-RED rule

Future P1-6C implementation is composition-proof first. Production code must remain unchanged when targeted integration tests prove the existing caller chain. A production change is allowed only after a P1-6C RED test exposes a concrete wiring defect, and must be the smallest correction in an existing caller/composition seam such as progression, configured AI composition or its directly required existing dependency. No new subsystem, schema, migration, public contract, Web code or dependency is authorized.

### 11.4 Dual-workload network-free provider proof

The focused test harness must supply one deterministic, network-free project-owned provider seam for both workloads: candidate `__call__` returns a deterministic utterance, while generic `invoke` returns closed, valid `MemoryPatch` JSON. This proves semantic derivation and subsequent candidate generation through the configured production path without adding a production provider, registry, router, fallback or real provider call.

### 11.5 Happy-path composition scenario

Starting from a valid Human + 3 AI session whose existing scheduler can reach an AI floor and whose authoritative public evidence crosses the P1-6B compaction threshold, the test drives `resume_discussion_progression()` through the real configured path. It must prove: a semantic Memory revision is durably accepted; its source cursor/provenance is valid; candidate V3 consumes that exact revision plus the correct raw tail; `GenerationRequestMetadata` V2 records the exact Memory revision and visible public cursor; no other seat's Private Stance enters shared Memory/context; exactly one `AiUtterance` and one public `participant.utterance.created` fact result for the grant; release is not duplicated; and Memory performs no phase/floor mutation.

### 11.6 Failure and fallback scenarios

- Safe fallback: when semantic derivation fails but complete public history fits the bounded raw fallback, candidate generation continues with `GenerationRequestMetadata` V2 `context_mode = SAFE_RAW_FALLBACK`, while existing candidate, release and scheduler semantics remain authoritative.
- Unsafe context: when derivation fails and complete necessary context cannot fit, the existing context-rejection/recovery path emits no fabricated AI utterance, unauthorized phase/floor mutation or invented Memory revision.

These are focused backend integration proofs, not a second failure engine or a P1-6D restart/reload/cancellation scenario.

### 11.7 Evidence, provenance and privacy invariants

Authoritative public truth remains ordered `DiscussionEvent` evidence. The composed direction is `DiscussionEvent -> Memory projection -> Working Context -> AI output`; Memory never becomes a transcript authority and no event is rewritten or deleted. Candidate metadata must identify the exact consumed Memory revision and visible raw-tail cursor. Shared derivation/Memory/Working Context remain public-only and must not receive another participant's Private Stance or other private/evaluator/provider-secret material; P1-6B owns the detailed Memory invariants referenced by this section.

### 11.8 Public-contract compatibility

P1-6C adds or changes no public REST schema, public WebSocket command/event, Memory REST/WS surface, Web Memory state/API or transcript semantics. Web continues to consume existing snapshot, transcript and realtime contracts. If composition requires any public-contract change or Web knowledge of Memory internals, implementation must stop.

### 11.9 P1-6C/P1-6D boundary

P1-6C proves backend/application composition correctness through one focused production-caller integration path. It does not run a complete browser journey across all phases and all three AI seats. P1-6D separately owns the complete network-free Human + 3 distinct AI path through `FINAL_SUMMARY -> COMPLETED`, including reload/reconnect, API restart, generation failure/cancellation, duplicate-work prevention and memory-enabled composition.

### 11.10 Frozen future implementation scope and acceptance

Expected implementation is one focused progression/composition integration module or the closest existing integration extension, a deterministic dual-workload test fixture and targeted normal/fallback/context-rejection cases. Production changes default to `NONE`.

| Area | Required proof |
|---|---|
| Composition root | `resume_discussion_progression` drives the configured AI path; no new coordinator. |
| Memory | Real composition creates and consumes P1-6B Memory through existing interfaces. |
| Candidate context | V3 consumes the exact Memory revision plus raw tail. |
| Provenance | `GenerationRequestMetadata` V2 matches the actual consumed context. |
| Evidence | Human/AI `DiscussionEvent` remains authoritative. |
| Scheduler | Next-speaker/floor ownership remains P1-4. |
| Lifecycle | P1-3 remains sole phase authority. |
| Safe fallback | Memory failure plus bounded complete raw history continues as `SAFE_RAW_FALLBACK`. |
| Unsafe context | Context failure produces no fabricated utterance or unauthorized state mutation. |
| Privacy | No cross-seat Private Stance leakage. |
| Idempotency | No duplicate utterance or release for the composed grant. |
| Contracts | REST/WS/Web remain unchanged. |
| Scope | No P1-6D, report, voice or deferred infrastructure. |

### 11.11 STOP conditions and design result

Stop future implementation if actual source proves that: (1) Memory is not naturally consumed by normal AI generation; (2) composition requires a new business coordinator/authority; (3) existing progression needs structural redesign to drive memory-backed AI; (4) REST/WS must change; (5) Web must know Memory internals; (6) lifecycle/scheduler ownership must move; (7) P1-6C necessarily duplicates P1-6D full E2E; (8) schema/migration must change; (9) a new ADR/product decision is required; or (10) [`PROJECT_MASTER_PLAN.md`](../PROJECT_MASTER_PLAN.md) must change.

Design-time result: `NONE`. The only identified gap is proof coverage: existing focused progression tests stub configured AI composition, while the current broad browser provider fixture does not exercise the dual candidate/semantic workload through the real configured chain. That is a future test gap, not a production wiring defect.

External actual-source review verdict: `PASS` against `group-interview-arena-review-20260830-170659.zip` / SHA-256 `D4364CA666D715EA7932B3FC525D6D154EC18F8F4AC3D3989F40C19AE683B398`; design-review findings `NONE`; new findings `NONE`; open findings `NONE`. The P1-6C Design Freeze is therefore `DONE / DESIGN_SCOPE_FROZEN / ACTUAL_SOURCE_REVIEW_PASS`.

### 11.12 Production implementation checkpoint

P1-6C production implementation is `DONE / DESIGN_SCOPE_FROZEN / IMPLEMENTATION_COMPLETE / ACTUAL_SOURCE_REVIEW_PASS`. The focused PostgreSQL integration module [`test_full_text_simulation_composition.py`](../../apps/api/tests/integration/test_full_text_simulation_composition.py) drives the real `resume_discussion_progression()` production caller through configured composition, continuous AI drive, candidate runtime, P1-6B Memory/Working Context, candidate V3, durable utterance/public event and floor release. One network-free test provider supplies both semantic `invoke` and candidate `__call__` workloads.

The proof covers accepted Memory revision plus low-watermark raw-tail composition, exact candidate V3 and `GenerationRequestMetadata` V2 provenance, bounded `SAFE_RAW_FALLBACK`, unsafe-context rejection before candidate generation, public-evidence authority, cross-seat Private Stance exclusion, lifecycle/floor ownership and repeat progression without duplicate Memory revision, utterance or public event. The initial RED was limited to invalid synthetic Human evidence in the test fixture and an incorrect full-compaction test expectation; correcting the fixture to valid AI public evidence and asserting the frozen lazy high/low watermark semantics produced GREEN. No production wiring defect was found, production source changes are `NONE`, implementation STOP conditions are `NONE`, and no real provider call or P1-6D work occurred.

Fresh gates: focused composition proof `3 passed`; affected PostgreSQL progression/composition/continuous/orchestration/runtime slice `87 passed`; API unit regression `521 passed` with `197 deselected`; Ruff lint `PASS`; Ruff format-check `143 files already formatted`; Pyright `0 errors, 0 warnings, 0 informations`. External actual-source implementation review verdict is `PASS` against `group-interview-arena-review-20260830-235324.zip` / SHA-256 `1E1FBE37255E294AEA76A4E4CC68E49490556C804BE77804731F78CF56EB944B`; implementation findings `NONE`; new findings `NONE`; open findings `NONE`; production wiring gap `NONE`; production source changes `NONE`. P1-6D Design Freeze is now `DONE / DESIGN_SCOPE_FROZEN / ACTUAL_SOURCE_REVIEW_PASS`; P1-6D production implementation and P1-6E remain `NOT_STARTED`, and P1-6/P1 remain `IN_PROGRESS`.

## 12. P1-6D Recovery / Three-AI End-to-End Validation Design Freeze

P1-6D is a dedicated network-free Browser Acceptance Scenario, separate from the existing layout-heavy session Browser proof. It composes the already accepted P1-3 lifecycle, P1-4 floor/scheduler, P1-5 recovery/runtime, P1-6B Memory and P1-6C production caller chain; it creates no second lifecycle, scheduler, recovery engine, provider router or Memory authority. Actual-source calibration at baseline `6204bb030299671dcd22b5bb5c765c5c1262dd58` found proof gaps only: production wiring gap `NONE`, production source changes default to `NONE`, and design-time STOP conditions `NONE`.

At the Design Freeze closeout checkpoint, P1-6D was `DONE / DESIGN_SCOPE_FROZEN / ACTUAL_SOURCE_REVIEW_PASS` and production implementation was `NOT_STARTED`. That historical review gate did not itself authorize implementation, enter P1-6E, or run independent acceptance; the later final implementation status is recorded in §12.13.

### 12.1 Actual-source calibration and pre-existing coverage

The existing [`browser_e2e.py`](../../apps/api/tests/integration/browser_e2e.py), [`session.spec.ts`](../../apps/web/e2e/session.spec.ts), [`playwright.config.ts`](../../apps/web/playwright.config.ts), Web package runner and Chromium CI job already provide an isolated temporary PostgreSQL database, migrated/seeded API, real Web process, Chromium, product UI session creation/start, REST + WebSocket observation, Human submission, reload/reconnect, API restart, cancelled generation recovery, durable verification, cleanup and the accepted lifecycle through `FINAL_SUMMARY -> COMPLETED`. The existing test is intentionally retained as the broad recovery/layout proof.

The accepted P1-6C [`test_full_text_simulation_composition.py`](../../apps/api/tests/integration/test_full_text_simulation_composition.py) separately proves the real progression caller chain with one network-free provider that implements semantic `invoke(ModelInvocationInput)` and candidate `__call__(RuntimeGenerationInput)`, durable Memory revision, candidate V3, `GenerationRequestMetadata` V2, safe fallback, unsafe-context rejection, privacy and re-entry idempotency.

Neither proof alone establishes the P1-6D contract. The current Browser fake is candidate-only, cancels by a global call ordinal, logs insufficient identity/workload/provenance data, proves only one AI contribution and uses one private sentinel. The P1-6C proof is backend-focused and does not exercise a complete Human + 3 AI Browser/restart journey. Actual source also proves that current `browser_e2e.py` invokes `test:e2e:browser`, that script invokes unfiltered `playwright test`, and the Playwright `testDir` discovers all `apps/web/e2e` specs. Therefore adding the dedicated spec without explicit selection would run it under the legacy API/provider/database harness. These are future test-isolation/proof gaps, not production defects.

### 12.2 Frozen scenario boundary and ownership

The future P1-6D scenario is a second, dedicated Browser spec with its own harness. The harness owns environment mechanics: isolated database, API/Web processes, restart coordinator, deterministic provider, persistent cross-restart signals/logs, post-run database verifier and cleanup. The Browser spec owns only the visible product journey: create/start, observe roster and phases, submit legitimate Human turns, reload/reconnect, request API restart, arm/cause one cancellation and observe safe continuation. It must not duplicate responsive, scroll, layout or screenshot assertions from `session.spec.ts`.

Existing production ownership remains unchanged:

| Concern | Frozen owner |
|---|---|
| Lifecycle and accepted phase order | P1-3 |
| Speaker selection, grants and releases | P1-4 |
| Candidate generation and cancellation recovery | P1-5/P1-6B runtime and orchestration |
| Public semantic Memory and Working Context | P1-6B |
| Normal production composition root | P1-6C existing progression |
| Public snapshot/transcript/realtime rendering | Existing REST/WS/Web |
| P1-6D | Acceptance composition and durable proof only |

### 12.3 Dedicated harness and future file map

The frozen future implementation shape is:

- new `apps/api/tests/integration/p1_6d_browser_e2e.py`: dedicated process/database/provider/restart/durable-verifier harness;
- new `apps/web/e2e/p1-6d-full-session.spec.ts`: product-journey-only Browser scenario;
- minimal test-only adjustment to existing `apps/api/tests/integration/browser_e2e.py` and/or `apps/web/package.json` runner scripts so the legacy harness explicitly selects the complete existing legacy Browser suite and the dedicated harness explicitly selects only `p1-6d-full-session.spec.ts`;
- minimal `apps/api/tests/integration/conftest.py` prefix allowlist extension for an isolated `gia_p16d_` database identity;
- required minimal `.github/workflows/ci.yml` cleanup-prefix recognition for `gia_p16d_`; the existing Chromium job remains the owner and no new CI job is added;
- these three governance documents only when status/evidence changes.

Production source, schema/migration, public REST/WS/Web contracts, provider/runtime behavior, prompt assets and dependencies default to no change. Any additional file requires a directly observed RED gap and the STOP/re-approval rule in §12.12.

The frozen runner topology is explicit and sequential:

```text
web:test:e2e
  -> legacy browser harness
       -> explicit selector for the complete existing legacy Browser suite
          (baseline auth.spec.ts + session.spec.ts, or source-compatible explicit selector)
       -> complete legacy harness cleanup
  -> dedicated P1-6D harness
       -> explicit selector for p1-6d-full-session.spec.ts only
       -> complete dedicated harness cleanup
```

No unfiltered legacy `playwright test` may discover the P1-6D spec. Playwright keeps `workers = 1`; the two harnesses never overlap, and this finding does not authorize a new parallelism architecture.

### 12.4 Authoritative roster and three-AI identity proof

The scenario resolves participant identity from the authoritative session snapshot created by the existing roster service, not from provider-call position, UI label text or assumed seat ordering. It must prove exactly one Human plus exactly three AI participants, three unique authoritative AI `participant_id` values, and one or more durable public AI utterances from each of those three IDs. Provider logs record workload type, session, participant, floor grant, phase and relevant prompt/provenance fields so calls can be correlated across API restart.

AI output is deterministic but distinct per authoritative participant. Assertions use durable participant/event/request relations; the proof must fail if one AI speaks three times while another never speaks.

### 12.5 Active Human contribution strategy

The Browser observes the authoritative current floor. Whenever the Human owns a live eligible floor, it submits one legitimate phase-aware public contribution through the existing UI and waits for the accepted public event/release before continuing. It does not mutate the database, manufacture events, bypass the UI command path or depend on fixed wall-clock sleeps. A per-grant record prevents duplicate Human submission after reload/reconnect.

Human content is deterministic and tagged by phase/grant for post-run correlation. The harness/verifier proves each accepted Human utterance belongs to the Human participant and an authoritative floor, while P1-4 remains the only speaker authority.

### 12.6 Dual-workload Memory and candidate proof

The network-free provider implements both accepted interfaces in one persistent test seam:

- semantic `invoke(ModelInvocationInput)` returns strict valid `MemoryPatch` JSON derived only from public input;
- candidate `__call__(RuntimeGenerationInput)` returns deterministic participant-distinct public text.

Persistent logs survive API restart and distinguish semantic from candidate workloads. The run must prove at least one semantic invocation creates a durable Memory revision; a later candidate uses immutable `AI_CANDIDATE_TURN` V3 and `GenerationRequestMetadata` V2 with `memory_revision > 0`; its recorded memory cursor and recent public raw-tail boundary match the visible authoritative evidence; and after API restart later generation continues from durable Memory rather than resetting it. Memory/rebuild may append derived revisions but must not rewrite, delete or replace any authoritative public `DiscussionEvent`.

### 12.7 Three-seat privacy sentinels

Each AI Private Stance carries a different unmistakable sentinel. For sentinel A/B/C, the future proof checks absence from every other candidate's rendered prompt/input, `MemoryDerivationInput`, persisted structured Memory, patch-journal semantic payload, shared Working Context, public utterances/events, REST/WS payloads, Browser DOM, persistent provider logs and safe observability output. Evaluator/reference-answer metadata and provider credentials receive equivalent absence assertions.

The current candidate may consume only its own authorized private stance at the candidate-local boundary. A sentinel must never be copied into public candidate output. DiscussionEvent remains the sole public evidence authority; semantic Memory is never treated as raw evidence.

### 12.8 Recovery and cancellation protocol

The single scenario runs these ordered stages:

1. Normal composition: all three authoritative AI participants speak and Memory is created/consumed.
2. Browser reload: reconnect from the durable watermark without duplicate public facts or work.
3. API restart: stop and restart the API against the same database, then prove snapshot/transcript/realtime and Memory-backed generation continue.
4. Eligible-candidate cancellation: after restart, the Browser/harness arms cancellation for the **next eligible candidate generation**, identified by authoritative participant/floor/runtime input rather than a global provider-call ordinal. The provider exposes a file-backed `RUNNING` signal and blocks that exact candidate call. The Browser reload/disconnect cancels it; the harness records exactly one candidate attempt for the grant, a durable failed request in the existing safe state, no AI utterance/public utterance event, exactly one durable/public `INTERRUPTED` release, and subsequent scheduling/generation through `COMPLETED`.

Semantic calls cannot accidentally consume the cancellation arm. The persistent arm, running, cancelled and call-log files make behavior observable across process boundaries without network access or provider credentials.

### 12.9 Durable idempotency and lifecycle verifier

After the Browser finishes, the harness queries PostgreSQL and fails unless all of the following hold:

- one session exists with exactly one Human and three AI participants;
- event sequences are contiguous and public utterance/event identity relations are one-to-one;
- every authoritative AI ID contributed and accepted Human turns are attributable to valid Human floors;
- each grant has at most one generation request, at most one AI utterance and exactly one terminal release; the cancelled grant has exactly the frozen failure/release shape from §12.8;
- reload, reconnect, API restart and repeated progression created no duplicate request, utterance, event, release, Memory consumption or revision-chain break;
- Memory revision/cursor, candidate V3 and metadata V2 provenance match the actual evidence consumed;
- the exact accepted phase order is `PREPARATION -> OPENING_STATEMENTS -> EXPLORATION -> CONFLICT_AND_EVALUATION -> CONVERGENCE -> FINAL_SUMMARY -> COMPLETED`;
- terminal session state is `COMPLETED` with no current floor and no live phase timing.

### 12.10 Inherited P1-6C failure-proof boundary

P1-6D owns only the normal memory-enabled full journey: durable Memory revision; candidate V3 and metadata V2 consumption/provenance; reload/reconnect; API restart; one intentional next-eligible-candidate cancellation/recovery; legitimate Human + three-AI participation; and full lifecycle completion. The one cancellation is the parent P1-6D generation-failure boundary.

`SAFE_RAW_FALLBACK` and unsafe-context rejection remain accepted P1-6C focused backend composition proofs. P1-6D must not add a second fallback or unsafe-context scenario merely for phase ownership. Those P1-6C tests are inherited regressions and are rerun only if future P1-6D work changes a directly relevant runtime/Memory seam.

### 12.11 Serial runner and Chromium CI contract

`pnpm web:test:e2e` remains the single package/CI entry. It must first run the legacy harness with an explicit selector covering the complete existing legacy suite, wait for complete cleanup, then run the dedicated harness with an explicit selector for only `p1-6d-full-session.spec.ts`, and wait for its cleanup. The existing `chromium-e2e` job remains the owner. Required cleanup recognition for the frozen dedicated `gia_p16d_` prefix is added minimally; there is no parallel Browser execution, additional CI job, real provider call or secret requirement.

Implementation verification must include the dedicated scenario, the explicitly selected complete legacy Browser regression, directly affected API/database checks, format/lint/type checks, single-head/migration checks only if actual changes require them, and repository/governance checks. P1-6C fallback/unsafe-context tests are rerun only when a relevant runtime/Memory seam changes. This Design Freeze runs none of those implementation suites.

### 12.12 Production-change gate, STOP conditions and review gate

Implementation begins test-first and production changes remain `NONE` unless a focused RED result proves a real existing-wiring defect. Stop and request explicit approval before changing production behavior, schema/migration, public REST/WS/Web contracts, PromptVersion/provider/runtime contracts, participant/lifecycle/floor ownership, Memory architecture, dependencies or CI topology; before adding a coordinator/router/worker/queue; if exact cancellation cannot be addressed through the existing floor/runtime seam; if three-AI identity requires call ordinals instead of authoritative IDs; if private sentinels cannot remain isolated; or if [`PROJECT_MASTER_PLAN.md`](../PROJECT_MASTER_PLAN.md) or an ADR must change.

The initial external actual-source review of `group-interview-arena-review-20260831-004302.zip` / SHA-256 `7CE39C1EB4DE8314DCE7DB1CDE9809EB386E0E0CADDED8620D11B47FDB1791D0` returned `BLOCKED` on exactly `P16D-REV-001` and `P16D-REV-002`. Finding-only remediation froze explicit legacy/dedicated Browser selector isolation plus required `gia_p16d_` cleanup recognition, and restored fallback/unsafe-context ownership to P1-6C.

External finding-only actual-source re-review returned `PASS` against `group-interview-arena-review-20260831-005931.zip` / SHA-256 `502D21B84410EDD606C806C188FFFF1FAF6C8E8ACE3F08381B86E9FA13E29A66`; `P16D-REV-001 CLOSED`; `P16D-REV-002 CLOSED`; new findings `NONE`; open findings `NONE`. At that checkpoint, P1-6D Design Freeze was therefore `DONE / DESIGN_SCOPE_FROZEN / ACTUAL_SOURCE_REVIEW_PASS` and production implementation remained `NOT_STARTED`. No independent review occurred and P1-6E remained `NOT_STARTED`; the later production implementation and final closeout are recorded below.

### 12.13 Production implementation final acceptance closeout

P1-6D production implementation is `DONE / DESIGN_SCOPE_FROZEN / IMPLEMENTATION_COMPLETE / ACTUAL_SOURCE_REVIEW_PASS`. D2-D1 happy path, D2-D2A Browser reload recovery, D2-D2B API restart recovery, D2-D3 cancellation recovery and D2-D4 final integration all `PASS`; accepted commit `6dcce5e961d6aa7b460243dbd6407e17c2478aa2`; CI `GREEN`.

Final acceptance ledger:

| Acceptance | Final evidence |
|---|---|
| Human + exactly three AI | Exactly one Human and three authoritative AI participants; Human contributes through the real UI and all three AI seats contribute publicly. |
| Semantic Memory | A durable Semantic Memory revision is created and later consumed without replacing authoritative public evidence. |
| V3 + metadata V2 | A later candidate uses `AI_CANDIDATE_TURN` V3 with `GenerationRequestMetadata` V2 Memory provenance. |
| Privacy isolation | Three distinct private sentinels remain candidate-local and absent from public transcript/events, shared Memory/context, Browser output and cancellation evidence. |
| Exact-once | Generation request, AI utterance, public utterance event and floor release relations satisfy the durable exact-once contract. |
| Browser reload recovery | The same durable session reconnects, transcript/sequence converge and progression continues without duplicate side effects. |
| API restart recovery | A new API process reconnects to the same session/database; sequence, transcript and Memory remain durable and progression continues. |
| Cancellation recovery | One eligible candidate is cancelled through the deterministic gate, reaches the accepted durable terminal/release shape and repeated recovery creates no second side effect. |
| Final lifecycle | Authoritative `session.state_changed` records `FINAL_SUMMARY -> COMPLETED` with trigger `PHASE_DEADLINE`; terminal session status is `COMPLETED` with no current floor. |

D2-D4 actual-source review initially opened `P16D-D2D4-REV-001` because the Human continuation action was inside a polling predicate. Finding-only remediation moved that action outside polling and retained an observation-only durable-completion predicate without a timeout/retry/sleep workaround. Final review verdict is `PASS`; `P16D-D2D4-REV-001 CLOSED`; new findings `NONE`; open findings `NONE`.

This final closeout changes only `docs/ROADMAP.md`, `docs/TASKS.md` and this plan. It adds no feature or acceptance, changes no production code, tests or CI logic, does not run independent review, and leaves P1-6E `NOT_STARTED`; P1-6 and P1 remain `IN_PROGRESS`.
