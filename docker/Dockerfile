FROM python:3.12-slim AS base

LABEL description="AURORA - Retail Competitor Intelligence (synthetic-data demo profile)"

# Run as a non-root user
RUN groupadd --gid 1001 retailintel && \
    useradd --uid 1001 --gid retailintel --shell /bin/bash --create-home retailintel

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Layer 1: runtime dependencies only (cached until requirements.txt changes)
COPY requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Layer 2: application source, seed fixtures and config
COPY src/ ./src/
COPY data/ ./data/
COPY configs/ ./configs/

# Writable runtime directories (SQLite store, evidence payloads)
RUN mkdir -p /app/runtime && chown -R retailintel:retailintel /app

USER retailintel

ENV PYTHONPATH="/app/src" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    RETAIL_INTEL_BASE_DIR="/app" \
    LOCAL_STORAGE_DIR="/app/runtime/payload_store" \
    OBSERVATION_DB_PATH="/app/runtime/observations.sqlite3"

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000

CMD ["sh", "-c", "uvicorn retail_intel.api.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1"]
