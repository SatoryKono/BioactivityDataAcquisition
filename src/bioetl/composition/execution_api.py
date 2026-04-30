"""Public execution-oriented composition API."""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bioetl.application.services.execution.pipeline_runner_models import (
        PipelineRunResult as PipelineRunResult,
    )
    from bioetl.application.services.execution.pipeline_runner_models import (
        RunOptions as RunOptions,
    )
    from bioetl.application.services.execution.pipeline_runner_models import (
        RunResult as RunResult,
    )
    from bioetl.application.services.execution.pipeline_runner_service import (
        PipelineRunnerService as PipelineRunnerService,
    )
    from bioetl.composition._pipeline_execution import ArchiveOptions as ArchiveOptions
    from bioetl.composition._pipeline_execution import VacuumOptions as VacuumOptions
    from bioetl.composition.bootstrap.runtime.observability import (
        maybe_start_metrics_server as maybe_start_metrics_server,
    )
    from bioetl.composition.registry_api import PipelineRegistry
    from bioetl.domain.context import PipelineRunContext
    from bioetl.domain.ports import ExecutionMetricsRunnerPort

_PIPELINE_EXECUTION_MODULE = "bioetl.composition._pipeline_execution"
_PIPELINE_RUNNER_MODELS_MODULE = (
    "bioetl.application.services.execution.pipeline_runner_models"
)

_PUBLIC_EXPORTS: dict[str, str] = {
    "ArchiveOptions": _PIPELINE_EXECUTION_MODULE,
    "PipelineRunResult": _PIPELINE_RUNNER_MODELS_MODULE,
    "RunOptions": _PIPELINE_RUNNER_MODELS_MODULE,
    "RunResult": _PIPELINE_RUNNER_MODELS_MODULE,
    "VacuumOptions": _PIPELINE_EXECUTION_MODULE,
    "build_pipeline_context": _PIPELINE_EXECUTION_MODULE,
    "create_pipeline_runner": _PIPELINE_EXECUTION_MODULE,
    "ensure_metrics_server_started": _PIPELINE_EXECUTION_MODULE,
    "get_pipeline_runner_service": "bioetl.composition._services",
    "maybe_start_metrics_server": "bioetl.composition.bootstrap.runtime.observability",
    "run_pipeline": _PIPELINE_EXECUTION_MODULE,
}

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

if TYPE_CHECKING:

    def build_pipeline_context(
        name: str, options: RunOptions
    ) -> PipelineRunContext: ...

    def create_pipeline_runner(
        name: str,
        options: RunOptions,
    ) -> ExecutionMetricsRunnerPort: ...

    def ensure_metrics_server_started() -> bool: ...

    def get_pipeline_runner_service(
        registry: PipelineRegistry | None = None,
    ) -> PipelineRunnerService: ...

    async def run_pipeline(name: str, options: RunOptions) -> RunResult: ...


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

    return bool(
        _impl(
            run_label=run_label,
            pipeline_name=pipeline_name,
            run_type=run_type,
        )
    )


def __getattr__(name: str) -> object:
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
