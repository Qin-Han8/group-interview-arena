# 数据库技术基线

- Status: P0 Data Architecture Baseline
- Current phase: P0
- Data architecture baseline established by: P0-2 — DONE
- Local PostgreSQL infrastructure: P0-4B — completed
- SQLAlchemy async foundation: P0-4C — completed
- Alembic migration foundation: P0-4D — completed
- PostgreSQL integration test foundation: P0-4E — completed
- Target version: V0.1 Internal Validation
- Business schema: Not started
- Authority: 低于 [`PROJECT_MASTER_PLAN.md`](PROJECT_MASTER_PLAN.md) 和已确认的 [`DECISIONS.md`](DECISIONS.md)

## 文档目的

本文件记录 P0-2 已批准的数据技术基线、数据边界和 P0-4 实施状态。P0-4B 已建立本地 PostgreSQL infrastructure；P0-4C 已建立 SQLAlchemy async/psycopg 3 底层 factory；P0-4D 已建立 Alembic async migration foundation 与 zero-op baseline revision。当前仍不建立业务表，也不冻结 V0.1 实体集合。

正式决策见 [`DECISIONS.md`](DECISIONS.md) `ADR-005`、`ADR-010`、`ADR-013`。

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

当前没有 Redis 或业务 Schema；Alembic migration history 只包含 zero-op baseline。

## P0-4C implemented async foundation

- direct dependencies：SQLAlchemy `2.0.52`、psycopg/psycopg-binary `3.3.4`；binary package 是本地开发 runtime baseline；
- SQLAlchemy URL dialect：只接受 `postgresql+psycopg://`；sqlite、asyncpg、psycopg2 与 malformed URL fail fast；
- configuration：`GIA_API_DATABASE_URL` 通过 `DatabaseSettings`/`SecretStr` 按需加载，是 server-only secret，不进入 `NEXT_PUBLIC_*`；现有 app startup 与 `/health` 不加载该配置；
- metadata：`DeclarativeBase` 使用 `ix`、`uq`、`ck`、`fk`、`pk` 稳定 naming convention，当前 `Base.metadata.tables` 为空；
- runtime：无 global engine；factory 使用 `create_async_engine()`，SQL echo disabled，pool 保持 SQLAlchemy defaults；session factory 使用 `async_sessionmaker[AsyncSession]` 与 `expire_on_commit=False`；caller 负责显式 transaction boundary；
- lifecycle：仅提供显式 `await engine.dispose()` 的薄 helper；尚无 FastAPI DB dependency、app lifespan 或启动连接；
- verification：14 项新增 DB foundation unit tests 不连接 PostgreSQL；真实 integration/migration tests 尚未执行。

P0-4E reusable PostgreSQL integration test suite 已完成。

## P0-4D implemented migration foundation

- dependency：Alembic `1.18.5`，constraint 为 `>=1.18.5,<1.19`，只位于 development dependency group；
- configuration：`apps/api/alembic.ini` 不保存 database URL 或 credential；`apps/api/migrations/env.py` 通过现有 `DatabaseSettings` 读取 server-only `GIA_API_DATABASE_URL`；
- runtime：只接受 `postgresql+psycopg`，使用 migration-specific `AsyncEngine`、`connection.run_sync(...)` 与 `NullPool`；Windows 使用 selector event loop 以兼容 psycopg async；
- metadata：`target_metadata = Base.metadata`，当前 business table count 为 `0`；
- history：唯一 head `7c6ccd86b3c5`（`establish database baseline`），`down_revision = None`，`upgrade()`/`downgrade()` 均为 zero-op，不含业务 DDL；
- runtime smoke：只在随机 `gia_p04d_*` 临时 PostgreSQL database 上执行 fresh upgrade、重复 upgrade、`current --check-heads`、`alembic check`、downgrade base 与 re-upgrade，均通过；head 状态下只产生 Alembic 自身的 `alembic_version` table，business table count 为 `0`；
- isolation：未迁移 development database；临时数据库已精确删除，development database `SELECT 1` 回归通过；
- lifecycle：API startup 不自动执行 migration，现有 `/health` 仍不加载数据库配置。

上述真实 PostgreSQL 操作是 P0-4D migration runtime smoke，不是 P0-4E reusable integration test suite。

## P0-4E implemented integration test foundation

- config：test-only typed settings 从根目录被 Git ignore 的 `.env` 读取 `POSTGRES_*`；password 使用 `SecretStr`，不会成为 application runtime config；
- isolation：每个需要独立 schema state 的测试使用唯一 `gia_p04e_<uuid hex>` database；development database 与 `postgres`/`template0`/`template1` 受显式 guard 保护；
- administration：复用现有 psycopg 3 sync API 和 autocommit maintenance connection，只用于 test database create/drop；SQL identifier 使用 `psycopg.sql.Identifier`；
- cleanup：fixture `finally` 只终止并删除本轮精确 database，随后验证其不存在；不通配清理历史 database；
- application runtime：现有 `create_database_engine()` 与 `create_database_session_factory()` 在真实 PostgreSQL 上验证 `AsyncEngine`、`AsyncSession`、server major 18、commit 与显式 rollback；application DB runtime 保持 async；
- transaction probe：`gia_test_transaction_probe` 只存在于独立临时 database，不加入 `Base.metadata`、migration 或 product schema；
- migration：fresh → unique head、repeat upgrade、`current --check-heads`、`alembic check`、downgrade base、re-upgrade 与 final check 均通过；migration business table count 为 `0`；
- regression：`Base.metadata.tables = 0`；development database 未迁移、没有 `alembic_version` 且 `SELECT 1` 通过；本轮 `gia_p04e_%` residual audit 为 `0`。

## Rejected paths

- 不使用 SQLite 作为正式开发路径或 PostgreSQL integration test 的临时替代；
- 不使用 SQLModel 将 API schema 与 ORM 永久统一；
- 当前不使用 UUIDv7；
- 当前不建立 internal integer ID + public UUID 的双 ID 体系；
- 不因总纲列出未来实体就在 P0-4 一次性创建全部表。

只有未来测量结果证明 UUIDv7 或双 ID 体系有实际收益时，才能提出新的技术决策。

## P0-4 implementation scope

P0-4 将依据 Accepted ADR 建立：

- Docker Compose；
- PostgreSQL 18.x service；
- 安全数据库连接配置和占位符；
- SQLAlchemy 2.x engine/session 基础；
- Alembic migration environment；
- 当前范围需要的最小基础模型；
- PostgreSQL integration tests；
- migration checks。

P0-4 不运行 Redis，不创建未来完整业务 Schema，也不提前实现支付、语音、成长或 V0.5/V1.0 实体。

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

## Future business schema

总纲提到 `users`、题目版本、角色模板、会话、参与者、阶段、发言、讨论事件、结构化记忆、报告、证据、训练、反馈、模型调用和审计等未来领域概念。

这些只是长期领域导航：

- 表名、字段、关系、索引和删除策略尚未冻结；
- V0.1 最小实体集合仍需在 P1 业务设计中确认；
- 支付、权益、语音和成长数据不得提前进入 V0.1 Schema；
- 正式认证方案仍是 TBD，不影响 P0-4 建立技术基础。

## TBD

- TBD：V0.1 最小实体集合和正式 Schema；
- TBD：正式认证方案及用户主键边界；
- TBD：原始音频是否默认完全不保存（总纲第 37 节）；
- TBD：各类数据的精确保留期限；
- TBD：删除、匿名化和审计的具体规则；
- TBD：结构化记忆、证据和模型调用日志 Schema；
- TBD：未来多租户或机构隔离模型。

## Future work

- P0-4F：独立审查 P0-4 database foundation；
- P1：按文字讨论闭环实现最小题目、角色、会话、事件、记忆和报告数据；
- P2～P4：仅随获批范围增加音频、评分训练和商业化数据。

## 与其他文档关系

- 技术决策：[`DECISIONS.md`](DECISIONS.md)
- 架构边界：[`ARCHITECTURE.md`](ARCHITECTURE.md)
- API 契约：[`API.md`](API.md)
- 数据安全和删除：[`PRIVACY_AND_SAFETY.md`](PRIVACY_AND_SAFETY.md)
- 当前任务：[`TASKS.md`](TASKS.md)
