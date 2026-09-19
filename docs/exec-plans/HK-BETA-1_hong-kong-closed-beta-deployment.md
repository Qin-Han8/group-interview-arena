# HK-BETA-1 Hong Kong Closed Beta Deployment Packaging

- Status: `DONE / LOCAL_ACCEPTANCE_PASS`
- Target: `Hong Kong Closed Text Beta`
- Product classification: invitation-only, free, text-only beta; not the D-005 public MVP
- Baseline branch: `main`
- Baseline HEAD: `91f29b1e45f6cf71cdfa530293f7716bda3bfa37`
- Immutable master-plan SHA-256: `2388A9660320406CB35D5354126AD71C6849A98DB7C4A356796CA951BF372F26`
- Authority: `PROJECT_MASTER_PLAN.md` > Accepted `DECISIONS.md` > `ROADMAP.md` > `TASKS.md` > this plan > domain docs > code

## Goal

Package the existing P1 closed text loop for a single-host Hong Kong closed beta and prove the package locally. This phase creates production-shaped container images, a separate beta Compose topology, Caddy routing, safe configuration examples, operator documentation and CI packaging gates. It does not provision or connect cloud resources and does not authorize public exposure.

## Frozen topology

```text
Internet :80/:443
  -> Caddy
       -> web:3000 (edge network only)
       -> api:8000 (edge + data networks)
            -> postgres:5432 (data network only)

migrate -> postgres:5432 (data network only, one-shot)
```

Only Caddy publishes host ports. PostgreSQL, API and Web use Docker-internal connectivity. `infra/compose.yaml` remains local-development-only and is not modified.

## Approved changed set

- `apps/web/next.config.ts`
- `apps/web/Dockerfile`
- `apps/api/Dockerfile`
- `apps/api/pyproject.toml`
- `apps/api/uv.lock`
- `.dockerignore`
- `deploy/beta/compose.yaml`
- `deploy/beta/Caddyfile`
- `deploy/beta/.env.example`
- `deploy/beta/README.md`
- `.github/workflows/ci.yml`
- this execution plan

No runtime business flow, REST/WS contract, schema, Alembic revision, provider behavior, product content or master-plan change is approved.

## Implementation decisions

1. Next.js uses `output: "standalone"`. `NEXT_PUBLIC_API_BASE_URL` is supplied as a mandatory Docker build argument because browser code is build-time frozen. The production candidate value is exactly `https://api.beta.lijingai.com`.
2. Web runtime is Node 24, runs as a non-root user, and starts the standalone server with `HOSTNAME=0.0.0.0`, `PORT=3000`, `node server.js`.
3. API runtime is CPython 3.14 with a frozen uv install, one Uvicorn worker, the existing project loop factory and no reload/debug mode.
4. Alembic becomes an explicit `ops` dependency group included by `dev`. The API Dockerfile has separate `runtime` and `migrate` targets; the runtime image does not install test/lint/typecheck dependencies.
5. Migration remains an explicit operator step using the existing linear Alembic history. API startup never runs migrations and never calls `create_all()`.
6. CORS, CSRF and WebSocket Origin reuse the one existing `GIA_API_CORS_ORIGINS` source of truth. Production is the exact origin `https://beta.lijingai.com`; wildcard CORS is forbidden.
7. Production Cookie settings are `HttpOnly`, host-only, `SameSite=Lax`, `Secure=true`. OTel remains disabled unless separately configured with an approved collector.
8. Caddy performs ordinary HTTP and WebSocket reverse proxying without a new Next.js business proxy. A host-name/TLS substitution supports local validation with `.localhost` and Caddy internal TLS while retaining the same services and routes. HTTP access logging is disabled so Caddy does not create a second raw-path/query record; normal Caddy runtime/error logging remains available.

## Deployment and migration sequence

```text
checkout committed SHA after CI PASS
  -> build images
  -> start PostgreSQL and wait healthy
  -> docker compose run --rm migrate (alembic upgrade head)
  -> explicit idempotent V0.1 catalog bootstrap on first deploy
  -> start API and wait healthy
  -> start Web
  -> start Caddy
  -> smoke/security/persistence checks
```

The candidate migration command is:

```shell
docker compose --env-file deploy/beta/.env -f deploy/beta/compose.yaml run --rm migrate
```

The image command behind it is exactly `alembic upgrade head`.

Actual fresh-database validation established that migrations create schema only and the API lifespan seeds Prompt Versions but not the reviewed V0.1 question catalog. The deployment therefore includes a documented explicit one-shot invocation of the existing idempotent `seed_question_persona_foundation(...)` service before first API exposure. This is deployment initialization, not a new content path, API startup hook, migration or sixth Compose service.

## Acceptance gates

- frozen Web/API dependency installation and image builds;
- standalone artifact contains the selected public API URL and no localhost API fallback;
- Compose renders with only Caddy publishing `80/443`, required network separation, named volumes and no privileged container;
- fresh PostgreSQL migration and repeated `upgrade head` succeed at single head `f1a17b17c008`;
- API `/health`, Web and Caddy routing smoke;
- exact CORS, credentialed preflight, Secure Cookie, CSRF rejection and success;
- WebSocket upgrade/auth/origin/reconnect through Caddy;
- existing deterministic complete-session/report/restart evidence remains green without a real provider call;
- restart persistence, provider-failure behavior, secret scan, image-user and exposed-port audit;
- existing API/Web quality, migration, integration and Chromium gates remain green.

If a complete provider-backed container session would require a production test backdoor, it is not added. The accepted network-free full-session harness is used for business-flow proof and the container path separately proves HTTP/Cookie/CORS/CSRF/WebSocket routing.

## Rollback boundary

Application rollback checks out the previous accepted Git SHA, rebuilds its images and starts them against the same database only after confirming that the previous code supports the current schema. Database downgrades are not automatic. Because HK-BETA-1 adds no migration, rollback does not alter data. Any future irreversible migration must define a forward-fix/restore decision before deployment.

## Deferred public-exposure gates

Invitation enforcement, durable auth rate limiting, verified recovery, account deletion, per-user/session quota, LLM token/cost ceiling, concurrent-session ceiling, payment, Voice/P2, Redis, queues, RDS, OSS automation, CDN, Terraform, Kubernetes, automatic CD, ICP work, DNS and ECS purchase remain deferred. Their absence blocks actual go-live unless explicitly accepted for a tightly controlled operator-invited test.

HK-BETA-2 / actual-go-live hardening must also separate the application database identity from the Docker Official PostgreSQL bootstrap superuser. In this package `POSTGRES_USER` is both roles; HK-BETA-1 does not add an init script, role migration or database permission framework.

## Stop conditions

Stop if packaging requires changing the master plan, business/runtime contracts, existing migrations, product routes, provider semantics, local `infra/compose.yaml`, or adding a test-only production backdoor, cloud resource, registry push or automatic deployment.

## Local acceptance record — 2026-09-19

- Docker Desktop `29.6.2` built the Web, API runtime and API migrate targets. All final image users are `10001:10001`; API runtime excludes Alembic/test tools and migrate adds Alembic without pytest/Ruff/Pyright.
- The production Web image contains `api.beta.lijingai.com` and contains neither `localhost:8000` nor `http://localhost`. Final image metadata/history contains no synthetic acceptance credential or example secret value.
- Production and `tls internal` Caddy configurations validate. The local stack exposed only Caddy 80/443; Web 3000, API 8000 and PostgreSQL 5432 remained container-only.
- A fresh PostgreSQL 18.4 named volume migrated through the immutable linear history to `f1a17b17c008`; repeated migration was a no-op. The explicit V0.1 catalog bootstrap inserted 4 personas/12 questions and repeated with zero inserts.
- Through Caddy internal TLS, API `/health`, standalone Web, exact credentialed CORS, disallowed origin, missing-CSRF rejection, host-only Secure/HttpOnly/SameSite=Lax Cookie, authenticated WebSocket catch-up and reconnect passed.
- Restarting PostgreSQL, API, Web and Caddy preserved head `f1a17b17c008`, 12 questions, two acceptance users and one session. A dump/restore into the separately named `gia_beta_restore_drill` database preserved those counts and the migration head; the drill database was then dropped.
- API gates passed: frozen sync/lock, Ruff, format, strict Pyright, `600` unit tests, `256` PostgreSQL integration tests, Alembic heads/current/check and OpenAPI drift.
- Web gates passed: frozen install, lint, format, typecheck, `283` unit tests and production build. Existing Chromium E2E passed `5 + 2`; P1-7E full session/report/reload/second API restart passed `2`. All provider paths in these acceptance runs were network-free; no real LLM call occurred.
- The isolated acceptance containers, networks, PostgreSQL/Caddy volumes, temporary `.env` and acceptance script were removed. Existing local-development PostgreSQL remained untouched.
- `PROJECT_MASTER_PLAN.md` remains byte-identical. No schema/migration/runtime business flow/provider change, dependency installation outside frozen project workflows, cloud action, registry push, commit or Git push occurred.

Deployment package conclusion: `READY` for review. Actual go-live conclusion: `BLOCKED` pending operator/cloud/DNS/TLS/backup execution and explicit acceptance of the deferred closed-beta exposure gates; this plan does not authorize them.
