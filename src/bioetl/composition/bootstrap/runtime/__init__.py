"""Runtime bootstrap module for pipeline execution.

Contains bootstrap functions for actual pipeline execution scenarios:
- Single pipeline runs (incremental, backfill, rebuild)
- Composite pipeline runs with enrichment coordination
- Full observability stack (logging, tracing, metrics, DQ monitoring)

IMPORTANT: This module MUST NOT import from bootstrap/cli/.
CLI modules may import from runtime for runner access, but not vice versa.

Public runtime helpers are re-exported lazily so importing one light-weight
submodule does not eagerly initialize the full runtime bootstrap graph.
"""

from __future__ import annotations

from importlib import import_module
from typing import Any

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
    "validate_observability_preflight",
]

_PUBLIC_EXPORTS: dict[str, str] = {
    "MetricsServerError": "bioetl.composition.bootstrap.runtime.observability",
    "assemble_filter_config": "bioetl.composition.bootstrap.runtime.assembly",
    "assemble_runtime_config": "bioetl.composition.bootstrap.runtime.assembly",
    "assemble_vacuum_settings": "bioetl.composition.bootstrap.runtime.assembly",
    "bootstrap_composite_runner": "bioetl.composition.bootstrap.runtime.composite",
    "bootstrap_dq_monitor_port": "bioetl.composition.bootstrap.runtime.observability",
    "bootstrap_logger_port": "bioetl.composition.bootstrap.runtime.observability",
    "bootstrap_metrics_port": "bioetl.composition.bootstrap.runtime.observability",
    "bootstrap_observability_bundle": (
        "bioetl.composition.bootstrap.runtime.observability"
    ),
    "bootstrap_pipeline_runner": "bioetl.composition.bootstrap.runtime.pipeline",
    "bootstrap_pipeline_runner_service": (
        "bioetl.composition.bootstrap.runtime.pipeline_runner_service_bootstrap"
    ),
    "bootstrap_tracer_port": "bioetl.composition.bootstrap.runtime.observability",
    "load_composite_config": "bioetl.composition.bootstrap.runtime.composite",
    "maybe_start_metrics_server": "bioetl.composition.bootstrap.runtime.observability",
    "validate_observability_preflight": (
        "bioetl.composition.bootstrap.runtime.observability"
    ),
}


def __getattr__(
    name: str,
) -> (
    Any
):  # Any: lazy runtime re-export preserves the original symbol type at lookup time.
    """Resolve runtime re-exports lazily to keep package import light-weight."""
    module_name = _PUBLIC_EXPORTS.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    value = getattr(import_module(module_name), name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    """Expose lazy re-exports to introspection and wildcard imports."""
    return sorted(set(globals()) | set(__all__))
