# Multi-stage build for BioETL Python application
# docker:S8431 — pin by digest only (no tag+digest).
FROM python@sha256:baf89808ec37adeaab83cec287adb4a2afa4a11c1d51e961c7ec737877e61af6 AS base

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

# Copy dependency files + source required by lockfile-backed project install.
COPY pyproject.toml uv.lock README.md ./
COPY src/ ./src/

# Binary-only uv bootstrap + frozen lockfile sync (Sonar docker:S8541/S8544).
# Third-party deps: --no-build. Local project: wheel build + pinned binary install.
RUN pip install --only-binary=:all: --no-cache-dir uv==0.11.26 && \
    UV_NO_BUILD=1 uv sync --frozen --no-build --no-dev --no-install-project \
        --directory /app && \
    uv build --wheel --out-dir /tmp/bioetl-wheels --directory /app && \
    BIOETL_VERSION="$(python -c "import tomllib; \
print(tomllib.load(open('pyproject.toml','rb'))['project']['version'])")" && \
    uv pip install --python /app/.venv/bin/python --no-deps \
        --only-binary :all: --no-index \
        --find-links=/tmp/bioetl-wheels "bioetl==${BIOETL_VERSION}" && \
    rm -rf /tmp/bioetl-wheels

# ============ Production Stage ============
FROM base AS production

# Copy virtual environment from lockfile-backed builder (no unpinned reinstall).
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/src /app/src
COPY --from=builder /app/pyproject.toml /app/pyproject.toml

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH="/app/src"

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

# Binary-only uv bootstrap + frozen lockfile sync for dev extras (S8541/S8544).
RUN pip install --only-binary=:all: --no-cache-dir uv==0.11.26 && \
    UV_NO_BUILD=1 uv sync --frozen --no-build --no-install-project \
        --extra dev --extra docs --directory /app && \
    uv build --wheel --out-dir /tmp/bioetl-wheels --directory /app && \
    BIOETL_VERSION="$(python -c "import tomllib; \
print(tomllib.load(open('pyproject.toml','rb'))['project']['version'])")" && \
    uv pip install --python /app/.venv/bin/python --no-deps \
        --only-binary :all: --no-index \
        --find-links=/tmp/bioetl-wheels "bioetl[dev,docs]==${BIOETL_VERSION}" && \
    rm -rf /tmp/bioetl-wheels && \
    useradd -m -u 1000 bioetl && \
    chown -R bioetl:bioetl /app

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH="/app/src"

USER bioetl

WORKDIR /app

CMD ["/bin/bash"]
