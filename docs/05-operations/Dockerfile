# Multi-stage build for BioETL Python application
FROM python:3.11-slim@sha256:baf89808ec37adeaab83cec287adb4a2afa4a11c1d51e961c7ec737877e61af6 AS base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# ============ Builder Stage ============
FROM base AS builder

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install uv and builder dependencies (binary-only + locked uv version).
RUN pip install --only-binary=:all: --no-cache-dir uv==0.11.26 && \
    uv pip install --system -e .

# ============ Production Stage ============
FROM base AS production

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application source
COPY src/ /app/src/
COPY pyproject.toml /app/

# Install the package in editable mode (no transitive build scripts).
RUN pip install --only-binary=:all: --no-deps --no-cache-dir -e .

# Create non-root user
RUN useradd -m -u 1000 bioetl && \
    chown -R bioetl:bioetl /app

USER bioetl

# Default command
CMD ["bioetl", "--help"]

# ============ Development Stage ============
FROM base AS development

# Copy development workspace explicitly to avoid recursive context import.
COPY pyproject.toml uv.lock README.md mkdocs.yml /app/
COPY src/ /app/src/
COPY scripts/ /app/scripts/
COPY docs/ /app/docs/
COPY tests/ /app/tests/
COPY configs/ /app/configs/
COPY grafana/ /app/grafana/
COPY package.json package-lock.json /app/
COPY docker-compose.yml docker-compose.monitoring.yml docker-compose.neo4j.yml /app/

# Install development dependencies (binary-only + locked uv version).
RUN pip install --only-binary=:all: --no-cache-dir uv==0.11.26 && \
    uv pip install --system -e ".[dev,docs]" && \
    useradd -m -u 1000 bioetl && \
    chown -R bioetl:bioetl /app

USER bioetl

WORKDIR /app

CMD ["/bin/bash"]
