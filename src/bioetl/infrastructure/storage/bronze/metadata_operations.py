"""Metadata preparation helpers for Bronze writer side effects."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Protocol, cast

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
    from bioetl.domain.lineage import LineageGraphFragment, MetadataLineageBundle
    from bioetl.domain.models.metadata import (
        BronzeMetadata,
        BronzeMetadataInput,
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


class _BronzeMetadataBundleFactory(Protocol):
    """Callable contract exposed by coordinator bundle factory hooks."""

    def __call__(
        self,
        input_data: BronzeMetadataInput,
    ) -> MetadataLineageBundle[BronzeMetadata]:
        """Build bundled bronze metadata and lineage."""


def prepare_bronze_metadata_write(
    host: _BronzeMetadataWriteHostProtocol,
    request: BronzeMetadataWriteRequest,
) -> PreparedBronzeMetadataWrite:
    """Resolve metadata payload and target path for one Bronze write."""
    live_snapshot = _build_live_input_snapshot_ref_if_available(
        base_path=host.base_path,
        relative_path=request.relative_path,
        query_string=(
            None
            if request.source_metadata is None
            else request.source_metadata.query_string
        ),
    )
    source_metadata = (
        None
        if request.source_metadata is None
        else _attach_live_snapshot_to_source_metadata(
            source_metadata=request.source_metadata,
            snapshot=live_snapshot,
        )
    )
    completed_at = calculate_bronze_completed_at(request.ingestion_ts, request.duration)
    metadata_base_path = resolve_bronze_metadata_base_path(
        base_path=host.base_path,
        provider=request.provider,
        entity=request.entity,
        flat_structure=host._flat_structure,
    )

    coordinator = host._metadata_coordinator
    if coordinator is None:
        raise RuntimeError(
            "MetadataCoordinator with create_bronze_metadata_bundle is required "
            "for Bronze metadata publication: "
            f"provider={request.provider}, entity={request.entity}, "
            f"relative_path={request.relative_path}"
        )

    bronze_input = build_bronze_metadata_input(
        _build_bronze_metadata_input_request(
            request=request,
            completed_at=completed_at,
            source_metadata=source_metadata,
            live_snapshot=live_snapshot,
        )
    )
    create_bundle = _resolve_bronze_metadata_bundle_factory(coordinator)
    if not callable(create_bundle):
        raise RuntimeError(
            "MetadataCoordinator with create_bronze_metadata_bundle is required "
            "for Bronze metadata publication: "
            f"provider={request.provider}, entity={request.entity}, "
            f"relative_path={request.relative_path}"
        )
    bundle = create_bundle(bronze_input)
    return PreparedBronzeMetadataWrite(
        metadata_base_path=metadata_base_path,
        metadata=bundle.metadata,
        lineage_fragment=bundle.lineage_fragment,
    )


def _build_bronze_metadata_input_request(
    *,
    request: BronzeMetadataWriteRequest,
    completed_at: datetime,
    source_metadata: SourceMetadata | None,
    live_snapshot: InputSnapshotRef | None,
) -> BronzeMetadataInputRequest:
    """Build normalized Bronze metadata input payload for coordinator-backed flow."""
    input_snapshots = (
        () if source_metadata is None else tuple(source_metadata.input_snapshots)
    )
    if live_snapshot is not None and source_metadata is None:
        input_snapshots = (live_snapshot,)
    return BronzeMetadataInputRequest(
        batch_id=request.batch_id,
        record_count=request.record_count,
        compressed_size=request.compressed_size,
        output_path=request.relative_path,
        started_at=request.ingestion_ts,
        completed_at=completed_at,
        source_metadata=source_metadata,
        input_snapshots=input_snapshots,
    )


def _resolve_bronze_metadata_bundle_factory(
    coordinator: MetadataCoordinatorPort,
) -> _BronzeMetadataBundleFactory | None:
    """Return bundle factory only when the coordinator exposes the override hook."""
    if (
        "create_bronze_metadata_bundle" not in vars(coordinator)
        and getattr(
            type(coordinator),
            "create_bronze_metadata_bundle",
            None,
        )
        is None
    ):
        return None
    return cast(
        _BronzeMetadataBundleFactory | None,
        getattr(coordinator, "create_bronze_metadata_bundle", None),
    )


def _build_bronze_source_metadata_with_live_snapshot(
    *,
    source_metadata: SourceMetadata | None,
    snapshot: InputSnapshotRef | None,
) -> SourceMetadata | None:
    """Return source metadata enriched with the live snapshot when available."""
    if snapshot is None:
        return source_metadata
    if source_metadata is None:
        from bioetl.domain.models.metadata import SourceMetadata

        return SourceMetadata(type="api", input_snapshots=[snapshot])
    return _attach_live_snapshot_to_source_metadata(
        source_metadata=source_metadata,
        snapshot=snapshot,
    )


def _attach_live_snapshot_to_source_metadata(
    *,
    source_metadata: SourceMetadata,
    snapshot: InputSnapshotRef | None,
) -> SourceMetadata | None:
    """Attach the snapshot in-place while preserving ``source_metadata`` identity."""
    if snapshot is None:
        return source_metadata
    for existing in source_metadata.input_snapshots:
        if (
            existing.snapshot_id == snapshot.snapshot_id
            and existing.content_hash == snapshot.content_hash
            and existing.immutable_uri == snapshot.immutable_uri
        ):
            return source_metadata

    source_metadata.input_snapshots.append(snapshot)
    return source_metadata


def _build_live_input_snapshot_ref_if_available(
    *,
    base_path: Path,
    relative_path: str,
    query_string: str | None,
) -> InputSnapshotRef | None:
    """Build a live snapshot ref only when the Bronze output file already exists."""
    full_path = base_path / relative_path
    if not full_path.exists():
        return None
    return _build_live_input_snapshot_ref(
        full_path=full_path,
        relative_path=relative_path,
        query_string=query_string,
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
