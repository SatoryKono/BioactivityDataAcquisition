"""Base ETL Pipeline class.

Coordinates the pipeline components.
"""

from __future__ import annotations

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


class BasePipeline(ABC):
    """
    Base class for ETL pipelines.

    This class is a container for the pipeline's configuration, services,
    and application-layer components (like the executor). It does not
    concern itself with how the pipeline is run.
    """

    def __init__(
        self,
        config: PipelineConfig,
        runtime: PipelineRuntimeConfig,
        services: PipelineServices,
    ) -> None:
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

        # Lazy-initialized components
        self._executor: PipelineExecutor | None = None
        self._checkpoint_manager: CheckpointManager | None = None
        self._quarantine_manager: QuarantineManager | None = None
        self._error_classifier: ErrorClassifier | None = None

    # --- Properties for accessing config, services, and context ---

    @property
    def config(self) -> PipelineConfig:
        return self._config

    @property
    def runtime(self) -> PipelineRuntimeConfig:
        return self._runtime

    @property
    def services(self) -> PipelineServices:
        return self._services

    @property
    def run_id(self) -> RunID:
        return self._run_id

    @property
    def context(self) -> PipelineContext:
        return self._context

    @property
    def logger(self) -> "structlog.BoundLogger":
        return self._logger

    @property
    def shutdown_signal(self) -> ShutdownSignal:
        return self._shutdown_signal

    # --- Lazy-initialized components ---

    @property
    def error_classifier(self) -> ErrorClassifier:
        if self._error_classifier is None:
            self._error_classifier = ErrorClassifier()
        return self._error_classifier

    @property
    def checkpoint_manager(self) -> CheckpointManager:
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
        if self._quarantine_manager is None:
            self._quarantine_manager = QuarantineManager(
                quarantine_port=self._services.quarantine,
                pipeline_name=self._config.pipeline_name,
            )
        return self._quarantine_manager

    @property
    def executor(self) -> "PipelineExecutor":
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

    # --- Abstract methods for subclasses ---

    @abstractmethod
    async def transform_bronze_to_silver(
        self, context: PipelineContext, record: dict[str, Any]
    ) -> dict[str, Any] | None:
        pass

    def should_write_gold(
        self, _context: PipelineContext, _record: dict[str, Any]
    ) -> bool:
        return True

    def extract_watermark(
        self, _context: PipelineContext, _record: dict[str, Any]
    ) -> Watermark:
        return Watermark(datetime.now(UTC))
