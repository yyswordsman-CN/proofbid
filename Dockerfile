FROM node:22-alpine AS web-builder
WORKDIR /app/apps/web
COPY apps/web/package.json apps/web/package-lock.json ./
RUN npm ci
COPY apps/web/ ./
RUN npm run build

FROM python:3.12-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080 \
    PROOFBID_PROJECT_ROOT=/app \
    PROOFBID_WEB_DIST=/app/apps/web/dist
WORKDIR /app
COPY requirements-runtime.txt ./
RUN python -m pip install --no-cache-dir -r requirements-runtime.txt
COPY pyproject.toml README.md LICENSE ./
COPY src/ ./src/
RUN python -m pip install --no-cache-dir --no-deps .
COPY examples/ ./examples/
COPY --from=web-builder /app/apps/web/dist ./apps/web/dist
USER 65532:65532
CMD ["sh", "-c", "uvicorn proofbid.service:app --host 0.0.0.0 --port ${PORT}"]
