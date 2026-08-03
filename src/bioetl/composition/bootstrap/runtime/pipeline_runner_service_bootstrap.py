"""Canonical bootstrap entrypoint for PipelineRunnerService."""

from __future__ import annotations

from bioetl.composition.bootstrap.runtime.runner import (
    bootstrap_pipeline_runner_service,
)

__all__ = ["bootstrap_pipeline_runner_service"]
