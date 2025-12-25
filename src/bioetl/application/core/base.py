"""Base ETL Pipeline class.

Defines the structure and logic of a pipeline (config, transformations, filters).
Does NOT handle execution orchestration.

Refactored per ADR-0005.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, ClassVar, Self

from bioetl.application.core.shutdown import ShutdownSignal
from bioetl.domain.context import PipelineContext

if TYPE_CHECKING:
    import structlog

    from bioetl.application.core.pipeline_services import PipelineServices
    from bioetl.domain.config import PipelineConfig, RuntimeConfig
    from bioetl.domain.types import BronzeRecord, RunID, RunType, SilverRecord


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
        run_id: RunID,
        runtime: RuntimeConfig,
        services: PipelineServices,
        config: PipelineConfig,
    ) -> Self:
        """Create pipeline instance.

        Default factory method. Subclasses can override if custom initialization is needed.

        Args:
            run_id: Unique identifier for this pipeline run (from CLI/orchestrator).
            runtime: Runtime configuration.
            services: Injected services (ports).
            config: Pipeline configuration.

        """
        return cls(config, runtime, services, run_id)

    def __init__(
        self,
        config: PipelineConfig,
        runtime: RuntimeConfig,
        services: PipelineServices,
        run_id: RunID,
    ) -> None:
        """Initialize pipeline definition.

        Args:
            config: Pipeline configuration.
            runtime: Runtime configuration.
            services: Injected services (ports).
            run_id: Unique identifier for this pipeline run.
                    MUST be passed from CLI/orchestrator to ensure consistency.

        """
        self._config = config
        self._runtime = runtime
        self._services = services
        self._run_id = run_id
        self._logger = services.logger.bind(
            run_id=str(self._run_id),
            pipeline=config.pipeline_name,
        )
        # Use factory method to ensure started_at is set (single source of time)
        self._context = PipelineContext.create(
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

    # Fields to exclude from Gold layer (JSON strings retained only in Silver)
    GOLD_EXCLUDE_FIELDS: ClassVar[frozenset[str]] = frozenset({
        # Molecule JSON fields (Silver forensic only)
        "molecule_hierarchy",
        "molecule_properties",
        "molecule_structures",
        "molecule_synonyms",
        "cross_references",
        "atc_classifications",
        # Internal metadata fields (Silver only)
        "entity_id",
        "content_hash",
        "_run_type",
        "_source_batch_id",
    })

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

    def transform_for_gold(
        self, _context: PipelineContext, silver_record: dict[str, Any]
    ) -> dict[str, Any]:
        """Transform Silver record for Gold layer.

        Removes JSON string fields that are retained only in Silver for forensic purposes.
        Subclasses can override for custom Gold transformations.

        Args:
            _context: Pipeline context (unused in base implementation).
            silver_record: Silver record to transform.

        Returns:
            Record suitable for Gold layer (flat fields only).

        """
        return {
            k: v for k, v in silver_record.items() if k not in self.GOLD_EXCLUDE_FIELDS
        }
