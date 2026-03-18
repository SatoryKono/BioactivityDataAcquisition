"""Batch processing service extracted from BatchExecutor."""

from __future__ import annotations

__all__ = [
    "BatchProcessingComponents",
    "BatchProcessingOutcome",
    "BatchProcessingService",
]

from dataclasses import dataclass
from typing import TYPE_CHECKING, cast

from bioetl.application.core.batch_processing_contracts import BatchProcessingOutcome
from bioetl.application.core.batch_processing_service_mixins import (
    _BatchProcessingExecutionMixin,
    _BatchProcessingMetadataMixin,
)
from bioetl.domain.ports import BatchIdGeneratorPort
from bioetl.domain.types import BronzeRecord

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from bioetl.application.core.batch_metrics import BatchMetricsRecorderService
    from bioetl.application.core.batch_tracing import BatchTracingManagerService
    from bioetl.application.core.batch_transformer import BatchTransformer
    from bioetl.application.core.batch_writer import BatchWriter
    from bioetl.application.core.config import RecordProcessorConfig
    from bioetl.application.core.pipeline_services import PipelineService
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.value_objects.bronze_result import BronzeWriteResult


@dataclass(frozen=True, slots=True)
class BatchProcessingComponents:
    """Injected components shared by RecordProcessor and BatchExecutor."""

    batch_metrics: BatchMetricsRecorderService
    transformer: BatchTransformer
    writer: BatchWriter


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
        components: BatchProcessingComponents,
        tracing_manager: BatchTracingManagerService,
        batch_id_factory: BatchIdGeneratorPort,
    ) -> None:
        """Initialise batch processing service with required collaborators."""
        self._services = services
        self._context = context
        self._config = config
        self._logger = context.logger
        self._batch_metrics = components.batch_metrics
        self._transformer = components.transformer
        self._writer = components.writer
        self._tracing = tracing_manager
        self._batch_id_factory = batch_id_factory

    async def extract_records(
        self,
        *,
        limit: int | None,
        query: str | None = None,
        offset: int | None = None,
    ) -> AsyncIterator[BronzeRecord]:
        """Extract records from source adapter for configured entity.

        Args:
            limit: Maximum number of records to yield, or None for all.
            query: Optional query string forwarded to the data source.
            offset: Optional pagination offset for resuming extraction.
        """
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
    ) -> BatchProcessingOutcome:
        """Process one batch through Bronze, Silver, and Gold writes.

        Args:
            records: List of raw Bronze records to process.
            start_index: Absolute record index of the first record in this batch.
            query_string: Query string used to fetch these records, for logging context.

        Returns:
            BatchProcessingOutcome with write counts and source batch ID.
        """
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

            return BatchProcessingOutcome(
                batch_id=batch_id,
                bronze_result=cast("BronzeWriteResult | None", bronze_result),
                silver_records=transform_result.silver_records,
                gold_records=transform_result.gold_records,
                quarantined_count=transform_result.quarantined_count,
                filtered_out_count=transform_result.filtered_out_count,
            )
        except self._PIPELINE_EXECUTION_ERRORS as error:
            self._tracing.end_span(span, error)
            raise
