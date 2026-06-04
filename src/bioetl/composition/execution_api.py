"""Public execution-oriented composition API."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from bioetl.composition.lazy_exports import install_lazy_exports

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
    from collections.abc import Callable

    from bioetl.application.services.execution.pipeline_runner_models import (
        PipelineRunResult,
        RunOptions,
        RunResult,
    )
    from bioetl.application.services.execution.pipeline_runner_service import (
        PipelineRunnerService,
    )
    from bioetl.composition._pipeline_execution import ArchiveOptions, VacuumOptions
    from bioetl.composition.bootstrap.runtime.observability import (
        maybe_start_metrics_server,
    )
    from bioetl.composition.registry_api import PipelineRegistry
    from bioetl.domain.context import PipelineRunContext
    from bioetl.domain.ports import ClockPort, ExecutionMetricsRunnerPort
    from bioetl.domain.types import RunID

    def build_pipeline_context(
        name: str,
        options: RunOptions,
        *,
        run_id: RunID | UUID | str | None = None,
        run_id_factory: Callable[[], RunID | UUID | str] | None = None,
        clock: ClockPort | None = None,
        started_at: datetime | None = None,
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
    grouping_key_extra: Mapping[str, str] | None = None,
    metric_names: tuple[str, ...] | None = None,
) -> bool:
    """Push metrics through the composition-owned observability seam."""
    from bioetl.composition.observability_api import (
        push_metrics_to_gateway as _impl,
    )

    gateway_kwargs: dict[str, object] = {
        "run_label": run_label,
        "pipeline_name": pipeline_name,
        "run_type": run_type,
    }
    if grouping_key_extra is not None:
        gateway_kwargs["grouping_key_extra"] = grouping_key_extra
    if metric_names is not None:
        gateway_kwargs["metric_names"] = metric_names
    return bool(_impl(**gateway_kwargs))


install_lazy_exports(
    module_globals=globals(), public_exports=_PUBLIC_EXPORTS, module_name=__name__
)
