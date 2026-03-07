"""Unit tests for OpenAlex client_helpers_mixin compatibility shim."""

from __future__ import annotations

import pytest


@pytest.mark.unit
class TestOpenAlexClientHelpersMixin:
    """Tests for backward-compatible import shim."""

    def test_import_canonical_class(self) -> None:
        """Should re-export OpenAlexAdapterHelpersMixin from canonical module."""
        from bioetl.infrastructure.adapters.openalex.client_helpers_mixin import (
            OpenAlexAdapterHelpersMixin,
        )

        assert OpenAlexAdapterHelpersMixin is not None

    def test_import_private_alias(self) -> None:
        """Should re-export _OpenAlexAdapterHelpersMixin as backward-compatible alias."""
        from bioetl.infrastructure.adapters.openalex.client_helpers_mixin import (
            _OpenAlexAdapterHelpersMixin,
        )

        assert _OpenAlexAdapterHelpersMixin is not None

    def test_alias_matches_canonical(self) -> None:
        """Private alias should be the same class as canonical export."""
        from bioetl.infrastructure.adapters.openalex.client_helpers_mixin import (
            OpenAlexAdapterHelpersMixin,
            _OpenAlexAdapterHelpersMixin,
        )

        assert _OpenAlexAdapterHelpersMixin is OpenAlexAdapterHelpersMixin

    def test_all_exports(self) -> None:
        """__all__ should contain both names."""
        from bioetl.infrastructure.adapters.openalex import client_helpers_mixin

        assert "OpenAlexAdapterHelpersMixin" in client_helpers_mixin.__all__
        assert "_OpenAlexAdapterHelpersMixin" in client_helpers_mixin.__all__
