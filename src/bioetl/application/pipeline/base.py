"""Base ETL Pipeline class.

Implements RULES.md §4 - Generic ETL Pipeline pattern.

Requirements:
- Lock acquisition and heartbeat
- Checkpoint save/restore
- Graceful shutdown (SIGTERM/SIGINT)
- Bronze → Silver → Gold flow
- Error handling and quarantine
- Observability (logging, metrics)
"""

import asyncio
import signal
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from datetime import datetime
from typing import Any
from uuid import uuid4

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
from bioetl.observability.logging import create_logger


class PipelineShutdownError(Exception):
    """Raised when pipeline receives shutdown signal."""

    pass


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
        ...     def __init__(self, ...):
        ...         super().__init__(
        ...             pipeline_name="my_pipeline",
        ...             provider="chembl",
        ...             entity_type="activity",
        ...             ...
        ...         )
        ...
        ...     async def transform_bronze_to_silver(self, record):
        ...         # Transform logic
        ...         return transformed_record
        ...
        >>> pipeline = MyPipeline(...)
        >>> await pipeline.run()
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
        """Initialize pipeline.

        Args:
            pipeline_name: Pipeline identifier (e.g., 'chembl_activity')
            provider: Provider name (e.g., 'chembl')
            entity_type: Entity type (e.g., 'activity')
            run_type: Type of run (incremental, backfill, rebuild)
            data_source: Data source adapter
            storage: Storage adapter (Bronze/Silver/Gold)
            lock: Distributed lock adapter
            checkpoint: Checkpoint storage adapter
            quarantine: Quarantine adapter
            resume: Resume from checkpoint if available
        """
        self.pipeline_name = pipeline_name
        self.provider = provider
        self.entity_type = entity_type
        self.run_type = run_type

        # Adapters
        self.data_source = data_source
        self.storage = storage
        self.lock = lock
        self.checkpoint = checkpoint
        self.quarantine = quarantine

        # State
        self.run_id = RunID(uuid4())
        self.resume = resume
        self.shutdown_requested = False
        self.heartbeat_task: asyncio.Task[None] | None = None

        # Metrics
        self.records_fetched = 0
        self.records_bronze = 0
        self.records_silver = 0
        self.records_gold = 0
        self.records_quarantined = 0

        # Logging
        self.logger = create_logger(
            run_id=str(self.run_id),
            pipeline=pipeline_name,
        )

    async def run(self) -> None:
        """Execute pipeline.

        Main entry point for pipeline execution.
        Handles lock acquisition, checkpoint recovery, and graceful shutdown.

        Raises:
            PipelineShutdownError: If shutdown signal received
            Exception: Pipeline execution errors
        """
        self.logger.info(
            f"Starting pipeline: {self.pipeline_name}",
            extra={
                "stage": "startup",
                "run_type": self.run_type.value,
                "provider": self.provider,
                "entity_type": self.entity_type,
            },
        )

        # Setup shutdown handlers
        self._setup_shutdown_handlers()

        try:
            # Acquire lock
            lock_key = f"{self.provider}_{self.entity_type}"
            exclusive = self.run_type in (RunType.BACKFILL, RunType.REBUILD)

            acquired = await self.lock.acquire(
                key=lock_key,
                owner_id=self.run_id,
                wait=False,
                exclusive=exclusive,
            )

            if not acquired:
                self.logger.error(
                    f"Failed to acquire lock for {lock_key}",
                    extra={"stage": "lock", "exclusive": exclusive},
                )
                return

            self.logger.info(
                f"Lock acquired for {lock_key}",
                extra={"stage": "lock", "exclusive": exclusive},
            )

            # Start heartbeat
            self.heartbeat_task = asyncio.create_task(
                self._heartbeat_loop(lock_key, exclusive)
            )

            # Load checkpoint if resuming
            watermark: Watermark | None = None
            if self.resume:
                checkpoint_data = self.checkpoint.load(self.pipeline_name)
                if checkpoint_data:
                    watermark, _, metadata = checkpoint_data
                    self.logger.info(
                        f"Resuming from checkpoint: {watermark}",
                        extra={"stage": "checkpoint", "metadata": metadata},
                    )

            # Execute pipeline stages
            await self._execute_pipeline(watermark)

            # Delete checkpoint on success
            self.checkpoint.delete(self.pipeline_name)

            self.logger.info(
                "Pipeline completed successfully",
                extra={
                    "stage": "complete",
                    "records_fetched": self.records_fetched,
                    "records_bronze": self.records_bronze,
                    "records_silver": self.records_silver,
                    "records_gold": self.records_gold,
                    "records_quarantined": self.records_quarantined,
                },
            )

        except PipelineShutdownError:
            self.logger.warning(
                "Pipeline shutdown requested",
                extra={"stage": "shutdown"},
            )
            raise

        except Exception as e:
            self.logger.error(
                f"Pipeline failed: {e}",
                extra={"stage": "error", "error_type": type(e).__name__},
                exc_info=True,
            )
            raise

        finally:
            # Cleanup
            if self.heartbeat_task:
                self.heartbeat_task.cancel()
                try:
                    await self.heartbeat_task
                except asyncio.CancelledError:
                    pass

            # Release lock
            await self.lock.release(lock_key, self.run_id, exclusive=exclusive)
            self.logger.info("Lock released", extra={"stage": "cleanup"})

    async def _execute_pipeline(self, watermark: Watermark | None) -> None:
        """Execute main pipeline logic.

        Args:
            watermark: Starting watermark for incremental load
        """
        # Stage 1: Extract (fetch from source)
        self.logger.info("Starting extraction", extra={"stage": "extract"})

        async for raw_record in self._extract(watermark):
            if self.shutdown_requested:
                raise PipelineShutdownError("Shutdown during extraction")

            self.records_fetched += 1

            # Stage 2: Load to Bronze (raw storage)
            try:
                batch_id = await self._load_bronze(raw_record)
                self.records_bronze += 1
            except Exception as e:
                self.logger.error(
                    f"Failed to write to Bronze: {e}",
                    extra={"stage": "bronze", "record": raw_record},
                )
                continue

            # Stage 3: Transform and load to Silver
            try:
                transformed = await self.transform_bronze_to_silver(raw_record)
                if transformed:
                    await self._load_silver(transformed, batch_id)
                    self.records_silver += 1

                    # Stage 4: Optional Gold layer
                    if self.should_write_gold(transformed):
                        await self._load_gold(transformed)
                        self.records_gold += 1

            except Exception as e:
                # Quarantine on transform/validation errors
                error_type = self._classify_error(e)
                if error_type.is_data_quality():
                    await self._quarantine_record(
                        raw_record, error_type, batch_id, str(e)
                    )
                    self.records_quarantined += 1
                else:
                    # Critical error, re-raise
                    raise

            # Checkpoint every 1000 records
            if self.records_fetched % 1000 == 0:
                await self._save_checkpoint(raw_record)

    async def _extract(
        self, watermark: Watermark | None
    ) -> AsyncIterator[dict[str, Any]]:
        """Extract records from data source.

        Args:
            watermark: Starting watermark

        Yields:
            Raw records
        """
        async for record in self.data_source.fetch(
            entity_type=self.entity_type,
            watermark=watermark,
        ):
            yield record

    async def _load_bronze(self, record: dict[str, Any]) -> BatchID:
        """Write record to Bronze layer.

        Args:
            record: Raw record

        Returns:
            Batch ID
        """
        batch_id = BatchID(uuid4())

        # Convert to JSONL bytes
        import json

        record_bytes = (json.dumps(record) + "\n").encode("utf-8")

        # Write to Bronze
        self.storage.write_bronze(
            records=iter([record_bytes]),
            provider=self.provider,
            entity=self.entity_type,
            date=datetime.utcnow(),
            batch_id=batch_id,
        )

        return batch_id

    async def _load_silver(
        self,
        record: dict[str, Any],
        batch_id: BatchID,
    ) -> None:
        """Write transformed record to Silver layer.

        Args:
            record: Transformed record
            batch_id: Source batch ID
        """
        # Add metadata
        record_with_meta = {
            **record,
            "_run_id": str(self.run_id),
            "_run_type": self.run_type.value,
            "_source_batch_id": str(batch_id),
            "_ingestion_ts": datetime.utcnow().isoformat(),
        }

        # Write to Silver
        table_name = f"{self.provider}.{self.entity_type}"
        self.storage.write_silver(
            table_name=table_name,
            records=[record_with_meta],
            primary_keys=["entity_id"],
        )

    async def _load_gold(self, record: dict[str, Any]) -> None:
        """Write validated record to Gold layer.

        Args:
            record: Validated record
        """
        table_name = f"{self.provider}.{self.entity_type}_gold"
        self.storage.write_gold(
            table_name=table_name,
            records=[record],
            mode="append",
        )

    async def _quarantine_record(
        self,
        record: dict[str, Any],
        error_type: ErrorType,
        batch_id: BatchID,
        error_details: str,
    ) -> None:
        """Write failed record to quarantine.

        Args:
            record: Failed record
            error_type: Type of error
            batch_id: Source batch ID
            error_details: Error description
        """
        self.quarantine.write(
            pipeline=self.pipeline_name,
            error_code=error_type.value,
            payload=record,
            bronze_batch_id=batch_id,
            error_details={"message": error_details},
        )

    async def _save_checkpoint(self, last_record: dict[str, Any]) -> None:
        """Save checkpoint.

        Args:
            last_record: Last processed record
        """
        watermark = self.extract_watermark(last_record)

        self.checkpoint.save(
            pipeline=self.pipeline_name,
            watermark=watermark,
            run_id=self.run_id,
            metadata={
                "records_processed": self.records_fetched,
                "timestamp": datetime.utcnow().isoformat(),
            },
        )

    async def _heartbeat_loop(self, lock_key: str, exclusive: bool) -> None:
        """Maintain lock heartbeat.

        Args:
            lock_key: Lock key
            exclusive: Whether lock is exclusive
        """
        while not self.shutdown_requested:
            await asyncio.sleep(20)  # Heartbeat every 20s

            success = await self.lock.heartbeat(
                lock_key, self.run_id, exclusive=exclusive
            )

            if not success:
                self.logger.error(
                    "Lost lock during execution!",
                    extra={"stage": "heartbeat"},
                )
                self.shutdown_requested = True
                raise PipelineShutdownError("Lock lost")

    def _setup_shutdown_handlers(self) -> None:
        """Setup signal handlers for graceful shutdown."""

        def signal_handler(signum: int, frame: Any) -> None:
            self.logger.warning(
                f"Received signal {signum}, initiating graceful shutdown",
                extra={"stage": "shutdown"},
            )
            self.shutdown_requested = True

        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)

    def _classify_error(self, error: Exception) -> ErrorType:
        """Classify error type.

        Args:
            error: Exception

        Returns:
            ErrorType enum value
        """
        error_name = type(error).__name__

        if "Schema" in error_name or "Validation" in error_name:
            return ErrorType.SCHEMA_VIOLATION
        elif "Missing" in error_name or "Required" in error_name:
            return ErrorType.MISSING_REQUIRED_FIELD
        else:
            return ErrorType.INVALID_DATA

    # Abstract methods to be implemented by subclasses

    @abstractmethod
    async def transform_bronze_to_silver(
        self,
        record: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Transform raw Bronze record to normalized Silver record.

        Args:
            record: Raw record from Bronze

        Returns:
            Transformed record or None if should be skipped

        Example:
            >>> async def transform_bronze_to_silver(self, record):
            ...     return {
            ...         "entity_id": record["id"],
            ...         "value": float(record["value"]),
            ...         "unit": record.get("unit", "nM"),
            ...     }
        """
        pass

    def should_write_gold(self, record: dict[str, Any]) -> bool:
        """Determine if record should be written to Gold layer.

        Default: Write all records. Override for filtering.

        Args:
            record: Silver record

        Returns:
            True if should write to Gold
        """
        return True

    def extract_watermark(self, record: dict[str, Any]) -> Watermark:
        """Extract watermark value from record.

        Default: Use current timestamp. Override for custom logic.

        Args:
            record: Record

        Returns:
            Watermark value
        """
        return Watermark(datetime.utcnow())
