"""Public execution-oriented composition API."""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bioetl.application.services import PipelineRunResult, RunOptions, RunResult
    from bioetl.composition._pipeline_execution import (
        ArchiveOptions,
        VacuumOptions,
        build_pipeline_context,
        create_pipeline_runner,
        ensure_metrics_server_started,
        run_pipeline,
    )
    from bioetl.composition._services import get_pipeline_runner_service
    from bioetl.composition.bootstrap import maybe_start_metrics_server

_PIPELINE_EXECUTION_MODULE = "bioetl.composition._pipeline_execution"
_APPLICATION_SERVICES_MODULE = "bioetl.application.services"

__all__ = [
    "ArchiveOptions",
    "PipelineRunResult",
    "RunOptions",
    "RunResult",
    "VacuumOptions",
    "build_pipeline_context",
    "create_pipeline_runner",
    "ensure_metrics_server_started",
    "get_pipeline_runner_service",
    "maybe_start_metrics_server",
    "push_metrics_to_gateway",
    "run_pipeline",
]

_PUBLIC_EXPORTS: dict[str, str] = {
    "ArchiveOptions": _PIPELINE_EXECUTION_MODULE,
    "PipelineRunResult": _APPLICATION_SERVICES_MODULE,
    "RunOptions": _APPLICATION_SERVICES_MODULE,
    "RunResult": _APPLICATION_SERVICES_MODULE,
    "VacuumOptions": _PIPELINE_EXECUTION_MODULE,
    "build_pipeline_context": _PIPELINE_EXECUTION_MODULE,
    "create_pipeline_runner": _PIPELINE_EXECUTION_MODULE,
    "ensure_metrics_server_started": _PIPELINE_EXECUTION_MODULE,
    "get_pipeline_runner_service": "bioetl.composition._services",
    "maybe_start_metrics_server": "bioetl.composition.bootstrap",
    "run_pipeline": _PIPELINE_EXECUTION_MODULE,
}


def push_metrics_to_gateway(
    run_label: str = "bioetl",
    *,
    pipeline_name: str | None = None,
    run_type: str | None = None,
) -> bool:
    """Push metrics through the composition-owned observability seam."""
    from bioetl.composition.observability_api import (
        push_metrics_to_gateway as _impl,
    )

    return _impl(
        run_label=run_label,
        pipeline_name=pipeline_name,
        run_type=run_type,
    )


def __getattr__(
    name: str,
) -> Any:  # Any: lazy export returns either classes or callables from multiple modules.
    """Resolve execution-oriented public exports lazily."""
    module_name = _PUBLIC_EXPORTS.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    value = getattr(import_module(module_name), name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    """Expose lazy re-exports to introspection and wildcard imports."""
    return sorted(set(globals()) | set(__all__))
