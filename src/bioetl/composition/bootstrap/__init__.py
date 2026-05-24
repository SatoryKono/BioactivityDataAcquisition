"""Curated package-root re-exports for approved bootstrap entrypoints.

Import concrete helpers from ``bioetl.composition.bootstrap.runtime`` or
``bioetl.composition.bootstrap.cli`` modules when you need the owner module.
The package root preserves only the curated public bootstrap surface without
forcing eager runtime bootstrap imports during package initialization.
"""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING

if TYPE_CHECKING:
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
    "bootstrap_composite_runner": (
        "bioetl.composition.bootstrap.runtime.composite",
        "bootstrap_composite_runner",
    ),
    "bootstrap_dq_monitor": (
        "bioetl.composition.bootstrap.runtime.observability",
        "bootstrap_dq_monitor",
    ),
    "bootstrap_logger": (
        "bioetl.composition.bootstrap.runtime.observability",
        "bootstrap_logger",
    ),
    "bootstrap_metrics": (
        "bioetl.composition.bootstrap.runtime.observability",
        "bootstrap_metrics",
    ),
    "bootstrap_observability_bundle": (
        "bioetl.composition.bootstrap.runtime.observability",
        "bootstrap_observability_bundle",
    ),
    "bootstrap_pipeline_runner": (
        "bioetl.composition.bootstrap.runtime.pipeline",
        "bootstrap_pipeline_runner",
    ),
    "bootstrap_tracer": (
        "bioetl.composition.bootstrap.runtime.observability",
        "bootstrap_tracer",
    ),
    "load_composite_config": (
        "bioetl.composition.bootstrap.runtime.composite",
        "load_composite_config",
    ),
    "load_pipeline_config": (
        "bioetl.infrastructure.config.pipeline_config_api",
        "load_pipeline_config",
    ),
    "maybe_start_metrics_server": (
        "bioetl.composition.bootstrap.runtime.observability",
        "maybe_start_metrics_server",
    ),
}

__all__ = list(_PUBLIC_EXPORTS)


def __getattr__(name: str) -> object:
    export = _PUBLIC_EXPORTS.get(name)
    if export is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_name, attr_name = export
    value = getattr(import_module(module_name), attr_name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(__all__))
