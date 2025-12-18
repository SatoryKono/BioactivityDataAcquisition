"""
Pipeline Executor: orchestrates the data flow from extraction to processing.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any
from uuid import uuid4

from bioetl.application.core.checkpoint_manager import CheckpointManager
from bioetl.application.core.protocols import GoldFilterCallback, TransformCallback
from bioetl.application.core.record_processor import RecordProcessor
from bioetl.application.core.shutdown import PipelineShutdownError, ShutdownSignal
from bioetl.domain.context import PipelineContext
from bioetl.domain.error_classifier import ErrorClassifier
from bioetl.domain.ports import DataSourcePort, StoragePort
from bioetl.domain.types import BatchID, Watermark


class PipelineExecutor:
    """
    Orchestrates the data flow: extracts data, accumulates batches,
    and delegates processing to a RecordProcessor.
    """

    DEFAULT_BATCH_SIZE = 100
    DEFAULT_CHECKPOINT_INTERVAL = 1000

    def __init__(
        self,
        data_source: DataSourcePort,
        storage: StoragePort,
        checkpoint_manager: CheckpointManager,
        quarantine_manager: Any,  # Using 'Any' to avoid circular import if QuarantineManager is in this file
        error_classifier: ErrorClassifier,
        context: PipelineContext,
        shutdown_signal: ShutdownSignal,
        provider: str,
        entity_type: str,
        transform_callback: TransformCallback,
        gold_filter_callback: GoldFilterCallback,
        silver_schema: Any,
        batch_size: int | None = None,
        checkpoint_interval: int | None = None,
    ):
        self._data_source = data_source
        self._checkpoint_manager = checkpoint_manager
        self._shutdown_signal = shutdown_signal
        self._entity_type = entity_type
        self.batch_size = batch_size or self.DEFAULT_BATCH_SIZE
        self.checkpoint_interval = (
            checkpoint_interval or self.DEFAULT_CHECKPOINT_INTERVAL
        )

        self._record_processor = RecordProcessor(
            storage=storage,
            quarantine_manager=quarantine_manager,
            error_classifier=error_classifier,
            context=context,
            provider=provider,
            entity_type=entity_type,
            transform_callback=transform_callback,
            gold_filter_callback=gold_filter_callback,
            silver_schema=silver_schema,
        )

        # Counters
        self.records_fetched = 0
        self.records_bronze = 0
        self.records_silver = 0
        self.records_gold = 0
        self.records_quarantined = 0

    async def execute(self, watermark: Watermark | None, limit: int | None) -> None:
        batch: list[dict[str, Any]] = []
        last_record: dict[str, Any] | None = None

        async for raw_record in self._extract(watermark, limit):
            if self._shutdown_signal.is_requested:
                if last_record:
                    await self._checkpoint_manager.save_checkpoint(
                        last_record, self.records_fetched
                    )
                raise PipelineShutdownError("Shutdown during extraction")

            batch.append(raw_record)
            last_record = raw_record
            self.records_fetched += 1

            if len(batch) >= self.batch_size:
                await self._process_and_update_counts(batch)
                batch = []

            if self.records_fetched % self.checkpoint_interval == 0:
                await self._checkpoint_manager.save_checkpoint(
                    raw_record, self.records_fetched
                )

        if batch:
            await self._process_and_update_counts(batch)

    async def _process_and_update_counts(self, batch: list[dict[str, Any]]) -> None:
        bronze, silver, gold, quarantined = await self._record_processor.process_batch(
            records=batch, batch_id=BatchID(uuid4())
        )
        self.records_bronze += bronze
        self.records_silver += silver
        self.records_gold += gold
        self.records_quarantined += quarantined

    async def _extract(
        self, watermark: Watermark | None, limit: int | None
    ) -> AsyncIterator[dict[str, Any]]:
        async for record in self._data_source.fetch(
            entity_type=self._entity_type,
            watermark=watermark,
            limit=limit,
        ):
            yield record
