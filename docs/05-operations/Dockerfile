# Multi-stage build for BioETL Python application
FROM python:3.11-slim AS base

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

# Install uv and builder dependencies
RUN pip install uv && \
    uv pip install --system -e .

# ============ Production Stage ============
FROM base AS production

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application source
COPY src/ /app/src/
COPY pyproject.toml /app/

# Install the package in editable mode
RUN pip install --no-deps -e .

# Create non-root user
RUN useradd -m -u 1000 bioetl && \
    chown -R bioetl:bioetl /app

USER bioetl

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD bioetl --version || exit 1

# Default command
CMD ["bioetl", "--help"]

# ============ Development Stage ============
FROM base AS development

# Copy development workspace explicitly to avoid recursive context import.
COPY pyproject.toml uv.lock README.md mkdocs.yml pytest.ini /app/
COPY src/ /app/src/
COPY scripts/ /app/scripts/
COPY docs/ /app/docs/
COPY tests/ /app/tests/
COPY configs/ /app/configs/
COPY grafana/ /app/grafana/
COPY package.json package-lock.json /app/
COPY docker-compose.yml docker-compose.monitoring.yml docker-compose.neo4j.yml /app/

# Install development dependencies
RUN pip install uv && \
    uv pip install --system -e ".[dev,docs]"

# Create non-root user
RUN useradd -m -u 1000 bioetl && \
    chown -R bioetl:bioetl /app

USER bioetl

WORKDIR /app

CMD ["/bin/bash"]
