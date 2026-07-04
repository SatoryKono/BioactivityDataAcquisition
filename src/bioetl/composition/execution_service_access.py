"""Narrow execution-service access seam for first-party interface callers."""

from __future__ import annotations

from bioetl.composition._pipeline_execution import (
    ensure_metrics_server_started as ensure_metrics_server_started,
)
from bioetl.composition._services import (
    get_pipeline_runner_service as get_pipeline_runner_service,
)

__all__ = [
    "ensure_metrics_server_started",
    "get_pipeline_runner_service",
]
