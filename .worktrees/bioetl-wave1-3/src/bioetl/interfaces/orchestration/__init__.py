"""Orchestration utilities for pipeline execution.

This module is the designated location for orchestration utilities that
coordinate pipeline execution from interfaces layer (CLI, REST API, etc.).

REQ-ARCH-APP-001 states that external orchestration frameworks (Celery, Airflow)
must NOT be imported in application layer. This module serves as the integration
point for any such frameworks when needed.

Current status:
- Signal handlers were removed in 2025-12-31 (CLI handles KeyboardInterrupt directly)
- The module is reserved for future orchestration needs

For pipeline execution, use the entrypoints module:
    from bioetl.composition.entrypoints import run_pipeline, get_pipeline_runner_service
"""

from __future__ import annotations

__all__: list[str] = []
