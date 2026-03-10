"""Services Factory.

Consolidated module for creating pipeline infrastructure services.

Contains:
- BaseServicesFactory: Creates PipelineServices with all dependencies
- ServicesBuilder: Creates CheckpointManagerService, RecordProcessor, BatchExecutor

This module follows the DI pattern: all services are created in the
composition layer and injected into pipeline components.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Sequence
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

from bioetl.application.core.batch_executor import BatchExecutor
from bioetl.application.core.batch_metrics import BatchMetricsRecorderService
from bioetl.application.core.batch_tracing import BatchTracingManagerService
from bioetl.application.core.batch_transformer import BatchTransformer
from bioetl.application.core.batch_writer import BatchWriter
from bioetl.application.core.checkpoint_manager import CheckpointManagerService
from bioetl.application.core.config import RecordProcessorConfig
from bioetl.application.core.pipeline_services import PipelineServices
from bioetl.application.core.quarantine_manager import QuarantineManagerService
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
        metrics: MetricsPort | None = None,
        tracer: TracingPort | None = None,
        dq_monitor: DQMonitorPort | None = None,
        metadata_coordinator: MetadataCoordinator | None = None,
        silver_validator: Any = None,  # Any: SilverValidatorPort (optional lazy import)
    ) -> PipelineServices:
        """Create services with injected data source.

        Args:
            settings: Application settings
            logger: Structured logger
            data_source: Data source port implementation
            pipeline_config: Pipeline YAML configuration
            metrics: Optional shared MetricsPort. If not provided, created from settings.
            tracer: Optional tracer (defaults to NoOpTracing if not provided)
            dq_monitor: Optional data quality monitor for anomaly detection
            metadata_coordinator: Optional MetadataCoordinator for centralized
                                metadata creation across Bronze, Silver, Gold.
            silver_validator: Optional SilverValidatorPort for Pandera validation
                in SilverWriter. If None, validation is skipped by storage layer.

        Returns:
            PipelineServices with all dependencies configured
        """
        # Reuse shared metrics when provided so data source/storage write to same port.
        metrics_port = metrics if metrics is not None else cls._create_metrics(settings)

        if (
            settings.env == "prod"
            and not settings.test_mode
            and silver_validator is None
        ):
            raise ValueError(
                "Silver validator is required for production pipelines "
                f"(pipeline={pipeline_config.pipeline_name})"
            )

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

        # Use provided tracer or fallback to NoOpTracing
        # Tracer should be created via bootstrap_tracer_port() for consistent configuration
        if tracer is None:
            from bioetl.domain.ports import NoOpTracing

            tracer = NoOpTracing()

        # Create DQ services if any layer has dq_report enabled
        dq_services = cls._create_dq_services(
            settings=settings,
            pipeline_config=pipeline_config,
            logger=logger,
        )

        # Create MetadataWriter
        from bioetl.infrastructure.storage.metadata_writer import MetadataWriter

        metadata_writer = MetadataWriter(logger=logger)

        return PipelineServices(
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
    ) -> dict[str, Any]:  # Any: heterogeneous DQ service instances
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
    ) -> CheckpointManagerService:
        """Create a configured checkpoint manager."""
        return CheckpointManagerService(
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
        gold_schema: Any,  # Any: Pandera DataFrameModel (no common base type)
        dq_config: Any,  # Any: DQ config type varies per pipeline
        primary_keys: Sequence[str],
        silver_table: str,
        gold_table: str | None,
        silver_write_mode: SilverWriteMode,
        gold_write_mode: GoldWriteMode,
        on_schema_mismatch: Literal["error", "evolve", "ignore"],
        transform_callback: Any,  # Any: callback signature varies (sync/async)
        gold_filter_callback: Any,  # Any: callback signature varies (sync/async)
        gold_transform_callback: Any,  # Any: callback signature varies (sync/async)
        *,
        strict_gold_validation: bool = True,
        lock_validator: Callable[[], Awaitable[bool]] | None = None,
        column_groups: tuple[ColumnGroupConfig, ...] = (),
        scd_config: dict[str, str] | None = None,
    ) -> RecordProcessor:
        """Create a configured record processor with injected collaborators."""
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
            scd_config=scd_config,
        )

        pipeline_label = f"{provider}_{entity_type}"
        batch_metrics = BatchMetricsRecorderService(
            services.metrics,
            pipeline_label,
            context.run_type.value,
        )
        quarantine_manager = QuarantineManagerService(
            quarantine_port=services.quarantine,
            pipeline_name=pipeline_name,
            metrics=services.metrics,
        )
        transformer = BatchTransformer(
            context=context,
            config=processor_config,
            error_classifier=error_classifier,
            quarantine_manager=quarantine_manager,
            batch_metrics=batch_metrics,
            transform_callback=transform_callback,
            gold_filter_callback=gold_filter_callback,
            gold_transform_callback=gold_transform_callback,
        )

        # Create Gold validator from schema (DI pattern)
        # strict mode requires schema to be provided
        gold_validator = PanderaGoldValidator(
            gold_schema, strict=strict_gold_validation
        )
        writer = BatchWriter(
            storage=services.storage,
            context=context,
            config=processor_config,
            gold_validator=gold_validator,
            error_classifier=error_classifier,
            batch_metrics=batch_metrics,
            lock_validator=lock_validator,
        )

        return RecordProcessor(
            context=context,
            batch_metrics=batch_metrics,
            transformer=transformer,
            writer=writer,
            config=processor_config,
            tracer=services.tracing,
        )

    @staticmethod
    def create_record_processor_from_pipeline(
        pipeline: BasePipeline,
        silver_schema: pa.Schema | None,
        gold_schema: Any,  # Any: Pandera DataFrameModel (no common base type)
        *,
        strict_gold_validation: bool = True,
        lock_validator: Callable[[], Awaitable[bool]] | None = None,
    ) -> RecordProcessor:
        """Create a record processor from a pipeline instance."""
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
            primary_keys=pipeline.config.table.primary_keys,
            silver_table=pipeline.config.effective_silver_table,
            gold_table=pipeline.config.effective_gold_table,
            silver_write_mode=pipeline.config.table.silver_write_mode,
            gold_write_mode=pipeline.config.table.gold_write_mode,
            on_schema_mismatch=pipeline.config.table.on_schema_mismatch,
            transform_callback=callbacks.transform,
            gold_filter_callback=callbacks.gold_filter,
            gold_transform_callback=callbacks.gold_transform,
            strict_gold_validation=strict_gold_validation,
            lock_validator=lock_validator,
            column_groups=tuple(pipeline.config.column_groups),
            scd_config=pipeline.config.scd_config,
        )

    @staticmethod
    def create_batch_executor_from_pipeline(
        pipeline: BasePipeline,
        silver_schema: pa.Schema | None,
        gold_schema: Any,  # Any: Pandera DataFrameModel (no common base type)
        checkpoint_manager: CheckpointManagerService,
        shutdown_signal: ShutdownSignal,
        *,
        strict_gold_validation: bool = True,
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
        """Create a batch executor from a pipeline instance."""
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
            scd_config=pipeline.config.scd_config,
        )

        pipeline_label = f"{pipeline.config.provider}_{pipeline.config.entity_type}"
        batch_metrics = BatchMetricsRecorderService(
            pipeline.services.metrics,
            pipeline_label,
            pipeline.context.run_type.value,
        )
        quarantine_manager = QuarantineManagerService(
            quarantine_port=pipeline.services.quarantine,
            pipeline_name=pipeline.config.pipeline_name,
            metrics=pipeline.services.metrics,
        )
        transformer = BatchTransformer(
            context=pipeline.context,
            config=processor_config,
            error_classifier=error_classifier,
            quarantine_manager=quarantine_manager,
            batch_metrics=batch_metrics,
            transform_callback=callbacks.transform,
            gold_filter_callback=gold_filter,
            gold_transform_callback=callbacks.gold_transform,
        )

        # Create Gold validator
        gold_validator = PanderaGoldValidator(
            gold_schema, strict=strict_gold_validation
        )
        writer = BatchWriter(
            storage=pipeline.services.storage,
            context=pipeline.context,
            config=processor_config,
            gold_validator=gold_validator,
            error_classifier=error_classifier,
            batch_metrics=batch_metrics,
            tracer=tracer,
            lock_validator=lock_validator,
        )

        effective_batch_size = (
            pipeline.config.batch_size or BatchExecutor.DEFAULT_BATCH_SIZE
        )
        tracing_manager = BatchTracingManagerService(
            tracer=tracer,
            context=pipeline.context,
            config=processor_config,
            initial_batch_size=effective_batch_size,
            adaptive_sizing_enabled=(
                memory_monitor is not None
                or (memory_config is not None and memory_config.enable_adaptive_sizing)
            ),
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
            batch_metrics=batch_metrics,
            transformer=transformer,
            writer=writer,
            tracing_manager=tracing_manager,
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
