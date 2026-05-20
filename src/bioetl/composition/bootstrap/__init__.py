"""Curated package-root re-exports for approved bootstrap entrypoints.

Import concrete helpers from ``bioetl.composition.bootstrap.runtime`` or
``bioetl.composition.bootstrap.cli`` modules when you need the owner module.
The package root preserves only the curated public bootstrap surface.
"""

from __future__ import annotations

from bioetl.composition.bootstrap.runtime.composite import (
    bootstrap_composite_runner,
    load_composite_config,
)
from bioetl.composition.bootstrap.runtime.observability import (
    bootstrap_dq_monitor,
    bootstrap_logger,
    bootstrap_metrics,
    bootstrap_observability_bundle,
    bootstrap_tracer,
    maybe_start_metrics_server,
)
from bioetl.composition.bootstrap.runtime.pipeline import bootstrap_pipeline_runner
from bioetl.infrastructure.config.pipeline_config_api import load_pipeline_config

_PUBLIC_EXPORTS = {
    "bootstrap_composite_runner",
    "bootstrap_dq_monitor",
    "bootstrap_logger",
    "bootstrap_metrics",
    "bootstrap_observability_bundle",
    "bootstrap_pipeline_runner",
    "bootstrap_tracer",
    "load_composite_config",
    "load_pipeline_config",
    "maybe_start_metrics_server",
}

__all__ = [
    "bootstrap_composite_runner",
    "bootstrap_dq_monitor",
    "bootstrap_logger",
    "bootstrap_metrics",
    "bootstrap_observability_bundle",
    "bootstrap_pipeline_runner",
    "bootstrap_tracer",
    "load_composite_config",
    "load_pipeline_config",
    "maybe_start_metrics_server",
]
