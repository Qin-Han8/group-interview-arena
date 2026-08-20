# P1-2 Question & Persona Foundation Execution Plan

Status: `P1 IN_PROGRESS`; `P1-2 DONE`; `P1-2A` through `P1-2D completed`; independent final verdict `PASS`; `P1-3 not started / awaiting explicit approval`

Target version: `V0.1 Internal Validation`

Product baseline: [`PROJECT_MASTER_PLAN.md`](../PROJECT_MASTER_PLAN.md)

Accepted decisions: [`D-007`](../DECISIONS.md#2-已确认产品决策索引), [`D-012`](../DECISIONS.md#2-已确认产品决策索引), [`D-013`](../DECISIONS.md#2-已确认产品决策索引), [`D-014`](../DECISIONS.md#2-已确认产品决策索引), [`ADR-003`](../DECISIONS.md#adr-003--fastapi-作为主要业务后端), [`ADR-005`](../DECISIONS.md#adr-005--postgresqlsqlalchemy-与-alembic-数据基线), [`ADR-006`](../DECISIONS.md#adr-006--rest-与-websocket-通信边界), [`ADR-007`](../DECISIONS.md#adr-007--api-契约生成策略), [`ADR-011`](../DECISIONS.md#adr-011--轻量领域导向混合模块架构), [`ADR-012`](../DECISIONS.md#adr-012--分阶段测试与质量工具策略), [`ADR-013`](../DECISIONS.md#adr-013--配置错误与结构化日志基线), [`ADR-014`](../DECISIONS.md#adr-014--provider-neutral-ai-与自定义讨论编排), [`ADR-015`](../DECISIONS.md#adr-015--initial-identity-and-browser-session-boundary)

P1-2A baseline: committed `main` at `895a1d432150af198373f43dedd5a97af23f1ea9`; [`PROJECT_MASTER_PLAN.md`](../PROJECT_MASTER_PLAN.md) SHA-256 `2388A9660320406CB35D5354126AD71C6849A98DB7C4A356796CA951BF372F26`

## Goal

建立 P1 文字讨论闭环可依赖的最小题目与人格基础：稳定的 `Question Template` identity 拥有 append-only `Question Version`；每个发布版本携带 V0.1 三个 AI 席位的 `Persona Assignment` 和题目特定 `Private Stance`；后续创建的 session 绑定 immutable `question_version_id`，所以新版本、下线或模板退休都不会改变历史 session 的题目、分配或私有立场。

P1-2 只建立题目/人格的 persistence、domain、最小 authenticated read/session caller 和 Web 选择/展示 vertical slice。它不实现完整 CMS、正式题库生产、参与者、逐句发言、完整状态机、调度、记忆、LLM/provider、评分、报告或语音。

## Current baseline

- P1-1 independent verdict 为 `PASS`；当前 Alembic single head 为 `f1a11d15c001`，product tables 精确为 `users`、`auth_sessions`、`simulation_sessions`、`session_actions`、`discussion_events`。
- `simulation_sessions` 已是 session aggregate root，并拥有 durable `last_sequence`、action idempotency 和 formal event ordering；当前没有 question、participant、utterance 或 persona columns/tables。
- `POST /sessions` 当前无 request body，只创建 `CREATED` session。P1-2C 才会把新的 session creation caller 改为显式选择 published/non-retired `question_version_id`。
- P1-1 已冻结 additive evolution：P1-1 legacy rows 可保持 nullable question reference；真实 question caller 出现后，新 session 由 application invariant 强制绑定版本。
- FastAPI/domain/PostgreSQL 是业务权威；Next.js 只使用 generated REST contract 和 server-authoritative session snapshot。
- REST 继续复用 opaque Cookie、owner authorization、exact Origin 和 `X-GIA-CSRF: 1`；普通 browser API 不得读取 Private Stance 或内部题目校准字段。
- 当前没有 LLM caller，因此 P1-2 不创建 `LLMProvider`、fake provider、prompt runtime 或未来 AI adapter。

## Four-stage decomposition

1. **P1-2A — Design freeze**：`completed`。本轮 docs-only；冻结 domain、lifecycle、security、B～D scope/callers/acceptance/testing，并同步必要文档。不修改 runtime、tests、schema/migrations、dependencies/lockfiles 或 CI。
2. **P1-2B — Persistence + Domain + Seed foundation**：`completed`。新增最小 ORM/migration、纯 domain validation、application-owned idempotent seed 和真实 PostgreSQL tests；未新增 HTTP/WS/Web caller。
3. **P1-2C — API + Session integration + minimal Web vertical slice**：`completed`。已增加 authenticated safe question reads，使新 session 绑定 immutable version，并增加最小 Web 选题/题面展示；未创建 participant/utterance/AI loop。
4. **P1-2D — Independent acceptance + closeout**：`completed`。已从 committed source 独立复核 P1-2B/C 的 schema、immutability、non-disclosure、history traceability 和 browser vertical slice；未增加新业务能力，verdict `PASS`。

P1-2B、P1-2C、P1-2D 均需单独明确批准。P1-2A 完成后不得自动开始 P1-2B。

## Frozen domain model

### 1. Question Template — stable logical identity

`QuestionTemplate` 只表示一道逻辑题目的长期身份和生命周期容器：

- `id`: UUIDv4 primary identity；session 和外部 caller 不使用 mutable title/code 作为 foreign key。
- `code`: 稳定、唯一、受限 uppercase snake-case internal code；首个 version 发布后不可改名复用。
- `created_at` and nullable `retired_at`。

Template 不持有 title、scenario、objective、question type、difficulty、options、constraints、persona assignments 或“当前内容”。这些全部属于具体 version。Template 退休只阻止创建/发现未来可选内容，不改变既有 versions 或历史 session。

不建立 mutable `current_version_id` 作为历史权威。当前可选版本由 published/non-retired version query 决定；新版本发布不会覆盖旧版本。

### 2. Question Version — immutable published snapshot

`QuestionVersion` 由全局 UUIDv4 `id` 标识，并以 `(question_template_id, version_number)` 唯一。它拥有一次群面所需的完整版本化内容：

- scalar content：`title`、`question_type_code`、`background_domain_code`、`difficulty_code`、`scenario`、`objective`、`estimated_minutes`；
- structured collections：hard/soft constraints、stakeholders、options、reference dimensions、hidden conflicts、acceptable outcome patterns、phase prompts、safety tags；
- lifecycle：`created_at`、nullable `published_at`、nullable `retired_at`。

Lifecycle 由 timestamps 表达，不使用 PostgreSQL native enum：

- draft：`published_at IS NULL` and `retired_at IS NULL`；
- selectable published：`published_at IS NOT NULL` and `retired_at IS NULL`；
- retired historical：`published_at IS NOT NULL` and `retired_at IS NOT NULL`。

`retired_at` 是发布后唯一允许变化的 availability metadata；所有 content、version number、template link、assignment 和 stance 在 `published_at` 之后不可 update/replace。修订任何内容必须插入同一 template 下的新 version。退休旧 version 不影响 owner 通过历史 session 加载其 safe public snapshot。

### 3. Structured question content boundary

P1-2B 不允许一个 catch-all `content`/`payload` JSONB 保存整道题，也不允许 transport/domain 传递 arbitrary `dict[str, object]` 作为题目权威。持久化采用 scalar columns 加以下分别命名的 JSONB columns，每列都有独立 closed Pydantic/domain item schema、bounded count/length、stable item key 和 database-level JSON array/object shape check：

- `hard_constraints` / `soft_constraints`: ordered `ConstraintItem{key,text}` arrays；
- `stakeholders`: ordered `StakeholderItem{key,name,description}` array；
- `options`: ordered `QuestionOption{key,label,description}` array；
- `reference_dimensions`: ordered `ReferenceDimension{key,name,description}` array；
- `hidden_conflicts`: ordered `InternalTextItem{key,text}` array；
- `acceptable_outcome_patterns`: ordered `InternalTextItem{key,text}` array；
- `phase_prompts`: closed `PhasePromptSet` keyed only by application-supported discussion phase codes；
- `safety_tags`: unique bounded code array。

Domain construction rejects unknown item fields、duplicate keys、blank/oversized text、invalid counts、non-finite numbers and question-type-specific invalid combinations。ORM JSON values are adapter details; domain and API models stay distinct. P1-2B creates no generic extension/metadata JSON escape hatch. Future normalization is additive only when a real query/edit caller needs item-level relational access。

`question_type_code`、`difficulty_code` and `background_domain_code` use bounded `VARCHAR` plus application registries and syntax validation, not PostgreSQL native enums or closed value check constraints. V0.1 question types initially register `ORDERING_SELECTION`、`RESOURCE_ALLOCATION`、`PLAN_DESIGN`; the initial difficulty registry contains `STANDARD` and may grow additively without a database enum migration。

Reference dimensions、hidden conflicts、acceptable patterns、phase prompts and safety tags are internal calibration/orchestration data. They are not part of the ordinary browser question response。

### 4. Persona Template — stable behavior only

`PersonaTemplate` describes stable cross-question behavior probabilities and presentation metadata. It never owns a concrete answer, preferred option, hidden fact or question-specific goal。

Fields are explicit columns, not a generic parameter blob：

- identity/presentation：UUIDv4 `id`、unique stable `code`、`display_name`、bounded `speech_style_code`、`created_at`、nullable `retired_at`；
- probability parameters in `[0.000, 1.000]`：`initiative`、`interrupt_tendency`、`stance_stability`、`persuasion_threshold`、`novel_idea_rate`、`summary_tendency`、`time_awareness`、`detail_focus`、`cooperation`、`error_rate`、`off_topic_rate`；
- signed parameter in `[-1.000, 1.000]`：`support_user_bias`；V0.1 seeds keep it `0.000` so personas do not help the user刷分；
- bounded integer：`average_turn_seconds` in `[10, 90]`。

API/domain validation rejects bool-as-number、NaN/infinity、out-of-range values and precision beyond three decimal places；domain uses canonical `Decimal` values，ORM uses `NUMERIC(4,3)` plus matching range checks for canonical storage. Direct SQL overprecision follows PostgreSQL numeric canonicalization；P1-2B adds no trigger/custom type for scale rejection. `average_turn_seconds` uses `SMALLINT` with a DB range check。Database constraints are defense-in-depth；domain validation is the write boundary。

Seeded/assigned V0.1 persona templates are immutable behavior records. Calibration that changes their parameters creates a successor template record/code rather than silently rewriting historical behavior. `retired_at` only removes a template from future assignment choices。

### 5. Question-version Persona Assignment and Private Stance

`QuestionPersonaAssignment` belongs to exactly one `QuestionVersion` and references exactly one `PersonaTemplate`：

- UUIDv4 `id`；
- `question_version_id`；
- `slot_number` positive small integer；
- `persona_template_id`；
- unique `(question_version_id, slot_number)` and `(question_version_id, persona_template_id)` for the V0.1 distinct-persona assignment set。

V0.1 publication validation requires exactly three assignments with contiguous slots `1..3` and a complete Private Stance for each assignment. The database does not hard-code “3” so a future approved version can evolve without a destructive enum/check migration。

`PrivateStance` is a required one-to-one child whose primary/foreign key is `assignment_id`. It uses explicit bounded fields rather than a catch-all JSON blob：

- `initial_position`；
- `priority_dimensions`: closed ordered list of `{code,weight}` with unique codes and finite weights `[0.000,1.000]`；
- `concession_conditions`；
- nullable `private_information`；
- `red_lines`；
- nullable `preferred_group_role`。

Assignment and stance form part of the immutable published question-version bundle. A Persona Template may be reused across versions, but its stance never is；the same persona can support different positions in different question versions。

## V0.1 persona seed set

P1-2B seeds exactly these four stable behavior templates. Exact values are initial calibration baselines, not personality scores exposed to users：

| Code | Display name | Distinguishing baseline |
|---|---|---|
| `LOGIC_ANALYST` | 逻辑分析者 | high detail/stance/evidence discipline; low interruption/off-topic |
| `CREATIVE_DIVERGER` | 创意发散者 | high novelty/initiative; lower convergence/time awareness |
| `GENTLE_COORDINATOR` | 温和协调者 | high cooperation/summary; very low interruption |
| `ASSERTIVE_FACILITATOR` | 强势控场者 | high initiative/interruption/stance; moderate cooperation and not always correct |

P1-2B source fixtures must define every numeric field explicitly and be reviewed in the implementation diff. Seed reruns compare canonical persisted values：missing rows are inserted；exact rows are no-op；drift in an existing stable code fails loudly and never overwrites a referenced template。

The 12 formal V0.1 questions are Deferred. To give P1-2C a real caller, P1-2B may seed exactly one clearly labeled `INTERNAL_VALIDATION` manually-authored question bundle with one published version and three assignments/stances. It is test/development content, is excluded from the “12 formal questions” acceptance, and must not be represented as production-reviewed content。

## Publication, retirement and deletion invariants

- Publishing validates the entire version atomically：closed content schemas、registered codes、three V0.1 assignments、distinct personas、complete private stances and no draft mutation race。
- No ordinary update service exists for a published payload. Any future CMS mutation path must call the same domain publication/immutability boundary。
- `simulation_sessions.question_version_id` references the immutable version with `ON DELETE RESTRICT`/default no-action semantics. P1-1 legacy rows remain nullable；P1-2C application creation requires a non-null selectable version。
- Template/version/persona “下线” is retirement, not destructive deletion. Retirement changes discovery/selection only；it does not cascade into sessions or reports。
- Template/Persona Template retirement cannot precede creation；Question Version retirement requires publication and cannot precede `published_at`。
- New version publication rejects a retired Question Template；new assignment rejects a retired Persona Template。An already-persisted exact-match immutable bundle remains a no-op after later retirement so historical rows stay resolvable and deterministic seed reruns do not mutate them。
- Draft versions with no session reference may be hard-deleted by a future authorized CMS workflow；that workflow is Deferred. Published versions and any version referenced by a session are never hard-deleted through product services。
- Persona templates referenced by any assignment are not hard-deleted. Assignments/stances attached to a published version are not edited or deleted。
- Deleting a user-owned training session may delete that session aggregate under the future approved retention workflow, but never deletes shared question/persona source records。
- A newer version under the same template has a new version UUID and does not redirect or rewrite existing session foreign keys。

## Private Stance isolation and future AI boundary

- Ordinary browser REST responses、generated TypeScript contract、WebSocket events、session snapshot、logs、traces and errors must not contain private stance fields, internal reference dimensions, hidden conflicts, acceptable outcome patterns or phase prompts。
- P1-2B keeps private types inside the server-side question/persona module and persistence layer；it does not define a public API schema for them。
- P1-2C session creation validates assignment completeness server-side but returns only `question_version_id` and safe public question fields. It does not return persona labels/parameters because participant creation is Deferred。
- When a later explicitly approved orchestrator/AI caller exists, an internal application service may resolve one assignment belonging to the session-bound version and return only that assignment's Persona Template behavior plus its own Private Stance. It must not expose other assignments' stances to the candidate context, provider adapter, browser or logs。
- Provider SDK objects、prompt text and model invocation records remain absent in P1-2. The future caller boundary is documented, not pre-built as an unused interface/factory。

## P1-2B — Persistence + Domain + Seed foundation

### Scope

- Add domain types/validators for the four frozen objects and structured value objects, separate from ORM and API schemas。
- Add exactly `question_templates`、`question_versions`、`persona_templates`、`question_persona_assignments` and `persona_private_stances` tables plus nullable `simulation_sessions.question_version_id`。
- Add one linear Alembic revision on current head; preserve all historical revisions byte-for-byte。
- Add application-owned idempotent seed command/data for the four Persona Templates and, if required for the next caller, the one explicit internal-validation question bundle。
- Add no HTTP/WS route, Web UI, participant/utterance, provider, CMS/RBAC or dependency。

### Dependency

- P1-2A completed and separately approved P1-2B start；P1-1 `DONE`；current single migration head and safe PostgreSQL disposable-test harness；Accepted `ADR-005`、`ADR-011`、`ADR-012`、`ADR-015` 中相关边界。

### Expected caller boundary

- Domain constructors/publication service are the only write-validation boundary。
- Seed CLI/application function is the only runtime writer in P1-2B；it uses an explicit transaction and fails on stable-code drift。
- ORM records do not escape as API/domain objects. No browser or provider caller exists yet。

### Acceptance criteria

- Exact schema、FK/delete behavior、generic checks、indexes and nullable legacy session reference match this plan；no native DB enum or catch-all question/persona blob。
- Published bundle mutation/replacement is rejected by application service；new version insertion succeeds without changing the old version。
- Domain rejects invalid numeric range/precision and malformed structured content；DB range checks reject out-of-range values while `NUMERIC(4,3)` provides canonical storage rather than a separate overprecision rejection mechanism。
- Seed is deterministic/idempotent, creates exactly four persona codes, refuses drift and never logs private stance/content。
- Fresh/repeat upgrade、single head、`alembic check`、downgrade to P1-1 head、re-upgrade and exact PostgreSQL catalog tests pass in disposable databases。
- Existing P1-1 session/action/event behavior remains green；no route/OpenAPI/Web/dependency/lockfile/CI changes。

### Testing strategy

- TDD pure-domain tests for code syntax、closed structures、publication completeness、immutability and persona numeric boundaries。
- ORM/static tests for exact metadata and no speculative tables/columns。
- Real PostgreSQL migration/schema/FK/retirement/history/seed integration tests；no SQLite。
- Seed rerun and drift-negative tests using isolated migrated databases。
- Existing API non-integration/integration/full regression plus Ruff、format、Pyright、Alembic and `git diff --check`。

## P1-2C — API + Session integration + minimal Web vertical slice

### Scope

- Add authenticated `GET /questions` for selectable published/non-retired summaries and `GET /questions/{question_version_id}` for safe published public content. A retired published version remains retrievable by immutable ID for historical session display；draft/missing use non-disclosing not-found semantics。
- Change authenticated/CSRF-protected `POST /sessions` to require `{question_version_id}`；create atomically validates a selectable version and stores the FK while preserving P1-1 `session.created` ordering/idempotency semantics。
- Extend owner-only session snapshot with `question_version_id`；legacy nullable rows remain representable but are not newly creatable through the API。
- Add minimal Web flow：load selectable questions、show safe title/type/difficulty、select one、create session、render safe public scenario/objective/constraints/options and continue using the existing authoritative session panel/reload path。
- Update FastAPI OpenAPI and generated Web derivative. No question mutation/admin endpoint, persona endpoint, WebSocket contract expansion, participant/utterance or AI behavior。

### Dependency

- Separately approved P1-2C；P1-2B implementation/validation completed；seeded internal validation bundle or equivalent isolated caller fixture available；existing P1-1 REST/WS/Web contract remains authoritative。

### Expected caller boundary

- Browser receives a purpose-built public projection only. It never receives internal calibration fields, persona parameters/labels/assignment rows or Private Stance。
- Session service receives a validated immutable version identity, not template identity, title or mutable “latest” alias。
- Web uses generated REST client and existing realtime client；Next.js does not duplicate selection/publication rules。

### Acceptance criteria

- New sessions always persist the exact selected published/non-retired version；retired/draft/missing versions cannot start new sessions。
- Publishing a newer version or retiring the selected version after session creation does not change the session FK or historical safe content loaded by immutable ID。
- Ordinary OpenAPI/JSON/WS/browser/log/span/error surfaces contain none of the private/internal fields；negative sentinel tests prove non-disclosure。
- Existing owner isolation、CSRF/CORS/Origin、sequence、action replay、gap reload and session reload semantics remain intact。
- Minimal authenticated browser → FastAPI → PostgreSQL flow selects a question, creates a version-bound session, displays safe content, reloads the same version and cleans all temporary resources。
- No CMS/RBAC、participant/utterance、LLM/provider、scheduler/memory、score/report、voice、Redis/queue or new dependency unless a separately approved real blocker is proven。

### Testing strategy

- REST contract/serialization tests for public allowlists、auth、CSRF、retired history and safe 404/error semantics。
- PostgreSQL integration tests for create transaction、FK binding、new-version independence、retirement and legacy-null snapshot。
- Web unit/component tests for list/select/create/public render/empty/error/reload states and private sentinel absence。
- Real disposable PostgreSQL + Next/Chromium/Uvicorn E2E for the complete minimal vertical slice, followed by database/process/port/artifact cleanup checks。
- Full API/Web quality、build、OpenAPI drift、Alembic and P1-1 realtime regressions required at checkpoint。

## P1-2D — Independent acceptance + closeout

### Scope

- Read-only independent review from committed P1-2B/C source by default；only separately approved finding remediation may change implementation。
- Reproduce schema/migration、seed、immutability、private non-disclosure、session binding/history and browser evidence。
- Confirm all explicit deferrals remain absent and documentation matches actual source。

### Dependency

- P1-2B and P1-2C completed, actual-source review/remediation complete, reviewable committed baseline available, and separate explicit P1-2D approval。

### Expected caller boundary

- No new caller. Review only the implemented persistence/domain/REST/session/Web boundaries and their evidence。

### Acceptance criteria

- Independent verdict `PASS` with no unresolved correctness、privacy/security、migration integrity、API compatibility or material-rework finding。
- Full required API/Web/PostgreSQL/Chromium gates reproduce with zero skips where required；temporary resources are clean。
- P1-2A～D evidence matches actual Git source and no deferred capability leaked into implementation。
- Only after PASS mark P1-2 `DONE`；the next P1 task remains not started and separately approved。

### Testing strategy

- Re-run all risk-matched P1-2B/C gates from a clean committed state instead of relying on prior PASS prose。
- Independently inspect actual schemas/contracts and run targeted attacker-controlled sentinel/non-disclosure cases。
- Re-run full regression/build/OpenAPI/Alembic/real-browser checkpoint and exact cleanup/status checks。

## Explicit deferrals

- Complete CMS、RBAC、approval workflow、draft editing UI and content operations audit UI。
- AI automatic question generation/variants and unrestricted model-authored publication。
- Production of the 12 formal V0.1 questions beyond the optional single internal-validation fixture。
- LLM/provider/model、prompt runtime、model invocation and fake provider。
- Full session state machine、scheduler/floor control、structured memory and proactive events。
- Session participants、utterances、transcripts and AI candidate runtime instances。
- Scoring、report、evidence、objective metrics and drills。
- Redis、cross-process broadcast、queue/worker and voice/ASR/TTS。
- Industry-pack/plugin architecture、custom user-uploaded questions and public content marketplace。
- Persona calibration UI、persona version graph and V1.0 6～8 persona expansion。

## Decisions and open items

- No new Accepted or Proposed ADR is required。The question-version/persona-stance choices are P1-2 implementation boundaries frozen by this execution plan and the corresponding domain documents；they do not independently change the master plan or existing Accepted architecture。
- No conflict with D-001～D-015 or Accepted ADRs was found at P1-2A。
- Exact 12-question content、review owners、CMS permissions、LLM/provider、full discussion contract and formal persona calibration/blind-test thresholds remain Deferred/TBD and do not block P1-2B foundation。
- The one allowed internal-validation fixture is not one of the 12 formal content deliverables and must stay labeled accordingly。

## Risks and stop conditions

- **BLOCKER — authority conflict**：any later-discovered conflict with the master plan or an Accepted Decision stops implementation；do not rewrite the higher authority。
- **BLOCKER — baseline/user changes**：overlapping unknown working-tree changes、non-linear migration head or ambiguous development database stops P1-2B/C；never reset/restore/clean/stash。
- **HIGH — historical mutation**：session binding template/latest alias、published payload overwrite、assignment/stance replacement or destructive retirement blocks the phase。
- **HIGH — private leakage**：Private Stance/internal calibration in ordinary API、OpenAPI derivative、browser、WS event、log、trace or error blocks the phase。
- **HIGH — unconstrained structure**：a single arbitrary question/persona JSON blob or unvalidated dict boundary blocks P1-2B acceptance。
- **HIGH — numeric drift**：bool/NaN/infinity/out-of-range/over-precision persona parameters accepted at the write boundary blocks P1-2B。
- **MEDIUM — enum lock-in**：PostgreSQL native enum or closed DB check for question type/difficulty creates avoidable migration friction and must be corrected。
- **SCOPE STOP**：new dependency、CMS/RBAC、provider、participant/utterance、orchestrator/memory、score/report、voice、Redis/queue or industry plugin requires separate approval。

## Progress

- [x] User explicitly approved P1-2A。
- [x] Committed `main`、clean working tree、P1-1 actual source and immutable master-plan hash verified。
- [x] No higher-authority conflict or blocker found。
- [x] Question Template / immutable Question Version / Persona Template / version-specific Assignment + Private Stance frozen。
- [x] Publication、retirement、deletion、numeric validation、private isolation and future AI caller boundaries frozen。
- [x] P1-2B～D scope、dependencies、expected callers、acceptance and testing strategies frozen。
- [x] P1-2A docs-only synchronization and validation completed。
- [x] P1-2B implementation and risk-matched validation completed。
- [x] P1-2C safe API、immutable session binding、minimal Web caller and risk-matched validation completed。
- [x] P1-2D independent final acceptance completed；verdict `PASS`；findings 无 blocker/material item。
- [x] P1-2 `DONE`；P1 remains `IN_PROGRESS`；P1-3 not started / awaiting explicit approval。
