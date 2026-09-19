# HK-BETA-2A1 — Closed Beta Admission, Durable Auth Throttling & Trusted Client Source

## Goal

把现有 P1 文字闭环收紧为可验证的 Hong Kong Closed Text Beta admission/auth boundary：只有持有一次性邀请码的用户可以注册，register/login 滥用限制在 PostgreSQL 中跨进程和重启保持，真实客户端源只由 Caddy 覆盖传递；不把本任务扩大成公开商业 Production。

## Context

- Source of Truth：`PROJECT_MASTER_PLAN.md`、`ADR-015`、`ADR-016`、当前 `TASKS.md` 与本计划。
- Baseline：P1 `DONE / CLOSED`；HK-BETA-0 与 HK-BETA-1 complete；开始实施时 HEAD 为 `2d6c10756a0dacfc43aa1cfc48dd274843cf6ed8`、branch `main`、working tree clean，Master Plan SHA-256 为 `2388A9660320406CB35D5354126AD71C6849A98DB7C4A356796CA951BF372F26`。
- Existing identity：username/password、Argon2id、PostgreSQL opaque session、Secure/HttpOnly/SameSite Cookie、exact CORS/CSRF/WebSocket Origin boundary。
- Existing deployment：Caddy → Next.js/FastAPI → PostgreSQL single-host Compose；只有 Caddy 发布 host ports。

## Scope

- `beta_invitations` 与 `auth_rate_limit_buckets` 两张表及单一线性 Alembic revision；
- one-time、not username-bound、default 14-day、SHA-256-at-rest invitation；
- invitation row lock + user + session + consume 单 transaction；
- register/login PostgreSQL short independent limiter transactions；
- 固定 16,384 account shards、HMAC bucket identifiers、bounded invalid-invite cardinality；
- Caddy overwrite `X-GIA-Client-IP` 与 API IPv4/IPv6 canonicalization/fail-closed trusted mode；
- Web secret invitation field、generic copy、提交后清空、OpenAPI derivative；
- operator-only CLI `generate --count --expires-in-days --label`；
- deployment topology/config/docs、CI static gates 与风险匹配测试。

## Non-goals

不实现 recovery、password denylist 扩展、account deletion、quota/token/cost ceiling、payment、Voice/P2、Redis、queue、Admin UI、email/SMS、OAuth/social login、Kubernetes、ECS/DNS、backup、PostgreSQL least-privilege role 或任何自动 CD。

## Dependencies

- PostgreSQL 18.x、SQLAlchemy async 2.x、psycopg 3.3.x、Alembic current history；
- Caddy 2.10.2、现有 HK-BETA-1 Compose/Docker images；
- FastAPI OpenAPI → `openapi-typescript` contract flow；
- 既有 structured logging、request_id、Cookie/CORS/CSRF/WebSocket security boundaries。

## Implementation steps

1. 核实 governance、Git/HEAD/working tree、Master Plan hash 与 actual source。
2. 新增两表 ORM 与 `f1a18a18c009` linear migration，不改旧 revision。
3. 实现 invite generation/digest/CLI 与 registration atomic consumption。
4. 实现 PostgreSQL row-locked durable limiter、固定 thresholds 与 bounded identifiers。
5. 实现 trusted client source resolution、production fail-closed settings 与 generic error contracts。
6. 分离 `web-edge`/`api-edge`，保留 API provider-only egress；Caddy 覆盖内部 header。
7. 增加 Web invitation secret input，重新生成 OpenAPI contract。
8. 同步 deployment/operator/governance docs 与 CI topology assertions。
9. 执行 unit/integration/Web/Compose/Caddy/migration/secret/diff validation。

## Validation

- API Ruff、Pyright、unit tests；
- real PostgreSQL migration fresh/repeat/downgrade/re-upgrade/check；
- valid/invalid/expired/revoked/reused/concurrent invite tests；
- register/login thresholds、restart persistence、bounded cardinality/account shards；
- enumeration、CSRF、Cookie、owner isolation、no-secret logging regression；
- Web lint/type/unit/build、OpenAPI drift 与 Chromium happy path；
- Compose config/topology、Caddy validate/header overwrite、image/build audits；
- `git diff --check`、secret scan、Master Plan hash/unchanged check。

## Decisions

- Accepted parameters are recorded in `ADR-016`; this plan does not create a second authority.
- No automatic cleanup job: expired limiter/invitation rows are harmless at current Beta scale; future retention work requires a separate task.
- Login `Retry-After` remains one generic 900-second value so the rejected scope is not disclosed.
- Recovery remains deferred/blocking under `ADR-015`; this task does not reinterpret “closed” as authorization to weaken that rule.

## Risks and carry-forward actual-go-live blockers

以下事项均未由 HK-BETA-2A1 关闭，继续保持 open；在各自后续任务完成并验收前，actual go-live 仍 `BLOCKED`：

- Row-lock order must remain stable to avoid limiter deadlocks.
- Caddy header trust is safe only while API 8000 is unpublished and Caddy is the sole ingress.
- HMAC key rotation changes bucket identities and therefore resets effective limiter history; rotate only through an explicit operational decision.
- Migration rollback after invitation use may destroy admission/audit facts; production-style rollback should prefer a compatible forward fix.
- Verified recovery remains required before public testing under ADR-015; stronger compromised-password control also remains open.
- Current `POSTGRES_USER` remains an application superuser; least-privilege runtime role is a separate actual-go-live blocker.
- `beta_invitations.consumed_by_user_id` currently uses `ON DELETE RESTRICT`, and the consumption-pair constraint requires the consumed user to remain present. A later account/data deletion phase must explicitly resolve this schema dependency; this finding is carry-forward only here.
- Because `REGISTER_INVITE` bookkeeping is created only for invitations that actually exist, repeated attempts retain a low-risk invitation-existence timing/rate-limit side channel. Raw invitations remain at least 256-bit high entropy and ADR-016's per-existing-invite limiter is unchanged, but strict indistinguishability is not claimed.
- Off-host backup plus a verified restore drill remain open; a same-ECS copy is not sufficient.
- Per-user quota、LLM token/cost ceiling and concurrent-session ceiling remain open.
- A controlled production-provider smoke with production configuration remains open; HK-BETA-2A1 made no such go-live claim.
- Account/data deletion remains open independently of the invitation foreign-key dependency above.

## Progress

- Completed: governance/source recovery、baseline verification、accepted design freeze、ORM/migration/backend/Web/deployment implementation、OpenAPI regeneration、API `607` non-integration + `262` PostgreSQL integration tests、Web `285` unit tests、Chromium `5 + 2` acceptance、Ruff/Pyright/Web lint/type/build、migration/OpenAPI、Compose/Caddy/image/topology 与 secret/diff validation。
- Completed finding: registration limiter SQL-order regression proved global/source bookkeeping now precedes invitation lookup；random invitations still create no per-invite bucket，only existing invitations enter the bounded invitation limiter。
- Completed: actual-source review and finding-only remediation/re-review passed；F1 limiter short-circuit、F2 real Caddy proxy-path proof、F3 governance correction and F4 browser-storage copy correction are closed.
- Accepted final commit `664857efe8ef9b27c055429e36c45d67ef9395a6` is pushed to `main`; exact GitHub Actions CI run `35452988196` completed successfully.
- Closed: HK-BETA-2A1 is `DONE / CLOSED`; implementation findings are closed, while the carry-forward actual-go-live blockers above remain open.
- Boundary: actual go-live remains `BLOCKED`; HK-BETA-2A2 has not started and P2 remains `NOT_STARTED`.
