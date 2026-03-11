"""Unit tests for OpenAlex client_helpers_mixin compatibility shim."""

from __future__ import annotations

import pytest


@pytest.mark.unit
class TestOpenAlexClientHelpersMixin:
    """Tests for backward-compatible import shim."""

    def test_reexports_canonical_class_and_compat_alias(self) -> None:
        """Shim should expose the canonical class and backward-compatible alias."""
        from bioetl.infrastructure.adapters.openalex.client_helpers_mixin import (
            OpenAlexAdapterHelpersMixin,
            _OpenAlexAdapterHelpersMixin,
        )
        from bioetl.infrastructure.adapters.openalex import client_helpers_mixin

        assert _OpenAlexAdapterHelpersMixin is OpenAlexAdapterHelpersMixin
        assert client_helpers_mixin.__all__ == [
            "OpenAlexAdapterHelpersMixin",
            "_OpenAlexAdapterHelpersMixin",
        ]
