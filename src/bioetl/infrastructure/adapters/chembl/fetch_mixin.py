"""Compatibility shim for ChEMBL adapter fetch mixin.

Canonical implementation lives in ``fetch_adapter_mixin.py``.
"""

from __future__ import annotations

from bioetl.infrastructure.adapters.chembl.fetch_adapter_mixin import (
    ChemblFetchAdapterMixin,
)

# Backward-compatible alias for existing imports.
ChemblFetchMixin = ChemblFetchAdapterMixin

__all__ = ["ChemblFetchAdapterMixin", "ChemblFetchMixin"]
