"""Compatibility shim for UniProt metadata adapter mixin.

Canonical implementation lives in ``metadata_adapter_mixin.py``.
"""

from __future__ import annotations

from bioetl.infrastructure.adapters.uniprot.metadata_adapter_mixin import (
    UniProtAdapterMetadataMixin,
)

# Backward-compatible alias for existing imports.
_UniProtAdapterMetadataMixin = UniProtAdapterMetadataMixin

__all__ = ["UniProtAdapterMetadataMixin", "_UniProtAdapterMetadataMixin"]
