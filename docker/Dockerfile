# hermes-agent-gui — multi-stage Dockerfile (Phase 10).
# Stage 1 builds the Vite SPA. Stage 2 ships a slim Python image that serves
# both the API and the built static assets.

FROM node:22-alpine AS web-build
WORKDIR /app
RUN corepack enable
COPY package.json pnpm-workspace.yaml pnpm-lock.yaml* ./
COPY apps/web/package.json ./apps/web/
RUN pnpm install --frozen-lockfile
COPY apps/web ./apps/web
RUN pnpm --filter @hermes-agent-gui/web build

FROM python:3.12-slim AS runtime
RUN useradd -m -u 1000 hermes && apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY apps/server/requirements.txt ./apps/server/requirements.txt
RUN pip install --no-cache-dir -r apps/server/requirements.txt
COPY apps/server ./apps/server
COPY --from=web-build /app/apps/web/dist ./apps/web/dist
USER hermes
ENV HERMES_GUI_STATE_DIR=/home/hermes/.hermes-agent-gui
ENV HERMES_GUI_HOST=0.0.0.0
ENV HERMES_GUI_PORT=8800
EXPOSE 8800
HEALTHCHECK --interval=15s --timeout=3s CMD curl -fsS http://127.0.0.1:8800/api/health || exit 1
CMD ["python3", "apps/server/server.py", "--host", "0.0.0.0", "--port", "8800"]
