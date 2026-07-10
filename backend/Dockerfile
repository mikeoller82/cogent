FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# System deps for `cryptography`, aiohttp, and other wheel builds.
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
        build-essential curl ca-certificates \
 && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt ./requirements.txt
RUN pip install -r requirements.txt

COPY backend/ ./backend/

# PROJECT_ROOT is computed at /app (see cogent_constants._discover_project_root),
# so MEMORY_DIR lives at /app/memory. The compose file bind-mounts these so
# data survives container restarts. cogent_constants will also honour the
# ARTIFACTS_DIR env var, so we never write into ~/Desktop inside the container.
RUN mkdir -p /app/memory /app/backend/uploads /app/artifacts /app/logs

# PYTHONPATH=/app/backend lets `uvicorn server:app` resolve the module.
# (Earlier iterations used `backend.server:app` which collided with
# /app/backend/backend/server.py — that's why this image was failing.)
ENV PYTHONPATH=/app/backend \
    COGENT_MONGO_URL=mongodb://mongo:27017 \
    COGENT_DB_NAME=cogent \
    ARTIFACTS_DIR=/app/artifacts

EXPOSE 8000

# Healthcheck so docker can probe readiness.
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD curl -fsS http://localhost:8000/api/health/live || exit 1

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
