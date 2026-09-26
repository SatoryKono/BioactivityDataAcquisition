"""Lineage and reporting helpers for Bronze writer side effects."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from bioetl.domain.models.metadata import InputSnapshotRef, SourceMetadata
from bioetl.domain.ports import (
    AuditEntry,
    AuditLayer,
    AuditOperation,
    BronzeMetadataInput,
)
from bioetl.domain.types import BatchID, RunID, RunType

__all__ = [
    "BronzeAuditWriteRequest",
    "BronzeMetadataInputRequest",
    "build_bronze_audit_entry",
    "build_bronze_metadata_input",
]


@dataclass(frozen=True, slots=True)
class BronzeAuditWriteRequest:
    """Contract for Bronze audit event construction."""

    run_id: RunID
    ingestion_ts: datetime
    relative_path: str
    batch_id: BatchID
    run_type: RunType
    record_count: int
    compressed_size: int
    uncompressed_size: int
    provider: str
    entity: str


@dataclass(frozen=True, slots=True)
class BronzeMetadataInputRequest:
    """Contract for Bronze metadata-coordinator input construction."""

    batch_id: BatchID
    record_count: int
    compressed_size: int
    output_path: str
    started_at: datetime
    completed_at: datetime
    source_metadata: SourceMetadata | None
    output_content_hash: str | None = None
    input_snapshots: tuple[InputSnapshotRef, ...] = ()


def build_bronze_audit_entry(request: BronzeAuditWriteRequest) -> AuditEntry:
    """Build the Bronze audit entry from the external write contract."""
    return AuditEntry(
        run_id=request.run_id,
        timestamp=request.ingestion_ts,
        layer=AuditLayer.BRONZE,
        table_name=request.relative_path,
        operation=AuditOperation.WRITE,
        records_count=request.record_count,
        metadata={
            "provider": request.provider,
            "entity": request.entity,
            "batch_id": str(request.batch_id),
            "run_type": request.run_type.value,
            "compressed_bytes": request.compressed_size,
            "uncompressed_bytes": request.uncompressed_size,
        },
    )


def build_bronze_metadata_input(
    request: BronzeMetadataInputRequest,
) -> BronzeMetadataInput:
    """Build the coordinator-facing Bronze metadata input payload."""
    return BronzeMetadataInput(
        batch_id=request.batch_id,
        record_count=request.record_count,
        compressed_size=request.compressed_size,
        output_path=request.output_path,
        started_at=request.started_at,
        completed_at=request.completed_at,
        output_content_hash=request.output_content_hash,
        source_metadata=request.source_metadata,
        input_snapshots=request.input_snapshots,
        query_string=(
            request.source_metadata.query_string
            if request.source_metadata is not None
            else None
        ),
    )
