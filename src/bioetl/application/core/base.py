"""Base ETL Pipeline class.

Defines the structure and logic of a pipeline (config, transformations, filters).
Does NOT handle execution orchestration.

Refactored per ADR-005.
"""

from __future__ import annotations

__all__ = ["BasePipeline"]

from abc import ABC
from datetime import UTC, date, datetime
from typing import TYPE_CHECKING, Self

from bioetl.application.core.lifecycle.shutdown import ShutdownSignal
from bioetl.domain.context import PipelineContext
from bioetl.domain.ports import ClockPort

if TYPE_CHECKING:
    from bioetl.application.core.base_transformer import BaseTransformer
    from bioetl.application.core.pipeline_service_protocols import (
        PipelineServicesProtocol,
    )
    from bioetl.domain.config import PipelineConfig, RuntimeConfig
    from bioetl.domain.ports import LoggerPort
    from bioetl.domain.types import BronzeRecord, RunID, RunType, SilverRecord


def _resolve_replay_timestamp_anchor(runtime: RuntimeConfig) -> datetime | None:
    """Resolve one deterministic timestamp anchor for exact replay side effects."""
    if not runtime.exact_replay:
        return None
    if runtime.replay_anchor_date is None:
        return datetime(1970, 1, 1, tzinfo=UTC)
    replay_date = date.fromisoformat(runtime.replay_anchor_date)
    return datetime.combine(replay_date, datetime.min.time(), tzinfo=UTC)


class BasePipeline(ABC):  # noqa: B024
    """Base class for ETL pipelines.

    Acts as a container for:
    - Configuration (Static & Runtime)
    - Services (Ports)
    - Business Logic (Transformations, Filtering)

    It does NOT orchestrate execution. See PipelineRunner for execution logic.

    Transformers MUST be injected via DI from GenericPipelineFactory.
    BasePipeline does NOT create transformers internally.
    """

    @classmethod
    def create(
        cls,
        run_id: RunID,
        runtime: RuntimeConfig,
        services: PipelineServicesProtocol,
        config: PipelineConfig,
        shutdown_signal: ShutdownSignal,
        started_at: datetime | None = None,
        clock: ClockPort | None = None,
        transformer: BaseTransformer | None = None,
    ) -> Self:
        """Create pipeline instance.

        Default factory method. Subclasses can override if custom initialization is needed.

        Args:
            run_id: Unique identifier for this pipeline run (from CLI/orchestrator).
            runtime: Runtime configuration.
            services: Injected services (ports).
            config: Pipeline configuration.
            shutdown_signal: Injected shutdown signal instance.
            started_at: Explicit runtime anchor captured by the caller.
            clock: Optional replay-safe clock seam used when ``started_at`` is
                omitted.
            transformer: Injected transformer for Bronze→Silver transformation (DI).
                If provided, the pipeline will use this transformer instead of
                creating one internally. This is the preferred DI approach.

        Returns:
            Newly created Self instance.
        """
        return cls(
            config,
            runtime,
            services,
            run_id,
            shutdown_signal=shutdown_signal,
            started_at=started_at,
            clock=clock,
            transformer=transformer,
        )

    def __init__(
        self,
        config: PipelineConfig,
        runtime: RuntimeConfig,
        services: PipelineServicesProtocol,
        run_id: RunID,
        shutdown_signal: ShutdownSignal,
        started_at: datetime | None = None,
        clock: ClockPort | None = None,
        transformer: BaseTransformer | None = None,
    ) -> None:
        """Initialize pipeline definition.

        Args:
            config: Pipeline configuration.
            runtime: Runtime configuration.
            services: Injected services (ports).
            run_id: Unique identifier for this pipeline run.
                    MUST be passed from CLI/orchestrator to ensure consistency.
            shutdown_signal: Injected shutdown signal instance for graceful stop.
            started_at: Explicit runtime anchor captured by the caller.
            clock: Optional replay-safe clock seam used when ``started_at`` is
                omitted.
            transformer: Injected transformer for Bronze→Silver transformation.
                MUST be provided via DI from GenericPipelineFactory.
                If None, transform_bronze_to_silver() will raise NotImplementedError.

        """
        self._config = config
        self._runtime = runtime
        self._services = services
        self._run_id = run_id
        # Transformer MUST be injected via DI - no fallback creation
        self._transformer = transformer
        self._logger = services.logger.bind(
            run_id=str(self._run_id),
            pipeline=config.pipeline_name,
        )
        replay_timestamp_anchor = _resolve_replay_timestamp_anchor(runtime)
        # Use factory method to ensure started_at is set (single source of time)
        self._context = PipelineContext.create(
            run_id=self._run_id,
            run_type=runtime.run_type,
            logger=self._logger,
            started_at=started_at,
            clock=clock,
            replay_timestamp_anchor=replay_timestamp_anchor,
            pipeline_name=config.pipeline_name,
            workflow_id=runtime.workflow_id,
        )
        self._shutdown_signal = shutdown_signal

    @property
    def config(self) -> PipelineConfig:
        """Access pipeline configuration."""
        return self._config

    @property
    def runtime(self) -> RuntimeConfig:
        """Access runtime configuration."""
        return self._runtime

    @property
    def services(self) -> PipelineServicesProtocol:
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
    def logger(self) -> LoggerPort:
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

    @property
    def transformer(self) -> BaseTransformer | None:
        """Access the injected transformer."""
        return self._transformer

    # --- Logic Methods (to be used by Executor) ---

    async def transform_bronze_to_silver(
        self, context: PipelineContext, record: BronzeRecord, index: int = 0
    ) -> SilverRecord | None:
        """Transform a raw record from Bronze to Silver format.

        If a transformer was injected via DI, delegates to it.
        Otherwise, subclasses MUST override this method.

        Args:
            context: Pipeline context with run_id, run_type, logger.
            record: Raw Bronze record from data source.
            index: Sequential index of the record in the pipeline run.

        Returns:
            SilverRecord if transformation successful, None if skipped.

        Raises:
            NotImplementedError: If no transformer is available and method not overridden.

        """
        if self._transformer is not None:
            return await self._transformer.transform(context, record, index)
        raise NotImplementedError(
            f"{self.__class__.__name__} must either receive a transformer via DI "
            "or override transform_bronze_to_silver()"
        )
