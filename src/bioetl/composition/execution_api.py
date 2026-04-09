"""Public execution-oriented composition API."""

from __future__ import annotations

from bioetl.application.services import PipelineRunResult, RunOptions, RunResult
from bioetl.composition._pipeline_execution import (
    ArchiveOptions,
    VacuumOptions,
    build_pipeline_context,
    create_pipeline_runner,
    ensure_metrics_server_started,
    push_metrics_to_gateway,
    run_pipeline,
)
from bioetl.composition._services import get_pipeline_runner_service
from bioetl.composition.bootstrap import maybe_start_metrics_server

__all__ = [
    "ArchiveOptions",
    "PipelineRunResult",
    "RunOptions",
    "RunResult",
    "VacuumOptions",
    "build_pipeline_context",
    "create_pipeline_runner",
    "ensure_metrics_server_started",
    "get_pipeline_runner_service",
    "maybe_start_metrics_server",
    "push_metrics_to_gateway",
    "run_pipeline",
]
