"""Application-level bundle for metadata sidecars and lineage fragments."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Generic, TypeVar

from bioetl.domain.models.metadata import BronzeMetadata, GoldMetadata, SilverMetadata

if TYPE_CHECKING:
    from bioetl.domain.lineage import LineageGraphFragment

__all__ = ["MetadataLineageBundle", "MetadataLineageBundleResult", "MetadataT"]

MetadataT = TypeVar("MetadataT", BronzeMetadata, SilverMetadata, GoldMetadata)


def _attach_fragment_anchor(metadata: object, fragment_id: str) -> None:
    """Attach the canonical lineage fragment id to sidecar output metadata."""
    output = getattr(metadata, "output", None)
    if output is None or not hasattr(output, "lineage_fragment_id"):
        return
    output.lineage_fragment_id = fragment_id


@dataclass(frozen=True, slots=True)
class MetadataLineageBundleResult(Generic[MetadataT]):
    """Bundle one sidecar metadata payload together with its lineage fragment."""

    metadata: MetadataT
    lineage_fragment: LineageGraphFragment

    def __post_init__(self) -> None:
        """Keep sidecar summary and full lineage fragment explicitly linked."""
        _attach_fragment_anchor(
            metadata=self.metadata,
            fragment_id=self.lineage_fragment.fragment_id,
        )


MetadataLineageBundle = MetadataLineageBundleResult
