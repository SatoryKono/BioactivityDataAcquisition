"""Pipeline Executor: orchestrates the data flow from extraction to processing.

Observability (O2):
- Root span for each batch with batch_id, record_count, run_type attributes
- Nested spans for fetch → transform → write operations

Memory Management:
- Adaptive batch sizing based on memory pressure
- Automatic batch size reduction when approaching memory limits
- Configurable memory thresholds via MemoryConfig
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from uuid import uuid4

from bioetl.application.core.shutdown import PipelineShutdownError, ShutdownSignal
from bioetl.domain.ports import NoOpTracing
from bioetl.domain.types import BatchID

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from bioetl.application.core.checkpoint_manager import CheckpointManager
    from bioetl.application.core.memory_monitor import MemoryConfig
    from bioetl.application.core.pipeline_services import PipelineServices
    from bioetl.application.core.record_processor import RecordProcessor
    from bioetl.domain.ports import LoggerPort, MemoryMonitorPort, TracingPort
    from bioetl.domain.types import RunType


class PipelineExecutor:
    """Orchestrates the data flow: extracts data, accumulates batches.

    Also delegates processing to a RecordProcessor.

    Observability (O2):
    - Root span "batch_{batch_id}" for each batch
    - Span attributes: batch_id, record_count, run_type
    - Nested spans delegated to RecordProcessor

    Memory Management:
    - Adaptive batch sizing based on memory pressure
    - Automatic batch size reduction when memory threshold exceeded
    - Configurable via MemoryConfig
    """

    DEFAULT_BATCH_SIZE = 100
    DEFAULT_CHECKPOINT_INTERVAL = 1000

    def __init__(
        self,
        services: PipelineServices,
        record_processor: RecordProcessor,
        checkpoint_manager: CheckpointManager,
        shutdown_signal: ShutdownSignal,
        entity_type: str,
        batch_size: int | None = None,
        checkpoint_interval: int | None = None,
        run_type: RunType | None = None,
        tracer: TracingPort | None = None,
        pipeline_name: str | None = None,
        run_id: str | None = None,
        memory_monitor: MemoryMonitorPort | None = None,
        memory_config: MemoryConfig | None = None,
        logger: LoggerPort | None = None,
    ):
        """Initialize pipeline executor.

        Args:
            services: Common pipeline services (logging, metrics, etc.).
            record_processor: Record processor instance.
            checkpoint_manager: Checkpoint manager instance.
            shutdown_signal: Signal to handle graceful shutdown.
            entity_type: Type of entity to process.
            batch_size: Number of records per batch.
            checkpoint_interval: Number of records between checkpoints.
            run_type: Type of pipeline run (for tracing attributes).
            tracer: Optional tracing port for distributed tracing.
            pipeline_name: Name of the pipeline (for tracing attributes).
            run_id: Unique run identifier (for tracing attributes).
            memory_monitor: Optional memory monitor for adaptive batch sizing.
            memory_config: Memory configuration (used if memory_monitor not provided).
            logger: Logger for memory-related messages.

        """
        self._data_source = services.data_source
        self._checkpoint_manager = checkpoint_manager
        self._shutdown_signal = shutdown_signal
        self._entity_type = entity_type
        self._initial_batch_size = batch_size or self.DEFAULT_BATCH_SIZE
        self.batch_size = self._initial_batch_size
        self.checkpoint_interval = (
            checkpoint_interval or self.DEFAULT_CHECKPOINT_INTERVAL
        )

        self._record_processor = record_processor
        self._run_type = run_type

        # Use NoOpTracing if not provided (Null Object Pattern)
        # NoOpTracing is imported at module level from domain.ports
        self._tracer: TracingPort = tracer if tracer is not None else NoOpTracing()

        self._pipeline_name = pipeline_name
        self._run_id = run_id
        self._logger = logger or services.logger

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
            Exception: Any exception from data source or record processor.

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

    def _start_execution_span(self) -> Any | None:
        """Start root tracing span for pipeline execution.

        Returns:
            The span context manager or None if tracing disabled.

        """
        otel_tracer = self._tracer.get_tracer("bioetl.executor")
        span = otel_tracer.start_as_current_span(
            "pipeline_execution",
            attributes={
                "bioetl.pipeline": self._pipeline_name or "unknown",
                "bioetl.run_id": self._run_id or "unknown",
                "bioetl.entity_type": self._entity_type,
                "bioetl.run_type": (
                    self._run_type.value if self._run_type else "unknown"
                ),
                "bioetl.adaptive_batch_sizing": self._adaptive_batch_size_enabled,
                "bioetl.initial_batch_size": self._initial_batch_size,
            },
        )
        span.__enter__()
        return span

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
                # Calculate start index for this batch
                start_index = self.records_fetched - len(batch)
                await self._process_and_update_counts(batch, start_index)
                batch = []
                current_batch_size = self._maybe_recover_batch_size(current_batch_size)

            if self.records_fetched % self.checkpoint_interval == 0:
                await self._checkpoint_manager.save_checkpoint(self.records_fetched)

        if batch:
            start_index = self.records_fetched - len(batch)
            await self._process_and_update_counts(batch, start_index)

    def _check_memory_pressure(self, current_size: int, check_interval: int) -> int:
        """Check memory pressure and adjust batch size if needed.

        Args:
            current_size: Current batch size.
            check_interval: Records between checks.

        Returns:
            Adjusted batch size.

        """
        if not self._adaptive_batch_size_enabled:
            return current_size
        if self.records_fetched % check_interval != 0:
            return current_size
        return self._adjust_batch_size(current_size)

    def _maybe_recover_batch_size(self, current_size: int) -> int:
        """Try to recover batch size after processing if adaptive sizing enabled.

        Args:
            current_size: Current batch size.

        Returns:
            Potentially larger batch size.

        """
        if not self._adaptive_batch_size_enabled:
            return current_size
        return self._try_recover_batch_size(current_size)

    def _set_execution_span_stats(self, span: Any | None) -> None:
        """Set final statistics on the execution span.

        Args:
            span: The span to update, or None if tracing disabled.

        """
        if not span:
            return

        span.set_attribute("bioetl.total_fetched", self.records_fetched)
        span.set_attribute("bioetl.total_bronze", self.records_bronze)
        span.set_attribute("bioetl.total_silver", self.records_silver)
        span.set_attribute("bioetl.total_gold", self.records_gold)
        span.set_attribute("bioetl.total_quarantined", self.records_quarantined)
        span.set_attribute("bioetl.batch_size_reductions", self._batch_size_reductions)
        span.set_attribute("bioetl.min_batch_size_used", self._min_batch_size_used)

    async def _handle_shutdown(self, span: Any | None) -> None:
        """Handle graceful shutdown with checkpoint save.

        Args:
            span: The span to finalize, or None if tracing disabled.

        """
        try:
            await self._checkpoint_manager.save_checkpoint(self.records_fetched)
        except Exception:
            pass  # Ignore errors during emergency checkpoint save

        if span:
            span.set_attribute("bioetl.shutdown", True)
            span.__exit__(None, None, None)

    def _handle_execution_error(self, span: Any | None, error: Exception) -> None:
        """Handle execution error with span cleanup.

        Args:
            span: The span to finalize, or None if tracing disabled.
            error: The exception that occurred.

        """
        if span:
            span.set_attribute("error", True)
            span.record_exception(error)
            span.__exit__(None, None, None)

    def _finalize_span(self, span: Any | None) -> None:
        """Finalize span on successful completion.

        Args:
            span: The span to finalize, or None if tracing disabled.

        """
        if span:
            span.__exit__(None, None, None)

    def _get_memory_check_interval(self) -> int:
        """Get interval for memory pressure checks.

        Returns:
            Number of records between memory checks.

        """
        if self._memory_config:
            return self._memory_config.check_interval_records
        return 100  # Default check every 100 records

    def _adjust_batch_size(self, current_size: int) -> int:
        """Adjust batch size based on memory pressure.

        Args:
            current_size: Current batch size.

        Returns:
            Adjusted batch size (may be smaller if under pressure).

        """
        if self._memory_monitor:
            new_size = self._memory_monitor.get_recommended_batch_size(current_size)
        elif self._memory_config:
            # Use config-based adjustment without psutil
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
        """Estimate batch size without memory monitoring.

        Falls back to conservative reduction based on record count.

        Args:
            current_size: Current batch size.

        Returns:
            Estimated safe batch size.

        """
        if not self._memory_config:
            return current_size

        # Simple heuristic: reduce batch size if we've processed many records
        # This is a fallback when psutil is not available
        records_per_mb = 1000  # Assume ~1KB per record as conservative estimate
        max_records = self._memory_config.max_batch_memory_mb * records_per_mb

        if current_size > max_records:
            return max(max_records, self._memory_config.min_batch_size)

        return current_size

    def _try_recover_batch_size(self, current_size: int) -> int:
        """Try to recover batch size after pressure is relieved.

        Args:
            current_size: Current batch size.

        Returns:
            Potentially larger batch size if pressure is relieved.

        """
        if self._memory_monitor:
            return self._memory_monitor.get_recommended_batch_size(current_size)

        # Without monitor, gradually increase if below initial size
        if current_size < self._initial_batch_size:
            recovery_size = min(
                int(current_size * 1.1),  # Increase by 10%
                self._initial_batch_size,
            )
            return recovery_size

        return current_size

    async def _process_and_update_counts(
        self, batch: list[dict[str, Any]], start_index: int
    ) -> None:
        """Process batch with tracing span.

        Creates a root span for the batch with attributes:
        - batch_id: Unique identifier for this batch
        - record_count: Number of records in the batch
        - run_type: Type of pipeline run
        """
        batch_id = BatchID(uuid4())
        span = None

        # Start batch tracing span if tracer is available
        otel_tracer = self._tracer.get_tracer("bioetl.executor")
        span = otel_tracer.start_as_current_span(
            f"batch_{batch_id}",
            attributes={
                "bioetl.batch_id": str(batch_id),
                "bioetl.record_count": len(batch),
                "bioetl.run_type": (
                    self._run_type.value if self._run_type else "unknown"
                ),
                "bioetl.entity_type": self._entity_type,
                "bioetl.start_index": start_index,
            },
        )
        span.__enter__()

        try:
            result = await self._record_processor.process_batch(
                records=batch, batch_id=batch_id, start_index=start_index
            )
            self.records_bronze += result.bronze_count
            self.records_silver += result.silver_count
            self.records_gold += result.gold_count
            self.records_quarantined += result.quarantined_count

            # Add result attributes to span
            if span:
                span.set_attribute("bioetl.bronze_count", result.bronze_count)
                span.set_attribute("bioetl.silver_count", result.silver_count)
                span.set_attribute("bioetl.gold_count", result.gold_count)
                span.set_attribute("bioetl.quarantined_count", result.quarantined_count)
        except Exception as e:
            if span:
                span.set_attribute("error", True)
                span.record_exception(e)
            raise
        finally:
            if span:
                span.__exit__(None, None, None)

    async def _extract(
        self, limit: int | None, query: str | None = None
    ) -> AsyncIterator[dict[str, Any]]:
        """Extract records from data source.

        Delegates to the data source port to fetch records for the
        configured entity type.

        Args:
            limit: Maximum number of records to extract. None means no limit.
            query: Optional query string for server-side filtering.

        Yields:
            Raw records as dictionaries from the data source.

        """
        # Pass filter_ids and filter_field if configured in data source
        # This requires checking if data source supports filtering
        # For now, we assume standard fetch unless executor is extended

        # Check if data source has filter config injected
        # This is a bit of a hack, ideally executor should know about filters
        # But filters are injected into data source at creation time

        async for record in self._data_source.fetch(
            entity_type=self._entity_type,
            limit=limit,
            query=query,
        ):
            yield record
