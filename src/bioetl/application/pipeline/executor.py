"""Pipeline Executor.

Handles the Bronze -> Silver -> Gold data flow.
"""

import json
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from prefect import task

from bioetl.application.pipeline.orchestrator import PipelineShutdownError
from bioetl.domain.types import BatchID, Watermark

if TYPE_CHECKING:
    from bioetl.application.pipeline.base import BasePipeline


class PipelineExecutor:
    """Executes the main data processing logic of the pipeline."""

    def __init__(self, pipeline: "BasePipeline"):
        self.pipeline = pipeline
        self.records_fetched = 0
        self.records_bronze = 0
        self.records_silver = 0
        self.records_gold = 0
        self.records_quarantined = 0

    @task(name="Execute Pipeline")
    async def execute(self, watermark: Watermark | None) -> None:
        """Execute main pipeline logic as a Prefect task."""
        async for raw_record in self._extract(watermark):
            if self.pipeline.orchestrator.shutdown_requested:
                raise PipelineShutdownError("Shutdown during extraction")

            self.records_fetched += 1
            batch_id = await self._write_bronze(raw_record)
            self.records_bronze += 1

            # Create a new context for this record
            record_context = self.pipeline.context.bind_logger(
                batch_id=str(batch_id),
                entity_id=raw_record.get("activity_id"),
            )

            try:
                transformed = await self.pipeline.transform_bronze_to_silver(
                    record_context, raw_record
                )
                if transformed:
                    await self._write_silver(transformed, batch_id)
                    self.records_silver += 1
                    if self.pipeline.should_write_gold(record_context, transformed):
                        await self._write_gold(transformed)
                        self.records_gold += 1
            except Exception as e:
                error_type = self.pipeline.error_classifier.classify(e)
                if error_type.is_data_quality():
                    await self.pipeline.quarantine_manager.quarantine_record(
                        raw_record, error_type, batch_id, str(e)
                    )
                    self.records_quarantined += 1
                else:
                    raise

            if self.records_fetched % 1000 == 0:
                await self.pipeline.checkpoint_manager.save_checkpoint(raw_record)

    async def _extract(
        self, watermark: Watermark | None
    ) -> AsyncIterator[dict[str, Any]]:
        async for record in self.pipeline.data_source.fetch(
            entity_type=self.pipeline.entity_type, watermark=watermark
        ):
            yield record

    async def _write_bronze(self, record: dict[str, Any]) -> BatchID:
        batch_id = BatchID(uuid4())
        record_bytes = (json.dumps(record) + "\n").encode("utf-8")
        self.pipeline.storage.write_bronze(
            records=iter([record_bytes]),
            provider=self.pipeline.provider,
            entity=self.pipeline.entity_type,
            date=datetime.now(UTC),
            batch_id=batch_id,
        )
        return batch_id

    async def _write_silver(self, record: dict[str, Any], batch_id: BatchID) -> None:
        record_with_meta = {
            **record,
            "_run_id": str(self.pipeline.context.run_id),
            "_run_type": self.pipeline.context.run_type.value,
            "_source_batch_id": str(batch_id),
            "_ingestion_ts": datetime.now(UTC).isoformat(),
        }
        table_name = f"{self.pipeline.provider}.{self.pipeline.entity_type}"
        self.pipeline.storage.write_silver(
            table_name=table_name,
            records=[record_with_meta],
            primary_keys=["entity_id"],
        )

    async def _write_gold(self, record: dict[str, Any]) -> None:
        table_name = f"{self.pipeline.provider}.{self.pipeline.entity_type}_gold"
        self.pipeline.storage.write_gold(
            table_name=table_name, records=[record], mode="append"
        )
