"""Facade for the canonical execution seam."""

from __future__ import annotations

from bioetl.application.services.execution.pipeline_run_lifecycle_service import (
    PipelineRunLifecycleService,
)

__all__ = [
    "PipelineRunLifecycleService",
]
