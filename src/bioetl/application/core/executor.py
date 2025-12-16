"""Pipeline Executor with batch processing.

Handles the Bronze -> Silver -> Gold data flow with efficient batch writes.
"""

import json
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from prefect import task

from bioetl.application.core.orchestrator import PipelineShutdownError
from bioetl.domain.types import BatchID, Watermark

if TYPE_CHECKING:
    from bioetl.application.core.base import BasePipeline


class PipelineExecutor:
    """Executes the main data processing logic with batch optimization."""

    DEFAULT_BATCH_SIZE = 100
    DEFAULT_CHECKPOINT_INTERVAL = 1000

    def __init__(
        self,
        pipeline: "BasePipeline",
        batch_size: int | None = None,
        checkpoint_interval: int | None = None,
    ):
        self.pipeline = pipeline
        self.batch_size = batch_size or self.DEFAULT_BATCH_SIZE
        self.checkpoint_interval = (
            checkpoint_interval or self.DEFAULT_CHECKPOINT_INTERVAL
        )

        # Counters
        self.records_fetched = 0
        self.records_bronze = 0
        self.records_silver = 0
        self.records_gold = 0
        self.records_quarantined = 0

    @task(name="Execute Pipeline")
    async def execute(self, watermark: Watermark | None) -> None:
        """Execute main pipeline logic with batch processing."""
        batch: list[dict[str, Any]] = []
        batch_id = BatchID(uuid4())
        last_record: dict[str, Any] | None = None

        async for raw_record in self._extract(watermark):
            if self.pipeline.orchestrator.shutdown_requested:
                # Save checkpoint before shutdown
                if last_record:
                    await self.pipeline.checkpoint_manager.save_checkpoint(last_record)
                raise PipelineShutdownError("Shutdown during extraction")

            batch.append(raw_record)
            last_record = raw_record
            self.records_fetched += 1

            # Process batch when full
            if len(batch) >= self.batch_size:
                await self._process_batch(batch, batch_id)
                batch = []
                batch_id = BatchID(uuid4())

            # Checkpoint at intervals
            if self.records_fetched % self.checkpoint_interval == 0:
                await self.pipeline.checkpoint_manager.save_checkpoint(raw_record)

        # Process remaining records
        if batch:
            await self._process_batch(batch, batch_id)

    async def _process_batch(
        self,
        records: list[dict[str, Any]],
        batch_id: BatchID,
    ) -> None:
        """Process a batch of records through Bronze -> Silver -> Gold."""
        # 1. Write all records to Bronze as single batch
        await self._write_bronze_batch(records, batch_id)
        self.records_bronze += len(records)

        # 2. Transform and collect Silver records
        silver_records: list[dict[str, Any]] = []
        gold_records: list[dict[str, Any]] = []

        for raw_record in records:
            record_context = self.pipeline.context.bind_logger(
                batch_id=str(batch_id),
                entity_id=raw_record.get("activity_id"),
            )

            try:
                transformed = await self.pipeline.transform_bronze_to_silver(
                    record_context, raw_record
                )
                if transformed:
                    silver_records.append(transformed)
                    if self.pipeline.should_write_gold(record_context, transformed):
                        gold_records.append(transformed)
            except Exception as e:
                error_type = self.pipeline.error_classifier.classify(e)
                if error_type.is_data_quality():
                    await self.pipeline.quarantine_manager.quarantine_record(
                        raw_record, error_type, batch_id, str(e)
                    )
                    self.records_quarantined += 1
                else:
                    raise

        # 3. Batch write to Silver
        if silver_records:
            await self._write_silver_batch(silver_records, batch_id)
            self.records_silver += len(silver_records)

        # 4. Batch write to Gold
        if gold_records:
            await self._write_gold_batch(gold_records)
            self.records_gold += len(gold_records)

    async def _extract(
        self, watermark: Watermark | None
    ) -> AsyncIterator[dict[str, Any]]:
        """Extract records from data source."""
        async for record in self.pipeline.data_source.fetch(
            entity_type=self.pipeline.entity_type, watermark=watermark
        ):
            yield record

    async def _write_bronze_batch(
        self,
        records: list[dict[str, Any]],
        batch_id: BatchID,
    ) -> None:
        """Write batch of records to Bronze layer."""
        record_bytes = [
            (json.dumps(record) + "\n").encode("utf-8") for record in records
        ]
        self.pipeline.storage.write_bronze(
            records=iter(record_bytes),
            provider=self.pipeline.provider,
            entity=self.pipeline.entity_type,
            date=datetime.now(UTC),
            batch_id=batch_id,
        )

    async def _write_silver_batch(
        self,
        records: list[dict[str, Any]],
        batch_id: BatchID,
    ) -> None:
        """Write batch of records to Silver layer."""
        records_with_meta = [
            {
                **record,
                "_run_id": str(self.pipeline.context.run_id),
                "_run_type": self.pipeline.context.run_type.value,
                "_source_batch_id": str(batch_id),
                "_ingestion_ts": datetime.now(UTC).isoformat(),
            }
            for record in records
        ]
        table_name = f"{self.pipeline.provider}.{self.pipeline.entity_type}"
        self.pipeline.storage.write_silver(
            table_name=table_name,
            records=records_with_meta,
            primary_keys=["entity_id"],
        )

    async def _write_gold_batch(self, records: list[dict[str, Any]]) -> None:
        """Write batch of records to Gold layer."""
        table_name = f"{self.pipeline.provider}.{self.pipeline.entity_type}_gold"
        self.pipeline.storage.write_gold(
            table_name=table_name,
            records=records,
            mode="append",
        )
