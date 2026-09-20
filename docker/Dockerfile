FROM python:3.12-slim AS base

LABEL maintainer="Retail AI & Merchandising Intelligence Engineering <retail-ai@enterprise.internal>"
LABEL description="Retail Competitor Intelligence — Autonomous Hybrid Agentic Platform"

# Security: run as non-root user
RUN groupadd --gid 1001 retailintel && \
    useradd --uid 1001 --gid retailintel --shell /bin/bash --create-home retailintel

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Layer 1: Install Python dependencies (cached unless pyproject.toml changes)
COPY pyproject.toml ./
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir ".[gcp]" 2>/dev/null || pip install --no-cache-dir . && \
    pip install --no-cache-dir uvicorn[standard]

# Layer 2: Copy application source
COPY src/ ./src/
COPY data/ ./data/

# Layer 3: Copy configs
COPY configs/ ./configs/

# Change ownership
RUN chown -R retailintel:retailintel /app

USER retailintel

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000

ENV PYTHONPATH="/app/src" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

CMD uvicorn retail_intel.api.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1
