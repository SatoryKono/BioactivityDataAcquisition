"""Runner port interfaces for dependency inversion.

Defines protocols for pipeline runner creation and execution.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from pathlib import Path

    from bioetl.domain.context import PipelineRunContext


@runtime_checkable
class RunnablePort(Protocol):
    """Protocol for runnable objects (e.g., PipelineRunner).

    This port abstracts the execution interface for pipelines.
    """

    async def run(self) -> None:
        """Execute the pipeline."""
        ...

    @property
    def shutdown_signal(self) -> Any | None:
        """Optional shutdown signal for graceful termination."""
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
