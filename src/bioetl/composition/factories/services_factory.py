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
from typing import TYPE_CHECKING, Any, Literal

from bioetl.application.core.batch_executor import BatchExecutor
from bioetl.application.core.checkpoint_manager import CheckpointManager
from bioetl.application.core.config import RecordProcessorConfig
from bioetl.application.core.pipeline_services import PipelineServices
from bioetl.application.core.record_processor import RecordProcessor
from bioetl.composition.bootstrap_contexts import PipelineCallbacksContext
from bioetl.composition.factories.dq_factory import DQServicesFactory
from bioetl.composition.factories.storage import StorageContext, StorageFactory
from bioetl.domain.composite.config import ColumnGroupConfig
from bioetl.domain.config import TableConfig
from bioetl.domain.error_classifier import ErrorClassifier
from bioetl.domain.medallion import GoldWriteMode, LoadingStrategy, SilverWriteMode
from bioetl.domain.ports import NoOpMetrics
from bioetl.infrastructure.checkpoint.local_checkpoint import LocalCheckpoint
from bioetl.infrastructure.locking.memory_lock import MemoryLock
from bioetl.infrastructure.observability.prometheus_metrics import PrometheusMetrics
from bioetl.infrastructure.quarantine import UnifiedQuarantine
from bioetl.infrastructure.validation import PanderaGoldValidator

if TYPE_CHECKING:
    import pyarrow as pa

    from bioetl.application.core.base import BasePipeline
    from bioetl.application.core.shutdown import ShutdownSignal
    from bioetl.composition.services.metadata_coordinator import MetadataCoordinator
    from bioetl.domain.config import MemoryConfig
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.ports import (
        CheckpointPort,
        DataNormalizationPort,
        DataSourcePort,
        DQMonitorPort,
        LockPort,
        LoggerPort,
        MemoryMonitorPort,
        MetricsPort,
        QuarantinePort,
        TracingPort,
    )
    from bioetl.domain.services import DataNormalizationConfig
    from bioetl.domain.types import RunID
    from bioetl.infrastructure.config import Settings
    from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig


__all__ = [
    "BaseServicesFactory",
    "PipelineCallbacksContext",
    "ServicesBuilder",
    "create_data_normalization_service",
    "extract_pipeline_callbacks",
]


# =============================================================================
# Helper Functions
# =============================================================================


def extract_pipeline_callbacks(
    pipeline: BasePipeline,
) -> PipelineCallbacksContext:
    """Extract transformation callbacks from pipeline.

    Extracts callbacks from the pipeline's transformer if available,
    otherwise falls back to pipeline methods (legacy support).

    Args:
        pipeline: Pipeline instance with transformer or legacy methods.

    Returns:
        PipelineCallbacksContext with transform, gold_filter, and gold_transform callbacks.

    Raises:
        AttributeError: If pipeline has no transformer and doesn't implement
            transform_bronze_to_silver (enforces REQ-ARCH-REF-001).
    """
    transformer = pipeline.transformer
    if transformer is not None:
        return PipelineCallbacksContext(
            transform=transformer.transform,
            gold_filter=transformer.should_write_gold,
            gold_transform=transformer.transform_for_gold,
        )

    # Fallback for pipelines without explicit transformer (legacy)
    # NOTE: BasePipeline no longer implements these methods.
    # If a subclass does not implement them and has no transformer, this will raise AttributeError.
    # This is intentional to enforce the new architecture (REQ-ARCH-REF-001).
    transform_cb = pipeline.transform_bronze_to_silver
    gold_filter_cb = getattr(
        pipeline, "should_write_gold", lambda _context, record: True
    )
    gold_transform_cb = getattr(
        pipeline,
        "transform_for_gold",
        lambda _context, silver_record: silver_record,
    )
    return PipelineCallbacksContext(
        transform=transform_cb,
        gold_filter=gold_filter_cb,
        gold_transform=gold_transform_cb,
    )


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
        metadata_coordinator: MetadataCoordinator | None = None,
        silver_validator: Any = None,
    ) -> PipelineServices:
        """Create services with injected data source.

        Args:
            settings: Application settings
            logger: Structured logger
            data_source: Data source port implementation
            pipeline_config: Pipeline YAML configuration
            tracer: Optional tracer (defaults to NoOpTracing if not provided)
            dq_monitor: Optional data quality monitor for anomaly detection
            metadata_coordinator: Optional MetadataCoordinator for centralized
                                metadata creation across Bronze, Silver, Gold.
            silver_validator: Optional SilverValidatorPort for Pandera validation
                in SilverWriter. If None, SilverWriter uses NoOpSilverValidator.

        Returns:
            PipelineServices with all dependencies configured
        """
        # Create metrics first so it can be passed to storage factory
        metrics = cls._create_metrics(settings)

        storage_ctx = StorageFactory.create(
            settings,
            pipeline_config,
            logger,
            metrics=metrics,
            metadata_coordinator=metadata_coordinator,
            silver_validator=silver_validator,
        )

        lock = cls._create_lock()
        checkpoint = cls._create_checkpoint(storage_ctx)
        quarantine = cls._create_quarantine(settings)

        # Use provided tracer or fallback to NoOpTracing
        # Tracer should be created via bootstrap_tracer() for consistent configuration
        if tracer is None:
            from bioetl.domain.ports import NoOpTracing

            tracer = NoOpTracing()

        # Create DQ services if any layer has dq_report enabled
        dq_services = cls._create_dq_services(
            settings=settings,
            pipeline_config=pipeline_config,
            logger=logger,
        )

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
            bronze_dq_analyzer=dq_services.get("bronze_analyzer"),
            silver_dq_analyzer=dq_services.get("silver_analyzer"),
            gold_dq_analyzer=dq_services.get("gold_analyzer"),
            dq_report_writer=dq_services.get("report_writer"),
            dq_report_service=dq_services.get("report_service"),
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
    def _create_quarantine(settings: Settings) -> QuarantinePort:
        """Create unified quarantine storage independent of entity paths.

        Quarantine storage is centralized at data_dir/quarantine to avoid
        coupling with Silver path structure and simplify management.
        """
        return UnifiedQuarantine(
            base_path=str(settings.quarantine_path),
        )

    @staticmethod
    def _create_metrics(settings: Settings) -> MetricsPort:
        if settings.metrics_enabled:
            return PrometheusMetrics()
        return NoOpMetrics()

    @staticmethod
    def _get_output_root(
        settings: Settings,
        pipeline_config: PipelineYamlConfig,
    ) -> Path:
        """Derive output root from pipeline config or fall back to settings.

        DQ reports should be written alongside the data. This method extracts
        the output root from the bronze sink path configuration when available.

        For paths like 'data/output/bronze/chembl/activity':
        - parent = 'data/output/bronze/chembl'
        - parent.parent = 'data/output/bronze'
        - parent.parent.parent = 'data/output' (output root)

        Args:
            settings: Application settings.
            pipeline_config: Pipeline YAML configuration.

        Returns:
            Path to the output root directory.
        """
        bronze_config = pipeline_config.sink.get("bronze")

        # Use bronze path from config if available and not in test mode
        if not settings.test_mode and bronze_config and bronze_config.path:
            bronze_path = Path(bronze_config.path)
            # Go up 3 levels: bronze/provider/entity -> output root
            # e.g., data/output/bronze/chembl/activity -> data/output
            return bronze_path.parent.parent.parent

        # Fall back to settings data_dir
        return settings.data_dir

    @classmethod
    def _create_dq_services(
        cls,
        settings: Settings,
        pipeline_config: PipelineYamlConfig,
        logger: LoggerPort,
    ) -> dict[str, Any]:
        """Create DQ services if any layer has dq_report enabled.

        Args:
            settings: Application settings.
            pipeline_config: Pipeline YAML configuration.
            logger: Structured logger.

        Returns:
            Dictionary with DQ services (empty if none enabled).
        """
        # Check if any DQ report is enabled in sink config
        dq_enabled = cls._is_dq_report_enabled(pipeline_config)

        if not dq_enabled:
            return {}

        # Create DQ analyzers
        bronze_analyzer = DQServicesFactory.create_bronze_analyzer()
        silver_analyzer = DQServicesFactory.create_silver_analyzer()
        gold_analyzer = DQServicesFactory.create_gold_analyzer()

        # DQ reports are written to dedicated reports/dq/ directory
        output_root = cls._get_output_root(settings, pipeline_config)
        dq_reports_path = output_root / "reports" / "dq"
        # Get flat_structure from sink config (use Silver as primary)
        flat_structure = cls._get_flat_structure(pipeline_config)
        report_writer = DQServicesFactory.create_report_writer(
            base_path=dq_reports_path,
            logger=logger,
            flat_structure=flat_structure,
        )

        # Create DQ report service
        from bioetl.application.services.dq_report_service import DQReportService

        report_service = DQReportService(
            logger=logger,
            bronze_analyzer=bronze_analyzer,
            silver_analyzer=silver_analyzer,
            gold_analyzer=gold_analyzer,
            report_writer=report_writer,
        )

        return {
            "bronze_analyzer": bronze_analyzer,
            "silver_analyzer": silver_analyzer,
            "gold_analyzer": gold_analyzer,
            "report_writer": report_writer,
            "report_service": report_service,
        }

    @staticmethod
    def _is_dq_report_enabled(config: PipelineYamlConfig) -> bool:
        """Check if any DQ report is enabled in pipeline config.

        Args:
            config: Pipeline YAML configuration.

        Returns:
            True if any layer has dq_report.enabled = true.
        """
        sink = config.sink

        # Check each layer for dq_report.enabled
        for layer_name in ("bronze", "silver", "gold"):
            layer_config = sink.get(layer_name)
            if layer_config and layer_config.dq_report.enabled:
                return True

        return False

    @staticmethod
    def _get_flat_structure(config: PipelineYamlConfig) -> bool:
        """Get flat_structure setting from pipeline config.

        Checks Silver and Gold layers for flat_structure setting.
        Returns True if either layer has flat_structure enabled.

        Args:
            config: Pipeline YAML configuration.

        Returns:
            True if flat_structure is enabled for any layer.
        """
        sink = config.sink

        # Check Silver and Gold for flat_structure
        for layer_name in ("silver", "gold"):
            layer_config = sink.get(layer_name)
            if layer_config and getattr(layer_config, "flat_structure", False):
                return True

        return False


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
        *,
        loading_strategy: LoadingStrategy | None = None,
    ) -> CheckpointManager:
        """Create configured CheckpointManager.

        Args:
            checkpoint_port: Checkpoint storage port
            logger: Structured logger
            pipeline_name: Name of the pipeline
            run_id: Unique run identifier
            resume: Whether to resume from previous checkpoint
            loading_strategy: Loading strategy (ADR-031).
                FULL_SCAN_ONLY disables checkpoint resume.

        Returns:
            Configured CheckpointManager instance
        """
        return CheckpointManager(
            checkpoint_port=checkpoint_port,
            logger=logger,
            pipeline_name=pipeline_name,
            run_id=run_id,
            resume=resume,
            loading_strategy=loading_strategy,
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
        silver_write_mode: SilverWriteMode | str,
        gold_write_mode: GoldWriteMode | str,
        on_schema_mismatch: Literal["error", "evolve", "ignore"],
        transform_callback: Any,
        gold_filter_callback: Any,
        gold_transform_callback: Any,
        *,
        strict_gold_validation: bool = False,
        lock_validator: Callable[[], Awaitable[bool]] | None = None,
        column_groups: tuple[ColumnGroupConfig, ...] = (),
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
            column_groups=column_groups,
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
        callbacks = extract_pipeline_callbacks(pipeline)

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
            transform_callback=callbacks.transform,
            gold_filter_callback=callbacks.gold_filter,
            gold_transform_callback=callbacks.gold_transform,
            strict_gold_validation=strict_gold_validation,
            lock_validator=lock_validator,
            column_groups=tuple(pipeline.config.column_groups),
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
        # DQ report output paths (for flat_structure support)
        bronze_output_path: str | None = None,
        silver_output_path: str | None = None,
        gold_output_path: str | None = None,
        flat_structure: bool = False,
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
        callbacks = extract_pipeline_callbacks(pipeline)
        skip = pipeline.runtime.skip_gold
        gold_filter = (lambda _c, _r: False) if skip else callbacks.gold_filter

        # Build configuration
        error_classifier = ErrorClassifier()

        processor_config = RecordProcessorConfig(
            pipeline_name=pipeline.config.pipeline_name,
            provider=pipeline.config.provider,
            entity_type=pipeline.config.entity_type,
            silver_schema=silver_schema,
            gold_schema=gold_schema,
            dq_config=pipeline.config.dq,
            table_config=pipeline.config.table,
            # DQ report output paths for flat_structure support
            bronze_output_path=bronze_output_path,
            silver_output_path=silver_output_path,
            gold_output_path=gold_output_path,
            flat_structure=flat_structure,
            column_groups=pipeline.config.column_groups,
        )

        # Create Gold validator
        gold_validator = PanderaGoldValidator(
            gold_schema, strict=strict_gold_validation
        )

        return BatchExecutor(
            services=pipeline.services,
            context=pipeline.context,
            config=processor_config,
            error_classifier=error_classifier,
            transform_callback=callbacks.transform,
            gold_filter_callback=gold_filter,
            gold_transform_callback=callbacks.gold_transform,
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


# =============================================================================
# Domain Service Factory Functions
# =============================================================================


def create_data_normalization_service(
    config: DataNormalizationConfig | None = None,
) -> DataNormalizationPort:
    """Create DataNormalizationService with optional configuration.

    Factory function for creating DataNormalizationService instances.
    Uses default configuration if not provided.

    Args:
        config: Optional configuration for normalization behavior.

    Returns:
        DataNormalizationPort implementation (DefaultDataNormalizationService).

    Example:
        >>> from bioetl.composition.factories import create_data_normalization_service
        >>> normalizer = create_data_normalization_service()
        >>> normalizer.normalize_doi("10.1038/NATURE12373")
        '10.1038/nature12373'

        >>> from bioetl.domain.services import DataNormalizationConfig
        >>> config = DataNormalizationConfig(min_publication_year=1900)
        >>> normalizer = create_data_normalization_service(config)
    """
    from bioetl.domain.services import (
        DataNormalizationConfig,
        DefaultDataNormalizationService,
    )

    if config is None:
        config = DataNormalizationConfig()
    return DefaultDataNormalizationService(config=config)
