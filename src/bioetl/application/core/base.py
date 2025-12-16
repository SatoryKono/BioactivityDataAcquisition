"""Base ETL Pipeline class.

Coordinates the pipeline components.

NOTE: This module is being refactored per ADR-0005.
The legacy constructor is deprecated. Use `from_config()` instead.
"""

from __future__ import annotations

import warnings
from abc import ABC, abstractmethod
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from bioetl.application.core.checkpoint_manager import CheckpointManager
from bioetl.application.core.executor import PipelineExecutor
from bioetl.application.core.lock_manager import LockManager
from bioetl.application.core.orchestrator import PipelineOrchestrator
from bioetl.application.core.pipeline_config import PipelineConfig, PipelineRuntimeConfig
from bioetl.application.core.pipeline_services import PipelineServices
from bioetl.application.core.quarantine_manager import QuarantineManager
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


class BasePipeline(ABC):
    """Base class for ETL pipelines.

    This class coordinates pipeline execution by managing configuration,
    services, and decomposed components (orchestrator, executor, etc.).

    There are two ways to create a pipeline:

    1. **New API (Recommended)**: Use `from_config()` classmethod
       ```python
       pipeline = MyPipeline.from_config(
           config=PipelineConfig(...),
           runtime=PipelineRuntimeConfig(...),
           services=PipelineServices(...),
       )
       ```

    2. **Legacy API (Deprecated)**: Direct constructor with 13 parameters
       ```python
       pipeline = MyPipeline(
           pipeline_name="...",
           provider="...",
           # ... 10 more parameters
       )
       ```

    The legacy API will be removed after 2025-01-15.
    """

    # Store decomposed config for new API
    _config: PipelineConfig | None = None
    _runtime: PipelineRuntimeConfig | None = None
    _services: PipelineServices | None = None

    def __init__(
        self,
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
        *,
        # Hidden params for new API (set by from_config)
        _config: PipelineConfig | None = None,
        _runtime: PipelineRuntimeConfig | None = None,
        _services: PipelineServices | None = None,
        _skip_deprecation_warning: bool = False,
    ) -> None:
        """Initialize pipeline with legacy parameters.

        DEPRECATED: Use `from_config()` classmethod instead.
        This constructor will be removed after 2025-01-15.
        """
        # Emit deprecation warning unless called from from_config()
        if not _skip_deprecation_warning:
            warnings.warn(
                "Direct BasePipeline constructor is deprecated. "
                "Use MyPipeline.from_config(config, runtime, services) instead. "
                "Will be removed after 2025-01-15.",
                DeprecationWarning,
                stacklevel=2,
            )

        # Store decomposed structures if provided
        self._config = _config
        self._runtime = _runtime
        self._services = _services

        # Legacy attributes (for backward compatibility)
        self.pipeline_name = pipeline_name
        self.provider = provider
        self.entity_type = entity_type
        self.run_type = run_type
        self.data_source = data_source
        self.storage = storage
        self.lock = lock
        self.checkpoint = checkpoint
        self.quarantine = quarantine
        self.metrics = metrics
        self.resume = resume
        self.limit = limit
        self.run_id = RunID(uuid4())
        self.logger = logger.bind(run_id=str(self.run_id))

        self.context = PipelineContext(
            run_id=self.run_id,
            run_type=self.run_type,
            logger=self.logger,
        )

        # Decomposed components
        self.orchestrator = PipelineOrchestrator(self)
        self.executor = PipelineExecutor(self)
        self.lock_manager = LockManager.from_pipeline(self)
        self.checkpoint_manager = CheckpointManager(
            checkpoint_port=self.checkpoint,
            logger=self.logger,
            pipeline_name=self.pipeline_name,
            run_id=self.run_id,
            resume=self.resume,
            watermark_extractor=lambda record: self.extract_watermark(
                self.context, record
            ),
        )
        self.error_classifier = ErrorClassifier()
        self.quarantine_manager = QuarantineManager(
            quarantine_port=self.quarantine, pipeline_name=self.pipeline_name
        )

    @classmethod
    def from_config(
        cls,
        config: PipelineConfig,
        runtime: PipelineRuntimeConfig,
        services: PipelineServices,
    ) -> "BasePipeline":
        """Create pipeline from decomposed configuration.

        This is the recommended way to create pipelines.

        Args:
            config: Static pipeline configuration (immutable).
            runtime: Runtime execution parameters.
            services: Injected I/O port dependencies.

        Returns:
            Configured pipeline instance ready for execution.

        Example:
            >>> config = PipelineConfig(
            ...     pipeline_name="chembl_activity",
            ...     provider="chembl",
            ...     entity_type="activity",
            ...     primary_keys=["activity_id"],
            ...     silver_table="chembl_activity",
            ... )
            >>> runtime = PipelineRuntimeConfig(
            ...     run_type=RunType.INCREMENTAL,
            ...     resume=True,
            ... )
            >>> services = PipelineServices(
            ...     data_source=chembl_client,
            ...     storage=delta_storage,
            ...     lock=redis_lock,
            ...     checkpoint=s3_checkpoint,
            ...     quarantine=unified_quarantine,
            ...     metrics=prometheus_metrics,
            ...     logger=logger,
            ... )
            >>> pipeline = ChEMBLActivityPipeline.from_config(
            ...     config, runtime, services
            ... )
        """
        return cls(
            pipeline_name=config.pipeline_name,
            provider=config.provider,
            entity_type=config.entity_type,
            run_type=runtime.run_type,
            data_source=services.data_source,
            storage=services.storage,
            lock=services.lock,
            checkpoint=services.checkpoint,
            quarantine=services.quarantine,
            logger=services.logger,
            metrics=services.metrics,
            resume=runtime.resume,
            limit=runtime.limit,
            # Pass decomposed structures for future use
            _config=config,
            _runtime=runtime,
            _services=services,
            _skip_deprecation_warning=True,
        )

    # --- Properties for accessing decomposed config (optional) ---

    @property
    def config(self) -> PipelineConfig | None:
        """Access pipeline configuration (None if created via legacy API)."""
        return self._config

    @property
    def runtime_config(self) -> PipelineRuntimeConfig | None:
        """Access runtime configuration (None if created via legacy API)."""
        return self._runtime

    @property
    def services(self) -> PipelineServices | None:
        """Access injected services (None if created via legacy API)."""
        return self._services

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

        Args:
            _context: Pipeline execution context.
            _record: Transformed Silver record.

        Returns:
            True if record should be written to Gold layer.
        """
        return True

    def extract_watermark(
        self, _context: PipelineContext, _record: dict[str, Any]
    ) -> Watermark:
        """Extract watermark value from a record.

        Override in subclass for custom watermark extraction logic.

        Args:
            _context: Pipeline execution context.
            _record: Record to extract watermark from.

        Returns:
            Watermark value for checkpoint tracking.
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
        if pipeline.services:
            await pipeline.services.aclose()
