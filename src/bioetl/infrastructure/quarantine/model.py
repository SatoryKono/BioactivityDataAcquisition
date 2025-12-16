"""Quarantine data models.

Defines the structure of quarantine records.
"""
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any

from bioetl.domain.types import BatchID, DQStatus


@dataclass
class QuarantineRecord:
    """Represents a single record in quarantine."""

    ingestion_ts: str
    pipeline: str
    error_code: str
    payload: str  # JSON string
    payload_hash: str
    payload_truncated: bool
    bronze_batch_id: str
    bronze_file_uri: str
    error_details: str  # JSON string
    dq_status: str = DQStatus.NEW.value

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
