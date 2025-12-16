"""Unified quarantine entry point.

Re-exports UnifiedQuarantine for backward compatibility while using the decomposed architecture.
"""
from typing import Any, Iterator

from bioetl.domain.types import BatchID, ContentHash, DQStatus
from bioetl.infrastructure.quarantine.repository import QuarantineRepository
from bioetl.infrastructure.quarantine.service import QuarantineService


class UnifiedQuarantine:
    """Unified quarantine table for failed records.

    Facade for QuarantineService and QuarantineRepository.
    Keeps API compatibility with previous implementation.
    """

    # Maximum payload size (64KB) - kept for compatibility
    MAX_PAYLOAD_SIZE = QuarantineService.MAX_PAYLOAD_SIZE

    def __init__(
        self,
        base_path: str,
        storage_options: dict[str, str] | None = None,
    ) -> None:
        self.repository = QuarantineRepository(base_path, storage_options)
        self.service = QuarantineService(self.repository)

    def write(
        self,
        pipeline: str,
        error_code: str,
        payload: dict[str, Any],
        bronze_batch_id: BatchID,
        bronze_file_uri: str | None = None,
        error_details: dict[str, Any] | None = None,
    ) -> ContentHash:
        return self.service.write_record(
            pipeline, error_code, payload, bronze_batch_id, bronze_file_uri, error_details
        )

    def inspect(
        self,
        pipeline: str,
        limit: int = 100,
        error_code: str | None = None,
        dq_status: DQStatus | None = None,
    ) -> list[dict[str, Any]]:
        return self.service.inspect_records(pipeline, limit, error_code, dq_status)

    def replay(
        self,
        pipeline: str,
        error_code: str | None = None,
        max_age_days: int = 7,
    ) -> Iterator[dict[str, Any]]:
        return self.service.replay_records(pipeline, error_code, max_age_days)

    def purge(self, pipeline: str, older_than_days: int = 30) -> int:
        return self.service.purge_old_records(pipeline, older_than_days)

    def update_status(
        self,
        payload_hash: str,
        new_status: DQStatus,
    ) -> bool:
        return self.service.update_record_status(payload_hash, new_status)

    def get_stats(self, pipeline: str) -> dict[str, Any]:
        return self.service.get_pipeline_stats(pipeline)
