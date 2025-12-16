"""Orchestration layer - Prefect integration.

This module contains Prefect-specific wrappers around the clean application layer.
It acts as an adapter between the orchestration framework and the application.

The application layer (executor, orchestrator) remains framework-agnostic,
while this layer provides the Prefect decorators and integration.
"""

from bioetl.orchestration.tasks import execute_pipeline_task, run_pipeline_flow

__all__ = [
    "execute_pipeline_task",
    "run_pipeline_flow",
]
