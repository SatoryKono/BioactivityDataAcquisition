"""Pure helper functions for metadata coordinator orchestration."""

from __future__ import annotations

from typing import TypeVar

from bioetl.application.services.metadata_lineage_bundle import MetadataLineageBundle
from bioetl.domain.lineage import LineageGraphFragment
from bioetl.domain.models.metadata import (
    BronzeMetadata,
    FileOutputMetadata,
    GoldMetadata,
    SilverMetadata,
    SourceMetadata,
)
from bioetl.domain.ports import BronzeMetadataInput

_MetadataT = TypeVar(
    "_MetadataT",
    BronzeMetadata,
    SilverMetadata,
    GoldMetadata,
)


def validate_records_present(
    *,
    records: object,
    total_records: object,
    layer_name: str,
) -> None:
    """Reject sidecar creation when neither records nor total count are present."""
    if not records and total_records is None:
        raise ValueError(f"Cannot create {layer_name} metadata without records")


def create_metadata_bundle(
    *,
    metadata: _MetadataT,
    lineage_fragment: LineageGraphFragment,
) -> MetadataLineageBundle[_MetadataT]:
    """Bundle sidecar metadata with its canonical lineage fragment."""
    return MetadataLineageBundle(
        metadata=metadata,
        lineage_fragment=lineage_fragment,
    )


def build_bronze_source_metadata(input_data: BronzeMetadataInput) -> SourceMetadata:
    """Build Bronze source metadata, injecting query_string when needed."""
    if input_data.source_metadata is not None:
        source = input_data.source_metadata
        if input_data.query_string and source.query_string is None:
            updated_source: SourceMetadata = source.model_copy(
                update={"query_string": input_data.query_string}
            )
            return updated_source
        return source

    return SourceMetadata(
        type="api",
        query_string=input_data.query_string,
    )


def build_bronze_file_output_metadata(
    input_data: BronzeMetadataInput,
) -> FileOutputMetadata:
    """Build Bronze file metadata for output_ext."""
    return FileOutputMetadata(
        path=input_data.output_path,
        size_bytes=input_data.compressed_size,
        record_count=input_data.record_count,
    )
