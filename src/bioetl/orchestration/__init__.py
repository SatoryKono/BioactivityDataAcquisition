"""Orchestration layer - Prefect integration.

This module contains Prefect-specific wrappers around the clean application layer.
It acts as an adapter between the orchestration framework and the application.

The application layer (executor, orchestrator, checkpoint_manager) remains
framework-agnostic, while this layer provides the Prefect decorators and integration.
"""

from bioetl.orchestration.tasks import (
    delete_checkpoint_task,
    execute_pipeline_task,
    load_checkpoint_task,
    run_pipeline_flow,
)

__all__ = [
    "delete_checkpoint_task",
    "execute_pipeline_task",
    "load_checkpoint_task",
    "run_pipeline_flow",
]
