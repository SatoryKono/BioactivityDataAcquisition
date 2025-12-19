"""Quarantine Manager for ETL Pipelines.

Refactored per ADR-0005 to accept explicit dependencies instead of full pipeline.
"""

from typing import Any

from bioetl.domain.ports import QuarantinePort
from bioetl.domain.types import BatchID, ErrorType


class QuarantineManager:
    """Manages quarantining of records that fail processing.

    This manager handles writing failed records to quarantine storage
    for later analysis and potential reprocessing.
    """

    def __init__(
        self,
        quarantine_port: QuarantinePort,
        pipeline_name: str,
    ) -> None:
        """Initialize QuarantineManager with explicit dependencies.

        Args:
            quarantine_port: Port for writing to quarantine storage.
            pipeline_name: Name of the pipeline for identification.
        """
        self._quarantine = quarantine_port
        self._pipeline_name = pipeline_name

    async def quarantine_record(
        self,
        record: dict[str, Any],
        error_type: ErrorType,
        batch_id: BatchID,
        error_details: str,
    ) -> None:
        """Write a record to the quarantine.

        Args:
            record: The raw record that failed processing.
            error_type: Classification of the error.
            batch_id: ID of the batch containing this record.
            error_details: Human-readable error description.
        """
        await self._quarantine.write(
            pipeline=self._pipeline_name,
            error_code=error_type.value,
            payload=record,
            bronze_batch_id=batch_id,
            metadata={"error_details": {"message": error_details}},
        )
