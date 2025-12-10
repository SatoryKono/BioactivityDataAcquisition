# Use official Python runtime as a parent image
FROM python:3.11-slim-bookworm

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/app/src

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy only requirements to cache them in docker layer
COPY pyproject.toml .
COPY requirements.txt .

# Install dependencies
# We use pip to install from pyproject.toml in editable mode or just dependencies
RUN pip install --upgrade pip && \
    pip install -e .

# Copy project
COPY . .

# Create non-root user for security
RUN useradd -m bioetl && \
    chown -R bioetl:bioetl /app

USER bioetl

# Entrypoint for the application
ENTRYPOINT ["bioetl"]
CMD ["--help"]
