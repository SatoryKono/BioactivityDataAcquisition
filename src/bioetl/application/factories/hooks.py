"""
Factory for creating pipeline hooks.
"""
from __future__ import annotations

from bioetl.application.pipelines.hooks_impl import (
    LoggingPipelineHookImpl,
    MetricsPipelineHookImpl,
)
from bioetl.domain.configs import PipelineConfig
from bioetl.domain.observability import LoggingPortABC, MetricsPortABC
from bioetl.domain.pipelines.contracts import PipelineHookABC


class PipelineHookFactory:
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
