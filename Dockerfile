FROM node:24-bookworm-slim AS web
WORKDIR /web
RUN npm install -g pnpm@11.25.0
COPY frontend/package.json frontend/pnpm-lock.yaml frontend/pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile
COPY frontend/ ./
RUN pnpm build
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY engine/ ./engine/
COPY config/ ./config/
COPY reports/metrics.json ./reports/metrics.json
COPY --from=web /web/dist ./frontend/dist
RUN useradd --create-home sandbox && mkdir -p /var/lib/pranatwin && chown -R sandbox:sandbox /app /var/lib/pranatwin
USER sandbox
EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=3s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health',timeout=2)"
CMD ["python","-m","uvicorn","engine.api:app","--host","0.0.0.0","--port","8000","--no-access-log"]
