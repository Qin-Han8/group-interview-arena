# 数据库技术基线

- Status: P0 Data Architecture Baseline
- Current phase: P0
- Data architecture baseline established by: P0-2 — DONE
- Local PostgreSQL infrastructure: P0-4B — completed
- Target version: V0.1 Internal Validation
- Business schema and migrations: Not started
- Authority: 低于 [`PROJECT_MASTER_PLAN.md`](PROJECT_MASTER_PLAN.md) 和已确认的 [`DECISIONS.md`](DECISIONS.md)

## 文档目的

本文件记录 P0-2 已批准的数据技术基线、数据边界和 P0-4 实施状态。P0-4B 已建立本地 PostgreSQL infrastructure；当前仍不建立业务表、不冻结 V0.1 实体集合，SQLAlchemy、Alembic 与 migration 尚未创建。

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

当前没有 Redis、SQLAlchemy、Alembic、PostgreSQL Python driver、migration 或业务 Schema。PostgreSQL async driver 仍待 P0-4C 前确认。

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

- P0-4C～P0-4F：建立 SQLAlchemy/Alembic、migration 与真实 PostgreSQL integration/migration checks；
- P1：按文字讨论闭环实现最小题目、角色、会话、事件、记忆和报告数据；
- P2～P4：仅随获批范围增加音频、评分训练和商业化数据。

## 与其他文档关系

- 技术决策：[`DECISIONS.md`](DECISIONS.md)
- 架构边界：[`ARCHITECTURE.md`](ARCHITECTURE.md)
- API 契约：[`API.md`](API.md)
- 数据安全和删除：[`PRIVACY_AND_SAFETY.md`](PRIVACY_AND_SAFETY.md)
- 当前任务：[`TASKS.md`](TASKS.md)
