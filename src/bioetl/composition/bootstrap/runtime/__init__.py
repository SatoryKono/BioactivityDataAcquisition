"""Runtime bootstrap module for pipeline execution.

Contains bootstrap functions for actual pipeline execution scenarios:
- Single pipeline runs (incremental, backfill, rebuild)
- Composite pipeline runs with enrichment coordination
- Full observability stack (logging, tracing, metrics, DQ monitoring)

IMPORTANT: This module MUST NOT import from bootstrap/cli/.
CLI modules may import from runtime for runner access, but not vice versa.

Components:
- observability: Full observability stack bootstrap
- pipeline: Main pipeline bootstrap entry point
- composite: Composite pipeline bootstrap
- runner: PipelineRunnerService bootstrap
"""

from __future__ import annotations

from bioetl.composition.bootstrap.runtime.composite import (
    bootstrap_composite_pipeline,
    load_composite_config,
)
from bioetl.composition.bootstrap.runtime.observability import (
    MetricsServerError,
    bootstrap_dq_monitor,
    bootstrap_logger,
    bootstrap_metrics,
    bootstrap_observability,
    bootstrap_tracer,
    maybe_start_metrics_server,
    start_metrics_server,
    validate_observability_preflight,
)
from bioetl.composition.bootstrap.runtime.pipeline import bootstrap_pipeline
from bioetl.composition.bootstrap.runtime.runner import (
    bootstrap_pipeline_runner_service,
)

__all__ = [
    # Observability
    "MetricsServerError",
    # Composite
    "bootstrap_composite_pipeline",
    "bootstrap_dq_monitor",
    "bootstrap_logger",
    "bootstrap_metrics",
    "bootstrap_observability",
    # Pipeline
    "bootstrap_pipeline",
    # Runner service
    "bootstrap_pipeline_runner_service",
    "bootstrap_tracer",
    "load_composite_config",
    "maybe_start_metrics_server",
    "start_metrics_server",
    "validate_observability_preflight",
]
