"""Services Factory.

Consolidated module for creating pipeline infrastructure services.

Contains:
- BaseServicesFactory: Creates PipelineServices with all dependencies
- ServicesBuilder: Creates CheckpointManager, RecordProcessor, BatchExecutor

This module follows the DI pattern: all services are created in the
composition layer and injected into pipeline components.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Sequence
from pathlib import Path
from typing import TYPE_CHECKING, Any

from bioetl.application.core.batch_executor import BatchExecutor
from bioetl.application.core.checkpoint_manager import CheckpointManager
from bioetl.application.core.config import RecordProcessorConfig
from bioetl.application.core.pipeline_services import PipelineServices
from bioetl.application.core.record_processor import RecordProcessor
from bioetl.composition.factories.storage import StorageContext, StorageFactory
from bioetl.domain.config import TableConfig
from bioetl.domain.error_classifier import ErrorClassifier
from bioetl.infrastructure.checkpoint.local_checkpoint import LocalCheckpoint
from bioetl.infrastructure.locking.memory_lock import MemoryLock
from bioetl.infrastructure.observability.noop_metrics import NoOpMetrics
from bioetl.infrastructure.observability.prometheus_metrics import PrometheusMetrics
from bioetl.infrastructure.quarantine import UnifiedQuarantine
from bioetl.infrastructure.validation import PanderaGoldValidator

if TYPE_CHECKING:
    import pyarrow as pa

    from bioetl.application.core.base import BasePipeline
    from bioetl.application.core.memory_monitor import MemoryConfig
    from bioetl.application.core.shutdown import ShutdownSignal
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.ports import (
        CheckpointPort,
        DataSourcePort,
        DQMonitorPort,
        LockPort,
        LoggerPort,
        MemoryMonitorPort,
        MetricsPort,
        QuarantinePort,
        TracingPort,
    )
    from bioetl.domain.types import RunID
    from bioetl.infrastructure.config import Settings
    from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig


__all__ = [
    "BaseServicesFactory",
    "ServicesBuilder",
]


# =============================================================================
# BaseServicesFactory - Creates PipelineServices
# =============================================================================


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
# ServicesBuilder - Creates infrastructure components
# =============================================================================


class ServicesBuilder:
    """Builder for pipeline infrastructure components."""

    @staticmethod
    def create_checkpoint_manager(
        checkpoint_port: CheckpointPort,
        logger: LoggerPort,
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
        gold_table: str | None,
        silver_write_mode: str,
        gold_write_mode: str,
        on_schema_mismatch: str,
        transform_callback: Any,
        gold_filter_callback: Any,
        gold_transform_callback: Any,
        *,
        strict_gold_validation: bool = False,
        lock_validator: Callable[[], Awaitable[bool]] | None = None,
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
            lock_validator: Async callable that validates lock ownership.
                Returns True if lock is still held, False otherwise.
                Typically LockManager.validate(). If None, lock validation
                is skipped (Safety Guard §4.6).

        Returns:
            Configured RecordProcessor instance
        """
        error_classifier = ErrorClassifier()
        table_config = TableConfig(
            primary_keys=tuple(primary_keys),
            silver_table=silver_table,
            gold_table=gold_table,
            silver_write_mode=silver_write_mode,
            gold_write_mode=gold_write_mode,
            on_schema_mismatch=on_schema_mismatch,  # type: ignore[arg-type]
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
        gold_validator = PanderaGoldValidator(
            gold_schema, strict=strict_gold_validation
        )

        return RecordProcessor(
            services=services,
            error_classifier=error_classifier,
            context=context,
            config=processor_config,
            transform_callback=transform_callback,
            gold_filter_callback=gold_filter_callback,
            gold_transform_callback=gold_transform_callback,
            gold_validator=gold_validator,
            lock_validator=lock_validator,
        )

    @staticmethod
    def create_record_processor_from_pipeline(
        pipeline: BasePipeline,
        silver_schema: pa.Schema | None,
        gold_schema: Any,
        *,
        strict_gold_validation: bool = False,
        lock_validator: Callable[[], Awaitable[bool]] | None = None,
    ) -> RecordProcessor:
        """Create RecordProcessor from pipeline instance.

        Convenience method that extracts configuration from pipeline.

        Args:
            pipeline: Pipeline instance
            silver_schema: PyArrow schema for Silver layer
            gold_schema: Pandera schema for Gold layer
            strict_gold_validation: If True, validation fails when gold_schema is None.
                Default False for backward compatibility.
            lock_validator: Async callable that validates lock ownership.
                Returns True if lock is still held, False otherwise.
                Typically LockManager.validate(). If None, lock validation
                is skipped (Safety Guard §4.6).

        Returns:
            Configured RecordProcessor instance
        """
        # Use injected transformer if available
        transformer = pipeline.transformer
        if transformer is not None:
            transform_cb = transformer.transform
            gold_filter_cb = transformer.should_write_gold
            gold_transform_cb = transformer.transform_for_gold
        else:
            # Fallback for pipelines without explicit transformer (legacy)
            # NOTE: BasePipeline no longer implements these methods.
            # If a subclass does not implement them and has no transformer, this will raise AttributeError.
            # This is intentional to enforce the new architecture (REQ-ARCH-REF-001).
            transform_cb = pipeline.transform_bronze_to_silver

            # Use getattr to avoid MyPy errors if we assume they exist, but runtime will fail if missing.
            # We provide a dummy lambda for safety if methods are strictly missing but user logic
            # handles it elsewhere? No, strict fail is better.
            gold_filter_cb = getattr(
                pipeline, "should_write_gold", lambda _context, record: True
            )

            # Default identity transform if missing
            gold_transform_cb = getattr(
                pipeline,
                "transform_for_gold",
                lambda _context, silver_record: silver_record,
            )

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
            transform_callback=transform_cb,
            gold_filter_callback=gold_filter_cb,
            gold_transform_callback=gold_transform_cb,
            strict_gold_validation=strict_gold_validation,
            lock_validator=lock_validator,
        )

    @staticmethod
    def create_batch_executor_from_pipeline(
        pipeline: BasePipeline,
        silver_schema: pa.Schema | None,
        gold_schema: Any,
        checkpoint_manager: CheckpointManager,
        shutdown_signal: ShutdownSignal,
        *,
        strict_gold_validation: bool = False,
        lock_validator: Callable[[], Awaitable[bool]] | None = None,
        tracer: TracingPort | None = None,
        memory_monitor: MemoryMonitorPort | None = None,
        memory_config: MemoryConfig | None = None,
    ) -> BatchExecutor:
        """Create BatchExecutor from pipeline instance.

        This is the preferred method for creating batch executors as it
        consolidates PipelineExecutor and RecordProcessor into a single component.

        Args:
            pipeline: Pipeline instance.
            silver_schema: PyArrow schema for Silver layer.
            gold_schema: Pandera schema for Gold layer.
            checkpoint_manager: Checkpoint manager instance.
            shutdown_signal: Shutdown signal for graceful termination.
            strict_gold_validation: If True, validation fails when gold_schema is None.
            lock_validator: Async callable that validates lock ownership (Safety Guard §4.6).
            tracer: Optional tracing port for distributed tracing.
            memory_monitor: Optional memory monitor for adaptive batch sizing.
            memory_config: Memory configuration (used if memory_monitor not provided).

        Returns:
            Configured BatchExecutor instance.
        """
        # Extract callbacks from transformer or pipeline
        transformer = pipeline.transformer
        if transformer is not None:
            transform_cb = transformer.transform
            gold_filter_cb = transformer.should_write_gold
            gold_transform_cb = transformer.transform_for_gold
        else:
            transform_cb = pipeline.transform_bronze_to_silver
            gold_filter_cb = getattr(
                pipeline, "should_write_gold", lambda _context, record: True
            )
            gold_transform_cb = getattr(
                pipeline,
                "transform_for_gold",
                lambda _context, silver_record: silver_record,
            )

        # Build configuration
        error_classifier = ErrorClassifier()
        table_config = TableConfig(
            primary_keys=tuple(pipeline.config.primary_keys),
            silver_table=pipeline.config.silver_table,
            gold_table=pipeline.config.gold_table,
            silver_write_mode=pipeline.config.write_mode,
            gold_write_mode=pipeline.config.gold_write_mode,
            on_schema_mismatch=pipeline.config.on_schema_mismatch,
        )

        processor_config = RecordProcessorConfig(
            pipeline_name=pipeline.config.pipeline_name,
            provider=pipeline.config.provider,
            entity_type=pipeline.config.entity_type,
            silver_schema=silver_schema,
            gold_schema=gold_schema,
            dq_config=pipeline.config.dq,
            table_config=table_config,
        )

        # Create Gold validator
        gold_validator = PanderaGoldValidator(gold_schema, strict=strict_gold_validation)

        return BatchExecutor(
            services=pipeline.services,
            context=pipeline.context,
            config=processor_config,
            error_classifier=error_classifier,
            transform_callback=transform_cb,  # type: ignore[arg-type]
            gold_filter_callback=gold_filter_cb,  # type: ignore[arg-type]
            gold_transform_callback=gold_transform_cb,  # type: ignore[arg-type]
            gold_validator=gold_validator,
            checkpoint_manager=checkpoint_manager,
            shutdown_signal=shutdown_signal,
            batch_size=pipeline.config.batch_size,
            checkpoint_interval=pipeline.config.checkpoint_interval,
            tracer=tracer,
            lock_validator=lock_validator,
            memory_monitor=memory_monitor,
            memory_config=memory_config,
        )
