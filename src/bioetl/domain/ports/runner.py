"""Runner port interfaces for dependency inversion.

Defines protocols for pipeline runner creation and execution.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    import pyarrow as pa

    from bioetl.application.core.base import BasePipeline
    from bioetl.application.core.runner import PipelineRunner
    from bioetl.composition.observability import ObservabilityBundle
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
    from bioetl.infrastructure.config import Settings
    from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig

__all__ = [
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
    ) -> RunnablePort:
        """Create a configured pipeline runner.

        Args:
            context: Pipeline run context containing all execution parameters.

        Returns:
            Runnable object ready for execution.

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

    def extract_metrics(self, runner: RunnablePort) -> dict[str, int]:
        """Extract execution metrics from a runner.

        Args:
            runner: Runner to extract metrics from.

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
    silver_schema: pa.Schema | None
    pandera_silver_schema: object | None

    def create_with_services(
        self,
        run_id: RunID,
        runtime: RuntimeConfig,
        settings: Settings,
        logger: LoggerPort,
        config: PipelineYamlConfig | None = ...,
        filter_config: InputFilterConfig | None = ...,
        tracer: TracingPort | None = ...,
        dq_monitor: DQMonitorPort | None = ...,
        metrics: MetricsPort | None = ...,
        cached_bronze: CachedBronzeContext | None = ...,
    ) -> BasePipeline:
        """Create pipeline with services.

        Args:
            run_id: Pipeline run identifier.
            runtime: Runtime configuration.
            settings: Settings object.
            logger: Logger instance.
            config: Configuration object.
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
        settings: Settings,
        observability: ObservabilityBundle,
        filter_config: InputFilterConfig | None = None,
        config: PipelineYamlConfig | None = None,
        cached_bronze: CachedBronzeContext | None = None,
    ) -> PipelineRunner:
        """Create pipeline runner.

        Args:
            run_id: Pipeline run identifier.
            runtime: Runtime configuration.
            settings: Settings object.
            observability: Observability.
            filter_config: Configuration for filter.
            config: Configuration object.
            cached_bronze: Cached bronze.

        Returns:
            Newly created PipelineRunner instance.
        """
        ...
