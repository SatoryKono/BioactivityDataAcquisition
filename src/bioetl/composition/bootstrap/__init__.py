"""Curated package-root re-exports for approved bootstrap entrypoints.

Import concrete helpers from ``bioetl.composition.bootstrap.runtime`` or
``bioetl.composition.bootstrap.cli`` modules when you need the owner module.
The package root preserves only the curated public bootstrap surface without
forcing eager runtime bootstrap imports during package initialization.
"""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING

from bioetl.composition.lazy_exports import build_lazy_export_hooks

if TYPE_CHECKING:
    from bioetl.domain.ports import AdrServicePort
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
    from bioetl.infrastructure.control_plane import FileControlPlaneArtifactLifecycleStore
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

__all__: list[str] = [
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


def __getattr__(name: str) -> object:
    if name == "runtime":
        module = import_module("bioetl.composition.bootstrap.runtime")
        globals()[name] = module
        return module
    return _BOOTSTRAP_EXPORT_GETATTR(name)


def __dir__() -> list[str]:
    return _BOOTSTRAP_EXPORT_DIR()


_BOOTSTRAP_EXPORT_GETATTR, _BOOTSTRAP_EXPORT_DIR = build_lazy_export_hooks(
    module_globals=globals(),
    public_exports=_PUBLIC_EXPORTS,
    module_name=__name__,
    explicit_exports=__all__,
    cache=True,
)
