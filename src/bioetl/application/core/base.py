"""Base ETL Pipeline class.

Coordinates the pipeline components.

Refactored per ADR-0005:
- BasePipeline.__init__ accepts exactly 3 params: config, runtime, services
- No self-reference in Executor/Orchestrator
- Legacy API available via from_params() with DeprecationWarning
"""

from __future__ import annotations

import warnings
from abc import ABC, abstractmethod
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from bioetl.application.core.checkpoint_manager import CheckpointManager
from bioetl.application.core.pipeline_config import PipelineConfig, PipelineRuntimeConfig
from bioetl.application.core.pipeline_services import PipelineServices
from bioetl.application.core.quarantine_manager import QuarantineManager
from bioetl.application.core.shutdown import ShutdownSignal
from bioetl.domain.context import PipelineContext
from bioetl.domain.error_classifier import ErrorClassifier
from bioetl.domain.ports import (
    CheckpointPort,
    DataSourcePort,
    LockPort,
    MetricsPort,
    QuarantinePort,
    StoragePort,
)
from bioetl.domain.types import (
    RunID,
    RunType,
    Watermark,
)

if TYPE_CHECKING:
    import structlog

    from bioetl.application.core.executor import PipelineExecutor
    from bioetl.application.core.orchestrator import PipelineOrchestrator


class BasePipeline(ABC):
    """Base class for ETL pipelines.

    This class coordinates pipeline execution by managing configuration,
    services, and decomposed components (orchestrator, executor, etc.).

    Constructor accepts exactly 3 parameters per ADR-0005:
    - config: Static pipeline configuration
    - runtime: Runtime execution parameters
    - services: I/O port dependencies

    Example:
        >>> config = PipelineConfig(...)
        >>> runtime = PipelineRuntimeConfig(run_type=RunType.INCREMENTAL)
        >>> services = PipelineServices(...)
        >>> pipeline = ChEMBLActivityPipeline(config, runtime, services)
        >>> await pipeline.run()
    """

    def __init__(
        self,
        config: PipelineConfig,
        runtime: PipelineRuntimeConfig,
        services: PipelineServices,
    ) -> None:
        """Initialize pipeline with decomposed configuration.

        Args:
            config: Static pipeline configuration (immutable).
            runtime: Runtime execution parameters.
            services: Injected I/O port dependencies.
        """
        # Store decomposed config
        self._config = config
        self._runtime = runtime
        self._services = services

        # Generate run ID
        self._run_id = RunID(uuid4())

        # Bind logger with run context
        self._logger = services.logger.bind(
            run_id=str(self._run_id),
            pipeline=config.pipeline_name,
        )

        # Create context
        self._context = PipelineContext(
            run_id=self._run_id,
            run_type=runtime.run_type,
            logger=self._logger,
        )

        # Shared shutdown signal (no circular deps)
        self._shutdown_signal = ShutdownSignal()

        # Initialize components (lazy - created on first access)
        self._orchestrator: PipelineOrchestrator | None = None
        self._executor: PipelineExecutor | None = None
        self._checkpoint_manager: CheckpointManager | None = None
        self._quarantine_manager: QuarantineManager | None = None
        self._error_classifier: ErrorClassifier | None = None

    # --- Properties for accessing config (read-only) ---

    @property
    def config(self) -> PipelineConfig:
        """Access pipeline configuration."""
        return self._config

    @property
    def runtime(self) -> PipelineRuntimeConfig:
        """Access runtime configuration."""
        return self._runtime

    @property
    def services(self) -> PipelineServices:
        """Access injected services."""
        return self._services

    @property
    def run_id(self) -> RunID:
        """Access run ID."""
        return self._run_id

    @property
    def context(self) -> PipelineContext:
        """Access pipeline context."""
        return self._context

    @property
    def logger(self) -> "structlog.BoundLogger":
        """Access bound logger."""
        return self._logger

    @property
    def shutdown_signal(self) -> ShutdownSignal:
        """Access shutdown signal."""
        return self._shutdown_signal

    # --- Convenience properties (delegate to config) ---

    @property
    def pipeline_name(self) -> str:
        """Pipeline name (from config)."""
        return self._config.pipeline_name

    @property
    def provider(self) -> str:
        """Provider name (from config)."""
        return self._config.provider

    @property
    def entity_type(self) -> str:
        """Entity type (from config)."""
        return self._config.entity_type

    @property
    def run_type(self) -> RunType:
        """Run type (from runtime)."""
        return self._runtime.run_type

    @property
    def resume(self) -> bool:
        """Resume flag (from runtime)."""
        return self._runtime.resume

    @property
    def limit(self) -> int | None:
        """Record limit (from runtime)."""
        return self._runtime.limit

    # --- Convenience properties (delegate to services) ---

    @property
    def data_source(self) -> DataSourcePort:
        """Data source port (from services)."""
        return self._services.data_source

    @property
    def storage(self) -> StoragePort:
        """Storage port (from services)."""
        return self._services.storage

    @property
    def lock(self) -> LockPort:
        """Lock port (from services)."""
        return self._services.lock

    @property
    def checkpoint(self) -> CheckpointPort:
        """Checkpoint port (from services)."""
        return self._services.checkpoint

    @property
    def quarantine(self) -> QuarantinePort:
        """Quarantine port (from services)."""
        return self._services.quarantine

    @property
    def metrics(self) -> MetricsPort:
        """Metrics port (from services)."""
        return self._services.metrics

    # --- Lazy-initialized components ---

    @property
    def error_classifier(self) -> ErrorClassifier:
        """Get error classifier (lazy init)."""
        if self._error_classifier is None:
            self._error_classifier = ErrorClassifier()
        return self._error_classifier

    @property
    def checkpoint_manager(self) -> CheckpointManager:
        """Get checkpoint manager (lazy init)."""
        if self._checkpoint_manager is None:
            self._checkpoint_manager = CheckpointManager(
                checkpoint_port=self._services.checkpoint,
                logger=self._logger,
                pipeline_name=self._config.pipeline_name,
                run_id=self._run_id,
                resume=self._runtime.resume,
                watermark_extractor=lambda record: self.extract_watermark(
                    self._context, record
                ),
            )
        return self._checkpoint_manager

    @property
    def quarantine_manager(self) -> QuarantineManager:
        """Get quarantine manager (lazy init)."""
        if self._quarantine_manager is None:
            self._quarantine_manager = QuarantineManager(
                quarantine_port=self._services.quarantine,
                pipeline_name=self._config.pipeline_name,
            )
        return self._quarantine_manager

    @property
    def executor(self) -> "PipelineExecutor":
        """Get executor (lazy init, no self-reference)."""
        if self._executor is None:
            from bioetl.application.core.executor import PipelineExecutor

            self._executor = PipelineExecutor.from_components(
                data_source=self._services.data_source,
                storage=self._services.storage,
                checkpoint_manager=self.checkpoint_manager,
                quarantine_manager=self.quarantine_manager,
                error_classifier=self.error_classifier,
                context=self._context,
                shutdown_signal=self._shutdown_signal,
                provider=self._config.provider,
                entity_type=self._config.entity_type,
                transform_callback=self.transform_bronze_to_silver,
                gold_filter_callback=self.should_write_gold,
                batch_size=self._config.batch_size,
                checkpoint_interval=self._config.checkpoint_interval,
            )
        return self._executor

    @property
    def orchestrator(self) -> "PipelineOrchestrator":
        """Get orchestrator (lazy init, no self-reference)."""
        if self._orchestrator is None:
            from bioetl.application.core.orchestrator import PipelineOrchestrator

            self._orchestrator = PipelineOrchestrator.from_components(
                config=self._config,
                runtime=self._runtime,
                services=self._services,
                context=self._context,
                executor=self.executor,
                checkpoint_manager=self.checkpoint_manager,
                shutdown_signal=self._shutdown_signal,
                logger=self._logger,
            )
        return self._orchestrator

    # --- Legacy API (deprecated) ---

    @classmethod
    def from_params(
        cls,
        pipeline_name: str,
        provider: str,
        entity_type: str,
        run_type: RunType,
        data_source: DataSourcePort,
        storage: StoragePort,
        lock: LockPort,
        checkpoint: CheckpointPort,
        quarantine: QuarantinePort,
        logger: "structlog.BoundLogger",
        metrics: MetricsPort,
        resume: bool = False,
        limit: int | None = None,
        primary_keys: list[str] | None = None,
        silver_table: str | None = None,
    ) -> "BasePipeline":
        """Create pipeline from individual parameters (DEPRECATED).

        Use __init__(config, runtime, services) instead.
        Will be removed after 2025-01-15.
        """
        warnings.warn(
            "BasePipeline.from_params() is deprecated. "
            "Use BasePipeline(config, runtime, services) instead. "
            "Will be removed after 2025-01-15.",
            DeprecationWarning,
            stacklevel=2,
        )

        config = PipelineConfig(
            pipeline_name=pipeline_name,
            provider=provider,
            entity_type=entity_type,
            primary_keys=primary_keys or [f"{entity_type}_id"],
            silver_table=silver_table or f"{provider}.{entity_type}",
        )
        runtime = PipelineRuntimeConfig(
            run_type=run_type,
            resume=resume,
            limit=limit,
        )
        services = PipelineServices(
            data_source=data_source,
            storage=storage,
            lock=lock,
            checkpoint=checkpoint,
            quarantine=quarantine,
            metrics=metrics,
            logger=logger,
        )
        return cls(config, runtime, services)

    # --- Pipeline execution ---

    async def run(self) -> None:
        """Execute pipeline. Main entry point."""
        await self.orchestrator.run()

    @abstractmethod
    async def transform_bronze_to_silver(
        self, context: PipelineContext, record: dict[str, Any]
    ) -> dict[str, Any] | None:
        """Transform a raw record from Bronze to Silver format.

        Args:
            context: Pipeline execution context.
            record: Raw record from data source.

        Returns:
            Transformed record for Silver layer, or None to skip.
        """
        pass

    def should_write_gold(
        self, _context: PipelineContext, _record: dict[str, Any]
    ) -> bool:
        """Determine if a Silver record should be written to Gold.

        Override in subclass for custom Gold layer filtering logic.
        """
        return True

    def extract_watermark(
        self, _context: PipelineContext, _record: dict[str, Any]
    ) -> Watermark:
        """Extract watermark value from a record.

        Override in subclass for custom watermark extraction logic.
        """
        return Watermark(datetime.now(UTC))


async def run_pipeline_flow(
    pipeline: BasePipeline, logger: "structlog.BoundLogger"
) -> None:
    """Run a pipeline with logging and error handling."""
    try:
        await pipeline.run()
    except Exception as e:
        logger.exception("Pipeline execution failed", error=str(e))
        raise
    finally:
        await pipeline.services.aclose()
