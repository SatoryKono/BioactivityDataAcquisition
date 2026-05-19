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

from bioetl.composition.factories.pipeline.registry import register_all_pipelines
from bioetl.composition.providers import ensure_providers_loaded
from bioetl.composition.registry_api import PipelineRegistry, create_registry
from bioetl.composition.runtime_builders.runner_builder import build_pipeline_runner

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineRunContext
    from bioetl.domain.ports import (
        ExecutionMetricsReadablePort,
        ExecutionMetricsRunnerPort,
    )


__all__ = [
    "MetricsExtractor",
    "RunnerFactory",
    "create_metrics_extractor",
    "create_runner_factory",
]


def _require_execution_metrics_runner(
    runner: object,
) -> ExecutionMetricsRunnerPort:
    """Validate that a producer returned a metrics-readable runnable."""
    from bioetl.domain.ports import ExecutionMetricsRunnerPort

    if not isinstance(runner, ExecutionMetricsRunnerPort):
        raise TypeError("Runner does not implement ExecutionMetricsRunnerPort")
    return runner


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
        registry_factory: Callable[[], PipelineRegistry] | None = None,
        runner_builder: Callable[..., ExecutionMetricsRunnerPort] | None = None,
        ensure_providers_loaded_fn: Callable[[], None] = ensure_providers_loaded,
    ) -> None:
        """Initialize the factory.

        Args:
            registry: Optional custom registry. If None, a fresh registry is
                created lazily for this factory instance.
            registry_factory: Optional registry factory for DI/testing when no
                explicit registry is supplied.
            runner_builder: Optional runner assembly function for DI/testing.
        """
        self._registry = registry
        self._registry_factory = registry_factory or create_registry
        self._runner_builder = runner_builder
        self._ensure_providers_loaded_fn = ensure_providers_loaded_fn
        self._registrations_done = False

    def _ensure_registrations(self) -> None:
        """Ensure all providers and pipelines are registered.

        Idempotent - safe to call multiple times.
        """
        if not self._registrations_done:
            self._ensure_providers_loaded_fn()
            if not self._effective_registry.list_pipelines():
                register_all_pipelines(registry=self._effective_registry)
            self._registrations_done = True

    @property
    def _effective_registry(self) -> PipelineRegistry:
        """Get the effective registry instance."""
        if self._registry is None:
            self._registry = self._registry_factory()
        return self._registry

    def create(self, context: PipelineRunContext) -> ExecutionMetricsRunnerPort:
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
        runner = runner_builder(context, registry=self._effective_registry)
        return _require_execution_metrics_runner(runner)

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
        return bool(self._effective_registry.contains(pipeline_name))


class MetricsExtractor:
    """Extractor for pipeline execution metrics.

    Implements MetricsExtractorPort protocol for PipelineRunnerService.
    Extracts metrics from the runner's public execution-metrics contract.
    """

    def extract_metrics(self, runner: ExecutionMetricsReadablePort) -> dict[str, int]:
        """Extract execution metrics from a runner.

        Args:
            runner: Runner to extract metrics from.

        Returns:
            Dictionary with metric names and values.
        """
        try:
            metrics = runner.execution_metrics
        except AttributeError as error:
            raise TypeError(
                "Runner does not expose a valid execution_metrics mapping"
            ) from error
        if not isinstance(metrics, dict):
            raise TypeError("Runner does not expose a valid execution_metrics mapping")

        return {
            "records_fetched": int(metrics["records_fetched"]),
            "records_bronze": int(metrics["records_bronze"]),
            "records_silver": int(metrics["records_silver"]),
            "records_gold": int(metrics["records_gold"]),
            "records_gold_excluded_by_contract": int(
                metrics.get("records_gold_excluded_by_contract", 0)
            ),
            "records_quarantined": int(metrics["records_quarantined"]),
            "records_filtered_out": int(metrics.get("records_filtered_out", 0)),
        }


def create_runner_factory(
    registry: PipelineRegistry | None = None,
    registry_factory: Callable[[], PipelineRegistry] | None = None,
    runner_builder: Callable[..., ExecutionMetricsRunnerPort] | None = None,
    ensure_providers_loaded_fn: Callable[[], None] = ensure_providers_loaded,
) -> RunnerFactory:
    """Create a new RunnerFactory instance.

    Args:
        registry: Optional custom registry for test isolation.
        registry_factory: Optional registry factory used when ``registry`` is not
            provided.
        runner_builder: Optional runner assembly function for DI/testing.
        ensure_providers_loaded_fn: Optional runtime provider bootstrap callable.

    Returns:
        RunnerFactory instance.
    """
    return RunnerFactory(
        registry=registry,
        registry_factory=registry_factory,
        runner_builder=runner_builder,
        ensure_providers_loaded_fn=ensure_providers_loaded_fn,
    )


def create_metrics_extractor() -> MetricsExtractor:
    """Create a new MetricsExtractor instance.

    Returns:
        MetricsExtractor instance.
    """
    return MetricsExtractor()
