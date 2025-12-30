"""Unified Batch Executor.

Combines functionality from PipelineExecutor and RecordProcessor into a single
component that orchestrates the complete ETL flow: extraction → transformation → writing.

This consolidation reduces the call stack depth by one level while maintaining
all functionality: adaptive batch sizing, checkpointing, graceful shutdown,
Bronze/Silver/Gold processing, and quarantine management.

Observability:
- Root span for pipeline execution
- Nested spans for each batch
- Per-layer spans for transform/write operations
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from bioetl.application.core.batch_metrics import BatchMetricsRecorder
from bioetl.application.core.batch_transformer import BatchTransformer, TransformResult
from bioetl.application.core.batch_writer import BatchWriter
from bioetl.application.core.quarantine_manager import QuarantineManager
from bioetl.application.core.shutdown import PipelineShutdownError, ShutdownSignal
from bioetl.domain.ports import NoOpTracing
from bioetl.domain.types import BatchID

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from bioetl.application.core.checkpoint_manager import CheckpointManager
    from bioetl.application.core.config import RecordProcessorConfig
    from bioetl.application.core.memory_monitor import MemoryConfig
    from bioetl.application.core.pipeline_services import PipelineServices
    from bioetl.application.core.protocols import (
        GoldFilterCallback,
        GoldTransformCallback,
        TransformCallback,
    )
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.error_classifier import ErrorClassifier
    from bioetl.domain.ports import (
        GoldValidatorPort,
        LoggerPort,
        MemoryMonitorPort,
        TracingPort,
    )


@dataclass(frozen=True, slots=True)
class BatchResult:
    """Result of processing a batch of records."""

    bronze_count: int
    silver_count: int
    gold_count: int
    quarantined_count: int


class BatchExecutor:
    """Unified executor for ETL pipeline batches.

    Combines the extraction loop (formerly PipelineExecutor) with batch
    processing logic (formerly RecordProcessor) into a single component.

    Responsibilities:
    - Extract records from data source
    - Accumulate records into batches
    - Adaptive batch sizing based on memory pressure
    - Transform Bronze → Silver → Gold
    - Write to all layers
    - Quarantine failed records
    - Checkpoint management
    - Graceful shutdown handling

    Observability:
    - Root span for complete execution
    - Per-batch spans with record counts
    - Per-layer spans (transform, write_bronze, write_silver, write_gold)
    """

    DEFAULT_BATCH_SIZE = 100
    DEFAULT_CHECKPOINT_INTERVAL = 1000

    def __init__(
        self,
        services: PipelineServices,
        context: PipelineContext,
        config: RecordProcessorConfig,
        error_classifier: ErrorClassifier,
        transform_callback: TransformCallback,
        gold_filter_callback: GoldFilterCallback,
        gold_transform_callback: GoldTransformCallback,
        gold_validator: GoldValidatorPort,
        checkpoint_manager: CheckpointManager,
        shutdown_signal: ShutdownSignal,
        *,
        batch_size: int | None = None,
        checkpoint_interval: int | None = None,
        tracer: TracingPort | None = None,
        lock_validator: Callable[[], Awaitable[bool]] | None = None,
        memory_monitor: MemoryMonitorPort | None = None,
        memory_config: MemoryConfig | None = None,
        logger: LoggerPort | None = None,
    ) -> None:
        """Initialize batch executor.

        Args:
            services: Common pipeline services (data source, storage, metrics, etc.).
            context: Pipeline execution context (run_id, run_type, started_at).
            config: Record processor configuration.
            error_classifier: Service for error classification.
            transform_callback: Callback for Bronze → Silver transformation.
            gold_filter_callback: Callback for filtering Silver records for Gold.
            gold_transform_callback: Callback for Silver → Gold transformation.
            gold_validator: Validator for Gold layer records.
            checkpoint_manager: Checkpoint manager instance.
            shutdown_signal: Signal to handle graceful shutdown.
            batch_size: Number of records per batch.
            checkpoint_interval: Number of records between checkpoints.
            tracer: Optional tracing port for distributed tracing.
            lock_validator: Async callable that validates lock ownership (Safety Guard §4.6).
            memory_monitor: Optional memory monitor for adaptive batch sizing.
            memory_config: Memory configuration (used if memory_monitor not provided).
            logger: Logger for memory-related messages.

        """
        self._services = services
        self._context = context
        self._config = config
        self._checkpoint_manager = checkpoint_manager
        self._shutdown_signal = shutdown_signal
        self._logger = logger or services.logger

        # Batch configuration
        self._initial_batch_size = batch_size or self.DEFAULT_BATCH_SIZE
        self.batch_size = self._initial_batch_size
        self.checkpoint_interval = (
            checkpoint_interval or self.DEFAULT_CHECKPOINT_INTERVAL
        )

        # Tracing
        self._tracer: TracingPort = tracer if tracer is not None else NoOpTracing()

        # Memory management
        self._memory_monitor = memory_monitor
        self._memory_config = memory_config
        self._adaptive_batch_size_enabled = memory_monitor is not None or (
            memory_config is not None and memory_config.enable_adaptive_sizing
        )
        self._batch_size_reductions = 0
        self._min_batch_size_used = self._initial_batch_size

        # Counters
        self.records_fetched = 0
        self.records_bronze = 0
        self.records_silver = 0
        self.records_gold = 0
        self.records_quarantined = 0

        # Create internal components (from RecordProcessor)
        pipeline_label = f"{config.provider}_{config.entity_type}"
        self._batch_metrics = BatchMetricsRecorder(
            services.metrics, pipeline_label, context.run_type.value
        )

        self._transformer = BatchTransformer(
            context=context,
            config=config,
            error_classifier=error_classifier,
            quarantine_manager=QuarantineManager(
                quarantine_port=services.quarantine,
                pipeline_name=config.pipeline_name,
            ),
            batch_metrics=self._batch_metrics,
            transform_callback=transform_callback,
            gold_filter_callback=gold_filter_callback,
            gold_transform_callback=gold_transform_callback,
        )

        self._writer = BatchWriter(
            storage=services.storage,
            context=context,
            config=config,
            gold_validator=gold_validator,
            error_classifier=error_classifier,
            batch_metrics=self._batch_metrics,
            tracer=tracer,
            lock_validator=lock_validator,
        )

    @property
    def entity_type(self) -> str:
        """Get entity type being processed."""
        return self._config.entity_type

    async def execute(
        self,
        limit: int | None,
        query: str | None = None,
    ) -> None:
        """Execute the pipeline with memory-efficient adaptive batch sizing.

        Orchestrates the complete data flow: fetch → transform → write for
        all records from the data source. Handles graceful shutdown and
        checkpointing.

        Args:
            limit: Maximum number of records to process. None means no limit.
            query: Optional query string for data source filtering.

        Raises:
            PipelineShutdownError: If shutdown signal received during execution.
            Exception: Any exception from data source or processing.

        Note:
            After execution, counters are updated:
            - records_fetched: Total records retrieved from source
            - records_bronze: Records written to Bronze layer
            - records_silver: Records written to Silver layer
            - records_gold: Records written to Gold layer
            - records_quarantined: Records sent to quarantine

        """
        root_span = self._start_execution_span()

        try:
            await self._run_extraction_loop(limit, query)
            self._set_execution_span_stats(root_span)
        except PipelineShutdownError:
            await self._handle_shutdown(root_span)
            raise
        except Exception as e:
            self._handle_execution_error(root_span, e)
            raise
        else:
            self._finalize_span(root_span)

    async def _run_extraction_loop(self, limit: int | None, query: str | None) -> None:
        """Run the main extraction and processing loop.

        Args:
            limit: Maximum number of records to process.
            query: Optional query string for data source.

        """
        batch: list[dict[str, Any]] = []
        current_batch_size = self.batch_size
        check_interval = self._get_memory_check_interval()

        async for raw_record in self._extract(limit, query):
            if self._shutdown_signal.is_requested:
                await self._checkpoint_manager.save_checkpoint(self.records_fetched)
                raise PipelineShutdownError("Shutdown during extraction")

            batch.append(raw_record)
            self.records_fetched += 1

            current_batch_size = self._check_memory_pressure(
                current_batch_size, check_interval
            )

            if len(batch) >= current_batch_size:
                start_index = self.records_fetched - len(batch)
                await self._process_batch(batch, start_index)
                batch = []
                current_batch_size = self._maybe_recover_batch_size(current_batch_size)

            if self.records_fetched % self.checkpoint_interval == 0:
                await self._checkpoint_manager.save_checkpoint(self.records_fetched)

        if batch:
            start_index = self.records_fetched - len(batch)
            await self._process_batch(batch, start_index)

    async def _process_batch(
        self, records: list[dict[str, Any]], start_index: int
    ) -> None:
        """Process a batch through Bronze → Silver → Gold with tracing.

        Creates a span for the batch and delegates to internal components
        for transformation and writing.

        Args:
            records: Raw records to process.
            start_index: Starting index for records in this batch.

        """
        batch_id = BatchID(uuid4())
        ingestion_ts = self._context.started_at

        # Start batch tracing span
        span = self._start_batch_span(batch_id, len(records), start_index)

        try:
            # Write to Bronze
            await self._execute_with_span(
                "write_bronze",
                self._writer.write_bronze(records, batch_id, ingestion_ts),
                batch_id,
                len(records),
                on_error=lambda e: self._writer.log_and_track_write_error(
                    "bronze", e, batch_id
                ),
            )
            self._batch_metrics.track_batch_size("bronze", len(records))
            self._batch_metrics.track_processed_records("bronze", len(records))

            # Transform records
            result = await self._execute_transform_with_span(
                records, batch_id, start_index
            )
            self._batch_metrics.track_processed_records(
                "quarantined", result.quarantined_count
            )
            self._batch_metrics.track_processed_records(
                "silver", len(result.silver_records)
            )
            self._batch_metrics.track_processed_records(
                "gold", len(result.gold_records)
            )

            # Write to Silver
            if result.silver_records:
                await self._execute_with_span(
                    "write_silver",
                    self._writer.write_silver(
                        result.silver_records, batch_id, ingestion_ts
                    ),
                    batch_id,
                    len(result.silver_records),
                    on_error=lambda e: self._writer.log_and_track_write_error(
                        "silver", e, batch_id
                    ),
                )

            # Write to Gold
            if result.gold_records:
                await self._execute_with_span(
                    "write_gold",
                    self._writer.write_gold(result.gold_records),
                    batch_id,
                    len(result.gold_records),
                    on_error=lambda e: self._writer.log_and_track_write_error(
                        "gold", e, batch_id
                    ),
                )

            # Update counters
            self.records_bronze += len(records)
            self.records_silver += len(result.silver_records)
            self.records_gold += len(result.gold_records)
            self.records_quarantined += result.quarantined_count

            # Add result attributes to span
            if span:
                span.set_attribute("bioetl.bronze_count", len(records))
                span.set_attribute("bioetl.silver_count", len(result.silver_records))
                span.set_attribute("bioetl.gold_count", len(result.gold_records))
                span.set_attribute("bioetl.quarantined_count", result.quarantined_count)

        except Exception as e:
            if span:
                span.set_attribute("error", True)
                span.record_exception(e)
            raise
        finally:
            if span:
                span.__exit__(None, None, None)

    async def _execute_with_span(
        self,
        name: str,
        coro: Any,
        batch_id: BatchID,
        count: int,
        on_error: Any = None,
    ) -> Any:
        """Execute coroutine with tracing span."""
        span = self._start_layer_span(name, batch_id, count)
        try:
            result = await coro
            self._end_span(span)
            return result
        except Exception as e:
            self._end_span(span, e)
            if on_error:
                on_error(e)
            raise

    async def _execute_transform_with_span(
        self, records: list[dict[str, Any]], batch_id: BatchID, start_index: int
    ) -> TransformResult:
        """Execute transformation with extended span attributes."""
        span = self._start_layer_span(
            "transform", batch_id, len(records), input_count=True
        )
        try:
            result = await self._transformer.transform_batch(
                records, batch_id, start_index=start_index
            )
            if span:
                span.set_attribute("bioetl.silver_count", len(result.silver_records))
                span.set_attribute("bioetl.gold_count", len(result.gold_records))
                span.set_attribute("bioetl.quarantined_count", result.quarantined_count)
            self._end_span(span)
            return result
        except Exception as e:
            self._end_span(span, e)
            raise

    # -------------------------------------------------------------------------
    # Tracing helpers
    # -------------------------------------------------------------------------

    def _start_execution_span(self) -> Any | None:
        """Start root tracing span for pipeline execution."""
        otel_tracer = self._tracer.get_tracer("bioetl.batch_executor")
        span = otel_tracer.start_as_current_span(
            "pipeline_execution",
            attributes={
                "bioetl.pipeline": self._config.pipeline_name or "unknown",
                "bioetl.run_id": str(self._context.run_id),
                "bioetl.entity_type": self._config.entity_type,
                "bioetl.run_type": self._context.run_type.value,
                "bioetl.adaptive_batch_sizing": self._adaptive_batch_size_enabled,
                "bioetl.initial_batch_size": self._initial_batch_size,
            },
        )
        span.__enter__()
        return span

    def _start_batch_span(
        self, batch_id: BatchID, record_count: int, start_index: int
    ) -> Any | None:
        """Start tracing span for a batch."""
        otel_tracer = self._tracer.get_tracer("bioetl.batch_executor")
        span = otel_tracer.start_as_current_span(
            f"batch_{batch_id}",
            attributes={
                "bioetl.batch_id": str(batch_id),
                "bioetl.record_count": record_count,
                "bioetl.run_type": self._context.run_type.value,
                "bioetl.entity_type": self._config.entity_type,
                "bioetl.start_index": start_index,
            },
        )
        span.__enter__()
        return span

    def _start_layer_span(
        self,
        name: str,
        batch_id: BatchID,
        count: int,
        input_count: bool = False,
    ) -> Any:
        """Start a tracing span for a layer operation."""
        count_key = "bioetl.input_count" if input_count else "bioetl.record_count"
        attrs = {"bioetl.batch_id": str(batch_id), count_key: count}
        span = self._tracer.get_tracer("bioetl.batch_executor").start_as_current_span(
            name, attributes=attrs
        )
        span.__enter__()
        return span

    def _set_execution_span_stats(self, span: Any | None) -> None:
        """Set final statistics on the execution span."""
        if not span:
            return

        span.set_attribute("bioetl.total_fetched", self.records_fetched)
        span.set_attribute("bioetl.total_bronze", self.records_bronze)
        span.set_attribute("bioetl.total_silver", self.records_silver)
        span.set_attribute("bioetl.total_gold", self.records_gold)
        span.set_attribute("bioetl.total_quarantined", self.records_quarantined)
        span.set_attribute("bioetl.batch_size_reductions", self._batch_size_reductions)
        span.set_attribute("bioetl.min_batch_size_used", self._min_batch_size_used)

    def _end_span(self, span: Any, error: Exception | None = None) -> None:
        """End a tracing span."""
        if not span:
            return
        if error:
            span.set_attribute("error", True)
            span.record_exception(error)
        span.__exit__(None, None, None)

    def _finalize_span(self, span: Any | None) -> None:
        """Finalize span on successful completion."""
        if span:
            span.__exit__(None, None, None)

    async def _handle_shutdown(self, span: Any | None) -> None:
        """Handle graceful shutdown with checkpoint save."""
        try:
            await self._checkpoint_manager.save_checkpoint(self.records_fetched)
        except Exception:
            pass  # Ignore errors during emergency checkpoint save

        if span:
            span.set_attribute("bioetl.shutdown", True)
            span.__exit__(None, None, None)

    def _handle_execution_error(self, span: Any | None, error: Exception) -> None:
        """Handle execution error with span cleanup."""
        if span:
            span.set_attribute("error", True)
            span.record_exception(error)
            span.__exit__(None, None, None)

    # -------------------------------------------------------------------------
    # Memory management helpers (from PipelineExecutor)
    # -------------------------------------------------------------------------

    def _get_memory_check_interval(self) -> int:
        """Get interval for memory pressure checks."""
        if self._memory_config:
            return self._memory_config.check_interval_records
        return 100  # Default check every 100 records

    def _check_memory_pressure(self, current_size: int, check_interval: int) -> int:
        """Check memory pressure and adjust batch size if needed."""
        if not self._adaptive_batch_size_enabled:
            return current_size
        if self.records_fetched % check_interval != 0:
            return current_size
        return self._adjust_batch_size(current_size)

    def _maybe_recover_batch_size(self, current_size: int) -> int:
        """Try to recover batch size after processing if adaptive sizing enabled."""
        if not self._adaptive_batch_size_enabled:
            return current_size
        return self._try_recover_batch_size(current_size)

    def _adjust_batch_size(self, current_size: int) -> int:
        """Adjust batch size based on memory pressure."""
        if self._memory_monitor:
            new_size = self._memory_monitor.get_recommended_batch_size(current_size)
        elif self._memory_config:
            new_size = self._estimate_batch_size_from_config(current_size)
        else:
            return current_size

        if new_size < current_size:
            self._batch_size_reductions += 1
            self._min_batch_size_used = min(self._min_batch_size_used, new_size)
            self._logger.info(
                "Reduced batch size due to memory pressure",
                old_size=current_size,
                new_size=new_size,
                total_reductions=self._batch_size_reductions,
            )

        return new_size

    def _estimate_batch_size_from_config(self, current_size: int) -> int:
        """Estimate batch size without memory monitoring."""
        if not self._memory_config:
            return current_size

        records_per_mb = 1000
        max_records = self._memory_config.max_batch_memory_mb * records_per_mb

        if current_size > max_records:
            return max(max_records, self._memory_config.min_batch_size)

        return current_size

    def _try_recover_batch_size(self, current_size: int) -> int:
        """Try to recover batch size after pressure is relieved."""
        if self._memory_monitor:
            return self._memory_monitor.get_recommended_batch_size(current_size)

        if current_size < self._initial_batch_size:
            recovery_size = min(
                int(current_size * 1.1),
                self._initial_batch_size,
            )
            return recovery_size

        return current_size

    # -------------------------------------------------------------------------
    # Data extraction
    # -------------------------------------------------------------------------

    async def _extract(
        self, limit: int | None, query: str | None = None
    ) -> AsyncIterator[dict[str, Any]]:
        """Extract records from data source.

        Args:
            limit: Maximum number of records to extract. None means no limit.
            query: Optional query string for server-side filtering.

        Yields:
            Raw records as dictionaries from the data source.

        """
        async for record in self._services.data_source.fetch(
            entity_type=self._config.entity_type,
            limit=limit,
            query=query,
        ):
            yield record
