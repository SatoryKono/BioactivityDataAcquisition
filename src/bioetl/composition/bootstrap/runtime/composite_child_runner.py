"""Run composite children through the canonical report-producing lifecycle."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from bioetl.application.services.execution.pipeline_runner_models import (
    PipelineRunResult,
    RunOptions,
)
from bioetl.composition.bootstrap.runtime.runner import (
    bootstrap_pipeline_runner_service,
)
from bioetl.domain.context import PipelineRunContext
from bioetl.domain.exceptions.pipeline_shutdown import PipelineShutdownError
from bioetl.domain.ports import ExecutionMetricsRunnerPort

if TYPE_CHECKING:
    from bioetl.application.services.execution.pipeline_runner_service import (
        PipelineRunnerService,
    )


@dataclass
class _ChildRunnerFactory:
    pipeline_name: str
    builder: Callable[[PipelineRunContext], ExecutionMetricsRunnerPort]
    runner: ExecutionMetricsRunnerPort | None = None

    def contains(self, pipeline_name: str) -> bool:
        return pipeline_name == self.pipeline_name

    def list_pipelines(self) -> list[str]:
        return [self.pipeline_name]

    def create(self, context: PipelineRunContext) -> ExecutionMetricsRunnerPort:
        # Creation happens inside the service's observation/accounting context.
        self.runner = self.builder(context)
        return self.runner


@dataclass
class ReportedChildRunner:
    """Preserve coordinator metrics and failure semantics after saving evidence."""

    context: PipelineRunContext
    options: RunOptions
    service: PipelineRunnerService
    factory: _ChildRunnerFactory

    @property
    def run_id(self) -> str:
        return str(self.context.run_id)

    @property
    def shutdown_signal(self) -> object | None:
        return self.factory.runner.shutdown_signal if self.factory.runner else None

    @property
    def execution_metrics(self) -> dict[str, int]:
        return self.factory.runner.execution_metrics if self.factory.runner else {}

    async def run(self) -> None:
        result = await self.service.run(
            self.context.pipeline_name,
            run_id=self.context.run_id,
            options=self.options,
        )
        if result.status == PipelineRunResult.SHUTDOWN:
            raise PipelineShutdownError(
                f"Composite child {result.pipeline_name} shut down"
            )
        if not result.is_success:
            raise RuntimeError(
                f"Composite child {result.pipeline_name} failed: "
                f"{result.error_type}: {result.error_message}"
            )
        if result.run_report_error:
            raise RuntimeError(
                f"Composite child evidence failed: {result.run_report_error}"
            )


def build_reported_child_runner(
    *,
    context: PipelineRunContext,
    options: RunOptions,
    runner_builder: Callable[[PipelineRunContext], ExecutionMetricsRunnerPort],
) -> ReportedChildRunner:
    """Keep each child's reporting dependencies and mutable factory isolated."""
    factory = _ChildRunnerFactory(context.pipeline_name, runner_builder)
    service = bootstrap_pipeline_runner_service()
    service.runner_factory = factory
    return ReportedChildRunner(context, options, service, factory)
