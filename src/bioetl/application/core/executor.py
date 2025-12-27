"""Pipeline Executor: orchestrates the data flow from extraction to processing.

Observability (O2):
- Root span for each batch with batch_id, record_count, run_type attributes
- Nested spans for fetch → transform → write operations

Memory Management:
- Adaptive batch sizing based on memory pressure
- Automatic batch size reduction under high memory load
- Gradual recovery when memory pressure decreases
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from uuid import uuid4

from bioetl.application.core.memory_manager import MemoryConfig, MemoryManager
from bioetl.application.core.shutdown import PipelineShutdownError, ShutdownSignal
from bioetl.domain.types import BatchID

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from bioetl.application.core.checkpoint_manager import CheckpointManager
    from bioetl.application.core.pipeline_services import PipelineServices
    from bioetl.application.core.record_processor import RecordProcessor
    from bioetl.domain.ports import LoggerPort, TracingPort
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
    - Automatic batch size reduction when memory is constrained
    - Gradual batch size recovery when memory pressure decreases
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
            memory_config: Optional memory management configuration.
            logger: Optional logger for memory management logs.

        """
        self._data_source = services.data_source
        self._checkpoint_manager = checkpoint_manager
        self._shutdown_signal = shutdown_signal
        self._entity_type = entity_type
        self._base_batch_size = batch_size or self.DEFAULT_BATCH_SIZE
        self.batch_size = self._base_batch_size
        self.checkpoint_interval = (
            checkpoint_interval or self.DEFAULT_CHECKPOINT_INTERVAL
        )

        self._record_processor = record_processor
        self._run_type = run_type
        self._tracer = tracer

        # Memory management
        self._memory_manager = MemoryManager(config=memory_config, logger=logger)
        self._memory_manager.set_base_batch_size(self._base_batch_size)

        # Counters
        self.records_fetched = 0
        self.records_bronze = 0
        self.records_silver = 0
        self.records_gold = 0
        self.records_quarantined = 0

    @property
    def memory_manager(self) -> MemoryManager:
        """Get the memory manager instance."""
        return self._memory_manager

    async def execute(
        self,
        limit: int | None,
        query: str | None = None,
    ) -> None:
        """Execute the pipeline with memory-efficient batch processing.

        Uses adaptive batch sizing to prevent OOM errors when processing
        large datasets. Batch size is automatically reduced under memory
        pressure and gradually recovered when pressure decreases.

        Args:
            limit: Maximum number of records to process.
            query: Optional query string for data source.

        """
        batch: list[dict[str, Any]] = []
        current_batch_size = self.batch_size

        try:
            async for raw_record in self._extract(limit, query):
                if self._shutdown_signal.is_requested:
                    # Graceful shutdown: save where we stopped
                    await self._checkpoint_manager.save_checkpoint(
                        self.records_fetched
                    )
                    raise PipelineShutdownError("Shutdown during extraction")

                batch.append(raw_record)
                self.records_fetched += 1

                if len(batch) >= current_batch_size:
                    await self._process_and_update_counts(batch)
                    batch = []

                    # Adjust batch size based on memory pressure after processing
                    current_batch_size = self._memory_manager.get_recommended_batch_size(
                        current_batch_size
                    )
                    # Update instance batch_size for observability
                    self.batch_size = current_batch_size

                if self.records_fetched % self.checkpoint_interval == 0:
                    await self._checkpoint_manager.save_checkpoint(
                        self.records_fetched
                    )

            if batch:
                await self._process_and_update_counts(batch)

        except PipelineShutdownError:
            # Re-raise explicit shutdown signal
            try:
                await self._checkpoint_manager.save_checkpoint(
                    self.records_fetched
                )
            except Exception:
                # Ignore errors during emergency checkpoint save
                pass
            raise

    async def _process_and_update_counts(self, batch: list[dict[str, Any]]) -> None:
        """Process batch with tracing span.

        Creates a root span for the batch with attributes:
        - batch_id: Unique identifier for this batch
        - record_count: Number of records in the batch
        - run_type: Type of pipeline run
        """
        batch_id = BatchID(uuid4())
        span = None

        # Start batch tracing span if tracer is available
        if self._tracer:
            otel_tracer = self._tracer.get_tracer("bioetl.executor")
            span = otel_tracer.start_as_current_span(
                f"batch_{batch_id}",
                attributes={
                    "bioetl.batch_id": str(batch_id),
                    "bioetl.record_count": len(batch),
                    "bioetl.run_type": self._run_type.value if self._run_type else "unknown",
                    "bioetl.entity_type": self._entity_type,
                },
            )
            span.__enter__()

        try:
            result = await self._record_processor.process_batch(
                records=batch, batch_id=batch_id
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
        async for record in self._data_source.fetch(
            entity_type=self._entity_type,
            limit=limit,
            query=query,
        ):
            yield record
