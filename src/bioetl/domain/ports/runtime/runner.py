"""Runner port interfaces for dependency inversion.

Defines protocols for pipeline runner creation and execution.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from bioetl.domain.config import RuntimeConfig
    from bioetl.domain.context import CachedBronzeContext, PipelineRunContext
    from bioetl.domain.filtering import InputFilterConfig
    from bioetl.domain.ports.observability import (
        DQMonitorPort,
        LoggerPort,
        MetricsPort,
        TracingPort,
    )
    from bioetl.domain.types import RunID

__all__ = [
    "ExecutionMetricsReadablePort",
    "ExecutionMetricsRunnerPort",
    "MetricsExtractorPort",
    "PipelineFactoryPort",
    "RunnablePort",
    "RunnerFactoryPort",
]


@runtime_checkable
class RunnablePort(Protocol):
    """Protocol for runnable objects (e.g., PipelineRunner).

    This port abstracts the execution interface for pipelines.
    """

    async def run(self) -> None:
        """Execute the pipeline."""
        ...

    @property
    def shutdown_signal(self) -> object | None:
        """Optional shutdown signal for graceful termination.

        Returns:
            Shutdown signal object or None.
        """
        ...

    @property
    def run_id(self) -> str:
        """Stable run identifier for the current execution."""
        ...


@runtime_checkable
class ExecutionMetricsReadablePort(Protocol):
    """Protocol for runners that expose execution counters."""

    @property
    def execution_metrics(self) -> dict[str, int]:
        """Execution counters keyed by canonical metric names.

        Required keys:
        - ``records_fetched``
        - ``records_bronze``
        - ``records_silver``
        - ``records_gold``
        - ``records_quarantined``
        """
        ...


@runtime_checkable
class ExecutionMetricsRunnerPort(
    RunnablePort,
    ExecutionMetricsReadablePort,
    Protocol,
):
    """Protocol for runners that are executable and expose counters."""


@runtime_checkable
class RunnerFactoryPort(Protocol):
    """Port for creating pipeline runners.

    This port abstracts runner creation, allowing the application layer
    to orchestrate pipeline runs without depending on composition layer.

    Implements RULES.md §1.1 - Ports & Adapters architecture.
    """

    def create(
        self,
        context: PipelineRunContext,
    ) -> ExecutionMetricsRunnerPort:
        """Create a configured pipeline runner.

        Args:
            context: Pipeline run context containing all execution parameters.

        Returns:
            Runnable object ready for execution and metric extraction.

        Raises:
            ValueError: If pipeline name is unknown or config is invalid.
            FileNotFoundError: If pipeline config file is missing.
        """
        ...

    def list_pipelines(self) -> list[str]:
        """List all available pipeline names.

        Returns:
            Sorted list of registered pipeline names.
        """
        ...

    def contains(self, pipeline_name: str) -> bool:
        """Check if a pipeline is registered.

        Args:
            pipeline_name: Name of the pipeline to check.

        Returns:
            True if pipeline exists, False otherwise.
        """
        ...


@runtime_checkable
class MetricsExtractorPort(Protocol):
    """Protocol for extracting execution metrics from a runner.

    This port allows the service to collect metrics without
    depending on internal runner structure.
    """

    def extract_metrics(self, runner: ExecutionMetricsReadablePort) -> dict[str, int]:
        """Extract execution metrics from a runner.

        Args:
            runner: Runner exposing the execution-metrics contract.

        Returns:
            Dictionary with metric names and values:
            - records_fetched: Total records retrieved
            - records_bronze: Records written to Bronze
            - records_silver: Records written to Silver
            - records_gold: Records written to Gold
            - records_quarantined: Records sent to quarantine
        """
        ...


@runtime_checkable
class PipelineFactoryPort(Protocol):
    """Protocol for pipeline factories."""

    pipeline_name: str
    silver_schema: object | None
    pandera_silver_schema: object | None

    def create_with_services(
        self,
        run_id: RunID,
        runtime: RuntimeConfig,
        settings: object,
        logger: LoggerPort,
        config: object | None = ...,
        filter_config: InputFilterConfig | None = ...,
        tracer: TracingPort | None = ...,
        dq_monitor: DQMonitorPort | None = ...,
        metrics: MetricsPort | None = ...,
        cached_bronze: CachedBronzeContext | None = ...,
    ) -> object:
        """Create pipeline with services.

        Args:
            run_id: Pipeline run identifier.
            runtime: Runtime configuration.
            settings: Settings object (infrastructure.config.Settings).
            logger: Logger instance.
            config: Configuration object (PipelineYamlConfig).
            filter_config: Configuration for filter.
            tracer: Tracing instance.
            dq_monitor: Dq monitor.
            metrics: Metrics collector instance.
            cached_bronze: Cached bronze.

        Returns:
            Newly created BasePipeline instance.
        """
        ...

    def create_runner(
        self,
        run_id: RunID,
        runtime: RuntimeConfig,
        settings: object,
        observability: object,
        filter_config: InputFilterConfig | None = None,
        config: object | None = None,
        cached_bronze: CachedBronzeContext | None = None,
    ) -> object:
        """Create pipeline runner.

        Args:
            run_id: Pipeline run identifier.
            runtime: Runtime configuration.
            settings: Settings object (infrastructure.config.Settings).
            observability: ObservabilityBundle from composition layer.
            filter_config: Configuration for filter.
            config: Configuration object (PipelineYamlConfig).
            cached_bronze: Cached bronze.

        Returns:
            Newly created PipelineRunner instance.
        """
        ...
