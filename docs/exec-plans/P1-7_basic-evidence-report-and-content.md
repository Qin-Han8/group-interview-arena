# P1-7 Basic Evidence Report & V0.1 Content Closure Execution Plan

- Status: `P1-7 IN_PROGRESS`
- Current completed checkpoint: `P1-7D DONE / ACTUAL_SOURCE_REVIEW_PASS`
- Accepted checkpoints: `P1-7A / P1-7B / P1-7C / P1-7D`
- Remaining checkpoint: `P1-7E NOT_STARTED`
- Parent phase: `P1 IN_PROGRESS`
- Product target: `V0.1 Internal Validation`
- P1-7A reviewed baseline: `codex/p1-6e-closeout` at `bc8cb40148598230bd64feeeaebb498d05137fbe`
- P1-7B implementation baseline: `dcd9c0670fb239e4ad2b1f77b867ea68636df245`
- Git `main` / `origin/main` observed during P1-7A preflight: `df144f7605d435970a82871bd6f424dbd60722ee`
- GitHub `main` confirmed during governance closeout: `f6f105ed2fcc334f6c9dd83c00d934428e1b689b`
- External actual-source review: `PASS`; material findings/new blockers/open findings: `NONE`
- Reviewed bundle: `group-interview-arena-review-20260909-234536.zip`; SHA-256 `4EA3FE5DD23775106C2602CAA2EC6DC68AC8DDA6D9895C5D74465F90390798F3`
- Authority: [`PROJECT_MASTER_PLAN.md`](../PROJECT_MASTER_PLAN.md) > Accepted [`DECISIONS.md`](../DECISIONS.md) > [`ROADMAP.md`](../ROADMAP.md) > [`TASKS.md`](../TASKS.md) > this plan > domain docs > code
- Immutable master-plan SHA-256: `2388A9660320406CB35D5354126AD71C6849A98DB7C4A356796CA951BF372F26`

## 1. Goal and checkpoint boundary

P1-7 delivers **Basic Evidence Report + V0.1 Content Closure**. After a complete text discussion reaches authoritative `SimulationSession.status == COMPLETED`, the product derives a durable, versioned and traceable V0.1 training report from verifiable raw public discussion evidence. In parallel, P1-7 closes the V0.1 content target of 3 supported question types, 12 human-reviewed questions and the already established 4 basic Persona Templates.

P1-7A is a strict docs-only architecture/content freeze. It creates this plan and minimally synchronizes approved governance/domain documentation. It creates no report/evidence schema, migration, runtime, API/OpenAPI artifact, WebSocket lifecycle, Web UI, evaluator/provider call, prompt, dependency, CI or infrastructure change. It does not enter P1-7B.

The user-approved design is the governing specification for this plan. No additional ADR is required: the freeze applies D-009/D-010, ADR-006/007/009/014 and the existing P1-6 evidence/privacy boundary without changing them.

## 2. P1-7A actual-source reconciliation

P1-7A inspected the committed checkout `bc8cb40148598230bd64feeeaebb498d05137fbe` read-only. At preflight that checkout was the accepted P1-6 closeout baseline and four commits ahead of the then-observed `main` ref `df144f7605d435970a82871bd6f424dbd60722ee`; this plan records those historical identities rather than claiming the refs were equal.

| Boundary | Actual committed source fact | P1-7 consequence |
|---|---|---|
| Session lifecycle | `SessionStatus` ends the normal timed path at `COMPLETED`; the only other terminal value is `ABORTED_USER`. No report lifecycle state exists. | Report remains an independent post-session resource; do not add `REPORT_GENERATING` or `REPORTED`. |
| Public evidence | `participant.utterance.created` v1 exposes stable utterance, participant, actor kind, floor grant, phase, exact content and ordered event sequence/occurrence time. | Evidence resolves to authoritative public utterance/event facts by stable identity and sequence. |
| Human/AI identity | The authoritative roster records one Human and three AI participants; public utterances carry participant and actor kind. | Evidence about the Human must validate the Human source and cannot silently cite AI speech. |
| Memory | P1-6 implements public-only, versioned structured Memory and bounded Working Context over raw events. | Memory may provide bounded auxiliary context, but is never transcript, evidence or report truth. |
| Question model | The closed registry supports `ORDERING_SELECTION`, `RESOURCE_ALLOCATION` and `PLAN_DESIGN`. Public Question Version fields are separated from hidden/reference/evaluator fields. | These are the exact V0.1 content categories; evaluator input uses an explicit public allowlist. |
| Current content | Seed source contains exactly 4 V0.1 Persona Templates and 1 published internal-validation `RESOURCE_ALLOCATION` Question Version. | Content closure gap is 11 reviewed questions: ordering 4, resource allocation 3 additional, plan design 4. P1-7A writes none of them. |
| Persistence | P1-7B adds `evaluation_reports` and `evidence_items` as linear revision `f1a17b17c008`, extending 21 to 23 product tables. | The foundation owns durable identity/lifecycle/version/watermark and same-session relational provenance only; semantic evidence validation/generation remains P1-7C. |
| Public report surface | No report module, report route, OpenAPI report contract, report Web UI or report WS event exists. | P1-7D owns REST/Web. No existing public contract is overwritten. |

No actual-source conflict requires an ADR or master-plan change. During governance closeout, current GitHub `main` resolved to merge commit `f6f105ed2fcc334f6c9dd83c00d934428e1b689b`: the reviewed checkout `bc8cb40148598230bd64feeeaebb498d05137fbe` is one of its direct parents, and both commits have the same tree identity with an empty file-content diff. This is a review baseline-equivalence fact. It does not mean their commit SHAs are equal, that the review bundle was generated directly from the later `main` working tree, or that the historical branch deviation did not exist.

## 3. Frozen report architecture

P1-7 uses **Independent Report Resource + Evidence Records**:

```text
authoritative raw public utterance / DiscussionEvent history
  -> project-owned source collection and deterministic validation
  -> semantic evaluator proposal
  -> project-owned evidence acceptance/rejection
  -> versioned durable report + evidence records
  -> REST resource/read path
  -> Web report experience
```

`SimulationSession.COMPLETED` remains the discussion lifecycle endpoint. Report generation status belongs to the independent report resource, not the session state machine. Report generation is persisted and idempotent/re-enterable; `GET` reads durable state and never regenerates the report ad hoc. Report progress does not create a new activity WebSocket lifecycle.

P1-6 Memory is an optional bounded public-only aid:

```text
Memory != Evidence
Memory != Transcript
Memory != Report Truth
```

Raw authoritative public history remains the only evidence authority. A report may be rebuilt or superseded by a new version without rewriting the session, source events, prior report version or prior evidence provenance.

## 4. Frozen V0.1 report surface

### 4.1 Session overview

- authoritative completion fact;
- exact public Question Version content needed to identify the exercise;
- basic deterministic participation facts;
- covered discussion phases;
- concise training summary.

### 4.2 Strongest behaviors

- zero to three items;
- every item must resolve to at least one accepted authoritative source evidence record;
- absence of valid evidence is represented honestly, never filled with unsupported praise.

### 4.3 Largest improvement opportunities

- zero to three items;
- every item must resolve to at least one accepted authoritative source evidence record;
- language evaluates observable behavior and avoids personality or hiring conclusions.

### 4.4 Next-session priority

- exactly one priority improvement in every completed report;
- it is a training recommendation only;
- it does not create the P3 drill, training-plan or growth system.

### 4.5 Evidence cards

Each displayed card contains source participant, phase, source utterance, source event sequence, exact quote, interpretation and confidence. V0.1 text reports must not fabricate audio timestamps. P2/P3 may add real timestamp/audio provenance additively when authoritative audio timing exists.

## 5. Explicit non-scoring boundary

P1-7 does not output or imply:

- six 0–100 dimension scores;
- an overall score;
- a radar chart;
- percentile or ranking;
- “outperformed X% of users” claims;
- hiring probability;
- job fit;
- personality type.

The master-plan question “score versus level + evidence” remains `TBD`. This freeze does not resolve, rename or promote that TBD. P3 owns formal six-dimension scoring, aggregation, calibration, user dispute/feedback and specialty training.

## 6. Conceptual report/evidence contract

P1-7A freezes responsibilities, not physical columns or public DTO field names.

### 6.1 `EvaluationReport`

At minimum, the future resource must carry stable report identity and session identity; report schema version; evaluator/derivation version; authoritative source watermark (`source_through_sequence` or equivalent); report-owned generation status; overall summary; exactly one priority improvement when complete; created/completed timestamps; and provenance sufficient for later reproducibility.

### 6.2 `EvidenceItem`

At minimum, each accepted record must carry stable evidence identity and report identity; evidence kind `STRENGTH` or `IMPROVEMENT`; source participant identity; source utterance identity; source event sequence; authoritative phase; exact source-derived quote; interpretation; and confidence.

P1 does not require dimension, score, score effect, objective metric or rubric aggregation. P3 must be able to add dimension/metric/rubric/scoring-version relations without replacing the P1 report/evidence identities or provenance model.

## 7. Project-owned evidence validation

The semantic evaluator **proposes** evidence. Project-owned deterministic code **accepts or rejects** the proposal before persistence or display.

For every proposed evidence item, deterministic validation must prove at least:

1. source session equals report session;
2. source participant exists and belongs to that session;
3. source identity resolves to an authoritative public utterance/event;
4. source utterance belongs to the claimed participant and session;
5. phase equals the authoritative source phase;
6. source sequence/watermark/provenance is valid and within the evaluator-visible range;
7. quote is an exact contiguous substring of authoritative source content, with no model repair, paraphrase or whitespace-normalizing substitution;
8. Human-evaluation evidence points to the authoritative Human participant, never silently to AI speech.

Any failed check rejects the evidence proposal. Deterministic code does not “fix approximately correct” model output. Report completeness validation then enforces item caps, evidence linkage, exactly one priority and required version/provenance fields before marking the report complete.

## 8. Evaluator input and privacy boundary

The evaluator may receive only exact public Question Version identity and fields needed for training interpretation; public scenario/objective/constraints/stakeholders/options/material; authoritative session phase/completion facts; ordered public Human + AI utterance/events; public participant identity/actor kind; and bounded public-only Discussion Memory as auxiliary context.

The evaluator and report must never receive or persist Persona Private Stance, private candidate information, persona behavior/calibration parameters, hidden conflicts/acceptable outcome patterns/reference-answer fields, internal scoring/calibration secrets, candidate-private/system prompts, provider credential or Authorization data, raw provider request/response/error body, hidden reasoning/chain-of-thought, user-private notes or other non-public internal fields.

The report evaluates how the user behaved in relation to public discussion facts. It cannot use hidden backend answers to grade the user. Ordinary logs/traces/errors record only safe identities, versions, counts, status, latency and typed failure categories; they do not become a shadow transcript or report.

## 9. Deterministic and semantic responsibilities

Project-owned deterministic responsibilities are report eligibility; source collection/order/watermark; evidence lookup and exact quote matching; session/participant/utterance/phase validation; Human-source enforcement; report completeness; provenance/versioning; and generation idempotency/re-entry/stale-source handling.

Semantic evaluator responsibilities are proposing high-value behaviors, improvement opportunities, interpretations, the single priority improvement and confidence.

All automated acceptance uses a deterministic/fake evaluator and remains network-free. P1-7 does not select a new vendor-specific evaluator or require a real external LLM to pass any gate.

## 10. Eligibility and failure boundary

V0.1 formal report eligibility is exactly `SimulationSession.status == COMPLETED`. `ABORTED_USER`, partial completion and service-failure reports remain Deferred. P1-7 does not add `COMPLETED_PARTIAL`, pause/recovery states or report states to `SimulationSession`.

A failed or invalid generation attempt cannot publish a complete report or unvalidated evidence. Re-entry reads durable report/source truth, never relies on in-memory exactly-once delivery, and cannot duplicate a complete report version for the same frozen idempotency identity. Detailed retry/status/cardinality rules are frozen in P1-7B/C against the then-current source without adding a queue unless separately re-approved under ADR-009 triggers.

## 11. V0.1 content architecture closure

| Question category | Registered source code | Reviewed target | P1-7D candidate implementation | Human-review state |
|---|---|---:|---:|---|
| 排序选择型 | `ORDERING_SELECTION` | 4 | 4 | Pass |
| 资源分配型 | `RESOURCE_ALLOCATION` | 4 | 4 | Pass |
| 方案策划型 | `PLAN_DESIGN` | 4 | 4 | Pass |
| **Total** | 3 types | **12** | **12** | **Human content review PASS** |

The current 4 Persona Templates are retained as the V0.1 base. P1-7D authors the remaining 11 immutable candidate versions through the existing publication model without changing the retained internal-validation bundle. Automated structure is complete; external human content review is `PASS` with material content findings `NONE OPEN`.

Every V0.1 question must be a versioned, structured, human-reviewed public question suitable for a complete text session and report evidence interpretation. Quality review covers clear objective, coherent public constraints/material, meaningful discussion trade-offs, valid three-seat assignments/private isolation, safety and a complete runnable session. Quantity alone is not acceptance.

P1-7 excludes dilemma-decision/V0.5 expansion, industry packs and unconstrained instant AI generation of public questions.

## 12. Frozen P1-7 decomposition

### P1-7A — Basic Evidence Report & V0.1 Content Architecture Freeze

Completed docs-only checkpoint. Its external actual-source review is `PASS`; status is `DONE / DESIGN_SCOPE_FROZEN / ACTUAL_SOURCE_REVIEW_PASS`.

### P1-7B — Evidence / Report Persistence Foundation

Done with external actual-source review `PASS`. Revision `f1a17b17c008` adds the smallest report/evidence persistence and domain foundation, including report/evidence identities, closed report-owned generation status, version/source-watermark provenance, same-session constraints and concurrency-safe idempotent eligibility/re-entry. `get_or_create_eligible_report` accepts only owner-scoped `COMPLETED` sessions and uses the database generation-identity unique constraint as final authority. It does not implement semantic generation, Evidence creation, REST/Web or content closure.

### P1-7C — Evidence Extraction + Basic Report Generation

Done with external actual-source review `PASS`. The closed pipeline is `ReportSourceCollector -> ReportEvaluator -> EvidenceValidator -> ReportComposer -> ReportGenerationCoordinator`: it collects only the public Question/roster/authoritative utterance allowlist through the frozen watermark, validates every Human citation and exact quote without repair, and persists only complete trusted composition. A network-free deterministic evaluator supports tests. Positive-lease claims and status/`started_at` CAS protect stale workers; evaluation holds no DB scope; failure and atomic completion use short transactions; retry/re-entry reuse durable identity. It does not implement formal P3 scoring, a real provider, REST/Web or question authoring.

### P1-7D — Report REST/Web + V0.1 Content Closure

Done with external actual-source review `PASS`. The owner-only POST command invokes the accepted coordinator with server-owned V0.1 identity and the network-free deterministic evaluator; GET remains a strict independent read using `created_at DESC, id DESC` and projects completed-only content from the frozen trusted public source. A completed SessionPanel invokes the command and navigates to the reloadable report URL. The exact 4/4/4 immutable catalog is implemented; human content review passed and F001～F005 are closed.

### P1-7E — Composition Acceptance + Independent Acceptance

After separate approval, independently prove the complete P1-7 boundary and close P1-7 only if findings are resolved. P1-8 remains the separate full-P1 independent acceptance.

## 13. P1-7E required composed acceptance

P1-7E plans one network-free path through real product boundaries:

```text
select question
  -> create session
  -> exactly 1 Human + 3 AI
  -> complete all text phases
  -> COMPLETED
  -> generate report with deterministic/fake evaluator
  -> Web report view
  -> every evidence card resolves to an authoritative source utterance
  -> Browser reload
  -> API restart/recovery
  -> report remains durable, versioned and correct
```

The proof must also show owner isolation, source watermark correctness, Human-source enforcement, quote/phase/participant validation, stable read without GET regeneration, no private/evaluator/provider-secret leakage, and no real-provider call. P1-8 later performs separate full-P1 acceptance and is not folded into P1-7E.

## 14. Future implementation scope and STOP conditions

P1-7B～D may touch only the then-approved minimal report/evidence domain, persistence/migration, evaluator-neutral application boundary, report REST/OpenAPI-derived Web client, report Web feature, exact V0.1 Question Version content, directly affected tests and synchronized docs.

Stop and request review if implementation would require changing the master plan or an Accepted Decision; adding report state to the session lifecycle; treating Memory/model output as evidence authority; accepting evidence that cannot deterministically resolve to raw public source; exposing private/evaluator/provider/user-note material; destructive migration/source-event rewrite; choosing a vendor-specific evaluator or requiring a real provider; deferred queue/worker/infrastructure; resolving the score-versus-level TBD; or content beyond the exact V0.1 4/4/4 target.

P1-7A STOP-condition result: `NONE`.

## 15. P1-7A acceptance gate and status transition

P1-7A requires the changed set to remain this plan plus approved minimal `TASKS`, `ROADMAP`, `SCORING_RUBRIC`, `PRODUCT_REQUIREMENTS`, `DATABASE`, `API` and `PRIVACY_AND_SAFETY` synchronization; the master plan to remain byte-identical; no production/test/schema/migration/runtime API/OpenAPI/WebSocket/Web/provider/prompt/dependency/CI/infrastructure diff; resolving links and consistent state/TBD/source claims; `git diff --check`; and a `$gia-review-bundle` artifact.

At the P1-7A closeout checkpoint, governance was P1 `IN_PROGRESS`; P1-6 `DONE / CLOSED`; P1-7 `IN_PROGRESS`; P1-7A `DONE / DESIGN_SCOPE_FROZEN / ACTUAL_SOURCE_REVIEW_PASS`; and the later P1-7 subphases plus P1-8 had not begun. The current P1-7B status is recorded below.

The external actual-source review verdict is `PASS` against `group-interview-arena-review-20260909-234536.zip` / SHA-256 `4EA3FE5DD23775106C2602CAA2EC6DC68AC8DDA6D9895C5D74465F90390798F3`; material findings, new blockers and open findings are `NONE`. The reviewed bundle contained exactly the eight approved P1-7A docs-only changed files and no production/schema/migration/API runtime/Web/provider/dependency/CI/infrastructure drift. No real-provider call and no P1-7B implementation occurred.

## 16. P1-7B implementation checkpoint

P1-7B is `DONE / ACTUAL_SOURCE_REVIEW_PASS`. The accepted P1-7A boundary remains unchanged. The physical schema uses `REQUESTED/RUNNING/COMPLETED/FAILED`, the current project generation-lifecycle convention; generation identity is `(session_id, report_schema_version, derivation_version, source_through_sequence)`. Evidence uses same-session report/participant/event composite foreign keys, while `source_utterance_id` intentionally has no AI-only FK because Human utterances are authoritative event payload facts.

Fresh validation passes domain/model/migration tests, all API unit tests, all PostgreSQL integration tests, two-session concurrency, previous-head upgrade, downgrade/re-upgrade, exact 23-table catalog, Ruff, format and strict Pyright. Temporary database residue is zero, master-plan SHA-256 remains `2388A9660320406CB35D5354126AD71C6849A98DB7C4A356796CA951BF372F26`, implementation findings/open findings are `NONE`, and no real provider, REST/Web/OpenAPI, question content or P1-7C work occurred.

Finding-only remediation `P1-7B-F001` separates authoritative quote validation from whitespace-stripping semantic text validation: `EvidenceItemDraft.quote` now rejects empty/whitespace-only input while returning every accepted caller string byte-for-byte at the Python string level, including leading/trailing spaces, tabs and newlines. The required RED reproduced as `2 failed / 11 passed`; GREEN is `13 passed`; fresh full API unit validation is `536 passed / 228 deselected`; focused real-PostgreSQL report persistence is `17 passed`; Ruff, format and strict Pyright pass; residual test databases are zero. Migration `f1a17b17c008` and ORM persistence schema remain byte-identical to the initial P1-7B review bundle, so migration tests were not rerun for this domain-only remediation. External actual-source review final verdict is `PASS`; `P1-7B-F001` is `CLOSED`; material findings/new blockers/open findings are `NONE`. Accepted bundles are `gia-p1-7b-report-persistence-review-20260910-113955.zip` / SHA-256 `9FB2E9CF3E2BD3E865295F11C15764670E216BC0FED4CD9E1CD59DDE5F12AD9E` and `gia-p1-7b-f001-finding-only-review-20260910-120420.zip` / SHA-256 `CCA43286017D97133755285F8D5EFC6EFAF15F38DDD54D3DD07327C936AFE4B0`. P1-7B/P1-7C/P1-7D are `DONE / ACTUAL_SOURCE_REVIEW_PASS`; P1-7E and P1-8 remain `NOT_STARTED`.

## 17. P1-7C implementation checkpoint

The implementation is based on accepted main `e6c45acd89d7de0b48739113d8dad0356a91264d`. `ReportSourceSnapshot` is immutable and closed; its serialized form contains no Memory or private Question/Persona material. Evaluator proposals are closed and untrusted, item collections are capped at three without truncation, explicit zero-evidence output is valid, and any proposed invalid evidence fails the complete generation. Accepted quotes retain exact caller/source whitespace and Unicode form.

The coordinator allocates the P1-7B identity, claims with a database-round-tripped `started_at` token, releases the source read scope before evaluation, and performs completion plus all Evidence inserts atomically. Fresh RUNNING and COMPLETED identities do not evaluate; FAILED and lease-expired RUNNING identities can be reclaimed with a strictly newer token; old completion/failure CAS attempts persist nothing. P1-7C changes no ORM schema or migration, and Alembic remains `f1a17b17c008` with 23 product tables. External actual-source review passed; P1-7C is `DONE / ACTUAL_SOURCE_REVIEW_PASS`.

## 18. P1-7D implementation checkpoint

P1-7D is `DONE / ACTUAL_SOURCE_REVIEW_PASS`. `POST /sessions/{session_id}/report` supplies the real product caller for the accepted coordinator, with server-owned `1` / `basic-report/v1` identity, deterministic evaluator, existing CSRF/owner/eligibility rules and metadata-only response. `GET /sessions/{session_id}/report` performs owner-filtered selection of exactly the newest durable identity by `created_at DESC, id DESC`; a newer REQUESTED/RUNNING/FAILED row is never replaced by an older COMPLETED row. The GET path remains mutation-free and has no evaluator, coordinator, provider or generation caller.

The closed response contains safe durable metadata and `content = null` unless status is `COMPLETED`. Completed content reuses `ReportSourceCollector` through the frozen watermark and exposes the public Question, factual roster/utterance/phase overview, durable summary/priority and persisted evidence provenance. Strengths and improvements are each capped at three and ordered by `source_event_sequence ASC, evidence id ASC` solely for deterministic presentation, not scoring.

The completed SessionPanel invokes the typed POST and navigates to the Next.js route `/sessions/{sessionId}/report`, which consumes only the REST model and handles loading, unauthenticated, missing, REQUESTED, RUNNING, FAILED and COMPLETED states. The V0.1 catalog retains the original internal-validation bundle byte-for-byte at the model-definition level and adds exactly 11 immutable candidate bundles, producing 4/4/4 across the three registered types with four Persona Templates and three explicit question-specific AI stances per added version. Museum/rural-clinic/heatwave public facts are now decision-grade. The review manifest is [`../V01_CONTENT_REVIEW_MANIFEST.md`](../V01_CONTENT_REVIEW_MANIFEST.md). Content is `4/4/4 IMPLEMENTED / HUMAN_CONTENT_REVIEW_PASS`; P1-7E and P1-8 remain `NOT_STARTED`.

External actual-source review returned `PASS`; P1-7D-F001～F005 are `CLOSED`. External human content review returned `PASS` with material content findings `NONE OPEN`.

Fresh P1-7D verification is green: API unit `585 passed / 252 deselected`; PostgreSQL integration `252 passed / 585 deselected`; Web unit `195 passed`; Ruff, Ruff format, Pyright, Web lint/format/typecheck/build and OpenAPI drift all pass. The repository full Chromium entry point passes its `2 + 2` tests after selecting the retained internal-validation version explicitly from the 12-question catalog, and the dedicated report browser acceptance passes its single P1-7D test for completed-session CTA, coordinator generation, durable owner report, exact quote/provenance, reload, non-owner isolation and no-provider-call behavior. Development PostgreSQL is at the single `f1a17b17c008` head with 23 product tables; Alembic check passes; residual disposable databases and listeners on ports 3000/8000 are zero; migration, ORM schema, dependencies, lockfiles and the master plan remain unchanged.

## 19. P1-7D governance closeout

P1-7D external actual-source review is `PASS`; P1-7D-F001～F005 are `CLOSED`; V0.1 human content review is `PASS` for the exact 4/4/4 inventory (12 immutable Question Versions). The accepted implementation adds no schema change; Alembic remains at single head `f1a17b17c008` with 23 product tables. P1-7 remains `IN_PROGRESS`, and P1-7E remains `NOT_STARTED`.
