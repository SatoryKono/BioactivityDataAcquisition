"""Base ETL Pipeline class.

Coordinates the pipeline components.
"""

from abc import ABC, abstractmethod
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from bioetl.application.core.checkpoint_manager import CheckpointManager
from bioetl.application.core.executor import PipelineExecutor
from bioetl.application.core.lock_manager import LockManager
from bioetl.application.core.orchestrator import PipelineOrchestrator
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
    """Base class for ETL pipelines."""

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
    ) -> None:
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
        self.lock_manager = LockManager(self)
        self.checkpoint_manager = CheckpointManager(
            checkpoint_port=self.checkpoint,
            logger=self.logger,
            pipeline_name=self.pipeline_name,
            run_id=self.run_id,
            resume=self.resume,
            watermark_extractor=lambda record: self.extract_watermark(self.context, record),
        )
        self.error_classifier = ErrorClassifier()
        self.quarantine_manager = QuarantineManager(self)

    async def run(self) -> None:
        """Execute pipeline. Main entry point."""
        await self.orchestrator.run()

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


async def run_pipeline_flow(
    pipeline: BasePipeline, logger: "structlog.BoundLogger"
) -> None:
    """Run a pipeline with logging and error handling."""
    try:
        await pipeline.run()
    except Exception as e:
        logger.exception("Pipeline execution failed", error=str(e))
        raise
