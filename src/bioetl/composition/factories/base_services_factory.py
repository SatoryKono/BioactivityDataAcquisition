"""Base factory for creating PipelineServices.

Simplified for local-only deployment.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Protocol

from bioetl.application.core.pipeline_services import PipelineServices
from bioetl.composition.factories.storage_factory import StorageContext, StorageFactory
from bioetl.domain.ports import LoggerPort
from bioetl.infrastructure.checkpoint.local_checkpoint import LocalCheckpoint
from bioetl.infrastructure.locking.memory_lock import MemoryLock
from bioetl.infrastructure.observability.noop_metrics import NoOpMetrics
from bioetl.infrastructure.observability.prometheus_metrics import PrometheusMetrics
from bioetl.infrastructure.quarantine.unified_quarantine import UnifiedQuarantine

if TYPE_CHECKING:
    from bioetl.domain.ports import (
        CheckpointPort,
        DataSourcePort,
        DQMonitorPort,
        LockPort,
        MetricsPort,
        QuarantinePort,
        TracingPort,
    )
    from bioetl.infrastructure.config import Settings
    from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig


class DataSourceFactory(Protocol):
    """Protocol for data source creation."""

    def create(self, settings: Settings, logger: LoggerPort) -> DataSourcePort: ...


class BaseServicesFactory:
    """Reusable factory for common services (local deployment)."""

    @classmethod
    def create_common_services(
        cls,
        settings: Settings,
        logger: LoggerPort,
        data_source: DataSourcePort,
        pipeline_config: PipelineYamlConfig,
        tracer: TracingPort | None = None,
        dq_monitor: DQMonitorPort | None = None,
    ) -> PipelineServices:
        """Create services with injected data source.

        Args:
            settings: Application settings
            logger: Structured logger
            data_source: Data source port implementation
            pipeline_config: Pipeline YAML configuration
            tracer: Optional tracer (defaults to NoOpTracing if not provided)
            dq_monitor: Optional data quality monitor for anomaly detection

        Returns:
            PipelineServices with all dependencies configured
        """
        storage_ctx = StorageFactory.create(settings, pipeline_config, logger)

        lock = cls._create_lock()
        checkpoint = cls._create_checkpoint(storage_ctx)
        quarantine = cls._create_quarantine(storage_ctx)
        metrics = cls._create_metrics(settings)

        # Use provided tracer or fallback to NoOpTracing
        # Tracer should be created via bootstrap_tracer() for consistent configuration
        if tracer is None:
            from bioetl.infrastructure.observability.noop_tracing import NoOpTracing

            tracer = NoOpTracing()

        return PipelineServices(
            data_source=data_source,
            storage=storage_ctx.adapter,
            lock=lock,
            checkpoint=checkpoint,
            quarantine=quarantine,
            metrics=metrics,
            tracing=tracer,
            logger=logger,
            dq_monitor=dq_monitor,
        )

    @staticmethod
    def _create_lock() -> LockPort:
        """Create in-memory lock for local deployment."""
        return MemoryLock()

    @staticmethod
    def _create_checkpoint(storage_ctx: StorageContext) -> CheckpointPort:
        """Create local filesystem checkpoint."""
        return LocalCheckpoint(base_path=storage_ctx.checkpoints_path)

    @staticmethod
    def _create_quarantine(storage_ctx: StorageContext) -> QuarantinePort:
        """Create local quarantine storage."""
        silver_path = storage_ctx.silver_path
        if isinstance(silver_path, str):
            silver_path = Path(silver_path)
        return UnifiedQuarantine(
            base_path=str(silver_path / "common" / "quarantine"),
        )

    @staticmethod
    def _create_metrics(settings: Settings) -> MetricsPort:
        if settings.metrics_enabled:
            return PrometheusMetrics()
        return NoOpMetrics()
