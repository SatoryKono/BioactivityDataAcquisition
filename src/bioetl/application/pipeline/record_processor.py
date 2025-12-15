"""Record processor for ETL pipelines.

Handles Bronze/Silver/Gold layer loading and quarantine operations.
"""

import json
from datetime import UTC, datetime
from logging import Logger
from typing import Any
from uuid import uuid4

from bioetl.domain.ports import QuarantinePort, StoragePort
from bioetl.domain.types import BatchID, ErrorType, RunID, RunType


class RecordProcessor:
    """Processes records through Bronze/Silver/Gold layers.

    Responsibilities:
    - Load raw records to Bronze layer
    - Load transformed records to Silver layer
    - Load filtered records to Gold layer
    - Handle quarantine for failed records
    - Classify errors for proper handling
    """

    def __init__(
        self,
        storage: StoragePort,
        quarantine: QuarantinePort,
        provider: str,
        entity_type: str,
        pipeline_name: str,
        run_id: RunID,
        run_type: RunType,
        logger: Logger,
    ) -> None:
        self._storage = storage
        self._quarantine = quarantine
        self._provider = provider
        self._entity_type = entity_type
        self._pipeline_name = pipeline_name
        self._run_id = run_id
        self._run_type = run_type
        self._logger = logger

    def load_bronze(self, record: dict[str, Any]) -> BatchID:
        """Load raw record to Bronze layer.

        Args:
            record: Raw record from data source

        Returns:
            BatchID for tracking lineage
        """
        batch_id = BatchID(uuid4())
        record_bytes = (json.dumps(record) + "\n").encode("utf-8")
        self._storage.write_bronze(
            records=iter([record_bytes]),
            provider=self._provider,
            entity=self._entity_type,
            date=datetime.now(UTC),
            batch_id=batch_id,
        )
        return batch_id

    def load_silver(self, record: dict[str, Any], batch_id: BatchID) -> None:
        """Load transformed record to Silver layer.

        Args:
            record: Transformed record
            batch_id: Source batch ID for lineage
        """
        record_with_meta = {
            **record,
            "_run_id": str(self._run_id),
            "_run_type": self._run_type.value,
            "_source_batch_id": str(batch_id),
            "_ingestion_ts": datetime.now(UTC).isoformat(),
        }
        table_name = f"{self._provider}.{self._entity_type}"
        self._storage.write_silver(
            table_name=table_name,
            records=[record_with_meta],
            primary_keys=["entity_id"],
        )

    def load_gold(self, record: dict[str, Any]) -> None:
        """Load record to Gold layer.

        Args:
            record: Record that passed quality filters
        """
        table_name = f"{self._provider}.{self._entity_type}_gold"
        self._storage.write_gold(table_name=table_name, records=[record], mode="append")

    def quarantine_record(
        self,
        record: dict[str, Any],
        error_type: ErrorType,
        batch_id: BatchID,
        error_details: str,
    ) -> None:
        """Send failed record to quarantine.

        Args:
            record: Failed record
            error_type: Classification of the error
            batch_id: Source batch ID
            error_details: Error message
        """
        self._quarantine.write(
            pipeline=self._pipeline_name,
            error_code=error_type.value,
            payload=record,
            bronze_batch_id=batch_id,
            error_details={"message": error_details},
        )

    @staticmethod
    def classify_error(error: Exception) -> ErrorType:
        """Classify error for proper handling.

        Args:
            error: Exception that occurred

        Returns:
            ErrorType classification
        """
        error_name = type(error).__name__
        if "Schema" in error_name or "Validation" in error_name:
            return ErrorType.SCHEMA_VIOLATION
        elif "Missing" in error_name or "Required" in error_name:
            return ErrorType.MISSING_REQUIRED_FIELD
        else:
            return ErrorType.INVALID_DATA
