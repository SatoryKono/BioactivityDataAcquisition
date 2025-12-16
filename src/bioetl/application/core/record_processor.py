"""
Processes a batch of records through the Bronze, Silver, and Gold layers.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from bioetl.application.core.protocols import GoldFilterCallback, TransformCallback
from bioetl.application.core.quarantine_manager import QuarantineManager
from bioetl.domain.context import PipelineContext
from bioetl.domain.error_classifier import ErrorClassifier
from bioetl.domain.ports import StoragePort
from bioetl.domain.types import BatchID

if TYPE_CHECKING:
    pass


class RecordProcessor:
    """
    Handles the transformation and writing of a single batch of records.
    This class contains the core ETL logic for a batch.
    """

    def __init__(
        self,
        storage: StoragePort,
        quarantine_manager: QuarantineManager,
        error_classifier: ErrorClassifier,
        context: PipelineContext,
        provider: str,
        entity_type: str,
        transform_callback: TransformCallback,
        gold_filter_callback: GoldFilterCallback,
    ):
        self._storage = storage
        self._quarantine_manager = quarantine_manager
        self._error_classifier = error_classifier
        self._context = context
        self._provider = provider
        self._entity_type = entity_type
        self._transform = transform_callback
        self._gold_filter = gold_filter_callback

    async def process_batch(
        self,
        records: list[dict[str, Any]],
        batch_id: BatchID,
    ) -> tuple[int, int, int, int]:
        """Process a batch of records through Bronze -> Silver -> Gold."""
        # 1. Write to Bronze
        await self._write_bronze_batch(records, batch_id)
        records_bronze = len(records)

        # 2. Transform and collect Silver/Gold
        silver_records: list[dict[str, Any]] = []
        gold_records: list[dict[str, Any]] = []
        records_quarantined = 0

        for raw_record in records:
            record_context = self._context.bind_logger(
                batch_id=str(batch_id),
                entity_id=raw_record.get("activity_id"),
            )
            try:
                transformed = await self._transform(record_context, raw_record)
                if transformed:
                    silver_records.append(transformed)
                    if self._gold_filter(record_context, transformed):
                        gold_records.append(transformed)
            except Exception as e:
                error_type = self._error_classifier.classify(e)
                if error_type.is_data_quality():
                    await self._quarantine_manager.quarantine_record(
                        raw_record, error_type, batch_id, str(e)
                    )
                    records_quarantined += 1
                else:
                    raise

        # 3. Write to Silver
        if silver_records:
            await self._write_silver_batch(silver_records, batch_id)

        # 4. Write to Gold
        if gold_records:
            await self._write_gold_batch(gold_records)

        return (
            records_bronze,
            len(silver_records),
            len(gold_records),
            records_quarantined,
        )

    async def _write_bronze_batch(
        self, records: list[dict[str, Any]], batch_id: BatchID
    ) -> None:
        record_bytes = [(json.dumps(r) + "\n").encode("utf-8") for r in records]
        await self._storage.write_bronze(
            records=iter(record_bytes),
            provider=self._provider,
            entity=self._entity_type,
            date=datetime.now(UTC),
            batch_id=batch_id,
        )

    async def _write_silver_batch(
        self, records: list[dict[str, Any]], batch_id: BatchID
    ) -> None:
        records_with_meta = [
            {
                **r,
                "_run_id": str(self._context.run_id),
                "_run_type": self._context.run_type.value,
                "_source_batch_id": str(batch_id),
                "_ingestion_ts": datetime.now(UTC).isoformat(),
            }
            for r in records
        ]
        table_name = f"{self._provider}.{self._entity_type}"
        await self._storage.write_silver(
            table_name=table_name,
            records=records_with_meta,
            primary_keys=["entity_id"],
        )

    async def _write_gold_batch(self, records: list[dict[str, Any]]) -> None:
        table_name = f"{self._provider}.{self._entity_type}_gold"
        await self._storage.write_gold(
            table_name=table_name, records=records, mode="append"
        )
