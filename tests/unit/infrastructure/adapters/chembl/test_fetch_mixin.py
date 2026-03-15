"""Unit tests for ChEMBL fetch_mixin compatibility shim."""

from __future__ import annotations

import pytest


@pytest.mark.unit
def test_fetch_mixin_reexports_canonical_class_and_alias() -> None:
    """fetch_mixin should expose the canonical class and backward-compatible alias."""
    from bioetl.infrastructure.adapters.chembl import fetch_mixin
    from bioetl.infrastructure.adapters.chembl.fetch_adapter_mixin import (
        ChemblFetchAdapterMixin as CanonicalChemblFetchAdapterMixin,
    )
    from bioetl.infrastructure.adapters.chembl.fetch_mixin import (
        ChemblFetchAdapterMixin,
        ChemblFetchMixin,
    )

    assert ChemblFetchAdapterMixin is CanonicalChemblFetchAdapterMixin
    assert ChemblFetchMixin is CanonicalChemblFetchAdapterMixin
    assert fetch_mixin.__all__ == ["ChemblFetchAdapterMixin", "ChemblFetchMixin"]
