# syntax=docker/dockerfile:1

FROM ghcr.io/astral-sh/uv:0.12.4 AS uv

FROM python:3.14-slim-trixie AS build-base

COPY --from=uv /uv /uvx /bin/

ENV UV_CACHE_DIR=/tmp/uv-cache
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
ENV UV_PROJECT_ENVIRONMENT=/opt/venv

WORKDIR /app

COPY apps/api/pyproject.toml apps/api/uv.lock ./

FROM build-base AS runtime-builder

RUN uv sync --frozen --no-dev --no-install-project
COPY apps/api/src ./src
RUN uv sync --frozen --no-dev

FROM build-base AS migrate-builder

RUN uv sync --frozen --no-dev --group ops --no-install-project
COPY apps/api/src ./src
COPY apps/api/alembic.ini ./alembic.ini
COPY apps/api/migrations ./migrations
RUN uv sync --frozen --no-dev --group ops

FROM python:3.14-slim-trixie AS runtime-base

ENV PATH=/opt/venv/bin:${PATH}
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

RUN groupadd --system --gid 10001 gia \
    && useradd --system --uid 10001 --gid gia --no-create-home gia

WORKDIR /app

FROM runtime-base AS runtime

COPY --from=runtime-builder --chown=gia:gia /opt/venv /opt/venv
COPY --from=runtime-builder --chown=gia:gia /app/src ./src

USER 10001:10001

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3).read()"]

CMD ["uvicorn", "group_interview_arena_api.app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--loop", "group_interview_arena_api.core.event_loop:create_runtime_event_loop", "--no-access-log"]

FROM runtime-base AS migrate

COPY --from=migrate-builder --chown=gia:gia /opt/venv /opt/venv
COPY --from=migrate-builder --chown=gia:gia /app/src ./src
COPY --from=migrate-builder --chown=gia:gia /app/alembic.ini ./alembic.ini
COPY --from=migrate-builder --chown=gia:gia /app/migrations ./migrations

USER 10001:10001

CMD ["alembic", "upgrade", "head"]

