"""Backward-compatible re-export for metadata coordinator contracts.

Compatibility shim: canonical Port Protocol definitions remain @runtime_checkable
in subpackages and are re-exported here for stable import paths."""

from bioetl.domain.ports.metadata.coordinator import (
    BronzeMetadataInput,
    GoldMetadataInput,
    MetadataCoordinatorPort,
    SilverMetadataInput,
    SilverRef,
)

__all__ = [
    "BronzeMetadataInput",
    "GoldMetadataInput",
    "MetadataCoordinatorPort",
    "SilverMetadataInput",
    "SilverRef",
]
