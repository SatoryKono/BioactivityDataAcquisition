"""End-to-end tests for BioETL pipelines.

These tests use real Docker infrastructure (MinIO, Redis) to verify
complete pipeline flows from Extract to Bronze/Silver/Gold.

Requirements:
- Docker and docker-compose installed
- Services started via `docker compose -f docker-compose.test.yml up -d`
- Run with: `pytest tests/e2e/ -v -m e2e`
"""
