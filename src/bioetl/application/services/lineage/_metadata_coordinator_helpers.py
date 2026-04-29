# ruff: noqa: UP049
"""Pure helper functions for metadata coordinator orchestration."""

from __future__ import annotations

import hashlib
from pathlib import PurePath

from bioetl.domain.lineage import LineageGraphFragment, MetadataLineageBundleResult
from bioetl.domain.models.metadata import (
    BronzeMetadata,
    FileOutputMetadata,
    GoldMetadata,
    InputSnapshotRef,
    SilverMetadata,
    SourceMetadata,
)
from bioetl.domain.ports import BronzeMetadataInput
from bioetl.domain.serialization import serialize_to_canonical_json


def validate_records_present(
    *,
    records: object,
    total_records: object,
    layer_name: str,
) -> None:
    """Reject sidecar creation when neither records nor total count are present."""
    if not records and total_records is None:
        raise ValueError(f"Cannot create {layer_name} metadata without records")


def create_metadata_bundle[_MetadataT: (BronzeMetadata, SilverMetadata, GoldMetadata)](
    *,
    metadata: _MetadataT,
    lineage_fragment: LineageGraphFragment,
) -> MetadataLineageBundleResult[_MetadataT]:
    """Bundle sidecar metadata with its canonical lineage fragment."""
    return MetadataLineageBundleResult(
        metadata=metadata,
        lineage_fragment=lineage_fragment,
    )


def build_bronze_source_metadata(input_data: BronzeMetadataInput) -> SourceMetadata:
    """Build Bronze source metadata, injecting query_string when needed."""
    snapshots = _merge_input_snapshots(
        source=input_data.source_metadata,
        input_snapshots=input_data.input_snapshots,
    )
    if input_data.source_metadata is not None:
        source = input_data.source_metadata
        if (input_data.query_string and source.query_string is None) or snapshots:
            update_data: dict[str, object] = {}
            if input_data.query_string and source.query_string is None:
                update_data["query_string"] = input_data.query_string
            if snapshots:
                update_data["input_snapshots"] = snapshots
            updated_source: SourceMetadata = source.model_copy(update=update_data)
            return updated_source
        return source

    return SourceMetadata(
        type="api",
        query_string=input_data.query_string,
        input_snapshots=snapshots,
    )


def _merge_input_snapshots(
    *,
    source: SourceMetadata | None,
    input_snapshots: tuple[InputSnapshotRef, ...],
) -> list[InputSnapshotRef]:
    """Merge persisted and newly computed snapshots without duplicate identities."""
    merged: list[InputSnapshotRef] = []
    seen: set[tuple[str, str, str | None]] = set()

    for snapshot in [
        *(source.input_snapshots if source is not None else []),
        *input_snapshots,
    ]:
        key = (snapshot.snapshot_id, snapshot.content_hash, snapshot.immutable_uri)
        if key in seen:
            continue
        seen.add(key)
        merged.append(snapshot)

    return merged


def build_bronze_file_output_metadata(
    input_data: BronzeMetadataInput,
) -> FileOutputMetadata:
    """Build Bronze file metadata for output_ext."""
    return FileOutputMetadata(
        path=input_data.output_path,
        size_bytes=input_data.compressed_size,
        record_count=input_data.record_count,
    )


def build_bronze_output_content_hash(input_data: BronzeMetadataInput) -> str:
    """Build deterministic Bronze output identity from emitted file evidence."""
    payload = {
        "files": [
            {
                "path": PurePath(input_data.output_path).as_posix(),
                "record_count": input_data.record_count,
                "size_bytes": input_data.compressed_size,
                "content_hash": input_data.output_content_hash,
            }
        ]
    }
    canonical = serialize_to_canonical_json(payload)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
