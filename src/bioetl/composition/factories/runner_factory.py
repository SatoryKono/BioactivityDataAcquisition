"""Runner factory implementation for composition layer.

Implements RunnerFactoryPort and MetricsExtractorPort protocols
for the PipelineRunnerService.

This module provides the composition-layer implementation of runner
creation, allowing the application layer to remain independent of
bootstrap details.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from bioetl.composition.factories.pipeline_factories import register_all_pipelines
from bioetl.composition.providers.registration import register_all_providers
from bioetl.composition.registry import PipelineRegistry, get_default_registry
from bioetl.composition.runtime_builders.runner_builder import build_pipeline_runner

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineRunContext
    from bioetl.domain.ports import RunnablePort


__all__ = [
    "MetricsExtractor",
    "RunnerFactory",
    "create_metrics_extractor",
    "create_runner_factory",
]


class RunnerFactory:
    """Factory for creating pipeline runners.

    Implements RunnerFactoryPort protocol for PipelineRunnerService.
    Delegates to build_pipeline_runner() for actual runner creation.

    Attributes:
        registry: Optional custom registry for test isolation.
    """

    def __init__(
        self,
        registry: PipelineRegistry | None = None,
        runner_builder: Callable[..., RunnablePort] | None = None,
    ) -> None:
        """Initialize the factory.

        Args:
            registry: Optional custom registry. If None, uses default.
            runner_builder: Optional runner assembly function for DI/testing.
        """
        self._registry = registry
        self._runner_builder = runner_builder
        self._registrations_done = False

    def _ensure_registrations(self) -> None:
        """Ensure all providers and pipelines are registered.

        Idempotent - safe to call multiple times.
        """
        if not self._registrations_done:
            register_all_providers()
            register_all_pipelines(registry=self._registry)
            self._registrations_done = True

    @property
    def _effective_registry(self) -> PipelineRegistry:
        """Get the effective registry instance."""
        return self._registry if self._registry is not None else get_default_registry()

    def create(self, context: PipelineRunContext) -> RunnablePort:
        """Create a configured pipeline runner.

        Args:
            context: Pipeline run context containing all execution parameters.

        Returns:
            PipelineRunner ready for execution.

        Raises:
            ValueError: If pipeline name is unknown or config is invalid.
            FileNotFoundError: If pipeline config file is missing.
        """
        self._ensure_registrations()
        runner_builder = self._runner_builder or build_pipeline_runner
        runner: RunnablePort = runner_builder(context, registry=self._registry)
        return runner

    def list_pipelines(self) -> list[str]:
        """List all available pipeline names.

        Returns:
            Sorted list of registered pipeline names.
        """
        self._ensure_registrations()
        return self._effective_registry.list_pipelines()

    def contains(self, pipeline_name: str) -> bool:
        """Check if a pipeline is registered.

        Args:
            pipeline_name: Name of the pipeline to check.

        Returns:
            True if pipeline exists, False otherwise.
        """
        self._ensure_registrations()
        return self._effective_registry.contains(pipeline_name)


class MetricsExtractor:
    """Extractor for pipeline execution metrics.

    Implements MetricsExtractorPort protocol for PipelineRunnerService.
    Extracts metrics from the runner's internal executor.
    """

    def extract_metrics(self, runner: RunnablePort) -> dict[str, int]:
        """Extract execution metrics from a runner.

        Args:
            runner: Runner to extract metrics from.

        Returns:
            Dictionary with metric names and values.
        """
        # Access the internal executor if available
        executor = getattr(runner, "_executor", None)

        if executor is None:
            return {
                "records_fetched": 0,
                "records_bronze": 0,
                "records_silver": 0,
                "records_gold": 0,
                "records_quarantined": 0,
            }

        return {
            "records_fetched": getattr(executor, "records_fetched", 0),
            "records_bronze": getattr(executor, "records_bronze", 0),
            "records_silver": getattr(executor, "records_silver", 0),
            "records_gold": getattr(executor, "records_gold", 0),
            "records_quarantined": getattr(executor, "records_quarantined", 0),
        }


def create_runner_factory(
    registry: PipelineRegistry | None = None,
    runner_builder: Callable[..., RunnablePort] | None = None,
) -> RunnerFactory:
    """Create a new RunnerFactory instance.

    Args:
        registry: Optional custom registry for test isolation.
        runner_builder: Optional runner assembly function for DI/testing.

    Returns:
        RunnerFactory instance.
    """
    return RunnerFactory(registry=registry, runner_builder=runner_builder)


def create_metrics_extractor() -> MetricsExtractor:
    """Create a new MetricsExtractor instance.

    Returns:
        MetricsExtractor instance.
    """
    return MetricsExtractor()
