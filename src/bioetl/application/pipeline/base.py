"""Base ETL Pipeline class with Prefect integration.

Implements RULES.md §4 - Generic ETL Pipeline pattern.
"""

import signal
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from prefect import flow, task

from bioetl.application.pipeline.checkpoint_manager import CheckpointManager
from bioetl.application.pipeline.lock_manager import LockManager, PipelineLockLostError
from bioetl.application.pipeline.record_processor import RecordProcessor
from bioetl.domain.ports import (
    CheckpointPort,
    DataSourcePort,
    LockPort,
    QuarantinePort,
    StoragePort,
)
from bioetl.domain.types import RunID, RunType, Watermark
from bioetl.infrastructure.observability.logging import create_logger


class PipelineShutdownError(Exception):
    """Raised when pipeline receives shutdown signal."""

    pass


@flow(name="{self.pipeline_name}", log_prints=True, validate_parameters=False)
async def run_pipeline_flow(pipeline: "BasePipeline") -> None:
    """Prefect flow to run the ETL pipeline."""
    await pipeline.run()


class BasePipeline(ABC):
    """Base class for ETL pipelines with decomposed responsibilities."""

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
        self.resume = resume
        self.run_id = RunID(uuid4())
        self.shutdown_requested = False
        self.records_fetched = 0
        self.logger = create_logger(run_id=str(self.run_id), pipeline=pipeline_name)

        self._lock_mgr = LockManager(lock, self.run_id, self.logger)
        self._checkpoint_mgr = CheckpointManager(
            checkpoint, pipeline_name, self.run_id, self.logger
        )
        self._processor = RecordProcessor(
            storage, quarantine, provider, entity_type,
            pipeline_name, self.run_id, run_type, self.logger
        )

    async def run(self) -> None:
        """Execute pipeline. Main entry point."""
        self.logger.info(f"Starting pipeline: {self.pipeline_name}",
                         extra={"stage": "startup", "run_type": self.run_type.value})
        self._setup_shutdown_handlers()

        lock_key = f"{self.provider}_{self.entity_type}"
        exclusive = self.run_type in (RunType.BACKFILL, RunType.REBUILD)

        try:
            if not await self._lock_mgr.acquire(lock_key, exclusive):
                return
            self._lock_mgr.start_heartbeat(
                lock_key, exclusive, lambda: setattr(self, "shutdown_requested", True)
            )
            await self._execute_with_checkpoint()
        except (PipelineShutdownError, PipelineLockLostError):
            self.logger.warning("Pipeline shutdown requested", extra={"stage": "shutdown"})
            raise PipelineShutdownError("Shutdown requested") from None
        finally:
            self._lock_mgr.stop_heartbeat()
            await self._lock_mgr.release(lock_key, exclusive)

    @task(name="Execute Pipeline")
    async def _execute_with_checkpoint(self) -> None:
        watermark = self._checkpoint_mgr.load(self.resume)
        async for record in self._extract(watermark):
            if self.shutdown_requested:
                raise PipelineShutdownError("Shutdown during extraction")
            await self._process_record(record)
        self._checkpoint_mgr.delete()
        self.logger.info("Pipeline completed", extra={"records": self.records_fetched})

    async def _process_record(self, raw: dict[str, Any]) -> None:
        self.records_fetched += 1
        batch_id = self._processor.load_bronze(raw)
        try:
            transformed = await self.transform_bronze_to_silver(raw)
            if transformed:
                self._processor.load_silver(transformed, batch_id)
                if self.should_write_gold(transformed):
                    self._processor.load_gold(transformed)
        except Exception as e:
            err_type = RecordProcessor.classify_error(e)
            if err_type.is_data_quality():
                self._processor.quarantine_record(raw, err_type, batch_id, str(e))
            else:
                raise
        if self.records_fetched % 1000 == 0:
            self._checkpoint_mgr.save(self.extract_watermark(raw), self.records_fetched)

    async def _extract(self, watermark: Watermark | None) -> AsyncIterator[dict[str, Any]]:
        async for record in self.data_source.fetch(self.entity_type, watermark):
            yield record

    def _setup_shutdown_handlers(self) -> None:
        def handler(signum: int, _frame: Any) -> None:
            self.logger.warning(f"Received signal {signum}, initiating shutdown")
            self.shutdown_requested = True
        signal.signal(signal.SIGTERM, handler)
        signal.signal(signal.SIGINT, handler)

    @abstractmethod
    async def transform_bronze_to_silver(self, record: dict[str, Any]) -> dict[str, Any] | None:
        pass

    def should_write_gold(self, record: dict[str, Any]) -> bool:  # noqa: ARG002
        return True

    def extract_watermark(self, record: dict[str, Any]) -> Watermark:  # noqa: ARG002
        return Watermark(datetime.now(UTC))
