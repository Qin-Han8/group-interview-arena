# 数据库技术基线

- Status: P0 Data Architecture Baseline + P1-1～P1-4 schema implemented + P1-5A/P1-5B/P1-5C completed; P1-5C adds no schema
- Current phase: P1 — IN_PROGRESS
- Data architecture baseline established by: P0-2 — DONE
- Local PostgreSQL infrastructure: P0-4B — completed
- SQLAlchemy async foundation: P0-4C — completed
- Alembic migration foundation: P0-4D — completed
- PostgreSQL integration test foundation: P0-4E — completed
- Independent final review: P0-4F — completed
- P0-4 database foundation: DONE
- P0-5A identity data boundary: completed / approved
- P0-5B identity persistence: completed
- P0-5C backend auth runtime: completed
- Target version: V0.1 Internal Validation
- Business schema: identity, session, question/persona, durable phase timing, participant/floor audit, and AI Runtime persistence foundation (nineteen product tables)
- P1-1 status: P1-1A～E completed; independent final verdict PASS; P1-1 DONE
- P1-2/P1-3/P1-4 status: DONE; P1-5A freeze completed; P1-5B adds three product tables through linear revision `f1a15b15c005`
- Authority: 低于 [`PROJECT_MASTER_PLAN.md`](PROJECT_MASTER_PLAN.md) 和已确认的 [`DECISIONS.md`](DECISIONS.md)

## 文档目的

本文件记录 P0-2 已批准的数据技术基线、P0-4 完成状态、P0-5 identity persistence、P1-1 session persistence/transaction callers、P1-2B question/persona persistence foundation、P1-3B durable phase/timing fields、P1-4B participant/floor persistence，以及 P1-5B AI Runtime persistence。迁移目标 product tables 精确为十九张，Alembic single head 为 `f1a15b15c005`。

正式决策见 [`DECISIONS.md`](DECISIONS.md) `ADR-005`、`ADR-010`、`ADR-013`、`ADR-015`。

## Accepted technical baseline

- 数据库：PostgreSQL；
- P0-4 implementation baseline：PostgreSQL 18.x；
- ORM/data access：SQLAlchemy 2.x；
- Migration：Alembic；
- 模型边界：ORM model、Pydantic v2 API schema、domain object 分离；
- Entity ID：UUIDv4；
- Internal storage time：UTC；
- API timestamp：ISO 8601，UTC 输出使用 `Z`；
- Session event ordering：monotonic sequence，不依赖 UUID 顺序；
- Integration/migration tests：使用真实 PostgreSQL。

架构 ADR 冻结 PostgreSQL，不永久冻结数据库 major。P0-4 使用明确的 PostgreSQL 18.x 镜像版本，不得使用 `postgres:latest`；未来升级 major 需要独立评估。

## P0-4B implemented local infrastructure

- Compose：`infra/compose.yaml`；
- service：`postgres`，且 Compose 中没有其他 service；
- exact image：`postgres:18.4-trixie`（Docker Official Image）；
- verified server：PostgreSQL `18.4 (Debian 18.4-1.pgdg13+1)`；
- host binding：`127.0.0.1:5432`，container port：`5432`；
- persistence：Docker local named volume `postgres_data`；
- PostgreSQL 18 mount target：`/var/lib/postgresql`；
- healthcheck：`pg_isready`，使用容器内实际 `POSTGRES_USER` 和 `POSTGRES_DB`；
- configuration：Compose 显式 interpolation `POSTGRES_DB`、`POSTGRES_USER`、`POSTGRES_PASSWORD`，真实值只存在于被 Git ignore 的本地 `.env`；
- verified：Compose config、image pull、healthy、开发数据库、`SELECT 1`、mount inspection 与 restart smoke。

P0-4B 完成时没有 Redis 或业务 Schema，Alembic history 也尚未建立；P0-5B 后 Redis 仍未运行，但 identity schema 已按下文建立。

## P0-4C implemented async foundation

- direct dependencies：SQLAlchemy `2.0.52`、psycopg/psycopg-binary `3.3.4`；binary package 是本地开发 runtime baseline；
- SQLAlchemy URL dialect：只接受 `postgresql+psycopg://`；sqlite、asyncpg、psycopg2 与 malformed URL fail fast；
- configuration：`GIA_API_DATABASE_URL` 通过 `DatabaseSettings`/`SecretStr` 按需加载，是 server-only secret，不进入 `NEXT_PUBLIC_*`；现有 app startup 与 `/health` 不加载该配置；
- metadata：`DeclarativeBase` 使用 `ix`、`uq`、`ck`、`fk`、`pk` 稳定 naming convention；P0-4C 完成时 metadata 为空，P0-5B 后精确注册 `users` 与 `auth_sessions`；
- runtime：无 global engine；factory 使用 `create_async_engine()`，SQL echo disabled，pool 保持 SQLAlchemy defaults；session factory 使用 `async_sessionmaker[AsyncSession]` 与 `expire_on_commit=False`；caller 负责显式 transaction boundary；
- lifecycle：仅提供显式 `await engine.dispose()` 的薄 helper；尚无 FastAPI DB dependency、app lifespan 或启动连接；
- verification：14 项新增 DB foundation unit tests 不连接 PostgreSQL；真实 integration/migration tests 尚未执行。

P0-4E reusable PostgreSQL integration test suite 已完成。

## P0-4D implemented migration foundation

- dependency：Alembic `1.18.5`，constraint 为 `>=1.18.5,<1.19`，只位于 development dependency group；
- configuration：`apps/api/alembic.ini` 不保存 database URL 或 credential；`apps/api/migrations/env.py` 通过现有 `DatabaseSettings` 读取 server-only `GIA_API_DATABASE_URL`；
- runtime：只接受 `postgresql+psycopg`，使用 migration-specific `AsyncEngine`、`connection.run_sync(...)` 与 `NullPool`；Windows 使用 selector event loop 以兼容 psycopg async；
- metadata：P0-4D 建立 `target_metadata = Base.metadata`，当时 business table count 为 `0`；P0-5B 后 Alembic 通过显式 model registration 可靠加载两张 identity table；
- history：P0-4D 建立 revision `7c6ccd86b3c5`（`establish database baseline`），`down_revision = None`，`upgrade()`/`downgrade()` 均为 zero-op，不含业务 DDL；该 baseline 在 P0-5B 保持 immutable；
- runtime smoke：只在随机 `gia_p04d_*` 临时 PostgreSQL database 上执行 fresh upgrade、重复 upgrade、`current --check-heads`、`alembic check`、downgrade base 与 re-upgrade，均通过；head 状态下只产生 Alembic 自身的 `alembic_version` table，business table count 为 `0`；
- isolation：P0-4D smoke 当时未迁移 development database；临时数据库已精确删除，development database `SELECT 1` 回归通过；P0-5B 后的当前状态见 identity migration 结果；
- lifecycle：API startup 不自动执行 migration，现有 `/health` 仍不加载数据库配置。

上述真实 PostgreSQL 操作是 P0-4D migration runtime smoke，不是 P0-4E reusable integration test suite。

## P0-4E implemented integration test foundation

- config：test-only typed settings 从根目录被 Git ignore 的 `.env` 读取 `POSTGRES_*`；password 使用 `SecretStr`，不会成为 application runtime config；
- isolation：每个需要独立 schema state 的测试使用唯一 `gia_p04e_<uuid hex>` database；development database 与 `postgres`/`template0`/`template1` 受显式 guard 保护；
- administration：复用现有 psycopg 3 sync API 和 autocommit maintenance connection，只用于 test database create/drop；SQL identifier 使用 `psycopg.sql.Identifier`；
- cleanup：fixture `finally` 只终止并删除本轮精确 database，随后验证其不存在；不通配清理历史 database；
- application runtime：现有 `create_database_engine()` 与 `create_database_session_factory()` 在真实 PostgreSQL 上验证 `AsyncEngine`、`AsyncSession`、server major 18、commit 与显式 rollback；application DB runtime 保持 async；
- transaction probe：`gia_test_transaction_probe` 只存在于独立临时 database，不加入 `Base.metadata`、migration 或 product schema；
- migration：P0-4E 验收时 fresh → zero-op head、repeat upgrade、`current --check-heads`、`alembic check`、downgrade base、re-upgrade 与 final check 均通过；当时 business table count 为 `0`；
- regression：P0-4E 验收时 `Base.metadata.tables = 0`，development database 未迁移且没有 `alembic_version`；P0-5B 的后续状态见下节。

## Rejected paths

- 不使用 SQLite 作为正式开发路径或 PostgreSQL integration test 的临时替代；
- 不使用 SQLModel 将 API schema 与 ORM 永久统一；
- 当前不使用 UUIDv7；
- 当前不建立 internal integer ID + public UUID 的双 ID 体系；
- 不因总纲列出未来实体就在 P0-4 一次性创建全部表。

只有未来测量结果证明 UUIDv7 或双 ID 体系有实际收益时，才能提出新的技术决策。

## P0-4 completed implementation scope

P0-4 已依据 Accepted ADR 建立：

- Docker Compose；
- PostgreSQL 18.x service；
- 安全数据库连接配置和占位符；
- SQLAlchemy 2.x engine/session 基础；
- Alembic migration environment；
- 当前范围需要的最小基础模型；
- PostgreSQL integration tests；
- migration checks。

P0-4F 已独立确认上述基础的实现、运行态与质量门均通过。P0-4 不运行 Redis，不创建未来完整业务 Schema，也不提前实现支付、语音、成长或 V0.5/V1.0 实体。

## P0-5B implemented identity persistence

以下 P0-5A scoped baseline 已由 P0-5B 实现为 ORM model 与 Alembic migration；P0-5C 使用它们实现 backend auth runtime，但没有新增 table、column、constraint 或 migration，也不表示其他 product schema 已实现。

### `users`

- `id`：UUIDv4 primary key，stable internal `user_id`；
- `username`：`VARCHAR(32) UNIQUE NOT NULL`，保存 lowercase canonical ASCII login identifier，不使用 `CITEXT`，不承担 display name 职责；
- `password_hash`：`TEXT NOT NULL`，只保存 application 显式配置的 Argon2id PHC hash；
- `created_at`：`TIMESTAMPTZ NOT NULL`；
- `updated_at`：`TIMESTAMPTZ NOT NULL`。

当前 DEFER：email、phone、display name、role、status、`is_active`、`deleted_at`、`last_login_at` 与 verification timestamps。

### `auth_sessions`

- `id`：UUIDv4 primary key；
- `user_id`：`UUID NOT NULL`，foreign key → `users.id`，`ON DELETE CASCADE`；
- `token_hash`：`BYTEA UNIQUE NOT NULL`，只保存 security primitive 生成的 32-byte SHA-256 digest；
- `created_at`：`TIMESTAMPTZ NOT NULL`；
- `expires_at`：`TIMESTAMPTZ NOT NULL`，提供适当 expiry lookup index。

当前 DEFER：`revoked_at`、`last_seen_at`、IP、User-Agent、device metadata 与 refresh token。Raw session token 永不进入数据库；P0-5 baseline 使用 `secrets.token_urlsafe(32)` 生成 token，并使用 SHA-256 或等价 cryptographic digest 进行高熵 token lookup，不使用 Argon2 处理 session token。

### First identity migration result

- 保持 baseline revision `7c6ccd86b3c5` immutable；
- identity revision `4fe43b42641b`（`establish identity schema`）只创建 `users` 与 `auth_sessions`，`down_revision = 7c6ccd86b3c5`，revision count 为 2 且保持 single head；
- fresh isolated PostgreSQL database 已通过 upgrade、repeat upgrade、`current --check-heads`、`alembic check`、downgrade 至 baseline、identity table removal、re-upgrade、exact columns/constraints/indexes 与 final check；
- development database 在 exact-name/read-only preflight 确认 product table count 为 `0` 且 `alembic_version` absent 后，首次迁移到 identity head；
- 第二次 development `upgrade head` 为 no-op，当前 `users`/`auth_sessions` 行数均为 `0`；从未 downgrade development database；
- 本轮 `gia_p05b_%` 与 reusable harness `gia_p04e_%` residual audit 均为 `0`，没有 wildcard cleanup。

当前 development database 已迁移到 `4fe43b42641b`，product table set 精确为 `users`、`auth_sessions`，`alembic_version` 存在且为 identity head；两张 product table 均为空。

## Confirmed data principles from master plan

### 可追溯性

- 题目发布后不得直接覆盖；历史会话关联原题版本；
- 会话未来需要关联题目版本、参与者、发言、事件和报告；
- 报告未来需要关联证据、题目版本、模型版本和评分规则版本；
- 会话事件使用 session 内单调 sequence；
- 断线恢复以服务端状态为准。

### 生命周期与最小化

- 原始音频在报告后尽快删除，或仅在用户明确开启回放时限期保存；最终默认策略仍为 TBD；
- 转写文本必须允许用户删除；
- 删除训练记录时，结构化指标同步删除或匿名化；
- 模型日志不得保留不必要的完整敏感输入；
- 匿名训练数据必须单独授权并去标识化；
- 数据隔离、删除、审计和最小保留必须从首次业务 Schema 设计开始考虑。

## P1-1B session persistence foundation — implemented

P1-1A 冻结第一条 session foundation 的最小 schema；P1-1B 已按该 scope 实现 ORM、revision `f1a11d15c001` 和 PostgreSQL schema。当前 actual product tables 精确为 `users`、`auth_sessions`、`simulation_sessions`、`session_actions`、`discussion_events`。P1-1C 已在不改变 schema/migration 的前提下实现 REST、WebSocket 和 command/domain transaction callers。

### P1-1C implemented transaction callers

- session create 在单一 transaction 内写入 session、durable `last_sequence=1` 与 `session.created`；
- command transaction 以 owner predicate `SELECT ... FOR UPDATE` 锁定 aggregate row，先检查 `(session_id, action_id)`，再验证 state、写入 action、推进 state/watermark 并插入连续一到多条 events；
- duplicate semantic action 从 `(session_id, causation_action_id, sequence)` replay index 读取全部 stored events，保留原 sequence/occurred_at；conflict/invalid state 不写入 action/event/watermark；
- network send 发生在 transaction commit 后；send failure 由后续 PostgreSQL catch-up 恢复；每次 authentication/catch-up/command 使用短 session，WebSocket connection 不持有长期 transaction；
- P1-1C 没有新增 table/column/index/constraint/revision，Alembic head 与 exact five-table schema 保持不变。

### Implemented `simulation_sessions`

- `id UUID PRIMARY KEY`（UUIDv4）；
- `owner_user_id UUID NOT NULL` → `users.id ON DELETE CASCADE`；
- `status VARCHAR(32) NOT NULL`，当前 application values 为 `CREATED` / `ABORTED_USER`；
- `last_sequence BIGINT NOT NULL DEFAULT 0`，check `>= 0`；
- `created_at TIMESTAMPTZ NOT NULL`；
- `updated_at TIMESTAMPTZ NOT NULL`。

不使用 PostgreSQL native enum 或只允许当前两个状态的封闭 DB check。当前 owner authorization 查询由 primary key + owner predicate 完成，不为尚不存在的 list/filter caller 提前建立 owner-only index。

### Implemented `session_actions`

- composite primary key `(session_id, action_id)`；
- `session_id UUID NOT NULL` → `simulation_sessions.id ON DELETE CASCADE`；
- `action_id UUID NOT NULL`，作用域为单一 session；
- `command_version SMALLINT NOT NULL`，generic positive check；
- `command_type VARCHAR(64) NOT NULL`；
- `payload_digest BYTEA NOT NULL`，check `octet_length(...) = 32`；
- `created_at TIMESTAMPTZ NOT NULL`。

幂等记录随 session 持久化，不使用 memory-only cache，也不重复保存 command content。相同 action/type/version/digest 重试返回原 events；同 action 不同 semantic digest 返回 conflict 且无 mutation。

### Implemented `discussion_events`

- composite primary key `(session_id, sequence)`；
- `session_id UUID NOT NULL` → `simulation_sessions.id ON DELETE CASCADE`；
- `sequence BIGINT NOT NULL`，positive check；
- `event_version SMALLINT NOT NULL`，generic positive check；
- `event_type VARCHAR(64) NOT NULL`；
- nullable `causation_action_id UUID`；
- `payload JSONB NOT NULL`；
- `occurred_at TIMESTAMPTZ NOT NULL`；
- composite foreign key `(session_id, causation_action_id)` → `session_actions(session_id, action_id)`；
- index `(session_id, causation_action_id, sequence)`。

`causation_action_id` 不唯一，一个 action 可产生多条 ordered events。System/creation event 可使用 null causation。Event payload 是变化通知，不替代 future normalized question/participant/utterance records。

### Concurrency and evolution boundary

- 正式 sequence 从锁定的 `simulation_sessions.last_sequence` 分配 contiguous range；禁止 `MAX(sequence)+1`、UUID order 或 in-memory counter。
- action、state update、watermark 和所有 causal events 在一个短 PostgreSQL transaction 中 commit；WebSocket network send 在 commit 后。
- P1-1 不创建 `question_versions`、`session_participants`、`utterances`。它们在真实 caller 出现时以 additive migration 建立；session 后续增加 question version foreign key，participant 使用独立 one-to-many 表，utterance 持有 transcript/timing 并由 event payload 引用 id。
- P1-1 foundation session 可以作为 future question foreign key migration 的 nullable legacy row；从题目 caller 出现后由 application invariant 要求新的 runnable session 关联正式 version，不使用 fake question UUID。
- P2 voice/ASR/TTS fields、Redis/queue data 和评分/report schema 均不进入 P1-1。

完整 columns/constraints/indexes、transaction semantics 和 migration acceptance 见 [`exec-plans/P1-1_discussion-session-foundation.md`](exec-plans/P1-1_discussion-session-foundation.md)。

## P1-2 question/persona persistence — implemented in P1-2B

P1-2B 已按 P1-2A 冻结边界实现以下 additive persistence target。revision `f1a12b15c002` 线性接续 P1-1 head，历史 revisions 未改写。

### Implemented `question_templates`

- UUIDv4 `id` primary key；
- unique bounded stable `code`；
- `created_at TIMESTAMPTZ NOT NULL`；
- nullable `retired_at TIMESTAMPTZ`，check 保证 retirement 不早于 creation。

Template 不保存 title/type/difficulty/content/current version。首个 version 发布后的 code immutability 和 retirement 由 application domain boundary 管理。

### Implemented `question_versions`

- UUIDv4 `id` primary key；
- `question_template_id` foreign key with restrict/no-action history semantics；
- positive `version_number`，unique `(question_template_id, version_number)`；
- bounded scalar `title`、`question_type_code`、`background_domain_code`、`difficulty_code`、`scenario`、`objective`、positive bounded `estimated_minutes`；
- separately named JSONB fields for hard/soft constraints、stakeholders、options、reference dimensions、hidden conflicts、acceptable outcome patterns、phase prompts and safety tags；每列有 JSON array/object shape check，并且值只通过 closed domain schemas 写入；
- `created_at`、nullable `published_at`、nullable `retired_at`，check 保证 retired version 已发布且 retirement 不早于 publication。

不使用单一 catch-all content blob、generic extension metadata 或 question type/difficulty native PostgreSQL enum。Published payload、template link 和 version number 由 application service append-only；`retired_at` 是发布后唯一允许变化的 availability metadata。

### Implemented `persona_templates`

- UUIDv4 `id`、unique stable `code`、`display_name`、`speech_style_code`、`created_at`、nullable `retired_at`，check 保证 retirement 不早于 creation；
- explicit `NUMERIC(4,3)` columns with `[0,1]` checks：initiative、interrupt tendency、stance stability、persuasion threshold、novel idea rate、summary tendency、time awareness、detail focus、cooperation、error rate、off-topic rate；
- `support_user_bias NUMERIC(4,3)` with `[-1,1]` check；
- `average_turn_seconds SMALLINT` with `[10,90]` check。

Persona behavior parameters 不保存为 JSON。Domain write boundary 拒绝 bool、NaN/infinity、out-of-range 和超过三位小数。PostgreSQL `NUMERIC(4,3)` 加 range checks 提供 canonical storage 与 defense-in-depth；直接 SQL 写入的过精度 decimal 会按 PostgreSQL 语义 canonicalize，而不是作为 domain rejection。P1-2B 不为 scale rejection 增加 trigger 或 custom type。

### Implemented `question_persona_assignments`

- UUIDv4 `id` primary key；
- `question_version_id` foreign key；
- positive `slot_number SMALLINT`；
- `persona_template_id` foreign key with restrict/no-action semantics；
- unique `(question_version_id, slot_number)` and `(question_version_id, persona_template_id)`。

V0.1 exactly three contiguous slots 是 publication application invariant，不做永久 DB cardinality check。

### Implemented `persona_private_stances`

- `assignment_id` 同时为 primary key 和 one-to-one foreign key；
- bounded explicit `initial_position`、`concession_conditions`、nullable `private_information`、`red_lines`、nullable `preferred_group_role`；
- `priority_dimensions JSONB` 只保存 closed ordered `{code,weight}` list，并有 JSON array shape check；codes unique，weights 为 finite `[0,1]` Decimal。

Private Stance 属于具体 version assignment，不属于 Persona Template。Published version 下的 assignment/stance 不可 update/delete，且不进入普通 transport serialization。

### Implemented session binding and delete semantics

- 向既有 `simulation_sessions` additive 增加 nullable `question_version_id` foreign key → `question_versions.id`，使用 restrict/no-action historical semantics；
- P1-1 legacy rows 可以保持 null；P1-2C 后所有 API-created sessions 由 application invariant 要求 non-null selectable version；
- 新 version 或 retirement 不修改既有 session foreign key；
- future session deletion 不 cascade 到 shared question/persona source；
- draft-only cleanup、published retirement 和 CMS authorization 仍 Deferred，但 product service 不 hard-delete published/referenced versions 或 assigned Persona Templates。

P1-2B table set 是既有五张加上述五张，共十张；没有增加 participant、utterance、memory、provider、report、voice、Redis/queue 或 CMS/RBAC tables。Exact catalog、single-head、downgrade-to-P1-1/re-upgrade 和 drift checks 已由 disposable PostgreSQL tests 覆盖。P1-2C 没有 schema/migration 变更；application creation transaction 已强制 exact version FK，历史读取不按 template/latest 重解析。开发库经 exact-name、P1-1-head、五表、全零行只读 preflight 后仅向前迁移到 `f1a12b15c002`；repeat upgrade、head/drift 和十表全零行检查通过，未 downgrade 或写入 seed。

Publication service 对新 version/new assignment 先拒绝 retired Question Template 或 Persona Template；若 immutable bundle 已经存在且 exact-match，则在后续 retirement 后仍保持 no-op，以保留 deterministic seed 和历史解析语义。

## P1-3 durable phase data — P1-3B implemented

P1-3B 根据 P1-3A 冻结模型，以线性 Alembic revision `f1a13b15c003` 向既有 `simulation_sessions` additive 增加以下 columns；历史 revisions 未改写，product table count 仍为十张：

- `simulation_sessions.phase_started_at TIMESTAMPTZ NULL`：current timed phase 的 effective start；
- `simulation_sessions.phase_deadline_at TIMESTAMPTZ NULL`：current timed phase 的 authoritative server UTC deadline；
- `simulation_sessions.phase_duration_plan JSONB NULL`：在 accepted `session.start` 时由 server config 解析并冻结的 closed six-phase positive-integer seconds map。

`CREATED` 和既有 legacy rows 可以全部为 null；started active sessions 必须由 application invariant 保持三者完整，terminal `COMPLETED` / `ABORTED_USER` 清空 current start/deadline 但保留 immutable plan。数据库继续使用 evolvable `status VARCHAR`，不增加把当前状态集合永久锁死的 PostgreSQL native enum。

P1-3B database constraints are scoped to real invariants：`phase_started_at`/`phase_deadline_at` must be both null or both present with deadline after start；active timed statuses require current timing and a duration plan；non-active statuses require current timing to be null；non-null duration plans must be JSON objects with all six required timed phase keys。Exact positive-integer closed plan validation remains the domain/config write boundary.

Duration plan 是特定用途、closed-schema domain value，不是 generic metadata；Browser、ordinary logs/traces/errors 和 formal event payload 不接收完整 plan。它用于保证 app restart/config change 后未来 phase duration 仍由 session-start 时已冻结的配置决定。

Phase history 不另建 speculative table：现有 `discussion_events` 以 ordered `session.state_changed` v2 保存每次 effective start/deadline，current row 保存当前 projection。Historical v1 abort event 保持原样可读，不执行 data rewrite。

Deadline transition 继续锁定 `simulation_sessions` row，并在同一 transaction 内更新 status/current timing/`last_sequence`、插入所有 ordered events。System deadline events 使用 null causation；user start/abort events 关联现有 durable action。Concurrent timeout / user command races are reconciled under the same aggregate row lock before new user intent is applied；network send 仍在 commit 后。

完整 migration、catalog、rollback、concurrency、restart recovery 和 B～D acceptance 见 [`exec-plans/P1-3_session-state-machine.md`](exec-plans/P1-3_session-state-machine.md)。

## P1-4 floor-control data — P1-4B implemented

Linear revision `f1a14b15c004` preserves all historical revisions and additively creates six session-scoped product tables:

- `session_participants`：generalized `AI` / `HUMAN` / `SYSTEM` identity with `CANDIDATE` / `MODERATOR` role、positive stable seat order and `AVAILABLE` / `UNAVAILABLE` lifecycle. Closed checks enforce AI assignment、human user and system moderator identity shapes；same-session seat/user/assignment uniqueness prevents ambiguous roster identity；
- `speaking_opportunities`：durable participant + phase + closed opportunity kind (`PHASE_MANDATED` / `EXPLICIT_REQUEST` / `NOMINATION` / `FAIRNESS`) and accepted timestamp；
- `floor_decisions`：immutable causal audit facts with expected sequence、phase、closed outcome target shape、policy version、primary/supporting safe reasons、allowlisted JSONB metadata and decision timestamp；
- `floor_grants`：immutable participant/decision/opportunity/phase grant fact；one decision and one opportunity can cause at most one grant；
- `floor_releases`：one-to-one immutable end fact keyed by grant, with optional causal session action、safe reason and release timestamp；
- `floor_interventions`：one-to-one immutable intervention request fact tied to its decision and typed intervention kind。

`simulation_sessions.current_floor_grant_id` is nullable and constrained together with session `id` to a grant belonging to that same session. The aggregate row lock serializes mutations of this pointer, so a session has zero or one current grant even under concurrent grant requests. The historical rows are not updated to derive current state；grant release inserts `floor_releases` and clears only the current pointer.

All cross-session domain references use composite foreign keys. Historical decision/grant/release/intervention references use deferred no-action semantics so referenced facts cannot be independently removed while complete session/user deletion still cascades without circular-order failure. Supporting indexes cover session + phase/order/time access and causal action lookup.

The migration backfills the same four-seat roster for existing sessions that already reference a question version；legacy null-question sessions remain without fabricated participants. API session creation persists one human owner candidate and the three immutable question Persona Assignment candidates in the same transaction as `session.created`. The schema can represent a future `SYSTEM` moderator, but P1-4B does not create participant presence/provider/audio/video runtime.

Floor mutation reuses `session_actions` command identity and SHA-256 semantic digest, the locked session aggregate, contiguous `discussion_events` allocation and atomic commit. The durable facts are sufficient to reconstruct the single current owner and observable floor history after restart；candidate lists、derived fairness counters、timer calculations and ranking alternatives remain runtime calculations. Private Stance、persona calibration、prompt/provider internals、hidden weights and future scoring data have no floor columns or persisted metadata keys.

P1-4C adds no migration or column. Its internal scheduler reads the existing participant/opportunity/grant/release facts after acquiring the session row lock, derives runtime fairness deterministically, and writes into the existing action/decision/grant/intervention/event schema atomically. Therefore the linear head remains `f1a14b15c004` and the exact product-table count remains sixteen.

The exact schema, migration and concurrency gates are in [`exec-plans/P1-4_floor-control.md`](exec-plans/P1-4_floor-control.md)。

## P1-5A logical AI runtime data boundary — frozen

P1-5A intentionally creates no table、column、constraint、index or migration。Current Alembic head remains `f1a14b15c004` and product-table count remains sixteen。

Future persistence must represent these separate logical identities without collapsing them into `discussion_events.payload` or a provider raw-response blob:

- versioned Prompt asset identity；
- effective non-secret model configuration snapshot/version；
- logical Generation Request tied to exact session、AI participant、floor grant、phase、Question Version、Persona Assignment/Private Stance and Prompt Version；
- optional explicit provider attempt records when retry/fallback audit requires them；
- final Utterance tied to exactly one logical request and exact provenance；
- safe typed terminal failure when no final utterance exists。

Frozen invariants for later schema design:

- one logical generation request produces zero or one final utterance；retry/fallback cannot duplicate final content；
- historical utterance provenance does not follow mutable `latest` pointers and identifies the actual provider/model/effective configuration；
- provider credential、chain-of-thought、unnecessary complete rendered prompt/raw response and other participants' Private Stance are not persistence requirements；
- phase/grant stale output cannot become a final utterance；
- failure does not mutate session phase/deadline/current floor owner or scheduler decision；exact grant release remains a separate deterministic floor fact；
- deletion/retention must preserve necessary audit explainability while following prompt/input minimization and future user-data deletion rules。

P1-5A 当时将 exact table names、columns、foreign keys、attempt cardinality、event causation、retention and migration 留给单独批准的 implementation subphase；P1-5B 已完成其中的最小 persistence foundation。See [`exec-plans/P1-5_ai-runtime-foundation.md`](exec-plans/P1-5_ai-runtime-foundation.md)。

## P1-5B AI Runtime persistence foundation — implemented

Linear revision `f1a15b15c005` preserves all prior revisions and additively creates three provider-neutral tables:

- `prompt_versions`：UUID immutable identity、stable `prompt_key + version_number`、purpose、template text、SHA-256 content digest and creation/publication/retirement lifecycle。Domain publication is insert-or-exact-replay；a stable identity cannot be overwritten。Persona Template remains unchanged and stores neither prompt nor provider binding/secret。
- `llm_generation_requests`：one AI generation attempt linked to exact session、AI participant、floor grant and Prompt Version；stores provider/model identifiers、closed `{schema_version, configuration_version}` metadata、semantic request digest、timestamps and safe typed failure code。Lifecycle is evolvable `VARCHAR` with checks for `REQUESTED / RUNNING / COMPLETED / FAILED`；no PostgreSQL native enum or raw provider error/body is stored。
- `ai_utterances`：final displayable content linked to exact session、participant、floor grant and generation request。A composite deferred foreign key includes fixed `COMPLETED` request status, so a requested/running/failed generation cannot own a formal utterance；unique request and floor-grant constraints enforce at most one official utterance。

The application service locks the existing owner-scoped `simulation_sessions` aggregate before request/start/complete/fail mutation。Create/start/complete revalidate exact current grant、AI participant and phase；request identity uses a SHA-256 semantic digest for exact replay versus conflict。Completion changes request state and inserts the utterance in one transaction；constraint failure rolls both back。Failure records only typed reason/timing, creates no utterance, and does not change session status、phase timing、current floor pointer、scheduler fact or event sequence。Floor release remains a separate P1-4 control operation。

Historical generation context is recovered through immutable links: session → Question Version, participant → Persona Assignment/Template/Private Stance, request → Prompt Version + actual provider/model + non-secret configuration version, and utterance → successful request。Private stance content、persona calibration、hidden ranking、internal prompt variables、credential、API key、raw provider body、token/cost fields are absent from these tables and ordinary snapshots。

P1-5B itself added no API、WebSocket event、Web projection、provider client/SDK/interface、prompt rendering/orchestration、automatic generation、streaming、token/cost accounting、queue/worker、memory/RAG、scoring/report or voice behavior。

P1-5C adds application-only deterministic prompt/context assembly and generation orchestration while reusing these nineteen tables unchanged。Before authoritative generation create/claim/final-completion mutation, it holds the existing session aggregate row lock and reuses P1-3 `reconcile_due_for_locked_aggregate(...)` with server-authoritative current UTC。AI generation success/failure does not independently mutate lifecycle or floor authority；if overdue reconciliation advances phase/deadline, releases the old grant, appends ordered `floor.released` / `session.state_changed` events or advances discussion sequence, those persisted changes are P1-3 lifecycle facts, and the stale generation fails closed without an `ai_utterances` row。No migration or column is added。The development database was forward-migrated from the P1-4 revision to existing head `f1a15b15c005` before final validation；all original sixteen product-table row counts were preserved and the three P1-5B tables remained empty before tests。

## Future business schema

总纲提到 `users`、题目版本、角色模板、会话、参与者、阶段、发言、讨论事件、结构化记忆、报告、证据、训练、反馈、模型调用和审计等未来领域概念。

除上述已实现 identity/session/question/persona/phase/floor schema 外，其余仍只是长期领域导航：

- P1-5B implements Prompt Version、Generation Request and final AI Utterance persistence；provider attempts beyond the current one-request/one-attempt identity and detailed retention/deletion policy remain Deferred；memory、report、evidence、training and feedback schema also remain Deferred；
- V0.1 最小实体集合仍需在 P1 业务设计中确认；
- 支付、权益、语音和成长数据不得提前进入 V0.1 Schema；
- P0/V0.1 initial identity boundary 已由 `ADR-015` 确认；公开身份扩展与 recovery 仍 Deferred。

## TBD

- Implemented：P1-2 question/persona 五表与 nullable session version reference；
- Implemented：P1-4B generalized participant、opportunity、decision、grant、release 与 intervention schema；
- Implemented in P1-5B：Prompt Version、closed configuration-version provenance、Generation Request lifecycle and successful final AI Utterance relation；
- Deferred：participant runtime/presence、memory、report 等后续最小实体和正式 Schema；
- TBD：未来 phone/WeChat identity mapping 的具体 Schema；
- TBD：verified recovery identity、account recovery 与账号删除的完整数据语义；
- TBD：原始音频是否默认完全不保存（总纲第 37 节）；
- TBD：各类数据的精确保留期限；
- TBD：删除、匿名化和审计的具体规则；
- TBD：结构化记忆、证据和模型调用日志 Schema；
- TBD：未来多租户或机构隔离模型。

## Future work

- P0-5C：FastAPI lifespan/request dependency 已成为现有 async DB runtime 的第一个 application caller；真实 PostgreSQL auth integration 只使用迁移到 head 的隔离临时数据库，development DB 保持 head `4fe43b42641b` 且两张表均为 0 rows；
- P0-5D：completed；browser closure 已实现，existing Cookie/CORS/CSRF/shared trusted-origin boundary 已生效；P1 不得创建第二套 trusted-origin config；
- P1：`IN_PROGRESS`；P1-1～P1-4 `DONE`；P1-5A/P1-5B/P1-5C `DONE`；current migration head `f1a15b15c005`、精确十九张 product tables；P1-5C schema delta 为零；真实 provider、automatic runtime、记忆和报告继续 Deferred；
- P2～P4：仅随获批范围增加音频、评分训练和商业化数据。

## 与其他文档关系

- 技术决策：[`DECISIONS.md`](DECISIONS.md)
- 架构边界：[`ARCHITECTURE.md`](ARCHITECTURE.md)
- API 契约：[`API.md`](API.md)
- 数据安全和删除：[`PRIVACY_AND_SAFETY.md`](PRIVACY_AND_SAFETY.md)
- 当前任务：[`TASKS.md`](TASKS.md)
