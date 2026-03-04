"""Services Factory.

Contains BaseServicesFactory for creating PipelineService with all dependencies.
ServicesBuilder and helpers have been extracted to services_builder.py.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from bioetl.application.core.pipeline_services import PipelineService
from bioetl.composition.factories.dq_context_resolver import (
    create_dq_services as _create_dq_services_impl,
)
from bioetl.domain.types import JsonDict
from bioetl.composition.factories.dq_context_resolver import (
    get_flat_structure as _get_flat_structure_impl,
)
from bioetl.composition.factories.dq_context_resolver import (
    get_output_root as _get_output_root_impl,
)
from bioetl.composition.factories.dq_context_resolver import (
    is_dq_report_enabled as _is_dq_report_enabled_impl,
)
from bioetl.composition.factories.dq_factory import DQServicesFactory
from bioetl.composition.factories.services_builder import (
    ServicesBuilder,
    create_data_normalization_service,
    extract_pipeline_callbacks,
)
from bioetl.composition.factories.storage import StorageContext, StorageFactory
from bioetl.domain.ports import (
    CheckpointPort,
    LockPort,
    MetricsPort,
    NoOpMetrics,
    QuarantinePort,
)
from bioetl.infrastructure.checkpoint.local_checkpoint import LocalCheckpoint
from bioetl.infrastructure.locking.memory_lock import MemoryLock
from bioetl.infrastructure.observability.prometheus_metrics import PrometheusMetrics
from bioetl.infrastructure.quarantine import UnifiedQuarantine

if TYPE_CHECKING:
    from bioetl.composition.services.metadata_coordinator import MetadataCoordinator
    from bioetl.domain.ports import (
        DataSourcePort,
        DQMonitorPort,
        LoggerPort,
        SilverValidatorPort,
        TracingPort,
    )
    from bioetl.infrastructure.config import Settings
    from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig


__all__ = [
    "BaseServicesFactory",
    "DQServicesFactory",
    "ServicesBuilder",
    "create_data_normalization_service",
    "extract_pipeline_callbacks",
]


class BaseServicesFactory:
    """Reusable factory for common services (local deployment)."""

    @classmethod
    def create_common_services(
        cls,
        settings: Settings,
        logger: LoggerPort,
        data_source: DataSourcePort,
        pipeline_config: PipelineYamlConfig,
        metrics: MetricsPort | None = None,
        tracer: TracingPort | None = None,
        dq_monitor: DQMonitorPort | None = None,
        metadata_coordinator: MetadataCoordinator | None = None,
        silver_validator: SilverValidatorPort | None = None,
    ) -> PipelineService:
        """Create a fully wired `PipelineService` bundle for one pipeline run."""
        metrics_port = metrics if metrics is not None else cls._create_metrics(settings)
        cls._ensure_prod_silver_validator(settings, pipeline_config, silver_validator)
        storage_ctx = StorageFactory.create(
            settings,
            pipeline_config,
            logger,
            metrics=metrics_port,
            metadata_coordinator=metadata_coordinator,
            silver_validator=silver_validator,
        )
        lock = cls._create_lock()
        checkpoint = cls._create_checkpoint(storage_ctx)
        quarantine = cls._create_quarantine(settings)
        tracer_port = cls._resolve_tracer(tracer)
        dq_services = cls._create_dq_services(
            settings=settings,
            pipeline_config=pipeline_config,
            logger=logger,
        )
        return cls._build_pipeline_services(
            data_source=data_source,
            storage_ctx=storage_ctx,
            lock=lock,
            checkpoint=checkpoint,
            quarantine=quarantine,
            metrics_port=metrics_port,
            tracer=tracer_port,
            logger=logger,
            dq_monitor=dq_monitor,
            metadata_coordinator=metadata_coordinator,
            dq_services=dq_services,
        )

    @staticmethod
    def _ensure_prod_silver_validator(
        settings: Settings,
        pipeline_config: PipelineYamlConfig,
        silver_validator: SilverValidatorPort | None,
    ) -> None:
        """Enforce validator requirement in production mode."""
        if (
            settings.env == "prod"
            and not settings.test_mode
            and silver_validator is None
        ):
            raise ValueError(
                "Silver validator is required for production pipelines "
                f"(pipeline={pipeline_config.pipeline_name})"
            )

    @staticmethod
    def _resolve_tracer(tracer: TracingPort | None) -> TracingPort:
        """Return tracer or fallback to NoOpTracing."""
        if tracer is None:
            from bioetl.domain.ports import NoOpTracing

            return NoOpTracing()
        return tracer

    @staticmethod
    def _build_pipeline_services(
        *,
        data_source: DataSourcePort,
        storage_ctx: StorageContext,
        lock: LockPort,
        checkpoint: CheckpointPort,
        quarantine: QuarantinePort,
        metrics_port: MetricsPort,
        tracer: TracingPort,
        logger: LoggerPort,
        dq_monitor: DQMonitorPort | None,
        metadata_coordinator: MetadataCoordinator | None,
        dq_services: JsonDict,  # Any: heterogeneous DQ service instances
    ) -> PipelineService:
        """Assemble PipelineService from pre-built dependencies."""
        from bioetl.infrastructure.storage.metadata_writer import MetadataWriter

        metadata_writer = MetadataWriter(logger=logger)
        return PipelineService(
            data_source=data_source,
            storage=storage_ctx.adapter,
            lock=lock,
            checkpoint=checkpoint,
            quarantine=quarantine,
            metrics=metrics_port,
            tracing=tracer,
            logger=logger,
            dq_monitor=dq_monitor,
            metadata_coordinator=metadata_coordinator,
            metadata_writer=metadata_writer,
            bronze_dq_analyzer=dq_services.get("bronze_analyzer"),
            silver_dq_analyzer=dq_services.get("silver_analyzer"),
            gold_dq_analyzer=dq_services.get("gold_analyzer"),
            dq_report_writer=dq_services.get("report_writer"),
            dq_report_service=dq_services.get("report_service"),
        )

    @staticmethod
    def _create_lock() -> LockPort:
        """Create in-memory lock for local deployment."""
        lock = MemoryLock()
        assert isinstance(lock, LockPort), f"MemoryLock must implement LockPort, got {type(lock)}"
        return lock

    @staticmethod
    def _create_checkpoint(storage_ctx: StorageContext) -> CheckpointPort:
        """Create local filesystem checkpoint."""
        checkpoint = LocalCheckpoint(base_path=storage_ctx.checkpoints_path)
        assert isinstance(checkpoint, CheckpointPort), (
            f"LocalCheckpoint must implement CheckpointPort, got {type(checkpoint)}"
        )
        return checkpoint

    @staticmethod
    def _create_quarantine(settings: Settings) -> QuarantinePort:
        """Create unified quarantine storage."""
        quarantine = UnifiedQuarantine(base_path=str(settings.quarantine_path))
        assert isinstance(quarantine, QuarantinePort), (
            f"UnifiedQuarantine must implement QuarantinePort, got {type(quarantine)}"
        )
        return quarantine

    @staticmethod
    def _create_metrics(settings: Settings) -> MetricsPort:
        if settings.metrics_enabled:
            metrics = PrometheusMetrics()
        else:
            metrics = NoOpMetrics()
        assert isinstance(metrics, MetricsPort), (
            f"Metrics adapter must implement MetricsPort, got {type(metrics)}"
        )
        return metrics

    @staticmethod
    def _get_output_root(
        settings: Settings,
        pipeline_config: PipelineYamlConfig,
    ) -> Path:
        """Derive output root from pipeline config or fall back to settings."""
        return _get_output_root_impl(settings, pipeline_config)

    @classmethod
    def _create_dq_services(
        cls,
        settings: Settings,
        pipeline_config: PipelineYamlConfig,
        logger: LoggerPort,
    ) -> JsonDict:  # Any: heterogeneous DQ service instances
        """Create DQ analyzers/writer/services when DQ reporting is enabled."""
        return _create_dq_services_impl(settings, pipeline_config, logger)

    @staticmethod
    def _is_dq_report_enabled(config: PipelineYamlConfig) -> bool:
        """Check if any DQ report is enabled in pipeline config."""
        return _is_dq_report_enabled_impl(config)

    @staticmethod
    def _get_flat_structure(config: PipelineYamlConfig) -> bool:
        """Get flat_structure setting from pipeline config."""
        return _get_flat_structure_impl(config)
