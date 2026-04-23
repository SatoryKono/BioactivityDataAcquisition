"""Facade for the canonical execution seam."""

from __future__ import annotations

from bioetl.application.services.execution.pipeline_run_execution_service import (
    PipelineExecutionResult,
    PipelineRunExecutionService,
)

__all__ = [
    "PipelineExecutionResult",
    "PipelineRunExecutionService",
]
