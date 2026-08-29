# P1-6A Scope Reconciliation + Evolution-Readiness Freeze

Status: `DRAFT / USER_REVIEW_PENDING`

Parent: `P1 — 文字版讨论闭环`

Baseline: clean committed `main` at `1d6bfec1e9cbb1b9b2917c63d63aeacea30a9976`; P1-5 is `DONE`; open findings are `NONE`.

Authority: `docs/PROJECT_MASTER_PLAN.md` remains immutable product baseline. This document does not redefine P1/P2/P3/P4 product scope.

## 1. Goal

P1-6A is a docs-only reconciliation checkpoint before continuing P1-6.

It has two goals only:

1. reconcile the original P1 execution intent with what P1-1 through P1-5 actually implemented, so later phases do not duplicate work or silently lose the structured-memory requirement;
2. freeze the smallest architecture boundaries needed so P1-6/P1-7 can evolve into P2/P3/P4 without avoidable rewrites, while explicitly refusing speculative infrastructure.

P1-6A does not implement production behavior.

## 2. Budget / complexity rule

This checkpoint is intentionally small.

- Prefer existing accepted docs and committed evidence over broad repository re-analysis.
- Inspect production source only when accepted docs conflict or cannot prove a material boundary.
- Do not create a generic future-platform architecture.
- A future capability may justify an interface/boundary/version seam, but not an unused runtime subsystem.
- Every new abstraction must solve a current P1 correctness/evolution problem; otherwise defer it.

## 3. Reconciled capability matrix

| Original intent | Current committed result | P1-6 consequence |
| --- | --- | --- |
| P1-1 contract / first vertical slice | Completed through session REST/WS foundation and reconnect semantics | Reuse; do not rebuild transport foundation |
| P1-2 question / persona system | Completed with immutable Question Version, Persona/Assignment/Private Stance boundaries | Reuse exact version/private-data authority |
| P1-3 session state machine | Completed with server-authoritative phases/deadlines | Reuse; memory/AI must not own lifecycle |
| P1-4 floor scheduling | Completed with deterministic scheduler and durable floor authority | Reuse; memory/AI must not own speaker selection |
| P1-5 discussion memory + AI Provider | AI provider/runtime, prompts, generation persistence/orchestration and Web/realtime composition completed; structured discussion memory was explicitly deferred | Structured memory is the material capability gap that must be closed in P1-6 |
| P1-6 complete text simulation | Much of Web + REST/WS + reconnect + Human/AI composition was completed early in P1-5F/P1-5R | P1-6 integrates missing memory into the existing stack and proves complete-session behavior; it must not rebuild the UI/transport |
| P1-7 basic report + V0.1 content | Not owned by P1-6A | Remains P1-7 |
| P1-8 P1 independent acceptance | Not owned by P1-6A | Remains P1-8 |

## 4. Frozen evolution-safe boundaries

These are architecture constraints, not authorizations to implement future products.

### 4.1 Discussion core stays transport-neutral

Session lifecycle, phase, floor, utterance/event history and discussion memory must not depend on Web presentation, a specific LLM provider, ASR or TTS. P2 voice should attach at input/output boundaries rather than replace the discussion core.

### 4.2 Evidence -> memory -> report is one-way

Authoritative persisted Utterance / Discussion Event history remains evidence truth.

Structured Discussion Memory is a derived, revisioned projection of public discussion facts. It may be rebuilt or upgraded; it must not overwrite evidence history.

Future reports consume evidence and/or derived projections; reports do not become session truth.

### 4.3 Three-layer discussion context remains mandatory

P1 must preserve the master-plan model:

1. raw utterance history for replay/report;
2. structured discussion memory for proposals, criteria, agreements, open conflicts, discarded options, current decision and similar public discussion state;
3. bounded short context for each model invocation.

Do not send the complete transcript to every model call as the normal context strategy.

### 4.4 AI is content authority only

P1-3 remains lifecycle authority. P1-4 remains floor/speaker authority. AI Runtime decides content for an already-authorized AI speaker; provider adapters perform model I/O only.

Provider/model output must not directly mutate phase, deadline, floor, scheduler decisions, scoring or database authority.

### 4.5 Stable identity and versioning

Existing Question Version and Prompt Version patterns remain the precedent. New persisted derived artifacts that can change semantics over time must carry enough identity/version/provenance to explain historical behavior and support future recalculation without rewriting session history.

P1-6A does not require a universal version framework.

### 4.6 Public/private context isolation

Shared structured memory may contain only public discussion facts. Persona Private Stance, another participant's private assignment data, provider secrets and unrelated user-private data must not leak into shared memory, public API/WS payloads or another participant's context.

### 4.7 API/realtime contracts are not database mirrors

Web consumes project-owned REST/WS contracts and projections, not persistence layout. Future storage or memory-schema changes should not force unrelated Web rewrites.

### 4.8 Additive-first persistence evolution

Historical training data is treated as potentially durable product data. Prefer additive migration and explicit backfill/transition over destructive reinterpretation. This is a design rule, not a requirement to build zero-downtime migration infrastructure in P1.

### 4.9 Future seam, not future infrastructure

Do not introduce Redis, queues/workers, vector DB/RAG, generic workflow engines, microservices, multi-tenant billing/entitlement systems, plugin frameworks or distributed locks merely for future commercial use.

If later scale requires one, it should replace/extend a stable application boundary rather than require rewriting discussion semantics.

## 5. Minimal P1-6 decomposition after this freeze

Subject to user approval of this design:

- `P1-6B — Structured Discussion Memory`: close the missing three-layer memory/context requirement with the smallest durable/rebuildable projection and bounded model context; no vector DB/RAG.
- `P1-6C — Complete Text Simulation Integration`: wire the memory result into the already-existing runtime/Web/realtime composition without rebuilding P1-5F assets.
- `P1-6D — Recovery + Three-AI E2E`: verify complete-session progression, reload/reconnect/API restart and AI failure/recovery with one Human + three AI participants.
- `P1-6E — P1-6 Acceptance / Closeout`: independent proof that the complete text simulation is stable enough to proceed to P1-7.

P1-7 remains Basic Report + V0.1 Content. P1-8 remains P1 Independent Acceptance.

## 6. P1-6B design questions to answer later, not in P1-6A

P1-6A deliberately does not pre-design the implementation. P1-6B must determine from actual source:

- exact persistence shape for current memory revision/provenance;
- exact event/utterance cursor used to prove projection freshness;
- deterministic vs semantic update responsibilities;
- bounded recent-context limit and summary contract;
- recovery/rebuild semantics after restart or duplicate processing;
- whether an existing P1-5 durable generation mechanism is sufficient for any semantic extraction work.

No answer may require an LLM call inside a database transaction.

## 7. Commercial-readiness filter

For every material P1-6/P1-7 design decision, apply three questions:

1. If usage grows materially, does the domain/interface boundary still make sense?
2. If the implementation behind the boundary is replaced, can consumers remain mostly unchanged?
3. Are we about to implement a future system for which there is no current requirement?

A negative answer to 1 or 2 is an architecture-risk signal. A positive answer to 3 is a stop/defer signal.

## 8. Explicit out of scope

P1-6A does not authorize:

- production code, schema/migration, API/WS contract, dependency, CI or Web changes;
- scoring, six-dimension evaluation or report implementation;
- ASR/TTS/voice work;
- payment, quota, entitlement, tenant or commercial operations code;
- Redis/queue/worker/vector DB/RAG/LangGraph/microservices;
- multi-provider routing/fallback/model marketplace;
- real-provider/model calls.

Any formal real-provider call remains separately user-authorized.

## 9. Acceptance criteria for P1-6A

P1-6A may be frozen only when:

- the original P1-1 through P1-8 execution intent is reconciled without renumbering later stages;
- structured discussion memory is explicitly recorded as the missing material P1-5 capability to be closed inside P1-6;
- already-completed P1-5F/P1-5R Web/realtime/composition work is explicitly reused rather than duplicated;
- the evolution-safe boundaries above are accepted without adding speculative infrastructure;
- P1-7 and P1-8 ownership remains unchanged;
- `PROJECT_MASTER_PLAN.md` remains byte-identical;
- no production/source/schema/API/dependency/CI change is made;
- after user review, only minimal governance/status synchronization is performed before P1-6B planning.

## 10. User review gate

This document is `DRAFT / USER_REVIEW_PENDING`.

No P1-6B implementation planning or production change is authorized until the user approves this written freeze. After approval, P1-6A may be marked frozen/complete with minimal `TASKS.md` / `ROADMAP.md` synchronization, then P1-6B receives its own design/implementation gate.
