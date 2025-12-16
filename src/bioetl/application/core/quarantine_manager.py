"""Quarantine Manager for ETL Pipelines."""

from typing import TYPE_CHECKING

from bioetl.domain.types import BatchID, ErrorType

if TYPE_CHECKING:
    from bioetl.application.core.base import BasePipeline


class QuarantineManager:
    """Manages quarantining of records that fail processing."""

    def __init__(self, pipeline: "BasePipeline"):
        self.pipeline = pipeline

    async def quarantine_record(
        self,
        record: dict,
        error_type: ErrorType,
        batch_id: BatchID,
        error_details: str,
    ) -> None:
        """Write a record to the quarantine."""
        self.pipeline.quarantine.write(
            pipeline=self.pipeline.pipeline_name,
            error_code=error_type.value,
            payload=record,
            bronze_batch_id=batch_id,
            error_details={"message": error_details},
        )
