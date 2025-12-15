"""Base ETL Pipeline class with Prefect integration.

Implements RULES.md §4 - Generic ETL Pipeline pattern.

Requirements:
- Lock acquisition and heartbeat
- Checkpoint save/restore
- Graceful shutdown (SIGTERM/SIGINT)
- Bronze → Silver → Gold flow
- Error handling and quarantine
- Observability (logging, metrics)
- Prefect integration for orchestration
"""

import asyncio
import json
import signal
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from prefect import flow, task

from bioetl.domain.ports import (
    CheckpointPort,
    DataSourcePort,
    LockPort,
    QuarantinePort,
    StoragePort,
)
from bioetl.domain.types import (
    BatchID,
    ErrorType,
    RunID,
    RunType,
    Watermark,
)
from bioetl.infrastructure.observability.logging import create_logger


class PipelineShutdownError(Exception):
    """Raised when pipeline receives shutdown signal."""

    pass


@flow(
    name="{self.pipeline_name}",
    log_prints=True,
    validate_parameters=False,
)
async def run_pipeline_flow(pipeline: "BasePipeline") -> None:
    """Prefect flow to run the ETL pipeline."""
    await pipeline.run()


class BasePipeline(ABC):
    """Base class for ETL pipelines.

    Implements common pipeline patterns:
    - Lock acquisition with heartbeat
    - Checkpoint management
    - Graceful shutdown
    - Bronze → Silver → Gold flow
    - Error handling and quarantine

    Example:
        >>> class MyPipeline(BasePipeline):
        ...     # ... implementation ...
        ...
        >>> pipeline = MyPipeline(...)
        >>> await run_pipeline_flow(pipeline)
    """

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
        self.shutdown_requested = False
        self.heartbeat_task: asyncio.Task[None] | None = None
        self.records_fetched = 0
        self.records_bronze = 0
        self.records_silver = 0
        self.records_gold = 0
        self.records_quarantined = 0
        self.logger = create_logger(
            run_id=str(self.run_id),
            pipeline=pipeline_name,
        )

    async def run(self) -> None:
        """Execute pipeline. Main entry point."""
        self.logger.info(
            f"Starting pipeline: {self.pipeline_name}",
            extra={"stage": "startup", "run_type": self.run_type.value},
        )
        self._setup_shutdown_handlers()

        lock_key = f"{self.provider}_{self.entity_type}"
        exclusive = self.run_type in (RunType.BACKFILL, RunType.REBUILD)

        try:
            acquired = await self.lock.acquire(
                key=lock_key, owner_id=self.run_id, wait=False, exclusive=exclusive
            )
            if not acquired:
                self.logger.error(f"Failed to acquire lock for {lock_key}")
                return

            self.logger.info(f"Lock acquired for {lock_key}")
            self.heartbeat_task = asyncio.create_task(
                self._heartbeat_loop(lock_key, exclusive)
            )

            watermark = await self._load_checkpoint_task()
            await self._execute_pipeline_task(watermark)
            await self._delete_checkpoint_task()

            self.logger.info(
                "Pipeline completed successfully",
                extra={
                    "stage": "complete",
                    "records_fetched": self.records_fetched,
                },
            )
        except PipelineShutdownError:
            self.logger.warning(
                "Pipeline shutdown requested", extra={"stage": "shutdown"}
            )
            raise
        except Exception as e:
            self.logger.error(f"Pipeline failed: {e}", exc_info=True)
            raise
        finally:
            if self.heartbeat_task:
                self.heartbeat_task.cancel()
            await self.lock.release(lock_key, self.run_id, exclusive=exclusive)
            self.logger.info("Lock released", extra={"stage": "cleanup"})

    @task(name="Load Checkpoint")
    async def _load_checkpoint_task(self) -> Watermark | None:
        if self.resume:
            checkpoint_data = self.checkpoint.load(self.pipeline_name)
            if checkpoint_data:
                watermark, _, metadata = checkpoint_data
                self.logger.info(
                    f"Resuming from checkpoint: {watermark}",
                    extra={"metadata": metadata},
                )
                return watermark
        return None

    @task(name="Execute Pipeline")
    async def _execute_pipeline_task(self, watermark: Watermark | None) -> None:
        """Execute main pipeline logic as a Prefect task."""
        async for raw_record in self._extract(watermark):
            if self.shutdown_requested:
                raise PipelineShutdownError("Shutdown during extraction")

            self.records_fetched += 1
            batch_id = await self._load_bronze(raw_record)
            self.records_bronze += 1

            try:
                transformed = await self.transform_bronze_to_silver(raw_record)
                if transformed:
                    await self._load_silver(transformed, batch_id)
                    self.records_silver += 1
                    if self.should_write_gold(transformed):
                        await self._load_gold(transformed)
                        self.records_gold += 1
            except Exception as e:
                error_type = self._classify_error(e)
                if error_type.is_data_quality():
                    await self._quarantine_record(
                        raw_record, error_type, batch_id, str(e)
                    )
                    self.records_quarantined += 1
                else:
                    raise

            if self.records_fetched % 1000 == 0:
                await self._save_checkpoint(raw_record)

    @task(name="Delete Checkpoint")
    async def _delete_checkpoint_task(self) -> None:
        self.checkpoint.delete(self.pipeline_name)

    async def _extract(
        self, watermark: Watermark | None
    ) -> AsyncIterator[dict[str, Any]]:
        async for record in self.data_source.fetch(
            entity_type=self.entity_type, watermark=watermark
        ):
            yield record

    async def _load_bronze(self, record: dict[str, Any]) -> BatchID:
        batch_id = BatchID(uuid4())
        record_bytes = (json.dumps(record) + "\n").encode("utf-8")
        self.storage.write_bronze(
            records=iter([record_bytes]),
            provider=self.provider,
            entity=self.entity_type,
            date=datetime.now(timezone.utc),
            batch_id=batch_id,
        )
        return batch_id

    async def _load_silver(self, record: dict[str, Any], batch_id: BatchID) -> None:
        record_with_meta = {
            **record,
            "_run_id": str(self.run_id),
            "_run_type": self.run_type.value,
            "_source_batch_id": str(batch_id),
            "_ingestion_ts": datetime.now(timezone.utc).isoformat(),
        }
        table_name = f"{self.provider}.{self.entity_type}"
        self.storage.write_silver(
            table_name=table_name,
            records=[record_with_meta],
            primary_keys=["entity_id"],
        )

    async def _load_gold(self, record: dict[str, Any]) -> None:
        table_name = f"{self.provider}.{self.entity_type}_gold"
        self.storage.write_gold(table_name=table_name, records=[record], mode="append")

    async def _quarantine_record(
        self,
        record: dict[str, Any],
        error_type: ErrorType,
        batch_id: BatchID,
        error_details: str,
    ) -> None:
        self.quarantine.write(
            pipeline=self.pipeline_name,
            error_code=error_type.value,
            payload=record,
            bronze_batch_id=batch_id,
            error_details={"message": error_details},
        )

    async def _save_checkpoint(self, last_record: dict[str, Any]) -> None:
        watermark = self.extract_watermark(last_record)
        self.checkpoint.save(
            pipeline=self.pipeline_name,
            watermark=watermark,
            run_id=self.run_id,
            metadata={"records_processed": self.records_fetched},
        )

    async def _heartbeat_loop(self, lock_key: str, exclusive: bool) -> None:
        while not self.shutdown_requested:
            await asyncio.sleep(20)
            success = await self.lock.heartbeat(
                lock_key, self.run_id, exclusive=exclusive
            )
            if not success:
                self.logger.error("Lost lock during execution!")
                self.shutdown_requested = True
                raise PipelineShutdownError("Lock lost")

    def _setup_shutdown_handlers(self) -> None:
        def signal_handler(signum: int, frame: Any) -> None:
            self.logger.warning(
                f"Received signal {signum}, initiating graceful shutdown"
            )
            self.shutdown_requested = True

        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)

    def _classify_error(self, error: Exception) -> ErrorType:
        error_name = type(error).__name__
        if "Schema" in error_name or "Validation" in error_name:
            return ErrorType.SCHEMA_VIOLATION
        elif "Missing" in error_name or "Required" in error_name:
            return ErrorType.MISSING_REQUIRED_FIELD
        else:
            return ErrorType.INVALID_DATA

    @abstractmethod
    async def transform_bronze_to_silver(
        self, record: dict[str, Any]
    ) -> dict[str, Any] | None:
        pass

    def should_write_gold(self, record: dict[str, Any]) -> bool:
        return True

    def extract_watermark(self, record: dict[str, Any]) -> Watermark:
        return Watermark(datetime.now(timezone.utc))
