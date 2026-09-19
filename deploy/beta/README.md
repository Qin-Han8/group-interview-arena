# Hong Kong Closed Text Beta deployment package

This directory packages the existing P1 text-only closed loop for one Ubuntu 24.04 x86_64 host. It is an invitation-only, free beta package, not the D-005 public MVP. It does not provision Alibaba Cloud, DNS, OSS or any other external resource.

`infra/compose.yaml` remains the local-development PostgreSQL responsibility. This file is the separate production-shaped beta topology.

## Services and exposure

- `caddy`: the only service publishing host ports (`80/tcp`, `443/tcp`, `443/udp`);
- `web`: Next.js standalone server on private `edge:3000`;
- `api`: one Uvicorn worker on private `edge:8000`, plus private `data` access;
- `postgres`: PostgreSQL 18.4 on private `data:5432`, backed by `postgres_data`;
- `migrate`: one-shot Alembic image on `data`, enabled only with the `ops` profile or `docker compose run`.

Web and API images run as non-root users. Caddy runs as its image user with only `NET_BIND_SERVICE`; no service is privileged. Long-running services use `unless-stopped`, JSON-file log rotation and named state volumes.

## Configuration boundary

Create the real file locally and keep it out of Git:

```shell
cp deploy/beta/.env.example deploy/beta/.env
chmod 600 deploy/beta/.env
```

Replace every `CHANGE_ME` value. Generate independent high-entropy PostgreSQL and provider credentials; URL-encode the database password inside `GIA_API_DATABASE_URL`. Do not add a session secret: the current identity implementation uses random opaque tokens and database digests and has no session-secret setting.

`NEXT_PUBLIC_API_BASE_URL` is public and build-time frozen by Next.js. A production beta Web image must be built with exactly:

```text
https://api.beta.lijingai.com
```

Changing the value requires rebuilding the Web image. Setting it only on the running container is ineffective. Provider key, database URL and database password are server-only runtime values and must never be build arguments, image layers, `NEXT_PUBLIC_*` values or committed files.

Production security values are fixed by Compose: `GIA_API_ENVIRONMENT=production`, `GIA_API_SESSION_COOKIE_SECURE=true` and `GIA_API_OTEL_TRACING_ENABLED=false`. `GIA_API_CORS_ORIGINS` must remain the exact JSON array `["https://beta.lijingai.com"]`; it is the shared CORS, CSRF and WebSocket trusted-origin source. Wildcards are invalid.

## Production-shaped local validation mode

Local validation uses the same images, services, networks and routes. Only host names, Caddy certificate issuer, Web build-time public API URL and the corresponding exact trusted origin change in the untracked `.env`:

```dotenv
NEXT_PUBLIC_API_BASE_URL=https://api.beta.localhost
BETA_WEB_SITE=beta.localhost
BETA_API_SITE=api.beta.localhost
BETA_CADDY_TLS=tls internal
GIA_API_CORS_ORIGINS=["https://beta.localhost"]
```

`.localhost` is reserved for local use, but resolver behavior varies. Verify both names resolve to `127.0.0.1`; for browser testing, use temporary local hosts entries or an equivalent browser host-resolver rule if needed. The `curl --resolve` commands below do not require hosts-file or real-DNS changes. Caddy uses an internal CA in this mode; use `curl --insecure` for command-line smoke tests or explicitly trust only the generated local Caddy root certificate on a test machine. Never carry `tls internal` into the real beta `.env`.

## Build and static checks

Run from the repository root:

```shell
docker compose --env-file deploy/beta/.env -f deploy/beta/compose.yaml config --quiet
docker compose --env-file deploy/beta/.env -f deploy/beta/compose.yaml build migrate api web
docker image inspect gia-beta-web:local --format '{{.Config.User}}'
docker image inspect gia-beta-api:local --format '{{.Config.User}}'
docker image inspect gia-beta-api-migrate:local --format '{{.Config.User}}'
```

Expected image user is `10001:10001`. Before a real beta build, verify the browser bundle has the intended API domain and no localhost fallback:

```shell
docker run --rm --entrypoint sh gia-beta-web:local -c "grep -R -a -q 'api.beta.lijingai.com' /app && ! grep -R -a -E -q 'localhost:8000|http://localhost' /app"
```

## First deployment sequence

Deploy only a committed SHA whose CI run is green. From that exact checkout:

```shell
docker compose --env-file deploy/beta/.env -f deploy/beta/compose.yaml build migrate api web
docker compose --env-file deploy/beta/.env -f deploy/beta/compose.yaml up -d postgres
docker compose --env-file deploy/beta/.env -f deploy/beta/compose.yaml ps
docker compose --env-file deploy/beta/.env -f deploy/beta/compose.yaml run --rm migrate
docker compose --env-file deploy/beta/.env -f deploy/beta/compose.yaml run --rm migrate python -c "import asyncio; from group_interview_arena_api.core.config import DatabaseSettings; from group_interview_arena_api.db.runtime import create_database_engine, create_database_session_factory; from group_interview_arena_api.modules.question_personas.seed import seed_question_persona_foundation; engine=create_database_engine(DatabaseSettings()); print(asyncio.run(seed_question_persona_foundation(create_database_session_factory(engine))))"
docker compose --env-file deploy/beta/.env -f deploy/beta/compose.yaml up -d api
docker compose --env-file deploy/beta/.env -f deploy/beta/compose.yaml up -d web
docker compose --env-file deploy/beta/.env -f deploy/beta/compose.yaml up -d caddy
docker compose --env-file deploy/beta/.env -f deploy/beta/compose.yaml ps
```

The migration container command is exactly `alembic upgrade head`; the candidate head is `f1a17b17c008`. Re-running the command must be a no-op success. API startup never executes Alembic and `Base.metadata.create_all()` is not used.

Migrations create schema, not product content. The following explicit command reuses the existing reviewed, idempotent P1 catalog service and must report `question_versions_inserted=12` on a fresh database; a repeat must report zero inserts. It is intentionally not hidden inside migration or API startup. After it completes, `GET /questions` must return exactly 12 published Question Versions in the accepted 4/4/4 catalog. If it raises `SeedDataConflictError` or `PublishedQuestionMutationError`, stop deployment and investigate; do not overwrite rows.

Smoke the real endpoints after DNS and certificates are ready:

```shell
curl --fail --silent --show-error https://api.beta.lijingai.com/health
curl --fail --silent --show-error https://beta.lijingai.com/ >/dev/null
```

For local internal-TLS mode:

```shell
curl --insecure --fail --silent --show-error --resolve api.beta.localhost:443:127.0.0.1 https://api.beta.localhost/health
curl --insecure --fail --silent --show-error --resolve beta.localhost:443:127.0.0.1 https://beta.localhost/ >/dev/null
```

Then verify in a browser: registration/login, `Secure; HttpOnly; SameSite=Lax` host-only `gia_session`, exact CORS allow-origin with credentials, rejected missing/wrong CSRF headers, authenticated WebSocket upgrade and reconnect, one complete deterministic test session/report flow, and reload persistence. Automated complete-session proof must use the existing network-free harness; do not put a fake-provider switch into the production image.

## Update procedure

```text
committed Git SHA
  -> CI PASS
  -> server fetch and checkout exact SHA
  -> validate Compose config quietly without rendering runtime secrets
  -> build images
  -> start/wait PostgreSQL
  -> run one-shot migration
  -> run/verify the idempotent catalog bootstrap on first deploy
  -> start API, Web and Caddy
  -> smoke and security checks
```

Record the old and new SHA, image IDs, migration head, backup name and smoke result. This phase intentionally has no push-to-main automatic deployment.

## Rollback

1. Stop application traffic or put the beta into a short maintenance window.
2. Confirm the previous SHA is compatible with the current database head. Never guess and never automatically downgrade.
3. Check out the exact previous accepted SHA and rebuild its `api` and `web` images.
4. Start API/Web/Caddy against the unchanged named PostgreSQL volume.
5. Repeat health, auth, CORS/CSRF, WebSocket and persistence smoke tests.

HK-BETA-1 adds no database revision, so its package rollback requires no database change. For a future incompatible migration, prefer a reviewed forward fix; restore from a pre-deploy backup only after an explicit data-loss assessment. Never pass Compose's volume-removal flag during beta shutdown because it deletes named state volumes.

## Backup and restore drill

Minimum beta policy:

- create one PostgreSQL custom-format dump daily;
- retain seven daily recovery points;
- copy each successful dump off the ECS host; Alibaba OSS is a later candidate, not created by this phase;
- encrypt and access-control the off-host copy;
- record dump SHA-256, database name, Git SHA, migration head, time and operator;
- execute and document one restore drill before inviting users, then repeat after material schema/backup changes.

Example dump command (the redirection writes on the host, not inside the container):

```shell
umask 077
docker compose --env-file deploy/beta/.env -f deploy/beta/compose.yaml exec -T postgres sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' > /approved/off-host-staging/gia-beta-YYYYMMDD.dump
sha256sum /approved/off-host-staging/gia-beta-YYYYMMDD.dump
```

Restore drill into a separately named disposable database; never overwrite the beta database:

```shell
docker compose --env-file deploy/beta/.env -f deploy/beta/compose.yaml exec -T postgres sh -c 'createdb -U "$POSTGRES_USER" gia_beta_restore_drill'
docker compose --env-file deploy/beta/.env -f deploy/beta/compose.yaml exec -T postgres sh -c 'pg_restore -U "$POSTGRES_USER" -d gia_beta_restore_drill --exit-on-error' < /approved/off-host-staging/gia-beta-YYYYMMDD.dump
docker compose --env-file deploy/beta/.env -f deploy/beta/compose.yaml exec -T postgres sh -c 'psql -U "$POSTGRES_USER" -d gia_beta_restore_drill -c "SELECT version_num FROM alembic_version"'
docker compose --env-file deploy/beta/.env -f deploy/beta/compose.yaml exec -T postgres sh -c 'dropdb -U "$POSTGRES_USER" gia_beta_restore_drill'
```

The final `dropdb` targets only the explicitly named drill database and is run only after verification evidence is captured. Seven-day pruning and off-host transfer must be implemented by a separately reviewed host job; this repository does not contain cloud credentials or an OSS client.

## Minimal observation

```shell
docker compose --env-file deploy/beta/.env -f deploy/beta/compose.yaml ps
docker compose --env-file deploy/beta/.env -f deploy/beta/compose.yaml logs --since 30m --tail 200 caddy web api postgres
docker stats --no-stream
docker system df
docker volume inspect group-interview-arena-beta_postgres_data
docker compose --env-file deploy/beta/.env -f deploy/beta/compose.yaml exec -T postgres sh -c 'pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
```

Application logs retain the existing structured logging and `request_id` boundary. OTel is default-disabled. No Sentry, Prometheus/Grafana, collector or other vendor is introduced.

Caddy HTTP access logging is intentionally disabled so the reverse proxy does not create a second record of raw request paths or query strings. Caddy's normal runtime and error logging remains available through the container log stream.

## Exposed-port audit and safe cleanup

```shell
docker compose --env-file deploy/beta/.env -f deploy/beta/compose.yaml ps
docker port $(docker compose --env-file deploy/beta/.env -f deploy/beta/compose.yaml ps -q caddy)
```

The runtime listing must show host mappings only for Caddy 80/443. Web 3000, API 8000 and PostgreSQL 5432 may appear as container ports but never as published host ports. Use the earlier `config --quiet` command for real-environment validation; do not render a Compose config backed by the real `.env` into terminal output or logs.

For an ordinary stop or local acceptance cleanup that preserves named data:

```shell
docker compose --env-file deploy/beta/.env -f deploy/beta/compose.yaml stop
docker compose --env-file deploy/beta/.env -f deploy/beta/compose.yaml down
```

`down` removes containers and networks but preserves the PostgreSQL and Caddy named volumes. Removing any named volume is a separate destructive decision: first resolve its exact project-qualified name, prove it belongs only to a disposable local acceptance project, and obtain explicit approval. Never remove the beta PostgreSQL volume as routine cleanup or rollback.

## Deferred before broader exposure

The package does not implement invitation enforcement, durable auth retry/rate limiting, verified recovery, account deletion, per-user session quotas, LLM invocation/token/cost ceilings or concurrent-session ceilings. It also does not add payment, Voice/P2, Redis, queues, RDS, CDN, Kubernetes, Terraform, automatic CD, ICP work or commercial operations. Provider timeout/rate-limit/unavailable failures remain safely typed, but there is no automatic retry/fallback or hard cost ceiling.

HK-BETA-2 / actual-go-live hardening must separately design a least-privilege PostgreSQL runtime role. The current `POSTGRES_USER` is also the application database user, and Docker Official PostgreSQL initializes that role as a superuser. HK-BETA-1 intentionally adds no init script, role migration or database permission framework.

Those are explicit go-live risk decisions. Packaging readiness does not itself authorize DNS cutover or invited-user access.
