"""Base ETL Pipeline class.

Defines the structure and logic of a pipeline (config, transformations, filters).
Does NOT handle execution orchestration.

Refactored per ADR-0005.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Self
from uuid import uuid4

from bioetl.application.core.shutdown import ShutdownSignal
from bioetl.domain.context import PipelineContext
from bioetl.domain.types import BronzeRecord, RunID, RunType, SilverRecord

if TYPE_CHECKING:
    import structlog

    from bioetl.application.core.pipeline_services import PipelineServices
    from bioetl.domain.config import PipelineConfig, RuntimeConfig


class BasePipeline(ABC):
    """Base class for ETL pipelines.

    Acts as a container for:
    - Configuration (Static & Runtime)
    - Services (Ports)
    - Business Logic (Transformations, Filtering)

    It does NOT orchestrate execution. See PipelineRunner for execution logic.
    """

    @classmethod
    def create(
        cls,
        runtime: RuntimeConfig,
        services: PipelineServices,
        config: PipelineConfig,
    ) -> Self:
        """Create pipeline instance.

        Default factory method. Subclasses can override if custom initialization is needed.
        """
        return cls(config, runtime, services)

    def __init__(
        self,
        config: PipelineConfig,
        runtime: RuntimeConfig,
        services: PipelineServices,
    ) -> None:
        """Initialize pipeline definition."""
        self._config = config
        self._runtime = runtime
        self._services = services
        self._run_id = RunID(uuid4())
        self._logger = services.logger.bind(
            run_id=str(self._run_id),
            pipeline=config.pipeline_name,
        )
        self._context = PipelineContext(
            run_id=self._run_id,
            run_type=runtime.run_type,
            logger=self._logger,
        )
        self._shutdown_signal = ShutdownSignal()

    # --- Properties for accessing config (read-only) ---

    @property
    def config(self) -> PipelineConfig:
        """Access pipeline configuration."""
        return self._config

    @property
    def runtime(self) -> RuntimeConfig:
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
    def logger(self) -> structlog.BoundLogger:
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

    # --- Logic Methods (to be used by Executor) ---

    @abstractmethod
    async def transform_bronze_to_silver(
        self, context: PipelineContext, record: BronzeRecord
    ) -> SilverRecord | None:
        """Transform a raw record from Bronze to Silver format."""
        pass

    def should_write_gold(
        self, _context: PipelineContext, record: dict[str, Any]
    ) -> bool:
        """Determine if a Silver record should be written to Gold.

        Uses gold_filters from config if configured, otherwise passes all records.
        Subclasses can override for custom filtering logic.

        Args:
            _context: Pipeline context (unused in base implementation).
            record: Silver record to evaluate.

        Returns:
            True if record should be written to Gold layer.
        """
        gold_filters = self._config.gold_filters
        if gold_filters is None or gold_filters.is_empty():
            return True
        return gold_filters.should_include(record)
