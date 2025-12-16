"""Pipeline Executor with batch processing.

Handles the Bronze -> Silver -> Gold data flow with efficient batch writes.

Refactored per ADR-0005 to accept explicit dependencies instead of full pipeline.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator, Awaitable
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Protocol
from uuid import uuid4

from bioetl.application.core.checkpoint_manager import CheckpointManager
from bioetl.application.core.quarantine_manager import QuarantineManager
from bioetl.application.core.shutdown import PipelineShutdownError, ShutdownSignal
from bioetl.domain.context import PipelineContext
from bioetl.domain.error_classifier import ErrorClassifier
from bioetl.domain.ports import DataSourcePort, StoragePort
from bioetl.domain.types import BatchID, Watermark

if TYPE_CHECKING:
    from bioetl.application.core.base import BasePipeline


class TransformCallback(Protocol):
    """Protocol for Bronze to Silver transformation callback."""

    def __call__(
        self, context: PipelineContext, record: dict[str, Any]
    ) -> Awaitable[dict[str, Any] | None]: ...


class GoldFilterCallback(Protocol):
    """Protocol for Gold layer filtering callback."""

    def __call__(self, context: PipelineContext, record: dict[str, Any]) -> bool: ...


class PipelineExecutor:
    """Executes the main data processing logic with batch optimization.

    This executor implements efficient batch processing with automatic backpressure
    control to prevent out-of-memory (OOM) errors during high-throughput ingestion.

    Backpressure Mechanism (RULES.md §5.1):
    =======================================
    The executor naturally implements backpressure through synchronous batch processing:

    1. **Fetch records** from data source (async iterator)
    2. **Accumulate batch** until batch_size reached (in-memory buffer)
    3. **Process batch** (Bronze → Silver → Gold) - BLOCKS until complete
    4. **Repeat** - fetching resumes only after batch processing completes

    This creates natural flow control:
    - If Bronze write is slow (S3 latency) → fetch slows down automatically
    - If compression is CPU-bound → batch accumulation pauses
    - Memory usage bounded by: batch_size × avg_record_size

    For explicit backpressure monitoring, track:
    - bronze_write_duration_seconds (P95 latency)
    - batch_queue_depth (if using async queues in future)

    Performance Tuning:
    ===================
    - DEFAULT_BATCH_SIZE: Controls memory/throughput tradeoff
      * Smaller (50-100): Lower memory, more S3 API calls
      * Larger (500-1000): Higher throughput, more memory
      * Optimal: 100-200 records for typical JSON payloads (~10-50MB compressed)

    - DEFAULT_CHECKPOINT_INTERVAL: How often to save progress
      * Smaller: More fault-tolerant, more S3 writes
      * Larger: Fewer checkpoints, faster processing
      * Optimal: 1000 records (balance between safety and performance)
    """

    DEFAULT_BATCH_SIZE = 100
    DEFAULT_CHECKPOINT_INTERVAL = 1000

    def __init__(
        self,
        pipeline: "BasePipeline",
        batch_size: int | None = None,
        checkpoint_interval: int | None = None,
        *,
        # New explicit dependencies (ADR-0005)
        _shutdown_signal: ShutdownSignal | None = None,
    ) -> None:
        """Initialize executor.

        Legacy mode: Pass pipeline only
        New mode: Use from_components() factory method
        """
        self.pipeline = pipeline
        self.batch_size = batch_size or self.DEFAULT_BATCH_SIZE
        self.checkpoint_interval = checkpoint_interval or self.DEFAULT_CHECKPOINT_INTERVAL

        # New: explicit shutdown signal (falls back to orchestrator check)
        self._shutdown_signal = _shutdown_signal

        # Counters
        self.records_fetched = 0
        self.records_bronze = 0
        self.records_silver = 0
        self.records_gold = 0
        self.records_quarantined = 0

    @classmethod
    def from_components(
        cls,
        data_source: DataSourcePort,
        storage: StoragePort,
        checkpoint_manager: CheckpointManager,
        quarantine_manager: QuarantineManager,
        error_classifier: ErrorClassifier,
        context: PipelineContext,
        shutdown_signal: ShutdownSignal,
        provider: str,
        entity_type: str,
        transform_callback: TransformCallback,
        gold_filter_callback: GoldFilterCallback,
        batch_size: int | None = None,
        checkpoint_interval: int | None = None,
    ) -> "PipelineExecutor":
        """Create PipelineExecutor from explicit components (new API).

        This factory method creates an executor without circular dependencies.

        Args:
            data_source: Port for fetching data.
            storage: Port for writing to Bronze/Silver/Gold.
            checkpoint_manager: Manager for checkpoint operations.
            quarantine_manager: Manager for failed records.
            error_classifier: Classifier for error types.
            context: Pipeline execution context.
            shutdown_signal: Shared signal for shutdown coordination.
            provider: Data provider name.
            entity_type: Entity type being processed.
            transform_callback: Async callback for Bronze->Silver transformation.
            gold_filter_callback: Callback to determine if record goes to Gold.
            batch_size: Records per batch.
            checkpoint_interval: Records between checkpoints.
        """
        # Create a minimal adapter that wraps components
        executor = object.__new__(cls)
        executor._data_source = data_source
        executor._storage = storage
        executor._checkpoint_manager = checkpoint_manager
        executor._quarantine_manager = quarantine_manager
        executor._error_classifier = error_classifier
        executor._context = context
        executor._shutdown_signal = shutdown_signal
        executor._provider = provider
        executor._entity_type = entity_type
        executor._transform = transform_callback
        executor._gold_filter = gold_filter_callback
        executor.batch_size = batch_size or cls.DEFAULT_BATCH_SIZE
        executor.checkpoint_interval = checkpoint_interval or cls.DEFAULT_CHECKPOINT_INTERVAL
        executor.pipeline = None  # Not used in new mode

        # Counters
        executor.records_fetched = 0
        executor.records_bronze = 0
        executor.records_silver = 0
        executor.records_gold = 0
        executor.records_quarantined = 0

        return executor

    def _is_shutdown_requested(self) -> bool:
        """Check if shutdown was requested (supports both modes)."""
        if self._shutdown_signal is not None:
            return self._shutdown_signal.is_requested
        # Legacy fallback
        return self.pipeline.orchestrator.shutdown_requested

    def _get_checkpoint_manager(self) -> CheckpointManager:
        """Get checkpoint manager (supports both modes)."""
        if hasattr(self, "_checkpoint_manager"):
            return self._checkpoint_manager
        return self.pipeline.checkpoint_manager

    def _get_data_source(self) -> DataSourcePort:
        """Get data source (supports both modes)."""
        if hasattr(self, "_data_source"):
            return self._data_source
        return self.pipeline.data_source

    def _get_storage(self) -> StoragePort:
        """Get storage port (supports both modes)."""
        if hasattr(self, "_storage"):
            return self._storage
        return self.pipeline.storage

    def _get_context(self) -> PipelineContext:
        """Get pipeline context (supports both modes)."""
        if hasattr(self, "_context"):
            return self._context
        return self.pipeline.context

    def _get_provider(self) -> str:
        """Get provider (supports both modes)."""
        if hasattr(self, "_provider"):
            return self._provider
        return self.pipeline.provider

    def _get_entity_type(self) -> str:
        """Get entity type (supports both modes)."""
        if hasattr(self, "_entity_type"):
            return self._entity_type
        return self.pipeline.entity_type

    async def _call_transform(
        self, context: PipelineContext, record: dict[str, Any]
    ) -> dict[str, Any] | None:
        """Call transform callback (supports both modes)."""
        if hasattr(self, "_transform"):
            return await self._transform(context, record)
        return await self.pipeline.transform_bronze_to_silver(context, record)

    def _call_gold_filter(
        self, context: PipelineContext, record: dict[str, Any]
    ) -> bool:
        """Call gold filter callback (supports both modes)."""
        if hasattr(self, "_gold_filter"):
            return self._gold_filter(context, record)
        return self.pipeline.should_write_gold(context, record)

    def _get_error_classifier(self) -> ErrorClassifier:
        """Get error classifier (supports both modes)."""
        if hasattr(self, "_error_classifier"):
            return self._error_classifier
        return self.pipeline.error_classifier

    def _get_quarantine_manager(self) -> QuarantineManager:
        """Get quarantine manager (supports both modes)."""
        if hasattr(self, "_quarantine_manager"):
            return self._quarantine_manager
        return self.pipeline.quarantine_manager

    async def execute(self, watermark: Watermark | None, limit: int | None) -> None:
        """Execute main pipeline logic with batch processing."""
        batch: list[dict[str, Any]] = []
        batch_id = BatchID(uuid4())
        last_record: dict[str, Any] | None = None
        checkpoint_mgr = self._get_checkpoint_manager()

        async for raw_record in self._extract(watermark, limit):
            if self._is_shutdown_requested():
                # Save checkpoint before shutdown
                if last_record:
                    await checkpoint_mgr.save_checkpoint(last_record, self.records_fetched)
                raise PipelineShutdownError("Shutdown during extraction")

            batch.append(raw_record)
            last_record = raw_record
            self.records_fetched += 1

            # Process batch when full
            if len(batch) >= self.batch_size:
                await self._process_batch(batch, batch_id)
                batch = []
                batch_id = BatchID(uuid4())

            # Checkpoint at intervals
            if self.records_fetched % self.checkpoint_interval == 0:
                await checkpoint_mgr.save_checkpoint(raw_record, self.records_fetched)

        # Process remaining records
        if batch:
            await self._process_batch(batch, batch_id)

    async def _process_batch(
        self,
        records: list[dict[str, Any]],
        batch_id: BatchID,
    ) -> None:
        """Process a batch of records through Bronze -> Silver -> Gold."""
        # 1. Write all records to Bronze as single batch
        await self._write_bronze_batch(records, batch_id)
        self.records_bronze += len(records)

        # 2. Transform and collect Silver records
        silver_records: list[dict[str, Any]] = []
        gold_records: list[dict[str, Any]] = []
        context = self._get_context()
        error_classifier = self._get_error_classifier()
        quarantine_mgr = self._get_quarantine_manager()

        for raw_record in records:
            record_context = context.bind_logger(
                batch_id=str(batch_id),
                entity_id=raw_record.get("activity_id"),
            )

            try:
                transformed = await self._call_transform(record_context, raw_record)
                if transformed:
                    silver_records.append(transformed)
                    if self._call_gold_filter(record_context, transformed):
                        gold_records.append(transformed)
            except Exception as e:
                error_type = error_classifier.classify(e)
                if error_type.is_data_quality():
                    await quarantine_mgr.quarantine_record(
                        raw_record, error_type, batch_id, str(e)
                    )
                    self.records_quarantined += 1
                else:
                    raise

        # 3. Batch write to Silver
        if silver_records:
            await self._write_silver_batch(silver_records, batch_id)
            self.records_silver += len(silver_records)

        # 4. Batch write to Gold
        if gold_records:
            await self._write_gold_batch(gold_records)
            self.records_gold += len(gold_records)

    async def _extract(
        self, watermark: Watermark | None, limit: int | None
    ) -> AsyncIterator[dict[str, Any]]:
        """Extract records from data source."""
        data_source = self._get_data_source()
        entity_type = self._get_entity_type()

        async for record in data_source.fetch(
            entity_type=entity_type,
            watermark=watermark,
            limit=limit,
        ):
            yield record

    async def _write_bronze_batch(
        self,
        records: list[dict[str, Any]],
        batch_id: BatchID,
    ) -> None:
        """Write batch of records to Bronze layer."""
        record_bytes = [
            (json.dumps(record) + "\n").encode("utf-8") for record in records
        ]
        storage = self._get_storage()
        provider = self._get_provider()
        entity_type = self._get_entity_type()

        await storage.write_bronze(
            records=iter(record_bytes),
            provider=provider,
            entity=entity_type,
            date=datetime.now(UTC),
            batch_id=batch_id,
        )

    async def _write_silver_batch(
        self,
        records: list[dict[str, Any]],
        batch_id: BatchID,
    ) -> None:
        """Write batch of records to Silver layer."""
        context = self._get_context()
        provider = self._get_provider()
        entity_type = self._get_entity_type()
        storage = self._get_storage()

        records_with_meta = [
            {
                **record,
                "_run_id": str(context.run_id),
                "_run_type": context.run_type.value,
                "_source_batch_id": str(batch_id),
                "_ingestion_ts": datetime.now(UTC).isoformat(),
            }
            for record in records
        ]
        table_name = f"{provider}.{entity_type}"
        await storage.write_silver(
            table_name=table_name,
            records=records_with_meta,
            primary_keys=["entity_id"],
        )

    async def _write_gold_batch(self, records: list[dict[str, Any]]) -> None:
        """Write batch of records to Gold layer."""
        provider = self._get_provider()
        entity_type = self._get_entity_type()
        storage = self._get_storage()

        table_name = f"{provider}.{entity_type}_gold"
        await storage.write_gold(
            table_name=table_name,
            records=records,
            mode="append",
        )
