"""Metadata preparation helpers for Bronze writer side effects."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime
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
    from bioetl.domain.lineage import LineageGraphFragment
    from bioetl.domain.models.metadata import (
        BronzeMetadata,
        InputSnapshotRef,
        SourceMetadata,
    )
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
    lineage_fragment: LineageGraphFragment | None = None


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
    source_metadata = _build_bronze_source_metadata_with_live_snapshot(
        base_path=host.base_path,
        relative_path=request.relative_path,
        source_metadata=request.source_metadata,
    )
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
            source_metadata=source_metadata,
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
            source_metadata=source_metadata,
            input_snapshots=tuple(source_metadata.input_snapshots),
        )
    )
    create_bundle = (
        getattr(host._metadata_coordinator, "create_bronze_metadata_bundle", None)
        if (
            "create_bronze_metadata_bundle" in vars(host._metadata_coordinator)
            or getattr(
                type(host._metadata_coordinator),
                "create_bronze_metadata_bundle",
                None,
            )
            is not None
        )
        else None
    )
    if callable(create_bundle):
        bundle = create_bundle(bronze_input)
        return PreparedBronzeMetadataWrite(
            metadata_base_path=metadata_base_path,
            metadata=bundle.metadata,
            lineage_fragment=bundle.lineage_fragment,
        )
    metadata = host._metadata_coordinator.create_bronze_metadata(bronze_input)
    return PreparedBronzeMetadataWrite(
        metadata_base_path=metadata_base_path,
        metadata=metadata,
    )


def _build_bronze_source_metadata_with_live_snapshot(
    *,
    base_path: Path,
    relative_path: str,
    source_metadata: SourceMetadata | None,
) -> SourceMetadata | None:
    """Attach an immutable Bronze batch snapshot to source metadata when possible."""
    full_path = base_path / relative_path
    if not full_path.exists():
        return source_metadata

    snapshot = _build_live_input_snapshot_ref(
        full_path=full_path,
        relative_path=relative_path,
        query_string=None if source_metadata is None else source_metadata.query_string,
    )
    if source_metadata is None:
        from bioetl.domain.models.metadata import SourceMetadata

        return SourceMetadata(type="api", input_snapshots=[snapshot])

    for existing in source_metadata.input_snapshots:
        if (
            existing.snapshot_id == snapshot.snapshot_id
            and existing.content_hash == snapshot.content_hash
            and existing.immutable_uri == snapshot.immutable_uri
        ):
            return source_metadata

    return source_metadata.model_copy(
        update={"input_snapshots": [*source_metadata.input_snapshots, snapshot]}
    )


def _build_live_input_snapshot_ref(
    *,
    full_path: Path,
    relative_path: str,
    query_string: str | None,
) -> InputSnapshotRef:
    """Build a replayable snapshot ref from the persisted Bronze batch file."""
    from bioetl.domain.models.metadata import InputSnapshotRef

    content_hash = _compute_file_sha256(full_path)
    query_fingerprint = (
        None
        if not query_string
        else hashlib.sha256(query_string.encode("utf-8")).hexdigest()
    )
    snapshot_id = hashlib.sha256(
        f"bronze:{relative_path}:{content_hash}".encode()
    ).hexdigest()
    return InputSnapshotRef(
        snapshot_id=snapshot_id,
        content_hash=content_hash,
        immutable_uri=str(full_path),
        query_fingerprint=query_fingerprint,
        captured_at=datetime.fromtimestamp(full_path.stat().st_mtime, tz=UTC),
    )


def _compute_file_sha256(path: Path) -> str:
    """Hash the persisted Bronze batch bytes for replay-safe provenance."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
