# P0-4 Database Foundation Execution Plan

## Goal

依据已批准的 P0 数据技术决策，建立可重复验证的 PostgreSQL 18.x、SQLAlchemy 2.x 与 Alembic 基础，并以真实 PostgreSQL 完成 integration/migration checks；不提前创建业务 Schema。

## Context

- 当前开发阶段：`P0 — 项目基础`；目标版本：`V0.1 Internal Validation`。
- `P0-1`、`P0-2`、`P0-3` 已完成；`P0-4A` 已通过审核。
- Source of Truth：[`../PROJECT_MASTER_PLAN.md`](../PROJECT_MASTER_PLAN.md)、[`../DECISIONS.md`](../DECISIONS.md)、[`../TASKS.md`](../TASKS.md)、[`../DATABASE.md`](../DATABASE.md)。
- 当前已完成子步骤：`P0-4B — Docker Compose + PostgreSQL local infrastructure`。
- 当前已完成子步骤：`P0-4C — SQLAlchemy async foundation + typed DB config`。
- 当前已完成子步骤：`P0-4D — Alembic migration foundation + zero-op baseline revision`。
- 当前子步骤：`P0-4E — PostgreSQL integration tests + migration validation + docs`，completed。
- 下一子步骤：`P0-4F — Independent final review`，awaiting explicit approval。

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
- P0-4C scoped driver decision 已确认：`psycopg[binary]>=3.3.4,<3.4`；不采用 asyncpg、psycopg2 或同步 application runtime。

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
- P0-4C SQLAlchemy baseline：`sqlalchemy>=2.0.51,<2.1`，URL 只接受 `postgresql+psycopg://`；
- `GIA_API_DATABASE_URL` 是 lazy、server-only SecretStr，现有 app startup 与 `/health` 不加载；
- 当前 metadata 必须为空，app runtime 尚无 DB caller、DB dependency 或 lifecycle。

## Implementation steps

1. `P0-4A`：完成 Git、总纲、文档、Docker 与端口预检，冻结范围。
2. `P0-4B`：建立只含 PostgreSQL 的 Compose，验证 image、health、版本、数据库、named volume 与 restart smoke。
3. `P0-4C`：使用 scoped psycopg 3 driver decision 建立 SQLAlchemy async 与 typed DB config；已完成。
4. `P0-4D`：建立 Alembic async environment 与不创建业务表的 migration baseline；已完成。
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

P0-4D 的隔离 migration runtime smoke 与 P0-4E reusable integration/migration test suite 均已完成；P0-4F 等待明确批准。

## Decisions

- 已确认：PostgreSQL 18.x、SQLAlchemy 2.x、Alembic、真实 PostgreSQL tests、无 SQLite 过渡。
- 已确认：P0-4 不创建业务表。
- P0-4 scoped implementation decision：SQLAlchemy `>=2.0.51,<2.1`、`psycopg[binary]>=3.3.4,<3.4`、`postgresql+psycopg://` 与 async SQLAlchemy runtime；该选择不是永久 ADR。
- 已确认：Compose 只承载 PostgreSQL，不包含 Redis/Web/API/worker/admin UI。

## Risks

- Docker daemon 或 Docker Hub 不可用会阻塞本地基础设施验证；
- PostgreSQL 18 official image 使用版本化数据目录，错误挂载旧路径可能导致持久化行为不符合预期；
- `.env` 含本地 credential，必须保持 Git ignored 且不得写入日志或报告；
- 删除 named volume 是破坏性操作，未经用户明确批准不得执行。

## Progress

- 2026-08-13：`P0-4A` completed，预检与范围冻结通过。
- 2026-08-13：`P0-4B` completed；PostgreSQL-only Compose、official image pull、healthy、18.4 server、开发数据库、`SELECT 1`、named volume、restart smoke 与 IPv4 loopback binding 已验证，最终 diff 审核通过。
- 2026-08-13：`P0-4C` completed；resolved SQLAlchemy `2.0.52`、psycopg/psycopg-binary `3.3.4`，已创建 `db/__init__.py`、`db/base.py`、`db/runtime.py`，31 项 API 测试通过（14 项新增 DB foundation unit tests），最终源码/diff 审核通过。
- 2026-08-13：`P0-4D` completed；resolved Alembic `1.18.5`，建立 async migration environment 与唯一 zero-op baseline head `7c6ccd86b3c5`。隔离临时 PostgreSQL database 的 upgrade/repeat/check/downgrade/re-upgrade smoke 通过，business table count 为 `0`，临时数据库已清理，development database 未迁移且回归通过，最终源码与 migration foundation 审核通过。
- 2026-08-14：`P0-4E` completed；新增 `tests/integration/conftest.py`、`test_database.py`、`test_migrations.py` 与 pytest marker/importlib mode。Unit 35、integration 11、full 46 项通过；逐测试 `gia_p04e_*` database 均精确清理，development database 未迁移且回归通过。
- 当前下一步：P0-4F awaiting explicit approval。

## Deviations

- `docker manifest inspect postgres:18.4-trixie` 首次访问 Docker Hub 时超时；PostgreSQL 官方 release notes 与 Docker Official Image tags 均确认 18.4/`18.4-trixie`，随后实际 `docker compose pull postgres` 成功，registry gate 已解除。
- 首次组合只读 SQL 命令因 PowerShell 到容器的引号传递失败，未执行 DDL；改用参数化的 `psql -c` 调用后，所有查询通过。
- P0-4C 首次 `uv add` 在 workspace sandbox 中因网络访问限制失败；经用户批准仅放行 `uv add` 访问 PyPI 后成功，未扩大文件系统权限。
- P0-4C 首轮质量检查发现 import order、Pyright 对环境注入必填 field 的静态建模和显式 `echo=False` 断言问题；均已最小修正，最终全门通过。
- P0-4D 首次 `uv add` 在 sandbox 中因 network restriction 失败；按已批准的 scoped `uv add --dev` 权限访问 PyPI 后成功，未扩大文件系统权限。
- P0-4D 前两次 migration smoke 在运行 Alembic 前分别暴露 PowerShell URL scalar 解析问题与 Windows Proactor event loop 不兼容；相应临时数据库均由精确 `finally` cleanup 删除。migration environment 最小改用 selector event loop 后，第三次 Alembic upgrade 已通过；随后修正仅用于验证的 catalog scalar 解析并用新临时数据库完成全部闭环。没有迁移 development database。
- P0-4E 执行中发生一次 response stream 网络中断；working tree 修改被保留，并从当前 diff 恢复审查，未 reset、restore 或重复建立 infrastructure。恢复后所有最终质量门与 integration gates 均重新执行，中断前未完整返回的结果未作为最终 PASS 证据。
- 根 tests 与 `tests/integration/` 的同名模块在 pytest 默认 prepend mode 下发生 collection collision；最小启用 `--import-mode=importlib`，未新增 `__init__.py`、pytest dependency 或重命名批准文件。
- Full suite 首轮发现 programmatic Alembic `fileConfig()` 会污染同进程 logging state；integration tests 改用无 config filename 的 programmatic `Config()` 与绝对 `script_location`，自然跳过 `fileConfig()`，并以 logging isolation regression 验证既有 logger state 保持不变。Production migration/logging config 未修改。

## Verification evidence

- P0-4D Git baseline：`main`、clean、HEAD `bd534f1`；
- `PROJECT_MASTER_PLAN.md` SHA-256：`2388A9660320406CB35D5354126AD71C6849A98DB7C4A356796CA951BF372F26`；
- Docker Engine/CLI：`29.6.2`；Compose：`v5.3.1`；context：`desktop-linux`；
- P0-4B 开始前 localhost `5432` 无 listener；
- PostgreSQL 18.4 是当前 18 系稳定补丁，`postgres:18.4-trixie` 是 Docker Official Image tag。
- Compose config：唯一 service `postgres`、唯一 image `postgres:18.4-trixie`、host binding `127.0.0.1:5432`、container port `5432`；
- container health：`healthy`；server：`18.4 (Debian 18.4-1.pgdg13+1)`；
- development database 存在，`SELECT 1` 在启动后与 restart 后均通过；
- Docker local named volume `group-interview-arena_postgres_data` 挂载至 `/var/lib/postgresql`；
- local `.env` 由根 `.gitignore` 覆盖，未进入 Git status。
- P0-4C dependency resolution：SQLAlchemy `2.0.52`、psycopg/psycopg-binary `3.3.4`，无 prerelease；
- P0-4C quality：`uv sync --frozen`、`uv lock --check`、Ruff lint/format、Pyright 与 31 项 pytest 全部通过；
- P0-4C security/scope：数据库 URL 由 SecretStr 保护，未记录 credential；metadata table count 为 0；无 Alembic、migration、业务 model、FastAPI DB caller 或真实 PostgreSQL integration test。
- P0-4D dependency/config：Alembic `1.18.5` 仅在 dev dependency group；`alembic.ini` 不含 URL/credential；runtime 由 `DatabaseSettings` 读取 `GIA_API_DATABASE_URL`。
- P0-4D revision：唯一 head `7c6ccd86b3c5`，`down_revision = None`，upgrade/downgrade zero-op，business DDL count 为 `0`。
- P0-4D runtime：随机 `gia_p04d_*` 临时 PostgreSQL database 上 fresh upgrade、repeat upgrade、`current --check-heads`、两次 `alembic check`、downgrade base 与 re-upgrade 全部通过；business table count 始终为 `0`。
- P0-4D cleanup/regression：临时数据库不存在；development database 存在、未迁移且 `SELECT 1` 通过；PostgreSQL container 与 named volume 保留。
- P0-4D quality：`uv sync --frozen`、`uv lock --check`、Ruff lint/format、Pyright 与 35 项 pytest 全部通过（4 项新增 migration static/unit tests）。
- P0-4E Git baseline：`main`、clean、HEAD `94ee4f0`；
- P0-4E test architecture：test-only typed root `.env` settings、`SecretStr` password、per-test `gia_p04e_*` isolation、psycopg sync autocommit admin、`sql.Identifier` 与 exact cleanup；
- P0-4E database integration：AsyncEngine/AsyncSession、PostgreSQL major 18、commit/rollback 通过；test-only probe 不属于 product schema；
- P0-4E migration integration：fresh/repeat/check/downgrade/re-upgrade/final check 通过，unique head `7c6ccd86b3c5`，business table count 为 `0`；
- P0-4E test totals：unit 35 passed、integration 11 passed/0 skipped、full 46 passed；Ruff、format、Pyright、frozen sync 与 lock check 通过；
- P0-4E cleanup/regression：run-created temp database 最终均不存在，`gia_p04e_%` residual count 为 `0`；development database 存在、未迁移、无 `alembic_version` 且 `SELECT 1` 通过；
- P0-4E dependency/schema：无新增 dependency，`uv.lock` 未变；`Base.metadata.tables = 0`，baseline revision 未改且无新 revision。
