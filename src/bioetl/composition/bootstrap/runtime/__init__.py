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

_RUNTIME_OBSERVABILITY_MODULE = "bioetl.composition.bootstrap.runtime.observability"
_RUNTIME_ASSEMBLY_MODULE = "bioetl.composition.bootstrap.runtime.assembly"

__all__ = [
    "MetricsServerError",
    "apply_runtime_compatibility_patches",
    "assemble_filter_config",
    "assemble_runtime_config",
    "assemble_vacuum_settings",
    "bootstrap_composite_runner",
    "bootstrap_dq_monitor",
    "bootstrap_logger",
    "bootstrap_metrics",
    "bootstrap_observability_bundle",
    "bootstrap_pipeline_runner",
    "bootstrap_pipeline_runner_service",
    "bootstrap_tracer",
    "load_composite_config",
    "maybe_start_metrics_server",
    "validate_observability_preflight",
]

_PUBLIC_EXPORTS: dict[str, str] = {
    "MetricsServerError": _RUNTIME_OBSERVABILITY_MODULE,
    "assemble_filter_config": _RUNTIME_ASSEMBLY_MODULE,
    "assemble_runtime_config": _RUNTIME_ASSEMBLY_MODULE,
    "apply_runtime_compatibility_patches": "bioetl.composition.bootstrap.runtime.compatibility",
    "assemble_vacuum_settings": _RUNTIME_ASSEMBLY_MODULE,
    "bootstrap_composite_runner": "bioetl.composition.bootstrap.runtime.composite",
    "bootstrap_dq_monitor": _RUNTIME_OBSERVABILITY_MODULE,
    "bootstrap_logger": _RUNTIME_OBSERVABILITY_MODULE,
    "bootstrap_metrics": _RUNTIME_OBSERVABILITY_MODULE,
    "bootstrap_observability_bundle": _RUNTIME_OBSERVABILITY_MODULE,
    "bootstrap_pipeline_runner": "bioetl.composition.bootstrap.runtime.pipeline",
    "bootstrap_pipeline_runner_service": (
        "bioetl.composition.bootstrap.runtime.pipeline_runner_service_bootstrap"
    ),
    "bootstrap_tracer": _RUNTIME_OBSERVABILITY_MODULE,
    "load_composite_config": "bioetl.composition.bootstrap.runtime.composite",
    "maybe_start_metrics_server": _RUNTIME_OBSERVABILITY_MODULE,
    "validate_observability_preflight": _RUNTIME_OBSERVABILITY_MODULE,
}


def __getattr__(
    name: str,
) -> (
    Any  # Any: lazy runtime re-export preserves the original symbol type at lookup time.
):  # Any: lazy runtime re-export preserves the original symbol type at lookup time.
    """Resolve runtime re-exports lazily to keep package import light-weight."""
    if name == "compatibility":
        module = import_module("bioetl.composition.bootstrap.runtime.compatibility")
        globals()[name] = module
        return module
    module_name = _PUBLIC_EXPORTS.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    value = getattr(import_module(module_name), name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    """Expose lazy re-exports to introspection and wildcard imports."""
    return sorted(set(globals()) | set(__all__))
