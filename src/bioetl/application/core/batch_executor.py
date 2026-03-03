"""Unified Batch Executor for ETL pipeline orchestration.

Combines extraction, transformation, and writing into a single component with
adaptive batch sizing, checkpointing, and graceful shutdown handling.

DQ Report Integration:
- Accumulates data for DQ report generation when DQ report service is available
- Provides get_dq_context() method for building DQ report context
"""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from bioetl.application.core.batch_memory_manager import BatchMemoryManager
from bioetl.application.core.batch_metrics import BatchMetricsRecorder
from bioetl.application.core.batch_tracing import BatchTracingManager
from bioetl.application.core.batch_transformer import BatchTransformer, TransformResult
from bioetl.application.core.batch_writer import BatchWriter
from bioetl.application.core.quarantine_manager import QuarantineManager
from bioetl.application.core.shutdown import PipelineShutdownError, ShutdownSignal
from bioetl.domain.types import BatchID

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from opentelemetry.trace import Span

    from bioetl.application.core.checkpoint_manager import CheckpointManager
    from bioetl.application.core.config import RecordProcessorConfig
    from bioetl.application.core.pipeline_services import PipelineServices
    from bioetl.application.core.protocols import (
        GoldFilterCallback,
        GoldTransformCallback,
        TransformCallback,
    )
    from bioetl.application.services.dq_report_service import DQReportContext
    from bioetl.domain.config import MemoryConfig
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.error_classifier import ErrorClassifier
    from bioetl.domain.models.metadata import SourceMetadata
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
    """Unified executor for ETL batches: fetch → transform → write with tracing."""

    DEFAULT_BATCH_SIZE = 1000
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

        # Memory management (extracted to BatchMemoryManager)
        self._memory = BatchMemoryManager(
            self._initial_batch_size,
            memory_monitor=memory_monitor,
            memory_config=memory_config,
            logger=self._logger,
        )

        # Counters
        self.records_fetched = 0
        self.records_bronze = 0
        self.records_silver = 0
        self.records_gold = 0
        self.records_quarantined = 0
        self.records_filtered_out = 0

        # Progress reporting
        self._total_records: int | None = None
        self._progress_interval: int | None = None
        self._next_progress_threshold: int = 0

        # DQ Report data accumulation (only if DQ report service is available)
        # Collecting data adds memory overhead, so only enabled when needed
        self._bronze_records_for_dq: list[bytes] = []
        self._silver_records_for_dq: list[dict[str, Any]] = []
        self._gold_records_for_dq: list[dict[str, Any]] = []
        self._source_batch_ids: list[str] = []
        self._last_bronze_path: str | None = None

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
                metrics=services.metrics,
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

        # Tracing manager (extracted for class size reduction)
        self._tracing = BatchTracingManager(
            tracer=tracer,
            context=context,
            config=config,
            initial_batch_size=self._initial_batch_size,
            adaptive_sizing_enabled=self._memory.enabled,
        )

        # Query string for metadata (stored during execute())
        self._query_string: str | None = None

    @property
    def entity_type(self) -> str:
        """Get entity type being processed."""
        return self._config.entity_type

    async def execute(
        self,
        limit: int | None,
        query: str | None = None,
        offset: int | None = None,
    ) -> None:
        """Execute the pipeline: fetch → transform → write.

        Args:
            limit: Maximum number of records to process. None means no limit.
            query: Optional query string for data source filtering.
            offset: Starting offset for checkpoint resume (records already processed).

        Raises:
            PipelineShutdownError: If shutdown signal received during execution.

        """
        self._resume_offset = offset or 0
        self._query_string = query
        await self._init_progress_tracking(limit)

        root_span = self._tracing.start_execution_span()

        try:
            await self._run_extraction_loop(limit, query, offset=offset)
            self._tracing.set_execution_stats(
                root_span,
                total_fetched=self.records_fetched,
                total_bronze=self.records_bronze,
                total_silver=self.records_silver,
                total_gold=self.records_gold,
                total_quarantined=self.records_quarantined,
                batch_size_reductions=self._memory.batch_size_reductions,
                min_batch_size_used=self._memory.min_batch_size_used,
            )
        except PipelineShutdownError:
            await self._handle_shutdown(root_span)
            raise
        except Exception as e:
            # Save checkpoint on crash for future --resume recovery
            try:
                total = self._resume_offset + self.records_fetched
                if total > 0:
                    await self._checkpoint_manager.save_checkpoint(total)
                    self._logger.warning(
                        "Checkpoint saved on exception for recovery",
                        records_processed=total,
                        error_type=type(e).__name__,
                    )
            except Exception:
                pass  # Don't mask the original exception
            self._tracing.end_span(root_span, e)
            raise
        else:
            self._tracing.end_span(root_span)

    async def _init_progress_tracking(self, limit: int | None) -> None:
        """Estimate total records and configure progress reporting."""
        self._total_records = limit
        if not self._total_records:
            get_total = getattr(self._services.data_source, "get_total_records", None)
            if get_total and callable(get_total):
                result = await get_total()
                if isinstance(result, int) and result > 0:
                    self._total_records = result

        if self._total_records:
            self._progress_interval = max(1, self._total_records // 10)
            self._next_progress_threshold = self._progress_interval
            self._logger.info(
                "Starting pipeline with total records estimate",
                total_records=self._total_records,
                progress_interval=self._progress_interval,
            )

    async def _run_extraction_loop(
        self,
        limit: int | None,
        query: str | None,
        offset: int | None = None,
    ) -> None:
        """Run the main extraction and processing loop."""
        batch: list[dict[str, Any]] = []
        current_batch_size = self.batch_size
        check_interval = self._memory.get_check_interval()

        async for raw_record in self._extract(limit, query, offset=offset):
            if self._shutdown_signal.is_requested:
                total = self._resume_offset + self.records_fetched
                await self._checkpoint_manager.save_checkpoint(total)
                raise PipelineShutdownError("Shutdown during extraction")

            batch.append(raw_record)
            self.records_fetched += 1
            self._report_progress()

            current_batch_size = self._memory.check_pressure(
                current_batch_size, check_interval, self.records_fetched
            )

            if len(batch) >= current_batch_size:
                start_index = self.records_fetched - len(batch)
                await self._process_batch(batch, start_index)
                batch = []
                current_batch_size = self._memory.maybe_recover(current_batch_size)
                self._report_progress()

            if self.records_fetched % self.checkpoint_interval == 0:
                total = self._resume_offset + self.records_fetched
                await self._checkpoint_manager.save_checkpoint(total)

        if batch:
            start_index = self.records_fetched - len(batch)
            await self._process_batch(batch, start_index)

    async def process(
        self, records: list[dict[str, Any]], start_index: int = 0
    ) -> BatchResult:
        """Process a batch of records through the full ETL pipeline.

        Public API for processing individual batches. Delegates to internal
        processing with full tracing and observability.

        This method is the public entry point for batch processing, enabling:
        - Direct batch processing from external callers
        - Integration testing of the processing logic
        - Custom orchestration scenarios

        Args:
            records: Raw records to process through Bronze → Silver → Gold.
            start_index: Starting index for records in this batch. Default 0.

        Returns:
            BatchResult with counts for each layer.

        Example:
            >>> executor = BatchExecutor(...)
            >>> result = await executor.process(records, start_index=0)
            >>> logger.info("batch_processed", silver_count=result.silver_count)

        """
        await self._process_batch(records, start_index)
        return BatchResult(
            bronze_count=self.records_bronze,
            silver_count=self.records_silver,
            gold_count=self.records_gold,
            quarantined_count=self.records_quarantined,
        )

    def _get_source_metadata(self) -> SourceMetadata | None:
        """Get source metadata from data source if available.

        Checks if the data source has a `get_source_metadata()` method
        and calls it to retrieve accumulated API request metadata for
        Bronze layer enrichment.

        Also injects the query_string from execute() if not already set
        in the source metadata.

        Returns:
            SourceMetadata with API request details and query_string,
            or None if not available.

        """
        # Import SourceMetadata for runtime type check and creation
        from bioetl.domain.models.metadata import SourceMetadata

        source_metadata: SourceMetadata | None = None

        # Try to get metadata from data source
        data_source = self._services.data_source
        get_metadata = getattr(data_source, "get_source_metadata", None)
        if get_metadata is not None and callable(get_metadata):
            try:
                result = get_metadata()
                if isinstance(result, SourceMetadata):
                    source_metadata = result
            except Exception:
                # Gracefully handle any errors in metadata collection
                pass

        # Inject query_string if we have one and it's not already set
        if self._query_string:
            if source_metadata is not None:
                if source_metadata.query_string is None:
                    source_metadata = source_metadata.model_copy(
                        update={"query_string": self._query_string}
                    )
            else:
                # Create minimal SourceMetadata with query_string
                source_metadata = SourceMetadata(
                    type="api",
                    query_string=self._query_string,
                )

        return source_metadata

    async def _process_batch(
        self, records: list[dict[str, Any]], start_index: int
    ) -> None:
        """Process batch through Bronze → Silver → Gold with tracing.

        Args:
            records: Raw records to process.
            start_index: Starting index for records in this batch.
        """
        batch_id = BatchID(uuid4())
        ingestion_ts = self._context.started_at

        # Get source metadata from data source (if available)
        source_metadata = self._get_source_metadata()

        # Start batch tracing span
        span = self._tracing.start_batch_span(batch_id, len(records), start_index)

        try:
            # Write to Bronze and capture result for lineage tracking (REQ-LINEAGE-001)
            bronze_result = await self._execute_with_span(
                "write_bronze",
                self._writer.write_bronze(
                    records, batch_id, ingestion_ts, source_metadata=source_metadata
                ),
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

            # Write to Silver with bronze_refs for lineage tracking (REQ-LINEAGE-001)
            bronze_refs = [bronze_result] if bronze_result else None
            silver_result = None
            if result.silver_records:
                silver_result = await self._execute_with_span(
                    "write_silver",
                    self._writer.write_silver(
                        result.silver_records,
                        batch_id,
                        ingestion_ts,
                        bronze_refs=bronze_refs,
                    ),
                    batch_id,
                    len(result.silver_records),
                    on_error=lambda e: self._writer.log_and_track_write_error(
                        "silver", e, batch_id
                    ),
                )

            # Write to Gold with silver_refs for lineage tracking (REQ-LINEAGE-002)
            silver_refs = [silver_result] if silver_result else None
            if result.gold_records:
                await self._execute_with_span(
                    "write_gold",
                    self._writer.write_gold(
                        result.gold_records, silver_refs=silver_refs
                    ),
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
            self.records_filtered_out += result.filtered_out_count

            # Track batch ID for lineage (always enabled)
            self._source_batch_ids.append(str(batch_id))

            # Collect data for DQ reports (if enabled)
            if self._should_collect_dq_data():
                self._collect_dq_data(
                    records=records,
                    batch_id=batch_id,
                    bronze_result=bronze_result,
                    silver_records=result.silver_records,
                    gold_records=result.gold_records,
                )

            # Add result attributes to span
            self._tracing.set_batch_result(
                span,
                bronze_count=len(records),
                silver_count=len(result.silver_records),
                gold_count=len(result.gold_records),
                quarantined_count=result.quarantined_count,
            )

        except Exception as e:
            self._tracing.end_span(span, e)
            raise
        else:
            self._tracing.end_span(span)

    async def _execute_with_span(
        self,
        name: str,
        coro: Any,  # Any: Awaitable (generic coroutine)
        batch_id: BatchID,
        count: int,
        on_error: Any = None,  # Any: fallback return value type varies
    ) -> Any:  # Any: coroutine return type varies
        """Execute coroutine with tracing span."""
        span = self._tracing.start_layer_span(name, batch_id, count)
        try:
            result = await coro
            self._tracing.end_span(span)
            return result
        except Exception as e:
            self._tracing.end_span(span, e)
            if on_error:
                on_error(e)
            raise

    async def _execute_transform_with_span(
        self, records: list[dict[str, Any]], batch_id: BatchID, start_index: int
    ) -> TransformResult:
        """Execute transformation with extended span attributes."""
        span = self._tracing.start_layer_span(
            "transform", batch_id, len(records), input_count=True
        )
        try:
            result = await self._transformer.transform_batch(
                records, batch_id, start_index=start_index
            )
            self._tracing.set_transform_result(
                span,
                silver_count=len(result.silver_records),
                gold_count=len(result.gold_records),
                quarantined_count=result.quarantined_count,
            )
            self._tracing.end_span(span)
            return result
        except Exception as e:
            self._tracing.end_span(span, e)
            raise

    async def _handle_shutdown(self, span: Span | None) -> None:
        """Handle graceful shutdown with checkpoint save."""
        try:
            total = self._resume_offset + self.records_fetched
            await self._checkpoint_manager.save_checkpoint(total)
        except Exception:
            pass  # Ignore errors during emergency checkpoint save

        self._tracing.end_span_with_shutdown(span)

    # -------------------------------------------------------------------------
    # Progress reporting
    # -------------------------------------------------------------------------

    def _report_progress(self) -> None:
        """Report pipeline progress if threshold reached."""
        if (
            self._progress_interval
            and self._total_records
            and self.records_fetched >= self._next_progress_threshold
        ):
            pct = min(100, (self.records_fetched / self._total_records) * 100)
            self._logger.info(
                "Pipeline progress",
                progress=f"{pct:.0f}%",
                bronze=self.records_bronze,
                silver=self.records_silver,
                filtered_out=self.records_filtered_out,
                fetched=self.records_fetched,
            )
            self._next_progress_threshold += self._progress_interval

    # -------------------------------------------------------------------------
    # Data extraction
    # -------------------------------------------------------------------------

    async def _extract(
        self,
        limit: int | None,
        query: str | None = None,
        offset: int | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Extract records from data source."""
        async for record in self._services.data_source.fetch(
            entity_type=self._config.entity_type,
            limit=limit,
            query=query,
            offset=offset,
        ):
            yield record

    # -------------------------------------------------------------------------
    # DQ Report data collection
    # -------------------------------------------------------------------------

    def _should_collect_dq_data(self) -> bool:
        """Check if DQ report service is available.

        Returns:
            True if DQ report service is configured and data should be collected.
        """
        return self._services.dq_report_service is not None

    def _collect_dq_data(
        self,
        records: list[dict[str, Any]],
        batch_id: BatchID,
        bronze_result: Any,  # Any: BronzeWriteResult (avoids circular import)
        silver_records: list[dict[str, Any]],
        gold_records: list[dict[str, Any]],
    ) -> None:
        """Collect data from batch processing for DQ reports.

        Args:
            records: Raw Bronze records.
            batch_id: Batch identifier.
            bronze_result: Result from Bronze write operation (contains path).
            silver_records: Transformed Silver records.
            gold_records: Transformed Gold records.
        """
        # Collect Bronze records as bytes (JSON-encoded)
        for record in records:
            try:
                self._bronze_records_for_dq.append(
                    json.dumps(record, default=str).encode("utf-8")
                )
            except (TypeError, ValueError):
                # Skip records that can't be serialized
                pass

        # Track Bronze file path if available
        if bronze_result is not None and hasattr(bronze_result, "path"):
            self._last_bronze_path = str(bronze_result.path)

        # Collect Silver records
        self._silver_records_for_dq.extend(silver_records)

        # Collect Gold records
        self._gold_records_for_dq.extend(gold_records)

    def _build_dataframe_from_records(
        self, records: list[dict[str, Any]]
    ) -> Any | None:  # Any: pl.DataFrame (avoids polars import at module level)
        """Build a Polars DataFrame from records, returning None on failure."""
        if not records:
            return None
        try:
            import polars as pl

            return pl.DataFrame(records)
        except Exception:
            # Catch all: Polars import failure OR DataFrame construction errors
            # (malformed data, type mismatches). Graceful degradation: return None
            # so DQ analysis can proceed with fallback logic.
            return None

    def _get_dq_thresholds(self) -> tuple[float, float]:
        """Get DQ thresholds from config or defaults."""
        if self._config.dq_config:
            return (
                self._config.dq_config.soft_fail_threshold,
                self._config.dq_config.hard_fail_threshold,
            )
        return (0.05, 0.20)

    def _extract_dq_entity(self) -> str:
        """Extract entity name from silver_table for DQ report naming.

        Ensures consistency with actual table names (e.g., "publication" not "document").

        Returns:
            Entity name extracted from silver_table or fallback to entity_type.
        """
        silver_table = self._config.table_config.silver_table
        if silver_table and "_" in silver_table:
            return silver_table.split("_", 1)[1]
        if silver_table and "." in silver_table:
            return silver_table.split(".")[-1]
        return silver_table or self._config.entity_type

    def get_dq_context(self) -> DQReportContext | None:
        """Build DQ report context from accumulated data.

        Creates a DQReportContext containing all data collected during
        batch processing. This context is used by PostrunService to
        generate DQ reports for Bronze, Silver, and Gold layers.

        Returns:
            DQReportContext if DQ reporting is enabled and data is available,
            None otherwise.

        Note:
            This method should be called after execute() completes.
            The returned context contains snapshots of the accumulated data.
        """
        if not self._should_collect_dq_data():
            return None

        # Import here to avoid circular dependency
        from bioetl.application.services.dq_report_service import DQReportContext

        silver_data = self._build_dataframe_from_records(self._silver_records_for_dq)
        gold_data = self._build_dataframe_from_records(self._gold_records_for_dq)
        primary_keys = list(self._config.table_config.primary_keys)
        soft_threshold, hard_threshold = self._get_dq_thresholds()
        key_nullability_rules = None
        if self._config.dq_config is not None:
            key_nullability_rules = [
                {
                    "field": rule.field,
                    "key_type": rule.key_type,
                    "nullable": rule.nullable,
                }
                for rule in self._config.dq_config.key_nullability_rules
            ]

        # Get current date for Bronze DQ report filename
        current_date_str = datetime.now(UTC).strftime("%Y-%m-%d")
        dq_entity = self._extract_dq_entity()

        return DQReportContext(
            run_id=str(self._context.run_id),
            pipeline_name=self._config.pipeline_name,
            timestamp=datetime.now(UTC),
            # Provider and entity for DQ report naming
            # Use extracted entity from silver_table for consistency
            provider=self._config.provider,
            entity=dq_entity,
            # Bronze context
            bronze_records=self._bronze_records_for_dq or None,
            bronze_batch_id=self._source_batch_ids[-1]
            if self._source_batch_ids
            else None,
            bronze_source_file=self._last_bronze_path,
            bronze_output_path=self._config.bronze_output_path,
            bronze_date_str=current_date_str,
            # Silver context
            silver_data=silver_data,
            silver_target_table=self._config.table_config.silver_table,
            silver_source_batch_ids=self._source_batch_ids or None,
            silver_primary_keys=primary_keys or None,
            silver_input_count=self.records_fetched,
            silver_quarantined_count=self.records_quarantined,
            silver_output_path=self._config.silver_output_path,
            silver_key_nullability_rules=key_nullability_rules,
            # Gold context
            gold_data=gold_data,
            gold_target_table=self._config.table_config.gold_table,
            gold_output_path=self._config.gold_output_path,
            # DQ thresholds from config (use defaults if not configured)
            dq_soft_threshold=soft_threshold,
            dq_hard_threshold=hard_threshold,
            # Flat structure flag for DQ reports
            flat_structure=self._config.flat_structure,
        )

    def get_run_statistics(self) -> dict[str, Any]:
        """Get aggregated statistics for the entire pipeline run.

        Returns:
            Dictionary with total counts and lists of IDs accumulated
            across all processed batches.
        """
        return {
            "records_fetched": self.records_fetched,
            "records_bronze": self.records_bronze,
            "records_silver": self.records_silver,
            "records_gold": self.records_gold,
            "records_quarantined": self.records_quarantined,
            "records_filtered_out": self.records_filtered_out,
            "source_batch_ids": list(set(self._source_batch_ids)),
        }
