"""Batch processing service extracted from BatchExecutor."""

from __future__ import annotations

__all__ = ["BatchProcessingOutput", "BatchProcessingService"]


import asyncio
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from bioetl.application.core.batch_transformer import TransformResult
from bioetl.domain.exceptions import BioETLError
from bioetl.domain.ports import BatchIdGeneratorPort
from bioetl.domain.types import BatchID, BronzeRecord, GoldRecord

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from bioetl.application.core.batch_metrics import BatchMetricsRecorderService
    from bioetl.application.core.batch_tracing import BatchTracingManagerService
    from bioetl.application.core.batch_transformer import BatchTransformer
    from bioetl.application.core.batch_writer import BatchWriter
    from bioetl.application.core.config import RecordProcessorConfig
    from bioetl.application.core.pipeline_services import PipelineService
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.models.metadata import SourceMetadata
    from bioetl.domain.ports import LoggerPort


@dataclass(frozen=True, slots=True)
class BatchProcessingOutput:
    """Batch-level write/transform output used by BatchExecutor state updates."""

    batch_id: BatchID
    bronze_result: object
    silver_records: list[BronzeRecord]
    gold_records: list[GoldRecord]
    quarantined_count: int
    filtered_out_count: int


class BatchProcessingService:
    """Handles extract/transform/write processing for one ETL batch."""

    _PIPELINE_EXECUTION_ERRORS = (
        BioETLError,
        OSError,
        RuntimeError,
        ValueError,
        TypeError,
        KeyError,
        AttributeError,
    )
    _SOURCE_METADATA_ERRORS = (
        BioETLError,
        OSError,
        RuntimeError,
        ValueError,
        TypeError,
        AttributeError,
    )

    def __init__(
        self,
        *,
        services: PipelineService,
        context: PipelineContext,
        config: RecordProcessorConfig,
        logger: LoggerPort,
        batch_metrics: BatchMetricsRecorderService,
        transformer: BatchTransformer,
        writer: BatchWriter,
        tracing_manager: BatchTracingManagerService,
        batch_id_factory: BatchIdGeneratorPort,
    ) -> None:
        self._services = services
        self._context = context
        self._config = config
        self._logger = logger
        self._batch_metrics = batch_metrics
        self._transformer = transformer
        self._writer = writer
        self._tracing = tracing_manager
        self._batch_id_factory = batch_id_factory

    def set_batch_id_factory(self, batch_id_factory: BatchIdGeneratorPort) -> None:
        """Replace batch ID generator used for subsequent processed batches."""
        self._batch_id_factory = batch_id_factory

    async def extract_records(
        self,
        *,
        limit: int | None,
        query: str | None = None,
        offset: int | None = None,
    ) -> AsyncIterator[BronzeRecord]:
        """Extract records from source adapter for configured entity."""
        async for record in self._services.data_source.fetch(
            entity_type=self._config.entity_type,
            limit=limit,
            query=query,
            offset=offset,
        ):
            yield record

    async def process_batch(
        self,
        *,
        records: list[BronzeRecord],
        start_index: int,
        query_string: str | None,
    ) -> BatchProcessingOutput:
        """Process one batch through Bronze, Silver, and Gold writes."""
        batch_id = self._batch_id_factory.create()
        ingestion_ts = self._context.started_at
        source_metadata = self._get_source_metadata(query_string)
        span = self._tracing.start_batch_span(batch_id, len(records), start_index)

        try:
            bronze_result = await self._execute_with_span(
                "write_bronze",
                self._writer.write_bronze(
                    records,
                    batch_id,
                    ingestion_ts,
                    source_metadata=source_metadata,
                ),
                batch_id,
                len(records),
                on_error=lambda error: self._writer.log_and_track_write_error(
                    "bronze", error, batch_id
                ),
            )
            self._batch_metrics.track_batch_size("bronze", len(records))
            self._batch_metrics.track_processed_records("bronze", len(records))

            transform_result = await self._execute_transform_with_span(
                records,
                batch_id,
                start_index,
            )
            self._batch_metrics.track_processed_records(
                "quarantined",
                transform_result.quarantined_count,
            )
            self._batch_metrics.track_processed_records(
                "silver",
                len(transform_result.silver_records),
            )
            self._batch_metrics.track_processed_records(
                "gold",
                len(transform_result.gold_records),
            )

            # Fire Silver and Gold writes concurrently — they target
            # independent Delta tables and silver_refs is only a lineage
            # reference, not a data dependency.
            bronze_refs = [bronze_result] if bronze_result else None
            write_coros = []

            if transform_result.silver_records:
                write_coros.append(
                    self._execute_with_span(
                        "write_silver",
                        self._writer.write_silver(
                            transform_result.silver_records,
                            batch_id,
                            ingestion_ts,
                            bronze_refs=bronze_refs,
                        ),
                        batch_id,
                        len(transform_result.silver_records),
                        on_error=lambda error: self._writer.log_and_track_write_error(
                            "silver", error, batch_id
                        ),
                    )
                )

            if transform_result.gold_records:
                write_coros.append(
                    self._execute_with_span(
                        "write_gold",
                        self._writer.write_gold(transform_result.gold_records),
                        batch_id,
                        len(transform_result.gold_records),
                        on_error=lambda error: self._writer.log_and_track_write_error(
                            "gold", error, batch_id
                        ),
                    )
                )

            if write_coros:
                await asyncio.gather(*write_coros)

            self._tracing.set_batch_result(
                span,
                bronze_count=len(records),
                silver_count=len(transform_result.silver_records),
                gold_count=len(transform_result.gold_records),
                quarantined_count=transform_result.quarantined_count,
            )

            return BatchProcessingOutput(
                batch_id=batch_id,
                bronze_result=bronze_result,
                silver_records=transform_result.silver_records,
                gold_records=transform_result.gold_records,
                quarantined_count=transform_result.quarantined_count,
                filtered_out_count=transform_result.filtered_out_count,
            )
        except self._PIPELINE_EXECUTION_ERRORS as error:
            self._tracing.end_span(span, error)
            raise
        else:
            self._tracing.end_span(span)

    def _get_source_metadata(self, query_string: str | None) -> SourceMetadata | None:
        """Get source metadata and enrich it with query string when available."""
        from bioetl.domain.models.metadata import SourceMetadata

        source_metadata: SourceMetadata | None = None
        data_source = self._services.data_source
        get_metadata = getattr(data_source, "get_source_metadata", None)
        if get_metadata is not None and callable(get_metadata):
            try:
                result = get_metadata()
                if isinstance(result, SourceMetadata):
                    source_metadata = result
            except self._SOURCE_METADATA_ERRORS as metadata_error:
                self._logger.warning(
                    "Source metadata collection failed",
                    error_type=type(metadata_error).__name__,
                    reason="source_metadata_collection_failed",
                )

        if query_string:
            if source_metadata is not None:
                if source_metadata.query_string is None:
                    source_metadata = source_metadata.model_copy(
                        update={"query_string": query_string}
                    )
            else:
                source_metadata = SourceMetadata(type="api", query_string=query_string)

        return source_metadata

    async def _execute_with_span(
        self,
        name: str,
        coro: Any,  # Any: Awaitable return type varies by storage layer
        batch_id: BatchID,
        count: int,
        on_error: Any = None,  # Any: callback return type varies
    ) -> Any:  # Any: return type depends on storage layer callback
        """Execute coroutine wrapped with per-layer tracing span."""
        span = self._tracing.start_layer_span(name, batch_id, count)
        try:
            result = await coro
            self._tracing.end_span(span)
            return result
        except self._PIPELINE_EXECUTION_ERRORS as error:
            self._tracing.end_span(span, error)
            if on_error:
                on_error(error)
            raise

    async def _execute_transform_with_span(
        self,
        records: list[BronzeRecord],
        batch_id: BatchID,
        start_index: int,
    ) -> TransformResult:
        """Execute transform stage and attach output metrics to span."""
        span = self._tracing.start_layer_span(
            "transform",
            batch_id,
            len(records),
            input_count=True,
        )
        try:
            result = await self._transformer.transform_batch(
                records,
                batch_id,
                start_index=start_index,
            )
            self._tracing.set_transform_result(
                span,
                silver_count=len(result.silver_records),
                gold_count=len(result.gold_records),
                quarantined_count=result.quarantined_count,
            )
            self._tracing.end_span(span)
            return result
        except self._PIPELINE_EXECUTION_ERRORS as error:
            self._tracing.end_span(span, error)
            raise
