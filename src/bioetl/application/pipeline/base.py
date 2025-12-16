"""Base ETL Pipeline class with Prefect integration."""

from abc import ABC, abstractmethod
from datetime import datetime, UTC
from typing import Any
from uuid import uuid4

from prefect import flow, task

from bioetl.application.pipeline.checkpoint_manager import PipelineCheckpointManager
from bioetl.application.pipeline.lock_manager import PipelineLockManager
from bioetl.application.pipeline.record_processor import PipelineRecordProcessor
from bioetl.domain.ports import (
    CheckpointPort, DataSourcePort, LockPort, QuarantinePort, StoragePort,
)
from bioetl.domain.types import RunID, RunType, Watermark
from bioetl.infrastructure.observability.logging import create_logger


class PipelineShutdownError(Exception):
    """Raised when pipeline receives shutdown signal."""


@flow(name="{self.pipeline_name}", log_prints=True, validate_parameters=False)
async def run_pipeline_flow(pipeline: "BasePipeline") -> None:
    """Prefect flow to run the ETL pipeline."""
    await pipeline.run()


class BasePipeline(ABC):
    """Base class for ETL pipelines."""

    def __init__(
        self, pipeline_name: str, provider: str, entity_type: str,
        run_type: RunType, data_source: DataSourcePort, storage: StoragePort,
        lock: LockPort, checkpoint: CheckpointPort, quarantine: QuarantinePort,
        resume: bool = False,
    ) -> None:
        self.pipeline_name, self.provider, self.entity_type = pipeline_name, provider, entity_type
        self.run_type, self.resume, self.run_id = run_type, resume, RunID(uuid4())
        self.logger = create_logger(run_id=str(self.run_id), pipeline=pipeline_name)
        self.records_fetched = 0
        self._lock_mgr = PipelineLockManager(lock, self.run_id, self.logger)
        self._ckpt_mgr = PipelineCheckpointManager(checkpoint, pipeline_name, self.run_id, self.logger)
        self._processor = PipelineRecordProcessor(
            data_source, storage, quarantine, provider, entity_type,
            pipeline_name, self.run_id, run_type, self.logger,
        )

    async def run(self) -> None:
        """Execute pipeline."""
        self.logger.info(f"Starting pipeline: {self.pipeline_name}")
        self._lock_mgr.setup_shutdown_handlers()
        lock_key = f"{self.provider}_{self.entity_type}"
        exclusive = self.run_type in (RunType.BACKFILL, RunType.REBUILD)
        try:
            if not await self._lock_mgr.acquire(lock_key, exclusive):
                return
            watermark = await self._ckpt_mgr.load(self.resume)
            await self._execute_pipeline(watermark)
            await self._ckpt_mgr.delete()
            self.logger.info("Pipeline completed", extra={"records": self.records_fetched})
        except PipelineShutdownError:
            self.logger.warning("Pipeline shutdown requested")
            raise
        finally:
            await self._lock_mgr.release(lock_key, exclusive)

    @task(name="Execute Pipeline")
    async def _execute_pipeline(self, watermark: Watermark | None) -> None:
        async for raw in self._processor.extract(watermark):
            if self._lock_mgr.shutdown_requested:
                raise PipelineShutdownError("Shutdown during extraction")
            self.records_fetched += 1
            batch_id = await self._processor.load_bronze(raw)
            try:
                silver = await self.transform_bronze_to_silver(raw)
                if silver:
                    await self._processor.load_silver(silver, batch_id)
                    if self.should_write_gold(silver):
                        await self._processor.load_gold(silver)
            except Exception as e:
                err_type = PipelineRecordProcessor.classify_error(e)
                if err_type.is_data_quality():
                    await self._processor.quarantine_record(raw, err_type, batch_id, str(e))
                else:
                    raise
            if self.records_fetched % 1000 == 0:
                await self._ckpt_mgr.save(self.extract_watermark(raw), self.records_fetched)

    @abstractmethod
    async def transform_bronze_to_silver(self, record: dict[str, Any]) -> dict[str, Any] | None:
        pass

    def should_write_gold(self, _: dict[str, Any]) -> bool:
        return True

    def extract_watermark(self, _: dict[str, Any]) -> Watermark:
        return Watermark(datetime.now(UTC))
