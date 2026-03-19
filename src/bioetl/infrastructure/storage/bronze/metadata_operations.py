"""Metadata preparation helpers for Bronze writer side effects."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Protocol

from bioetl.domain.types import BatchID, RunID, RunType
from bioetl.infrastructure.storage.bronze.metadata_paths import (
    calculate_bronze_completed_at,
    resolve_bronze_metadata_base_path,
)
from bioetl.infrastructure.storage.bronze.reporting_helpers import (
    BronzeMetadataInputRequest,
    build_bronze_metadata_input,
)

if TYPE_CHECKING:
    from bioetl.domain.models.metadata import BronzeMetadata, SourceMetadata
    from bioetl.domain.ports import MetadataCoordinatorPort

__all__ = [
    "BronzeMetadataWriteRequest",
    "PreparedBronzeMetadataWrite",
    "prepare_bronze_metadata_write",
]


@dataclass(frozen=True, slots=True)
class BronzeMetadataWriteRequest:
    """Normalized request for one Bronze metadata sidecar write."""

    run_id: RunID
    run_type: RunType
    provider: str
    entity: str
    batch_id: BatchID
    record_count: int
    compressed_size: int
    relative_path: str
    ingestion_ts: datetime
    duration: float
    source_metadata: SourceMetadata | None


@dataclass(frozen=True, slots=True)
class PreparedBronzeMetadataWrite:
    """Prepared metadata write payload handed to the metadata writer."""

    metadata_base_path: Path
    metadata: BronzeMetadata


class _BronzeMetadataWriteHostProtocol(Protocol):
    """Typed host contract for Bronze metadata preparation."""

    _metadata_coordinator: MetadataCoordinatorPort | None
    _flat_structure: bool
    base_path: Path

    def _build_full_bronze_metadata(
        self,
        *,
        run_id: RunID,
        run_type: RunType,
        provider: str,
        entity: str,
        batch_id: BatchID,
        record_count: int,
        compressed_size: int,
        output_path: str,
        started_at: datetime,
        completed_at: datetime,
        duration_seconds: float,
        source_metadata: SourceMetadata | None,
    ) -> BronzeMetadata: ...


def prepare_bronze_metadata_write(
    host: _BronzeMetadataWriteHostProtocol,
    request: BronzeMetadataWriteRequest,
) -> PreparedBronzeMetadataWrite:
    """Resolve metadata payload and target path for one Bronze write."""
    completed_at = calculate_bronze_completed_at(request.ingestion_ts, request.duration)
    metadata_base_path = resolve_bronze_metadata_base_path(
        base_path=host.base_path,
        provider=request.provider,
        entity=request.entity,
        flat_structure=host._flat_structure,
    )

    if host._metadata_coordinator is None:
        metadata = host._build_full_bronze_metadata(
            run_id=request.run_id,
            run_type=request.run_type,
            provider=request.provider,
            entity=request.entity,
            batch_id=request.batch_id,
            record_count=request.record_count,
            compressed_size=request.compressed_size,
            output_path=request.relative_path,
            started_at=request.ingestion_ts,
            completed_at=completed_at,
            duration_seconds=request.duration,
            source_metadata=request.source_metadata,
        )
        return PreparedBronzeMetadataWrite(
            metadata_base_path=metadata_base_path,
            metadata=metadata,
        )

    bronze_input = build_bronze_metadata_input(
        BronzeMetadataInputRequest(
            batch_id=request.batch_id,
            record_count=request.record_count,
            compressed_size=request.compressed_size,
            output_path=request.relative_path,
            started_at=request.ingestion_ts,
            completed_at=completed_at,
            source_metadata=request.source_metadata,
        )
    )
    metadata = host._metadata_coordinator.create_bronze_metadata(bronze_input)
    return PreparedBronzeMetadataWrite(
        metadata_base_path=metadata_base_path,
        metadata=metadata,
    )
