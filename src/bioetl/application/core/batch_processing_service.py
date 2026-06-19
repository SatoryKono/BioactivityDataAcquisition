"""Batch processing service extracted from BatchExecutor."""

from __future__ import annotations

__all__ = [
    "BatchProcessingComponents",
    "BatchProcessingOutcome",
    "BatchProcessingService",
]

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, cast

from bioetl.application.core.batch_processing_contracts import BatchProcessingOutcome
from bioetl.application.core.batch_processing_runtime import (
    build_bronze_refs,
    execute_with_pipeline_failure_policy,
)
from bioetl.application.core.batch_processing_support import (
    BatchProcessingSupportService,
)
from bioetl.domain.aggregates.batch import Batch
from bioetl.domain.models.metadata import SourceMetadata
from bioetl.domain.ports import BatchIdGeneratorPort
from bioetl.domain.types import BatchID, BronzeRecord

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from opentelemetry.trace import Span

    from bioetl.application.core.batch_metrics import BatchMetricsRecorderService
    from bioetl.application.core.batch_tracing import BatchTracingManagerService
    from bioetl.application.core.batch_transformer import BatchTransformer
    from bioetl.application.core.batch_writer import BatchWriter
    from bioetl.application.core.pipeline_runtime_service_protocols import (
        PipelineDataSourceServicesProtocol,
    )
    from bioetl.application.core.record_processor_config import RecordProcessorConfig
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.value_objects.bronze_result import BronzeWriteResult


@dataclass(frozen=True, slots=True)
class BatchProcessingComponents:
    """Injected components shared by RecordProcessor and BatchExecutor."""

    batch_metrics: BatchMetricsRecorderService
    transformer: BatchTransformer
    writer: BatchWriter


class BatchProcessingService:
    """Handles extract/transform/write processing for one ETL batch."""

    def __init__(
        self,
        *,
        services: PipelineDataSourceServicesProtocol,
        context: PipelineContext,
        config: RecordProcessorConfig,
        components: BatchProcessingComponents,
        tracing_manager: BatchTracingManagerService,
        batch_id_factory: BatchIdGeneratorPort,
        support_service: BatchProcessingSupportService,
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
        self._support = support_service

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
        batch = Batch.open_with_id(
            batch_id=batch_id,
            run_id=self._context.run_id,
            records=records,
            start_index=start_index,
            created_at=ingestion_ts,
        )
        source_metadata = self._get_source_metadata(query_string)
        span = self._tracing.start_batch_span(batch_id, len(records), start_index)
        self._batch_metrics.track_records_fetched(len(records))
        self._batch_metrics.track_batch_created(stage="bronze", count=len(records))
        self._publish_batch_events(batch)

        return cast(
            "BatchProcessingOutcome",
            await execute_with_pipeline_failure_policy(
                tracing=self._tracing,
                span=span,
                work_coro=self._process_batch_work(
                    records=records,
                    batch_id=batch_id,
                    batch=batch,
                    start_index=start_index,
                    ingestion_ts=ingestion_ts,
                    source_metadata=source_metadata,
                    span=span,
                ),
            ),
        )

    def _get_source_metadata(
        self,
        query_string: str | None,
    ) -> SourceMetadata | None:
        """Delegate source metadata retrieval through the support service."""
        return self._support.get_source_metadata(query_string)

    @property
    def debug_export_service(self) -> object | None:
        """Expose the optional debug export collaborator to the executor."""
        return getattr(self._support, "_debug_export_service", None)

    async def _process_batch_work(
        self,
        *,
        records: list[BronzeRecord],
        batch_id: BatchID,
        batch: Batch,
        start_index: int,
        ingestion_ts: datetime,
        source_metadata: SourceMetadata | None,
        span: Span | None,
    ) -> BatchProcessingOutcome:
        """Run the explicit Bronze/transform/Silver/Gold batch choreography."""
        bronze_result = await self._support.write_bronze_layer(
            records=records,
            batch_id=batch_id,
            start_index=start_index,
            ingestion_ts=ingestion_ts,
            source_metadata=source_metadata,
        )
        transform_result = await self._support.transform_and_track_metrics(
            records=records,
            batch_id=batch_id,
            start_index=start_index,
        )
        batch.seal_with_counts(
            record_count=len(records),
            valid_count=max(
                len(records)
                - transform_result.quarantined_count
                - transform_result.filtered_out_count,
                0,
            ),
            quarantined_count=transform_result.quarantined_count,
            sealed_at=ingestion_ts,
        )
        self._publish_batch_events(batch)
        await self._support.write_silver_gold_concurrent(
            transform_result=transform_result,
            batch_id=batch_id,
            ingestion_ts=ingestion_ts,
            bronze_refs=build_bronze_refs(bronze_result),
        )
        self._tracing.set_batch_result(
            span,
            bronze_count=len(records),
            silver_count=len(transform_result.silver_records),
            gold_count=len(transform_result.gold_records),
            quarantined_count=transform_result.quarantined_count,
        )
        self._tracing.end_span(span)
        return BatchProcessingOutcome(
            batch_id=batch_id,
            bronze_result=cast("BronzeWriteResult | None", bronze_result),
            silver_records=transform_result.silver_records,
            gold_records=transform_result.gold_records,
            quarantined_count=transform_result.quarantined_count,
            filtered_out_count=transform_result.filtered_out_count,
            gold_excluded_by_contract_count=(
                transform_result.gold_excluded_by_contract_count
            ),
        )

    def _publish_batch_events(self, batch: Batch) -> None:
        """Publish domain events collected from the Batch aggregate."""
        for event in batch.collect_events():
            self._support.emit_domain_event(event)
