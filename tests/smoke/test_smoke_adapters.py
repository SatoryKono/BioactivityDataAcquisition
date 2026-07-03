"""Smoke tests for provider adapter import health.

Verifies that each provider's client module loads cleanly,
catching missing dependencies or circular imports early.
"""

from __future__ import annotations

import importlib

import pytest

_ADAPTER_MODULES = [
    "bioetl.infrastructure.adapters.chembl.client",
    "bioetl.infrastructure.adapters.crossref.client",
    "bioetl.infrastructure.adapters.openalex.client",
    "bioetl.infrastructure.adapters.pubchem.client",
    "bioetl.infrastructure.adapters.pubmed",
    "bioetl.infrastructure.adapters.semanticscholar",
    "bioetl.infrastructure.adapters.uniprot.client",
    "bioetl.application.composite.merger",
]


@pytest.mark.smoke
class TestAdapterImportHealth:
    """Parametrized import guard for provider adapter modules."""

    @pytest.mark.parametrize("module_path", _ADAPTER_MODULES)
    def test_module_importable(self, module_path: str) -> None:
        """Each adapter module must import without errors."""
        module = importlib.import_module(module_path)
        assert module is not None
