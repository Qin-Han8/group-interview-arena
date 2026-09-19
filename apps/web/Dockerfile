# syntax=docker/dockerfile:1

FROM node:24-bookworm-slim AS dependencies

ENV PNPM_HOME=/pnpm
ENV PATH=${PNPM_HOME}:${PATH}
ENV NEXT_TELEMETRY_DISABLED=1

WORKDIR /workspace

RUN corepack enable && corepack prepare pnpm@11.21.0 --activate

COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY apps/web/package.json apps/web/package.json

RUN pnpm install --frozen-lockfile --filter @group-interview-arena/web

FROM dependencies AS builder

ARG NEXT_PUBLIC_API_BASE_URL
ENV NEXT_PUBLIC_API_BASE_URL=${NEXT_PUBLIC_API_BASE_URL}

COPY apps/web apps/web

RUN node -e "const value=process.env.NEXT_PUBLIC_API_BASE_URL; const url=new URL(value); if (url.protocol !== 'https:' || url.username || url.password || url.search || url.hash) process.exit(1)"
RUN pnpm --filter @group-interview-arena/web build

FROM node:24-bookworm-slim AS runtime

ENV NODE_ENV=production
ENV HOSTNAME=0.0.0.0
ENV PORT=3000

RUN groupadd --system --gid 10001 nextjs \
    && useradd --system --uid 10001 --gid nextjs --no-create-home nextjs

WORKDIR /app/apps/web

COPY --from=builder --chown=nextjs:nextjs /workspace/apps/web/.next/standalone /app
COPY --from=builder --chown=nextjs:nextjs /workspace/apps/web/.next/static ./.next/static

USER 10001:10001

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD ["node", "-e", "fetch('http://127.0.0.1:3000/').then(r=>{if(!r.ok)process.exit(1)}).catch(()=>process.exit(1))"]

CMD ["node", "server.js"]
