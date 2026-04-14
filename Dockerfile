# Multi-stage build for BioETL
# Stage 1: Builder
FROM python:3.11-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files only (layer caching optimization)
COPY pyproject.toml uv.lock requirements.txt ./

# Install dependencies with pip cache disabled
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade pip setuptools && \
    pip install -e .[tracing] && \
    pip install -r requirements.txt

# Copy application code
COPY src ./src

# Stage 2: Runtime
FROM python:3.11-slim

# Set environment variables for production
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install runtime dependencies and ca-certificates for HTTPS
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Copy installed packages and app from builder in single operation
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY --from=builder /app/src ./src

# Create non-root user with no shell access
RUN useradd -m -u 1000 -s /sbin/nologin bioetl && \
    chown -R bioetl:bioetl /app
USER bioetl

ENTRYPOINT ["bioetl"]
CMD ["--help"]
