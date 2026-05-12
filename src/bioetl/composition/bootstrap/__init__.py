"""Compatibility package-root lazy proxies for composition bootstrap surfaces."""

from __future__ import annotations

from importlib import import_module
from typing import Any

_RUNTIME_OBSERVABILITY_MODULE = "bioetl.composition.bootstrap.runtime.observability"
_RUNTIME_COMPOSITE_MODULE = "bioetl.composition.bootstrap.runtime.composite"
_RUNTIME_PIPELINE_MODULE = "bioetl.composition.bootstrap.runtime.pipeline"
_PIPELINE_CONFIG_API_MODULE = "bioetl.infrastructure.config.pipeline_config_api"

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
    "bootstrap_composite_runner": _RUNTIME_COMPOSITE_MODULE,
    "bootstrap_dq_monitor": _RUNTIME_OBSERVABILITY_MODULE,
    "bootstrap_logger": _RUNTIME_OBSERVABILITY_MODULE,
    "bootstrap_metrics": _RUNTIME_OBSERVABILITY_MODULE,
    "bootstrap_observability_bundle": _RUNTIME_OBSERVABILITY_MODULE,
    "bootstrap_pipeline_runner": _RUNTIME_PIPELINE_MODULE,
    "bootstrap_tracer": _RUNTIME_OBSERVABILITY_MODULE,
    "load_composite_config": _RUNTIME_COMPOSITE_MODULE,
    "load_pipeline_config": _PIPELINE_CONFIG_API_MODULE,
    "maybe_start_metrics_server": _RUNTIME_OBSERVABILITY_MODULE,
}


def __getattr__(
    name: str,
) -> (
    Any  # Any: lazy package-root re-export preserves owner symbol type at lookup time.
):  # Any: lazy package-root re-export preserves owner symbol type at lookup time.
    """Resolve sanctioned bootstrap compatibility exports lazily."""
    module_name = _PUBLIC_EXPORTS.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    value = getattr(import_module(module_name), name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    """Expose lazy package-root compatibility exports to introspection."""
    return sorted(set(globals()) | set(__all__))
