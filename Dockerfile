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

# Install uv for fast dependency management
RUN pip install uv

# Install dependencies using uv
RUN uv pip install --system -e .

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

# Install development dependencies
COPY pyproject.toml uv.lock ./

RUN pip install uv && \
    uv pip install --system -e ".[dev,docs]"

# Copy application source
COPY . /app/

# Create non-root user
RUN useradd -m -u 1000 bioetl && \
    chown -R bioetl:bioetl /app

USER bioetl

WORKDIR /app

CMD ["/bin/bash"]
