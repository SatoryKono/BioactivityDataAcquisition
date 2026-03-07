"""Batch processing service extracted from BatchExecutor."""

from __future__ import annotations

__all__ = ["BatchProcessingOutput", "BatchProcessingService"]

from dataclasses import dataclass
from typing import TYPE_CHECKING, cast

from bioetl.application.core.batch_processing_service_mixins import (
    _BatchProcessingExecutionMixin,
    _BatchProcessingMetadataMixin,
)
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
    from bioetl.domain.ports import LoggerPort
    from bioetl.domain.value_objects.bronze_result import BronzeWriteResult


@dataclass(frozen=True, slots=True)
class BatchProcessingOutput:
    """Batch-level write/transform output used by BatchExecutor state updates."""

    batch_id: BatchID
    bronze_result: object
    silver_records: list[BronzeRecord]
    gold_records: list[GoldRecord]
    quarantined_count: int
    filtered_out_count: int


class BatchProcessingService(
    _BatchProcessingMetadataMixin, _BatchProcessingExecutionMixin
):
    """Handles extract/transform/write processing for one ETL batch."""

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
        """Initialise batch processing service with required collaborators."""
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
            bronze_result = await self._write_bronze_layer(
                records,
                batch_id,
                ingestion_ts,
                source_metadata,
            )
            transform_result = await self._transform_and_track_metrics(
                records,
                batch_id,
                start_index,
            )
            await self._write_silver_gold_concurrent(
                transform_result,
                batch_id,
                ingestion_ts,
                [cast("BronzeWriteResult", bronze_result)] if bronze_result else None,
            )
            self._finalize_batch_span(span, records, transform_result)

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
