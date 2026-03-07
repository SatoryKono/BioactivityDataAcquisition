"""Unit tests for UniProt metadata_mixin compatibility shim."""

from __future__ import annotations

import pytest


@pytest.mark.unit
class TestUniProtMetadataMixin:
    """Tests for backward-compatible import shim."""

    def test_import_canonical_class(self) -> None:
        """Should re-export UniProtAdapterMetadataMixin from canonical module."""
        from bioetl.infrastructure.adapters.uniprot.metadata_mixin import (
            UniProtAdapterMetadataMixin,
        )

        assert UniProtAdapterMetadataMixin is not None

    def test_import_private_alias(self) -> None:
        """Should re-export _UniProtAdapterMetadataMixin as backward-compatible alias."""
        from bioetl.infrastructure.adapters.uniprot.metadata_mixin import (
            _UniProtAdapterMetadataMixin,
        )

        assert _UniProtAdapterMetadataMixin is not None

    def test_alias_matches_canonical(self) -> None:
        """Private alias should be the same class as canonical export."""
        from bioetl.infrastructure.adapters.uniprot.metadata_mixin import (
            UniProtAdapterMetadataMixin,
            _UniProtAdapterMetadataMixin,
        )

        assert _UniProtAdapterMetadataMixin is UniProtAdapterMetadataMixin

    def test_all_exports(self) -> None:
        """__all__ should contain both names."""
        from bioetl.infrastructure.adapters.uniprot import metadata_mixin

        assert "UniProtAdapterMetadataMixin" in metadata_mixin.__all__
        assert "_UniProtAdapterMetadataMixin" in metadata_mixin.__all__
