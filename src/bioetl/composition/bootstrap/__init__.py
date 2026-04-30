"""Bootstrap package for BioETL Composition Root.

Provides modular bootstrap functions organized by context:

- **assembly**: Shared infrastructure components (ports, storage adapters)
  without side-effects. Used by both CLI and runtime.
- **cli**: Bootstrap functions for CLI-only commands (inspect, list, maintenance,
  admin operations). These use NoOp observability implementations.
- **runtime**: Bootstrap functions for actual pipeline execution (pipeline run,
  composite pipelines). These use full observability stack.

Import Rules:
- runtime MUST NOT import from cli
- cli MAY import from runtime (for runner access)
- Both MUST import shared code from assembly

Public names are resolved lazily so light-weight imports, such as test fixtures
that only need a helper submodule, do not pay the cost of importing the entire
runtime bootstrap tree.
"""

from __future__ import annotations

from importlib import import_module
from typing import Any

_BOOTSTRAP_RUNTIME_MODULE = "bioetl.composition.bootstrap.runtime"
_BOOTSTRAP_OBSERVABILITY_MODULE = "bioetl.composition.bootstrap.runtime.observability"

__all__ = [
    "bootstrap_composite_runner",
    "bootstrap_dq_monitor_port",
    "bootstrap_logger_port",
    "bootstrap_metrics_port",
    "bootstrap_observability_bundle",
    "bootstrap_pipeline_runner",
    "bootstrap_tracer_port",
    "load_composite_config",
    "load_pipeline_config",
    "maybe_start_metrics_server",
]

_PUBLIC_EXPORTS: dict[str, str] = {
    "bootstrap_composite_runner": _BOOTSTRAP_RUNTIME_MODULE,
    "bootstrap_dq_monitor_port": _BOOTSTRAP_OBSERVABILITY_MODULE,
    "bootstrap_logger_port": _BOOTSTRAP_OBSERVABILITY_MODULE,
    "bootstrap_metrics_port": _BOOTSTRAP_OBSERVABILITY_MODULE,
    "bootstrap_observability_bundle": _BOOTSTRAP_OBSERVABILITY_MODULE,
    "bootstrap_pipeline_runner": _BOOTSTRAP_RUNTIME_MODULE,
    "bootstrap_tracer_port": _BOOTSTRAP_OBSERVABILITY_MODULE,
    "load_composite_config": _BOOTSTRAP_RUNTIME_MODULE,
    "load_pipeline_config": "bioetl.infrastructure.config.pipeline_config_api",
    "maybe_start_metrics_server": _BOOTSTRAP_OBSERVABILITY_MODULE,
}

# ``importlib.reload`` preserves the existing module dict. Clear any cached lazy
# exports so post-reload attribute access still flows through ``__getattr__``.
for _cached_export_name in tuple(_PUBLIC_EXPORTS):
    globals().pop(_cached_export_name, None)


def __getattr__(
    name: str,
) -> Any:  # Any: lazy re-export preserves the original symbol type at lookup time.
    """Resolve bootstrap re-exports lazily to avoid eager runtime imports."""
    module_name = _PUBLIC_EXPORTS.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    compat_module = import_module("bioetl.infrastructure.compat.pandera_compat")
    compat_module.apply_pandera_typing_compat_if_needed()
    value = getattr(import_module(module_name), name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    """Expose lazy re-exports to introspection and wildcard imports."""
    return sorted(set(globals()) | set(__all__))
