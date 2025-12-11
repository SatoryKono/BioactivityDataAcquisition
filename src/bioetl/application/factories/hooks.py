"""
Factory for creating pipeline hooks.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from bioetl.application.factories.hooks_impl import (
    LoggingPipelineHookImpl,
    MetricsPipelineHookImpl,
)
from bioetl.domain.configs import PipelineConfig
from bioetl.domain.observability import LoggingPortABC, MetricsPortABC
from bioetl.domain.pipelines.contracts import PipelineHookABC


class PipelineHookFactoryABC(ABC):
    """Abstract factory for creating pipeline hooks.

    Defines the contract for factories that create hooks for pipeline execution.
    Hooks receive callbacks at various points during pipeline execution
    (start, batch processed, error, completion).
    """

    @abstractmethod
    def create_hooks(self, logger: LoggingPortABC) -> list[PipelineHookABC]:
        """Create pipeline execution hooks.

        Args:
            logger: Logger instance for logging hooks.

        Returns:
            List of pipeline hooks to be invoked during execution.
        """


class PipelineHookFactory(PipelineHookFactoryABC):
    """Factory for creating pipeline hooks."""

    def __init__(
        self,
        config: PipelineConfig,
        metrics_port: MetricsPortABC,
    ) -> None:
        self._config = config
        self._metrics_port = metrics_port

    def create_hooks(self, logger: LoggingPortABC) -> list[PipelineHookABC]:
        """Create standard pipeline hooks."""
        return [
            LoggingPipelineHookImpl(logger),
            MetricsPipelineHookImpl(
                pipeline_id=self._config.id,
                provider=self._config.provider,
                entity_name=self._config.entity_name,
                metrics_port=self._metrics_port,
            ),
        ]
