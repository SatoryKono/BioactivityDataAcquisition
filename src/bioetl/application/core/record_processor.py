"""Record processing for ETL pipelines.

Handles extraction, transformation, and loading of records.
"""

import json
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from bioetl.domain.ports import (
    DataSourcePort,
    QuarantinePort,
    StoragePort,
)
from bioetl.domain.types import BatchID, ErrorType, RunID, RunType, Watermark

if TYPE_CHECKING:
    import structlog


class PipelineRecordProcessor:
    """Processes records through Bronze → Silver → Gold layers.

    Handles:
    - Extraction from data source
    - Bronze layer writing
    - Silver layer transformation and writing
    - Gold layer filtering and writing
    - Quarantine of failed records
    """

    def __init__(
        self,
        data_source: DataSourcePort,
        storage: StoragePort,
        quarantine: QuarantinePort,
        provider: str,
        entity_type: str,
        pipeline_name: str,
        run_id: RunID,
        run_type: RunType,
        logger: "structlog.BoundLogger",
    ) -> None:
        self.data_source = data_source
        self.storage = storage
        self.quarantine = quarantine
        self.provider = provider
        self.entity_type = entity_type
        self.pipeline_name = pipeline_name
        self.run_id = run_id
        self.run_type = run_type
        self.logger = logger

    async def extract(
        self, watermark: Watermark | None
    ) -> AsyncIterator[dict[str, Any]]:
        """Extract records from data source."""
        async for record in self.data_source.fetch(
            entity_type=self.entity_type, watermark=watermark
        ):
            yield record

    async def load_bronze(self, record: dict[str, Any]) -> BatchID:
        """Write raw record to Bronze layer."""
        batch_id = BatchID(uuid4())
        record_bytes = (json.dumps(record) + "\n").encode("utf-8")
        self.storage.write_bronze(
            records=iter([record_bytes]),
            provider=self.provider,
            entity=self.entity_type,
            date=datetime.now(UTC),
            batch_id=batch_id,
        )
        return batch_id

    async def load_silver(self, record: dict[str, Any], batch_id: BatchID) -> None:
        """Write transformed record to Silver layer."""
        record_with_meta = {
            **record,
            "_run_id": str(self.run_id),
            "_run_type": self.run_type.value,
            "_source_batch_id": str(batch_id),
            "_ingestion_ts": datetime.now(UTC).isoformat(),
        }
        table_name = f"{self.provider}.{self.entity_type}"
        self.storage.write_silver(
            table_name=table_name,
            records=[record_with_meta],
            primary_keys=["entity_id"],
        )

    async def load_gold(self, record: dict[str, Any]) -> None:
        """Write record to Gold layer."""
        table_name = f"{self.provider}.{self.entity_type}_gold"
        self.storage.write_gold(table_name=table_name, records=[record], mode="append")

    async def quarantine_record(
        self,
        record: dict[str, Any],
        error_type: ErrorType,
        batch_id: BatchID,
        error_details: str,
    ) -> None:
        """Send failed record to quarantine."""
        self.quarantine.write(
            pipeline=self.pipeline_name,
            error_code=error_type.value,
            payload=record,
            bronze_batch_id=batch_id,
            error_details={"message": error_details},
        )
