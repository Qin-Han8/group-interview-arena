# P0-4 Database Foundation Execution Plan

## Goal

依据已批准的 P0 数据技术决策，建立可重复验证的 PostgreSQL 18.x、SQLAlchemy 2.x 与 Alembic 基础，并以真实 PostgreSQL 完成 integration/migration checks；不提前创建业务 Schema。

## Context

- 当前开发阶段：`P0 — 项目基础`；目标版本：`V0.1 Internal Validation`。
- `P0-1`、`P0-2`、`P0-3` 已完成；`P0-4A` 已通过审核。
- Source of Truth：[`../PROJECT_MASTER_PLAN.md`](../PROJECT_MASTER_PLAN.md)、[`../DECISIONS.md`](../DECISIONS.md)、[`../TASKS.md`](../TASKS.md)、[`../DATABASE.md`](../DATABASE.md)。
- 当前已完成子步骤：`P0-4B — Docker Compose + PostgreSQL local infrastructure`。
- 下一子步骤：`P0-4C — SQLAlchemy async foundation + typed DB config`，等待明确批准。

## Scope

- P0-4A：预检、边界冻结与执行计划；
- P0-4B：Docker Compose 与 PostgreSQL 本地基础设施；
- P0-4C：SQLAlchemy async foundation 与 typed DB config；
- P0-4D：Alembic migration foundation 与 initial schema strategy；
- P0-4E：真实 PostgreSQL integration tests、migration validation 与文档同步；
- P0-4F：独立最终审查。

## Non-goals

- 不创建业务表或完整长期数据模型；
- 不使用 SQLite；
- 不运行 Redis、task queue、worker 或管理 UI；
- 不容器化 Web/API；
- 不实现认证、WebSocket、Provider、AI 或其他业务能力；
- 不修改现有 `GET /health`，不新增 `/ready`。

## Dependencies

- Accepted ADR：ADR-005、ADR-010、ADR-011、ADR-012、ADR-013；
- Docker Desktop 与 Linux container daemon；
- PostgreSQL Official Image registry 可访问；
- P0-4C 前必须确认 PostgreSQL async driver；当前 `psycopg 3` 与 `asyncpg` 均未批准。

## Scoped implementation baseline

- P0-4 不创建业务表；首个业务表在真实业务阶段通过 migration 加入；
- P0-4B Compose 只包含 PostgreSQL；
- Web 与 API 继续作为 Windows native process；
- PostgreSQL image：`postgres:18.4-trixie`；
- host binding：`127.0.0.1:5432`；container port：`5432`；service：`postgres`；
- PostgreSQL 18 named volume 挂载至 `/var/lib/postgresql`；
- Redis 与 task queue 继续 Deferred；
- development DB 与未来 test DB 必须隔离；
- 不自动删除 development DB 或 named volume。

## Implementation steps

1. `P0-4A`：完成 Git、总纲、文档、Docker 与端口预检，冻结范围。
2. `P0-4B`：建立只含 PostgreSQL 的 Compose，验证 image、health、版本、数据库、named volume 与 restart smoke。
3. `P0-4C`：在获得 driver 明确批准后建立 SQLAlchemy async 与 typed DB config。
4. `P0-4D`：建立 Alembic async environment 与不创建业务表的 migration baseline。
5. `P0-4E`：在隔离的真实 PostgreSQL test DB 完成 integration/migration checks，并同步文档。
6. `P0-4F`：独立复核范围、实现、迁移、安全、测试证据与文档一致性。

## Validation

P0-4B 要求：

- `docker compose ... config`；
- official image pull；
- container healthy；
- `SELECT version()` / `SHOW server_version` 确认 PostgreSQL 18.x；
- development database 存在且 `SELECT 1` 成功；
- named volume 挂载到 `/var/lib/postgresql`；
- restart 后重新 healthy 且 `SELECT 1` 成功；
- `git diff --check`、scope audit、secret audit 与总纲 hash 检查。

后续 P0-4C～P0-4E 的 SQLAlchemy、Alembic、integration/migration checks 只在对应子步骤获批后执行。

## Decisions

- 已确认：PostgreSQL 18.x、SQLAlchemy 2.x、Alembic、真实 PostgreSQL tests、无 SQLite 过渡。
- 已确认：P0-4 不创建业务表。
- 已确认：Compose 只承载 PostgreSQL，不包含 Redis/Web/API/worker/admin UI。
- 待确认：P0-4C PostgreSQL async driver（`psycopg 3` 或 `asyncpg`）。

## Risks

- Docker daemon 或 Docker Hub 不可用会阻塞本地基础设施验证；
- PostgreSQL 18 official image 使用版本化数据目录，错误挂载旧路径可能导致持久化行为不符合预期；
- `.env` 含本地 credential，必须保持 Git ignored 且不得写入日志或报告；
- 删除 named volume 是破坏性操作，未经用户明确批准不得执行。

## Progress

- 2026-08-13：`P0-4A` completed，预检与范围冻结通过。
- 2026-08-13：`P0-4B` completed；PostgreSQL-only Compose、official image pull、healthy、18.4 server、开发数据库、`SELECT 1`、named volume、restart smoke 与 IPv4 loopback binding 已验证，最终 diff 审核通过。
- 当前下一步：等待 P0-4B diff 审核；通过后再进入 P0-4C。

## Deviations

- `docker manifest inspect postgres:18.4-trixie` 首次访问 Docker Hub 时超时；PostgreSQL 官方 release notes 与 Docker Official Image tags 均确认 18.4/`18.4-trixie`，随后实际 `docker compose pull postgres` 成功，registry gate 已解除。
- 首次组合只读 SQL 命令因 PowerShell 到容器的引号传递失败，未执行 DDL；改用参数化的 `psql -c` 调用后，所有查询通过。

## Verification evidence

- Git baseline：`main`、clean、HEAD `261e6930c2fd87cc49968ca5a7f32a1ffb78b6c6`；
- `PROJECT_MASTER_PLAN.md` SHA-256：`2388A9660320406CB35D5354126AD71C6849A98DB7C4A356796CA951BF372F26`；
- Docker Engine/CLI：`29.6.2`；Compose：`v5.3.1`；context：`desktop-linux`；
- P0-4B 开始前 localhost `5432` 无 listener；
- PostgreSQL 18.4 是当前 18 系稳定补丁，`postgres:18.4-trixie` 是 Docker Official Image tag。
- Compose config：唯一 service `postgres`、唯一 image `postgres:18.4-trixie`、host binding `127.0.0.1:5432`、container port `5432`；
- container health：`healthy`；server：`18.4 (Debian 18.4-1.pgdg13+1)`；
- development database 存在，`SELECT 1` 在启动后与 restart 后均通过；
- Docker local named volume `group-interview-arena_postgres_data` 挂载至 `/var/lib/postgresql`；
- local `.env` 由根 `.gitignore` 覆盖，未进入 Git status。
