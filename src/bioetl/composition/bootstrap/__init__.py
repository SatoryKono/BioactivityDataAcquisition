"""Lazy package-root proxies for approved bootstrap entrypoints.

Import concrete helpers from ``bioetl.composition.bootstrap.runtime`` or
``bioetl.composition.bootstrap.cli`` modules when you need the owner module.
The package root preserves only the curated public bootstrap surface.
"""

from __future__ import annotations

from importlib import import_module
from typing import Any

_RUNTIME_OBSERVABILITY_MODULE = "bioetl.composition.bootstrap.runtime.observability"

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

_PUBLIC_EXPORTS: dict[str, str] = {
    "bootstrap_composite_runner": "bioetl.composition.bootstrap.runtime.composite",
    "bootstrap_dq_monitor": _RUNTIME_OBSERVABILITY_MODULE,
    "bootstrap_logger": _RUNTIME_OBSERVABILITY_MODULE,
    "bootstrap_metrics": _RUNTIME_OBSERVABILITY_MODULE,
    "bootstrap_observability_bundle": _RUNTIME_OBSERVABILITY_MODULE,
    "bootstrap_pipeline_runner": "bioetl.composition.bootstrap.runtime.pipeline",
    "bootstrap_tracer": _RUNTIME_OBSERVABILITY_MODULE,
    "load_composite_config": "bioetl.composition.bootstrap.runtime.composite",
    "load_pipeline_config": "bioetl.infrastructure.config.pipeline_config_api",
    "maybe_start_metrics_server": _RUNTIME_OBSERVABILITY_MODULE,
}


def __getattr__(
    name: str,
) -> Any:  # Any: Dynamic attribute resolution returns various types
    """Resolve one approved bootstrap entrypoint lazily."""
    module_name = _PUBLIC_EXPORTS.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    value = getattr(import_module(module_name), name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    """Expose lazy package-root proxies to introspection and patching."""
    return sorted(set(globals()) | set(__all__))
