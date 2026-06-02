"""Public composition entrypoint focused on execution-oriented APIs.

`bioetl.composition.entrypoints` remains a stable import seam with an explicit
execution-focused public surface.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.composition._lazy_exports import install_lazy_exports

if TYPE_CHECKING:
    from bioetl.composition.composite_api import (
        bootstrap_composite_runner,
        load_composite_config,
        load_pipeline_config,
    )
    from bioetl.composition.execution_api import (
        ArchiveOptions,
        PipelineRunResult,
        RunOptions,
        RunResult,
        VacuumOptions,
        build_pipeline_context,
        create_pipeline_runner,
        ensure_metrics_server_started,
        maybe_start_metrics_server,
        push_metrics_to_gateway,
        run_pipeline,
    )
    from bioetl.composition.observability_api import start_metrics_server

_COMPOSITION_EXECUTION_API_MODULE = "bioetl.composition.execution_api"
_COMPOSITION_COMPOSITE_API_MODULE = "bioetl.composition.composite_api"
__all__ = [
    "ArchiveOptions",
    "PipelineRunResult",
    "RunOptions",
    "RunResult",
    "VacuumOptions",
    "bootstrap_composite_runner",
    "build_pipeline_context",
    "create_pipeline_runner",
    "ensure_metrics_server_started",
    "load_composite_config",
    "load_pipeline_config",
    "maybe_start_metrics_server",
    "push_metrics_to_gateway",
    "run_pipeline",
    "start_metrics_server",
]

_PUBLIC_SYMBOL_TARGETS: dict[str, str] = {
    "ArchiveOptions": _COMPOSITION_EXECUTION_API_MODULE,
    "PipelineRunResult": _COMPOSITION_EXECUTION_API_MODULE,
    "RunOptions": _COMPOSITION_EXECUTION_API_MODULE,
    "RunResult": _COMPOSITION_EXECUTION_API_MODULE,
    "VacuumOptions": _COMPOSITION_EXECUTION_API_MODULE,
    "bootstrap_composite_runner": _COMPOSITION_COMPOSITE_API_MODULE,
    "build_pipeline_context": _COMPOSITION_EXECUTION_API_MODULE,
    "create_pipeline_runner": _COMPOSITION_EXECUTION_API_MODULE,
    "ensure_metrics_server_started": _COMPOSITION_EXECUTION_API_MODULE,
    "load_composite_config": _COMPOSITION_COMPOSITE_API_MODULE,
    "load_pipeline_config": _COMPOSITION_COMPOSITE_API_MODULE,
    "maybe_start_metrics_server": _COMPOSITION_EXECUTION_API_MODULE,
    "push_metrics_to_gateway": _COMPOSITION_EXECUTION_API_MODULE,
    "run_pipeline": _COMPOSITION_EXECUTION_API_MODULE,
    "start_metrics_server": "bioetl.composition.observability_api",
}
install_lazy_exports(
    module_globals=globals(),
    public_exports=_PUBLIC_SYMBOL_TARGETS,
    module_name=__name__,
)
