# 发布与阶段验收清单骨架

- Status: Skeleton / Baseline
- Current phase: P0
- Target version: V0.1 Internal Validation
- Detailed design: Not started
- Detailed operational checklist: Not started
- Authority: 低于 [`PROJECT_MASTER_PLAN.md`](PROJECT_MASTER_PLAN.md) 和已确认的 [`DECISIONS.md`](DECISIONS.md)

## 文档目的

本文件按 P0 exit、V0.1、V0.5 和 V1.0 分层整理总纲已经明确的范围及验收要求。复选框只是未来验收项，不表示当前已经完成。

## Confirmed by PROJECT_MASTER_PLAN

以下 P0、V0.1、V0.5 和 V1.0 清单只整理总纲第 30～32 节已经明确的范围与验收原则，不新增版本功能或质量指标。完整语义仍以总纲为准。

## 当前版本范围

P0-2 技术架构决策、P0-3 前后端项目骨架与 P0-4 数据库及迁移基础已完成。P0-4A～P0-4F 均已完成，P0-4 已通过独立最终验收并转为 `DONE`。P0-5 已进入 `IN_PROGRESS`：P0-5A/P0-5B/P0-5C/P0-5D completed，P0-5E awaiting explicit approval，independent final review not started。P0 尚未完成；browser CORS/CSRF/Web closure 已实现，但 P0-5E 与 V0.1 业务能力尚未完成。下方 P0 exit 与产品版本复选框仍表示完整阶段/版本验收，不能由单个子任务替代。

## Implementation guidance

- 只有实际验证并有证据的项目才能勾选。
- 不得因功能存在就跳过隐私、安全、恢复和证据质量检查。
- 版本范围变化必须先形成正式决策。
- 具体命令、负责人和发布流程在相关技术任务中补充，不在 P0-1 虚构。

### P0-3C Web foundation verification — 2026-08-12

- [x] `pnpm.cmd install`
- [x] `pnpm.cmd web:lint`
- [x] `pnpm.cmd web:typecheck`
- [x] `pnpm.cmd web:test`
- [x] `pnpm.cmd web:format:check`
- [x] `pnpm.cmd web:build`
- [x] `pnpm.cmd web:dev` 后访问 `http://localhost:3000` 返回 HTTP 200，验证后已停止服务。

这些证据只覆盖 P0-3C Web 技术骨架；不代表 API、数据库、migration、CI 或 P0 exit 已通过。

### P0-3D API foundation verification — 2026-08-13

- [x] `uv sync --frozen`
- [x] `uv lock --check`
- [x] `uv run ruff check .`
- [x] `uv run ruff format --check .`
- [x] `uv run pyright`
- [x] `uv run pytest`
- [x] package 与 FastAPI app import；
- [x] Uvicorn 下 `GET /health` 返回 `200`、精确 JSON 和 `X-Request-ID`；
- [x] Uvicorn 下 `GET /openapi.json` 返回 `200` 并包含 `/health`，验证后已停止服务。

这些证据只覆盖 P0-3D API 技术骨架；不代表 Web/API browser connectivity、CORS、数据库、migration、CI、WebSocket 或 P0 exit 已通过。

### P0-3E connectivity verification — 2026-08-13

API：

- [x] `uv sync --frozen`；
- [x] `uv lock --check`；
- [x] `uv run ruff check .`；
- [x] `uv run ruff format --check .`；
- [x] `uv run pyright`；
- [x] `uv run pytest`，17 项通过；
- [x] 真实 `GET /health` 与 `/openapi.json` 均返回 `200`；
- [x] allowed origin 获得明确 CORS allow origin 与 exposed `X-Request-ID`；
- [x] disallowed origin 未获得 `Access-Control-Allow-Origin`；
- [x] `GET` preflight 通过。

Web 与 contract：

- [x] `pnpm.cmd install --frozen-lockfile`；
- [x] `pnpm.cmd web:lint`；
- [x] `pnpm.cmd web:typecheck`；
- [x] `pnpm.cmd web:test`，8 项通过；
- [x] `pnpm.cmd web:format:check`；
- [x] `pnpm.cmd web:build`；
- [x] `pnpm.cmd web:api:generate` 生成只包含 `/health` 的契约；
- [x] `pnpm.cmd web:api:check` 无漂移；
- [x] Web `:3000` 与 API `:8000` 同时返回 HTTP `200`，验证后服务均已停止；
- [x] 用户在真实浏览器打开 `http://localhost:3000`，页面正常显示“API 状态：已连接”；
- [x] 用户在同一真实浏览器直接请求 `http://localhost:8000/health`，获得 HTTP `200` 与 `{"status":"ok"}`；
- [x] 真实浏览器请求中的 CORS 与 `X-Request-ID` 表现正常；
- [x] 浏览器 Console 未发现与本次功能相关的运行时或 CORS 错误。

P0-3E 已完成，真实浏览器手工验收为 PASS。本项未执行 Playwright、E2E 或其他浏览器自动化；这些证据不代表数据库、WebSocket、业务能力、CI、P0-3F 或 P0 exit 已通过。

### P0-3F independent final verification — 2026-08-13

- [x] 从当前 clean `main` HEAD 重新验证 Git、总纲 hash、工具链、仓库结构、lockfile、依赖范围及 Web/API 静态架构；
- [x] ADR-007 OpenAPI tooling blocker 已解决，REST Source of Truth、派生 contract 与 WebSocket Deferred 边界一致；
- [x] Web frozen install、lint、typecheck、8 项测试、format check 与 production build 通过；
- [x] API frozen sync、lock check、Ruff lint/format、Pyright、17 项 pytest、package/app import 通过；
- [x] 真实 `/health`、`/openapi.json`、allowed/disallowed CORS、preflight、OpenAPI drift 与 Web `:3000` HTTP smoke 通过，服务已清理；
- [x] 文档、scope、public env/secret 与 generated/ignored files 审计通过。

P0-3 已通过第二次独立最终验收并转为 `DONE`。P0 整体仍为 `IN_PROGRESS`；P0-4 当前为 `IN_PROGRESS`，P0-4B 已完成。本项不代表 P0-4、P0 exit 或 V0.1 业务能力已完成。

### P0-4B PostgreSQL local infrastructure verification — 2026-08-13

- [x] Docker Engine/CLI `29.6.2`、Docker Compose `v5.3.1`、`desktop-linux` context 与 Linux daemon 可用；
- [x] localhost `5432` 在启动前无 listener；
- [x] PostgreSQL 官方 release 与 Docker Official Image tag 核验为 `18.4` / `postgres:18.4-trixie`；
- [x] `docker compose --env-file .env -f infra/compose.yaml config` 通过，且只包含 `postgres`；
- [x] official image pull 成功；
- [x] container 达到 `healthy`；
- [x] `SHOW server_version` 返回 PostgreSQL `18.4`；
- [x] development database 存在且 `SELECT 1` 成功；
- [x] published port 只绑定 IPv4 loopback `127.0.0.1:5432`；
- [x] persistence 使用 Docker local named volume，挂载至 `/var/lib/postgresql`；
- [x] restart 后重新 `healthy` 且 `SELECT 1` 成功；
- [x] `.env` 保持 Git ignored，tracked 配置和文档没有真实 credential。

这些证据只覆盖已完成的 P0-4B 本地 PostgreSQL infrastructure；在该子步骤验收时，SQLAlchemy、driver、Alembic、migration、数据库 integration tests 与业务 Schema 均尚未建立。当前后续状态见下方 P0-4C verification。

### P0-4C SQLAlchemy async foundation verification — 2026-08-13

- [x] `uv sync --frozen`；
- [x] `uv lock --check`；
- [x] SQLAlchemy `2.0.52` 与 psycopg/psycopg-binary `3.3.4` import，psycopg binary implementation 已确认；
- [x] `uv run ruff check .`；
- [x] `uv run ruff format --check .`；
- [x] `uv run pyright`；
- [x] `uv run pytest`，31 项通过，其中 14 项为新增 DB foundation unit tests；
- [x] `GIA_API_DATABASE_URL` lazy/server-only SecretStr、driver boundary、URL redaction、DeclarativeBase/naming、空 metadata、async engine/session 与 dispose behavior 已验证；
- [x] 现有 app startup 与 `GET /health` 在无数据库 URL 时保持不变。

这些证据只覆盖已完成的 P0-4C SQLAlchemy async foundation，且测试未连接 PostgreSQL，不是 integration tests。当时尚无 Alembic/migration；当前后续状态见下方 P0-4D verification。业务 table/model、FastAPI DB dependency 与 app DB lifecycle 仍未建立。

### P0-4D Alembic migration foundation verification — 2026-08-13

- [x] Alembic `1.18.5` 只加入 development dependency group，frozen sync 与 lock check 通过；
- [x] `alembic.ini`、async `migrations/env.py`、template、README 与 versions 目录已建立，配置不保存 credential；
- [x] migration runtime 与 application DB config 共用 server-only `GIA_API_DATABASE_URL`，只接受 `postgresql+psycopg`；
- [x] `target_metadata` 使用 `Base.metadata`，migration engine 使用 `AsyncEngine`、`connection.run_sync(...)` 与 `NullPool`；
- [x] 唯一 head `7c6ccd86b3c5` 是 zero-op baseline，upgrade/downgrade 均无业务 DDL；
- [x] fresh 隔离临时 PostgreSQL database upgrade 到 head、重复 upgrade、`current --check-heads` 与 `alembic check` 通过；
- [x] downgrade base、re-upgrade 与最终 `alembic check` 通过；
- [x] P0-4D 临时数据库在 zero-op head 时只存在 Alembic 自身的 `alembic_version`，当时 business table count 为 `0`；
- [x] 临时数据库已精确删除；P0-4D 验收时 development database 未迁移、仍存在且 `SELECT 1` 通过；P0-5B 后的当前状态见 identity 验证记录；
- [x] Ruff、format check、Pyright 与 35 项 pytest 通过，其中 4 项为 migration static/unit tests。

这些证据是 P0-4D migration runtime smoke，不是 P0-4E reusable PostgreSQL integration test suite。P0-4D 已完成；当前 P0-4E 证据见下方 verification。

### P0-4E PostgreSQL integration verification — 2026-08-14

- [x] reusable per-test `gia_p04e_*` temporary database fixture 与 exact cleanup；
- [x] development/system/unprefixed database guards 在执行 SQL 前拒绝危险名称；
- [x] sync psycopg admin connection 使用 autocommit，database identifier 使用 `psycopg.sql.Identifier`；
- [x] 现有 AsyncEngine 与 AsyncSession 真实连接 PostgreSQL major 18；
- [x] test-only probe table 上的 commit 与 explicit rollback 均通过；
- [x] fresh database → unique migration head、repeat upgrade、`alembic check`、downgrade base、re-upgrade 与 final check 通过；
- [x] P0-4E 验收时 migration business table count 与 `Base.metadata` table count 均为 `0`；probe table 未进入 product schema；
- [x] unit suite 35 项、integration suite 11 项（skipped 0）、full suite 46 项通过；
- [x] `uv sync --frozen`、`uv lock --check`、Ruff、format check 与 Pyright 通过；
- [x] P0-4E 验收时 development database 未执行 migration、没有 `alembic_version`、`SELECT 1` 通过；P0-5B 后的当前状态见 identity 验证记录；本轮临时 database residual count 为 `0`；
- [x] 未新增 dependency，`uv.lock`、baseline revision、Web、Compose 与业务 schema 均未改变。

这些证据只覆盖 P0-4E reusable PostgreSQL integration/migration test foundation；P0-4F 的独立最终验收证据见下方记录。

### P0-4F independent final verification — 2026-08-14

- [x] clean `main`、HEAD `622170f9f1cae0d6ad7492d4134564001b030713`，P0-4B/C/D/E commits 均存在；
- [x] `PROJECT_MASTER_PLAN.md` SHA-256 精确匹配批准值；
- [x] Docker/Compose、唯一 PostgreSQL `18.4` service、IPv4 loopback binding、healthy 与 local named volume 通过；
- [x] secret、direct dependency、SQLAlchemy、FastAPI、Alembic、Windows asyncio、migration history/template 与 integration harness safety 审计通过；
- [x] unit 35、integration 11（skipped 0）、full 46 项通过；frozen sync、lock check、Ruff、format、Pyright 与唯一 Alembic head 通过；
- [x] P0-4F 验收时 development database `SELECT 1` 通过、无 `alembic_version`、public product table 为 `0`；P0-5B 后已安全迁移至 identity head；`gia_p04e_%` residual 为 `0`；
- [x] 未修改被审计实现或运行资源，PostgreSQL container、named volume 与 development database 均保留。

P0-4 已通过独立最终验收并转为 `DONE`。该验收时 P0-5 尚未获批；当前 P0-5A 已完成，实施状态见下方记录。这不代表 P0 exit 或 V0.1 业务能力已完成。

### P0-5A identity decision closeout — 2026-08-14

- [x] P0-5A identity preflight/security/scope freeze 已由用户批准；
- [x] `ADR-015` 已记录 username/password、稳定 UUIDv4 `user_id`、Argon2id 与 PostgreSQL-backed opaque Cookie session 的长期边界；
- [x] raw token only in HttpOnly Cookie、database digest-only persistence 与 current no-JWT decision 已记录；
- [x] explicit Argon2 parameter ownership/benchmark、small offline full-password blocklist、shared `GIA_API_CORS_ORIGINS` trusted-origin Source of Truth 与 V0.1 recovery defer 四项修订已记录；
- [x] P0-5 five-stage execution plan、migration safety、security risks 与 public-exposure gates 已建立；
- [x] 文档明确区分 approved architecture、planned implementation 与 actually implemented capability。

这些证据只覆盖 P0-5A 决策和范围收尾；后续 P0-5B implementation evidence 见下节。P0 identity exit item 仍不得勾选。

### P0-5B identity persistence and security primitives — 2026-08-14

- [x] `pwdlib[argon2]>=0.3.0,<0.4` 是唯一新增 direct runtime dependency；解析 `pwdlib 0.3.1`、`argon2-cffi 25.1.0`，CPython 3.14.7 import/API 验证通过；
- [x] Argon2id 参数由 application 显式拥有：memory 65536 KiB、time 3、parallelism 4、hash 32、salt 16；未使用 `PasswordHash.recommended()`；
- [x] 5 个本机样本的 hash median 约 54.3 ms、verify median 约 51.6 ms，未出现不合理秒级成本；该证据不是跨机器性能保证；
- [x] canonical username 先校验 raw ASCII，Unicode lowercase bypass regression 通过；15–128 password、NFC/no-trim/no-silent-change、small offline full-match blocklist、hash/verify/verify-and-update、policy drift 与 malformed hash safe-failure 测试通过；
- [x] `users`、`auth_sessions` models 与 exact PK/unique/FK `ON DELETE CASCADE`/expiry index schema 已实现，session primitive 与 integration persistence 验证 32-byte SHA-256 digest，metadata product table count 精确为 2；
- [x] identity revision `4fe43b42641b` 线性承接 immutable baseline `7c6ccd86b3c5`；single head、revision count 2；
- [x] fresh temporary PostgreSQL upgrade/repeat/check、downgrade 至 baseline、identity table removal、re-upgrade/final check 与 exact schema validation 通过；
- [x] unit 83、integration 12（skipped 0）、full 95 项通过；frozen sync、lock check、Ruff、format 与 Pyright 通过；
- [x] development database preflight 确认 product table count 0、`alembic_version` absent 后首次迁移至 identity head；repeat upgrade no-op，两张表 row count 0，未 downgrade；
- [x] `gia_p05b_%` 与 `gia_p04e_%` residual 均为 0；无 wildcard cleanup；无 auth route、FastAPI DB lifecycle、Cookie/CORS/CSRF 或 Web auth scope expansion。

P0-5B 最终源码审核已 PASS 并转为 completed；其后的 P0-5C 当前状态见下节。

### P0-5C backend authentication runtime — 2026-08-14

- [x] FastAPI lifespan、AsyncEngine/sessionmaker app state、shutdown disposal 与 request-scoped `AsyncSession` 已实现；import/OpenAPI 不加载 DB settings 或连接 PostgreSQL；
- [x] register/login/logout/me、generic login failure、fixed dummy Argon2 verification、rehash、fresh-session fixation defense、absolute expiry 与 exact logout deletion 已验证；
- [x] `gia_session` local/production flags、7-day Max-Age、host-only behavior 与 logout clear semantics 已验证；production + insecure Cookie 配置 fail closed，raw token 不进入普通 result repr，且 raw token/password/hash/digest/DB URL 不进入 JSON response 或 structured request log；
- [x] auth PostgreSQL integration 覆盖 atomic register rollback、rehash rollback、unknown/expired session、no sliding expiry 与 other-session preservation；
- [x] unit 102、integration 18（skipped 0）、full 120 项通过；frozen sync、lock check、Ruff、format、Pyright、唯一 Alembic head 与 revision count 2 通过；
- [x] FastAPI OpenAPI 与 Web generated derivative 已同步；Web frozen install、lint、typecheck、8 tests、format check、build 与 OpenAPI drift 通过；
- [x] 无新 dependency、lockfile change、migration、schema change 或 development DB mutation；development DB 仍为 identity head 且 `users`/`auth_sessions` 均 0 rows；
- [ ] Credentialed CORS、CSRF、Web auth UI 与真实 browser auth round trip 留给 P0-5D，P0-5C 不构成 browser authentication closure。

P0-5C final review 已 PASS 并转为 completed；P0-5D 证据见下节，P0-5E awaiting explicit approval / not started。

### P0-5D browser authentication closure — 2026-08-14

- [x] Credentialed explicit CORS 共用 `GIA_API_CORS_ORIGINS`，methods 精确为 `GET`/`POST`，headers 精确为 `Content-Type`/`X-GIA-CSRF`，只 expose `X-Request-ID`；
- [x] register/login/logout 统一要求 exact trusted Origin 与 `X-GIA-CSRF: 1`；missing/null/untrusted/duplicate/wrong boundary 返回 `403 CSRF_REJECTED`，`GET /auth/me` 豁免；
- [x] Web `openapi-fetch` client 使用 `credentials: "include"`，只为 unsafe auth POST 添加 CSRF marker；
- [x] 最小 UI 覆盖 loading、unauthenticated register/login、authenticated username、initial `/auth/me` restore 与 logout；
- [x] Web 保留 uppercase-capable raw ASCII username，API caller 接收 raw value，backend canonical lowercase username 在注册结果与 reload restore 中一致显示；
- [x] Web unit suite 16 项通过；API unit 132、integration 18（skipped 0）、full 150 项通过；lint、format、typecheck、build、Alembic head 与 OpenAPI drift 通过；
- [x] 唯一新增 direct Web dev dependency 为 `@playwright/test 1.62.1`；Chromium only；
- [x] Browser E2E 使用 fresh migrated `gia_p05d_*` PostgreSQL database，成功/失败路径均精确 drop；development DB 未被写入；
- [x] 真实 Chromium 验证 register、Cookie flags、`document.cookie` 隔离、reload restore、storage 无 secret、missing-CSRF `403`、logout、后续 `/auth/me` `401` 与 Cookie 清除；selected 1、skipped 0、passed 1；
- [x] Windows Uvicorn runtime 使用 Psycopg-compatible `SelectorEventLoop`；E2E 后 3000/8000 listener 与 `gia_p05d_*` residual 均为 0。

P0-5D actual-source final review 已 PASS 并转为 completed；P0-5E awaiting explicit approval，independent final review not started，因此 P0-5 尚不能转为 `DONE`。

## P0 exit

来源：总纲 P0 路线图及 P0 基础职责。

- [ ] 项目仓库和开发规范可供后续任务使用；
- [ ] 环境配置方式已由正式技术决策确定并验证；
- [ ] V0.1 所需的最小身份边界已验证，且生产环境不会误启不安全的开发身份；
- [x] 已依据 P0-2 批准的技术决策验证 V0.1 所需的关系型数据库、数据访问层和 migration 基础；
- [ ] 自动检查、日志和基础监控已验证；
- [ ] 产品及技术决策记录完整可追溯；
- [ ] P0-1～P0-6 均满足各自验收条件；
- [ ] 已完成 P0-7 独立验收并获得进入 P1 的明确批准。

P0-2 已 Accepted PostgreSQL、SQLAlchemy 2.x 和 Alembic，P0-4 实施基线为 PostgreSQL 18.x，并要求真实 PostgreSQL integration/migration checks。`ADR-015` 已确认 P0/V0.1 initial identity boundary；email/phone/WeChat/OAuth、verified recovery 与完整公开账号产品继续 Deferred，不是 P0-5B 的前置实现范围。

## V0.1 internal validation

目标：验证多角色讨论和状态机，不公开收费。

### 范围

- [ ] 桌面 Web；
- [ ] 文字输入输出；
- [ ] 排序选择、资源分配、方案策划 3 种题型；
- [ ] 12 道人工审核题；
- [ ] 每场 3 名 AI 候选人；
- [ ] 4 种基础角色；
- [ ] 准备、陈述、讨论和总结流程；
- [ ] 基础逐句记录；
- [ ] 简版证据报告；
- [ ] 管理端最小题目配置。

### 边界

- [ ] 未加入支付；
- [ ] 未加入 ASR/TTS；
- [ ] 未加入完整成长系统；
- [ ] 未加入压力事件；
- [ ] 未加入行业题包。

### 核心质量

- [ ] 三名 AI 的行为具有可感知且有意义的差异；
- [ ] 讨论由状态机和发言权调度控制，不陷入长期复述；
- [ ] 用户能够完成选题到简版报告的内部闭环；
- [ ] 重要评价具有可核对的发言证据；
- [ ] AI 不替用户完成答案，也不输出招聘结论。

## V0.5 public MVP

目标：验证用户是否认为产品值得付费。

### 必需能力

- [ ] 语音输入；
- [ ] AI 语音输出；
- [ ] 每场 3 名 AI 候选人；
- [ ] 4 类题型；
- [ ] 20～30 道精品题；
- [ ] 新手和标准模式；
- [ ] 六维评分；
- [ ] 时间戳证据；
- [ ] 5～8 种专项训练；
- [ ] 用户账号；
- [ ] 历史报告；
- [ ] 场次权益和支付；
- [ ] 删除数据和隐私设置；
- [ ] 基础运营后台。

### 核心流程与安全

- [ ] 讨论状态可在刷新或短断线后恢复；
- [ ] 权益不会重复扣减，系统故障场次可自动返还；
- [ ] 题目和评分规则具有版本记录；
- [ ] 用户可执行训练记录和账号删除；
- [ ] 前端无服务端密钥，用户数据隔离，对象存储默认私有；
- [ ] AI 身份明确标识；
- [ ] 报告不输出录取概率、歧视性或人格定性语言；
- [ ] 不完整会话降低置信度，用户可反馈评价准确性。

## V1.0

目标：形成稳定商业产品。

### 新增范围

- [ ] 压力模式；
- [ ] 6～8 种 AI 角色；
- [ ] 40～60 道精品题；
- [ ] 7 天冲刺计划；
- [ ] 成长趋势；
- [ ] 报告音频跳转；
- [ ] 题目 AI 变体；
- [ ] 更完善的模型路由和成本控制；
- [ ] 用户评价申诉；
- [ ] 邀请奖励；
- [ ] 移动端短训练体验优化。

### 稳定商业产品要求

- [ ] 压力模式通过复杂互动制造难度，而非单纯增加攻击性；
- [ ] 更多角色仍能通过盲测区分且不依赖固定剧本；
- [ ] 成长与冲刺围绕真实训练行为，不依赖无意义签到；
- [ ] 报告音频跳转遵守用户授权和数据保留策略；
- [ ] 成本优化没有牺牲角色差异、证据质量或可接受延迟。

## TBD

- TBD：每层检查的负责人、证据链接和签字流程；
- TBD：migration、跨应用及后续阶段的具体检查命令；
- TBD：性能、可靠性和成本阈值的正式基线；
- TBD：公开发布的合规、备案和邀请测试路径；
- TBD：版本回滚、数据迁移和事故响应流程。

这些是派生 TBD，不是总纲原始 D-xxx。

## Future work

- P0-5D：completed；P0-5E awaiting explicit approval，independent final review not started。
- P0-6：补充实际自动检查和基础可观测性项目。
- P0-7：执行并记录 P0 exit 验收。
- 各版本发布任务：补充负责人、环境、命令、证据和发布/回滚步骤。

## 与其他文档关系

- 范围和路线：[`ROADMAP.md`](ROADMAP.md)
- 当前任务：[`TASKS.md`](TASKS.md)
- 产品验收：[`PRODUCT_REQUIREMENTS.md`](PRODUCT_REQUIREMENTS.md)
- 隐私与安全：[`PRIVACY_AND_SAFETY.md`](PRIVACY_AND_SAFETY.md)
- 技术与数据：[`ARCHITECTURE.md`](ARCHITECTURE.md)、[`DATABASE.md`](DATABASE.md) 和 [`API.md`](API.md)
