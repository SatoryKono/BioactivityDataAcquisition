"""Runtime bootstrap module for pipeline execution.

Contains bootstrap functions for actual pipeline execution scenarios:
- Single pipeline runs (incremental, backfill, rebuild)
- Composite pipeline runs with enrichment coordination
- Full observability stack (logging, tracing, metrics, DQ monitoring)

IMPORTANT: This module MUST NOT import from bootstrap/cli/.
CLI modules may import from runtime for runner access, but not vice versa.

Components:
- assembly: Pure configuration assembly functions (no I/O)
- observability: Full observability stack bootstrap
- pipeline: Main pipeline bootstrap entry point
- composite: Composite pipeline bootstrap
- runner: PipelineRunnerService bootstrap
"""

from __future__ import annotations

from bioetl.composition.bootstrap.runtime.assembly import (
    assemble_filter_config,
    assemble_runtime_config,
    assemble_vacuum_settings,
)
from bioetl.composition.bootstrap.runtime.composite import (
    bootstrap_composite_runner,
    load_composite_config,
)
from bioetl.composition.bootstrap.runtime.observability import (
    MetricsServerError,
    bootstrap_dq_monitor_port,
    bootstrap_logger_port,
    bootstrap_metrics_port,
    bootstrap_observability_bundle,
    bootstrap_tracer_port,
    maybe_start_metrics_server,
    start_metrics_server,
    validate_observability_preflight,
)
from bioetl.composition.bootstrap.runtime.pipeline import (
    bootstrap_pipeline_runner,
)
from bioetl.composition.bootstrap.runtime.pipeline_runner_service_bootstrap import (
    bootstrap_pipeline_runner_service,
)

__all__ = [
    "MetricsServerError",
    "assemble_filter_config",
    "assemble_runtime_config",
    "assemble_vacuum_settings",
    "bootstrap_composite_runner",
    "bootstrap_dq_monitor_port",
    "bootstrap_logger_port",
    "bootstrap_metrics_port",
    "bootstrap_observability_bundle",
    "bootstrap_pipeline_runner",
    "bootstrap_pipeline_runner_service",
    "bootstrap_tracer_port",
    "load_composite_config",
    "maybe_start_metrics_server",
    "start_metrics_server",
    "validate_observability_preflight",
]
