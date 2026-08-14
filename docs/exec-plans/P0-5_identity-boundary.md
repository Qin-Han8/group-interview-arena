# P0-5 Identity Boundary Execution Plan

Status: `P0-5 IN_PROGRESS`; `P0-5A completed`; `P0-5B completed`; `P0-5C awaiting explicit approval`; `P0-5D`～`P0-5E` not started

Target version: `V0.1 Internal Validation`

Approved architecture: [`ADR-015`](../DECISIONS.md#adr-015--initial-identity-and-browser-session-boundary)

Product baseline: [`PROJECT_MASTER_PLAN.md`](../PROJECT_MASTER_PLAN.md)

## Goal

在不扩展为通用账户系统的前提下，为 first-party Web、FastAPI 与 PostgreSQL 建立最小、可验证的身份闭环：username/password credential、稳定 UUIDv4 `user_id`、Argon2id password hash、opaque server-side session、浏览器安全边界以及前后端认证往返。

本计划记录 P0-5 范围内的实施决策和验收边界。除 ADR-015 明确列出的长期架构边界外，本文件中的具体字段、正则、参数候选、TTL、Cookie 和 API 细节都是 P0-5 scoped decisions，不自动成为永久产品契约。

## Current baseline

- P0-4 已完成 PostgreSQL、SQLAlchemy async、Alembic 和 integration test foundation。
- Alembic baseline revision 为 `7c6ccd86b3c5`，必须保持不可变且 migration graph 保持 single head。
- P0-5B 前 development database 为 public product tables = 0 且不存在 `alembic_version`；通过全部 isolated gates 后，现已首次迁移至 identity head `4fe43b42641b`。
- 当前应用已具有 `users`、`auth_sessions`、password/session security primitives；仍没有 session Cookie、认证 API、FastAPI DB lifecycle 或 Web auth flow。
- 现有 typed `GIA_API_CORS_ORIGINS` 是已批准的 browser trusted-origin Source of Truth；P0-5 不建立第二套 CSRF trusted-origin 配置。

## Five-stage decomposition

1. **P0-5A — Identity preflight / security & scope freeze**：`completed`。批准 ADR-015、范围、风险与本执行计划；不实施认证代码。
2. **P0-5B — Identity persistence + migration + security primitives**：`completed`。已实现 identity schema、migration、显式 Argon2id 配置和 session token primitives，并通过最终源码审核。
3. **P0-5C — Backend auth runtime + FastAPI DB lifecycle + API**：`awaiting explicit approval`。获批后接入 request-scoped database session 和最小 auth API。
4. **P0-5D — Web auth round trip + CORS/CSRF + cross-layer validation**：`not started`。完成 Web 技术闭环和浏览器安全验证。
5. **P0-5E — Independent final review**：`not started`。独立复核完整 P0-5 diff、质量门、迁移安全和范围一致性，不新增业务能力。

不得机械增加第六阶段，也不得在未获明确批准时进入下一阶段。

## Approved durable boundary

ADR-015 确认：

- P0/V0.1 首个认证机制是 username + password，内部核心身份是稳定 UUIDv4 `user_id`。
- Password 使用 Argon2id；安全参数由 application 显式拥有并在目标环境 benchmark。
- Browser session 是 PostgreSQL-backed opaque server-side session；当前没有采用 JWT 的真实 requirement。
- Raw session token 只存在于 HttpOnly Cookie；数据库只保存 cryptographic digest。
- `auth_sessions` 属于 FastAPI/PostgreSQL identity boundary。
- Browser boundary 组合 host-only Cookie、credentialed explicit CORS、exact Origin validation、required custom CSRF header 和 SameSite defense-in-depth。
- CORS 与 CSRF exact Origin validation 使用同一份 typed、normalized trusted-origin configuration。
- 未来 phone/WeChat identity 通过 mapping migration 关联既有 `user_id`，当前不预建 provider tables。
- V0.1 self-service account recovery 延后；public testing 前必须重新建立 verified recovery identity / flow。
- JWT 不是永久禁止；若出现 mobile client、third-party API 或 distributed service trust boundary，必须通过新 ADR 重新评估。

## Scoped identity decisions

### Username

- Canonical ASCII login identifier；lowercase storage。
- Pattern：`^[a-z][a-z0-9_]{2,31}$`。
- Length：3–32。
- `username` 不等于未来的 display name。
- 不使用 `CITEXT`。
- 若未来改变 username product semantics，必须明确 migration 与 decision，不能静默修改。

### Password and Argon2id

- P0-5B 唯一新增 direct runtime dependency 为 `pwdlib[argon2]>=0.3.0,<0.4`；实际解析 `pwdlib 0.3.1` 与 `argon2-cffi 25.1.0`，并已在 CPython 3.14.7 验证 API 与 dependency graph。
- Password scoped baseline：15–128 Unicode code points；以一致的 NFC 规范化进行验证和处理，不 trim、不改变大小写、不拼接额外内容、不静默截断。
- Application 必须显式配置并拥有 Argon2id 参数，不能只调用 `PasswordHash.recommended()` 后声称参数永久固定。
- 以下值已通过本机 benchmark，冻结为 P0-5B implementation values，但不是长期 ADR contract：
  - `memory_cost = 65536 KiB`
  - `time_cost = 3`
  - `parallelism = 4`
  - `hash_len = 32`
  - `salt_len = 16`
- 实际使用显式 `PasswordHash((Argon2Hasher(...),))`，未使用 `PasswordHash.recommended()`；5 个本机样本的 hash median 约 54.3 ms、verify median 约 51.6 ms，该观察不构成跨机器性能保证。
- NOW：small application-owned offline password blocklist、context-specific obvious passwords、normalized full-password exact match。
- 不做 substring 禁止，不调用 external breach API，不引入 massive leaked-password dataset、Redis 或 production distributed rate limiter，也不声称完整 NIST compliance。

### `users` implemented schema

P0-5B 已按 P0-5A 批准的 scoped schema baseline 实现：

- `id`: UUIDv4 primary key
- `username`: `VARCHAR(32) UNIQUE NOT NULL`
- `password_hash`: `TEXT NOT NULL`
- `created_at`: `TIMESTAMPTZ NOT NULL`
- `updated_at`: `TIMESTAMPTZ NOT NULL`

DEFER：email、phone、display_name、role、status、is_active、deleted_at、last_login_at、verification timestamps。除非 P0-5B 实施前发现真实 blocker，否则不得扩展字段。

### `auth_sessions` implemented schema

P0-5B 已按 P0-5A 批准的 scoped schema baseline 实现：

- `id`: UUIDv4 primary key
- `user_id`: UUID foreign key → `users.id`, `ON DELETE CASCADE`
- `token_hash`: `BYTEA UNIQUE NOT NULL`
- `created_at`: `TIMESTAMPTZ NOT NULL`
- `expires_at`: `TIMESTAMPTZ NOT NULL`
- 只增加支持 expiry lookup 所必需的适当 index。

DEFER：revoked_at、last_seen_at、IP、user_agent、device、refresh token。

### Session token and lifetime

- Token baseline：`secrets.token_urlsafe(32)`。
- Raw token 只进入浏览器 HttpOnly Cookie，不写数据库、不记录日志、不在 JSON response 返回。
- 数据库以 SHA-256 digest 或等价的 cryptographic digest 查询高熵 token；不得使用 Argon2 做 session lookup token hashing。
- Implementation-scoped default：7-day absolute expiry、no sliding refresh、no refresh token。
- P0-5B/C 若发现明确技术 blocker，可提出变更，但不得静默改变。

### Cookie

Local development baseline：

- `HttpOnly = true`
- `Secure = false`
- `SameSite = Lax`
- `Path = /`
- `Domain` omitted，保持 host-only

Production HTTPS baseline：

- `HttpOnly = true`
- `Secure = true`
- `SameSite = Lax`
- `Path = /`
- `Domain` omitted，保持 host-only

Cookie exact name 属于 P0-5C scoped detail；若现有文档没有已批准名称，本阶段不凭空永久冻结。

### CSRF and trusted origins

所有当前 browser state-changing auth POST（`POST /auth/register`、`POST /auth/login`、`POST /auth/logout`）统一要求：

1. exact Origin validation；
2. Origin 必须属于与 CORS 共用的 normalized `GIA_API_CORS_ORIGINS` set；
3. required custom CSRF header；
4. credentialed explicit CORS；
5. `SameSite=Lax` defense-in-depth。

`GET /auth/me` 不要求 CSRF header。当前只有 first-party Web caller；未来如需 non-browser、mobile 或 third-party auth client，必须通过新的明确 API/security decision 重新评估，不得因此弱化当前 browser boundary。P0-5A 只冻结该策略、不实施，也不新增 `GIA_API_CSRF_TRUSTED_ORIGINS`。

### FastAPI database lifecycle

P0-5C 是 database runtime 的首个真实 application caller，预期生命周期为：

```text
FastAPI lifespan
    → AsyncEngine
    → async_sessionmaker
    → app state
    → request-scoped AsyncSession
```

- 禁止 import-time engine、eager connection、startup migration、`create_all()`、`drop_all()`。
- Database dependency 只管理 session lifecycle，不对所有请求隐式 commit。
- Commit 由 application operation/service boundary 显式拥有。

## Dependency proposal

- P0-5 唯一新 direct runtime dependency 是 `pwdlib[argon2]>=0.3.0,<0.4`；P0-5B 解析并锁定 `pwdlib 0.3.1`、`argon2-cffi 25.1.0`，CPython 3.14.7 compatibility 与实际 password-hash API 已验证。
- `email-validator`：NO；当前没有 email credential 或 email field。
- `PyJWT` / `python-jose`：NO；当前不采用 JWT。
- OAuth/social/auth framework：NO；当前没有对应 caller。
- P0-5A 未安装 dependency；P0-5B 只因上述批准 dependency graph 修改 `pyproject.toml` 与 `uv.lock`。

## Planned API and Web boundary

P0-5C 最小 planned API contract：

- `POST /auth/register`：成功后创建 authenticated session 的候选流程。
- `POST /auth/login`：成功后创建新 session；unknown username 与 wrong password 返回相同的 generic auth failure。
- `POST /auth/logout`：服务端 session invalidation 并清除 Cookie。
- `GET /auth/me`：只返回 `id` 和 `username`；unauthenticated 返回 `401`。

Password、password hash 和 raw token 不得出现在 response。除 unauthenticated `401` 外，具体成功 HTTP status 与 REST error code 由 P0-5C 在现有 error semantics 下落实，当前不制造尚未实现的细节。

P0-5D Web 只实现 register、login、current-user status、logout 的技术闭环。不实现 profile、account center、settings、phone、WeChat、password reset、avatar 或 marketing auth UI。

## Migration policy and safety

- Baseline revision `7c6ccd86b3c5` 不可修改、不 squash。
- P0-5B 已创建 revision `4fe43b42641b`，且仅包含批准的 identity schema；baseline immutable，revision count 2，保持 single head。
- 首次 development DB migration 前，必须先在 fresh isolated temporary database 验证：upgrade、downgrade、re-upgrade、`alembic check` 和 constraints。
- Development DB 操作必须有 exact database-name guard、read-only preflight、schema precondition 和明确获批的实施范围。
- Development DB precondition 已验证：public product tables = 0、`alembic_version` absent；随后首次升级到 identity head并验证 repeat upgrade no-op。
- Development DB 未执行 downgrade；当前精确包含 `users`、`auth_sessions` 与 infrastructure `alembic_version`，两张 product table 行数为 0。

## NOW / DEFER

### NOW in P0-5

- Username/password credential and validation boundary。
- UUIDv4 user identity、`users` 与 `auth_sessions` persistence。
- Explicit benchmarked Argon2id configuration。
- Small offline password blocklist。
- Opaque server-side session、digest-only persistence、Cookie delivery。
- FastAPI DB lifecycle、最小 auth API、Web round trip。
- Shared trusted-origin CORS/CSRF enforcement 和跨层测试。

### DEFER

- Email login、phone login、SMS、WeChat、OAuth/social login。
- JWT、refresh token、MFA、self-service password/account recovery。
- Future identity-provider tables、profile、account center、RBAC。
- External breach API、massive leaked-password dataset、Redis、production distributed rate limiter。
- Account deletion workflow，直至存在需要处理的 owned product data 与正式生命周期决策。

## Exit criteria

### P0-5B

- Dependency stable/Python 3.14/API/graph review complete，且只增加获批的 `pwdlib[argon2]` constraint。
- Explicit Argon2id parameters 已通过目标环境 benchmark，并有 hash/verify/rehash 和 password policy tests。
- `users`、`auth_sessions` models/constraints/indexes 与 session token primitives 符合本计划；无 deferred fields/tables。
- 新 migration single head、baseline unchanged；fresh temporary DB upgrade/downgrade/re-upgrade/check/constraints 全通过。
- 获明确批准并通过 exact-name/read-only/schema preflight 后，才可首次迁移 development DB；不得自动 downgrade。
- Unit、integration、lint、format、typecheck 和 migration gates 全通过；P0-5C 尚未实施并等待明确批准。

### P0-5C

- FastAPI lifespan 建立并清理 AsyncEngine/sessionmaker；request-scoped session 无隐式 commit。
- Register/login/logout/me API 与 generic auth failure、session invalidation、safe response/logging 行为有测试证据。
- Cookie flags、absolute expiry、digest lookup 和 shared-origin CSRF design 按 approved baseline 落实。
- P0-5A 已冻结的 register/login/logout browser-origin protection 已实现并测试，不存在安全策略分叉。
- 无 startup migration、create/drop all、import-time engine 或 raw token persistence。

### P0-5D

- Web register/login/current-user/logout 技术闭环完成，credentials 使用正确。
- CORS middleware 与 CSRF exact Origin validation 消费同一 normalized typed origin set。
- Unsafe authenticated requests 要求 exact Origin + custom CSRF header；Cookie 和 SameSite 行为经真实浏览器或等价跨层验证。
- 无 profile/account center/recovery/provider 等范围扩张。
- Web/API lint、format、typecheck、unit/integration/build、OpenAPI drift 与必要 browser smoke 全通过。

### P0-5E

- 独立审查 ADR、docs、schema、migration、security primitives、API、Web 和 tests 的一致性。
- Fresh migration 与 development DB 状态、single head、baseline immutability、temp DB cleanup 均有重新验证证据。
- Security review 确认无 raw token/password leakage、origin config drift、fake recovery、scope creep 或 credential exposure。
- 所有质量门重新执行并通过；P0-5 才可被建议为 DONE。

## Security risks and public-exposure gates

- **BLOCKER — migration target safety**：development DB exact-name、schema precondition 或 fresh-temp migration gate 任一不满足即停止；不得猜测、自动 downgrade 或修改 baseline。
- **HIGH — password storage / offline guessing / input DoS**：明文不得持久化或记录；限制已批准的最大输入长度；Argon2id 参数必须由应用显式拥有并 benchmark；small blocklist 不能被描述为完整 compromised-password defense。
- **HIGH — online guessing / account enumeration**：unknown username 与 wrong password 使用 generic failure；P0-5 不假装用单进程内存计数器解决生产问题。Public exposure 前必须建立 durable authentication retry/rate limiting 和 stronger compromised-password controls。
- **HIGH — session fixation / theft / raw-token leakage**：每次成功 register/login 创建新 token；raw token 不落库、日志或 JSON；logout 使服务端 session 失效并清 Cookie；unknown、malformed、expired token 均不得产生 authenticated user。
- **HIGH — CSRF / credentialed CORS drift**：host-only Cookie、shared exact origins、required custom header 与 SameSite 必须共同验证；CORS 和 CSRF 不得维护两套 origin configuration。
- **HIGH — account recovery limitation**：V0.1 没有 verified email、verified phone 或 WeChat identity，因此 self-service recovery 明确延后。禁止 security questions、plaintext recovery secret、generic admin reset endpoint 或 fake email recovery；public testing 前必须设计 verified recovery identity / flow。
- **MEDIUM — username normalization / uniqueness race**：canonicalization 在唯一约束前一致完成，数据库 unique constraint 是并发冲突的最终权威，API 使用安全且确定的 conflict semantics。
- **MEDIUM — transaction rollback / test isolation**：registration 的 user/session 必须原子化；失败 operation 显式 rollback；integration tests 继续使用受保护的 exact temporary database lifecycle。
- **MEDIUM — local/production Cookie mismatch**：local HTTP 只允许 scoped `Secure=false`，production HTTPS 必须 `Secure=true`；不得用 localhost 便利永久降低 production policy。
- **LOW — future identity mapping**：不得为了 phone/WeChat 提前创建无调用方的 provider table；真实需求出现时用 migration 映射到既有 `user_id`。

## Progress

- [x] P0-5A approved preflight, ADR-015 and scope freeze
- [x] P0-5B identity persistence, migration and security primitives — completed
- [ ] P0-5C backend auth runtime, DB lifecycle and API — awaiting explicit approval
- [ ] P0-5D Web round trip, CORS/CSRF and cross-layer validation
- [ ] P0-5E independent final review
