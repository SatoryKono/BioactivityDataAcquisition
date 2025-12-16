"""Base ETL Pipeline class.

Coordinates the pipeline components.
"""

from abc import ABC, abstractmethod
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from bioetl.application.pipeline.checkpoint_manager import CheckpointManager
from bioetl.application.pipeline.executor import PipelineExecutor
from bioetl.application.pipeline.lock_manager import LockManager
from bioetl.application.pipeline.orchestrator import PipelineOrchestrator
from bioetl.application.pipeline.quarantine_manager import QuarantineManager
from bioetl.domain.context import PipelineContext
from bioetl.domain.error_classifier import ErrorClassifier
from bioetl.domain.ports import (
    CheckpointPort,
    DataSourcePort,
    LockPort,
    QuarantinePort,
    StoragePort,
)
from bioetl.domain.types import (
    RunID,
    RunType,
    Watermark,
)
from bioetl.infrastructure.observability.logging import create_logger


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
        resume: bool = False,
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
        self.resume = resume
        self.run_id = RunID(uuid4())

        logger = create_logger(
            run_id=str(self.run_id),
            pipeline=pipeline_name,
        )
        self.context = PipelineContext(
            run_id=self.run_id,
            run_type=self.run_type,
            logger=logger,
        )
        self.logger = logger

        # Decomposed components
        self.orchestrator = PipelineOrchestrator(self)
        self.executor = PipelineExecutor(self)
        self.lock_manager = LockManager(self)
        self.checkpoint_manager = CheckpointManager(self)
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
