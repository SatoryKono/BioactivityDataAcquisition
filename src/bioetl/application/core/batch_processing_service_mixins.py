"""Internal mixins for BatchProcessingService helpers."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

from bioetl.application.core.batch_transformer import TransformResult
from bioetl.domain.exceptions import BioETLError
from bioetl.domain.types import BatchID, BronzeRecord

if TYPE_CHECKING:
    from opentelemetry.trace import Span

    from bioetl.application.core.batch_metrics import BatchMetricsRecorderService
    from bioetl.application.core.batch_tracing import BatchTracingManagerService
    from bioetl.application.core.batch_transformer import BatchTransformer
    from bioetl.application.core.batch_writer import BatchWriter
    from bioetl.application.core.config import RecordProcessorConfig
    from bioetl.application.core.pipeline_services import PipelineService
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.models.metadata import SourceMetadata
    from bioetl.domain.ports import BatchIdGeneratorPort, LoggerPort
    from bioetl.domain.value_objects.bronze_result import BronzeWriteResult


class _BatchProcessingServiceAttrs:
    """Typed dependency surface for BatchProcessingService mixins."""

    __slots__ = ()

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

    _services: PipelineService
    _context: PipelineContext
    _config: RecordProcessorConfig
    _logger: LoggerPort
    _batch_metrics: BatchMetricsRecorderService
    _transformer: BatchTransformer
    _writer: BatchWriter
    _tracing: BatchTracingManagerService
    _batch_id_factory: BatchIdGeneratorPort


class _BatchProcessingMetadataMixin(_BatchProcessingServiceAttrs):
    """Source metadata retrieval/enrichment helpers."""

    __slots__ = ()

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


class _BatchProcessingExecutionMixin(_BatchProcessingServiceAttrs):
    """Transform/write/span helper methods used by process_batch."""

    __slots__ = ()

    async def _write_bronze_layer(
        self,
        records: list[BronzeRecord],
        batch_id: BatchID,
        ingestion_ts: Any,  # Any: timestamp type from PipelineContext
        source_metadata: SourceMetadata | None,
    ) -> object:
        """Write records to Bronze layer and track batch metrics."""
        result = await self._execute_with_span(
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
        return result

    async def _transform_and_track_metrics(
        self,
        records: list[BronzeRecord],
        batch_id: BatchID,
        start_index: int,
    ) -> TransformResult:
        """Execute transform stage and track per-layer record counts."""
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
        return transform_result

    async def _write_silver_gold_concurrent(
        self,
        transform_result: TransformResult,
        batch_id: BatchID,
        ingestion_ts: Any,  # Any: timestamp type from PipelineContext
        bronze_refs: list[BronzeWriteResult] | None,
    ) -> None:
        """Fire Silver and Gold writes concurrently to independent Delta tables."""
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

    def _finalize_batch_span(
        self,
        span: Span | None,
        records: list[BronzeRecord],
        transform_result: TransformResult,
    ) -> None:
        """Set batch result on tracing span and close it."""
        self._tracing.set_batch_result(
            span,
            bronze_count=len(records),
            silver_count=len(transform_result.silver_records),
            gold_count=len(transform_result.gold_records),
            quarantined_count=transform_result.quarantined_count,
        )
        self._tracing.end_span(span)

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
