"""Services Factory - unified factory for creating pipeline services.

Consolidated from base_services_factory.py, services_builder.py, and runner_services.py.
Provides:
- BaseServicesFactory: Factory for PipelineServices
- ServicesBuilder: Builder for pipeline infrastructure components
- build_runner_services: Factory function for RunnerServices
- RunnerServices: Re-export from application layer

Usage:
    >>> from bioetl.composition.factories.services_factory import BaseServicesFactory
    >>> services = BaseServicesFactory.create_common_services(...)
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol

from bioetl.application.core.checkpoint_manager import CheckpointManager
from bioetl.application.core.config import RecordProcessorConfig
from bioetl.application.core.lifecycle_orchestrator import LifecycleOrchestrator
from bioetl.application.core.lock_manager import LockManager
from bioetl.application.core.pipeline_services import PipelineServices
from bioetl.application.core.postrun_service import PostrunService
from bioetl.application.core.preflight_service import PreflightService
from bioetl.application.core.record_processor import RecordProcessor

# Re-export RunnerServices from application layer for backwards compatibility
from bioetl.application.core.runner_services import RunnerServices
from bioetl.application.observability.observer import PipelineObserver
from bioetl.composition.factories.storage_factory import StorageContext, StorageFactory
from bioetl.domain.config import TableConfig
from bioetl.domain.error_classifier import ErrorClassifier
from bioetl.infrastructure.checkpoint.local_checkpoint import LocalCheckpoint
from bioetl.infrastructure.locking.memory_lock import MemoryLock
from bioetl.infrastructure.observability.noop_metrics import NoOpMetrics
from bioetl.infrastructure.observability.prometheus_metrics import PrometheusMetrics
from bioetl.infrastructure.quarantine.unified_quarantine import UnifiedQuarantine
from bioetl.infrastructure.validation import PanderaGoldValidator

if TYPE_CHECKING:
    import pyarrow as pa
    from structlog.stdlib import BoundLogger

    from bioetl.application.core.base import BasePipeline
    from bioetl.application.core.pipeline_context import PipelineContext
    from bioetl.application.core.shutdown import ShutdownSignal
    from bioetl.application.services.medallion_lifecycle import (
        MedallionLifecycleService,
    )
    from bioetl.domain.config import PipelineConfig, RuntimeConfig
    from bioetl.domain.context import PipelineContext as DomainPipelineContext
    from bioetl.domain.ports import (
        CheckpointPort,
        DataSourcePort,
        DQMonitorPort,
        LockPort,
        LoggerPort,
        MetricsPort,
        QuarantinePort,
        TracingPort,
    )
    from bioetl.domain.types import RunID
    from bioetl.infrastructure.config import Settings
    from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig


# =============================================================================
# DataSourceFactory Protocol (from base_services_factory.py)
# =============================================================================


class DataSourceFactoryProtocol(Protocol):
    """Protocol for data source creation."""

    def create(self, settings: Settings, logger: BoundLogger) -> DataSourcePort: ...


# =============================================================================
# BaseServicesFactory (from base_services_factory.py)
# =============================================================================


class BaseServicesFactory:
    """Reusable factory for common services (local deployment)."""

    @classmethod
    def create_common_services(
        cls,
        settings: Settings,
        logger: BoundLogger,
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
        # Create metrics first so it can be passed to storage factory
        metrics = cls._create_metrics(settings)

        storage_ctx = StorageFactory.create(
            settings, pipeline_config, logger, metrics=metrics
        )

        lock = cls._create_lock()
        checkpoint = cls._create_checkpoint(storage_ctx)
        quarantine = cls._create_quarantine(storage_ctx)

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


# =============================================================================
# ServicesBuilder (from services_builder.py)
# =============================================================================


class ServicesBuilder:
    """Builder for pipeline infrastructure components."""

    @staticmethod
    def create_checkpoint_manager(
        checkpoint_port: CheckpointPort,
        logger: BoundLogger,
        pipeline_name: str,
        run_id: RunID,
        resume: bool,
    ) -> CheckpointManager:
        """Create configured CheckpointManager.

        Args:
            checkpoint_port: Checkpoint storage port
            logger: Structured logger
            pipeline_name: Name of the pipeline
            run_id: Unique run identifier
            resume: Whether to resume from previous checkpoint

        Returns:
            Configured CheckpointManager instance
        """
        return CheckpointManager(
            checkpoint_port=checkpoint_port,
            logger=logger,
            pipeline_name=pipeline_name,
            run_id=run_id,
            resume=resume,
        )

    @staticmethod
    def create_record_processor(
        services: PipelineServices,
        context: PipelineContext,
        pipeline_name: str,
        provider: str,
        entity_type: str,
        silver_schema: pa.Schema | None,
        gold_schema: Any,
        dq_config: Any,
        primary_keys: Sequence[str],
        silver_table: str,
        gold_table: str,
        silver_write_mode: str,
        gold_write_mode: str,
        on_schema_mismatch: str,
        transform_callback: Any,
        gold_filter_callback: Any,
        gold_transform_callback: Any,
        *,
        strict_gold_validation: bool = False,
    ) -> RecordProcessor:
        """Create configured RecordProcessor.

        Args:
            services: Pipeline services
            context: Pipeline context
            pipeline_name: Name of the pipeline
            provider: Data provider name
            entity_type: Entity type being processed
            silver_schema: PyArrow schema for Silver layer
            gold_schema: Pandera schema for Gold layer
            dq_config: Data quality configuration
            primary_keys: Primary key fields
            silver_table: Silver table name
            gold_table: Gold table name
            silver_write_mode: Write mode for Silver
            gold_write_mode: Write mode for Gold
            on_schema_mismatch: Schema mismatch handling strategy
            transform_callback: Bronze to Silver transformation callback
            gold_filter_callback: Gold filtering callback
            gold_transform_callback: Silver to Gold transformation callback
            strict_gold_validation: If True, validation fails when gold_schema is None.
                Default False for backward compatibility.

        Returns:
            Configured RecordProcessor instance
        """
        error_classifier = ErrorClassifier()
        table_config = TableConfig(
            primary_keys=primary_keys,
            silver_table=silver_table,
            gold_table=gold_table,
            silver_write_mode=silver_write_mode,
            gold_write_mode=gold_write_mode,
            on_schema_mismatch=on_schema_mismatch,
        )

        processor_config = RecordProcessorConfig(
            pipeline_name=pipeline_name,
            provider=provider,
            entity_type=entity_type,
            silver_schema=silver_schema,
            gold_schema=gold_schema,
            dq_config=dq_config,
            table_config=table_config,
        )

        # Create Gold validator from schema (DI pattern)
        # strict mode requires schema to be provided
        gold_validator = PanderaGoldValidator(gold_schema, strict=strict_gold_validation)

        return RecordProcessor(
            services=services,
            error_classifier=error_classifier,
            context=context,
            config=processor_config,
            transform_callback=transform_callback,
            gold_filter_callback=gold_filter_callback,
            gold_transform_callback=gold_transform_callback,
            gold_validator=gold_validator,
        )

    @staticmethod
    def create_record_processor_from_pipeline(
        pipeline: BasePipeline,
        silver_schema: pa.Schema | None,
        gold_schema: Any,
        *,
        strict_gold_validation: bool = False,
    ) -> RecordProcessor:
        """Create RecordProcessor from pipeline instance.

        Convenience method that extracts configuration from pipeline.

        Args:
            pipeline: Pipeline instance
            silver_schema: PyArrow schema for Silver layer
            gold_schema: Pandera schema for Gold layer
            strict_gold_validation: If True, validation fails when gold_schema is None.
                Default False for backward compatibility.

        Returns:
            Configured RecordProcessor instance
        """
        return ServicesBuilder.create_record_processor(
            services=pipeline.services,
            context=pipeline.context,
            pipeline_name=pipeline.config.pipeline_name,
            provider=pipeline.config.provider,
            entity_type=pipeline.config.entity_type,
            silver_schema=silver_schema,
            gold_schema=gold_schema,
            dq_config=pipeline.config.dq,
            primary_keys=pipeline.config.primary_keys,
            silver_table=pipeline.config.silver_table,
            gold_table=pipeline.config.gold_table,
            silver_write_mode=pipeline.config.write_mode,
            gold_write_mode=pipeline.config.gold_write_mode,
            on_schema_mismatch=pipeline.config.on_schema_mismatch,
            transform_callback=pipeline.transform_bronze_to_silver,
            gold_filter_callback=pipeline.should_write_gold,
            gold_transform_callback=pipeline.transform_for_gold,
            strict_gold_validation=strict_gold_validation,
        )


# =============================================================================
# RunnerServices Factory (from runner_services.py)
# =============================================================================


def build_runner_services(
    config: PipelineConfig,
    runtime: RuntimeConfig,
    services: PipelineServices,
    context: DomainPipelineContext,
    logger: LoggerPort,
    shutdown_signal: ShutdownSignal,
    checkpoint_manager: CheckpointManager,
    lifecycle_service: MedallionLifecycleService,
    tracer: TracingPort | None = None,
) -> RunnerServices:
    """Build RunnerServices bundle.

    Factory function that creates all application services required by PipelineRunner.
    This centralizes service creation in the composition layer.

    Args:
        config: Pipeline configuration.
        runtime: Runtime configuration.
        services: Pipeline services (storage, lock, metrics, etc.).
        context: Pipeline execution context.
        logger: Structured logger.
        shutdown_signal: Shutdown signal for graceful termination.
        checkpoint_manager: Checkpoint manager.
        lifecycle_service: Medallion lifecycle service.
        tracer: Optional tracing port for distributed tracing.

    Returns:
        RunnerServices bundle with all required services.
    """
    lock_manager = LockManager.create(
        lock_port=services.lock,
        run_id=context.run_id,
        provider=config.provider,
        entity_type=config.entity_type,
        run_type=runtime.run_type,
        lock_ttl=runtime.effective_lock_ttl,
        wait_for_lock=runtime.wait_for_lock,
        wait_timeout=runtime.lock_wait_timeout,
        heartbeat_interval=runtime.heartbeat_interval,
        logger=logger,
        shutdown_signal=shutdown_signal,
        checkpoint_manager=checkpoint_manager,
    )

    preflight_service = PreflightService(
        config=config,
        context=context,
        logger=logger,
        metrics=services.metrics,
    )

    postrun_service = PostrunService(
        config=config,
        runtime=runtime,
        services=services,
        logger=logger,
        lifecycle_service=lifecycle_service,
    )

    lifecycle_orchestrator = LifecycleOrchestrator(
        config=config,
        runtime=runtime,
        logger=logger,
        lifecycle_service=lifecycle_service,
    )

    observer = PipelineObserver(
        pipeline_name=config.pipeline_name,
        run_id=context.run_id,
        run_type=runtime.run_type,
        metrics=services.metrics,
        logger=logger,
        tracer=tracer,
    )

    return RunnerServices(
        lock_manager=lock_manager,
        preflight=preflight_service,
        postrun=postrun_service,
        lifecycle_orch=lifecycle_orchestrator,
        observer=observer,
    )


__all__ = [
    "BaseServicesFactory",
    "DataSourceFactoryProtocol",
    "RunnerServices",
    "ServicesBuilder",
    "build_runner_services",
]
