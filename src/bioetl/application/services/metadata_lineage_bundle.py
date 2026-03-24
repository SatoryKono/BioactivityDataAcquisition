"""Application-level bundle for metadata sidecars and lineage fragments."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, TypeVar

from bioetl.domain.lineage import LineageGraphFragment
from bioetl.domain.models.metadata import BronzeMetadata, GoldMetadata, SilverMetadata

__all__ = ["MetadataLineageBundle", "MetadataT"]

MetadataT = TypeVar("MetadataT", BronzeMetadata, SilverMetadata, GoldMetadata)


@dataclass(frozen=True, slots=True)
class MetadataLineageBundle(Generic[MetadataT]):
    """Bundle one sidecar metadata payload together with its lineage fragment."""

    metadata: MetadataT
    lineage_fragment: LineageGraphFragment
